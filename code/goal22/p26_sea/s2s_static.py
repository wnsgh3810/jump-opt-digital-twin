# -*- coding: utf-8 -*-
"""s2s_static — H3: 0604 페이로드 s2s 준정적 분석 (데이터측).

원리: 앉기/서기 유지 구간(|dq|≈0)에서 토크는 지속·자세는 정지 → 타이밍 무관.
  ① 정적 구간별 (τ1, q1, τ2, q2) 평균 추출 (영상 대조용 상태표)
  ② FK 유사슬립: 발 접지 상태에서 인코더-FK 발끝 이동 = 사슬 비틀림의 서명
     (진짜 슬립이면 영상에 보여야 — 영상 대조는 후속)
  ③ 유사슬립 진폭 vs hip 토크 진폭 → 저토크 영역 k_s 점 추가 (H2 비선형)
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
import os, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
ROOT = Path((DATA_ROOT + "/26_06_04"))
TRIALS = [("no_cvt 0kg", ROOT/"no_cvt/no_load/raw_unwrap", 0.0),
          ("no_cvt 5kg", ROOT/"no_cvt/load_5/raw_unwrap", 5.0),
          ("no_cvt 7.5kg", ROOT/"no_cvt/load_7.5/raw_unwrap", 7.5),
          ("cvt 0kg", ROOT/"cvt/no_load/raw_unwrap", 0.0),
          ("cvt 2.5kg", ROOT/"cvt/load_2.5/raw_unwrap", 2.5),
          ("cvt 5kg", ROOT/"cvt/load_5/raw_unwrap", 5.0)]
KT, GR, CF = 0.091, 9.0, 0.59
A = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
L = 0.25
def ahat(raw, v):
    Iq = (CF/(GR*KT))*np.asarray(raw, float); s = np.sign(v)
    return A[0]*GR*KT*Iq - A[1]*GR*np.abs(Iq)*Iq - A[2]*s - A[3]*np.abs(Iq)*s
def smooth(x, w=9): return np.convolve(x, np.ones(w)/w, mode="same")

RES = {}
for lab, fold, payload in TRIALS:
    try:
        hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    except FileNotFoundError:
        print(lab, "파일 없음"); continue
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1 = hip["currentAngle"].to_numpy(float); q2 = knee["currentAngle"].to_numpy(float)
    v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
    a1 = ahat(hip["currentTorque"].to_numpy(float), v1)
    a2 = ahat(knee["currentTorque"].to_numpy(float), v2)
    # ① 정적 구간: |dq| 평활 후 임계, 최소 0.08s 지속
    sp = np.maximum(np.abs(smooth(v1)), np.abs(smooth(v2)))
    quiet = sp < 0.25
    segs = []
    i = 0
    while i < n:
        if quiet[i]:
            j2 = i
            while j2 < n and quiet[j2]: j2 += 1
            if t[j2-1]-t[i] >= 0.08:
                sl = slice(i+3, j2-3)
                segs.append(dict(t0=round(t[i],3), t1=round(t[j2-1],3),
                                 q1=round(float(np.mean(q1[sl])),4), q2=round(float(np.mean(q2[sl])),4),
                                 tau1=round(float(np.mean(a1[sl])),2), tau2=round(float(np.mean(a2[sl])),2)))
            i = j2
        else: i += 1
    # ② FK 유사슬립 (전 구간)
    fx = L*(np.cos(q1)+np.cos(q1+q2))
    ps = (fx - fx[0])*1e3
    # ③ 유사슬립~τ1 회귀 (전 구간, 저토크 k 점)
    X = np.column_stack([a1, a2, np.ones(n)])
    b, _, _, _ = np.linalg.lstsq(X, ps, rcond=None)
    r2 = 1 - np.sum((ps-X@b)**2)/max(np.sum((ps-ps.mean())**2), 1e-9)
    RES[lab] = dict(payload=payload, segs=segs, ps_range=[round(float(ps.min()),1), round(float(ps.max()),1)],
                    c1_mm=round(float(b[0]),2), c2_mm=round(float(b[1]),2), r2=round(float(r2),3),
                    tau1_range=[round(float(a1.min()),2), round(float(a1.max()),2)])
    print(f"{lab:12s}: 정적 {len(segs)}구간 | τ1 범위 [{a1.min():.1f},{a1.max():.1f}]Nm | "
          f"유사슬립 [{ps.min():.0f},{ps.max():.0f}]mm | 회귀 c1={b[0]:+.2f} c2={b[1]:+.2f} mm/Nm R²={r2:.2f}")
    for s in segs:
        print(f"    [{s['t0']}~{s['t1']}s] q1={np.degrees(s['q1']):.1f}° q2={np.degrees(s['q2']):.1f}° τ1={s['tau1']:+.2f} τ2={s['tau2']:+.2f}")

json.dump(RES, open(HERE/"_s2s_static.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
