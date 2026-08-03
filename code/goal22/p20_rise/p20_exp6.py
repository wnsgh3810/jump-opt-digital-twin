# -*- coding: utf-8 -*-
"""P20 실험 6 — 26.04.22 (FF 토크제어, 0421 다음 날) 기준선 측정.

판별 목적 (사용자 정정으로 설계):
  0421 = 다른 세션과 같은 드라이버 PD (V_des=0) — 기준선 ≈ 0 (유일 예외)
  0422 = 진짜 다른 제어방식 (feedforward torque), 0421 바로 다음 날
  → 0422 기준선이 ≈0 이면: "4월 21-22 리그 상태"가 원인 (세션 상태설 — 4/22와 4/24 사이 변화 수색)
  → 0422 기준선이 ≈+2 면: 하루 새 갈림 = 명령 구조(PD vs FF) 의존 (구조설 부활)
주의: 0422는 파이프라인 밖 세션 — 각도 오프셋 미적합(o=0) 캐비앳 명시. held-out 아님(0319·0324만).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
from p20_exp4 import win_scan
from cvt_run2 import takeoff_time

DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_04_22/Torque Control")


def load_0422(sub):
    p = DATA / sub
    def rd(fn):
        df = pd.read_excel(p / fn)
        return {c: df[c].values.astype(float) for c in df.columns}
    hip = rd("hip.xlsx"); knee = rd("knee.xlsx")
    t = hip["Time"]
    d = dict(t=t - t[0])
    for nm, src in (("1", hip), ("2", knee)):
        tt = src["Time"]
        for col, key in (("currentAngle", "q"), ("currentAngleVelocity", "dq"),
                         ("currentTorque", "traw")):
            y = src[col]
            m = np.isfinite(tt) & np.isfinite(y)
            d[key + nm] = np.interp(t, tt[m], y[m])
    try:
        grf = rd("GRF.xlsx")
        col = [c for c in grf if "Current" in c][0]
        g = grf[col]
        tg = grf["Time"]
        m = np.isfinite(tg) & np.isfinite(g)
        d["grf"] = np.interp(t, tg[m], g[m])
    except Exception:
        d["grf"] = None
    return d


def main():
    model, _ = P.build_flip(E.X32, E.V[1], E.SP)
    print("0422 (FF 토크, 0421 다음 날) — 창별 λ* [o=0 캐비앳]")
    allr = []
    for sub in ("P40_D0.7", "P70_D2", "P100_D3"):
        d = load_0422(sub)
        toff = takeoff_time(d["t"], d["grf"]) if d["grf"] is not None else d["t"][-1] * 0.6
        starts = np.arange(0.02, max(toff - 0.10, 0.1), 0.035)
        rs = win_scan(model, d, 0.030, starts, 0.12)
        for r in rs:
            allr.append(dict(sub=sub, **r))
        lo = [r["lam"] for r in rs if abs(r["dq"]) < 3]
        hi = [r["lam"] for r in rs if abs(r["dq"]) > 8]
        print(f"  {sub:10s} toff={toff:.2f}  저속 λ* {np.mean(lo) if lo else float('nan'):+.2f}"
              f"±{np.std(lo) if lo else 0:.2f} (n={len(lo)}) | 고속 λ* "
              f"{np.mean(hi) if hi else float('nan'):+.2f} (n={len(hi)})", flush=True)
    lo = [r["lam"] for r in allr if abs(r["dq"]) < 3]
    hi = [r["lam"] for r in allr if abs(r["dq"]) > 8]
    print(f"\n[0422 종합] 저속 기준선 {np.mean(lo):+.2f}±{np.std(lo):.2f} (n={len(lo)}) | "
          f"고속 {np.mean(hi) if hi else float('nan'):+.2f}±{np.std(hi) if hi else 0:.2f} (n={len(hi)})")
    print("비교: 0421(전날, PD) +0.14 / 0424(이틀 뒤, PD+Vdes) +1.78 / 0324(FF, 3월) P18b적합 +2.06")


if __name__ == "__main__":
    main()
