# -*- coding: utf-8 -*-
"""t0nc_cma — P25-task0 캠페인: AVT task0 제약으로 트윈(no_cvt, l_i=30 flip) 점프 재최적화.

제약 = t0_spec (사용자 지시 07-18 — AVT LEG task0_vertjump_no_cvt.py 포팅본, 재정의 금지):
  |τ̂| ≤ 15 Nm · T-N 포락선 |dq| ≤ −0.731·|τ̂|+48.48 · |dq| ≤ 50 · q 박스
  (q1 ∈ [−72°,−17°], q2 ∈ [−146°,−36°]) · 스탠스 ≤ 0.3 s · 시작 자세 q0 자유(결정변수).

배선 = p25_deploy/p25_a_twin (골든 검증된 rollout_ol/rollout_cl 미러 — import만).
공급 클립 = env P25_CLIP_RAW=25.5810 (t0_spec.RAW15; â 운동방향 가지 정확히 15.00 Nm,
â(25.5810, mot)=14.99998 ≤ 15 → 클립 라이딩이 감사 tau를 넘지 않음).

목적: minimize f = −apex + t0_spec.penalty(L) + extra_pen(L)  (crash → CRASH_F).
extra_pen = 스크립트 보충 페널티 (t0_spec 정의 변경 아님 — 감사 엄격통과 보장용):
  (a) tau 15Nm 전 가지 — raw 클립은 운동방향 가지만 15Nm, 반대방향 순간 â(25.581,opp)=17.34
      (t0_spec.penalty에 tau 항 없음 → 보충 필수; t18 캠페인 strict 사영과 같은 원인)
  (b) 한계 −δ 안쪽 유도 (soft 페널티 평형이 경계 위 미세위반으로 남는 것 방지; 감사 tol 1e-6)
  (c) 스탠스 ≤ 0.3 s (t0_spec.T_ST_MAX — audit() dict엔 없어 여기서 강제·보고)
감사 실패 시 가중치 ×5 + δ ×2 로 xbest 이어달리기 (t0_spec 기본 가중치에서 시작 — 지시 준수).

모드: golden (기본클립 35.5로 기존 p25_a_res_{ol,cl}.json 재현 — 배선 증명) | ol | cl.
파라미터화 (기존 p25_a_cma_{ol,cl} 구조 재사용 + q0 2차원 추가, [0,1] 정규화 공간 CMA):
  ol: [q1_0, q2_0] + raw 매듭 8×2 (9매듭/관절 linspace(0,0.35), 끝매듭 0 고정) — dim 18.
      평가마다 settle_state(tw, q1_0, q2_0) 재계산 (0.4 s — q0가 결정변수라 캐시 불가).
  cl: [q1_0, q2_0] + q_des 매듭 7×2 (8매듭/관절 linspace(0,0.6), 매듭0=q0 연동) — dim 16.
      매듭 바운드 = t0_spec q 박스 (kp2=500이라 0.05 rad 오차로 클립 포화 — 권위 손실 없음).
      게인 = G_HIGH (150/2.2/500/4), dq_des = 스플라인 도함수. settle은 rollout_cl 내장.

산출: t0nc_{ol,cl}.npz (save_npz 스키마 + h_plan + q0 (+cl: qd/dqd) + knots) +
      t0nc_{ol,cl}_audit.json (t0_spec.audit 전 항목 + 스탠스 + q0 + eval 수 + t18 대비).
"""
import os
import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "golden"
assert MODE in ("golden", "ol", "cl"), f"usage: t0nc_cma.py [golden|ol|cl] (got {MODE})"
os.environ["PYTHONIOENCODING"] = "utf-8"
if MODE != "golden":
    os.environ["P25_CLIP_RAW"] = "25.5810"     # = t0_spec.RAW15 (import 전 필수)

from pathlib import Path

HERE = Path(__file__).parent
DEPLOY = HERE.parent / "p25_deploy"
sys.path.insert(0, str(DEPLOY))

import p25_a_twin as TW      # env 플래그 + repo 경로 주입 (반드시 첫 repo-import)
import t0_spec as T0

import time

import numpy as np
import cma
from scipy.interpolate import CubicSpline

import safe

