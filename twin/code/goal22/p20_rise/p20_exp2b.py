# -*- coding: utf-8 -*-
"""P20 실험 2b — 링키지 탄성 스캔 (폐루프 연결 구속의 시정수 1-파라미터).

가설: 상승 성분(+2~3Nm, 강한 푸시)은 링키지 탄성(활시위 효과 — 부하 시 에너지 저장,
폄에서 방출)이다. 모델의 coupler↔calf 연결은 현재 거의 강체(solref tc=0.8ms).
검사: eq_solref[0]=[tc, 1.0]을 풀어가며
  (a) 점프 창 점수 — 세션 기준선만(상승항 없음)으로 const-2.25 수준 회복하는가
  (b) 0429 Mode A — 같은 tc에서 무악화인가 (교차 게이트)
  (c) s2s — 무해한가
스텝핑/점수는 p20_exp1 재사용. 0324 미사용.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E          # ensure_init + win_scores/eval_set/BASE/JDS 재사용
import p19_judge as P

TCS = [0.0008, 0.002, 0.004, 0.008, 0.015, 0.03]


def flip_with_tc(tc):
    model, _ = P.build_flip(E.X32, E.V[1], E.SP)
    model.eq_solref[0] = [tc, 1.0]
    return model


def sc429_tc(tc):
    from cvt_run2 import sim_run, metrics2, score
    from cvt_core import load_0429
    import cvt_run2 as C
    SUB4 = ["60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"]
    o1, o2 = 3.14 * np.pi / 180, -3.0 * np.pi / 180
    A_save = C.A.copy(); C.A = np.asarray(E.A, float)
    try:
        scs = []
        model = None
        for sub in SUB4:
            d = load_0429(sub)
            if model is None:
                model, _ = P.build_cvt(E.X32, E.V[1], E.SP, d["l_i"])
                model.eq_solref[0] = [tc, 1.0]
            L, _ = sim_run(model, d, d["l_i"], "A", o1=o1, o2=o2)
            if L is None:
                return float("nan")
            scs.append(score(metrics2(d, L, o1, o2)))
        return float(np.mean(scs))
    finally:
        C.A = A_save


def main():
    base_fn = lambda tr: E.BASE[tr["ds"]]
    const_fn = lambda tr: 2.25
    print("기준 (tc=0.8ms 강체): const2.25 → 0421 75.0 / 0424 79.8 / 0602 82.9 | "
          "base_only → 89.8 / 84.7 / 82.9 | 0429 ref 58.5", flush=True)
    for tc in TCS:
        model = flip_with_tc(tc)
        rb = E.eval_set(model, E.JDS, base_fn)
        tot_b = float(np.mean(list(rb.values())))
        rc = E.eval_set(model, E.JDS, const_fn)
        tot_c = float(np.mean(list(rc.values())))
        s2s = E.eval_set(model, ("s2s_gnd_0319",), base_fn)
        m429 = sc429_tc(tc)
        print(f"tc={1000*tc:5.1f}ms | 기준선만 {tot_b:6.1f} (" +
              " ".join(f"{k.split('_')[-1]} {v:.0f}" for k, v in rb.items()) +
              f") | const2.25 {tot_c:6.1f} | s2s {list(s2s.values())[0]:5.1f} | 0429 {m429:6.1f}",
              flush=True)


if __name__ == "__main__":
    main()
