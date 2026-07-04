"""G20 — s2s_air BONUS held-out validation (queue item f).

sit2stand_air_0319 (base clamped, leg swings free, 15 cycles) was NEVER used in any
G20 fit. It exercises pure leg dynamics with ZERO contact — a clean probe of the
mass/inertia/friction identification, fully orthogonal to the contact axis.

Protocol: window replay (W=0.25s / stride 0.15s, s2s settings), measured-state reset,
pure tau replay — identical to the fit metric. Models compared on the SAME windows:
  (a) round-1 four-bar (canonical G20)      + fitted 0319 offsets (from s2s_gnd)
  (b) round-1 four-bar, offsets OFF          -> tests offset transfer within-session
  (c) v3 fitted serial (pre-G20 best)        + same offsets
Air XML = jump XML with base_z slide removed, base clamped at 1.5 m, floor at -10 m.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from scipy.signal import savgol_filter
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_refit as R
import mshoot_fourbar as FB

AIR_NPZ = Path("C:/Users/junho/Desktop/jump_opt/goal12/xval_v2/sit2stand_air_0319/ROOT/cycle_final.npz")
BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))


def air_xml_fourbar(arm_knee, scales):
    xml = FB.build_xml_fourbar_jump(arm_knee, scales)
    xml = xml.replace('<joint name="base_z" type="slide" axis="0 0 1"/>', "")
    xml = xml.replace('<body name="base" pos="0 0 0"', '<body name="base" pos="0 0 1.5"')
    xml = xml.replace('<geom name="floor" size="0 0 0.05"',
                      '<geom name="floor" pos="0 0 -10" size="0 0 0.05"')
    return xml


def load_air_cycles():
    d = np.load(AIR_NPZ)
    t = d["t"]; cyc = d["cycles"]
    out = []
    for i0, i1 in cyc:
        sl = slice(int(i0), int(i1))
        out.append(dict(t=t[sl] - t[sl][0], q1=d["q1"][sl], q2=d["q2"][sl],
                        dq1=d["dq1"][sl], dq2=d["dq2"][sl],
                        tau1=d["tau1"][sl], tau2=d["tau2"][sl]))
    return out


def prep_air(td, o1=0.0, o2=0.0):
    t = np.asarray(td["t"])
    q1m = -np.asarray(td["q1"]) - np.pi / 2 - o1
    q2m = -np.asarray(td["q2"]) - o2
    dq1m = savgol_filter(-np.asarray(td["dq1"]), 11, 3)
    dq2m = savgol_filter(-np.asarray(td["dq2"]), 11, 3)
    tau_h = -np.asarray(td["tau1"]); tau_k = -np.asarray(td["tau2"])
    starts = []
    t0 = t[0]
    while t0 <= t[-1] - 1e-9:
        i0 = int(np.argmin(np.abs(t - t0)))
        if t[-1] - t[i0] > 0.5 * MS.W_S2S:
            starts.append(i0)
        t0 += MS.STR_S2S
    return dict(t=t, q1m=q1m, q2m=q2m, dq1m=dq1m, dq2m=dq2m,
                tau_h=tau_h, tau_k=tau_k, starts=starts, W=MS.W_S2S)


def eval_air(model, pp, fourbar):
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        if fourbar:
            d.qpos[:] = [pp["q1m"][i0], q2, -q2, q2]
            d.qvel[:] = [pp["dq1m"][i0], dq2, -dq2, dq2]
        else:
            d.qpos[:] = [pp["q1m"][i0], q2]
            d.qvel[:] = [pp["dq1m"][i0], dq2]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[0]; q2a[k] = d.qpos[1]
            dq1a[k] = d.qvel[0]; dq2a[k] = d.qvel[1]
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


def run_model(model, cycles, o1, o2, fourbar):
    tot = 0.0; acc = np.zeros(4); nw = 0
    for td in cycles:
        pp = prep_air(td, o1, o2)
        wins = eval_air(model, pp, fourbar)
        tot += MS.window_score(wins); nw += len(wins)
        for w in wins:
            acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
    m = acc / max(nw, 1)
    return tot, nw, m


def main():
    cycles = load_air_cycles()
    print(f"s2s_air held-out: {len(cycles)} cycles, "
          f"{sum(len(c['t']) for c in cycles)} samples total")

    # (a)/(b) four-bar round-1
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    mfb = mujoco.MjModel.from_xml_string(air_xml_fourbar(BD["arm_knee"], BD))
    o1, o2 = BD["o1_0319"], BD["o2_0319"]
    ta, nwa, ma = run_model(mfb, cycles, o1, o2, True)
    tb, _, mb = run_model(mfb, cycles, 0.0, 0.0, True)

    # (c) v3 fitted serial
    V3 = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    dv3 = R.set_params(np.array(V3["x"]))
    mse = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_air_6d(0.0, dv3["arm_knee"]))
    tc, _, mc = run_model(mse, cycles, o1, o2, False)

    print(f"(a) 4-bar r1 + 0319 offsets : score={ta:.0f} ({nwa} win)  "
          f"q1={ma[0]:.4f} q2={ma[1]:.4f} dq1={ma[2]:.2f} dq2={ma[3]:.2f}")
    print(f"(b) 4-bar r1, offsets OFF   : score={tb:.0f}            "
          f"q1={mb[0]:.4f} q2={mb[1]:.4f} dq1={mb[2]:.2f} dq2={mb[3]:.2f}")
    print(f"(c) v3 serial + offsets     : score={tc:.0f}            "
          f"q1={mc[0]:.4f} q2={mc[1]:.4f} dq1={mc[2]:.2f} dq2={mc[3]:.2f}")
    print(f"4-bar vs serial: {100*(ta/tc-1):+.1f}%   offsets effect: {100*(ta/tb-1):+.1f}%")
    json.dump(dict(fourbar_off=dict(score=ta, mean=list(ma)),
                   fourbar_nooff=dict(score=tb, mean=list(mb)),
                   serial_v3=dict(score=tc, mean=list(mc)), n_windows=nwa),
              open(REPO / "code/goal19/phase11/s2s_air_holdout.json", "w"), indent=1)


if __name__ == "__main__":
    main()
