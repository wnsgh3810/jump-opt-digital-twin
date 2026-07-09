# -*- coding: utf-8 -*-
"""P18b iter2 — spring@calf 확정 구성에서 세션 오프셋(o1,o2) 그리드 + fric 배치 재결정."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from cvt_run2 import build_cvt2, sim_run, metrics2, score
from cvt_core import load_0429, SUBS429
import p14_judge as J

D2R = np.pi / 180
GRID = [-3, -1.5, 0, 1.5, 3]


def run_cell(args):
    fric_at, o1d, o2d, sub = args
    if not J._P:
        J.winit()
    d = load_0429(sub)
    model, _ = build_cvt2(d["l_i"], "calf", fric_at)
    L, diag = sim_run(model, d, d["l_i"], "A", o1=o1d * D2R, o2=o2d * D2R)
    if L is None:
        return dict(fric=fric_at, o1=o1d, o2=o2d, sub=sub, score=1e9)
    m = metrics2(d, L, o1d * D2R, o2d * D2R)
    return dict(fric=fric_at, o1=o1d, o2=o2d, sub=sub, score=score(m), **m)


def main():
    import multiprocessing as mp
    jobs = [(f, o1, o2, s) for f in ("crank", "calf") for o1 in GRID for o2 in GRID
            for s in SUBS429]
    pool = mp.Pool(10, initializer=J.winit)
    res = list(pool.imap_unordered(run_cell, jobs, chunksize=4))
    pool.close(); pool.join()
    json.dump(res, open(HERE / "p18b_iter2.json", "w"))
    print(f"{'fric':6s} {'o1':>5} {'o2':>5} {'score':>7} {'q2':>6} {'dq2':>6} "
          f"{'dtoff':>7} {'h_gap':>7}")
    best = []
    for f in ("crank", "calf"):
        cells = []
        for o1 in GRID:
            for o2 in GRID:
                rs = [r for r in res if r["fric"] == f and r["o1"] == o1
                      and r["o2"] == o2 and r["score"] < 1e8]
                if len(rs) < 10:
                    continue
                g = lambda k: float(np.mean([r[k] for r in rs]))
                cells.append((g("score"), o1, o2, g("q2"), g("dq2"), g("dtoff"),
                              g("h") - g("h_real")))
        cells.sort()
        for c in cells[:4]:
            print(f"{f:6s} {c[1]:5.1f} {c[2]:5.1f} {c[0]:7.1f} {c[3]:6.3f} "
                  f"{c[4]:6.2f} {c[5]*1000:6.1f}ms {c[6]:+7.3f}", flush=True)
        best.append((f, cells[0]))
    print("BEST:", best, flush=True)


if __name__ == "__main__":
    main()
