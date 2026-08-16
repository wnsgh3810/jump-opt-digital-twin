# -*- coding: utf-8 -*-
"""h12_bidir — H12: 양방향 검증. 2단 스프링 관측보정의 Mode A 교차 채점 (전 세션).

원칙(사용자): CL만 보면 PD가 오류를 흡수 → Mode A(토크 주입, PD 무관)로 교차 심판.
각 세션·trial에서 정본 Mode A 재생(플랜트 불변) 후 hip 오차 e1을 3종으로 채점:
  ①보정 없음  ②선형 보정 e1−τ̂1/166  ③2단 보정 e1−defl2s(τ̂1) (96/323@9, CL 승자)
예상 긴장: fit 세션(0424/0602)은 현행 보정층이 스프링을 이미 흡수 → 보정이 이중계산으로
악화될 수 있음. 그 크기 = H7 다이어트의 정량 입력. held-out 0324는 진단 관찰만.
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
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402

ROOT = Path(DATA_ROOT)
SESS = {
    "fit 0424": ROOT/"26_04_24",
    "fit 0602": ROOT/"26_06_02"/"position",
    "HO 0324": ROOT/"26_03_24"/"Jump"/"Jump_No_Tr",
    "exp1": ROOT/"26_07_22", "exp2": ROOT/"26_07_23", "exp3": ROOT/"26_07_24",
    "exp4": ROOT/"26_07_25", "exp5": ROOT/"26_07_27",
}
def defl_lin(tau): return tau/166.0
def defl_2s(tau):
    a = np.abs(tau)
    d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d
def smooth(x, w=5): return np.convolve(x, np.ones(w)/w, mode="same")

tw = TW.twin()
OUT = {}
for sess, base in SESS.items():
    if not base.is_dir(): continue
    for fold in sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists() and (p/"knee.xlsx").exists()]):
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
            n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
            t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
            q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
            if np.nanmax(np.abs(q2m)) > 7:
                q1m, q2m = np.radians(q1m), np.radians(q2m)
            v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
            raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
            a1 = ahat_np(raw1, v1)
            qd2 = knee["desiredAngle"].to_numpy(float)
            on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0] if np.nanstd(qd2) > 1e-6 else []
            if len(on): i0 = int(on[0])
            else:
                mv = np.where(np.abs(q2m-q2m[0]) > np.radians(1.0))[0]
                i0 = max(0, int(mv[0])-5) if len(mv) else 0
            t0 = t[i0]
            gf = fold/"GRF.xlsx"
            if gf.exists():
                g = pd.read_excel(gf)["Current_GRF"].to_numpy(float)[:n]
                g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
                ab = np.where(g >= thr)[0]
                t_lo = (t[min(int(ab[-1])+1, len(t)-1)] - t0) if len(ab) else (t[-1]-t0)
            else:
                t_lo = t[int(np.argmax(smooth(np.abs(v2), 5)))] - t0 + 0.02
            t_lo = float(min(t_lo, t[-1]-t0-0.004))
            if t_lo < 0.06: continue
            st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
            Lg = TW.rollout_ol(tw, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05)
            if Lg is None: continue
            m = ((t-t0) >= 0.005) & ((t-t0) <= t_lo)
            e1 = q1m[m] - np.interp((t-t0)[m], Lg["t"], Lg["q1"])
            tau = a1[m]
            r0 = np.degrees(np.sqrt(np.mean(e1**2)))
            rl = np.degrees(np.sqrt(np.mean((e1-defl_lin(tau))**2)))
            r2 = np.degrees(np.sqrt(np.mean((e1-defl_2s(tau))**2)))
            OUT.setdefault(sess, []).append(dict(trial=fold.name, raw=round(float(r0),2),
                                                 lin=round(float(rl),2), two=round(float(r2),2)))
            print(f"{sess}/{fold.name}: 원본 {r0:.2f}° | 선형166 {rl:.2f}° | 2단 {r2:.2f}°", flush=True)
        except Exception as ex:
            print(f"{sess}/{fold.name}: 오류 {type(ex).__name__} {ex}", flush=True)

json.dump(OUT, open(HERE/"_h12_bidir.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n=== H12 집계 (세션 평균, Mode A hip e1 RMSE[°]) ===")
for sess, rows in OUT.items():
    print(f"{sess:10s}: 원본 {np.mean([r['raw'] for r in rows]):5.2f} → 선형 {np.mean([r['lin'] for r in rows]):5.2f} → 2단 {np.mean([r['two'] for r in rows]):5.2f} (n={len(rows)})")
print("done")
