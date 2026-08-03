# -*- coding: utf-8 -*-
"""promo_figs_modea2 — Mode A 확장 분석: dq1 (보정 전/후) + knee q2/dq2 (모델 공통).

H12 러너 규약 그대로 (세션 8개, 온셋~이륙 창). 채점:
  dq1: ①보정 없음 vs ②2단 보정의 시간미분 dq1_sim + d/dt[defl_2s(â1 평활 w5)]
  knee q2·dq2: 변형 C의 Mode A 보정은 hip뿐 → 두 모델 동일 (플랜트 단일 평가)
Fig A: 세션별 dq1 바 (OLD vs C) + knee q2/dq2 바 (공통)
Fig B: 시계열 3종 (0602/exp5/0324) — 행: dq1, dq2
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
SESS = {
    "fit 0424": ROOT/"26_04_24",
    "fit 0602": ROOT/"26_06_02"/"position",
    "HO 0324": ROOT/"26_03_24"/"Jump"/"Jump_No_Tr",
    "exp1": ROOT/"26_07_22", "exp2": ROOT/"26_07_23", "exp3": ROOT/"26_07_24",
    "exp4": ROOT/"26_07_25", "exp5": ROOT/"26_07_27",
}
def defl_2s(tau):
    a = np.abs(tau)
    d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d
def smooth(x, w=5): return np.convolve(x, np.ones(w)/w, mode="same")

tw = TW.twin()

def run_trial(fold):
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
    if t_lo < 0.06: return None
    st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
    Lg = TW.rollout_ol(tw, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05)
    if Lg is None: return None
    m = ((t-t0) >= 0.005) & ((t-t0) <= t_lo)
    tt = t - t0
    dq1s = np.interp(tt, Lg["t"], Lg["dq1"])
    dq2s = np.interp(tt, Lg["t"], Lg["dq2"])
    q2s = np.interp(tt, Lg["t"], Lg["q2"])
    # 보정 미분항: d/dt defl_2s(â1 평활)
    dcor = np.gradient(defl_2s(smooth(a1, 5)), tt)
    r = dict(
        dq1_raw=float(np.sqrt(np.mean((v1[m]-dq1s[m])**2))),
        dq1_two=float(np.sqrt(np.mean((v1[m]-(dq1s+dcor)[m])**2))),
        dq2=float(np.sqrt(np.mean((v2[m]-dq2s[m])**2))),
        q2=float(np.degrees(np.sqrt(np.mean((q2m[m]-q2s[m])**2)))))
    r["_ts"] = dict(t=tt, m=m, v1=v1, v2=v2, dq1s=dq1s, dq1c=dq1s+dcor, dq2s=dq2s, t_lo=t_lo)
    return r

RES = {}
for sess, base in SESS.items():
    if not base.is_dir(): continue
    for fold in sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists() and (p/"knee.xlsx").exists()]):
        try:
            r = run_trial(fold)
        except Exception as ex:
            print(f"{sess}/{fold.name}: 오류 {type(ex).__name__}", flush=True); continue
        if r is None: continue
        RES.setdefault(sess, []).append((fold.name, {k: v for k, v in r.items() if k != "_ts"}))
        print(f"{sess}/{fold.name}: dq1 {r['dq1_raw']:.2f}->{r['dq1_two']:.2f} | dq2 {r['dq2']:.2f} | q2 {r['q2']:.2f}", flush=True)

json.dump({s: [dict(trial=n, **d) for n, d in v] for s, v in RES.items()},
          open(HERE/"_promo_modea_dq.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── Fig A: 바 3종 ──
names = [s for s in SESS if s in RES]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
x = np.arange(len(names))
mean = lambda s, k: float(np.mean([d[k] for _, d in RES[s]]))
ax = axes[0]
b1 = ax.bar(x-0.19, [mean(s, "dq1_raw") for s in names], width=0.38, label="OLD (보정 없음)")
b2 = ax.bar(x+0.19, [mean(s, "dq1_two") for s in names], width=0.38, label="변형 C (2단 보정 미분)")
for b in list(b1)+list(b2):
    ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{b.get_height():.2f}", ha="center", va="bottom", fontsize=7)
ax.set_title("Mode A dq1 RMSE [rad/s] — hip 속도 관측"); ax.legend(fontsize=8)
ax = axes[1]
b = ax.bar(x, [mean(s, "q2") for s in names], width=0.5)
for bb in b: ax.text(bb.get_x()+bb.get_width()/2, bb.get_height(), f"{bb.get_height():.2f}", ha="center", va="bottom", fontsize=7)
ax.set_title("Mode A q2 RMSE [°] — knee (두 모델 동일 = 플랜트 성적)")
ax = axes[2]
b = ax.bar(x, [mean(s, "dq2") for s in names], width=0.5)
for bb in b: ax.text(bb.get_x()+bb.get_width()/2, bb.get_height(), f"{bb.get_height():.2f}", ha="center", va="bottom", fontsize=7)
ax.set_title("Mode A dq2 RMSE [rad/s] — knee 속도 (두 모델 동일)")
for ax in axes:
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8, rotation=15); ax.grid(alpha=.3, axis="y")
fig.suptitle("Mode A 확장 — dq·knee (측정 τ 주입, PD 무관 · 낮을수록 좋음)", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(HERE/"promo_modea_dq_bars.png", dpi=115)
print("saved promo_modea_dq_bars.png", flush=True)

# ── Fig B: 시계열 (0602 / exp5 / 0324 — 대표 trial) ──
CASES = [("fit 0602", "fit 0602", "150_2.2_250_3"), ("배포 exp5", "exp5", "150_2.2_250_3"), ("held-out 0324", "HO 0324", "P40_D0.7")]
fig, axes = plt.subplots(2, 3, figsize=(17, 8))
for ci, (lab, sess, tn) in enumerate(CASES):
    base = SESS[sess]
    fold = base/tn
    r = run_trial(fold) if fold.is_dir() else None
    if r is None:
        axes[0][ci].set_title(f"{lab}: 없음"); continue
    ts = r["_ts"]; m = (ts["t"] >= 0) & (ts["t"] <= ts["t_lo"]+0.01)
    tms = ts["t"][m]*1000
    ax = axes[0][ci]
    ax.plot(tms, ts["v1"][m], lw=1.8, label="실측 dq1")
    ax.plot(tms, ts["dq1s"][m], lw=1.2, ls="--", label="OLD")
    ax.plot(tms, ts["dq1c"][m], lw=1.4, label="변형 C")
    ax.set_title(f"{lab} · {tn} | dq1 RMSE {r['dq1_raw']:.2f}→{r['dq1_two']:.2f}", fontsize=10)
    ax.set_ylabel("dq1 [rad/s]"); ax.grid(alpha=.3)
    ax = axes[1][ci]
    ax.plot(tms, ts["v2"][m], lw=1.8, label="실측 dq2")
    ax.plot(tms, ts["dq2s"][m], lw=1.4, label="트윈 (공통)")
    ax.set_title(f"dq2 RMSE {r['dq2']:.2f} (모델 공통)", fontsize=10)
    ax.set_ylabel("dq2 [rad/s]"); ax.set_xlabel("t [ms]"); ax.grid(alpha=.3)
axes[0][0].legend(fontsize=8); axes[1][0].legend(fontsize=8)
fig.suptitle("Mode A 시계열 — dq1 (관측보정 전/후) · dq2 (플랜트 공통)", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(HERE/"promo_modea_dq_ts.png", dpi=115)
print("saved promo_modea_dq_ts.png", flush=True)
print("done")
