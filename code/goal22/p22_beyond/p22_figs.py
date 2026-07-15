# -*- coding: utf-8 -*-
"""P22 노션용 그림: ① T3 에너지 원장 (W_in vs E_req) ② 0421 로더 인공물 오버레이."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))
OUT = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p22_results")
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def fig_ledger():
    res = json.load(open(HERE.parent / "p20_rise" / "p22_probe_t3_result.json"))
    rows = res["rows"]
    order = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0429"]
    rows = [r for r in rows if r.get("ds") in order]
    rows.sort(key=lambda r: (order.index(r["ds"]), r.get("sub", "")))
    W = [r["W_in"] for r in rows]
    E = [r["E_req"] for r in rows]
    labs = [f'{r["ds"].replace("jump_", "").replace("position_", "")}\n{r.get("sub", "")}' for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(x - 0.2, W, 0.4, label="입력일 W_in = ∫â·dq (전류로 계산한 일)")
    ax.bar(x + 0.2, E, 0.4, label="요구 에너지 E_req = M·g·Δh (실측 높이)")
    ax.set_xticks(x)
    ax.set_xticklabels(labs, fontsize=6, rotation=90)
    ax.set_ylabel("에너지 [J]")
    ax.set_title("T3 에너지 원장 (sim 무관): 전류가 말하는 일 vs 실제 점프가 요구한 에너지 — 0429만 큰 잉여")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "t3_ledger.png", dpi=140)
    plt.close(fig)
    print("saved t3_ledger.png")


def fig_0421():
    import p19_judge as P
    sub = "P100_D0.75_P100_D2"
    base = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.04.21/Position Control") / sub
    kx = pd.read_excel(base / "knee.xlsx")
    c = pd.read_csv(base / "jump_opt_compare" / "predicted_compare.csv")
    traw = kx["currentTorque"].values
    dq = kx["currentAngleVelocity"].values
    t = kx["Time"].values - kx["Time"].values[0]
    ah = P.J.ahat(P.A_PAPER, traw, dq)
    tp = c["kneeCurrentTorquePaper"].values
    tc = c["Time"].values - c["Time"].values[0]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(t, ah, label="원본 xlsx → Paper 변환 (진짜 기록)")
    ax.plot(tc, tp, "--", label="predicted_compare.csv (구 파이프라인, 로더가 쓰던 값)")
    ax.plot(t, 1.35 * ah, ":", label="xlsx × 1.35 (인공물 배율 재현)")
    ax.set_xlabel("t [s]")
    ax.set_ylabel("무릎 토크 [Nm]")
    ax.set_title(f"0421 로더 인공물: csv가 xlsx의 1.35배 ({sub})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fix0421_overlay.png", dpi=140)
    plt.close(fig)
    print("saved fix0421_overlay.png")


if __name__ == "__main__":
    fig_ledger()
    fig_0421()
