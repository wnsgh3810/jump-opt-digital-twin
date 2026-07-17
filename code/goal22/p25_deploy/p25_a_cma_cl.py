# -*- coding: utf-8 -*-
"""p25_a_cma_cl — P25 Phase A (iii): 폐루프 인식 (q_des, dq_des) 최적화.

배포 그 자체를 목적화: 후보 (q_des(t), dq_des(t))를 트윈 폐루프 PD 러너
(rollout_cl = cl_run23 비트 미러, 골든 ② 증명)로 굴리고 그 apex를 직접 최대화.
게인 = g_high (150, 2.2, 500, 4) = 실기 폴더 라벨 규약 (kp1, kd1, kp2, kd2 =
hip_kp, hip_kd, knee_kp, knee_kd — cl_run23 gains 튜플과 동일 순서),
alphas=[1,1,1,1], 클립 ±35.5 (R19.CLIP), 측정 관례 부호 (러너 내장).

파라미터: q_des = 관절별 3차 스플라인 (CubicSpline natural), 매듭 8개,
매듭시각 = linspace(0, 0.6, 8). 매듭0 = 시작 웅크림 q(0602 측정) 고정 (settle
목표와 연속 — 초기 PD 킥 방지) → 자유 매듭 7개/관절, 차원 14.
dq_des = q_des 스플라인의 해석적 도함수 (일관 쌍 — 배포 CSV 규약).
t>0.6 s: cl_run23 규약 (마지막 q_des 유지 추종 — 비행 중 접촉 없음 → apex 불변).

목적: minimize f = −apex + PEN_W·(실현 q 포락선 위반 적분) (crash → CRASH_F).
매듭 바운드 = 방문 포락선 +10%. 시드 = 0602 측정 qd(desired) 푸시 정렬 리샘플.
CMA popsize 16, ~3200 evals.

산출: p25_a_cl_cma.npz (공통 스키마 + qd/dqd 트레이스 + knots) + p25_a_res_cl.json.
"""
import p25_a_twin as TW          # env 플래그는 TW import가 설정

import time
from pathlib import Path

import numpy as np
import cma
from scipy.interpolate import CubicSpline

import safe

HERE = Path(__file__).parent
NK = 8
KT_ = np.linspace(0.0, TW.T_END, NK)
MAXFEVALS = 3200
POPSIZE = 16
SIGMA0 = 0.15                     # rad
TG = None


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
    t0 = time.time()
    print("=== p25_a_cma_cl — 폐루프 인식 q_des CMA (g_high 150/2.2/500/4) ===", flush=True)
    tw = TW.twin()
    print(f"init [{time.time() - t0:.0f}s] dt={tw['dt']}", flush=True)
    TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    q0 = tw["q0"]
    e = tw["env"]
    lo = np.array([e["q1"][0]] * (NK - 1) + [e["q2"][0]] * (NK - 1))
    hi = np.array([e["q1"][1]] * (NK - 1) + [e["q2"][1]] * (NK - 1))

    # 시드: 0602 측정 desired 궤적 (|dq2| 피크를 0.3 s 지점에 정렬)
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
                           alphas=(1, 1, 1, 1), t_end=TW.T_END)
        if Lg is None:
            ncrash[0] += 1
            return TW.CRASH_F
        return -TW.apex_of(Lg) + TW.PEN_W * TW.env_pen(tw, Lg)

    f0 = f(x0)
    print(f"seed f={f0:.4f} (apex~{-f0:.3f}m)", flush=True)

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
    print(f"h_plan={h_plan:.4f} m  peak raw=({stats['peak_raw1']:.1f}, "
          f"{stats['peak_raw2']:.1f})  peak dq=({stats['peak_dq1']:.1f}, "
          f"{stats['peak_dq2']:.1f})  ceil_frac=({stats['ceil_frac_raw1']:.2f}, "
          f"{stats['ceil_frac_raw2']:.2f})", flush=True)

    # qd/dqd를 로그 시간축(settle 포함)으로 확장 저장 (t<0 = 시작값, t>0.6 = 유지)
    tl = Lg["t"]
    qd_l = [np.interp(np.clip(tl, 0.0, TW.T_END), TG, g) for g in (g1, g2)]
    dqd_l = [np.where((tl >= 0) & (tl <= TW.T_END),
                      np.interp(np.clip(tl, 0.0, TW.T_END), TG, dg), 0.0)
             for dg in (dg1, dg2)]
    TW.save_npz(HERE / "p25_a_cl_cma.npz", Lg,
                extra=dict(qd1=qd_l[0], qd2=qd_l[1], dqd1=dqd_l[0], dqd2=dqd_l[1],
                           knot_t=KT_,
                           knots_qd1=np.concatenate([[q0[0]], xb[:NK - 1]]),
                           knots_qd2=np.concatenate([[q0[1]], xb[NK - 1:]]),
                           gains=np.array(TW.G_HIGH)))
    safe.atomic_json_write(HERE / "p25_a_res_cl.json", dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="cl_cma",
        note="폐루프 인식 q_des 스플라인 CMA (8매듭/관절, 매듭0=시작자세 고정, dim 14; "
             "dq_des=도함수; g_high=150/2.2/500/4, alphas=1, clip 35.5)",
        h_plan=h_plan, stats=stats, evals=nfev[0], crashes=ncrash[0],
        crash_rate=ncrash[0] / max(nfev[0], 1), f_best=fb, f_seed=float(f0),
        gains=list(TW.G_HIGH),
        params=dict(knot_t=[float(a) for a in KT_],
                    knots_qd1=[float(a) for a in np.concatenate([[q0[0]], xb[:NK - 1]])],
                    knots_qd2=[float(a) for a in np.concatenate([[q0[1]], xb[NK - 1:]])]),
        seed_trial=list(tw["seed_trial"]), npz="p25_a_cl_cma.npz",
        wall_s=float(time.time() - t0)))
    print(f"saved p25_a_cl_cma.npz + p25_a_res_cl.json [{(time.time() - t0) / 60:.1f}m]",
          flush=True)


if __name__ == "__main__":
    main()
