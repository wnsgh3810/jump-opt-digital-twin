# -*- coding: utf-8 -*-
"""t0wc_liopt — P25-task0 with_cvt 추가 임무 (사용자 지시 07-18): l_i도 최적화 대상.

① l_i 자유 최적화: CMA 결정벡터에 l_i ∈ [10, 30] mm 1축 추가 (AVT task0_with_cvt와
   동일 바운드). CL·OL 각각, 기존 li2508 최적해 warm-start. 제약·감사·에스컬레이션은
   t0_spec(cvt=True) 규약 그대로 + 서브-mrad 맹점용 선형 감사 라운드 (t0wc_polish 검증 기법).
   ★ 정정 노트: cl_run23의 l_i 인자는 qpos_from_crank/rtab용 런타임 인자지만 모델
   지오메트리(크랭크 길이·커플러 부착)는 빌드 시 굳음 → l_i를 0.05 mm로 양자화해
   모델/rtab 캐시 (W.model_cvt가 키별 1회 빌드). l_i* 해상도 = 0.05 mm.
   4절 브랜치 가드: AVT J=dq2/dqm ≤ −0.05 → 전달비 r(모델좌표) ≤ −0.05 소프트 페널티
   (r_guard 마진을 audit json에 병기; 폐쇄솔버/역학 발산은 crash 처리 기존 그대로).
② h(l_i) 프로파일: l_i ∈ {12,15,18,20,22,23,24,25.08,26,27,28,30} 고정-l_i CL 재최적화
   스윕 (이웃 warm-start, 축소 예산) → t0wc_li_sweep.json + t0wc_li_curve.png
   (검증 앵커 25.08/30 세로선, AVT 해석모델 최적 25.161 mm 참조선, l_i<25.08 외삽 음영).
③ 정직 규약: CVT 층(C_CVT |r|≤0.2 캡·게이트 스프링)은 l_i=25.08에서 fit —
   validity = "interpolation" ([25.08, 30], 양끝 실측 검증: 0429 CVT / 무변속 세션) |
   "extrapolation" (<25.08). extrapolated 플래그 = l_i < 25.08.

산출: t0wc_cl_liopt.npz/_audit.json · t0wc_ol_liopt.npz/_audit.json ·
t0wc_li_sweep.json · t0wc_li_curve.png. 커밋 금지.
"""
import t0wc_cma as W          # env 플래그 4종 + 클립(RAW15) + 경로는 W import가 설정

import json
import sys
import time
from pathlib import Path

import numpy as np
import cma
from scipy.interpolate import CubicSpline

import p19_run as R19
import p23_v6_runners as RU
import t0_spec as T0
import safe

HERE = Path(__file__).parent
LI_LB_MM, LI_UB_MM = 10.0, 30.0
LI_Q_MM = 0.05                 # l_i 양자화 [mm] (모델/rtab 캐시 키 해상도)
LI_FIT_MM = 25.08              # CVT 층 fit 지점 (0429 실측 검증)
AVT_OPT_MM = 25.161            # AVT 해석모델 최적 (참조선)
R_GUARD = -0.05                # AVT J_branch_ub — r(모델좌표) ≤ −0.05
W_R = 50.0
SWEEP_LIS = [12.0, 15.0, 18.0, 20.0, 22.0, 23.0, 24.0, 25.08, 26.0, 27.0, 28.0, 30.0]

# 라운드 스케줄: (esc, K_lin, budget, sigma) — 제곱합 에스컬레이션 → 선형 감사 마감
ROUNDS_CL = [(1.0, 0.0, 3200, 1.0), (10.0, 0.0, 1200, 0.4), (100.0, 0.0, 1200, 0.3),
             (100.0, 1000.0, 1200, 0.25), (100.0, 10000.0, 1500, 0.2)]
ROUNDS_OL = [(1.0, 0.0, 4000, 1.0), (10.0, 0.0, 1200, 0.4), (100.0, 0.0, 1200, 0.3),
             (100.0, 1000.0, 1200, 0.25), (100.0, 10000.0, 1500, 0.2)]
