# -*- coding: utf-8 -*-
"""exp5_analyze — 26.07.27 v9 실기(5게인: hip 100/120/150/200/250 × knee 250/3) 분석.

exp3/exp4 인라인 파이프라인의 파일화 재현 (규약 동일):
  · â = ahat(A_PAPER, raw, sgn(dq))  [p14_judge 상수 복제, 출처 주석]
  · 정렬 = 측정 desiredAngle ↔ v9 미끼 스플라인 교차상관 (관절별)
  · F_τ = sqrt(mean(e_hip²)+mean(e_knee²))/sqrt(mean(τ1*²)+mean(τ2*²)) over [0, t_lo)
  · 슬립 = 인코더 FK foot_x 변위 (레일 → base x 고정 가정), L_SEG=0.25 양링크
  · v_lo = FK base 높이 미분(5-샘플 평활)을 측정 이륙시각(GRF 지속-미만)에서 평가
산출: _exp5.json + graphs/exp5/exp5_qdqtau_<라벨>.png + exp5_summary.png
"""
import os, sys, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
DATA = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data/26.07.27")
OUT = HERE / "graphs" / "exp5"
OUT.mkdir(parents=True, exist_ok=True)

GAINS = sorted([p.name for p in DATA.iterdir() if p.is_dir() and (p / "hip.xlsx").exists()],
               key=lambda s: float(s.split("_")[0]))     # hip kp 오름차순 자동 발견 (60/80 추가)
HIPKP = [float(g.split("_")[0]) for g in GAINS]
L_SEG = 0.25                     # 두 링크 공통 (t0nc_cl_pdrep._L_SEG와 동일)

# ── a_hat (p14_ahat/p14_judge.py 복제 — Paper 식, sgn(v) only) ──
KT, GR, CF = 0.091, 9.0, 0.59
A_PAPER = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])

def ahat(raw, v):
    Iq = (CF / (GR * KT)) * np.asarray(raw, float)
    s = np.sign(v)
    return A_PAPER[0]*GR*KT*Iq - A_PAPER[1]*GR*np.abs(Iq)*Iq - A_PAPER[2]*s - A_PAPER[3]*np.abs(Iq)*s

# ── 계획 (v9 = t0nc_cl_v9.npz, jump_vector_CL_nocvt_pd_v9.xlsx의 원본) ──
Z = np.load(HERE / "t0nc_cl_v9.npz")
PT = Z["t"]                                   # −0.4 ~ 1.2, dt 0.5ms
def _sustained_lo(t, grf, thr=1.0, win=0.05):
    dt = float(t[1]-t[0]); w = int(round(win/dt)); on = grf > thr
    for i in range(len(grf)-w):
        if t[i] > 0.02 and not on[i:i+w].any():
            return float(t[i])
    return float(t[-1])
T_LO_PLAN = _sustained_lo(PT, Z["grf"])

def _smooth(x, w=5):
    k = np.ones(w)/w
    return np.convolve(x, k, mode="same")

def xcorr_lag(t_m, y_m, t_p, y_p, max_lag=0.03, dt=0.002):
    """측정 y_m을 몇 초 밀면 계획 y_p와 최상 일치하는가 (미분 신호 교차상관)."""
    lags = np.arange(-max_lag, max_lag+1e-9, dt)
    dy_m = np.gradient(y_m, t_m)
    best, bl = -np.inf, 0.0
    for lg in lags:
        yp = np.interp(t_m - lg, t_p, y_p)
        dyp = np.gradient(yp, t_m)
        c = np.corrcoef(dy_m, dyp)[0, 1]
        if np.isfinite(c) and c > best:
            best, bl = c, float(lg)
    return bl, best

def fk(q1_rad, q2_rad):
    c1, s1 = np.cos(q1_rad), np.sin(q1_rad)
    c12, s12 = np.cos(q1_rad+q2_rad), np.sin(q1_rad+q2_rad)
    foot_x = L_SEG*(c1+c12)
    bz = -L_SEG*(s1+s12)          # 발 접지 가정의 base 높이 (상대량만 사용)
    return foot_x, bz

def parse_realdata(p):
    txt = Path(p).read_text(encoding="utf-8", errors="ignore")
    d = {}
    m = re.search(r"실제 점프 높이\s*:\s*([\d.]+)m", txt);            d["h_real"] = float(m.group(1)) if m else np.nan
    m = re.search(r"Hip 절대 기계적 에너지\s*:\s*([\d.]+)", txt);      d["Wh_txt"] = float(m.group(1)) if m else np.nan
    m = re.search(r"Knee 절대 기계적 에너지\s*:\s*([\d.]+)", txt);     d["Wk_txt"] = float(m.group(1)) if m else np.nan
    m = re.search(r"Impulse[^:]*:\s*([\d.]+)", txt);                  d["impulse"] = float(m.group(1)) if m else np.nan
    return d

