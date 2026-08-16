# -*- coding: utf-8 -*-
"""p25_a_twin — P25 Phase A 공용 배선: 승격 p24a 트윈 + 점프 태스크 롤아웃 코어.

트윈 = fourbar_p24a_candidate.json (env P23_SPRING_GATED=1 P23_RISE_GATED=1
P24_HIP_LAW=1 P24_REFIT=1 을 import 전에 설정 — p23_v6_runners 모듈 상수가 import
시점에 결정되므로 반드시 이 모듈을 첫 repo-import로 쓸 것). 플랜트 전 층
(supp/rise/게이트 스프링/힙 지지)이 cl_run23/a_full23과 동일하게 모든 롤아웃에 활성.
무변속 flip 모델 (l_i=30) — CVT 가지 없음 (c_cvt 미배선, qg=None 경로).

공통 태스크 (MARATHON_p25 동결):
  수직 최대 점프 · 시작 = 0602 첫 trial 측정 q(0) 웅크림 · horizon 0.6 s ·
  공급 천장 |raw| ≤ 35.5 (R19.CLIP, cl_run23과 동일 지점에서 클립 → ahat 체인) ·
  관절 범위 = fit 세션(0421/0424/0602) 방문 포락선 +10% 마진 (소프트 페널티) ·
  목적 = base-z apex (t>0 최대 절대 bz — a_full23 h_sim 규약, h_real과 직접 비교 가능).
  발 미끄럼: 모델이 수직 레일 1-DOF 베이스라 수평 DOF 자체가 없음 — 자동 충족.

롤아웃 코어 2종 (cl_run23 본체를 문자 그대로 미러 — 변경점은 ★ 주석):
  rollout_ol(rawgrid)  개루프: raw 커맨드 시계열 → tm 필터 → 클립 → ahat → 플랜트 층.
                       t>t_end 이후는 a_full23 비행 규약 (s=0, extra=LAW_A, 스프링 h=0,
                       힙 e1=a1) — 기록 끝 이후 무명령 물리.
  rollout_cl(...)      폐루프: (q_des, dq_des) PD → tm 필터 → 클립 → ahat → 플랜트 층.
                       t>t_end는 cl_run23 규약 (마지막 q_des 유지 추종).

골든 (main): ① 스칼라 ahat == P.J.ahat (1e-12) ② rollout_cl(트라이얼 모드) ==
RU.cl_run23 비트 동일 (0602 전 sub) ③ a_full23 0602 세션 dq2 RMSE 평균 ≈ 1.29
(promote 내장 재검증과 동일 산법 — 배선이 정본 러너와 같음을 증명).
"""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["P23_SPRING_GATED"] = "1"        # ★ import 전 필수 (모듈 상수 결정)
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"
os.environ["P24_REFIT"] = "1"

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
G22 = HERE.parent
sys.path.insert(0, str(G22 / "p23_veins"))
sys.path.insert(0, str(G22 / "p22_beyond"))
sys.path.insert(0, str(G22 / "p20_rise"))
sys.path.insert(0, str(G22 / "p19_jump"))
sys.path.insert(0, str(G22.parent / "bench"))

import p21_cma as C
import p22_eval as E
import p19_run as R19
import p23_v6_runners as RU
import safe

# P25_CLIP_RAW → 공급 클립 재정의 (raw 도메인; 기본 35.5 = 무설정 시 기존 동작 완전 보존).
# 18Nm 캠페인: 31.1771 (a_hat 운동방향 가지 = 정확히 18.00Nm; 35.5→20.23Nm과 동일 가지).
# 클립 '지점'은 불변 — cl_run23/a_full23/rollout_*이 R19.CLIP을 호출 시점에 읽으므로
# 모듈 상수만 바꾼다. 비기본 클립 산출물은 OUT_TAG(_t18) 접미로 저장 (원본 npz 보존).
CLIP_RAW = float(os.environ.get("P25_CLIP_RAW", "35.5"))
R19.CLIP = CLIP_RAW
OUT_TAG = "" if abs(CLIP_RAW - 35.5) < 1e-9 else "_t18"

