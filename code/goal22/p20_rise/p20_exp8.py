# -*- coding: utf-8 -*-
"""P20 실험 8 — 발 접촉 기하 오프셋 단일 파라미터의 4-전선 동시 시험.

가설(v3): 부족 토크(준정적+동적)는 무릎 관절측에 살며, 정체는 모델의 GRF→무릎
모멘트암 과대 (발 접촉점 기하 오차). 성공 판정 = **하나의 δ**가 아래 4개 전선을
동시에 λ=0 쪽으로 끌어야 함 (지금까지 어떤 가설도 통과 못 한 시험):
  F1 점프 창 점수(λ=0, 0421/0424/0602)   [참조: δ=0에서 115.1, const2.25면 79.2]
  F2 s2s 창 점수(λ=0)                     [참조: 기준선만 11.6]
  F3 0429 창 λ* (저속/고속)               [참조: +1.5 / +1.6 — 0으로 가야 함]
  F4 0604 λ* (no_load vs load_5)          [참조: +1.0 / +3.8 — 스케일링 소멸해야 함]
이동축: dL=정강이 축 방향(다리 길이), dP=면내 수직(접촉점 앞뒤) — 런타임 유한차분으로 판별.
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
import p20_exp4 as X4
from p20_exp4 import win_scan
from cvt_core import SUBS429, load_0429

sys.path.insert(0, str(HERE.parent / "p18_cvt"))
import s2s_0604 as S0

mj = P.J._P["mj"]
DST = Path((LEGACY_ROOT + "/g22_p20_results"))


def perp_axis(model):
    """calf 로컬축 중 '면내 수직(world x 지배)' 축 인덱스를 유한차분으로 판별."""
    gid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    d = mj.MjData(model)
    sq1, sq2 = -(-0.3) - np.pi / 2, -(-2.55)
    base = model.geom_pos[gid].copy()
    moves = []
    for i in range(3):
        for s, qp in ((1, None),):
            model.geom_pos[gid] = base
            d.qpos[:] = [0.55, sq1, sq2, -sq2, sq2]
            mj.mj_forward(model, d)
            p0 = d.geom_xpos[gid].copy()
            model.geom_pos[gid] = base + np.eye(3)[i] * 1e-3
            mj.mj_forward(model, d)
            p1 = d.geom_xpos[gid].copy()
            moves.append(p1 - p0)
    model.geom_pos[gid] = base
    moves = np.array(moves) / 1e-3
    # dL축 = |Δ|가 정강이 방향(대략 [-0.96,0,-0.29])과 정렬, dP축 = world-x 지배 & y≈0
    iL = int(np.argmax([abs(m @ np.array([-0.958, 0, -0.287])) for m in moves]))
    iP = int(np.argmax([abs(m[0]) * (abs(m[1]) < 0.5) for m in moves]))
    return gid, iL, iP, base


def build_flip_d(dL, dP):
    model, _ = P.build_flip(E.X32, E.V[1], E.SP)
    gid, iL, iP, base = perp_axis(model)
    v = base.copy(); v[iL] += dL; v[iP] += dP
    model.geom_pos[gid] = v
    return model


def build_cvt_d(l_i, dL, dP):
    model, _ = P.build_cvt(E.X32, E.V[1], E.SP, l_i)
    gid, iL, iP, base = perp_axis(model)
    v = base.copy(); v[iL] += dL; v[iP] += dP
    model.geom_pos[gid] = v
    return model


def f1_f2(model):
    zero = lambda tr: 0.0
    r1 = E.eval_set(model, E.JDS, zero)
    r2 = E.eval_set(model, ("s2s_gnd_0319",), zero)
    return float(np.mean(list(r1.values()))), float(list(r2.values())[0]), r1


def f3(dL, dP):
    """0429 4 subs — 창 λ* (exp7 방식 축약)."""
    import p20_exp7 as X7
    lams_lo, lams_hi = [], []
    model = None
    for sub in ("60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"):
        d = load_0429(sub)
        if model is None:
            model = build_cvt_d(d["l_i"], dL, dP)
        percfg = {}
        for lam in X7.LGRID:
            for t0, sc in X7.win_lam_429(model, d, d["l_i"], lam):
                percfg.setdefault(round(t0, 4), []).append(sc)
        for t0, scs in percfg.items():
            scs = np.array(scs)
            if (scs.max() - scs.min()) / max(scs.min(), 1e-9) < 0.02:
                continue
            ls = X7.lam_star(scs)
            i0 = int(np.searchsorted(d["t"], t0))
            (lams_hi if abs(d["dq2"][i0]) > 10 else lams_lo).append(ls)
    return (float(np.mean(lams_lo)) if lams_lo else float("nan"),
            float(np.mean(lams_hi)) if lams_hi else float("nan"))


def f4(dL, dP):
    out = {}
    for grp, sub, load in (("cvt", "no_load", 0.0), ("cvt", "load_5", 5.0)):
        d = S0.load_0604(grp, sub)
        model = build_cvt_d(d["l_i"], dL, dP)
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load
        starts = np.arange(0.3, d["t"][-1] - 0.3, 0.5)
        rs = win_scan(model, d, d["l_i"], starts, 0.2)
        out[sub] = float(np.mean([r["lam"] for r in rs])) if rs else float("nan")
    return out


def main():
    grid = [(-0.010, 0.0), (-0.005, 0.0), (0.0, 0.0), (0.005, 0.0), (0.010, 0.0),
            (0.0, -0.010), (0.0, -0.005), (0.0, 0.005), (0.0, 0.010)]
    res = {}
    for dL, dP in grid:
        model_f = build_flip_d(dL, dP)
        s1, s2, per = f1_f2(model_f)
        lo, hi = f3(dL, dP)
        o604 = f4(dL, dP)
        res[f"{dL}|{dP}"] = dict(F1=s1, F2=s2, per=per, lo429=lo, hi429=hi, **o604)
        print(f"dL={1000*dL:+5.1f}mm dP={1000*dP:+5.1f}mm | F1점프(λ0) {s1:6.1f} | "
              f"F2 s2s(λ0) {s2:5.1f} | 0429 λ* 저 {lo:+5.2f}/고 {hi:+5.2f} | "
              f"0604 λ* {o604['no_load']:+5.2f}/{o604['load_5']:+5.2f}", flush=True)
    json.dump(res, open(DST / "exp8_results.json", "w"), indent=1, default=float)
    print("참조: F1 δ0·λ0=115.1 (const2.25=79.2) | F2 기준선만=11.6 | "
          "0429 +1.5/+1.6 | 0604 +1.0/+3.8", flush=True)


if __name__ == "__main__":
    main()
