# -*- coding: utf-8 -*-
"""_GHQ_inspect2 — 08.07 왕복의 실제 궤적 모양과 속도(평활 전/후) 확인. 읽기만."""
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

DATA = Path(DATA_ROOT)


def rd(p):
    df = pd.read_excel(p)
    c = {k.lower().replace(" ", ""): k for k in df.columns}
    g = lambda k: np.asarray(df[c[k]], float)
    return dict(t=g("time"), q=g("currentangle"), dq=g("currentanglevelocity"),
                tau=g("currenttorque"), qd=g("desiredangle"))


def vel(t, q, w=25):
    """중심차분 + 이동평균 (w 샘플, 2ms 표본이면 w=25 → 50ms)"""
    dt = float(np.median(np.diff(t)))
    v = np.gradient(q, dt)
    k = np.ones(w) / w
    return np.convolve(v, k, mode="same")


p = DATA / "26_08_07/0kg/probe_sweep_v1"
k = rd(p / "knee.xlsx"); h = rd(p / "hip.xlsx")
print("무릎각 시간열 (1초 간격, 앞 60초) [deg]")
idx = np.arange(0, min(len(k["t"]), 30000), 500)
print(" ".join(f"{np.degrees(k['q'][i]):.0f}" for i in idx))
print("\n힙각 시간열 (1초 간격, 앞 60초) [deg]")
print(" ".join(f"{np.degrees(h['q'][i]):.0f}" for i in idx))

for nm, d in (("hip", h), ("knee", k)):
    for w in (1, 11, 25, 51, 101):
        v = vel(d["t"], d["q"], w) if w > 1 else np.gradient(d["q"], 0.002)
        print(f"{nm:5s} 평활 {w:3d}샘플({w*2:3d}ms): |v| 중앙 {np.median(np.abs(v)):.4f} "
              f"p90 {np.percentile(np.abs(v),90):.4f} p99 {np.percentile(np.abs(v),99):.4f} "
              f"max {np.abs(v).max():.3f}  raw채널 대비 상관 "
              f"{np.corrcoef(v, d['dq'])[0,1]:.3f}")
    print(f"{nm:5s} raw dq 채널   : |v| 중앙 {np.median(np.abs(d['dq'])):.4f} "
          f"p99 {np.percentile(np.abs(d['dq']),99):.4f} max {np.abs(d['dq']).max():.3f}")
    # 왕복 주기 추정: 각도 부호 반전 횟수
    v = vel(d["t"], d["q"], 51)
    s = np.sign(v); ch = np.sum(np.abs(np.diff(s[np.abs(v) > 0.01])) > 1)
    print(f"{nm:5s} 방향 전환 횟수(평활 51) ≈ {ch}  → 주기 ≈ {2*(d['t'][-1]-d['t'][0])/max(ch,1):.1f}s")
    print()