ROUNDS_SW = [(1.0, 0.0, 1000, 0.3), (10.0, 0.0, 600, 0.15),
             (100.0, 1000.0, 600, 0.1), (100.0, 10000.0, 800, 0.08)]


def quant_mm(li_mm):
    """0.05 mm 격자 양자화 + fit 앵커(25.08) 스냅 — 격자에 25.08이 없으므로
    |l_i−25.08| ≤ 격자/2 셀은 정확히 25.08로 (검증점 재현성; 스모크에서 발견한 함정)."""
    li_mm = float(np.clip(li_mm, LI_LB_MM, LI_UB_MM))
    if abs(li_mm - LI_FIT_MM) <= LI_Q_MM / 2:
        return LI_FIT_MM
    return float(np.clip(round(round(li_mm / LI_Q_MM) * LI_Q_MM, 5),
                         LI_LB_MM, LI_UB_MM))


def li_m(li_mm):
    return round(quant_mm(li_mm) / 1000.0, 6)


def validity(li_mm):
    return "extrapolation" if li_mm < LI_FIT_MM - 1e-9 else "interpolation"


def r_guard_stats(Lg, l_i):
    """(제곱위반 평균, r_max) — 커맨드 창, r ≤ −0.05 가드 (AVT J_branch_ub)."""
    qs, rs = RU.rtab(round(float(l_i), 6))
    m = (Lg["t"] >= 0) & (Lg["t"] <= W.T_END)
    rr = np.interp(-Lg["q2"][m], qs, rs)
    v = np.maximum(0.0, rr - R_GUARD)
    return float(np.sum(v ** 2)) / max(m.sum(), 1), float(rr.max())


def lin_viol(aud, rg_margin):
    return float(sum(max(0.0, v) for k, v in aud.items() if k != "pass")
                 + max(0.0, rg_margin))


def objective(Lg, l_i, esc, K_lin):
    if Lg is None:
        return W.CRASH_F
    rsq, rmax = r_guard_stats(Lg, l_i)
    f = (-W.apex_of(Lg)
         + T0.penalty(Lg, t_end=W.T_END, cvt=True,
                      w_tn=50.0 * esc, w_dq=50.0 * esc, w_q=500.0 * esc)
         + W.tau_pen(Lg, esc=esc) + W_R * esc * rsq)
    if K_lin > 0:
        aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
        f += K_lin * lin_viol(aud, rmax - R_GUARD)
    return f


def save_liopt(method, Lg, li_mm, xb, params_json, npz_extra, meta):
    """save_all 미러 — l_i 자유값 판 (파일 접미 liopt, validity 명기)."""
    aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
    _, rmax = r_guard_stats(Lg, li_m(li_mm))
    h_plan = W.apex_of(Lg)
    st = W.stats_of(Lg)
    stance = st["t_liftoff"]
    rmin, rmax2 = W.r_range_of(Lg, li_m(li_mm))
    bz0 = float(np.interp(0.0, Lg["t"], Lg["bz"]))
    extrap = li_mm < LI_FIT_MM - 1e-9
    npz = HERE / f"t0wc_{method}_liopt.npz"
    d = dict(t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             raw1=Lg["raw1"], raw2=Lg["raw2"], tau1_nm=Lg["sh1"], tau2_nm=Lg["sh2"],
             bz=Lg["bz"], grf=Lg["grf"], h_plan=h_plan, qm=Lg["q2"], l_i=li_mm,
             extrapolated=float(extrap))
    d.update(npz_extra)
    np.savez(npz, **d)
    out = dict(gen=time.strftime("%Y-%m-%d %H:%M"), method=method + "_liopt",
               l_i_mm=li_mm, l_i_quant_mm=LI_Q_MM, extrapolated=bool(extrap),
               validity=validity(li_mm),
               validity_note=("CVT 층(C_CVT |r|<=0.2 캡·게이트 스프링)은 l_i=25.08 fit. "
                              "[25.08,30]=양끝 검증 내삽 (0429 CVT/무변속 세션), "
                              "<25.08=외삽 (참고용)"),
               clip_raw=float(R19.CLIP),
               gains=(list(W.GAINS) if method == "cl" else None),
               audit={k: (bool(v) if k == "pass" else float(v))
                      for k, v in aud.items()},
               r_guard=dict(bound=R_GUARD, r_max=rmax, margin=rmax - R_GUARD,
                            ok=bool(rmax - R_GUARD <= 1e-6)),
               h_plan=h_plan, bz_settle=bz0, h_rise=h_plan - bz0,
               stance_s=stance,
               stance_ok=(bool(stance <= T0.T_ST_MAX) if np.isfinite(stance) else False),
               r_range=[rmin, rmax2], stats=st, params=params_json,
               npz=npz.name, **meta)
    safe.atomic_json_write(HERE / f"t0wc_{method}_liopt_audit.json", out)
    print(f"[{method}/liopt] l_i*={li_mm:.2f}mm  h_plan={h_plan:.4f} m "
          f"(rise {h_plan - bz0:.4f})  stance={stance:.3f}s  "
          f"audit_pass={aud['pass']}  r_guard_ok={out['r_guard']['ok']}  "
          f"({validity(li_mm)})", flush=True)
    return out


