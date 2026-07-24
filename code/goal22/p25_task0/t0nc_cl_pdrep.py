# -*- coding: utf-8 -*-
"""t0nc_cl_pdrep — CL-CMA 재최적화 (순수 PD 배포 전용, 클립 리라이언스 제거).

동기 (사용자 07-22): 실기가 FF 없이 q_des·dq_des만 받는 순수 PD 채널. CL-CMA는
애초에 순수 PD용 최적화(q_des 미끼를 폐루프 PD가 점프로 만듦)라 딱 맞음.
★문제: 기존 t0nc_cl은 최적화 클립 25.581(=15Nm)에서 명령이 클립을 타 â=15로
눌리고 감사 통과 — 하지만 배포 클립 35.5에선 같은 폐루프가 명령을 25.581 넘겨
â가 20~23Nm로 터짐 (계획≠배포). ★해결: 최적화를 배포와 동일한 클립 35.5로 돌리고
15Nm은 클립이 아닌 페널티(W_tau=200)로만 강제 → 명령이 â≤15인 곳에 자연히 머물러
배포가 그대로 재현. 기존 t0nc_cl.npz는 불변 — 새 파일로 산출.

게인 = env P25_CL_GAIN="kp1,kd1,kp2,kd2" (기본 150/2.2/500/4, α=1).
제약·페널티·감사 = t0nc_cma의 CL 경로 재사용 (import). 시드 = 기존 t0nc_cl 매듭.
산출: t0nc_cl_<TAG>.npz + t0nc_cl_<TAG>_audit.json  (TAG = env P25_CL_TAG, 기본 pdrep).
"""
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
# ★ 클립 = 하드웨어 천장 35.5 (배포와 동일). 15Nm은 클립이 아닌 페널티로만 강제 →
#   명령이 â≤15인 곳에 자연히 머물러 배포(클립 35.5)가 그대로 재현 (클립 리라이언스 제거).
os.environ["P25_CLIP_RAW"] = "35.5"

from pathlib import Path
import time
import numpy as np
import cma
from scipy.interpolate import CubicSpline

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))

import p25_a_twin as TW          # noqa: E402  (env 플래그 + repo 경로 주입 — 첫 repo-import)
import t0_spec as T0             # noqa: E402
import safe                      # noqa: E402
import t0nc_cma as C             # noqa: E402  (constants + fval/extra_pen/bounds/stance_of 재사용)

# ── 대표 게인 (env 우선) — GAIN=로봇에 넣는 라벨, ALPHA=실효/라벨 배율(β, 관절별) ──
_g = os.environ.get("P25_CL_GAIN", "").strip()
GAIN = tuple(float(x) for x in _g.split(",")) if _g else TW.G_HIGH
assert len(GAIN) == 4, f"P25_CL_GAIN must be kp1,kd1,kp2,kd2 (got {GAIN})"
_a = os.environ.get("P25_CL_ALPHA", "").strip()
ALPHA = tuple(float(x) for x in _a.split(",")) if _a else (1.0, 1.0, 1.0, 1.0)
assert len(ALPHA) == 4, f"P25_CL_ALPHA must be ap1,ad1,ap2,ad2 (got {ALPHA})"
EFF = tuple(g * a for g, a in zip(GAIN, ALPHA))     # 실효 게인 (트윈이 실제 쓰는 값)
TAG = os.environ.get("P25_CL_TAG", "pdrep").strip()
# ★ hip 굽힘 제한 (env P25_Q1_FLEXLIM [deg, 음수]) — 미끄럼-안전 얕은 자세 강제.
#   실제 q1이 이보다 더 굽으면(더 음수) 페널티. pd15(-59.5) 안전·v4(-66.4) 미끄럼 → 중간 -63 권장.
_fl = os.environ.get("P25_Q1_FLEXLIM", "").strip()
FLEXLIM = np.radians(float(_fl)) if _fl else None
# ★ 자코비안 수평력 페널티 (env P25_FH_W>0 활성, v8) — 계획 토크→발끝 힘 F=J^{-T}τ (준정적
#   CAD 지렛대 산수, 접촉모델 불사용). 스탠스 |F_h|/F_v 비가 R0 넘으면 벌점 → 수직으로 미는
#   슬립-안전 궤적 유도. 근거: 슬립~hip일 r=0.70·hip 1Nm=수평력 2~6배(exp3 일원장 분석),
#   실측 비 exp1 0.25=안전 / exp2 0.84=슬립 100mm. α는 v7 그대로(OLD) — 변화는 F_h 하나만.
FH_W = float(os.environ.get("P25_FH_W", "0") or 0)
FH_R0 = float(os.environ.get("P25_FH_R0", "0.3"))
_L_SEG = 0.25


