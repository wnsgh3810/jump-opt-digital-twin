# -*- coding: utf-8 -*-
"""promo_figs_modea — 승격 판단용 Mode A 비교 (H12 규약 재사용).

Mode A(측정 토크 주입, PD 무관)에서 두 모델의 차이 = 관측층뿐 (플랜트 동일):
  OLD      = 보정 없음 (인코더각 = 관절각 가정)
  변형 C   = hip 2단 관측보정 q1_sim + defl_2s(τ̂1) (인코더=모터측 → 스프링 처짐 보정)
Fig A: 세션 8개 hip q1 RMSE 바 (H12 JSON 재사용, 40 trial)
Fig B: 대표 trial 시계열 3종 — fit 0602 / 배포 exp5 / HO 0324(과보정 정직 노출)
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

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
tw0 = TW.twin()

def defl_2s(tau):
    a = np.abs(tau); d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d

# ── Fig A: 세션 바차트 (H12 JSON) ──
H12 = json.load(open(HERE/"_h12_bidir.json", encoding="utf-8"))
names = list(H12.keys())
raw = [float(np.mean([t["raw"] for t in H12[k]])) for k in names]
two = [float(np.mean([t["two"] for t in H12[k]])) for k in names]
fig, ax = plt.subplots(figsize=(12, 5.5))
x = np.arange(len(names))
b1 = ax.bar(x-0.19, raw, width=0.38, label="OLD (보정 없음)")
b2 = ax.bar(x+0.19, two, width=0.38, label="변형 C (2단 관측보정)")
for b in list(b1)+list(b2):
    ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{b.get_height():.2f}", ha="center", va="bottom", fontsize=8)
for i, (r, w) in enumerate(zip(raw, two)):
    ax.text(i, max(r, w)+0.55, f"{(w-r)/r*100:+.0f}%", ha="center", fontsize=9,
            fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel("Mode A hip q1 RMSE [°]")
ax.set_title("Mode A (측정 τ 주입, PD 무관) — hip 관측 정확도: 세션 8개·40 trial (낮을수록 좋음)")
ax.grid(alpha=.3, axis="y"); ax.legend()
fig.tight_layout(); fig.savefig(HERE/"promo_modea_bars.png", dpi=115)
print("saved promo_modea_bars.png", flush=True)

# ── Fig B: 시계열 3종 ──
CASES = [("fit 0602", "R19:jump_0602:150_2.2_250_3", "150_2.2_250_3"),
         ("배포 exp5 (07-27)", ROOT/"26.07.27"/"150_2.2_250_3", "150_2.2_250_3"),
         ("held-out 0324 (과보정 최악례)", "R19:jump_0324:P40_D0.7", "P40_D0.7")]

def find_xlsx(fold):
    if (fold/"hip.xlsx").exists():
        return fold
    for sub in fold.rglob("hip.xlsx"):
        return sub.parent
    return None

def load_case(spec):
    """xlsx 폴더 경로 또는 'R19:ds:sub' — (t[온셋 0], q1m, q2m, raw1, raw2, a1, t_lo) 반환."""
    if isinstance(spec, str) and spec.startswith("R19:"):
        _, ds_t, sub_t = spec.split(":")
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
            if ds == ds_t and str(sub) == sub_t:
                t = np.asarray(d["t"], float); t = t - t[0]
                raw1 = np.asarray(d["traw1"], float); raw2 = np.asarray(d["traw2"], float)
                a1 = ahat_np(raw1, np.asarray(d["dq1"], float))
                return t, np.asarray(d["q1"], float), np.asarray(d["q2"], float), raw1, raw2, a1, float(t[-1]-0.004)
        return None
    fold = find_xlsx(spec)
    if fold is None:
        return None
    hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
    dq1m = hip["currentAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
    a1 = ahat_np(raw1, dq1m)
    qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    i0 = int(on[0]) if len(on) else 0
    try:
        grf = pd.read_excel(fold/"GRF.xlsx"); g = grf["Current_GRF"].to_numpy(float)[:n]
        gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(min(t[min(int(ab[-1])+1, n-1)]-t[i0], t[-1]-t[i0]-0.004))
    except Exception:
        t_lo = float(t[-1]-t[i0]-0.004)
    s = slice(i0, None)
    return t[s]-t[i0], q1m[s], q2m[s], raw1[s], raw2[s], a1[s], t_lo

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
for ax, (lab, spec, tn) in zip(axes, CASES):
    got = load_case(spec)
    if got is None:
        ax.set_title(f"{lab}: 데이터 못 찾음"); continue
    t, q1m, q2m, raw1, raw2, a1, t_lo = got
    t0 = 0.0
    st = TW.settle_state(tw0, float(q1m[0]), float(q2m[0]))
    Lg = TW.rollout_ol(tw0, t-t0, raw1, raw2, st, t_end=t_lo, t_after=0.05)
    if Lg is None:
        ax.set_title(f"{lab}: 발산"); continue
    m = ((t-t0) >= 0) & ((t-t0) <= t_lo+0.01)
    tms = (t-t0)[m]*1000
    q1s = np.interp(t-t0, Lg["t"], Lg["q1"])
    q1c = q1s + defl_2s(a1)
    msk = ((t-t0) >= 0.005) & ((t-t0) <= t_lo-0.005)
    r0 = float(np.degrees(np.sqrt(np.mean((q1m[msk]-q1s[msk])**2))))
    r2 = float(np.degrees(np.sqrt(np.mean((q1m[msk]-q1c[msk])**2))))
    ax.plot(tms, np.degrees(q1m[m]), lw=2.2, label="실측 q1 (모터 인코더)")
    ax.plot(tms, np.degrees(q1s[m]), lw=1.3, ls="--", label="OLD (보정 없음)")
    ax.plot(tms, np.degrees(q1c[m]), lw=1.5, label="변형 C (2단 보정)")
    ax.set_title(f"{lab} · {tn}\nRMSE OLD {r0:.2f}° → C {r2:.2f}°", fontsize=10)
    ax.set_xlabel("t [ms]"); ax.set_ylabel("q1 [°]"); ax.grid(alpha=.3)
    done_any = True
axes[0].legend(fontsize=9)
fig.suptitle("Mode A 시계열 — hip 인코더각: 같은 플랜트, 관측층만 차이 (0324는 과보정 정직 노출)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(HERE/"promo_modea_ts.png", dpi=115)
print("saved promo_modea_ts.png", flush=True)
print("done")
