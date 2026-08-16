# -*- coding: utf-8 -*-
"""_GHQ_s2sanal2 — Δ(모자란 토크)에서 **속도·자세·방향**을 갈라낸다.

■ 이 기록의 구조적 한계부터 (숨기지 않는다)
  일어서기 1회·앉기 1회뿐이라 **올라갈 때는 빠르고(0.3~3.8) 내려갈 때는 느리다(0.06~0.5).**
  겹치는 속도대는 0.3~0.6 rad/s 뿐이다. 그래서
    · 방향 효과는 **겹치는 속도대에서만** 정직하게 잴 수 있고,
    · 속도 효과는 **한 방향 안에서 자세를 통제해** 재야 한다.

■ 세 가지를 낸다
  1) 자세를 다항식으로 흡수한 뒤 |v| 의 계수 (방향별·경우별) — 속도 의존의 크기 [N·m per rad/s]
  2) 좁은 자세칸(10°) 안에서 속도가 2배 이상 변하는 칸만 골라 본 Δ — 비모수 확인
  3) **속도를 맞춘** 방향 시험 (0.30~0.60 rad/s 창만) — 마찰형/방향무관 분해
CLI: python _GHQ_s2sanal2.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
R = json.load(open(HERE / "_GHQ_s2sveldir.json", encoding="utf-8"))
CASES = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]


def ols(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    n, k = X.shape
    s2 = float(r @ r) / max(n - k, 1)
    XtXi = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(XtXi) * s2, 0))
    r2 = 1 - float(r @ r) / max(float(((y - y.mean()) ** 2).sum()), 1e-12)
    return b, se, r2


print("=" * 104)
print("1. 자세를 3차 다항식으로 흡수한 뒤 남는 **속도 계수** [N·m per rad/s] · 방향별")
print("   (계수가 0 이면 속도 의존 없음. 옆의 corr 은 그 표본에서 |v| 와 자세의 상관 = 통제의 어려움)")
print("=" * 104)
print(f"{'경우':16s} {'방향':>6s} {'n':>4s} {'|v| 범위':>12s} {'속도계수':>10s} {'±SE':>7s} "
      f"{'전체R²':>7s} {'자세만R²':>8s} {'corr(|v|,자세)':>13s}")
for c in CASES:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        g = [x for x in R if x["case"] == c and np.sign(x["v"]) == sgn]
        if len(g) < 15:
            continue
        v = np.array([abs(x["v"]) for x in g]); q = np.array([x["q2"] for x in g])
        y = np.array([x["dlt"] for x in g])
        qn = (q - q.mean()) / max(q.std(), 1e-9)
        P = np.stack([np.ones_like(qn), qn, qn ** 2, qn ** 3], 1)
        b0, _, r2p = ols(P, y)
        X = np.concatenate([P, v[:, None]], 1)
        b, se, r2 = ols(X, y)
        print(f"{c:16s} {lab:>6s} {len(g):4d} {v.min():5.2f}~{v.max():5.2f} "
              f"{b[-1]:+10.2f} {se[-1]:7.2f} {r2:7.2f} {r2p:8.2f} {np.corrcoef(v, q)[0,1]:+13.2f}")

print("\n" + "=" * 104)
print("2. 좁은 자세칸(10°) 안에서 속도가 2배 이상 벌어진 칸만 — Δ 가 실제로 변하나 (비모수)")
print("   tanh(v/0.3) 형태의 손실이 모자란 것이라면, 느린쪽→빠른쪽에서 |Δ| 가 그 비만큼 커져야 한다.")
print("=" * 104)
print(f"{'경우':16s} {'방향':>6s} {'자세칸':>12s} {'느린 v':>7s} {'Δ':>7s} {'빠른 v':>7s} {'Δ':>7s} "
      f"{'Δ변화':>7s} {'tanh비':>7s} {'n':>7s}")
rows2 = []
for c in CASES:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        g = [x for x in R if x["case"] == c and np.sign(x["v"]) == sgn]
        for lo in range(-180, -10, 10):
            gg = [x for x in g if lo <= x["q2"] < lo + 10]
            if len(gg) < 6:
                continue
            v = np.array([abs(x["v"]) for x in gg]); y = np.array([x["dlt"] for x in gg])
            o = np.argsort(v)
            k = max(2, len(gg) // 3)
            vs, ys = v[o[:k]].mean(), y[o[:k]].mean()
            vf, yf = v[o[-k:]].mean(), y[o[-k:]].mean()
            if vf / max(vs, 1e-6) < 2.0:
                continue
            rows2.append((c, lab, lo, vs, ys, vf, yf))
            print(f"{c:16s} {lab:>6s} {lo:5d}~{lo+10:<6d} {vs:7.2f} {ys:+7.2f} {vf:7.2f} {yf:+7.2f} "
                  f"{yf-ys:+7.2f} {np.tanh(vf/0.3)/np.tanh(vs/0.3):7.2f} {len(gg):7d}")
if rows2:
    d = np.array([r[6] - r[4] for r in rows2])
    print(f"→ 칸 {len(rows2)}개: Δ 변화 중앙 {np.median(d):+.2f} N·m (평균 {d.mean():+.2f}, 절대값 중앙 "
          f"{np.median(np.abs(d)):.2f}) · 속도는 중앙 {np.median([r[5]/r[3] for r in rows2]):.1f}배 벌어짐")

print("\n" + "=" * 104)
print("3. **속도를 맞춘** 방향 시험 — 0.30~0.60 rad/s 창만, 자세칸 10°")
print("   절반차 = (Δ올라 − Δ내려)/2 = 마찰형(방향 반전) · 절반합 = 방향 무관")
print("=" * 104)
print(f"{'경우':16s} {'자세칸':>12s} {'v올라':>6s} {'v내려':>6s} {'Δ올라':>7s} {'Δ내려':>7s} "
      f"{'절반차':>7s} {'절반합':>7s} {'n':>8s}")
agg = {}
for c in CASES:
    for lo in range(-180, -10, 10):
        u = [x for x in R if x["case"] == c and lo <= x["q2"] < lo + 10 and 0.30 <= x["v"] < 0.60]
        d = [x for x in R if x["case"] == c and lo <= x["q2"] < lo + 10 and -0.60 < x["v"] <= -0.30]
        if len(u) < 2 or len(d) < 2:
            continue
        mu = np.median([x["dlt"] for x in u]); md = np.median([x["dlt"] for x in d])
        print(f"{c:16s} {lo:5d}~{lo+10:<6d} {np.median([x['v'] for x in u]):6.2f} "
              f"{np.median([abs(x['v']) for x in d]):6.2f} {mu:+7.2f} {md:+7.2f} "
              f"{(mu-md)/2:+7.2f} {(mu+md)/2:+7.2f} {len(u):3d}/{len(d):<4d}")
        agg.setdefault(c, []).append(((mu - md) / 2, (mu + md) / 2))
print()
for c, g in agg.items():
    a = np.array(g)
    print(f"{c:16s} 속도 맞춘 칸 {len(g)}개 → 마찰형 중앙 {np.median(a[:,0]):+.2f} N·m · "
          f"방향무관 중앙 {np.median(a[:,1]):+.2f} N·m")

print("\n" + "=" * 104)
print("4. 대조: 속도를 **안** 맞추고 방향만 가르면? (앞선 08-14 판정과 같은 방식)")
print("=" * 104)
for c in CASES:
    for lo in range(-180, -10, 20):
        u = [x for x in R if x["case"] == c and lo <= x["q2"] < lo + 20 and x["v"] > 0.35]
        d = [x for x in R if x["case"] == c and lo <= x["q2"] < lo + 20 and x["v"] < -0.35]
        if len(u) < 2 or len(d) < 2:
            continue
        mu = np.median([x["dlt"] for x in u]); md = np.median([x["dlt"] for x in d])
        print(f"{c:16s} {lo:5d}~{lo+20:<6d} v올라 {np.median([x['v'] for x in u]):5.2f} "
              f"v내려 {np.median([abs(x['v']) for x in d]):5.2f} → 절반차 {(mu-md)/2:+6.2f} "
              f"절반합 {(mu+md)/2:+6.2f}")
