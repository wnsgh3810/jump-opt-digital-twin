"""P8c — sens_delay 정밀 스캔 on P13f (P8b KEEP 후보 확정용)."""
import json
import numpy as np
from pathlib import Path
from g22_p8b_axes import winit, eval_ax


def main():
    import multiprocessing as mp
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    x_f = np.array(json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))["x"])
    pool = mp.Pool(10, initializer=winit)
    base = eval_ax((x_f, {}))
    VALS = [-0.0035, -0.003, -0.0025, -0.002, -0.0015, -0.001, -0.0005]
    rs = pool.map(eval_ax, [(x_f, {"sens_delay": v}) for v in VALS])
    best = (None, 99.0)
    out = []
    for v, r in zip(VALS, rs):
        o = sum(r[g] / base[g] for g in G7)
        ho = r["fs_0324"] / base["fs_0324"]
        out.append(dict(v=v, obj=float(o), ho=float(ho), habs=float(r["habs"] / base["habs"])))
        print(f"sens_delay={v*1e3:+.1f}ms: obj={o:.4f} ho={ho:.3f} habs={r['habs']/base['habs']:.3f}",
              flush=True)
        if o < best[1] and ho <= 1.0:
            best = (v, o)
    print("BEST:", best, flush=True)
    json.dump(dict(rows=out, best=best[0]), open(Path(__file__).parent / "p8c_sensdelay.json", "w"))
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
