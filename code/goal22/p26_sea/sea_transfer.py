# -*- coding: utf-8 -*-
"""sea_transfer — SEA2 제로샷 전이 시험 (exp1~4, 손대지 않은 4일 + 다양한 knee 게인).

exp5로 찾은 스프링(k_s=169)을 그대로 들고, 각 세션의 자기 미끼(pd15/v4/v7/v8)로
CL 예측 → 실측 대조. 대조군 = OLD α 테이블(현행). 추가: knee SEA(650) 변형, k_s 민감도.
수렴 골든(온건판): ks=3000·bs=20·jm=0.02 → 정본 α=1과 근접해야.
"""
import os, sys, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25))
sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
SESS = {"exp1(07-22)": ("26.07.22", "t0nc_cl_pd15.npz"),
        "exp2(07-23)": ("26.07.23", "t0nc_cl_v4.npz"),
        "exp3(07-24)": ("26.07.24", "t0nc_cl_v7.npz"),
        "exp4(07-25)": ("26.07.25", "t0nc_cl_v8.npz"),
        "exp5(07-27)": ("26.07.27", "t0nc_cl_v9.npz")}
TH = {60: 0.70, 120: 0.50, 150: 0.40}          # OLD α 테이블 (hip)
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}   # (knee)
def old_alpha(g):
    return (TH.get(g[0], 0.40), 0.20, TK.get(g[2], 0.656), 0.20)

def sustained_lo(t, grf, thr=1.0, win=0.05):
    dt = float(t[1]-t[0]); w = int(round(win/dt)); on = grf > thr
    for i in range(len(grf)-w):
        if t[i] > 0.02 and not on[i:i+w].any(): return float(t[i])
    return float(t[-1])

tw = TW.twin()
# ── 수렴 골든 (온건판) ──
Z = np.load(P25/"t0nc_cl_v9.npz"); m0 = Z["t"] >= 0
tg9 = np.asarray(Z["t"][m0], float)
La = TW.rollout_cl(tw, tg9, Z["qd1"][m0], Z["qd2"][m0], Z["dqd1"][m0], Z["dqd2"][m0],
                   (150, 2.2, 250, 3), alphas=(1, 1, 1, 1), t_end=0.216)
Lb = rollout_cl_sea2(tw, tg9, Z["qd1"][m0], Z["qd2"][m0], Z["dqd1"][m0], Z["dqd2"][m0],
                     (150, 2.2, 250, 3), ks1=3000.0, bs1=20.0, jm1=0.02, t_end=0.216)
if Lb is None:
    print("수렴 골든(온건): 발산 FAIL")
else:
    d = max(float(np.abs(La[k]-Lb[k]).max()) for k in ("q1", "q2", "bz"))
    print(f"수렴 골든(온건 ks=3000): 정본 α=1 대비 최대차 {d:.3e} rad → {'PASS' if d < 2e-2 else 'CHECK'}", flush=True)

MODELS = {
    "OLD": None,
    "SEA_hip": dict(ks1=169.0, bs1=1.5, jm1=0.01),
    "SEA_hip140": dict(ks1=140.0, bs1=1.5, jm1=0.01),
    "SEA_hip200": dict(ks1=200.0, bs1=1.5, jm1=0.01),
    "SEA_hipknee": dict(ks1=169.0, bs1=1.5, jm1=0.01, ks2=650.0, bs2=1.5, jm2=0.01),
}
OUT = {}
for sess, (day, bait) in SESS.items():
    z = np.load(P25/bait); m = z["t"] >= 0
    tg = np.asarray(z["t"][m], float)
    qd1, qd2, dqd1, dqd2 = z["qd1"][m], z["qd2"][m], z["dqd1"][m], z["dqd2"][m]
    T_END = sustained_lo(z["t"], z["grf"]) if "grf" in z else 0.216
    base = ROOT/day
    for fold in sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
        gg = [float(x) for x in fold.name.split("_")]
        if len(gg) != 4: continue
        gains = tuple(gg)
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
        except FileNotFoundError:
            continue
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        qd2m = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2m-qd2m[0]) > np.radians(0.5))[0]
        t0 = t[on[0]] if len(on) else 0.0
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)] - t0)
        tmv = t - t0; msk = (tmv >= 0.005) & (tmv <= t_lo)
        if msk.sum() < 20: continue
        q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
        a1m = ahat_np(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float))
        a2m = ahat_np(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float))
        key = f"{sess}/{fold.name}"
        OUT[key] = {}
        for mn, kw in MODELS.items():
            if kw is None:
                L = TW.rollout_cl(tw, tg, qd1, qd2, dqd1, dqd2, gains, alphas=old_alpha(gains),
                                  t_end=T_END, t_after=0.3)
                e1v = L["q1"] if L else None; e2v = L["q2"] if L else None
                s1v = L["sh1"] if L else None; s2v = L["sh2"] if L else None
            else:
                L = rollout_cl_sea2(tw, tg, qd1, qd2, dqd1, dqd2, gains, t_end=T_END, t_after=0.3, **kw)
                if L is not None:
                    e1v = L["thm1"]; e2v = L["thm2"] if kw.get("ks2") else L["q2"]
                    s1v = L["tsp1"]; s2v = L["tsp2"]
            if L is None:
                OUT[key][mn] = None; continue
            q1s = np.interp(tmv[msk], L["t"], e1v); q2s = np.interp(tmv[msk], L["t"], e2v)
            s1s = np.interp(tmv[msk], L["t"], s1v); s2s_ = np.interp(tmv[msk], L["t"], s2v)
            OUT[key][mn] = dict(
                q1=round(float(np.degrees(np.sqrt(np.mean((q1m[msk]-q1s)**2)))), 2),
                q2=round(float(np.degrees(np.sqrt(np.mean((q2m[msk]-q2s)**2)))), 2),
                t1=round(float(np.sqrt(np.mean((a1m[msk]-s1s)**2))), 2),
                t2=round(float(np.sqrt(np.mean((a2m[msk]-s2s_)**2))), 2))
        r = OUT[key]
        print(f"{key:34s} " + " | ".join(f"{mn} q1 {r[mn]['q1']:5.1f} q2 {r[mn]['q2']:5.1f} τ1 {r[mn]['t1']:4.1f} τ2 {r[mn]['t2']:4.1f}"
              if r.get(mn) else f"{mn} FAIL" for mn in ("OLD", "SEA_hip", "SEA_hipknee")), flush=True)

json.dump(OUT, open(HERE/"_sea_transfer.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n=== 집계 (세션별 평균 → 전체) ===")
for mn in MODELS:
    per = {}
    for key, r in OUT.items():
        if r.get(mn):
            s = key.split("/")[0]
            per.setdefault(s, []).append(r[mn])
    tot = [x for v in per.values() for x in v]
    if not tot: print(f"{mn}: 전패"); continue
    line = f"{mn:12s}: 전체 q1 {np.mean([x['q1'] for x in tot]):6.2f}° q2 {np.mean([x['q2'] for x in tot]):6.2f}° " \
           f"τ1 {np.mean([x['t1'] for x in tot]):5.2f} τ2 {np.mean([x['t2'] for x in tot]):5.2f} (n={len(tot)})"
    print(line)
    for s, v in per.items():
        print(f"    {s}: q1 {np.mean([x['q1'] for x in v]):6.2f} q2 {np.mean([x['q2'] for x in v]):6.2f} "
              f"τ1 {np.mean([x['t1'] for x in v]):5.2f} τ2 {np.mean([x['t2'] for x in v]):5.2f} (n={len(v)})")