def fh_ratio(L):
    """스탠스(grf>1N) 구간의 |F_h|/F_v 벡터 (준정적 자코비안 역산)."""
    m = (L["t"] >= 0) & (L["t"] <= TW.T_END) & (L["grf"] > 1.0)
    if int(m.sum()) < 3:
        return np.zeros(0)
    a = L["q1"][m]; b = L["q1"][m] + L["q2"][m]
    t1 = L["sh1"][m]; t2 = L["sh2"][m]
    j00 = -_L_SEG * np.sin(a) - _L_SEG * np.sin(b); j01 = -_L_SEG * np.sin(b)
    j10 = _L_SEG * np.cos(a) + _L_SEG * np.cos(b); j11 = _L_SEG * np.cos(b)
    det = j00 * j11 - j01 * j10
    ok = np.abs(det) > 1e-6
    fh = (j11 * t1 - j10 * t2)[ok] / det[ok]
    fv = (-j01 * t1 + j00 * t2)[ok] / det[ok]
    return np.abs(fh) / np.maximum(np.abs(fv), 20.0)
# ★ 시작(몸)높이 제약 (env P25_BZFK_MIN [m], v8) — FK 몸높이 = -L(sin q1 + sin(q1+q2)).
#   스탠스 중 실현 몸높이가 이보다 낮으면 벌점. hip각도 FLEXLIM의 풍선효과(무릎 접기로 깊이
#   우회) 차단. 실측 시작높이: exp1 0.208(슬립 최소)/exp2 0.146/exp3 0.152(깊은 스쿼트 변장).
BZFK_MIN = float(os.environ.get("P25_BZFK_MIN", "0") or 0)


def bzfk_min(L):
    """스탠스(grf>1N) 중 FK 몸높이 최저 [m]."""
    m = (L["t"] >= 0) & (L["t"] <= TW.T_END) & (L["grf"] > 1.0)
    if int(m.sum()) < 3:
        return 1.0
    bh = -_L_SEG * (np.sin(L["q1"][m]) + np.sin(L["q1"][m] + L["q2"][m]))
    return float(bh.min())

BUDGET = 3600
ESC_BUDGET = 1600
MAX_ROUNDS = 3


# ★ 시작 속도 0 강제 (env P25_CLAMP0=1, v9) — 스플라인 시작 도함수=0 (clamped).
#   미끼가 t=0에 속도 명령을 던지는 '급발진 킥'(v8 dqd1(0)=-8.5) 차단: 킥은 (a)몸 조기낙하
#   →knee 조기하중 (b)실제 hip이 낙하 추종→계획(소프트 hip)의 지연-토크 소멸=hip 공백→knee 보상
#   두 갈래로 knee 조기토크·hip q 어긋남을 만들었다(exp4 5층 해부). 배포 xlsx는 npz 밀집배열
#   (qd/dqd)을 그대로 쓰므로 자동 일관. 주의: 분석 시 매듭 재구성하면 bc 동일하게 할 것.
CLAMP0 = os.environ.get("P25_CLAMP0", "").strip() == "1"
_BC = ((1, 0.0), "natural") if CLAMP0 else "natural"


