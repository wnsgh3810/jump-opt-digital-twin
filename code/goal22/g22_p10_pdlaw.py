"""GOAL22 P10-A1 — 실데이터에서 실제 인가된 제어 법칙 회귀 규명.

xlsx (Time, currentAngle, desiredAngle, currentAngleVelocity, desiredAngleVelocity,
currentTorque, desiredTorque)에서 raw currentTorque(=펌웨어 커맨드 추종치)를
  V1: kp·(q_des−q) + kd·(dq_des−dq)     (dq_des 인가)
  V2: kp·(q_des−q) + kd·(0−dq)          (dq_des=0 커맨드 — 사용자: 0324/0421이 이 경우)
  V3: V1 + c_ff·desiredTorque           (피드포워드 인가 여부 검증)
로 최소자승 → 실효 kp/kd, R², c_ff. 포화 샘플(|τ|>17.5) 제외.
산출: 데이터셋×trial×관절 표 + 폴더 라벨 게인 대비 비율(α).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
SETS = {
    "jump_0324": (DATA / "26_03_24/Jump/Jump_No_Tr", ["P40_D0.7", "P60_D1.5", "P100_D3"]),
    "jump_position_0421": (DATA / "26_04_21/Position Control",
                           ["P60_D0.75_P60_D2", "P70_D0.75_P70_D2", "P80_D0.75_P80_D2",
                            "P90_D0.75_P90_D2", "P100_D0.75_P100_D2", "P200_D1.5_P200_D4"]),
    "jump_0424": (DATA / "26_04_24",
                  ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "120_2_120_2",
                   "120_2.2_150_2.5", "120_2.2_200_2.8", "150_2.2_250_3",
                   "150_2.2_350_3.5", "150_2.2_500_4"]),
    "jump_0602": (DATA / "26_06_02/position",
                  ["60_0.75_60_2", "60_1.5_60_1.5", "90_0.75_90_2", "120_2_120_2",
                   "150_2.2_250_3", "150_2.2_500_5"]),
}
OUT = Path(__file__).parent / "p10_pdlaw.json"


def label_gains(ds, sub):
    """폴더명 → (hip_kp, hip_kd, knee_kp, knee_kd)."""
    if sub.startswith("P"):
        p = sub.split("_")
        if len(p) == 2:      # P40_D0.7 (0324, 양 관절 동일)
            kp = float(p[0][1:]); kd = float(p[1][1:])
            return kp, kd, kp, kd
        return (float(p[0][1:]), float(p[1][1:]), float(p[2][1:]), float(p[3][1:]))
    p = [float(v) for v in sub.split("_")]
    return p[0], p[1], p[2], p[3]


def read_joint(fp):
    df = pd.read_excel(fp)
    return {c: df[c].values.astype(float) for c in
            ["Time", "currentAngle", "desiredAngle", "currentAngleVelocity",
             "desiredAngleVelocity", "currentTorque", "desiredTorque"]}


def regress(d):
    q, qd = d["currentAngle"], d["desiredAngle"]
    v, vd = d["currentAngleVelocity"], d["desiredAngleVelocity"]
    tau, taud = d["currentTorque"], d["desiredTorque"]
    m = np.abs(tau) < 17.5
    e = (qd - q)[m]; ev1 = (vd - v)[m]; ev2 = (-v)[m]; y = tau[m]; tf = taud[m]
    out = {}
    for tag, cols in [("V1", [e, ev1]), ("V2", [e, ev2]), ("V3", [e, ev1, tf])]:
        A = np.column_stack(cols)
        c, res, *_ = np.linalg.lstsq(A, y, rcond=None)
        yh = A @ c
        r2 = 1 - np.sum((y - yh) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
        out[tag] = dict(kp=float(c[0]), kd=float(c[1]),
                        cff=float(c[2]) if len(c) > 2 else 0.0, r2=float(r2))
    out["n_sat"] = int((~m).sum()); out["n"] = int(len(tau))
    out["dqdes_rms"] = float(np.sqrt(np.mean(vd ** 2)))
    return out


if OUT.exists() and OUT.stat().st_size > 100:
    rows = json.load(open(OUT))          # 캐시 사용 (다중 워커 write 레이스 방지)
    _CACHED = True
else:
    _CACHED = False
    rows = {}
if _CACHED:
    pass
else:
    print(f"{'trial':28s} jt {'label':>10s}  {'V1 kp/kd(R2)':>24s}  {'V2 kp/kd(R2)':>24s}  cff  sat")
for ds, (root, subs) in (SETS.items() if not _CACHED else []):
    for sub in subs:
        lg = label_gains(ds, sub)
        for j, fn in [(1, "hip.xlsx"), (2, "knee.xlsx")]:
            d = read_joint(root / sub / fn)
            r = regress(d)
            rows[f"{ds}/{sub}/j{j}"] = dict(label_kp=lg[0 if j == 1 else 2],
                                            label_kd=lg[1 if j == 1 else 3], **r)
            lab = f"{lg[0 if j==1 else 2]:.0f}/{lg[1 if j==1 else 3]:.2f}"
            v1, v2, v3 = r["V1"], r["V2"], r["V3"]
            best = "V1" if v1["r2"] >= v2["r2"] else "V2"
            print(f"{ds+'/'+sub:28s} {j}  {lab:>10s}  "
                  f"{v1['kp']:7.1f}/{v1['kd']:5.2f}({v1['r2']:.3f})  "
                  f"{v2['kp']:7.1f}/{v2['kd']:5.2f}({v2['r2']:.3f})  "
                  f"{v3['cff']:+.3f}  {r['n_sat']:3d}  <-{best}", flush=True)
if not _CACHED:
    import os, tempfile
    fd, tmp = tempfile.mkstemp(dir=str(OUT.parent), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(rows, f, indent=1)
    os.replace(tmp, OUT)                 # 원자적 교체
    print("saved", OUT.name)
