# -*- coding: utf-8 -*-
"""sea_mass_scan — SEA2 위에서 강체 동역학(질량·CoM·관성) 민감도 재스캔.

동기(사용자): 과거 '무감' 판정은 스프링 오차(10°대)가 지형을 덮던 시절 — SEA2로 잔차가
절반(4.8°)이 된 지금, 죽은 축이 살아났는지 재심 (REJECTED #21 재심 조건 '구조 변경 시').
방법: 후보 SEA2(2단+knee650) 고정, 바디별 질량 ±10%(base ±5%)·CoM z ±10mm·관성 ±20%
1-at-a-time → exp5 7게인 + exp4 4게인 CL 전이 지표 Δ.
주의: 진단 스캔 (채택은 별도 — 채택 시 Mode A 게이트 전수 필수).
"""
import os, sys, json, copy
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
SESS = {"exp4": ("26_07_25", "t0nc_cl_v8.npz"), "exp5": ("26_07_27", "t0nc_cl_v9.npz")}
SEA = dict(ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=650.0, bs2=1.5, jm2=0.01)

def slo(t, g, thr=1.0, win=0.05):
    dt = float(t[1]-t[0]); w = int(round(win/dt)); on = g > thr
    for i in range(len(g)-w):
        if t[i] > 0.02 and not on[i:i+w].any(): return float(t[i])
    return float(t[-1])

tw0 = TW.twin()
mj = tw0["P"].J._P["mj"]
BID = {mj.mj_id2name(tw0["model"], mj.mjtObj.mjOBJ_BODY, i): i for i in range(tw0["model"].nbody)}

# 트라이얼 로드 (1회)
TR = []
for sess, (day, bait) in SESS.items():
    z = np.load(P25/bait); m = z["t"] >= 0
    tg = np.asarray(z["t"][m], float)
    bt = dict(tg=tg, qd1=z["qd1"][m], qd2=z["qd2"][m], dqd1=z["dqd1"][m], dqd2=z["dqd2"][m],
              T_END=slo(z["t"], z["grf"]) if "grf" in z else 0.216)
    for fold in sorted([p for p in (ROOT/day).iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
        gg = [float(x) for x in fold.name.split("_")]
        if len(gg) != 4: continue
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
        TR.append(dict(bait=bt, gains=tuple(gg), tmv=tmv, msk=msk,
                       q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                       a1=ahat_np(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float)),
                       a2=ahat_np(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float))))
print(f"트라이얼 {len(TR)}개 로드", flush=True)

def score(tw):
    rows = []
    for d in TR:
        b = d["bait"]
        L = rollout_cl_sea2(tw, b["tg"], b["qd1"], b["qd2"], b["dqd1"], b["dqd2"], d["gains"],
                            t_end=b["T_END"], t_after=0.3, **SEA)
        if L is None: return None
        msk = d["msk"]; tmv = d["tmv"]
        q1s = np.interp(tmv[msk], L["t"], L["thm1"]); q2s = np.interp(tmv[msk], L["t"], L["thm2"])
        s1s = np.interp(tmv[msk], L["t"], L["tsp1"]); s2s_ = np.interp(tmv[msk], L["t"], L["tsp2"])
        rows.append((np.degrees(np.sqrt(np.mean((d["q1"][msk]-q1s)**2))),
                     np.degrees(np.sqrt(np.mean((d["q2"][msk]-q2s)**2))),
                     np.sqrt(np.mean((d["a1"][msk]-s1s)**2)),
                     np.sqrt(np.mean((d["a2"][msk]-s2s_)**2))))
    a = np.array(rows)
    return a.mean(axis=0)

base = score(tw0)
print(f"기준(SEA 후보): q1 {base[0]:.2f}° q2 {base[1]:.2f}° τ1 {base[2]:.2f} τ2 {base[3]:.2f}", flush=True)

PERT = []
for bn, lo, hi in [("base", 0.95, 1.05), ("thigh", 0.9, 1.1), ("calf", 0.9, 1.1), ("crank", 0.9, 1.1), ("coupler", 0.9, 1.1)]:
    for f in (lo, hi):
        PERT.append((f"m_{bn}x{f}", ("mass", bn, f)))
for bn in ("thigh", "calf"):
    for dz in (-0.01, 0.01):
        PERT.append((f"com_{bn}{dz*1e3:+.0f}mm", ("com", bn, dz)))
    for f in (0.8, 1.2):
        PERT.append((f"I_{bn}x{f}", ("inertia", bn, f)))

RES = {}
for name, (kind, bn, val) in PERT:
    m2 = copy.deepcopy(tw0["model"])
    i = BID[bn]
    if kind == "mass":
        m2.body_mass[i] *= val
        m2.body_inertia[i] *= val               # 질량 비례 관성 동반 (물리 일관)
    elif kind == "com":
        m2.body_ipos[i][2] += val
    elif kind == "inertia":
        m2.body_inertia[i][0] *= val; m2.body_inertia[i][1] *= val
    tw2 = dict(tw0); tw2["model"] = m2
    s = score(tw2)
    if s is None:
        RES[name] = None; print(f"{name}: 발산", flush=True); continue
    d = s - base
    RES[name] = dict(q1=round(float(s[0]),2), dq1=round(float(d[0]),3), q2=round(float(s[1]),2), dq2=round(float(d[1]),3),
                     t1=round(float(s[2]),2), dt1=round(float(d[2]),3), t2=round(float(s[3]),2), dt2=round(float(d[3]),3))
    print(f"{name:16s}: Δq1 {d[0]:+.3f}° Δq2 {d[1]:+.3f}° Δτ1 {d[2]:+.3f} Δτ2 {d[3]:+.3f}", flush=True)

json.dump(dict(base=dict(q1=float(base[0]), q2=float(base[1]), t1=float(base[2]), t2=float(base[3])), pert=RES),
          open(HERE/"_sea_mass_scan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
