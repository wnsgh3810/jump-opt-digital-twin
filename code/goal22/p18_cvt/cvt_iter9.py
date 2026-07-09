# -*- coding: utf-8 -*-
"""P18b iter9 — 화해 적합: spring@calf 약화 + 세션 o_t2 공동 CMA (문제 3그룹 목적).
x = [stiff_knee, springref, o_0602, o_0421, o_s2s], 목적 = 3그룹 정규화 평균."""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from cvt_iter5 import build_flip_variant

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
SD = -0.0015
DS3 = ("jump_position_0421", "jump_0602", "s2s_gnd_0319")
BASE = {"w_0421": 2514.1, "w_0602": 2539.3, "w_s2s": 5371.9}
LO = np.array([0.0, 1.6, 0.0, 0.0, 0.0])
HI = np.array([1.6, 2.6, 5.0, 3.0, 3.0])
FIX_T = {"jump_0424": 3.0, "jump_0324": 3.0}


def eval3(v):
    stiff, ref, o602, o421, os2s = v
    if not J._P:
        J.winit()
    P12 = J._P["P12"]
    x32 = np.array(X37[:32]); x32[11] = stiff
    A = np.array(X37[32:36])
    dd = dict(zip(J._P["FR"].NAMES, x32[:26]))
    model, _ = build_flip_variant(x32, ref, "calf")
    ot2 = {"jump_0602": o602, "jump_position_0421": o421, "s2s_gnd_0319": os2s}
    res = {}
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        if ds not in DS3:
            continue
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        t = tr["pp"]["t"]
        th = -J.ahat(A, tr["raw1"], tr["v1"])
        tk = -(J.ahat(A, tr["raw2"], tr["v2"]) + ot2[ds])
        ppv = dict(tr["pp"], tau_h=np.interp(t - SD, t, th), tau_k=np.interp(t - SD, t, tk))
        ppo = P12._G["sv"](ppv, o1, o2)
        res[P12.GKEY[ds]] = res.get(P12.GKEY[ds], 0.0) + P12.eval_windows(model, ppo, None)
    return (res["w_0421"] / BASE["w_0421"] + res["w_0602"] / BASE["w_0602"]
            + res["w_s2s"] / BASE["w_s2s"]) / 3.0, res


def eval3_obj(v):
    try:
        return eval3(v)[0]
    except Exception:
        return 9.9


def main():
    import multiprocessing as mp
    import cma
    pool = mp.Pool(10, initializer=J.winit)
    x0 = np.array([0.5, 2.07, 3.0, 1.5, 1.2])
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.25,
                                  {"bounds": [0, 1], "maxfevals": 220, "popsize": 10,
                                   "seed": 7, "verbose": -9})
    best = (9.9, None); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LO + np.array(s) * (HI - LO) for s in sols]
        oo = pool.map(eval3_obj, xs)
        for x, o in zip(xs, oo):
            nev += 1
            if o < best[0]:
                best = (o, x)
                print(f"BEST nev={nev} obj={o:.3f} stiff={x[0]:.3f} ref={x[1]:.3f} "
                      f"o602={x[2]:.2f} o421={x[3]:.2f} os2s={x[4]:.2f} "
                      f"[{(time.time()-t0)/60:.1f}min]", flush=True)
        es.tell(sols, oo)
    o, x = best
    _, res = eval3(x) if J._P else (None, None)
    print(f"FINAL obj={o:.3f} x={[round(float(v),4) for v in x]}", flush=True)
    print(f"groups: w_0421={res['w_0421']:.0f}({res['w_0421']/BASE['w_0421']:.2f}) "
          f"w_0602={res['w_0602']:.0f}({res['w_0602']/BASE['w_0602']:.2f}) "
          f"w_s2s={res['w_s2s']:.0f}({res['w_s2s']/BASE['w_s2s']:.2f})", flush=True)
    json.dump(dict(obj=float(o), x=[float(v) for v in x],
                   groups={k: float(vv) for k, vv in res.items()}, fix=FIX_T),
              open(HERE / "p18b_iter9.json", "w"), indent=1)
    print("saved p18b_iter9.json", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
