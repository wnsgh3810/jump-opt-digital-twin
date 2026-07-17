# -*- coding: utf-8 -*-
"""p25_a4_ilqr — P25 Phase A-iv: iLQR(box-DDP)를 **트윈 원본 위에서** (대리모델 없음).

사용자 지시(07-17): "디지털 트윈 모델 그대로에서의 최적화" — 기울기(미분) 기반
궤적최적화를 해석적 근사 없이, 정확히 그 MuJoCo 트윈(mj_step + 측정 법칙층 전부)
위에서 수행한다. 미분은 MuJoCo 내장 유한차분 `mujoco.mjd_transitionFD`.

═══ 결정변수·스텝 구조 ═══
  u_t ∈ R² = raw 토크 커맨드 (관절 2개), 박스 |u| ≤ 35.5 (R19.CLIP = 공급 천장).
  제어 dt = 5 ms (= 모델 dt 0.5 ms × 서브스텝 M=10, ZOH), horizon 0.6 s → N=120 노드.
  1 유효스텝 F(z,u) = [필터 → 클립 → ahat → supp/rise/스프링/힙 층 → mj_step] × M
  — cl_run23/rollout_ol과 **동일한 커맨드 체인** (substep()이 rollout_ol 창 내부 본체의
  문자 미러; 골든 G2가 비트 동일 증명).

═══ 증강 상태 (12차원) ═══
  z = [qpos(5), qvel(5), c1f, c2f] — c1f/c2f는 tm 1차 필터 상태 (tm=1.31 ms ≈ 2.6 dt,
  메모리가 있으므로 상태에 포함해야 미분이 정확). 관절이 전부 slide/hinge (nq=nv=5)라
  qpos = 접선공간 그대로.

═══ 미분 체인 (핵심 미묘점 — 층이 스텝 함수의 일부) ═══
  mjd_transitionFD는 mj_step을 (상태, ctrl)에 대해 미분할 뿐, ctrl·qfrc_applied가
  상태·u의 함수(층)라는 걸 모른다. 따라서 서브스텝마다:
    ① A_mj(10×10), B_mj(10×2) = mjd_transitionFD (ctrl 고정점 기준, centered, eps=1e-6)
    ② Bq(10×1) = qfrc_applied[knee] 채널 수동 centered FD (eps=1e-3 Nm)
       — 게이트 스프링 토크가 qfrc로 들어가는데 transitionFD는 이 채널 미분을 안 주므로.
    ③ J_L(3×5) = 소형 층 사상 (v1c, v2c, q_knee, w1, w2) → (ctrl1, ctrl2, qfrc_knee)
       의 FD 야코비안 (eps=1e-6; w = 필터 출력). 층은 조각-매끄러움 (min/|·|/sgn 킹크는
       측도 0 — FD가 킹크 위에선 평균 기울기를 줌, 문서화된 한계).
    ④ 조립:  A_sub[:10,:10] = A_mj + [B_mj|Bq]·J_L∘(상태 배선: v1c=-qvel[1],
       v2c=-qvel[2], qk=qpos[4]),  필터 행 = (1-al)·I,  B_sub = [B_mj|Bq]·J_L_w·al + al·I행
       (al = dt/tm = 0.382; 필터가 u→w 선형이라 체인룰이 정확).
    매크로 스텝(M 서브스텝, ZOH u): A_t = ∏A_sub, B_t = Σ(∏A_sub)·B_sub.
  검증 (골든 G3): 위 체인 vs **유효스텝 전체의 직접 FD** (12+2 차원 centered) —
  Frobenius 상대오차 < 1e-3 (접촉 전이 상태는 별도 보고).

═══ 박스 처리 (문서화) ═══
  box-DDP (Tassa 2014) 방식: 후진패스에서 2차원 box-QP를 활성집합 완전 열거(9경우)로
  정확히 풀어 k(피드포워드)·K(자유행만) 산출, 전진패스는 u를 ±35.5로 클램프.
  |u| ≤ 35.5면 필터 출력 w도 볼록결합으로 자동 ≤ 35.5 → 플랜트 클립층은 불활성
  (경계 자체에서만 반기울기 — 측도 0, 문서화). squash(tanh) 대신 이 방식을 쓴 이유:
  최대점프 해는 천장 라이딩(bang-bang성)이 강해 squash는 경계 접근이 점근적으로 느림.

═══ 비용 ═══
  running: 0.5·R_U·|u|²·dt_c + W_ENV·dt_c·Σ hinge²(관절 포락선 +10% 위반) [매끈 C¹]
  terminal: −W_H·(bz + sp(vz)²/(2g)),  sp(v)=0.5(v+√(v²+ε²)) (매끈 양수부, ε=0.1)
  — 탄도 apex 프록시. vz² 원형 대신 sp²를 쓰는 이유: vz<0(하강)에도 vz²가 커지는
  "다이브 인센티브"를 차단 (상승 중이면 sp≈vz라 프록시 = 탄도 apex 그대로).
  이지 후 비행 중엔 bz+vz²/2g가 보존량이라 horizon 끝이 apex 이전이어도 정확.

═══ 접촉 불연속 (알려진 난점) 처리 ═══
  · 스탠스→이지: 트윈 접촉이 soft(solref/solimp)라 전이가 유한 강성으로 매끈화 —
    FD 야코비안이 유한값. 전이 순간에 걸친 상태는 G3에서 오차 별도 보고.
  · horizon 2종 실험: (i) through-liftoff 0.6 s (주력 — 비행 구간까지 미분),
    (ii) stance-only 0.35 s (terminal 프록시를 이지 부근에서 평가 — 비행 미분 회피).
  · 착지 재접촉은 horizon 내 없음 (apex ~0.68 s > 0.6 s).
  · 발산/크래시 롤아웃 = 비용 ∞ (라인서치가 자동 기각), 정규화 μ 스케줄이 방어.

═══ 초기화 ═══
  (a) crouch-hold: settle 끝 PD 커맨드를 전 구간 상수 유지 (중력 보상 근사)
  (b) warm: p25_a_*.npz (Phase A 형제 산출물) 존재 시 그 raw 궤적 리샘플
  (c) measured: 0602 첫 trial 측정 raw 푸시 (CMA 시드와 동일 규약) — (b) 부재 시 대체

산출: p25_a4_ilqr.npz (Phase A 공통 스키마 + q_des:=q, dq_des:=dq) ·
p25_a4_results.json · p25_a4_cost_curve.png (auto color cycle, Malgun Gothic).
철칙: 데이터 읽기 전용 · 단일 프로세스 (OMP_NUM_THREADS=2) · p25_a_*.py 불변 (import만).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")   # 다른 무거운 작업 병행 중 — 단일 프로세스
os.environ["PYTHONIOENCODING"] = "utf-8"

import p25_a_twin as TW      # ★ 첫 repo-import — P23/P24 env 플래그 4종을 import 전에 설정

import sys
import time
from pathlib import Path

import numpy as np
import mujoco

import p23_v6_runners as RU
import p19_run as R19
import safe

HERE = Path(__file__).parent

# ── 하이퍼파라미터 (전부 여기 고정) ──
DT_C = 0.005                 # 제어 dt [s] (스펙 4-5 ms)
T_HOR = 0.6                  # 주력 horizon [s] (MARATHON 동결)
T_STANCE = 0.35              # stance-only 변형 horizon [s]
G_GRAV = 9.81
R_U = 1e-5                   # u 정칙화 [1/raw²]
W_ENV = 100.0                # 포락선 hinge² 가중 [1/rad²]
W_H = 1.0                    # apex 프록시 가중 [1/m]
EPS_SP = 0.1                 # 매끈 양수부 ε [m/s]
EPS_FD = 1e-6                # mjd_transitionFD eps
EPS_Q = 1e-3                 # qfrc 채널 수동 FD eps [Nm]
EPS_L = 1e-6                 # 층 사상 FD eps
MU0, MU_MIN, MU_MAX = 1e-2, 1e-9, 1e8
MU_UP, MU_DN = 6.0, 3.0
ALPHAS = [1.0, 0.5, 0.25, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]
MAX_IT = 120
BUDGET_S = 1500.0            # run당 wall 상한 [s]
TOL_REL = 1e-6               # 상대 개선 수렴 임계
NX = 12                      # 증강 상태 차원
NU = 2


# ══════════════════ 컨텍스트 ══════════════════
def ctx_of(tw):
    P = tw["P"]
    mj = P.J._P["mj"]
    model = tw["model"]
    return dict(P=P, mj=mj, model=model, A=P.A_PAPER, law=tw["law"], kr=tw["kr"],
                sprm=tw["sprm"], tm=tw["tm"], dt=tw["dt"],
                al=tw["dt"] / max(tw["tm"], tw["dt"]),
                dof_knee=safe.dofadr(model, "knee", mj),
                iq_k=safe.qadr(model, "knee", mj),
                md=mj.MjData(model), mdJ=mj.MjData(model), env=tw["env"])


# ══════════════════ 유효 서브스텝 (rollout_ol 창 내부 본체 문자 미러 — 골든 G2) ══════════════════
def substep(cx, md, c1f, c2f, u1, u2):
    """[필터 → 클립 → ahat → 층 → mj_step] 1회. 반환 (c1f, c2f, s1, s2, c1, c2, w들).
    연산 순서·표현식을 rollout_ol과 문자 동일하게 유지 (비트 일치가 골든 G2)."""
    law_a, law_b, law_v0 = cx["law"]
    kr = cx["kr"]; sprm = cx["sprm"]; al = cx["al"]; A = cx["A"]
    v1c = -md.qvel[1]; v2c = -md.qvel[2]
    c1 = float(u1)
    c2 = float(u2)
    c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
    c1 = float(np.clip(c1f, -R19.CLIP, R19.CLIP))
    c2 = float(np.clip(c2f, -R19.CLIP, R19.CLIP))
    s1 = TW._ahat_s(A, c1, v1c)
    s2 = TW._ahat_s(A, c2, v2c)
    supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
    if kr:
        supp += float(RU.rise_term(v2c, kr, law_v0))
    tql = 0.0
    if sprm is not None:
        tql += RU.spr_tau(float(md.qpos[cx["iq_k"]]), abs(s2), sprm)
    md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
    md.qfrc_applied[cx["dof_knee"]] = tql
    cx["mj"].mj_step(cx["model"], md)
    return c1f, c2f, s1, s2, c1, c2


def layer_out(cx, v1c, v2c, qk, w1, w2):
    """소형 층 사상 (필터 출력 w, 상태 성분) → (ctrl1, ctrl2, qfrc_knee).
    substep과 동일 연산 (mj_step 제외) — 미분 대상의 정의."""
    law_a, law_b, law_v0 = cx["law"]
    c1 = float(np.clip(w1, -R19.CLIP, R19.CLIP))
    c2 = float(np.clip(w2, -R19.CLIP, R19.CLIP))
    s1 = TW._ahat_s(cx["A"], c1, v1c)
    s2 = TW._ahat_s(cx["A"], c2, v2c)
    supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
    if cx["kr"]:
        supp += float(RU.rise_term(v2c, cx["kr"], law_v0))
    tql = 0.0
    if cx["sprm"] is not None:
        tql += RU.spr_tau(qk, abs(s2), cx["sprm"])
    return np.array([-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp), tql])


def layer_jac(cx, v1c, v2c, qk, w1, w2):
    """층 사상 3×5 야코비안 — centered FD (조각-매끄러움; 킹크 위 평균 기울기)."""
    J = np.zeros((3, 5))
    x0 = [v1c, v2c, qk, w1, w2]
    for i in range(5):
        xp = list(x0); xm = list(x0)
        xp[i] += EPS_L; xm[i] -= EPS_L
        J[:, i] = (layer_out(cx, *xp) - layer_out(cx, *xm)) / (2 * EPS_L)
    return J


# ══════════════════ 롤아웃 (명목 + 저장 / 전진패스) ══════════════════
def _reset_md(cx, md, qpos, qvel):
    md.qpos[:] = qpos; md.qvel[:] = qvel
    md.time = 0.0
    md.qacc_warmstart[:] = 0.0
    md.qfrc_applied[:] = 0.0
    md.ctrl[:] = 0.0
    cx["mj"].mj_forward(cx["model"], md)


def rollout(cx, z0, U, M, store=False):
    """ZOH 커맨드 U(N×2)로 유효스텝 N회. 반환 dict:
    cost, X(N+1×12 노드), (store시) 서브스텝 저장(sub) — 크래시면 None."""
    md = cx["md"]
    _reset_md(cx, md, z0["qpos"], z0["qvel"])
    c1f, c2f = float(z0["c1f"]), float(z0["c2f"])
    N = U.shape[0]
    X = np.zeros((N + 1, NX))
    sub = dict(qpos=np.zeros((N * M, 5)), qvel=np.zeros((N * M, 5)),
               warm=np.zeros((N * M, 5)), time=np.zeros(N * M),
               c1f=np.zeros(N * M), c2f=np.zeros(N * M),
               ctrl=np.zeros((N * M, 2)), qfrc=np.zeros(N * M),
               w=np.zeros((N * M, 2))) if store else None
    cost = 0.0
    for j in range(N):
        X[j] = np.concatenate([md.qpos, md.qvel, [c1f, c2f]])
        cost += run_cost(cx, X[j], U[j])
        for i in range(M):
            k = j * M + i
            if store:
                sub["qpos"][k] = md.qpos; sub["qvel"][k] = md.qvel
                sub["warm"][k] = md.qacc_warmstart; sub["time"][k] = md.time
                sub["c1f"][k] = c1f; sub["c2f"][k] = c2f
            c1f, c2f, s1, s2, c1, c2 = substep(cx, md, c1f, c2f, U[j, 0], U[j, 1])
            if store:
                sub["ctrl"][k] = md.ctrl
                sub["qfrc"][k] = md.qfrc_applied[cx["dof_knee"]]
                sub["w"][k] = [c1f, c2f]
            if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
                return None
    X[N] = np.concatenate([md.qpos, md.qvel, [c1f, c2f]])
    cost += term_cost(cx, X[N])
    return dict(cost=float(cost), X=X, sub=sub, U=U.copy())


def forward_pass(cx, z0, nom, ks, Ks, alpha, M):
    """전진패스: u = clip(u_nom + α·k + K·δz, ±CLIP) — box-DDP 클램프."""
    md = cx["md"]
    _reset_md(cx, md, z0["qpos"], z0["qvel"])
    c1f, c2f = float(z0["c1f"]), float(z0["c2f"])
    N = nom["U"].shape[0]
    Xn = nom["X"]
    U = np.zeros((N, NU))
    X = np.zeros((N + 1, NX))
    cost = 0.0
    for j in range(N):
        z = np.concatenate([md.qpos, md.qvel, [c1f, c2f]])
        X[j] = z
        u = nom["U"][j] + alpha * ks[j] + Ks[j] @ (z - Xn[j])
        u = np.clip(u, -R19.CLIP, R19.CLIP)
        U[j] = u
        cost += run_cost(cx, z, u)
        for i in range(M):
            c1f, c2f, *_ = substep(cx, md, c1f, c2f, u[0], u[1])
            if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
                return None
    X[N] = np.concatenate([md.qpos, md.qvel, [c1f, c2f]])
    cost += term_cost(cx, X[N])
    return dict(cost=float(cost), X=X, sub=None, U=U)


# ══════════════════ 비용 (해석 미분 포함) ══════════════════
def _hinges(cx, z):
    """측정좌표 q1=-qpos[1]-π/2, q2=-qpos[2]의 포락선 위반 (hi측, lo측) 4개."""
    q1 = -z[1] - np.pi / 2; q2 = -z[2]
    l1, h1 = cx["env"]["q1"]; l2, h2 = cx["env"]["q2"]
    return (max(q1 - h1, 0.0), max(l1 - q1, 0.0),
            max(q2 - h2, 0.0), max(l2 - q2, 0.0))


def run_cost(cx, z, u):
    a, b, c, d = _hinges(cx, z)
    return (0.5 * R_U * float(u @ u) + W_ENV * (a * a + b * b + c * c + d * d)) * DT_C


def run_cost_derivs(cx, z, u):
    """(lx, lu, lxx, luu) — lux=0. hinge²는 C¹ (경계에서 기울기 0 연속)."""
    lx = np.zeros(NX); lxx = np.zeros((NX, NX))
    a, b, c, d = _hinges(cx, z)
    w = 2.0 * W_ENV * DT_C
    # q1 = -z1 - π/2 → dq1/dz1 = -1 ;  q2 = -z2 → dq2/dz2 = -1
    lx[1] = w * (a * -1.0 + b * 1.0)      # d(a²)/dz1 = 2a·(dq1/dz1)=-2a ; b: d(l-q1)/dz1=+1
    lx[2] = w * (c * -1.0 + d * 1.0)
    lxx[1, 1] = w * ((1.0 if a > 0 else 0.0) + (1.0 if b > 0 else 0.0))
    lxx[2, 2] = w * ((1.0 if c > 0 else 0.0) + (1.0 if d > 0 else 0.0))
    lu = R_U * DT_C * u
    luu = R_U * DT_C * np.eye(NU)
    return lx, lu, lxx, luu


def _sp(v):
    """매끈 양수부 sp(v)=0.5(v+√(v²+ε²)) 와 1·2차 도함수."""
    r = np.sqrt(v * v + EPS_SP * EPS_SP)
    return 0.5 * (v + r), 0.5 * (1.0 + v / r), 0.5 * EPS_SP * EPS_SP / r ** 3


def apex_proxy(z):
    """탄도 apex 프록시 [m]: bz + sp(vz)²/2g."""
    s, _, _ = _sp(z[5])
    return float(z[0] + s * s / (2 * G_GRAV))


def term_cost(cx, z):
    return -W_H * apex_proxy(z)


def term_derivs(cx, z):
    fx = np.zeros(NX); fxx = np.zeros((NX, NX))
    s, s1, s2 = _sp(z[5])
    fx[0] = -W_H
    fx[5] = -W_H * s * s1 / G_GRAV
    fxx[5, 5] = -W_H * (s1 * s1 + s * s2) / G_GRAV
    return fx, fxx


# ══════════════════ 야코비안 (체인 = mjd_transitionFD + 층 체인룰) ══════════════════
def _restore_sub(cx, md, sub, k):
    md.qpos[:] = sub["qpos"][k]; md.qvel[:] = sub["qvel"][k]
    md.qacc_warmstart[:] = sub["warm"][k]; md.time = sub["time"][k]
    md.ctrl[:] = sub["ctrl"][k]
    md.qfrc_applied[:] = 0.0
    md.qfrc_applied[cx["dof_knee"]] = sub["qfrc"][k]


def _qfrc_col(cx, sub, k):
    """qfrc_applied[knee] 채널의 상태 민감도 열 (10,) — 수동 centered FD."""
    md = cx["mdJ"]; mj = cx["mj"]; m = cx["model"]
    xs = []
    for sgn in (1.0, -1.0):
        _restore_sub(cx, md, sub, k)
        md.qfrc_applied[cx["dof_knee"]] = sub["qfrc"][k] + sgn * EPS_Q
        mj.mj_step(m, md)
        xs.append(np.concatenate([md.qpos, md.qvel]))
    return (xs[0] - xs[1]) / (2 * EPS_Q)


def substep_jac(cx, sub, k, u):
    """서브스텝 k의 (A_sub 12×12, B_sub 12×2) — 모듈 docstring ①~④."""
    md = cx["mdJ"]; mj = cx["mj"]; m = cx["model"]; al = cx["al"]
    _restore_sub(cx, md, sub, k)
    Amj = np.zeros((10, 10)); Bmj = np.zeros((10, 2))
    mujoco.mjd_transitionFD(m, md, EPS_FD, True, Amj, Bmj, None, None)
    Bq = _qfrc_col(cx, sub, k)
    # 층 야코비안 (명목 지점: 필터 갱신 후 w, 스텝 전 상태)
    c1f, c2f = sub["c1f"][k], sub["c2f"][k]
    w1 = c1f + al * (float(u[0]) - c1f); w2 = c2f + al * (float(u[1]) - c2f)
    v1c = -sub["qvel"][k][1]; v2c = -sub["qvel"][k][2]; qk = float(sub["qpos"][k][4])
    Jl = layer_jac(cx, v1c, v2c, qk, w1, w2)          # (ctrl1,ctrl2,qfrc) × (v1,v2,qk,w1,w2)
    BB = np.column_stack([Bmj, Bq])                   # 10×3
    Jlx = np.zeros((3, 10))
    Jlx[:, 4] = Jl[:, 2]                              # qk = qpos[4]
    Jlx[:, 6] = -Jl[:, 0]                             # v1c = -qvel[1]
    Jlx[:, 7] = -Jl[:, 1]                             # v2c = -qvel[2]
    A = np.zeros((NX, NX)); B = np.zeros((NX, NU))
    A[:10, :10] = Amj + BB @ Jlx
    A[:10, 10:] = (BB @ Jl[:, 3:5]) * (1.0 - al)
    A[10, 10] = 1.0 - al; A[11, 11] = 1.0 - al
    B[:10, :] = (BB @ Jl[:, 3:5]) * al
    B[10, 0] = al; B[11, 1] = al
    return A, B


def macro_jacs(cx, nom, M):
    """전 매크로 스텝의 (A_t, B_t) — 서브스텝 체인 곱."""
    N = nom["U"].shape[0]
    As = np.zeros((N, NX, NX)); Bs = np.zeros((N, NX, NU))
    for j in range(N):
        Phi = np.eye(NX); Psi = np.zeros((NX, NU))
        for i in range(M):
            A, B = substep_jac(cx, nom["sub"], j * M + i, nom["U"][j])
            Phi = A @ Phi
            Psi = A @ Psi + B
        As[j] = Phi; Bs[j] = Psi
    return As, Bs


def macro_step_raw(cx, z, u, M, warm0=None):
    """검증용: 증강 상태 z에서 유효 매크로스텝 1회 → z' (12,)."""
    md = cx["mdJ"]; mj = cx["mj"]; m = cx["model"]
    md.qpos[:] = z[:5]; md.qvel[:] = z[5:10]
    md.qacc_warmstart[:] = 0.0 if warm0 is None else warm0
    md.time = 0.0
    md.qfrc_applied[:] = 0.0
    c1f, c2f = float(z[10]), float(z[11])
    for i in range(M):
        c1f, c2f, *_ = substep(cx, md, c1f, c2f, u[0], u[1])
    return np.concatenate([md.qpos, md.qvel, [c1f, c2f]])


