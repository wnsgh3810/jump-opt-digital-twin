# -*- coding: utf-8 -*-
"""P25 Phase B — 해석적 NLP (CasADi direct collocation) on the p24a twin, 측정 법칙층 내장.

과제 (MARATHON_p25.md Phase B): 수직 최대 점프를 CasADi/IPOPT 직접 콜로케이션으로 최적화.
플랜트 = 승격 p24a 트윈 (fourbar_p24a_candidate.json)의 물리 **전 층 포함**:
  supp(무릎 부하-지지) + rise(게이트 상승항) + 부하연동 스프링 + 힙 부하-지지층 — 전부
  매끈한 함수라 심볼릭으로 그대로 내장 (NLP의 제어변수 u₂ = s₂(사후 ahat 명령)이므로
  층들은 제어·상태의 명시적 함수 — 암묵 루프 없음).

═══ 모델링 선택 (문서화 의무 항목) ═══
1) 등가 3-DOF EoM (bz, j1, j2 — MuJoCo 모델 프레임): **수치 적합** 경로 채택.
   l_i=30 flip은 정확한 평행사변형 (cvt_core.closure 잔차 1e-16, connect efc_pos=0 확인)
   → 전 좌표 q = [bz, j1, j2, -j2, j2] 선형 사상 Jm. M_red = Jmᵀ M_full Jm,
   G_red = Jmᵀ qfrc_bias(qvel=0)를 격자 샘플 → 삼각함수 기저
   {1, cos/sin j1, cos/sin j2, cos/sin(j1±j2), cos/sin 2j2} 최소제곱 적합
   (상대 잔차 ~1e-15 = 기계 정밀도, 실행 시 assert). 코리올리는 적합 M의
   Christoffel(CasADi 미분)로 — 구속 라그랑주 시스템이라 정확.
   armature는 mj_fullM에 포함, dof_damping은 d_red = Jmᵀ diag(damp) Jm (상수),
   frictionloss는 tanh(dq/EPS_V) 매끈화 (MuJoCo는 constraint 기반 정확 stiction —
   저속 교차에서만 차이, 검증 롤아웃으로 정량화).
2) 접촉: G20 레시피 — 발(원기둥 r=21mm) 스프링-댐퍼 지면.
   k_c = 1.3e5 N/m, b_c = 180 (G20 contact_sweep RECOMMENDED행 = 실측 k_eq).
   ★ 정직 노트: p24a 트윈 재실측(하중 스윕 0.5~8g) 시 시컨트 k_eq ≈ 4.4e4로 비선형
   (solimp 저부하 연화) — 단 점프 하중대(125~250N) 국소 기울기 ≈ 1.1e5로 G20값과 근접.
   기본 k_c=1.3e5 유지 + k_c=4.4e4 감도 재해석 1회 (결과 JSON에 병기).
   Fz = k_c·δ⁺ + b_c·δ̇·(δ⁺/(δ⁺+EPS_C)), δ⁺ = 매끈화 양수부. 노드 제약 Fz ≥ -0.5 N.
3) 미끄럼: 프로브에서 트윈 발은 **구름 접촉** (Δx_center ≈ +R·Δφ_calf, 미소슬립 rms
   1.3mm) → 스탠스 중 구름 밴드 제약 |fx - fx0 - R(φ-φ0)|·w ≤ 3mm (관측 미소슬립 스케일),
   w = Fz/(Fz+5) 이완 게이트. F_x는 결정변수, 마찰콘 |F_x| ≤ μ·Fz (μ=1.0 = 트윈 geom).
4) 공급 천장: |raw| ≤ 35.5 를 **보수적 포락선**으로 — u ∈ [ahat(-35.5, v), ahat(+35.5, v)],
   sgn(v)는 tanh(v/EPS_S) 매끈화. ahat이 raw에 단조(도함수 0.54@35.5 > 0)라 이 포락선은
   사실상 정확 (매끈화 오차만 근사). 출력 raw = 뉴턴 역변환 (p14 invert_paper 패턴).
5) 목적: G20 관례 그대로 — h_plan = bz(T) + max(v_com_z(T),0)²/(2g)
   ("Base via CoM v_z" = G20 optimizer target; T=0.6s 시점 비행 제약과 함께
   탄도 외삽. 비행 중 관절 재배치의 bz 편차는 트윈 롤아웃이 흡수/검증).
6) 시작: 0602 웅크림 = jump_0602/120_2_120_2 trial q(0) (Phase D 중간 게인세트와 동일
   폴더 — 문서화된 선택), 정지, 발 정적 침투 δ_st = M_tot·g/k_c.
7) 검증 (의무): 최적 u(t)를 실제 MuJoCo p24a 트윈에 개루프 재생 (a_full23 스타일 —
   settle 0.4s 온라인 PD 후 s₁,s₂ 주입, 층은 cl_run23 규약대로 **온라인**(시뮬 상태로)
   계산 = 플랜트측 법칙의 물리적 구현) → h_twin vs h_plan.

산출: p25_b_results.json + p25_b_traj.npz (Phase A 스키마: t, q, dq, tau_cmd raw+Nm,
bz, q_des:=q, dq_des:=dq) + p25_b_summary.png.

실행: PYTHONIOENCODING=utf-8 python p25_b_nlp.py   (읽기 전용 하네스, 커밋 없음)
"""
import os

os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_REFIT"] = "1"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
G22 = HERE.parent
for pth in ("p23_veins", "p22_beyond", "p20_rise", "p19_jump", "p18_cvt"):
    sys.path.insert(0, str(G22 / pth))
sys.path.insert(0, str(G22.parent.parent / "code/bench"))
sys.path.insert(0, str(G22.parent / "bench"))

import safe

safe.utf8_console()

import casadi as ca
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import p23_v6_runners as RU
import p21_cma as C
import p19_run as R19

