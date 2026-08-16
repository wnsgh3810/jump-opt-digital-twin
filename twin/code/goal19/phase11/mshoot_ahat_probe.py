"""G20+ — a_hat sign(v) correction probe (allow NEGATIVE effective knee Coulomb).

Motivation (07-06 diagnostics): normal-date failure mode = UNDER-whip with a fixed
~0.5-1 Nm-class residual dominating at low work; and the fit already rails knee
friction at its lower bounds (fv_knee 0.014~0, fc_knee 0.057 ~ LB 0.05) — the
optimizer has been asking for NEGATIVE effective knee friction. Physically this is
NOT negative friction but an actuator-model correction: the UMich a_hat (generic
unit) may over-subtract internal friction on OUR unit, so measured tau under-reads
shaft torque by ~delta*sign(v).

Probe: XML knee frictionloss=0; inject net Coulomb  tau_extra = -fc_eff*tanh(v/0.5)
in the window loop, sweep fc_eff_knee in [-0.9 .. +0.3] (0.057 ~= baseline).
Gate: window score, then held-out full-traj h + whip peak ratios on 0424 stiff.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR
from mshoot_dateoff import prep_with_grad, shifted_view

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
VS = 0.5


def build(fc_knee_xml):
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]
    S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = fc_knee_xml
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))


def eval_windows_inj(model, pp, c_k):
    """windows with injected knee Coulomb  tau_extra = -c_k*tanh(v/VS) (mujoco frame)."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]),
                         np.interp(tc, t, pp["tau_k"]) - c_k * np.tanh(d.qvel[2] / VS)]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1a, pp["q1m"]), rq2=r(q2a, pp["q2m"]),
                        rdq1=r(dq1a, pp["dq1m"]), rdq2=r(dq2a, pp["dq2m"])))
    return out


def score(model, c_k):
    mj, mg = FR.get_serial_models()
    total = 0.0
    for ds, subs, loader, isj in FR.all_groups():
        k1, k2 = FR.OFFKEY.get(ds, (None, None))
        o1 = BD[k1] if k1 else 0.0; o2 = BD[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            total += MS.window_score(eval_windows_inj(model, shifted_view(pp, o1, o2), c_k))
    return total


def replay_inj(model, td, c_k):
    t_real = td["t"]
    tau_h = -np.asarray(td["tau1_real"]); tau_k = -np.asarray(td["tau2_real"])
    sq1, sq2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    d = mujoco.MjData(model)
    d.qpos[:] = [S.BASE_Z_INIT + S.BASE_Z_INIT_OFF, sq1, sq2, -sq2, sq2]; d.qvel[:] = 0
    mujoco.mj_forward(model, d)
    dt = model.opt.timestep; T = float(t_real[-1])
    N = int((S.T_SETTLE + T + S.T_AFTER) / dt) + 1
    tl = np.arange(N) * dt - S.T_SETTLE
    bz = np.zeros(N); dq2c = np.zeros(N)
    for k in range(N):
        tc = k * dt
        if tc < S.T_SETTLE:
            th = S.SETTLE_KP * (sq1 - d.qpos[1]) + S.SETTLE_KD * (-d.qvel[1])
            tk = S.SETTLE_KP * (sq2 - d.qpos[2]) + S.SETTLE_KD * (-d.qvel[2])
        elif tc < S.T_SETTLE + T:
            tm = tc - S.T_SETTLE
            th = float(np.interp(tm, t_real, tau_h))
            tk = float(np.interp(tm, t_real, tau_k)) - c_k * np.tanh(d.qvel[2] / VS)
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        mujoco.mj_step(model, d)
        bz[k] = d.qpos[0]; dq2c[k] = d.qvel[2]
    return tl, bz, dq2c


def main():
    m0 = build(BD["fc_knee"])
    s_base = score(m0, 0.0)
    print(f"baseline (round-1 equiv): {s_base:.0f}", flush=True)
    m = build(0.0)   # knee frictionloss removed; injection supplies net Coulomb
    results = {}
    for c in [0.057, 0.0, -0.15, -0.3, -0.5, -0.7, -0.9]:
        sc = score(m, c)
        results[c] = sc
        print(f"fc_eff_knee={c:+.3f}: window={sc:.0f} ({100*(sc/s_base-1):+.1f}%)", flush=True)
    best_c = min(results, key=results.get)
    print(f"\nBEST fc_eff_knee = {best_c:+.3f} ({100*(results[best_c]/s_base-1):+.1f}%)")
    # held-out: whip + h on 0424 stiff + all-dataset h
    subs = ["90_0.75_90_2", "120_2_120_2", "150_2.2_250_3", "150_2.2_500_4"]
    print("\n0424 whip peak ratio & h (baseline -> best):")
    for sub in subs:
        td = S.load_jump_0424(sub)
        pkr = {}
        h = {}
        for tag, (mm, cc) in {"base": (m0, 0.0), "new": (m, best_c)}.items():
            tl, bz, dq2c = replay_inj(mm, td, cc)
            tr = np.asarray(td["t"]); mk = (tl >= 0) & (tl <= tr[-1])
            dq2s = np.interp(tr, tl[mk], (-dq2c)[mk])
            pkr[tag] = dq2s.max() / np.asarray(td["dq2"]).max()
            h[tag] = bz.max()
        print(f"  {sub:<16} whip {pkr['base']:.2f}->{pkr['new']:.2f}   "
              f"h {h['base']:.3f}->{h['new']:.3f} (cam {float(td['h_real']):.3f})")
    json.dump(dict(baseline=s_base, sweep={str(k): v for k, v in results.items()},
                   best=best_c), open(REPO / "code/goal19/phase11/ahat_probe.json", "w"), indent=1)
    print("saved ahat_probe.json")


if __name__ == "__main__":
    main()
