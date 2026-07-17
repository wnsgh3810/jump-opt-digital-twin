# -*- coding: utf-8 -*-
"""p25_d_runall — Phase D 일괄 배포 리허설: 전 방법 계획 × 2 게인세트.

입력: p25_deploy/ 의 `p25_[abc]_*.npz` 계획 파일 (스키마 = p25_d_deploy 모듈
docstring의 계약 — Phase A(i/ii/iii)/B/C가 이 이름 규약으로 산출).
  예: p25_a_cma.npz / p25_a_mppi.npz / p25_a_claware.npz / p25_b_nlp.npz / p25_c_ppo.npz
검증 산출물(p25_d_golden/fixedpoint)은 접두사 p25_d_라 스캔에 안 걸림.

출력:
  p25_d_results.json  — {계획: {게인세트: deploy() dict}}
  p25_d_compare.png   — h_plan vs h_PD 막대 (방법×게인, F_τ 주석; auto color cycle)
  stdout 비교표       — h_plan/h_PD/H_fid/F_τ(pooled·hip·knee)/dq RMSE/이지 시각

사용: 배포 리허설 게인 2종 = MARATHON 선고정 (mid 120_2_120_2 / high 150_2.2_500_4).
"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

import p25_d_deploy as D
import safe

GAINSETS = tuple(D.GAINS)          # env P25_GAINS_FULL=1 → 8종
T18 = bool(os.environ.get("P25_T18"))   # 1 → *_t18 계획만 + 클립 31.1771 (P25_CLIP_RAW 동반 필수)
SUF = "_t18" if T18 else ""
OUT_JSON = HERE / f"p25_d_results{SUF}.json"
OUT_PNG = HERE / f"p25_d_compare{SUF}.png"


def scan_plans():
    ps = sorted(set(HERE.glob("p25_[abc]_*.npz")) | set(HERE.glob("p25_a4_*.npz")))
    return [p for p in ps if ("_t18" in p.stem) == T18]


def _f(x, fmt):
    return fmt.format(x) if np.isfinite(x) else "  —  "


def print_table(results):
    hdr = (f"{'계획':28s} {'게인':5s} {'h_plan':>7s} {'h_PD':>7s} {'H_fid':>7s} "
           f"{'F_τ':>7s} {'F_τ,hip':>8s} {'F_τ,knee':>9s} {'dqRMSE':>7s} {'이지':>7s}")
    print(hdr, flush=True)
    print("─" * len(hdr), flush=True)
    for name, per in results.items():
        for gl, r in per.items():
            if r.get("crash"):
                print(f"{name:28s} {gl:5s} {'CRASH':>7s}", flush=True)
                continue
            print(f"{name:28s} {gl:5s} "
                  f"{_f(r['h_plan'], '{:7.3f}')} {_f(r['h_PD'], '{:7.3f}')} "
                  f"{_f(r['H_fid'] * 100, '{:6.1f}%')} "
                  f"{_f(r['F_tau'] * 100, '{:6.1f}%')} "
                  f"{_f(r['F_tau_hip'] * 100, '{:7.1f}%')} "
                  f"{_f(r['F_tau_knee'] * 100, '{:8.1f}%')} "
                  f"{_f(r['dq_rmse'], '{:7.2f}')} "
                  f"{_f(r['t_liftoff'] * 1000, '{:5.0f}ms')}"
                  + ("  [apex censored]" if r.get("apex_censored") else ""),
                  flush=True)


def make_fig(results):
    names = list(results)
    x = np.arange(len(names))
    w = 0.8 / (len(GAINSETS) + 1)
    hp = [results[n][GAINSETS[0]].get("h_plan", float("nan")) for n in names]
    fig, ax = plt.subplots(figsize=(max(7, 1.9 * len(names) + 3), 4.6))
    ax.bar(x - w, hp, w, label="h_plan (최적화기 롤아웃)")
    for j, gl in enumerate(GAINSETS):
        hv = [results[n][gl].get("h_PD", float("nan")) for n in names]
        bars = ax.bar(x + j * w, hv, w,
                      label=f"h_PD ({gl} { '_'.join(f'{v:g}' for v in D.GAINS[gl]) })")
        for b, n in zip(bars, names):
            ft = results[n][gl].get("F_tau", float("nan"))
            if np.isfinite(ft) and np.isfinite(b.get_height()):
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                        f"F_τ\n{ft * 100:.0f}%", ha="center", va="bottom",
                        fontsize=8)
    tops = [v for n in names for v in
            (results[n][GAINSETS[0]].get("h_plan", 0),
             *(results[n][g].get("h_PD", 0) for g in GAINSETS))
            if np.isfinite(v)]
    if tops:
        ax.set_ylim(0, max(tops) * 1.18)            # F_τ 주석 머리공간
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace("p25_", "").replace(".npz", "") for n in names],
                       rotation=15, ha="right")
    ax.set_ylabel("apex 높이 [m]")
    ax.set_title(f"P25 Phase D 배포 리허설 — h_plan vs h_PD ({D.MODEL_TAG} 트윈, "
                 f"F_τ 주석)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=130)
    plt.close(fig)
    print(f"그림 저장: {OUT_PNG}", flush=True)


def main():
    safe.utf8_console()
    plans = scan_plans()
    if not plans:
        print("계획 파일 없음 (p25_[abc]_*.npz) — Phase A/B/C 산출 대기 중. "
              "하네스 ready (검증은 p25_d_deploy.py validate).", flush=True)
        return
    t0 = time.time()
    D.setup()
    results = {}
    for p in plans:
        per = {}
        for gl in GAINSETS:
            r = D.deploy(p, gl)
            per[gl] = r
            print(f"deploy {p.name} [{gl}] — h_PD "
                  f"{_f(r.get('h_PD', float('nan')), '{:.3f}')} m, F_τ "
                  f"{_f(r.get('F_tau', float('nan')) * 100, '{:.1f}%')}"
                  + (" CRASH" if r.get("crash") else ""), flush=True)
        results[p.name] = per
    safe.atomic_json_write(OUT_JSON, dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), model=D.MODEL_TAG,
        gainsets={g: list(D.GAINS[g]) for g in GAINSETS}, results=results))
    print(f"결과 원장 저장: {OUT_JSON}", flush=True)
    print_table(results)
    make_fig(results)
    print(f"DONE [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
