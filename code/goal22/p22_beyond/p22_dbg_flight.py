# -*- coding: utf-8 -*-
"""디버그7: 비행창 검출이 왜 전멸인가 — trial별 grf/toff/len 진단."""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
import safe
safe.utf8_console()
import p19_adapter as AD

AD.ensure_init()
import p14_judge as J
import cvt_core as CC

for tr in J._P["cl"]:
    d = tr["d"]
    t = d["t"]
    g = d.get("grf_real")
    dt = float(np.median(np.diff(t)))
    if g is None:
        print(f"{tr['ds']}/{tr['sub']}: GRF 없음  len={len(t)} dt={dt * 1000:.1f}ms")
        continue
    g = np.asarray(g, float)
    on, toff = tr["on"], tr["toff"]
    print(f"{tr['ds']}/{tr['sub']}: len={len(t)} dt={dt * 1000:.1f}ms t_end={t[-1]:.2f}s "
          f"on={on} toff={toff} t_toff={t[min(toff, len(t) - 1)]:.2f} "
          f"g[toff:toff+5]={np.round(g[toff:toff + 5], 1)} gmax={np.nanmax(g):.0f} "
          f"잔여샘플={len(t) - toff}")

for sub in CC.SUBS429[:4]:
    d = CC.load_0429(sub)
    t = d["t"]
    g = np.asarray(d["grf_real"], float)
    dt = float(np.median(np.diff(t)))
    pk = int(np.nanargmax(g))
    below = np.where(g[pk:] < 0.02 * g[pk])[0]
    toff = pk + int(below[0]) if len(below) else len(t) - 1
    print(f"0429/{sub}: len={len(t)} dt={dt * 1000:.1f}ms t_end={t[-1]:.2f}s pk={pk} "
          f"toff={toff} g[toff:toff+5]={np.round(g[toff:toff + 5], 1)} 잔여={len(t) - toff}")