def macro_jac_fd(cx, z, u, M, warm0=None, ex=1e-6, eu=1e-5):
    """검증용: 유효 매크로스텝 전체의 직접 centered FD (A_fd 12×12, B_fd 12×2)."""
    A = np.zeros((NX, NX)); B = np.zeros((NX, NU))
    for i in range(NX):
        zp = z.copy(); zm = z.copy()
        zp[i] += ex; zm[i] -= ex
        A[:, i] = (macro_step_raw(cx, zp, u, M, warm0)
                   - macro_step_raw(cx, zm, u, M, warm0)) / (2 * ex)
    for i in range(NU):
        up = u.copy(); um = u.copy()
        up[i] += eu; um[i] -= eu
        B[:, i] = (macro_step_raw(cx, z, up, M, warm0)
                   - macro_step_raw(cx, z, um, M, warm0)) / (2 * eu)
    return A, B


# ══════════════════ box-QP (2차원, 활성집합 완전 열거 — box-DDP 후진패스용) ══════════════════
def boxqp2(Q, q, lo, hi):
    """min ½δᵀQδ + qᵀδ, lo≤δ≤hi. 반환 (δ*, free_mask) | None(Q 비정치).
    볼록 QP: 활성집합 9경우의 (자유부 무제약 최소, 박스 사영 코너) 중 실현가능 최소가 해."""
    if Q[0, 0] <= 0 or Q[1, 1] <= 0 or np.linalg.det(Q) <= 0:
        return None
    best = None
    for m1 in (0, 1, 2):            # 0=free, 1=lo, 2=hi
        for m2 in (0, 1, 2):
            d = np.zeros(2)
            fixed = []
            if m1:
                d[0] = lo[0] if m1 == 1 else hi[0]
                fixed.append(0)
            if m2:
                d[1] = lo[1] if m2 == 1 else hi[1]
                fixed.append(1)
            free = [i for i in (0, 1) if i not in fixed]
            if free:
                F = np.ix_(free, free)
                rhs = -(q[free] + (Q[np.ix_(free, fixed)] @ d[fixed] if fixed else 0.0))
                try:
                    d[free] = np.linalg.solve(Q[F], np.atleast_1d(rhs))
                except np.linalg.LinAlgError:
                    continue
                if any(d[i] < lo[i] - 1e-12 or d[i] > hi[i] + 1e-12 for i in free):
                    continue
            val = float(q @ d + 0.5 * d @ Q @ d)
            if best is None or val < best[0]:
                fm = np.array([i in free for i in (0, 1)])
                best = (val, d.copy(), fm)
    if best is None:
        return None
    return best[1], best[2]


