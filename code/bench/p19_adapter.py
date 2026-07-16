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
          G22 / "p16_structure", G22 / "p20_rise", G22, REPO / "code" / "goal21"):
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


def eval_p20(cand):
    """P20 2층 러너 심판 (준정적 게이트 어시스트 + 무릎측 동적층) — 지표 v3 동일."""
    ensure_init()
    import p19_judge as P
    import p19_run as R
    import p20_run as P20
    x32, v, sp, qoff = _p19_args(cand)
    p20 = cand.get("p20", {})
    rows = P20.eval_stack20(x32, v[1], sp, P.A_PAPER, v[15],
                            c=p20.get("c_qs", 0.25), v0=p20.get("v0", 6.0),
                            Cd=p20.get("C_dyn", 2.5), q_off_0429=qoff)
    s = R.summarize(rows)
    return dict(summary={k: list(map(float, val)) for k, val in s.items()},
                fit=float(s["FIT"][0]), heldout=float(s["jump_0324"][0]),
                rows=rows)


def eval_p22(cand):
    """P22 심판 — p20 러너 + pre30(preload=x[2], 무변속 전용) 적용.

    p21_cma.cl_metrics(P22 NSGA 내부 심판)와 동일 규약 + held-out 포함.
    p20 심판과의 차이는 preload 하나 — p20 세대 후보(pre30≈0)에는 수치 동일."""
    ensure_init()
    import p19_judge as P
    import p19_run as R
    import p20_run as P20
    x32, v, sp, qoff = _p19_args(cand)
    p20 = cand.get("p20", {})
    rows = P20.eval_stack20(x32, v[1], sp, P.A_PAPER, v[15],
                            c=p20.get("c_qs", 0.25), v0=p20.get("v0", 6.0),
                            Cd=p20.get("C_dyn", 0.0), q_off_0429=qoff,
                            preload=float(v[2]))
    s = R.summarize(rows)
    return dict(summary={k: list(map(float, val)) for k, val in s.items()},
                fit=float(s["FIT"][0]), heldout=float(s["jump_0324"][0]),
                rows=rows)


def eval_p23(cand):
    """P23 심판 — 측정 유지-지지 법칙 + 부하연동 스프링(4b) + 게이트 상승항(4c).

    p23_v6_eval.evaluate의 CL 성분(p23_v6_runners.cl_metrics23 규약)을 held-out(0324)
    포함으로 확장 (문자 그대로 미러 — 변경점은 0324 포함 + summarize 뿐):
      - 구조 플래그(P23_SPRING_GATED/P23_RISE_GATED)는 p23 모듈 import 전에 env로 강제
        (p23_v6_runners가 import 시점에 벡터 축수/의미를 결정하므로 순서 불변)
      - init = RU.ensure_init (winit + fix0421 — p23_v6_eval와 동일 규약; CL 경로는
        xlsx 직독이라 fix0421 무영향이나 초기화 체인 통일)
      - 동결 3축(M_c/I_ca/dz_ca)은 apply_freeze로 강제 (evaluate 내부와 동일)
      - no-CVT 적합 세션: build_flip23 + cl_run23, OFFK per-session 오프셋(x32 dict)
      - held-out 0324(ffk): ff_hip=True (P23 FF 주입 프로토콜 knee+hip, 앵커 동결) +
        o1=o2=0 — 적합 커맨드층·오프셋 없음 규약 (p23_runners cl_ff와 동일;
        OFFK의 o1_0324/o2_0324는 P16 레거시 잔재라 미사용). p23_ho_check.json의
        0.3469는 이 규약 + freeze 미적용 값 — 동결 심판은 0.3479 (Δ 0.1%p = freeze분)
      - CVT 0429: build_cvt23 + cl_run23, o1/o2 = x[17]/x[18], C_CVT=x[20]
      - alphas = R.ALPH (적합 세션; 0324는 [1,1,1,1])
      - crash 시 g=2.0 (cl_metrics23 규약 — eval_stack의 2.5와 다름, FIT 재현 우선)
    """
    import os
    st = cand.get("structure", {})
    sg = bool(st.get("spring_gated", True))
    rg = bool(st.get("rise_gated", True))
    os.environ["P23_SPRING_GATED"] = "1" if sg else "0"
    os.environ["P23_RISE_GATED"] = "1" if rg else "0"
    p23dir = str(G22 / "p23_veins")
    if p23dir not in sys.path:
        sys.path.insert(0, p23dir)
    import p23_v6_runners as RU
    assert RU.SPRING_GATED == sg and RU.RISE_GATED == rg, (
        "p23 구조 플래그가 import 캐시와 불일치 — 같은 프로세스에서 다른 플래그의 "
        "p23 후보를 이미 평가함 (프로세스 분리 필요)")
    import p19_run as R
    RU.ensure_init()
    global _INIT
    _INIT = True                      # winit 완료 (ensure_init 중복 호출 방지)
    P = RU.C._W["P"]
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    c_cvt = float(v[20]); d_dq = float(v[21])
    kr = RU.rise_of(d_dq)
    x32, sp = RU.C.x32_of(v[:20])
    ref = float(v[1]); tm = float(v[14])
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f = RU.build_flip23(x32, ref, sp, d_dq)
    model_c = None
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        alphas = R.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c = RU.build_cvt23(x32, ref, sp, l_i, d_dq)
            L = RU.cl_run23(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                            tm, alphas, law, c_cvt=c_cvt,
                            o1=float(v[17]), o2=float(v[18]), spr=spr, k_rise=kr)
        else:
            if ffk:                   # held-out 0324: 적합 오프셋 없음 (docstring 규약)
                o1 = o2 = 0.0
            else:
                k1, k2 = P.J.OFFK.get(ds, (None, None))
                o1 = dd.get(k1, 0.0) if k1 else 0.0
                o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = RU.cl_run23(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                            tm, alphas, law, c_cvt=0.0, o1=o1, o2=o2,
                            ff_hip=bool(ffk), spr=spr, k_rise=kr)
        if L is None:
            rows.append(dict(ds=ds, sub=sub, g=2.0, q2=9.9))
            continue
        g, q2r = R.gap_v3(L, d, P.A_PAPER, m)
        rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
    s = R.summarize(rows)
    return dict(summary={k: list(map(float, val)) for k, val in s.items()},
                fit=float(s["FIT"][0]), heldout=float(s["jump_0324"][0]),
                rows=rows)
