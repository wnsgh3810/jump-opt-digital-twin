# -*- coding: utf-8 -*-
"""_GHI_freeswing — 모터를 끈 자유 흔들림의 **박자**로 힙 모터축 회전 관성을 잰다 (08-12).

왜 이 방법인가 (어제 무효 판정 난 방법과 무엇이 다른가)
  08-12 낮에 "공중에서 흔든 기록에 측정 토크를 주입해 관성을 맞춘다"를 시도했다가
  **무효** 판정을 냈다. 오차가 최소가 되는 지점이 훑은 범위 끝에 있었고, 그 정체가
  "**주어진 토크를 무시하고 처음 속도로 미끄러지기**" 였다. 물리가 아니라 회피였다.

  여기서는 그 회피가 **원리상 불가능**하다:
    ① 모터가 꺼져 있어 **주입할 토크 자체가 없다** (명령 토크 표준편차 정확히 0 확인).
    ② 자유 진동은 관성을 키워도 흔들리는 **폭이 안 줄고 느려지기만** 한다.
       그래서 "관성을 키우면 안 움직여서 오차가 준다"는 퇴화가 성립하지 않는다.
    ③ 마찰은 폭을 줄이지 **박자를 거의 안 바꾼다** → 어제 뒤엉켰던 마찰과 관성이 갈린다.

데이터 (26.08.07, 사용자 확인 08-12)
  · 몸통은 **매달고 제대로 고정**했다 → 시뮬도 단단히 붙잡는다 (KB=30000).
  · 무릎은 **붙잡은 게 아니라 자유**인데 마찰 때문에 안 움직였다
    ("힙을 천천히 움직이면 무릎은 거의 안 움직이더라"). 실측 확인: 반 스윙 동안
    무릎이 움직인 각도 중앙 0.01도 · 최대 0.19도. ⇒ 시뮬도 무릎을 놓아 준다.
  · 다리를 놓을 때 **손을 완전히 뗐다** → 놓은 뒤 구간은 전부 자유 진동이다.
  · 다만 기록 전체가 자유 진동은 아니다. 사람이 들었다 놓는 것을 스무 번쯤 반복했다.
    **손이 들어 올리는 구간**을 걸러야 한다 — 손 뗀 뒤라면 마찰 때문에 흔들리는 폭이
    **반드시 줄어야** 하므로, **폭이 커진 스윙은 누가 밀어 준 것**이라 버린다.

재는 값 — "시간 비율"
  ① 무엇 대비: 다리를 한쪽에 놓고 손을 뗐을 때 **반대쪽 끝까지 가는 데 걸린 시간**을
     시뮬레이션과 실측에서 각각 구해 **시뮬 ÷ 실측**.
  ② 계산법: 실측 스윙 하나하나에 대해 같은 출발 자세로 시뮬을 돌려 비율을 내고 중앙값.
  ③ 완벽하면 **1.000**.
  ④ 물리적 뜻: 1보다 작으면 시뮬의 다리가 실제보다 **빨리** 움직인다 = **관성이 부족**하다.

결과 (08-12 · 표본 29개)
  현행 0.010 에서 0.9412 = 시뮬이 5.9% 빠르다 → 관성 부족.
  1.000 이 되는 값 = **0.0164**. 검산 범위 0.0142~0.0184, 전부 현행보다 크다.
  ★ 힙 마찰을 0 으로 놓아도 0.0153 → **마찰이 관성인 척하는 것이 아니다.**
  ★ 남는 흔들림: 크게 흔든 스윙일수록 큰 관성을 요구한다(중간 0.0145 · 큰 0.0184).
    관성은 폭과 무관해야 하므로, **빠를 때 실제를 더 느리게 만드는 무언가가 모델에 없다.**

CLI: python _GHI_freeswing.py [checks]
     인자 없으면 기본 표 · "checks" 면 검산(자료원별·폭별·마찰별)까지.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHI_freeswing.json"
DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_08_07")
FOLDS = ("no_current", "no_current2")

# 현행 런타임 스택 (CURRENT_STACK.md H3_260812) — 관성만 바꿔 가며 잰다
STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="3.733,2.309", FS_MASS="3.2988",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_CMD_LPF="0.00317,0.00292", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.2880", FS_KNEEM_DAMP="0.1617", FS_HIPM_FL="0.3026",
             FS_HIPM_DAMP="0.0964", FS_KS_HIP="138.53", FS_COMZ="thigh=-0.00189")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)

BZ = 1.5          # 발이 바닥에 안 닿는 높이 [m]
KB = 30000.0      # 몸통을 붙잡는 세기 [N/m] — 사용자 "매달고 제대로 고정"
                  #   검산: 300~100000 (333배) 로 바꿔도 답이 3% 만 움직인다.
SMOOTH = 0.05     # 각도 신호 다듬기 창 [s] — 방향전환을 잡음에서 가리기 위함
MIN_GAP = 0.10    # 방향전환끼리 최소 간격 [s] (이보다 촘촘하면 잡음)
MIN_AMP = 8.0     # 쓸 스윙의 최소 폭 [도]
MAX_DK = 5.0      # 그 동안 무릎이 움직여도 되는 한도 [도] (실측 실제값은 0.01도)
ARMS = np.array([0.005, 0.0075, 0.010, 0.0125, 0.015, 0.0175,
                 0.020, 0.025, 0.030, 0.040, 0.060])


def real_swings(fold):
    """손을 뗀 뒤의 반 스윙 전수 — (걸린 시간, 출발 힙각, 무릎각, 폭)."""
    h = pd.read_excel(DATA / fold / "hip.xlsx")
    k = pd.read_excel(DATA / fold / "knee.xlsx")
    n = min(len(h), len(k))
    t = h["Time"].to_numpy(float)[:n]; t = t - t[0]
    q1 = h["currentAngle"].to_numpy(float)[:n]
    q2 = k["currentAngle"].to_numpy(float)[:n]
    dt = float(np.median(np.diff(t)))
    w = int(SMOOTH / dt) | 1
    qs = np.convolve(q1, np.ones(w) / w, mode="same")
    ks = np.convolve(q2, np.ones(w) / w, mode="same")
    v = np.gradient(qs, dt)
    turn = list(np.where(np.diff(np.sign(v)) != 0)[0])
    keep = [turn[0]] if turn else []
    for i in turn[1:]:
        if t[i] - t[keep[-1]] > MIN_GAP:
            keep.append(i)
    out = []
    for a, b in zip(keep[:-1], keep[1:]):
        half = t[b] - t[a]
        amp = abs(np.degrees(qs[b] - qs[a]))
        dk = abs(np.degrees(ks[b] - ks[a]))
        if 0.15 < half < 1.5 and amp > MIN_AMP and dk < MAX_DK:
            out.append(dict(half=half, q1=np.degrees(qs[a]), q2=np.degrees(ks[a]),
                            amp=amp, dk=dk, vavg=amp / half))
    # 손 뗀 뒤 = 직전 스윙보다 폭이 줄었다 (늘었으면 누가 밀어 준 것)
    return [w for i, w in enumerate(out) if i and w["amp"] < out[i - 1]["amp"]]


_FT = {}


def sim_half(arm, q1_0, q2_0, tmax=2.0, key=""):
    """다리를 q1_0[도] 에 놓고 손을 뗀다(속도 0). 반대쪽 끝까지 걸린 시간 [초]."""
    import mujoco as mjm
    import fs_runner as FR
    ck = (round(float(arm), 6), key)
    if ck not in _FT:
        os.environ["FS_HIPM_ARM"] = f"{arm}"
        FR._S2S = None
        _FT[ck] = FR.fs_twin()
    ft = _FT[ck]
    m, iq, dof = ft["model"], ft["iq"], ft["dof"]
    dt = float(m.opt.timestep)
    q1 = np.radians(q1_0); q2 = np.radians(q2_0)
    md = mjm.MjData(m)
    md.qpos[:] = 0
    md.qpos[iq["hip_m"]] = -q1 - np.pi / 2
    md.qpos[iq["knee_motor"]] = -q2
    md.qpos[iq["cpin"]] = q2            # 4절 고리를 닫는 값 (0 이면 구속력 폭발)
    md.qpos[iq["knee"]] = -q2
    md.qpos[iq["base_z"]] = BZ
    mjm.mj_forward(m, md)
    md.qvel[:] = 0
    Mtot = float(sum(m.body_mass))
    prev = 0.0
    for c in range(int(tmax / dt)):
        v1 = -float(md.qvel[dof["hip_m"]])
        md.ctrl[:] = [0.0, 0.0]                      # 모터 꺼짐 — 넣을 토크가 없다
        # 무릎은 놓아 둔다 (사용자 확인: 자유인데 마찰 때문에 안 움직였다)
        md.qfrc_applied[dof["base_z"]] = (
            KB * (BZ - md.qpos[iq["base_z"]])
            - 2 * np.sqrt(KB * 3.3) * md.qvel[dof["base_z"]]
            + Mtot * 9.81)                           # 무게는 미리 받쳐 처짐을 없앤다
        mjm.mj_step(m, md)
        if not np.isfinite(md.qpos).all():
            return np.nan
        if c > 20 and prev * v1 < 0:                 # 방향이 바뀐 순간 = 반대쪽 끝
            return c * dt
        prev = v1
    return np.nan


def solve(sws, key=""):
    """시간 비율이 1.000 을 가로지르는 관성을 보간으로 찾는다. 반환 (관성, 비율표)."""
    med = []
    for arm in ARMS:
        r = [sim_half(arm, w["q1"], w["q2"], key=key) / w["half"] for w in sws]
        r = [x for x in r if np.isfinite(x)]
        med.append(float(np.median(r)) if r else np.nan)
    med = np.array(med)
    ok = np.isfinite(med)
    if ok.sum() < 3 or med[ok].min() > 1 or med[ok].max() < 1:
        return np.nan, med          # 훑은 범위에서 1.0 을 못 가로지름
    return float(np.interp(1.0, med[ok], ARMS[ok])), med


def main():
    import safe
    S = {f: real_swings(f) for f in FOLDS}
    allsw = [w for ws in S.values() for w in ws]
    print("모터를 끈 자유 흔들림으로 힙 모터축 회전 관성을 잰다 (현행 0.010 kg·m²)\n")
    print(f"  표본: {' · '.join(f'{f} {len(s)}개' for f, s in S.items())} "
          f"(합계 {len(allsw)}개)")
    print(f"  실측에서 반 스윙 동안 무릎이 움직인 각도: 중앙 "
          f"{np.median([w['dk'] for w in allsw]):.2f}도 · 최대 "
          f"{max(w['dk'] for w in allsw):.2f}도  (= 사실상 고정)\n")
    a, med = solve(allsw)
    print(f"  {'관성':>8s} {'시간 비율':>10s}   (1.000 이면 완벽 · 1 미만이면 관성 부족)")
    for arm, m_ in zip(ARMS, med):
        tag = "  ← 현행" if abs(arm - 0.010) < 1e-9 else ""
        print(f"  {arm:8.4f} {m_:10.4f}{tag}")
    print(f"\n  ⇒ 시간 비율이 1.000 이 되는 관성 = **{a:.4f}** (현행의 {a/0.010:.2f}배)")
    R = dict(n=len(allsw), arms=list(map(float, ARMS)),
             ratio=list(map(float, med)), answer=float(a))
    if len(sys.argv) > 1 and sys.argv[1] == "checks":
        print("\n■ 검산 — 답이 내가 정한 설정·자료 나누기에 얼마나 휘둘리나")
        R["checks"] = {}
        for f, sws in S.items():
            v, _ = solve(sws)
            R["checks"][f] = float(v)
            print(f"   자료원 {f:14s} n={len(sws):3d}  {v:.4f}")
        amps = np.array([w["amp"] for w in allsw])
        e = np.percentile(amps, [0, 33, 66, 100])
        for i, lab in enumerate(("작은 폭", "중간 폭", "큰 폭")):
            m = (amps >= e[i]) & (amps <= e[i + 1])
            v, _ = solve([w for w, x in zip(allsw, m) if x])
            R["checks"][f"amp_{lab}"] = float(v)
            print(f"   {lab} ({e[i]:.0f}~{e[i+1]:.0f}도)  n={int(m.sum()):3d}  {v:.4f}"
                  + ("   ← 관성은 폭과 무관해야 한다" if i == 2 else ""))
        for fl, dm, lab in ((0.0, 0.0, "힙 마찰 0"), (0.28, 0.0, "매달림 실측(건마찰만)"),
                            (0.3026, 0.0964, "현행")):
            os.environ["FS_HIPM_FL"] = f"{fl}"; os.environ["FS_HIPM_DAMP"] = f"{dm}"
            v, _ = solve(allsw, key=lab)
            R["checks"][lab] = float(v)
            print(f"   {lab:22s} n={len(allsw):3d}  {v:.4f}"
                  + ("   ← 마찰이 관성인 척하면 여기서 크게 달라진다" if fl == 0 else ""))
        os.environ["FS_HIPM_FL"] = STACK["FS_HIPM_FL"]
        os.environ["FS_HIPM_DAMP"] = STACK["FS_HIPM_DAMP"]
    os.environ.pop("FS_HIPM_ARM", None)
    safe.atomic_json_write(OUT, R)
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