NKO = 9                                  # ol 매듭/관절 (끝매듭 0 고정)
KTO = np.linspace(0.0, TW.T_PUSH, NKO)
NKC = 8                                  # cl 매듭/관절 (매듭0 = q0 연동)
KTC = np.linspace(0.0, TW.T_END, NKC)
POPSIZE = 16
SIGMA0 = 0.2                             # 정규화 공간
BUDGET = dict(ol=4500, cl=3600)
ESC_BUDGET = 1600                        # 가중치 상향 라운드 예산
MAX_ROUNDS = 3
REF_T18 = dict(ol=1.1482612761294173, cl=1.3881113499391244)   # 18Nm 캠페인 h_plan
TG = None

# 페널티 가중치·마진 (t0_spec 기본값에서 시작 — 지시; 감사 실패 시 ×5 / δ×2)
W0 = dict(tn=50.0, dq=50.0, q=500.0,     # t0_spec.penalty 인자
          tau=50.0, st=50.0,             # 보충: tau 전 가지 / 스탠스
          d_tau=0.05, d_tn=0.3, d_dq=0.3, d_q=0.003)   # 안쪽 유도 마진
D_CAP = dict(d_tau=0.2, d_tn=1.2, d_dq=1.2, d_q=0.012)


def stance_of(L):
    """스탠스 시간 [s] = apex 이전 마지막 접지(grf>1N) 시각. stats_of의 t_liftoff는
    초기 언로딩 딥(t≈0.02 grf<1N 순간)을 잡는 오검출 → apex 역행 정의로 대체."""
    m = L["t"] >= 0
    t = L["t"][m]; grf = L["grf"][m]; bz = L["bz"][m]
    ia = int(np.argmax(bz))
    idx = np.where(grf[:ia + 1] > 1.0)[0]
    return float(t[idx[-1]]) if len(idx) else 0.0


def extra_pen(L, W):
    """보충 페널티 (docstring (a)(b)(c)). 제곱+0.3·선형 (경계 기울기 소멸 방지)."""
    m = (L["t"] >= 0) & (L["t"] <= TW.T_END)
    n = max(int(m.sum()), 1)

    def hp(exc, w):
        e = np.maximum(0.0, np.asarray(exc, float))
        return w * float(np.sum(e * e + 0.3 * e)) / n

    p = 0.0
    for sh in (L["sh1"][m], L["sh2"][m]):
        p += hp(np.abs(sh) - (15.0 - W["d_tau"]), W["tau"])
    for dq, sh in ((L["dq1"][m], L["sh1"][m]), (L["dq2"][m], L["sh2"][m])):
        p += hp(T0.tn_gap(dq, sh) + W["d_tn"], W["tn"])
        p += hp(np.abs(dq) - (T0.DQ_LIM - W["d_dq"]), W["dq"])
    for q, lb, ub in ((L["q1"][m], T0.Q1_LB, T0.Q1_UB), (L["q2"][m], T0.Q2_LB, T0.Q2_UB)):
        p += hp((lb + W["d_q"]) - q, W["q"]) + hp(q - (ub - W["d_q"]), W["q"])
    e_st = max(0.0, stance_of(L) - (T0.T_ST_MAX - 0.005))
    p += W["st"] * (e_st * e_st + 0.3 * e_st)
    return p


def fval(L, W):
    if L is None:
        return TW.CRASH_F
    return (-TW.apex_of(L) + T0.penalty(L, t_end=TW.T_END, cvt=False,
                                        w_tn=W["tn"], w_dq=W["dq"], w_q=W["q"])
            + extra_pen(L, W))


# ══════════════ 파라미터화 (물리 z ↔ 정규화 x) ══════════════
def bounds(mode):
    if mode == "ol":
        lb = np.array([T0.Q1_LB, T0.Q2_LB] + [-T0.RAW15] * (2 * (NKO - 1)))
        ub = np.array([T0.Q1_UB, T0.Q2_UB] + [T0.RAW15] * (2 * (NKO - 1)))
    else:
        lb = np.array([T0.Q1_LB, T0.Q2_LB] + [T0.Q1_LB] * (NKC - 1) + [T0.Q2_LB] * (NKC - 1))
        ub = np.array([T0.Q1_UB, T0.Q2_UB] + [T0.Q1_UB] * (NKC - 1) + [T0.Q2_UB] * (NKC - 1))
    return lb, ub


