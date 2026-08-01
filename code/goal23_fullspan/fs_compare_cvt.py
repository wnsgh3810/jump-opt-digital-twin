# -*- coding: utf-8 -*-
"""fs_compare_cvt — CVT(0429) 전 trial 3자 비교: 실측 vs old α(5q 정본) vs 현행 fs.

CVT는 모델 경로가 달라 별도 (정본 CVT XML 캡처 + fs 6q 패치).
CL: fs_cvt_plot.cl5q(old) vs FR.rollout_cl_fs(fs, cvt 훅) — 점프(push) 구간
ModeA: fs_cvt.a_cvt_mirror(fs=False/True, R19 재생창)
출력: _compare/CVT_CL/<trial>.png · _compare/CVT_ModeA/<trial>.png
CLI: python fs_compare_cvt.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.002"),
             ("FS_KNEE_REL", "0.1"), ("FS_KNEE_LOAD", "1"), ("FS_TAULIM", "20.5")):
    os.environ.setdefault(k, v)
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import safe
import fs_data as FD
import fs_cvt as FC
import fs_cvt_plot as CVP
import fs_compare_plot as CP
import fs_runner as FR
import mujoco as mjm

OUT = HERE / "_compare"
LI = 0.02499
TKD = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}


def main():
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = float(nm["o1_429"]), float(nm["o2_429"]), float(nm["C_CVT"])
    P = tw["P"]
    from cvt_core import qpos_from_crank
    ft0 = FR.fs_twin()
    ft = dict(ft0)
    ft["model"] = model_cf
    ft["iq"] = {n: safe.qadr(model_cf, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model_cf, n, mjm) for n in ft["iq"]}
    ft["cvt_init"] = lambda q1, q2: qpos_from_crank(1.0, -q1 - np.pi / 2, -q2, LI)[0]
    qg, rg = FC.RU.rtab(LI)
    ft["cvt_diss"] = (cc, qg, rg)
    SP = FR._sess_params()
    sp = SP["26.04.29"]

    # ---- CL (점프 구간) ----
    for s, p, g, cvt, ho in FD.registry():
        if s != "26.04.29" or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)          # 원본 xlsx 창 = 점프 (훅 규약)
            tt = d["t"]
            mw = (tt >= pw[0]) & (tt <= pw[1])
            i0 = int(np.argmax(mw))
            t = tt[mw] - tt[i0]
            t_end = float(t[-1])
            init = (float(d["q1"][i0]), float(d["q2"][i0]), float(d["dq1"][i0]), float(d["dq2"][i0]),
                    float(d["raw1"][i0]), float(d["raw2"][i0]))
            Lf = FR.rollout_cl_fs(ft, t, CP.sh(d["qd1"][mw]), CP.sh(d["qd2"][mw]),
                                  CP.sh(d["dqd1"][mw]), CP.sh(d["dqd2"][mw]),
                                  tuple(g), t_end, two_stage=True, bias1=sp["bias1"],
                                  knee_deep=sp["knee_deep"], fade=True, taulim=None, init_meas=init)
            Lo = CVP.cl5q(model_c, tw, cc, d, seg, g, win=(mw, i0, init))
            if Lf is None or Lo is None:
                print(f"CL {p.name}: 실패"); continue
            m = np.ones(int(mw.sum()), bool)
            w = m
            dts = float(np.median(np.diff(Lo["t"])))
            sims = {
                "old": [np.interp(t, Lo["t"], Lo[k]) for k in ("q1", "q2", "dq1", "dq2")] +
                       [np.interp(t, Lo["t"], CVP.lpf(Lo["s1"], dts, 0.002)), np.interp(t, Lo["t"], Lo["s2"])],
                "fs": [np.interp(t, Lf["t"], Lf[k]) for k in ("thm1", "q2", "dq1", "dq2")] +
                      [np.clip(np.interp(t, Lf["t"], Lf["s1f"]), -20.5, 20.5), np.interp(t, Lf["t"], Lf["s2"])],
            }
            meas = {k: d[k][mw] for k, _ in CP.CH}
            fig, ax = CP.panels(f"26.04.29 (CVT l_i=25mm) / {p.name} — CL 점프 구간 (창 시작 실측 앵커 · 통짜) · 실측 vs old α vs 현행 fs",
                                f"push RMSE  old: {CP.rmse_line(meas, m, sims['old'])}   fs: {CP.rmse_line(meas, m, sims['fs'])}")
            for j, (a, (k, _)) in enumerate(zip(ax, CP.CH)):
                y, yo, yf = meas[k][w], sims["old"][j][w], sims["fs"][j][w]
                if k in ("q1", "q2"):
                    y, yo, yf = np.degrees(y), np.degrees(yo), np.degrees(yf)
                a.plot(tt[mw], y, lw=1.2, label="실측")
                a.plot(tt[mw], yo, "--", lw=1.0, label="old α (5q)")
                a.plot(tt[mw], yf, ":", lw=1.5, label="현행 fs (6q)")
            ax[0].legend(fontsize=8)
            fig.tight_layout()
            fp = OUT / "CVT_CL"; fp.mkdir(parents=True, exist_ok=True)
            fig.savefig(fp / f"{p.name}.png", dpi=105)
            plt.close(fig)
            print(f"CL {p.name}: OK", flush=True)
        except Exception as ex:
            print(f"CL {p.name}: ERR {type(ex).__name__} {ex}", flush=True)

    # ---- ModeA (R19 재생창) ----
    for sub, d in [(sub, dd) for ds, sub, dd, *r in FC.TW.R19.TRIALS if ds == "jump_0429"]:
        try:
            r5 = FC.a_cvt_mirror(model_c, d, tw, o1, o2, cc, fs=False, ret_traces=True)
            r6 = FC.a_cvt_mirror(model_cf, d, tw, o1, o2, cc, fs=True, bias1=sp["bias1"], ret_traces=True)
            if r5 is None or r6 is None:
                print(f"MA {sub}: 실패"); continue
            T5, T6 = r5[3], r6[3]
            t = d["t"]
            a1m = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
            a2m = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
            fig, ax = CP.panels(f"26.04.29 (CVT) / {sub} — ModeA 재생 (측정 토크 주입) · 실측 vs old α vs 현행 fs",
                                f"dq2 RMSE: old α {r5[0]:.2f} vs fs {r6[0]:.2f} | q1 RMSE: {r5[1]:.2f} vs {r6[1]:.2f}")
            series = [(np.degrees(d["q1"] + o1), np.degrees(T5["q1"]), np.degrees(T6["q1"])),
                      (np.degrees(d["q2"] + o2), np.degrees(T5["q2"]), np.degrees(T6["q2"])),
                      (d["dq1"], T5["dq1"], T6["dq1"]),
                      (d["dq2"], T5["dq2"], T6["dq2"]),
                      (a1m, None, None), (a2m, None, None)]
            for a, (k, lab), (ym, yo, yf) in zip(ax, CP.CH, series):
                a.plot(t, ym, lw=1.2, label="실측" + (" (주입 τ — 3자 공통)" if yo is None else ""))
                if yo is not None:
                    a.plot(T5["tl"], yo, "--", lw=1.0, label="old α (5q)")
                    a.plot(T6["tl"], yf, ":", lw=1.5, label="현행 fs (6q)")
            ax[0].legend(fontsize=8)
            fig.tight_layout()
            fp = OUT / "CVT_ModeA"; fp.mkdir(parents=True, exist_ok=True)
            fig.savefig(fp / f"{sub}.png", dpi=105)
            plt.close(fig)
            print(f"MA {sub}: OK", flush=True)
        except Exception as ex:
            print(f"MA {sub}: ERR {type(ex).__name__} {ex}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
