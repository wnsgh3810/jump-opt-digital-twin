# -*- coding: utf-8 -*-
"""p24_register — P24 승자 등록: fourbar_p24a_candidate.json 생성 (MARATHON_p23.md P24).

승자 = p23_fit_nsga_ckpt_p24.json (26축, ckpt gen80 = P24 재적합 최종 세그먼트, 계 240세대)
row 29 — p24_final_x.json에 고정된 엄격 선발 개체 (MARATHON 'P24 재적합 결과': 구현 게이트
전 통과 + v5 원문 수기 게이트 OLDQ평균≤1.00·CL≤1.00 강제, J_v6 0.8263).

구조 = p23a (P23_SPRING_GATED=1 + P23_RISE_GATED=1) 위 P24_REFIT=1:
  · 벡터 26축 — slots 23/24/25 = B1_HIP/V0_HIP/K1_HIP (힙 부하-지지층
    λ₁ = B1·|τ̂₂|·g(|dq₁|; V0₁) + K1·dq₁·(1−g), src=knee — p23_v6_runners P24 블록)
  · 케이지 교정 I_th 하한 0.35 / C_CVT 상한 1.0 (탐색 케이지 — 평가 의미 불변)

절차 (p23_register.py 패턴; 이 스크립트는 후보 JSON 하나만 쓴다 — safe.candidate_save):
  1. p24_final_x.json ↔ ckpt row 29 동일성 + 가능해(G≤0) assert
  2. p23_v6_eval.evaluate 신선 재평가 → J_v6 재현 assert + 성분/norm/게이트 확보
     + 수기 텍스트 게이트 (norm OLDQ평균 ≤1.00, norm CL ≤1.00) 재확인
  3. held-out: p19_adapter.eval_p24 (CL 폐루프 0324 포함 — ff_hip=True·o1=o2=0·
     alphas [1,1,1,1], 동결 적용; 어댑터 docstring 규약) — bench와 동일 코드 경로라
     metric_full ↔ FIT 사전 REPRODUCED 검증을 겸함
     + a_full23 재생 진단 (p24_refit_check.ho_replay 미러: 무변속 모델, o1=o2=0,
     spr·k_rise 포함 — 주의: p23a 시절 p23_ho_check.json(평균 2.9167)과는 산법 드리프트
     존재, golden에서 연속성 시드가 2.487로 관측됨 → 세대 간 직접 비교 금지, 진단 전용)
  4. 스키마 = fourbar_p23a_candidate.json 확장 (judge="p24", structure.hip_law/p24_refit,
     cmdlayer = p23a 사본 + TM=x[14], metric_full = 신선 CL — F1 블렌드(0.75CL+0.25CLFF)
     아님, p23a 교훈)

실행: PYTHONIOENCODING=utf-8 python p24_register.py  (평가 전용 — 데이터 무수정, 커밋 없음)
"""
import os

# ── 구조 플래그: p23/p24 모듈 import 전에 확정 (import 시점에 벡터 축수/힙 층 결정) ──
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_REFIT"] = "1"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

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

import safe

safe.utf8_console()

import p23_v6_eval as V6            # noqa: E402
import p23_v6_runners as RU         # noqa: E402
import p22_eval as E                # noqa: E402
import p23_runners as RN            # noqa: E402
import p21_cma as C                 # noqa: E402
import p19_run as R19               # noqa: E402
import p19_adapter as AD            # noqa: E402

assert RU.SPRING_GATED and RU.RISE_GATED and RU.P24_REFIT and RU.NV23 == 26, \
    "구조 플래그/축수 불일치 — env 순서 확인"

CKPT = HERE / "p23_fit_nsga_ckpt_p24.json"
FINAL = HERE / "p24_final_x.json"
P23A = HERE / "fourbar_p23a_candidate.json"
OUT = HERE / "fourbar_p24a_candidate.json"
J_TOL = 5e-4                        # J_v6 신선 재현 허용 오차 (p23_register 5e-4 규약)

