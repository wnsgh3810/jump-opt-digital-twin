# -*- coding: utf-8 -*-
"""P25-E — 전 방법 × 전 배포모드 통합 비교표 + 그림.

입력: p25_d_results.json(그대로 PD) · p25_d_shaped_results.json(기준 성형) · p25_d_ff_results.json(FF+PD)
출력: p25_e_master.json(전 행) · p25_e_table.md(마크다운 표) · p25_e_fig_{scatter,bars}.png
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import safe

METHOD = {
    "p25_a_ol_cma": ("OL-CMA", "개루프 토크 스플라인 CMA (트윈 직접)"),
    "p25_a_mppi": ("MPPI", "샘플링 MPC (트윈 직접)"),
    "p25_a_cl_cma": ("CL-CMA", "폐루프 인식 q_des 최적화 (트윈 직접)"),
    "p25_a_clt": ("CL-CMA(신뢰)", "폐루프 인식 + 측정 dq 신뢰영역"),
    "p25_a4_ilqr": ("iLQR", "box-DDP, mjd_transitionFD (트윈 원본 기울기)"),
    "p25_b_traj": ("NLP", "CasADi collocation (해석 등가모델+법칙층)"),
    "p25_c_ppo": ("PPO", "RL 파일럿 (최종 정책)"),
    "p25_c_ppo_best": ("PPO(best)", "RL 파일럿 (최고 체크포인트)"),
    "p25_a4_ilqr_strict": ("iLQR(엄격18)", "â≤18 전 구간 사영판"),
    "p25_c_ppo_strict": ("PPO(엄격18)", "â≤18 전 구간 사영판"),
    "p25_c_ppo_best_strict": ("PPO(best,엄격18)", "â≤18 전 구간 사영판"),
}
T18 = bool(os.environ.get("P25_T18"))
SUF = "_t18" if T18 else ""
FLOOR, NAIVE = 2.5, 64.7          # 기계 바닥 / 소박 재배포 (D 고정점 검증)
H_REAL, H_G20 = 0.98, 1.063       # 실측 최고 / G20 NLP 계획


def load_rows():
    rows = []
    p = HERE / f"p25_d_results{SUF}.json"
    if p.exists():
        res = json.load(open(p, encoding="utf-8"))["results"]
        for npz, per_g in res.items():
            for g, m in per_g.items():
                if isinstance(m, dict) and "F_tau" in m:
                    rows.append(dict(m, plan=npz, gains=g, mode="PD그대로"))
    for fn, mode in ((f"p25_d_shaped_results{SUF}.json", "성형"), (f"p25_d_ff_results{SUF}.json", "FF+PD")):
        p = HERE / fn
        if not p.exists():
            continue
        for key, m in json.load(open(p, encoding="utf-8")).items():
            if not (isinstance(m, dict) and "F_tau" in m):
                continue
            npz, g = key.split("|")
            rows.append(dict(m, plan=npz, gains=g, mode=mode))
    for r in rows:
        stem = r["plan"].replace(".npz", "").replace("_t18", "").replace("_t18", "")
        r["method"] = METHOD.get(stem, (stem, ""))[0]
    return rows


def main():
    rows = load_rows()
    safe.atomic_json_write(HERE / f"p25_e_master{SUF}.json", rows)

    # ── 마크다운 표 (방법 × 모드, 게인별 h_PD/F_τ) ──
    lines = ["| 방법 | 배포 모드 | 게인 | h_plan | h_PD | F_τ | F_τ hip | F_τ knee |",
             "|---|---|---|---|---|---|---|---|"]
    order = {m: i for i, m in enumerate(METHOD)}
    for r in sorted(rows, key=lambda r: (order.get(r["plan"].replace(".npz", "").replace("_t18", ""), 99),
                                         r["mode"], r["gains"])):
        lines.append(f"| {r['method']} | {r['mode']} | {r['gains']} | "
                     f"{r.get('h_plan', float('nan')):.3f} | {r['h_PD']:.3f} | "
                     f"{100*r['F_tau']:.1f}% | {100*r['F_tau_hip']:.1f}% | {100*r['F_tau_knee']:.1f}% |")
    (HERE / f"p25_e_table{SUF}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    # ── 그림 1: F_τ vs h_PD 산점 (배포 지형도) ──
    fig, ax = plt.subplots(figsize=(9, 6.5))
    marks = {"PD그대로": "o", "성형": "s", "FF+PD": "^"}
    meths = sorted({r["method"] for r in rows}, key=lambda m: order.get(
        next(k for k, v in METHOD.items() if v[0] == m), 99) if any(v[0] == m for v in METHOD.values()) else 99)
    for mi, meth in enumerate(meths):
        col = f"C{mi % 10}"
        for mode, mk in marks.items():
            xs = [100*r["F_tau"] for r in rows if r["method"] == meth and r["mode"] == mode]
            ys = [r["h_PD"] for r in rows if r["method"] == meth and r["mode"] == mode]
            if xs:
                ax.scatter(xs, ys, marker=mk, s=70, color=col, alpha=0.85,
                           label=f"{meth} · {mode}")
    ax.axvline(FLOOR, ls="--", lw=1, alpha=0.6)
    ax.axvline(NAIVE, ls=":", lw=1, alpha=0.6)
    ax.axhline(H_REAL, ls="--", lw=1, alpha=0.6)
    ax.axhline(H_G20, ls=":", lw=1, alpha=0.6)
    ax.text(FLOOR*1.05, ax.get_ylim()[0]+0.01, f"기계 바닥 {FLOOR}%", fontsize=8, rotation=90)
    ax.text(NAIVE*1.02, ax.get_ylim()[0]+0.01, f"소박 재배포 {NAIVE}%", fontsize=8, rotation=90)
    ax.text(0.3, H_REAL+0.005, f"실측 최고 {H_REAL}", fontsize=8)
    ax.text(0.3, H_G20+0.005, f"G20 계획 {H_G20}", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("F_τ = RMSE(τ_PD−τ*)/RMS(τ*) [%]  (왼쪽 = 계획 토크 충실)")
    ax.set_ylabel("h_PD [m]  (위 = 높이 실현)")
    ax.set_title("P25 배포 지형도 — 좌상단이 이상 (높이+τ-fidelity 동시)")
    ax.legend(fontsize=7, ncol=2, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(HERE / f"p25_e_fig_scatter{SUF}.png", dpi=140)

    # ── 그림 2: 방법별 최선 배포 (h_plan vs best h_PD, F_τ 주석) ──
    best = {}
    for r in rows:
        k = r["method"]
        if k not in best or r["F_tau"] < best[k]["F_tau"]:
            best[k] = r
    fig2, ax2 = plt.subplots(figsize=(9, 5))
    ms = [m for m in meths if m in best]
    x = np.arange(len(ms))
    hp = [best[m].get("h_plan", float("nan")) for m in ms]
    hd = [best[m]["h_PD"] for m in ms]
    ax2.bar(x-0.18, hp, 0.36, label="h_plan (계획)", alpha=0.85)
    ax2.bar(x+0.18, hd, 0.36, label="h_PD (최선 배포)", alpha=0.85)
    for i, m in enumerate(ms):
        ax2.text(i+0.18, hd[i]+0.012, f"F_τ {100*best[m]['F_tau']:.1f}%\n[{best[m]['mode']}·{best[m]['gains']}]",
                 ha="center", fontsize=7)
    ax2.axhline(H_REAL, ls="--", lw=1, alpha=0.6)
    ax2.text(-0.4, H_REAL+0.005, f"실측 최고 {H_REAL}", fontsize=8)
    ax2.set_xticks(x, ms)
    ax2.set_ylabel("apex 높이 [m]")
    ax2.set_title("방법별 계획 높이 vs 최선 배포 높이 (주석 = 그때의 F_τ·모드·게인)")
    ax2.legend()
    ax2.grid(axis="y", alpha=0.25)
    fig2.tight_layout()
    fig2.savefig(HERE / f"p25_e_fig_bars{SUF}.png", dpi=140)
    print("saved p25_e_master.json / p25_e_table.md / p25_e_fig_scatter.png / p25_e_fig_bars.png")


if __name__ == "__main__":
    main()
