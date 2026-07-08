"""P13i 재적합 — 폐루프 τ-채널 심판 (p13i_judge), P13h warm-start, 물리 케이지 동일.
사용: python p13i_fit.py [maxfev=800] [sigma=0.05]
게이트: held-out 0324 폐루프 점수 ≤ 1.05 (P13h 기준=1.0). canonical 미교체 — 결과는 이 폴더에.
"""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import p13i_judge as J
import g21_p13_linkage as P13
import g21_p13e_honest as PH

MAXFEV = int(sys.argv[1]) if len(sys.argv) > 1 else 800
SIGMA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
OUT = HERE / "p13i_result.json"


def winit():
    J.winit()


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = J._J["FR"]
    h = json.load(open(HERE.parent / "fourbar_p13h_candidate.json"))
    NAMES = h["names"]
    x0 = np.array(h["x"])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
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
    o0, ho0 = J.eval32_cl(x0)
    print(f"BASE(P13h, 폐루프 심판): obj={o0:.4f} gate_0324={ho0:.4f} (기대 ≈1.0)", flush=True)

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), SIGMA,
                                  {"bounds": [0, 1], "maxfevals": MAXFEV, "popsize": 16,
                                   "seed": 91, "verbose": -9})
    cands = []; best = dict(obj=float(o0), ho=float(ho0), x=x0.tolist())
    nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(J.eval32_cl, xs)
        oo = []
        for x, (o, ho) in zip(xs, rs):
            oo.append(o); nev += 1
            if o < 90 and ho <= 1.10:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} gate={ho:.3f} [{(time.time()-t0)/60:.1f}min]",
                      flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.05 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P13i DONE nev={nev} [{(time.time()-t0)/60:.1f}min] " +
          (f"selected obj={sel['obj']:.4f} gate={sel['ho']:.3f}" if sel else "none passed gate"),
          flush=True)
    if sel:
        xs_ = np.array(sel["x"])
        print("주요 파라미터 이동 (P13h -> P13i):", flush=True)
        for n in ["M_thigh", "M_calf", "M_c", "m_foot", "fv_hip", "fc_hip", "fv_knee", "fc_knee",
                  "stiff_knee", "arm_knee", "s_ic", "s_ip", "d_kneep", "solref_tc", "imp0"]:
            print(f"  {n:<11} {x0[idx(n)]:.4f} -> {xs_[idx(n)]:.4f}", flush=True)
        json.dump(dict(CANDIDATE="P13i — closed-loop tau-channel judge refit (2026-07-09)",
                       judge="label-gain closed-loop, ch-normalized(P13h), phase w E0.5/P2/F1, heldout 0324",
                       sens_delay=-0.0015, obj=sel["obj"], gate=sel["ho"],
                       names=NAMES, x=sel["x"]),
                  open(HERE / "fourbar_p13i_candidate.json", "w"), indent=1)
    json.dump(dict(base=dict(obj=o0, ho=ho0), selected=sel, n_cands=len(cands)),
              open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
