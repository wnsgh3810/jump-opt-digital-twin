# -*- coding: utf-8 -*-
"""t0wc_cma — P25-task0 캠페인: task0(with_cvt) 제약판 트윈 CVT 점프 최적화 (OL/CL-CMA).

사용자 지시 (07-18): 제약 = AVT LEG task0_vertjump_with_cvt.py 기준 (t0_spec 포팅본) —
q1∈[−1.2566,−0.2967], 크랭크 qm∈[−2.95,−0.05], |τ̂|≤15 (raw 클립 RAW15=25.5810),
|dq|≤50, T-N 포락선 −0.731019/48.476878, 스탠스 ≤0.3 s (감사), 시작 자세 자유 (정적 settle).

트윈 CVT 유효범위 (캠페인 설계): p24a CVT 층(게이트 스프링·C_CVT 전달손실)은 0429 세션
l_i=25.08 mm에서만 검증 → AVT처럼 l_i 연속 최적화 대신 l_i ∈ {25.08(검증점, 주 결과),
20.0, 15.0(외삽 — 참고용, extrapolated 플래그)} 3점 이산 비교.

배선: 플랜트/커맨드 층은 p23_v6_runners.cl_run23(is_cvt=True) 본체를 문자 그대로 미러
(변경점 = 커맨드 소스만 ★). 골든 2종이 배선=정본을 증명:
  ① 재생: a_full23(0429 10 trials, QOFF_A429) 세션평균 dq2 RMSE ≈ 2.6057
     (p24a_crosscheck_ref.oldq.jump_0429 — CURRENT_STACK '재생 0429 2.61') — 클립 무관 경로.
  ② CL 미러: rollout_cl(트라이얼 모드) vs RU.cl_run23 비트 동일 (0429 trial).

방법 2종 (p25_a_cma_{ol,cl} 구조 이식, 시작 자세 자유 확장):
  OL-CMA  raw 토크 스플라인 (9매듭/관절, 끝매듭 0, 푸시 0.35 s) + 시작자세 2축 = dim 18.
  CL-CMA  q_des 스플라인 (8매듭/관절, 매듭0=시작자세=settle 목표) = dim 16,
          dq_des=도함수, 게인 = 실기 라벨 규약 (150, 2.2, 500, 4) = 0429 최고게인 폴더.
목적: minimize −apex + t0_spec.penalty(cvt=True) + τ초과 페널티(감사 tau 마진 전용 —
클립 박스는 운동방향 15 Nm, 반대방향 순간은 마찰 가세로 초과 가능 → soft로 단속).
감사 실패 시 페널티 ×10 에스컬레이션 재시작 (최대 2회).

산출 (본 폴더): t0wc_{ol,cl}_{li2508,li20,li15}.npz + *_audit.json + t0wc_golden.json.
npz 스키마 = p25_a 공통 스키마 + h_plan + qm(크랭크각 트레이스)/l_i[mm]/extrapolated
(+ CL: qd/dqd/gains) (+ knots).
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ["PYTHONIOENCODING"] = "utf-8"
# ★ 구조 플래그 4종은 p23 모듈 import 전에 env로 강제 (import 시점에 벡터 축수 결정)
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"
os.environ["P24_REFIT"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
PV = HERE.parent / "p23_veins"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PV))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import p23_v6_runners as RU
import p22_eval as E
import p19_run as R19
import t0_spec as T0

# task0 클립 = RAW15 (25.5810 raw ↔ |â|운동방향 = 15.00 Nm). 러너·미러 모두
# R19.CLIP을 호출 시점에 읽음 → 이 한 곳이 유일한 진입점 (t0nc_env와 동일 규약).
os.environ.setdefault("P25_CLIP_RAW", repr(T0.RAW15))
R19.CLIP = float(os.environ["P25_CLIP_RAW"])

assert RU.SPRING_GATED and RU.RISE_GATED and RU.HIP_LAW and RU.P24_REFIT, \
    "p24a 구조 플래그 불일치 (env 강제 실패)"

CAND = json.load(open(PV / "fourbar_p24a_candidate.json", encoding="utf-8"))

# ── 캠페인 상수 ──
T_END = 0.6                      # 커맨드 호라이즌 [s] (t0_spec 감사창과 동일)
T_PUSH = 0.35                    # OL 푸시 창 [s] (이후 raw=0)
CRASH_F = 5.0
W_TAU = 50.0                     # |â|>15 soft 페널티 (감사 tau 마진 전용, t0_spec 스타일)
GAINS = (150.0, 2.2, 500.0, 4.0)  # CL 게인 — 실기 폴더 라벨 규약 (0429 최고게인 폴더)
SEED_SUB = "150_2.2_500_4"       # 시드 트라이얼 (0429, 게인 일치 폴더)
GOLDEN_0429 = 2.6057             # p24a_crosscheck_ref.oldq.jump_0429 (canonical)
LIS = {"li2508": (0.02508, False), "li20": (0.020, True), "li15": (0.015, True)}
NK_OL = 9                        # OL 매듭/관절 (마지막 0 고정 → 자유 8)
NK_CL = 8                        # CL 매듭/관절 (매듭0 = 시작자세, 자유)
KT_OL = np.linspace(0.0, T_PUSH, NK_OL)
KT_CL = np.linspace(0.0, T_END, NK_CL)
MAXFEV_OL = 4000
MAXFEV_CL = 3200
MAXFEV_ESC = 1200                # 감사 실패 에스컬레이션 라운드 예산
POPSIZE = 16
Q0_MARGIN = 0.02                 # 시작자세 바운드 내부 마진 [rad]

G = {}


def setup():
    """winit+fix0421 1회 → 후보 벡터/트라이얼/상수 전역 확정 (p24a_all_results.setup 순서)."""
    if G.get("ready"):
        return
    t0 = time.time()
    RU.ensure_init()
    P = RU.C._W["P"]
    v = RU.apply_freeze(RU.pad23(np.asarray(CAND["x"], float)))
    x32, sp = RU.C.x32_of(v[:20])
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()      # ★ 반드시 fix0421 이후 (ensure_init가 보장)
    tr429 = [tr for tr in R19.TRIALS if tr[0] == "jump_0429"]
    assert tr429, "jump_0429 trials 없음"
    G.update(ready=True, P=P, mj=RU.C._W["mj"], S=P.J._P["S"], A=P.A_PAPER,
             V=v, X32=x32, SP=sp, REF=float(v[1]), TM=float(v[14]),
             LAW=RU.law_of(v), SPR=RU.spr_of(v), D_DQ=float(v[21]),
             KR=RU.rise_of(float(v[21])), C_CVT=float(v[20]),
             QOFF_CL429=(float(v[17]), float(v[18])), TR429=tr429, MODELS={})
    print(f"setup done [{time.time() - t0:.0f}s] — clip={R19.CLIP} "
          f"law={tuple(round(x, 4) for x in G['LAW'])} c_cvt={G['C_CVT']:.4f} "
          f"k_rise={G['KR']:.4f} tm={G['TM'] * 1000:.2f}ms "
          f"n429={len(tr429)}", flush=True)


def model_cvt(l_i):
    """l_i별 CVT 모델 1회 빌드 → (model, sprm, (qg, rg))."""
    setup()
    key = round(float(l_i), 6)
    if key not in G["MODELS"]:
        m = RU.build_cvt23(G["X32"], G["REF"], G["SP"], key, G["D_DQ"])
        sprm = RU.spr_resolve(m, G["SPR"])
        qgrg = RU.rtab(key) if G["C_CVT"] > 0 else (None, None)
        G["MODELS"][key] = (m, sprm, qgrg)
    return G["MODELS"][key]


# ══════════════ 롤아웃 코어 (cl_run23 is_cvt=True 본체 문자 미러 — 변경점 ★) ══════════════
def rollout_cl(l_i, tg, qd1g, qd2g, dqd1g, dqd2g, gains, alphas=(1, 1, 1, 1),
               t_after=None, record=False):
    """폐루프 PD 롤아웃 — RU.cl_run23(is_cvt=True) 본체 미러 (ffk/ff_hip 없음).
    ★ 변경점: (qd, dqd)를 임의 그리드 (tg, ...)로 받음 + record 로그 확장.
    t>tg[-1]: cl_run23 규약 (tm_=min(tc, tg[-1]) — 마지막 q_des 유지 추종).
    골든 ②가 RU.cl_run23과의 비트 동일을 증명. 반환 로그 dict | None(발산)."""
    from cvt_core import qpos_from_crank
    P = G["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = G["LAW"]
    tm = G["TM"]; kr = G["KR"]; c_cvt = G["C_CVT"]
    A = G["A"]
    model, sprm, (qg, rg) = model_cvt(l_i)
    if c_cvt <= 0:
        qg = rg = None
    if t_after is None:
        t_after = P.J.T_AFTER
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -qd1g[0] - np.pi / 2, -qd2g[0]
    md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + tg[-1] + t_after) / dt)
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
            tm_ = min(tc, tg[-1])
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
        if qg is not None:                                      # ★ C_CVT (CVT 한정)
            rr = float(np.interp(md.qpos[2], qg, rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(md.qvel[dof_knee])
            tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if sprm is not None:                                    # 게이트 스프링
            tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        if RU.HIP_LAW:                                          # 힙 지지 (온라인)
            md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        else:
            md.ctrl[:] = [-s1, -(s2 + supp)]
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


def rollout_ol(l_i, tg, raw1g, raw2g, q0, t_after=None, record=False):
    """개루프 raw 커맨드 롤아웃 — 시작자세 q0=(q1, qm) 자유라 settle(0.4 s)을 매 평가
    포함 (cl_run23 settle 블록 문자 미러 — 층 전부 활성). 커맨드 창(0≤t≤tg[-1])은
    cl_run23의 커맨드 층(필터→클립→ahat)에 소스만 (tg, raw) 보간으로 교체 (★).
    t>tg[-1]: a_full23 비행 규약 (s=0, extra=LAW_A, 스프링 h=0 → qfrc=0, 힙 e1=a1)."""
    from cvt_core import qpos_from_crank
    P = G["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = G["LAW"]
    tm = G["TM"]; kr = G["KR"]; c_cvt = G["C_CVT"]
    A = G["A"]
    model, sprm, (qg, rg) = model_cvt(l_i)
    if c_cvt <= 0:
        qg = rg = None
    if t_after is None:
        t_after = P.J.T_AFTER
    q1_0, q2_0 = q0
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + tg[-1] + t_after) / dt)
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
        if tc > tg[-1]:                                         # ★ a_full23 비행 규약
            c1 = c2 = 0.0
            s1 = s2 = 0.0
            if RU.HIP_LAW:
                md.ctrl[:] = [-(0.0 + RU.HIP["a1"]), -(0.0 + law_a)]
            else:
                md.ctrl[:] = [0.0, -law_a]
            md.qfrc_applied[dof_knee] = 0.0
        else:
            if tc < 0:
                c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
                c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
                c1f, c2f = c1, c2
            else:
                c1 = float(np.interp(tc, tg, raw1g))            # ★ 커맨드 소스 = 개루프
                c2 = float(np.interp(tc, tg, raw2g))
                c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
                c1, c2 = c1f, c2f
            c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP))
            c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
            s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
            supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
            if kr:
                supp += float(RU.rise_term(v2c, kr, law_v0))
            tql = 0.0
            if qg is not None:
                rr = float(np.interp(md.qpos[2], qg, rg))
                amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
                vk = float(md.qvel[dof_knee])
                tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
            if sprm is not None:
                tql += RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
            if RU.HIP_LAW:
                md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
            else:
                md.ctrl[:] = [-s1, -(s2 + supp)]
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


# ══════════════ 목적/감사 공용 ══════════════
def apex_of(Lg):
    m = Lg["t"] > 0
    return float(Lg["bz"][m].max()) if m.any() else float("nan")


def tau_pen(L, esc=1.0, t_end=T_END):
    """|â|>15 soft 페널티 — 감사 tau 마진 전용 (클립 박스는 운동방향만 15 Nm 보장;
    반대방향 순간은 마찰 가세로 초과 가능 → t0_spec.penalty와 같은 제곱합 규약)."""
    m = (L["t"] >= 0) & (L["t"] <= t_end)
    p = 0.0
    for sh in (L["sh1"][m], L["sh2"][m]):
        p += W_TAU * esc * float(np.sum(np.maximum(0.0, np.abs(sh) - 15.0) ** 2)) \
            / max(m.sum(), 1)
    return p


def objective(Lg, esc=1.0):
    if Lg is None:
        return CRASH_F
    return (-apex_of(Lg)
            + T0.penalty(Lg, t_end=T_END, cvt=True,
                         w_tn=50.0 * esc, w_dq=50.0 * esc, w_q=500.0 * esc)
            + tau_pen(Lg, esc=esc))


def stance_of(Lg):
    """이지 시각 [s] — grf<1 N 첫 시각 (t>0.02, p25_a stats_of 규약)."""
    on = Lg["grf"] > 1.0
    idx = np.where((Lg["t"] > 0.02) & ~on)[0]
    return float(Lg["t"][idx[0]]) if len(idx) else float("nan")


def stats_of(Lg, t_push=T_END):
    m = (Lg["t"] >= 0) & (Lg["t"] <= t_push)
    return dict(
        peak_raw1=float(np.abs(Lg["raw1"][m]).max()),
        peak_raw2=float(np.abs(Lg["raw2"][m]).max()),
        peak_tau1_nm=float(np.abs(Lg["sh1"][m]).max()),
        peak_tau2_nm=float(np.abs(Lg["sh2"][m]).max()),
        peak_dq1=float(np.abs(Lg["dq1"][m]).max()),
        peak_dq2=float(np.abs(Lg["dq2"][m]).max()),
        ceil_frac_raw1=float(np.mean(np.abs(Lg["raw1"][m]) >= R19.CLIP - 0.1)),
        ceil_frac_raw2=float(np.mean(np.abs(Lg["raw2"][m]) >= R19.CLIP - 0.1)),
        t_liftoff=stance_of(Lg))


def r_range_of(Lg, l_i):
    """커맨드 창의 전달비 r=dq_knee/dq_crank 범위 (rtab, 모델 크랭크 좌표 = −qm)."""
    qs, rs = RU.rtab(round(float(l_i), 6))
    m = (Lg["t"] >= 0) & (Lg["t"] <= T_END)
    rr = np.interp(-Lg["q2"][m], qs, rs)
    return float(rr.min()), float(rr.max())


def seed_trial():
    setup()
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in G["TR429"]:
        if str(sub) == SEED_SUB:
            return d
    return G["TR429"][0][2]


def save_all(tag, method, li_key, Lg, xb, params, meta):
    """npz + audit json 저장 (스키마 = p25_a 공통 + h_plan + qm/l_i/extrapolated)."""
    l_i, extrap = LIS[li_key]
    aud = T0.audit(Lg, t_end=T_END, cvt=True)
    h_plan = apex_of(Lg)
    st = stats_of(Lg)
    stance = st["t_liftoff"]
    rmin, rmax = r_range_of(Lg, l_i)
    bz0 = float(np.interp(0.0, Lg["t"], Lg["bz"]))
    npz = HERE / f"t0wc_{method}_{li_key}.npz"
    d = dict(t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             raw1=Lg["raw1"], raw2=Lg["raw2"], tau1_nm=Lg["sh1"], tau2_nm=Lg["sh2"],
             bz=Lg["bz"], grf=Lg["grf"],
             h_plan=h_plan, qm=Lg["q2"], l_i=l_i * 1000.0,
             extrapolated=float(extrap))
    d.update(params.get("npz_extra", {}))
    np.savez(npz, **d)
    out = dict(gen=time.strftime("%Y-%m-%d %H:%M"), method=method,
               l_i_mm=l_i * 1000.0, extrapolated=bool(extrap),
               extrapolation_note=(None if not extrap else
                                   "CVT 층(게이트 스프링·C_CVT)은 l_i=25.08mm(0429)에서만 "
                                   "검증 — 본 결과는 모델 외삽, 참고용"),
               clip_raw=float(R19.CLIP), gains=(list(GAINS) if method == "cl" else None),
               audit={k: (bool(v) if k == "pass" else float(v)) for k, v in aud.items()},
               h_plan=h_plan, bz_settle=bz0, h_rise=h_plan - bz0,
               stance_s=stance, stance_ok=(bool(stance <= T0.T_ST_MAX)
                                           if np.isfinite(stance) else False),
               r_range=[rmin, rmax], stats=st,
               params=params.get("json_params", {}),
               seed_sub=SEED_SUB, npz=npz.name, **meta)
    safe.atomic_json_write(HERE / f"t0wc_{method}_{li_key}_audit.json", out)
    print(f"[{method}/{li_key}] h_plan={h_plan:.4f} m (rise {h_plan - bz0:.4f})  "
          f"stance={stance:.3f}s  audit_pass={aud['pass']}  "
          f"peak dq=({st['peak_dq1']:.1f},{st['peak_dq2']:.1f})  "
          f"peak tau=({st['peak_tau1_nm']:.2f},{st['peak_tau2_nm']:.2f})  "
          f"r=[{rmin:.3f},{rmax:.3f}]", flush=True)
    return out


# ══════════════ 골든 (배선 = 정본 러너 증명) ══════════════
def golden():
    setup()
    P = G["P"]
    out = {"clip_raw": float(R19.CLIP)}
    # 클립 등가 확인: â(RAW15) 운동방향 = 15.00 Nm
    a_chk = float(P.J.ahat(G["A"], np.array([T0.RAW15]), np.array([5.0]))[0])
    out["ahat_at_RAW15"] = a_chk
    print(f"[0] ahat(RAW15={T0.RAW15}, v=+5) = {a_chk:.6f} Nm (기대 ~15.00)", flush=True)
    # ① 재생 골든: a_full23(0429, QOFF_A429) 세션평균 ≈ 2.6057 (클립 무관 경로)
    model_a, _, _ = model_cvt(0.02508)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in G["TR429"]:
        o1, o2 = E.QOFF_A429
        res = RU.a_full23(model_a, True, d["l_i"], d, G["LAW"], o1, o2,
                          c_cvt=G["C_CVT"], spr=G["SPR"], k_rise=G["KR"])
        rows.append(dict(sub=str(sub), rmse=float(res[0]) if res else 9.9,
                         h_sim=float(res[1]) if res else float("nan")))
        print(f"[1] 0429/{sub:16s} dq2 RMSE={rows[-1]['rmse']:.3f}", flush=True)
    mean429 = float(np.mean([r["rmse"] for r in rows]))
    ok1 = abs(mean429 - GOLDEN_0429) < 0.05
    out["replay_0429"] = rows
    out["replay_0429_mean"] = mean429
    out["replay_0429_canonical"] = GOLDEN_0429
    print(f"[1] session mean = {mean429:.4f} (canonical {GOLDEN_0429}) "
          f"{'PASS' if ok1 else 'FAIL'}", flush=True)
    # ② CL 미러: rollout_cl(트라이얼 모드) vs RU.cl_run23 비트 동일 (앞 3 trials)
    diffs = []
    o1, o2 = G["QOFF_CL429"]
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in G["TR429"][:3]:
        alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
        model_c, _, _ = model_cvt(0.02508)
        Lc = RU.cl_run23(model_c, True, 0.02508, d, gains, dqon, ffk, G["A"],
                         G["TM"], alphas, G["LAW"], c_cvt=G["C_CVT"],
                         o1=o1, o2=o2, spr=G["SPR"], k_rise=G["KR"])
        t = d["t"]
        dqd1 = d["dqd1"] if dqon else np.zeros_like(t)
        dqd2 = d["dqd2"] if dqon else np.zeros_like(t)
        Lm = rollout_cl(0.02508, t, d["qd1"] + o1, d["qd2"] + o2, dqd1, dqd2,
                        gains, alphas)
        dd = max(float(np.abs(Lc[k] - Lm[k]).max())
                 for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"))
        diffs.append(dd)
        print(f"[2] 0429/{sub:16s} mirror max|Δ|={dd:.3e}", flush=True)
    out["cl_mirror_maxdiff"] = float(max(diffs))
    ok2 = max(diffs) < 1e-12
    out["pass"] = dict(replay=bool(ok1), cl_mirror=bool(ok2),
                       ALL=bool(ok1 and ok2))
    print(f"GOLDEN {'PASS' if out['pass']['ALL'] else 'FAIL'}", flush=True)
    safe.atomic_json_write(HERE / "t0wc_golden.json", out)
    if not out["pass"]["ALL"]:
        raise SystemExit("GOLDEN FAIL — 최적화 진입 금지")
    return out


# ══════════════ CMA 러너 (감사 실패 시 페널티 ×10 에스컬레이션) ══════════════
def run_cma(f_of, x0, sigma0, bounds, maxfev, seed, stds=None, label=""):
    import cma
    opts = dict(bounds=[list(bounds[0]), list(bounds[1])], popsize=POPSIZE,
                maxfevals=maxfev, seed=seed, verbose=-1)
    if stds is not None:
        opts["CMA_stds"] = list(stds)
    es = cma.CMAEvolutionStrategy(list(x0), sigma0, opts)
    t0 = time.time()
    nfev = [0]
    while not es.stop():
        X = es.ask()
        es.tell(X, [f_of(np.asarray(x, float), nfev) for x in X])
        if es.countiter % 25 == 0:
            print(f"  {label} it {es.countiter:4d}  nfev {nfev[0]:5d}  "
                  f"best f={es.result.fbest:.4f}  [{time.time() - t0:.0f}s]", flush=True)
    return np.asarray(es.result.xbest, float), float(es.result.fbest), nfev[0]


def run_ol(li_key):
    setup()
    l_i, _ = LIS[li_key]
    model, _, _ = model_cvt(l_i)
    dt = float(model.opt.timestep)
    TG = np.arange(0.0, T_END + dt, dt)
    d0 = seed_trial()
    t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    ts = tp - T_PUSH * 0.85
    seed1 = np.interp(ts + KT_OL[:-1], t, d0["traw1"])
    seed2 = np.interp(ts + KT_OL[:-1], t, d0["traw2"])
    q0_seed = (float(d0["q1"][0]), float(d0["q2"][0]))
    lo_q = [T0.Q1_LB + Q0_MARGIN, T0.QM_LB + Q0_MARGIN]
    hi_q = [T0.Q1_UB - Q0_MARGIN, T0.QM_UB - Q0_MARGIN]
    x0 = np.concatenate([np.clip(q0_seed, np.array(lo_q) + 1e-6, np.array(hi_q) - 1e-6),
                         np.clip(np.concatenate([seed1, seed2]),
                                 -(R19.CLIP - 0.5), R19.CLIP - 0.5)])
    lo = np.array(lo_q + [-R19.CLIP] * (2 * (NK_OL - 1)))
    hi = np.array(hi_q + [R19.CLIP] * (2 * (NK_OL - 1)))
    stds = [0.08, 0.15] + [8.0] * (2 * (NK_OL - 1))

    from scipy.interpolate import CubicSpline

    def raw_grid(free):
        k1 = np.append(free[:NK_OL - 1], 0.0)
        k2 = np.append(free[NK_OL - 1:], 0.0)
        s1 = CubicSpline(KT_OL, k1, bc_type="natural")
        s2 = CubicSpline(KT_OL, k2, bc_type="natural")
        r1 = np.where(TG <= T_PUSH, s1(np.minimum(TG, T_PUSH)), 0.0)
        r2 = np.where(TG <= T_PUSH, s2(np.minimum(TG, T_PUSH)), 0.0)
        return r1, r2

    ncrash = [0]

    def make_f(esc):
        def f(x, nfev):
            nfev[0] += 1
            r1, r2 = raw_grid(x[2:])
            Lg = rollout_ol(l_i, TG, r1, r2, (float(x[0]), float(x[1])))
            if Lg is None:
                ncrash[0] += 1
                return CRASH_F
            return objective(Lg, esc=esc)
        return f

    t0 = time.time()
    esc = 1.0
    x0r, sig, fev = x0, 1.0, MAXFEV_OL
    tot_ev = 0
    for rnd in range(3):
        f = make_f(esc)
        f0 = f(x0r, [0])
        print(f"[ol/{li_key}] round {rnd} esc={esc:.0f} seed f={f0:.4f}", flush=True)
        xb, fb, ne = run_cma(f, x0r, sig, (lo, hi), fev, seed=11 + rnd,
                             stds=stds, label=f"ol/{li_key}")
        tot_ev += ne
        r1, r2 = raw_grid(xb[2:])
        Lg = rollout_ol(l_i, TG, r1, r2, (float(xb[0]), float(xb[1])), record=True)
        aud = T0.audit(Lg, t_end=T_END, cvt=True)
        print(f"[ol/{li_key}] round {rnd} best f={fb:.4f} audit_pass={aud['pass']} "
              f"[{time.time() - t0:.0f}s]", flush=True)
        if aud["pass"]:
            break
        esc *= 10.0
        x0r, sig, fev = xb, 0.3, MAXFEV_ESC
    params = dict(
        npz_extra=dict(knot_t=KT_OL,
                       knots_raw1=np.append(xb[2:2 + NK_OL - 1], 0.0),
                       knots_raw2=np.append(xb[2 + NK_OL - 1:], 0.0),
                       q0=np.array([xb[0], xb[1]])),
        json_params=dict(q0=[float(xb[0]), float(xb[1])],
                         knot_t=[float(a) for a in KT_OL],
                         knots_raw1=[float(a) for a in np.append(xb[2:2 + NK_OL - 1], 0.0)],
                         knots_raw2=[float(a) for a in np.append(xb[2 + NK_OL - 1:], 0.0)]))
    meta = dict(evals=tot_ev, crashes=ncrash[0], f_best=fb, esc_final=esc,
                note=f"OL raw 스플라인 CMA (9매듭/관절, 끝매듭 0, 푸시 {T_PUSH}s, "
                     f"시작자세 자유 2축, dim {len(x0)}, clip ±{R19.CLIP})",
                wall_s=float(time.time() - t0))
    return save_all("t0wc", "ol", li_key, Lg, xb, params, meta)


def run_cl(li_key):
    setup()
    l_i, _ = LIS[li_key]
    model, _, _ = model_cvt(l_i)
    dt = float(model.opt.timestep)
    TG = np.arange(0.0, T_END + dt, dt)
    d0 = seed_trial()
    t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    ts = tp - 0.3
    lo = np.array([T0.Q1_LB] * NK_CL + [T0.QM_LB] * NK_CL)
    hi = np.array([T0.Q1_UB] * NK_CL + [T0.QM_UB] * NK_CL)
    seed1 = np.concatenate([[d0["q1"][0]], np.interp(ts + KT_CL[1:], t, d0["qd1"])])
    seed2 = np.concatenate([[d0["q2"][0]], np.interp(ts + KT_CL[1:], t, d0["qd2"])])
    x0 = np.clip(np.concatenate([seed1, seed2]), lo + 1e-6, hi - 1e-6)

    from scipy.interpolate import CubicSpline

    def qd_grids(x):
        s1 = CubicSpline(KT_CL, x[:NK_CL], bc_type="natural")
        s2 = CubicSpline(KT_CL, x[NK_CL:], bc_type="natural")
        return s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)

    ncrash = [0]

    def make_f(esc):
        def f(x, nfev):
            nfev[0] += 1
            g1, g2, dg1, dg2 = qd_grids(x)
            Lg = rollout_cl(l_i, TG, g1, g2, dg1, dg2, GAINS, alphas=(1, 1, 1, 1))
            if Lg is None:
                ncrash[0] += 1
                return CRASH_F
            return objective(Lg, esc=esc)
        return f

    t0 = time.time()
    esc = 1.0
    x0r, sig, fev = x0, 0.15, MAXFEV_CL
    tot_ev = 0
    for rnd in range(3):
        f = make_f(esc)
        f0 = f(x0r, [0])
        print(f"[cl/{li_key}] round {rnd} esc={esc:.0f} seed f={f0:.4f}", flush=True)
        xb, fb, ne = run_cma(f, x0r, sig, (lo, hi), fev, seed=31 + rnd,
                             label=f"cl/{li_key}")
        tot_ev += ne
        g1, g2, dg1, dg2 = qd_grids(xb)
        Lg = rollout_cl(l_i, TG, g1, g2, dg1, dg2, GAINS, alphas=(1, 1, 1, 1),
                        record=True)
        aud = T0.audit(Lg, t_end=T_END, cvt=True)
        print(f"[cl/{li_key}] round {rnd} best f={fb:.4f} audit_pass={aud['pass']} "
              f"[{time.time() - t0:.0f}s]", flush=True)
        if aud["pass"]:
            break
        esc *= 10.0
        x0r, sig, fev = xb, 0.05, MAXFEV_ESC
    # qd/dqd를 로그 시간축으로 확장 (t<0 = 시작값 유지, t>0.6 = 마지막값 유지 / dqd=0)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= T_END),
                      np.interp(np.clip(tl, 0.0, T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    params = dict(
        npz_extra=dict(qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
                       knot_t=KT_CL, knots_qd1=xb[:NK_CL], knots_qd2=xb[NK_CL:],
                       gains=np.array(GAINS)),
        json_params=dict(knot_t=[float(a) for a in KT_CL],
                         knots_qd1=[float(a) for a in xb[:NK_CL]],
                         knots_qd2=[float(a) for a in xb[NK_CL:]]))
    meta = dict(evals=tot_ev, crashes=ncrash[0], f_best=fb, esc_final=esc,
                note=f"CL q_des 스플라인 CMA (8매듭/관절, 매듭0=시작자세 자유, dim "
                     f"{len(x0)}; dq_des=도함수; gains={GAINS}, alphas=1, "
                     f"clip ±{R19.CLIP})",
                wall_s=float(time.time() - t0))
    return save_all("t0wc", "cl", li_key, Lg, xb, params, meta)


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "all"
    if mode == "golden":
        golden()
        return
    li_keys = [args[1]] if len(args) > 1 else list(LIS.keys())
    if mode in ("ol", "cl"):
        golden()
        for k in li_keys:
            (run_ol if mode == "ol" else run_cl)(k)
        return
    # all: 골든 → l_i별 (cl, ol)
    golden()
    for k in li_keys:
        run_cl(k)
        run_ol(k)


if __name__ == "__main__":
    main()
