"""P13b — 바운드 확장 재적합 (boundary-chasing 프로토콜).
P13 선택해에서 레일링한 축 확장: M_p 2.5→4.5, com_dz_th 0.10→0.20,
arm_knee LO 0.002→0.0005, fc_knee LO 0.05→0.0, offsets ±12°→±17°.
warm = P13 selected. 관찰 목표: M_p가 내부에 안착하는가(물리값) 계속 도주하는가(구조 흡수)."""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13_linkage as P13


def main():
    import multiprocessing as mp
    import cma
    P13.winit()
    P12 = P13._M["P12"]
    FR = P12._G["FR"]
    prev = json.load(open(REPO / "code/goal21/p13_linkage.json"))
    NAMES = prev["names"]
    x0 = np.array(prev["selected"]["x"])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
    HIb[idx("M_p")] = 4.5
    HIb[idx("com_dz_th")] = 0.20
    LOb[idx("arm_knee")] = 0.0005
    LOb[idx("fc_knee")] = 0.0
    for n in NAMES:
        if n.startswith("o1_") or n.startswith("o2_"):
            LOb[idx(n)] = -0.30; HIb[idx(n)] = 0.30
    pool = mp.Pool(10, initializer=P13.winit)
    base = P13.eval32(x0)
    G7 = P12.OBJ_GROUPS
    print("BASE(P13-selected):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.07,
                                  {"bounds": [0, 1], "maxfevals": 1200, "popsize": 20,
                                   "seed": 47, "verbose": -9})
    cands = []; best = dict(obj=8.0, ho=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(P13.eval32, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.05:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                xi = x
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} M_p={xi[idx('M_p')]:.3f} "
                      f"dzth={xi[idx('com_dz_th')]:.3f} fck={xi[idx('fc_knee')]:.3f} "
                      f"o2_0324={np.degrees(xi[idx('o2_0324')]):.1f}deg [{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P13b DONE nev={nev}  selected: obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "P13b DONE: none passed", flush=True)
    if sel:
        xs = np.array(sel["x"])
        print("rail check (widened axes):", flush=True)
        for n in ["M_p", "com_dz_th", "arm_knee", "fc_knee", "o2_0324", "o1_0421", "o2_0424"]:
            i = idx(n)
            v = xs[i]
            pos = (v - LOb[i]) / (HIb[i] - LOb[i])
            print(f"  {n:<11} {v:8.4f}  (bound-pos {pos:.2f})", flush=True)
        print("linkage:", " ".join(f"{n}={v:.3f}" for n, v in zip(P13.N6, xs[26:])), flush=True)
    json.dump(dict(selected=sel, names=NAMES,
                   lo=[float(v) for v in LOb], hi=[float(v) for v in HIb],
                   base={k: float(v) for k, v in base.items()}),
              open(REPO / "code/goal21/p13b_widen.json", "w"), indent=1)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