def roll_cl(tw, z):
    """t0nc_cma.roll_cl 미러 — 게인만 GAIN으로 교체 (alphas=(1,1,1,1))."""
    NKC = C.NKC
    k1 = np.concatenate([[z[0]], z[2:2 + NKC - 1]])
    k2 = np.concatenate([[z[1]], z[2 + NKC - 1:]])
    s1 = CubicSpline(C.KTC, k1, bc_type=_BC)
    s2 = CubicSpline(C.KTC, k2, bc_type=_BC)
    g1, g2, dg1, dg2 = s1(C.TG), s2(C.TG), s1(C.TG, 1), s2(C.TG, 1)
    L = TW.rollout_cl(tw, C.TG, g1, g2, dg1, dg2, GAIN, alphas=ALPHA,
                      t_end=TW.T_END, record=True)
    return L, dict(knot_t=C.KTC, knots_qd1=k1, knots_qd2=k2, grids=(g1, g2, dg1, dg2))


def seed_from_existing(tw, lb, ub):
    """시드 = 기존 t0nc_cl.npz 매듭 (이미 task0 실현). 부재 시 t0nc_cma.seed_x0 폴백."""
    src = HERE / os.environ.get("P25_SEED_NPZ", "t0nc_cl.npz")
    if src.exists():
        z0 = np.load(src)
        if "knots_qd1" in z0.files:
            k1 = np.asarray(z0["knots_qd1"], float)
            k2 = np.asarray(z0["knots_qd2"], float)
            q0 = np.asarray(z0["q0"], float)
            q1s = float(np.clip(q0[0], T0.Q1_LB + 2e-3, T0.Q1_UB - 2e-3))
            q2s = float(np.clip(q0[1], T0.Q2_LB + 2e-3, T0.Q2_UB - 2e-3))
            k1c = np.clip(k1[1:], T0.Q1_LB + 1e-3, T0.Q1_UB - 1e-3)
            k2c = np.clip(k2[1:], T0.Q2_LB + 1e-3, T0.Q2_UB - 1e-3)
            z = np.concatenate([[q1s, q2s], k1c, k2c])
            print(f"seed: 기존 t0nc_cl.npz 매듭  q0=({q1s:.4f},{q2s:.4f}) rad", flush=True)
            return (z - lb) / (ub - lb)
    print("seed: t0nc_cl.npz 부재 → t0nc_cma.seed_x0 폴백", flush=True)
    return C.seed_x0("cl", tw, lb, ub)


