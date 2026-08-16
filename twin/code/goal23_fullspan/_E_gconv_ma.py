# -*- coding: utf-8 -*-
"""_E_gconv_ma — 그래프 규약(점프 창 통짜 ModeA)으로 fs15 vs fs16 재집계 (정본 plot_ma 경로 미러).
CLI: FS_PRESLIDE=... python _E_gconv_ma.py <태그>
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD
import fs_compare_plot as CP          # 훅 면제 (정본 import)
import fs_runner as FR

OUT = {}
ft = FR.fs_twin(); SP = FR._sess_params()
for sess, p, g, cvt, ho in FD.registry():
    if cvt:
        continue
    try:
        d = FD.load2(p); seg = FD.segment(d)
        d["_sess"] = sess; d["_fold"] = p
        t = d["t"]; pw = FD.plot_window(p, d)
        if pw is None:
            continue
        m = (t >= pw[0]) & (t <= pw[1])
        if m.sum() < 30:
            continue
        i0 = int(np.argmax(m)); tg = t[m] - t[i0]
        sp = SP.get(sess, dict(bias1=0.0, knee_deep=None))
        Lf = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=sp["bias1"],
                                knee_deep=sp["knee_deep"], fade=True)
        if Lf is None:
            print(f"{sess}/{p.name}: 재생실패", flush=True); continue
        gf = lambda k: np.interp(tg, Lf["t"], Lf[k])
        fs = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2"), gf("s1"), gf("s2")]
        meas = {k: d[k][m] for k, _ in CP.CH}
        rr = [float(np.sqrt(np.mean((meas[k] - v) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1))
              for (k, _), v in zip(CP.CH, fs)]
        OUT.setdefault(sess, []).append(rr)
        print(f"{sess}/{p.name}: OK", flush=True)
    except Exception as ex:
        print(f"{sess}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
tag = sys.argv[1] if len(sys.argv) > 1 else "x"
json.dump(OUT, open(HERE / f"_E_gconvma_{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
