"""P14 적합 — 이중 심판 동시 최소화, x = 32 모델 + 4 a_hat 계수.

J(x) = 0.5·[ JA(x)/JA(x0) + JC(x)/JC(x0) ]
  JA = Mode A 하이브리드 그룹합 (P13h+paper 기준으로 그룹별 정규화 후 합)
  JC = 폐루프 τ-채널 심판 (fit 데이터셋 평균, 기준 정규화 내장 ≈1.0)
게이트: Mode A fs_0324 비 ≤1.05 AND CL 0324 ≤1.05.
a_hat 바운드: A1 [1.00,1.35] (paper 1.156 ±~15%), A2 [0,1.3e-3], A3 [0,0.45], A4 [0,0.10].
사용: python p14_fit.py [maxfev=1000] [sigma=0.05]
"""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import p14_judge as J
import g21_p13_linkage as P13
import g21_p13e_honest as PH

MAXFEV = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
SIGMA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
OUT = HERE / "p14_result.json"
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]


def winit():
    J.winit()


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = J._P["FR"]
    h = json.load(open(HERE.parent / "fourbar_p13h_candidate.json"))
    NAMES = h["names"] + ["A1", "A2", "A3", "A4"]
    x0 = np.concatenate([np.array(h["x"]), J.A_PAPER])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy(),
                          [1.00, 0.0, 0.0, 0.0]])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy(),
                          [1.35, 1.3e-3, 0.45, 0.10]])
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
    r0 = J.eval36(x0)
    baseA = {g: r0["A"][g] for g in G7}
    ho0A = r0["A"]["fs_0324"]
    JC0 = r0["C"]; Cg0 = r0["Cg"]
    print(f"BASE(P13h+paper): JA그룹 정규화 기준 확보, JC={JC0:.4f} CLgate0={Cg0:.4f} "
          f"fs0324={ho0A:.1f}", flush=True)

    def score(r):
        if r is None:
            return 99.0, 99.0, 99.0
        ja = sum(r["A"][g] / baseA[g] for g in G7) / len(G7)
        jc = r["C"] / JC0
        hoA = r["A"]["fs_0324"] / ho0A
        hoC = r["Cg"] / Cg0
        return 0.5 * (ja + jc), hoA, hoC

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), SIGMA,
                                  {"bounds": [0, 1], "maxfevals": MAXFEV, "popsize": 20,
                                   "seed": 101, "verbose": -9})
    cands = []; best = dict(obj=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(J.eval36, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, hoA, hoC = score(r); oo.append(o); nev += 1
            if o < 90 and hoA <= 1.10 and hoC <= 1.10:
                cands.append(dict(obj=float(o), hoA=float(hoA), hoC=float(hoC),
                                  x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), hoA=float(hoA), hoC=float(hoC),
                            x=[float(v) for v in x])
                A = x[32:36]
                print(f"BEST nev={nev} obj={o:.4f} hoA={hoA:.3f} hoC={hoC:.3f} "
                      f"A=[{A[0]:.3f},{A[1]:.2e},{A[2]:.3f},{A[3]:.3f}] "
                      f"[{(time.time()-t0)/60:.1f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["hoA"] <= 1.05 and c["hoC"] <= 1.05 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P14 DONE nev={nev} [{(time.time()-t0)/60:.1f}min] " +
          (f"selected obj={sel['obj']:.4f} hoA={sel['hoA']:.3f} hoC={sel['hoC']:.3f}"
           if sel else "none passed dual gate"), flush=True)
    if sel:
        xs_ = np.array(sel["x"])
        A = xs_[32:36]
        print(f"\na_hat: paper {J.A_PAPER.round(4).tolist()} -> "
              f"[{A[0]:.4f}, {A[1]:.2e}, {A[2]:.4f}, {A[3]:.4f}]", flush=True)
        print(f"  유효 변환게인 A1*CF: {J.A_PAPER[0]*J.CF:.3f} -> {A[0]*J.CF:.3f}", flush=True)
        for n in ["fv_hip", "fc_hip", "fv_knee", "fc_knee", "stiff_knee", "arm_knee",
                  "M_c", "M_thigh", "s_ip", "d_kneep"]:
            print(f"  {n:<11} {x0[idx(n)]:.4f} -> {xs_[idx(n)]:.4f}", flush=True)
        json.dump(dict(CANDIDATE="P14 — dual-judge + free a_hat (2026-07-09)",
                       sens_delay=-0.0015, obj=sel["obj"], hoA=sel["hoA"], hoC=sel["hoC"],
                       A_HAT=[float(v) for v in A], names=NAMES, x=sel["x"]),
                  open(HERE / "fourbar_p14_candidate.json", "w"), indent=1)
    json.dump(dict(base=dict(JC=JC0, Cg=Cg0, fs0324=float(ho0A)), selected=sel,
                   n_cands=len(cands)), open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