def optimize():
    t0 = time.time()
    assert abs(TW.CLIP_RAW - 35.5) < 1e-9, "P25_CLIP_RAW=35.5 미설정 (배포와 동일 클립)"
    tw = TW.twin()
    C.TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    lb, ub = C.bounds("cl")
    # ★ 깊은 크라우치 (env P25_CROUCH_Q1UB [deg]): q0 hip 상한을 더 깊게(음수↑) 제한.
    _q1ub = os.environ.get("P25_CROUCH_Q1UB", "").strip()
    if _q1ub:
        ub[0] = np.radians(float(_q1ub))
        print(f"★깊은 크라우치: q0 hip ∈ [{np.degrees(lb[0]):.0f}, {float(_q1ub):.0f}]°", flush=True)
    W = dict(C.W0)
    # ★ 15Nm 강제는 페널티 단독 (클립 35.5는 배포용 하드웨어 천장 — 15Nm 안 걸림).
    #   가중치 강화 + 목표 마진 0.3 (감사 max|â|≤15 통과 + 배포 여유).
    W["tau"] = 200.0
    W["d_tau"] = 0.3
    # ★ 스탠스 0.3s 제약 제거 (env P25_NO_STANCE=1): 긴 푸시 허용
    NO_STANCE = os.environ.get("P25_NO_STANCE", "").strip() == "1"
    if NO_STANCE:
        W["st"] = 0.0
        print("★스탠스 0.3s 제약 제거 (W_st=0)", flush=True)
    nfev = [0]; ncrash = [0]

    def f(x):
        nfev[0] += 1
        z = lb + np.clip(np.asarray(x, float), 0.0, 1.0) * (ub - lb)
        L, _ = roll_cl(tw, z)
        if L is None:
            ncrash[0] += 1
            return TW.CRASH_F
        val = C.fval(L, W)
        if FLEXLIM is not None:      # ★ hip 굽힘 제한 페널티 (실제 q1 < FLEXLIM 이면 벌점)
            m = (L["t"] >= 0) & (L["t"] <= TW.T_END)
            viol = np.maximum(0.0, FLEXLIM - L["q1"][m])
            val += 1000.0 * float(np.sum(viol * viol + 0.3 * viol)) / max(int(m.sum()), 1)
        if FH_W > 0:                 # ★ 수평력 비 페널티 (살짝 — 높이와 균형)
            r = fh_ratio(L)
            if len(r):
                e = np.maximum(0.0, r - FH_R0)
                val += FH_W * float(np.mean(e * e + 0.3 * e))
        if BZFK_MIN > 0:             # ★ 시작높이(몸) 제약 — 깊은 스쿼트 벌점 (풍선효과 차단)
            e = max(0.0, BZFK_MIN - bzfk_min(L))
            val += 1000.0 * (e * e + 0.3 * e)
        return val

    x0 = np.clip(seed_from_existing(tw, lb, ub), 0.0, 1.0)   # 새 바운드(깊은 크라우치) 밖 시드 클립
    f0 = f(x0)
    print(f"=== t0nc CL 재최적 (순수 PD) — 게인 {GAIN}  ★clip ±{TW.CLIP_RAW}(배포동일)  "
          f"15Nm=페널티단독(W_tau={W['tau']:.0f})  dim {len(lb)} ===", flush=True)
    print(f"seed f={f0:.4f}", flush=True)

    xcur, sigma, budget = x0, C.SIGMA0, BUDGET
    rounds = []
    L = knots = aud = None; ts = float("nan")
    for rnd in range(MAX_ROUNDS):
        es = cma.CMAEvolutionStrategy(
            xcur, sigma,
            dict(bounds=[0.0, 1.0], popsize=C.POPSIZE, maxfevals=budget,
                 seed=11 + rnd, verbose=-1))
        while not es.stop():
            X = es.ask()
            es.tell(X, [f(x) for x in X])
            if es.countiter % 25 == 0:
                print(f"  r{rnd} it {es.countiter:4d}  nfev {nfev[0]:5d}  "
                      f"best f={es.result.fbest:.4f}  [{time.time() - t0:.0f}s]", flush=True)
        xcur = np.asarray(es.result.xbest, float)
        z = lb + np.clip(xcur, 0.0, 1.0) * (ub - lb)
        L, knots = roll_cl(tw, z)
        assert L is not None, "최적해 롤아웃 발산"
        aud = T0.audit(L, t_end=TW.T_END, cvt=False)
        ts = C.stance_of(L)
        h = TW.apex_of(L)
        ok = aud["pass"] and (NO_STANCE or ts <= T0.T_ST_MAX + 1e-6)
        worst = max((v, k) for k, v in aud.items() if k != "pass")
        rounds.append(dict(round=rnd, budget=budget, f_best=float(es.result.fbest),
                           h=float(h), audit_pass=bool(aud["pass"]), stance=float(ts),
                           worst=[worst[1], float(worst[0])]))
        r_fh = fh_ratio(L)
        print(f"round {rnd}: h={h:.4f} stance={ts:.3f} audit_pass={aud['pass']} "
              f"worst={worst[1]}:{worst[0]:+.4f}  Fh/Fv 중앙 {np.median(r_fh) if len(r_fh) else 0:.2f}"
              f"/90% {np.percentile(r_fh, 90) if len(r_fh) else 0:.2f}  몸높이최저 {bzfk_min(L):.3f}m"
              f"  [{time.time() - t0:.0f}s]", flush=True)
        if ok:
            break
        for k in ("tn", "dq", "q", "tau", "st"):
            W[k] *= 5.0
        for k in ("d_tau", "d_tn", "d_dq", "d_q"):
            W[k] = min(W[k] * 2.0, C.D_CAP[k])
        sigma, budget = 0.08, ESC_BUDGET
        print(f"  → 감사 미통과: 가중치 ×5, δ ×2 (r{rnd + 1})", flush=True)

    z = lb + np.clip(xcur, 0.0, 1.0) * (ub - lb)
    q0 = [float(z[0]), float(z[1])]
    h = TW.apex_of(L)
    stats = TW.stats_of(tw, L, t_push=TW.T_END)
    g1, g2, dg1, dg2 = knots["grids"]
    tl = L["t"]
    extra = dict(
        h_plan=h, q0=np.array(q0), clip_raw=TW.CLIP_RAW, knot_t=knots["knot_t"],
        qd1=np.interp(np.clip(tl, 0.0, TW.T_END), C.TG, g1),
        qd2=np.interp(np.clip(tl, 0.0, TW.T_END), C.TG, g2),
        dqd1=np.where((tl >= 0) & (tl <= TW.T_END),
                      np.interp(np.clip(tl, 0.0, TW.T_END), C.TG, dg1), 0.0),
        dqd2=np.where((tl >= 0) & (tl <= TW.T_END),
                      np.interp(np.clip(tl, 0.0, TW.T_END), C.TG, dg2), 0.0),
        knots_qd1=knots["knots_qd1"], knots_qd2=knots["knots_qd2"],
        gains=np.array(GAIN))
    TW.save_npz(HERE / f"t0nc_cl_{TAG}.npz", L, extra=extra)
    audit_doc = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method=f"t0nc_cl_{TAG}_cma",
        note=("CL-CMA 순수 PD 배포용 재최적 — ★클립=배포와 동일한 하드웨어 천장 35.5, "
              "15Nm은 클립이 아닌 페널티(W_tau=200)로만 강제. 명령이 â≤15인 곳에 자연히 "
              "머물러 배포(클립 35.5)가 그대로 재현 (기존 t0nc_cl은 클립 25.581 리라이언스라 "
              "배포 시 20~23Nm 터짐). AVT task0 제약 그대로. 기존 t0nc_cl 불변."),
        gain=list(GAIN), h_plan=float(h), audit=aud, stance_s=float(ts),
        stance_limit=T0.T_ST_MAX, stance_pass=bool(ts <= T0.T_ST_MAX + 1e-6),
        q0_rad=q0, q0_deg=[float(np.degrees(a)) for a in q0], stats=stats,
        evals=nfev[0], crashes=ncrash[0], rounds=rounds, clip_raw=float(TW.CLIP_RAW),
        h_ref_cl500=0.9772, seed_trial=list(tw["seed_trial"]),
        npz=f"t0nc_cl_{TAG}.npz",
        params={k: np.asarray(v).tolist() for k, v in knots.items() if k != "grids"},
        wall_s=float(time.time() - t0))
    safe.atomic_json_write(HERE / f"t0nc_cl_{TAG}_audit.json", audit_doc)
    print(f"\nh_plan={h:.4f} m  stance={ts:.3f}s  "
          f"q0=({np.degrees(q0[0]):.1f}°,{np.degrees(q0[1]):.1f}°)  게인 {GAIN}", flush=True)
    print("audit: " + "  ".join(f"{k}={v:+.4f}" for k, v in aud.items() if k != "pass")
          + f"  PASS={aud['pass']}", flush=True)
    print(f"saved t0nc_cl_{TAG}.npz + audit  [{(time.time() - t0) / 60:.1f}m, evals={nfev[0]}]",
          flush=True)


if __name__ == "__main__":
    safe.utf8_console()
    optimize()
