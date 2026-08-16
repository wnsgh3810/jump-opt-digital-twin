# -*- coding: utf-8 -*-
"""_GHQ_final — 결론 수치 정리 (속도 의존의 크기 · 방향 분해 · 창길이 민감도)."""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
CASES = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]


def ols(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    n, k = X.shape
    s2 = float(r @ r) / max(n - k, 1)
    se = np.sqrt(np.maximum(np.diag(np.linalg.pinv(X.T @ X)) * s2, 0))
    r2 = 1 - float(r @ r) / max(float(((y - y.mean()) ** 2).sum()), 1e-12)
    return b, se, r2


def load(p):
    return json.load(open(HERE / p, encoding="utf-8"))


R = load("_GHQ_s2sveldir.json")

print("A. 속도가 설명하는 몫 (자세 3차 다항식 먼저 넣고, 속도를 추가로 넣었을 때 R² 증가)")
print(f"   {'경우':16s} {'방향':>6s} {'n':>4s} {'자세만 R²':>9s} {'+속도 R²':>9s} {'증가':>6s} "
      f"{'속도계수±SE':>16s}")
inc = []
for c in CASES:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        g = [x for x in R if x["case"] == c and np.sign(x["v"]) == sgn]
        if len(g) < 15:
            continue
        v = np.array([abs(x["v"]) for x in g]); q = np.array([x["q2"] for x in g])
        y = np.array([x["dlt"] for x in g])
        qn = (q - q.mean()) / max(q.std(), 1e-9)
        P = np.stack([np.ones_like(qn), qn, qn ** 2, qn ** 3], 1)
        _, _, r2p = ols(P, y)
        b, se, r2 = ols(np.concatenate([P, v[:, None]], 1), y)
        inc.append(r2 - r2p)
        print(f"   {c:16s} {lab:>6s} {len(g):4d} {r2p:9.3f} {r2:9.3f} {r2-r2p:+6.3f} "
              f"{b[-1]:+8.2f} ± {se[-1]:5.2f}")
print(f"   → R² 증가 중앙 {np.median(inc):+.3f} · 최대 {max(inc):+.3f}")

print("\nB. 좁은 자세칸(10°) 안에서 속도만 2배 이상 벌어졌을 때 |Δ| 의 비 (실측) vs tanh(v/0.3) 요구비")
rows = []
for c in CASES:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        g = [x for x in R if x["case"] == c and np.sign(x["v"]) == sgn]
        for lo in range(-180, -10, 10):
            gg = [x for x in g if lo <= x["q2"] < lo + 10]
            if len(gg) < 6:
                continue
            v = np.array([abs(x["v"]) for x in gg]); y = np.array([x["dlt"] for x in gg])
            o = np.argsort(v); k = max(2, len(gg) // 3)
            vs, ys = v[o[:k]].mean(), y[o[:k]].mean()
            vf, yf = v[o[-k:]].mean(), y[o[-k:]].mean()
            if vf / max(vs, 1e-6) < 2.0 or abs(ys) < 0.5:
                continue
            rows.append((c, lab, lo, vs, vf, ys, yf, abs(yf) / abs(ys),
                         float(np.tanh(vf / 0.3) / np.tanh(vs / 0.3))))
for r in rows:
    print(f"   {r[0]:15s} {r[1]} {r[2]:5d}~{r[2]+10:<5d} v {r[3]:.2f}→{r[4]:.2f} ({r[4]/r[3]:.1f}배) "
          f"Δ {r[5]:+.2f}→{r[6]:+.2f}  실측비 {r[7]:.2f}  tanh요구비 {r[8]:.2f}")
print(f"   → 실측비 중앙 {np.median([r[7] for r in rows]):.2f} (n={len(rows)}) · "
      f"tanh(v/0.3) 요구비 중앙 {np.median([r[8] for r in rows]):.2f}")

print("\nC. 창 길이 민감도 (no_cvt/no_load, 0.10s · 0.15s · 0.25s 창)")
for p, w in (("_GHQ_w010.json", 0.10), ("_GHQ_s2sveldir.json", 0.15), ("_GHQ_w025.json", 0.25)):
    if not (HERE / p).exists():
        print(f"   {w:.2f}s: 아직 없음"); continue
    D = [x for x in load(p) if x["case"] == "no_cvt/no_load"]
    if not D:
        continue
    u = [x for x in D if x["v"] > 0 and -155 <= x["q2"] < -120]
    lo = [x["dlt"] for x in u if abs(x["v"]) < 0.5]
    hi = [x["dlt"] for x in u if abs(x["v"]) > 1.0]
    print(f"   창 {w:.2f}s (n={len(D):3d}): 올라감 −155~−120° 에서 "
          f"느림(<0.5) Δ중앙 {np.median(lo):+.2f}(n{len(lo)}) · "
          f"빠름(>1.0) Δ중앙 {np.median(hi):+.2f}(n{len(hi)})" if lo and hi else f"   창 {w:.2f}s: 칸 부족")
