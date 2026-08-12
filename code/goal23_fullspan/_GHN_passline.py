# -*- coding: utf-8 -*-
"""합격선 재산출 — 사용자 지적(08-12) 반영.
   ① 분모를 **실측이 실제로 오간 범위(최대-최소)** 로 (표준편차는 눈과 4.4배 어긋난다)
   ② 오차가 **이륙 급변 구간에 몰리는지** 분리해서 본다 (무릎 토크는 88% 가 거기서 온다)"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, r"C:/Users/junho/Documents/jump-opt-digital-twin/code/goal23_fullspan")
sys.path.insert(0, r"C:/Users/junho/Documents/jump-opt-digital-twin/code/bench")
import numpy as np
import _GHJ_hipvel as GJ
for k, v in GJ.STACK.items():
    os.environ.setdefault(k, v)
import fs_data as FD, fs_compare_plot as CP, fs_runner as FR, fs_cvt as FC

PERFECT = {("26.04.24", "60_0.75_60_2"), ("26.04.24", "60_1.5_60_1.5")}
BAD_K = {("26.04.24", "150_2.2_250_3"), ("26.04.24", "150_2.2_350_3.5"),
         ("26.04.24", "150_2.2_500_4"), ("26.07.23", "150_2.2_500_5")}
BAD_H = {("26.04.24", "150_2.2_250_3"), ("26.04.24", "120_2_120_2"),
         ("26.04.24", "120_2.2_150_2.5"), ("26.07.22", "150_3.3_500_5")}
ft0 = FR.fs_twin()
R = []
for s, p, g, cvt, ho in FD.registry():
    if not g: continue
    try:
        d = FD.load2(p); seg = FD.segment(d)
        d["_sess"] = s; d["_fold"] = p
        ft = FC.cvt_ft(d["l_i"], ft_base=ft0) if cvt else None
        r = CP.cl_pair(d, seg, g, s, ft=ft)
        if r is None: continue
        t, (mo, mf), old, fs, m, cmd, pl = r
        n = len(t); cut = int(n * 0.8)      # 앞 4/5 = 본체, 뒤 1/5 = 이륙 급변
        row = dict(s=s, n=p.name, kp1=g[0], kp2=g[2])
        for i, k in ((4, "a1"), (5, "a2")):
            real = np.asarray(mf[k]); sim = np.asarray(fs[i]); e = real - sim
            rng = float(real.max() - real.min())
            row[k] = dict(all=100 * float(np.sqrt(np.mean(e ** 2))) / rng,
                          body=100 * float(np.sqrt(np.mean(e[:cut] ** 2))) / rng,
                          tail=100 * float(np.sqrt(np.mean(e[cut:] ** 2))) / rng,
                          rmse=float(np.sqrt(np.mean(e ** 2))), rng=rng)
        R.append(row)
    except Exception:
        continue

print("합격선 재산출 — 분모 = 실측이 오간 범위 (0% 가 완벽)\n")
print("  '본체' = 창의 앞 4/5 · '이륙' = 마지막 1/5 (발이 떨어지는 급변 구간)\n")
print(f"  {'사용자 판정':18s} {'n':>3s} | {'힙 전체':>7s} {'힙 본체':>7s} {'힙 이륙':>7s} "
      f"| {'무릎 전체':>8s} {'무릎 본체':>8s} {'무릎 이륙':>8s}")
print("  " + "-" * 86)
for nm, S in (("★ 완벽", PERFECT), ("✗ 무릎 토크 나쁨", BAD_K), ("✗ 힙 토크 나쁨", BAD_H)):
    sel = [r for r in R if (r["s"], r["n"]) in S]
    if not sel: continue
    f = lambda k, w: np.mean([r[k][w] for r in sel])
    print(f"  {nm:18s} {len(sel):3d} | {f('a1','all'):6.1f}% {f('a1','body'):6.1f}% {f('a1','tail'):6.1f}% "
          f"| {f('a2','all'):7.1f}% {f('a2','body'):7.1f}% {f('a2','tail'):7.1f}%")
sel = [r for r in R if (r["s"], r["n"]) not in PERFECT | BAD_K | BAD_H]
f = lambda k, w: np.mean([r[k][w] for r in sel])
print(f"  {'(언급 없음=좋음)':18s} {len(sel):3d} | {f('a1','all'):6.1f}% {f('a1','body'):6.1f}% "
      f"{f('a1','tail'):6.1f}% | {f('a2','all'):7.1f}% {f('a2','body'):7.1f}% {f('a2','tail'):7.1f}%")
print("\n■ 게인별 (범위 대비 %)")
print(f"  {'힙게인':>6s} {'n':>3s} | {'힙 전체':>7s} {'힙 본체':>7s} | {'무릎 전체':>8s} {'무릎 본체':>8s}")
for lo, hi, lab in ((0, 89, "60~80"), (90, 139, "90~120"), (140, 999, "150+")):
    sel = [r for r in R if lo <= r["kp1"] <= hi]
    if not sel: continue
    f = lambda k, w: np.mean([r[k][w] for r in sel])
    print(f"  {lab:>6s} {len(sel):3d} | {f('a1','all'):6.1f}% {f('a1','body'):6.1f}% "
          f"| {f('a2','all'):7.1f}% {f('a2','body'):7.1f}%")
print("\n■ 오차가 이륙 급변에 얼마나 몰려 있나 (전 trial)")
rt = [r["a2"]["tail"] / max(r["a2"]["body"], 1e-9) for r in R]
print(f"  무릎 토크: 이륙 구간 오차가 본체의 {np.median(rt):.1f} 배 (중앙값)")
rt1 = [r["a1"]["tail"] / max(r["a1"]["body"], 1e-9) for r in R]
print(f"  힙   토크: {np.median(rt1):.1f} 배")