RES = {}
for lab in GAINS:
    fold = DATA / lab
    hip = pd.read_excel(fold / "hip.xlsx");  knee = pd.read_excel(fold / "knee.xlsx")
    grfd = pd.read_excel(fold / "GRF.xlsx")
    n = min(len(hip), len(knee), len(grfd))                # 행 수 불일치 방어 (120_2: 111/110/110)
    hip, knee, grfd = hip.iloc[:n], knee.iloc[:n], grfd.iloc[:n]
    rt0 = float(hip["Time"].iloc[0])
    tm = hip["Time"].to_numpy(float) - rt0                 # 로컬 시간 (아직 미정렬)
    q1m, q2m = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)
    qd1c, qd2c = hip["desiredAngle"].to_numpy(float), knee["desiredAngle"].to_numpy(float)
    if np.nanmax(np.abs(q2m)) < 7:                         # ★26.07.27 수출은 라디안 (이전 세션=deg)
        q1m, q2m, qd1c, qd2c = (np.degrees(x) for x in (q1m, q2m, qd1c, qd2c))
    v1, v2 = hip["currentAngleVelocity"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float)
    if np.nanmax(np.abs(v2)) > 100:                        # deg/s → rad/s 방어
        v1, v2 = np.radians(v1), np.radians(v2)
    a1 = ahat(hip["currentTorque"].to_numpy(float), v1)
    a2 = ahat(knee["currentTorque"].to_numpy(float), v2)
    # 정렬: desiredAngle(측정 로그) ↔ 미끼 스플라인. 초기 오프셋 추정 = 명령 온셋 근사 후 xcorr 정밀화
    on2 = np.where(np.abs(qd2c - qd2c[0]) > 0.5)[0]
    t_guess = -(tm[on2[0]] if len(on2) else 0.0)           # 로컬 온셋 → 계획 t=0 근사
    lag2, c2 = xcorr_lag(tm + t_guess, qd2c, PT, np.degrees(Z["qd2"]))
    lag1, c1 = xcorr_lag(tm + t_guess, qd1c, PT, np.degrees(Z["qd1"]))
    t = tm + t_guess - lag2                                # knee 기준 정렬 (exp4 규약)
    # 측정 이륙: GRF 상대 타이밍 — 마지막 하강 교차 (반동 딥 오검출 방지: 뒤에서 스캔)
    g = grfd["Current_GRF"].to_numpy(float)
    g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
    above = np.where(g >= thr)[0]
    i_last = int(above[-1]) if len(above) else len(g)-1
    t_lo = float(t[min(i_last+1, len(t)-1)])
    # FK: 슬립 + base 높이/속도
    fx, bz = fk(np.radians(q1m), np.radians(q2m))
    st = (t >= 0) & (t <= t_lo)
    slip = fx[st] - fx[st][0]
    vbz = np.gradient(_smooth(bz, 5), t)
    i_lo = int(np.searchsorted(t, t_lo)); i_lo = min(i_lo, len(t)-1)
    v_lo = float(vbz[max(0, i_lo-2)])
    # F_τ (측정 â vs 계획 τ*, [0, min(t_lo, 계획 이륙)))
    tc = np.arange(0.0, min(t_lo, T_LO_PLAN), 0.002)
    e1 = np.interp(tc, t, a1) - np.interp(tc, PT, Z["tau1_nm"])
    e2 = np.interp(tc, t, a2) - np.interp(tc, PT, Z["tau2_nm"])
    p1 = np.interp(tc, PT, Z["tau1_nm"]); p2 = np.interp(tc, PT, Z["tau2_nm"])
    den = max(np.sqrt(np.mean(p1**2) + np.mean(p2**2)), 1e-9)
    ftau = float(np.sqrt(np.mean(e1**2) + np.mean(e2**2)) / den)
    f_h = float(np.sqrt(np.mean(e1**2)) / max(np.sqrt(np.mean(p1**2)), 1e-9))
    f_k = float(np.sqrt(np.mean(e2**2)) / max(np.sqrt(np.mean(p2**2)), 1e-9))
    # 일/파워 (스탠스, |τ·dq| 적분) — Real Data.txt(전체창)와 별도로 동일정의 자가 계산
    Wh = float(np.trapezoid(np.abs(a1[st]*v1[st]), t[st]))
    Wk = float(np.trapezoid(np.abs(a2[st]*v2[st]), t[st]))
    rd = parse_realdata(fold / "Real Data.txt")
    RES[lab] = dict(rd, lag_ms=dict(hip=round((lag1-lag2)*1e3, 1), knee=0.0), corr=[round(c1,3), round(c2,3)],
                    t_lo=round(t_lo,4), ftau=round(ftau,4), ftau_hip=round(f_h,4), ftau_knee=round(f_k,4),
                    slip_mm=round(float(slip[-1])*1e3,1), slip_absmax_mm=round(float(np.abs(slip).max())*1e3,1),
                    v_lo=round(v_lo,3), Wh=round(Wh,2), Wk=round(Wk,2),
                    peak_hip=round(float(np.abs(a1[st]).max()),2), peak_knee=round(float(np.abs(a2[st]).max()),2),
                    a0=[round(float(a1[0]),2), round(float(a2[0]),2)])
    # ── qdqtau 그래프 (exp4 포맷: 2×3, 측정/명령/계획) ──
    fig, ax = plt.subplots(2, 3, figsize=(18, 10))
    xmax = min(float(t[-1]), 0.23)
    rows = [("knee", q2m, qd2c, v2, a2, np.degrees(Z["qd2"]), np.degrees(Z["q2"]), Z["dq2"], Z["tau2_nm"]),
            ("hip",  q1m, qd1c, v1, a1, np.degrees(Z["qd1"]), np.degrees(Z["q1"]), Z["dq1"], Z["tau1_nm"])]
    for r, (nm, qm, qc, vm, am, pqd, pq, pdq, ptau) in enumerate(rows):
        ax[r,0].plot(t, qm, label="측정")
        ax[r,0].plot(PT, pq, label="계획")
        ax[r,0].plot(t, qc, "k--", lw=1, label="명령")
        ax[r,0].set_title(f"{nm} 각도 [°]")
        ax[r,1].plot(t, vm, label="측정")
        ax[r,1].plot(PT, pdq, label="계획")
        ax[r,1].plot(PT, np.gradient(np.radians(pqd), PT), "k--", lw=1, label="명령")
        ax[r,1].set_title(f"{nm} 속도 [rad/s]")
        ax[r,2].plot(t, am, label="측정 â")
        ax[r,2].plot(PT, ptau, label="계획 τ*")
        for y in (15, -15):
            ax[r,2].axhline(y, color="r", ls=":", lw=1)
        ax[r,2].set_title(f"{nm} 토크 [Nm]")
        for cx in range(3):
            ax[r,cx].set_xlim(0, xmax); ax[r,cx].grid(alpha=.3); ax[r,cx].legend(fontsize=8)
            ax[r,cx].axvline(t_lo, color="gray", ls=":", lw=1)
            ax[r,cx].set_xlabel("t[s]")
    fig.suptitle(f"exp5 실기 {lab} | 정렬 knee xcorr (hip Δ{RES[lab]['lag_ms']['hip']:+.1f}ms) | 계획=v9 150/2.2/250/3 OLD α | 회색점선=측정이륙 {t_lo:.3f}s | 점프 높이 {rd['h_real']:.2f}m (계획 {float(Z['h_plan']):.2f}m)")
    fig.tight_layout()
    fig.savefig(OUT / f"exp5_qdqtau_{lab}.png", dpi=110); plt.close(fig)
    print(f"{lab}: h={rd['h_real']}m Fτ={ftau*100:.1f}% (hip {f_h*100:.0f}/knee {f_k*100:.0f}) "
          f"slip={RES[lab]['slip_mm']}mm v_lo={v_lo:.2f} t_lo={t_lo:.3f} W(h/k)={Wh:.1f}/{Wk:.1f}J "
          f"peak(h/k)={RES[lab]['peak_hip']}/{RES[lab]['peak_knee']}Nm", flush=True)

