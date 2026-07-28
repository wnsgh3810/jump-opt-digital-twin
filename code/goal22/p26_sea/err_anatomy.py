# -*- coding: utf-8 -*-
"""err_anatomy — Mode A hip 오차 e1(t)의 경쟁 가설 판별 회귀 (터널비전 방지).

경쟁 가설과 그 서명 변수:
  S(직렬탄성/마운트회전) : τ1(t)            — 토크 비례, 토크 복귀 시 오차 복귀
  L(시간지연/감쇠 오모델): dq1(t)           — 속도 비례
  C(인코더 스케일/중력)  : q1(t)−q1(0)      — 자세 비례 (토크 복귀해도 잔류)
  F(마찰 오모델)         : sign(dq1)·|τ1|   — 속도방향 의존
  B(무릎/베이스 유래)    : τ2(t)            — 무릎 토크 비례 (베이스 모멘트·현행 지지법칙류)
시험: 배포 3일(exp1/exp4/exp5) 16 trial에서 ①단변량 R² ②5변수 공동 회귀 기여도
③계수의 게인·날짜 간 일관성. 승자 = 어디서나 지배하는 변수.
산출: _err_anatomy.json + err_anatomy.png
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
SESS = {"exp1(07-22)": ROOT/"26.07.22", "exp4(07-25)": ROOT/"26.07.25", "exp5(07-27)": ROOT/"26.07.27"}
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s

tw = TW.twin()
OUT = {}
VARS = ["tau1", "dq1", "q1rel", "fric", "tau2"]
for sess, base in SESS.items():
    for fold in sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
            n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
            t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
            q1m, q2m = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)
            v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
            raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
            a1 = ahat(raw1, v1); a2 = ahat(raw2, v2)
            qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
            i0 = int(on[0]) if len(on) else 0; t0 = t[i0]
            g = grf["Current_GRF"].to_numpy(float); g0 = np.median(g[-5:]); thr = g0+0.06*(np.nanmax(g)-g0)
            ab = np.where(g >= thr)[0]; t_lo = float(min((t[min(int(ab[-1])+1, len(t)-1)] - t0), t[-1]-t0-0.004))
            if t_lo < 0.06: continue
            st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
            Lg = TW.rollout_ol(tw, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05, record=False)
            if Lg is None: continue
            m = ((t-t0) >= 0.005) & ((t-t0) <= t_lo)
            e1 = np.degrees(q1m[m] - np.interp((t-t0)[m], Lg["t"], Lg["q1"]))   # [°]
            X = {"tau1": a1[m], "dq1": v1[m], "q1rel": np.degrees(q1m[m]-q1m[i0]),
                 "fric": np.sign(v1[m])*np.abs(a1[m]), "tau2": a2[m]}
            res = {"n": int(m.sum())}
            # ① 단변량 R²
            for k, x in X.items():
                Z = np.column_stack([x, np.ones_like(x)])
                b, _, _, _ = np.linalg.lstsq(Z, e1, rcond=None)
                res[f"R2_{k}"] = round(float(1 - np.sum((e1-Z@b)**2)/np.sum((e1-e1.mean())**2)), 3)
            # ② 공동 회귀 — 표준화 계수(|β|)로 기여 순위
            Xm = np.column_stack([(X[k]-X[k].mean())/max(X[k].std(), 1e-9) for k in VARS] + [np.ones(m.sum())])
            bj, _, _, _ = np.linalg.lstsq(Xm, e1, rcond=None)
            res["beta_joint"] = {k: round(float(bj[i]), 3) for i, k in enumerate(VARS)}
            res["R2_joint"] = round(float(1 - np.sum((e1-Xm@bj)**2)/np.sum((e1-e1.mean())**2)), 3)
            # ③ 물리 계수 (τ1 단독): k̂
            Z = np.column_stack([X["tau1"], np.ones(m.sum())])
            b1, _, _, _ = np.linalg.lstsq(Z, np.radians(e1), rcond=None)
            res["k_hat"] = round(float(1/abs(b1[0])), 1) if b1[0] else None
            OUT[f"{sess}/{fold.name}"] = res
            top = max(VARS, key=lambda k: res[f"R2_{k}"])
            print(f"{sess}/{fold.name}: 단변량R² τ1={res['R2_tau1']} dq1={res['R2_dq1']} q1={res['R2_q1rel']} "
                  f"fric={res['R2_fric']} τ2={res['R2_tau2']} | 승자={top} | 공동R²={res['R2_joint']} β={res['beta_joint']}", flush=True)
        except Exception as ex:
            print(fold, type(ex).__name__, ex)

json.dump(OUT, open(HERE/"_err_anatomy.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 요약 그림: 변수별 단변량 R² 분포 + 공동 표준화 계수 분포
fig, ax = plt.subplots(1, 2, figsize=(15, 5.4))
for i, k in enumerate(VARS):
    vals = [OUT[t][f"R2_{k}"] for t in OUT]
    ax[0].scatter([i]*len(vals), vals, s=30)
ax[0].set_xticks(range(len(VARS))); ax[0].set_xticklabels(["τ1\n(직렬탄성)","dq1\n(지연)","q1\n(스케일/중력)","sgn·|τ|\n(마찰)","τ2\n(무릎/베이스)"])
ax[0].set_ylabel("단변량 R²"); ax[0].set_title("① 가설별 단독 설명력 (16 trial, 3일)"); ax[0].grid(alpha=.3)
for i, k in enumerate(VARS):
    vals = [abs(OUT[t]["beta_joint"][k]) for t in OUT]
    ax[1].scatter([i]*len(vals), vals, s=30)
ax[1].set_xticks(range(len(VARS))); ax[1].set_xticklabels(["τ1","dq1","q1","sgn·|τ|","τ2"])
ax[1].set_ylabel("|표준화 계수| (공동 회귀)"); ax[1].set_title("② 5변수 동시 경쟁 시 기여 크기"); ax[1].grid(alpha=.3)
fig.suptitle("Mode A hip 오차의 해부 — 경쟁 가설 판별 (배포 3일)", fontsize=13)
fig.tight_layout(); fig.savefig(HERE/"err_anatomy.png", dpi=115)
print("done → err_anatomy.png")
