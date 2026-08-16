# -*- coding: utf-8 -*-
"""_GHD_summary — 마라톤H 전체 before/after 요약 그림 1장 (2026-08-12).

옛 배포모델(p24) vs 현행 H3_260812 을 세 판으로 나란히 본다.
  ① 측정 토크를 그대로 넣고 돌리기 — PD 가 없어 오차를 못 감춘다 (물리의 1급 심판)
  ② 실제 제어기 흉내내기 — 우리가 의도한 대로 q·dq·τ 가 나오는가
  ③ 점프 높이 — 영상 실측 대비

★ 색을 명시하지 않는다 (헌법 7). matplotlib 자동 순환색만 쓴다.
★ 이 스크립트는 **새로 굴리지 않는다** — 정본 경로(`fs_compare_plot.py`)가 이미 만든
  `_compare_H3/_rmse.json` · `_jumph.json` 만 읽어 막대·산점도로 다시 그린다.
  즉 창(plot_window)·앵커·α 규약은 정본이 이미 지킨 값이고, 여기서는 표현만 바꾼다.
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

HERE = Path(__file__).parent
rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False
SRC = HERE / "_compare_H3"
OUT = HERE / "_GHD_summary.png"
CH = ["힙 각도\n[도]", "무릎 각도\n[도]", "힙 속도\n[rad/s]", "무릎 속도\n[rad/s]",
      "힙 토크\n[N·m]", "무릎 토크\n[N·m]"]


def collect(mode):
    R = json.load(io.open(SRC / "_rmse.json", encoding="utf-8"))
    O, F, n = [], [], 0
    for k, v in R.items():
        if not k.startswith(mode + "|"):
            continue
        o = np.array(v["old"], float); f = np.array(v["new"], float)
        if np.all(np.isfinite(o)) and np.all(np.isfinite(f)):
            O.append(o); F.append(f); n += v["n"]
    return np.median(np.array(O), 0), np.median(np.array(F), 0), n


def main():
    fig = plt.figure(figsize=(15.5, 5.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.15, 1.0], wspace=0.32)
    for j, (mode, title) in enumerate((("ModeA", "① 측정된 토크를 그대로 넣고 돌렸을 때"),
                                       ("CL", "② 실제 제어기를 그대로 흉내냈을 때"))):
        o, f, n = collect(mode)
        ax = fig.add_subplot(gs[0, j])
        x = np.arange(6); w = 0.38
        ax.bar(x - w / 2, o, w, label="옛 배포 모델")
        ax.bar(x + w / 2, f, w, label="지금 모델 (H3)")
        for i in range(6):
            ax.text(i + w / 2, f[i], f"{100*(f[i]/o[i]-1):+.0f}%", ha="center",
                    va="bottom", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(CH, fontsize=9)
        ax.set_ylabel("예측 오차 (작을수록 정확)")
        ax.set_title(f"{title}\n{n} trial · 값은 오차의 중앙값", fontsize=11)
        ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(0, max(o.max(), f.max()) * 1.18)

    H = json.load(io.open(SRC / "_jumph.json", encoding="utf-8"))
    A = []
    for v in H.values():
        try:
            r = [float(z) for z in v]
        except Exception:
            continue
        if all(np.isfinite(r)):
            A.append(r)
    A = np.array(A) * 100
    ax = fig.add_subplot(gs[0, 2])
    ax.scatter(A[:, 0], A[:, 1], s=26, alpha=0.75, label="옛 배포 모델")
    ax.scatter(A[:, 0], A[:, 2], s=26, alpha=0.75, label="지금 모델 (H3)")
    lo, hi = A[:, 0].min() - 6, A[:, 0].max() + 6
    ax.plot([lo, hi], [lo, hi], lw=1.0, ls="--")          # 색 명시 금지 — 자동 순환색
    ax.text(hi, hi, " 완벽", va="center", fontsize=9)
    eo = np.median(np.abs(A[:, 1] - A[:, 0])); ef = np.median(np.abs(A[:, 2] - A[:, 0]))
    ax.set_xlabel("영상으로 잰 실제 점프 높이 [cm]")
    ax.set_ylabel("시뮬레이션이 예측한 높이 [cm]")
    ax.set_title(f"③ 점프 높이 — {len(A)} trial\n오차 중앙 {eo:.2f} → {ef:.2f} cm "
                 f"({100*ef/eo:.0f}%) · {int((np.abs(A[:,2]-A[:,0])<np.abs(A[:,1]-A[:,0])).sum())}/{len(A)} 승",
                 fontsize=11)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    fig.suptitle("마라톤H 결과 — 옛 배포 모델 대비 현행 H3_260812  "
                 "(질량·탄성·마찰·변환식 11축 공동 재적합)", fontsize=13, y=1.005)
    fig.tight_layout()
    fig.savefig(OUT, dpi=125, bbox_inches="tight")
    print(f"저장 → {OUT}")


if __name__ == "__main__":
    main()
