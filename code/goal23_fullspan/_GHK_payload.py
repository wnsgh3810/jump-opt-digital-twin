# -*- coding: utf-8 -*-
"""_GHK_payload — **짐 지고 일어서기로 외삽 능력을 잰다** (08-12).

왜 이게 필요한가
  이 연구의 최종 목표는 "짐 지고 일어서기·앞으로 뛰기 같은 **해본 적 없는 동작**을
  시뮬레이션만으로 예측하는 것" 이다. 그런데 채점에 올라 있는 10 세션이 **전부 점프**다.
  ⇒ **외삽 능력을 한 번도 잰 적이 없다.** 26.06.04 에 데이터가 있는데 채점에 없다.

무엇을 재나
  측정된 토크를 시뮬레이션에 그대로 넣고 돌린 뒤(PD 제어 없음) 관절 각도·각속도가
  실제와 얼마나 맞는지 본다. PD 가 없어 오차를 감춰 주지 않으므로 물리가 틀리면 드러난다.
  **짐 무게만 바꿔 가며** 같은 모델로 예측한다 — 짐 0kg 로 맞춘 모델이 2.5·5kg 를
  맞히면 그것이 곧 외삽 능력이다.

★★ **통짜로 잰다 — 조각으로 자르지 말 것** (사용자 지적 08-12 · 규약 §11-2)
  "창 분할 재생은 **에러를 초기화해 모델 발전의 자가 못 된다**."
  08-12 첫 판에서 0.25초 조각으로 쟀다가 지적받았다. 조각을 쓰면 무릎 각도 오차가
  234~673도 → 4.8~9.5도 로 **보이지만**, 그건 0.25초마다 실측으로 되돌려 준 결과일 뿐
  모델이 실제로 그만큼 따라간다는 뜻이 아니다.

  대신 **"따라간 시간"** 을 같이 잰다 — 통짜 재생에서 무릎 각도 오차가 문턱을 처음
  넘을 때까지의 시간 [초]. **길수록 좋다.** 이러면 길이가 다른 과제끼리도 견줄 수 있다.

★ 앉은 구간은 제외한다 (규약 §7 off-stop): 앉아 있는 동안은 몸통이 레일 아래 받침에
  얹혀 있는데 모델에 그 하중 경로가 없다. 과거에 이 구간 오염으로 발산 220~267도가 났다.
  실측 각도로 몸통 높이를 계산해 판정한다. **이건 '오차 초기화'와 다르다** —
  물리가 없는 구간을 빼는 것이지 중간에 되돌리는 것이 아니다.

유효한 데이터 (데이터 사전 + 파일 확인 08-12)
  · 변속기 있음(링크 25.19mm): 0kg · 2.5kg · 5kg — 셋 다 유효
  · 변속기 없음: **0kg 만 유효** — 5kg/7.5kg 는 기립 실패라 파일 자체가 없다

짐을 어떻게 넣나
  총질량을 늘리면 러너가 **몸통(base)에 몰아서** 붙인다 = 짐을 몸통에 얹는 것과 같다
  (사용자 확인 08-12: "짐은 base 에 통째로 실었다").

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
Z_MIN = 0.10                # 몸통이 이 높이[m] 위로 떠 있는 구간만
FOLLOW_TH = 10.0            # '따라간 시간' 문턱 [도] — 무릎 각도 오차가 이걸 넘으면 놓친 것
CASES = [("cvt/no_load",   0.0, True),
         ("cvt/load_2.5",  2.5, True),
         ("cvt/load_5",    5.0, True),
         ("no_cvt/no_load", 0.0, False)]


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


def stand_window(d):
    """몸통이 받침에서 **떠 있는** 통짜 구간 (i0, i1). 앉은 구간은 제외."""
    ok = base_height(d["q1"], d["q2"]) > Z_MIN
    if ok.sum() < 30:
        return None
    return int(np.argmax(ok)), int(len(ok) - np.argmax(ok[::-1]))


def run_case(sub, payload, is_cvt, mass_eff=None):
    """통짜 재생. 반환 (오차 4채널, 따라간 시간[s], 창 길이[s], 데이터)."""
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
    w = stand_window(d)
    if w is None:
        return None, np.nan, np.nan, d
    i0, i1 = w
    ix = np.arange(i0, i1)
    tg = d["t"][ix] - d["t"][ix[0]]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][ix], d["raw2"][ix],
                           float(d["q1"][ix[0]]), float(d["q2"][ix[0]]),
                           float(d["dq1"][ix[0]]), float(d["dq2"][ix[0]]),
                           float(tg[-1] - 0.004), bias1=0.0, knee_deep=None, fade=True)
    if L is None:
        return None, 0.0, float(tg[-1]), d
    gi = lambda k: np.interp(tg, L["t"], L[k])
    sim = (gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"))
    e = [float(np.sqrt(np.mean((d[k][ix] - s) ** 2))) * (180 / np.pi if k in ("q1", "q2") else 1)
         for k, s in zip(("q1", "q2", "dq1", "dq2"), sim)]
    dk = np.degrees(np.abs(d["q2"][ix] - sim[1]))
    bad = np.where(dk > FOLLOW_TH)[0]
    follow = float(tg[bad[0]]) if len(bad) else float(tg[-1])
    return e, follow, float(tg[-1]), d


def band(d):
    """각 채널이 떠 있는 구간에서 실제로 움직인 폭 (평균 뺀 표준편차)."""
    w = stand_window(d)
    if w is None:
        return [np.nan] * 4
    i0, i1 = w
    return [float(np.std(np.degrees(np.asarray(d[k])[i0:i1]) if k in ("q1", "q2")
                         else np.asarray(d[k])[i0:i1]))
            for k in ("q1", "q2", "dq1", "dq2")]


def main():
    import safe
    print("짐 지고 일어서기 — 외삽 능력 (측정 토크 주입 재생, PD 제어 없음)")
    print()
    print("  * 통짜 재생이다 — 중간에 실측으로 되돌리지 않는다. 조각으로 자르면")
    print("    오차가 초기화되어 모델을 재는 자가 못 된다 (규약, 사용자 지적 08-12).")
    print("  * 같은 모델로 짐 무게만 바꿔 예측한다. 이 판은 적합에 넣지 않는다.")
    print()
    R = {}
    print(f"  {'경우':16s} {'짐kg':>5s} {'창s':>5s} {'따라간s':>7s} | "
          f"{'힙각°':>13s} {'무릎각°':>14s} {'힙속도':>13s} {'무릎속도':>14s}")
    print("  " + "-" * 100)
    for sub, pay, cvt in CASES:
        try:
            e, follow, span, d = run_case(sub, pay, cvt)
            bd = band(d)
            if e is None:
                print(f"  {sub:16s} {pay:5.1f} {span:5.2f} {follow:7.2f} | (재생 발산)")
                R[sub] = dict(payload=pay, cvt=cvt, err=None, follow=follow, span=span)
                continue
            cells = " ".join(f"{v:6.2f}({100*v/b:4.0f}%)" if np.isfinite(b) and b > 1e-9
                             else f"{v:6.2f}(   -)" for v, b in zip(e, bd))
            print(f"  {sub:16s} {pay:5.1f} {span:5.2f} {follow:7.2f} | {cells}")
            R[sub] = dict(payload=pay, cvt=cvt, err=list(map(float, e)),
                          band=list(map(float, bd)), follow=follow, span=span)
        except Exception as ex:
            print(f"  {sub:16s} {pay:5.1f}     -       - | ERR {type(ex).__name__} {ex}")
    print()
    print("  * '창s' = 몸통이 떠 있는 구간 길이 [초]")
    print(f"  * '따라간s' = 무릎 각도 오차가 {FOLLOW_TH:.0f}도를 처음 넘을 때까지의 시간 [초]")
    print("    — 길수록 좋다. 창 전체와 같으면 끝까지 따라간 것이다.")
    print("  * 괄호 = 그 채널이 실제로 움직인 폭 대비 몇 % (0% 가 완벽). 각도 도, 속도 rad/s.")
    print("  * 통짜라 오차가 계속 쌓인다 — 길이가 다른 판끼리 값 비교 금지.")
    print()
    print("■ 짐의 유효 무게가 명목보다 작은가 (07-29 관측: 5kg 이 4.5kg 처럼 작용)")
    print(f"  {'경우':16s} {'넣은 무게':>9s} {'따라간s':>7s} | {'힙각°':>7s} {'무릎각°':>8s}")
    EFF = {}
    for sub, pay, cvt in CASES:
        if pay == 0:
            continue
        for eff in (pay * 0.8, pay * 0.9, pay, pay * 1.1):
            try:
                e, follow, span, d = run_case(sub, pay, cvt, mass_eff=eff)
                if e:
                    print(f"  {sub:16s} {eff:9.2f} {follow:7.2f} | {e[0]:7.2f} {e[1]:8.2f}")
                    EFF.setdefault(sub, []).append(dict(eff=eff, follow=follow,
                                                        err=list(map(float, e))))
            except Exception:
                pass
    os.environ["FS_MASS"] = STACK["FS_MASS"]
    R["_eff"] = EFF
    safe.atomic_json_write(OUT, R)
    print(f"\n저장 -> {OUT}")


if __name__ == "__main__":
    main()
