# -*- coding: utf-8 -*-
"""h13_cvt429 — 큐1: 0429 CVT 세션 hip 직렬탄성 검사 (hip은 CVT 무관 직결 구동).

절차: ①RU.build_cvt23으로 CVT 모델(l_i=25.08) 구축 ②RU.a_full23_log로 통짜 재생
(골든 0429 dq2 RMSE ~3.31 재현 확인 = 러너 신뢰) ③hip e1(t)=q1측정−q1재생을 â1로 회귀
→ r·k̂이 무변속 세션들(k̂ 93~220, r 0.7~0.9)과 같은 대역이면 CVT 세션도 스프링 일관.
④2단 보정 후 e1 RMSE (H12 확장).
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
P25 = HERE.parent / "p25_task0"
sys.path.insert(0, str(P25)); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402

RU = TW.RU
tw = TW.twin()
P = tw["P"]

def defl_2s(tau):
    a = np.abs(tau); d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d

# CVT 모델 (p24a 후보 x로, twin()과 동일 재료)
import safe                      # noqa: E402
cand = safe.read_json(TW.CAND_PATH)
v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
x32, sp = TW.C.x32_of(v[:20])
ref = float(v[1]); d_dq = float(v[21])
model_c = RU.build_cvt23(x32, ref, sp, 0.02508, d_dq)
spr_c = RU.spr_resolve(model_c, tw["spr"])
nm = {n: float(x) for n, x in zip(cand["names"], cand["x"])}
c_cvt = nm["C_CVT"]; o1_429 = nm["o1_429"]; o2_429 = nm["o2_429"]
print(f"C_CVT={c_cvt:.3f} o1_429={o1_429:.4f} o2_429={o2_429:.4f}", flush=True)

OUT = []
for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
    if ds != "jump_0429":
        continue
    try:
        res = RU.a_full23_log(model_c, True, d.get("l_i", l_i), d, tw["law"], o1_429, o2_429,
                              c_cvt=c_cvt, spr=spr_c, k_rise=tw["kr"])
    except Exception as ex:
        print(f"{sub}: 러너 예외 {type(ex).__name__} {ex}", flush=True); continue
    if res is None:
        print(f"{sub}: CRASH", flush=True); continue
    # a_full23_log 반환 형식 탐사적 처리: (rmse, h, Lg) 또는 Lg dict
    Lg = None
    if isinstance(res, dict):
        Lg = res
    elif isinstance(res, (tuple, list)):
        for x in res:
            if isinstance(x, dict) and "q1" in x:
                Lg = x
        print(f"{sub}: 튜플 반환 {[type(x).__name__ for x in res]}", flush=True)
    if Lg is None:
        print(f"{sub}: 로그 dict 미발견 — 반환 {type(res)}", flush=True); continue
    t = d["t"]
    tl = Lg.get("t")
    q1s = np.interp(t, tl, Lg["q1"])
    e1 = d["q1"] - q1s
    raw1 = d.get("traw1")
    if raw1 is None:
        print(f"{sub}: traw1 없음", flush=True); continue
    KT, GR, CF = 0.091, 9.0, 0.59
    A_P = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
    Iq = (CF/(GR*KT))*np.asarray(raw1, float); s = np.sign(d["dq1"])
    a1 = A_P[0]*GR*KT*Iq - A_P[1]*GR*np.abs(Iq)*Iq - A_P[2]*s - A_P[3]*np.abs(Iq)*s
    msk = (t >= 0.02) & (t <= t[-1]-0.02)
    X = np.column_stack([a1[msk], np.ones(msk.sum())])
    b, _, _, _ = np.linalg.lstsq(X, e1[msk], rcond=None)
    r = float(np.corrcoef(a1[msk], e1[msk])[0, 1])
    k_hat = 1/abs(b[0]) if b[0] else np.nan
    r0 = np.degrees(np.sqrt(np.mean(e1[msk]**2)))
    r2s = np.degrees(np.sqrt(np.mean((e1[msk]-defl_2s(a1[msk]))**2)))
    OUT.append(dict(sub=str(sub), r=round(r,3), k_hat=round(float(k_hat),1),
                    rmse=round(float(r0),2), rmse_2s=round(float(r2s),2)))
    print(f"0429/{sub}: e1~â1 r={r:+.2f} k̂={k_hat:.0f} | RMSE {r0:.2f}° → 2단보정 {r2s:.2f}°", flush=True)

json.dump(OUT, open(HERE/"_h13_cvt429.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
