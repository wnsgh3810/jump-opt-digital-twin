# -*- coding: utf-8 -*-
"""h2_shape — H2: hip 스프링의 비선형 형태 확정 (배포 19 trial 풀드).

후보 3형:
  ①선형        e1 = τ/k + c                     (2p)
  ②2단(연화)   |τ|<τ0: τ/k_lo, 밖: 연속 이어 τ/k_hi (4p; 저부하 무름 가설)
  ③백래시      e1 = sign(τ)·max(|τ|−d,0)/k + c  (3p; 데드밴드)
판정: 풀드 SSE/BIC + 저게인 k̂(93~122) vs 고게인(170~220) 패턴 재현 여부.
"""
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
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
DAYS = ["26_07_22", "26_07_23", "26_07_24", "26_07_25", "26_07_27"]
tw = TW.twin()
E1, T1, TRIAL = [], [], []
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
        e1 = q1m[m] - np.interp((t-t0)[m], Lg["t"], Lg["q1"])   # rad
        # trial별 절편 제거 (백래시/캘리브 오프셋 흡수 — 형태만 비교)
        E1.append(e1 - e1[:5].mean()); T1.append(a1[m] - a1[m][:5].mean()); TRIAL.append(f"{day}/{fold.name}")
        print(f"{day}/{fold.name}: n={m.sum()}", flush=True)

e = np.concatenate(E1); tau = np.concatenate(T1)
N = len(e)
def sse_of(pred): return float(np.sum((e-pred)**2))
# ① 선형
X = np.column_stack([tau, np.ones(N)])
b, _, _, _ = np.linalg.lstsq(X, e, rcond=None)
sse1 = sse_of(X@b); k_lin = 1/abs(b[0])
# ② 2단 연속 (τ0 격자 + 조각 lsq)
best2 = (1e18, None)
for tau0 in np.arange(2, 14, 0.5):
    lo = np.clip(tau, -tau0, tau0)
    hi = tau - lo
    X2 = np.column_stack([lo, hi, np.ones(N)])
    b2, _, _, _ = np.linalg.lstsq(X2, e, rcond=None)
    s = sse_of(X2@b2)
    if s < best2[0]: best2 = (s, (tau0, b2))
sse2, (tau0, b2) = best2
k_lo, k_hi = 1/abs(b2[0]), 1/abs(b2[1])
# ③ 백래시
best3 = (1e18, None)
for d in np.arange(0, 6, 0.25):
    z = np.sign(tau)*np.maximum(np.abs(tau)-d, 0)
    X3 = np.column_stack([z, np.ones(N)])
    b3, _, _, _ = np.linalg.lstsq(X3, e, rcond=None)
    s = sse_of(X3@b3)
    if s < best3[0]: best3 = (s, (d, b3))
sse3, (dz, b3) = best3
def bic(sse, k): return N*np.log(sse/N) + k*np.log(N)
print(f"\n풀드 N={N} (19 trial · 5일)")
print(f"① 선형:   k={k_lin:6.0f}                SSE {sse1:.4f}  BIC {bic(sse1,2):.0f}")
print(f"② 2단:    k_lo={k_lo:5.0f} k_hi={k_hi:5.0f} @|τ|₀={tau0:.1f}Nm  SSE {sse2:.4f}  BIC {bic(sse2,4):.0f}")
print(f"③ 백래시: k={1/abs(b3[0]):6.0f} 데드밴드 d={dz:.2f}Nm     SSE {sse3:.4f}  BIC {bic(sse3,3):.0f}")
win = min([("선형",bic(sse1,2)),("2단",bic(sse2,4)),("백래시",bic(sse3,3))], key=lambda x: x[1])
print("BIC 승자:", win[0])
json.dump(dict(N=N, lin=dict(k=round(k_lin,1), sse=sse1, bic=bic(sse1,2)),
               two=dict(k_lo=round(k_lo,1), k_hi=round(k_hi,1), tau0=tau0, sse=sse2, bic=bic(sse2,4)),
               backlash=dict(k=round(1/abs(b3[0]),1), dead=dz, sse=sse3, bic=bic(sse3,3)),
               winner=win[0]), open(HERE/"_h2_shape.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# 그림
fig, ax = plt.subplots(figsize=(9, 6))
ax.scatter(tau, np.degrees(e), s=2, alpha=0.15, label="풀드 (19 trial)")
xs = np.linspace(tau.min(), tau.max(), 200)
ax.plot(xs, np.degrees(xs*b[0]+b[1]), lw=2, label=f"①선형 k={k_lin:.0f}")
lo = np.clip(xs, -tau0, tau0); hi = xs-lo
ax.plot(xs, np.degrees(lo*b2[0]+hi*b2[1]+b2[2]), lw=2, ls="--", label=f"②2단 {k_lo:.0f}/{k_hi:.0f}@{tau0:.0f}Nm")
z = np.sign(xs)*np.maximum(np.abs(xs)-dz, 0)
ax.plot(xs, np.degrees(z*b3[0]+b3[1]), lw=2, ls=":", label=f"③백래시 d={dz:.1f}Nm")
ax.set_xlabel("Δτ1 [Nm] (trial별 기준선 차감)"); ax.set_ylabel("Δe1 [°]")
ax.set_title(f"H2: hip 스프링 형태 — BIC 승자: {win[0]}")
ax.legend(); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(HERE/"h2_shape.png", dpi=115)
print("done → h2_shape.png")
