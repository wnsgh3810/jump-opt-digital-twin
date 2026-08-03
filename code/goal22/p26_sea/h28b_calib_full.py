# -*- coding: utf-8 -*-
"""h28b — 세션 캘리브 LOTO 확장판 (그리드 26~126) + 성분 분해.

h28 발견: 66이 경계가 아니라 22/25의 진짜 최소는 36~56/46 (드리프트 ±2배급).
① 전 22 trial × 11 ks1 → LOTO 재판정 (고정 96 vs 캘리브 vs 오라클)
② 성분 분해: 07-25 오라클(46) vs 96 — 무른 스프링이 무엇을 고치나 (τ1 dqd킥 미결과 연결?)
③ 가드형 프로토콜: 캘리브 trial의 최소가 '안쪽'(경계 아님)이고 개선폭>5%일 때만 채택, 아니면 96 유지.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
tw0 = TW.twin()
BR = (2.40, 2.25, 1.05, 1.09, 3.86, 3.09)
GRID = (26.0, 36.0, 46.0, 56.0, 66.0, 76.0, 86.0, 96.0, 106.0, 116.0, 126.0)

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
        TR.append(dict(day=day, name=fold.name, t=t, t_lo=t_lo, msk=msk,
                       qd1=hip["desiredAngle"].to_numpy(float), qd2=knee["desiredAngle"].to_numpy(float),
                       dqd1=hip["desiredAngleVelocity"].to_numpy(float), dqd2=knee["desiredAngleVelocity"].to_numpy(float),
                       q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                       dq1=dq1m, dq2=dq2m,
                       a1=ahat_np(hip["currentTorque"].to_numpy(float), dq1m),
                       a2=ahat_np(knee["currentTorque"].to_numpy(float), dq2m),
                       gm=(gg[0], gg[1], gg[2]*TK.get(gg[2], 0.656), gg[3]*0.20)))
print(f"트라이얼 {len(TR)}개 × 그리드 {len(GRID)}", flush=True)

def comps(d, ks):
    sea = dict(ks1=float(ks), ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
    L = rollout_cl_sea2(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], d["gm"],
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
    return r

CACHE = {}
for d in TR:
    for ks in GRID:
        r = comps(d, ks)
        CACHE[(d["day"], d["name"], ks)] = r
    print(f"{d['day']}/{d['name']} 완료", flush=True)

def J_of(r):
    return sum(x / b for x, b in zip(r, BR))

DAYS = sorted(set(d["day"] for d in TR))
OUT = {"grid": list(GRID)}
print("\n=== ① LOTO 재판정 (그리드 26~126) ===", flush=True)
TOT = dict(fix=[], loto=[], guard=[], oracle=[])
for day in DAYS:
    names = [d["name"] for d in TR if d["day"] == day]
    Jt = {(n, ks): J_of(CACHE[(day, n, ks)]) for n in names for ks in GRID}
    fix = np.mean([Jt[(n, 96.0)] for n in names])
    fixq = np.mean([CACHE[(day, n, 96.0)][0] for n in names])
    orks = min(GRID, key=lambda ks: np.mean([Jt[(n, ks)] for n in names]))
    orc = np.mean([Jt[(n, orks)] for n in names]); orq = np.mean([CACHE[(day, n, orks)][0] for n in names])
    lo, gu, picks, gpicks = [], [], [], []
    for c in names:
        ks_c = min(GRID, key=lambda ks: Jt[(c, ks)])
        picks.append(int(ks_c))
        rest = [n for n in names if n != c]
        lo.append((np.mean([Jt[(n, ks_c)] for n in rest]), np.mean([CACHE[(day, n, ks_c)][0] for n in rest])))
        # 가드: 안쪽 최소 + 개선폭 >5%
        interior = GRID[0] < ks_c < GRID[-1]
        gain = (Jt[(c, 96.0)] - Jt[(c, ks_c)]) / Jt[(c, 96.0)]
        ks_g = ks_c if (interior and gain > 0.05) else 96.0
        gpicks.append(int(ks_g))
        gu.append((np.mean([Jt[(n, ks_g)] for n in rest]), np.mean([CACHE[(day, n, ks_g)][0] for n in rest])))
    lo = np.array(lo); gu = np.array(gu)
    OUT[day] = dict(n=len(names), fix_J=round(float(fix), 3), fix_q1=round(float(fixq), 2),
                    loto_J=round(float(lo[:, 0].mean()), 3), loto_q1=round(float(lo[:, 1].mean()), 2), picks=picks,
                    guard_J=round(float(gu[:, 0].mean()), 3), guard_q1=round(float(gu[:, 1].mean()), 2), gpicks=gpicks,
                    oracle_ks=float(orks), oracle_J=round(float(orc), 3), oracle_q1=round(float(orq), 2))
    TOT["fix"].append(fix); TOT["loto"].append(lo[:, 0].mean()); TOT["guard"].append(gu[:, 0].mean()); TOT["oracle"].append(orc)
    print(f"{day} (n={len(names)}): 고정 J {fix:.3f}/q1 {fixq:.2f} | LOTO {lo[:,0].mean():.3f}/{lo[:,1].mean():.2f} {picks} | "
          f"가드 {gu[:,0].mean():.3f}/{gu[:,1].mean():.2f} {gpicks} | 오라클 ks={int(orks)} {orc:.3f}/{orq:.2f}", flush=True)
print(f"\n5일 평균 J: 고정 {np.mean(TOT['fix']):.3f} | LOTO {np.mean(TOT['loto']):.3f} | 가드 {np.mean(TOT['guard']):.3f} | 오라클 {np.mean(TOT['oracle']):.3f}", flush=True)

print("\n=== ② 성분 분해 (날짜 오라클 vs 96) ===", flush=True)
for day in DAYS:
    names = [d["name"] for d in TR if d["day"] == day]
    orks = OUT[day]["oracle_ks"]
    a96 = np.array([CACHE[(day, n, 96.0)] for n in names]).mean(axis=0)
    aor = np.array([CACHE[(day, n, orks)] for n in names]).mean(axis=0)
    lbl = ("q1", "q2", "dq1", "dq2", "t1", "t2")
    OUT[day]["comps_96"] = [round(float(x), 3) for x in a96]
    OUT[day]["comps_or"] = [round(float(x), 3) for x in aor]
    print(f"{day} @96 → @{int(orks)}: " + " | ".join(f"{l} {x:.2f}→{y:.2f}" for l, x, y in zip(lbl, a96, aor)), flush=True)

json.dump(OUT, open(HERE / "_h28b_calib_full.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", flush=True)