CAND_PATH = G22 / "p23_veins/fourbar_p24a_candidate.json"
T_END = 0.6          # 커맨드 호라이즌 [s] (MARATHON 동결)
T_PUSH = 0.35        # 개루프 푸시 창 [s] (이후 0)
ENV_MARGIN = 0.10    # 방문 포락선 마진
PEN_W = 10.0         # 관절 포락선 위반 페널티 [1/(rad·s)] (apex[m]와 합산)
CRASH_F = 5.0        # 발산 시 목적값 (minimize 부호)
G_HIGH = (150.0, 2.2, 500.0, 4.0)   # (kp1, kd1, kp2, kd2) — 실기 폴더 라벨 규약
FIT_SESS = ("jump_position_0421", "jump_0424", "jump_0602")
GOLDEN_0602 = 1.29   # 세션 dq2 RMSE 평균 기대값 (promote 내장 재검증)

_T = {"tw": None}


def _ahat_s(A, raw, v):
    """p14_judge.ahat의 스칼라 동형 (np.array 래핑 제거 — 핫루프용). 골든 ①이 검증."""
    KT, GR, CF = 0.091, 9.0, 0.59
    Iq = (CF / (GR * KT)) * raw
    s = 0.0 if v == 0 else (1.0 if v > 0 else -1.0)
    return A[0] * GR * KT * Iq - A[1] * GR * abs(Iq) * Iq - A[2] * s - A[3] * abs(Iq) * s


def twin():
    """승격 트윈 1회 초기화 → dict (모델·층 파라미터·트라이얼·포락선·시작자세)."""
    if _T["tw"] is not None:
        return _T["tw"]
    assert RU.SPRING_GATED and RU.RISE_GATED and RU.HIP_LAW and RU.P24_REFIT, \
        "env 플래그가 import 전에 설정되지 않음"
    assert RU.NV23 == 26
    E.ensure_init()
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    cand = safe.read_json(CAND_PATH)
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))   # HIP dict 주입 포함
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    x32, sp = C.x32_of(v[:20])
    ref = float(v[1]); tm = float(v[14])
    d_dq = float(v[21]); kr = RU.rise_of(d_dq)
    model = RU.build_flip23(x32, ref, sp, d_dq)
    sprm = RU.spr_resolve(model, spr)
    P = C._W["P"]
    assert abs(R19.CLIP - CLIP_RAW) < 1e-12, f"CLIP={R19.CLIP} (기대 {CLIP_RAW})"

    # 시작 자세 = 0602 첫 trial 측정 q(0) (표준 로더 R19.TRIALS 경로)
    tr0602 = [(ds, sub, d) for ds, sub, d, *_ in R19.TRIALS if ds == "jump_0602"]
    ds0, sub0, d0 = tr0602[0]
    q1_0 = float(d0["q1"][0]); q2_0 = float(d0["q2"][0])

    # 방문 포락선 (fit 세션 측정 q 전 트레이스; held-out 0324 제외) + 10% 마진
    q1s = np.concatenate([d["q1"] for ds, sub, d, *_ in R19.TRIALS if ds in FIT_SESS])
    q2s = np.concatenate([d["q2"] for ds, sub, d, *_ in R19.TRIALS if ds in FIT_SESS])
    def _env(a):
        lo, hi = float(a.min()), float(a.max())
        m = ENV_MARGIN * (hi - lo)
        return lo - m, hi + m
    env = dict(q1=_env(q1s), q2=_env(q2s))

    _T["tw"] = dict(cand=cand, v=v, law=law, spr=spr, sprm=sprm, x32=x32, sp=sp,
                    ref=ref, tm=tm, d_dq=d_dq, kr=kr, model=model, P=P,
                    dt=float(model.opt.timestep), env=env,
                    q0=(q1_0, q2_0), seed_trial=(ds0, str(sub0)), d0=d0)
    return _T["tw"]


