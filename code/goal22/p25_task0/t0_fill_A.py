# -*- coding: utf-8 -*-
"""배치 A — 결손 채우기 (신규 물리 없음):
  ① PPO_long canonical plan.gif + deploy_best.gif (누락 2)
  ② CVT 계획 our-standard 2×3 그래프 (plan-only, 크랭크좌표) → graphs/CVT/plan/
  ③ CVT 계획 canonical gif (전 l_i 변형) → sims/canonical/CVT/
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
import numpy as np
import mujoco

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import t0_mjc_render as R          # render/qpos_flip/qpos_cvt/build 재사용
import p25_d_deploy as D
import p25_d_ff as FF
import p23_v6_runners as RU
from t0_figs import _chan, _log_chan
from t0_ours import fig_std, rmse_vs

CVT = [("t0wc_cl_li2508", 0.02508, "CL l_i=25.08"),
       ("t0wc_cl_liopt", 0.02625, "CL l_i=26.25 (최적)"),
       ("t0wc_ol_li2508", 0.02508, "OL l_i=25.08"),
       ("t0wc_cl_li20", 0.02000, "CL l_i=20 (외삽)"),
       ("t0wc_cl_li15", 0.01500, "CL l_i=15 (외삽)")]


def fig_cvt_plan(stem, li_m, lab):
    """CVT 계획 단독 2×3 (배포 없음 — sim=plan 자기 자신, 계획 시각화)."""
    z = np.load(HERE / f"{stem}.npz")
    P = _chan(z)
    tlo = None
    # bz>1e-3 이후 grf<1 최초 → 대략 이지 (없으면 apex 근처)
    t = P["t"]
    on = P["grf"] > 1.0
    idx = np.where((t > 0.02) & ~on)[0]
    tlo = float(t[idx[0]]) if len(idx) else 0.15
    out = HERE / "graphs" / "CVT" / "plan" / f"{stem}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    ttl = (f"{stem} [{lab} · 계획, task0 15Nm] — h_plan {float(z['h_plan']):.3f} m "
           f"(q2=크랭크, 배포 하네스 flip전용이라 계획 단독)")
    # fig_std는 (P, Dc, ...) 요구 — plan을 양쪽에 넣어 자기일치(=계획 시각화)
    fig_std(P, P, out, ttl, tlo)
    print("graph:", out.name, flush=True)


def main():
    R.D.setup()
    only = sys.argv[1:] or None

    # ── ① PPO_long 시뮬 (flip, no_cvt) ──
    if only is None or "ppo_long" in only:
        mf = R.D.model_flip()
        xmlf = R.SCR / "twin_flip.xml"
        mujoco.mj_saveLastXML(str(xmlf), mf)
        outdir = HERE / "sims" / "canonical" / "PPO_long"
        outdir.mkdir(parents=True, exist_ok=True)
        R.OUT = outdir
        z = np.load(HERE / "t0nc_ppo_long.npz")
        hp = float(z["h_plan"])
        t, q1, q2, bz, grf = (np.asarray(z[k], float) for k in ("t", "q1", "q2", "bz", "grf"))
        R.render("plan", t, R.qpos_flip(bz, q1, q2), grf, xmlf,
                 "task0 PPO_long plan", hp, "h_plan(npz)", hp)
        r = FF.deploy_ff(HERE / "t0nc_ppo_long.npz", R.GAIN, return_log=True)
        L = r["log"]
        R.render("deploy_best", L["t"], R.qpos_flip(L["bz"], L["q1"], L["q2"]),
                 L["grf"], xmlf, f"task0 PPO_long FF+PD {R.GAIN}",
                 float(r["h_PD"]), "h_PD", float(r["h_plan"]))
        print("PPO_long sims done", flush=True)

    # ── ②③ CVT 계획 그래프 + 시뮬 ──
    outdir = HERE / "sims" / "canonical" / "CVT"
    outdir.mkdir(parents=True, exist_ok=True)
    for stem, li_m, lab in CVT:
        if not (HERE / f"{stem}.npz").exists():
            continue
        if only and stem not in only and "cvt" not in only:
            continue
        # ② 그래프
        fig_cvt_plan(stem, li_m, lab)
        # ③ canonical gif
        mc = RU.build_cvt23(R.D.G["X32"], R.D.G["REF"], R.D.G["SP"], li_m, R.D.G["D_DQ"])
        xmlc = R.SCR / f"twin_cvt_{stem}.xml"
        mujoco.mj_saveLastXML(str(xmlc), mc)
        R.OUT = outdir
        z = np.load(HERE / f"{stem}.npz")
        t, q1, qm, bz, grf = (np.asarray(z[k], float) for k in ("t", "q1", "qm", "bz", "grf"))
        tag = stem.replace("t0wc_", "").replace("cl_", "CL_").replace("ol_", "OL_")
        R.render(tag + "_plan", t, R.qpos_cvt(bz, q1, qm, li_m), grf, xmlc,
                 f"task0 CVT {lab} plan", float(z["h_plan"]), "h_plan(npz)", float(z["h_plan"]))
        print("cvt gif:", tag, flush=True)
    print("FILL-A DONE", flush=True)


if __name__ == "__main__":
    main()
