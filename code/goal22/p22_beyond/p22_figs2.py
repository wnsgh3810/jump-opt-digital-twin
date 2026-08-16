# -*- coding: utf-8 -*-
"""P22 노션 그림 2탄: 민감도 지도 + 0429 전류-bin 분해."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import safe

OUT = Path((LEGACY_ROOT + "/g22_p22_results"))
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def fig_sens():
    d = safe.read_json(HERE / "p22_exp_sens.json")
    picks = ["fv_hip:0.8", "fv_hip:0.6", "fv_knee:0.6", "stiff:1.2", "stiff:0.6"]
    comps = ["CL", "JW2", "S2S", "OLDQ", "H"]
    labels = ["폐루프 τ-갭", "0.2s 창", "s2s", "통짜 재생 dq", "점프높이 오차"]
    x = np.arange(len(picks))
    w = 0.15
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for i, (c, lb) in enumerate(zip(comps, labels)):
        ax.bar(x + (i - 2) * w, [d[p][c] for p in picks], w, label=lb)
    ax.axhline(1.0, lw=0.8, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([p.replace(":", " ×") for p in picks])
    ax.set_ylabel("P19 = 1.0 정규화 (낮을수록 좋음)")
    ax.set_title("소산 민감도 지도: 감쇠를 깎으면 τ·창·높이는 좋아지고 재생 dq만 나빠진다")
    ax.legend(fontsize=8, ncol=5)
    fig.tight_layout()
    fig.savefig(OUT / "sens_map.png", dpi=140)
    plt.close(fig)
    print("saved sens_map.png")


def fig_bins():
    d = safe.read_json(HERE / "p22_probe_0429_energy_result.json")
    # bin_share: 세션별 [0-20, 20-30, 30+] 점유율 구조를 유연히 탐색
    bs = d["bin_shares"]
    sess = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0429"]
    cats = ["[0,20)", "[20,30)", "[30+] (포화 근방)"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(sess))
    bot = np.zeros(len(sess))
    for ci in range(3):
        vals = [100 * float(bs[s]["shares"][ci]) for s in sess]
        ax.bar(x, vals, 0.55, bottom=bot, label=cats[ci])
        bot += np.array(vals)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("jump_", "").replace("position_", "") for s in sess])
    ax.set_ylabel("무릎 채널 일 점유율 [%]")
    ax.set_title("전류 대역별 일 분해: 0602도 [30+] 대역에서 일하는데 수지는 균형 — 전류 인덱스 가설(H1) 기각 근거")
    ax.legend(title="|traw2| 대역")
    fig.tight_layout()
    fig.savefig(OUT / "bins_0429.png", dpi=140)
    plt.close(fig)
    print("saved bins_0429.png")


if __name__ == "__main__":
    fig_sens()
    fig_bins()
