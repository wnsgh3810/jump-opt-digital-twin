"""P8 — direct test of the 'stuck in a local minimum' hypothesis.

If canonical were a LOCAL optimum with a better basin elsewhere, uniform random
sampling of the FULL 26-D bounds box (far from canonical) should occasionally
land in that basin, and CMA descending from the best random point should
converge somewhere better (and generalize: held-out fs_0324 <= 1).

Phase 1: N uniform samples in [LOb, HIb]  -> distribution of hybrid obj.
Phase 2: CMA (sigma 0.20, wide) from the best random point, 400 evals.
Report: best obj found anywhere, its held-out, param distance to canonical.
"""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
from g21_fourbar_hybrid import winit, eval_hybrid, OBJ_GROUPS, _G


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = _G["FR"]
    can = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    x_can = np.array(can["x"]); LOb, HIb = FR.LOb, FR.HIb
    base = json.load(open(REPO / "code/goal21/fourbar_hybrid_best.json"))["base"]
    pool = mp.Pool(10, initializer=winit)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in OBJ_GROUPS), r["fs_0324"] / base["fs_0324"])

    rng = np.random.default_rng(3)
    N = 1000
    X = LOb + rng.random((N, len(LOb))) * (HIb - LOb)
    objs = np.full(N, 99.0); hos = np.full(N, 99.0)
    for i0 in range(0, N, 100):
        rs = pool.map(eval_hybrid, [x for x in X[i0:i0 + 100]])
        for j, r in enumerate(rs):
            objs[i0 + j], hos[i0 + j] = obj_of(r)
        print(f"phase1 {i0+100}/{N}  running-min={objs[:i0+100].min():.3f}", flush=True)
    order = np.argsort(objs)
    print("\n[PHASE1] uniform box sampling vs canonical obj=7.0:")
    print(f"  best 5: " + "  ".join(f"{objs[i]:.3f}(ho {hos[i]:.2f})" for i in order[:5]))
    print(f"  beat canonical (<7.0): {(objs < 7.0).sum()}/{N}")
    print(f"  median {np.median(objs[objs < 90]):.2f}", flush=True)

    xb = X[order[0]]
    x0n = (xb - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n.tolist(), 0.20,
                                  {"bounds": [0, 1], "maxfevals": 400, "popsize": 20,
                                   "seed": 5, "verbose": -9})
    best = dict(obj=float(objs[order[0]]), ho=float(hos[order[0]]), x=xb.tolist())
    nev = 0
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval_hybrid, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
        es.tell(sols, oo)
    dist_can = float(np.linalg.norm((np.array(best["x"]) - x_can) / (HIb - LOb)))
    print(f"\n[PHASE2] CMA from best random point ({nev} evals):")
    print(f"  final obj {best['obj']:.4f} (canonical 7.0)   held-out {best['ho']:.3f}")
    print(f"  normalized param distance to canonical: {dist_can:.3f} "
          f"(0=same point, ~1+=different corner of box)")
    json.dump(dict(phase1_best=[float(objs[i]) for i in order[:10]],
                   phase1_beat=int((objs < 7.0).sum()), N=N,
                   phase2=best, dist_to_canonical=dist_can),
              open(REPO / "code/goal21/multistart_probe.json", "w"), indent=1)
    print("saved multistart_probe.json", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
