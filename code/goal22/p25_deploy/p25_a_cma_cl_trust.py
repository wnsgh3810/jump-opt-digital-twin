# -*- coding: utf-8 -*-
"""p25_a_cma_cl_trust — P25 Phase A (iii-T): 폐루프 인식 q_des CMA + 트러스트 리전.

p25_a_cma_cl의 복사-변형. 동일 골든 배선(p25_a_twin) · 동일 g_high PD(150/2.2/500/4) ·
동일 스플라인 파라미터화(8매듭/관절, 매듭0 고정, dim 14) 위에, cl_cma 해(h=1.517)가
쓴 "트윈 신뢰구간 밖" 전략(다중 바운스 펌핑 + dq 외삽)을 하드 페널티로 봉쇄:

  (a) dq 트러스트: 관절속도를 측정 지지구간(p25_a_results.json dq_support_measured)
      +10% 마진(구간폭 기준 — ENV_MARGIN 규약 동형) 안으로. 위반 적분 [rad] ×
      TRUST_DQ_W.
  (b) 단일 접촉위상: 최초 이지(연속 공중 >20 ms 성립) 이후 apex 이전 재접촉
      (= 바운스 펌핑·드롭-캐치)을 GRF(>1 N 접촉 판정, stats_of 규약)로 검출,
      재접촉 체공시간 [s] × BOUNCE_W. 최적점에서 잔차 ~0 이어야 함.
  (c) 관절 포락선 +10% 소프트 페널티(PEN_W)·클립 ±35.5 천장은 원본과 동일.

산출: p25_a_clt.npz (Phase D 스캔 규약 p25_[abc]_*.npz — save_npz 공통 스키마 +
qd/dqd/knots) + p25_a_res_clt.json (h_plan · stats · 페널티 잔차 · 사용 dq 한계).
p25_a_results.json은 건드리지 않음 (append-safe — 별도 파일).

멀티스타트: `python p25_a_cma_cl_trust.py [meas|clcma]` — meas(기본) = 0602 측정
desired 시드, clcma = 무제약 cl_cma 최적 매듭(p25_a_results.json methods.cl_cma) 시드
(페널티가 트러스트 리전 안으로 끌어당김). 저장은 기존 p25_a_res_clt.json h_plan보다
좋을 때만 덮어씀 (베스트 유지 — 멀티스타트 안전).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")   # 동시 작업 배려 — import 전 설정

import p25_a_twin as TW          # env 플래그는 TW import가 설정

import sys
import time
from pathlib import Path

import numpy as np
import cma
from scipy.interpolate import CubicSpline

import safe

HERE = Path(__file__).parent
NK = 8
KT_ = np.linspace(0.0, TW.T_END, NK)
MAXFEVALS = 3000
POPSIZE = 16
SIGMA0 = 0.15                     # rad
TRUST_DQ_W = 50.0                 # dq 지지구간 위반 적분 페널티 [1/rad]
BOUNCE_W = 200.0                  # 재접촉 체공시간 페널티 [1/s]
AIR_MIN_S = 0.02                  # "공중" 성립 최소 지속 [s]
GRF_CONTACT = 1.0                 # 접촉 판정 [N] (stats_of t_liftoff 규약 동형)
TG = None


def dq_limits():
    """p25_a_results.json의 dq_support_measured를 +10% (구간폭) 확장."""
    res = safe.read_json(HERE / "p25_a_results.json")
    sup = res["dq_support_measured"]

    def _widen(b):
        lo, hi = float(b[0]), float(b[1])
        m = 0.10 * (hi - lo)
        return lo - m, hi + m

    return dict(dq1=_widen(sup["dq1"]), dq2=_widen(sup["dq2"]))


def trust_pen(tw, Lg, lim):
    """(dq 위반 적분 [rad], 재접촉 체공 [s], 재접촉 샘플수). t>=0 창 기준.
    재접촉 = 최초 '연속 공중 >= AIR_MIN_S' 성립 이후 ~ apex 사이의 접촉 샘플."""
    dt = tw["dt"]
    m = Lg["t"] >= 0
    p_dq = 0.0
    for key in ("dq1", "dq2"):
        lo, hi = lim[key]
        v = Lg[key][m]
        p_dq += float(np.sum(np.maximum(v - hi, 0.0) + np.maximum(lo - v, 0.0))) * dt
    contact = Lg["grf"][m] > GRF_CONTACT
    k_apex = int(np.argmax(Lg["bz"][m]))
    air_n = max(int(round(AIR_MIN_S / dt)), 1)
    n_re = 0
    k, N, k_q = 0, len(contact), None
    while k < N:                                  # 최초 유자격 공중 스트레치 탐색
        if contact[k]:
            k += 1
            continue
        j = k
        while j < N and not contact[j]:
            j += 1
        if j - k >= air_n:
            k_q = k + air_n                       # 공중 20 ms 성립 시점
            break
        k = j
    if k_q is not None and k_q < k_apex:
        n_re = int(np.sum(contact[k_q:k_apex + 1]))
    return p_dq, n_re * dt, n_re


def qd_grids(free, q0):
    """자유 매듭 14 → (qd1g, qd2g, dqd1g, dqd2g) 그리드 (dqd = 스플라인 도함수)."""
    k1 = np.concatenate([[q0[0]], free[:NK - 1]])
    k2 = np.concatenate([[q0[1]], free[NK - 1:]])
    s1 = CubicSpline(KT_, k1, bc_type="natural")
    s2 = CubicSpline(KT_, k2, bc_type="natural")
    return s1(TG), s2(TG), s1(TG, 1), s2(TG, 1)


def main():
    safe.utf8_console()
    global TG
    seed_mode = sys.argv[1] if len(sys.argv) > 1 else "meas"
    assert seed_mode in ("meas", "clcma"), f"seed_mode={seed_mode}"
    t0 = time.time()
    print("=== p25_a_cma_cl_trust — 트러스트 리전 폐루프 q_des CMA "
          f"(g_high 150/2.2/500/4, seed={seed_mode}) ===", flush=True)
    lim = dq_limits()
    print(f"dq trust(+10%): dq1=[{lim['dq1'][0]:.2f}, {lim['dq1'][1]:.2f}]  "
          f"dq2=[{lim['dq2'][0]:.2f}, {lim['dq2'][1]:.2f}] rad/s", flush=True)
    tw = TW.twin()
    print(f"init [{time.time() - t0:.0f}s] dt={tw['dt']}", flush=True)
    TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    q0 = tw["q0"]
    e = tw["env"]
    lo = np.array([e["q1"][0]] * (NK - 1) + [e["q2"][0]] * (NK - 1))
    hi = np.array([e["q1"][1]] * (NK - 1) + [e["q2"][1]] * (NK - 1))

    if seed_mode == "clcma":
        # 시드: 무제약 cl_cma 최적 매듭 (지지 밖 전략 — 페널티가 안으로 끌어당김)
        p = safe.read_json(HERE / "p25_a_results.json")["methods"]["cl_cma"]["params"]
        assert np.allclose(p["knot_t"], KT_), "cl_cma knot_t 불일치"
        seed1 = np.asarray(p["knots_qd1"][1:], float)
        seed2 = np.asarray(p["knots_qd2"][1:], float)
    else:
        # 시드: 0602 측정 desired 궤적 (|dq2| 피크를 0.3 s 지점에 정렬) — 원본 동일
        d0 = tw["d0"]; t = d0["t"]
        tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
        ts = tp - 0.3
        seed1 = np.interp(ts + KT_[1:], t, d0["qd1"])
        seed2 = np.interp(ts + KT_[1:], t, d0["qd2"])
    x0 = np.clip(np.concatenate([seed1, seed2]), lo + 1e-6, hi - 1e-6)

    nfev = [0]; ncrash = [0]

    def f(x):
        nfev[0] += 1
        g1, g2, dg1, dg2 = qd_grids(np.asarray(x, float), q0)
        Lg = TW.rollout_cl(tw, TG, g1, g2, dg1, dg2, TW.G_HIGH,
                           alphas=(1, 1, 1, 1), t_end=TW.T_END, record=True)
        if Lg is None:
            ncrash[0] += 1
            return TW.CRASH_F
        p_dq, p_bnc, _ = trust_pen(tw, Lg, lim)
        return (-TW.apex_of(Lg) + TW.PEN_W * TW.env_pen(tw, Lg)
                + TRUST_DQ_W * p_dq + BOUNCE_W * p_bnc)

    f0 = f(x0)
    print(f"seed f={f0:.4f}", flush=True)

    es = cma.CMAEvolutionStrategy(
        x0, SIGMA0,
        dict(bounds=[list(lo), list(hi)], popsize=POPSIZE, maxfevals=MAXFEVALS,
             seed=3, verbose=-1))
    while not es.stop():
        X = es.ask()
        es.tell(X, [f(x) for x in X])
        if es.countiter % 25 == 0:
            print(f"  it {es.countiter:4d}  nfev {nfev[0]:5d}  "
                  f"best f={es.result.fbest:.4f}  [{time.time() - t0:.0f}s]", flush=True)
    xb = np.asarray(es.result.xbest, float)
    fb = float(es.result.fbest)
    print(f"CMA done: nfev={nfev[0]} crash={ncrash[0]} best f={fb:.4f} "
          f"[{time.time() - t0:.0f}s]", flush=True)

    g1, g2, dg1, dg2 = qd_grids(xb, q0)
    Lg = TW.rollout_cl(tw, TG, g1, g2, dg1, dg2, TW.G_HIGH,
                       alphas=(1, 1, 1, 1), t_end=TW.T_END, record=True)
    h_plan = TW.apex_of(Lg)
    stats = TW.stats_of(tw, Lg, t_push=TW.T_END)
    p_dq, p_bnc, n_re = trust_pen(tw, Lg, lim)
    mpos = Lg["t"] >= 0
    t_apex = float(Lg["t"][mpos][int(np.argmax(Lg["bz"][mpos]))])
    print(f"h_plan={h_plan:.4f} m  peak raw=({stats['peak_raw1']:.1f}, "
          f"{stats['peak_raw2']:.1f})  peak dq=({stats['peak_dq1']:.1f}, "
          f"{stats['peak_dq2']:.1f})  ceil_frac=({stats['ceil_frac_raw1']:.2f}, "
          f"{stats['ceil_frac_raw2']:.2f})", flush=True)
    print(f"trust residuals: pen_dq={p_dq:.3e} rad  retouch={p_bnc * 1000:.1f} ms "
          f"({n_re} samples)  env_pen={stats['env_pen']:.3e} rad*s", flush=True)

    # 베스트 유지: 기존 산출물이 더 높으면 덮어쓰지 않음 (멀티스타트 안전)
    res_path = HERE / "p25_a_res_clt.json"
    if res_path.exists():
        prev = safe.read_json(res_path)
        if float(prev.get("h_plan", -1)) >= h_plan:
            print(f"기존 베스트 유지 (prev h_plan={prev['h_plan']:.4f} >= "
                  f"{h_plan:.4f}) — 저장 생략 [{(time.time() - t0) / 60:.1f}m]",
                  flush=True)
            return

    # qd/dqd를 로그 시간축(settle 포함)으로 확장 저장 (t<0 = 시작값, t>0.6 = 유지)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, TW.T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= TW.T_END),
                      np.interp(np.clip(tl, 0.0, TW.T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    TW.save_npz(HERE / "p25_a_clt.npz", Lg,
                extra=dict(qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
                           knot_t=KT_,
                           knots_qd1=np.concatenate([[q0[0]], xb[:NK - 1]]),
                           knots_qd2=np.concatenate([[q0[1]], xb[NK - 1:]]),
                           gains=np.array(TW.G_HIGH)))
    safe.atomic_json_write(HERE / "p25_a_res_clt.json", dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="cl_cma_trust",
        note="트러스트 리전 폐루프 q_des CMA — cl_cma 동일 배선 + 하드 페널티: "
             "dq 측정지지+10% (TRUST_DQ_W=50/rad) + 단일 접촉위상 (공중>20ms 후 "
             "apex 전 재접촉, BOUNCE_W=200/s) + 포락선 PEN_W=10; "
             "g_high=150/2.2/500/4, alphas=1, clip 35.5",
        h_plan=h_plan, stats=stats,
        trust=dict(dq_limits=dict(dq1=list(lim["dq1"]), dq2=list(lim["dq2"])),
                   dq_margin="dq_support_measured 구간폭 +10% 양측",
                   pen_dq_resid=p_dq, retouch_s=p_bnc, retouch_samples=n_re,
                   env_pen_resid=stats["env_pen"], t_apex=t_apex,
                   weights=dict(TRUST_DQ_W=TRUST_DQ_W, BOUNCE_W=BOUNCE_W,
                                PEN_W=TW.PEN_W),
                   air_min_s=AIR_MIN_S, grf_contact_N=GRF_CONTACT),
        evals=nfev[0], crashes=ncrash[0],
        crash_rate=ncrash[0] / max(nfev[0], 1), f_best=fb, f_seed=float(f0),
        seed_mode=seed_mode, gains=list(TW.G_HIGH),
        params=dict(knot_t=[float(a) for a in KT_],
                    knots_qd1=[float(a) for a in np.concatenate([[q0[0]], xb[:NK - 1]])],
                    knots_qd2=[float(a) for a in np.concatenate([[q0[1]], xb[NK - 1:]])]),
        seed_trial=list(tw["seed_trial"]), npz="p25_a_clt.npz",
        wall_s=float(time.time() - t0)))
    print(f"saved p25_a_clt.npz + p25_a_res_clt.json [{(time.time() - t0) / 60:.1f}m]",
          flush=True)


if __name__ == "__main__":
    main()
