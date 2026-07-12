# -*- coding: utf-8 -*-
"""P19 전 데이터 결과 생성 — 현행 승격 스택으로 모든 세션 그래프+GIF+npz.

출력: Desktop/jump_opt/g22_p19_all_results/<세션>/{png,gif,traj}/
  - 점프 5세션 (0324 held-out / 0421 / 0424 / 0602 / 0429 CVT) × 트라이얼별
    Mode A(τ replay) + CL(커맨드층 α·클립·tm 반영) 각각 PNG + GIF + npz
  - s2s_gnd_0319: 사이클 리셋 Mode A replay (P19는 점프 전용 fit — 참고용)
프로토콜 출처: CL=p19_run.cl_run(eval_stack 인자), A=cvt_run2.sim_run mode-A(블렌딩 0).
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_adapter as AD
import render_kit as RK

AD.ensure_init()
import p19_judge as P
import p19_run as R
import mujoco
from PIL import Image, ImageDraw
from cvt_core import closure, qpos_from_crank

sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA
from cvt_anim import build_anim_model

CAND = AD.load_candidate(HERE / "fourbar_p19_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)
TM, PRE30 = float(V[15]), float(V[2])
A = P.A_PAPER
CLIP = R.CLIP
ROOT = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p19_all_results")
DSDIR = {"jump_0324": "jump_0324_heldout", "jump_position_0421": "jump_position_0421",
         "jump_0424": "jump_0424", "jump_0602": "jump_0602",
         "jump_0429": "jump_0429_cvt"}
# Mode A 0429 q-오프셋 (p19_cma2.modeA_429 프로토콜 = P18b 값)
QOFF_A429 = (3.14 * np.pi / 180, -3.0 * np.pi / 180)


def run_any(model, is_cvt, l_i, d, mode, gains, dqon, ffk, alphas, preload, o1, o2):
    """CL(커맨드층) / A(τ replay) 공용 러너 — cl_run+sim_run 합본, GRF 로깅 추가."""
    mj = P.J._P["mj"]; S = P.J._P["S"]
    t = d["t"]
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    q1_0 = (qd1[0] if mode == "CL" else d["q1"][0] + o1)
    q2_0 = (qd2[0] if mode == "CL" else d["q2"][0] + o2)
    dqd1 = d["dqd1"] if dqon else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqon else np.zeros_like(t)
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    tau1_in = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tau2_in = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    if is_cvt:
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "grf"]}
    c1f = c2f = 0.0
    al = dt / max(TM, dt)
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
            c1f, c2f = c1, c2
        elif mode == "A":
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, tau1_in))
            s2 = float(np.interp(tm_, t, tau2_in))
            if tc > t[-1]:
                s1 = s2 = 0.0
        else:
            tm_ = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm_, t, qd1) - q1c) + kd1 * (np.interp(tm_, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm_, t, qd2) - q2c) + kd2 * (np.interp(tm_, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm_, t, d["tdes2"])
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1 = float(np.clip(c1f, -CLIP, CLIP)); c2 = float(np.clip(c2f, -CLIP, CLIP))
            s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -(s2 + preload)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
        gz = 0.0
        for ci in range(md.ncon):
            cf = np.zeros(6)
            mj.mj_contactForce(model, md, ci, cf)
            gz += (md.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
        L["grf"][k] = gz
    L["t"] = tl
    return L


def h_real_of(ds, sub):
    for tr in P.J._P["P12"]._G["trials"]:
        if tr["ds"] == ds and str(tr.get("sub", "")) == str(sub):
            hr = tr.get("h_real", float("nan"))
            return float(hr) if hr == hr else float("nan")
    return float("nan")


def sr_plot(ax, ts, ys, tr_, yr, lab_s, lab_r):
    ln, = ax.plot(ts, ys, lw=1.4, label=lab_s)
    ax.plot(tr_, yr, lw=1.0, ls="--", alpha=0.75, color=ln.get_color(), label=lab_r)
    ax.grid(alpha=0.3); ax.legend(fontsize=7)


def make_fig(ds, sub, d, L, mode, l_i, o1, o2, hr, out, cl_note=" · 실효게인 α+클립 반영"):
    """표준 그림 생성 — 지표=cvt_run2.metrics2(기준), 그림=render_kit.fig_trial_std(png_v2 규격)."""
    import cvt_run2 as CR
    d2 = dict(d)
    d2.setdefault("h_real", hr)
    if not np.isfinite(d2.get("h_real", float("nan"))):
        d2["h_real"] = float(hr)
    A_save = CR.A.copy(); CR.A = np.asarray(A, float)   # 주입 후 복원 (repo 규약)
    try:
        m = CR.metrics2(d2, L, o1, o2)
    finally:
        CR.A = A_save
    t = d["t"]
    tp1 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    RK.fig_trial_std(out, f"{ds}/{sub}", d2, L, m, mode, l_i, tp1, tp2,
                     o1q=o1, o2q=o2, model_tag="P19", cl_note=cl_note)


ANIM = {}


def render_gif(L, l_i, label, hr, out, t_end):
    li_r = round(float(l_i), 4)
    if li_r not in ANIM:
        ANIM[li_r] = build_anim_model(li_r)
    am = ANIM[li_r]
    mk = (L["t"] >= -0.05) & (L["t"] <= t_end + 0.35)
    tt = L["t"][mk]; q1 = L["q1"][mk]; qc = L["q2"][mk]; bz = L["bz"][mk]
    wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
    mj1 = wrap(-q1 - np.pi / 2); mjc = wrap(-qc)
    h_sim = float(bz[tt > 0].max()) if (tt > 0).any() else float("nan")
    dur = float(tt[-1] - tt[0])
    n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(tt) - 1, n).astype(int)
    data = mujoco.MjData(am)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])
    frames = []
    qk_prev = None
    with mujoco.Renderer(am, width=640, height=480) as ren:
        for i in idxs:
            qk, qp, _ = closure(float(mjc[i]), li_r, qk_prev)
            qk_prev = qk
            data.qpos[:] = [float(bz[i]), float(mj1[i]), float(mjc[i]), qp, qk]
            data.qvel[:] = 0.0
            mujoco.mj_forward(am, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            RK.draw_overlay(dr, MA, label, tt[i] * 1000, bz_cm=bz[i] * 100,
                            hip_deg=float(np.degrees(q1[i])),
                            knee_deg=float(np.degrees(qc[i])),
                            h_sim=h_sim, h_real=hr, l_i_mm=li_r * 1000)
            frames.append(img)
    frames[0].save(str(out), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)


def save_npz(out, L, **meta):
    np.savez(out, **{k: v for k, v in L.items()},
             **{k: v for k, v in meta.items()})


def do_jumps():
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f, _ = P.build_flip(X32, V[1], SP)
    model_c = None
    dd = dict(zip(P.J._P["FR"].NAMES, X32[:26]))
    results = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        sd = ROOT / DSDIR[ds]
        for c in ("png", "gif", "traj"):
            (sd / c).mkdir(parents=True, exist_ok=True)
        alphas = R.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(X32, V[1], SP, l_i)
            model = model_c
            o_cl = QOFF; o_a = QOFF_A429
            preload = 0.0
            hr = float(d.get("h_real", float("nan")))
        else:
            model = model_f
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o = (dd.get(k1, 0.0) if k1 else 0.0, dd.get(k2, 0.0) if k2 else 0.0)
            o_cl = o_a = o
            preload = PRE30
            hr = h_real_of(ds, sub)
        for mode, (o1, o2) in (("CL", o_cl), ("A", o_a)):
            aph = alphas if mode == "CL" else [1, 1, 1, 1]
            L = run_any(model, is_cvt, l_i, d, mode, gains, dqon, ffk, aph, preload, o1, o2)
            if L is None:
                print(f"CRASH {ds}/{sub} [{mode}]", flush=True)
                results.append((ds, sub, mode, "CRASH"))
                continue
            make_fig(ds, sub, d, L, mode, l_i, o1, o2, hr,
                     sd / "png" / f"{sub}__{mode}.png")
            save_npz(sd / "traj" / f"{sub}__{mode}.npz", L,
                     l_i=l_i, ds=ds, sub=sub, mode=mode, h_real=hr)
            results.append((ds, sub, mode, "OK"))
            print(f"png {ds}/{sub} [{mode}]", flush=True)
    return results


def do_s2s():
    """s2s_gnd_0319 — 사이클 시작마다 실측 상태로 리셋하는 Mode A replay (참고용)."""
    sd = ROOT / "s2s_gnd_0319"
    for c in ("png", "gif", "traj"):
        (sd / c).mkdir(parents=True, exist_ok=True)
    mj = P.J._P["mj"]
    model, _ = P.build_flip(X32, V[1], SP)
    P12 = P.J._P["P12"]
    dd = dict(zip(P.J._P["FR"].NAMES, X32[:26]))
    k1, k2 = P12.OFFKEY.get("s2s_gnd_0319", (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0
    o2 = dd.get(k2, 0.0) if k2 else 0.0
    dt = model.opt.timestep
    for tr in P12._G["trials"]:
        if tr["ds"] != "s2s_gnd_0319":
            continue
        sub = str(tr["sub"])
        # 심판(eval_windows) 프로토콜 그대로: pp는 MJ 관절좌표, sv()가 오프셋 적용,
        # tau_h/tau_k는 부호 반전본을 ctrl에 직결 (p14_judge.eval_modeA 패턴)
        t = tr["pp"]["t"]
        th = -P.J.ahat(A, tr["raw1"], tr["v1"])
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + PRE30)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        pp = P12._G["sv"](ppv, o1, o2)
        rs_i = sorted({0} | {int(i) for i in pp["starts"]})
        rs_t = [float(t[i]) for i in rs_i]
        md = mj.MjData(model)
        N = int(t[-1] / dt)
        tl = np.arange(N) * dt
        L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2",
                                      "bz", "grf"]}
        ridx = 0
        for k in range(N):
            tc = tl[k]
            if ridx < len(rs_i) and tc >= rs_t[ridx]:
                i0 = rs_i[ridx]; ridx += 1
                q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
                md.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
                md.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
                mj.mj_forward(model, md)
            c1 = float(np.interp(tc, t, pp["tau_h"]))
            c2 = float(np.interp(tc, t, pp["tau_k"]))
            md.ctrl[:] = [c1, c2]
            try:
                mj.mj_step(model, md)
            except Exception:
                break
            if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
                break
            L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
            L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
            L["sh1"][k] = -c1; L["sh2"][k] = -c2     # 측정좌표 축토크 (ctrl 부호 반전)
            L["bz"][k] = md.qpos[0]
            gz = 0.0
            for ci in range(md.ncon):
                cf = np.zeros(6)
                mj.mj_contactForce(model, md, ci, cf)
                gz += (md.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
            L["grf"][k] = gz
        L["t"] = tl
        # 의사-d (측정좌표 변환) — 표준 그림/지표 입력용
        d_ps = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                    dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                    traw1=tr["raw1"], traw2=tr["raw2"],
                    grf_real=None, h_real=float("nan"))
        make_fig("s2s_gnd_0319 (mshoot 창 리셋 replay)", sub, d_ps, L, "A",
                 0.030, 0.0, 0.0, float("nan"), sd / "png" / f"{sub}__A.png")
        save_npz(sd / "traj" / f"{sub}__A.npz", L, l_i=0.030, ds="s2s_gnd_0319",
                 sub=sub, mode="A", h_real=float("nan"))
        print(f"png s2s/{sub} [A]", flush=True)


def regen_pngs():
    """기존 traj npz에서 그림만 표준 규격으로 재생성 (재시뮬 없음, s2s_0319 제외)."""
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    dd = dict(zip(P.J._P["FR"].NAMES, X32[:26]))
    tri = {(ds, str(sub)): (d, is_cvt) for ds, sub, d, g_, dq_, ff_, m_, is_cvt, li_
           in R.TRIALS}
    import s2s_0604 as S0
    for ds_dir in sorted(ROOT.iterdir()):
        tj = ds_dir / "traj"
        if not tj.is_dir() or ds_dir.name == "s2s_gnd_0319":
            continue
        for f in sorted(tj.glob("*.npz")):
            z = np.load(f, allow_pickle=True)
            L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                                   "bz", "grf")}
            ds = str(z["ds"]); sub = str(z["sub"]); mode = str(z["mode"])
            l_i = float(z["l_i"]); hr = float(z["h_real"])
            out = ds_dir / "png" / (f.stem + ".png")
            if ds.startswith("s2s_0604"):
                grp = ds.replace("s2s_0604_", "")
                d = S0.load_0604(grp, sub)
                make_fig(f"s2s_0604/{grp}", sub, d, L, mode, l_i, 0.0, 0.0, hr,
                         out, cl_note=" · 회귀 실효게인 (P18c)")
            else:
                d, is_cvt = tri[(ds, sub)]
                if is_cvt:
                    o1, o2 = QOFF if mode == "CL" else QOFF_A429
                else:
                    k1, k2 = P.J.OFFK.get(ds, (None, None))
                    o1 = dd.get(k1, 0.0) if k1 else 0.0
                    o2 = dd.get(k2, 0.0) if k2 else 0.0
                make_fig(ds, sub, d, L, mode, l_i, o1, o2, hr, out)
            print("png", f.stem, flush=True)


def do_gifs():
    for sd in sorted(ROOT.iterdir()):
        if not (sd / "traj").is_dir():
            continue
        for f in sorted((sd / "traj").glob("*.npz")):
            out = sd / "gif" / (f.stem + ".gif")
            if out.exists():
                continue
            z = np.load(f, allow_pickle=True)
            L = {k: z[k] for k in ("t", "q1", "q2", "bz")}
            ds = str(z["ds"]); sub = str(z["sub"]); mode = str(z["mode"])
            t_end = float(z["t"][-1]) - 0.35 if ds.startswith("s2s") else None
            if t_end is None:
                mask = z["t"] >= 0
                t_end = float(z["t"][mask][-1]) - P.J.T_AFTER
            try:
                render_gif(L, float(z["l_i"]), f"P19 {ds}/{sub} [{mode}]",
                           float(z["h_real"]), out, t_end)
                print(f"gif {ds}/{sub} [{mode}]", flush=True)
            except Exception as e:
                print(f"GIF FAIL {ds}/{sub} [{mode}]: {e}", flush=True)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    print(f"P19 stack: sp={SP} tm={TM*1000:.2f}ms pre30={PRE30:.2f} "
          f"qoff429={QOFF} clip={CLIP}", flush=True)
    res = do_jumps()
    do_s2s()
    crashes = [r for r in res if r[3] != "OK"]
    print(f"SIM DONE — {len(res)} runs, crash {len(crashes)}: {crashes}", flush=True)
    do_gifs()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
