# -*- coding: utf-8 -*-
"""h28_session_calib — 세션 k_s 캘리브 프로토콜의 소급 실증 (LOTO).

H28: 날짜별 최적 ks1이 76~116 산포 (세션 드리프트). 실기 프로토콜 제안 = 세션 시작 시
캘리브 1회. 이 스크립트는 그 프로토콜이 소급적으로 작동함을 실증:
  하루 안에서 trial 1개(캘리브)로 ks1* 선택 → 같은 날 '나머지' trial로 채점 (인과 누수 없음).
비교 3열: ①고정 96 (현행) ②LOTO 캘리브 (프로토콜) ③날짜 오라클 (상한 — 그날 전 trial로 선택).
그리드는 66~126 (76이 경계였으므로 아래로 1스텝 확장 — 바운더리 체이싱 점검).
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
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(DATA_ROOT)
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
tw0 = TW.twin()
BASE_REF = dict(q1=2.40, q2=2.25, dq1=1.05, dq2=1.09, t1=3.86, t2=3.09)
GRID = (66.0, 76.0, 86.0, 96.0, 106.0, 116.0, 126.0)

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
print(f"트라이얼 {len(TR)}개", flush=True)

def trial_J(d, ks):
    sea = dict(ks1=float(ks), ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
    L = rollout_cl_sea2(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], d["gm"],
                        t_end=d["t_lo"], t_after=0.1, **sea)
    if L is None: return None, None
    m = d["msk"]; t = d["t"]
    de1 = np.gradient(L["thm1"], L["t"]); de2 = np.gradient(L["q2"], L["t"])
    r = (np.degrees(np.sqrt(np.mean((d["q1"][m]-np.interp(t[m], L["t"], L["thm1"]))**2))),
         np.degrees(np.sqrt(np.mean((d["q2"][m]-np.interp(t[m], L["t"], L["q2"]))**2))),
         float(np.sqrt(np.mean((d["dq1"][m]-np.interp(t[m], L["t"], de1))**2))),
         float(np.sqrt(np.mean((d["dq2"][m]-np.interp(t[m], L["t"], de2))**2))),
         float(np.sqrt(np.mean((d["a1"][m]-np.interp(t[m], L["t"], L["tsp1"]))**2))),
         float(np.sqrt(np.mean((d["a2"][m]-np.interp(t[m], L["t"], L["tsp2"]))**2))))
    J = r[0]/BASE_REF["q1"]+r[1]/BASE_REF["q2"]+r[2]/BASE_REF["dq1"]+r[3]/BASE_REF["dq2"]+r[4]/BASE_REF["t1"]+r[5]/BASE_REF["t2"]
    return float(J), r

# 전 trial × 전 그리드 사전계산
CACHE = {}   # (day, name, ks) -> (J, q1)
for d in TR:
    for ks in GRID:
        J, r = trial_J(d, ks)
        CACHE[(d["day"], d["name"], ks)] = (J, r[0] if r else None)
    js = {ks: round(CACHE[(d['day'], d['name'], ks)][0], 3) for ks in GRID}
    print(f"{d['day']}/{d['name']}: " + " ".join(f"{int(k)}:{v}" for k, v in js.items()), flush=True)

# LOTO 판정
DAYS = sorted(set(d["day"] for d in TR))
OUT = {}
print("\n=== LOTO 캘리브 판정 (J / q1[°]) ===", flush=True)
for day in DAYS:
    names = [d["name"] for d in TR if d["day"] == day]
    if len(names) < 2:
        print(f"{day}: trial {len(names)}개 — LOTO 불가"); continue
    # ① 고정 96
    fix = np.mean([CACHE[(day, n, 96.0)][0] for n in names])
    fixq = np.mean([CACHE[(day, n, 96.0)][1] for n in names])
    # ③ 오라클 (그날 전 trial 평균 최소 ks1)
    orks = min(GRID, key=lambda ks: np.mean([CACHE[(day, n, ks)][0] for n in names]))
    orc = np.mean([CACHE[(day, n, orks)][0] for n in names])
    orq = np.mean([CACHE[(day, n, orks)][1] for n in names])
    # ② LOTO: 각 trial을 캘리브로 → 나머지 채점
    loto_rows, picks = [], []
    for c in names:
        ks_c = min(GRID, key=lambda ks: CACHE[(day, c, ks)][0])
        picks.append(int(ks_c))
        rest = [n for n in names if n != c]
        loto_rows.append((np.mean([CACHE[(day, n, ks_c)][0] for n in rest]),
                          np.mean([CACHE[(day, n, ks_c)][1] for n in rest]),
                          np.mean([CACHE[(day, n, 96.0)][0] for n in rest]),
                          np.mean([CACHE[(day, n, 96.0)][1] for n in rest])))
    lo = np.array(loto_rows)
    OUT[day] = dict(n=len(names), fix_J=round(float(fix), 3), fix_q1=round(float(fixq), 2),
                    loto_J=round(float(lo[:, 0].mean()), 3), loto_q1=round(float(lo[:, 1].mean()), 2),
                    loto_rest96_J=round(float(lo[:, 2].mean()), 3),
                    oracle_ks=float(orks), oracle_J=round(float(orc), 3), oracle_q1=round(float(orq), 2),
                    picks=picks)
    print(f"{day} (n={len(names)}): 고정96 J {fix:.3f}/q1 {fixq:.2f} | LOTO J {lo[:,0].mean():.3f}/q1 {lo[:,1].mean():.2f} "
          f"(선택 {picks}) | 오라클 ks={int(orks)} J {orc:.3f}/q1 {orq:.2f}", flush=True)

json.dump(OUT, open(HERE / "_h28_session_calib.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", flush=True)
