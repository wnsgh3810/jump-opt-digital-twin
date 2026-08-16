# -*- coding: utf-8 -*-
"""h14_s2s_modea — 큐2: 0604 페이로드 s2s 다과제 Mode A 검증 (게인 불필요·PD-free).

목적(사용자): 이 트윈으로 max payload s2s까지 최적화할 것 → 페이로드 하 재현력이 필수.
방법: base 질량에 페이로드 추가한 트윈으로 기립 전이 구간(크라우치 홀드 끝~기립 홀드 끝)
측정 raw 토크 재생 → q1/q2 재현 RMSE. 변형: ①페이로드 반영 ②미반영(대조 — 반영이 나아야 정상)
③hip e1의 2단 관측보정 효과 (s2s 저토크 −2~−6Nm = 무른 구간 96의 시험대).
대상: no_cvt 0/5/7.5kg (knee=관절각 직접 비교 가능).
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
import copy
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402

ROOT = Path((DATA_ROOT + "/26_06_04"))
TRIALS = [("0kg", ROOT/"no_cvt/no_load/raw_unwrap", 0.0),
          ("5kg", ROOT/"no_cvt/load_5/raw_unwrap", 5.0),
          ("7.5kg", ROOT/"no_cvt/load_7.5/raw_unwrap", 7.5)]
# 기립 전이 창 (정적 카탈로그 근거: 크라우치 끝~기립 홀드 끝)
WIN = {"0kg": (47.8, 53.2), "5kg": (47.0, 53.0), "7.5kg": (52.9, 58.5)}

def defl_2s(tau):
    a = np.abs(tau); d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d

tw0 = TW.twin()
mj = tw0["P"].J._P["mj"]
BID = {mj.mj_id2name(tw0["model"], mj.mjtObj.mjOBJ_BODY, i): i for i in range(tw0["model"].nbody)}
OUT = {}
for lab, fold, P in TRIALS:
    hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
    v1 = hip["currentAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
    a1 = ahat_np(raw1, v1)
    t0, t1 = WIN[lab]
    i0 = int(np.searchsorted(t, t0))
    seg = (t >= t0) & (t <= t1)
    tg = t[seg] - t0
    OUT[lab] = {}
    for variant, dp in [("페이로드 반영", P), ("페이로드 무시", 0.0)]:
        m2 = copy.deepcopy(tw0["model"])
        if dp > 0:
            b = BID["base"]
            m2.body_mass[b] += dp
            m2.body_inertia[b] *= (1 + dp/1.39*0.5)   # 대략 (베이스 위 적재 가정)
        tw2 = dict(tw0); tw2["model"] = m2
        st = TW.settle_state(tw2, float(q1m[i0]), float(q2m[i0]))
        Lg = TW.rollout_ol(tw2, tg, raw1[seg], raw2[seg], st, t_end=float(tg[-1]-0.01), t_after=0.02)
        if Lg is None:
            OUT[lab][variant] = None; print(f"{lab}/{variant}: 발산", flush=True); continue
        msk = (tg >= 0.05) & (tg <= tg[-1]-0.05)
        q1s = np.interp(tg[msk], Lg["t"], Lg["q1"]); q2s = np.interp(tg[msk], Lg["t"], Lg["q2"])
        e1 = q1m[seg][msk] - q1s
        e1c = e1 - defl_2s(a1[seg][msk])
        r1 = np.degrees(np.sqrt(np.mean(e1**2))); r1c = np.degrees(np.sqrt(np.mean(e1c**2)))
        r2 = np.degrees(np.sqrt(np.mean((q2m[seg][msk]-q2s)**2)))
        OUT[lab][variant] = dict(q1=round(float(r1),2), q1_2s=round(float(r1c),2), q2=round(float(r2),2))
        print(f"{lab}/{variant}: q1 {r1:.2f}° (2단보정 {r1c:.2f}°) q2 {r2:.2f}°", flush=True)

json.dump(OUT, open(HERE/"_h14_s2s.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
