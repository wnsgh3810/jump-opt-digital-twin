# -*- coding: utf-8 -*-
"""**현행 트윈으로 점프 계획 궤적을 만든다** (수직 점프, 08-14 신설).

■ 왜 새로 만드나 — 끊어져 있던 다리
  실기에 내려 본 유일한 계획(26.07.27)은 **07-25 시절 트윈**으로 만들어졌고, 그 트윈이
  실기보다 궤적을 훨씬 못 따라가서(추종 오차 힙 12.9° vs 실기 8.1°) **실효 게인을 0.40배로
  줄여** 토크를 계산했다. 그런데 지금 트윈은 실기만큼 따라간다(7.5°, 0.93배)라 그 축소가
  더 이상 맞지 않는다. 그 결과 배포된 계획의 힙 토크가 실측보다 **1.49배 작았다**.
  ⇒ 계획은 **지금 트윈으로, 실효 게인 축소 없이** 다시 만들어야 한다. 그 경로가 없어서 만든다.

■ 무엇을 정하나 (결정 변수 16 개)
  · 시작 자세 2 개 (힙·무릎 각도) — 로봇이 웅크리고 대기하는 자세
  · 목표각 곡선의 매듭 14 개 (관절당 7 개, 0.6 초 구간). 첫 매듭은 시작 자세와 같게 묶는다.
  목표각 곡선을 부드러운 3차 곡선으로 잇고, 그 미분을 목표 속도로 쓴다.
  실기는 이 목표각·목표속도만 받아 PD 제어로 따라간다 (앞먹임 토크 없음).

■ 무엇을 좋다고 하나
  **점프 높이(몸통 중심의 최고 높이 [m], 클수록 좋다)** 를 최대로 하되, 아래를 어기면 벌점:
  축 토크 15 N·m · 모터 속도-토크 한계선 · 관절 각도 범위 · 관절 속도 50 rad/s ·
  발이 땅에 붙어 있는 시간 0.3 초. (제약 정의는 기존 파일 `t0_spec.py` 를 그대로 쓴다 —
  이 값들은 최종 목표인 궤적 최적화 과제에서 온 것이라 여기서 바꾸면 안 된다.)

■ 어느 트윈으로 도나
  기본은 지금 배포된 값 묶음. 탐색이 끝나 새 값이 나오면 `--stack _GHB_sweep5.json` 처럼
  주면 **그 값으로** 계획을 만든다. 즉 트윈이 좋아지면 계획도 같이 좋아진다.

■ 산출
  `_PLAN_<태그>.npz` — 기존 계획 파일과 **같은 형식**이라 최종 지표 도구(`fs_taufid.py`)로
  바로 잴 수 있다. 그리고 `_PLAN_<태그>_audit.json` (제약 검사 결과).

사용법:
  python fs_plan.py --tag v10 --budget 2000            (지금 배포 스택으로)
  python fs_plan.py --tag v10n --stack _GHB_sweep5.json  (탐색 결과로)
  ※ 오래 걸리므로 사용자가 .bat 으로 시동하는 것을 권장한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p25_task0"))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "0")

import t0_spec as T0             # noqa: E402  제약 정의 (최종 과제에서 온 값 — 변경 금지)

T_END = 0.6          # 목표각 곡선의 길이 [s]
N_KNOT = 8           # 관절당 매듭 수 (첫 매듭은 시작 자세)
GRID = 0.002         # 목표각을 넘겨줄 시간 간격 [s]
CRASH = 1e3


def apply_stack(spec):
    """트윈에 어떤 값 묶음을 심을지 정한다. spec=None 이면 지금 배포된 값."""
    import _GHB_sweep as S
    if spec in (None, "", "deploy"):
        x = np.asarray(S.DEPLOY, float)
        src = "배포 스택 (CURRENT_STACK.md)"
    else:
        p = Path(spec)
        if not p.is_absolute():
            p = HERE / p
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        x = np.asarray(d["res"]["canon_cap"]["x"], float)
        src = f"{p.name} 의 탐색 승자"
    S._apply(S.env_of("canon_cap", x))
    return x, src


def spline(knots_t, knots_v, tg):
    """매듭을 부드러운 3차 곡선으로 잇는다. (값, 미분) 반환."""
    from scipy.interpolate import CubicSpline
    cs = CubicSpline(knots_t, knots_v, bc_type=((1, 0.0), (1, 0.0)))
    return cs(tg), cs(tg, 1)


def rollout(ft, x, gains, record=False):
    """결정 변수 → 트윈 폐루프 재생 로그. 발산하면 None."""
    import fs_runner as FR
    q1_0, q2_0 = float(x[0]), float(x[1])
    kt = np.linspace(0.0, T_END, N_KNOT)
    k1 = np.concatenate([[q1_0], np.asarray(x[2:2 + N_KNOT - 1], float)])
    k2 = np.concatenate([[q2_0], np.asarray(x[2 + N_KNOT - 1:], float)])
    tg = np.arange(0.0, T_END + 1e-9, GRID)
    qd1, dqd1 = spline(kt, k1, tg)
    qd2, dqd2 = spline(kt, k2, tg)
    try:
        L = FR.rollout_cl_fs(ft, tg, qd1, qd2, dqd1, dqd2, gains, T_END, t_after=0.6)
    except Exception:
        return None
    if L is None:
        return None
    L["qd1_g"], L["qd2_g"], L["dqd1_g"], L["dqd2_g"], L["tg"] = qd1, qd2, dqd1, dqd2, tg
    return L


def stance_time(L):
    """발이 땅에 붙어 있던 시간 [s] — 접촉 수직력이 사라지는 순간까지."""
    t = np.asarray(L["t"], float)
    fz = np.abs(np.asarray(L.get("cfz", np.zeros_like(t)), float))
    m = t >= 0.0
    if not m.any():
        return 0.0
    on = fz[m] > 1.0                      # 1 N — 접촉 유무만 본다 (힘 크기는 안 쓴다)
    if not on.any():
        return 0.0
    tt = t[m]
    off = np.where(~on)[0]
    off = off[off > np.argmax(on)]
    return float(tt[off[0]] - tt[0]) if len(off) else float(tt[-1] - tt[0])


def apex(L):
    """몸통 중심의 최고 높이 [m] — 이 연구의 점프 높이 정의 (정본과 같다)."""
    return float(np.max(np.asarray(L["bz"], float)))


def audit_of(L):
    """제약 검사 — 기존 정의(t0_spec)를 그대로 쓴다. 축 토크 이름만 맞춰 준다."""
    m = np.asarray(L["t"], float) >= -1e-9
    A = {k: np.asarray(L[k], float)[m] for k in ("t", "q1", "q2", "dq1", "dq2")}
    A["sh1"] = np.asarray(L["s1"], float)[m]
    A["sh2"] = np.asarray(L["s2"], float)[m]
    out = T0.audit(A, t_end=T_END, cvt=False)
    out["stance"] = stance_time(L)
    out["stance_gap"] = out["stance"] - T0.T_ST_MAX
    out["pass_all"] = bool(out["pass"] and out["stance_gap"] <= 1e-6)
    return out


def objective(ft, x, gains, w=1.0):
    """작을수록 좋다. = −(점프 높이) + 제약 위반 벌점."""
    L = rollout(ft, x, gains)
    if L is None:
        return CRASH, None, None
    a = audit_of(L)
    pen = 0.0
    for k, v in a.items():
        if k in ("pass", "pass_all", "stance"):
            continue
        pen += w * max(0.0, float(v)) * (500.0 if k.startswith("q") else 50.0)
    pen += w * 200.0 * max(0.0, a["stance_gap"])
    return -apex(L) + pen, L, a


def bounds():
    lo = [T0.Q1_LB, T0.Q2_LB] + [T0.Q1_LB] * (N_KNOT - 1) + [T0.Q2_LB] * (N_KNOT - 1)
    hi = [T0.Q1_UB, T0.Q2_UB] + [T0.Q1_UB] * (N_KNOT - 1) + [T0.Q2_UB] * (N_KNOT - 1)
    return np.asarray(lo, float), np.asarray(hi, float)


def seed_from_v9():
    """옛 계획(v9)의 목표각 매듭을 출발점으로 쓴다 — 이미 제약을 통과한 자리라 안전하다."""
    p = HERE.parent / "goal22" / "p25_task0" / "t0nc_cl_v9.npz"
    if not p.exists():
        return None
    Z = np.load(p)
    if "knots_qd1" not in Z:
        return None
    k1 = np.asarray(Z["knots_qd1"], float); k2 = np.asarray(Z["knots_qd2"], float)
    if len(k1) < N_KNOT or len(k2) < N_KNOT:
        return None
    return np.concatenate([[k1[0], k2[0]], k1[1:N_KNOT], k2[1:N_KNOT]])


def save(tag, L, a, gains, x, src):
    """기존 계획 파일과 같은 형식으로 저장 — 최종 지표 도구가 그대로 읽는다."""
    t = np.asarray(L["t"], float)
    g = lambda k: np.asarray(L[k], float)          # noqa: E731
    tg = L["tg"]
    ip = lambda v: np.interp(t, tg, v)             # noqa: E731
    out = dict(t=t, q1=g("q1"), q2=g("q2"), dq1=g("dq1"), dq2=g("dq2"),
               raw1=g("c1"), raw2=g("c2"),          # 환산식 통과 **전** 명령 [N·m]
               tau1_nm=g("s1"), tau2_nm=g("s2"),    # 관절 축토크 [N·m]
               bz=g("bz"), qd1=ip(L["qd1_g"]), qd2=ip(L["qd2_g"]),
               dqd1=ip(L["dqd1_g"]), dqd2=ip(L["dqd2_g"]),
               gains=np.asarray(gains, float), h_plan=apex(L),
               knot_t=np.linspace(0.0, T_END, N_KNOT),
               knots_qd1=np.concatenate([[x[0]], x[2:2 + N_KNOT - 1]]),
               knots_qd2=np.concatenate([[x[1]], x[2 + N_KNOT - 1:]]),
               clip_raw=35.5, q0=np.asarray([x[0], x[1]], float))
    np.savez(HERE / f"_PLAN_{tag}.npz", **out)
    with open(HERE / f"_PLAN_{tag}_audit.json", "w", encoding="utf-8") as f:
        json.dump(dict(audit=a, h_plan=apex(L), gains=list(map(float, gains)),
                       stack=src, x=list(map(float, x)),
                       note="실효 게인 축소 없음 (라벨 게인 그대로) — 08-14 규약"),
                  f, ensure_ascii=False, indent=1, default=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v10")
    ap.add_argument("--stack", default="deploy")
    ap.add_argument("--budget", type=int, default=2000, help="평가 횟수")
    ap.add_argument("--gains", default="150,2.2,250,3", help="로봇에 넣을 게인 라벨")
    ap.add_argument("--smoke", action="store_true", help="배선만 확인 (3 회 평가)")
    args = ap.parse_args()

    import fs_runner as FR
    x_stack, src = apply_stack(args.stack)
    gains = tuple(float(v) for v in args.gains.split(","))
    ft = FR.fs_twin()
    lo, hi = bounds()
    print(f"■ 계획 만들기 — 트윈: {src}")
    print(f"  게인 라벨 {gains} · **실효 게인 축소 없음** (08-14 규약: 옛 계획은 0.40배로 줄여 만들어 1.49배 어긋났다)")

    x0 = seed_from_v9()
    if x0 is None:
        x0 = 0.5 * (lo + hi)
        print("  출발점: 범위 가운데 (옛 계획 매듭을 못 읽음)")
    else:
        x0 = np.clip(x0, lo, hi)
        print("  출발점: 옛 계획(v9)의 목표각 매듭")
    v0, L0, a0 = objective(ft, x0, gains)
    print(f"  출발점 점수 {v0:.4f} · 높이 {apex(L0) if L0 else float('nan'):.4f} m"
          f" · 제약통과 {a0['pass_all'] if a0 else '—'}")
    if args.smoke:
        for i in range(2):
            xx = np.clip(x0 + 0.02 * (hi - lo) * np.random.RandomState(i).randn(len(x0)), lo, hi)
            v, L, a = objective(ft, xx, gains)
            print(f"  흔들기 {i+1}: 점수 {v:.4f} · 높이 {apex(L) if L else float('nan'):.4f} m")
        print("배선 확인 완료 (실제 탐색은 --smoke 없이).")
        return

    # ── 여러 판으로 나눠 돈다 (기존 생성기가 쓰던 방식) ────────────────────────────
    #   왜: 제약을 어긴 자리에서 출발하면 한 판으로는 잘 못 빠져나온다. 실제로 1500 회를
    #   한 판으로 돌렸더니 160 회 만에 멈춰 서서 끝까지 안 움직였다.
    #   ⇒ ① 벌점 무게를 판마다 올려 "일단 규칙부터 지키게" 만들고 ② 매 판 최고점에서
    #     다시 출발하며 ③ 흔드는 폭(sigma)을 줄여 간다. 규칙을 지키게 된 뒤부터는
    #     높이를 키우는 쪽으로 자연히 움직인다.
    import cma
    t0 = time.time()
    rounds = [(1.0, 0.20), (5.0, 0.12), (25.0, 0.07), (25.0, 0.04)]
    per = max(200, args.budget // len(rounds))
    best = (v0, x0.copy())
    xcur = x0.copy()
    for ri, (w, sig) in enumerate(rounds, 1):
        es = cma.CMAEvolutionStrategy(((xcur - lo) / (hi - lo)).tolist(), sig,
                                      {"bounds": [0, 1], "popsize": 18,
                                       "seed": 20260814 + ri,
                                       "maxfevals": per, "verbose": -9})
        rb = (np.inf, xcur.copy())
        while not es.stop():
            Xn = es.ask()
            F = []
            for z in Xn:
                xx = lo + np.asarray(z, float) * (hi - lo)
                v, _L, _a = objective(ft, xx, gains, w=w)
                F.append(v)
                if v < rb[0]:
                    rb = (v, xx.copy())
            es.tell(Xn, F)
        xcur = rb[1].copy()
        # 판 사이 비교는 **같은 자(무게 1.0)** 로 한다 — 무게를 올린 판의 점수는 서로 못 견준다
        v1, L1, a1 = objective(ft, xcur, gains, w=1.0)
        if v1 < best[0]:
            best = (v1, xcur.copy())
        print(f"  [{(time.time()-t0)/60:5.1f}분] {ri}판(벌점무게 {w:g}) 끝 · "
              f"높이 {apex(L1) if L1 else float('nan'):.4f} m · 제약통과 {a1['pass_all'] if a1 else '—'} · "
              f"공통자 점수 {v1:.4f}", flush=True)
    v, L, a = objective(ft, best[1], gains)
    print(f"\n■ 결과: 점프 높이 {apex(L):.4f} m · 제약통과 {a['pass_all']} · "
          f"발 붙은 시간 {a['stance']:.3f}s")
    print("  제약 위반량 (0 이하가 통과): " +
          " · ".join(f"{k} {v:+.4f}" for k, v in a.items()
                     if k not in ("pass", "pass_all", "stance")))
    save(args.tag, L, a, gains, best[1], src)
    print(f"  저장 → _PLAN_{args.tag}.npz  (최종 지표는 fs_taufid 로 잰다)")


if __name__ == "__main__":
    main()