# ══════════════ 롤아웃 코어 (cl_run23 미러 — 변경점 ★) ══════════════
def rollout_cl(tw, tg, qd1g, qd2g, dqd1g, dqd2g, gains, alphas=(1, 1, 1, 1),
               t_end=None, t_after=None, record=False):
    """폐루프 PD 롤아웃 — RU.cl_run23 본체 문자 미러 (무변속 가지, ffk/ff_hip 없음).
    ★ 변경점: (qd, dqd)를 임의 그리드 (tg, ...)로 받음 (트라이얼 d 대신) + 로그 확장.
    t>t_end: cl_run23 규약 그대로 (tm_=min(tc,t_end) — 마지막 q_des 유지 추종).
    반환 로그 dict | None(발산). record=True면 raw/Nm 커맨드·grf도 기록."""
    P = tw["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]
    tm = tw["tm"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    if t_end is None:
        t_end = float(tg[-1])
    if t_after is None:
        t_after = P.J.T_AFTER
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -qd1g[0] - np.pi / 2, -qd2g[0]
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
    if record:
        keys += ["raw1", "raw2", "grf"]
    Lg = {k: np.zeros(N) for k in keys}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1g[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2g[0] - q2c) - S.SETTLE_KD * v2c
            c1f, c2f = c1, c2
        else:
            tm_ = min(tc, t_end)
            c1 = kp1 * (np.interp(tm_, tg, qd1g) - q1c) + kd1 * (np.interp(tm_, tg, dqd1g) - v1c)
            c2 = kp2 * (np.interp(tm_, tg, qd2g) - q2c) + kd2 * (np.interp(tm_, tg, dqd2g) - v2c)
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP)); c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = 0.0
        if sprm is not None:
            tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
        if record:
            Lg["raw1"][k] = c1; Lg["raw2"][k] = c2
            Lg["grf"][k] = RU._grf_z(model, md)
    Lg["t"] = tl
    return Lg


def settle_state(tw, q1_0, q2_0):
    """settle 0.4 s만 실행 (cl_run23 settle 블록 미러 — 층 전부 활성) → 상태 캐시.
    settle 커맨드는 최적화 파라미터와 무관 → 전 평가 공유 (비트 동일 지점)."""
    P = tw["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]
    kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    Ns = int(round(P.J.T_SETTLE / dt))
    c1f = c2f = 0.0
    for k in range(Ns):
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        c1f, c2f = c1, c2
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP)); c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = 0.0
        if sprm is not None:
            tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        mj.mj_step(model, md)
    return dict(qpos=md.qpos.copy(), qvel=md.qvel.copy(), c1f=c1f, c2f=c2f)


def rollout_ol(tw, tg, raw1g, raw2g, st, t_end=T_END, t_after=None, record=False):
    """개루프 raw 커맨드 롤아웃 — cl_run23의 커맨드 층(필터→클립→ahat)에 커맨드 소스만
    (tg, raw1g, raw2g) 보간으로 교체. st = settle_state 캐시에서 시작 (t=0부터 스텝).
    t>t_end: a_full23 비행 규약 (s=0, extra=LAW_A, 스프링 h=0, 힙 e1=a1=0).
    반환 로그 dict | None. _ahat_s 스칼라 사용 (골든 ①이 P.J.ahat 동치 검증)."""
    P = tw["P"]
    mj = P.J._P["mj"]
    law_a, law_b, law_v0 = tw["law"]
    tm = tw["tm"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    if t_after is None:
        t_after = P.J.T_AFTER
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    md.qpos[:] = st["qpos"]; md.qvel[:] = st["qvel"]
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((t_end + t_after) / dt)
    tl = np.arange(N) * dt
    keys = ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]
    if record:
        keys += ["raw1", "raw2", "grf"]
    Lg = {k: np.zeros(N) for k in keys}
    c1f, c2f = st["c1f"], st["c2f"]
    al = dt / max(tm, dt)
    for k in range(N):
        tc = tl[k]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc <= t_end:
            c1 = float(np.interp(tc, tg, raw1g))                # ★ 커맨드 소스 = 개루프
            c2 = float(np.interp(tc, tg, raw2g))
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)      # tm 필터 (cl_run23 동일)
            c1 = float(np.clip(c1f, -R19.CLIP, R19.CLIP))
            c2 = float(np.clip(c2f, -R19.CLIP, R19.CLIP))
            s1 = _ahat_s(A, c1, v1c)
            s2 = _ahat_s(A, c2, v2c)
            supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
            if kr:
                supp += float(RU.rise_term(v2c, kr, law_v0))
            tql = 0.0
            if sprm is not None:
                tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
            md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
            md.qfrc_applied[dof_knee] = tql
        else:                                                   # ★ a_full23 비행 규약
            c1 = c2 = 0.0
            s1 = s2 = 0.0
            md.ctrl[:] = [-(0.0 + RU.HIP["a1"]), -(0.0 + law_a)]
            md.qfrc_applied[dof_knee] = 0.0
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
        if record:
            Lg["raw1"][k] = c1; Lg["raw2"][k] = c2
            Lg["grf"][k] = RU._grf_z(model, md)
    Lg["t"] = tl
    return Lg


