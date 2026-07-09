# -*- coding: utf-8 -*-
"""P18c part2 — 반사실 실험: 실기가 못 한/안 한 조합을 트윈으로.
no_cvt(l_i=30) × load {2.5, 5, 7.5} + cvt(25.2) × load 7.5, 각각 천장 유/무.
CL 게인·목표궤적은 같은 그룹의 실측 trial에서 (no_cvt: no_load, cvt: load_5).
판정: 기립 성공 = 최종 0.3s 무릎각 목표 추종 + base 상승량."""
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
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from cvt_run2 import sim_run
from s2s_0604 import load_0604, build_0604, fig_trial, metrics_s2s, PRELOAD_30, DST, A

GAINS = json.load(open(HERE / "s2s_0604_gains.json"))


def cap_shaft(v=2.0):
    return float(J.ahat(A, np.array([35.5]), np.array([v]))[0])


def run_cf(args):
    grp, ref_sub, load, cap = args
    if not J._P:
        J.winit()
    d = load_0604(grp, ref_sub)
    model = build_0604(d["l_i"], load)
    pre = PRELOAD_30 if grp == "no_cvt" else 0.0
    g = GAINS[f"{grp}/{ref_sub}"]
    L, _ = sim_run(model, d, d["l_i"], "CL", gains=g, preload=pre, cap=cap)
    tagc = "cap" if cap else "nocap"
    name = f"{grp}_load{load}_{tagc}"
    if L is None:
        return dict(name=name, err="CRASH")
    t = d["t"]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    fin = t >= t[-1] - 0.3
    q2_fin_err = float(np.sqrt(np.mean((f(L["q2"]) - d["qd2"])[fin] ** 2)))
    bz = L["bz"][mk]
    rise = float(np.interp(t[-1] - 0.15, L["t"][mk], bz) - bz[0])
    pk = float(np.percentile(np.abs(L["sh2"][mk]), 99))
    over = float(np.mean(np.abs(L["sh2"][mk]) > cap_shaft())) * 100
    m = metrics_s2s(d, L)
    fig_trial(f"{grp}/CF_load{load}", d, L, m, f"CL{tagc}", d["l_i"], load,
              outdir="counterfactual")
    return dict(name=name, grp=grp, load=load, cap=bool(cap),
                q2_fin_err=q2_fin_err, rise=rise, pk99=pk, over_pct=over)


def main():
    J.winit()
    CAP = cap_shaft()
    print(f"supply ceiling (raw 35.5 -> shaft): {CAP:.1f} Nm", flush=True)
    import multiprocessing as mp
    jobs = []
    for load in (2.5, 5.0, 7.5):
        for cap in (None, CAP):
            jobs.append(("no_cvt", "no_load", load, cap))
    for cap in (None, CAP):
        jobs.append(("cvt", "load_5", 7.5, cap))
        jobs.append(("cvt", "load_5", 10.0, cap))
    pool = mp.Pool(8, initializer=J.winit)
    res = list(pool.imap_unordered(run_cf, jobs))
    pool.close(); pool.join()
    print(f"\n{'case':26s} {'기립(rise cm)':>12} {'q2종단err[deg]':>14} "
          f"{'cmd99% [Nm]':>11} {'천장초과%':>9}")
    for r in sorted([r for r in res if "err" not in r],
                    key=lambda r: (r["grp"], r["load"], r["cap"])):
        print(f"{r['name']:26s} {r['rise']*100:12.1f} "
              f"{np.degrees(r['q2_fin_err']):14.1f} {r['pk99']:11.1f} "
              f"{r['over_pct']:9.1f}", flush=True)
    json.dump(res, open(HERE / "s2s_0604_cf.json", "w"), indent=1)

    # 토크-마진 플롯: 측정(실기) + 반사실(트윈, cap) vs 천장
    real_pk = {}
    for grp, sub, load in [("cvt", "no_load", 0), ("cvt", "load_2.5", 2.5),
                           ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0)]:
        d = load_0604(grp, sub)
        tp2 = J.ahat(A, d["traw2"], d["dq2"])
        real_pk[(grp, load)] = float(np.percentile(np.abs(tp2), 99))
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    cv_r = [(l, v) for (g, l), v in real_pk.items() if g == "cvt"]
    ax.plot(*zip(*sorted(cv_r)), "o-", ms=8, label="CVT (l_i=25.2mm) — 실측")
    ax.plot([0], [real_pk[("no_cvt", 0)]], "s", ms=10, label="no-CVT (30mm) — 실측")
    for grp, mark, lab in [("no_cvt", "s--", "no-CVT — 트윈 반사실 (천장 적용)"),
                           ("cvt", "o--", "CVT — 트윈 반사실 (천장 적용)")]:
        pts = sorted([(r["load"], r["pk99"]) for r in res
                      if "err" not in r and r["grp"] == grp and r["cap"]])
        if grp == "no_cvt":
            pts = [(0, real_pk[("no_cvt", 0)])] + pts
        if pts:
            ax.plot(*zip(*pts), mark, alpha=0.8, label=lab)
    ax.axhline(CAP, color="r", ls=":", lw=2, label=f"공급 천장 {CAP:.1f} Nm (raw 35.5)")
    ax.set_xlabel("payload on base [kg]")
    ax.set_ylabel("knee motor shaft torque 99th pct [Nm]")
    ax.set_title("26.06.04 payload s2s — knee torque demand vs supply ceiling (P18b twin)")
    ax.grid(alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(DST / "torque_margin.png", dpi=130)
    print("saved torque_margin.png", flush=True)


if __name__ == "__main__":
    main()
