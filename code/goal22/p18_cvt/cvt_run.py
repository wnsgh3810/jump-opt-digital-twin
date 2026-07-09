# -*- coding: utf-8 -*-
"""P18 러너 — 26.04.29 (l_i=25.08mm) Mode A 검증 + PD 폐루프, P16 모델 그대로.

Mode A: settle(PD, 측정 초기 crank각) -> a_hat(P16) 변환 τ replay -> crank/hip 궤적·GRF·h 비교
CL   : 라벨 게인, dq_des=0 (What.txt: V_des≈0), 무클립+a_hat, 참조 τ = P16 a_hat 변환
공통 : 오프셋 = 0 (신규 세션), sens_delay −1.5ms, 초기화는 폐쇄 솔버.
"""
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from cvt_core import build_cvt, qpos_from_crank, closure, load_0429, label_gains_429, SUBS429
import p14_judge as J

SD = -0.0015
T_SETTLE, T_AFTER = 0.4, 0.6
C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X = np.array(C16["x"])
A = np.array([C16["x"][32], C16["x"][33], C16["x"][34], C16["x"][35]])
REF = float(C16["x"][36])
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_cvt_0429_results")
(DST / "png").mkdir(parents=True, exist_ok=True)
(DST / "gif").mkdir(parents=True, exist_ok=True)
TRAJD = HERE / "traj"; TRAJD.mkdir(exist_ok=True)


def fk_bz(model, dta, q1m, qc, l_i):
    mj = J._P["mj"]; S = J._P["S"]
    qp5, qk, r = qpos_from_crank(1.0, q1m, qc, l_i)
    dta.qpos[:] = qp5
    dta.qvel[:] = 0
    mj.mj_forward(model, dta)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(dta.geom_xpos[fg][2]) + S.FOOT_RADIUS


