# -*- coding: utf-8 -*-
"""_GH9_summary — 마라톤 결과 한 장 요약 그림 (2026-08-11).

배포모델(p24) → 승격판(G26_0811) 을 채널별로 보여준다. 저장된 보드 원수치만 읽고
새로 시뮬레이션하지 않는다 (표와 그림이 어긋나는 사고 방지 — 08-09 전례).

CLI: python _GH9_summary.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

SRC = HERE / "_compare_G50"
NM = ["힙 관절각\n[°]", "무릎 관절각\n[°]", "힙 각속도\n[rad/s]", "무릎 각속도\n[rad/s]",
      "힙 토크\n[N·m]", "무릎 토크\n[N·m]"]


def agg(mode):
    R = {**json.load(io.open(SRC / "_rmse.json", encoding="utf-8")),
         **json.load(io.open(SRC / "_rmse_cvt.json", encoding="utf-8"))}
    rows = [v for k, v in R.items() if k.startswith(mode + "|") and len(v["old"]) >= 6]
    w = np.array([v["n"] for v in rows], float)
    O = (np.array([v["old"] for v in rows]) * w[:, None]).sum(0) / w.sum()
    F = (np.array([v["new"] for v in rows]) * w[:, None]).sum(0) / w.sum()
    n = sum(v["n"] for k, v in R.items() if k.startswith(mode + "|"))
    return O, F, n


def main():
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8),
                           gridspec_kw={"width_ratios": [1.15, 1.15, 0.9]})
    for a, mode, title in ((ax[0], "ModeA", "측정 토크를 그대로 넣고 재생"),
                           (ax[1], "CL", "스스로 제어 (폐루프)")):
        O, F, n = agg(mode)
        x = np.arange(6)
        a.bar(x - 0.2, O, 0.4, label="배포모델 p24")
        a.bar(x + 0.2, F, 0.4, label="승격판 G26_0811")
        for i in range(6):
            a.annotate(f"{100*(F[i]/O[i]-1):+.0f}%", (x[i] + 0.2, F[i]),
                       ha="center", va="bottom", fontsize=8)
        a.set_xticks(x); a.set_xticklabels(NM, fontsize=8)
        a.set_ylabel("예측 오차 RMSE (낮을수록 좋음)")
        a.set_title(f"{title}\n{n} 시행 · 전 채널 {O.mean():.2f} → {F.mean():.2f} "
                    f"({100*(F.mean()/O.mean()-1):+.0f}%)", fontsize=10)
        a.legend(fontsize=8); a.grid(alpha=0.3, axis="y")

    # 점프높이
    J = {**json.load(io.open(SRC / "_jumph.json", encoding="utf-8")),
         **json.load(io.open(SRC / "_jumph_cvt.json", encoding="utf-8"))}
    S = {}
    for k, v in J.items():
        if v[0]:
            S.setdefault(k.split("|")[0], []).append(v)
    ss = sorted(S)
    eo = [100 * np.mean([abs(x[1] / x[0] - 1) for x in S[s]]) for s in ss]
    ef = [100 * np.mean([abs(x[2] / x[0] - 1) for x in S[s]]) for s in ss]
    x = np.arange(len(ss))
    ax[2].bar(x - 0.2, eo, 0.4, label="배포모델 p24")
    ax[2].bar(x + 0.2, ef, 0.4, label="승격판")
    ax[2].set_xticks(x); ax[2].set_xticklabels([s[3:] for s in ss], fontsize=7, rotation=45)
    ax[2].set_ylabel("점프높이 오차 [%]")
    ax[2].set_title(f"점프 높이 (영상 실측 대비)\n{sum(len(S[s]) for s in ss)} 시행 · "
                    f"평균 {np.mean(eo):.2f}% → {np.mean(ef):.2f}%", fontsize=10)
    ax[2].legend(fontsize=8); ax[2].grid(alpha=0.3, axis="y")

    fig.suptitle("마라톤 G 결과 — 배포모델 대비 승격판 (109 시행 전수, 변속 포함)", fontsize=12)
    fig.tight_layout()
    fp = SRC / "00_마라톤결과.png"
    fig.savefig(fp, dpi=115)
    plt.close(fig)
    print(f"저장 → {fp}")


if __name__ == "__main__":
    main()
