"""GOAL22 P3 — P13f: dq-가중 재적합 (정직 물리 케이지의 (dq, h) 프런티어).

P13e와 동일한 물리 케이지·게이트, 목적의 W_DQ만 50→ARG로 상향해 dq-우선 해 확보.
산출: P13e(W_DQ=50) vs P13f 후보들의 창 dq/q + fs + habs 비교 → 프런티어 점.
사용법: python g22_p3_dqweight.py [W_DQ=150] [maxfev=1400]
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

W_DQ_NEW = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
MAXFEV = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
OUT = Path(__file__).parent / f"p3_dqw{int(W_DQ_NEW)}.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    P12._G["MS"].W_DQ = W_DQ_NEW      # 창+fs 점수의 dq 가중 상향


def eval32(x):
    if not P13._M:
        winit()
    return P13.eval32(x)


def main():
    import multiprocessing as mp
    import cma
    winit()
    P12 = P13._M["P12"]
    FR = P12._G["FR"]
    G7 = P12.OBJ_GROUPS
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    NAMES = can["names"]
    x0 = np.array(can["x"])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
    # ── P13e 물리 케이지 그대로 ──
    LOb[idx("M_p")] = PH.MP_PHYS - 5e-4; HIb[idx("M_p")] = PH.MP_PHYS + 5e-4
    LOb[idx("M_calf")] = 0.97; HIb[idx("M_calf")] = 1.03
    LOb[idx("M_thigh")] = 0.92; HIb[idx("M_thigh")] = 1.08
    LOb[idx("M_c")] = 0.45; HIb[idx("M_c")] = 1.00
    LOb[idx("M_base")] = 0.999; HIb[idx("M_base")] = 1.001
    for n in NAMES:
        if n.startswith("o1_") or n.startswith("o2_"):
            LOb[idx(n)] = -0.0524; HIb[idx(n)] = 0.0524
    LOb[idx("arm_knee")] = 0.0005
    LOb[idx("fc_knee")] = 0.0
    LOb[idx("m_foot")] = 0.0;  HIb[idx("m_foot")] = 0.010
    LOb[idx("I_thigh")] = 0.8; HIb[idx("I_thigh")] = 1.2
    LOb[idx("I_calf")] = 0.8;  HIb[idx("I_calf")] = 1.2
    LOb[idx("com_dz_th")] = -0.03; HIb[idx("com_dz_th")] = 0.03
    LOb[idx("com_dz_ca")] = -0.03; HIb[idx("com_dz_ca")] = 0.03
    LOb[idx("s_ic")] = 0.7; HIb[idx("s_ic")] = 1.4
    LOb[idx("s_ip")] = 0.7; HIb[idx("s_ip")] = 1.4
    LOb[idx("s_rc")] = 0.8; HIb[idx("s_rc")] = 1.2
    LOb[idx("s_rp")] = 0.8; HIb[idx("s_rp")] = 1.2
    x0 = np.clip(x0, LOb + 1e-9, HIb - 1e-9)
    pool = mp.Pool(10, initializer=winit)
    base = eval32(x0)     # P13e 시작점, 새 가중으로 잰 기준
    print(f"BASE(P13e, W_DQ={W_DQ_NEW}):",
          " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.07,
                                  {"bounds": [0, 1], "maxfevals": MAXFEV, "popsize": 20,
                                   "seed": 71, "verbose": -9})
    cands = []; best = dict(obj=float(len(G7)), ho=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval32, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.08:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} "
                      f"[{(time.time()-t0)/60:.1f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P3 DONE nev={nev} [{(time.time()-t0)/60:.1f}min] " +
          (f"selected obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel else "none passed ho<=1.0"),
          flush=True)
    if sel:
        xs_ = np.array(sel["x"])
        for n in ["M_thigh", "M_calf", "M_c", "m_foot", "fv_hip", "fc_hip", "fv_knee", "fc_knee",
                  "stiff_knee", "arm_knee", "s_ic", "s_ip", "d_kneep"]:
            print(f"  {n:<11} {x0[idx(n)]:.4f} -> {xs_[idx(n)]:.4f}", flush=True)
    json.dump(dict(w_dq=W_DQ_NEW, selected=sel, names=NAMES,
                   base={k: float(v) for k, v in base.items()}),
              open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