def sim_run(model, d, l_i, mode, gains=None):
    """mode='A'(τ replay) 또는 'CL'(PD). 반환 로그 dict (canonical)."""
    mj = J._P["mj"]; S = J._P["S"]
    t = d["t"]
    dta = mj.MjData(model)
    # 목표/초기: crank(=측정 q2) 기준, calf는 폐쇄
    q1_0 = d["qd1"][0] if mode == "CL" else d["q1"][0]
    q2_0 = d["qd2"][0] if mode == "CL" else d["q2"][0]
    mj_q1_0 = -q1_0 - np.pi / 2
    mj_qc_0 = -q2_0
    bz0 = fk_bz(model, dta, mj_q1_0, mj_qc_0, l_i)
    qp5, qk_prev, _ = qpos_from_crank(bz0, mj_q1_0, mj_qc_0, l_i)
    dta.qpos[:] = qp5; dta.qvel[:] = 0
    mj.mj_forward(model, dta)
    # 입력 준비
    tau1_in = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tau2_in = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    dt = model.opt.timestep
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "grf",
                                  "qk", "qpin"]}
    kp1 = kd1 = kp2 = kd2 = 0.0
    if gains:
        kp1, kd1, kp2, kd2 = gains
    for k in range(N):
        tc = tl[k]
        q1c = -dta.qpos[1] - np.pi / 2
        q2c = -dta.qpos[2]                      # crank = 엔코더
        v1c = -dta.qvel[1]; v2c = -dta.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        elif mode == "A":
            tm = min(tc, t[-1])
            s1 = float(np.interp(tm, t, tau1_in))
            s2 = float(np.interp(tm, t, tau2_in))
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, d["qd1"]) - q1c) + kd1 * (0.0 - v1c)
            c2 = kp2 * (np.interp(tm, t, d["qd2"]) - q2c) + kd2 * (0.0 - v2c)
            s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        if tc > t[-1]:
            s1 = s2 = 0.0
        dta.ctrl[:] = [-s1, -s2]
        try:
            mj.mj_step(model, dta)
        except Exception:
            return None
        if abs(dta.qpos[0]) > 5 or not np.isfinite(dta.qpos).all():
            return None
        L["q1"][k] = -dta.qpos[1] - np.pi / 2; L["q2"][k] = -dta.qpos[2]
        L["dq1"][k] = -dta.qvel[1]; L["dq2"][k] = -dta.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = dta.qpos[0]
        L["qk"][k] = dta.qpos[4]; L["qpin"][k] = dta.qpos[3]
        gz = 0.0
        for ci in range(dta.ncon):
            cf = np.zeros(6)
            mj.mj_contactForce(model, dta, ci, cf)
            gz += (dta.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
        L["grf"][k] = gz
    L["t"] = tl
    return L


def metrics(d, L):
    t = d["t"]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    return dict(q1=r(f(L["q1"]), d["q1"]), q2=r(f(L["q2"]), d["q2"]),
                dq1=r(f(L["dq1"]), d["dq1"]), dq2=r(f(L["dq2"]), d["dq2"]),
                tau1=r(f(L["sh1"]), tp1), tau2=r(f(L["sh2"]), tp2),
                h=float(L["bz"].max()), h_real=float(d["h_real"]))


def fig_trial(sub, d, L, m, tag, l_i):
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk]), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk]), "C0", lw=1.3, label="q2(crank) sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    if tag == "CL":
        ax[0, 0].plot(t, np.degrees(d["qd1"]), "C2--", lw=1.1, label="q_des")
        ax[0, 0].plot(t, np.degrees(d["qd2"]), "C2--", lw=1.1, label="_nolegend_")
    ax[0, 0].set_ylabel("q [deg]")
    ax[0, 1].plot(L["t"][mk], L["dq1"][mk], lw=1.3, label="sim")
    ax[0, 1].plot(t, d["dq1"], lw=1.3, label="real")
    ax[0, 1].set_ylabel("dq1 hip [rad/s]")
    ax[0, 2].plot(L["t"][mk], L["dq2"][mk], lw=1.3, label="sim")
    ax[0, 2].plot(t, d["dq2"], lw=1.3, label="real")
    ax[0, 2].set_ylabel("dq2 crank [rad/s]")
    ax[1, 0].plot(L["t"][mk], L["sh1"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 0].plot(t, tp1, lw=1.3, label="real tau (P16 a_hat)")
    ax[1, 0].set_ylabel("hip tau [Nm]")
    ax[1, 1].plot(L["t"][mk], L["sh2"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 1].plot(t, tp2, lw=1.3, label="real tau (P16 a_hat)")
    ax[1, 1].set_ylabel("knee(crank) tau [Nm]")
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a_ in ax.flat:
        a_.grid(alpha=0.3); a_.legend(fontsize=7); a_.set_xlabel("t [s]")
    fig.suptitle(f"26.04.29/{sub} [{tag}, l_i={l_i*1000:.1f}mm] — "
                 f"tau RMSE hip {m['tau1']:.2f} / knee {m['tau2']:.2f} Nm · "
                 f"h_sim {m['h']:.2f} / h_real {m['h_real']:.2f} m")
    fig.tight_layout()
    fig.savefig(DST / "png" / f"{sub}__{tag}.png", dpi=100)
    plt.close(fig)


def run_one(args):
    sub, mode = args
    if not J._P:
        J.winit()
    d = load_0429(sub)
    l_i = d["l_i"]
    model, dd = build_cvt(X[:32], REF, l_i)
    gains = label_gains_429(sub) if mode == "CL" else None
    L = sim_run(model, d, l_i, mode, gains)
    if L is None:
        return dict(sub=sub, mode=mode, err="CRASH")
    m = metrics(d, L)
    fig_trial(sub, d, L, m, mode, l_i)
    np.savez(TRAJD / f"{sub}__{mode}.npz",
             t=L["t"], q1=L["q1"], q2=L["q2"], qk=L["qk"], qpin=L["qpin"], bz=L["bz"],
             dq1=L["dq1"], dq2=L["dq2"], sh1=L["sh1"], sh2=L["sh2"], grf=L["grf"],
             l_i=l_i)
    return dict(sub=sub, mode=mode, l_i=l_i, **m)


def main():
    import multiprocessing as mp
    jobs = [(s, m) for s in SUBS429 for m in ("A", "CL")]
    pool = mp.Pool(10, initializer=J.winit)
    res = {}
    for r in pool.imap_unordered(run_one, jobs):
        key = f"{r['sub']}/{r['mode']}"
        res[key] = r
        if "err" in r:
            print(key, r["err"], flush=True)
        else:
            print(f"{key:28s} q2 {r['q2']:.3f} dq2 {r['dq2']:.2f} "
                  f"tau1 {r['tau1']:.2f} tau2 {r['tau2']:.2f} h {r['h']:.3f}/{r['h_real']:.3f}",
                  flush=True)
    json.dump(res, open(HERE / "cvt_results.json", "w"), indent=1)
    for mode in ("A", "CL"):
        ks = [k for k in res if k.endswith("/" + mode) and "err" not in res[k]]
        if ks:
            avg = lambda f: np.mean([res[k][f] for k in ks])
            print(f"\n[{mode}] 평균: q2 {avg('q2'):.3f} dq2 {avg('dq2'):.2f} "
                  f"tau1 {avg('tau1'):.2f} tau2 {avg('tau2'):.2f} "
                  f"h {avg('h'):.3f} (real {avg('h_real'):.3f})", flush=True)
    print("saved cvt_results.json", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