json.dump(RES, open(HERE / "_exp5.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 요약 4패널: 예측 채점 (h / F_τ / slip / v_lo vs hip 게인) ──
hips = HIPKP
fig, ax = plt.subplots(1, 4, figsize=(20, 4.2))
h = [RES[g]["h_real"] for g in GAINS]
ax[0].plot(hips, h, "o-"); ax[0].set_title("점프 높이 [m]"); ax[0].axhline(float(Z["h_plan"]), ls="--", lw=1, color="gray")
ax[0].text(hips[0], float(Z["h_plan"])+0.002, f"계획 {float(Z['h_plan']):.3f}", fontsize=8, color="gray")
ax[1].plot(hips, [RES[g]["ftau"]*100 for g in GAINS], "o-", label="합성")
ax[1].plot(hips, [RES[g]["ftau_hip"]*100 for g in GAINS], "s--", label="hip")
ax[1].plot(hips, [RES[g]["ftau_knee"]*100 for g in GAINS], "^--", label="knee")
ax[1].set_title("F_τ [%] (측정 â vs 계획 τ*)"); ax[1].legend(fontsize=8)
ax[2].plot(hips, [RES[g]["slip_absmax_mm"] for g in GAINS], "o-"); ax[2].set_title("슬립 |max| [mm] (인코더 FK)")
ax[3].plot(hips, [RES[g]["v_lo"] for g in GAINS], "o-"); ax[3].set_title("이지 속도 [m/s] (FK)")
for a in ax:
    a.grid(alpha=.3); a.set_xlabel("hip kp (knee 250/3 고정)"); a.set_xticks(hips)
fig.suptitle("exp5 (26.07.27, v9 배포) — hip 게인 스윕 요약")
fig.tight_layout(); fig.savefig(OUT / "exp5_summary.png", dpi=110); plt.close(fig)
print("done →", OUT)
