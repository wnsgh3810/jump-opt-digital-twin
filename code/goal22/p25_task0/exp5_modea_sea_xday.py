# -*- coding: utf-8 -*-
"""exp5_modea_sea_xday — hip 직렬탄성(e1~â1, k_s≈160)의 교차-세션(다른 날) 검증.

exp5(26.07.27)에서 확립한 Mode A 검증을 7일치 세션에 동일 적용:
  배포: 26.07.22 / 07.23 / 07.24 / 07.25  · fit: 26.04.24 / 26.06.02(position)
  · held-out: 26.03.24 Jump_No_Tr (검증 전용 — fit 아님, k_s 고정 예측 확인)
제외: 26.04.29(CVT: knee=크랭크), Jump_Tr(l_i 불량).
방법 = exp5_modea_sea와 동일: 측정 raw 주입 Mode A(rollout_ol) → e1=q1측정−q1심 →
e1 ~ â1 회귀 (기울기→k̂=강성 추정, r=상관). 스프링이 구조물이면 날짜 무관 k̂≈160±20.
산출: _modea_sea_xday.json + graphs/exp5/modea_sea_xday.png
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
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(DATA_ROOT)
SESS = {  # 표시명: 베이스 경로
    "07-22 배포(exp1)": ROOT/"26_07_22",
    "07-23 배포(exp2)": ROOT/"26_07_23",
    "07-24 배포(exp3)": ROOT/"26_07_24",
    "07-25 배포(exp4)": ROOT/"26_07_25",
    "07-27 배포(exp5)": ROOT/"26_07_27",
    "04-24 fit": ROOT/"26_04_24",
    "06-02 fit": ROOT/"26_06_02"/"position",
    "03-24 held-out": ROOT/"26_03_24"/"Jump"/"Jump_No_Tr",
}
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s
def smooth(x, w=5): return np.convolve(x, np.ones(w)/w, mode="same")

tw = TW.twin()
OUTJ = {}
for sess, base in SESS.items():
    if not base.is_dir():
        continue
    trials = sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists() and (p/"knee.xlsx").exists()])
    for fold in trials:
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
            n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
            t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
            q1m, q2m = hip["currentAngle"].to_numpy(float), knee["currentAngle"].to_numpy(float)
            if np.nanmax(np.abs(q2m)) > 7:           # deg 방어 (전 세션 rad 확인됐지만)
                q1m, q2m = np.radians(q1m), np.radians(q2m)
            v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
            raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
            a1 = ahat(raw1, v1)
            # 온셋: 명령 knee 움직임 우선, 없으면(FF 세션) 측정 q2 움직임 − 10ms
            qd2 = knee["desiredAngle"].to_numpy(float)
            on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0] if np.nanstd(qd2) > 1e-6 else []
            if len(on):
                i0 = int(on[0])
            else:
                mv = np.where(np.abs(q2m-q2m[0]) > np.radians(1.0))[0]
                i0 = max(0, int(mv[0])-5) if len(mv) else 0
            t0 = t[i0]
            # 이륙: GRF 마지막 하강 교차, 없으면 |dq2| 피크 + 20ms
            gf = fold/"GRF.xlsx"
            if gf.exists():
                g = pd.read_excel(gf)["Current_GRF"].to_numpy(float)[:n]
                g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
                ab = np.where(g >= thr)[0]
                t_lo = t[min(int(ab[-1])+1, len(t)-1)] - t0 if len(ab) else t[-1]-t0
            else:
                t_lo = t[int(np.argmax(smooth(np.abs(v2), 5)))] - t0 + 0.02
            t_lo = float(min(t_lo, t[-1]-t0-0.004))
            if t_lo < 0.06:
                continue
            st = TW.settle_state(tw, float(q1m[i0]), float(q2m[i0]))
            Lg = TW.rollout_ol(tw, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05, record=False)
            if Lg is None:
                print(f"  {sess}/{fold.name}: rollout 실패"); continue
            m = ((t-t0) >= 0.005) & ((t-t0) <= t_lo)
            q1s = np.interp((t-t0)[m], Lg["t"], Lg["q1"])
            e1 = q1m[m] - q1s
            X = np.column_stack([a1[m], np.ones(m.sum())])
            (b, c), _, _, _ = np.linalg.lstsq(X, e1, rcond=None)
            r = float(np.corrcoef(a1[m], e1)[0, 1])
            rms0 = np.degrees(np.sqrt(np.mean(e1**2))); rms1 = np.degrees(np.sqrt(np.mean((e1-b*a1[m]-c)**2)))
            k_hat = 1/abs(b) if b else np.nan
            OUTJ.setdefault(sess, []).append(dict(trial=fold.name, k_hat=round(float(k_hat),1), r=round(r,3),
                                                  slope=round(float(b),5), rms=round(float(rms0),2), rms_corr=round(float(rms1),2),
                                                  t_lo=round(t_lo,3), n=int(m.sum())))
            print(f"  {sess}/{fold.name}: r={r:+.2f} k̂={k_hat:.0f} RMSE {rms0:.1f}°→{rms1:.1f}°", flush=True)
        except Exception as ex:
            print(f"  {sess}/{fold.name}: 오류 {type(ex).__name__} {ex}"); continue

json.dump(OUTJ, open(HERE/"_modea_sea_xday.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 요약 그림: 세션별 k̂ 산점 + r ──
fig, ax = plt.subplots(1, 2, figsize=(16, 5.6))
names = [s for s in SESS if s in OUTJ]
for i, s in enumerate(names):
    ks = [d["k_hat"] for d in OUTJ[s] if d["r"] > 0.5 and d["k_hat"] < 600]
    ks_low = [d["k_hat"] for d in OUTJ[s] if d["r"] <= 0.5 and d["k_hat"] < 600]
    ax[0].scatter([i]*len(ks), ks, s=45, zorder=3)
    ax[0].scatter([i]*len(ks_low), ks_low, s=25, marker="x", color="gray", zorder=2)
    rr = [d["r"] for d in OUTJ[s]]
    ax[1].scatter([i]*len(rr), rr, s=45, zorder=3)
ax[0].axhspan(140, 180, alpha=0.15, color="tab:green")
ax[0].text(0.05, 178, "exp5 삼중수렴 대역 160±20", fontsize=9, color="green", va="top")
ax[0].set_xticks(range(len(names))); ax[0].set_xticklabels(names, rotation=20, fontsize=8)
ax[0].set_ylabel("k_hat [Nm/rad] (추정 강성 = 1/기울기)"); ax[0].set_title("① 세션(날짜)별 hip 강성 추정 — 대역 안이면 같은 스프링")
ax[0].set_ylim(0, 400); ax[0].grid(alpha=.3)
ax[1].axhline(0.85, ls="--", color="gray"); ax[1].text(0.05, 0.86, "exp5 수준 r=0.87~0.92", fontsize=8, color="gray")
ax[1].set_xticks(range(len(names))); ax[1].set_xticklabels(names, rotation=20, fontsize=8)
ax[1].set_ylabel("상관 r (e1 ~ â1)"); ax[1].set_title("② 오차-토크 상관 — 높을수록 '오차=비틀림' 서명 뚜렷")
ax[1].set_ylim(-0.2, 1.0); ax[1].grid(alpha=.3)
fig.suptitle("hip 직렬탄성 교차-세션 검증 (7일치): Mode A 오차 e1 ~ 측정 토크 â1 회귀", fontsize=13)
fig.tight_layout(); fig.savefig(HERE/"graphs"/"exp5"/"modea_sea_xday.png", dpi=115)
print("done → graphs/exp5/modea_sea_xday.png")
