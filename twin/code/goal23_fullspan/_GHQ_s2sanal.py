# -*- coding: utf-8 -*-
"""_GHQ_s2sanal — `_GHQ_s2sveldir.json` (창별 모자란 토크 Δ) 를 속도·방향으로 읽는다.

Δ 의 뜻: 무릎(크랭크) 명령에 이만큼 더해야 그 창의 실측과 같아진다 [명령 N·m].
  Δ<0 = 모델이 그만큼 **더 밀고 있다** = 모델에 손실이 그만큼 **모자란다**.
  올라갈 때(v>0)와 내려갈 때(v<0) 를 갈라:
    절반차 (Δ_up − Δ_dn)/2 = **방향 반전 성분 = 마찰형**
    절반합 (Δ_up + Δ_dn)/2 = **방향 무관 성분** (중력·하중이 지나가는 길)
CLI: python _GHQ_s2sanal.py
"""
import os, sys, json, itertools
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
R = json.load(open(HERE / "_GHQ_s2sveldir.json", encoding="utf-8"))
CASES = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]
PBIN = [(-180, -155), (-155, -120), (-120, -80), (-80, 0)]
VED = np.array([0.05, 0.15, 0.30, 0.60, 1.00, 1.60, 2.50, 4.50])


def sel(**kw):
    out = R
    for k, v in kw.items():
        out = [r for r in out if r[k] == v]
    return out


print("=" * 112)
print("0. 창 수집 현황  (Δ = 모자란 무릎 명령 토크 [N·m], 0 이 완벽 · 음수 = 모델이 과하게 민다)")
print("=" * 112)
print(f"{'경우':16s} {'올라감':>26s} {'내려감':>26s}")
for c in CASES:
    r = sel(case=c)
    if not r:
        print(f"{c:16s} 없음"); continue
    u = [x for x in r if x["v"] > 0]; d = [x for x in r if x["v"] < 0]
    f = lambda g: (f"n={len(g):3d} |v| {min(abs(x['v']) for x in g):.2f}~{max(abs(x['v']) for x in g):.2f} "
                   f"Δ중앙 {np.median([x['dlt'] for x in g]):+.2f}") if g else "없음"
    print(f"{c:16s} {f(u):>26s} {f(d):>26s}")

print("\n" + "=" * 112)
print("1. 속도칸별 Δ — 방향별 (자세 무시). 괄호 = 창 수")
print("=" * 112)
hdr = " ".join(f"{VED[j]:.2f}~{VED[j+1]:.2f}".rjust(14) for j in range(len(VED) - 1))
print(f"{'경우/방향':22s} {hdr}")
for c in CASES:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        r = [x for x in sel(case=c) if np.sign(x["v"]) == sgn]
        if not r:
            continue
        row = []
        for j in range(len(VED) - 1):
            g = [x["dlt"] for x in r if VED[j] <= abs(x["v"]) < VED[j + 1]]
            row.append(f"{np.median(g):+8.2f}({len(g):2d})" if len(g) >= 2 else " " * 14)
        print(f"{c+' '+lab:22s} " + " ".join(f"{x:>14s}" for x in row))

print("\n" + "=" * 112)
print("2. 자세를 고정하고 속도만 본다 — 자세칸 × 속도칸, 방향별 Δ 중앙값")
print("=" * 112)
for c in CASES:
    r = sel(case=c)
    if not r:
        continue
    print(f"\n── {c}")
    print(f"   {'자세칸[°]':>12s} {'방향':>6s} " + " ".join(f"{VED[j]:.2f}~{VED[j+1]:.2f}".rjust(12)
                                                       for j in range(len(VED) - 1)))
    for pb in PBIN:
        for lab, sgn in (("올라감", +1), ("내려감", -1)):
            g0 = [x for x in r if pb[0] <= x["q2"] < pb[1] and np.sign(x["v"]) == sgn]
            if len(g0) < 2:
                continue
            row = []
            for j in range(len(VED) - 1):
                g = [x["dlt"] for x in g0 if VED[j] <= abs(x["v"]) < VED[j + 1]]
                row.append(f"{np.median(g):+7.2f}({len(g):2d})" if len(g) >= 2 else " " * 12)
            print(f"   {pb[0]}~{pb[1]}".rjust(15) + f" {lab:>6s} " + " ".join(f"{x:>12s}" for x in row))