# ══════════════ 목적/페널티 공용 ══════════════
def env_pen(tw, Lg, dt=None):
    """관절 포락선(+10%) 위반 적분 [rad·s] — 소프트 제약."""
    e = tw["env"]
    if dt is None:
        dt = tw["dt"]
    v = 0.0
    for j, key in ((1, "q1"), (2, "q2")):
        lo, hi = e[key]
        q = Lg[key]
        v += float(np.sum(np.maximum(q - hi, 0.0) + np.maximum(lo - q, 0.0))) * dt
    return v


def apex_of(Lg):
    """h_plan = t>0 base-z 최대 [m] (a_full23 h_sim 규약 — 절대 bz)."""
    m = Lg["t"] > 0
    return float(Lg["bz"][m].max()) if m.any() else float("nan")


def stats_of(tw, Lg, t_push=T_END):
    """보고용 통계 (피크 raw/Nm/dq, 천장 점유율, 이지 시각)."""
    m = (Lg["t"] >= 0) & (Lg["t"] <= t_push)
    out = dict(
        peak_raw1=float(np.abs(Lg["raw1"][m]).max()),
        peak_raw2=float(np.abs(Lg["raw2"][m]).max()),
        peak_tau1_nm=float(np.abs(Lg["sh1"][m]).max()),
        peak_tau2_nm=float(np.abs(Lg["sh2"][m]).max()),
        peak_dq1=float(np.abs(Lg["dq1"]).max()),
        peak_dq2=float(np.abs(Lg["dq2"]).max()),
        ceil_frac_raw1=float(np.mean(np.abs(Lg["raw1"][m]) >= R19.CLIP - 0.1)),
        ceil_frac_raw2=float(np.mean(np.abs(Lg["raw2"][m]) >= R19.CLIP - 0.1)),
        env_pen=env_pen(tw, Lg))
    if "grf" in Lg:
        on = Lg["grf"] > 1.0
        idx = np.where((Lg["t"] > 0.02) & ~on)[0]
        out["t_liftoff"] = float(Lg["t"][idx[0]]) if len(idx) else float("nan")
    return out


def save_npz(path, Lg, extra=None):
    """npz 스키마 (Phase D 소비 규약 — 전 방법 공통):
    t[s] (settle 포함, 0=커맨드 시작) / q1 q2 dq1 dq2 (측정 관례 rad, rad/s) /
    raw1 raw2 (τ* raw 커맨드, 클립 후) / tau1_nm tau2_nm (=sh1/sh2, ahat 축토크 Nm) /
    bz[m] / grf[N] (+ qd1 qd2 dqd1 dqd2, 폐루프 방법) (+ knots_* 파라미터)."""
    d = dict(t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             raw1=Lg["raw1"], raw2=Lg["raw2"], tau1_nm=Lg["sh1"], tau2_nm=Lg["sh2"],
             bz=Lg["bz"], grf=Lg["grf"])
    if extra:
        d.update(extra)
    np.savez(path, **d)


