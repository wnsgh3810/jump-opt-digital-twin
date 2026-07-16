# -*- coding: utf-8 -*-
"""p23_register — P23 승자 등록: fourbar_p23a_candidate.json 생성 (MARATHON_p23.md Phase 4).

승자 = p23_fit_nsga_ckpt.json (gen80, 23축)의 **가능해 min-F2 개체** (pop index 1,
F=[0.9708, 0.927]) — p23_ho_check.json으로 held-out 사전 검증된 개체 (HO CL 34.7%,
HO 재생 진단 2.92). 구조 = P23_SPRING_GATED=1 + P23_RISE_GATED=1, LAW_C 고정.

절차 (이 스크립트는 후보 JSON 하나만 쓴다 — safe.candidate_save, 덮어쓰기 불가):
  1. ckpt에서 가능해 min-F2 개체 선별 → p23_ho_check.json 승자와 동일성 assert
  2. p23_v6_eval.evaluate 신선 재평가 → F 재현 assert + 성분/게이트/J_v5/J_v6 확보
  3. 스키마 = fourbar_p22b_candidate.json 확장 (judge="p23", structure 블록,
     v6_gates, heldout {cl, replay_diag}, metric_full=신선 CL(=judge FIT 규약))
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent

# ── 구조 플래그: p23 모듈 import 전에 확정 (p23_v6_runners가 import 시점에 읽음) ──
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

CKPT = HERE / "p23_fit_nsga_ckpt.json"
HO = HERE / "p23_ho_check.json"
P22B = HERE.parent / "p22_beyond/fourbar_p22b_candidate.json"
OUT = HERE / "fourbar_p23a_candidate.json"
FF_SESS = ("jump_0422", "jump_0319tau")
OLDQ_SESS = ("jump_0424", "jump_0602", "jump_0429")


def pick_winner():
    """ckpt → (pop_index, x, F, gen). 가능해 중 F2 최소 + ho_check 승자와 동일성 검증."""
    ck = safe.read_json(CKPT)
    X = np.array(ck["X"], float)
    F = np.array(ck["F"], float)
    G = np.array(ck["G"], float)
    feas = (G <= 0).all(axis=1)
    assert feas.any(), "ckpt에 가능해 없음"
    idx = np.where(feas)[0]
    i = int(idx[np.argmin(F[idx, 1])])
    ho = safe.read_json(HO)
    assert i == int(ho["row"]), f"min-F2 index {i} != ho_check row {ho['row']}"
    assert np.allclose(X[i], ho["x"], atol=1e-12), "ckpt 개체 != p23_ho_check.json 승자"
    return i, [float(a) for a in ho["x"]], F[i], int(ck["gen"]), ho


def fresh_eval(x):
    """신선 재평가 → (comp, F=[f1,f2]) — p23_fit_nsga.normalize(검증 진입점) 재사용."""
    import p23_v6_eval as V
    import p23_fit_nsga as N
    comp = V.evaluate(np.asarray(x, float), verbose=True, keep_rows=False)
    a5, aff, _ = V.anchors()
    f, _ = N.normalize(comp, a5, aff)
    return comp, f


def main():
    import p23_v6_runners as RU
    assert RU.SPRING_GATED and RU.RISE_GATED and RU.NV23 == 23, "구조 플래그/축수 불일치"
    i, x, F_ck, gen, ho = pick_winner()
    print(f"승자: ckpt gen{gen} pop[{i}]  F_ckpt=[{F_ck[0]:.4f}, {F_ck[1]:.4f}]", flush=True)
    assert len(x) == 23 and abs(x[14] - 0.001235357746802837) < 1e-15

    comp, f = fresh_eval(x)
    print(f"신선 평가: F=[{f[0]:.4f}, {f[1]:.4f}]  CL={comp['CL']:.5f}  "
          f"J_v6={comp['J_v6']:.4f}  J_v5={comp['J_v5']:.4f}", flush=True)
    assert abs(f[0] - F_ck[0]) < 5e-4 and abs(f[1] - F_ck[1]) < 5e-4, \
        f"F 재현 실패: fresh {f} vs ckpt {F_ck.tolist()} — 규약 드리프트 규명 먼저"

    p22b = safe.read_json(P22B)
    cmdlayer = dict(p22b["cmdlayer"])
    cmdlayer["TM"] = x[14]

    cand = {
        "CANDIDATE": ("P23 p23a — NSGA-II(v6) gen80 가능해 min-F2 (pop 1) : 측정 법칙 + "
                      "부하연동 스프링 + 게이트 상승항, held-out 사전검증 (2026-07-16)"),
        "judge": "p23",
        "names": list(RU.NAMES23),
        "x": x,
        "A": "paper",
        "structure": {
            "spring_gated": True,
            "rise_gated": True,
            "LAW_C": -0.0281448,
            "note": ("측정 법칙(P23-2) + 부하연동 스프링(P23-4b, springref 도-해석 유령) + "
                     "게이트 너머 상승항(P23-4c, K_RISE=측정 CI 내)"),
        },
        "cmdlayer": cmdlayer,
        "v6_gates": {
            "norm": {k: float(v) for k, v in comp["norm"].items()},
            "pass": {k: bool(v) for k, v in comp["gates"].items()},
        },
        "J_v6": float(comp["J_v6"]),
        "J_v5": float(comp["J_v5"]),
        "heldout": {
            "cl": float(ho["cl"]),
            "replay_diag": float(np.mean(ho["rep"])),
        },
        "metric_full": round(float(comp["CL"]), 4),
        "origin": {
            "nsga_gen": gen,
            "pop_index": i,
            "ckpt": "p23_fit_nsga_ckpt.json",
            "F": [float(f[0]), float(f[1])],
            "anchors": "p23_anchors.json (v6 신규) + p22_eval_anchors.json (v5)",
            "ho_check": "p23_ho_check.json",
        },
    }
    safe.candidate_save(OUT, cand)
    print(f"saved {OUT}", flush=True)
    print(f"metric_full={cand['metric_full']}  heldout.cl={cand['heldout']['cl']:.4f}  "
          f"heldout.replay_diag={cand['heldout']['replay_diag']:.3f}", flush=True)
    print("gates: " + "  ".join(f"{k}={'P' if ok else 'F'}"
                                for k, ok in comp["gates"].items()), flush=True)


if __name__ == "__main__":
    main()
