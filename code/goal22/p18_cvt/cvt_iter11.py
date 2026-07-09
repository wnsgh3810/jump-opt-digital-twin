# -*- coding: utf-8 -*-
"""P18b iter11 — 최종 통합 CMA: 삼중 목적 (평행사변형 G7 + 0429).
x = [stiff, ref, o2_0602, o2_0421, o2_s2s, o2_0424, o2_0324, o1_s2s, o1_0421]
spring@calf (stiff=0이면 none과 동일), fric@crank.
J = 0.5·mean(G7 ratio) + 0.5·(0429 score / 243.7)   [기준 = P16 crank]
0429 fit은 5-trial 부분집합, 최종 검증은 10 전체."""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from cvt_iter10 import evalG7, G7

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
BASE_G7 = {"w_0421": 2514.1, "w_0424": 3558.4, "w_0602": 2539.3, "w_0324": 2010.2,
           "w_s2s": 5371.9, "fs_0424": 1069.9, "fs_0602": 589.9, "habs": 0.2686}
BASE_429 = 243.7
SUB5 = ["60_0.75_60_2", "90_1.5_90_2.5", "120_2_120_2", "120_2.2_200_2.8",
        "150_2.2_500_4"]
LO = np.array([0.0, 1.6, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5])
HI = np.array([1.4, 2.6,  4.0,  3.0,  4.0,  4.0,  4.0,  3.0,  2.0])
K_EFF = None


def sc429(stiff, ref, ot2_0429=0.0, subs=SUB5):
    from cvt_run2 import build_cvt2, metrics2, score, sim_run
    from cvt_core import load_0429
    global K_EFF
    if K_EFF is None:
        A = np.array(X37[32:36])
        K_EFF = float((J.ahat(A, np.array([10.0]), np.array([0.0]))
                       - J.ahat(A, np.array([9.0]), np.array([0.0])))[0])
    x32 = np.array(X37[:32]); x32[11] = max(stiff, 1e-6)
    sp = "calf" if stiff > 1e-3 else "none"
    scs = []
    for sub in subs:
        d = load_0429(sub)
        if abs(ot2_0429) > 1e-9:
            d = dict(d); d["traw2"] = d["traw2"] + ot2_0429 / K_EFF
        model, _ = build_cvt2(d["l_i"], sp, "crank", x32=x32, ref=ref)
        L, _ = sim_run(model, d, d["l_i"], "A",
                       o1=3.14 * np.pi / 180, o2=-3.0 * np.pi / 180)
        if L is None:
            return 9e3, None
        scs.append(dict(score=score(metrics2(d, L, 3.14 * np.pi / 180,
                                             -3.0 * np.pi / 180)),
                        **metrics2(d, L, 3.14 * np.pi / 180, -3.0 * np.pi / 180)))
    g = lambda k: float(np.mean([s[k] for s in scs]))
    return g("score"), dict(q2=g("q2"), dq2=g("dq2"), h_gap=g("h") - g("h_real"))


def eval_full(v):
    try:
        stiff, ref, o602, o421, os2s, o424, o324, o1s2s, o1_421 = v
        if not J._P:
            J.winit()
        ot2 = {"jump_0602": o602, "jump_position_0421": o421, "s2s": os2s,
               "jump_0424": o424, "jump_0324": o324}
        ot1 = {"s2s": o1s2s, "jump_position_0421": o1_421}
        x32 = np.array(X37[:32]); x32[11] = max(stiff, 1e-6)
        sp = "calf" if stiff > 1e-3 else "none"
        r = evalG7(x32, ref, sp, ot2, ot1)
        jg = np.mean([r[g] / BASE_G7[g] for g in G7])
        s429, _ = sc429(stiff, ref)
        return 0.5 * jg + 0.5 * s429 / BASE_429, jg, s429
    except Exception:
        return 99.0, 99.0, 9e9


def eval_obj(v):
    return eval_full(v)[0]


def main():
    import multiprocessing as mp
    import cma
    pool = mp.Pool(10, initializer=J.winit)
    x0 = np.array([0.4, 1.95, 1.5, 0.8, 3.0, 2.0, 2.0, 1.5, 0.5])
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.22,
                                  {"bounds": [0, 1], "maxfevals": 300, "popsize": 10,
                                   "seed": 11, "verbose": -9})
    best = (99.0, None); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LO + np.array(s) * (HI - LO) for s in sols]
        rs = pool.map(eval_full, xs)
        oo = [r[0] for r in rs]
        for x, (o, jg, s4) in zip(xs, rs):
            nev += 1
            if o < best[0]:
                best = (o, x)
                print(f"BEST nev={nev} J={o:.3f} (G7 {jg:.3f} | 0429 {s4:.0f}) "
                      f"stiff={x[0]:.3f} ref={x[1]:.2f} "
                      f"o2=[{x[2]:.2f},{x[3]:.2f},{x[4]:.2f},{x[5]:.2f},{x[6]:.2f}] "
                      f"o1=[{x[7]:.2f},{x[8]:.2f}] [{(time.time()-t0)/60:.1f}m]",
                      flush=True)
        es.tell(sols, oo)
    o, x = best
    json.dump(dict(obj=float(o), x=[float(v) for v in x]),
              open(HERE / "p18b_iter11.json", "w"), indent=1)
    print(f"FINAL J={o:.3f} x={[round(float(v), 3) for v in x]}", flush=True)
    print("saved p18b_iter11.json", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
