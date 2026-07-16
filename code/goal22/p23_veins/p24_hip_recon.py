# -*- coding: utf-8 -*-
"""p24_hip_recon — P24 preflight 카드 1: 화해 시험 (단일 eval 그리드).

질문: [p23a + light thigh + 힙 지지 법칙(측정 적합)]이 오늘의 모순을 닫는가?
  SUCCESS = 지상 성분 ≈ p23a (±~5%) AND AIR(norm) ≤ 0.8 AND H(norm) ≤ 1.02.
  부수 질문: 가벼운 관성으로 지상 재생 dq(OLDQ)가 실제로 개선되는가.

케이스 (전부 P24_HIP_LAW=1 프로세스, RU.HIP in-process 갱신):
  base      : p23a 그대로 + HIP 0 (골든 재현 확인 — OFF와 수치 동일해야 함)
  light_noh : light thigh (I_th 0.40, dz_th −0.03) + HIP 0 (오늘 probe의 하네스 재현)
  그리드 12  : b₁ ∈ {적합, ±CI} × I_th ∈ {0.40, 0.50} × dz_th ∈ {−0.03, −0.015}
              (K2f: a₁=0, v0₁=3.324, cap=15.66, src=knee — p24_hip_fit.json wire)
  H2_lit    : 과제 문언형 (src=hip, a₁=−1.696, b₁=+1.257, v0₁=0.30) × light —
              적합에서 퇴화 판정났지만 문언 그대로의 기록용 1 eval (AIR 붕괴 예상).

출력: p24_hip_recon.json + 콘솔 표. 기존 파일 불변, 커밋 없음.
실행: PYTHONIOENCODING=utf-8 python p24_hip_recon.py
"""
import os
import sys
import time
from pathlib import Path

# ★ 구조/층 플래그는 p23 모듈 import 전에 env로 강제
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import p23_v6_runners as RU
import p23_v6_eval as EV
import p23_runners as RN
import p22_eval as E

assert RU.SPRING_GATED and RU.RISE_GATED and RU.HIP_LAW

CAND_PATH = HERE / "fourbar_p23a_candidate.json"
FIT_PATH = HERE / "p24_hip_fit.json"
OUT_PATH = HERE / "p24_hip_recon.json"
GROUND_KEYS = ("CL", "DQ", "JW2", "JW6", "S2S", "O6", "OLDQ", "CLFF", "OLDQFF")
TOL_GND = 0.05          # 지상 성분 허용 악화 (baseline norm 대비 상대)
CAP_AIR, CAP_H = 0.80, 1.02


def build_cases():
    fit = safe.read_json(FIT_PATH)
    w = fit["wire"]
    b1s = [w["b1"] - w["b1_ci"], w["b1"], w["b1"] + w["b1_ci"]]
    k2f = dict(a1=0.0, v01=w["v01"], cap=w["cap"], src="knee")
    cases = [("base", {}, dict(a1=0.0, b1=0.0, v01=w["v01"], cap=w["cap"], src="knee")),
             ("light_noh", dict(I_th=0.40, dz_th=-0.03),
              dict(a1=0.0, b1=0.0, v01=w["v01"], cap=w["cap"], src="knee"))]
    for ith in (0.40, 0.50):
        for dz in (-0.03, -0.015):
            for tag, b1 in zip(("lo", "fit", "hi"), b1s):
                cases.append((f"I{ith:.2f}_dz{dz:+.3f}_b{tag}",
                              dict(I_th=ith, dz_th=dz), dict(k2f, b1=b1)))
    h2 = fit["fits"]["H2"]["params"]
    cases.append(("H2_lit", dict(I_th=0.40, dz_th=-0.03),
                  dict(a1=h2["a"], b1=h2["b"], v01=h2["v0"], cap=15.66, src="hip")))
    return cases, w


def vec_of(over):
    cand = safe.read_json(CAND_PATH)
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    for k, val in over.items():
        v[RU.NAMES23.index(k)] = val
    return v


