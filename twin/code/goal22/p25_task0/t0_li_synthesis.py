# -*- coding: utf-8 -*-
"""l_i 상수 최적화 — 4방법 합본 그림 (h vs l_i): CMA 곡선 + NLP 스윕 + PPO 점 + 앵커/참조."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
J = lambda p: json.load(open(HERE / p, encoding="utf-8"))

cma = J("t0wc_li_sweep.json")["rows"]
xs_c = sorted(float(k) for k in cma)
ys_c = [cma[k if k in cma else str(k)]["h_plan"] for k in
        [next(kk for kk in cma if float(kk) == x) for x in xs_c]]

nlp = J("t0wc_nlp_sweep.json")["rows"]
ok = {float(k): v for k, v in nlp.items()
      if v.get("status") == "converged" and v["h_plan"] < 1.5}   # 미수렴(l_i=30 iter캡) 제외
xs_n = sorted(ok)
ys_n = [ok[x]["h_plan"] for x in xs_n]

ppo_fix = {25.08: 0.7146, 26.0: 0.6882, 30.0: 0.9860}
ppo_cond = (27.0, 0.9838)   # wc2 재시도 (다중앵커 BC+128넷, 07-18)

fig, ax = plt.subplots(figsize=(10, 6.5))
ax.axvspan(10, 25.08, alpha=0.10, label="외삽 구간 (CVT 층 fit @25.08)")
l1, = ax.plot(xs_c, ys_c, "o-", lw=2, label="CL-CMA 고정-l_i 스윕 (트윈 정확판)")
ax.plot([26.25], [1.1233], "*", ms=18, color=l1.get_color(),
        label="CL-CMA 자유-l_i 최적: 26.25mm, 1.123m")
l2, = ax.plot(xs_n, ys_n, "s--", lw=1.6, label="NLP 스윕 (대리모델 — 접촉 과강성 편향)")
ax.plot([28.0], [0.9848], "*", ms=14, color=l2.get_color(),
        label="NLP l_i*: 28.0mm (joint 28.2 일치)")
l3 = ax.scatter(list(ppo_fix), list(ppo_fix.values()), marker="^", s=90,
                label="PPO 고정-l_i (저예산 — 충격전략 미학습 아티팩트)")
ax.plot([ppo_cond[0]], [ppo_cond[1]], "D", ms=10,
        label=f"PPO 조건부(wc2) argmax: {ppo_cond[0]:.0f}mm, {ppo_cond[1]:.3f}m")
ax.axvline(25.08, ls="--", lw=1.2, alpha=0.6, color="0.4")
ax.axvline(30.0, ls="--", lw=1.2, alpha=0.6, color="0.6")
ax.axvline(25.161, ls=":", lw=1.5, alpha=0.9, color="k",
           label="AVT 해석모델 최적 25.161mm")
ax.text(25.0, 0.76, "검증앵커 25.08 (0429 CVT)", fontsize=8, ha="right", rotation=90)
ax.text(29.92, 0.76, "검증앵커 30 (무변속)", fontsize=8, ha="right", rotation=90)
ax.set(xlabel="l_i [mm]", ylabel="h_plan [m]",
       title="l_i 상수 최적화 — 4방법 합본 (task0 제약 15Nm)\n"
             "수렴: 트윈 CMA 26.25 ≈ PPO조건부 26.0 ≈ AVT 25.16 (NLP 28은 대리모델 편향, PPO 고정판은 예산 아티팩트)")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, loc="upper left", framealpha=0.95)
ax.set_xlim(11, 31)
fig.tight_layout()
fig.savefig(HERE / "t0_li_synthesis.png", dpi=140)
print("saved t0_li_synthesis.png")
