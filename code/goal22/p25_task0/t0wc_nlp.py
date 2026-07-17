# -*- coding: utf-8 -*-
"""t0wc_nlp — P25-task0 확장 (사용자 지시 07-18): with_cvt NLP, l_i(상수) 결정변수 포함.

t0nc_nlp(무변속 NLP)의 CVT 확장판. 플랜트 = p24a CVT 트윈(build_cvt23)의 등가 3-DOF EoM
(상태 z, q1, qm — qm = 크랭크/모터각 측정 규약), l_i는 스칼라 결정변수 [10, 30] mm.

═══ 설계 (문서화 의무) ═══
1) 등가 EoM: (bz, j1, j2=−qm 모델 프레임)에서 **l_i 파라미터 수치 적합**.
   CVT 폐쇄(cvt_core.closure: 4절 crank l_i–coupler 0.25–rocker 0.03, Newton 1e-14)로
   qfull = [bz, j1, j2, qpin(j2;l_i), qk(j2;l_i)] → Jm(j2;l_i) 사상.
   M_red = JmᵀM_full Jm, G_red = Jmᵀqfrc_bias(qvel=0)를 격자 샘플 →
   기저 {1, cos j1, sin j1} ⊗ Chebyshev_deg18(j2) 최소제곱 적합 (구조상 분리가능 — 평면
   체인의 j1 의존은 cos/sin j1 두 항뿐). 코리올리 = 적합 M의 Christoffel (구속 라그랑주
   시스템이라 정확, p25_b와 동일 논거). 1D 함수 qk/qpin'/r=dqk/dqc/φ₂는 Chebyshev deg24.
2) l_i 의존: **신뢰영역 반복** — 중심 l_c에서 5점 (l_c + u·0.75mm, u=−2..2) 적합 →
   Lagrange 4차 보간으로 CasADi 심볼릭 계수 C(l_i) → NLP가 l_i ∈ l_c±1.5mm에서 최적화.
   해가 신뢰영역 경계면 재중심·재적합 (최대 4회). 보간 검증: u=±0.5에서 직접 적합 대비
   상대오차 기록. 공중 개루프 롤아웃 검증(mj_step vs 적합 EoM RK4)은 중심·l_i* 양쪽.
3) CVT 층 (p24a, l_i=25.08 fit — 유효성 규약은 t0wc_liopt와 동일):
   게이트 스프링 ks(kref−qk(j2;l_i))·h(|s2|) 및 C_CVT 손실 −c_cvt|s2|·amp(r)·tanh(vk)를
   knee dof에 인가 → 축소좌표로 r(j2;l_i) 배율 사상. amp = max(1/max(|r|,0.2)−1, 0)
   매끈화 (smooth_max/smooth_pos ε=1e-2). validity: l_i ≥ 25.08 = interpolation
   ([25.08, 30] 양끝 실측 검증), l_i < 25.08 = extrapolation (플래그).
4) 제약 = t0_spec (audit cvt=True): |â| ≤ 15 (+raw 공급 포락선 25.5810), T-N 포락선
   (hip축 + **크랭크측** |dqm|), |dq| ≤ 50 (전 상태), q1 ∈ [−1.2566,−0.2967],
   qm ∈ [−2.95,−0.05], 스탠스 ≤ 0.3 s (감사 → 실패 시 비행 강제 2차해), 시작 자세 자유
   (정지 + 정적 평형). + AVT 브랜치 가드 J = dq2/dqm ≤ −0.05 (task0_with_cvt 이식
   mechanism_fun의 CasADi 재현 — 트윈 폐쇄와 교차검증 후 사용).
5) 목적/전사: p25_b 그대로 (trapezoidal collocation N=121, G20 'Base via CoM v_z').
6) 심판: â 개루프 트윈 재생 (rollout_ahat = t0wc_cma.rollout_ol 본체 문자 미러,
   커맨드 소스만 â 직접 주입 — p25_b.twin_rollout 규약). 골든 2종:
   ① W.golden() (0429 재생 2.6057 + CL 미러 + â(25.5810)=15.00)
   ② 미러 골든: t0wc_cl_li2508 기록 â 재주입 → 기록 궤적 재현 (rollout_ahat 배선 증명).

warm-start: t0wc_cl_li2508 (CMA CL 최적해, h_plan 1.1045), l_i 초기값 25.08 mm.
산출: t0wc_nlp.npz / t0wc_nlp_audit.json / t0wc_nlp_summary.png. 커밋 금지.
실행: PYTHONIOENCODING=utf-8 python t0wc_nlp.py
"""
import os

os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"
os.environ["P24_REFIT"] = "1"
os.environ["P25_CLIP_RAW"] = "25.5810"   # |â_motoring| = 15.00 Nm (t0_spec.RAW15)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
G22 = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(G22 / "p25_deploy"))

import t0wc_cma as W          # env 플래그 4종 + RAW15 클립 + CVT 롤아웃 배선(골든 증명)
import t0_spec as T0
import p25_b_nlp as B         # NLP 공용 (smooth_*, ahat_env, raw_of, 상수, build_layers)
import safe
import p19_run as R19
import p23_v6_runners as RU
import p21_cma as C
from cvt_core import closure, qpos_from_crank, L1 as CVT_L1, LO as CVT_LO

import casadi as ca
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ══════════ 상수 ══════════
TAU_LIM = 15.0
J1_LB, J1_UB = -T0.Q1_UB - np.pi / 2, -T0.Q1_LB - np.pi / 2   # 모델 j1
J2_LB, J2_UB = -T0.QM_UB, -T0.QM_LB                            # 모델 크랭크 = -qm
EPS_TN = 0.05                # [rad/s] T-N 좌변 매끈화 (보수측)
TN_ACT_TOL = 0.5
LI_LB, LI_UB = 0.010, 0.030  # [m] AVT task0 바운드
LI0 = 0.02508                # warm-start = CVT 층 fit 지점 (0429 실측)
LI_FIT_MM = 25.08
AVT_OPT_MM = 25.161          # AVT 해석모델 최적 (참조)
DLI = 0.00075                # [m] 신뢰영역 노드 간격 (5점 = ±1.5 mm)
US = (-2.0, -1.0, 0.0, 1.0, 2.0)
MAX_ROUNDS = 4
R_GUARD = -0.05              # AVT J_branch_ub
DEG2, N_J1, N_J2 = 24, 7, 121    # 2D 기저/격자
DEG1, N_J2F = 30, 241            # 1D (j2 전용) 기저/격자
# ★ EoM 적합 유효 상한: l_i ∈ (29.6, 30.0)mm 협대역은 폐쇄 in/anti 브랜치 근접 첨점
#   (qc→0.05)으로 Cheb 적합 실패 (29.58 OK 2.9e-5 / 29.90 FAIL 2.1e-4 / 30.00 정확 8e-11)
#   → 신뢰영역 중심 상한 28.08mm (최대 노드 29.58). l_i=30 무변속판은 t0nc가 커버.
LI_C_MAX = 0.02808
AVT_L, AVT_LO = 0.25, 0.03       # AVT mechanism 링크 (트윈 cvt_core와 동일값)
WARM_NPZ = HERE / "t0wc_cl_li2508.npz"
WARM_AUD = HERE / "t0wc_cl_li2508_audit.json"
OUT_NPZ = HERE / "t0wc_nlp.npz"
OUT_JSON = HERE / "t0wc_nlp_audit.json"
OUT_PNG = HERE / "t0wc_nlp_summary.png"
OUT_SWEEP = HERE / "t0wc_nlp_sweep.json"
OUT_SWEEP_PNG = HERE / "t0wc_nlp_sweep.png"
NB2 = 3 * (DEG2 + 1)
# 고정-l_i NLP 스윕 (사용자 지시 07-18: joint가 취약하면 스윕 전환 / 둘 다 되면 교차확인)
SWEEP_LIS_MM = [20.0, 22.0, 23.0, 24.0, 25.08, 26.0, 27.0, 28.0, 30.0]
SWEEP_REFINE_MM = 0.5        # 피크 주변 세분 간격


# ══════════ Chebyshev 기저 (np + ca 동형) ══════════
def cheb_vander_np(x, deg, lo, hi):
    u = (2.0 * np.asarray(x, float) - (lo + hi)) / (hi - lo)
    return np.polynomial.chebyshev.chebvander(u, deg)


def cheb_vec_ca(x, deg, lo, hi):
    u = (2.0 * x - (lo + hi)) / (hi - lo)
    ts = [u * 0 + 1.0, u]
    for _ in range(2, deg + 1):
        ts.append(2.0 * u * ts[-1] - ts[-2])
    return ca.vertcat(*ts[:deg + 1])


def basis2d_np(j1, j2):
    V = cheb_vander_np(j2, DEG2, J2_LB, J2_UB)
    c = np.cos(np.asarray(j1, float))[:, None]
    s = np.sin(np.asarray(j1, float))[:, None]
    return np.hstack([V, c * V, s * V])


def basis2d_ca(j1, j2):
    cv = cheb_vec_ca(j2, DEG2, J2_LB, J2_UB)
    return ca.vertcat(cv, ca.cos(j1) * cv, ca.sin(j1) * cv)


def lag_w(u):
    """5점 Lagrange 가중 (u = (l_i − l_c)/DLI)."""
    ws = []
    for i, ui in enumerate(US):
        w = 1.0
        for j, uj in enumerate(US):
            if j != i:
                w = w * (u - uj) / (ui - uj)
        ws.append(w)
    return ws


# ══════════ AVT mechanism_fun 이식 (task0_vertjump_with_cvt.py 170~183행 동형) ══════════
def make_avt_funs():
    qmS = ca.SX.sym("qm")
    liS = ca.SX.sym("l_i")
    eps = 1e-8

    def sacos(x):
        return ca.acos(ca.fmax(-1 + eps, ca.fmin(1 - eps, x)))

    l, l_o = AVT_L, AVT_LO
    ld = ca.sqrt(ca.fmax(1e-10, liS ** 2 + l ** 2 - 2 * liS * l * ca.cos(-qmS)))
    alpha = sacos((liS ** 2 + ld ** 2 - l ** 2) / (2 * liS * ld))
    beta = sacos((l ** 2 + ld ** 2 - l_o ** 2) / (2 * l * ld))
    gamma = sacos((l_o ** 2 + ld ** 2 - l ** 2) / (2 * l_o * ld))
    delta = sacos((l ** 2 + ld ** 2 - liS ** 2) / (2 * l * ld))
    q2 = -(gamma + delta)
    theta1 = alpha + beta
    theta2 = beta + gamma
    J = ca.jacobian(q2, qmS)
    q2_of = ca.Function("avt_q2", [qmS, liS], [q2])
    J_of = ca.Function("avt_J", [qmS, liS], [J])
    th_of = ca.Function("avt_th", [qmS, liS], [theta1, theta2])
    return q2_of, J_of, th_of


AVT_Q2, AVT_J, AVT_TH = make_avt_funs()


