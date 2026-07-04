"""G20-B — per-DATE encoder offset test (0602 = reference).

Physical basis: encoder re-zeroing between sessions. Per-date (NOT per-trial) q1/q2
offsets for 0324/0421/0424; 0602 fixed as reference. v3 dynamics FROZEN (stage 1:
isolate the axis). FK base shift is linearized via cached d(bz)/dq gradients.
If stage-1 gain is significant -> stage 2 joint refit later.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco
from scipy.signal import savgol_filter

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_refit as R
from load_31exp import list_experiments

OUT = REPO / "code/goal19/phase11/dateoff_best.json"
DATES = ["jump_0324", "jump_position_0421", "jump_0424"]  # 0602 = reference (0 offset)


def prep_with_grad(key, td, model):
    """mshoot prep + d(bz)/d(q1m), d(bz)/d(q2m) for linearized offset shift."""
    pp = MS.get_prep(key, td, model, True)
    if "dbz1" in pp:
        return pp
    d = mujoco.MjData(model)
    fg = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    n = len(pp["t"]); eps = 1e-5
    dbz1 = np.zeros(n); dbz2 = np.zeros(n)
    for i in range(n):
        d.qpos[:] = [1.0, pp["q1m"][i] + eps, pp["q2m"][i]]
        mujoco.mj_forward(model, d); zp = 1.0 - float(d.geom_xpos[fg][2])
        d.qpos[:] = [1.0, pp["q1m"][i] - eps, pp["q2m"][i]]
        mujoco.mj_forward(model, d); zm = 1.0 - float(d.geom_xpos[fg][2])
        dbz1[i] = (zp - zm) / (2 * eps)
        d.qpos[:] = [1.0, pp["q1m"][i], pp["q2m"][i] + eps]
        mujoco.mj_forward(model, d); zp = 1.0 - float(d.geom_xpos[fg][2])
        d.qpos[:] = [1.0, pp["q1m"][i], pp["q2m"][i] - eps]
        mujoco.mj_forward(model, d); zm = 1.0 - float(d.geom_xpos[fg][2])
        dbz2[i] = (zp - zm) / (2 * eps)
    pp["dbz1"] = savgol_filter(dbz1, 11, 3); pp["dbz2"] = savgol_filter(dbz2, 11, 3)
    return pp


def shifted_view(pp, o1c, o2c):
    """Offsets in CANONICAL frame (q_true = q_meas + o). mj: q1m' = q1m - o1c, q2m' = q2m - o2c."""
    if o1c == 0.0 and o2c == 0.0:
        return pp
    q1m = pp["q1m"] - o1c; q2m = pp["q2m"] - o2c
    bz = pp["bz"] + pp["dbz1"] * (-o1c) + pp["dbz2"] * (-o2c)
    vbz = np.gradient(bz, pp["t"])
    return dict(pp, q1m=q1m, q2m=q2m, bz=bz, vbz=vbz)


def evaluate(offs, arm_knee, model):
    """offs = [o1_0324,o2_0324, o1_0421,o2_0421, o1_0424,o2_0424] canonical rad."""
    omap = {DATES[i]: (offs[2*i], offs[2*i+1]) for i in range(3)}
    total = 0.0; per = {}
    groups = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        groups.append((ds, subs, MS.LOADERS[ds]))
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    for ds, subs, loader in groups:
        o1, o2 = omap.get(ds, (0.0, 0.0))
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, model)
            wins = MS.eval_windows(model, shifted_view(pp, o1, o2))
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = dict(score=sc, mean=acc / max(nw, 1))
    return total, per


def main():
    import cma
    best_model = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    d = R.set_params(np.array(best_model["x"]))
    model = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, d["arm_knee"]))
    o0 = np.zeros(6)
    t0, per0 = evaluate(o0, d["arm_knee"], model)
    print(f"BASE (no offsets, jumps only): {t0:.0f}", flush=True)
    LIM = np.deg2rad(5.0)
    es = cma.CMAEvolutionStrategy(np.zeros(6), 0.3, {"bounds": [-1, 1], "maxfevals": 120,
                                                     "popsize": 10, "seed": 17, "verbose": -9})
    best = dict(obj=float(t0), offs=[0.0] * 6)
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            offs = np.array(sn) * LIM
            o, _ = evaluate(offs, d["arm_knee"], model)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), offs=[float(v) for v in offs])
                json.dump(best, open(OUT, "w"), indent=2)
        es.tell(sols, objs)
        print(f"best={best['obj']:.0f}", flush=True)
    print(f"\nRESULT: {t0:.0f} -> {best['obj']:.0f} ({100*(best['obj']/t0-1):+.1f}%)")
    lab = ["0324_q1", "0324_q2", "0421_q1", "0421_q2", "0424_q1", "0424_q2"]
    print("offsets(deg):", {lab[i]: round(np.rad2deg(best["offs"][i]), 2) for i in range(6)})
    _, per = evaluate(np.array(best["offs"]), d["arm_knee"], model)
    for ds, v in per.items():
        m = v["mean"]
        print(f"   {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f}")


if __name__ == "__main__":
    main()
