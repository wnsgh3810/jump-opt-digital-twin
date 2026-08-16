# -*- coding: utf-8 -*-
"""_GHQ_inspect3 — 08.07 세 하중의 전 구간 궤적(2초 간격)과 채널별 움직임 구간. 읽기만."""
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


for lo in ("0kg", "2kg", "4kg"):
    p = DATA / "26_08_07" / lo / "probe_sweep_v1"
    h = rd(p / "hip.xlsx"); k = rd(p / "knee.xlsx")
    print(f"== {lo}  (T={h['t'][-1]-h['t'][0]:.0f}s)")
    for nm, d in (("hip ", h), ("knee", k)):
        idx = np.arange(0, len(d["t"]), 1000)          # 2초 간격
        print(f"  {nm} 각[deg]: " + " ".join(f"{np.degrees(d['q'][i]):.0f}" for i in idx))
        v = vel(d["t"], d["q"])
        mv = np.abs(v) > 0.02
        print(f"  {nm} 움직이는 시간 비율(|v|>0.02, 50ms평활) {100*mv.mean():.1f}%  "
              f"|v| 움직일때 중앙 {np.median(np.abs(v)[mv]):.3f} p95 {np.percentile(np.abs(v)[mv],95):.3f}")
        print(f"  {nm} 토크[명령]: " + " ".join(f"{d['tau'][i]:+.1f}" for i in idx))
    print()