# ══════════ 상수 (선택 문서화) ══════════
KT, GR, CF = 0.091, 9.0, 0.59          # p14_judge 규약 (AK80-9 V2)
RAW_CLIP = 35.5                        # R19.CLIP — 공급 천장 (raw)
K_C = 1.3e5                            # [N/m] G20 RECOMMENDED (실측 k_eq)
B_C = 180.0                            # [N·s/m] G20 페어링
K_C_ALT = 4.43e4                       # p24a 재실측 시컨트 (감도 재해석용)
MU = 1.0                               # 트윈 geom sliding friction (foot=floor=1.0)
T_HOR = 0.6                            # [s] horizon (MARATHON 고정)
N_NODE = 121                           # 콜로케이션 노드 (120 구간, dt≈5ms)
EPS_A = 0.05                           # [Nm] soft-abs
EPS_M = 0.1                            # soft-min
EPS_V = 0.05                           # [rad/s] frictionloss tanh 매끈화 (NLP)
EPS_S = 0.5                            # [rad/s] ahat sgn(v) tanh 매끈화
EPS_C = 1e-4                           # [m] 침투 양수부 매끈화
SLIP_BAND = 0.003                      # [m] 구름 밴드 (관측 미소슬립 rms 1.3mm의 ~2배)
FZ_W0 = 5.0                            # [N] 이완 게이트 스케일
START_TRIAL = ("jump_0602", "120_2_120_2")
G20_REF = 1.063                        # G20 k_c=k_eq 완결판 트윈 실현 높이 [m]
GG = 9.81

OUT_JSON = HERE / "p25_b_results.json"
OUT_NPZ = HERE / "p25_b_traj.npz"
OUT_PNG = HERE / "p25_b_summary.png"


# ══════════ 1. 하네스 초기화 + p24a 트윈 ══════════
def init_twin():
    RU.ensure_init()
    cand = safe.read_json(G22 / "p23_veins/fourbar_p24a_candidate.json")
    x = np.asarray(cand["x"], float)
    v = RU.apply_freeze(RU.pad23(x))
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    kr = RU.rise_of(float(v[21]))
    x32, sp = C.x32_of(v[:20])
    model = RU.build_flip23(x32, float(v[1]), sp, float(v[21]))
    return model, dict(v=v, law=law, spr=spr, kr=kr, x32=x32, sp=sp, cand=cand)


# ══════════ 2. 등가 3-DOF 추출 (수치 적합) ══════════
NB = 11  # 기저 크기


def _basis_np(j1, j2):
    return np.array([np.ones_like(j1), np.cos(j1), np.sin(j1), np.cos(j2),
                     np.sin(j2), np.cos(j1 + j2), np.sin(j1 + j2),
                     np.cos(j1 - j2), np.sin(j1 - j2),
                     np.cos(2 * j2), np.sin(2 * j2)])


def _basis_ca(j1, j2):
    return ca.vertcat(1, ca.cos(j1), ca.sin(j1), ca.cos(j2), ca.sin(j2),
                      ca.cos(j1 + j2), ca.sin(j1 + j2),
                      ca.cos(j1 - j2), ca.sin(j1 - j2),
                      ca.cos(2 * j2), ca.sin(2 * j2))


