# -*- coding: utf-8 -*-
"""t0wc_polish — CL 해의 감사 미세위반 사영 폴리시 (t0wc_cma 보조).

용도: CMA 최종해가 q 바운드를 머리카락 두께(~1e-3 rad)로 넘는 경우 — 페널티 기울기가
apex 대비 너무 작아 CMA가 못 지우는 구조적 잔여물. 원리: 실현 q가 바운드를 넘은 만큼
(+버퍼) q_des 매듭을 바운드 안쪽으로 캡 → 재롤아웃 → 재감사 (최대 8회, 버퍼 점증).
apex 변화는 ~mm 규모 (사영량이 mrad 규모). 산출은 동일 파일명으로 덮어씀 (npz+audit).

사용: python t0wc_polish.py cl li20
"""
import sys

import numpy as np

import t0wc_cma as W          # env 플래그/클립은 t0wc_cma import가 설정
import t0_spec as T0
import safe

BUF0 = 0.002                  # 사영 버퍼 [rad] (반복마다 +50%)


def polish_cl(li_key):
    W.setup()
    l_i, _ = W.LIS[li_key]
    aj = safe.read_json(W.HERE / f"t0wc_cl_{li_key}_audit.json")
    p = aj["params"]
    k1 = np.asarray(p["knots_qd1"], float)
    k2 = np.asarray(p["knots_qd2"], float)
    model, _, _ = W.model_cvt(l_i)
    dt = float(model.opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    from scipy.interpolate import CubicSpline

    def grids(k1, k2):
        s1 = CubicSpline(W.KT_CL, k1, bc_type="natural")
        s2 = CubicSpline(W.KT_CL, k2, bc_type="natural")
        return s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)

    # 사영 = 평가 그리드 클립 (스플라인 매듭-사이 오버슛 + 동적 오버슛 모두 커버).
    # 클립 레벨을 위반량+버퍼만큼 반복적으로 조임. 클립 구간은 dqd=0 (일관 쌍 유지).
    cap = {"q1_lo": T0.Q1_LB, "q1_hi": T0.Q1_UB, "q2_lo": T0.QM_LB, "q2_hi": T0.QM_UB}
    buf = BUF0
    Lg = None
    for it in range(10):
        g1, g2, dg1, dg2 = grids(k1, k2)
        c1m = (g1 <= cap["q1_lo"]) | (g1 >= cap["q1_hi"])
        c2m = (g2 <= cap["q2_lo"]) | (g2 >= cap["q2_hi"])
        g1 = np.clip(g1, cap["q1_lo"], cap["q1_hi"]); dg1 = np.where(c1m, 0.0, dg1)
        g2 = np.clip(g2, cap["q2_lo"], cap["q2_hi"]); dg2 = np.where(c2m, 0.0, dg2)
        Lg = W.rollout_cl(l_i, TG, g1, g2, dg1, dg2, W.GAINS,
                          alphas=(1, 1, 1, 1), record=True)
        assert Lg is not None, "polish 롤아웃 발산"
        aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
        bad = {k: v for k, v in aud.items() if k != "pass" and v > 1e-6}
        print(f"[polish cl/{li_key}] it {it}  h={W.apex_of(Lg):.4f}  "
              f"pass={aud['pass']}  viol={ {k: round(v, 5) for k, v in bad.items()} }  "
              f"cap={ {k: round(v, 4) for k, v in cap.items()} }",
              flush=True)
        if aud["pass"]:
            break
        # q 바운드 위반 → 해당 방향 클립 레벨을 (위반량+버퍼)만큼 안쪽으로
        if aud["q1_hi"] > 0:
            cap["q1_hi"] -= aud["q1_hi"] + buf
        if aud["q1_lo"] > 0:
            cap["q1_lo"] += aud["q1_lo"] + buf
        if aud["q2_hi"] > 0:
            cap["q2_hi"] -= aud["q2_hi"] + buf
        if aud["q2_lo"] > 0:
            cap["q2_lo"] += aud["q2_lo"] + buf
        # 그 외 위반(tau/TN/dq)은 사영 대상 아님 — 남아 있으면 실패로 종료
        if not any(k.startswith("q") for k in bad):
            raise SystemExit(f"polish 불가 위반 잔존: {bad}")
        buf *= 1.5
    # 저장 (run_cl 산출 규약 동일 — 동일 파일명 덮어씀)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, W.T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= W.T_END),
                      np.interp(np.clip(tl, 0.0, W.T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    params = dict(
        npz_extra=dict(qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
                       knot_t=W.KT_CL, knots_qd1=k1, knots_qd2=k2,
                       gains=np.array(W.GAINS)),
        json_params=dict(knot_t=[float(a) for a in W.KT_CL],
                         knots_qd1=[float(a) for a in k1],
                         knots_qd2=[float(a) for a in k2],
                         qd_grid_caps={k: float(v) for k, v in cap.items()}))
    meta = dict(evals=aj.get("evals"), crashes=aj.get("crashes"),
                f_best=aj.get("f_best"), esc_final=aj.get("esc_final"),
                note=aj.get("note", "") + " + 감사 사영 폴리시 (q_des 매듭 바운드 캡)",
                polish=dict(iters=it + 1, h_before=aj.get("h_plan"),
                            buf_final=buf),
                wall_s=aj.get("wall_s"))
    xb = np.concatenate([k1, k2])
    W.save_all("t0wc", "cl", li_key, Lg, xb, params, meta)


def lin_viol(aud):
    """감사 마진의 선형 위반합 — 서브-mrad 위반에도 유효한 기울기 (제곱합의 맹점 보정)."""
    return float(sum(max(0.0, v) for k, v in aud.items() if k != "pass"))


def polish_ol(li_key, budget=1000, K=1000.0):
    """OL 해 폴리시 — 선형 감사 페널티 단거리 CMA (현 최적해 시드, 좁은 스텝).
    근거: CMA 본선의 제곱합 페널티는 위반 ~3e-4 rad에서 기울기 ~1e-5로 apex 잡음에
    묻힘 → 선형항 K·Σmax(0,마진) (K=1000 → 0.3 규모)이 mm 규모 apex와 교환 가능."""
    from scipy.interpolate import CubicSpline
    import cma
    import p19_run as R19
    W.setup()
    l_i, _ = W.LIS[li_key]
    aj = safe.read_json(W.HERE / f"t0wc_ol_{li_key}_audit.json")
    p = aj["params"]
    x0 = np.concatenate([np.asarray(p["q0"], float),
                         np.asarray(p["knots_raw1"], float)[:W.NK_OL - 1],
                         np.asarray(p["knots_raw2"], float)[:W.NK_OL - 1]])
    model, _, _ = W.model_cvt(l_i)
    dt = float(model.opt.timestep)
    TG = np.arange(0.0, W.T_END + dt, dt)
    lo = np.array([T0.Q1_LB + W.Q0_MARGIN, T0.QM_LB + W.Q0_MARGIN]
                  + [-R19.CLIP] * (2 * (W.NK_OL - 1)))
    hi = np.array([T0.Q1_UB - W.Q0_MARGIN, T0.QM_UB - W.Q0_MARGIN]
                  + [R19.CLIP] * (2 * (W.NK_OL - 1)))

    def raw_grid(free):
        k1 = np.append(free[:W.NK_OL - 1], 0.0)
        k2 = np.append(free[W.NK_OL - 1:], 0.0)
        s1 = CubicSpline(W.KT_OL, k1, bc_type="natural")
        s2 = CubicSpline(W.KT_OL, k2, bc_type="natural")
        r1 = np.where(TG <= W.T_PUSH, s1(np.minimum(TG, W.T_PUSH)), 0.0)
        r2 = np.where(TG <= W.T_PUSH, s2(np.minimum(TG, W.T_PUSH)), 0.0)
        return r1, r2

    def roll(x, record=False):
        r1, r2 = raw_grid(x[2:])
        return W.rollout_ol(l_i, TG, r1, r2, (float(x[0]), float(x[1])),
                            record=record)

    def f(x):
        Lg = roll(np.asarray(x, float))
        if Lg is None:
            return W.CRASH_F
        aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
        return (-W.apex_of(Lg) + T0.penalty(Lg, t_end=W.T_END, cvt=True)
                + W.tau_pen(Lg) + K * lin_viol(aud))
    print(f"[polish ol/{li_key}] seed f={f(x0):.4f} (h before={aj['h_plan']:.4f})",
          flush=True)
    es = cma.CMAEvolutionStrategy(
        list(x0), 0.5,
        dict(bounds=[list(lo), list(hi)], popsize=16, maxfevals=budget,
             seed=71, verbose=-1,
             CMA_stds=[0.02, 0.04] + [2.0] * (2 * (W.NK_OL - 1))))
    while not es.stop():
        X = es.ask()
        es.tell(X, [f(x) for x in X])
    xb = np.asarray(es.result.xbest, float)
    Lg = roll(xb, record=True)
    aud = T0.audit(Lg, t_end=W.T_END, cvt=True)
    print(f"[polish ol/{li_key}] done f={es.result.fbest:.4f} "
          f"h={W.apex_of(Lg):.4f} pass={aud['pass']} "
          f"viol={ {k: round(v, 6) for k, v in aud.items() if k != 'pass' and v > 1e-6} }",
          flush=True)
    params = dict(
        npz_extra=dict(knot_t=W.KT_OL,
                       knots_raw1=np.append(xb[2:2 + W.NK_OL - 1], 0.0),
                       knots_raw2=np.append(xb[2 + W.NK_OL - 1:], 0.0),
                       q0=np.array([xb[0], xb[1]])),
        json_params=dict(q0=[float(xb[0]), float(xb[1])],
                         knot_t=[float(a) for a in W.KT_OL],
                         knots_raw1=[float(a) for a in np.append(xb[2:2 + W.NK_OL - 1], 0.0)],
                         knots_raw2=[float(a) for a in np.append(xb[2 + W.NK_OL - 1:], 0.0)]))
    meta = dict(evals=aj.get("evals"), crashes=aj.get("crashes"),
                f_best=float(es.result.fbest), esc_final=aj.get("esc_final"),
                note=aj.get("note", "") + f" + 선형감사 폴리시 (K={K:g}, {budget}ev)",
                polish=dict(kind="linear_audit_cma", K=K, budget=budget,
                            h_before=aj.get("h_plan")),
                wall_s=aj.get("wall_s"))
    W.save_all("t0wc", "ol", li_key, Lg, xb, params, meta)
    return bool(aud["pass"])


if __name__ == "__main__":
    mode, key = sys.argv[1], sys.argv[2]
    if mode == "cl":
        polish_cl(key)
    else:
        ok = polish_ol(key)
        if not ok:
            ok = polish_ol(key, budget=1500, K=10000.0)
        assert ok, "OL polish 실패 — 감사 위반 잔존"
