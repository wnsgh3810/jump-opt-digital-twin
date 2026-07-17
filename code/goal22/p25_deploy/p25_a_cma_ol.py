# -*- coding: utf-8 -*-
"""p25_a_cma_ol — P25 Phase A (i): 개루프 토크 스플라인 CMA-ES.

파라미터: 관절별 raw 토크 프로파일 = 3차 스플라인 (CubicSpline, natural BC),
매듭 9개/관절, 매듭시각 = linspace(0, 0.35, 9). 마지막 매듭은 0 고정 (푸시 끝
연속 소멸 — "0.35 s push + zero after") → 자유 매듭 8개/관절, 차원 16.
커맨드 체인 = 배포와 동일 (tm 필터 → 클립 ±35.5 → ahat → 플랜트 전 층;
rollout_ol이 cl_run23 커맨드 층 미러). 스플라인이 매듭 사이에서 ±35.5를 넘어도
체인 클립이 천장을 강제 (천장 라이딩 허용 — G20 헤드룸 예상).

목적: minimize f = −apex + PEN_W·(포락선 위반 적분) (crash → CRASH_F).
시드: 0602 첫 trial 측정 raw 푸시 구간 (|dq2| 피크 정렬) 리샘플 — 실기 자신의
푸시가 초기해 (부호/스케일 자동 정합). CMA popsize 16, ~4500 evals.

산출: p25_a_ol_cma.npz (p25_a_twin.save_npz 스키마 + knots) + p25_a_res_ol.json.
"""
import p25_a_twin as TW          # env 플래그는 TW import가 설정 (반드시 첫 repo-import)

import time
from pathlib import Path

import numpy as np
import cma
from scipy.interpolate import CubicSpline

import safe

HERE = Path(__file__).parent
NK = 9                            # 매듭 수/관절 (마지막 0 고정)
KT_ = np.linspace(0.0, TW.T_PUSH, NK)
MAXFEVALS = 4500
POPSIZE = 16
SIGMA0 = 8.0                      # raw 단위 (천장 35.5의 ~23%)
TG = None                         # 커맨드 평가 그리드 (dt 해상도)


def raw_grid(free):
    """자유 매듭 16 → (raw1g, raw2g) 커맨드 그리드 (스플라인 → 체인 클립 전 값)."""
    k1 = np.append(free[:NK - 1], 0.0)
    k2 = np.append(free[NK - 1:], 0.0)
    s1 = CubicSpline(KT_, k1, bc_type="natural")
    s2 = CubicSpline(KT_, k2, bc_type="natural")
    r1 = np.where(TG <= TW.T_PUSH, s1(np.minimum(TG, TW.T_PUSH)), 0.0)
    r2 = np.where(TG <= TW.T_PUSH, s2(np.minimum(TG, TW.T_PUSH)), 0.0)
    return r1, r2


def main():
    safe.utf8_console()
    global TG
    t0 = time.time()
    print("=== p25_a_cma_ol — 개루프 토크 스플라인 CMA ===", flush=True)
    tw = TW.twin()
    print(f"init [{time.time() - t0:.0f}s] dt={tw['dt']}", flush=True)
    TG = np.arange(0.0, TW.T_END + tw["dt"], tw["dt"])
    st = TW.settle_state(tw, *tw["q0"])
    print(f"settle cached: q=({-st['qpos'][1] - np.pi / 2:.4f}, {-st['qpos'][2]:.4f}) "
          f"target=({tw['q0'][0]:.4f}, {tw['q0'][1]:.4f})", flush=True)

    # 시드: 측정 raw 푸시 (|dq2| 피크를 T_PUSH*0.85 지점에 정렬)
    d0 = tw["d0"]; t = d0["t"]
    tp = float(t[int(np.argmax(np.abs(d0["dq2"])))])
    ts = tp - TW.T_PUSH * 0.85
    seed1 = np.interp(ts + KT_[:-1], t, d0["traw1"])
    seed2 = np.interp(ts + KT_[:-1], t, d0["traw2"])
    x0 = np.clip(np.concatenate([seed1, seed2]), -35.0, 35.0)

    nfev = [0]; ncrash = [0]

    def f(x):
        nfev[0] += 1
        r1, r2 = raw_grid(np.asarray(x, float))
        Lg = TW.rollout_ol(tw, TG, r1, r2, st, t_end=TW.T_END)
        if Lg is None:
            ncrash[0] += 1
            return TW.CRASH_F
        return -TW.apex_of(Lg) + TW.PEN_W * TW.env_pen(tw, Lg)

    f0 = f(x0)
    print(f"seed f={f0:.4f} (apex~{-f0:.3f}m, trial {tw['seed_trial'][1]}, "
          f"push peak t={tp:.3f})", flush=True)

    es = cma.CMAEvolutionStrategy(
        x0, SIGMA0,
        dict(bounds=[-35.5, 35.5], popsize=POPSIZE, maxfevals=MAXFEVALS,
             seed=1, verbose=-1))
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

    r1, r2 = raw_grid(xb)
    Lg = TW.rollout_ol(tw, TG, r1, r2, st, t_end=TW.T_END, record=True)
    h_plan = TW.apex_of(Lg)
    stats = TW.stats_of(tw, Lg, t_push=TW.T_PUSH)
    print(f"h_plan={h_plan:.4f} m  peak raw=({stats['peak_raw1']:.1f}, "
          f"{stats['peak_raw2']:.1f})  peak dq=({stats['peak_dq1']:.1f}, "
          f"{stats['peak_dq2']:.1f})  ceil_frac=({stats['ceil_frac_raw1']:.2f}, "
          f"{stats['ceil_frac_raw2']:.2f})", flush=True)

    TW.save_npz(HERE / "p25_a_ol_cma.npz", Lg,
                extra=dict(knot_t=KT_,
                           knots_raw1=np.append(xb[:NK - 1], 0.0),
                           knots_raw2=np.append(xb[NK - 1:], 0.0)))
    safe.atomic_json_write(HERE / "p25_a_res_ol.json", dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="ol_cma",
        note="개루프 raw 토크 스플라인 CMA (9매듭/관절, 끝매듭 0 고정, dim 16)",
        h_plan=h_plan, stats=stats, evals=nfev[0], crashes=ncrash[0],
        crash_rate=ncrash[0] / max(nfev[0], 1), f_best=fb, f_seed=float(f0),
        params=dict(knot_t=[float(a) for a in KT_],
                    knots_raw1=[float(a) for a in np.append(xb[:NK - 1], 0.0)],
                    knots_raw2=[float(a) for a in np.append(xb[NK - 1:], 0.0)]),
        seed_trial=list(tw["seed_trial"]), npz="p25_a_ol_cma.npz",
        wall_s=float(time.time() - t0)))
    print(f"saved p25_a_ol_cma.npz + p25_a_res_ol.json [{(time.time() - t0) / 60:.1f}m]",
          flush=True)


if __name__ == "__main__":
    main()
