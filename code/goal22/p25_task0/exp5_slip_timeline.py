# -*- coding: utf-8 -*-
"""exp5_slip_timeline — 26.07.27 7게인 슬립의 시간축 시각화.

각 trial: 인코더 FK foot_x 변위(=슬립, mm)와 슬립 속도(mm/s)를 스탠스 시간축으로.
  · 슬립 = foot_x(t) − foot_x(push onset), 부호 유지(방향 보임)
  · 시간 = 명령 onset을 t=0 (push 시작), 회색점선 = GRF 지속-이륙
  · 표기: 최대편위(★), 끝점(o), 방향 반전(가역) 여부
개별 7장 + 전체 오버레이 1장 → graphs/exp5/slip_timeline/
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_07_27")
OUT = HERE / "graphs" / "exp5" / "slip_timeline"; OUT.mkdir(parents=True, exist_ok=True)
L_SEG = 0.25
GAINS = sorted([p.name for p in DATA.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()],
               key=lambda s: float(s.split("_")[0]))
def smooth(x, w=5): return np.convolve(x, np.ones(w)/w, mode="same")

def load(lab):
    hip = pd.read_excel(DATA/lab/"hip.xlsx"); knee = pd.read_excel(DATA/lab/"knee.xlsx"); grf = pd.read_excel(DATA/lab/"GRF.xlsx")
    n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1, q2 = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)   # rad
    qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    t0 = t[on[0]] if len(on) else 0.0
    g = grf["Current_GRF"].to_numpy(float); g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
    ab = np.where(g >= thr)[0]; t_lo = t[min(int(ab[-1])+1, len(t)-1)] if len(ab) else t[-1]
    fx = L_SEG*(np.cos(q1)+np.cos(q1+q2))
    tl = t - t0                                             # push onset = 0
    m = (tl >= -0.01) & (tl <= t_lo - t0 + 0.005)
    slip = (fx - fx[np.searchsorted(tl, 0.0)]) * 1e3        # mm, onset 기준
    return tl[m], slip[m], t_lo - t0

# ── 개별 7장 (슬립 변위 + 속도) ──
for lab in GAINS:
    tl, slip, tlo = load(lab)
    vel = np.gradient(smooth(slip, 5), tl)                  # mm/s
    ipk = int(np.argmax(np.abs(slip)))
    net, amx = slip[-1], slip[ipk]
    recov = abs(amx) - abs(net)
    revers = "가역(복귀)" if recov > abs(amx)*0.4 else ("영구(눌러앉음)" if abs(net) > abs(amx)*0.7 else "부분복귀")
    fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    c = ax[0].plot(tl, slip, lw=2)[0].get_color()
    ax[0].plot(tl[ipk], amx, "*", ms=16, color=c); ax[0].annotate(f"최대편위 {amx:+.0f}mm", (tl[ipk], amx), textcoords="offset points", xytext=(8, 0), fontsize=10)
    ax[0].plot(tl[-1], net, "o", ms=9, color=c); ax[0].annotate(f"끝점(순) {net:+.0f}mm", (tl[-1], net), textcoords="offset points", xytext=(-95, 0), fontsize=10)
    ax[0].axhline(0, color="gray", lw=0.8); ax[0].axvline(tlo, color="gray", ls=":", lw=1.2)
    ax[0].text(tlo, ax[0].get_ylim()[1], " 이륙", color="gray", fontsize=9, va="top")
    ax[0].set_ylabel("슬립 변위 [mm] (−=뒤로)"); ax[0].set_title(f"슬립 {revers} | 최대 {abs(amx):.0f} → 끝 {abs(net):.0f}mm (복귀 {recov:.0f}mm)")
    ax[1].plot(tl, vel, lw=1.5, color=c); ax[1].axhline(0, color="gray", lw=0.8); ax[1].axvline(tlo, color="gray", ls=":", lw=1.2)
    ax[1].fill_between(tl, vel, 0, alpha=0.2, color=c)
    ax[1].set_ylabel("슬립 속도 [mm/s]"); ax[1].set_xlabel("t [s] (push 시작=0)")
    fig.suptitle(f"exp5 슬립 타임라인 — {lab} (hip kp {lab.split('_')[0]})", fontsize=13)
    fig.tight_layout(); fig.savefig(OUT/f"slip_{lab}.png", dpi=115); plt.close(fig)
    print(f"{lab.split('_')[0]:>4}: 최대 {abs(amx):.0f}mm@{tl[ipk]*1e3:.0f}ms → 끝 {abs(net):.0f}mm | {revers}", flush=True)

# ── 전체 오버레이 ──
fig, ax = plt.subplots(1, 2, figsize=(17, 6))
for lab in GAINS:
    tl, slip, tlo = load(lab); vel = np.gradient(smooth(slip, 5), tl)
    lab0 = lab.split("_")[0]
    l = ax[0].plot(tl, slip, lw=1.8, label=f"kp {lab0}")[0]
    ax[0].plot(tlo, np.interp(tlo, tl, slip), "o", ms=6, color=l.get_color())
    ax[1].plot(tl, vel, lw=1.3, color=l.get_color(), label=f"kp {lab0}")
ax[0].axhline(0, color="gray", lw=0.8); ax[0].set_title("슬립 변위 오버레이 — 저게인=왕복복귀 / 고게인=편도누적")
ax[0].set_xlabel("t [s] (push=0)"); ax[0].set_ylabel("슬립 [mm]"); ax[0].legend(fontsize=8, ncol=2); ax[0].grid(alpha=.3)
ax[1].axhline(0, color="gray", lw=0.8); ax[1].set_title("슬립 속도 오버레이 (음=뒤로 미끄러지는 중)")
ax[1].set_xlabel("t [s] (push=0)"); ax[1].set_ylabel("슬립 속도 [mm/s]"); ax[1].legend(fontsize=8, ncol=2); ax[1].grid(alpha=.3)
fig.suptitle("exp5 슬립 타임라인 전체 오버레이 (26.07.27, hip 60~250)", fontsize=13)
fig.tight_layout(); fig.savefig(OUT/"slip_overlay.png", dpi=120); plt.close(fig)
print("done →", OUT)
