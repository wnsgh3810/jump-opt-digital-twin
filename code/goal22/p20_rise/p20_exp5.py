# -*- coding: utf-8 -*-
"""P20 실험 5 — 통일 법칙 검증: λ = c · â (무릎 토크 비례 보정, 파라미터 1개).

exp4 발견: 같은 세션 내에서 기준선이 부하에 비례 (0604: 1.0→2.1→3.8 as 3.8→8.8A).
가설: pre30의 두 성분(세션별 기준선 + 푸시 상승)은 사실 하나 —
  실제 무릎 축토크 = a_hat 추정 × (1 + c)  꼴의 부하 비례 과소추정.
검증 설계 (과적합 방지):
  1) c는 점프 창(0421/0424/0602)에서만 적합 (기준선 없음, c 단독)
  2) 표본 외 예측: s2s_0319(+1.0), 0604(+1.0/+2.1/+3.8), 0429 저속(+1.0)의
     실측 λ*를 ĉ·⟨â⟩로 예측해 비교 + s2s/0429 총점 무악화 확인
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
from p14_judge import KT, GR, CF, invert_paper

DST = Path((LEGACY_ROOT + "/g22_p20_results"))
CS = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40]


def main():
    model, _ = P.build_flip(E.X32, E.V[1], E.SP)
    # ── 1) c 적합 (점프 창만, 기준선 0) ──
    print("점프 창 점수 vs c (기준: const2.25 → 0421 75.0 / 0424 79.8 / 0602 82.9, 평균 79.2)")
    best = (None, 9e9)
    for c in CS:
        fn = lambda tr, _c=c: _c * P.J.ahat(E.A, tr["raw2"], tr["v2"])
        r = E.eval_set(model, E.JDS, fn)
        tot = float(np.mean(list(r.values())))
        print(f"  c={c:.2f}: 평균 {tot:6.1f} | " +
              " ".join(f"{k.split('_')[-1]} {v:.1f}" for k, v in r.items()), flush=True)
        if tot < best[1]:
            best = (c, tot)
    c = best[0]
    print(f"BEST c = {c:.2f} (평균 {best[1]:.1f})", flush=True)
    # ── 2) 표본 외: s2s 창 점수 ──
    fn = lambda tr: c * P.J.ahat(E.A, tr["raw2"], tr["v2"])
    s2s = E.eval_set(model, ("s2s_gnd_0319",), fn)
    print(f"s2s 창 점수 (c={c}): {list(s2s.values())[0]:.1f}  "
          f"[참조: const2.25 43.2 / 세션기준선 11.6]", flush=True)
    # ── 3) 표본 외: 0429 총점 (invert_paper 주입) ──
    dform = lambda raw, dq, _c=c: _c * P.J.ahat(E.A, raw, dq)
    m429 = E.sc429(dform)
    print(f"0429 Mode A 총점 (c={c}): {m429:.2f}  [참조: 현행 58.5]", flush=True)
    # ── 4) 예측표: λ̂ = c·⟨â⟩(저속 유지) vs 실측 λ* ──
    print("\n[예측표] 저속 유지 구간 — 예측 c·⟨â⟩ vs 실측 λ*")
    rows = []
    # 점프 세션 유지 ⟨â⟩ (초반 0.1s)
    for ds, lam_meas in (("jump_position_0421", 0.14), ("jump_0424", 1.78),
                         ("jump_0602", 2.20)):
        ahs = []
        for tr in E.P12._G["trials"]:
            if tr["ds"] != ds:
                continue
            t = tr["pp"]["t"]
            m = t <= 0.10
            ahs.append(float(np.mean(np.abs(P.J.ahat(E.A, tr["raw2"], tr["v2"])[m]))))
        rows.append((ds, np.mean(ahs), lam_meas))
    # s2s_0319 전체 ⟨â⟩
    ahs = []
    for tr in E.P12._G["trials"]:
        if tr["ds"] == "s2s_gnd_0319":
            ahs.append(float(np.mean(np.abs(P.J.ahat(E.A, tr["raw1"] * 0 + tr["raw2"], tr["v2"])))))
    rows.append(("s2s_gnd_0319", np.mean(ahs), 1.02))
    # 0604 (exp4 실측), 0429 저속 (exp3 실측) — ⟨â⟩는 |Iq|로부터 (â≈A0·CF·raw≈1.156·0.59·raw)
    for name, iq, lam_meas in (("0604 cvt no_load", 3.8, 1.02), ("0604 cvt 2.5kg", 6.9, 2.09),
                               ("0604 cvt 5kg", 8.8, 3.77), ("0604 no_cvt", 5.2, 0.71),
                               ("0429 저속", None, 1.01)):
        ah = iq * (GR * KT / CF) * E.A[0] * CF / 1.0 if iq else float("nan")
        # â ≈ A0·GR·KT·Iq (마찰항 무시 근사)
        ah = E.A[0] * GR * KT * iq if iq else float("nan")
        rows.append((name, ah, lam_meas))
    print(f"{'구간':22s} {'⟨â⟩[Nm]':>8} {'예측 c·⟨â⟩':>10} {'실측 λ*':>8}")
    for name, ah, lm in rows:
        pred = c * ah if np.isfinite(ah) else float("nan")
        print(f"{name:22s} {ah:8.1f} {pred:10.2f} {lm:8.2f}")
    json.dump(dict(c=c, rows=[(n, float(a), float(l)) for n, a, l in rows]),
              open(DST / "exp5_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
