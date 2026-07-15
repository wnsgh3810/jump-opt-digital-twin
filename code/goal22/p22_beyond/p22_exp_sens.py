# -*- coding: utf-8 -*-
"""P22 exp — 소산 민감도 지도: 어느 나사가 '재생 개선 / 폐루프 손상' 교환비가 좋은가.

배경: T3 판정 = l_i=30에서 트윈이 과잉 소산 (재생 under-speed). P20c는 감쇠를 깎아 재생을
얻고 CL을 잃었다. 이 스캔은 소산·전달 관련 나사 각각에 대해 v5 전 성분의 국소 기울기를
재서, Phase 2(NSGA-II)의 자유축 선정과 파레토 벽의 '얇은 방향'을 특정한다.

변형: 소산축 {fv_hip, fc_hip, fv_knee, fc_knee, stiff, tm} × 스케일 {0.6, 0.8, 1.2}
      (+ ref ±2%: 스프링 기준각 — 에너지 주입 방향의 대조군)
출력: p22_exp_sens.json + 표 (성분별 Δ%, 교환비 = −ΔOLdq% / max(ΔCL%, 0.1)).
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

import p22_eval as E
import p22_rebase as RB
import safe

AXES = {"fv_hip": 2, "fc_hip": 3, "fv_knee": 4, "fc_knee": 5, "stiff": 0, "tm": 14}
SCALES = [0.6, 0.8, 1.2]


def norm(res, anch):
    """v5 성분을 앵커 정규화한 dict."""
    oldq = np.mean([res["OLDQ"][ds] / anch["OLDQ"][ds]
                    for ds in ("jump_0424", "jump_0602", "jump_0429")])
    return dict(CL=res["CL"] / anch["CL"], DQ=res["DQ"] / anch["DQ"],
                JW2=res["JW2"] / anch["JW2"],
                J6=0.5 * res["J6J"] / anch["J6J"] + 0.5 * res["J6C"] / anch["J6C"],
                S2S=res["S2S"] / anch["S2S"], O6=res["O6"] / anch["O6"],
                OLDQ=float(oldq), H=res["H"] / anch["H"], J_v5=res["J_v5"])


def main():
    E.ensure_init()
    anch = json.load(open(HERE / "p22_eval_anchors.json"))
    x19 = RB.x19_vec()
    out = {}
    print("variant | CL DQ JW2 J6 S2S O6 OLDQ H | J_v5  (전부 P19=1.0 정규화)", flush=True)
    variants = [(n, s) for n in AXES for s in SCALES] + [("ref", 0.98), ("ref", 1.02)]
    for name, s in variants:
        v = x19.copy()
        i = AXES.get(name, 1)
        v[i] = np.clip(v[i] * s, 1e-9, None)
        try:
            r = norm(E.evaluate(v), anch)
        except Exception as ex:
            print(f"{name} x{s}: CRASH {ex}", flush=True)
            continue
        out[f"{name}:{s}"] = r
        print(f"{name:7s} x{s:4.2f} | " +
              " ".join(f"{r[k]:.3f}" for k in ("CL", "DQ", "JW2", "J6", "S2S", "O6", "OLDQ", "H")) +
              f" | {r['J_v5']:.4f}", flush=True)
        safe.atomic_json_write(HERE / "p22_exp_sens.json", out)
    # 교환비 요약
    print("\n== 교환비 (OLdq 개선% / CL 손상%) — 소산 절감 방향(0.6/0.8)만 ==", flush=True)
    for key, r in out.items():
        name, s = key.split(":")
        if float(s) >= 1.0:
            continue
        dol = (1 - r["OLDQ"]) * 100
        dcl = (r["CL"] - 1) * 100
        print(f"{key:14s} ΔOLdq {dol:+.1f}%  ΔCL {dcl:+.1f}%  비율 {dol / max(dcl, 0.1):+.2f}", flush=True)
    print("saved p22_exp_sens.json", flush=True)


if __name__ == "__main__":
    main()
