# -*- coding: utf-8 -*-
"""_GHQ_fricfit — _GHQ_fricv2 가 만든 점들을 **속도칸 중앙값**으로 요약한 뒤 모형을 맞춘다.
(생점 RMS 는 기준값이 작은 칸에서 나온 몇 개의 폭주 비율에 지배당한다 — 그래서 중앙값으로.)
CLI: python _GHQ_fricfit.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
J = json.load(open(HERE / "_GHQ_fricv2.json", encoding="utf-8"))
VED = np.array([0.005, 0.010, 0.018, 0.030, 0.050, 0.080, 0.120, 0.180, 0.280, 0.450, 0.700])
VMIN_TRUST = 0.010     # 이보다 느리면 50ms 창 안 움직임이 0.5mrad 미만 = 방향 판정이 잡음


def summarize(ch):
    P = J["pool"][ch]
    v = np.array([p[0] for p in P]); f = np.array([p[1] for p in P])
    out = []
    for j in range(len(VED) - 1):
        m = (v >= VED[j]) & (v < VED[j + 1])
        if m.sum() < 3:
            continue
        out.append((float(np.median(v[m])), float(np.median(f[m])), int(m.sum()),
                    float(np.percentile(f[m], 25)), float(np.percentile(f[m], 75))))
    return np.array([o[:3] for o in out]), out


def fit(ch):
    A, raw = summarize(ch)
    ok = A[:, 0] >= VMIN_TRUST
    v, f, w = A[ok, 0], A[ok, 1], A[ok, 2]
    vr = 0.10
    def rms(pred):
        return float(np.sqrt(np.sum(w * (f - pred) ** 2) / np.sum(w)))
    res = {}
    res["쿨롱 (속도 무관, 상수)"] = (rms(np.full_like(f, np.average(f, weights=w))),
                              f"수준={np.average(f, weights=w):.3f}")
    best = (np.inf, None)
    for v0 in np.geomspace(0.001, 5.0, 400):
        for A0 in np.linspace(0.2, 3.0, 141):
            p = A0 * np.tanh(v / v0)
            r = rms(p)
            if r < best[0]:
                best = (r, (v0, A0))
    res["tanh(v/v0)·A, v0 자유"] = (best[0], f"v0={best[1][0]:.3f} rad/s, A={best[1][1]:.2f}")
    b0 = np.inf; bA = None
    for A0 in np.linspace(0.2, 3.0, 281):
        r = rms(A0 * np.tanh(v / 0.30))
        if r < b0:
            b0, bA = r, A0
    res["tanh(v/0.30)·A — 지금 모델"] = (b0, f"A={bA:.2f} (v0 고정 0.30)")
    X = np.stack([np.ones_like(v), v], 1)
    b, *_ = np.linalg.lstsq(X * np.sqrt(w)[:, None], f * np.sqrt(w), rcond=None)
    res["쿨롱+점성 c+b·v"] = (rms(X @ b), f"c={b[0]:.3f}, b={b[1]:+.3f}/(rad/s)")
    best2 = (np.inf, None)
    for fc in np.linspace(0.3, 1.5, 61):
        for ex in np.linspace(0.0, 2.0, 81):
            for vs in np.geomspace(0.005, 1.0, 60):
                p = fc + ex * np.exp(-(v / vs) ** 2)
                r = rms(p)
                if r < best2[0]:
                    best2 = (r, (fc, ex, vs))
    res["Stribeck fc+Δ·exp(−(v/vs)²)"] = (best2[0],
                                          f"fc={best2[1][0]:.2f}, Δ={best2[1][1]:.2f}, vs={best2[1][2]:.3f}")
    return res, raw


for ch in ("hip", "knee"):
    R, raw = fit(ch)
    print(f"\n■ {ch} — 자세 고정·정규화한 마찰비 (기준 0.06~0.16 rad/s = 1.00)")
    print(f"   {'v[rad/s]':>9s} {'실측비':>7s} {'사분위':>14s} {'점':>4s} | {'tanh(v/0.3)':>11s}")
    for vm, fm, n, lo, hi in raw:
        flag = "  ← 신뢰 밖(정지 잡음)" if vm < VMIN_TRUST else ""
        print(f"   {vm:9.3f} {fm:7.2f}  {lo:6.2f}~{hi:6.2f} {n:4d} | "
              f"{np.tanh(vm/0.3)/np.tanh(0.10/0.3):11.2f}{flag}")
    print("   모형 (속도칸 중앙값에 표본수 가중, v≥0.010 만):")
    for k, (r, note) in sorted(R.items(), key=lambda x: x[1][0]):
        print(f"      {k:30s} 잔차RMS {r:.3f}   {note}")