# ══════════════ ① l_i 자유 최적화 ══════════════
def run_liopt_cl():
    W.setup()
    aj = safe.read_json(HERE / "t0wc_cl_li2508_audit.json")
    p = aj["params"]
    dt = float(W.model_cvt(li_m(LI_FIT_MM))[0].opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    x0 = np.concatenate([[LI_FIT_MM], np.asarray(p["knots_qd1"], float),
                         np.asarray(p["knots_qd2"], float)])
    lo = np.array([LI_LB_MM] + [T0.Q1_LB] * W.NK_CL + [T0.QM_LB] * W.NK_CL)
    hi = np.array([LI_UB_MM] + [T0.Q1_UB] * W.NK_CL + [T0.QM_UB] * W.NK_CL)
    stds = [1.0] + [0.15] * (2 * W.NK_CL)

    def grids(x):
        s1 = CubicSpline(W.KT_CL, x[1:1 + W.NK_CL], bc_type="natural")
        s2 = CubicSpline(W.KT_CL, x[1 + W.NK_CL:], bc_type="natural")
        return s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)

    def roll(x, record=False):
        l_i = li_m(float(x[0]))
        g1, g2, dg1, dg2 = grids(x)
        try:
            return W.rollout_cl(l_i, TG, g1, g2, dg1, dg2, W.GAINS,
                                alphas=(1, 1, 1, 1), record=record), l_i
        except Exception:
            return None, l_i

    best = _rounds(x0, lo, hi, stds, ROUNDS_CL, roll, "cl/liopt")
    xb, Lg = best["x"], best["Lg"]
    li_mm = quant_mm(float(xb[0]))
    g1, g2, dg1, dg2 = grids(xb)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, W.T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= W.T_END),
                      np.interp(np.clip(tl, 0.0, W.T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    return save_liopt(
        "cl", Lg, li_mm, xb,
        dict(knot_t=[float(a) for a in W.KT_CL],
             knots_qd1=[float(a) for a in xb[1:1 + W.NK_CL]],
             knots_qd2=[float(a) for a in xb[1 + W.NK_CL:]]),
        dict(qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
             knot_t=W.KT_CL, knots_qd1=xb[1:1 + W.NK_CL],
             knots_qd2=xb[1 + W.NK_CL:], gains=np.array(W.GAINS)),
        dict(evals=best["evals"], f_best=best["f"], rounds=best["rounds"],
             warm_start="t0wc_cl_li2508",
             note="CL q_des 스플라인 + l_i 1축 CMA (dim 17, l_i∈[10,30]mm 양자화 "
                  f"{LI_Q_MM}mm; r≤−0.05 브랜치 가드 페널티)", wall_s=best["wall"]))


def run_liopt_ol():
    W.setup()
    aj = safe.read_json(HERE / "t0wc_ol_li2508_audit.json")
    p = aj["params"]
    dt = float(W.model_cvt(li_m(LI_FIT_MM))[0].opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    x0 = np.concatenate([[LI_FIT_MM], np.asarray(p["q0"], float),
                         np.asarray(p["knots_raw1"], float)[:W.NK_OL - 1],
                         np.asarray(p["knots_raw2"], float)[:W.NK_OL - 1]])
    lo = np.array([LI_LB_MM, T0.Q1_LB + W.Q0_MARGIN, T0.QM_LB + W.Q0_MARGIN]
                  + [-R19.CLIP] * (2 * (W.NK_OL - 1)))
    hi = np.array([LI_UB_MM, T0.Q1_UB - W.Q0_MARGIN, T0.QM_UB - W.Q0_MARGIN]
                  + [R19.CLIP] * (2 * (W.NK_OL - 1)))
    stds = [1.0, 0.05, 0.08] + [4.0] * (2 * (W.NK_OL - 1))

    def raw_grid(x):
        k1 = np.append(x[3:3 + W.NK_OL - 1], 0.0)
        k2 = np.append(x[3 + W.NK_OL - 1:], 0.0)
        s1 = CubicSpline(W.KT_OL, k1, bc_type="natural")
        s2 = CubicSpline(W.KT_OL, k2, bc_type="natural")
        r1 = np.where(TG <= W.T_PUSH, s1(np.minimum(TG, W.T_PUSH)), 0.0)
        r2 = np.where(TG <= W.T_PUSH, s2(np.minimum(TG, W.T_PUSH)), 0.0)
        return r1, r2

    def roll(x, record=False):
        l_i = li_m(float(x[0]))
        r1, r2 = raw_grid(x)
        try:
            return W.rollout_ol(l_i, TG, r1, r2, (float(x[1]), float(x[2])),
                                record=record), l_i
        except Exception:
            return None, l_i

    best = _rounds(x0, lo, hi, stds, ROUNDS_OL, roll, "ol/liopt")
    xb, Lg = best["x"], best["Lg"]
    li_mm = quant_mm(float(xb[0]))
    return save_liopt(
        "ol", Lg, li_mm, xb,
        dict(q0=[float(xb[1]), float(xb[2])],
             knot_t=[float(a) for a in W.KT_OL],
             knots_raw1=[float(a) for a in np.append(xb[3:3 + W.NK_OL - 1], 0.0)],
             knots_raw2=[float(a) for a in np.append(xb[3 + W.NK_OL - 1:], 0.0)]),
        dict(knot_t=W.KT_OL, knots_raw1=np.append(xb[3:3 + W.NK_OL - 1], 0.0),
             knots_raw2=np.append(xb[3 + W.NK_OL - 1:], 0.0),
             q0=np.array([xb[1], xb[2]])),
        dict(evals=best["evals"], f_best=best["f"], rounds=best["rounds"],
             warm_start="t0wc_ol_li2508",
             note="OL raw 스플라인 + 시작자세 + l_i 1축 CMA (dim 19; r≤−0.05 "
                  "브랜치 가드 페널티)", wall_s=best["wall"]))


def _rounds(x0, lo, hi, stds, sched, roll, label):
    """에스컬레이션+선형 라운드 실행기 — (t0_spec 감사 ∧ r가드) 통과 최고 h 해 추적."""
    t0 = time.time()
    tot = 0
    rounds_log = []
    best_pass = None          # (h, x, Lg)
    x_cur = np.asarray(x0, float)
    xb = x_cur; Lg_last = None
    for i, (esc, K_lin, budget, sig) in enumerate(sched):
        def f(x):
            Lg, l_i = roll(np.asarray(x, float))
            return objective(Lg, l_i, esc, K_lin)
        es = cma.CMAEvolutionStrategy(
            list(x_cur), sig,
            dict(bounds=[list(lo), list(hi)], popsize=W.POPSIZE,
                 maxfevals=budget, seed=101 + i, verbose=-1,
                 CMA_stds=list(stds)))
        while not es.stop():
            X = es.ask()
            es.tell(X, [f(x) for x in X])
        tot += es.result.evaluations
        xb = np.asarray(es.result.xbest, float)
        Lg, l_i = roll(xb, record=True)
        assert Lg is not None, f"{label} round {i}: 최적해 발산"
        Lg_last = Lg
        aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
        _, rmax = r_guard_stats(Lg, l_i)
        ok = aud["pass"] and (rmax - R_GUARD <= 1e-6)
        h = W.apex_of(Lg)
        rounds_log.append(dict(round=i, esc=esc, K_lin=K_lin, budget=budget,
                               f=float(es.result.fbest), h=float(h),
                               audit_pass=bool(aud["pass"]),
                               r_guard_margin=float(rmax - R_GUARD),
                               li_mm=quant_mm(float(xb[0]))))
        print(f"  {label} round {i} esc={esc:g} K={K_lin:g}: h={h:.4f} "
              f"li={quant_mm(float(xb[0])):.2f} pass={aud['pass']} "
              f"rg={rmax - R_GUARD:+.4f} [{time.time() - t0:.0f}s]", flush=True)
        if ok and (best_pass is None or h > best_pass[0]):
            best_pass = (h, xb.copy(), Lg)
        if ok and i >= 1:      # 통과해를 확보한 뒤 최소 1회 정련이면 종료
            break
        x_cur = xb
    if best_pass is not None:
        h, xb, Lg_last = best_pass
    return dict(x=xb, Lg=Lg_last, f=rounds_log[-1]["f"], evals=tot,
                rounds=rounds_log, wall=float(time.time() - t0))


# ══════════════ ② h(l_i) 스윕 (고정 l_i CL 재최적화) ══════════════
def run_sweep():
    W.setup()
    dt = float(W.model_cvt(li_m(LI_FIT_MM))[0].opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    aj = safe.read_json(HERE / "t0wc_cl_li2508_audit.json")
    p0 = aj["params"]
    x_seed = np.concatenate([np.asarray(p0["knots_qd1"], float),
                             np.asarray(p0["knots_qd2"], float)])
    lo = np.array([T0.Q1_LB] * W.NK_CL + [T0.QM_LB] * W.NK_CL)
    hi = np.array([T0.Q1_UB] * W.NK_CL + [T0.QM_UB] * W.NK_CL)
    stds = [0.15] * (2 * W.NK_CL)

    def make_roll(li_mm):
        l_i = li_m(li_mm)

        def grids(x):
            s1 = CubicSpline(W.KT_CL, x[:W.NK_CL], bc_type="natural")
            s2 = CubicSpline(W.KT_CL, x[W.NK_CL:], bc_type="natural")
            return s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)

        def roll(x, record=False):
            g1, g2, dg1, dg2 = grids(x)
            try:
                return W.rollout_cl(l_i, TG, g1, g2, dg1, dg2, W.GAINS,
                                    alphas=(1, 1, 1, 1), record=record), l_i
            except Exception:
                return None, l_i
        return roll

    # 스윕 순서: 25.08에서 위로 → 25.08에서 아래로 (이웃 warm-start 연쇄)
    ups = [x for x in SWEEP_LIS if x >= LI_FIT_MM]
    downs = [x for x in sorted(SWEEP_LIS, reverse=True) if x < LI_FIT_MM]
    rows = {}
    seeds = {LI_FIT_MM: x_seed}
    t00 = time.time()
    for chain in (ups, downs):
        x_prev = x_seed
        for li_mm in chain:
            roll = make_roll(li_mm)
            best = _rounds(x_prev, lo, hi, stds, ROUNDS_SW, roll,
                           f"sweep/{li_mm:g}")
            xb, Lg = best["x"], best["Lg"]
            aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
            _, rmax = r_guard_stats(Lg, li_m(li_mm))
            st = W.stats_of(Lg)
            rows[f"{li_mm:g}"] = dict(
                l_i_mm=li_mm, h_plan=float(W.apex_of(Lg)),
                h_rise=float(W.apex_of(Lg) - np.interp(0.0, Lg["t"], Lg["bz"])),
                stance_s=st["t_liftoff"],
                audit_pass=bool(aud["pass"]),
                audit={k: (bool(v) if k == "pass" else float(v))
                       for k, v in aud.items()},
                r_guard_margin=float(rmax - R_GUARD),
                r_guard_ok=bool(rmax - R_GUARD <= 1e-6),
                validity=validity(li_mm), evals=best["evals"],
                rounds=best["rounds"],
                knots_qd1=[float(a) for a in xb[:W.NK_CL]],
                knots_qd2=[float(a) for a in xb[W.NK_CL:]])
            seeds[li_mm] = xb
            x_prev = xb
            print(f"[sweep] l_i={li_mm:g}mm  h={rows[f'{li_mm:g}']['h_plan']:.4f}  "
                  f"pass={aud['pass']}  rg_ok={rows[f'{li_mm:g}']['r_guard_ok']}  "
                  f"[{time.time() - t00:.0f}s]", flush=True)
            safe.atomic_json_write(HERE / "t0wc_li_sweep.json", dict(
                gen=time.strftime("%Y-%m-%d %H:%M"),
                note="고정-l_i CL 재최적화 스윕 (이웃 warm-start, r≤−0.05 가드 포함; "
                     "t0_spec(cvt=True) 감사)", clip_raw=float(R19.CLIP),
                gains=list(W.GAINS), li_fit_mm=LI_FIT_MM, avt_opt_mm=AVT_OPT_MM,
                rows=rows))
    return rows


# ══════════════ ③ 곡선 (색 명시 금지 — auto cycle/기본값만) ══════════════
def make_curve():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sw = safe.read_json(HERE / "t0wc_li_sweep.json")["rows"]
    lis = sorted(float(v["l_i_mm"]) for v in sw.values())
    hs = [sw[f"{x:g}"]["h_plan"] for x in lis]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(lis, hs, marker="o", label="fixed-l_i CL re-opt (twin)")
    for name, mk in (("cl", "*"), ("ol", "^")):
        try:
            d = safe.read_json(HERE / f"t0wc_{name}_liopt_audit.json")
            ax.plot([d["l_i_mm"]], [d["h_plan"]], marker=mk, markersize=14,
                    linestyle="none",
                    label=f"{name.upper()} free-l_i opt: {d['l_i_mm']:.2f} mm, "
                          f"{d['h_plan']:.3f} m")
        except Exception:
            pass
    ax.axvline(LI_FIT_MM, linestyle="--", alpha=0.7,
               label="verified anchor 25.08 (0429 CVT)")
    ax.axvline(30.0, linestyle="--", alpha=0.4,
               label="verified anchor 30 (no-CVT sessions)")
    ax.axvline(AVT_OPT_MM, linestyle=":",
               label="AVT analytic opt 25.161")
    ax.axvspan(LI_LB_MM, LI_FIT_MM, alpha=0.10,
               label="extrapolation zone (CVT layer fit @25.08)")
    ax.set_xlabel("l_i [mm]")
    ax.set_ylabel("h_plan (base-z apex) [m]")
    ax.set_title("task0 with_cvt (15 Nm): jump apex vs CVT link length l_i")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(HERE / "t0wc_li_curve.png", dpi=150)
    print("saved t0wc_li_curve.png", flush=True)


def main():
    safe.utf8_console()
    t0 = time.time()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    W.setup()
    if stage in ("all", "cl"):
        run_liopt_cl()
    if stage in ("all", "ol"):
        run_liopt_ol()
    if stage in ("all", "sweep"):
        run_sweep()
    if stage in ("all", "curve", "sweep"):
        make_curve()
    print(f"DONE [{(time.time() - t0) / 60:.1f} min]", flush=True)


if __name__ == "__main__":
    main()
