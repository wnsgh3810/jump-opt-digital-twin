# -*- coding: utf-8 -*-
"""exp5_modea_sea — Mode A로 직렬탄성 가설 검증 (26.07.27 7게인).

원리: Mode A(측정 raw 토크 주입, α무관)는 트윈 '사지'를 재생. 실물 인코더는 '모터측'.
직렬탄성이 실재하면  e1(t) = q1_측정 − q1_ModeA ≈ â1(t)/k_s  (오차가 토크 파형에 비례).
검증 3단: ① per-trial 회귀 e1~â1 (기울기→k̂, 상관 r) ② 게인 무관 k̂ 일관성
③ 측정각 보정(q1−â1/k̂) 후 Mode A RMSE 감소량. 모델 수술 없음 (게이트 불변).
산출: _exp5_modea_sea.json + graphs/exp5/modea_sea_verify.png
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402 (env 플래그+경로 주입)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.07.27")
OUT = HERE / "graphs" / "exp5"
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s

GAINS = sorted([p.name for p in DATA.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()],
               key=lambda s: float(s.split("_")[0]))
tw = TW.twin()
R = {}
for lab in GAINS:
    hip = pd.read_excel(DATA/lab/"hip.xlsx"); knee = pd.read_excel(DATA/lab/"knee.xlsx"); grf = pd.read_excel(DATA/lab/"GRF.xlsx")
    n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m, q2m = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)   # rad
    v1, v2 = hip["currentAngleVelocity"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float)
    raw1, raw2 = hip["currentTorque"].to_numpy(float), knee["currentTorque"].to_numpy(float)
    a1, a2 = ahat(raw1, v1), ahat(raw2, v2)
    qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    i0 = int(on[0]) if len(on) else 0; t0 = t[i0]
    g = grf["Current_GRF"].to_numpy(float); g0 = np.median(g[-5:]); thr = g0+0.06*(np.nanmax(g)-g0)
    ab = np.where(g >= thr)[0]; t_lo = t[min(int(ab[-1])+1, len(t)-1)] - t0
    tg = t - t0
    st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
    Lg = TW.rollout_ol(tw, tg, raw1, raw2, st, t_end=float(t_lo), t_after=0.05, record=True)
    if Lg is None:
        print(lab, "rollout 실패"); continue
    m = (tg >= 0.005) & (tg <= t_lo)
    q1s = np.interp(tg[m], Lg["t"], Lg["q1"]); q2s = np.interp(tg[m], Lg["t"], Lg["q2"])
    e1 = q1m[m] - q1s; e2 = q2m[m] - q2s                     # rad (측정−ModeA)
    # 회귀 e ~ â (+절편): 기울기 b → k̂ = 1/|b|
    def fit(e, a):
        X = np.column_stack([a, np.ones_like(a)])
        (b, c), _, _, _ = np.linalg.lstsq(X, e, rcond=None)
        r = np.corrcoef(a, e)[0, 1]
        rms0 = np.sqrt(np.mean(e**2)); rms1 = np.sqrt(np.mean((e - b*a - c)**2))
        return b, c, r, rms0, rms1
    b1, c1_, r1, rms1_0, rms1_1 = fit(e1, a1[m])
    b2, c2_, r2, rms2_0, rms2_1 = fit(e2, a2[m])
    R[lab] = dict(hipkp=float(lab.split("_")[0]), t_lo=round(float(t_lo), 4),
                  hip=dict(slope=round(b1, 5), k_hat=round(1/abs(b1), 1) if b1 else None, r=round(float(r1), 3),
                           rms_deg=round(np.degrees(rms1_0), 2), rms_corr_deg=round(np.degrees(rms1_1), 2)),
                  knee=dict(slope=round(b2, 5), k_hat=round(1/abs(b2), 1) if b2 else None, r=round(float(r2), 3),
                            rms_deg=round(np.degrees(rms2_0), 2), rms_corr_deg=round(np.degrees(rms2_1), 2)),
                  e1=np.degrees(e1).round(3).tolist(), a1=a1[m].round(3).tolist(),
                  tgm=tg[m].round(4).tolist())
    print(f"{lab.split('_')[0]:>4}: hip e1~â1 r={r1:+.2f} 기울기 {b1:+.5f} rad/Nm → k̂={1/abs(b1):.0f} | "
          f"RMSE {np.degrees(rms1_0):.2f}°→보정 {np.degrees(rms1_1):.2f}° || "
          f"knee r={r2:+.2f} k̂={1/abs(b2):.0f} RMSE {np.degrees(rms2_0):.2f}°→{np.degrees(rms2_1):.2f}°", flush=True)

json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("e1", "a1", "tgm")} for k, v in R.items()},
          open(HERE/"_exp5_modea_sea.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 그림: ①150 오버레이 ②풀드 스캐터 ③RMSE 전/후 ──
fig, ax = plt.subplots(1, 3, figsize=(19, 5.4))
lab0 = "150_2.2_250_3"
if lab0 in R:
    d = R[lab0]; ks = d["hip"]["k_hat"]
    ax[0].plot(d["tgm"], d["e1"], label="e1 = 측정 - ModeA [°]")
    ax[0].plot(d["tgm"], np.degrees(np.array(d["a1"])/ks*np.sign(d["hip"]["slope"])), "--",
               label=f"a1/k_s (k_s={ks:.0f} Nm/rad)")
    ax[0].set_title(f"① {lab0}: Mode A hip 오차 vs 토크/k_s (r={d['hip']['r']:+.2f})")
    ax[0].set_xlabel("t [s]"); ax[0].legend(fontsize=9)
allA = np.concatenate([np.array(R[g]["a1"]) for g in R])
allE = np.concatenate([np.array(R[g]["e1"]) for g in R])
ax[1].scatter(allA, allE, s=4, alpha=0.35)
bp = np.polyfit(allA, allE, 1)
xs = np.linspace(allA.min(), allA.max(), 50)
ax[1].plot(xs, np.polyval(bp, xs), lw=2)
kpool = 1/abs(np.radians(bp[0]))
ax[1].set_title(f"② 풀드 (7게인): e1 vs a1 — k_s(풀드)={kpool:.0f} Nm/rad, r={np.corrcoef(allA,allE)[0,1]:+.2f}")
ax[1].set_xlabel("â1 [Nm]"); ax[1].set_ylabel("e1 [°]")
kps = [R[g]["hipkp"] for g in R]
r0 = [R[g]["hip"]["rms_deg"] for g in R]; r1_ = [R[g]["hip"]["rms_corr_deg"] for g in R]
w = 8
ax[2].bar([k-w/2 for k in kps], r0, width=w, label="Mode A hip RMSE [°]")
ax[2].bar([k+w/2 for k in kps], r1_, width=w, label="τ/k_s 보정 후 [°]")
ax[2].set_title("③ 탄성 보정 후 Mode A hip 오차"); ax[2].set_xlabel("hip kp"); ax[2].legend(fontsize=9)
for a_ in ax: a_.grid(alpha=.3)
fig.suptitle("Mode A 검증 — hip 직렬탄성 가설 (오차 e1 = 토크/k_s 인가?)", fontsize=13)
fig.tight_layout(); fig.savefig(OUT/"modea_sea_verify.png", dpi=115)
print("done →", OUT/"modea_sea_verify.png")
