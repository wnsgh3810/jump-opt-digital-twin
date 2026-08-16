# -*- coding: utf-8 -*-
"""grand_plant_sweep — 3부: 정렬 무결 지표 위 전 플랜트 축 재스캔 (역대 goal 전 축).

논리: 과거 '무감' 판정은 오염된 잣대(정렬 유령 5~12°) 위의 것 — 잣대가 1~4° 해상도가 된 지금 재심.
축 (역대 goal 전수): ①후보 x 26축 (마찰 fv/fc·접촉 solref/imp0·기하 arm/ref·지지법칙 LAW/B1/V0/K_RISE·
스프링 T_SPR·stiff·관성 I_th/I_ca·질량 M_c·CoM dz_th/dz_ca) ②바디 질량·CoM·관성 (post-patch)
③SEA 커맨드층 (ks1·ks1_hi·tau0·bs1·jm1) ④접촉 μ.
지표: 변형 C 정렬무결 CL 22 trial — J = q1/2.4 + q2/2.25 + dq1/1.05 + dq2/1.09 + τ1/3.86 + τ2/3.09 (기준=1씩, 총 6).
주의: 진단 스캔 — 채택은 골든 게이트(0602 1.29±0.15) 동반 별도 절차. 후보 파일 무수정.
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
import safe                      # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

RU = TW.RU; C = TW.C
ROOT = Path(DATA_ROOT)
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
tw0 = TW.twin()
P = tw0["P"]; mj = P.J._P["mj"]
BID = {mj.mj_id2name(tw0["model"], mj.mjtObj.mjOBJ_BODY, i): i for i in range(tw0["model"].nbody)}
cand = safe.read_json(TW.CAND_PATH)
NAMES = cand["names"]; X0 = np.asarray(cand["x"], float)

def build_tw(x):
    """twin() 내부 미러 — x 벡터로 tw dict 재구축 (전 층 파라미터 반영)."""
    v = RU.apply_freeze(RU.pad23(np.asarray(x, float)))
    law = RU.law_of(v); spr = RU.spr_of(v)
    x32, sp = C.x32_of(v[:20])
    ref = float(v[1]); tm = float(v[14]); d_dq = float(v[21])
    kr = RU.rise_of(d_dq)
    model = RU.build_flip23(x32, ref, sp, d_dq)
    sprm = RU.spr_resolve(model, spr)
    tw = dict(tw0)
    tw.update(model=model, law=law, tm=tm, kr=kr, sprm=sprm, spr=spr)
    return tw

# ── 트라이얼 로드 (1회) ──
TR = []
for day in ["26_07_22", "26_07_23", "26_07_24", "26_07_25", "26_07_27"]:
    for fold in sorted([p for p in (ROOT/day).iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
        gg = [float(x) for x in fold.name.split("_")]
        if len(gg) != 4: continue
        try:
            hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
        except FileNotFoundError:
            continue
        n = min(len(hip), len(knee), len(grf)); hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
        t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
        g = grf["Current_GRF"].to_numpy(float); gb = np.median(g[-5:]); thr = gb+0.06*(np.nanmax(g)-gb)
        ab = np.where(g >= thr)[0]; t_lo = float(t[min(int(ab[-1])+1, len(t)-1)])
        msk = (t >= 0.005) & (t <= t_lo-0.005)
        if msk.sum() < 20: continue
        dq1m = hip["currentAngleVelocity"].to_numpy(float); dq2m = knee["currentAngleVelocity"].to_numpy(float)
        TR.append(dict(t=t, t_lo=t_lo, msk=msk,
                       qd1=hip["desiredAngle"].to_numpy(float), qd2=knee["desiredAngle"].to_numpy(float),
                       dqd1=hip["desiredAngleVelocity"].to_numpy(float), dqd2=knee["desiredAngleVelocity"].to_numpy(float),
                       q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
                       dq1=dq1m, dq2=dq2m,
                       a1=ahat_np(hip["currentTorque"].to_numpy(float), dq1m),
                       a2=ahat_np(knee["currentTorque"].to_numpy(float), dq2m),
                       gm=(gg[0], gg[1], gg[2]*TK.get(gg[2], 0.656), gg[3]*0.20)))
print(f"트라이얼 {len(TR)}개", flush=True)
BASE_REF = dict(q1=2.40, q2=2.25, dq1=1.05, dq2=1.09, t1=3.86, t2=3.09)

def score(tw, sea=None):
    sea = sea or dict(ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
    rows = []
    for d in TR:
        L = rollout_cl_sea2(tw, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], d["gm"],
                            t_end=d["t_lo"], t_after=0.1, **sea)
        if L is None: return None, None
        m = d["msk"]; t = d["t"]
        de1 = np.gradient(L["thm1"], L["t"]); de2 = np.gradient(L["q2"], L["t"])
        rows.append((np.degrees(np.sqrt(np.mean((d["q1"][m]-np.interp(t[m], L["t"], L["thm1"]))**2))),
                     np.degrees(np.sqrt(np.mean((d["q2"][m]-np.interp(t[m], L["t"], L["q2"]))**2))),
                     float(np.sqrt(np.mean((d["dq1"][m]-np.interp(t[m], L["t"], de1))**2))),
                     float(np.sqrt(np.mean((d["dq2"][m]-np.interp(t[m], L["t"], de2))**2))),
                     float(np.sqrt(np.mean((d["a1"][m]-np.interp(t[m], L["t"], L["tsp1"]))**2))),
                     float(np.sqrt(np.mean((d["a2"][m]-np.interp(t[m], L["t"], L["tsp2"]))**2)))))
    a = np.array(rows).mean(axis=0)
    J = a[0]/BASE_REF["q1"]+a[1]/BASE_REF["q2"]+a[2]/BASE_REF["dq1"]+a[3]/BASE_REF["dq2"]+a[4]/BASE_REF["t1"]+a[5]/BASE_REF["t2"]
    return float(J), a

J0, A0 = score(tw0)
print(f"기준 J={J0:.4f} | {np.round(A0,3)}", flush=True)
OUT = {"base": dict(J=J0, cols=A0.tolist())}

# ── ① 후보 x 26축 (±10%, 0 근방은 절대 스텝) ──
SKIP = {"o1_429", "o2_429", "C_CVT", "tm"}
for i, nm in enumerate(NAMES):
    if nm in SKIP: continue
    for sgn in (+1, -1):
        x = X0.copy()
        step = 0.10*abs(x[i]) if abs(x[i]) > 1e-6 else 0.05
        x[i] += sgn*step
        try:
            tw2 = build_tw(x)
            J, A = score(tw2)
        except Exception as ex:
            J, A = None, None
        key = f"x:{nm}{'+' if sgn>0 else '-'}"
        OUT[key] = dict(J=J, dJ=(J-J0) if J else None, step=float(sgn*step))
        print(f"{key:22s}: J {J if J else 'FAIL'} (ΔJ {J-J0:+.4f})" if J else f"{key}: FAIL", flush=True)

# ── ② 바디 질량/CoM/관성 (모델 패치) ──
for bn in ("base", "thigh", "calf", "crank", "coupler"):
    for kind, val in (("m", 1.1), ("m", 0.9), ("com", +0.01), ("com", -0.01)):
        m2 = copy.deepcopy(tw0["model"]); i = BID[bn]
        if kind == "m":
            m2.body_mass[i] *= val; m2.body_inertia[i] *= val
        else:
            m2.body_ipos[i][2] += val
        tw2 = dict(tw0); tw2["model"] = m2
        J, A = score(tw2)
        key = f"body:{bn}:{kind}{val:+}" if kind == "com" else f"body:{bn}:m x{val}"
        OUT[key] = dict(J=J, dJ=(J-J0) if J else None)
        print(f"{key:22s}: ΔJ {J-J0:+.4f}" if J else f"{key}: FAIL", flush=True)

# ── ③ SEA 커맨드층 파라미터 ──
for nm, base, vals in [("ks1", 96.0, (86, 106)), ("ks1_hi", 323.0, (250, 400)), ("tau0_1", 9.0, (7.5, 10.5)),
                        ("bs1", 1.5, (0.8, 2.5)), ("jm1", 0.01, (0.006, 0.02))]:
    for v in vals:
        sea = dict(ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None); sea[nm] = float(v)
        J, A = score(tw0, sea)
        key = f"sea:{nm}={v}"
        OUT[key] = dict(J=J, dJ=(J-J0) if J else None)
        print(f"{key:22s}: ΔJ {J-J0:+.4f}" if J else f"{key}: FAIL", flush=True)

# ── ④ 접촉 μ ──
for mu in (0.85, 1.2):
    m2 = copy.deepcopy(tw0["model"])
    for gi in range(m2.ngeom):
        m2.geom_friction[gi][0] = mu
    tw2 = dict(tw0); tw2["model"] = m2
    J, A = score(tw2)
    OUT[f"contact:mu={mu}"] = dict(J=J, dJ=(J-J0) if J else None)
    print(f"contact:mu={mu}: ΔJ {J-J0:+.4f}" if J else "FAIL", flush=True)

json.dump(OUT, open(HERE/"_grand_sweep.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sig = sorted([(k, v["dJ"]) for k, v in OUT.items() if isinstance(v, dict) and v.get("dJ") is not None],
             key=lambda kv: kv[1])
print("\n=== 개선 상위 12 (ΔJ<0=개선) ===")
for k, dj in sig[:12]: print(f"{k:24s} ΔJ {dj:+.4f}")
print("=== 악화 상위 5 ===")
for k, dj in sig[-5:]: print(f"{k:24s} ΔJ {dj:+.4f}")
print("done")
