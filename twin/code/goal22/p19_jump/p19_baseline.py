# -*- coding: utf-8 -*-
"""P19 베이스라인 — {P16, P18b} × {A_fit, A_paper} 점프 τ-갭 전수 측정."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P

CONFIGS = {}


def make_configs():
    X = P.X37
    x16 = np.array(X[:32])
    x18 = np.array(X[:32]); x18[11] = P.W18[0]
    return {
        "P16_Afit":    (x16, float(X[36]), "crank", P.A_FIT,   0.0),
        "P16_Apaper":  (x16, float(X[36]), "crank", P.A_PAPER, 0.0),
        "P18b_Afit":   (x18, P.W18[1],     "calf",  P.A_FIT,   2.06),
        "P18b_Apaper": (x18, P.W18[1],     "calf",  P.A_PAPER, 2.06),
    }


def run_config(name):
    if not P.J._P:
        P.winit()
    x32, ref, sp, A, pre = make_configs()[name]
    rows = P.eval_cl_nocvt(x32, ref, sp, A, pre)
    rows += P.eval_cl_cvt(x32, ref, sp, A)
    s = P.summarize(rows)
    ma = P.eval_modeA_jump(x32, ref, sp, A)
    return name, s, ma, rows


def main():
    import multiprocessing as mp
    pool = mp.Pool(4, initializer=P.winit)
    out = {}
    for name, s, ma, rows in pool.imap_unordered(run_config, list(make_configs())):
        out[name] = dict(summary=s, modeA={k: float(v) for k, v in ma.items()}, rows=rows)
        print(f"[{name}] FIT gap {s['FIT_ALL']['gap']*100:.1f}% "
              f"(hip {s['FIT_ALL']['g1']*100:.1f} / knee {s['FIT_ALL']['g2']*100:.1f}) "
              f"HO {s.get('HELDOUT', {}).get('gap', float('nan'))*100:.1f}%", flush=True)
        for ds, v in s.items():
            if ds.startswith("jump"):
                print(f"    {ds:22s} hip {v['g1']*100:5.1f}% knee {v['g2']*100:5.1f}% "
                      f"q2 {v['q2']:.3f} (n={v['n']})", flush=True)
    pool.close(); pool.join()
    json.dump(out, open(HERE / "p19_baseline.json", "w"), indent=1)
    print("saved p19_baseline.json", flush=True)


if __name__ == "__main__":
    main()
