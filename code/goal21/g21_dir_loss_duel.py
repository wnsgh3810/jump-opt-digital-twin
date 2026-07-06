"""GOAL21 P3b — direction-dependent knee loss duel.

Physics: 4-bar lead screw is near self-locking. Air regression measured the
asymmetry (knee raise eta 0.40, lower eta -0.18): lowering costs much more.
Symmetric fc_knee sweep showed the conflict: s2s wants ~2.0+, jumps want ~1.0
(push-off is single-direction). Test: keep XML frictionloss at canonical
(a=0.99, proper stiction), add smooth EXTRA opposing torque only in one knee
direction via ctrl during replay:  tau_extra = -c_extra * tanh(dq2/0.3) applied
only when sign(dq2) == dir.  Grid over (dir, c_extra); prediction if self-locking
is real: one direction's column wins big on s2s while leaving jumps ~intact.
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
import sub_sim_iter6v2 as S
from apply_final_and_regen import apply_final
from load_31exp import list_experiments

DIR = +1
C_EXTRA = 0.0


def eval_windows_dir(model, pp):
    """eval_windows + direction-gated extra knee loss."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0]]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0]]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1 = np.empty(nst); q2 = np.empty(nst)
        dq1 = np.empty(nst); dq2 = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            v2 = d.qvel[2]
            extra = -C_EXTRA * np.tanh(v2 / 0.3) if (v2 * DIR > 0) else 0.0
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]),
                         np.interp(tc, t, pp["tau_k"]) + extra]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1[k] = d.qpos[1]; q2[k] = d.qpos[2]
            dq1[k] = d.qvel[1]; dq2[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1, pp["q1m"]), rq2=r(q2, pp["q2m"]),
                        rdq1=r(dq1, pp["dq1m"]), rdq2=r(dq2, pp["dq2m"])))
    return out


def main():
    global DIR, C_EXTRA
    ap = apply_final()
    MS.eval_windows = eval_windows_dir          # patch replay
    res = {}
    grid = [(+1, 0.0)] + [(sgn, c) for sgn in (+1, -1) for c in (0.5, 1.0, 1.5, 2.0)]
    for sgn, c in grid:
        DIR, C_EXTRA = sgn, c
        total, per = MS.evaluate_all(ap["arm_hip"], ap["arm_knee"])
        key = f"dir{sgn:+d}_c{c:.1f}"
        res[key] = dict(total=float(total),
                        per={k: float(v["score"]) for k, v in per.items()})
        line = "  ".join(f"{k}:{v['score']:.0f}" for k, v in per.items())
        print(f"{key:<14} TOTAL={total:.0f}   {line}", flush=True)
    json.dump(res, open(REPO / "code/goal21/dir_loss_duel.json", "w"), indent=1)
    print("saved dir_loss_duel.json")


if __name__ == "__main__":
    main()
