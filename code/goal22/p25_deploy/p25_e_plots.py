# -*- coding: utf-8 -*-
"""P25 표준 시계열 오버레이 — 계획(실선) vs 배포(파선), 채널별 같은 색 (get_color 패턴).

우리 표준 형식: 4×2 서브플롯 [q1 q2 / dq1 dq2 / τ1 τ2 (â Nm) / bz GRF].
케이스: 권고안(PPO best t18 FF+PD mid/high) + 대비(그대로 PD) + MPPI FF+PD.
실행: P25_CLIP_RAW=31.1771 P25_GAINS_FULL=1 python p25_e_plots.py  (t18 계획이므로 클립 필수)
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ.setdefault("P25_CLIP_RAW", "31.1771")
os.environ.setdefault("P25_GAINS_FULL", "1")

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p25_d_deploy as D
import p25_d_ff as FF

CASES = [  # (계획 npz, 모드, 게인 키, 파일 태그)
    ("p25_c_ppo_best_t18.npz", "FF+PD", "120_2_120_2", "ppo_ff_mid"),
    ("p25_c_ppo_best_t18.npz", "FF+PD", "150_2.2_500_4", "ppo_ff_high"),
    ("p25_c_ppo_best_t18.npz", "PD그대로", "120_2_120_2", "ppo_pd_mid"),
    ("p25_a_mppi_t18.npz", "FF+PD", "120_2_120_2", "mppi_ff_mid"),
]


def overlay(ax, tp, yp, tl, yl, ylab, lab_p="계획", lab_d="배포"):
    ln, = ax.plot(tp, yp, lw=1.6, label=lab_p)
    ax.plot(tl, yl, "--", lw=1.3, color=ln.get_color(), label=lab_d)
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.25)


def make_fig(npz, mode, gkey, tag):
    if mode == "FF+PD":
        r = FF.deploy_ff(HERE / npz, gkey, return_log=True)
    else:
        r = D.deploy(HERE / npz, gkey, return_log=True)
    L, plan = r["log"], r["_plan"]
    z = np.load(HERE / npz)
    t = plan["t"]
    tl = L["t"]
    zm = np.asarray(z["t"], float) >= 0
    tz = np.asarray(z["t"], float)[zm]
    tz = tz - tz[0]

    fig, axs = plt.subplots(4, 2, figsize=(11, 12), sharex=True)
    overlay(axs[0, 0], t, plan["qd"][:, 0], tl, L["q1"], "q1 hip [rad]")
    overlay(axs[0, 1], t, plan["qd"][:, 1], tl, L["q2"], "q2 knee(crank) [rad]")
    overlay(axs[1, 0], t, plan["dqd"][:, 0], tl, L["dq1"], "dq1 [rad/s]")
    overlay(axs[1, 1], t, plan["dqd"][:, 1], tl, L["dq2"], "dq2 [rad/s]")
    overlay(axs[2, 0], t, plan["tau"][:, 0], tl, L["sh1"], "τ1 hip â [Nm]",
            lab_p="계획 τ*", lab_d="배포 τ_PD")
    overlay(axs[2, 1], t, plan["tau"][:, 1], tl, L["sh2"], "τ2 knee â [Nm]",
            lab_p="계획 τ*", lab_d="배포 τ_PD")
    for a in (axs[2, 0], axs[2, 1]):
        a.axhline(18, ls=":", lw=1, alpha=0.5)
        a.axhline(-18, ls=":", lw=1, alpha=0.5)
    overlay(axs[3, 0], tz, np.asarray(z["bz"], float)[zm], tl, L["bz"], "base z [m]")
    axs[3, 0].axhline(r["h_plan"], ls=":", lw=1, alpha=0.5)
    axs[3, 0].axhline(r["h_PD"], ls="-.", lw=1, alpha=0.5)
    overlay(axs[3, 1], tz, np.asarray(z["grf"], float)[zm], tl, L["grf"], "GRF [N]")
    tlo = r.get("t_liftoff", float("nan"))
    for a in axs.flat:
        if np.isfinite(tlo):
            a.axvline(tlo, color="0.5", ls=":", lw=0.9, alpha=0.7)
        a.set_xlim(-0.02, 0.62)
    axs[0, 0].legend(fontsize=8)
    axs[2, 0].legend(fontsize=8)
    for a in axs[3]:
        a.set_xlabel("t [s]")
    meth = npz.replace("p25_", "").replace(".npz", "")
    fig.suptitle(f"{meth} · {mode} · 게인 {gkey}  —  h_plan {r['h_plan']:.3f} → h_PD {r['h_PD']:.3f} m, "
                 f"F_τ {100*r['F_tau']:.1f}% (hip {100*r['F_tau_hip']:.1f} / knee {100*r['F_tau_knee']:.1f})"
                 f"   [세로점선=이지]", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = HERE / f"p25_e_ts_{tag}.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("saved", out.name, flush=True)


def main():
    for npz, mode, gkey, tag in CASES:
        make_fig(npz, mode, gkey, tag)


if __name__ == "__main__":
    main()