# ══════════════════ 후진패스 ══════════════════
def backward_pass(cx, nom, As, Bs, mu):
    """box-DDP 후진패스 (상태 정규화 변형: Quu_reg = luu + Bᵀ(Vxx+μI)B).
    반환 (ks, Ks, dV1, dV2) | None(비정치 → μ 인상 필요)."""
    N = nom["U"].shape[0]
    X = nom["X"]; U = nom["U"]
    fx, fxx = term_derivs(cx, X[N])
    Vx = fx; Vxx = fxx
    ks = np.zeros((N, NU)); Ks = np.zeros((N, NU, NX))
    dV1 = dV2 = 0.0
    lo = np.full(NU, -R19.CLIP); hi = np.full(NU, R19.CLIP)
    for j in range(N - 1, -1, -1):
        A, B = As[j], Bs[j]
        lx, lu, lxx, luu = run_cost_derivs(cx, X[j], U[j])
        Qx = lx + A.T @ Vx
        Qu = lu + B.T @ Vx
        Qxx = lxx + A.T @ Vxx @ A
        Quu = luu + B.T @ Vxx @ B
        Qux = B.T @ Vxx @ A
        Vxx_reg = Vxx + mu * np.eye(NX)
        Quu_r = luu + B.T @ Vxx_reg @ B
        Qux_r = B.T @ Vxx_reg @ A
        sol = boxqp2(Quu_r, Qu, lo - U[j], hi - U[j])
        if sol is None:
            return None
        k, free = sol
        K = np.zeros((NU, NX))
        if free.any():
            F = np.where(free)[0]
            try:
                K[F, :] = -np.linalg.solve(Quu_r[np.ix_(F, F)], Qux_r[F, :])
            except np.linalg.LinAlgError:
                return None
        ks[j] = k; Ks[j] = K
        dV1 += float(k @ Qu)
        dV2 += 0.5 * float(k @ Quu @ k)
        Vx = Qx + K.T @ Quu @ k + K.T @ Qu + Qux.T @ k
        Vxx = Qxx + K.T @ Quu @ K + K.T @ Qux + Qux.T @ K
        Vxx = 0.5 * (Vxx + Vxx.T)
    return ks, Ks, float(dV1), float(dV2)


