# -*- coding: utf-8 -*-
"""교환비 표 검산 — 이어풀기 가지 선택 사고 확인 + 모델이 실제로 쓰는 표(RU.rtab)와 대조."""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "goal22" / "p18_cvt"))
os.chdir(HERE)
import numpy as np
from cvt_core import closure

LI = 0.025193


def per_point(deg):
    return closure(np.radians(-deg), LI)[2]


def cont(qmax=3.09, n=6001):
    """qc=π/2 (−90도, 조건 좋은 자리) 에서 양쪽으로 이어푼다."""
    qc = np.linspace(0.0, qmax, n)
    i0 = int(np.argmin(np.abs(qc - np.pi / 2)))
    r = np.zeros(n); qk = np.zeros(n)
    qk0, _, r0 = closure(float(qc[i0]), LI, None)
    r[i0] = r0; qk[i0] = qk0
    p = qk0
    for i in range(i0 + 1, n):
        p, _, rr = closure(float(qc[i]), LI, p); r[i] = rr; qk[i] = p
    p = qk0
    for i in range(i0 - 1, -1, -1):
        p, _, rr = closure(float(qc[i]), LI, p); r[i] = rr; qk[i] = p
    return -np.degrees(qc), r, qk


ang, r, qk = cont()
print(f"{'각도':>8s} {'점별(seed=qc)':>14s} {'이어풀기':>10s}")
for a in (-177, -176.5, -176, -175, -174, -172, -170, -160, -140, -120, -90, -60, -40, -20, -10, -5, -2, 0):
    print(f"{a:8.1f} {per_point(a):14.4f} {np.interp(a, ang[::-1], r[::-1]):10.4f}")

print()
print("모델이 실제로 쓰는 표 RU.rtab (범위 ±3 rad = ±171.9도, 그 밖은 끝값으로 고정)")
os.environ["FS_CVT_XML"] = "0"
import fs_cvt as FC
qg, rg = FC.RU.rtab(LI)
for a in (-180, -175, -171.9, -170, -160, -140, -90, -40, -20, -10, 0):
    q = np.radians(-a)
    print(f"{a:8.1f} rtab={float(np.interp(q, qg, rg)):8.4f}  "
          f"amp=max(1/max(|r|,0.2)-1,0)={max(1/max(abs(float(np.interp(q,qg,rg))),0.2)-1,0):6.3f}")
print(f"rtab 격자 간격 {np.degrees(qg[1]-qg[0]):.2f}도 · 끝값 r(+3rad)={rg[-1]:.4f} r(-3rad)={rg[0]:.4f}")

print()
print("무변속(l_i=30.00mm, 평행사변형)에서 두 가지 비교 — 실제 모델은 r≡1 이어야 한다")
qg2, rg2 = FC.RU.rtab(0.030)
for a in (-170, -140, -90, -40, -20):
    q = np.radians(-a)
    print(f"{a:8.1f} 점별 {closure(q,0.030)[2]:8.4f}   rtab {float(np.interp(q,qg2,rg2)):8.4f}")