def roll_ol(tw, z):
    q1_0, q2_0 = float(z[0]), float(z[1])
    try:
        st = TW.settle_state(tw, q1_0, q2_0)
    except Exception:
        return None, None
    k1 = np.append(z[2:2 + NKO - 1], 0.0)
    k2 = np.append(z[2 + NKO - 1:], 0.0)
    s1 = CubicSpline(KTO, k1, bc_type="natural")
    s2 = CubicSpline(KTO, k2, bc_type="natural")
    r1 = np.where(TG <= TW.T_PUSH, s1(np.minimum(TG, TW.T_PUSH)), 0.0)
    r2 = np.where(TG <= TW.T_PUSH, s2(np.minimum(TG, TW.T_PUSH)), 0.0)
    L = TW.rollout_ol(tw, TG, r1, r2, st, t_end=TW.T_END, record=True)
    return L, dict(knot_t=KTO, knots_raw1=k1, knots_raw2=k2)


def roll_cl(tw, z):
    k1 = np.concatenate([[z[0]], z[2:2 + NKC - 1]])
    k2 = np.concatenate([[z[1]], z[2 + NKC - 1:]])
    s1 = CubicSpline(KTC, k1, bc_type="natural")
    s2 = CubicSpline(KTC, k2, bc_type="natural")
    g1, g2, dg1, dg2 = s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)
    L = TW.rollout_cl(tw, TG, g1, g2, dg1, dg2, TW.G_HIGH, alphas=(1, 1, 1, 1),
                      t_end=TW.T_END, record=True)
    return L, dict(knot_t=KTC, knots_qd1=k1, knots_qd2=k2, grids=(g1, g2, dg1, dg2))


def seed_x0(mode, tw, lb, ub):
    """시드: t18 캠페인 최적해 매듭을 새 바운드로 사영 (+q0 = 0602 측정을 박스로 사영).
    t18 파일 부재 시 0602 측정 raw/qd 리샘플 (기존 스크립트 시드 규약)."""
    q1s = float(np.clip(tw["q0"][0], T0.Q1_LB + 2e-3, T0.Q1_UB - 2e-3))
    q2s = float(np.clip(tw["q0"][1], T0.Q2_LB + 2e-3, T0.Q2_UB - 2e-3))
    d0 = tw["d0"]; t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    if mode == "ol":
        src = DEPLOY / "p25_a_res_ol_t18.json"
        if src.exists():
            p = safe.read_json(src)["params"]
            kk = np.array(p["knots_raw1"][:NKO - 1] + p["knots_raw2"][:NKO - 1])
            tag = src.name
        else:
            ts_ = tp - TW.T_PUSH * 0.85
            kk = np.concatenate([np.interp(ts_ + KTO[:-1], t, d0["traw1"]),
                                 np.interp(ts_ + KTO[:-1], t, d0["traw2"])])
            tag = "0602 측정 raw"
        kk = np.clip(kk, -(T0.RAW15 - 1e-3), T0.RAW15 - 1e-3)
    else:
        src = DEPLOY / "p25_a_res_cl_t18.json"
        if src.exists():
            p = safe.read_json(src)["params"]
            kk = np.array(p["knots_qd1"][1:] + p["knots_qd2"][1:])
            q1s = float(np.clip(p["knots_qd1"][0], T0.Q1_LB + 2e-3, T0.Q1_UB - 2e-3))
            q2s = float(np.clip(p["knots_qd2"][0], T0.Q2_LB + 2e-3, T0.Q2_UB - 2e-3))
            tag = src.name
        else:
            ts_ = tp - 0.3
            kk = np.concatenate([np.interp(ts_ + KTC[1:], t, d0["qd1"]),
                                 np.interp(ts_ + KTC[1:], t, d0["qd2"])])
            tag = "0602 측정 qd"
        kk[:NKC - 1] = np.clip(kk[:NKC - 1], T0.Q1_LB + 1e-3, T0.Q1_UB - 1e-3)
        kk[NKC - 1:] = np.clip(kk[NKC - 1:], T0.Q2_LB + 1e-3, T0.Q2_UB - 1e-3)
    z = np.concatenate([[q1s, q2s], kk])
    print(f"seed: {tag} 사영  q0=({q1s:.4f}, {q2s:.4f}) rad", flush=True)
    return (z - lb) / (ub - lb)


