# -*- coding: utf-8 -*-
"""고게인 확장 스터디 — 전 방법 × {FF+PD, PD단독} × 확장 게인 4종 (사용자 지시 07-18).

게인: 배포가능 300_3_500_4 / 500_5_500_5 (MIT 인코딩 상한 kp≤500·kd≤5 내, 힙 강화)
      시뮬전용 1000_8_2000_10 / 2000_10_8000_20 (실기 불가 — 극한 레짐 연구)
산출: 기준양식 그림 graphs/<방법>/<모드>/gain_<라벨>.png + 원장 t0_hi_gains.json
      + 추세 그림 graphs/summary/gain_trend.png (게인↑에 따른 F_τ·h_PD·des/plan 거리)
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ["P25_CLIP_RAW"] = "35.5"
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
import safe
from t0_figs import _chan, _log_chan
from t0_ours import fig_std, rmse_vs, MDIR

HI = [("300_3_500_4", (300.0, 3.0, 500.0, 4.0), "배포가능"),
      ("500_5_500_5", (500.0, 5.0, 500.0, 5.0), "배포가능"),
      ("1000_8_2000_10", (1000.0, 8.0, 2000.0, 10.0), "시뮬전용"),
      ("2000_10_8000_20", (2000.0, 10.0, 8000.0, 20.0), "시뮬전용")]
for _gl, _g4, _ in HI:          # deploy_ff는 게인 키 조회형 — 확장 게인 등록
    D.GAINS[_gl] = _g4

MODES = (("FF+PD", "ffpd", lambda p, g: FF.deploy_ff(p, g, return_log=True)),
         ("PD단독", "pd_only", lambda p, g: D.deploy(p, g, return_log=True)))


def dq_dist(P, Dc, ref_key, tmax):
    m = P["t"] <= tmax
    s = np.interp(P["t"][m], Dc["t"], Dc["dq2"])
    return float(np.sqrt(np.mean((s - P[ref_key][m]) ** 2)))


def main():
    rows = {}
    for stem, mdir in MDIR.items():
        f = HERE / f"{stem}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        P = _chan(z)
        has_des = "qd1" in z.files and np.max(np.abs(
            np.asarray(z["qd1"], float)[np.asarray(z["t"], float) >= 0] - P["q1"])) > 1e-6
        if has_des:
            mm = np.asarray(z["t"], float) >= 0
            P = dict(P, qd1=np.asarray(z["qd1"], float)[mm], qd2=np.asarray(z["qd2"], float)[mm],
                     ddq1=np.asarray(z["dqd1"], float)[mm], ddq2=np.asarray(z["dqd2"], float)[mm])
        for glabel, g4, cls in HI:
            for mname, sub, fn in MODES:
                r = fn(f, glabel)
                if r.get("crash"):
                    print(f"[{stem}|{mname}|{glabel}] CRASH", flush=True)
                    continue
                Dc = _log_chan(r["log"])
                tlo = r.get("t_liftoff", float("nan"))
                tm = tlo if np.isfinite(tlo) else 0.3
                row = dict(h_plan=float(r["h_plan"]), h_PD=float(r["h_PD"]),
                           F_tau=float(r["F_tau"]), cls=cls,
                           rmse_dq_plan=dq_dist(P, Dc, "dq2", tm))
                if has_des:
                    row["rmse_dq_des"] = dq_dist(P, Dc, "ddq2", tm)
                rows[f"{stem}|{sub}|{glabel}"] = row
                ttl = (f"{stem}/{glabel} [{mname} p24a, task0 15Nm · {cls}] — "
                       f"h_PD {r['h_PD']:.2f} / h_plan {r['h_plan']:.2f} m  (F_τ {100*r['F_tau']:.1f}%)")
                out = HERE / "graphs" / mdir / sub / f"gain_{glabel}.png"
                out = HERE / "graphs" / MDIR[stem] / sub / f"gain_{glabel}.png"
                fig_std(P, Dc, out, ttl, tlo)
                print(f"[{stem}|{mname}|{glabel}] h_PD {r['h_PD']:.3f} F_τ {100*r['F_tau']:.1f}%", flush=True)
    safe.atomic_json_write(HERE / "t0_hi_gains.json", rows)

    # ── 추세 그림: 기존 8게인 원장 + 확장 4게인 (F_τ vs 게인 순번) ──
    base = None
    p = HERE / "t0_deploy_results.json"
    if p.exists():
        import json
        base = json.load(open(p, encoding="utf-8"))
    order = ["60_1.5_60_1.5", "90_1.5_90_2.5", "120_2_120_2", "120_2.2_150_2.5",
             "120_2.2_200_2.8", "150_2.2_250_3", "150_2.2_350_3.5", "150_2.2_500_4",
             "300_3_500_4", "500_5_500_5", "1000_8_2000_10", "2000_10_8000_20"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for ax, (mname, sub, _) in zip(axs, MODES):
        for stem, mdir in MDIR.items():
            xs, ys = [], []
            for gi, gl in enumerate(order):
                v = None
                if gi < 8 and base is not None:
                    v = base.get(f"{stem}.npz|{mname if mname!='PD단독' else '그대로'}|{gl}")
                    if v:
                        v = v.get("F_tau")
                else:
                    rr = rows.get(f"{stem}|{sub}|{gl}")
                    if rr:
                        v = rr["F_tau"]
                if v is not None:
                    xs.append(gi)
                    ys.append(100 * v)
            if xs:
                ax.plot(xs, ys, "o-", lw=1.5, label=mdir)
        ax.axvline(7.5, color="0.5", ls="--", lw=1)
        ax.axvline(9.5, color="0.5", ls=":", lw=1)
        ax.text(7.6, ax.get_ylim()[1] * 0.9, "← 실 세션 | 확장 →", fontsize=8)
        ax.text(9.6, ax.get_ylim()[1] * 0.8, "← 배포가능 | 시뮬전용 →", fontsize=8)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
        ax.set_title(f"{mname}")
        ax.set_ylabel("F_τ [%]")
        ax.set_yscale("log")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("게인 확장 스터디 — F_τ vs 게인 (전 방법, 좌 FF+PD / 우 순수 PD)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / "graphs" / "summary" / "gain_trend.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    print("saved gain_trend.png", flush=True)


if __name__ == "__main__":
    main()