def extract_reduced(model, twin, j1_rng, j2_rng):
    """격자 샘플 → M_red/G_red/FK(fx, fz_rel, φ_calf, zc_com) 기저 적합 + 검증."""
    mj = C._W["mj"]
    S = C._W["P"].J._P["S"]
    iq = {n: safe.qadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    idof = {n: safe.dofadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    nv = model.nv
    Jm = np.zeros((nv, 3))
    Jm[0, 0] = 1.0
    Jm[idof["hip"], 1] = 1.0
    Jm[idof["knee_motor"], 2] = 1.0
    Jm[idof["cpin"], 2] = -1.0
    Jm[idof["knee"], 2] = 1.0
    data = mj.MjData(model)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    cb = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "calf")
    BZ = 2.0  # 공중 (접촉 없음)

    def set_pose(j1, j2):
        data.qpos[:] = 0
        data.qpos[0] = BZ
        data.qpos[iq["hip"]] = j1
        data.qpos[iq["knee_motor"]] = j2
        data.qpos[iq["cpin"]] = -j2
        data.qpos[iq["knee"]] = j2
        data.qvel[:] = 0
        mj.mj_forward(model, data)

    def phi_at(j1, j2):
        set_pose(j1, j2)
        xm = data.xmat[cb].reshape(3, 3)
        return float(np.arctan2(xm[0, 2], xm[2, 2]))

    j1s = np.linspace(*j1_rng, 21)
    j2s = np.linspace(*j2_rng, 21)
    rows, tM, tG, tF, tPhi = [], [], [], [], []
    Mfull = np.zeros((nv, nv))
    for j1 in j1s:
        for j2 in j2s:
            set_pose(j1, j2)
            mj.mj_fullM(model, Mfull, data.qM)
            Mr = Jm.T @ Mfull @ Jm
            Gr = Jm.T @ data.qfrc_bias
            xm = data.xmat[cb].reshape(3, 3)
            tPhi.append(float(np.arctan2(xm[0, 2], xm[2, 2])))
            rows.append(_basis_np(j1, j2))
            tM.append([Mr[0, 0], Mr[0, 1], Mr[0, 2], Mr[1, 1], Mr[1, 2], Mr[2, 2]])
            tG.append(Gr)
            tF.append([data.geom_xpos[fg][0], data.geom_xpos[fg][2] - BZ,
                       data.subtree_com[0][2] - BZ])
    rows = np.array(rows)
    fits, resids = {}, {}
    for name, T in (("M", np.array(tM)), ("G", np.array(tG)), ("F", np.array(tF))):
        coef, *_ = np.linalg.lstsq(rows, T, rcond=None)
        rel = np.abs(rows @ coef - T).max(axis=0) / (np.abs(T).max(axis=0) + 1e-9)
        fits[name] = coef
        resids[name] = rel
        assert rel.max() < 1e-9, f"{name} 기저 적합 실패: rel={rel}"
    # φ_calf: 평면 힌지 체인이라 (j1, j2)에 정확 선형 — 중심 유한차분으로 기울기
    # (±1 정수 기대), 격자 전수 랩-인지 잔차로 검증 (atan2 랩은 선형 적합을 깨므로 분리)
    jc1, jc2 = float(np.mean(j1_rng)), float(np.mean(j2_rng))
    hh = 1e-5
    p1 = (phi_at(jc1 + hh, jc2) - phi_at(jc1 - hh, jc2)) / (2 * hh)
    p2 = (phi_at(jc1, jc2 + hh) - phi_at(jc1, jc2 - hh)) / (2 * hh)
    p0 = phi_at(jc1, jc2) - p1 * jc1 - p2 * jc2
    phi_res = []
    idx = 0
    for j1 in j1s:
        for j2 in j2s:
            pred = p0 + p1 * j1 + p2 * j2
            e = (tPhi[idx] - pred + np.pi) % (2 * np.pi) - np.pi
            phi_res.append(abs(e))
            idx += 1
    phi_resid = float(max(phi_res))
    assert phi_resid < 1e-6, f"φ 선형 적합 실패: {phi_resid}"
    resids["phi"] = np.array([phi_resid])
    d_red = Jm.T @ np.diag(model.dof_damping) @ Jm
    fl = model.dof_frictionloss.copy()
    ks, kref, tspr = RU.spr_resolve(model, twin["spr"])
    ex = dict(Jm=Jm, iq=iq, idof=idof, coefM=fits["M"], coefG=fits["G"],
              coefF=fits["F"], phi_coef=(p0, p1, p2), d_red=d_red, fl=fl,
              R=float(S.FOOT_RADIUS), ks=ks, kref=kref, tspr=tspr,
              resids={k: v.tolist() for k, v in resids.items()},
              Mtot=float(model.body_mass.sum()))
    return ex


def verify_reduced(model, ex, j1_rng, j2_rng, n_trial=5, n_step=200):
    """공중 개루프 토크 롤아웃: mj_step vs 적합 EoM RK4 — 궤적 레벨 정량 검증."""
    mj = C._W["mj"]
    data = mj.MjData(model)
    coefM, coefG, Jm = ex["coefM"], ex["coefG"], ex["Jm"]
    d_red, fl = ex["d_red"], ex["fl"]
    dt = model.opt.timestep

    def Mred(y):
        m = _basis_np(y[1], y[2]) @ coefM
        return np.array([[m[0], m[1], m[2]], [m[1], m[3], m[4]], [m[2], m[4], m[5]]])

    def f_ode(y, dy, u):
        h = 1e-6
        c = np.zeros(3)
        dM = []
        for k in (1, 2):
            yp = y.copy(); yp[k] += h
            ym = y.copy(); ym[k] -= h
            dM.append((Mred(yp) - Mred(ym)) / (2 * h))
        dMd = {1: dM[0], 2: dM[1], 0: np.zeros((3, 3))}
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    c[i] += 0.5 * (dMd[k][i, j] + dMd[j][i, k] - dMd[i][j, k]) * dy[j] * dy[k]
        G = _basis_np(y[1], y[2]) @ coefG
        Q = np.array([0.0, u[0], u[1]])
        Qd = -d_red @ dy
        vfull = Jm @ dy
        Qf = Jm.T @ (-fl * np.tanh(vfull / 0.005))
        return np.linalg.solve(Mred(y), Q + Qd + Qf - c - G)

    rng = np.random.default_rng(7)
    errs = []
    for _ in range(n_trial):
        j1 = rng.uniform(j1_rng[0] + 0.15, j1_rng[1] - 0.15)
        j2 = rng.uniform(j2_rng[0] + 0.3, j2_rng[1] - 0.3)
        u = rng.uniform(-5, 5, 2)
        data.qpos[:] = [2.0, j1, j2, -j2, j2]
        data.qvel[:] = 0
        mj.mj_forward(model, data)
        for _ in range(n_step):
            data.ctrl[:] = u
            mj.mj_step(model, data)
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
    errs = np.array(errs)
    return dict(q_err_max=float(errs.max()), q_err_mean=float(errs.mean()),
                horizon_s=n_step * dt, n=n_trial)


# ══════════ 3. NLP ══════════
def smooth_abs(z):
    return ca.sqrt(z * z + EPS_A * EPS_A)


def smooth_min(a, b):
    return 0.5 * (a + b - ca.sqrt((a - b) ** 2 + EPS_M * EPS_M))


def smooth_pos(z, eps):
    return 0.5 * (z + ca.sqrt(z * z + eps * eps))


def build_layers(twin):
    """측정 법칙층 (p23_v6_runners 동형, 매끈화) — (s1, s2, v1c, v2c, j2) → 심볼릭."""
    law_a, law_b, law_v0 = twin["law"]
    kr = twin["kr"]
    LAW_C = RU.LAW_C
    HIP = RU.HIP
    x_pk = law_b / (2.0 * abs(LAW_C))

    def gate(vv, v0):
        return 1.0 / (1.0 + (vv / v0) ** 2)

    def supp(s2, v2c):
        xa = smooth_min(smooth_abs(s2), x_pk)
        term = smooth_min(law_b * xa + LAW_C * xa * xa, RU.SUPP_CAP)
        return law_a + term * gate(v2c, law_v0)

    def rise(v2c):
        return kr * v2c * (1.0 - gate(v2c, law_v0))

    def hip_layer(s1, s2, v1c):
        xa = smooth_min(smooth_abs(s2), HIP["cap"])   # src='knee'
        out = HIP["a1"] + HIP["b1"] * xa * gate(v1c, HIP["v01"])
        out = out + HIP["k1"] * v1c * (1.0 - gate(v1c, HIP["v01"]))
        return out

    return supp, rise, hip_layer


def ahat_env(v_meas, sign_raw):
    """raw=±35.5 포락선 토크 (sgn(v) tanh 매끈화)."""
    A = C._W["P"].A_PAPER
    Iq = (CF / (GR * KT)) * (sign_raw * RAW_CLIP)
    s = ca.tanh(v_meas / EPS_S)
    return A[0] * GR * KT * Iq - A[1] * GR * ca.fabs(Iq) * Iq - A[2] * s - A[3] * ca.fabs(Iq) * s


def solve_nlp(model, twin, ex, y0, guess, k_c=K_C, b_c=B_C, warm=None):
    coefM = ca.DM(ex["coefM"])
    coefG = ca.DM(ex["coefG"])
    coefF = ca.DM(ex["coefF"])
    d_red = ca.DM(ex["d_red"])
    fl_h = float(ex["fl"][ex["idof"]["hip"]])
    fl_k = float(ex["fl"][ex["idof"]["knee_motor"]])
    R = ex["R"]
    ks, kref, tspr = ex["ks"], ex["kref"], ex["tspr"]
    supp_f, rise_f, hip_f = build_layers(twin)

    p0, p1, p2 = ex["phi_coef"]

    yS = ca.SX.sym("y", 3)
    bF = _basis_ca(yS[1], yS[2])
    mrow = ca.mtimes(bF.T, coefM).T
    M_of = ca.Function("M_of", [yS], [ca.vertcat(
        ca.horzcat(mrow[0], mrow[1], mrow[2]),
        ca.horzcat(mrow[1], mrow[3], mrow[4]),
        ca.horzcat(mrow[2], mrow[4], mrow[5]))])
    G_of = ca.Function("G_of", [yS], [ca.mtimes(bF.T, coefG).T])
    fk = ca.mtimes(bF.T, coefF).T          # [fx, fz_rel, zc_rel]
    FK_of = ca.Function("FK_of", [yS], [fk])
    Jfk_of = ca.Function("Jfk_of", [yS], [ca.jacobian(fk, yS)])  # 3x3 (bz열=0)

    dyS = ca.SX.sym("dy", 3)
    Mdy = ca.mtimes(M_of(yS), dyS)
    Cvec = ca.mtimes(ca.jacobian(Mdy, yS), dyS) \
        - 0.5 * ca.jacobian(ca.mtimes(dyS.T, Mdy), yS).T
    C_of = ca.Function("C_of", [yS, dyS], [Cvec])

    opti = ca.Opti()
    N = N_NODE
    dt = T_HOR / (N - 1)
    Y = opti.variable(3, N)      # bz, j1, j2 (모델 프레임)
    DY = opti.variable(3, N)
    U = opti.variable(2, N)      # s1, s2 (측정 프레임 사후 ahat 토크 [Nm])
    FX = opti.variable(1, N)     # 접선 접촉력 [N]

    def node_forces(k):
        y = Y[:, k]; dy = DY[:, k]
        v1c = -dy[1]; v2c = -dy[2]
        s1 = U[0, k]; s2 = U[1, k]
        fkv = FK_of(y)
        Jf = Jfk_of(y)
        foot_z = y[0] + fkv[1]
        dfoot_z = dy[0] + ca.mtimes(Jf[1, 1:3], dy[1:3])
        delta = R - foot_z
        dpos = smooth_pos(delta, EPS_C)
        ddelta = -dfoot_z
        fz = k_c * dpos + b_c * ddelta * (dpos / (dpos + EPS_C))
        # 층
        sup = supp_f(s2, v2c)
        ris = rise_f(v2c)
        lam1 = hip_f(s1, s2, v1c)
        tspr_tau = ks * (kref - y[2]) * (smooth_abs(s2) / (smooth_abs(s2) + tspr))
        # 일반화력 (모델 프레임 reduced)
        Q = ca.vertcat(0, -(s1 + lam1), -(s2 + sup + ris) + tspr_tau)
        Q = Q - ca.mtimes(d_red, dy)
        Q = Q - ca.vertcat(0, fl_h * ca.tanh(dy[1] / EPS_V), fl_k * ca.tanh(dy[2] / EPS_V))
        # 접촉 (fx는 결정변수, fz는 상태 함수) — J_c^T [fx, fz]
        Jc = ca.vertcat(ca.horzcat(0, Jf[0, 1], Jf[0, 2]),
                        ca.horzcat(1, Jf[1, 1], Jf[1, 2]))
        Q = Q + ca.mtimes(Jc.T, ca.vertcat(FX[0, k], fz))
        return Q, fz, fkv

    acc, fzs, fkvs = [], [], []
    for k in range(N):
        Q, fz, fkv = node_forces(k)
        y = Y[:, k]; dy = DY[:, k]
        ddy = ca.solve(M_of(y), Q - C_of(y, dy) - G_of(y).reshape((3, 1)))
        acc.append(ddy)
        fzs.append(fz)
        fkvs.append(fkv)

    for k in range(N - 1):
        opti.subject_to(Y[:, k + 1] == Y[:, k] + 0.5 * dt * (DY[:, k] + DY[:, k + 1]))
        opti.subject_to(DY[:, k + 1] == DY[:, k] + 0.5 * dt * (acc[k] + acc[k + 1]))

    # ── 경계/경로 제약 ──
    opti.subject_to(Y[:, 0] == y0)
    opti.subject_to(DY[:, 0] == 0)
    j1_lb, j1_ub = guess["j1_rng"]
    j2_lb, j2_ub = guess["j2_rng"]
    opti.subject_to(opti.bounded(j1_lb, Y[1, :], j1_ub))
    opti.subject_to(opti.bounded(j2_lb, Y[2, :], j2_ub))
    opti.subject_to(opti.bounded(-0.05, Y[0, :], 1.5))
    opti.subject_to(opti.bounded(-35.0, DY, 35.0))
    fx00 = float(guess["fx0"]); phi00 = float(guess["phi0"])
    for k in range(N):
        v1c = -DY[1, k]; v2c = -DY[2, k]
        opti.subject_to(U[0, k] <= ahat_env(v1c, +1.0))
        opti.subject_to(U[0, k] >= ahat_env(v1c, -1.0))
        opti.subject_to(U[1, k] <= ahat_env(v2c, +1.0))
        opti.subject_to(U[1, k] >= ahat_env(v2c, -1.0))
        fz = fzs[k]
        opti.subject_to(fz >= -0.5)
        fzp = smooth_pos(fz, 0.5)
        opti.subject_to(FX[0, k] <= MU * fzp + 0.05)
        opti.subject_to(FX[0, k] >= -MU * fzp - 0.05)
        # 구름(no-slip) 밴드 — 이완 게이트 w (φ = p0+p1·j1+p2·j2, 정확 선형)
        w = fzp / (fzp + FZ_W0)
        phi_k = p0 + p1 * Y[1, k] + p2 * Y[2, k]
        slip = fkvs[k][0] - fx00 - R * (phi_k - phi00)
        opti.subject_to(opti.bounded(-SLIP_BAND, w * slip, SLIP_BAND))
        # 침투 상한 (수치 안전)
        opti.subject_to(R - (Y[0, k] + fkvs[k][1]) <= 0.012)
    # 종단: 비행 (발 지상 5mm 이상)
    opti.subject_to(Y[0, N - 1] + fkvs[N - 1][1] >= R + 0.005)

    # ── 목적 (G20 관례) ──
    JfT = Jfk_of(Y[:, N - 1])
    vz_com = DY[0, N - 1] + ca.mtimes(JfT[2, 1:3], DY[1:3, N - 1])
    h_plan = Y[0, N - 1] + smooth_pos(vz_com, 0.01) ** 2 / (2 * GG)
    J_du = sum(ca.sumsqr(U[:, k + 1] - U[:, k]) for k in range(N - 1))
    J_jerk = sum(ca.sumsqr(DY[:, k + 1] - 2 * DY[:, k] + DY[:, k - 1]) for k in range(1, N - 1))
    J_fx = ca.sumsqr(FX) * 1e-4
    opti.minimize(-2000.0 * h_plan + 1.0 * J_du + 20.0 * J_jerk + J_fx)

    # ── 초기 추정 ──
    if warm is not None:
        opti.set_initial(Y, warm["Y"]); opti.set_initial(DY, warm["DY"])
        opti.set_initial(U, warm["U"]); opti.set_initial(FX, warm["FX"])
    else:
        opti.set_initial(Y, guess["Y"]); opti.set_initial(DY, guess["DY"])
        opti.set_initial(U, guess["U"]); opti.set_initial(FX, np.zeros((1, N)))

    opts = {"ipopt.print_level": 3, "ipopt.max_iter": 4000, "ipopt.tol": 1e-4,
            "ipopt.acceptable_tol": 1e-3, "ipopt.mu_strategy": "adaptive",
            "print_time": True}
    opti.solver("ipopt", opts)
    t0 = time.time()
    try:
        sol = opti.solve()
        status = "converged"
    except Exception as e:  # noqa: BLE001
        print(f"IPOPT FAIL: {e}")
        sol = opti.debug
        status = "failed(debug values)"
    wall = time.time() - t0
    st = sol.stats() if hasattr(sol, "stats") else opti.stats()
    res = dict(Y=np.array(sol.value(Y)), DY=np.array(sol.value(DY)),
               U=np.array(sol.value(U)), FX=np.atleast_2d(np.array(sol.value(FX))),
               fz=np.array([float(sol.value(f)) for f in fzs]),
               h_plan=float(sol.value(h_plan)),
               vz_com_T=float(sol.value(vz_com)),
               status=status, iters=int(st.get("iter_count", -1)), wall_s=wall,
               t=np.arange(N) * dt, dt=dt, k_c=k_c, b_c=b_c)
    return res


# ══════════ 4. 초기 추정 구성 (0602 측정 궤적 시드) ══════════
def make_guess(ex, d, k_c):
    R = ex["R"]
    coefF = ex["coefF"]
    t_m = d["t"]
    j1_m = -np.asarray(d["q1"]) - np.pi / 2
    j2_m = -np.asarray(d["q2"])
    s1_m = C._W["P"].J.ahat(C._W["P"].A_PAPER, d["traw1"], d["dq1"])
    s2_m = C._W["P"].J.ahat(C._W["P"].A_PAPER, d["traw2"], d["dq2"])
    N = N_NODE
    tg = np.linspace(0, T_HOR, N)
    j1 = np.interp(np.minimum(tg, t_m[-1]), t_m, j1_m)
    j2 = np.interp(np.minimum(tg, t_m[-1]), t_m, j2_m)
    u1 = np.where(tg <= t_m[-1], np.interp(tg, t_m, s1_m), 0.0)
    u2 = np.where(tg <= t_m[-1], np.interp(tg, t_m, s2_m), 0.0)
    fz_rel = (_basis_np(j1, j2).T @ coefF)[:, 1]
    dst = ex["Mtot"] * GG / k_c
    bz_st = (R - dst) - fz_rel
    # 이지 추정: 기록 끝 시점부터 탄도 (vbz는 스탠스 말 수치미분)
    bz = bz_st.copy()
    vbz = np.gradient(bz_st, tg)
    i_lo = int(np.searchsorted(tg, min(0.255, t_m[-1] - 1e-9)))
    v_lo = float(np.clip(vbz[max(i_lo - 2, 0)], 0, 5))
    for i in range(i_lo, N):
        dtb = tg[i] - tg[i_lo]
        bz[i] = bz_st[i_lo] + v_lo * dtb - 0.5 * GG * dtb ** 2
    Yg = np.vstack([bz, j1, j2])
    DYg = np.vstack([np.gradient(bz, tg), np.gradient(j1, tg), np.gradient(j2, tg)])
    Ug = np.vstack([u1, u2])
    return dict(Y=Yg, DY=DYg, U=Ug, tg=tg)


# ══════════ 5. raw 역변환 (뉴턴 — p14 invert_paper 패턴, 실제 sgn(v)) ══════════
def raw_of(u, v):
    A = C._W["P"].A_PAPER
    kq = CF / (GR * KT)
    x = np.asarray(u, float) / (A[0] * CF)
    s = np.sign(v)
    for _ in range(40):
        Iq = kq * x
        f = A[0] * GR * KT * Iq - A[1] * GR * np.abs(Iq) * Iq - A[2] * s - A[3] * np.abs(Iq) * s - u
        df = A[0] * CF - 2 * A[1] * GR * kq * kq * np.abs(x) - A[3] * kq * s * np.sign(x)
        x = x - f / np.maximum(np.abs(df), 0.05) * np.sign(df)
    return x


# ══════════ 6. 트윈 개루프 검증 롤아웃 (a_full23 스타일, 층 온라인) ══════════
def twin_rollout(model, twin, t_u, s1_u, s2_u, q1_0, q2_0):
    mj = C._W["mj"]
    P = C._W["P"]
    S = P.J._P["S"]
    law_a, law_b, law_v0 = twin["law"]
    kr = twin["kr"]
    sprm = RU.spr_resolve(model, twin["spr"])
    ks, kref, tspr = sprm
    data = mj.MjData(model)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    data.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, data)
    data.qpos[0] = 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS
    data.qvel[:] = 0
    mj.mj_forward(model, data)
    dt = model.opt.timestep
    T_end = t_u[-1]
    N = int((P.J.T_SETTLE + T_end + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz",
                                  "grf", "fx"]}
    for k in range(N):
        tc = tl[k]
        q1c = -data.qpos[1] - np.pi / 2; q2c = -data.qpos[2]
        v1c = -data.qvel[1]; v2c = -data.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([c1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([c2]), np.array([v2c]))[0])
        elif tc <= T_end:
            s1 = float(np.interp(tc, t_u, s1_u))
            s2 = float(np.interp(tc, t_u, s2_u))
        else:
            s1 = s2 = 0.0
        if tc <= T_end:
            sup = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0) \
                + float(RU.rise_term(v2c, kr, law_v0))
            lam1 = RU.hip_supp_scalar(s1, s2, v1c)
            h = RU.h_load(abs(s2), tspr)
            tql = ks * (kref - float(data.qpos[iq_k])) * h
        else:
            sup = law_a          # a_full23 규약: 기록 끝 이후 상수 성분만
            lam1 = RU.HIP["a1"]
            tql = 0.0            # h=0 (무명령 = 무부하)
        data.ctrl[:] = [-(s1 + lam1), -(s2 + sup)]
        data.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, data)
        except Exception:
            return None
        if abs(data.qpos[0]) > 5 or not np.isfinite(data.qpos).all():
            return None
        L["q1"][k] = -data.qpos[1] - np.pi / 2; L["q2"][k] = -data.qpos[2]
        L["dq1"][k] = -data.qvel[1]; L["dq2"][k] = -data.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = data.qpos[0]
        L["fx"][k] = float(data.geom_xpos[fg][0])
        L["grf"][k] = RU._grf_z(model, data)
    L["t"] = tl
    return L


