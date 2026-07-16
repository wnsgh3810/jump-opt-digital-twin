# -*- coding: utf-8 -*-
"""p23_v6_eval — 지표 v6 단일 후보 평가기 (MARATHON_p23.md v6 동결식, P23 Phase 4).

J_v6 = 0.70·J_v5 + 0.10·ĈL_FF + 0.12·ÔLdq_FF + 0.08·ÂIR
  · J_v5 앵커  = p22_beyond/p22_eval_anchors.json (P19_rebased) — p22_eval.j_v5 그대로
  · 신규 앵커 = p23_anchors.json anchors.P19 (CL_FF/OLDQ_FF 세션별, AIR)
  · FF 주입 프로토콜 = p23_anchors.json ff_protocol.chosen ("knee+hip") — 앵커와 동일 동결
전 성분은 p23_v6_runners(측정 법칙층)로 산출 — pre30/준정적층 경로는 이 평가기에 없음.

게이트 (MARATHON 승격 조건의 하네스 구현 — 보고용; NSGA 제약은 p23_fit_nsga가 별도 적용):
  DQ̂≤1.00, JŴ02≤1.05, JŴ06≤1.05, Ŝ2S≤1.05, Ô6≤1.05, Ĥ≤1.02,
  ĈL_FF≤1.02, ÔLdq_FF≤1.02, ÂIR≤1.02
  (+ held-out(0324) CL 무악화·bench REPRODUCED는 오프라인 절차 — 여기서 안 함)

main(): P19+law 구조 변경 베이스라인 산출 → 성분표 (vs P19 앵커) 출력 +
        p23_v6_baseline.json 저장. 이 값이 "법칙 교체 자체의 효과" 기준선이다 —
        구 층과 식형이 달라 정확한 에뮬레이션은 불가능하므로 (정직 노트) 앵커 대비
        비율로 보고한다.
"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C
import p22_eval as E
import p23_runners as RN
import p23_v6_runners as RU
import safe

ANCH5_PATH = HERE.parent / "p22_beyond/p22_eval_anchors.json"
AFF_PATH = HERE / "p23_anchors.json"
BASE_OUT = HERE / "p23_v6_baseline.json"
W_V6 = dict(V5=0.70, CLFF=0.10, OLDQFF=0.12, AIR=0.08)      # MARATHON v6 동결
JDS = ("jump_position_0421", "jump_0424", "jump_0602")
GATES = dict(DQ=1.00, JW2=1.05, JW6=1.05, S2S=1.05, O6=1.05, H=1.02,
             CLFF=1.02, OLDQFF=1.02, AIR=1.02)

_A = {"a5": None, "aff": None, "ffhip": None}


def ensure_init():
    E.ensure_init()


def anchors():
    """(v5 앵커, v6 신규 앵커(P19), ff_hip 프로토콜) — 파일 1회 로드."""
    if _A["a5"] is None:
        _A["a5"] = safe.read_json(ANCH5_PATH)
        j = safe.read_json(AFF_PATH)
        _A["aff"] = j["anchors"]["P19"]
        _A["ffhip"] = (j["ff_protocol"]["chosen"] == "knee+hip")
    return _A["a5"], _A["aff"], _A["ffhip"]


def norm_of(comp, a5, aff):
    """성분 → 앵커 정규화 hat 사전 (게이트/목적 공용)."""
    jw6 = 0.5 * comp["J6J"] / a5["J6J"] + 0.5 * comp["J6C"] / a5["J6C"]
    return dict(
        CL=comp["CL"] / a5["CL"],
        DQ=comp["DQ"] / a5["DQ"],
        JW2=comp["JW2"] / a5["JW2"],
        JW6=float(jw6),
        S2S=comp["S2S"] / a5["S2S"],
        O6=comp["O6"] / a5["O6"],
        OLDQ=float(np.mean([comp["OLDQ"][s] / a5["OLDQ"][s] for s in E.OLDQ_SESS])),
        H=comp["H"] / a5["H"],
        CLFF=float(np.mean([comp["CLFF"][s] / aff["CL_FF"][s] for s in RN.FF_SESS])),
        OLDQFF=float(np.mean([comp["OLDQFF"][s] / aff["OLDQ_FF"][s]
                              for s in RN.FF_SESS])),
        AIR=comp["AIR"] / aff["AIR"])


def gates_of(norm):
    g = {k: bool(norm[k] <= cap + 1e-12) for k, cap in GATES.items()}
    g["ALL"] = all(g.values())
    return g


def j_v6_of(comp, a5, aff):
    """(J_v6, J_v5) — MARATHON 동결식."""
    jv5 = E.j_v5(comp, a5)
    n = norm_of(comp, a5, aff)
    jv6 = (W_V6["V5"] * jv5 + W_V6["CLFF"] * n["CLFF"]
           + W_V6["OLDQFF"] * n["OLDQFF"] + W_V6["AIR"] * n["AIR"])
    return float(jv6), float(jv5)


def evaluate(v23, verbose=False, keep_rows=True):
    """v23(22축; SPRING_GATED면 23축 — 22축 입력은 T_SPR init 자동 패드) → 전 v6 성분 +
    J_v5/J_v6 + norm + gates. 동결 3축은 내부에서 강제."""
    ensure_init()
    a5, aff, ffhip = anchors()
    t0 = time.time()
    v = RU.apply_freeze(RU.pad23(np.asarray(v23, float)))
    law = RU.law_of(v)
    spr = RU.spr_of(v)          # Phase 4b 게이트 스프링 (모드 OFF면 None)
    c_cvt = float(v[20]); d_dq = float(v[21])
    x32, sp = C.x32_of(v[:20])
    ref = float(v[1]); tm = float(v[14])
    say = (lambda s: print(s, flush=True)) if verbose else (lambda s: None)

    model_f = RU.build_flip23(x32, ref, sp, d_dq)
    say("  CL/DQ (폐루프 20+10 trial) ...")
    jcl, jdq = RU.cl_metrics23(v, x32, sp, law, c_cvt, d_dq, spr=spr,
                               model_f=model_f)
    say("  windows (JW02/JW06/S2S) ...")
    jw02 = RU.windows23(model_f, x32, JDS, law, spr=spr)
    j6j = RU.windows23(model_f, x32, JDS, law, W_override=0.6, spr=spr)
    j6c = RU.win429_06_23(x32, sp, ref, law, c_cvt, d_dq, spr=spr)
    s2s = RU.windows23(model_f, x32, ("s2s_gnd_0319",), law, spr=spr)
    say("  0604 창 ...")
    o6 = RU.score_0604_23(x32, sp, ref, law, c_cvt, d_dq, spr=spr)
    say("  OLDQ/H (통짜 재생 25 trial) ...")
    oldq, H, oldq_rows = RU.oldq_h23(v, x32, sp, law, c_cvt, d_dq, spr=spr,
                                     model_f=model_f)
    say("  CL_FF / OLDQ_FF (신규 FF 4 trial ×2) ...")
    clff, clff_rows = RU.cl_ff23(x32, sp, ref, tm, law, d_dq, ff_hip=ffhip,
                                 spr=spr, model_f=model_f)
    oldqff, oldqff_rows = RU.oldq_ff23(x32, sp, ref, law, d_dq, spr=spr,
                                       model_f=model_f)
    say("  AIR (용접 14사이클) ...")
    air, air_rows = RU.air23(x32, sp, ref, law, d_dq, spr=spr)

    comp = dict(CL=float(jcl), DQ=float(jdq), JW2=float(jw02), J6J=float(j6j),
                J6C=float(j6c), S2S=float(s2s), O6=float(o6), OLDQ=oldq,
                H=float(H), CLFF=clff, OLDQFF=oldqff, AIR=float(air))
    if keep_rows:
        comp["OLDQ_trials"] = oldq_rows
        comp["CLFF_rows"] = clff_rows
        comp["OLDQFF_rows"] = oldqff_rows
        comp["AIR_rows"] = air_rows
    jv6, jv5 = j_v6_of(comp, a5, aff)
    comp["J_v5"] = jv5
    comp["J_v6"] = jv6
    comp["norm"] = norm_of(comp, a5, aff)
    comp["gates"] = gates_of(comp["norm"])
    comp["t_eval_s"] = float(time.time() - t0)
    return comp


# ══════════ main: P19+law 구조 변경 베이스라인 ══════════
def main():
    safe.utf8_console()
    t0 = time.time()
    print("=== p23_v6_eval — P19+law 구조 변경 베이스라인 (플랜트=P19, 법칙=측정 init, "
          "C_CVT=0, D_DQ=0) ===", flush=True)
    ensure_init()
    print(f"winit+fix0421 done [{time.time() - t0:.0f}s]", flush=True)
    a5, aff, ffhip = anchors()
    v0 = RU.v23_p19_law()
    print("v23(P19+law): " + " ".join(f"{n}={x:.4g}" for n, x in zip(RU.NAMES23, v0)),
          flush=True)
    print(f"FF 주입 프로토콜 = {'knee+hip' if ffhip else 'knee-only'} (앵커 동결)",
          flush=True)
    comp = evaluate(v0, verbose=True)

    print("\n=== 성분표: P19 앵커 vs P19+law (hat = law/앵커; <1 = 개선) ===", flush=True)
    print(f"{'component':16s} {'P19 anchor':>12s} {'P19+law':>12s} {'hat':>8s}", flush=True)
    for k in ("CL", "DQ", "JW2", "J6J", "J6C", "S2S", "O6"):
        print(f"{k:16s} {a5[k]:12.4f} {comp[k]:12.4f} {comp[k] / a5[k]:8.3f}", flush=True)
    for s in E.OLDQ_SESS:
        print(f"OLDQ[{s:10s}] {a5['OLDQ'][s]:12.4f} {comp['OLDQ'][s]:12.4f} "
              f"{comp['OLDQ'][s] / a5['OLDQ'][s]:8.3f}", flush=True)
    print(f"{'H':16s} {a5['H']:12.4f} {comp['H']:12.4f} {comp['H'] / a5['H']:8.3f}",
          flush=True)
    for s in RN.FF_SESS:
        print(f"CL_FF[{s:12s}] {aff['CL_FF'][s]:10.4f} {comp['CLFF'][s]:12.4f} "
              f"{comp['CLFF'][s] / aff['CL_FF'][s]:8.3f}", flush=True)
    for s in RN.FF_SESS:
        print(f"OLDQ_FF[{s:10s}] {aff['OLDQ_FF'][s]:10.4f} {comp['OLDQFF'][s]:12.4f} "
              f"{comp['OLDQFF'][s] / aff['OLDQ_FF'][s]:8.3f}", flush=True)
    print(f"{'AIR':16s} {aff['AIR']:12.4f} {comp['AIR']:12.4f} "
          f"{comp['AIR'] / aff['AIR']:8.3f}", flush=True)
    print(f"\nJ_v5 = {comp['J_v5']:.4f}   J_v6 = {comp['J_v6']:.4f} "
          f"(P19 정의상 J_v5(P19)=1.0; 신규 성분 앵커도 P19 → J_v6(P19)=1.0)", flush=True)
    print("gates: " + "  ".join(f"{k}={'P' if ok else 'F'}"
                                for k, ok in comp["gates"].items()), flush=True)
    print(f"eval time = {comp['t_eval_s']:.0f}s", flush=True)

    safe.atomic_json_write(BASE_OUT, dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        note=("P19+law 구조 변경 베이스라인 — 측정 법칙(고정 init)이 pre30+준정적층을 "
              "대체했을 때의 전 v6 성분. 구 층과 식형이 달라 정확 에뮬레이션 불가 — "
              "이 표가 새 구조의 정직한 출발점."),
        v=[float(a) for a in v0], names=RU.NAMES23,
        law=dict(A=RU.LAW_A0, B=RU.LAW_B0, C=RU.LAW_C, V0=RU.LAW_V00, cap=RU.SUPP_CAP),
        comp=comp))
    print(f"saved {BASE_OUT.name} [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
