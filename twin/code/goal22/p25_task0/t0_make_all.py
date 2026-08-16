# -*- coding: utf-8 -*-
"""t0 산출물 일괄 생성 — 계획별: fig1(단독/8게인/최적게인) + fig2 + 스틱 + GIF(계획/최적배포).

no_cvt: 배포 로그 포함 (FF+PD, 게인 8종 — t0_deploy와 동일 배선).
with_cvt: 계획 그림/GIF만 (배포 하네스는 flip 전용 — 정직 표기). GIF 무릎각은
animate_results.calc_q2_from_qm(4절 정운동학)으로 크랭크→무릎 변환.
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ["P25_CLIP_RAW"] = "25.5810"
os.environ["P25_GAINS_FULL"] = "1"

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))
sys.path.insert(0, r"C:\Users\junho\CVT\AVT LEG\optimization_tasks")

import t0_figs as F
import t0_export as E

NC_LABEL = {"t0nc_nlp": "NLP", "t0nc_ol": "OL-CMA", "t0nc_cl": "CL-CMA",
            "t0nc_ppo": "PPO", "t0nc_ppo_best": "PPO(best)"}


def apex_tmax(P):
    k = int(np.argmax(P["bz"]))
    return float(min(P["t"][-1], P["t"][k] + 0.12))


def do_nc(stem):
    import p25_d_ff as FF
    z = np.load(HERE / f"{stem}.npz")
    P = F._chan(z)
    tm = apex_tmax(P)
    lab = NC_LABEL.get(stem, stem)
    ttl = f"[task0 제약 | no_cvt] {lab} — h_plan {float(z['h_plan']):.3f} m"
    F.fig1(P, HERE / f"{stem}_fig1.png", ttl, t_max=tm)
    # 배포 (FF+PD × 8게인)
    deps, best = {}, None
    import p25_d_deploy as D
    for gk in D.GAINS:
        r = FF.deploy_ff(HERE / f"{stem}.npz", gk, return_log=True)
        deps[gk] = F._log_chan(r["log"])
        if best is None or r["F_tau"] < best[1]["F_tau"]:
            best = (gk, r)
    F.fig1(P, HERE / f"{stem}_fig1_gains.png",
           ttl + "  |  FF+PD 배포 게인 8종 오버레이", deps=deps, t_max=tm)
    bg, br = best
    F.fig1(P, HERE / f"{stem}_fig1_best.png",
           ttl + f"  |  최적게인 {bg} (F_τ {100*br['F_tau']:.1f}%, h_PD {br['h_PD']:.3f})",
           deps={bg: deps[bg]}, t_max=tm)
    F.fig2(P, HERE / f"{stem}_fig2.png", ttl,
           h_bars={"h_plan": float(z["h_plan"]), f"h_PD\n({bg})": br["h_PD"]},
           t_end=br.get("t_liftoff", 0.3))
    F.fig_stick(P, HERE / f"{stem}_stick.png", f"{ttl} — Stick Figure", t_end=tm)
    E.gif_of(P, HERE / f"{stem}.gif", f"{lab} plan (task0, 15Nm)")
    E.gif_of(deps[bg], HERE / f"{stem}_deploy.gif", f"{lab} FF+PD {bg}")
    print(f"[{stem}] done — best {bg} F_τ {100*br['F_tau']:.1f}%", flush=True)


def do_wc(stem, full=True):
    from animate_results import calc_q2_from_qm
    z = np.load(HERE / f"{stem}.npz")
    P = F._chan(z)
    tm = apex_tmax(P)
    li = float(np.atleast_1d(z["l_i"])[0])
    t_all = np.asarray(z["t"], float)
    qm = np.asarray(z["qm"], float)[t_all >= 0]
    ttl = f"[task0 제약 | with_cvt l_i={li:.2f}mm] {stem.split('_')[1].upper()} — h_plan {float(z['h_plan']):.3f} m"
    F.fig1(P, HERE / f"{stem}_fig1.png", ttl + "  (q2=크랭크)", t_max=tm)
    if not full:
        return
    # 무릎각 (4절 정운동학) — 스틱/GIF용
    q2k = np.array([calc_q2_from_qm(abs(q), li / 1000.0) for q in qm])
    Pk = dict(P, q2=q2k)
    F.fig2(P, HERE / f"{stem}_fig2.png", ttl, h_bars={"h_plan": float(z["h_plan"])}, t_end=0.3)
    F.fig_stick(Pk, HERE / f"{stem}_stick.png", f"{ttl} — Stick", t_end=tm)
    E.gif_of(Pk, HERE / f"{stem}.gif", f"CVT l_i={li:.2f}mm (task0, 15Nm)", qm=qm, l_i_mm=li)
    print(f"[{stem}] done", flush=True)


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for stem in ("t0nc_nlp", "t0nc_ol", "t0nc_cl", "t0nc_ppo_best", "t0nc_ppo"):
        if (HERE / f"{stem}.npz").exists() and (only is None or stem in only):
            do_nc(stem)
    for stem, full in (("t0wc_cl_li2508", True), ("t0wc_ol_li2508", True),
                       ("t0wc_cl_li20", False), ("t0wc_cl_li15", False)):
        if (HERE / f"{stem}.npz").exists() and (only is None or stem in only):
            do_wc(stem, full)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
