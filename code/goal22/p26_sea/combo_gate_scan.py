# -*- coding: utf-8 -*-
"""combo_gate_scan — 대재스캔 후속 2판정.

① 골든 게이트: 질량×1.1(base/thigh/crank) 플랜트가 0602 재생(1.29±0.15)을 통과하는가
   — 플랜트 변경이므로 진짜 시험 (엔드스톱 때와 달리 동역학이 바뀜).
② 세션 드리프트 판별: 날짜별 최적 ks1이 서로 다른가 (조합 시험서 날짜별 성적 엇갈림
   → 전역 파라미터가 아니라 세션별 상수 문제라는 가설의 직접 판별 실험).
"""
import os, sys, json, copy
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

RU = TW.RU; R19 = TW.R19; E = TW.E
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
tw0 = TW.twin()
mj = tw0["P"].J._P["mj"]
BID = {mj.mj_id2name(tw0["model"], mj.mjtObj.mjOBJ_BODY, i): i for i in range(tw0["model"].nbody)}

def patched(mscale=None, mu=None):
    m2 = copy.deepcopy(tw0["model"])
    if mscale:
        for bn in ("base", "thigh", "crank"):
            i = BID[bn]; m2.body_mass[i] *= mscale; m2.body_inertia[i] *= mscale
    if mu:
        for gi in range(m2.ngeom):
            m2.geom_friction[gi][0] = mu
    tw2 = dict(tw0); tw2["model"] = m2
    return tw2

# ── ① 골든 게이트 (0602 재생 — p25_a_twin.golden ③ 미러) ──
print("=== ① 골든 게이트: 0602 재생 ===", flush=True)
GATE = {}
for tag, tw_ in [("mass_x1.1", patched(mscale=1.1)), ("mass_x1.1+mu0.85", patched(mscale=1.1, mu=0.85))]:
    rms = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0602":
            continue
        res = RU.a_full23(tw_["model"], False, l_i, d, tw_["law"], 0.0, 0.0,
                          c_cvt=0.0, spr=tw_["spr"], k_rise=tw_["kr"])
        rms.append(float(res[0]) if res else 9.9)
    mean = float(np.mean(rms))
    ok = abs(mean - TW.GOLDEN_0602) < 0.15
    GATE[tag] = dict(mean=round(mean, 3), golden=TW.GOLDEN_0602, ok=bool(ok), rms=[round(x, 3) for x in rms])
    print(f"{tag}: 0602 재생 {mean:.3f} (골든 {TW.GOLDEN_0602}±0.15) → {'PASS' if ok else 'FAIL'}", flush=True)

# ── 트라이얼 로드 (grand_plant_sweep 미러) ──
TR = []
for day in ["26_07_22", "26_07_23", "26_07_24", "26_07_25", "26_07_27"]:
    for fold in sorted([p for p in (ROOT / day).iterdir() if p.is_dir() and (p / "hip.xlsx").exists()]):
        gg = [float(x) for x in fold.name.split("_")]
        if len(gg) != 4: continue
        try:
            hip = pd.read_excel(fold / "hip.xlsx"); knee = pd.read_excel(fold / "knee.xlsx"); grf = pd.read_excel(fold / "GRF.xlsx")
        except FileNotFoundError:
            continue
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb + 0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)])
        msk = (t >= 0.005) & (t <= t_lo - 0.005)
        if msk.sum() < 20: continue
        dq1m = hip["currentAngleVelocity"].to_numpy(float); dq2m = knee["currentAngleVelocity"].to_numpy(float)
        TR.append(dict(day=day, t=t, t_lo=t_lo, msk=msk,
                       qd1=hip["desiredAngle"].to_numpy(float), qd2=knee["desiredAngle"].to_numpy(float),
                       dqd1=hip["desiredAngleVelocity"].to_numpy(float), dqd2=knee["desiredAngleVelocity"].to_numpy(float),
                       q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                       dq1=dq1m, dq2=dq2m,
                       a1=ahat_np(hip["currentTorque"].to_numpy(float), dq1m),
                       a2=ahat_np(knee["currentTorque"].to_numpy(float), dq2m),
                       gm=(gg[0], gg[1], gg[2]*TK.get(gg[2], 0.656), gg[3]*0.20)))
