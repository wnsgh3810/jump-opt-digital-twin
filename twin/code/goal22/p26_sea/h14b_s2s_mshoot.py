# -*- coding: utf-8 -*-
"""h14b — 0604 s2s Mode A를 multiple shooting으로 (0.4s 창, 측정상태 리셋 — P19 규약).

h14 교훈: 5~6s 통짜 개루프 재생은 오차 적분 발산 (페이로드 무시 대조군 917°가 증명).
창 리셋: qpos/qvel을 측정 (q1,q2,dq1,dq2)+발접지 FK(bz,dbz)로 직접 설정.
채점: 창별 q1/q2 RMSE 평균 (페이로드 반영 트윈), hip은 2단 관측보정 전/후.
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
import os, sys, json, copy
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import ahat_np    # noqa: E402
import safe                      # noqa: E402

ROOT = Path((DATA_ROOT + "/26_06_04"))
TRIALS = [("0kg", ROOT/"no_cvt/no_load/raw_unwrap", 0.0, (47.8, 53.2)),
          ("5kg", ROOT/"no_cvt/load_5/raw_unwrap", 5.0, (47.0, 53.0)),
          ("7.5kg", ROOT/"no_cvt/load_7.5/raw_unwrap", 7.5, (52.9, 58.5))]
WLEN, STRIDE = 0.4, 0.3
L_SEG = 0.25

def defl_2s(tau):
    a = np.abs(tau); d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d

tw0 = TW.twin()
P = tw0["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]
BID = {mj.mj_id2name(tw0["model"], mj.mjtObj.mjOBJ_BODY, i): i for i in range(tw0["model"].nbody)}

def st_from_meas(tw, q1_0, q2_0, dq1_0, dq2_0, raw1_0, raw2_0):
    model = tw["model"]
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi/2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    c1, s1_ = np.cos(q1_0), np.sin(q1_0)
    c12 = np.cos(q1_0+q2_0)
    dbz = -L_SEG*(c1*dq1_0 + c12*(dq1_0+dq2_0))
    md.qvel[:] = [dbz, -dq1_0, -dq2_0, dq2_0, -dq2_0]
    mj.mj_forward(model, md)
    return dict(qpos=md.qpos.copy(), qvel=md.qvel.copy(), c1f=float(raw1_0), c2f=float(raw2_0))

OUT = {}
for lab, fold, PL, (t0, t1) in TRIALS:
    hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
    dq1m = hip["currentAngleVelocity"].to_numpy(float); dq2m = knee["currentAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
    a1 = ahat_np(raw1, dq1m)
    m2 = copy.deepcopy(tw0["model"])
    if PL > 0:
        b = BID["base"]; m2.body_mass[b] += PL; m2.body_inertia[b] *= (1 + PL/1.39*0.5)
    tw2 = dict(tw0); tw2["model"] = m2
    rows = []
    w0 = t0
    while w0 + WLEN <= t1:
        seg = (t >= w0) & (t <= w0 + WLEN)
        if seg.sum() < 50:
            w0 += STRIDE; continue
        tg = t[seg] - w0
        i0 = int(np.argmax(seg))
        st = st_from_meas(tw2, float(q1m[i0]), float(q2m[i0]), float(dq1m[i0]), float(dq2m[i0]),
                          float(raw1[i0]), float(raw2[i0]))
        Lg = TW.rollout_ol(tw2, tg, raw1[seg], raw2[seg], st, t_end=float(tg[-1]-0.005), t_after=0.005)
        if Lg is None:
            w0 += STRIDE; continue
        msk = (tg >= 0.02) & (tg <= tg[-1]-0.02)
        q1s = np.interp(tg[msk], Lg["t"], Lg["q1"]); q2s = np.interp(tg[msk], Lg["t"], Lg["q2"])
        e1 = q1m[seg][msk] - q1s
        e1c = e1 - defl_2s(a1[seg][msk]) + defl_2s(a1[seg][msk][0])   # 창 시작 기준 상대 보정
        rows.append((np.degrees(np.sqrt(np.mean(e1**2))),
                     np.degrees(np.sqrt(np.mean(e1c**2))),
                     np.degrees(np.sqrt(np.mean((q2m[seg][msk]-q2s)**2)))))
        w0 += STRIDE
    a = np.array(rows)
    OUT[lab] = dict(n_win=len(rows), q1=round(float(a[:,0].mean()),2), q1_2s=round(float(a[:,1].mean()),2),
                    q2=round(float(a[:,2].mean()),2))
    print(f"{lab}: 창 {len(rows)}개 | q1 {a[:,0].mean():.2f}° (2단보정 {a[:,1].mean():.2f}°) | q2 {a[:,2].mean():.2f}°", flush=True)

json.dump(OUT, open(HERE/"_h14b_s2s.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
