# -*- coding: utf-8 -*-
"""p19_adapter — 심판 래퍼 (재구현 금지, 검증된 진입점만 감싼다).

래핑 지점 (2026-07-10 P19 마라톤에서 검증):
  - x32_of: p19_final.py의 6줄 매핑 복제 (출처 주석) — 후보 x → 32-param 벡터
  - CL τ-갭: p19_run.eval_stack(x32, ref, sp, A_PAPER, pre30, tm, use_alpha=True) → summarize
  - Mode A 보조: p19_judge.eval_modeA_jump
  - 구세대(P13~P16) 후보: p14_judge.eval36 (지표 체계가 다름 — judge 필드로 구분)
골든 재현 기준: fourbar_p19_candidate.json → metric_full≈0.3807 / heldout≈0.3570.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
REPO = HERE.parent.parent
G22 = REPO / "code" / "goal22"
for p in (G22 / "p19_jump", G22 / "p18_cvt", G22 / "p14_ahat",
          G22 / "p16_structure", G22, REPO / "code" / "goal21"):
    sys.path.insert(0, str(p))

sys.path.insert(0, str(HERE))
import safe  # noqa: E402

_INIT = False


def ensure_init():
    """p14_judge.winit() 1회 캐시 (트라이얼/모델 빌더 로딩 — 수십 초)."""
    global _INIT
    if _INIT:
        return
    import p19_judge as P
    P.winit()
    _INIT = True


# ── 후보 로딩/검증 ──
P19_KEYS = {"names", "x"}


def load_candidate(path):
    cand = safe.read_json(path)
    if not P19_KEYS.issubset(cand):
        raise ValueError(f"후보 스키마 불일치 ({path}): names/x 필수. keys={list(cand)}")
    cand["_path"] = str(path)
    return cand


# 출처: p19_final.py x32_of / p19_cma2.IDX (P19 마라톤 정본)
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
N6IDX = {"s_rc": 26, "s_ic": 27, "s_rp": 28, "s_ip": 29, "d_cpin": 30, "d_kneep": 31}


def x32_of(cand):
    import p19_judge as P
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(cand["names"]):
        if n in IDX:
            x32[IDX[n]] = cand["x"][i]
        elif n in N6IDX:
            x32[N6IDX[n]] = cand["x"][i]
    return x32


def _p19_args(cand):
    v = np.array(cand["x"], dtype=float)
    x32 = x32_of(cand)
    sp = "calf" if v[0] > 1e-3 else "none"
    qoff = (v[16], v[17]) if len(v) > 17 else (0.0548, -0.0524)
    return x32, v, sp, qoff


def eval_p19(cand):
    """점프 CL τ-갭 v3 (마라톤 고정 지표). 반환: summarize dict + rows."""
    ensure_init()
    import p19_judge as P
    import p19_run as R
    x32, v, sp, qoff = _p19_args(cand)
    rows = R.eval_stack(x32, v[1], sp, P.A_PAPER, v[2], v[15],
                        use_alpha=True, q_off_0429=qoff)
    s = R.summarize(rows)
    return dict(summary={k: list(map(float, val)) for k, val in s.items()},
                fit=float(s["FIT"][0]), heldout=float(s["jump_0324"][0]),
                rows=rows)


def eval_modea(cand):
    """Mode A 점프 보조 심판 (w_0421/0424/0602 + fs + habs)."""
    ensure_init()
    import p19_judge as P
    x32, v, sp, _ = _p19_args(cand)
    ot2 = {ds: v[2] for ds in ("jump_0424", "jump_0602",
                               "jump_position_0421", "jump_0324")}
    ma = P.eval_modeA_jump(x32, v[1], sp, P.A_PAPER, ot2)
    return {k: float(x) for k, x in ma.items()}


def eval_p14(cand):
    """구세대(P13~P16) 후보용 이중 심판 (Mode A 그룹 + CL, 지표 체계 상이)."""
    ensure_init()
    import p14_judge as J
    x = list(cand["x"])
    if len(x) >= 37:                     # P16류: x[36]=springref → build_model 패치
        import p16a_spring as PS
        ref = float(x[36])
        J.build_model = lambda x32, _r=ref: PS.build_with_ref(x32, _r)
        x = x[:36]
    r = J.eval36(x)
    out = {**{k: float(v) for k, v in r["A"].items()},
           "C": float(r["C"]), "Cg": float(r["Cg"])}
    return out