# ══════════ main ══════════
def main():
    t00 = time.time()
    print("═══ P25 Phase B — analytic NLP (CasADi/IPOPT) on p24a twin ═══", flush=True)
    model, twin = init_twin()
    mj = C._W["mj"]
    P = C._W["P"]
    print(f"[init {time.time()-t00:.0f}s] p24a 트윈 빌드 완료  law={twin['law']}", flush=True)

    # 시작 자세 + 방문 범위 (무변속 점프 세션 전체)
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    d0 = None
    q1_all, q2_all = [], []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if is_cvt:
            continue
        q1_all.append(np.asarray(d["q1"]))
        q2_all.append(np.asarray(d["q2"]))
        if (ds, sub) == START_TRIAL:
            d0 = d
    assert d0 is not None, f"시작 trial {START_TRIAL} 미발견"
    q1_all = np.concatenate(q1_all); q2_all = np.concatenate(q2_all)
    sp1 = q1_all.max() - q1_all.min(); sp2 = q2_all.max() - q2_all.min()
    q1_rng = (q1_all.min() - 0.1 * sp1, q1_all.max() + 0.1 * sp1)
    q2_rng = (q2_all.min() - 0.1 * sp2, q2_all.max() + 0.1 * sp2)
    # 모델 프레임 (j1=-q1-π/2 감소사상, j2=-q2)
    j1_rng = (-q1_rng[1] - np.pi / 2, -q1_rng[0] - np.pi / 2)
    j2_rng = (-q2_rng[1], -q2_rng[0])
    print(f"관절 케이지 (+10%): q1 [{q1_rng[0]:.3f},{q1_rng[1]:.3f}] "
          f"q2 [{q2_rng[0]:.3f},{q2_rng[1]:.3f}]", flush=True)

    # 등가 EoM 추출 + 검증
    ex = extract_reduced(model, twin, j1_rng, j2_rng)
    print(f"[EoM] 기저 적합 rel resid: M={max(ex['resids']['M']):.1e} "
          f"G={max(ex['resids']['G']):.1e} F={max(ex['resids']['F']):.1e}", flush=True)
    ver = verify_reduced(model, ex, j1_rng, j2_rng)
    print(f"[EoM 검증] 공중 개루프 {ver['horizon_s']*1000:.0f}ms×{ver['n']}: "
          f"q err max {ver['q_err_max']:.2e} rad", flush=True)

    # 시작 상태
    q1_0 = float(d0["q1"][0]); q2_0 = float(d0["q2"][0])
    j1_0, j2_0 = -q1_0 - np.pi / 2, -q2_0
    fk0 = (_basis_np(np.array([j1_0]), np.array([j2_0])).T @ ex["coefF"])[0]
    p0, p1, p2 = ex["phi_coef"]
    phi0 = p0 + p1 * j1_0 + p2 * j2_0
    dst = ex["Mtot"] * GG / K_C
    bz0 = (ex["R"] - dst) - fk0[1]
    y0 = np.array([bz0, j1_0, j2_0])
    guess = make_guess(ex, d0, K_C)
    guess.update(j1_rng=j1_rng, j2_rng=j2_rng, fx0=fk0[0], phi0=phi0)
    guess["Y"][:, 0] = y0
    print(f"시작: {START_TRIAL} q=({q1_0:+.4f},{q2_0:+.4f}) bz0={bz0:.4f} "
          f"(δ_st={dst*1000:.2f}mm)", flush=True)

    # ── NLP 본해 (k_c=1.3e5, G20 레시피) ──
    res = solve_nlp(model, twin, ex, y0, guess, k_c=K_C, b_c=B_C)
    print(f"[NLP] status={res['status']} iters={res['iters']} "
          f"wall={res['wall_s']:.1f}s  h_plan={res['h_plan']:.4f} m "
          f"(vz_com(T)={res['vz_com_T']:.3f})", flush=True)

    # ── 트윈 개루프 검증 ──
    tt = res["t"]
    q1_pl = -res["Y"][1] - np.pi / 2
    q2_pl = -res["Y"][2]
    dq1_pl = -res["DY"][1]
    dq2_pl = -res["DY"][2]
    L = twin_rollout(model, twin, tt, res["U"][0], res["U"][1], q1_0, q2_0)
    assert L is not None, "트윈 롤아웃 발산"
    h_twin = float(L["bz"][L["t"] > 0].max())
    gap = h_twin / res["h_plan"] - 1.0
    print(f"[검증] h_plan={res['h_plan']:.4f}  h_twin={h_twin:.4f}  "
          f"gap={100*gap:+.1f}%", flush=True)
    # 스탠스 궤적 교차 RMSE (플랜 vs 트윈)
    mstance = tt <= 0.35
    f = lambda k: np.interp(tt, L["t"], L[k])
    rq = float(np.sqrt(np.mean((f("q1") - q1_pl)[mstance] ** 2
                               + (f("q2") - q2_pl)[mstance] ** 2)))
    print(f"  플랜-트윈 스탠스 q RMSE = {rq:.4f} rad", flush=True)

    # ── 감도: k_c = p24a 재실측 시컨트 (웜스타트 재해석) ──
    dst_alt = ex["Mtot"] * GG / K_C_ALT
    y0_alt = np.array([(ex["R"] - dst_alt) - fk0[1], j1_0, j2_0])
    res_alt = solve_nlp(model, twin, ex, y0_alt, guess, k_c=K_C_ALT, b_c=90.0,
                        warm=dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"]))
    L_alt = twin_rollout(model, twin, res_alt["t"], res_alt["U"][0], res_alt["U"][1],
                         q1_0, q2_0)
    h_twin_alt = float(L_alt["bz"][L_alt["t"] > 0].max()) if L_alt is not None else float("nan")
    gap_alt = h_twin_alt / res_alt["h_plan"] - 1.0
    print(f"[감도 k_c={K_C_ALT:.2e}] h_plan={res_alt['h_plan']:.4f} "
          f"h_twin={h_twin_alt:.4f} gap={100*gap_alt:+.1f}%", flush=True)

    # ── 피크/한계 보고 ──
    v1_pl = dq1_pl; v2_pl = dq2_pl
    raw1 = raw_of(res["U"][0], np.where(np.abs(v1_pl) < 1e-9, 1e-9, v1_pl))
    raw2 = raw_of(res["U"][1], np.where(np.abs(v2_pl) < 1e-9, 1e-9, v2_pl))
    peaks = dict(
        s1_absmax=float(np.abs(res["U"][0]).max()),
        s2_absmax=float(np.abs(res["U"][1]).max()),
        raw1_absmax=float(np.abs(raw1).max()),
        raw2_absmax=float(np.abs(raw2).max()),
        dq1_absmax=float(np.abs(v1_pl).max()),
        dq2_absmax=float(np.abs(v2_pl).max()),
        grf_max=float(res["fz"].max()),
        grf_twin_max=float(L["grf"].max()),
        liftoff_plan_s=float(tt[np.argmax(res["fz"] < 0.5)]) if (res["fz"] < 0.5).any() else None,
    )
    print(f"피크: |s1|={peaks['s1_absmax']:.1f} |s2|={peaks['s2_absmax']:.1f} Nm  "
          f"|raw|=({peaks['raw1_absmax']:.1f},{peaks['raw2_absmax']:.1f})/35.5  "
          f"|dq|=({peaks['dq1_absmax']:.1f},{peaks['dq2_absmax']:.1f}) rad/s  "
          f"GRF={peaks['grf_max']:.0f}N", flush=True)

    # ── 저장 (Phase A 스키마) ──
    np.savez(OUT_NPZ,
             t=tt, q=np.vstack([q1_pl, q2_pl]).T, dq=np.vstack([dq1_pl, dq2_pl]).T,
             tau_cmd_nm=res["U"].T, tau_cmd_raw=np.vstack([raw1, raw2]).T,
             bz=res["Y"][0], q_des=np.vstack([q1_pl, q2_pl]).T,
             dq_des=np.vstack([dq1_pl, dq2_pl]).T,
             fz_plan=res["fz"], fx_plan=res["FX"][0],
             t_twin=L["t"], bz_twin=L["bz"],
             q_twin=np.vstack([L["q1"], L["q2"]]).T,
             dq_twin=np.vstack([L["dq1"], L["dq2"]]).T,
             grf_twin=L["grf"], footx_twin=L["fx"])
    summary = dict(
        PHASE="p25_B_analytic_NLP",
        twin="fourbar_p24a_candidate.json",
        nlp=dict(N=N_NODE, dt=res["dt"], horizon_s=T_HOR, k_c=K_C, b_c=B_C, mu=MU,
                 transcription="trapezoidal direct collocation (G20 관례)",
                 objective="bz(T) + max(vz_com,0)^2/2g (G20 'Base via CoM v_z')",
                 eps=dict(abs_Nm=EPS_A, min=EPS_M, fric_v=EPS_V, sgn_v=EPS_S,
                          contact_m=EPS_C, slip_band_m=SLIP_BAND),
                 supply="conservative envelope u∈[ahat(-35.5,v), ahat(+35.5,v)], "
                        "tanh(v/0.5) smoothed sgn",
                 start=dict(trial="/".join(START_TRIAL), q1_0=q1_0, q2_0=q2_0,
                            bz0=float(bz0), delta_static_mm=float(dst * 1e3)),
                 joint_cage=dict(q1=list(map(float, q1_rng)), q2=list(map(float, q2_rng)),
                                 note="무변속 점프 세션 방문범위 +10% span"),
                 status=res["status"], iters=res["iters"], wall_s=res["wall_s"]),
        eom=dict(method="numeric fit of reduced M/G/FK on p24a MuJoCo model "
                        "(parallelogram exact linear map [bz,j1,j2,-j2,j2])",
                 basis_rel_resid={k: max(v) for k, v in ex["resids"].items()},
                 air_rollout_check=ver),
        results=dict(h_plan=res["h_plan"], h_twin_rollout=h_twin, gap_pct=100 * gap,
                     plan_twin_stance_qRMSE=rq, vz_com_T=res["vz_com_T"]),
        sensitivity_kc=dict(k_c=K_C_ALT, b_c=90.0, h_plan=res_alt["h_plan"],
                            h_twin=h_twin_alt, gap_pct=100 * gap_alt,
                            status=res_alt["status"], iters=res_alt["iters"]),
        peaks=peaks,
        references=dict(G20_realized_m=G20_REF, real_best_0602_m=0.98,
                        modeA_replay_this_trial_m=0.924),
        k_eq_p24a=dict(secant=4.43e4, local_jump_loads=1.1e5,
                       note="하중스윕 0.5~8g — solimp 비선형 (저부하 연화); "
                            "G20 1.3e5는 점프 하중대 국소 기울기와 근접"),
        caveats=[
            "frictionloss tanh 매끈화 — MuJoCo 정확 stiction과 저속 교차 시 차이",
            "접촉: NLP 선형 스프링-댐퍼 vs 트윈 solimp 비선형 임피던스 (감도행 참조)",
            "구름 밴드 3mm 이완 — 트윈 미소슬립 1.3mm rms의 관측 기반",
            "목적은 vz_com 탄도 외삽 — 비행 중 관절 재배치의 bz 편차는 트윈 롤아웃으로 검증",
            "sgn(v) tanh(v/0.5) 매끈화 — |v|<1 rad/s 대역 마찰항 부호 블렌드",
        ],
    )
    safe.atomic_json_write(OUT_JSON, summary)
    print(f"saved {OUT_JSON.name}, {OUT_NPZ.name}", flush=True)

    # ── 그림 ──
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    ax = axs[0, 0]
    ax.plot(tt, res["Y"][0], label="plan bz")
    ln = ax.plot(L["t"], L["bz"], "--", label="twin rollout bz")
    ax.axhline(res["h_plan"], ls=":", lw=1, label=f"h_plan {res['h_plan']:.3f}")
    ax.axhline(h_twin, ls=":", lw=1, color=ln[0].get_color(),
               label=f"h_twin {h_twin:.3f}")
    ax.set_title("Base height"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[0, 1]
    l1 = ax.plot(tt, q1_pl, label="plan q1")
    l2 = ax.plot(tt, q2_pl, label="plan q2")
    ax.plot(L["t"], L["q1"], "--", color=l1[0].get_color(), label="twin q1")
    ax.plot(L["t"], L["q2"], "--", color=l2[0].get_color(), label="twin q2")
    ax.set_title("Joint angles (measured frame)"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[0, 2]
    l1 = ax.plot(tt, dq1_pl, label="plan dq1")
    l2 = ax.plot(tt, dq2_pl, label="plan dq2")
    ax.plot(L["t"], L["dq1"], "--", color=l1[0].get_color())
    ax.plot(L["t"], L["dq2"], "--", color=l2[0].get_color())
    ax.set_title("Joint velocities"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 0]
    ax.plot(tt, res["U"][0], label="s1 (hip)")
    ax.plot(tt, res["U"][1], label="s2 (knee)")
    ax.set_title("Command torque u=s [Nm]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 1]
    ax.plot(tt, raw1, label="raw1")
    ax.plot(tt, raw2, label="raw2")
    ax.axhline(RAW_CLIP, ls=":", lw=1); ax.axhline(-RAW_CLIP, ls=":", lw=1)
    ax.set_title("raw command (|.|<=35.5)"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 2]
    ax.plot(tt, res["fz"], label="plan Fz")
    ax.plot(L["t"], L["grf"], "--", label="twin GRF")
    ax.set_xlim(-0.05, 0.45)
    ax.set_title("Contact normal force [N]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.suptitle(f"P25-B analytic NLP (p24a, k_c={K_C:.1e}) — "
                 f"h_plan {res['h_plan']:.3f} m / twin {h_twin:.3f} m "
                 f"({100*gap:+.1f}%) / G20 ref {G20_REF}")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=110)
    print(f"saved {OUT_PNG.name}  [{(time.time()-t00)/60:.1f} min total]", flush=True)


if __name__ == "__main__":
    main()