STRUCT = {
    "spring_gated": True,
    "rise_gated": True,
    "hip_law": {
        "src": "knee",
        "cap": 15.66,
        "note": "λ₁=B1·|τ̂₂|·g(|dq₁|;V0₁)+K1·dq₁·(1−g) — slots 23/24/25 = "
                "B1_HIP/V0_HIP/K1_HIP (apply_freeze가 RU.HIP 주입; cap=적합창 |τ̂₂| 최대)",
    },
    "p24_refit": True,
    "LAW_C": -0.0281448,
    "note": "p23a 구조(측정 법칙 + 부하연동 스프링 + 게이트 상승항) + P24 힙 부하-지지층 "
            "(무릎 부하 |τ̂₂| 연동, 카드 1) + 케이지 교정(I_th 0.35↓/C_CVT 1.0↑, 카드 2)",
}


def pick_winner():
    """p24_final_x.json → (row, x, F_ckpt, gen) — ckpt row 동일성 + 가능해 검증."""
    fx = safe.read_json(FINAL)
    ck = safe.read_json(CKPT)
    X = np.array(ck["X"], float)
    F = np.array(ck["F"], float)
    G = np.array(ck["G"], float)
    i = int(fx["row"])
    assert np.allclose(X[i], fx["x"], atol=1e-12), "p24_final_x != ckpt row 29"
    assert (G[i] <= 0).all(), f"row {i} 비가능해 (G={G[i].tolist()})"
    assert len(fx["x"]) == RU.NV23 == 26
    return i, [float(a) for a in fx["x"]], F[i], int(ck["gen"]), float(fx["J_v6"])


def ho_replay(x):
    """0324 A-재생 진단 — p24_refit_check.ho_replay 문자 그대로 미러
    (a_full23, 무변속 모델, o1=o2=0, spr·k_rise 포함; 힙 층은 apply_freeze 주입)."""
    v = RU.apply_freeze(RU.pad23(np.asarray(x, float)))
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    kr = RU.rise_of(float(v[21]))
    x32, sp = C.x32_of(v[:20])
    model_f = RU.build_flip23(x32, float(v[1]), sp, float(v[21]))
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    reps = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0324":
            continue
        res = RU.a_full23(model_f, False, l_i, d, law, 0.0, 0.0, c_cvt=0.0,
                          spr=spr, k_rise=kr)
        reps.append(float(res[0]) if res is not None else 9.9)
    return reps