print("\n" + "=" * 112)
print("3. 같은 자세칸 × 같은 속도칸에서 방향을 갈랐다 — 절반차(마찰형) / 절반합(방향무관)")
print("=" * 112)
POOL = []
for c in CASES:
    r = sel(case=c)
    if not r:
        continue
    print(f"\n── {c}")
    print(f"   {'자세칸':>12s} {'속도칸':>12s} {'v중앙':>7s} {'Δ올라':>8s} {'Δ내려':>8s} "
          f"{'절반차(마찰)':>12s} {'절반합':>9s} {'창수':>7s}")
    for pb in PBIN:
        for j in range(len(VED) - 1):
            u = [x for x in r if pb[0] <= x["q2"] < pb[1] and x["v"] > 0 and VED[j] <= x["v"] < VED[j + 1]]
            d = [x for x in r if pb[0] <= x["q2"] < pb[1] and x["v"] < 0 and VED[j] <= -x["v"] < VED[j + 1]]
            if len(u) < 2 or len(d) < 2:
                continue
            mu, md = np.median([x["dlt"] for x in u]), np.median([x["dlt"] for x in d])
            vm = np.median([abs(x["v"]) for x in u + d])
            POOL.append(dict(case=c, pb=pb, v=vm, half_d=(mu - md) / 2, half_s=(mu + md) / 2,
                             n=len(u) + len(d)))
            print(f"   {pb[0]}~{pb[1]}".rjust(15) + f" {VED[j]:.2f}~{VED[j+1]:.2f}".rjust(13)
                  + f" {vm:7.2f} {mu:+8.2f} {md:+8.2f} {(mu-md)/2:+12.2f} {(mu+md)/2:+9.2f}"
                  + f" {len(u):3d}/{len(d):<3d}")

print("\n" + "=" * 112)
print("4. 마찰형 성분(절반차)이 속도에 따라 변하나 — 위 칸들을 속도로 모음")
print("=" * 112)
if POOL:
    print(f"   {'속도칸':>12s} {'v중앙':>7s} {'절반차 중앙':>12s} {'사분위':>16s} {'칸수':>5s} "
          f"{'tanh(v/0.3) 예상비':>18s}")
    ref = None
    for j in range(len(VED) - 1):
        g = [p for p in POOL if VED[j] <= p["v"] < VED[j + 1]]
        if len(g) < 2:
            continue
        h = np.array([p["half_d"] for p in g])
        if ref is None:
            ref = (np.median(np.abs(h)), np.median([p["v"] for p in g]))
        vm = np.median([p["v"] for p in g])
        print(f"   {VED[j]:.2f}~{VED[j+1]:.2f}".rjust(15)
              + f" {vm:7.2f} {np.median(h):+12.2f} {np.percentile(h,25):+7.2f}~{np.percentile(h,75):+7.2f}"
              + f" {len(g):5d} {np.tanh(vm/0.3)/np.tanh(ref[1]/0.3):18.2f}")
    print(f"   (예상비 기준 = {ref[1]:.2f} rad/s 칸)")

print("\n" + "=" * 112)
print("5. 회귀: 같은 자세칸·같은 방향 안에서 Δ 를 |v| 로 설명하면? (기울기 [N·m per rad/s])")
print("=" * 112)
for c in CASES:
    r = sel(case=c)
    for pb in PBIN:
        for lab, sgn in (("올라감", +1), ("내려감", -1)):
            g = [x for x in r if pb[0] <= x["q2"] < pb[1] and np.sign(x["v"]) == sgn]
            if len(g) < 8:
                continue
            v = np.array([abs(x["v"]) for x in g]); y = np.array([x["dlt"] for x in g])
            if v.max() - v.min() < 0.3:
                continue
            A = np.stack([np.ones_like(v), v], 1)
            b, *_ = np.linalg.lstsq(A, y, rcond=None)
            pred = A @ b
            ss = 1 - np.sum((y - pred) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
            print(f"   {c:16s} {pb[0]:>5d}~{pb[1]:<5d} {lab} n={len(g):3d} "
                  f"|v| {v.min():.2f}~{v.max():.2f} → 절편 {b[0]:+6.2f} 기울기 {b[1]:+6.2f} R²{ss:5.2f}")
