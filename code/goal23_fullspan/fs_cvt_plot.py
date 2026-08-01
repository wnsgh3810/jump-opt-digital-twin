# -*- coding: utf-8 -*-
"""fs_cvt_plot — 0429: 실측 vs old α(5q 정본) vs 현행 fs(6q) 겹침 그래프.

ModeA(측정 raw 주입, R19 재생창): q1·q2(크랭크)·dq1·dq2 + τ 주입(공통) 패널.
CL(폴더 게인 PD, *2 fullspan i_desc~t_lo): q1·q2·dq1·dq2·τ1(lpf 관측)·τ2.
old α CL = 5q 직결 hip 미러 (TK·kd0.2 동일 컨벤션, 벨트 α 집약 표현 공유).
출력: _plots/*.png. CLI: python fs_cvt_plot.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.010"),
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
import fs_cvt as FC
import fs_runner as FR
import fs_data as FD
import mujoco as mjm

TW = FC.TW; RU = FC.RU
OUT = HERE / "_plots"
OUT.mkdir(exist_ok=True)
LI = 0.02508
TKD = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}


def lpf(x, dt, tc=0.010):
    a = dt / (tc + dt)
    y = np.zeros_like(x); acc = float(x[0])
    for i in range(len(x)):
        acc += a * (float(x[i]) - acc); y[i] = acc
    return y


def tri(ax, t0, y0, t1, y1, t2, y2, ylab):
    ln, = ax.plot(t0, y0, lw=1.0, label="실측")
    ax.plot(t1, y1, "--", lw=1.0, label="old α (5q)")
    ax.plot(t2, y2, ":", lw=1.4, label="fs (6q)")
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.3)


def cl5q(model, tw, cc, d, seg, g, win=None):
    """old α CL 미러 (5q 직결 hip): settle→폴더 게인 PD(TK·kd0.2)→supp/spr/CVT소산."""
    P = tw["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    from cvt_core import qpos_from_crank
    if win is not None:                       # P16: 점프 창 시작 실측 앵커 (ModeA 동일 규칙)
        mw, i0, init = win
        t = d["t"][mw] - d["t"][i0]
        qd1g, qd2g = d["qd1"][mw], d["qd2"][mw]
        dqd1g, dqd2g = d["dqd1"][mw], d["dqd2"][mw]
        t_end = float(t[-1])
    else:
        mw = None
        i0 = max(0, seg["i_desc"] - 5)
        t = d["t"][i0:] - d["t"][i0]
        qd1g, qd2g = d["qd1"][i0:], d["qd2"][i0:]
        dqd1g, dqd2g = d["dqd1"][i0:], d["dqd2"][i0:]
        t_end = seg["t_lo"] - d["t"][i0]
    kp1, kd1 = g[0], g[1]
    kp2 = g[2] * TKD.get(g[2], 0.656); kd2 = g[3] * 0.20
    md = mjm.MjData(model)
    _a1 = -(init[0] if win is not None else float(qd1g[0])) - np.pi / 2
    _a2 = -(init[1] if win is not None else float(qd2g[0]))
    md.qpos[:] = qpos_from_crank(1.0, _a1, _a2, LI)[0]
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    if win is not None:                       # 실측 속도 주입 (5q 좌표: [bz, hip, crank, cpin, knee])
        _c1, _c12 = np.cos(init[0]), np.cos(init[0] + init[1])
        md.qvel[:] = [-0.25 * (_c1 * init[2] + _c12 * (init[2] + init[3])), -init[2], -init[3], init[3], -init[3]]
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    qg, rg = RU.rtab(LI)
    for k in range(0 if win is not None else int(round(P.J.T_SETTLE / dt))):        # settle (앵커판은 생략)
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        c1 = S.SETTLE_KP * (float(qd1g[0]) - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (float(qd2g[0]) - q2c) - S.SETTLE_KD * v2c
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[4]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[4] = tql
        mjm.mj_step(model, md)
    N = int(round((t_end + 0.05) / dt))
    L = {k: np.zeros(N) for k in ("t", "q1", "q2", "dq1", "dq2", "s1", "s2")}
    for k in range(N):
        tc = k * dt
        tm_ = min(tc, t_end)
        qd1 = float(np.interp(tm_, t, qd1g)); qd2 = float(np.interp(tm_, t, qd2g))
        dqd1 = float(np.interp(tm_, t, dqd1g)); dqd2 = float(np.interp(tm_, t, dqd2g))
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc <= t_end:
            c1 = kp1 * (qd1 - q1c) + kd1 * (dqd1 - v1c)
            c2 = kp2 * (qd2 - q2c) + kd2 * (dqd2 - v2c)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[4]), abs(s2), sprm) if sprm is not None else 0.0
        rr = float(np.interp(float(md.qpos[2]), qg, rg))
        amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
        tql += -cc * abs(s2) * amp * float(np.tanh(float(md.qvel[4]) / 1.0))
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[4] = tql
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        L["t"][k] = tc
        L["q1"][k] = -md.qpos[1] - np.pi / 2
        L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]
        L["dq2"][k] = -md.qvel[2]
        L["s1"][k] = s1
        L["s2"][k] = s2
    return L


def main():
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = float(nm["o1_429"]), float(nm["o2_429"]), float(nm["C_CVT"])
    P = tw["P"]

    # ---- ModeA (R19 재생창) ----
    subs = [(sub, d) for ds, sub, d, *rest in TW.R19.TRIALS if ds == "jump_0429"]
    print(f"R19 0429 subs: {[s for s, _ in subs]}", flush=True)
    _want = ("150_2.2_250_3", "60_0.75_60_2")
    for sub, d in [x for x in subs if x[0] in _want]:
        r5 = FC.a_cvt_mirror(model_c, d, tw, o1, o2, cc, fs=False, ret_traces=True)
        r6 = FC.a_cvt_mirror(model_cf, d, tw, o1, o2, cc, fs=True, bias1=0.85, ret_traces=True)
        if r5 is None or r6 is None:
            print(f"{sub}: ModeA 실패", flush=True)
            continue
        T5, T6 = r5[3], r6[3]
        t = d["t"]
        a1m = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
        a2m = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
        fig, ax = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
        tri(ax[0, 0], t, np.degrees(d["q1"]) + np.degrees(o1), T5["tl"], np.degrees(T5["q1"]), T6["tl"], np.degrees(T6["q1"]), "q1 [°]")
        tri(ax[0, 1], t, np.degrees(d["q2"]) + np.degrees(o2), T5["tl"], np.degrees(T5["q2"]), T6["tl"], np.degrees(T6["q2"]), "q2 크랭크 [°]")
        tri(ax[1, 0], t, d["dq1"], T5["tl"], T5["dq1"], T6["tl"], T6["dq1"], "dq1 [rad/s]")
        tri(ax[1, 1], t, d["dq2"], T5["tl"], T5["dq2"], T6["tl"], T6["dq2"], "dq2 크랭크 [rad/s]")
        ax[0, 2].plot(t, a1m, lw=1.0)
        ax[0, 2].set_ylabel("τ1 주입 (공통) [Nm]"); ax[0, 2].grid(alpha=0.3)
        ax[1, 2].plot(t, a2m, lw=1.0)
        ax[1, 2].set_ylabel("τ2 주입 (공통) [Nm]"); ax[1, 2].grid(alpha=0.3)
        ax[0, 0].legend(fontsize=8)
        for a in ax[1]:
            a.set_xlabel("t [s]")
        fig.suptitle(f"0429 CVT ModeA (측정 raw 주입, R19 재생창) — {sub} | dq2 RMSE: old α {r5[0]:.2f} vs fs {r6[0]:.2f}")
        fig.tight_layout()
        fp = OUT / f"cvt0429_modeA_{sub}.png"
        fig.savefig(fp, dpi=110)
        plt.close(fig)
        print(f"saved {fp.name}", flush=True)

    # ---- CL (*2 fullspan) ----
    ft0 = FR.fs_twin()
    from cvt_core import qpos_from_crank
    ft = dict(ft0)
    ft["model"] = model_cf
    ft["iq"] = {n: safe.qadr(model_cf, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model_cf, n, mjm) for n in ft["iq"]}
    ft["cvt_init"] = lambda q1, q2: qpos_from_crank(1.0, -q1 - np.pi / 2, -q2, LI)[0]
    qg, rg = RU.rtab(LI)
    ft["cvt_diss"] = (cc, qg, rg)
    SP = FR._sess_params()
    sp = SP["26.04.29"]
    for s, p, g, cvt, ho in FD.registry():
        if s != "26.04.29" or p.name not in ("150_2.2_250_3", "60_0.75_60_2"):
            continue
        d = FD.load2(p); seg = FD.segment(d)
        gm = (g[0], g[1], g[2] * TKD.get(g[2], 0.656), g[3] * 0.20)
        i0 = max(0, seg["i_desc"] - 5)
        t = d["t"][i0:] - d["t"][i0]
        t_end = seg["t_lo"] - d["t"][i0]
        Lf = FR.rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                              fade=True, taulim=None)
        Lo = cl5q(model_c, tw, cc, d, seg, g)
        if Lf is None or Lo is None:
            print(f"{p.name}: CL 실패 (fs {Lf is None} old {Lo is None})", flush=True)
            continue
        dt5 = float(np.median(np.diff(Lo["t"])))
        pm = seg["push"][i0:][: len(t)]
        t_push0 = float(t[pm][0]) if pm.sum() else 0.0
        w0, w1 = t_push0 - 0.05, t_end                  # 점프(push) 구간만 — 이륙에서 절단 (이후 sim은 커맨드 0 관례라 비교 무의미)
        mseg = (t >= w0) & (t <= w1)
        tm = t[mseg]
        mo = (Lo["t"] >= w0) & (Lo["t"] <= w1)
        mf = (Lf["t"] >= w0) & (Lf["t"] <= w1)
        s1o_l = lpf(Lo["s1"], dt5)
        fig, ax = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
        tri(ax[0, 0], tm, np.degrees(d["q1"][i0:][mseg]), Lo["t"][mo], np.degrees(Lo["q1"][mo]), Lf["t"][mf], np.degrees(Lf["thm1"][mf]), "q1 [°]")
        tri(ax[0, 1], tm, np.degrees(d["q2"][i0:][mseg]), Lo["t"][mo], np.degrees(Lo["q2"][mo]), Lf["t"][mf], np.degrees(Lf["q2"][mf]), "q2 크랭크 [°]")
        tri(ax[1, 0], tm, d["dq1"][i0:][mseg], Lo["t"][mo], Lo["dq1"][mo], Lf["t"][mf], Lf["dq1"][mf], "dq1 [rad/s]")
        tri(ax[1, 1], tm, d["dq2"][i0:][mseg], Lo["t"][mo], Lo["dq2"][mo], Lf["t"][mf], Lf["dq2"][mf], "dq2 크랭크 [rad/s]")
        tri(ax[0, 2], tm, d["a1"][i0:][mseg], Lo["t"][mo], s1o_l[mo], Lf["t"][mf], Lf["s1f"][mf], "τ1 (lpf 관측) [Nm]")
        tri(ax[1, 2], tm, d["a2"][i0:][mseg], Lo["t"][mo], Lo["s2"][mo], Lf["t"][mf], Lf["s2"][mf], "τ2 [Nm]")
        ax[0, 0].legend(fontsize=8)
        for a in ax[1]:
            a.set_xlabel("t [s]")
        for a in ax.flat:
            a.axvline(t_push0, lw=0.6, alpha=0.4)
            a.axvline(t_end, lw=0.6, alpha=0.4)
        fig.suptitle(f"0429 CVT CL 점프(push) 구간 (세로선=push 시작/이륙) — {p.name}")
        fig.tight_layout()
        fp = OUT / f"cvt0429_CL_{p.name}.png"
        fig.savefig(fp, dpi=110)
        plt.close(fig)
        print(f"saved {fp.name}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
