# -*- coding: utf-8 -*-
"""P22 노션 그림 4탄: 대표 trial 재생 dq2 오버레이 (실측 vs P19 vs p22b)."""
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

OUT = Path((LEGACY_ROOT + "/g22_p22_results"))
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

PICKS = [
    ("jump_0424", "150_2.2_500_4"),
    ("jump_0602", "150_2.2_500_5"),
    ("jump_0429", "150_2.2_500_4"),
    ("jump_position_0421", "P200_D1.5_P200_D4"),
]


def main():
    import p22_eval as E
    import p21_cma as C
    E.ensure_init()
    R = C._W["R"]
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    real = {(ds, str(sub)): d for ds, sub, d, *_ in R.TRIALS}
    b19 = Path((LEGACY_ROOT + "/g22_p19_all_results"))
    b22 = Path((LEGACY_ROOT + "/g22_p22b_all_results"))
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, (ds, sub) in zip(axes.flat, PICKS):
        d = real[(ds, sub)]
        folder = {"jump_0429": "jump_0429_cvt", "jump_0324": "jump_0324_heldout"}.get(ds, ds)
        za = np.load(b19 / folder / "traj" / f"{sub}__A.npz", allow_pickle=True)
        zb = np.load(b22 / folder / "traj" / f"{sub}__A.npz", allow_pickle=True)
        ax.plot(d["t"], d["dq2"], lw=1.6, label="실측")
        ax.plot(za["t"], za["dq2"], "--", lw=1.2, label="P19 재생")
        ax.plot(zb["t"], zb["dq2"], ":", lw=1.6, label="p22b 재생")
        ax.set_xlim(0, float(d["t"][-1]))
        ax.set_title(f"{ds} / {sub} — 무릎(크랭크) 속도 dq2 [rad/s]", fontsize=9)
        ax.legend(fontsize=7)
        ax.set_xlabel("t [s]", fontsize=8)
    fig.suptitle("통짜 재생(Mode A) 오버레이 — 고게인 대표 trial 4종", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "overlay_p19_p22b.png", dpi=140)
    plt.close(fig)
    print("saved overlay_p19_p22b.png")


if __name__ == "__main__":
    main()