# ══════════════════ iLQR 본체 ══════════════════
def ilqr(cx, z0, U0, M, tag, log):
    t0 = time.time()
    nom = rollout(cx, z0, U0, M, store=True)
    if nom is None:
        raise RuntimeError(f"[{tag}] 초기 롤아웃 발산 — 시드 재선정 필요")
    mu = MU0
    curve = [nom["cost"]]
    n_acc = n_rej = 0
    small = 0
    stop = "max_iter"
    for it in range(1, MAX_IT + 1):
        As, Bs = macro_jacs(cx, nom, M)
        bp = None
        while bp is None:
            bp = backward_pass(cx, nom, As, Bs, mu)
            if bp is None:
                mu *= MU_UP
                if mu > MU_MAX:
                    stop = "mu_max(backward)"
                    break
        if bp is None:
            break
        ks, Ks, dV1, dV2 = bp
        accepted = False
        for alpha in ALPHAS:
            cand = forward_pass(cx, z0, nom, ks, Ks, alpha, M)
            if cand is None or not np.isfinite(cand["cost"]):
                continue
            if cand["cost"] < nom["cost"] - 1e-12:
                exp = -(alpha * dV1 + alpha * alpha * dV2)
                rel = (nom["cost"] - cand["cost"]) / max(abs(nom["cost"]), 1e-9)
                nom2 = rollout(cx, z0, cand["U"], M, store=True)  # 저장 포함 재롤 (동일 궤적)
                if nom2 is None:
                    continue
                nom = nom2
                accepted = True
                n_acc += 1
                mu = max(mu / MU_DN, MU_MIN)
                curve.append(nom["cost"])
                if it % 5 == 0 or it <= 3:
                    log(f"  [{tag}] it {it:3d} cost={nom['cost']:+.5f} "
                        f"proxy={apex_proxy(nom['X'][-1]):.4f}m alpha={alpha:.3g} "
                        f"mu={mu:.2g} exp={exp:.2e} [{time.time() - t0:.0f}s]")
                if rel < TOL_REL:
                    small += 1
                    if small >= 3:
                        stop = "tol"

                else:
                    small = 0
                break
        if not accepted:
            n_rej += 1
            mu *= MU_UP
            curve.append(nom["cost"])
            if mu > MU_MAX:
                stop = "mu_max(linesearch)"
                break
        if stop == "tol":
            break
        if time.time() - t0 > BUDGET_S:
            stop = "budget"
            break
    wall = time.time() - t0
    log(f"  [{tag}] done: it={len(curve) - 1} acc={n_acc} rej={n_rej} "
        f"cost={nom['cost']:+.5f} proxy={apex_proxy(nom['X'][-1]):.4f}m "
        f"stop={stop} [{wall:.0f}s]")
    return dict(U=nom["U"], cost=float(nom["cost"]),
                proxy=float(apex_proxy(nom["X"][-1])), curve=[float(c) for c in curve],
                iters=len(curve) - 1, n_acc=n_acc, n_rej=n_rej, stop=stop,
                wall_s=float(wall), mu_final=float(mu))


