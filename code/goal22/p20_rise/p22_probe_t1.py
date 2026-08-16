# -*- coding: utf-8 -*-
"""P22 프로브 T1 — 0429 교차게이트 정량 재심문: 푸시 전류 수준 비교.

질문: 0429(CVT, l_i=25.08mm)의 푸시 무릎(크랭크) 전류가 무변속 세션보다 실질적으로
낮은가? (CVT가 크랭크→무릎 토크를 증폭하므로 같은 점프에 크랭크 전류가 덜 필요)
낮다면(R=med|traw2|_0429/med|traw2|_noCVT < 1), Iq² 꼴 모터측 토크추정 부족분은
0429에서 R²배로 축소 → R²이 작으면(≲0.5) "0429가 보정 0을 요구했다"는 기존
교차게이트는 Iq² 형태에 대해 검정력이 없었다 (기각이 성급했다).

푸시 창 정의 (본 스크립트 고정):
  dq2_s = savgol(dq2, 11, 3)  [P12 _prep_arrays와 동일 스무딩]
  피크 탐색은 t ≤ toff+0.1 (GRF 이륙시각, cvt_run2.takeoff_time 로직 복제; GRF 없으면 전체)
  푸시 = 전역 |dq2_s| 피크를 포함하는 연속 구간 where |dq2_s| > 0.30·피크
데이터: fit 세션만 (0421/0424/0602/0429). held-out 0324 제외 (철칙 9).
원본 xlsx 읽기 전용. 산출물: 표(stdout) + JSON(Desktop/jump_opt/g22_p20_results).
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

DATA = Path(DATA_ROOT)
DST = Path((LEGACY_ROOT + "/g22_p20_results"))
DST.mkdir(parents=True, exist_ok=True)

# a_hat (Paper) — 출처: code/goal22/p14_ahat/p14_judge.py L26-27, L38-41 (사본, 검증된 상수)
KT, GR, CF = 0.091, 9.0, 0.59
A_PAPER = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])


def ahat(A, tau_rep, v):
    Iq = (CF / (GR * KT)) * np.asarray(tau_rep, float)
    s = np.sign(v)
    return A[0] * GR * KT * Iq - A[1] * GR * np.abs(Iq) * Iq - A[2] * s - A[3] * np.abs(Iq) * s


SETS = {
    "jump_position_0421": (DATA / "26_04_21/Position Control",
                           ["P60_D0.75_P60_D2", "P70_D0.75_P70_D2", "P80_D0.75_P80_D2",
                            "P90_D0.75_P90_D2", "P100_D0.75_P100_D2", "P200_D1.5_P200_D4"]),
    "jump_0424": (DATA / "26_04_24",
                  ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "120_2_120_2",
                   "120_2.2_150_2.5", "120_2.2_200_2.8", "150_2.2_250_3",
                   "150_2.2_350_3.5", "150_2.2_500_4"]),
    "jump_0602": (DATA / "26_06_02/position",
                  ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "120_2_120_2",
                   "150_2.2_250_3", "150_2.2_500_5"]),
    "jump_0429": (DATA / "26_04_29",
                  ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "90_1.5_90_2.5",
                   "120_2_120_2", "120_2.2_150_2.5", "120_2.2_200_2.8",
                   "150_2.2_250_3", "150_2.2_350_3.5", "150_2.2_500_4"]),
}


def push_window(t, dq2, grf):
    """(ia, ib) 푸시 연속 구간 인덱스 + 스무딩 |dq2| 피크."""
    dqs = savgol_filter(dq2, 11, 3)
    if grf is not None and len(grf) >= 5:
        n = min(len(grf), len(t))
        pk = int(np.argmax(grf[:n]))
        below = np.where(grf[pk:n] < 0.02 * grf[pk])[0]
        toff = t[pk + below[0]] if len(below) else t[n - 1]
        m = t <= toff + 0.1
    else:
        m = np.ones_like(t, bool)
    ip = int(np.argmax(np.abs(dqs) * m))
    pkv = abs(dqs[ip])
    thr = 0.30 * pkv
    ia = ip
    while ia > 0 and abs(dqs[ia - 1]) > thr:
        ia -= 1
    ib = ip
    while ib < len(t) - 1 and abs(dqs[ib + 1]) > thr:
        ib += 1
    return ia, ib, pkv


def main():
    res = {}
    for ds, (root, subs) in SETS.items():
        pool_raw, pool_ah = [], []
        trials = []
        for sub in subs:
            k = pd.read_excel(root / sub / "knee.xlsx")
            t = k["Time"].values.astype(float)
            t = t - t[0]
            dq2 = k["currentAngleVelocity"].values.astype(float)
            traw2 = k["currentTorque"].values.astype(float)
            try:
                grf = pd.read_excel(root / sub / "GRF.xlsx")["Current_GRF"].values.astype(float)
            except Exception:
                grf = None
            ia, ib, pkv = push_window(t, dq2, grf)
            araw = np.abs(traw2[ia:ib + 1])
            aah = np.abs(ahat(A_PAPER, traw2[ia:ib + 1], dq2[ia:ib + 1]))
            pool_raw.append(araw)
            pool_ah.append(aah)
            trials.append(dict(sub=sub, t0=float(t[ia]), t1=float(t[ib]),
                               pk_dq2=float(pkv), n=int(ib - ia + 1),
                               med_raw=float(np.median(araw)), p90_raw=float(np.percentile(araw, 90)),
                               max_raw=float(araw.max()), med_ah=float(np.median(aah)),
                               p90_ah=float(np.percentile(aah, 90)), max_ah=float(aah.max())))
        pr = np.concatenate(pool_raw)
        pa = np.concatenate(pool_ah)
        res[ds] = dict(trials=trials, n_samp=int(len(pr)),
                       med_raw=float(np.median(pr)), p90_raw=float(np.percentile(pr, 90)),
                       max_raw=float(pr.max()),
                       med_ah=float(np.median(pa)), p90_ah=float(np.percentile(pa, 90)),
                       max_ah=float(pa.max()),
                       med_iq=float(np.median(pr) * CF / (GR * KT)))

    print("=== T1: 푸시 창 |traw2| (raw iTM 단위) / |ahat2| (축 Nm) — 세션 풀 통계 ===")
    hdr = f"{'세션':22s} {'n':>5} {'med|traw2|':>11} {'p90':>8} {'max':>8}  {'med|ahat2|':>11} {'p90':>8} {'max':>8}"
    print(hdr)
    for ds, r in res.items():
        print(f"{ds:22s} {r['n_samp']:5d} {r['med_raw']:11.2f} {r['p90_raw']:8.2f} {r['max_raw']:8.2f}"
              f"  {r['med_ah']:11.2f} {r['p90_ah']:8.2f} {r['max_ah']:8.2f}")
    print("\n--- 트라이얼별 med|traw2| (게인 의존 점검) ---")
    for ds, r in res.items():
        s = " ".join(f"{tr['med_raw']:.1f}" for tr in r["trials"])
        print(f"{ds:22s} [{s}]")

    print("\n=== 비율 R = med_push|traw2|(0429) / med_push|traw2|(no-CVT 세션) ===")
    m429 = res["jump_0429"]["med_raw"]
    ratios = {}
    for ds in ("jump_position_0421", "jump_0424", "jump_0602"):
        R = m429 / res[ds]["med_raw"]
        Rah = res["jump_0429"]["med_ah"] / res[ds]["med_ah"]
        ratios[ds] = dict(R=float(R), R2=float(R * R), R_ahat=float(Rah))
        print(f"vs {ds:22s} R={R:.3f}  R²={R*R:.3f}   (ahat 단위 R={Rah:.3f})")
    p90r = {ds: res["jump_0429"]["p90_raw"] / res[ds]["p90_raw"]
            for ds in ("jump_position_0421", "jump_0424", "jump_0602")}
    print("p90 기준 R:", " ".join(f"{k.split('_')[-1]}={v:.3f}" for k, v in p90r.items()))
    print("\n해석: |Iq| 비례 부족분은 0429에서 R배, Iq² 비례 부족분은 R²배로 축소.")
    print("0429 게이트의 측정 노이즈(속도 고점 비율 ±0.17) 아래로 R²·(무변속 부족분 효과)가")
    print("숨으면 → Iq² 형태에 대한 기존 기각은 검정력 부족.")
    json.dump(dict(sessions=res, ratios=ratios, p90_ratios=p90r),
              open(DST / "p22_probe_t1.json", "w"), indent=1)
    print("saved", DST / "p22_probe_t1.json")


if __name__ == "__main__":
    main()