def main():
    t0 = time.time()
    EV.ensure_init()
    cases, wire = build_cases()
    cand = safe.read_json(CAND_PATH)
    ref_norm = cand["v6_gates"]["norm"]
    print(f"=== p24_hip_recon — {len(cases)} evals (HIP wire: b1={wire['b1']:+.4f}"
          f"±{wire['b1_ci']:.4f}, v01={wire['v01']:.3f}, cap={wire['cap']}, src=knee) ===",
          flush=True)
    results = []
    for name, over, hip in cases:
        RU.HIP.update(hip)
        v = vec_of(over)
        tc = time.time()
        comp = EV.evaluate(v, verbose=False, keep_rows=False)
        n = comp["norm"]
        gnd_ok = all(n[k] <= ref_norm[k] * (1 + TOL_GND) + 1e-12 for k in GROUND_KEYS)
        succ = gnd_ok and n["AIR"] <= CAP_AIR and n["H"] <= CAP_H
        row = dict(name=name, over=over, hip=dict(hip), norm=n,
                   OLDQ_raw=comp["OLDQ"], CLFF_raw=comp["CLFF"],
                   OLDQFF_raw=comp["OLDQFF"], AIR_raw=comp["AIR"], H_raw=comp["H"],
                   J_v5=comp["J_v5"], J_v6=comp["J_v6"], gates=comp["gates"],
                   gnd_ok=bool(gnd_ok), success=bool(succ),
                   t_eval_s=round(time.time() - tc, 1))
        results.append(row)
        print(f"[{name:22s}] J6={comp['J_v6']:.4f} | "
              + " ".join(f"{k}={n[k]:.3f}" for k in
                         ("CL", "OLDQ", "H", "CLFF", "OLDQFF", "AIR", "S2S", "JW2"))
              + f" | gnd{'✓' if gnd_ok else '✗'} AIR{'✓' if n['AIR'] <= CAP_AIR else '✗'}"
                f" H{'✓' if n['H'] <= CAP_H else '✗'}"
                f" → {'SUCCESS' if succ else 'fail'} [{row['t_eval_s']}s]", flush=True)

    # 표: norm 성분 상세 (baseline 대비)
    base = next(r for r in results if r["name"] == "base")
    print("\n=== v6 성분 norm 표 (열 = 성분, ref = base; ⧫ = base 대비 +5% 초과 악화) ===",
          flush=True)
    keys = ("CL", "DQ", "JW2", "JW6", "S2S", "O6", "OLDQ", "H", "CLFF", "OLDQFF", "AIR")
    print(f"{'case':22s} " + " ".join(f"{k:>7s}" for k in keys) + f" {'J_v6':>7s}", flush=True)
    for r in results:
        cells = []
        for k in keys:
            mark = "⧫" if (k in GROUND_KEYS
                           and r["norm"][k] > base["norm"][k] * (1 + TOL_GND) + 1e-12) else " "
            cells.append(f"{r['norm'][k]:6.3f}{mark}")
        print(f"{r['name']:22s} " + " ".join(cells) + f" {r['J_v6']:7.4f}", flush=True)

    print("\n=== 지상 재생 dq (OLDQ 세션 raw, rad/s) — '가벼운 관성' 개선 여부 ===", flush=True)
    print(f"{'case':22s} " + " ".join(f"{s:>10s}" for s in E.OLDQ_SESS)
          + " " + " ".join(f"FF:{s[-7:]:>8s}" for s in RN.FF_SESS), flush=True)
    for r in results:
        print(f"{r['name']:22s} "
              + " ".join(f"{r['OLDQ_raw'][s]:10.3f}" for s in E.OLDQ_SESS) + " "
              + " ".join(f"{r['OLDQFF_raw'][s]:11.3f}" for s in RN.FF_SESS), flush=True)

    safe.atomic_json_write(OUT_PATH, dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), wire=wire, tol_gnd=TOL_GND,
        cap_air=CAP_AIR, cap_h=CAP_H, ref_norm=ref_norm, results=results,
        note=("화해 시험: base=골든 재현(HIP 0), light_noh=probe 재현, 그리드=K2f 법칙, "
              "H2_lit=과제 문언형 기록용. success = 지상 ±5% AND AIR≤0.8 AND H≤1.02.")))
    print(f"\nsaved {OUT_PATH.name} [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
