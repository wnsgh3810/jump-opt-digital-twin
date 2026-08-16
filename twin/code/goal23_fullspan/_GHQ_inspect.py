# -*- coding: utf-8 -*-
"""_GHQ_inspect — 원자료 훑기 (시뮬 없음): 일어서기 4경우 전 구간 기록 · 08.07 왕복 기록의
속도 분포와 방향(올라감/내려감) 구조를 본다. 읽기만 한다."""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); os.chdir(HERE)
DATA = Path(DATA_ROOT)
S2S = DATA / "26_06_04"
CASES = ["cvt/no_load", "cvt/load_2.5", "cvt/load_5", "no_cvt/no_load"]


def rd(p):
    df = pd.read_excel(p)
    c = {k.lower().replace(" ", ""): k for k in df.columns}
    g = lambda k: np.asarray(df[c[k]], float)
    return dict(t=g("time"), q=g("currentangle"), dq=g("currentanglevelocity"),
                tau=g("currenttorque"), qd=g("desiredangle"))


print("=" * 100)
print("A. 일어서기 4경우 — 전 구간(raw_unwrap) 기록 구조")
print("=" * 100)
for s in CASES:
    for tag, fold in (("창(정본)", S2S / s), ("전구간", S2S / s / "raw_unwrap")):
        if not (fold / "knee.xlsx").exists():
            print(f"{s:15s} {tag}: 없음"); continue
        k = rd(fold / "knee.xlsx"); h = rd(fold / "hip.xlsx")
        dt = np.median(np.diff(k["t"]))
        v = k["dq"]
        print(f"{s:15s} {tag:8s} n={len(k['t']):5d} dt={dt*1000:.2f}ms "
              f"t={k['t'][0]:.2f}~{k['t'][-1]:.2f}s ({k['t'][-1]-k['t'][0]:.2f}s) "
              f"무릎각 {np.degrees(k['q']).min():7.1f}~{np.degrees(k['q']).max():7.1f}° "
              f"|v|max={np.abs(v).max():5.2f} v>0 {100*np.mean(v>0.05):4.1f}% "
              f"v<0 {100*np.mean(v<-0.05):4.1f}% |v|<0.05 {100*np.mean(np.abs(v)<0.05):4.1f}%")
    print()

print("=" * 100)
print("B. 08.07 무게추 왕복 (probe_sweep_v1) — 속도 분포")
print("=" * 100)
for lo in ("0kg/probe_sweep_v1", "0kg/probe_sweep_v1 - 2", "2kg/probe_sweep_v1", "4kg/probe_sweep_v1"):
    p = DATA / "26_08_07" / lo
    if not (p / "knee.xlsx").exists():
        print(f"{lo}: 없음"); continue
    for nm in ("hip", "knee"):
        d = rd(p / f"{nm}.xlsx")
        v = d["dq"]; sp = np.abs(v)
        qs = np.percentile(sp, [50, 90, 99])
        print(f"{lo:24s} {nm:5s} n={len(v):6d} dt={np.median(np.diff(d['t']))*1000:.2f}ms "
              f"T={d['t'][-1]-d['t'][0]:6.1f}s 각 {np.degrees(d['q']).min():7.1f}~{np.degrees(d['q']).max():7.1f}° "
              f"|v| 중앙 {qs[0]:.3f} p90 {qs[1]:.3f} p99 {qs[2]:.3f} max {sp.max():.2f} "
              f"토크 {d['tau'].min():+6.2f}~{d['tau'].max():+6.2f}")
    print()