# ══════════════════ 골든 ══════════════════
def golden_afull(cx, tw, d):
    """G1: 0602 A-mode trial을 내 스텝 래퍼(ctrl/qfrc 적용+mj_step)로 재생 vs
    정본 a_full23_log — 전 키 최대차 (비트 0 기대). 커맨드 산출식은 a_full23 문자 미러."""
    P = cx["P"]; mj = cx["mj"]; S = P.J._P["S"]
    model = cx["model"]; law = tw["law"]; spr = tw["spr"]; kr = tw["kr"]
    t = d["t"]; law_a = law[0]
    hl = RU.hl_vec(d["traw2"], d["dq2"], spr)
    ks_, kref, _ = RU.spr_resolve(model, spr)
    sv = RU.supp_vec(d["traw2"], d["dq2"], law)
    if kr:
        sv = sv + RU.rise_term(d["dq2"], kr, law[2])
    sv1_0 = 0.0
    a1v = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
    sv1 = RU.hip_supp_vec(d["traw1"], d["dq1"], d["traw2"], d["dq2"])
    a1v = a1v + sv1
    sv1_0 = float(sv1[0])
    t1 = np.interp(t - P.SD, t, a1v)
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
    supp0 = float(sv[0])
    q1_0 = float(d["q1"][0]); q2_0 = float(d["q2"][0])
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    Lg = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "bz"]}
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
            v1c = -md.qvel[1]; v2c = -md.qvel[2]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
            extra = supp0
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            extra = 0.0
            if tc > t[-1]:
                s1 = s2 = 0.0
                extra = law_a
        e1 = sv1_0 if tc < 0 else (RU.HIP["a1"] if tc > t[-1] else 0.0)
        # ── 내 스텝 래퍼의 적용부 (ctrl·qfrc 세팅 + mj_step — substep과 동일 지점) ──
        md.ctrl[:] = [-(s1 + e1), -(s2 + extra)]
        tql = 0.0
        if tc < 0:
            h = float(hl[0])
        elif tc > t[-1]:
            h = 0.0
        else:
            h = float(np.interp(tc, t, hl))
        tql += ks_ * (kref - float(md.qpos[cx["iq_k"]])) * h
        md.qfrc_applied[cx["dof_knee"]] = tql
        mj.mj_step(model, md)
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["bz"][k] = md.qpos[0]
    ref_log = RU.a_full23_log(model, False, 0.030, d, law, 0.0, 0.0, c_cvt=0.0,
                              spr=spr, k_rise=kr)
    return max(float(np.abs(Lg[k] - ref_log[k]).max())
               for k in ("q1", "q2", "dq1", "dq2", "bz"))


