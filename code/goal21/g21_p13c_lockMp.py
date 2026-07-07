"""P13c — M_p를 실측(150 g / CAD 136.6 g = 1.0983)에 LOCK하고 재적합.
관찰: ① 물리 M_p의 성능 비용 ② 보상이 흐르는 곳(M_c? com? offsets?) ③ held-out."""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13_linkage as P13

MP_PHYS = 0.150 / 0.13657     # = 1.0983


def main():
    import multiprocessing as mp
    import cma
    P13.winit()
    P12 = P13._M["P12"]
    FR = P12._G["FR"]
    prev = json.load(open(REPO / "code/goal21/fourbar_flip_canonical.json"))
    NAMES = prev["names"] + P13.N6
    x0 = np.concatenate([np.array(prev["x"]), P13.DEF6])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
    i_mp = idx("M_p")
    x0[i_mp] = MP_PHYS
    LOb[i_mp] = MP_PHYS - 5e-4; HIb[i_mp] = MP_PHYS + 5e-4   # LOCK
    HIb[idx("com_dz_th")] = 0.20
    LOb[idx("arm_knee")] = 0.0005
    LOb[idx("fc_knee")] = 0.0
    pool = mp.Pool(10, initializer=P13.winit)
    base = P13.eval32(x0)                       # M_p 물리 고정 상태의 출발점
    ref = P13.eval32(np.concatenate([np.array(prev["x"]), P13.DEF6]))  # P10-selected (M_p 1.82)
    G7 = P12.OBJ_GROUPS
    o_ref = sum(base[g] / base[g] for g in G7)
    print("BASE(M_p locked 1.098):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)
    cost = sum(base[g] / ref[g] for g in G7)
    print(f"물리 M_p의 즉시 비용: P10-selected 대비 obj x{cost/8.0*8.0/8.0:.4f} -> "
          f"{sum(base[g]/ref[g] for g in G7):.4f} (8.0=동일)", flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.07,
                                  {"bounds": [0, 1], "maxfevals": 1200, "popsize": 20,
                                   "seed": 53, "verbose": -9})
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
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} M_c={x[idx('M_c')]:.3f} "
                      f"M_calf={x[idx('M_calf')]:.3f} s_ip={x[idx('s_ip')]:.3f} "
                      f"dzca={x[idx('com_dz_ca')]:.3f} [{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P13c DONE nev={nev}  selected: obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "P13c DONE: none passed", flush=True)
    if sel:
        xs_ = np.array(sel["x"]); xp = np.concatenate([np.array(prev["x"]), P13.DEF6])
        print("보상 흐름 (P10-selected -> P13c, 변화 큰 순):", flush=True)
        moves = []
        for i, n in enumerate(NAMES):
            span = HIb[i] - LOb[i]
            if span > 1e-6 and abs(xs_[i] - xp[i]) / span > 0.04:
                moves.append((abs(xs_[i] - xp[i]) / span, n, xp[i], xs_[i]))
        for _, n, a, b in sorted(moves, reverse=True)[:12]:
            print(f"  {n:<11} {a:8.4f} -> {b:8.4f}", flush=True)
    json.dump(dict(selected=sel, names=NAMES, mp_locked=MP_PHYS,
                   base={k: float(v) for k, v in base.items()}),
              open(REPO / "code/goal21/p13c_lockMp.json", "w"), indent=1)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()

