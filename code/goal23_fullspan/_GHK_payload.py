# -*- coding: utf-8 -*-
"""_GHK_payload — **짐 지고 일어서기로 외삽 능력을 처음 잰다** (08-12).

왜 이게 필요한가
  이 연구의 최종 목표는 "짐 지고 일어서기·앞으로 뛰기 같은 **해본 적 없는 동작**을
  시뮬레이션만으로 예측하는 것" 이다. 그런데 채점에 올라 있는 10 세션이 **전부 점프**다.
  ⇒ **외삽 능력을 한 번도 잰 적이 없다.** 26.06.04 에 짐 지고 일어서기 데이터가 있는데
    채점에 들어가 있지 않다.

무엇을 재나
  측정된 토크를 시뮬레이션에 그대로 넣고 돌린 뒤(PD 제어 없음) 관절 각도·각속도가
  실제와 얼마나 맞는지 본다. PD 가 없어 오차를 감춰 주지 않으므로 물리가 틀리면 드러난다.
  **짐 무게만 바꿔 가며** 같은 모델로 예측한다 — 짐 0kg 로 맞춘 모델이 2.5kg·5kg 를
  맞히면 그것이 곧 외삽 능력이다.

유효한 데이터 (데이터 사전 + 파일 확인 08-12)
  · 변속기 있음(`cvt`, 링크 25.19mm): 0kg · 2.5kg · 5kg — 셋 다 유효
  · 변속기 없음(`no_cvt`): **0kg 만 유효** — 5kg/7.5kg 는 기립 실패라 파일 자체가 없다
  ⇒ 쓸 수 있는 것 4 개.

짐을 어떻게 넣나
  총질량을 늘리면 러너가 **몸통(base)에 몰아서** 붙인다 = 짐을 몸통에 얹는 것과 같다.
  ※ 과거 관측(07-29): 유효 질량이 명목보다 작다 (5→4.5, 7.5→5.5). 그것도 같이 시험한다.

★ 이 판은 **적합에 절대 넣지 않는다.** 검증 전용이다.

CLI: python _GHK_payload.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHK_payload.json"
DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_06_04")

# 현행 런타임 스택 (CURRENT_STACK.md H3_260812)
STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="3.733,2.309", FS_MASS="3.2988",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_PRESLIDE="0.86,0.85,0.02,1.0",
             FS_CMD_LPF="0.00317,0.00292", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.2880", FS_KNEEM_DAMP="0.1617", FS_HIPM_FL="0.3026",
             FS_HIPM_DAMP="0.0964", FS_KS_HIP="138.53", FS_COMZ="thigh=-0.00189")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)

BASE_MASS = 3.2988          # 짐 없을 때 총질량 [kg]
CASES = [("cvt/no_load",   0.0, True),
         ("cvt/load_2.5",  2.5, True),
         ("cvt/load_5",    5.0, True),
         ("no_cvt/no_load", 0.0, False)]
WIN = 0.25                  # 조각 길이 [s] — 개루프 재생은 길면 표류한다 (점프 창과 같은 규모)
STRIDE = 0.12
# ★★ 08-12 첫 실행에서 밟은 함정 (방법론 문서에 이미 적혀 있었다)
#   "앉았다 일어서기는 **접촉 상태가 바뀌는 과제**라, 앉아 있는 구간을 채점에서 분리해야 한다.
#    과거에 발산 220~267도가 **전부 그 구간 오염**이었다." (PLAYBOOK §7 off-stop 창 선별)
#   앉아 있는 동안은 몸통이 레일 아래 받침에 얹혀 있는데 모델에 그 하중 경로가 없다.
#   ⇒ 몸통이 충분히 떠 있는 구간만 쓴다. 몸통 높이는 실측 각도로 직접 계산한다
#     (다리 두 마디 0.25m 씩: 높이 ∝ −0.25·(sin q1 + sin(q1+q2)), 러너의 초기화 식과 같은 규약).
Z_MIN = 0.10                # 이 높이[m] 위로 떠 있는 구간만 채점


def base_height(q1, q2, L=0.25):
    """실측 관절 각도로 계산한 몸통 높이 [m] (발 기준). 러너 초기화와 같은 규약."""
    return -L * (np.sin(q1) + np.sin(q1 + q2))


def load(sub):
    h = pd.read_excel(DATA / sub / "hip.xlsx")
    k = pd.read_excel(DATA / sub / "knee.xlsx")
    n = min(len(h), len(k))
    g = lambda df, c: df[c].to_numpy(float)[:n]
    t = g(h, "Time"); t = t - t[0]
    d = dict(t=t, q1=g(h, "currentAngle"), q2=g(k, "currentAngle"),
             dq1=g(h, "currentAngleVelocity"), dq2=g(k, "currentAngleVelocity"),
             raw1=g(h, "currentTorque"), raw2=g(k, "currentTorque"))
    f = DATA / sub / "clutch.xlsx"
    li = 0.030
    if f.exists():
        c = pd.read_excel(f)
        col = [x for x in c.columns if "ink" in x]
        if col:
            li = float(np.median(c[col[0]].to_numpy(float))) / 1000.0
    d["l_i"] = li
    return d


def segments(d):
    """일어서는 동안 중 **몸통이 받침에서 떠 있는** 구간만 조각으로 나눈다."""
    t = d["t"]; dt = float(np.median(np.diff(t)))
    z = base_height(d["q1"], d["q2"])
    ok = (np.abs(d["dq2"]) > 0.2) & (z > Z_MIN)       # 움직이는 중 + 충분히 떠 있음
    nw = int(WIN / dt); ns = max(1, int(STRIDE / dt))
    segs = []
    for a in range(0, len(t) - nw, ns):
        if ok[a:a + nw].all():                        # 조각 **전체**가 조건을 만족할 때만
            segs.append(int(a))
    return segs, nw


def run_case(sub, payload, is_cvt, mass_eff=None):
    """반환 [(힙각 오차°, 무릎각 오차°, 힙속도, 무릎속도), …] 조각별."""
    import fs_runner as FR
    import fs_cvt as FC
    m_add = payload if mass_eff is None else mass_eff
    os.environ["FS_MASS"] = f"{BASE_MASS + m_add:.4f}"
    FR._S2S = None
    if is_cvt:
        FC._MC.clear(); FC._RT.clear()
    ft0 = FR.fs_twin()
    d = load(sub)
    ft = FC.cvt_ft(d["l_i"], ft_base=ft0) if is_cvt else ft0
    segs, nw = segments(d)
    E = []
    for a in segs:
        ix = np.arange(a, min(a + nw, len(d["t"])))
        if len(ix) < 20:
            continue
        tg = d["t"][ix] - d["t"][ix[0]]
        L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][ix], d["raw2"][ix],
                               float(d["q1"][ix[0]]), float(d["q2"][ix[0]]),
                               float(d["dq1"][ix[0]]), float(d["dq2"][ix[0]]),
                               float(tg[-1] - 0.004), bias1=0.0,
                               knee_deep=None, fade=True)
        if L is None:
            continue
        gi = lambda k: np.interp(tg, L["t"], L[k])
        e = [float(np.sqrt(np.mean((d[k][ix] - s) ** 2))) * (180 / np.pi if k in ("q1", "q2") else 1)
             for k, s in zip(("q1", "q2", "dq1", "dq2"),
                             (gi("thm1"), gi("q2"), gi("dq1"), gi("dq2")))]
        if all(np.isfinite(e)) and max(e) < 1e4:
            E.append(e)
    return E, d


def band(d, segs, nw):
    """각 채널이 실제로 움직인 폭 (평균 뺀 표준편차) — 오차를 나눌 분모."""
    out = []
    for k in ("q1", "q2", "dq1", "dq2"):
        v = np.asarray(d[k])
        sc = np.degrees(v) if k in ("q1", "q2") else v
        vals = [float(np.std(sc[a:a + nw])) for a in segs if a + nw <= len(sc)]
        out.append(float(np.mean(vals)) if vals else np.nan)
    return out


def main():
    import safe
    print("짐 지고 일어서기 — 외삽 능력 첫 측정 (측정 토크 주입 재생, PD 제어 없음)\n")
    print("  같은 모델로 짐 무게만 바꿔 예측한다. 짐 0kg 로 맞춘 모델이 2.5·5kg 를")
    print("  맞히면 그것이 외삽 능력이다. **이 판은 적합에 넣지 않는다.**\n")
    R = {}
    print(f"  {'경우':16s} {'짐kg':>5s} {'조각':>4s} | "
          f"{'힙각°':>14s} {'무릎각°':>15s} {'힙속도':>14s} {'무릎속도':>15s}")
    print("  " + "-" * 92)
    for sub, pay, cvt in CASES:
        try:
            E, d = run_case(sub, pay, cvt)
            segs, nw = segments(d)
            bd = band(d, segs, nw)
            if not E:
                print(f"  {sub:16s} {pay:5.1f} {0:4d} | (재생 실패)")
                continue
            A = np.array(E); mu = A.mean(axis=0)
            cells = " ".join(f"{v:6.2f}({100*v/b:4.0f}%)" if np.isfinite(b) and b > 1e-9
                             else f"{v:6.2f}(   -)" for v, b in zip(mu, bd))
            print(f"  {sub:16s} {pay:5.1f} {len(E):4d} | {cells}")
            R[sub] = dict(payload=pay, cvt=cvt, n=len(E),
                          err=list(map(float, mu)), band=list(map(float, bd)))
        except Exception as ex:
            print(f"  {sub:16s} {pay:5.1f}    - | ERR {type(ex).__name__} {ex}")
    print("\n  ※ 괄호 = 그 채널이 실제로 움직인 폭 대비 몇 % (0% 가 완벽).")
    print("     각도는 도, 속도는 rad/s. 조각 길이 0.5초씩 겹쳐 가며 전 구간.")
    # 과거 관측 확인 — 짐의 '유효 무게'가 명목보다 작다는 말이 맞나
    print("\n■ 짐의 유효 무게가 명목보다 작은가 (07-29 관측: 5kg → 4.5kg)")
    print(f"  {'경우':16s} {'넣은 무게':>9s} | {'힙각°':>7s} {'무릎각°':>8s} {'힙속도':>7s} {'무릎속도':>8s}")
    for sub, pay, cvt in CASES:
        if pay == 0:
            continue
        for eff in (pay * 0.8, pay * 0.9, pay, pay * 1.1):
            try:
                E, d = run_case(sub, pay, cvt, mass_eff=eff)
                if E:
                    mu = np.array(E).mean(axis=0)
                    print(f"  {sub:16s} {eff:9.2f} | {mu[0]:7.2f} {mu[1]:8.2f} "
                          f"{mu[2]:7.2f} {mu[3]:8.2f}")
            except Exception:
                pass
    os.environ["FS_MASS"] = STACK["FS_MASS"]
    safe.atomic_json_write(OUT, R)
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
