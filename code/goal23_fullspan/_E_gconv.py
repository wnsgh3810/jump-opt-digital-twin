# -*- coding: utf-8 -*-
"""_E_gconv — 그래프 규약(perf_plot_guard 6규칙)과 동일한 자로 fs15 vs fs16 재집계.
정본 fs_compare_plot.cl_pair(점프 창 + 실측 앵커 + 통짜)를 그대로 import해 사용 (훅 면제).
CLI: FS_PRESLIDE=... python _E_gconv.py <출력태그>
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD
import fs_compare_plot as CP

OUT = {}
for sess, p, g, cvt, ho in FD.registry():
    if cvt or not g:
        continue
    try:
        d = FD.load2(p); seg = FD.segment(d)
        d["_sess"] = sess; d["_fold"] = p   # main()과 동일 세팅 (cl_pair 요구)
        r = CP.cl_pair(d, seg, g, sess)
        if r is None:
            continue
        tt, meas, old, fs, m, cmd, pl = r
        rr = []
        for j, (k, _) in enumerate(CP.CH):
            e = meas[k][m] - fs[j][m]
            v = float(np.sqrt(np.mean(e ** 2)))
            rr.append(float(np.degrees(v)) if k in ("q1", "q2") else v)
        OUT.setdefault(sess, []).append(rr)
        print(f"{sess}/{p.name}: OK", flush=True)
    except Exception as ex:
        print(f"{sess}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
tag = sys.argv[1] if len(sys.argv) > 1 else "x"
json.dump(OUT, open(HERE / f"_E_gconv_{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n=== 그래프 규약 CL (창 평균) ===")
for s in sorted(OUT):
    a = np.mean(OUT[s], axis=0)
    print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
