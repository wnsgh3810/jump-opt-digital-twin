# -*- coding: utf-8 -*-
"""h28c — H28 양방향 검증: Mode A(PD 무관)의 날짜별 k̂이 CL 오라클과 일치하는가.

CL 캘리브 오라클: 22→36 / 25→46 / 27→86~96 (23/24는 슬립 날 — 비일관).
Mode A e1~â1 회귀는 PD 게인이 안 들어가므로, 여기서도 그날 기울기가 무르면(1/k̂ 큼)
드리프트는 실재 물리(스프링). CL만 원하면 게인층 아티팩트.
회귀: h2_shape와 동일 (rollout_ol, trial별 기준선 차감) — 날짜별로 분리.
저부하역(|Δτ|<9Nm) k̂_lo와 전역 k̂ 둘 다 보고.
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402

ROOT = Path(DATA_ROOT)
DAYS = ["26_07_22", "26_07_23", "26_07_24", "26_07_25", "26_07_27"]
tw = TW.twin()
POOL = {d: dict(e=[], tau=[]) for d in DAYS}
for day in DAYS:
    for fold in sorted([p for p in (ROOT/day).iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
        except FileNotFoundError:
            continue
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
        v1 = hip["currentAngleVelocity"].to_numpy(float)
        raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
        a1 = ahat_np(raw1, v1)
        qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
        i0 = int(on[0]) if len(on) else 0; t0 = t[i0]
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(min(t[min(int(ab[-1])+1, len(t)-1)]-t0, t[-1]-t0-0.004))
        if t_lo < 0.06: continue
        st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
        Lg = TW.rollout_ol(tw, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05)
        if Lg is None: continue
        m = ((t-t0) >= 0.005) & ((t-t0) <= t_lo)
        e1 = q1m[m] - np.interp((t-t0)[m], Lg["t"], Lg["q1"])
        POOL[day]["e"].append(e1 - e1[:5].mean())
        POOL[day]["tau"].append(a1[m] - a1[m][:5].mean())
        print(f"{day}/{fold.name}: n={int(m.sum())}", flush=True)

print("\n=== 날짜별 Mode A k̂ (e1~Δτ1 회귀) vs CL 오라클 ===", flush=True)
ORACLE = {"26_07_22": 36, "26_07_23": "혼재(슬립)", "26_07_24": "혼재(슬립)", "26_07_25": 46, "26_07_27": "86~96"}
OUT = {}
for day in DAYS:
    e = np.concatenate(POOL[day]["e"]); tau = np.concatenate(POOL[day]["tau"])
    def khat(mask):
        X = np.column_stack([tau[mask], np.ones(int(mask.sum()))])
        b, _, _, _ = np.linalg.lstsq(X, e[mask], rcond=None)
        r = np.corrcoef(tau[mask], e[mask])[0, 1]
        return (1/abs(b[0]) if abs(b[0]) > 1e-9 else float("inf")), float(r)
    k_all, r_all = khat(np.ones(len(e), bool))
    lo = np.abs(tau) < 9.0
    k_lo, r_lo = khat(lo)
    OUT[day] = dict(n=len(e), k_all=round(k_all, 1), r_all=round(r_all, 3),
                    k_lo=round(k_lo, 1), r_lo=round(r_lo, 3), cl_oracle=str(ORACLE[day]))
    print(f"{day}: k̂전역 {k_all:6.0f} (r {r_all:+.2f}) | k̂저부하 {k_lo:6.0f} (r {r_lo:+.2f}) | CL 오라클 {ORACLE[day]}", flush=True)

json.dump(OUT, open(HERE/"_h28c_modea_perday.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", flush=True)
