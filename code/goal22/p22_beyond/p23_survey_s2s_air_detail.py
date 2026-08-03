# -*- coding: utf-8 -*-
"""p23_survey detail — s2s_air 0319: cycle count, per-cycle repeatability (l_i drift proxy),
knee desiredTorque NaN check."""
import sys, io
import numpy as np
import pandas as pd
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
D = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_03_19/position/sit2stand_air")

hip = pd.read_excel(D / "hip.xlsx")
knee = pd.read_excel(D / "knee.xlsx")
t = hip["Time"].values
q2 = knee["currentAngle"].values
qd2 = knee["desiredAngle"].values

# desiredTorque NaN check
for nm, df in (("hip", hip), ("knee", knee)):
    dtau = df["desiredTorque"].values.astype(float)
    print(f"{nm} desiredTorque: n_nan={int(np.isnan(dtau).sum())}/{len(dtau)} "
          f"n_zero={int((dtau == 0).sum())}")

# cycle detection from desiredAngle square wave (stand=-1.571, sit=-2.532)
mid = (qd2.max() + qd2.min()) / 2
hi = qd2 > mid
edges = np.where(np.diff(hi.astype(int)) != 0)[0]
rise = np.where(np.diff(hi.astype(int)) == 1)[0]
print(f"\nq2_des levels: min={qd2.min():.3f} max={qd2.max():.3f}  edges={len(edges)} "
      f"sit->stand transitions={len(rise)}")

# per sit->stand cycle: reached q2 extremes + settle value (l_i drift proxy:
# crank->knee mapping drift would shift the reached stand/sit angles over time)
rows = []
for i, r in enumerate(rise):
    j0 = r
    j1 = rise[i + 1] if i + 1 < len(rise) else len(q2) - 1
    seg = q2[j0:j1]
    if len(seg) < 100:
        continue
    rows.append((t[j0], float(seg.max()), float(seg.min())))
print("cycle  t_start   q2_max(stand)  q2_min(sit)")
for i, (ts, qmx, qmn) in enumerate(rows):
    print(f"{i:3d}  {ts:8.1f}  {qmx:12.4f}  {qmn:12.4f}")
if rows:
    qmx = np.array([r[1] for r in rows]); qmn = np.array([r[2] for r in rows])
    print(f"\nstand q2_max: mean={qmx.mean():.4f} std={qmx.std():.4f} drift(last-first)={qmx[-1]-qmx[0]:+.4f}")
    print(f"sit   q2_min: mean={qmn.mean():.4f} std={qmn.std():.4f} drift(last-first)={qmn[-1]-qmn[0]:+.4f}")
