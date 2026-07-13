# -*- coding: utf-8 -*-
"""P20 실험 10 — 2층 러너의 본게이트 평가 (CL τ-갭 FIT/HO) + C_dyn 적합.

게이트 (사전 등록): FIT ≤ 38.1%(P19) 동등 이상 + held-out(0324) ≤ 35.7+3%p +
점프 창(2층 입력벡터) ≤ 79.2(const2.25) + s2s/0429/0604 잔여 무악화 (exp9a 확인분).
pre30 상수는 제거된 상태 (2층이 대체).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
import p19_run as R
import p20_run as P20

DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20_results")


def main():
    model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
    out = {}
    for Cd in (1.5, 2.0, 2.5, 3.0):
        # 창 F1 (입력 벡터 — 빠른 선별)
        fn = lambda tr, _c=Cd: P20.lam_input_vec(
            dict(traw2=tr["raw2"], dq2=tr["v2"], q2=-tr["pp"]["q2m"]),
            False, 0.030, Cd=_c)
        r1 = E.eval_set(model_f, E.JDS, fn)
        F1 = float(np.mean(list(r1.values())))
        # 본게이트: CL τ-갭
        rows = P20.eval_stack20(E.X32, E.V[1], E.SP, P.A_PAPER, E.V[15],
                                Cd=Cd, q_off_0429=E.QOFF)
        s = R.summarize(rows)
        fit, ho = 100 * s["FIT"][0], 100 * s["jump_0324"][0]
        per = {k: round(100 * v[0], 1) for k, v in s.items() if k.startswith("jump")}
        out[Cd] = dict(F1=F1, fit=fit, ho=ho, per=per)
        print(f"Cd={Cd:.1f} | 창F1 {F1:6.1f} (참조 79.2) | CL FIT {fit:5.1f}% HO {ho:5.1f}% "
              f"(P19: 38.1/35.7) | " +
              " ".join(f"{k.split('_')[-1]} {v}" for k, v in per.items()), flush=True)
    json.dump(out, open(DST / "exp10_results.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
