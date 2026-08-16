# -*- coding: utf-8 -*-
"""P25-task0 캠페인 — no_cvt: p25_b NLP를 AVT task0 제약 블록으로 재최적화.

사용자 지시 (07-18): 제약을 AVT LEG/optimization_tasks/task0_vertjump_no_cvt.py와
동일하게. 플랜트/전사/목적은 p25_b_nlp (p24a 트윈 등가 3-DOF EoM + 법칙층 심볼릭,
trapezoidal collocation, G20 'Base via CoM v_z' 목적) 그대로 — 제약 블록만
task0 규약(t0_spec 포팅본)으로 교체.

이식 제약 (t0_spec = task0 265~318행):
 1) |τ̂(축 Nm)| ≤ 15 — U(=â 심볼릭)에 직접 박스. raw 공급 박스는 25.5810 유지
    (env P25_CLIP_RAW=25.5810 → â 운동방향 가지 정확히 15.00 Nm — t18=31.1771/18Nm
    과 동일 규약. 제동 가지는 마찰 가산으로 15 초과 가능 → 박스가 잘라냄).
 2) T-N 포락선: |dq_j| ≤ −0.731019·|â_j| + 48.476878 (관절별).
    fabs는 sqrt(x²+ε²) 매끈화 — 양변 모두 보수측 (sqrt≥|·|, lim은 작아짐).
 3) |dq| ≤ 50 — task0은 V 전체(dz 포함)에 적용 → 동일하게 DY 전체.
 4) q1 ∈ [−1.2566, −0.2967], q2 ∈ [−2.5482, −0.6283] (측정 규약 = AVT 규약, 전 노드
    — 하드웨어 각도 한계라 비행 중에도 적용, t0_spec.audit 정의역과 일치).
 5) 시작 자세 자유(박스 내) + 정지(DY(0)=0) + 정적 평형: 발 침투 = M·g/k_c
    ⇔ Fz(0)=M·g (task0 soft 모델의 foot_z0 == −delta_static 과 동일 규약).
    시작 자유화에 따라 구름밴드 기준점(fx0, φ0)을 시작 노드의 심볼릭 함수로 일반화.
 6) 스탠스 ≤ 0.3 s — 고정 그리드(T=0.6)이므로 기본은 이지 시각 감사만.
    감사 초과 시에만 t ≥ 0.3 비행 강제(발 클리어런스) 제약을 추가해 웜스타트 재해.

warm-start: p25_b_traj_t18.npz (t18 해)를 새 제약 박스(τ15/q박스/T-N/dq50/정적시작)로 사영.
트윈 교차검증: 기존 절차 그대로 — R19.CLIP=25.5810 동기화(env로 자동), 개루프 â replay.

산출: t0nc_nlp.npz(p25_b_traj 스키마 + h_plan/h_twin/raw_clip) /
      t0nc_nlp_audit.json(t0_spec.audit 플랜·트윈 + 스탠스·T-N 활성 감사) /
      t0nc_nlp_summary.png
실행: PYTHONIOENCODING=utf-8 python t0nc_nlp.py  (읽기 전용, 원본 덮어쓰기·커밋 없음)
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

import p25_b_nlp as B   # env 반영: B.RAW_CLIP=25.5810 + R19.CLIP 동기화 + 하네스 경로
import t0_spec as T0
import safe

import casadi as ca
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TAU_LIM = 15.0
T18_NPZ = G22 / "p25_deploy" / "p25_b_traj_t18.npz"
T18_H_PLAN = 1.0703          # t18 자기모델 h (참조)
T18_H_TWIN = 1.0273
# 모델 프레임 박스 (j1 = -q1 - π/2 감소사상, j2 = -q2)
J1_LB, J1_UB = -T0.Q1_UB - np.pi / 2, -T0.Q1_LB - np.pi / 2
J2_LB, J2_UB = -T0.Q2_UB, -T0.Q2_LB
EPS_TN = 0.05                # [rad/s] T-N 좌변 |dq| 매끈화 (보수측)
TN_ACT_TOL = 0.5             # [rad/s] "T-N 활성" 판정 여유
OUT_NPZ = HERE / "t0nc_nlp.npz"
OUT_JSON = HERE / "t0nc_nlp_audit.json"
OUT_PNG = HERE / "t0nc_nlp_summary.png"


# ══════════ NLP (p25_b solve_nlp 동형 — 제약 블록만 task0) ══════════
def solve_t0(model, twin, ex, warm, k_c=B.K_C, b_c=B.B_C, enforce_tst=False):
    coefM = ca.DM(ex["coefM"])
    coefG = ca.DM(ex["coefG"])
    coefF = ca.DM(ex["coefF"])
    d_red = ca.DM(ex["d_red"])
    fl_h = float(ex["fl"][ex["idof"]["hip"]])
    fl_k = float(ex["fl"][ex["idof"]["knee_motor"]])
    R = ex["R"]
    ks, kref, tspr = ex["ks"], ex["kref"], ex["tspr"]
    supp_f, rise_f, hip_f = B.build_layers(twin)
    p0, p1, p2 = ex["phi_coef"]

    yS = ca.SX.sym("y", 3)
    bF = B._basis_ca(yS[1], yS[2])
    mrow = ca.mtimes(bF.T, coefM).T
    M_of = ca.Function("M_of", [yS], [ca.vertcat(
        ca.horzcat(mrow[0], mrow[1], mrow[2]),
        ca.horzcat(mrow[1], mrow[3], mrow[4]),
        ca.horzcat(mrow[2], mrow[4], mrow[5]))])
    G_of = ca.Function("G_of", [yS], [ca.mtimes(bF.T, coefG).T])
    fk = ca.mtimes(bF.T, coefF).T          # [fx, fz_rel, zc_rel]
    FK_of = ca.Function("FK_of", [yS], [fk])
    Jfk_of = ca.Function("Jfk_of", [yS], [ca.jacobian(fk, yS)])

    dyS = ca.SX.sym("dy", 3)
    Mdy = ca.mtimes(M_of(yS), dyS)
    Cvec = ca.mtimes(ca.jacobian(Mdy, yS), dyS) \
        - 0.5 * ca.jacobian(ca.mtimes(dyS.T, Mdy), yS).T
    C_of = ca.Function("C_of", [yS, dyS], [Cvec])

    opti = ca.Opti()
    N = B.N_NODE
    dt = B.T_HOR / (N - 1)
    tg = np.arange(N) * dt
    Y = opti.variable(3, N)      # bz, j1, j2 (모델 프레임)
    DY = opti.variable(3, N)
    U = opti.variable(2, N)      # s1, s2 = â (측정 프레임 사후 ahat 토크 [Nm])
    FX = opti.variable(1, N)

    def node_forces(k):
        y = Y[:, k]; dy = DY[:, k]
        v1c = -dy[1]; v2c = -dy[2]
        s1 = U[0, k]; s2 = U[1, k]
        fkv = FK_of(y)
        Jf = Jfk_of(y)
        foot_z = y[0] + fkv[1]
        dfoot_z = dy[0] + ca.mtimes(Jf[1, 1:3], dy[1:3])
        delta = R - foot_z
        dpos = B.smooth_pos(delta, B.EPS_C)
        ddelta = -dfoot_z
        fz = k_c * dpos + b_c * ddelta * (dpos / (dpos + B.EPS_C))
        sup = supp_f(s2, v2c)
        ris = rise_f(v2c)
        lam1 = hip_f(s1, s2, v1c)
        tspr_tau = ks * (kref - y[2]) * (B.smooth_abs(s2) / (B.smooth_abs(s2) + tspr))
        Q = ca.vertcat(0, -(s1 + lam1), -(s2 + sup + ris) + tspr_tau)
        Q = Q - ca.mtimes(d_red, dy)
        Q = Q - ca.vertcat(0, fl_h * ca.tanh(dy[1] / B.EPS_V),
                           fl_k * ca.tanh(dy[2] / B.EPS_V))
        Jc = ca.vertcat(ca.horzcat(0, Jf[0, 1], Jf[0, 2]),
                        ca.horzcat(1, Jf[1, 1], Jf[1, 2]))
        Q = Q + ca.mtimes(Jc.T, ca.vertcat(FX[0, k], fz))
        return Q, fz, fkv

    acc, fzs, fkvs = [], [], []
    for k in range(N):
        Qk, fz, fkv = node_forces(k)
        y = Y[:, k]; dy = DY[:, k]
        ddy = ca.solve(M_of(y), Qk - C_of(y, dy) - G_of(y).reshape((3, 1)))
        acc.append(ddy)
        fzs.append(fz)
        fkvs.append(fkv)

    for k in range(N - 1):
        opti.subject_to(Y[:, k + 1] == Y[:, k] + 0.5 * dt * (DY[:, k] + DY[:, k + 1]))
        opti.subject_to(DY[:, k + 1] == DY[:, k] + 0.5 * dt * (acc[k] + acc[k + 1]))

    # ── task0 제약 블록 ──
    dst = ex["Mtot"] * B.GG / k_c
    opti.subject_to(DY[:, 0] == 0)                          # 5) 정지
    opti.subject_to(Y[0, 0] + fkvs[0][1] == R - dst)        # 5) 정적 평형 Fz(0)=M·g
    opti.subject_to(opti.bounded(J1_LB, Y[1, :], J1_UB))    # 4) q1 박스
    opti.subject_to(opti.bounded(J2_LB, Y[2, :], J2_UB))    # 4) q2 박스
    opti.subject_to(opti.bounded(-0.05, Y[0, :], 1.5))
    opti.subject_to(opti.bounded(-T0.DQ_LIM, DY, T0.DQ_LIM))  # 3) |dq| ≤ 50 (dz 포함)
    opti.subject_to(opti.bounded(-TAU_LIM, U, TAU_LIM))       # 1) |â| ≤ 15
    fx0s = fkvs[0][0]                                       # 자유 시작 → 심볼릭 기준점
    phi0s = p0 + p1 * Y[1, 0] + p2 * Y[2, 0]
    for k in range(N):
        v1c = -DY[1, k]; v2c = -DY[2, k]
        # raw 공급 박스 25.5810 (유지)
        opti.subject_to(U[0, k] <= B.ahat_env(v1c, +1.0))
        opti.subject_to(U[0, k] >= B.ahat_env(v1c, -1.0))
        opti.subject_to(U[1, k] <= B.ahat_env(v2c, +1.0))
        opti.subject_to(U[1, k] >= B.ahat_env(v2c, -1.0))
        # 2) T-N 포락선 (관절별, 매끈화 보수측)
        for j in (0, 1):
            lim = T0.TN_COEF * B.smooth_abs(U[j, k]) + T0.TN_OFF
            opti.subject_to(ca.sqrt(DY[j + 1, k] ** 2 + EPS_TN ** 2) <= lim)
        # 접촉 (p25_b 그대로 — 플랜트측)
        fz = fzs[k]
        opti.subject_to(fz >= -0.5)
        fzp = B.smooth_pos(fz, 0.5)
        opti.subject_to(FX[0, k] <= B.MU * fzp + 0.05)
        opti.subject_to(FX[0, k] >= -B.MU * fzp - 0.05)
        w = fzp / (fzp + B.FZ_W0)
        phi_k = p0 + p1 * Y[1, k] + p2 * Y[2, k]
        slip = fkvs[k][0] - fx0s - R * (phi_k - phi0s)
        opti.subject_to(opti.bounded(-B.SLIP_BAND, w * slip, B.SLIP_BAND))
        opti.subject_to(R - (Y[0, k] + fkvs[k][1]) <= 0.012)
        # 6) 감사 실패 시 2차해 전용: t ≥ 0.3 비행 강제
        if enforce_tst and tg[k] >= T0.T_ST_MAX:
            opti.subject_to(Y[0, k] + fkvs[k][1] >= R)
    opti.subject_to(Y[0, N - 1] + fkvs[N - 1][1] >= R + 0.005)

    # ── 목적 (p25_b 그대로 = G20 관례) ──
    JfT = Jfk_of(Y[:, N - 1])
    vz_com = DY[0, N - 1] + ca.mtimes(JfT[2, 1:3], DY[1:3, N - 1])
    h_plan = Y[0, N - 1] + B.smooth_pos(vz_com, 0.01) ** 2 / (2 * B.GG)
    J_du = sum(ca.sumsqr(U[:, k + 1] - U[:, k]) for k in range(N - 1))
    J_jerk = sum(ca.sumsqr(DY[:, k + 1] - 2 * DY[:, k] + DY[:, k - 1])
                 for k in range(1, N - 1))
    opti.minimize(-2000.0 * h_plan + 1.0 * J_du + 20.0 * J_jerk + ca.sumsqr(FX) * 1e-4)

    opti.set_initial(Y, warm["Y"]); opti.set_initial(DY, warm["DY"])
    opti.set_initial(U, warm["U"]); opti.set_initial(FX, warm["FX"])
    opts = {"ipopt.print_level": 3, "ipopt.max_iter": 4000, "ipopt.tol": 1e-4,
            "ipopt.acceptable_tol": 1e-3, "ipopt.mu_strategy": "adaptive",
            "print_time": True}
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
                fz=np.array([float(sol.value(f)) for f in fzs]),
                h_plan=float(sol.value(h_plan)), vz_com_T=float(sol.value(vz_com)),
                status=status, iters=int(st.get("iter_count", -1)),
                wall_s=time.time() - t0c, t=tg, dt=dt, k_c=k_c, b_c=b_c,
                enforce_tst=enforce_tst)


# ══════════ warm-start: t18 해를 task0 박스로 사영 ══════════
def warm_t18(ex, k_c):
    w = B.warm_from_base(T18_NPZ)          # ahat 포락선(25.5810) 사영 포함
    w["U"] = np.clip(w["U"], -TAU_LIM, TAU_LIM)
    w["Y"][1] = np.clip(w["Y"][1], J1_LB, J1_UB)
    w["Y"][2] = np.clip(w["Y"][2], J2_LB, J2_UB)
    w["DY"] = np.clip(w["DY"], -T0.DQ_LIM, T0.DQ_LIM)
    for j in (1, 2):                       # T-N 사영 (dq를 포락선 안으로)
        lim = T0.TN_COEF * np.abs(w["U"][j - 1]) + T0.TN_OFF
        w["DY"][j] = np.clip(w["DY"][j], -lim, lim)
    # 정지 + 정적 평형 시드
    w["DY"][:, 0] = 0.0
    fk0 = (B._basis_np(w["Y"][1, :1], w["Y"][2, :1]).T @ ex["coefF"])[0]
    w["Y"][0, 0] = (ex["R"] - ex["Mtot"] * B.GG / k_c) - fk0[1]
    return w


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


# ══════════ main ══════════
def main():
    t00 = time.time()
    print("═══ P25-task0 no_cvt — task0 제약 블록 NLP (p24a twin) ═══", flush=True)
    assert abs(B.RAW_CLIP - T0.RAW15) < 1e-9, B.RAW_CLIP

    model, twin = B.init_twin()
    ah_mot = float(B.ahat_env_np(10.0, +1.0))   # 운동방향 가지 (v≫ε)
    assert abs(ah_mot - 15.0) < 0.02, f"RAW15 검증 실패: â_motoring={ah_mot}"
    print(f"[검증] raw={T0.RAW15} → â_motoring={ah_mot:.4f} Nm (=15 규약)  "
          f"R19.CLIP={B.R19.CLIP}", flush=True)
    print(f"[init {time.time()-t00:.0f}s] p24a 트윈 빌드 완료  law={twin['law']}", flush=True)

    j1_rng = (J1_LB, J1_UB)
    j2_rng = (J2_LB, J2_UB)
    print(f"task0 관절 박스 (측정 규약): q1 [{T0.Q1_LB},{T0.Q1_UB}] "
          f"q2 [{T0.Q2_LB},{T0.Q2_UB}]", flush=True)

    ex = B.extract_reduced(model, twin, j1_rng, j2_rng)
    print(f"[EoM] 기저 적합 rel resid: M={max(ex['resids']['M']):.1e} "
          f"G={max(ex['resids']['G']):.1e} F={max(ex['resids']['F']):.1e}", flush=True)
    ver = B.verify_reduced(model, ex, j1_rng, j2_rng)
    print(f"[EoM 검증] 공중 개루프 {ver['horizon_s']*1000:.0f}ms×{ver['n']}: "
          f"q err max {ver['q_err_max']:.2e} rad", flush=True)

    warm = warm_t18(ex, B.K_C)
    print(f"[warm] t18 해 사영 시드: q(0)=({-warm['Y'][1,0]-np.pi/2:+.4f},"
          f"{-warm['Y'][2,0]:+.4f}) bz0={warm['Y'][0,0]:.4f}", flush=True)

    res = solve_t0(model, twin, ex, warm)
    print(f"[NLP] status={res['status']} iters={res['iters']} "
          f"wall={res['wall_s']:.1f}s  h_plan={res['h_plan']:.4f} m "
          f"(vz_com(T)={res['vz_com_T']:.3f})", flush=True)

    # 6) 스탠스 시각 감사 → 초과 시 2차해
    tt = res["t"]
    lift_plan = float(tt[np.argmax(res["fz"] < 0.5)]) if (res["fz"] < 0.5).any() else None
    if lift_plan is None or lift_plan > T0.T_ST_MAX + 1e-9:
        print(f"[스탠스 감사] 이지 {lift_plan} s > {T0.T_ST_MAX} — "
              f"t≥0.3 비행 강제 재해 (웜스타트)", flush=True)
        res = solve_t0(model, twin, ex,
                       dict(Y=res["Y"], DY=res["DY"], U=res["U"], FX=res["FX"]),
                       enforce_tst=True)
        tt = res["t"]
        lift_plan = float(tt[np.argmax(res["fz"] < 0.5)]) if (res["fz"] < 0.5).any() else None
        print(f"[NLP 2차] status={res['status']} iters={res['iters']} "
              f"h_plan={res['h_plan']:.4f}  이지={lift_plan}", flush=True)

    # 측정 프레임 플랜
    q1_pl = -res["Y"][1] - np.pi / 2
    q2_pl = -res["Y"][2]
    dq1_pl = -res["DY"][1]
    dq2_pl = -res["DY"][2]
    q1_0 = float(q1_pl[0]); q2_0 = float(q2_pl[0])
    print(f"시작 자세 (자유해): q=({q1_0:+.4f},{q2_0:+.4f})  "
          f"bz0={res['Y'][0,0]:.4f}", flush=True)

    # 플랜 자기 감사 (제약 만족 확인)
    L_plan = dict(t=tt, q1=q1_pl, q2=q2_pl, dq1=dq1_pl, dq2=dq2_pl,
                  sh1=res["U"][0], sh2=res["U"][1])
    A_plan = T0.audit(L_plan)
    print(f"[감사·플랜] pass={A_plan['pass']}  " +
          "  ".join(f"{k}={v:+.4f}" for k, v in A_plan.items() if k != "pass"),
          flush=True)

    # ── 트윈 개루프 교차검증 (기존 절차, R19.CLIP=25.5810) ──
    L = B.twin_rollout(model, twin, tt, res["U"][0], res["U"][1], q1_0, q2_0)
    assert L is not None, "트윈 롤아웃 발산"
    h_twin = float(L["bz"][L["t"] > 0].max())
    gap = h_twin / res["h_plan"] - 1.0
    print(f"[검증] h_plan={res['h_plan']:.4f}  h_twin={h_twin:.4f}  "
          f"gap={100*gap:+.1f}%", flush=True)
    mstance = tt <= 0.35
    f = lambda k: np.interp(tt, L["t"], L[k])  # noqa: E731
    rq = float(np.sqrt(np.mean((f("q1") - q1_pl)[mstance] ** 2
                               + (f("q2") - q2_pl)[mstance] ** 2)))
    print(f"  플랜-트윈 스탠스 q RMSE = {rq:.4f} rad", flush=True)

    A_twin = T0.audit(L)
    print(f"[감사·트윈] pass={A_twin['pass']}  " +
          "  ".join(f"{k}={v:+.4f}" for k, v in A_twin.items() if k != "pass"),
          flush=True)
    mpos = L["t"] > 0
    gl = L["grf"][mpos] < 0.5
    lift_twin = float(L["t"][mpos][np.argmax(gl)]) if gl.any() else None

    # T-N 활성 비율
    tn_pl = tn_report(res["U"], dq1_pl, dq2_pl, res["fz"])
    m06 = (L["t"] >= 0) & (L["t"] <= B.T_HOR)
    tn_tw = tn_report(np.vstack([L["sh1"][m06], L["sh2"][m06]]),
                      L["dq1"][m06], L["dq2"][m06], L["grf"][m06])
    print(f"[T-N 활성·플랜] 스탠스 hip {tn_pl['hip_active_pct_stance']:.0f}% / "
          f"knee {tn_pl['knee_active_pct_stance']:.0f}%  "
          f"(min margin {tn_pl['hip_min_margin_rads']:+.2f}/"
          f"{tn_pl['knee_min_margin_rads']:+.2f} rad/s)", flush=True)

    # raw 역변환 + 피크
    v1g = np.where(np.abs(dq1_pl) < 1e-9, 1e-9, dq1_pl)
    v2g = np.where(np.abs(dq2_pl) < 1e-9, 1e-9, dq2_pl)
    raw1 = B.raw_of(res["U"][0], v1g)
    raw2 = B.raw_of(res["U"][1], v2g)
    stance_n = res["fz"] >= 0.5
    peaks = dict(
        s1_absmax=float(np.abs(res["U"][0]).max()),
        s2_absmax=float(np.abs(res["U"][1]).max()),
        raw1_absmax=float(np.abs(raw1).max()),
        raw2_absmax=float(np.abs(raw2).max()),
        dq1_absmax=float(np.abs(dq1_pl).max()),
        dq2_absmax=float(np.abs(dq2_pl).max()),
        grf_max=float(res["fz"].max()),
        grf_twin_max=float(L["grf"].max()),
        ceiling_ride_pct_stance=[
            float(np.mean(np.abs(res["U"][0])[stance_n] >= TAU_LIM - 0.01) * 100),
            float(np.mean(np.abs(res["U"][1])[stance_n] >= TAU_LIM - 0.01) * 100)],
        raw_le_clip_ok=bool(max(np.abs(raw1).max(), np.abs(raw2).max())
                            <= B.RAW_CLIP + 0.005))
    print(f"피크: |s|=({peaks['s1_absmax']:.2f},{peaks['s2_absmax']:.2f})/15 Nm  "
          f"|raw|=({peaks['raw1_absmax']:.3f},{peaks['raw2_absmax']:.3f})/{B.RAW_CLIP:g}  "
          f"|dq|=({peaks['dq1_absmax']:.1f},{peaks['dq2_absmax']:.1f})  "
          f"τ천장(스탠스)=({peaks['ceiling_ride_pct_stance'][0]:.0f}%,"
          f"{peaks['ceiling_ride_pct_stance'][1]:.0f}%)", flush=True)

    # ── 저장 (p25_b_traj 스키마 + h_plan/h_twin/raw_clip) ──
    np.savez(OUT_NPZ,
             t=tt, q=np.vstack([q1_pl, q2_pl]).T, dq=np.vstack([dq1_pl, dq2_pl]).T,
             tau_cmd_nm=res["U"].T, tau_cmd_raw=np.vstack([raw1, raw2]).T,
             bz=res["Y"][0], q_des=np.vstack([q1_pl, q2_pl]).T,
             dq_des=np.vstack([dq1_pl, dq2_pl]).T,
             fz_plan=res["fz"], fx_plan=res["FX"][0],
             t_twin=L["t"], bz_twin=L["bz"],
             q_twin=np.vstack([L["q1"], L["q2"]]).T,
             dq_twin=np.vstack([L["dq1"], L["dq2"]]).T,
             grf_twin=L["grf"], footx_twin=L["fx"],
             h_plan=res["h_plan"], h_twin=h_twin, raw_clip=B.RAW_CLIP)

    audit_doc = dict(
        CAMPAIGN="P25-task0 no_cvt (task0 constraint block on p25_b NLP / p24a twin)",
        constraints=dict(
            tau_axis_abs_max=TAU_LIM, raw_box=B.RAW_CLIP,
            tn=f"|dq| <= {T0.TN_COEF}*|ahat| + {T0.TN_OFF}",
            dq_abs_max=T0.DQ_LIM,
            q1=[T0.Q1_LB, T0.Q1_UB], q2=[T0.Q2_LB, T0.Q2_UB],
            start="free pose in box + rest + static equilibrium (Fz(0)=M*g)",
            stance_max_s=T0.T_ST_MAX,
            stance_mode="fixed grid -> liftoff audit"
                        + (" + enforced flight t>=0.3 (2nd solve)" if res["enforce_tst"] else "")),
        nlp=dict(status=res["status"], iters=res["iters"], wall_s=res["wall_s"],
                 N=B.N_NODE, dt=res["dt"], horizon_s=B.T_HOR, k_c=res["k_c"],
                 b_c=res["b_c"], objective="G20 'Base via CoM v_z' (p25_b 동일)",
                 warm_start="p25_b_traj_t18.npz projected to task0 box",
                 enforce_tst_2nd_solve=bool(res["enforce_tst"])),
        start=dict(q1_0=q1_0, q2_0=q2_0, bz0=float(res["Y"][0, 0]),
                   note="자유 최적화 결과 (t18은 0602 웅크림 고정 = 박스 밖이었음)"),
        results=dict(h_plan=res["h_plan"], h_twin_rollout=h_twin,
                     gap_pct=100 * gap, plan_twin_stance_qRMSE=rq,
                     vz_com_T=res["vz_com_T"],
                     t18_ref=dict(h_plan=T18_H_PLAN, h_twin=T18_H_TWIN),
                     dh_plan_vs_t18=res["h_plan"] - T18_H_PLAN),
        stance=dict(liftoff_plan_s=lift_plan, liftoff_twin_s=lift_twin,
                    limit_s=T0.T_ST_MAX,
                    pass_plan=bool(lift_plan is not None and lift_plan <= T0.T_ST_MAX + 1e-9),
                    pass_twin=bool(lift_twin is not None and lift_twin <= T0.T_ST_MAX + 1e-9)),
        audit_plan=A_plan,
        audit_twin_rollout=A_twin,
        tn_active_plan=tn_pl,
        tn_active_twin=tn_tw,
        peaks=peaks,
        eom=dict(basis_rel_resid={k: max(v) for k, v in ex["resids"].items()},
                 air_rollout_check=ver),
        notes=[
            "audit_twin은 개루프 â replay의 실현 궤적 감사 — 플랜 준수여도 트윈 편차로 위반 가능",
            "T-N/|dq| 매끈화(sqrt(x²+ε²), ε=0.05)는 보수측 — 정확 fabs 감사가 기준",
            "raw 공급 박스(25.5810)와 |â|≤15 박스 공존 — 제동 가지는 박스가 지배",
        ])
    safe.atomic_json_write(OUT_JSON, audit_doc)
    print(f"saved {OUT_NPZ.name}, {OUT_JSON.name}", flush=True)

    # ── 그림 (auto color cycle, sim/real 매칭 get_color) ──
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
    l2 = ax.plot(tt, q2_pl, label="plan q2")
    ax.plot(L["t"], L["q1"], "--", color=l1[0].get_color(), label="twin q1")
    ax.plot(L["t"], L["q2"], "--", color=l2[0].get_color(), label="twin q2")
    for v, c in ((T0.Q1_LB, l1), (T0.Q1_UB, l1), (T0.Q2_LB, l2), (T0.Q2_UB, l2)):
        ax.axhline(v, ls=":", lw=0.8, color=c[0].get_color(), alpha=0.6)
    ax.set_title("Joint angles (measured frame, task0 box dotted)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[0, 2]
    l1 = ax.plot(tt, dq1_pl, label="plan dq1")
    l2 = ax.plot(tt, dq2_pl, label="plan dq2")
    ax.plot(L["t"], L["dq1"], "--", color=l1[0].get_color())
    ax.plot(L["t"], L["dq2"], "--", color=l2[0].get_color())
    ax.axhline(T0.DQ_LIM, ls=":", lw=0.8, alpha=0.6)
    ax.axhline(-T0.DQ_LIM, ls=":", lw=0.8, alpha=0.6)
    ax.set_title("Joint velocities [rad/s] (|dq|<=50 dotted)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 0]
    ax.plot(tt, res["U"][0], label="s1 (hip)")
    ax.plot(tt, res["U"][1], label="s2 (knee)")
    ax.axhline(TAU_LIM, ls=":", lw=1); ax.axhline(-TAU_LIM, ls=":", lw=1)
    ax.set_title("Command ahat u=s [Nm] (|ahat|<=15)")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 1]
    tr = np.linspace(0, TAU_LIM, 60)
    ax.plot(tr, T0.TN_COEF * tr + T0.TN_OFF, "k--", lw=1, alpha=0.5,
            label="T-N envelope")
    ax.plot(np.abs(res["U"][0]), np.abs(dq1_pl), ".", ms=4, label="hip")
    ax.plot(np.abs(res["U"][1]), np.abs(dq2_pl), ".", ms=4, label="knee")
    ax.set_xlabel("|ahat| [Nm]"); ax.set_ylabel("|dq| [rad/s]")
    ax.set_title("T-N limit check"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    ax = axs[1, 2]
    ax.plot(tt, res["fz"], label="plan Fz")
    ax.plot(L["t"], L["grf"], "--", label="twin GRF")
    ax.set_xlim(-0.05, 0.45)
    ax.set_title("Contact normal force [N]"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.suptitle(
        f"P25-task0 no_cvt NLP (task0 constraints, tau<=15) — "
        f"h_plan {res['h_plan']:.3f} / twin {h_twin:.3f} ({100*gap:+.1f}%) | "
        f"t18 ref {T18_H_PLAN} | liftoff {lift_plan}s (<= {T0.T_ST_MAX})")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=110)
    print(f"saved {OUT_PNG.name}  [{(time.time()-t00)/60:.1f} min total]", flush=True)


if __name__ == "__main__":
    main()
