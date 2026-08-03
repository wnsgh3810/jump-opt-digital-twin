# -*- coding: utf-8 -*-
"""sea_twin2 — H6 v2: 모터상태 SEA-lite CL 롤아웃.

물리: 모터(감속기 출력축) 각 θ_m을 컨트롤러측 상태로 명시 적분 (MuJoCo DOF 추가 없음
→ goal19 질량행렬 병조건 회피). 인코더 = θ_m (관측식 교정 내장).
  PD:      c = kp(qd − θ_m) + kd(dqd − dθ_m)  → clip → s = ahat(c, dθ_m)
  모터:    J_m·ddθ_m = s − τ_spr,  τ_spr = k_s(θ_m − q_link) + b_s(dθ_m − dq_link)
  링크:    ctrl = −(τ_spr + 지지법칙)   (스프링이 전달하는 토크만 사지에 감)
준정적 극한에서 τ_spr → s (기존과 동일), 위치 실효게인 = kp·k_s/(kp+k_s) 자연 창발.
검증: ①수렴 골든 (k_s=1e5, b_s=50 → 정본 α=1 롤아웃과 근접) ②H6: exp5 7게인 예측 대결.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402

KT, GR, CF = 0.091, 9.0, 0.59
A_P = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat_np(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A_P[0]*GR*KT*Iq - A_P[1]*GR*np.abs(Iq)*Iq - A_P[2]*s - A_P[3]*np.abs(Iq)*s

def rollout_cl_sea2(tw, tg, qd1g, qd2g, dqd1g, dqd2g, gains,
                    ks1=169.0, bs1=1.0, jm1=0.03,
                    ks2=None, bs2=1.0, jm2=0.03,
                    ks1_hi=None, tau0_1=9.0,
                    t_end=None, t_after=None, record=False):
    """모터상태 SEA-lite. ks2=None → knee는 정본 경로(강체, α 그대로 1).
    ks1_hi 지정 시 hip 스프링 2단(H2): |τ|<tau0_1까지 ks1(무른), 초과분 ks1_hi(단단) — 연속 조각선형."""
    d0_1 = (tau0_1 / ks1) if ks1_hi else None      # 변곡 변형 [rad]
    def spr1(d):
        if not ks1_hi or abs(d) <= d0_1:
            return ks1 * d
        return np.sign(d) * (tau0_1 + ks1_hi * (abs(d) - d0_1))
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
    keys = ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "thm1", "thm2", "tsp1", "tsp2"]
    if record: keys += ["raw1", "raw2", "grf"]
    Lg = {k: np.zeros(N) for k in keys}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    # 모터 상태 초기화 (settle 시작 = 사지와 일치, 정지)
    th1 = -md.qpos[1] - np.pi/2; dth1 = 0.0
    th2 = -md.qpos[2]; dth2 = 0.0
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
        # ── hip 모터-스프링 (2단 옵션) ──
        tsp1 = spr1(th1 - q1c) + bs1*(dth1 - v1c)
        ddth1 = (s1 - tsp1)/jm1
        dth1 += ddth1*dt; th1 += dth1*dt                 # semi-implicit
        # ── knee (옵션) ──
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
        Lg["tsp1"][k] = tsp1; Lg["tsp2"][k] = tsp2
        if record:
            Lg["raw1"][k] = c1; Lg["raw2"][k] = c2
            Lg["grf"][k] = RU._grf_z(model, md)
    Lg["t"] = tl
    return Lg


if __name__ == "__main__":
    tw = TW.twin()
    Z = np.load(P25/"t0nc_cl_v9.npz")
    m0 = Z["t"] >= 0
    tg = np.asarray(Z["t"][m0], float)
    qd1, qd2 = Z["qd1"][m0], Z["qd2"][m0]
    dqd1, dqd2 = Z["dqd1"][m0], Z["dqd2"][m0]
    T_END = 0.216
    g0 = (150.0, 2.2, 250.0, 3.0)
    # ── 수렴 골든: 강성 극한 → 정본 α=1과 근접해야 ──
    La = TW.rollout_cl(tw, tg, qd1, qd2, dqd1, dqd2, g0, alphas=(1,1,1,1), t_end=T_END)
    Lb = rollout_cl_sea2(tw, tg, qd1, qd2, dqd1, dqd2, g0, ks1=1e5, bs1=60.0, jm1=0.005, t_end=T_END)
    if Lb is None:
        print("수렴 골든: 발산 FAIL")
    else:
        d = max(float(np.abs(La[k]-Lb[k]).max()) for k in ("q1", "q2", "bz"))
        print(f"수렴 골든 (ks=1e5): 정본 α=1 대비 최대차 {d:.2e} rad → {'PASS' if d < 5e-3 else 'CHECK'}", flush=True)
    # ── H6 v2: exp5 7게인 (hip만 SEA, b_s·J_m 소격자) ──
    DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_07_27")
    GAINS = [("60_2_250_3",(60,2)),("80_2_250_3",(80,2)),("100_1.5_250_3",(100,1.5)),("120_2_250_3",(120,2)),
             ("150_2.2_250_3",(150,2.2)),("200_2.5_250_3",(200,2.5)),("250_3_250_3",(250,3))]
    MODELS = {"OLD α (현행)": None}
    for bs in (0.5, 1.5, 3.0):
        for jm in (0.01, 0.03):
            MODELS[f"SEA2 bs{bs} jm{jm}"] = dict(ks1=169.0, bs1=bs, jm1=jm)
    OUT = {}
    MEAS = {}
    for lab, (kp1, kd1) in GAINS:
        hip = pd.read_excel(DATA/lab/"hip.xlsx"); knee = pd.read_excel(DATA/lab/"knee.xlsx"); grf = pd.read_excel(DATA/lab/"GRF.xlsx")
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        qd2m = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2m-qd2m[0]) > np.radians(0.5))[0]
        t0 = t[on[0]] if len(on) else 0.0
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)] - t0)
        tmv = t - t0
        MEAS[lab] = dict(t=tmv, q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                         a1=ahat_np(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float)),
                         a2=ahat_np(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float)),
                         msk=(tmv >= 0.005) & (tmv <= t_lo))
        OUT[lab] = {}
        for mname, kw in MODELS.items():
            if kw is None:
                L = TW.rollout_cl(tw, tg, qd1, qd2, dqd1, dqd2, (kp1, kd1, 250.0, 3.0),
                                  alphas=(0.40, 0.20, 0.656, 0.20), t_end=T_END, t_after=0.4)
                enc1 = L["q1"] if L else None; enc2 = L["q2"] if L else None
                sh1 = L["sh1"] if L else None; sh2 = L["sh2"] if L else None
            else:
                L = rollout_cl_sea2(tw, tg, qd1, qd2, dqd1, dqd2, (kp1, kd1, 250.0, 3.0),
                                    t_end=T_END, t_after=0.4, **kw)
                enc1 = L["thm1"] if L else None; enc2 = L["q2"] if L else None
                sh1 = L["tsp1"] if L else None; sh2 = L["tsp2"] if L else None
            if L is None:
                OUT[lab][mname] = None; continue
            M = MEAS[lab]; msk = M["msk"]
            q1s = np.interp(M["t"][msk], L["t"], enc1); q2s = np.interp(M["t"][msk], L["t"], enc2)
            s1s = np.interp(M["t"][msk], L["t"], sh1); s2ss = np.interp(M["t"][msk], L["t"], sh2)
            OUT[lab][mname] = dict(
                q1=round(float(np.degrees(np.sqrt(np.mean((M["q1"][msk]-q1s)**2)))), 2),
                q2=round(float(np.degrees(np.sqrt(np.mean((M["q2"][msk]-q2s)**2)))), 2),
                t1=round(float(np.sqrt(np.mean((M["a1"][msk]-s1s)**2))), 2),
                t2=round(float(np.sqrt(np.mean((M["a2"][msk]-s2ss)**2))), 2))
    json.dump(OUT, open(HERE/"_h6v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== H6 v2 집계 (7게인 평균: 인코더 q1/q2 RMSE[°], τ1/τ2 RMSE[Nm]) ===")
    for mn in MODELS:
        rs = [OUT[l][mn] for l, _ in GAINS if OUT[l].get(mn)]
        nf = 7 - len(rs)
        if not rs:
            print(f"{mn}: 전패(발산)"); continue
        print(f"{mn}: q1 {np.mean([r['q1'] for r in rs]):6.2f}  q2 {np.mean([r['q2'] for r in rs]):6.2f}  "
              f"τ1 {np.mean([r['t1'] for r in rs]):5.2f}  τ2 {np.mean([r['t2'] for r in rs]):5.2f}"
              + (f"  (발산 {nf})" if nf else ""))
