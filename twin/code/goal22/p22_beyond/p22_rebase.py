# -*- coding: utf-8 -*-
"""P22 Phase 0 — 골든 재베이스라인: fix0421 전/후 P19 지표 v4 7성분 + OLdq 바닥 재산정.

출력: p22_rebase.json (before/after 성분표) — MARATHON_p22.md의 베이스라인 표 원천.
CL 경로는 xlsx 직독이라 fix 전후 동일해야 함 (침묵실패 방역 겸 일관성 체크).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C
import p19_adapter as AD
import p22_fix0421 as FX


def x19_vec():
    C19 = AD.load_candidate(HERE.parent / "p19_jump/fourbar_p19_candidate.json")
    v19 = np.array(C19["x"], float)
    x19 = np.array([v19[0], v19[1], v19[3], v19[4], v19[5], v19[6], v19[7], v19[8],
                    v19[9], v19[10], v19[11], v19[12], v19[13], v19[14], v19[15],
                    0.0, 6.0, v19[16], v19[17], v19[2]])
    return np.clip(x19, C.LO + 1e-9, C.HI - 1e-9)


def parts_dict(p):
    jcl, jdq, jw02, (j6j, j6c), s2s, o6 = p
    return dict(CL=float(jcl), DQ=float(jdq), JW2=float(jw02),
                J6J=float(j6j), J6C=float(j6c), S2S=float(s2s), O6=float(o6))


def dq_noise_floor():
    """OLdq 바닥: 유지(저속) 구간 dq2의 표본 표준편차 = 측정 노이즈 바닥 추정."""
    P12 = C._W["P12"]
    out = {}
    for tr in P12._G["trials"]:
        if not tr.get("isj", False):
            continue
        v2 = np.asarray(tr["v2"], float)
        m = np.abs(v2) < 0.5
        if m.sum() >= 10:
            out.setdefault(tr["ds"], []).append(float(v2[m].std()))
    return {k: float(np.mean(v)) for k, v in out.items()}


def main():
    C.winit_worker(dict(CL=1, DQ=1, JW2=1, J6J=1, J6C=1, S2S=1, O6=1, raw=True))
    x19 = x19_vec()
    print("=== BEFORE fix0421 ===", flush=True)
    before = parts_dict(C.eval_parts(x19))
    print(before, flush=True)
    rows = FX.apply(C._W["P"])
    print("=== AFTER fix0421 ===", flush=True)
    after = parts_dict(C.eval_parts(x19))
    print(after, flush=True)
    floor = dq_noise_floor()
    print("dq2 noise floor (rad/s):", floor, flush=True)
    res = dict(before=before, after=after,
               fix_ratios=[(s, j, float(r)) for s, j, r in rows],
               dq2_noise_floor=floor)
    json.dump(res, open(HERE / "p22_rebase.json", "w"), indent=1)
    print("saved p22_rebase.json", flush=True)


if __name__ == "__main__":
    main()
