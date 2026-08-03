# -*- coding: utf-8 -*-
"""promo_figs — 승격 판단용 비교 그래프: OLD α 모델 vs 변형 C (실측 대조, dq·τ 중심).

동일 조건 (정렬무결 규약: 실기 로그 qd 미끼, 이륙까지 창):
  OLD  = TW.rollout_cl(폴더 게인, alphas=old_alpha)  — sh1/sh2 = 전류토크 대응
  변형C = rollout_cl_sea2(hip 원게인+SEA 96/323@9, knee OLD α) — thm1=인코더, tsp = 전류토크 대응
대표 trial = 각 날짜의 150_2.2_250_3 (5일 공통 게인).
Fig A: hip (q1/dq1/τ1) × 5일 · Fig B: knee (q2/dq2/τ2) × 5일 · Fig C: 6지표 날짜별 RMSE 바 (JSON 재사용).
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
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
TH = {60: 0.70, 120: 0.50, 150: 0.40}
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
def old_alpha(g):
    return (TH.get(g[0], 0.40), 0.20, TK.get(g[2], 0.656), 0.20)

tw0 = TW.twin()
DAYS = ["26_07_22", "26_07_23", "26_07_24", "26_07_25", "26_07_27"]
TRIAL = "150_2.2_250_3"

def load(day):
    fold = ROOT / day / TRIAL
    hip = pd.read_excel(fold / "hip.xlsx"); knee = pd.read_excel(fold / "knee.xlsx"); grf = pd.read_excel(fold / "GRF.xlsx")
    n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb + 0.06*(np.nanmax(g)-gb)
    ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)])
    dq1 = hip["currentAngleVelocity"].to_numpy(float); dq2 = knee["currentAngleVelocity"].to_numpy(float)
    return dict(t=t, t_lo=t_lo,
                qd1=hip["desiredAngle"].to_numpy(float), qd2=knee["desiredAngle"].to_numpy(float),
                dqd1=hip["desiredAngleVelocity"].to_numpy(float), dqd2=knee["desiredAngleVelocity"].to_numpy(float),
                q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                dq1=dq1, dq2=dq2,
                a1=ahat_np(hip["currentTorque"].to_numpy(float), dq1),
                a2=ahat_np(knee["currentTorque"].to_numpy(float), dq2))

def run_models(d):
    gains = (150.0, 2.2, 250.0, 3.0)
    Lo = TW.rollout_cl(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], gains,
                       alphas=old_alpha(gains), t_end=d["t_lo"], t_after=0.1)
    gm = (150.0, 2.2, 250.0*TK[250], 3.0*0.20)
    Lc = rollout_cl_sea2(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], gm,
                         t_end=d["t_lo"], t_after=0.1,
                         ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
    return Lo, Lc

def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))

# ── Fig A/B: 시계열 오버레이 ──
for fig_name, joint in [("promo_fig_hip.png", "hip"), ("promo_fig_knee.png", "knee")]:
    fig, axes = plt.subplots(3, 5, figsize=(22, 10), sharex="col")
    rows = ([("q1 [°]", "q1"), ("dq1 [rad/s]", "dq1"), ("τ1 [Nm] (전류토크)", "t1")] if joint == "hip"
            else [("q2 [°]", "q2"), ("dq2 [rad/s]", "dq2"), ("τ2 [Nm] (전류토크)", "t2")])
    for ci, day in enumerate(DAYS):
        d = load(day)
        Lo, Lc = run_models(d)
        m = (d["t"] >= 0.0) & (d["t"] <= d["t_lo"] + 0.02)
        tms = d["t"][m]*1000
        msk = (d["t"] >= 0.005) & (d["t"] <= d["t_lo"] - 0.005)
        for ri, (lab, key) in enumerate(rows):
            ax = axes[ri][ci]
            if joint == "hip":
                real = {"q1": np.degrees(d["q1"]), "dq1": d["dq1"], "t1": d["a1"]}[key]
                simo = {"q1": np.degrees(np.interp(d["t"], Lo["t"], Lo["q1"])),
                        "dq1": np.interp(d["t"], Lo["t"], Lo["dq1"]),
                        "t1": np.interp(d["t"], Lo["t"], Lo["sh1"])}[key]
                de1 = np.gradient(Lc["thm1"], Lc["t"])
                simc = {"q1": np.degrees(np.interp(d["t"], Lc["t"], Lc["thm1"])),
                        "dq1": np.interp(d["t"], Lc["t"], de1),
                        "t1": np.interp(d["t"], Lc["t"], Lc["tsp1"])}[key]
            else:
                real = {"q2": np.degrees(d["q2"]), "dq2": d["dq2"], "t2": d["a2"]}[key]
                simo = {"q2": np.degrees(np.interp(d["t"], Lo["t"], Lo["q2"])),
                        "dq2": np.interp(d["t"], Lo["t"], Lo["dq2"]),
                        "t2": np.interp(d["t"], Lo["t"], Lo["sh2"])}[key]
                de2 = np.gradient(Lc["q2"], Lc["t"])
                simc = {"q2": np.degrees(np.interp(d["t"], Lc["t"], Lc["q2"])),
                        "dq2": np.interp(d["t"], Lc["t"], de2),
                        "t2": np.interp(d["t"], Lc["t"], Lc["tsp2"])}[key]
            ax.plot(tms, real[m], lw=2.2, label="실측")
            ax.plot(tms, simo[m], lw=1.3, ls="--", label="OLD α")
            ax.plot(tms, simc[m], lw=1.5, label="변형 C")
            ro, rc = rmse(real[msk], simo[msk]), rmse(real[msk], simc[msk])
            ax.set_title(f"{day[6:]}일 | RMSE OLD {ro:.2f} → C {rc:.2f}", fontsize=9)
            if ci == 0: ax.set_ylabel(lab)
            if ri == 2: ax.set_xlabel("t [ms]")
            ax.grid(alpha=.3)
            ax.axvline(d["t_lo"]*1000, ls=":", lw=0.8)
    axes[0][0].legend(fontsize=9, loc="best")
    jname = "Hip" if joint == "hip" else "Knee"
    fig.suptitle(f"{jname} — 실측 vs OLD α vs 변형 C (150_2.2_250_3, 5일 공통 게인 · 정렬무결 · 점선=이륙)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(HERE/fig_name, dpi=110)
    print("saved", fig_name, flush=True)

# ── Fig C: 6지표 날짜별 RMSE 바 (기록 JSON 재사용 — 22 trial 전체) ──
FA = json.load(open(HERE/"_final_aligned.json", encoding="utf-8"))
VC = json.load(open(HERE/"_variantC_aligned.json", encoding="utf-8"))
METRICS = [("q1 [°]", 0), ("q2 [°]", 1), ("dq1 [rad/s]", 2), ("dq2 [rad/s]", 3), ("τ1 [Nm]", 4), ("τ2 [Nm]", 5)]
fig, axes = plt.subplots(2, 3, figsize=(16, 8))
x = np.arange(len(DAYS)+1)
for k, (lab, idx) in enumerate(METRICS):
    ax = axes[k//3][k % 3]
    old = [FA[d]["OLD"][idx] for d in DAYS]; new = [VC[d][idx] for d in DAYS]
    old.append(float(np.mean(old))); new.append(float(np.mean(new)))
    b1 = ax.bar(x-0.18, old, width=0.36, label="OLD α")
    b2 = ax.bar(x+0.18, new, width=0.36, label="변형 C")
    for b in list(b1)+list(b2):
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{b.get_height():.2f}",
                ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels([d[6:] for d in DAYS]+["평균"])
    ax.set_title(lab); ax.grid(alpha=.3, axis="y")
    if k == 0: ax.legend(fontsize=9)
fig.suptitle("날짜별 RMSE — OLD α vs 변형 C (전 trial 22개 · 정렬무결 · 낮을수록 좋음)", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(HERE/"promo_fig_summary.png", dpi=110)
print("saved promo_fig_summary.png", flush=True)
print("done")
