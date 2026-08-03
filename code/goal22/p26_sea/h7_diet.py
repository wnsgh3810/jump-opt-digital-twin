# -*- coding: utf-8 -*-
"""h7_diet — H7: hip 보정층(무릎커플링 b1=−0.2608) 다이어트 양방향 프로브.

가설: b1은 스프링을 현상적으로 흡수하던 항 — SEA2 도입 후엔 이중계산이므로
줄이면(0.5×/0×) CL과 Mode A가 '동시에' 개선되어야 (한쪽만 좋아지면 스펀지 이동일 뿐).
채점 (b1 ∈ {1.0×, 0.5×, 0×} 각각):
  [CL]     22 trial 제로샷 전이 (SEA2 2단+knee650) — q1/q2/τ1/τ2
  [Mode A] 0602 재생 dq2 RMSE (골든 게이트 지표, a_full23) + 0424 Mode A hip e1(2단 보정 후)
주의: RU.HIP 런타임 변형 → 각 평가 후 원복. 원본 파일 무수정.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

RU = TW.RU
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
SEA = dict(ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=650.0, bs2=1.5, jm2=0.01)
B1_0 = RU.HIP["b1"]

def slo(t, g, thr=1.0, win=0.05):
    dt = float(t[1]-t[0]); w = int(round(win/dt)); on = g > thr
    for i in range(len(g)-w):
        if t[i] > 0.02 and not on[i:i+w].any(): return float(t[i])
    return float(t[-1])
def defl_2s(tau):
    a = np.abs(tau); d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d

tw = TW.twin()
# ── CL 전이 세트 로드 ──
SESS = {"exp1": ("26_07_22","t0nc_cl_pd15.npz"),"exp2": ("26_07_23","t0nc_cl_v4.npz"),
        "exp3": ("26_07_24","t0nc_cl_v7.npz"),"exp4": ("26_07_25","t0nc_cl_v8.npz"),
        "exp5": ("26_07_27","t0nc_cl_v9.npz")}
CLTR = []
for sess, (day, bait) in SESS.items():
    z = np.load(P25/bait); m = z["t"] >= 0
    bt = dict(tg=np.asarray(z["t"][m], float), qd1=z["qd1"][m], qd2=z["qd2"][m],
              dqd1=z["dqd1"][m], dqd2=z["dqd2"][m],
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
        CLTR.append(dict(bait=bt, gains=tuple(gg), tmv=tmv, msk=msk,
                         q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                         a1=ahat_np(hip["currentTorque"].to_numpy(float), hip["currentAngleVelocity"].to_numpy(float)),
                         a2=ahat_np(knee["currentTorque"].to_numpy(float), knee["currentAngleVelocity"].to_numpy(float))))
# ── 0424 Mode A 세트 로드 ──
MA424 = []
for fold in sorted([p for p in (ROOT/"26_04_24").iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
    try:
        hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    except FileNotFoundError:
        continue
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
    v2 = knee["currentAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
    a1 = ahat_np(raw1, hip["currentAngleVelocity"].to_numpy(float))
    qd2 = knee["desiredAngle"].to_numpy(float); on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0]
    i0 = int(on[0]) if len(on) else 0; t0 = t[i0]
    gf = fold/"GRF.xlsx"
    if gf.exists():
        g = pd.read_excel(gf)["Current_GRF"].to_numpy(float)[:n]
        g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
        ab = np.where(g >= thr)[0]
        t_lo = (t[min(int(ab[-1])+1, len(t)-1)] - t0) if len(ab) else (t[-1]-t0)
    else:
        t_lo = t[-1]-t0
    t_lo = float(min(t_lo, t[-1]-t0-0.004))
    if t_lo < 0.06: continue
    MA424.append(dict(t=t, t0=t0, t_lo=t_lo, i0=i0, q1=q1m, raw1=raw1, raw2=raw2, a1=a1, q2=q2m))

def eval_all(tag):
    # [CL]
    rows = []
    for d in CLTR:
        b = d["bait"]
        L = rollout_cl_sea2(tw, b["tg"], b["qd1"], b["qd2"], b["dqd1"], b["dqd2"], d["gains"],
                            t_end=b["T_END"], t_after=0.3, **SEA)
        if L is None: continue
        msk = d["msk"]; tmv = d["tmv"]
        q1s = np.interp(tmv[msk], L["t"], L["thm1"]); q2s = np.interp(tmv[msk], L["t"], L["thm2"])
        s1s = np.interp(tmv[msk], L["t"], L["tsp1"]); s2s_ = np.interp(tmv[msk], L["t"], L["tsp2"])
        rows.append((np.degrees(np.sqrt(np.mean((d["q1"][msk]-q1s)**2))),
                     np.degrees(np.sqrt(np.mean((d["q2"][msk]-q2s)**2))),
                     np.sqrt(np.mean((d["a1"][msk]-s1s)**2)),
                     np.sqrt(np.mean((d["a2"][msk]-s2s_)**2))))
    cl = np.array(rows).mean(axis=0)
    # [Mode A] 0602 재생 (골든 지표)
    g = TW.golden()
    r0602 = g["replay_0602_mean"]
    # [Mode A] 0424 rollout_ol + 2단 보정 후 hip e1
    e424 = []
    for d in MA424:
        st = TW.settle_state(tw, float(d["q1"][d["i0"]]), float(d["q2"][d["i0"]]))
        Lg = TW.rollout_ol(tw, d["t"]-d["t0"], d["raw1"], d["raw2"], st, t_end=d["t_lo"], t_after=0.05)
        if Lg is None: continue
        m = ((d["t"]-d["t0"]) >= 0.005) & ((d["t"]-d["t0"]) <= d["t_lo"])
        e1 = d["q1"][m] - np.interp((d["t"]-d["t0"])[m], Lg["t"], Lg["q1"]) - defl_2s(d["a1"][m])
        e424.append(np.degrees(np.sqrt(np.mean(e1**2))))
    print(f"[{tag}] CL(n={len(rows)}): q1 {cl[0]:.2f}° q2 {cl[1]:.2f}° τ1 {cl[2]:.2f} τ2 {cl[3]:.2f} | "
          f"ModeA 0602재생 {r0602:.3f} (게이트 1.29±0.15) | 0424 e1(2단보정) {np.mean(e424):.2f}° (n={len(e424)})", flush=True)
    return dict(cl_q1=float(cl[0]), cl_q2=float(cl[1]), cl_t1=float(cl[2]), cl_t2=float(cl[3]),
                r0602=float(r0602), e424=float(np.mean(e424)))

OUT = {}
for scale in (1.0, 0.5, 0.0):
    RU.HIP["b1"] = B1_0 * scale
    OUT[f"b1x{scale}"] = eval_all(f"b1×{scale}")
RU.HIP["b1"] = B1_0
json.dump(OUT, open(HERE/"_h7_diet.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