# ══════════════ 골든 (배선 = 정본 러너 증명) ══════════════
def golden():
    tw = twin()
    P = tw["P"]
    out = {}
    # ① 스칼라 ahat == P.J.ahat
    rng = np.random.default_rng(0)
    raws = rng.uniform(-40, 40, 200); vs = rng.uniform(-20, 20, 200)
    dmax = max(abs(_ahat_s(P.A_PAPER, float(r), float(v))
                   - float(P.J.ahat(P.A_PAPER, np.array([r]), np.array([v]))[0]))
               for r, v in zip(raws, vs))
    out["ahat_scalar_maxdiff"] = float(dmax)
    ok1 = dmax < 1e-12
    # ② rollout_cl == RU.cl_run23 (0602 전 trial, 세션 alphas — 비트 동일)
    diffs = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0602":
            continue
        alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
        t = d["t"]
        dqd1 = d["dqd1"] if dqon else np.zeros_like(t)
        dqd2 = d["dqd2"] if dqon else np.zeros_like(t)
        Lc = RU.cl_run23(tw["model"], False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                         tw["tm"], alphas, tw["law"], c_cvt=0.0, o1=0.0, o2=0.0,
                         spr=tw["spr"], k_rise=tw["kr"])
        Lm = rollout_cl(tw, t, d["qd1"], d["qd2"], dqd1, dqd2, gains, alphas,
                        t_end=float(t[-1]))
        dd = max(float(np.abs(Lc[k] - Lm[k]).max()) for k in ("q1", "q2", "dq2", "bz"))
        diffs.append(dd)
    out["cl_mirror_maxdiff"] = float(max(diffs))
    ok2 = max(diffs) < 1e-12
    # ③ a_full23 0602 재생 dq2 RMSE (세션 평균 ≈ 1.29)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0602":
            continue
        res = RU.a_full23(tw["model"], False, l_i, d, tw["law"], 0.0, 0.0,
                          c_cvt=0.0, spr=tw["spr"], k_rise=tw["kr"])
        rows.append(dict(sub=str(sub), rmse=float(res[0]) if res else 9.9,
                         h_sim=float(res[1]) if res else float("nan"),
                         h_real=E.h_real_of(ds, sub)))
    mean0602 = float(np.mean([r["rmse"] for r in rows]))
    out["replay_0602"] = rows
    out["replay_0602_mean"] = mean0602
    ok3 = abs(mean0602 - GOLDEN_0602) < 0.15
    out["pass"] = dict(ahat=bool(ok1), cl_mirror=bool(ok2), replay=bool(ok3),
                       ALL=bool(ok1 and ok2 and ok3))
    return out


def main():
    safe.utf8_console()
    t0 = time.time()
    print("=== p25_a_twin golden — 배선 = 정본 러너 검증 ===", flush=True)
    tw = twin()
    print(f"init done [{time.time() - t0:.0f}s]  dt={tw['dt']}  "
          f"start q=({tw['q0'][0]:.4f}, {tw['q0'][1]:.4f}) rad "
          f"({tw['seed_trial'][0]}/{tw['seed_trial'][1]})", flush=True)
    print(f"envelope+10%: q1=[{tw['env']['q1'][0]:.4f}, {tw['env']['q1'][1]:.4f}] "
          f"q2=[{tw['env']['q2'][0]:.4f}, {tw['env']['q2'][1]:.4f}]", flush=True)
    g = golden()
    print(f"[1] ahat scalar maxdiff = {g['ahat_scalar_maxdiff']:.3e}", flush=True)
    print(f"[2] rollout_cl vs cl_run23 maxdiff = {g['cl_mirror_maxdiff']:.3e}", flush=True)
    for r in g["replay_0602"]:
        print(f"[3] 0602/{r['sub']:12s} dq2 RMSE={r['rmse']:.3f}  "
              f"h_sim={r['h_sim']:.3f}  h_real={r['h_real']:.3f}", flush=True)
    print(f"[3] session mean = {g['replay_0602_mean']:.3f} (기대 ~{GOLDEN_0602})", flush=True)
    print("PASS: " + "  ".join(f"{k}={'P' if v else 'F'}" for k, v in g["pass"].items()),
          flush=True)
    safe.atomic_json_write(HERE / "p25_a_golden.json",
                           dict(gen=time.strftime("%Y-%m-%d %H:%M"), golden=g,
                                dt=tw["dt"], q0=list(tw["q0"]),
                                env=tw["env"], seed_trial=list(tw["seed_trial"])))
    print(f"saved p25_a_golden.json [{time.time() - t0:.0f}s]", flush=True)


if __name__ == "__main__":
    main()