def avt_crosscheck(lis):
    """AVT mechanism vs 트윈 폐쇄(cvt_core.closure, 물리 in-phase 브랜치) 교차검증.
    ★ 좌표 대응 (수치 발굴): AVT 크랭크 기준방향이 트윈과 π 반전 —
      qm_avt = −π + qc_twin  (qc_twin = 모델 크랭크각 = −qm_twin)
      → q2_avt(qm_avt) = −qk_in(qc_twin),  J_avt(qm_avt) = −r_in(qc_twin).
    (직접 대입 qm_avt=qm_twin은 1.97 rad 편차 — 대응 없이는 사용 불가.)"""
    out = {}
    for li in lis:
        qcs = np.linspace(J2_LB + 0.02, J2_UB - 0.02, 120)
        dq2, dJ = 0.0, 0.0
        qk_prev = None
        for qc in qcs:
            qk, _, r = closure(float(qc), float(li), qk_prev)
            qk_prev = qk
            qma = -np.pi + qc
            q2a = float(AVT_Q2(qma, li))
            Ja = float(AVT_J(qma, li))
            dq2 = max(dq2, abs(q2a - (-qk)))
            dJ = max(dJ, abs(Ja - (-r)))
        out[f"{li * 1000:.2f}mm"] = dict(max_dq2_rad=dq2, max_dJ=dJ)
    return out


# ══════════ 등가 EoM 적합 (l_i 1점) ══════════
_FITS = {}


