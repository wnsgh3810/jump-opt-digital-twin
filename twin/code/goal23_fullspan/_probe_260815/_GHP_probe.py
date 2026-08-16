# -*- coding: utf-8 -*-
"""_GHP_probe — 자료 정찰 (MuJoCo 없음): 네 경우의 l_i·창·크랭크 각도 분포 + 교환비 표."""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
HERE = str(Path(__file__).parent)
sys.path.insert(0, HERE)
sys.path.insert(0, str(Path(HERE).parent / "goal22" / "p18_cvt"))
os.chdir(HERE)
import numpy as np
import fs_data as FD
from cvt_core import closure

print("=== 네 경우 정찰 ===")
for sub, pay, cvt in FD.S2S_CASES:
    d = FD.load_s2s(sub)
    W = FD.air_windows(d, nwin=4, wmax=2.0)
    t = d["t"]
    cr = np.degrees(d["q2"])
    tot = 0
    for w0, w1 in W:
        m = (t >= w0) & (t <= w1)
        tot += int(m.sum())
    print(f"{sub:16s} pay={pay:4.1f} cvt={cvt} l_i={d['l_i']*1000:.3f}mm  n={len(t)}  "
          f"t={t[-1]:.3f}s dt={np.median(np.diff(t))*1000:.2f}ms")
    print(f"   창 {len(W)}개: " + " ".join(f"[{a:.2f},{b:.2f}]" for a, b in W) + f"  표본 {tot}")
    print(f"   크랭크 전체 {cr.min():.1f}~{cr.max():.1f}도 · 창 안 "
          + " ".join(f"{np.degrees(d['q2'][(t>=a)&(t<=b)]).min():.0f}~{np.degrees(d['q2'][(t>=a)&(t<=b)]).max():.0f}" for a, b in W))
    print(f"   무릎속도 |dq2| 중앙 {np.median(np.abs(d['dq2'])):.2f} rad/s")

print()
print("=== 교환비 r = dq_무릎/dq_크랭크 (cvt_core.closure) ===")
print(f"{'크랭크각[도]':>12s} " + " ".join(f"{li:>10.2f}mm" for li in (25.08, 25.19, 30.0)))
for ang in range(-180, 1, 10):
    row = []
    for li in (0.02508, 0.02519, 0.030):
        qk, qp, r = closure(np.radians(-ang), li)
        row.append(r)
    print(f"{ang:12d} " + " ".join(f"{x:12.4f}" for x in row))
