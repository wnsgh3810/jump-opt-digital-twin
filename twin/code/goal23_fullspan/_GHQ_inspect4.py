# -*- coding: utf-8 -*-
"""_GHQ_inspect4 — 08.07 무릎 왕복 구간의 미세 구조(0.1초 간격)와 속도-자세 상관. 읽기만."""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os
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
    dt = float(np.median(np.diff(t)))
    return np.convolve(np.gradient(q, dt), np.ones(w) / w, mode="same")


p = DATA / "26_08_07/0kg/probe_sweep_v1"
k = rd(p / "knee.xlsx")
t = k["t"] - k["t"][0]
v = vel(k["t"], k["q"])
m = (t > 118) & (t < 132)
print("무릎 왕복 구간 t=118~132s, 0.2초 간격: 각[deg] / 목표각[deg] / 속도(50ms평활)[rad/s]")
idx = np.nonzero(m)[0][::100]
print("각   : " + " ".join(f"{np.degrees(k['q'][i]):6.1f}" for i in idx))
print("목표 : " + " ".join(f"{np.degrees(k['qd'][i]):6.1f}" for i in idx))
print("속도 : " + " ".join(f"{v[i]:+6.3f}" for i in idx))
print("토크 : " + " ".join(f"{k['tau'][i]:+6.2f}" for i in idx))

# 위상별 속도 분포
for nm, lo, hi in (("phase1 힙왕복(무릎 -112 고정)", 5, 55),
                   ("phase2 힙왕복(무릎 -58 고정)", 60, 110),
                   ("phase3 무릎왕복(힙 -45 고정)", 114, 166)):
    mm = (t > lo) & (t < hi)
    for ch, d in (("hip", rd(p / "hip.xlsx")), ("knee", k)):
        vv = vel(d["t"], d["q"])[mm]
        qq = d["q"][mm]
        mv = np.abs(vv) > 0.015
        if mv.sum() < 100:
            print(f"{nm:28s} {ch:5s} 거의 정지 ({100*mv.mean():.0f}%)")
            continue
        print(f"{nm:28s} {ch:5s} 움직임 {100*mv.mean():4.0f}%  |v| p10 {np.percentile(np.abs(vv)[mv],10):.3f} "
              f"중앙 {np.median(np.abs(vv)[mv]):.3f} p90 {np.percentile(np.abs(vv)[mv],90):.3f} "
              f"max {np.abs(vv).max():.3f} · 각범위 {np.degrees(qq.min()):.0f}~{np.degrees(qq.max()):.0f}° "
              f"· corr(|v|,|각-중앙|) {np.corrcoef(np.abs(vv)[mv], np.abs(qq[mv]-np.median(qq)))[0,1]:+.2f}")