def fit_li(l_i):
    key = round(float(l_i), 7)
    if key in _FITS:
        return _FITS[key]
    t0 = time.time()
    model, sprm, (qg, rg) = W.model_cvt(round(float(l_i), 6))
    mj = C._W["mj"]
    S = C._W["P"].J._P["S"]
    data = mj.MjData(model)
    iq = {n: safe.qadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    idof = {n: safe.dofadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    nv = model.nv
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    cb = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "calf")
    BZ = 2.0
    hh = 1e-5

    def clo_chain(qc, qk_prev):
        qk, qp, r = closure(float(qc), float(l_i), qk_prev)
        qkp, qpp, _ = closure(float(qc) + hh, float(l_i), qk)
        qkm, qpm, _ = closure(float(qc) - hh, float(l_i), qk)
        cp = (((qpp - qpm + np.pi) % (2 * np.pi)) - np.pi) / (2 * hh)
        r_fd = (qkp - qkm) / (2 * hh)
        # 폐쇄 잔차 + 해석 r vs FD 정합
        Cv = l_i * np.array([np.sin(qc), np.cos(qc)])
        Rv = np.array([0.0, -CVT_L1]) + CVT_LO * np.array([np.sin(qk), np.cos(qk)])
        assert abs(float(np.hypot(*(Cv - Rv))) - CVT_L1) < 1e-8, (l_i, qc)
        assert abs(r - r_fd) < 5e-4, (l_i, qc, r, r_fd)
        return qk, qp, r, cp

    # ── 1D (j2 전용): qk, qpin' (cp), r ──
    j2f = np.linspace(J2_LB, J2_UB, N_J2F)
    qkf = np.zeros(N_J2F); cpf = np.zeros(N_J2F); rf = np.zeros(N_J2F)
    qk_prev = None
    for i, qc in enumerate(j2f):
        qk, _, r, cp = clo_chain(qc, qk_prev)
        qkf[i], rf[i], cpf[i] = qk, r, cp
        qk_prev = qk
    V1 = cheb_vander_np(j2f, DEG1, J2_LB, J2_UB)
    c_qk, *_ = np.linalg.lstsq(V1, qkf, rcond=None)
    c_cp, *_ = np.linalg.lstsq(V1, cpf, rcond=None)
    c_r, *_ = np.linalg.lstsq(V1, rf, rcond=None)
    r1d = {n: float(np.abs(V1 @ c - t).max() / (np.abs(t).max() + 1e-12))
           for n, c, t in (("qk", c_qk, qkf), ("cp", c_cp, cpf), ("r", c_r, rf))}
    # ── rtab(반위상 브랜치) 미러 적합 — C_CVT amp 룩업의 플랜트 정의 그대로 ──
    # ★ 러너(cl_run23/a_full23/W 롤아웃)의 rr = interp(qpos[2], rtab)은 qc>0에서
    #   반위상 브랜치 (r<0, 체인 스윕 -3→3의 branch 유지) — 물리 in-phase r(>0)과 다른
    #   곡선. p24a c_cvt는 이 테이블로 fit → NLP도 rtab 값을 그대로 적합해 미러.
    assert qg is not None, "C_CVT rtab 부재 (c_cvt>0인데 테이블 없음)"
    rtb = np.interp(j2f, qg, rg)
    c_rt, *_ = np.linalg.lstsq(V1, rtb, rcond=None)
    r1d["rtab"] = float(np.abs(V1 @ c_rt - rtb).max() / (np.abs(rtb).max() + 1e-12))

    # ── 2D 격자: M(6)/G(3)/F(3)/φ ──
    j2s = np.linspace(J2_LB, J2_UB, N_J2)
    j1s = np.linspace(J1_LB, J1_UB, N_J1)
    rows, tM, tG, tF = [], [], [], []
    tPhi = np.zeros((N_J1, N_J2))
    Mfull = np.zeros((nv, nv))
    qk_prev = None
    for jj2, qc in enumerate(j2s):
        qk, qp, r, cp = clo_chain(qc, qk_prev)
        qk_prev = qk
        Jm = np.zeros((nv, 3))
        Jm[0, 0] = 1.0
        Jm[idof["hip"], 1] = 1.0
        Jm[idof["knee_motor"], 2] = 1.0
        Jm[idof["cpin"], 2] = cp
        Jm[idof["knee"], 2] = r
        for jj1, j1 in enumerate(j1s):
            data.qpos[:] = 0
            data.qpos[0] = BZ
            data.qpos[iq["hip"]] = j1
            data.qpos[iq["knee_motor"]] = qc
            data.qpos[iq["cpin"]] = qp
            data.qpos[iq["knee"]] = qk
            data.qvel[:] = 0
            mj.mj_forward(model, data)
            mj.mj_fullM(model, Mfull, data.qM)
            Mr = Jm.T @ Mfull @ Jm
            Gr = Jm.T @ data.qfrc_bias
            xm = data.xmat[cb].reshape(3, 3)
            tPhi[jj1, jj2] = float(np.arctan2(xm[0, 2], xm[2, 2]))
            rows.append(basis2d_np(np.array([j1]), np.array([qc]))[0])
            tM.append([Mr[0, 0], Mr[0, 1], Mr[0, 2], Mr[1, 1], Mr[1, 2], Mr[2, 2]])
            tG.append(list(Gr))
            tF.append([data.geom_xpos[fg][0], data.geom_xpos[fg][2] - BZ,
                       data.subtree_com[0][2] - BZ])
    rows = np.array(rows)
    fits, resids = {}, dict(r1d)
    for name, T in (("M", np.array(tM)), ("G", np.array(tG)), ("F", np.array(tF))):
        coef, *_ = np.linalg.lstsq(rows, T, rcond=None)
        rel = np.abs(rows @ coef - T).max(axis=0) / (np.abs(T).max(axis=0) + 1e-9)
        fits[name] = coef
        resids[name] = float(rel.max())
        assert rel.max() < 1e-4, f"{name} 기저 적합 실패 (l_i={l_i}): rel={rel}"

    # ── φ = p1·j1 + φ₂(j2): p1 FD + 중심행 unwrap 적합 + 전 격자 랩 잔차 ──
    j1c, j2c = float(np.mean(j1s)), float(np.mean(j2s))
    ic = N_J1 // 2

    def phi_at(j1, qc, qp, qk):
        data.qpos[:] = 0
        data.qpos[0] = BZ
        data.qpos[iq["hip"]] = j1
        data.qpos[iq["knee_motor"]] = qc
        data.qpos[iq["cpin"]] = qp
        data.qpos[iq["knee"]] = qk
        data.qvel[:] = 0
        mj.mj_forward(model, data)
        xm = data.xmat[cb].reshape(3, 3)
        return float(np.arctan2(xm[0, 2], xm[2, 2]))

    qkc, qpc, _, _ = clo_chain(j2c, None)
    p1 = (phi_at(j1c + hh, j2c, qpc, qkc) - phi_at(j1c - hh, j2c, qpc, qkc)) / (2 * hh)
    assert abs(abs(p1) - 1.0) < 1e-6, f"φ hip 기울기 비정수: {p1}"
    phi2_t = np.unwrap(tPhi[ic]) - p1 * j1s[ic]
    V1s = cheb_vander_np(j2s, DEG1, J2_LB, J2_UB)
    c_phi, *_ = np.linalg.lstsq(V1s, phi2_t, rcond=None)
    per = 0.0
    for jj1, j1 in enumerate(j1s):
        pred = p1 * j1 + V1s @ c_phi
        e = (tPhi[jj1] - pred + np.pi) % (2 * np.pi) - np.pi
        per = max(per, float(np.abs(e).max()))
    assert per < 1e-6, f"φ 분해 잔차 {per}"
    resids["phi"] = per

    out = dict(l_i=float(l_i), coefM=fits["M"], coefG=fits["G"], coefF=fits["F"],
               c_qk=c_qk, c_cp=c_cp, c_r=c_r, c_rt=c_rt, c_phi=c_phi, p1=float(p1),
               sprm=tuple(float(x) for x in sprm),
               Mtot=float(model.body_mass.sum()), R=float(S.FOOT_RADIUS),
               damp={n: float(model.dof_damping[idof[n]]) for n in idof},
               damp_bz=float(model.dof_damping[0]),
               fl={n: float(model.dof_frictionloss[idof[n]]) for n in idof},
               fl_bz=float(model.dof_frictionloss[0]),
               resids=resids, wall_s=float(time.time() - t0))
    _FITS[key] = out
    return out


# ══════════ l_i 보간 평가기 (np) + 검증 ══════════
class NpF:
    def __init__(self, F5, l_c):
        self.F5, self.l_c = F5, l_c

    def blend(self, key, li):
        ws = lag_w((li - self.l_c) / DLI)
        return sum(w * self.F5[i][key] for i, w in enumerate(ws))

    def fk(self, j1, j2, li):
        return basis2d_np(np.atleast_1d(j1), np.atleast_1d(j2)) @ self.blend("coefF", li)

    def Mmat(self, y, li):
        m = (basis2d_np([y[1]], [y[2]]) @ self.blend("coefM", li))[0]
        return np.array([[m[0], m[1], m[2]], [m[1], m[3], m[4]], [m[2], m[4], m[5]]])

    def Gvec(self, y, li):
        return (basis2d_np([y[1]], [y[2]]) @ self.blend("coefG", li))[0]

    def f1d(self, key, j2, li):
        return cheb_vander_np(np.atleast_1d(j2), DEG1, J2_LB, J2_UB) @ self.blend(key, li)


def validate_interp(F5, l_c, n_pose=30, seed=3):
    """u=±0.5 (적합 노드 사이)에서 직접 계산 vs Lagrange 보간 상대오차."""
    npf = NpF(F5, l_c)
    mj = C._W["mj"]
    rng = np.random.default_rng(seed)
    out = {}
    for u in (-0.5, 0.5):
        li = l_c + u * DLI
        model, _, _ = W.model_cvt(round(li, 6))
        data = mj.MjData(model)
        iq = {n: safe.qadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
        idof = {n: safe.dofadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
        Mfull = np.zeros((model.nv, model.nv))
        eM = eG = eR = 0.0
        for _ in range(n_pose):
            j1 = rng.uniform(J1_LB, J1_UB)
            j2 = rng.uniform(J2_LB + 0.05, J2_UB - 0.05)
            qk, qp, r = closure(float(j2), float(li), None)
            data.qpos[:] = 0
            data.qpos[0] = 2.0
            data.qpos[iq["hip"]] = j1
            data.qpos[iq["knee_motor"]] = j2
            data.qpos[iq["cpin"]] = qp
            data.qpos[iq["knee"]] = qk
            data.qvel[:] = 0
            mj.mj_forward(model, data)
            mj.mj_fullM(model, Mfull, data.qM)
            Jm = np.zeros((model.nv, 3))
            Jm[0, 0] = 1.0
            Jm[idof["hip"], 1] = 1.0
            Jm[idof["knee_motor"], 2] = 1.0
            _, qppp, _ = closure(float(j2) + 1e-5, float(li), qk)
            _, qpmm, _ = closure(float(j2) - 1e-5, float(li), qk)
            cp = (((qppp - qpmm + np.pi) % (2 * np.pi)) - np.pi) / 2e-5
            Jm[idof["cpin"], 2] = cp
            Jm[idof["knee"], 2] = r
            Mr = Jm.T @ Mfull @ Jm
            Gr = Jm.T @ data.qfrc_bias
            y = np.array([2.0, j1, j2])
            eM = max(eM, float(np.abs(npf.Mmat(y, li) - Mr).max() / (np.abs(Mr).max())))
            eG = max(eG, float(np.abs(npf.Gvec(y, li) - Gr).max() / (np.abs(Gr).max() + 1e-9)))
            eR = max(eR, float(abs(npf.f1d("c_r", j2, li)[0] - r)))
        out[f"u={u:+.1f}"] = dict(rel_M=eM, rel_G=eG, abs_r=eR)
    return out


def verify_air(F5, l_c, l_i, n_trial=4, n_step=200, seed=7):
    """공중 개루프 검증: mj_step vs 적합 EoM RK4 (l_i 보간판) — p25_b.verify_reduced 미러."""
    npf = NpF(F5, l_c)
    mj = C._W["mj"]
    model, _, _ = W.model_cvt(round(l_i, 6))
    data = mj.MjData(model)
    dt = model.opt.timestep
    fc = F5[len(F5) // 2]
    d_bz, d_hip = fc["damp_bz"], fc["damp"]["hip"]
    d_cr, d_cp, d_kn = fc["damp"]["knee_motor"], fc["damp"]["cpin"], fc["damp"]["knee"]
    fl_hip, fl_cr = fc["fl"]["hip"], fc["fl"]["knee_motor"]
    fl_cp, fl_kn, fl_bz = fc["fl"]["cpin"], fc["fl"]["knee"], fc["fl_bz"]

    def f_ode(y, dy, u):
        h = 1e-6
        cvec = np.zeros(3)
        dM = []
        for k in (1, 2):
            yp = y.copy(); yp[k] += h
            ym = y.copy(); ym[k] -= h
            dM.append((npf.Mmat(yp, l_i) - npf.Mmat(ym, l_i)) / (2 * h))
        dMd = {1: dM[0], 2: dM[1], 0: np.zeros((3, 3))}
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    cvec[i] += 0.5 * (dMd[k][i, j] + dMd[j][i, k] - dMd[i][j, k]) * dy[j] * dy[k]
        G = npf.Gvec(y, l_i)
        r = float(npf.f1d("c_r", y[2], l_i)[0])
        cp = float(npf.f1d("c_cp", y[2], l_i)[0])
        Q = np.array([0.0, u[0], u[1]])
        d33 = d_cr + d_cp * cp * cp + d_kn * r * r
        Q = Q - np.array([d_bz * dy[0], d_hip * dy[1], d33 * dy[2]])
        ev = 0.005
        Q = Q - np.array([fl_bz * np.tanh(dy[0] / ev),
                          fl_hip * np.tanh(dy[1] / ev),
                          fl_cr * np.tanh(dy[2] / ev)
                          + fl_cp * cp * np.tanh(cp * dy[2] / ev)
                          + fl_kn * r * np.tanh(r * dy[2] / ev)])
        return np.linalg.solve(npf.Mmat(y, l_i), Q - cvec - G)

    rng = np.random.default_rng(seed)
    errs = []
    n_skip = 0
    tries = 0
    while len(errs) < n_trial and tries < n_trial * 6:
        tries += 1
        j1 = rng.uniform(J1_LB + 0.15, J1_UB - 0.15)
        j2 = rng.uniform(J2_LB + 0.3, J2_UB - 0.3)
        u = rng.uniform(-5, 5, 2)
        data.qpos[:] = qpos_from_crank(2.0, j1, j2, l_i)[0]
        data.qvel[:] = 0
        mj.mj_forward(model, data)
        in_dom = True
        for _ in range(n_step):
            data.ctrl[:] = u
            mj.mj_step(model, data)
            if not (J1_LB - 0.02 <= data.qpos[1] <= J1_UB + 0.02
                    and J2_LB - 0.02 <= data.qpos[2] <= J2_UB + 0.02):
                in_dom = False
                break
        if not in_dom:      # 개루프 랜덤 토크가 적합 정의역(스펙 박스) 이탈 — 외삽
            n_skip += 1     # 영역이라 비교 무의미 (NLP는 박스로 상태를 구속)
            continue
        y_mj = np.array([data.qpos[0], data.qpos[1], data.qpos[2]])
        y = np.array([2.0, j1, j2]); dy = np.zeros(3)
        for _ in range(n_step):
            k1 = f_ode(y, dy, u); k1y = dy
            k2 = f_ode(y + 0.5 * dt * k1y, dy + 0.5 * dt * k1, u); k2y = dy + 0.5 * dt * k1
            k3 = f_ode(y + 0.5 * dt * k2y, dy + 0.5 * dt * k2, u); k3y = dy + 0.5 * dt * k2
            k4 = f_ode(y + dt * k3y, dy + dt * k3, u); k4y = dy + dt * k3
            y = y + dt / 6 * (k1y + 2 * k2y + 2 * k3y + k4y)
            dy = dy + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        errs.append(np.abs(y - y_mj))
    errs = np.array(errs) if errs else np.array([[float("nan")] * 3])
    return dict(l_i_mm=float(l_i * 1000), q_err_max=float(errs.max()),
                q_err_mean=float(errs.mean()), horizon_s=n_step * dt,
                n=len(errs), n_skipped_out_of_domain=n_skip)


# ══════════ CasADi 심볼릭 팩토리 ══════════
def make_funcs(F5, l_c):
    fc = F5[len(F5) // 2]
    for f in F5:   # 상수 계열 정합 확인
        assert abs(f["Mtot"] - fc["Mtot"]) / fc["Mtot"] < 5e-3, "Mtot l_i 변동 과대"
        assert all(abs(f["sprm"][i] - fc["sprm"][i]) < 1e-9 for i in range(3)), "sprm 변동"
        assert abs(f["p1"] - fc["p1"]) < 1e-9
    yS = ca.SX.sym("y", 3)
    dyS = ca.SX.sym("dy", 3)
    liS = ca.SX.sym("li")
    ws = lag_w((liS - l_c) / DLI)

    def blend(key):
        out = ws[0] * ca.DM(F5[0][key])
        for i in range(1, 5):
            out = out + ws[i] * ca.DM(F5[i][key])
        return out

    bF = basis2d_ca(yS[1], yS[2])
    mrow = ca.mtimes(bF.T, blend("coefM")).T
    Mexp = ca.vertcat(
        ca.horzcat(mrow[0], mrow[1], mrow[2]),
        ca.horzcat(mrow[1], mrow[3], mrow[4]),
        ca.horzcat(mrow[2], mrow[4], mrow[5]))
    Gexp = ca.mtimes(bF.T, blend("coefG")).T
    fk = ca.mtimes(bF.T, blend("coefF")).T          # [fx, fz_rel, zc_rel]
    cv = cheb_vec_ca(yS[2], DEG1, J2_LB, J2_UB)
    r_e = ca.mtimes(cv.T, blend("c_r"))
    rt_e = ca.mtimes(cv.T, blend("c_rt"))
    cp_e = ca.mtimes(cv.T, blend("c_cp"))
    qk_e = ca.mtimes(cv.T, blend("c_qk"))
    phi_e = fc["p1"] * yS[1] + ca.mtimes(cv.T, blend("c_phi"))
    Mdy = ca.mtimes(Mexp, dyS)
    Cvec = ca.mtimes(ca.jacobian(Mdy, yS), dyS) \
        - 0.5 * ca.jacobian(ca.mtimes(dyS.T, Mdy), yS).T
    return dict(
        M=ca.Function("M_of", [yS, liS], [Mexp]),
        G=ca.Function("G_of", [yS, liS], [Gexp]),
        FK=ca.Function("FK_of", [yS, liS], [fk]),
        JFK=ca.Function("JFK_of", [yS, liS], [ca.jacobian(fk, yS)]),
        C=ca.Function("C_of", [yS, dyS, liS], [Cvec]),
        r=ca.Function("r_of", [yS, liS], [r_e]),
        rt=ca.Function("rt_of", [yS, liS], [rt_e]),
        cp=ca.Function("cp_of", [yS, liS], [cp_e]),
        qk=ca.Function("qk_of", [yS, liS], [qk_e]),
        phi=ca.Function("phi_of", [yS, liS], [phi_e]),
        fc=fc)


# ══════════ NLP (t0nc_nlp.solve_t0 동형 — CVT 층 + l_i 변수) ══════════
def solve_t0wc(fn, warm, li_lo, li_hi, k_c=B.K_C, b_c=B.B_C, t_flight=None,
               obj="full", max_iter=4000):
    fc = fn["fc"]
    ks, kref, tspr = fc["sprm"]
    c_cvt = W.G["C_CVT"]
    d_bz, d_hip = fc["damp_bz"], fc["damp"]["hip"]
    d_cr, d_cp, d_kn = fc["damp"]["knee_motor"], fc["damp"]["cpin"], fc["damp"]["knee"]
    fl_hip, fl_cr = fc["fl"]["hip"], fc["fl"]["knee_motor"]
    fl_cp, fl_kn, fl_bz = fc["fl"]["cpin"], fc["fl"]["knee"], fc["fl_bz"]
    R = fc["R"]
    supp_f, rise_f, hip_f = B.build_layers(dict(law=W.G["LAW"], kr=W.G["KR"]))

    opti = ca.Opti()
    N = B.N_NODE
    dt = B.T_HOR / (N - 1)
    tg = np.arange(N) * dt
    Y = opti.variable(3, N)      # bz, j1, j2(크랭크 모델각 = -qm)
    DY = opti.variable(3, N)
    U = opti.variable(2, N)      # s1, s2 = â (측정 프레임, s2 = 크랭크 모터)
    FX = opti.variable(1, N)
    uLI = opti.variable()        # 무차원 l_i (스케일링) — l_i = l_c + uLI·DLI
    l_c = (li_lo + li_hi) / 2
    LI = l_c + uLI * DLI

    def node_forces(k):
        y = Y[:, k]; dy = DY[:, k]
        v1c = -dy[1]; v2c = -dy[2]
        s1 = U[0, k]; s2 = U[1, k]
        fkv = fn["FK"](y, LI)
        Jf = fn["JFK"](y, LI)
        rr = fn["r"](y, LI)
        cpv = fn["cp"](y, LI)
        qkv = fn["qk"](y, LI)
        foot_z = y[0] + fkv[1]
        dfoot_z = dy[0] + ca.mtimes(Jf[1, 1:3], dy[1:3])
        delta = R - foot_z
        dpos = B.smooth_pos(delta, B.EPS_C)
        fz = k_c * dpos + b_c * (-dfoot_z) * (dpos / (dpos + B.EPS_C))
        sup = supp_f(s2, v2c)
        ris = rise_f(v2c)
        lam1 = hip_f(s1, s2, v1c)
        # ── knee dof 인가 토크 (게이트 스프링 + C_CVT 손실) → 크랭크 좌표 r_in 배율 ──
        # amp = rtab(반위상) 룩업 미러 (러너 정의) / vk·사상 = 물리 in-phase r
        h_l = B.smooth_abs(s2) / (B.smooth_abs(s2) + tspr)
        tql = ks * (kref - qkv) * h_l
        if c_cvt > 0:
            rrt = fn["rt"](y, LI)
            absr = ca.sqrt(rrt * rrt + 1e-8)
            mx = 0.5 * (absr + 0.2 + ca.sqrt((absr - 0.2) ** 2 + 1e-4))   # smooth max(|r|,0.2)
            amp = B.smooth_pos(1.0 / mx - 1.0, 0.01)
            vk = rr * dy[2]
            tql = tql - c_cvt * B.smooth_abs(s2) * amp * ca.tanh(vk / 1.0)
        Q = ca.vertcat(0, -(s1 + lam1), -(s2 + sup + ris) + rr * tql)
        d33 = d_cr + d_cp * cpv ** 2 + d_kn * rr ** 2
        Q = Q - ca.vertcat(d_bz * dy[0], d_hip * dy[1], d33 * dy[2])
        Q = Q - ca.vertcat(
            fl_bz * ca.tanh(dy[0] / B.EPS_V),
            fl_hip * ca.tanh(dy[1] / B.EPS_V),
            fl_cr * ca.tanh(dy[2] / B.EPS_V)
            + fl_cp * cpv * ca.tanh(cpv * dy[2] / B.EPS_V)
            + fl_kn * rr * ca.tanh(rr * dy[2] / B.EPS_V))
        Jc = ca.vertcat(ca.horzcat(0, Jf[0, 1], Jf[0, 2]),
                        ca.horzcat(1, Jf[1, 1], Jf[1, 2]))
        Q = Q + ca.mtimes(Jc.T, ca.vertcat(FX[0, k], fz))
        return Q, fz, fkv

    acc, fzs, fkvs = [], [], []
    for k in range(N):
        Qk, fz, fkv = node_forces(k)
        y = Y[:, k]; dy = DY[:, k]
        ddy = ca.solve(fn["M"](y, LI), Qk - fn["C"](y, dy, LI) - fn["G"](y, LI).reshape((3, 1)))
        acc.append(ddy)
        fzs.append(fz)
        fkvs.append(fkv)

    for k in range(N - 1):
        opti.subject_to(Y[:, k + 1] == Y[:, k] + 0.5 * dt * (DY[:, k] + DY[:, k + 1]))
        opti.subject_to(DY[:, k + 1] == DY[:, k] + 0.5 * dt * (acc[k] + acc[k + 1]))

    # ── task0 제약 블록 (t0nc 동형 + qm 박스 + l_i + 브랜치 가드) ──
    dst = fc["Mtot"] * B.GG / k_c
    opti.subject_to(DY[:, 0] == 0)
    opti.subject_to(Y[0, 0] + fkvs[0][1] == R - dst)             # Fz(0)=M·g
    opti.subject_to(opti.bounded(J1_LB, Y[1, :], J1_UB))          # q1 박스
    opti.subject_to(opti.bounded(J2_LB, Y[2, :], J2_UB))          # qm(크랭크) 박스
    opti.subject_to(opti.bounded(-0.05, Y[0, :], 1.5))
    opti.subject_to(opti.bounded(-T0.DQ_LIM, DY, T0.DQ_LIM))      # |dq| ≤ 50 (dz 포함)
    opti.subject_to(opti.bounded(-TAU_LIM, U, TAU_LIM))           # |â| ≤ 15
    opti.subject_to(opti.bounded((li_lo - l_c) / DLI, uLI, (li_hi - l_c) / DLI))
    fx0s = fkvs[0][0]
    phi0s = fn["phi"](Y[:, 0], LI)
    for k in range(N):
        v1c = -DY[1, k]; v2c = -DY[2, k]
        opti.subject_to(U[0, k] <= B.ahat_env(v1c, +1.0))         # raw 공급 박스 25.5810
        opti.subject_to(U[0, k] >= B.ahat_env(v1c, -1.0))
        opti.subject_to(U[1, k] <= B.ahat_env(v2c, +1.0))
        opti.subject_to(U[1, k] >= B.ahat_env(v2c, -1.0))
        for j in (0, 1):                                          # T-N (hip축 + 크랭크측)
            lim = T0.TN_COEF * B.smooth_abs(U[j, k]) + T0.TN_OFF
            opti.subject_to(ca.sqrt(DY[j + 1, k] ** 2 + EPS_TN ** 2) <= lim)
        # 브랜치 가드 J≤−0.05 양판: ① rtab(반위상) — liopt/audit 정본 규약,
        # ② AVT mechanism_fun 이식판 (좌표 대응 qm_avt=−π+qc: J_avt=−r_in)
        opti.subject_to(fn["rt"](Y[:, k], LI) <= R_GUARD)
        opti.subject_to(AVT_J(-np.pi + Y[2, k], LI) <= R_GUARD)
        fz = fzs[k]
        opti.subject_to(fz >= -0.5)
        fzp = B.smooth_pos(fz, 0.5)
        opti.subject_to(FX[0, k] <= B.MU * fzp + 0.05)
        opti.subject_to(FX[0, k] >= -B.MU * fzp - 0.05)
        w = fzp / (fzp + B.FZ_W0)
        slip = fkvs[k][0] - fx0s - R * (fn["phi"](Y[:, k], LI) - phi0s)
        opti.subject_to(opti.bounded(-B.SLIP_BAND, w * slip, B.SLIP_BAND))
        opti.subject_to(R - (Y[0, k] + fkvs[k][1]) <= 0.012)
        if t_flight is not None and tg[k] >= t_flight:
            opti.subject_to(Y[0, k] + fkvs[k][1] >= R)
    opti.subject_to(Y[0, N - 1] + fkvs[N - 1][1] >= R + 0.005)

    # ── 목적 (G20 관례 — p25_b/t0nc 동일) ──
    JfT = fn["JFK"](Y[:, N - 1], LI)
    vz_com = DY[0, N - 1] + ca.mtimes(JfT[2, 1:3], DY[1:3, N - 1])
    h_plan = Y[0, N - 1] + B.smooth_pos(vz_com, 0.01) ** 2 / (2 * B.GG)
    J_du = sum(ca.sumsqr(U[:, k + 1] - U[:, k]) for k in range(N - 1))
    J_jerk = sum(ca.sumsqr(DY[:, k + 1] - 2 * DY[:, k] + DY[:, k - 1])
                 for k in range(1, N - 1))
    if obj == "feas":     # 실행가능화 프리솔브 — 트윈 트레이스 warm은 NLP 플랜트와
        # 동역학 부정합 (접촉/EoM 근사) → 목적 없이 defect 복원만 해 분지 보존
        opti.minimize(1.0 * J_du + 20.0 * J_jerk + ca.sumsqr(FX) * 1e-4)
    else:
        opti.minimize(-2000.0 * h_plan + 1.0 * J_du + 20.0 * J_jerk
                      + ca.sumsqr(FX) * 1e-4)

    opti.set_initial(Y, warm["Y"]); opti.set_initial(DY, warm["DY"])
    opti.set_initial(U, warm["U"]); opti.set_initial(FX, warm["FX"])
    opti.set_initial(uLI, (np.clip(warm["LI"], li_lo, li_hi) - l_c) / DLI)
    opts = {"ipopt.print_level": 3, "ipopt.max_iter": int(max_iter), "ipopt.tol": 1e-4,
            "ipopt.acceptable_tol": 1e-3, "ipopt.mu_strategy": "adaptive",
            "print_time": True}
    if obj == "feas":     # 프리솔브는 짧게 — 정밀 수렴 불필요 (defect 축소가 목적)
        opts.update({"ipopt.max_iter": 800, "ipopt.tol": 1e-3,
                     "ipopt.acceptable_tol": 1e-2, "ipopt.acceptable_iter": 5})
    opti.solver("ipopt", opts)
    t0c = time.time()
    try:
        sol = opti.solve()
        status = "converged"
    except Exception as e:  # noqa: BLE001
        print(f"IPOPT FAIL: {e}")
        sol = opti.debug
        status = "failed(debug values)"
    st = sol.stats() if hasattr(sol, "stats") else opti.stats()
    return dict(Y=np.array(sol.value(Y)), DY=np.array(sol.value(DY)),
                U=np.array(sol.value(U)), FX=np.atleast_2d(np.array(sol.value(FX))),
                LI=float(sol.value(LI)),
                fz=np.array([float(sol.value(f)) for f in fzs]),
                h_plan=float(sol.value(h_plan)), vz_com_T=float(sol.value(vz_com)),
                status=status, iters=int(st.get("iter_count", -1)),
                wall_s=time.time() - t0c, t=tg, dt=dt, k_c=k_c, b_c=b_c,
                t_flight=t_flight, li_bounds=(li_lo, li_hi))


# ══════════ warm-start: CMA CL 해 사영 (+apex 정렬 시프트) ══════════
def warm_from_cma(npf, li0, npz_path):
    """CMA CL 해 → NLP 시드. ★ apex 정렬: G20 목적 h_plan = bz(T)+탄도(vz>0)⁺라
    apex(기록 ~0.53s)가 T=0.6 근방에 오도록 커맨드를 +shift 지연 (ts<0은 기록 settle
    구간 값 = PD 유지 토크). 시프트 없으면 apex 후 하강분이 목적에서 소실 → 나쁜 분지."""
    z = np.load(npz_path)
    t = np.asarray(z["t"], float)
    bz_r = np.asarray(z["bz"], float)
    mwin = t > 0
    t_apex = float(t[mwin][np.argmax(bz_r[mwin])])   # 전체 로그 apex (기록 ~0.65s > T!)
    # 전진(advance) 금지 — 스탠스가 t<0으로 압축되면 시작 정지/정적 제약과 정면 모순
    # (run3에서 feas 프리솔브 20분+ 교착 확인). 기록 base apex(~0.65s)는 T=0.6 밖이지만
    # bz(0.6)=1.09~1.11이 이미 목적 h_plan(warm)에 담김 — 시프트 불필요, feas가 분지 보존.
    shift = float(np.clip(B.T_HOR - t_apex - 0.02, 0.0, 0.25))
    N = B.N_NODE
    tg = np.linspace(0, B.T_HOR, N)
    ts = tg - shift
    f = lambda k: np.interp(ts, t, np.asarray(z[k], float))  # noqa: E731
    bz, q1, q2 = f("bz"), f("q1"), f("q2")
    Y = np.vstack([bz, -q1 - np.pi / 2, -q2])
    DY = np.vstack([np.gradient(bz, tg), -f("dq1"), -f("dq2")])
    U = np.vstack([f("tau1_nm"), f("tau2_nm")])
    U = np.clip(U, -TAU_LIM, TAU_LIM)
    v1c = -DY[1]; v2c = -DY[2]
    U[0] = np.clip(U[0], B.ahat_env_np(v1c, -1.0), B.ahat_env_np(v1c, +1.0))
    U[1] = np.clip(U[1], B.ahat_env_np(v2c, -1.0), B.ahat_env_np(v2c, +1.0))
    Y[1] = np.clip(Y[1], J1_LB, J1_UB)
    Y[2] = np.clip(Y[2], J2_LB, J2_UB)
    DY = np.clip(DY, -T0.DQ_LIM, T0.DQ_LIM)
    for j in (1, 2):
        lim = T0.TN_COEF * np.abs(U[j - 1]) + T0.TN_OFF
        DY[j] = np.clip(DY[j], -lim, lim)
    DY[:, 0] = 0.0
    fk0 = npf.fk(Y[1, 0], Y[2, 0], li0)[0]
    fc = npf.F5[2]
    Y[0, 0] = (fc["R"] - fc["Mtot"] * B.GG / B.K_C) - fk0[1]
    return dict(Y=Y, DY=DY, U=U, FX=np.zeros((1, N)), LI=float(li0), shift=shift)


# ══════════ 트윈 â 재생 롤아웃 (W.rollout_ol 본체 미러 — 커맨드 소스만 â 주입 ★) ══════════
def rollout_ahat(l_i, t_u, s1_u, s2_u, q0, t_after=None):
    G = W.G
    P = G["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = G["LAW"]
    kr = G["KR"]; c_cvt = G["C_CVT"]; A = G["A"]
    model, sprm, (qg, rg) = W.model_cvt(round(float(l_i), 6))
    if c_cvt <= 0:
        qg = rg = None
    if t_after is None:
        t_after = P.J.T_AFTER
    q1_0, q2_0 = q0
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t_u[-1] + t_after) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz",
                                  "grf", "fx"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc > t_u[-1]:                                        # a_full23 비행 규약
            s1 = s2 = 0.0
            if RU.HIP_LAW:
                md.ctrl[:] = [-(0.0 + RU.HIP["a1"]), -(0.0 + law_a)]
            else:
                md.ctrl[:] = [0.0, -law_a]
            md.qfrc_applied[dof_knee] = 0.0
        else:
            if tc < 0:
                c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
                c2 = S.SETTLE_KP * (q2_0 - (-md.qpos[2])) - S.SETTLE_KD * v2c
                c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP))
                c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
                s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
                s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
            else:
                s1 = float(np.interp(tc, t_u, s1_u))            # ★ â 직접 주입
                s2 = float(np.interp(tc, t_u, s2_u))
            supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
            if kr:
                supp += float(RU.rise_term(v2c, kr, law_v0))
            tql = 0.0
            if qg is not None:
                rr = float(np.interp(md.qpos[2], qg, rg))
                amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
                vk = float(md.qvel[dof_knee])
                tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
            if sprm is not None:
                tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
            if RU.HIP_LAW:
                md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
            else:
                md.ctrl[:] = [-s1, -(s2 + supp)]
            md.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
        L["fx"][k] = float(md.geom_xpos[fg][0])
        L["grf"][k] = RU._grf_z(model, md)
    L["t"] = tl
    return L


def mirror_golden():
    """미러 골든: t0wc_cl_li2508 기록 â를 rollout_ahat으로 재주입 → 기록 궤적 재현.
    settle 목표 = 기록해의 매듭0 (= rollout_cl q_des(0)) → settle 상태 결정론 일치 →
    t ≤ 0.6 구간 비트-수준 재현이 기대값 (â 주입 배선의 정본 증명)."""
    z = np.load(WARM_NPZ)
    aj = safe.read_json(WARM_AUD)
    q0 = (float(aj["params"]["knots_qd1"][0]), float(aj["params"]["knots_qd2"][0]))
    t = np.asarray(z["t"], float)
    m = (t >= -1e-12) & (t <= W.T_END + 1e-12)
    t_u = t[m]
    Lg = rollout_ahat(LI0, t_u, np.asarray(z["tau1_nm"])[m],
                      np.asarray(z["tau2_nm"])[m], q0)
    assert Lg is not None, "mirror golden 발산"
    mm = Lg["t"] <= W.T_END + 1e-12
    n = min(mm.sum(), len(t))
    diffs = {k: float(np.abs(Lg[k][:n] - np.asarray(z[k2], float)[:n]).max())
             for k, k2 in (("bz", "bz"), ("q1", "q1"), ("q2", "q2"),
                           ("dq1", "dq1"), ("dq2", "dq2"))}
    apex_rec = float(np.asarray(z["bz"])[(t > 0) & (t <= W.T_END)].max())
    apex_new = float(Lg["bz"][(Lg["t"] > 0) & mm].max())
    ok = max(diffs.values()) < 1e-6
    return dict(maxdiff=diffs, apex_recorded_win=apex_rec, apex_replay_win=apex_new,
                ok=bool(ok))


def liftoff_of(res):
    return (float(res["t"][np.argmax(res["fz"] < 0.5)])
            if (res["fz"] < 0.5).any() else None)


def fn_fixed(l_i):
    """고정-l_i 판 심볼릭 팩토리 — 동일 fit 5장 = 상수 Lagrange 블렌드."""
    f = fit_li(l_i)
    return make_funcs([f] * 5, float(l_i))


def sweep_solve_at(li_mm, warm):
    """고정-l_i NLP 1점 (자유해 1회, iter 캡 2000).
    ※ 홉/체인 warm 축 기각 (run6): 홉은 전 구간 열세 (t_f 사다리 h 단조 하락),
    이웃 체인 warm은 국소최적 붕괴(26mm h 0.51)를 하류로 오염 — 시드 고정이 강건."""
    l_i = li_mm / 1000.0
    fn1 = fn_fixed(l_i)
    w = dict(Y=warm["Y"], DY=warm["DY"], U=warm["U"], FX=warm["FX"], LI=l_i)
    r = solve_t0wc(fn1, w, l_i, l_i, max_iter=2000)
    return r, fn1, False


def sweep_row(li_mm, r, hop_used):
    """스윕 1점 기록: 플랜 감사 + 트윈 â 재생 격차 + r 가드."""
    tt = r["t"]
    q1_pl = -r["Y"][1] - np.pi / 2
    qm_pl = -r["Y"][2]
    L_plan = dict(t=tt, q1=q1_pl, q2=qm_pl, dq1=-r["DY"][1], dq2=-r["DY"][2],
                  sh1=r["U"][0], sh2=r["U"][1])
    aud = T0.audit(L_plan, cvt=True)
    l_i = li_mm / 1000.0
    L = rollout_ahat(l_i, tt, r["U"][0], r["U"][1],
                     (float(q1_pl[0]), float(qm_pl[0])))
    h_twin = float(L["bz"][L["t"] > 0].max()) if L is not None else float("nan")
    aud_tw = (T0.audit(L, cvt=True) if L is not None else None)
    qg, rg = RU.rtab(round(l_i, 6))
    rr = np.interp(r["Y"][2], qg, rg)
    return dict(
        l_i_mm=float(li_mm), h_plan=float(r["h_plan"]), h_twin=h_twin,
        gap_pct=float(100 * (h_twin / r["h_plan"] - 1.0)) if np.isfinite(h_twin) else None,
        status=r["status"], iters=r["iters"], wall_s=r["wall_s"],
        liftoff_plan_s=liftoff_of(r), hop_used=bool(hop_used),
        audit_plan_pass=bool(aud["pass"]),
        audit_plan={k: (bool(v) if k == "pass" else float(v)) for k, v in aud.items()},
        audit_twin_pass=(bool(aud_tw["pass"]) if aud_tw else None),
        r_guard_margin_rtab=float(rr.max() - R_GUARD),
        validity=validity(li_mm))


def sweep_stage(seed_res):
    """고정-l_i NLP 스윕 — 전 점 공통 warm = joint 최적해 (체인 오염 방지, run6 교훈)
    + 피크 ±0.5mm 세분. 반환: (rows dict, sols dict — l_i키별 res)."""
    rows, sols = {}, {}
    t00 = time.time()
    for li_mm in SWEEP_LIS_MM:
        r, _, hop = sweep_solve_at(li_mm, seed_res)
        rows[f"{li_mm:g}"] = sweep_row(li_mm, r, hop)
        sols[f"{li_mm:g}"] = r
        print(f"[sweep {li_mm:g}mm] {r['status']} h_plan={r['h_plan']:.4f} "
              f"h_twin={rows[f'{li_mm:g}']['h_twin']:.4f} "
              f"gap={rows[f'{li_mm:g}']['gap_pct']:+.1f}% "
              f"[{time.time() - t00:.0f}s]", flush=True)
    # 피크 세분 (±0.5mm — 기존 점과 0.25mm 이상 떨어진 것만)
    conv = {k: v for k, v in rows.items() if v["status"] == "converged"}
    if conv:
        kb = max(conv, key=lambda k: conv[k]["h_plan"])
        lb = rows[kb]["l_i_mm"]
        for li_mm in (lb - SWEEP_REFINE_MM, lb + SWEEP_REFINE_MM):
            li_mm = round(li_mm, 3)
            if not (LI_LB * 1000 <= li_mm <= LI_UB * 1000):
                continue
            if any(abs(li_mm - v["l_i_mm"]) < 0.25 for v in rows.values()):
                continue
            if 29.6 < li_mm < 29.999:      # EoM 적합 유효성 협대역 제외
                continue
            r, _, hop = sweep_solve_at(li_mm, sols[kb])
            rows[f"{li_mm:g}"] = sweep_row(li_mm, r, hop)
            sols[f"{li_mm:g}"] = r
            print(f"[sweep refine {li_mm:g}mm] {r['status']} h_plan={r['h_plan']:.4f} "
                  f"gap={rows[f'{li_mm:g}']['gap_pct']:+.1f}%", flush=True)
    return rows, sols


def sweep_curve_png(rows, joint_pt, refs):
    fig, ax = plt.subplots(figsize=(8.5, 5))
    conv = {k: v for k, v in rows.items() if v["status"] == "converged"}
    lis = sorted(v["l_i_mm"] for v in conv.values())
    key = {v["l_i_mm"]: k for k, v in conv.items()}
    hp = [conv[key[x]]["h_plan"] for x in lis]
    ht = [conv[key[x]]["h_twin"] for x in lis]
    ax.plot(lis, hp, marker="o", label="fixed-l_i NLP h_plan")
    ax.plot(lis, ht, marker="s", ls="--", label="twin ahat-replay h")
    fails = [v["l_i_mm"] for v in rows.values() if v["status"] != "converged"]
    if fails:
        ax.plot(fails, [min(hp)] * len(fails), marker="x", ms=10, ls="none",
                label=f"not converged (iter cap): {[f'{x:g}' for x in fails]} mm")
    ax.plot([joint_pt[0]], [joint_pt[1]], marker="*", ms=15, ls="none",
            label=f"joint NLP (l_i free): {joint_pt[0]:.2f} mm, {joint_pt[1]:.3f} m")
    if "cma_cl_liopt" in refs:
        ax.plot([refs["cma_cl_liopt"]["l_i_mm"]], [refs["cma_cl_liopt"]["h_plan"]],
                marker="^", ms=10, ls="none",
                label=f"CMA CL free-l_i: {refs['cma_cl_liopt']['l_i_mm']:.2f} mm, "
                      f"{refs['cma_cl_liopt']['h_plan']:.3f} m")
    ax.plot([LI_FIT_MM], [refs["cma_cl_li2508"]["h_plan"]], marker="v", ms=10,
            ls="none", label=f"CMA CL l_i=25.08: {refs['cma_cl_li2508']['h_plan']:.3f} m")
    ax.axvline(LI_FIT_MM, ls="--", alpha=0.6, label="verified anchor 25.08 (0429 CVT)")
    ax.axvline(30.0, ls="--", alpha=0.35, label="verified anchor 30 (no-CVT)")
    ax.axvline(AVT_OPT_MM, ls=":", label="AVT analytic opt 25.161")
    ax.axvspan(LI_LB * 1000, LI_FIT_MM, alpha=0.08,
               label="extrapolation zone (CVT layer fit @25.08)")
    ax.set_xlabel("l_i [mm]")
    ax.set_ylabel("h (base-z apex 계열) [m]")
    ax.set_title("task0 with_cvt NLP: h vs l_i (fixed-l_i sweep + joint)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_SWEEP_PNG, dpi=150)
    print(f"saved {OUT_SWEEP_PNG.name}", flush=True)


def tn_report(U, dq1, dq2, fz):
    lim1 = T0.TN_COEF * np.abs(U[0]) + T0.TN_OFF
    lim2 = T0.TN_COEF * np.abs(U[1]) + T0.TN_OFF
    m1 = lim1 - np.abs(dq1)
    m2 = lim2 - np.abs(dq2)
    st = fz >= 0.5
    return dict(
        hip_active_pct_stance=float(np.mean(m1[st] <= TN_ACT_TOL) * 100) if st.any() else 0.0,
        knee_active_pct_stance=float(np.mean(m2[st] <= TN_ACT_TOL) * 100) if st.any() else 0.0,
        hip_active_pct_all=float(np.mean(m1 <= TN_ACT_TOL) * 100),
        knee_active_pct_all=float(np.mean(m2 <= TN_ACT_TOL) * 100),
        hip_min_margin_rads=float(m1.min()),
        knee_min_margin_rads=float(m2.min()),
        active_tol_rads=TN_ACT_TOL)


def validity(li_mm):
    return "extrapolation" if li_mm < LI_FIT_MM - 1e-9 else "interpolation"


# ══════════ main ══════════
def main():
    t00 = time.time()
    print("═══ P25-task0 with_cvt — NLP (l_i 결정변수, p24a CVT twin) ═══", flush=True)
    W.setup()
    assert abs(B.RAW_CLIP - T0.RAW15) < 1e-9, B.RAW_CLIP
    ah_mot = float(B.ahat_env_np(10.0, +1.0))
    assert abs(ah_mot - 15.0) < 0.02, f"RAW15 검증 실패: {ah_mot}"
    print(f"[검증] raw={T0.RAW15} → â_motoring={ah_mot:.4f} Nm  R19.CLIP={R19.CLIP}",
          flush=True)

    # 골든 ①: 배선 = 정본 (0429 재생 2.6057 + CL 미러)
    gold_w = W.golden()
    # 골든 ②: â 주입 롤아웃 미러
    mg = mirror_golden()
    print(f"[mirror golden] max|Δ|={max(mg['maxdiff'].values()):.2e}  "
          f"apex {mg['apex_recorded_win']:.4f}→{mg['apex_replay_win']:.4f}  "
          f"{'PASS' if mg['ok'] else 'FAIL'}", flush=True)
    assert mg["ok"], "mirror golden FAIL — rollout_ahat 배선 불일치"

    # AVT mechanism vs 트윈 폐쇄 교차검증
    xchk = avt_crosscheck([LI0, LI0 - 2 * DLI, LI0 + 2 * DLI])
    xmax = max(v["max_dJ"] for v in xchk.values())
    print(f"[AVT crosscheck] max|q2_avt-(-qk)|={max(v['max_dq2_rad'] for v in xchk.values()):.2e} "
          f"rad  max|J_avt-r|={xmax:.2e}", flush=True)
    assert xmax < 1e-3, f"AVT mechanism ≠ 트윈 폐쇄 (J 편차 {xmax}) — 가드 사용 불가"

    print(f"박스: q1 [{T0.Q1_LB},{T0.Q1_UB}]  qm [{T0.QM_LB},{T0.QM_UB}]  "
          f"l_i [{LI_LB * 1000:g},{LI_UB * 1000:g}]mm  J≤{R_GUARD}", flush=True)

    # ── 신뢰영역 반복 (시드 attempt 2종: li2508 / liopt — 최고 h 채택) ──
    fit_resid_max = {}
    interp_chk = {}

    def trust_solve(label, npz_path, li0):
        l_c = float(np.clip(li0, LI_LB + 2 * DLI, LI_C_MAX))
        warm = None
        res = None
        rounds_log = []
        shift = None
        truncated = False
        for rnd in range(MAX_ROUNDS):
            t0r = time.time()
            lis = [l_c + u * DLI for u in US]
            F5 = [fit_li(x) for x in lis]
            for f in F5:
                for kk, vv in f["resids"].items():
                    fit_resid_max[kk] = max(fit_resid_max.get(kk, 0.0), float(vv))
            npf = NpF(F5, l_c)
            if not interp_chk:
                interp_chk.update(validate_interp(F5, l_c))
                print(f"[l_i 보간 검증] {interp_chk}", flush=True)
            fn = make_funcs(F5, l_c)
            if warm is None:
                # ※ feas 프리솔브 축은 기각 (run3/run4): 트윈 트레이스는 NLP 접촉모델의
                #   가능해 다양체에서 멀어 restoration이 웅크림 붕괴 (h 0.20) — 분지
                #   진입은 trust 해 + 이지 강제 호모토피(아래 basin hop)가 담당.
                warm = warm_from_cma(npf, li0, npz_path)
                shift = warm["shift"]
                print(f"[{label}] warm={Path(npz_path).name} li0={li0 * 1000:.2f}mm "
                      f"apex정렬 shift={shift * 1000:+.0f}ms", flush=True)
            print(f"[{label} r{rnd}] fits@{[f'{x * 1000:.2f}' for x in lis]}mm "
                  f"resid(max) M={max(f['resids']['M'] for f in F5):.1e} "
                  f"[{time.time() - t0r:.0f}s]", flush=True)
            res = solve_t0wc(fn, warm, l_c - 2 * DLI, l_c + 2 * DLI)
            li_star = res["LI"]
            at_lo = li_star - res["li_bounds"][0] < 1e-5
            at_hi = res["li_bounds"][1] - li_star < 1e-5
            at_glob = (abs(li_star - LI_LB) < 2e-6) or (abs(li_star - LI_UB) < 2e-6)
            cap_hi = at_hi and abs(l_c - LI_C_MAX) < 1e-9      # 적합 유효성 상한 절단
            rounds_log.append(dict(round=rnd, l_c_mm=l_c * 1000, li_mm=li_star * 1000,
                                   h_plan=res["h_plan"], status=res["status"],
                                   iters=res["iters"], wall_s=res["wall_s"],
                                   at_edge=bool(at_lo or at_hi)))
            print(f"[{label} r{rnd}] {res['status']} iters={res['iters']} "
                  f"wall={res['wall_s']:.0f}s  h_plan={res['h_plan']:.4f}  "
                  f"l_i*={li_star * 1000:.3f}mm  edge={'Y' if (at_lo or at_hi) else 'N'}",
                  flush=True)
            if not (at_lo or at_hi) or at_glob or cap_hi:
                truncated = cap_hi
                break
            l_c = float(np.clip(li_star, LI_LB + 2 * DLI, LI_C_MAX))
            warm = dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"], LI=li_star)
        return dict(label=label, res=res, l_c=l_c, rounds=rounds_log,
                    warm_npz=Path(npz_path).name, warm_li0_mm=li0 * 1000,
                    warm_shift_s=shift, truncated_at_fit_cap=bool(truncated))

    attempts = [trust_solve("li2508", WARM_NPZ, LI0)]
    liopt_npz = HERE / "t0wc_cl_liopt.npz"
    if liopt_npz.exists():
        li0_b = float(np.load(liopt_npz)["l_i"]) / 1000.0
        attempts.append(trust_solve("liopt", liopt_npz, li0_b))
    att = max(attempts, key=lambda a: a["res"]["h_plan"])
    res, l_c = att["res"], att["l_c"]
    rounds_log = att["rounds"]
    print(f"[선택] attempt={att['label']}  h_plan={res['h_plan']:.4f}  "
          f"(후보: {[(a['label'], round(a['res']['h_plan'], 4)) for a in attempts]})",
          flush=True)
    F5 = [fit_li(l_c + u * DLI) for u in US]
    npf = NpF(F5, l_c)
    fn = make_funcs(F5, l_c)

    # ── 분지 홉 호모토피: 조기 이지 강제(비행 t≥t_f) 사다리 → 해제 재해 ──
    # 동기: CMA 분지(이지 0.04~0.1s + 비행 턱으로 bz(T) +0.1m)는 트윈-트레이스 warm으론
    # 도달 불가 (run2~4) — 자기 플랜트 해에서 이지 시각만 제약으로 끌어내리는 호모토피가
    # 분지를 보존하며 이동. 각 단은 직전 "강제해" warm, 자유 재해로 가치 측정.
    hops = []
    best_free = res
    warm_h = dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"], LI=res["LI"])
    for t_f in (0.20, 0.14, 0.10):
        rh = solve_t0wc(fn, warm_h, l_c - 2 * DLI, l_c + 2 * DLI, t_flight=t_f)
        hops.append(dict(t_flight=t_f, status=rh["status"], h_plan=rh["h_plan"],
                         li_mm=rh["LI"] * 1000, iters=rh["iters"]))
        print(f"[hop t_f={t_f}] {rh['status']} iters={rh['iters']} "
              f"h={rh['h_plan']:.4f} l_i={rh['LI'] * 1000:.2f}mm", flush=True)
        if rh["status"] != "converged":
            break
        warm_h = dict(Y=rh["Y"], DY=rh["DY"], U=rh["U"], FX=rh["FX"], LI=rh["LI"])
        rf = solve_t0wc(fn, warm_h, l_c - 2 * DLI, l_c + 2 * DLI)
        hops.append(dict(t_flight=None, status=rf["status"], h_plan=rf["h_plan"],
                         li_mm=rf["LI"] * 1000, iters=rf["iters"]))
        print(f"[hop free@{t_f}] {rf['status']} iters={rf['iters']} "
              f"h={rf['h_plan']:.4f} l_i={rf['LI'] * 1000:.2f}mm", flush=True)
        if rf["status"] == "converged" and rf["h_plan"] > best_free["h_plan"] + 1e-6:
            best_free = rf
    if best_free is not res:
        print(f"[hop 채택] h {res['h_plan']:.4f} → {best_free['h_plan']:.4f}", flush=True)
        res = best_free
    # 홉 후 l_i가 신뢰영역 경계면 재중심 재해 (최대 2회)
    for _ in range(2):
        li_s = res["LI"]
        lo_b, hi_b = res["li_bounds"]
        at_edge = min(li_s - lo_b, hi_b - li_s) < 1e-5
        at_glob = (abs(li_s - LI_LB) < 2e-6) or (abs(l_c - LI_C_MAX) < 1e-9
                                                 and hi_b - li_s < 1e-5)
        if not at_edge or at_glob:
            break
        l_c = float(np.clip(li_s, LI_LB + 2 * DLI, LI_C_MAX))
        F5 = [fit_li(l_c + u * DLI) for u in US]
        npf = NpF(F5, l_c)
        fn = make_funcs(F5, l_c)
        r2 = solve_t0wc(fn, dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"],
                                 LI=li_s), l_c - 2 * DLI, l_c + 2 * DLI)
        print(f"[hop 재중심 l_c={l_c * 1000:.2f}mm] {r2['status']} "
              f"h={r2['h_plan']:.4f} l_i={r2['LI'] * 1000:.2f}mm", flush=True)
        if r2["status"] != "converged":
            break
        res = r2
    li_star = res["LI"]
    joint_res, joint_lc = res, l_c

    # ── 고정-l_i NLP 스윕 (사용자 지시 07-18: 교차확인 / joint 취약 시 대체) ──
    sw_rows, sw_sols = sweep_stage(dict(Y=res["Y"], DY=res["DY"], U=res["U"],
                                        FX=res["FX"]))
    method = "joint"
    conv = {k: v for k, v in sw_rows.items()
            if v["status"] == "converged" and v["audit_plan_pass"]}
    if conv:
        kb = max(conv, key=lambda k: conv[k]["h_plan"])
        if sw_rows[kb]["h_plan"] > res["h_plan"] + 1e-6:
            method = "sweep"
            res = sw_sols[kb]
            l_c = sw_rows[kb]["l_i_mm"] / 1000.0
            F5 = [fit_li(l_c)] * 5
            npf = NpF(F5, l_c)
            fn = make_funcs(F5, l_c)
            li_star = res["LI"]
    print(f"[방법 선택] {method}  h_plan={res['h_plan']:.4f}  "
          f"l_i*={li_star * 1000:.3f}mm  "
          f"(joint {joint_res['h_plan']:.4f}@{joint_res['LI'] * 1000:.2f}mm)", flush=True)

    # ── 스탠스 감사 → 초과 시 비행 강제 2차해 ──
    tt = res["t"]
    lift_plan = float(tt[np.argmax(res["fz"] < 0.5)]) if (res["fz"] < 0.5).any() else None
    if lift_plan is None or lift_plan > T0.T_ST_MAX + 1e-9:
        print(f"[스탠스 감사] 이지 {lift_plan} > {T0.T_ST_MAX}s — 비행 강제 재해", flush=True)
        lo_b, hi_b = res["li_bounds"]
        res = solve_t0wc(fn, dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"],
                                  LI=res["LI"]),
                         lo_b, hi_b, t_flight=T0.T_ST_MAX)
        li_star = res["LI"]
        tt = res["t"]
        lift_plan = float(tt[np.argmax(res["fz"] < 0.5)]) if (res["fz"] < 0.5).any() else None

    # ── EoM 공중 검증 (중심 + l_i*) ──
    air = [verify_air(F5, l_c, l_c), verify_air(F5, l_c, li_star)]
    print(f"[EoM 공중검증] center {air[0]['q_err_max']:.2e} / l_i* {air[1]['q_err_max']:.2e} "
          f"rad (0.1s×{air[0]['n']})", flush=True)

    # ── 플랜 (측정 프레임) ──
    q1_pl = -res["Y"][1] - np.pi / 2
    qm_pl = -res["Y"][2]                          # 크랭크(모터) 측정각
    dq1_pl = -res["DY"][1]
    dqm_pl = -res["DY"][2]
    q2k_pl = -np.array([float(npf.f1d("c_qk", j2, li_star)[0]) for j2 in res["Y"][2]])
    q1_0, qm_0 = float(q1_pl[0]), float(qm_pl[0])
    li_mm = li_star * 1000.0
    print(f"l_i* = {li_mm:.3f} mm ({validity(li_mm)})  시작 자세 q=({q1_0:+.4f},{qm_0:+.4f})",
          flush=True)

    L_plan = dict(t=tt, q1=q1_pl, q2=qm_pl, dq1=dq1_pl, dq2=dqm_pl,
                  sh1=res["U"][0], sh2=res["U"][1])
    A_plan = T0.audit(L_plan, cvt=True)
    print(f"[감사·플랜] pass={A_plan['pass']}  "
          + "  ".join(f"{k}={v:+.4f}" for k, v in A_plan.items() if k != "pass"),
          flush=True)
    # 브랜치 가드 (rtab 정본 + AVT 이식판 — 좌표 대응 qm_avt=−π+qc)
    qg, rg = RU.rtab(round(li_star, 6))
    rr_pl = np.interp(res["Y"][2], qg, rg)
    rg_margin = float(rr_pl.max() - R_GUARD)
    Javt_pl = np.array([float(AVT_J(-np.pi + qc, li_star)) for qc in res["Y"][2]])
    print(f"[r 가드] rtab r∈[{rr_pl.min():.3f},{rr_pl.max():.3f}] margin={rg_margin:+.4f}  "
          f"AVT J max={Javt_pl.max():.4f}", flush=True)

    # ── 트윈 â 재생 교차검증 ──
    L = rollout_ahat(li_star, tt, res["U"][0], res["U"][1], (q1_0, qm_0))
    assert L is not None, "트윈 롤아웃 발산"
    h_twin = float(L["bz"][L["t"] > 0].max())
    gap = h_twin / res["h_plan"] - 1.0
    print(f"[검증] h_plan={res['h_plan']:.4f}  h_twin={h_twin:.4f}  gap={100 * gap:+.1f}%",
          flush=True)
    mstance = tt <= 0.35
    fi = lambda k: np.interp(tt, L["t"], L[k])  # noqa: E731
    rq = float(np.sqrt(np.mean((fi("q1") - q1_pl)[mstance] ** 2
                               + (fi("q2") - qm_pl)[mstance] ** 2)))
    print(f"  플랜-트윈 스탠스 q RMSE = {rq:.4f} rad", flush=True)
    A_twin = T0.audit(L, cvt=True)
    print(f"[감사·트윈] pass={A_twin['pass']}  "
          + "  ".join(f"{k}={v:+.4f}" for k, v in A_twin.items() if k != "pass"),
          flush=True)
    mpos = L["t"] > 0
    gl = L["grf"][mpos] < 0.5
    lift_twin = float(L["t"][mpos][np.argmax(gl)]) if gl.any() else None
    rmin_t, rmax_t = W.r_range_of(L, li_star)

    # T-N 활성 + 피크
    tn_pl = tn_report(res["U"], dq1_pl, dqm_pl, res["fz"])
    m06 = (L["t"] >= 0) & (L["t"] <= B.T_HOR)
    tn_tw = tn_report(np.vstack([L["sh1"][m06], L["sh2"][m06]]),
                      L["dq1"][m06], L["dq2"][m06], L["grf"][m06])
    v1g = np.where(np.abs(dq1_pl) < 1e-9, 1e-9, dq1_pl)
    v2g = np.where(np.abs(dqm_pl) < 1e-9, 1e-9, dqm_pl)
    raw1 = B.raw_of(res["U"][0], v1g)
    raw2 = B.raw_of(res["U"][1], v2g)
    stance_n = res["fz"] >= 0.5
    peaks = dict(
        s1_absmax=float(np.abs(res["U"][0]).max()),
        s2_absmax=float(np.abs(res["U"][1]).max()),
        raw1_absmax=float(np.abs(raw1).max()),
        raw2_absmax=float(np.abs(raw2).max()),
        dq1_absmax=float(np.abs(dq1_pl).max()),
        dqm_absmax=float(np.abs(dqm_pl).max()),
        grf_max=float(res["fz"].max()),
        grf_twin_max=float(L["grf"].max()),
        ceiling_ride_pct_stance=[
            float(np.mean(np.abs(res["U"][0])[stance_n] >= TAU_LIM - 0.01) * 100),
            float(np.mean(np.abs(res["U"][1])[stance_n] >= TAU_LIM - 0.01) * 100)],
        raw_le_clip_ok=bool(max(np.abs(raw1).max(), np.abs(raw2).max())
                            <= B.RAW_CLIP + 0.005))
    print(f"피크: |s|=({peaks['s1_absmax']:.2f},{peaks['s2_absmax']:.2f})/15  "
          f"|raw|=({peaks['raw1_absmax']:.3f},{peaks['raw2_absmax']:.3f})/{B.RAW_CLIP:g}  "
          f"|dq|=({peaks['dq1_absmax']:.1f},{peaks['dqm_absmax']:.1f})  "
          f"τ천장=({peaks['ceiling_ride_pct_stance'][0]:.0f}%,"
          f"{peaks['ceiling_ride_pct_stance'][1]:.0f}%)", flush=True)

    # ── 참조 (CMA 고정-l_i / CMA 자유-l_i / AVT) ──
    cma_ref = safe.read_json(WARM_AUD)
    refs = dict(cma_cl_li2508=dict(l_i_mm=LI_FIT_MM, h_plan=float(cma_ref["h_plan"])),
                avt_analytic_opt_mm=AVT_OPT_MM)
    try:
        lj = safe.read_json(HERE / "t0wc_cl_liopt_audit.json")
        refs["cma_cl_liopt"] = dict(l_i_mm=float(lj["l_i_mm"]), h_plan=float(lj["h_plan"]))
    except Exception:
        pass

    # ── 스윕 산출 (json + 곡선) ──
    safe.atomic_json_write(OUT_SWEEP, dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        note="고정-l_i NLP 스윕 — 각 점 EoM 재적합, 전 점 공통 warm=joint 최적해 "
             "(이웃 체인은 국소최적 붕괴 오염으로 기각 — run6), 각 점 트윈 â 재생 "
             "격차/감사 포함 (사용자 지시 07-18)",
        clip_raw=float(B.RAW_CLIP), li_fit_mm=LI_FIT_MM, avt_opt_mm=AVT_OPT_MM,
        joint=dict(l_i_mm=joint_res["LI"] * 1000, h_plan=joint_res["h_plan"],
                   l_c_mm=joint_lc * 1000),
        chosen_method=method, rows=sw_rows))
    sweep_curve_png(sw_rows, (joint_res["LI"] * 1000, joint_res["h_plan"]), refs)

    # ── 저장 ──
    bz0 = float(res["Y"][0, 0])
    np.savez(OUT_NPZ,
             t=tt, q1=q1_pl, q2=qm_pl, qm=qm_pl, q2_knee=q2k_pl,
             dq1=dq1_pl, dq2=dqm_pl,
             raw1=raw1, raw2=raw2, tau1_nm=res["U"][0], tau2_nm=res["U"][1],
             bz=res["Y"][0], fz_plan=res["fz"], fx_plan=res["FX"][0],
             q=np.vstack([q1_pl, qm_pl]).T, dq=np.vstack([dq1_pl, dqm_pl]).T,
             q_des=np.vstack([q1_pl, qm_pl]).T, dq_des=np.vstack([dq1_pl, dqm_pl]).T,
             tau_cmd_nm=res["U"].T, tau_cmd_raw=np.vstack([raw1, raw2]).T,
             l_i=li_mm, extrapolated=float(li_mm < LI_FIT_MM - 1e-9),
             t_twin=L["t"], bz_twin=L["bz"],
             q_twin=np.vstack([L["q1"], L["q2"]]).T,
             dq_twin=np.vstack([L["dq1"], L["dq2"]]).T,
             grf_twin=L["grf"], footx_twin=L["fx"],
             h_plan=res["h_plan"], h_twin=h_twin, raw_clip=B.RAW_CLIP)

    sw_best_k = (max(conv, key=lambda k: conv[k]["h_plan"]) if conv else None)
    audit_doc = dict(
        CAMPAIGN="P25-task0 with_cvt NLP — l_i(상수) 결정변수 (task0 제약 / p24a CVT twin)",
        gen=time.strftime("%Y-%m-%d %H:%M"),
        method=method,
        method_note="joint = l_i 결정변수 NLP (5점 Lagrange 신뢰영역) / sweep = 고정-l_i "
                    "NLP 체인 스윕 — 최고 h_plan(감사 통과) 채택 (사용자 지시 07-18)",
        joint_result=dict(l_i_mm=joint_res["LI"] * 1000, h_plan=joint_res["h_plan"]),
        sweep=dict(file=OUT_SWEEP.name, n_points=len(sw_rows),
                   best=(dict(l_i_mm=sw_rows[sw_best_k]["l_i_mm"],
                              h_plan=sw_rows[sw_best_k]["h_plan"],
                              h_twin=sw_rows[sw_best_k]["h_twin"])
                         if sw_best_k else None)),
        l_i=dict(opt_mm=li_mm, bounds_mm=[LI_LB * 1000, LI_UB * 1000],
                 trust_final_mm=[res["li_bounds"][0] * 1000, res["li_bounds"][1] * 1000],
                 fit_cap_note=f"EoM 적합 유효 상한: 중심≤{LI_C_MAX * 1000:.2f}mm (최대 노드 "
                              "29.58) — (29.6,30)mm 협대역은 폐쇄 브랜치 근접 첨점으로 "
                              "적합 실패, l_i=30 무변속판은 t0nc 커버",
                 validity=validity(li_mm),
                 validity_note="CVT 층(게이트 스프링·C_CVT |r|≤0.2 캡)은 l_i=25.08 fit. "
                               "[25.08,30]=양끝 검증 내삽 (0429 CVT/무변속), <25.08=외삽",
                 chosen_attempt=att["label"],
                 attempts=[dict(label=a["label"], warm_npz=a["warm_npz"],
                                warm_li0_mm=a["warm_li0_mm"],
                                warm_shift_s=a["warm_shift_s"],
                                h_plan=a["res"]["h_plan"],
                                li_mm=a["res"]["LI"] * 1000,
                                truncated_at_fit_cap=a["truncated_at_fit_cap"],
                                rounds=a["rounds"]) for a in attempts]),
        constraints=dict(
            tau_axis_abs_max=TAU_LIM, raw_box=B.RAW_CLIP,
            tn=f"|dq| <= {T0.TN_COEF}*|ahat| + {T0.TN_OFF} (hip축 + 크랭크측)",
            dq_abs_max=T0.DQ_LIM,
            q1=[T0.Q1_LB, T0.Q1_UB], qm=[T0.QM_LB, T0.QM_UB],
            branch_guard=f"양판 하드 (전 노드): rtab(반위상) r <= {R_GUARD} (liopt/audit "
                         f"정본) + AVT mechanism_fun 이식 J(qm_avt=-pi+qc) <= {R_GUARD}",
            start="free pose in box + rest + static equilibrium (Fz(0)=M*g)",
            stance_max_s=T0.T_ST_MAX,
            stance_mode="fixed grid -> liftoff audit"
                        + (f" + enforced flight t>={res['t_flight']} (final solve)"
                           if res["t_flight"] is not None else "")),
        nlp=dict(status=res["status"], iters=res["iters"], wall_s=res["wall_s"],
                 N=B.N_NODE, dt=res["dt"], horizon_s=B.T_HOR,
                 k_c=res["k_c"], b_c=res["b_c"],
                 objective="G20 'Base via CoM v_z' (p25_b 동일)",
                 warm_start=f"{att['warm_npz']} (CMA CL) projected, apex-align shift "
                            f"+{att['warm_shift_s'] * 1000:.0f}ms, l_i0="
                            f"{att['warm_li0_mm']:.2f}mm",
                 li_variable="dimensionless uLI, l_i = l_c + uLI*0.75mm (trust region)",
                 t_flight_final=res["t_flight"],
                 basin_hop=hops),
        start=dict(q1_0=q1_0, qm_0=qm_0, bz0=bz0),
        results=dict(h_plan=res["h_plan"], h_twin_rollout=h_twin, gap_pct=100 * gap,
                     h_rise_plan=res["h_plan"] - bz0,
                     plan_twin_stance_qRMSE=rq, vz_com_T=res["vz_com_T"],
                     dh_vs_cma_li2508=res["h_plan"] - refs["cma_cl_li2508"]["h_plan"]),
        references=refs,
        stance=dict(liftoff_plan_s=lift_plan, liftoff_twin_s=lift_twin,
                    limit_s=T0.T_ST_MAX,
                    pass_plan=bool(lift_plan is not None and lift_plan <= T0.T_ST_MAX + 1e-9),
                    pass_twin=bool(lift_twin is not None and lift_twin <= T0.T_ST_MAX + 1e-9)),
        audit_plan=A_plan,
        audit_twin_rollout=A_twin,
        r_guard=dict(bound=R_GUARD, rtab_r_range_plan=[float(rr_pl.min()), float(rr_pl.max())],
                     rtab_margin_plan=rg_margin, ok_plan=bool(rg_margin <= 1e-6),
                     avt_J_max_plan=float(Javt_pl.max()),
                     rtab_r_range_twin=[rmin_t, rmax_t],
                     rtab_margin_twin=float(rmax_t - R_GUARD),
                     ok_twin=bool(rmax_t - R_GUARD <= 1e-6)),
        tn_active_plan=tn_pl,
        tn_active_twin=tn_tw,
        peaks=peaks,
        eom=dict(method="numeric fit on p24a CVT twin, (bz,j1,j2crank) reduced coords; "
                        "basis {1,cos j1,sin j1} x Cheb18(j2); l_i = 5-node Lagrange "
                        "(0.75mm spacing) trust region; kinematics = in-phase closure "
                        "(physical branch), C_CVT amp = rtab anti-phase mirror",
                 fit_rel_resid_max=fit_resid_max,
                 li_interp_check=interp_chk,
                 air_rollout_check=air),
        goldens=dict(w_golden=dict(replay_0429_mean=gold_w["replay_0429_mean"],
                                   cl_mirror_maxdiff=gold_w["cl_mirror_maxdiff"],
                                   ALL=gold_w["pass"]["ALL"]),
                     ahat_mirror=mg,
                     avt_mechanism_crosscheck=xchk),
        notes=[
            "audit_twin은 개루프 â replay의 실현 궤적 감사 — 플랜 준수여도 트윈 편차로 위반 가능",
            "T-N/|dq| 매끈화(sqrt(x²+ε²), ε=0.05)는 보수측 — 정확 fabs 감사가 기준",
            "raw 공급 박스(25.5810)와 |â|≤15 박스 공존 — 제동 가지는 박스가 지배",
            "트윈 재생 비행규약 = rollout_ol/a_full23 (t>0.6: s=0) — CL(1.1045)의 "
            "q_des 유지 규약과 다름 (기록 apex ~0.65s라 일부 손실 가능)",
            "C_CVT amp/스프링의 NLP측은 매끈화 근사 — 트윈 재생이 정확판 심판",
            "NLP-CMA h 격차의 성격: â 재생 진단(liopt CMA 해 → 트윈 1.1223 재현)이 "
            "보여주듯 트윈은 단스탠스(0.04~0.10s) 충격형 전략으로 1.12를 실현하나, "
            "본 NLP 대리 플랜트(수치 EoM + 선형 스프링-댐퍼 접촉 + 매끈화 층)는 같은 "
            "전략을 열세로 평가 (이지 강제 홉 사다리에서 t_f 짧아질수록 h 하락) — "
            "충격 레짐 대리모델 한계로 진단. 정량 진단은 audit 'diagnosis' 필드 참조",
        ])
    safe.atomic_json_write(OUT_JSON, audit_doc)
    print(f"saved {OUT_NPZ.name}, {OUT_JSON.name}", flush=True)

    # ── 그림 (색 명시 금지 — auto cycle, 매칭은 get_color) ──
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    ax = axs[0, 0]
    ln = ax.plot(tt, res["Y"][0], label="plan bz")
    lt = ax.plot(L["t"], L["bz"], "--", label="twin rollout bz")
    ax.axhline(res["h_plan"], ls=":", lw=1, color=ln[0].get_color(),
               label=f"h_plan {res['h_plan']:.3f}")
    ax.axhline(h_twin, ls=":", lw=1, color=lt[0].get_color(),
               label=f"h_twin {h_twin:.3f}")
    ax.set_title("Base height [m]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[0, 1]
    l1 = ax.plot(tt, q1_pl, label="plan q1")
    l2 = ax.plot(tt, qm_pl, label="plan qm (crank)")
    l3 = ax.plot(tt, q2k_pl, ls="-.", label="plan q2 knee (mech)")
    ax.plot(L["t"], L["q1"], "--", color=l1[0].get_color(), label="twin q1")
    ax.plot(L["t"], L["q2"], "--", color=l2[0].get_color(), label="twin qm")
    for v, c in ((T0.Q1_LB, l1), (T0.Q1_UB, l1), (T0.QM_LB, l2), (T0.QM_UB, l2)):
        ax.axhline(v, ls=":", lw=0.8, color=c[0].get_color(), alpha=0.5)
    ax.set_title("Angles (measured; task0 boxes dotted)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[0, 2]
    l1 = ax.plot(tt, dq1_pl, label="plan dq1")
    l2 = ax.plot(tt, dqm_pl, label="plan dqm")
    ax.plot(L["t"], L["dq1"], "--", color=l1[0].get_color())
    ax.plot(L["t"], L["dq2"], "--", color=l2[0].get_color())
    ax.axhline(T0.DQ_LIM, ls=":", lw=0.8, alpha=0.6)
    ax.axhline(-T0.DQ_LIM, ls=":", lw=0.8, alpha=0.6)
    ax.set_title("Velocities [rad/s] (|dq|<=50 dotted)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 0]
    ax.plot(tt, res["U"][0], label="s1 (hip)")
    ax.plot(tt, res["U"][1], label="s2 (crank motor)")
    ax.axhline(TAU_LIM, ls=":", lw=1); ax.axhline(-TAU_LIM, ls=":", lw=1)
    ax.set_title("Command ahat u=s [Nm] (|ahat|<=15)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 1]
    tr = np.linspace(0, TAU_LIM, 60)
    ax.plot(tr, T0.TN_COEF * tr + T0.TN_OFF, "k--", lw=1, alpha=0.5, label="T-N envelope")
    ax.plot(np.abs(res["U"][0]), np.abs(dq1_pl), ".", ms=4, label="hip")
    ax.plot(np.abs(res["U"][1]), np.abs(dqm_pl), ".", ms=4, label="crank")
    ax.set_xlabel("|ahat| [Nm]"); ax.set_ylabel("|dq| [rad/s]")
    ax.set_title("T-N limit check"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 2]
    ax.plot(tt, res["fz"], label="plan Fz")
    ax.plot(L["t"], L["grf"], "--", label="twin GRF")
    ax.set_xlim(-0.05, 0.45)
    ax.set_title("Contact normal force [N]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.suptitle(
        f"P25-task0 with_cvt NLP (l_i free) — l_i* {li_mm:.2f} mm ({validity(li_mm)}) | "
        f"h_plan {res['h_plan']:.3f} / twin {h_twin:.3f} ({100 * gap:+.1f}%) | "
        f"CMA li2508 {refs['cma_cl_li2508']['h_plan']:.4f} | AVT opt {AVT_OPT_MM} mm | "
        f"liftoff {lift_plan}s")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=110)
    print(f"saved {OUT_PNG.name}  [{(time.time() - t00) / 60:.1f} min total]", flush=True)
    print(f"SUMMARY l_i*={li_mm:.3f}mm  h_plan={res['h_plan']:.4f}  h_twin={h_twin:.4f}  "
          f"gap={100 * gap:+.2f}%  vs CMA {refs['cma_cl_li2508']['h_plan']:.4f}", flush=True)


if __name__ == "__main__":
    main()
