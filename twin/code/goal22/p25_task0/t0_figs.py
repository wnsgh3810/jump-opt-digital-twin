# -*- coding: utf-8 -*-
"""t0 그림 — AVT task0 스크립트의 그림 문법 그대로 (Figure1 3×2 / Figure2 에너지 / 스틱피겨).

색·선 규약 (task0_vertjump_no_cvt.py 775~895행 그대로):
- Figure1: 채널당 기본 색순환(C0=q1/hip, C1=q2/knee), 한계선 'k--', T-N 체크는 점('.')
- Figure2: hip '#2971B1' / knee '#C0392B' / total 'k--', GRF '#2E86AB'/'#E84855', 높이 막대 팔레트
- 스틱피겨: viridis 5포즈
배포 오버레이: 계획 실선, 배포 파선(같은 색) — 다게인 판은 게인마다 색순환.
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import t0_spec as S

TAU_LIM, DQ_LIM = 15.0, S.DQ_LIM
TN_C, TN_O = S.TN_COEF, S.TN_OFF


def _chan(z):
    """npz → dict(t,bz,dz,q1,q2,dq1,dq2,tau1,tau2,grf) (t≥0, â Nm 채널).
    쌍(pair)·행렬(Phase B: q/dq/tau_cmd_nm (N,2)) 스키마 겸용."""
    t = np.asarray(z["t"], float)
    m = t >= 0
    t = t[m] - t[m][0]
    if "q1" in z.files:
        g = lambda k: np.asarray(z[k], float)[m]
        bz = g("bz")
        return dict(t=t, bz=bz, dz=np.gradient(bz, t), q1=g("q1"), q2=g("q2"),
                    dq1=g("dq1"), dq2=g("dq2"), tau1=g("tau1_nm"), tau2=g("tau2_nm"),
                    grf=g("grf"))
    col = lambda k, j: np.asarray(z[k], float)[m][:, j]
    bz = np.asarray(z["bz"], float)[m]
    grf = (np.asarray(z["fz_plan"], float)[m] if "fz_plan" in z.files
           else np.asarray(z["grf"], float)[m])
    return dict(t=t, bz=bz, dz=np.gradient(bz, t), q1=col("q", 0), q2=col("q", 1),
                dq1=col("dq", 0), dq2=col("dq", 1),
                tau1=col("tau_cmd_nm", 0), tau2=col("tau_cmd_nm", 1), grf=grf)


def _log_chan(L):
    return dict(t=L["t"], bz=L["bz"], dz=np.gradient(L["bz"], L["t"]),
                q1=L["q1"], q2=L["q2"], dq1=L["dq1"], dq2=L["dq2"],
                tau1=L["sh1"], tau2=L["sh2"], grf=L["grf"])


def fig1(plan, out_png, title, deps=None, t_max=None):
    """task0 Figure1 (3×2). deps = {라벨: 채널dict} (파선 오버레이; 다게인이면 게인별 색)."""
    P = plan
    tm = t_max or P["t"][-1]
    multi = deps and len(deps) > 1
    plt.figure(figsize=(15, 8))
    plt.suptitle(title, fontsize=12)

    def over(sub, key, scale=1.0, plan_kw=None):
        plt.subplot(3, 2, sub)
        if multi:
            plt.plot(P["t"], scale * P[key], 'k', lw=2.2, label='계획')
            for gi, (lab, Dc) in enumerate(deps.items()):
                plt.plot(Dc["t"], scale * Dc[key], f'C{gi % 10}', lw=1.1, alpha=0.85, label=lab)
        else:
            ln, = plt.plot(P["t"], scale * P[key], lw=2, **(plan_kw or {}))
            if deps:
                lab, Dc = next(iter(deps.items()))
                plt.plot(Dc["t"], scale * Dc[key], '--', lw=1.5, color=ln.get_color(), label=f'배포 {lab}')
        plt.xlim(0, tm)
        plt.grid(True)

    over(1, "bz")
    plt.title("Base Height (m)")
    if multi:
        plt.legend(fontsize=6, ncol=2)
    over(2, "dz")
    plt.title("Base Vertical Velocity (m/s)")

    plt.subplot(3, 2, 3)
    plt.plot(P["t"], np.degrees(P["q1"]), label='q1 (Hip)')
    plt.plot(P["t"], np.degrees(P["q2"]), label='q2 (Knee)')
    if deps and not multi:
        lab, Dc = next(iter(deps.items()))
        plt.plot(Dc["t"], np.degrees(Dc["q1"]), 'C0--', lw=1.2)
        plt.plot(Dc["t"], np.degrees(Dc["q2"]), 'C1--', lw=1.2)
    plt.hlines(np.degrees([S.Q1_LB, S.Q1_UB]), 0, tm, 'C0', ':', alpha=0.5)
    plt.hlines(np.degrees([S.Q2_LB, S.Q2_UB]), 0, tm, 'C1', ':', alpha=0.5)
    plt.xlim(0, tm)
    plt.title("Joint Angles (deg)"); plt.legend(); plt.grid(True)

    plt.subplot(3, 2, 4)
    plt.plot(P["t"], P["dq1"], label='dq1')
    plt.plot(P["t"], P["dq2"], label='dq2')
    if deps and not multi:
        lab, Dc = next(iter(deps.items()))
        plt.plot(Dc["t"], Dc["dq1"], 'C0--', lw=1.2)
        plt.plot(Dc["t"], Dc["dq2"], 'C1--', lw=1.2)
    plt.hlines([-DQ_LIM, DQ_LIM], 0, tm, 'k', '--')
    plt.xlim(0, tm)
    plt.title("Joint Velocities (rad/s)"); plt.legend(); plt.grid(True)

    plt.subplot(3, 2, 5)
    plt.plot(P["t"], P["tau1"], label='Tau1 (Hip)')
    plt.plot(P["t"], P["tau2"], label='Tau2 (Knee)')
    if deps and not multi:
        lab, Dc = next(iter(deps.items()))
        plt.plot(Dc["t"], Dc["tau1"], 'C0--', lw=1.2)
        plt.plot(Dc["t"], Dc["tau2"], 'C1--', lw=1.2)
    plt.hlines([-TAU_LIM, TAU_LIM], 0, tm, 'k', '--')
    plt.xlim(0, tm)
    plt.title("Joint Torques (Nm, axis a-hat)"); plt.legend(); plt.grid(True)

    plt.subplot(3, 2, 6)
    tr = np.linspace(-TAU_LIM, TAU_LIM, 50)
    plt.plot(tr, TN_C * np.abs(tr) + TN_O, 'k--', alpha=0.3)
    plt.plot(P["tau1"], np.abs(P["dq1"]), '.', label='Motor 1 (hip)')
    plt.plot(P["tau2"], np.abs(P["dq2"]), '.', label='Motor 2 (knee)')
    if deps and not multi:
        lab, Dc = next(iter(deps.items()))
        plt.plot(Dc["tau1"], np.abs(Dc["dq1"]), '.', ms=3, alpha=0.5, color='C0')
        plt.plot(Dc["tau2"], np.abs(Dc["dq2"]), '.', ms=3, alpha=0.5, color='C1')
    plt.title("T-N Limit Check"); plt.legend(); plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=130)
    plt.close()
    print("saved", Path(out_png).name, flush=True)


def fig2(plan, out_png, title, h_bars=None, t_end=None):
    """task0 Figure2 — 파워/누적에너지/GRF+임펄스/높이 막대 (색 그대로)."""
    P = plan
    te = t_end or P["t"][-1]
    m = P["t"] <= te
    t = P["t"][m]
    Ph = P["tau1"][m] * P["dq1"][m]
    Pk = P["tau2"][m] * P["dq2"][m]
    Pt = Ph + Pk
    _trap = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    Wh = np.concatenate([[0], np.cumsum(0.5 * (Ph[1:] + Ph[:-1]) * np.diff(t))])
    Wk = np.concatenate([[0], np.cumsum(0.5 * (Pk[1:] + Pk[:-1]) * np.diff(t))])
    Wt = Wh + Wk
    imp = np.concatenate([[0], np.cumsum(0.5 * (P["grf"][m][1:] + P["grf"][m][:-1]) * np.diff(t))])

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(f"{title}\nW_hip={Wh[-1]:+.3f}J  W_knee={Wk[-1]:+.3f}J  W_mech={Wt[-1]:+.3f}J  |  "
                 f"Impulse_z={imp[-1]:.3f}N·s", fontsize=11)
    gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(t, Ph, '#2971B1', lw=2, label='Hip power')
    ax.plot(t, Pk, '#C0392B', lw=2, label='Knee power')
    ax.plot(t, Pt, 'k', lw=2, ls='--', label='Total')
    ax.fill_between(t, Pt, 0, where=(Pt >= 0), alpha=0.15, color='green')
    ax.fill_between(t, Pt, 0, where=(Pt < 0), alpha=0.15, color='red')
    ax.axhline(0, color='k', lw=0.8)
    ax.set(xlabel='Time (s)', ylabel='Power (W)', title='Instantaneous Power')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    ax = fig.add_subplot(gs[0, 1])
    ax.plot(t, Wh, '#2971B1', lw=2, label=f'W_hip  ({Wh[-1]:+.2f}J)')
    ax.plot(t, Wk, '#C0392B', lw=2, label=f'W_knee ({Wk[-1]:+.2f}J)')
    ax.plot(t, Wt, 'k', lw=2.5, ls='--', label=f'W_total ({Wt[-1]:+.2f}J)')
    ax.axhline(0, color='k', lw=0.8)
    ax.set(xlabel='Time (s)', ylabel='Cumul. work (J)', title='Cumulative Energy')
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    ax = fig.add_subplot(gs[1, 0])
    ax2 = ax.twinx()
    ax.plot(t, P["grf"][m], '#2E86AB', lw=2, label='GRF_z (N)')
    ax2.plot(t, imp, '#2E86AB', lw=1.5, ls='--', alpha=0.7, label=f'Impulse_z ({imp[-1]:.3f} N·s)')
    ax.set(xlabel='Time (s)', ylabel='Force (N)', title='GRF: ground→robot')
    ax2.set_ylabel('Cumul. impulse (N·s)')
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc='lower center')
    ax.grid(True, alpha=0.3)

    ax = fig.add_subplot(gs[1, 1])
    if h_bars:
        names = list(h_bars)
        vals = [h_bars[k] for k in names]
        cols = ['#95A5A6', '#5B9BD5', '#76A5E3', '#C0392B', '#E67E22'][:len(names)]
        bars = ax.bar(names, vals, color=cols, alpha=0.8, edgecolor='k', lw=0.8)
        for b, h in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.005, f'{h:.3f}m',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax.axhline(0.98, color='gray', ls=':', lw=1.2, label='실측 최고 0.98m')
        ax.set(ylabel='Jump height (m)', title='Jump Height Comparison')
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, max(vals) * 1.18)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print("saved", Path(out_png).name, flush=True)


def fig_stick(plan, out_png, title, n_pose=5, t_end=None):
    """task0 Figure3 — viridis 5포즈 스틱피겨 (AVT 2링크 기하, l1=l2=0.25)."""
    P = plan
    te = t_end or P["t"][-1]
    m = P["t"] <= te
    idxs = np.linspace(0, m.sum() - 1, n_pose, dtype=int)
    colors = plt.cm.viridis(np.linspace(0, 1, n_pose))
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot([-0.5, 0.5], [0, 0], 'k-', lw=3)
    for ci, i in enumerate(idxs):
        zi, q1i, q2i = P["bz"][m][i], P["q1"][m][i], P["q2"][m][i]
        kx, ky = S.L1 * np.cos(q1i), zi + S.L1 * np.sin(q1i)
        fx, fy = kx + S.L2 * np.cos(q1i + q2i), ky + S.L2 * np.sin(q1i + q2i)
        ax.plot([0, kx, fx], [zi, ky, fy], 'o-', lw=2, color=colors[ci],
                label=f't={P["t"][m][i]:.2f}s')
    ax.set_title(title)
    ax.set_xlim([-0.15, 0.35]); ax.set_ylim([-0.05, 0.75])
    ax.set_aspect('equal', adjustable='box')
    ax.legend(); ax.grid(True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print("saved", Path(out_png).name, flush=True)
