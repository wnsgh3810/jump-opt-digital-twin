# -*- coding: utf-8 -*-
"""P25-E 교차 — 토크캡 캠페인 비교 (20.2Nm[raw 35.5] vs 18Nm[raw 31.18]).

입력: p25_e_master.json / p25_e_master_t18.json (p25_e_summary 산출)
출력: p25_e_cross_table.md · p25_e_fig_cross.png (방법별 h_plan/최선배포 h_PD 캡 비교)
      p25_e_fig_gainrobust.png (FF+PD의 게인 강건성 — 게인 8종에 걸친 F_τ 범위)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
ORDER = ["OL-CMA", "MPPI", "CL-CMA", "CL-CMA(신뢰)", "iLQR", "NLP", "PPO", "PPO(best)"]


def best_rows(master):
    """방법별: h_plan, FF+PD 최저 F_τ 행, FF+PD의 게인 전체 F_τ/h_PD 범위."""
    out = {}
    for r in master:
        m = r["method"]
        d = out.setdefault(m, dict(h_plan=r.get("h_plan"), ff=[], best=None))
        if r["mode"] == "FF+PD":
            d["ff"].append(r)
        b = d["best"]
        if b is None or r["F_tau"] < b["F_tau"]:
            d["best"] = r
    return out


def main():
    A = best_rows(json.load(open(HERE / "p25_e_master.json", encoding="utf-8")))
    B = best_rows(json.load(open(HERE / "p25_e_master_t18.json", encoding="utf-8")))

    lines = ["| 방법 | h_plan 20.2 | h_plan 18 | Δ | 최선배포 h_PD/F_τ (20.2) | 최선배포 h_PD/F_τ (18) |",
             "|---|---|---|---|---|---|"]
    meths = [m for m in ORDER if m in A or m in B]
    for m in meths:
        a, b = A.get(m), B.get(m)
        def hb(d):
            if not d or not d["best"]:
                return "—"
            r = d["best"]
            return f"{r['h_PD']:.3f} / {100*r['F_tau']:.1f}% [{r['mode']}·{r['gains']}]"
        hpA = f"{a['h_plan']:.3f}" if a and a.get("h_plan") else "—"
        hpB = f"{b['h_plan']:.3f}" if b and b.get("h_plan") else "—"
        dd = (f"{100*(b['h_plan']/a['h_plan']-1):+.1f}%"
              if a and b and a.get("h_plan") and b.get("h_plan") else "—")
        lines.append(f"| {m} | {hpA} | {hpB} | {dd} | {hb(a)} | {hb(b)} |")
    (HERE / "p25_e_cross_table.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    # ── 그림 1: 캡 비교 (h_plan + 최선 FF+PD h_PD) ──
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(meths))
    w = 0.2
    for k, (lab, D_, off) in enumerate((("h_plan 20.2Nm", A, -1.5), ("h_plan 18Nm", B, -0.5),
                                        ("최선배포 20.2Nm", A, 0.5), ("최선배포 18Nm", B, 1.5))):
        if "h_plan" in lab:
            ys = [D_.get(m, {}).get("h_plan") or np.nan for m in meths]
        else:
            ys = [(D_.get(m, {}).get("best") or {}).get("h_PD", np.nan) for m in meths]
        ax.bar(x + off * w, ys, w, label=lab, alpha=0.85)
    ax.axhline(0.98, ls="--", lw=1, alpha=0.6)
    ax.text(-0.45, 0.985, "실측 최고 0.98", fontsize=8)
    ax.set_xticks(x, meths, rotation=12, ha="right")
    ax.set_ylabel("apex 높이 [m]")
    ax.set_title("토크캡 비교 — 계획 높이와 최선 배포 높이 (20.2Nm[raw 35.5] vs 18Nm[raw 31.18])")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(HERE / "p25_e_fig_cross.png", dpi=140)

    # ── 그림 2: FF+PD 게인 강건성 (캠페인별, 방법별 F_τ min~max 밴드) ──
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    for j, (lab, D_) in enumerate((("20.2Nm", A), ("18Nm", B))):
        xs, lo, hi, md = [], [], [], []
        for i, m in enumerate(meths):
            ff = D_.get(m, {}).get("ff", [])
            if not ff:
                continue
            fts = [100 * r["F_tau"] for r in ff]
            xs.append(i + (j - 0.5) * 0.3)
            lo.append(min(fts)); hi.append(max(fts)); md.append(float(np.median(fts)))
        ax2.errorbar(xs, md, yerr=[np.array(md) - np.array(lo), np.array(hi) - np.array(md)],
                     fmt="o", capsize=4, label=f"FF+PD F_τ (게인 8종 범위) — {lab}")
    ax2.axhline(2.5, ls="--", lw=1, alpha=0.6)
    ax2.text(-0.45, 2.6, "기계 바닥 2.5%", fontsize=8)
    ax2.set_yscale("log")
    ax2.set_xticks(range(len(meths)), meths, rotation=12, ha="right")
    ax2.set_ylabel("F_τ [%] (로그)")
    ax2.set_title("FF+PD 배포의 게인 강건성 — 실 세션 게인 8종에 걸친 F_τ 중앙값과 범위")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.25)
    fig2.tight_layout()
    fig2.savefig(HERE / "p25_e_fig_gainrobust.png", dpi=140)
    print("saved p25_e_cross_table.md / p25_e_fig_cross.png / p25_e_fig_gainrobust.png")


if __name__ == "__main__":
    main()
