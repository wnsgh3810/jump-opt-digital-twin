# -*- coding: utf-8 -*-
"""P22 노션 그림 3탄: 파레토 전선 (동결 개체군) + P19/p22a 마커."""
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


def main():
    ck = safe.read_json(HERE / "p22_nsga_ckpt.json")
    F = np.array(ck["F"], float)
    G = np.array(ck["G"], float)
    feas = (G <= 0).all(axis=1)
    dom = feas & (F[:, 0] <= 1.0) & (F[:, 1] <= 1.0)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(F[feas & ~dom, 0], F[feas & ~dom, 1], s=28, alpha=0.6,
               label="탐색 개체 (제약 통과)")
    ax.scatter(F[dom, 0], F[dom, 1], s=46, marker="D",
               label="P19를 양 축 모두에서 이기는 개체")
    ax.scatter([1.0], [1.0], s=140, marker="*", label="P19 (현행 canonical)")
    ax.scatter([0.972], [0.994], s=140, marker="P",
               label="p22a (엄격 게이트 통과·REPRODUCED)")
    ax.axvline(1.0, lw=0.7, ls="--")
    ax.axhline(1.0, lw=0.7, ls="--")
    ax.set_xlabel("폐루프 τ-갭 (P19=1.0, 왼쪽일수록 좋음)")
    ax.set_ylabel("통짜 재생 dq RMSE (P19=1.0, 아래일수록 좋음)")
    ax.set_title(f"파레토 전선 — 널 나사 동결 탐색 (세대 {ck['gen']}): "
                 "좌하 사분면 = P19 동시 지배 영역")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "pareto_front.png", dpi=140)
    plt.close(fig)
    print("saved pareto_front.png")


if __name__ == "__main__":
    main()