print(f"트라이얼 {len(TR)}개", flush=True)
BASE_REF = dict(q1=2.40, q2=2.25, dq1=1.05, dq2=1.09, t1=3.86, t2=3.09)

def perday_score(tw, sea):
    per = {}
    for d in TR:
        L = rollout_cl_sea2(tw, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], d["gm"],
                            t_end=d["t_lo"], t_after=0.1, **sea)
        if L is None: return None
        m = d["msk"]; t = d["t"]
        de1 = np.gradient(L["thm1"], L["t"]); de2 = np.gradient(L["q2"], L["t"])
        r = (np.degrees(np.sqrt(np.mean((d["q1"][m]-np.interp(t[m], L["t"], L["thm1"]))**2))),
             np.degrees(np.sqrt(np.mean((d["q2"][m]-np.interp(t[m], L["t"], L["q2"]))**2))),
             float(np.sqrt(np.mean((d["dq1"][m]-np.interp(t[m], L["t"], de1))**2))),
             float(np.sqrt(np.mean((d["dq2"][m]-np.interp(t[m], L["t"], de2))**2))),
             float(np.sqrt(np.mean((d["a1"][m]-np.interp(t[m], L["t"], L["tsp1"]))**2))),
             float(np.sqrt(np.mean((d["a2"][m]-np.interp(t[m], L["t"], L["tsp2"]))**2))))
        per.setdefault(d["day"], []).append(r)
    out = {}
    for k, v in per.items():
        a = np.array(v).mean(axis=0)
        Jd = a[0]/BASE_REF["q1"]+a[1]/BASE_REF["q2"]+a[2]/BASE_REF["dq1"]+a[3]/BASE_REF["dq2"]+a[4]/BASE_REF["t1"]+a[5]/BASE_REF["t2"]
        out[k] = dict(J=round(float(Jd), 4), q1=round(float(a[0]), 3))
    return out

# ── ② 날짜별 최적 ks1 스캔 ──
print("=== ② 날짜별 ks1 스캔 (세션 드리프트 판별) ===", flush=True)
SCAN = {}
for ks in (76.0, 86.0, 96.0, 106.0, 116.0):
    sea = dict(ks1=ks, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
    pd_ = perday_score(tw0, sea)
    SCAN[str(ks)] = pd_
    print(f"ks1={ks:5.0f}: " + " | ".join(f"{k[6:]}: J {v['J']:.3f} q1 {v['q1']:.2f}" for k, v in sorted(pd_.items())), flush=True)

# 날짜별 최적 ks1 요약
days = sorted(next(iter(SCAN.values())).keys())
print("\n=== 날짜별 최적 ks1 (J 기준 / q1 기준) ===", flush=True)
BESTS = {}
for day in days:
    bj = min(SCAN, key=lambda k: SCAN[k][day]["J"]); bq = min(SCAN, key=lambda k: SCAN[k][day]["q1"])
    BESTS[day] = dict(best_J=float(bj), best_q1=float(bq),
                      J_at_best=SCAN[bj][day]["J"], J_at_96=SCAN["96.0"][day]["J"],
                      q1_at_best=SCAN[bq][day]["q1"], q1_at_96=SCAN["96.0"][day]["q1"])
    print(f"{day}: J최적 ks1={bj} (J {SCAN[bj][day]['J']:.3f} vs 96에서 {SCAN['96.0'][day]['J']:.3f}) | "
          f"q1최적 ks1={bq} ({SCAN[bq][day]['q1']:.2f}° vs {SCAN['96.0'][day]['q1']:.2f}°)", flush=True)

json.dump(dict(gate=GATE, scan=SCAN, bests=BESTS),
          open(HERE / "_combo_gate_scan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", flush=True)