def golden_ol(cx, tw, st, U, M):
    """G2: 내 ZOH 매크로 롤아웃 vs TW.rollout_ol(밀집 그리드) — 비트 일치."""
    N = U.shape[0]
    dt = cx["dt"]
    n_dense = N * M + 1
    tg = np.arange(n_dense) * dt
    idx = np.minimum(np.arange(n_dense) // M, N - 1)
    r1 = U[idx, 0]; r2 = U[idx, 1]
    Lo = TW.rollout_ol(tw, tg, r1, r2, st, t_end=T_HOR, record=True)
    # 내 롤아웃 (post-step 로그 수집)
    md = cx["md"]
    _reset_md(cx, md, st["qpos"], st["qvel"])
    c1f, c2f = float(st["c1f"]), float(st["c2f"])
    dmax = 0.0
    for j in range(N):
        for i in range(M):
            k = j * M + i
            c1f, c2f, s1, s2, c1, c2 = substep(cx, md, c1f, c2f, U[j, 0], U[j, 1])
            dmax = max(dmax,
                       abs(-md.qpos[1] - np.pi / 2 - Lo["q1"][k]),
                       abs(-md.qpos[2] - Lo["q2"][k]),
                       abs(-md.qvel[2] - Lo["dq2"][k]),
                       abs(md.qpos[0] - Lo["bz"][k]),
                       abs(c1 - Lo["raw1"][k]), abs(c2 - Lo["raw2"][k]))
    return float(dmax)


def golden_jac(cx, nom, M, idxs, log):
    """G3: 체인 야코비안 vs 유효스텝 전체 직접 FD — Frobenius 상대오차."""
    rows = []
    for j in idxs:
        Phi = np.eye(NX); Psi = np.zeros((NX, NU))
        for i in range(M):
            A, B = substep_jac(cx, nom["sub"], j * M + i, nom["U"][j])
            Phi = A @ Phi; Psi = A @ Psi + B
        z = nom["X"][j]
        warm0 = nom["sub"]["warm"][j * M]
        Afd, Bfd = macro_jac_fd(cx, z, nom["U"][j].copy(), M, warm0)
        eA = float(np.linalg.norm(Phi - Afd) / max(np.linalg.norm(Afd), 1e-12))
        eB = float(np.linalg.norm(Psi - Bfd) / max(np.linalg.norm(Bfd), 1e-12))
        rows.append(dict(node=int(j), t=float(j * DT_C), relA=eA, relB=eB))
        log(f"  [G3] node {j:3d} (t={j * DT_C:.3f}s) relA={eA:.2e} relB={eB:.2e}")
    return rows


# ══════════════════ 시드 ══════════════════
def seed_crouch(st, N):
    """(a) crouch-hold: settle 끝 PD 커맨드 상수 유지."""
    u = np.array([np.clip(st["c1f"], -R19.CLIP, R19.CLIP),
                  np.clip(st["c2f"], -R19.CLIP, R19.CLIP)])
    return np.tile(u, (N, 1))


def seed_measured(tw, N):
    """(c) 0602 첫 trial 측정 raw 푸시 (p25_a_cma_ol 시드 규약 — |dq2| 피크 정렬)."""
    d0 = tw["d0"]; t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    ts = tp - T_STANCE * 0.85
    tj = (np.arange(N) + 0.5) * DT_C
    u1 = np.where(tj <= T_STANCE, np.interp(ts + np.minimum(tj, T_STANCE), t, d0["traw1"]), 0.0)
    u2 = np.where(tj <= T_STANCE, np.interp(ts + np.minimum(tj, T_STANCE), t, d0["traw2"]), 0.0)
    return np.clip(np.column_stack([u1, u2]), -R19.CLIP, R19.CLIP)


def seed_warm(N):
    """(b) Phase A 형제 npz (p25_a_*.npz) 전부에서 raw 궤적 리샘플 → [(U, 이름)] (없으면 [])."""
    out = []
    for p in sorted(HERE.glob("p25_a_*.npz")):
        try:
            z = np.load(p)
            if not all(k in z for k in ("t", "raw1", "raw2")):
                continue
            t = z["t"]; m = t >= 0
            tj = (np.arange(N) + 0.5) * DT_C
            u1 = np.interp(tj, t[m], z["raw1"][m])
            u2 = np.interp(tj, t[m], z["raw2"][m])
            out.append((np.clip(np.column_stack([u1, u2]), -R19.CLIP, R19.CLIP), p.name))
        except Exception:
            continue
    return out


# ══════════════════ 산출물 ══════════════════
def record_final(cx, tw, st, U, M, t_end=T_HOR):
    """최종 U를 정본 배선(TW.rollout_ol 밀집 그리드)으로 기록 롤아웃 → Lg (grf 포함)."""
    N = U.shape[0]
    dt = cx["dt"]
    n_dense = int(round(t_end / dt)) + 1
    tg = np.arange(n_dense) * dt
    idx = np.minimum(np.arange(n_dense) // M, N - 1)
    r1 = U[idx, 0]; r2 = U[idx, 1]
    return TW.rollout_ol(tw, tg, r1, r2, st, t_end=t_end, record=True)


def cost_curve_png(runs, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for r in runs:
        it = np.arange(len(r["curve"]))
        ax[0].plot(it, r["curve"], label=f"{r['tag']} (h={r['h_plan']:.3f}m)")
        ax[1].plot(it, -np.asarray(r["curve"]), label=r["tag"])
    ax[0].set_xlabel("iteration"); ax[0].set_ylabel("cost")
    ax[0].set_title("iLQR 비용 수렴 (box-DDP on 트윈 원본)")
    ax[0].legend(); ax[0].grid(alpha=0.3)
    ax[1].set_xlabel("iteration"); ax[1].set_ylabel("-cost ≈ apex 프록시 [m]")
    ax[1].set_title("apex 프록시 상승")
    ax[1].legend(); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ══════════════════ main ══════════════════
def main(smoke=False):
    safe.utf8_console()
    t00 = time.time()
    log = lambda s: print(s, flush=True)
    log("=== p25_a4_ilqr — iLQR(box-DDP) on 트윈 원본 (mjd_transitionFD) ===")
    tw = TW.twin()
    cx = ctx_of(tw)
    M = int(round(DT_C / cx["dt"]))
    N = int(round(T_HOR / DT_C))
    assert abs(M * cx["dt"] - DT_C) < 1e-12 and abs(N * DT_C - T_HOR) < 1e-12
    log(f"init [{time.time() - t00:.0f}s] dt={cx['dt']} M={M} N={N} al={cx['al']:.4f} "
        f"CLIP={R19.CLIP}")
    st = TW.settle_state(tw, *tw["q0"])
    z0 = dict(qpos=st["qpos"], qvel=st["qvel"], c1f=st["c1f"], c2f=st["c2f"])
    log(f"settle: q=({-st['qpos'][1] - np.pi / 2:.4f},{-st['qpos'][2]:.4f}) "
        f"c_f=({st['c1f']:.2f},{st['c2f']:.2f}) raw "
        f"{'(주의: |c_f|>CLIP)' if max(abs(st['c1f']), abs(st['c2f'])) > R19.CLIP else ''}")

    # ── 골든 G1: A-mode trial 재생 vs a_full23_log ──
    d0 = tw["d0"]
    g1 = golden_afull(cx, tw, d0)
    log(f"[G1] 스텝래퍼 A-mode 재생 vs a_full23_log maxdiff = {g1:.3e} "
        f"({tw['seed_trial'][0]}/{tw['seed_trial'][1]})")
    ok1 = g1 < 1e-12
    # ── 골든 G2: ZOH 매크로 롤아웃 vs rollout_ol ──
    U_m = seed_measured(tw, N)
    g2 = golden_ol(cx, tw, st, U_m, M)
    log(f"[G2] 내 ZOH 롤아웃 vs rollout_ol(밀집) maxdiff = {g2:.3e}")
    ok2 = g2 < 1e-12
    if not (ok1 and ok2):
        log("!! 골든 실패 — 배선 불일치, 최적화 진입 중단")
        safe.atomic_json_write(HERE / "p25_a4_results.json", dict(
            gen=time.strftime("%Y-%m-%d %H:%M"), status="GOLDEN_FAIL",
            g1=g1, g2=g2))
        return 1
    # ── 골든 G3: 야코비안 체인 vs 전체 FD ──
    nom_m = rollout(cx, z0, U_m, M, store=True)
    idxs = [0, 20, 40, 55, 60, 70, 90, 110] if not smoke else [0, 55]
    g3 = golden_jac(cx, nom_m, M, idxs, log)
    worstA = max(r["relA"] for r in g3); worstB = max(r["relB"] for r in g3)
    log(f"[G3] worst relA={worstA:.2e} relB={worstB:.2e} (임계 1e-3)")
    # eps 민감도 (1 노드)
    j = idxs[len(idxs) // 2]
    sens = []
    for eps in (1e-5, 1e-6, 1e-7):
        global EPS_FD
        keep = EPS_FD; EPS_FD = eps
        Phi = np.eye(NX); Psi = np.zeros((NX, NU))
        for i in range(M):
            A, B = substep_jac(cx, nom_m["sub"], j * M + i, nom_m["U"][j])
            Phi = A @ Phi; Psi = A @ Psi + B
        EPS_FD = keep
        sens.append(dict(eps=eps, nA=float(np.linalg.norm(Phi)),
                         nB=float(np.linalg.norm(Psi))))
    log("[G3] eps 민감도 " + "  ".join(f"eps={s['eps']:.0e}:|A|={s['nA']:.4f}" for s in sens))

    # ── 시드 3종 ──
    runs = []
    seeds = [("crouch", seed_crouch(st, N))]
    wms = seed_warm(N)
    for U_w, name in (wms if not smoke else wms[:1]):
        seeds.append((f"warm({name})", U_w))
    if not wms:
        seeds.append(("measured", U_m))
        log("warm npz (p25_a_*.npz) 없음 — measured 시드 대체")
    global MAX_IT, BUDGET_S
    if smoke:
        MAX_IT = 3; BUDGET_S = 300.0

    best = None
    for tag, U0 in seeds:
        r0 = rollout(cx, z0, U0, M, store=False)
        log(f"[{tag}] seed cost={r0['cost'] if r0 else float('nan'):+.5f} "
            f"proxy={apex_proxy(r0['X'][-1]) if r0 else float('nan'):.4f}m")
        res = ilqr(cx, z0, U0, M, tag, log)
        Lg = record_final(cx, tw, st, res["U"], M)
        res["tag"] = tag
        res["h_plan"] = TW.apex_of(Lg) if Lg is not None else float("nan")
        res["stats"] = TW.stats_of(tw, Lg, t_push=T_HOR) if Lg is not None else {}
        res["horizon"] = T_HOR
        log(f"[{tag}] h_plan(실현 apex)={res['h_plan']:.4f}m vs proxy={res['proxy']:.4f}m")
        runs.append(res)
        if best is None or res["h_plan"] > best["h_plan"]:
            best = res

    # ── stance-only 변형 (0.35 s horizon — 이지 이후 미분 회피) ──
    if not smoke:
        N2 = int(round(T_STANCE / DT_C))
        U0s = best["U"][:N2].copy()
        res = ilqr(cx, z0, U0s, M, "stance0.35", log)
        if res is not None:
            # 기록: 0.35 이후 raw=0으로 0.6까지 (CMA OL의 T_PUSH 규약과 동일)
            Ufull = np.zeros((N, NU)); Ufull[:N2] = res["U"]
            Lg = record_final(cx, tw, st, Ufull, M)
            res["tag"] = "stance0.35"
            res["h_plan"] = TW.apex_of(Lg) if Lg is not None else float("nan")
            res["stats"] = TW.stats_of(tw, Lg, t_push=T_STANCE) if Lg is not None else {}
            res["horizon"] = T_STANCE
            res["U"] = Ufull
            log(f"[stance0.35] h_plan={res['h_plan']:.4f}m vs proxy(0.35)={res['proxy']:.4f}m")
            runs.append(res)
            if res["h_plan"] > best["h_plan"]:
                best = res

    # ── 최종 산출물 (최고 h_plan 런) ──
    Lg = record_final(cx, tw, st, best["U"], M)
    extra = dict(qd1=Lg["q1"], qd2=Lg["q2"], dqd1=Lg["dq1"], dqd2=Lg["dq2"],
                 u_nodes=best["U"], t_nodes=np.arange(best["U"].shape[0]) * DT_C,
                 dt_ctrl=np.array(DT_C), horizon=np.array(best["horizon"]))
    TW.save_npz(HERE / "p25_a4_ilqr.npz", Lg, extra=extra)
    cost_curve_png(runs, HERE / "p25_a4_cost_curve.png")
    out = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="ilqr_boxddp_mjd_transitionFD",
        note=("iLQR(box-DDP) on 정확한 MuJoCo 트윈 — mjd_transitionFD + 층 체인룰 "
              "(필터 상태 2축 증강, qfrc 스프링 채널 수동 FD). 골든 G1/G2 비트, G3 체인 검증."),
        status="OK",
        config=dict(dt_ctrl=DT_C, horizon=T_HOR, n_nodes=N, substeps=M,
                    clip=float(R19.CLIP), r_u=R_U, w_env=W_ENV, w_h=W_H,
                    eps_fd=1e-6, eps_qfrc=EPS_Q, eps_layer=EPS_L, eps_sp=EPS_SP,
                    mu0=MU0, alphas=ALPHAS, max_it=MAX_IT, budget_s=BUDGET_S),
        golden=dict(g1_afull_maxdiff=g1, g2_ol_maxdiff=g2,
                    g3=g3, g3_worstA=worstA, g3_worstB=worstB, g3_eps_sens=sens),
        runs=[{k: v for k, v in r.items() if k != "U"} for r in runs],
        best=dict(tag=best["tag"], h_plan=best["h_plan"], proxy=best["proxy"],
                  cost=best["cost"], iters=best["iters"], wall_s=best["wall_s"],
                  horizon=best["horizon"], stats=best["stats"]),
        h_plan=best["h_plan"],
        seed_trial=list(tw["seed_trial"]), npz="p25_a4_ilqr.npz",
        wall_total_s=float(time.time() - t00))
    safe.atomic_json_write(HERE / "p25_a4_results.json", out)
    log(f"saved p25_a4_ilqr.npz + p25_a4_results.json + p25_a4_cost_curve.png "
        f"[{(time.time() - t00) / 60:.1f}m]  BEST={best['tag']} h_plan={best['h_plan']:.4f}m")
    return 0


if __name__ == "__main__":
    sys.exit(main(smoke="--smoke" in sys.argv))
