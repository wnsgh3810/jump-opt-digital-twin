# -*- coding: utf-8 -*-
"""P19 최종 검증 — CMA-2 승자: 전 세션 CL τ-갭 + Mode A + 대표 그림 + 후보 저장."""
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P
import p19_run as R
from p19_cma2 import NAMES, IDX, parts_x, G6

DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p19_results")
(DST / "png").mkdir(parents=True, exist_ok=True)


def x32_of(v):
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(NAMES):
        if n in IDX:
            x32[IDX[n]] = v[i]
    return x32, ("calf" if v[0] > 1e-3 else "none")


def fig_tau(tag, ds, sub, d, L, A, m):
    t = d["t"]
    tp1 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4))
    ax[0].plot(t[m], s1[m], lw=1.4, label="tau_hip sim (예측)")
    ax[0].plot(t[m], tp1[m], lw=1.2, label="tau_hip 실측 (paper)")
    ax[1].plot(t[m], s2[m], lw=1.4, label="tau_knee sim (예측)")
    ax[1].plot(t[m], tp2[m], lw=1.2, label="tau_knee 실측 (paper)")
    for a in ax:
        a.grid(alpha=0.3); a.legend(fontsize=8); a.set_xlabel("t [s]")
        a.set_ylabel("shaft tau [Nm]")
    fig.suptitle(f"{ds}/{sub} [{tag}] — 폐루프 토크 예측 vs 실측")
    fig.tight_layout()
    fig.savefig(DST / "png" / f"{ds}_{sub}__{tag}.png".replace("/", "_"), dpi=110)
    plt.close(fig)


def full_report(v, tag, make_figs=()):
    x32, sp = x32_of(v)
    rows = R.eval_stack(x32, v[1], sp, P.A_PAPER, v[2], v[15], use_alpha=True)
    s = R.summarize(rows)
    print(f"[{tag}] FIT τ-갭 {100*s['FIT'][0]:.1f}%")
    for ds, val in s.items():
        if ds.startswith("jump"):
            print(f"  {ds:22s} {100*val[0]:5.1f}%  q2 {val[1]:.3f} (n={val[2]})", flush=True)
    jcl, ma, j429 = parts_x(v)
    print(f"  ModeA: " + " ".join(f"{g}={ma[g]:.0f}" for g in G6) +
          f" | 0429A(4sub) {j429:.1f}", flush=True)
    # 대표 그림
    if make_figs:
        model_f, _ = P.build_flip(x32, v[1], sp)
        model_c = None
        for ds_w, sub_w in make_figs:
            for t_ in R.TRIALS or R.all_trials():
                ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i = t_
                if ds != ds_w or sub != sub_w:
                    continue
                alphas = R.ALPH.get(ds, [1, 1, 1, 1])
                if is_cvt:
                    if model_c is None:
                        model_c, _ = P.build_cvt(x32, v[1], sp, l_i)
                    L = R.cl_run(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                                 v[15], alphas, 0.0, o1=0.0548, o2=-0.0524)
                else:
                    dd = dict(zip(P.J._P["FR"].NAMES, x32[:26]))
                    k1, k2 = P.J.OFFK.get(ds, (None, None))
                    o1 = dd.get(k1, 0.0) if k1 else 0.0
                    o2 = dd.get(k2, 0.0) if k2 else 0.0
                    L = R.cl_run(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                                 v[15], alphas, v[2], o1=o1, o2=o2)
                if L is not None:
                    fig_tau(tag, ds, sub, d, L, P.A_PAPER, m)
    return s, ma, j429, rows


def main():
    P.winit()
    W = json.load(open(HERE / "p19_cma2.json"))
    v = np.array(W["x"])
    print("WINNER:", " ".join(f"{n}={x:.4g}" for n, x in zip(NAMES, v)), flush=True)
    figs = [("jump_0602", "120_2_120_2"), ("jump_0424", "120_2_120_2"),
            ("jump_0429", "120_2_120_2"), ("jump_position_0421", None)]
    figs = [(a, b) for a, b in figs if b]
    s, ma, j429, rows = full_report(v, "P19", make_figs=figs)
    # x0 비교
    X = P.X37
    x0 = np.array([P.W18[0], P.W18[1], 2.06, X[14], X[16], X[15], X[17], X[12],
                   X[13], X[9], X[4], X[5], X[6], X[7], X[8], 0.008])
    s0, ma0, j4290, _ = full_report(x0, "x0_P18b")
    json.dump(dict(CANDIDATE="P19 — jump tau-fidelity stack (2026-07-10)",
                   names=NAMES, x=[float(x) for x in v],
                   cmdlayer=R.CMD, A="paper",
                   summary={k: list(map(float, val)) for k, val in s.items()},
                   modeA={g: float(ma[g]) for g in G6}, modeA_429=float(j429),
                   rows=rows),
              open(HERE / "fourbar_p19_candidate.json", "w"), indent=1)
    print("saved fourbar_p19_candidate.json", flush=True)


if __name__ == "__main__":
    main()
