# -*- coding: utf-8 -*-
"""P20 실험 9a — 게이트형 부하 비례 어시스트: λ(t) = c·â₂(t)·g(|dq₂|), g=1/(1+(v/v₀)²).

실증 법칙 v3의 준정적 층 구현: 정지/저속에서 무릎 부하의 ~25%를 지지하는 성분이
운동 시작과 함께 잦아드는(정지→운동 마찰 전이 꼴) 모델. (c, v₀) 격자를 4개 전선에서
동시 평가 — 성공 = 전 전선이 [보정 0]과 [const 2.25] 참조를 동시에 이김.
  F1 점프 창 (0421/0424/0602)  [참조: λ0=115.1, const2.25=79.2]
  F2 s2s 창                    [참조: λ0=33.8, 기준선만=11.6]
  F3 0429 잔여 λ* 저/고속      [참조: 보정 0에서 +1.5/+1.6 → 0 근접해야]
  F4 0604 잔여 λ* 무부하/5kg   [참조: +0.77/+1.52 → 0 근접, 스케일링 소멸해야]
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
import p20_exp4 as X4
import p20_exp7 as X7
from cvt_core import load_0429

sys.path.insert(0, str(HERE.parent / "p18_cvt"))
import s2s_0604 as S0

mj = P.J._P["mj"]
DST = Path((LEGACY_ROOT + "/g22_p20_results"))
RES_GRID = np.arange(-2.0, 3.01, 0.5)


def corr_vec(raw2, dq2, c, v0):
    g = 1.0 / (1.0 + (np.abs(dq2) / v0) ** 2)
    return c * P.J.ahat(E.A, raw2, dq2) * g


def f3_resid(c, v0):
    lams_lo, lams_hi = [], []
    model = None
    for sub in ("60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"):
        d = load_0429(sub)
        if model is None:
            model, _ = P.build_cvt(E.X32, E.V[1], E.SP, d["l_i"])
        base = np.interp(d["t"] - P.SD, d["t"], corr_vec(d["traw2"], d["dq2"], c, v0))
        percfg = {}
        for lam in RES_GRID:
            for t0, sc in X7.win_lam_429(model, d, d["l_i"], lam, lam_base=base):
                percfg.setdefault(round(t0, 4), []).append(sc)
        for t0, scs in percfg.items():
            scs = np.array(scs)
            if (scs.max() - scs.min()) / max(scs.min(), 1e-9) < 0.02:
                continue
            i = int(np.argmin(scs))
            if i in (0, len(RES_GRID) - 1):
                ls = float(RES_GRID[i])
            else:
                a, b, cc = scs[i - 1], scs[i], scs[i + 1]
                den = a - 2 * b + cc
                ls = float(RES_GRID[i] + np.clip(0.5 * (a - cc) / den if abs(den) > 1e-12 else 0, -1, 1) * 0.5)
            i0 = int(np.searchsorted(d["t"], t0))
            (lams_hi if abs(d["dq2"][i0]) > 10 else lams_lo).append(ls)
    return (float(np.mean(lams_lo)) if lams_lo else float("nan"),
            float(np.mean(lams_hi)) if lams_hi else float("nan"))


def f4_resid(c, v0):
    out = {}
    for grp, sub, load in (("cvt", "no_load", 0.0), ("cvt", "load_5", 5.0)):
        d = S0.load_0604(grp, sub)
        model, _ = P.build_cvt(E.X32, E.V[1], E.SP, d["l_i"])
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load
        base = np.interp(d["t"] - P.SD, d["t"], corr_vec(d["traw2"], d["dq2"], c, v0))
        starts = np.arange(0.3, d["t"][-1] - 0.3, 0.5)
        rs = X4.win_scan(model, d, d["l_i"], starts, 0.2, lam_base=base, lam_grid=RES_GRID)
        out[sub] = float(np.mean([r["lam"] for r in rs])) if rs else float("nan")
    return out


def main():
    model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
    rows = {}
    for c in (0.20, 0.25, 0.30):
        for v0 in (1.5, 3.0, 6.0):
            fn = lambda tr, _c=c, _v=v0: corr_vec(tr["raw2"], tr["v2"], _c, _v)
            r1 = E.eval_set(model_f, E.JDS, fn)
            F1 = float(np.mean(list(r1.values())))
            F2 = float(list(E.eval_set(model_f, ("s2s_gnd_0319",), fn).values())[0])
            lo, hi = f3_resid(c, v0)
            o = f4_resid(c, v0)
            rows[f"{c}|{v0}"] = dict(F1=F1, F2=F2, per=r1, lo=lo, hi=hi, **o)
            print(f"c={c:.2f} v0={v0:3.1f} | F1 {F1:6.1f} (" +
                  " ".join(f"{k.split('_')[-1]} {v:.0f}" for k, v in r1.items()) +
                  f") | F2 {F2:5.1f} | 0429잔여 {lo:+5.2f}/{hi:+5.2f} | "
                  f"0604잔여 {o['no_load']:+5.2f}/{o['load_5']:+5.2f}", flush=True)
    json.dump(rows, open(DST / "exp9_results.json", "w"), indent=1, default=float)
    print("\n참조: F1 λ0=115.1 const2.25=79.2 | F2 λ0=33.8 기준선만=11.6 | "
          "0429 λ0=+1.5/+1.6 | 0604 λ0=+0.77/+1.52", flush=True)


if __name__ == "__main__":
    main()