# ══════════════ 골든 (배선 재현 — 기본 클립 35.5) ══════════════
def golden():
    assert abs(TW.CLIP_RAW - 35.5) < 1e-9, "golden은 P25_CLIP_RAW 미설정으로 실행"
    global TG
    tw = TW.twin()
    TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    out = {}
    # OL 재현
    r = safe.read_json(DEPLOY / "p25_a_res_ol.json")
    kt = np.array(r["params"]["knot_t"])
    s1 = CubicSpline(kt, np.array(r["params"]["knots_raw1"]), bc_type="natural")
    s2 = CubicSpline(kt, np.array(r["params"]["knots_raw2"]), bc_type="natural")
    r1 = np.where(TG <= TW.T_PUSH, s1(np.minimum(TG, TW.T_PUSH)), 0.0)
    r2 = np.where(TG <= TW.T_PUSH, s2(np.minimum(TG, TW.T_PUSH)), 0.0)
    st = TW.settle_state(tw, *tw["q0"])
    L = TW.rollout_ol(tw, TG, r1, r2, st, t_end=TW.T_END, record=True)
    h = TW.apex_of(L)
    out["ol"] = dict(h=h, ref=r["h_plan"], diff=abs(h - r["h_plan"]))
    print(f"[golden ol] h={h:.10f} ref={r['h_plan']:.10f} diff={out['ol']['diff']:.3e}",
          flush=True)
    # CL 재현
    r = safe.read_json(DEPLOY / "p25_a_res_cl.json")
    kt = np.array(r["params"]["knot_t"])
    s1 = CubicSpline(kt, np.array(r["params"]["knots_qd1"]), bc_type="natural")
    s2 = CubicSpline(kt, np.array(r["params"]["knots_qd2"]), bc_type="natural")
    L = TW.rollout_cl(tw, TG, s1(TG), s2(TG), s1(TG, 1), s2(TG, 1), TW.G_HIGH,
                      alphas=(1, 1, 1, 1), t_end=TW.T_END, record=True)
    h = TW.apex_of(L)
    out["cl"] = dict(h=h, ref=r["h_plan"], diff=abs(h - r["h_plan"]))
    print(f"[golden cl] h={h:.10f} ref={r['h_plan']:.10f} diff={out['cl']['diff']:.3e}",
          flush=True)
    ok = out["ol"]["diff"] < 1e-9 and out["cl"]["diff"] < 1e-9
    out["pass"] = bool(ok)
    safe.atomic_json_write(HERE / "t0nc_golden.json",
                           dict(gen=time.strftime("%Y-%m-%d %H:%M"), clip_raw=35.5, **out))
    print(f"golden {'PASS' if ok else 'FAIL'} — saved t0nc_golden.json", flush=True)
    assert ok


