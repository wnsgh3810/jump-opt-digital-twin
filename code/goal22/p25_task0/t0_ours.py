# -*- coding: utf-8 -*-
"""t0 그래프 — g22_p24a_all_results 양식 그대로 (사용자 기준 확정 07-18).

양식 (jump_0602/png/*__CL.png와 동일): 2×3 패널
  [q deg (q1·q2 합본 + q_des 초록파선) | dq1 hip | dq2 crank]
  [hip tau | knee(crank) tau | GRF z]
색: sim(배포)=C0 파랑 · plan(계획)=C1 주황 · q_des=C2 초록 파선. 트라이얼(게인)당 1장.
제목: 계획/게인 [FF+PD p24a, task0 15Nm] — q2 RMSE · dq2 RMSE · h_PD / h_plan
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
         "t0nc_ppo_long": "PPO_long"}


def fig_std(P, Dc, out_png, title, t_lo):
    """P=계획 채널, Dc=배포 채널 — p24a all_results 2×3 양식.
    창(t≤tm) 밖 데이터(착지 충격 등)는 플롯 전에 잘라냄 — y축 자동스케일 오염 방지."""
    tm = (t_lo + 0.05) if np.isfinite(t_lo) else 0.35
    P = {k: np.asarray(v)[np.asarray(P["t"]) <= tm] for k, v in P.items()}
    Dc = {k: np.asarray(v)[np.asarray(Dc["t"]) <= tm] for k, v in Dc.items()}
    fig, axs = plt.subplots(2, 3, figsize=(15, 7))

    ax = axs[0, 0]
    ax.plot(Dc["t"], np.degrees(Dc["q1"]), "C0", lw=1.6, label="q1 sim")
    ax.plot(P["t"], np.degrees(P["q1"]), "C1", lw=1.4, label="q1 plan")
    ax.plot(Dc["t"], np.degrees(Dc["q2"]), "C0", lw=1.6, label="q2(crank) sim")
    ax.plot(P["t"], np.degrees(P["q2"]), "C1", lw=1.4, label="q2 plan")
    ax.plot(P["t"], np.degrees(P["q1"]), "C2", lw=1.1, ls="--", label="q_des", alpha=0.8)
    ax.plot(P["t"], np.degrees(P["q2"]), "C2", lw=1.1, ls="--", alpha=0.8)
    ax.set(xlabel="t [s]", ylabel="q [deg]")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

    for ax, kd, ylab in ((axs[0, 1], "dq1", "dq1 hip [rad/s]"),
                         (axs[0, 2], "dq2", "dq2 crank [rad/s]")):
        ax.plot(Dc["t"], Dc[kd], "C0", lw=1.6, label="sim")
        ax.plot(P["t"], P[kd], "C1", lw=1.4, label="plan")
        ax.set(xlabel="t [s]", ylabel=ylab)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    for ax, kt, ylab in ((axs[1, 0], "tau1", "hip tau [Nm]"),
                         (axs[1, 1], "tau2", "knee(crank) tau [Nm]")):
        ax.plot(Dc["t"], Dc[kt], "C0", lw=1.6, label="sim shaft tau")
        ax.plot(P["t"], P[kt], "C1", lw=1.4, label="plan tau (a_hat)")
        ax.set(xlabel="t [s]", ylabel=ylab)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    ax = axs[1, 2]
    ax.plot(Dc["t"], Dc["grf"], "C0", lw=1.6, label="sim")
    ax.plot(P["t"], P["grf"], "C1", lw=1.4, label="plan")
    ax.set(xlabel="t [s]", ylabel="GRF z [N]")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    for ax in axs.flat:
        ax.set_xlim(-0.02, tm)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    print("saved", Path(out_png).name, flush=True)


def rmse_vs(P, Dc, key, tmax):
    m = P["t"] <= tmax
    d = np.interp(P["t"][m], Dc["t"], Dc[key])
    return float(np.sqrt(np.mean((d - P[key][m]) ** 2)))


def do_nc(stem):
    z = np.load(HERE / f"{stem}.npz")
    P = _chan(z)
    lab = LABEL.get(stem, stem)
    best = None
    for gk in D.GAINS:
        r = FF.deploy_ff(HERE / f"{stem}.npz", gk, return_log=True)
        Dc = _log_chan(r["log"])
        tlo = r.get("t_liftoff", float("nan"))
        rq2 = rmse_vs(P, Dc, "q2", tlo if np.isfinite(tlo) else 0.3)
        rdq2 = rmse_vs(P, Dc, "dq2", tlo if np.isfinite(tlo) else 0.3)
        ttl = (f"{stem}/{gk} [FF+PD p24a, task0 15Nm · l_i=30.0mm] — "
               f"q2 RMSE {rq2:.3f} rad · dq2 {rdq2:.2f} · "
               f"h_PD {r['h_PD']:.2f} / h_plan {r['h_plan']:.2f} m  (F_τ {100*r['F_tau']:.1f}%)")
        fig_std(P, Dc, HERE / f"{stem}_std_{gk}.png", ttl, tlo)
        if best is None or r["F_tau"] < best[1]:
            best = (gk, r["F_tau"])
    print(f"[{stem}] best gain {best[0]} (F_τ {100*best[1]:.1f}%)", flush=True)


def main():
    only = sys.argv[1:] or None
    for stem in ("t0nc_ol", "t0nc_cl", "t0nc_nlp", "t0nc_ppo", "t0nc_ppo_long"):
        if (HERE / f"{stem}.npz").exists() and (only is None or stem in only):
            do_nc(stem)
    print("STD DONE", flush=True)


if __name__ == "__main__":
    main()