def main():
    t0 = time.time()
    i, x, F_ck, gen, j_stored = pick_winner()
    print(f"승자: ckpt_p24 gen{gen} row[{i}]  F_ckpt=[{F_ck[0]:.4f}, {F_ck[1]:.4f}]  "
          f"저장 J_v6={j_stored:.6f}", flush=True)

    # ── 2. 신선 재평가 (v6 전 성분) ──
    comp = V6.evaluate(np.asarray(x, float), verbose=True, keep_rows=False)
    a5, aff, _ = V6.anchors()
    print(f"신선 평가: J_v6={comp['J_v6']:.4f}  J_v5={comp['J_v5']:.4f}  "
          f"CL={comp['CL']:.5f}  [{time.time() - t0:.0f}s]", flush=True)
    assert abs(comp["J_v6"] - j_stored) < J_TOL, \
        f"J_v6 재현 실패: fresh {comp['J_v6']:.6f} vs 저장 {j_stored:.6f}"
    assert comp["gates"]["ALL"], f"구현 게이트 실패: {comp['gates']}"
    tg_oldq = float(comp["norm"]["OLDQ"])
    tg_cl = float(comp["norm"]["CL"])
    assert tg_oldq <= 1.0 + 1e-12 and tg_cl <= 1.0 + 1e-12, \
        f"수기 텍스트 게이트 실패: OLDQ평균 {tg_oldq:.4f} / CL {tg_cl:.4f} (≤1.00 요구)"
    print(f"수기 텍스트 게이트: norm OLDQ평균={tg_oldq:.4f}✓  norm CL={tg_cl:.4f}✓",
          flush=True)
    print("OLDQ 재생 vs P19 앵커: "
          + "  ".join(f"{s[-4:]}={comp['OLDQ'][s]:.3f}/{a5['OLDQ'][s]:.3f}"
                      for s in E.OLDQ_SESS), flush=True)
    print("OLDQFF: " + "  ".join(f"{s}={comp['OLDQFF'][s]:.3f}" for s in RN.FF_SESS)
          + f"  AIR={comp['AIR']:.4f}  H_raw={comp['H']:.4f}", flush=True)

    # ── 3. held-out: 어댑터(bench 동일 경로) CL + a_full23 재생 진단 ──
    stub = dict(names=list(RU.NAMES23), x=x, structure=STRUCT)
    r = AD.eval_p24(stub)
    assert abs(r["fit"] - comp["CL"]) <= 0.005, \
        f"어댑터 FIT {r['fit']:.5f} != 신선 CL {comp['CL']:.5f} — REPRODUCED 불가 상태"
    print(f"judge(p24): FIT={100 * r['fit']:.2f}%  HO(0324)={100 * r['heldout']:.2f}%",
          flush=True)
    for ds, (g, q2, n) in sorted(r["summary"].items()):
        if ds.startswith("jump"):
            print(f"  {ds:22s} τ-갭 {100 * g:5.1f}%  q2 {q2:.3f}  (n={n})", flush=True)
    reps = ho_replay(x)
    print(f"HO 재생 진단(0324 3tr): {['%.3f' % a for a in reps]}  "
          f"mean={np.mean(reps):.4f}", flush=True)

    # ── 4. 후보 JSON ──
    p23a = safe.read_json(P23A)
    cmdlayer = dict(p23a["cmdlayer"])
    cmdlayer["TM"] = x[14]
    cand = {
        "CANDIDATE": ("P24 p24a — NSGA-II(v6) 26축 재적합 ckpt gen80 row 29 (엄격 수기게이트 "
                      "선발) : p23a 구조 + 힙 부하-지지층 + 케이지 교정, held-out 사전검증 "
                      "(2026-07-17)"),
        "judge": "p24",
        "names": list(RU.NAMES23),
        "x": x,
        "A": "paper",
        "structure": STRUCT,
        "cmdlayer": cmdlayer,
        "v6_gates": {
            "norm": {k: float(v) for k, v in comp["norm"].items()},
            "pass": {k: bool(v) for k, v in comp["gates"].items()},
        },
        "text_gates": {"OLDQ_mean": tg_oldq, "CL": tg_cl, "cap": 1.0,
                       "note": "v5 원문 수기 게이트 (구현 게이트에 OLDQ≤1.00 누락 — "
                               "MARATHON 정직 노트, 차기 하네스 수정 항목)"},
        "J_v6": float(comp["J_v6"]),
        "J_v5": float(comp["J_v5"]),
        "heldout": {
            "cl": float(r["heldout"]),
            "replay_diag": float(np.mean(reps)),
            "replay_trials": [float(a) for a in reps],
            "note": ("cl = p19_adapter.eval_p24 (동결 적용 폐루프; p23a의 0.3469는 동결 "
                     "미적용값 — 동결 심판 기준 p23a=0.3479). replay = a_full23 spr·k_rise "
                     "포함 (p24_refit_check.ho_replay 규약) — p23a 시절 p23_ho_check "
                     "산법과 드리프트 (golden 연속성 시드 2.487 vs 구 2.917), 진단 전용"),
        },
        "metric_full": round(float(comp["CL"]), 4),
        "origin": {
            "nsga_gen": gen,
            "nsga_gen_note": "ckpt = P24 재적합 최종 세그먼트 (계 240세대)",
            "pop_index": i,
            "ckpt": "p23_fit_nsga_ckpt_p24.json",
            "F": [float(F_ck[0]), float(F_ck[1])],
            "final_x": "p24_final_x.json",
            "selection": ("가능해 전집 엄격 선발 — 구현 게이트 ALL + v5 원문 수기 게이트 "
                          "(norm OLDQ평균≤1.00·norm CL≤1.00) 통과 (MARATHON 'P24 재적합 "
                          "결과' 07-17)"),
            "anchors": "p23_anchors.json (v6 신규) + p22_eval_anchors.json (v5)",
        },
    }
    safe.candidate_save(OUT, cand)
    print(f"saved {OUT}", flush=True)
    print(f"metric_full={cand['metric_full']}  heldout.cl={cand['heldout']['cl']:.4f}  "
          f"heldout.replay_diag={cand['heldout']['replay_diag']:.3f}", flush=True)
    print("gates: " + "  ".join(f"{k}={'P' if ok else 'F'}"
                                for k, ok in comp["gates"].items()), flush=True)
    print(f"done [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
