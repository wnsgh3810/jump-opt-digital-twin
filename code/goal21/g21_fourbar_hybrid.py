"""GOAL21 P5 — HYBRID-objective refit of the 4-bar CANONICAL (26 params).

Canonical fourbar_refit_best.json was fit with WINDOW-ONLY multiple shooting —
the objective proven gameable on the serial stack (windows -31% while full-stance
2.4x worse). Here: obj = 5 window groups + 2 full-stance groups (fs_0424, fs_0602),
each normalized by the canonical baseline. Canonical obj = 7.0.

Held-out judges (NOT in objective): fs_0324 full-stance, full-replay trace
(gallery metric) per date, h_ratio.

CMA-ES warm-started AT canonical; population evaluated in parallel (one worker
per candidate x). Guards: bounds from FR.SPEC; crash penalty.
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "code/goal21/fourbar_hybrid_best.json"
_G = {}


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import mshoot as MS
    import mshoot_fourbar as FB
    import mshoot_fourbar_refit as FR
    from mshoot_dateoff import prep_with_grad, shifted_view
    from load_31exp import list_experiments
    from scipy.signal import savgol_filter
    _G.update(mujoco=mujoco, MS=MS, FB=FB, FR=FR, pwg=prep_with_grad, sv=shifted_view,
              lex=list_experiments, sg=savgol_filter)


def _stance_range(td, t):
    grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
    gg = _G["sg"](grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
    st = np.where(gg > 15)[0]
    if len(st) < 10:
        return None
    brk = np.where(np.diff(st) > 3)[0]
    return st[0], (st[brk[0]] if len(brk) else st[-1])


def _fs_metric(model, pp, td):
    """Full push-off open-loop replay on the 4-bar model; W_Q/W_DQ RMSE."""
    mujoco, MS = _G["mujoco"], _G["MS"]
    t = pp["t"]
    rng = _stance_range(td, t)
    if rng is None:
        return 0.0
    i0, i1 = rng
    if t[i1] - t[i0] < 0.1:
        return 0.0
    d = mujoco.MjData(model)
    q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
    d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
    d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
    mujoco.mj_forward(model, d)
    dt = model.opt.timestep
    nst = int(round((t[i1] - t[i0]) / dt))
    out = np.empty((nst, 5))
    for k in range(nst):
        tc = t[i0] + k * dt
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
        try:
            mujoco.mj_step(model, d)
        except Exception:
            return MS.W_Q * 2.0 + MS.W_DQ * 20.0
        out[k] = [tc + dt, d.qpos[1], d.qpos[2], d.qvel[1], d.qvel[2]]
    if not np.all(np.isfinite(out)):
        return MS.W_Q * 2.0 + MS.W_DQ * 20.0
    msk = (t >= out[0, 0]) & (t <= out[-1, 0])
    if msk.sum() < 3:
        return 0.0
    r = lambda c, real: float(np.sqrt(np.mean((np.interp(t[msk], out[:, 0], out[:, c]) - real[msk]) ** 2)))
    return (MS.W_Q * (r(1, pp["q1m"]) + r(2, pp["q2m"]))
            + MS.W_DQ * (r(3, pp["dq1m"]) + r(4, pp["dq2m"])))


def eval_hybrid(x):
    """Window per-group scores (FR.evaluate) + full-stance groups. Returns dict."""
    try:
        FR, FB, MS, mujoco = _G["FR"], _G["FB"], _G["MS"], _G["mujoco"]
        x = np.asarray(x, dtype=float)
        total, per = FR.evaluate(x)                      # sets S globals + window scores
        if per is None:
            return None
        res = {ds: float(v["score"]) for ds, v in per.items()}
        dd = dict(zip(FR.NAMES, x))
        model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(dd["arm_knee"], dd))
        mj, _ = FR.get_serial_models()
        for ds, fsk in [("jump_0424", "fs_0424"), ("jump_0602", "fs_0602"), ("jump_0324", "fs_0324")]:
            k1, k2 = FR.OFFKEY.get(ds, (None, None))
            o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
            sc = 0.0
            if ds in MS.LOADERS:
                jobs = [(sub, MS.LOADERS[ds](sub)) for d2, sub, isj in _G["lex"]() if d2 == ds]
            else:
                tdir = [m[1] for m in MS.MARCH if m[0] == ds][0]
                subs = [m[2] for m in MS.MARCH if m[0] == ds][0]
                jobs = [(sub, MS.load_march(tdir, sub)) for sub in subs]
            for sub, td in jobs:
                pp = _G["pwg"]((ds, sub), td, mj)
                sc += _fs_metric(model, _G["sv"](pp, o1, o2), td)
            res[fsk] = float(sc)
        return res
    except Exception:
        return None


OBJ_GROUPS = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324",
              "s2s_gnd_0319", "fs_0424", "fs_0602"]     # fs_0324 = held-out


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = _G["FR"]
    best_json = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    x_can = np.array(best_json["x"]); NAMES = best_json["names"]
    LOb, HIb = FR.LOb, FR.HIb
    pool = mp.Pool(10, initializer=winit)
    log = open(REPO / "code/goal21/fourbar_hybrid_log.txt", "a", buffering=1)

    base = eval_hybrid(x_can)
    print("BASE:", " ".join(f"{k}:{v:.0f}" for k, v in base.items()), flush=True)
    log.write("BASE " + json.dumps(base) + "\n")

    def obj_of(res):
        if res is None:
            return 99.0
        return sum(res[g] / base[g] for g in OBJ_GROUPS)

    x0n = (x_can - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n, 0.10, {"bounds": [0, 1], "maxfevals": 1500,
                                              "popsize": 20, "seed": 7, "verbose": -9})
    cand = open(REPO / "code/goal21/fourbar_hybrid_cands.jsonl", "w", buffering=1)
    best = dict(obj=7.0, x=[float(v) for v in x_can], names=NAMES,
                res={k: float(v) for k, v in base.items()})
    nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(sn) * (HIb - LOb) for sn in sols]
        results = pool.map(eval_hybrid, xs)
        objs = [obj_of(r) for r in results]
        for x, r, o in zip(xs, results, objs):
            nev += 1
            if r is not None:
                ho = r["fs_0324"] / base["fs_0324"]
                log.write(f"ITER {nev} obj={o:.4f} " +
                          " ".join(f"{g.split('_')[-1]}:{r[g]/base[g]:.3f}" for g in OBJ_GROUPS) +
                          f" fs0324:{ho:.3f}\n")
                if o < 7.0 and ho <= 1.05:   # candidate pool for validation-based selection
                    cand.write(json.dumps(dict(obj=float(o), heldout=float(ho),
                                               x=[float(v) for v in x])) + "\n")
            if o < best["obj"]:
                best = dict(obj=float(o), x=[float(v) for v in x], names=NAMES,
                            res={k: float(v) for k, v in r.items()},
                            base={k: float(v) for k, v in base.items()})
                json.dump(best, open(OUT, "w"), indent=1)
                print(f"BEST nev={nev} obj={o:.4f} (canonical 7.0)  "
                      f"fs0324(heldout)={r['fs_0324']/base['fs_0324']:.3f}  "
                      f"[{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, objs)
    json.dump(best, open(OUT, "w"), indent=1)
    print(f"DONE obj={best['obj']:.4f} (canonical 7.0) nev={nev} saved fourbar_hybrid_best.json", flush=True)
    for g in OBJ_GROUPS + ["fs_0324"]:
        print(f"  {g:<22} rel {best['res'][g]/base[g]:.3f}", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
