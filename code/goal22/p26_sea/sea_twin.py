# -*- coding: utf-8 -*-
"""sea_twin — 관측면 직렬탄성 CL 롤아웃 (H6: α 창발 시험).

구현 A (동역학 불변·관측/제어면 스프링):
  실기 PD는 '인코더각'으로 오차를 계산한다. 인코더 = 사지 + 비틀림:
    q_enc  = q_link + s_prev/k_s          (s = 직전 스텝 인가 축토크 [Nm])
    dq_enc = dq_link + (ds/dt)/k_s
  rollout_cl(정본, p25_a_twin) 문자 미러에 이 두 줄만 추가. k_s=∞ → 정본과 비트 동일(미러 골든).
H6: exp5 7게인을 라벨 게인 그대로(α=(1,1,1,1)) + k_s1=169로 CL 예측 → 실측과 비교.
  대조군 = 현행 방식(OLD α 테이블, 스프링 없음). SEA가 넓게 이기면 α는 스프링의 창발임이 입증.
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"          # 배포와 동일 클립 (pdrep 규약)
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

def rollout_cl_sea(tw, tg, qd1g, qd2g, dqd1g, dqd2g, gains, ks1=1e12, ks2=1e12,
                   alphas=(1, 1, 1, 1), t_end=None, t_after=None, record=False):
    """p25_a_twin.rollout_cl 문자 미러 + 관측면 스프링 (q_enc/dq_enc로 PD 오차 계산).
    ks=1e12 → 정본과 수치 동일 (미러 골든으로 검증). 원본 함수는 불변."""
    P = tw["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]
    tm = tw["tm"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    R19 = TW.R19
    RU = TW.RU
    if t_end is None: t_end = float(tg[-1])
    if t_after is None: t_after = P.J.T_AFTER
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
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
    keys = ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]
    if record: keys += ["raw1", "raw2", "grf", "q1enc", "q2enc"]
    Lg = {k: np.zeros(N) for k in keys}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    s1p = s1pp = s2p = s2pp = 0.0            # 직전/전전 스텝 인가 축토크 (스프링 상태)
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi/2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        # ★관측면 스프링: 인코더 = 사지 + 비틀림 (부호: Mode A 회귀 e1=+0.339°/Nm×â1)
        q1e = q1c + s1p/ks1; q2e = q2c + s2p/ks2
        v1e = v1c + (s1p - s1pp)/dt/ks1; v2e = v2c + (s2p - s2pp)/dt/ks2
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1g[0] - q1e) - S.SETTLE_KD * v1e
            c2 = S.SETTLE_KP * (qd2g[0] - q2e) - S.SETTLE_KD * v2e
            c1f, c2f = c1, c2
        else:
            tm_ = min(tc, t_end)
            c1 = kp1 * (np.interp(tm_, tg, qd1g) - q1e) + kd1 * (np.interp(tm_, tg, dqd1g) - v1e)
            c2 = kp2 * (np.interp(tm_, tg, qd2g) - q2e) + kd2 * (np.interp(tm_, tg, dqd2g) - v2e)
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP)); c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr: supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = 0.0
        if sprm is not None: tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        s1pp, s1p = s1p, s1                  # 스프링 상태 갱신
        s2pp, s2p = s2p, s2
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi/2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
        if record:
            Lg["raw1"][k] = c1; Lg["raw2"][k] = c2
            Lg["grf"][k] = RU._grf_z(model, md)
            Lg["q1enc"][k] = q1e; Lg["q2enc"][k] = q2e
    Lg["t"] = tl
    return Lg


if __name__ == "__main__":
    tw = TW.twin()
    Z = np.load(P25/"t0nc_cl_v9.npz")
    m0 = Z["t"] >= 0
    tg = Z["t"][m0] - 0.0
    tg = np.asarray(tg, float)
    qd1, qd2 = Z["qd1"][m0], Z["qd2"][m0]
    dqd1, dqd2 = Z["dqd1"][m0], Z["dqd2"][m0]
    T_END = 0.216
    # ── 미러 골든: ks=∞ + α 동일 → 정본 rollout_cl과 최대차 ──
    g0 = (150.0, 2.2, 250.0, 3.0); al0 = (0.40, 0.20, 0.656, 0.20)
    La = TW.rollout_cl(tw, tg, qd1, qd2, dqd1, dqd2, g0, alphas=al0, t_end=T_END, record=True)
    Lb = rollout_cl_sea(tw, tg, qd1, qd2, dqd1, dqd2, g0, ks1=1e12, ks2=1e12, alphas=al0, t_end=T_END, record=True)
    dmax = max(float(np.abs(La[k]-Lb[k]).max()) for k in ("q1", "q2", "dq2", "bz", "sh1", "sh2"))
    print(f"미러 골든 (ks=inf): 최대차 {dmax:.2e} → {'PASS' if dmax < 1e-12 else 'FAIL'}", flush=True)
    # ── H6: exp5 7게인 — 모델 3종 비교 ──
    DATA = Path((DATA_ROOT + "/26_07_27"))
    GAINS = [("60_2_250_3",(60,2)),("80_2_250_3",(80,2)),("100_1.5_250_3",(100,1.5)),("120_2_250_3",(120,2)),
             ("150_2.2_250_3",(150,2.2)),("200_2.5_250_3",(200,2.5)),("250_3_250_3",(250,3))]
    MODELS = {"OLD α (현행)": dict(alphas=(0.40,0.20,0.656,0.20), ks1=1e12, ks2=1e12),
              "SEA hip (k1=169, α=1)": dict(alphas=(1,1,1,1), ks1=169.0, ks2=1e12),
              "SEA hip+knee (k2=650)": dict(alphas=(1,1,1,1), ks1=169.0, ks2=650.0)}
    OUT = {}
    for lab, (kp1, kd1) in GAINS:
        hip = pd.read_excel(DATA/lab/"hip.xlsx"); knee = pd.read_excel(DATA/lab/"knee.xlsx"); grf = pd.read_excel(DATA/lab/"GRF.xlsx")
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        qd2m = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2m-qd2m[0]) > np.radians(0.5))[0]
        t0 = t[on[0]] if len(on) else 0.0
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)] - t0)
        tm_ = (t - t0)
        q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
        v1m = hip["currentAngleVelocity"].to_numpy(float); v2m = knee["currentAngleVelocity"].to_numpy(float)
        a1m = ahat_np(hip["currentTorque"].to_numpy(float), v1m)
        a2m = ahat_np(knee["currentTorque"].to_numpy(float), v2m)
        msk = (tm_ >= 0.005) & (tm_ <= t_lo)
        h_real = None
        try:
            import re
            mm = re.search(r"실제 점프 높이\s*:\s*([\d.]+)m", (DATA/lab/"Real Data.txt").read_text(encoding="utf-8", errors="ignore"))
            h_real = float(mm.group(1)) if mm else None
        except Exception: pass
        row = {}
        for mname, kw in MODELS.items():
            L = rollout_cl_sea(tw, tg, qd1, qd2, dqd1, dqd2, (kp1, kd1, 250.0, 3.0),
                               t_end=T_END, t_after=0.8, record=True, **kw)
            if L is None: row[mname] = None; continue
            # 비교 신호: 실측 인코더 ↔ 시뮬 인코더(q_enc), 실측 â ↔ 시뮬 sh
            q1s = np.interp(tm_[msk], L["t"], L["q1enc"] if kw["ks1"] < 1e9 else L["q1"])
            q2s = np.interp(tm_[msk], L["t"], L["q2enc"] if kw["ks2"] < 1e9 else L["q2"])
            s1s = np.interp(tm_[msk], L["t"], L["sh1"]); s2s_ = np.interp(tm_[msk], L["t"], L["sh2"])
            e_q1 = np.degrees(np.sqrt(np.mean((q1m[msk]-q1s)**2)))
            e_q2 = np.degrees(np.sqrt(np.mean((q2m[msk]-q2s)**2)))
            e_t1 = float(np.sqrt(np.mean((a1m[msk]-s1s)**2)))
            e_t2 = float(np.sqrt(np.mean((a2m[msk]-s2s_)**2)))
            ap = L["bz"] - L["bz"][np.searchsorted(L["t"], 0.0)]
            h_sim = float(np.max(ap[np.searchsorted(L["t"], 0.0):]))
            row[mname] = dict(q1=round(e_q1,2), q2=round(e_q2,2), t1=round(e_t1,2), t2=round(e_t2,2),
                              h_sim=round(h_sim,3), h_real=h_real)
        OUT[lab] = row
        pr = " | ".join(f"{mn}: q1 {r['q1']}° q2 {r['q2']}° τ1 {r['t1']} τ2 {r['t2']} h {r['h_sim']}" if r else f"{mn}: FAIL"
                        for mn, r in row.items())
        print(f"{lab.split('_')[0]:>4} (실측 h {h_real}): {pr}", flush=True)
    json.dump(OUT, open(HERE/"_h6_emergence.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 집계
    print("\n=== 집계 (7게인 평균) ===")
    for mn in MODELS:
        rs = [OUT[l][mn] for l, _ in GAINS if OUT[l][mn]]
        if not rs: continue
        print(f"{mn}: q1 {np.mean([r['q1'] for r in rs]):.2f}° q2 {np.mean([r['q2'] for r in rs]):.2f}° "
              f"τ1 {np.mean([r['t1'] for r in rs]):.2f}Nm τ2 {np.mean([r['t2'] for r in rs]):.2f}Nm "
              f"|Δh| {np.mean([abs(r['h_sim']-(r['h_real'] or np.nan)) for r in rs]):.3f}m")
