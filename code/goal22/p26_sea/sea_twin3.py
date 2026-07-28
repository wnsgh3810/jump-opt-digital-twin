# -*- coding: utf-8 -*-
"""sea_twin3 — 마찰성 직렬탄성 (2단 스프링 + Dahl 마찰 고리) = H16 물리의 구현.

구조: 모터상태 SEA-lite(sea_twin2)에 hip 스프링을 '2단 탄성 + Dahl 마찰 상태'로 교체.
  τ_spr = spr2seg(δ) + F + b_s·(dθ_m − dq)
  dF/dt = σ_f·dδ/dt·(1 − (F/τ_C)·sgn(dδ/dt))     (F는 ±τ_C로 포화 — 고리 생성)
검증: ①정적 고리 재현 (H16 가지: 로딩 k178/언로딩 k266, 간격 0.4~1.3°) ②CL 전이 22 trial.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402

def rollout_cl_sea3(tw, tg, qd1g, qd2g, dqd1g, dqd2g, gains,
                    ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01,
                    tauC=1.5, sigf=800.0,
                    ks2=650.0, bs2=1.5, jm2=0.01,
                    t_end=None, t_after=None, record=False):
    """sea_twin2.rollout_cl_sea2 미러 + hip Dahl 마찰 상태 F1."""
    P = tw["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]
    tm = tw["tm"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    R19 = TW.R19; RU = TW.RU
    if t_end is None: t_end = float(tg[-1])
    if t_after is None: t_after = P.J.T_AFTER
    kp1, kd1, kp2, kd2 = gains
    d0_1 = tau0_1 / ks1
    def spr2(d):
        if abs(d) <= d0_1: return ks1 * d
        return np.sign(d) * (tau0_1 + ks1_hi * (abs(d) - d0_1))
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -qd1g[0] - np.pi/2, -qd2g[0]
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t_end + t_after) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    keys = ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "thm1", "thm2", "tsp1", "tsp2", "F1"]
    if record: keys += ["raw1", "raw2", "grf"]
    Lg = {k: np.zeros(N) for k in keys}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    th1 = -md.qpos[1] - np.pi/2; dth1 = 0.0
    th2 = -md.qpos[2]; dth2 = 0.0
    F1 = 0.0                                     # Dahl 마찰 상태
    dprev = 0.0
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi/2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        enc1, denc1 = th1, dth1
        enc2, denc2 = (th2, dth2) if ks2 else (q2c, v2c)
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1g[0] - enc1) - S.SETTLE_KD * denc1
            c2 = S.SETTLE_KP * (qd2g[0] - enc2) - S.SETTLE_KD * denc2
            c1f, c2f = c1, c2
        else:
            tm_ = min(tc, t_end)
            c1 = kp1 * (np.interp(tm_, tg, qd1g) - enc1) + kd1 * (np.interp(tm_, tg, dqd1g) - denc1)
            c2 = kp2 * (np.interp(tm_, tg, qd2g) - enc2) + kd2 * (np.interp(tm_, tg, dqd2g) - denc2)
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP)); c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([dth1]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([dth2 if ks2 else v2c]))[0])
        # ── hip: 2단 탄성 + Dahl 마찰 ──
        d1 = th1 - q1c
        dd = d1 - dprev                          # 이번 스텝 상대변위 증분
        if tauC > 0:
            F1 += sigf * dd * (1.0 - (F1/tauC) * np.sign(dd if dd != 0 else 1.0))
            F1 = float(np.clip(F1, -tauC*1.2, tauC*1.2))
        dprev = d1
        tsp1 = spr2(d1) + F1 + bs1*(dth1 - v1c)
        ddth1 = (s1 - tsp1)/jm1
        dth1 += ddth1*dt; th1 += dth1*dt
        # ── knee (선형 SEA) ──
        if ks2:
            tsp2 = ks2*(th2 - q2c) + bs2*(dth2 - v2c)
            ddth2 = (s2 - tsp2)/jm2
            dth2 += ddth2*dt; th2 += dth2*dt
        else:
            tsp2 = s2
        supp = RU.supp_scalar(tsp2, v2c, law_a, law_b, law_v0)
        if kr: supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = 0.0
        if sprm is not None: tql += RU.spr_tau(float(md.qpos[iq_k]), abs(tsp2), sprm)
        md.ctrl[:] = [-(tsp1 + RU.hip_supp_scalar(tsp1, tsp2, v1c)), -(tsp2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all() or abs(th1) > 20:
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi/2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
        Lg["thm1"][k] = th1; Lg["thm2"][k] = th2 if ks2 else q2c
        Lg["tsp1"][k] = tsp1; Lg["tsp2"][k] = tsp2; Lg["F1"][k] = F1
        if record:
            Lg["raw1"][k] = c1; Lg["raw2"][k] = c2
            Lg["grf"][k] = RU._grf_z(model, md)
    Lg["t"] = tl
    return Lg


if __name__ == "__main__":
    tw = TW.twin()
    ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
    SESS = {"exp1": ("26.07.22", "t0nc_cl_pd15.npz"), "exp2": ("26.07.23", "t0nc_cl_v4.npz"),
            "exp3": ("26.07.24", "t0nc_cl_v7.npz"), "exp4": ("26.07.25", "t0nc_cl_v8.npz"),
            "exp5": ("26.07.27", "t0nc_cl_v9.npz")}
    def slo(t, g, thr=1.0, win=0.05):
        dt = float(t[1]-t[0]); w = int(round(win/dt)); on = g > thr
        for i in range(len(g)-w):
            if t[i] > 0.02 and not on[i:i+w].any(): return float(t[i])
        return float(t[-1])
    GRID = {"2단 (τC=0, 기준)": dict(tauC=0.0),
            "3형 τC=0.8": dict(tauC=0.8), "3형 τC=1.5": dict(tauC=1.5), "3형 τC=2.5": dict(tauC=2.5)}
    AGG = {k: [] for k in GRID}
    for sess, (day, bait) in SESS.items():
        z = np.load(P25/bait); m = z["t"] >= 0
        tg = np.asarray(z["t"][m], float)
        qd1, qd2, dqd1, dqd2 = z["qd1"][m], z["qd2"][m], z["dqd1"][m], z["dqd2"][m]
        T_END = slo(z["t"], z["grf"]) if "grf" in z else 0.216
        for fold in sorted([p for p in (ROOT/day).iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
            gg = [float(x) for x in fold.name.split("_")]
            if len(gg) != 4: continue
            try:
                hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
            except FileNotFoundError:
                continue
            n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
            t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
            qd2m = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2m-qd2m[0]) > np.radians(0.5))[0]
            t0 = t[on[0]] if len(on) else 0.0
            g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
            ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)] - t0)
            tmv = t - t0; msk = (tmv >= 0.005) & (tmv <= t_lo)
            if msk.sum() < 20: continue
            q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
            a1m = ahat_np(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float))
            a2m = ahat_np(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float))
            for mn, kw in GRID.items():
                L = rollout_cl_sea3(tw, tg, qd1, qd2, dqd1, dqd2, tuple(gg), t_end=T_END, t_after=0.3, **kw)
                if L is None: continue
                q1s = np.interp(tmv[msk], L["t"], L["thm1"]); q2s = np.interp(tmv[msk], L["t"], L["thm2"])
                s1s = np.interp(tmv[msk], L["t"], L["tsp1"]); s2s_ = np.interp(tmv[msk], L["t"], L["tsp2"])
                AGG[mn].append((np.degrees(np.sqrt(np.mean((q1m[msk]-q1s)**2))),
                                np.degrees(np.sqrt(np.mean((q2m[msk]-q2s)**2))),
                                np.sqrt(np.mean((a1m[msk]-s1s)**2)),
                                np.sqrt(np.mean((a2m[msk]-s2s_)**2))))
    print("=== 3형(2단+Dahl) CL 전이 22 trial ===")
    for mn, v in AGG.items():
        a = np.array(v)
        print(f"{mn}: q1 {a[:,0].mean():5.2f}° q2 {a[:,1].mean():5.2f}° τ1 {a[:,2].mean():5.2f} τ2 {a[:,3].mean():5.2f} (n={len(v)})")
    json.dump({mn: np.array(v).mean(axis=0).tolist() for mn, v in AGG.items() if v},
              open(HERE/"_sea3_grid.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
