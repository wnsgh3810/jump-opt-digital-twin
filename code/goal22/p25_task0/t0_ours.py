# -*- coding: utf-8 -*-
"""t0 그래프 — 우리 표준 (p25_e_plots 규약: 4×2 [q1 q2 / dq1 dq2 / τ1 τ2 â / bz GRF],
계획 실선 vs 배포 파선 같은 색(get_color), 색 자동 순환, 세로 점선=이지, Malgun).

산출: {stem}_ours_best.png (계획 vs 최적게인 FF+PD) · {stem}_ours_gains.png (계획 + 게인 8종)
CVT 계획은 계획 단독판.
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ["P25_CLIP_RAW"] = "25.5810"
os.environ["P25_GAINS_FULL"] = "1"

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p25_d_deploy as D
import p25_d_ff as FF
from t0_figs import _chan, _log_chan

LABEL = {"t0nc_nlp": "NLP", "t0nc_ol": "OL-CMA", "t0nc_cl": "CL-CMA", "t0nc_ppo": "PPO",
         "t0nc_ppo_long": "PPO(장기)", "t0wc_cl_li2508": "CVT CL l_i=25.08",
         "t0wc_cl_liopt": "CVT CL l_i=26.25"}
PANEL = [("q1", "q1 hip [rad]"), ("q2", "q2 knee(crank) [rad]"),
         ("dq1", "dq1 [rad/s]"), ("dq2", "dq2 [rad/s]"),
         ("tau1", "τ1 hip â [Nm]"), ("tau2", "τ2 knee â [Nm]"),
         ("bz", "base z [m]"), ("grf", "GRF [N]")]


def fig_ours(P, out_png, title, deps=None, t_lo=None, t_max=0.72):
    """deps: None(계획 단독) | {라벨: 채널}(1개=get_color 짝 / 여럿=계획 검정+auto cycle)."""
    multi = deps is not None and len(deps) > 1
    fig, axs = plt.subplots(4, 2, figsize=(11, 12), sharex=True)
    for ax, (key, ylab) in zip(axs.flat, PANEL):
        if multi:
            ax.plot(P["t"], P[key], "k", lw=2.0, label="계획")
            for gi, (lab, Dc) in enumerate(deps.items()):
                ax.plot(Dc["t"], Dc[key], f"C{gi % 10}", lw=1.0, alpha=0.85, label=lab)
        else:
            ln, = ax.plot(P["t"], P[key], lw=1.6, label="계획")
            if deps:
                lab, Dc = next(iter(deps.items()))
                ax.plot(Dc["t"], Dc[key], "--", lw=1.3, color=ln.get_color(), label="배포")
        if key.startswith("tau"):
            ax.axhline(15, ls=":", lw=1, alpha=0.5)
            ax.axhline(-15, ls=":", lw=1, alpha=0.5)
        if t_lo is not None and np.isfinite(t_lo):
            ax.axvline(t_lo, color="0.5", ls=":", lw=0.9, alpha=0.7)
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.25)
        ax.set_xlim(-0.02, t_max)
    axs[0, 0].legend(fontsize=7, ncol=2 if multi else 1)
    for a in axs[3]:
        a.set_xlabel("t [s]")
    fig.suptitle(title + "   [세로점선=이지]", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print("saved", Path(out_png).name, flush=True)


def do_nc(stem):
    z = np.load(HERE / f"{stem}.npz")
    P = _chan(z)
    lab = LABEL.get(stem, stem)
    deps, best = {}, None
    for gk in D.GAINS:
        r = FF.deploy_ff(HERE / f"{stem}.npz", gk, return_log=True)
        deps[gk] = _log_chan(r["log"])
        if best is None or r["F_tau"] < best[1]["F_tau"]:
            best = (gk, r)
    bg, br = best
    tlo = br.get("t_liftoff", float("nan"))
    fig_ours(P, HERE / f"{stem}_ours_best.png",
             f"[task0|no_cvt] {lab} — FF+PD {bg}  (h {br['h_plan']:.3f}→{br['h_PD']:.3f}, "
             f"F_τ {100*br['F_tau']:.1f}% · hip {100*br['F_tau_hip']:.1f} / knee {100*br['F_tau_knee']:.1f})",
             deps={bg: deps[bg]}, t_lo=tlo)
    fig_ours(P, HERE / f"{stem}_ours_gains.png",
             f"[task0|no_cvt] {lab} — FF+PD 게인 8종 (h_plan {br['h_plan']:.3f})",
             deps=deps, t_lo=tlo)


def main():
    only = sys.argv[1:] or None
    for stem in ("t0nc_ol", "t0nc_cl", "t0nc_nlp", "t0nc_ppo", "t0nc_ppo_long"):
        if (HERE / f"{stem}.npz").exists() and (only is None or stem in only):
            do_nc(stem)
    for stem in ("t0wc_cl_liopt", "t0wc_cl_li2508"):
        if (HERE / f"{stem}.npz").exists() and (only is None or stem in only):
            z = np.load(HERE / f"{stem}.npz")
            P = _chan(z)
            fig_ours(P, HERE / f"{stem}_ours.png",
                     f"[task0|with_cvt] {LABEL.get(stem, stem)} — h_plan {float(z['h_plan']):.3f} (계획)",
                     t_max=0.6)
    print("OURS DONE", flush=True)


if __name__ == "__main__":
    main()
