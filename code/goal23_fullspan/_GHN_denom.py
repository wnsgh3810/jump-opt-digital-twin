# -*- coding: utf-8 -*-
"""'21%' 가 눈으로 본 것과 안 맞는 이유 — **분모를 무엇으로 나눴나**.
   사람 눈은 '축 범위 대비 얼마나 벌어졌나' 로 본다. 나는 표준편차로 나눴다."""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, r"C:/Users/junho/Documents/jump-opt-digital-twin/code/goal23_fullspan")
sys.path.insert(0, r"C:/Users/junho/Documents/jump-opt-digital-twin/code/bench")
import numpy as np
import _GHJ_hipvel as GJ
for k, v in GJ.STACK.items():
    os.environ.setdefault(k, v)
import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
from pathlib import Path

p = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_04_24/60_0.75_60_2")
d = FD.load2(p); seg = FD.segment(d)
d["_sess"] = "26.04.24"; d["_fold"] = p
r = CP.cl_pair(d, seg, (60, 0.75, 60, 2), "26.04.24")
t, (mo, mf), old, fs, m, cmd, pl = r
n = len(t)
print("26.04.24 / 60_0.75_60_2 (사용자 '아주 완벽')\n")
for i, (k, lab) in ((4, ("a1", "힙 토크")), (5, ("a2", "무릎 토크"))):
    real = np.asarray(mf[k]); sim = np.asarray(fs[i])
    err = real - sim
    rmse = float(np.sqrt(np.mean(err ** 2)))
    sd = float(np.std(real)); rng = float(real.max() - real.min())
    print(f"■ {lab}")
    print(f"   오차 RMSE            {rmse:6.2f} N·m")
    print(f"   실측 범위(최대-최소)  {rng:6.2f} N·m  ({real.min():.2f} ~ {real.max():.2f})")
    print(f"   실측 표준편차         {sd:6.2f} N·m")
    print(f"   → 범위로 나누면      {100*rmse/rng:5.1f}%   ← **눈으로 보는 것에 가깝다**")
    print(f"   → 표준편차로 나누면   {100*rmse/sd:5.1f}%   (내가 쓴 것)")
    # 오차가 어느 구간에서 오나 (5등분)
    q = np.array_split(np.arange(n), 5)
    con = [float(np.sum(err[ix] ** 2)) for ix in q]
    tot = sum(con)
    print(f"   오차가 어디서 오나(5등분, 제곱합 비중): "
          + " · ".join(f"{100*c/tot:.0f}%" for c in con))
    # 마지막 1/5 을 뺀 오차
    keep = np.concatenate(q[:4])
    print(f"   마지막 1/5(이륙 급변) 빼면 RMSE {float(np.sqrt(np.mean(err[keep]**2))):.2f} N·m "
          f"({100*float(np.sqrt(np.mean(err[keep]**2)))/rng:.1f}% of 범위)")
    print()
