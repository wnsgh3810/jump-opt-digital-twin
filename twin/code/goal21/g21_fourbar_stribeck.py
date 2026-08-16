"""GOAL21 P4c — port the serial-stack Stribeck finding onto the 4-BAR CANONICAL.

Serial-stack (goal19_final) hybrid refit found: knee = Coulomb 0.47 + Stribeck
c~4.9 (vs 1.46, w 0.44), hip friction ~0. Improved windows -29% AND full-stance
-40% dq2, whip 0.53->0.95, incl. out-of-sample 0324.

4-bar canonical differs (fc_knee 0.057, fv_hip 0.488, explicit loop). Port:
  gate velocity = crank (= encoder = lead-screw coordinate) qvel[2]
  extra torque on knee actuator ctrl[1]
Gate 0: reproduce canonical obj 14984 (fourbar_refit_best.json) exactly.
Grid: c x fc_knee x fv_hip (9+1 configs), then full-stance check for winner.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import mshoot as MS
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR

CP = {"c": 0.0, "vs": 1.46, "w": 0.44, "c_hip": 0.0}


def eval_windows_fourbar_strib(model, pp):
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
            vc = d.qvel[2]; vh = d.qvel[1]
            ek = -CP["c"] * np.tanh(vc / CP["w"]) * np.exp(-abs(vc) / CP["vs"])
            eh = -CP["c_hip"] * np.tanh(vh / CP["w"]) * np.exp(-abs(vh) / CP["vs"])
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) + eh,
                         np.interp(tc, t, pp["tau_k"]) + ek]
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


def main():
    FB.eval_windows_fourbar = eval_windows_fourbar_strib   # FR.evaluate uses FB.<name>
    best_json = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    x_can = np.array(best_json["x"])
    names = best_json["names"]
    i_fck = names.index("fc_knee"); i_fvh = names.index("fv_hip"); i_fvk = names.index("fv_knee")
    # Gate 0: canonical reproduction (c=0)
    CP.update(c=0.0)
    o0, per0 = FR.evaluate(x_can)
    print(f"GATE0 canonical: {o0:.1f} (expected {best_json['obj']:.1f})  "
          f"{'PASS' if abs(o0-best_json['obj'])/best_json['obj'] < 0.01 else 'FAIL'}", flush=True)
    if abs(o0 - best_json["obj"]) / best_json["obj"] > 0.01:
        return
    base_per = {k: v["score"] for k, v in per0.items()}
    res = {"baseline": dict(total=float(o0), per={k: float(v) for k, v in base_per.items()})}
    grid = []
    for c in (2.5, 5.0):
        for fck in (x_can[i_fck], 0.47):
            for fvh in (x_can[i_fvh], 0.05):
                grid.append((c, fck, fvh))
    for c, fck, fvh in grid:
        CP.update(c=c)
        x = x_can.copy(); x[i_fck] = fck; x[i_fvh] = fvh
        o, per = FR.evaluate(x)
        key = f"c{c:.1f}_fck{fck:.3f}_fvh{fvh:.3f}"
        res[key] = dict(total=float(o), per={k: float(v["score"]) for k, v in per.items()})
        line = "  ".join(f"{k.split('_')[-1]}:{v['score']/base_per[k]:.3f}" for k, v in per.items())
        print(f"{key:<28} TOTAL={o:.0f} ({o/o0:.3f})   {line}", flush=True)
    json.dump(res, open(REPO / "code/goal21/fourbar_stribeck_duel.json", "w"), indent=1)
    print("saved fourbar_stribeck_duel.json", flush=True)


if __name__ == "__main__":
    main()