# ══════════════ 최적화 본체 ══════════════
def optimize(mode):
    global TG
    t0 = time.time()
    assert abs(TW.CLIP_RAW - T0.RAW15) < 1e-9 and abs(TW.CLIP_RAW - 25.5810) < 1e-9
    tw = TW.twin()
    TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    lb, ub = bounds(mode)
    roll = roll_ol if mode == "ol" else roll_cl
    W = dict(W0)
    nfev = [0]; ncrash = [0]

    def f(x):
        nfev[0] += 1
        z = lb + np.clip(np.asarray(x, float), 0.0, 1.0) * (ub - lb)
        L, _ = roll(tw, z)
        if L is None:
            ncrash[0] += 1
            return TW.CRASH_F
        return fval(L, W)

    x0 = seed_x0(mode, tw, lb, ub)
    f0 = f(x0)
    print(f"=== t0nc {mode} — clip ±{TW.CLIP_RAW} (15Nm 등가), dim {len(lb)} ===", flush=True)
    print(f"seed f={f0:.4f}", flush=True)

    xcur, sigma, budget = x0, SIGMA0, BUDGET[mode]
    rounds = []
    L = knots = aud = None; ts = float("nan")
    for rnd in range(MAX_ROUNDS):
        es = cma.CMAEvolutionStrategy(
            xcur, sigma,
            dict(bounds=[0.0, 1.0], popsize=POPSIZE, maxfevals=budget,
                 seed=11 + rnd, verbose=-1))
        while not es.stop():
            X = es.ask()
            es.tell(X, [f(x) for x in X])
            if es.countiter % 25 == 0:
                print(f"  r{rnd} it {es.countiter:4d}  nfev {nfev[0]:5d}  "
                      f"best f={es.result.fbest:.4f}  [{time.time() - t0:.0f}s]", flush=True)
        xcur = np.asarray(es.result.xbest, float)
        z = lb + np.clip(xcur, 0.0, 1.0) * (ub - lb)
        L, knots = roll(tw, z)
        assert L is not None, "최적해 롤아웃 발산"
        aud = T0.audit(L, t_end=TW.T_END, cvt=False)
        ts = stance_of(L)
        h = TW.apex_of(L)
        ok = aud["pass"] and ts <= T0.T_ST_MAX + 1e-6
        worst = max((v, k) for k, v in aud.items() if k != "pass")
        rounds.append(dict(round=rnd, budget=budget, f_best=float(es.result.fbest),
                           h=float(h), audit_pass=bool(aud["pass"]), stance=float(ts),
                           worst=[worst[1], float(worst[0])], W=dict(W)))
        print(f"round {rnd}: h={h:.4f} stance={ts:.3f} audit_pass={aud['pass']} "
              f"worst={worst[1]}:{worst[0]:+.4f}  [{time.time() - t0:.0f}s]", flush=True)
        if ok:
            break
        for k in ("tn", "dq", "q", "tau", "st"):
            W[k] *= 5.0
        for k in ("d_tau", "d_tn", "d_dq", "d_q"):
            W[k] = min(W[k] * 2.0, D_CAP[k])
        sigma, budget = 0.08, ESC_BUDGET
        print(f"  → 감사 미통과: 가중치 ×5, δ ×2 (r{rnd + 1})", flush=True)

    # 최종 산출
    z = lb + np.clip(xcur, 0.0, 1.0) * (ub - lb)
    q0 = [float(z[0]), float(z[1])]
    h = TW.apex_of(L)
    stats = TW.stats_of(tw, L, t_push=(TW.T_PUSH if mode == "ol" else TW.T_END))
    extra = dict(h_plan=h, q0=np.array(q0), clip_raw=T0.RAW15,
                 knot_t=knots["knot_t"])
    if mode == "ol":
        extra.update(knots_raw1=knots["knots_raw1"], knots_raw2=knots["knots_raw2"])
    else:
        g1, g2, dg1, dg2 = knots["grids"]
        tl = L["t"]
        extra.update(
            qd1=np.interp(np.clip(tl, 0.0, TW.T_END), TG, g1),
            qd2=np.interp(np.clip(tl, 0.0, TW.T_END), TG, g2),
            dqd1=np.where((tl >= 0) & (tl <= TW.T_END),
                          np.interp(np.clip(tl, 0.0, TW.T_END), TG, dg1), 0.0),
            dqd2=np.where((tl >= 0) & (tl <= TW.T_END),
                          np.interp(np.clip(tl, 0.0, TW.T_END), TG, dg2), 0.0),
            knots_qd1=knots["knots_qd1"], knots_qd2=knots["knots_qd2"],
            gains=np.array(TW.G_HIGH))
    TW.save_npz(HERE / f"t0nc_{mode}.npz", L, extra=extra)
    audit_doc = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method=f"t0nc_{mode}_cma",
        note=("AVT task0 제약 (t0_spec) — 15Nm 등가 클립 25.5810 + T-N/dq50/q박스 페널티 "
              "+ 보충(tau 전 가지·마진·스탠스), q0 자유"),
        h_plan=float(h), audit=aud, stance_s=float(ts), stance_limit=T0.T_ST_MAX,
        stance_pass=bool(ts <= T0.T_ST_MAX + 1e-6),
        q0_rad=q0, q0_deg=[float(np.degrees(a)) for a in q0],
        stats=stats, evals=nfev[0], crashes=ncrash[0], rounds=rounds,
        clip_raw=T0.RAW15, weights_final=dict(W),
        h_ref_t18=REF_T18[mode], dh_vs_t18=float(h - REF_T18[mode]),
        seed_trial=list(tw["seed_trial"]), npz=f"t0nc_{mode}.npz",
        params={k: np.asarray(v).tolist() for k, v in knots.items() if k != "grids"},
        wall_s=float(time.time() - t0))
    safe.atomic_json_write(HERE / f"t0nc_{mode}_audit.json", audit_doc)
    print(f"h_plan={h:.4f} m  (t18 {REF_T18[mode]:.4f} → Δ{100 * (h - REF_T18[mode]):+.1f}cm)  "
          f"stance={ts:.3f}s  q0=({np.degrees(q0[0]):.1f}°, {np.degrees(q0[1]):.1f}°)",
          flush=True)
    print(f"audit: " + "  ".join(f"{k}={v:+.4f}" for k, v in aud.items() if k != "pass")
          + f"  PASS={aud['pass']}", flush=True)
    print(f"saved t0nc_{mode}.npz + t0nc_{mode}_audit.json "
          f"[{(time.time() - t0) / 60:.1f}m, evals={nfev[0]}]", flush=True)


def main():
    safe.utf8_console()
    if MODE == "golden":
        golden()
    else:
        optimize(MODE)


if __name__ == "__main__":
    main()
