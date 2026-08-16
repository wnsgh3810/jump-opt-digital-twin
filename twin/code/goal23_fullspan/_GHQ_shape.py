# -*- coding: utf-8 -*-
"""_GHQ_shape — ④ 지금 모델이 쓰는 tanh(v/0.3) 이 이 데이터에서 맞는 모양인가.

(1) 08.07 왕복에서 잰 **절대 마찰값** (명령 N·m) 을 저속/중속/고속으로 정리
(2) 일어서기 창들의 속도 분포에서 tanh(v/v0) 가 실제로 **몇 %의 손실을 전달하는지**
    v0=0.30(지금 후보) · 0.05(이 저장소의 다른 건마찰 항) · 0.011(08.07 무릎 실측 최적)
CLI: python _GHQ_shape.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
C = json.load(open(HERE / "_GHQ_fricv2.json", encoding="utf-8"))["cells"]
R = json.load(open(HERE / "_GHQ_s2sveldir.json", encoding="utf-8"))

print("=" * 100)
print("1. 08.07 무게추 왕복 — **마찰의 절대값** [명령 N·m] · 속도대별 (자세칸 중앙값)")
print("   (축 토크로 보려면 ×1.306(무릎)·×1.241(힙) — 데이터 사전의 정적 환산)")
print("=" * 100)
BANDS = [("아주 느림 0.010~0.030", 0.010, 0.030), ("느림 0.030~0.080", 0.030, 0.080),
         ("보통 0.080~0.180", 0.080, 0.180), ("빠름 0.180~0.450", 0.180, 0.450),
         ("가장 빠름 0.450~0.700", 0.450, 0.700)]
print(f"{'기록/채널':14s} " + " ".join(f"{b[0]:>22s}" for b in BANDS))
for k, cs in C.items():
    row = []
    for nm, lo, hi in BANDS:
        g = [c["fric"] for c in cs if lo <= c["v"] < hi]
        row.append(f"{np.median(g):8.3f} (칸{len(g):2d})" if len(g) >= 2 else " " * 15)
    print(f"{k:14s} " + " ".join(f"{x:>22s}" for x in row))

print("\n" + "=" * 100)
print("2. 일어서기 창의 속도에서 tanh(|v|/v0) 가 전달하는 손실 비율 (1.00 = 전액)")
print("   실측이 말하는 참값은 '거의 전 구간 전액'(쿨롱) 이다.")
print("=" * 100)
print(f"{'경우':16s} {'방향':>6s} {'창':>4s} {'|v| 중앙':>8s} "
      f"{'v0=0.30(지금)':>13s} {'v0=0.05':>9s} {'v0=0.011':>9s}")
for c in ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]:
    for lab, sgn in (("올라감", +1), ("내려감", -1)):
        g = [abs(x["v"]) for x in R if x["case"] == c and np.sign(x["v"]) == sgn]
        if not g:
            continue
        v = np.array(g)
        print(f"{c:16s} {lab:>6s} {len(v):4d} {np.median(v):8.2f} "
              f"{np.mean(np.tanh(v/0.30)):13.2f} {np.mean(np.tanh(v/0.05)):9.2f} "
              f"{np.mean(np.tanh(v/0.011)):9.2f}")
print(f"{'(참고) 점프 무릎':16s} {'':>6s} {'':>4s} {5.31:8.2f} "
      f"{np.tanh(5.31/0.30):13.2f} {np.tanh(5.31/0.05):9.2f} {np.tanh(5.31/0.011):9.2f}"
      "   ← 점프에선 세 값이 똑같다")

print("\n" + "=" * 100)
print("3. 두 속도 사이에서 tanh(v/0.3) 이 요구하는 변화 vs 실측이 보인 변화")
print("=" * 100)
for a, b in ((0.10, 0.40), (0.15, 0.45), (0.30, 2.00), (0.02, 0.55)):
    print(f"   {a:.2f} → {b:.2f} rad/s : tanh(v/0.3) 비 {np.tanh(b/0.3)/np.tanh(a/0.3):5.2f}배 · "
          f"tanh(v/0.05) 비 {np.tanh(b/0.05)/np.tanh(a/0.05):4.2f}배 · 쿨롱 1.00배")
