"""P8d — 보정된 계측(sens_delay=-1.5ms) 하 최종 재적합 (W_DQ=150, P13f warm).
계측 정렬 보정을 고정하고 파라미터가 재배치되도록 CMA 1400 evals. 케이지/게이트 동일."""
import json, time
import numpy as np
from pathlib import Path
from g22_p8b_axes import winit as winit0, eval_ax
import g21_p13_linkage as P13

SD = -0.0015
OUT = Path(__file__).parent / "p8d_refit_sd.json"


def winit():
    P12 = winit0()
    P12._G["MS"].W_DQ = 150.0
    return P12


def eval_sd(x):
    return eval_ax((x, {"sens_delay": SD}))


def main():
    import multiprocessing as mp
    import cma
    P12 = winit()
    FR = P12._G["FR"]
    G7 = P12.OBJ_GROUPS
    f = json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))
    NAMES = f["names"]
    x0 = np.array(f["x"])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
    import g21_p13e_honest as PH
    LOb[idx("M_p")] = PH.MP_PHYS - 5e-4; HIb[idx("M_p")] = PH.MP_PHYS + 5e-4
    LOb[idx("M_calf")] = 0.97; HIb[idx("M_calf")] = 1.03
    LOb[idx("M_thigh")] = 0.92; HIb[idx("M_thigh")] = 1.08
    LOb[idx("M_c")] = 0.45; HIb[idx("M_c")] = 1.00
    LOb[idx("M_base")] = 0.999; HIb[idx("M_base")] = 1.001
    for n in NAMES:
        if n.startswith("o1_") or n.startswith("o2_"):
            LOb[idx(n)] = -0.0524; HIb[idx(n)] = 0.0524
    LOb[idx("arm_knee")] = 0.0005; LOb[idx("fc_knee")] = 0.0
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
    base = eval_sd(x0)
    print("BASE(P13f+sd-1.5ms, W_DQ=150):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.05,
                                  {"bounds": [0, 1], "maxfevals": 1400, "popsize": 20,
                                   "seed": 81, "verbose": -9})
    cands = []; best = dict(obj=8.0, ho=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval_sd, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.08:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} [{(time.time()-t0)/60:.1f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P8d DONE nev={nev} " + (f"selected obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "none passed"), flush=True)
    json.dump(dict(sens_delay=SD, w_dq=150, selected=sel, names=NAMES,
                   base={k: float(v) for k, v in base.items()}), open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
