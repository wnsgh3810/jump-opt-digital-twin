# -*- coding: utf-8 -*-
"""P22 — NSGA 체크포인트에서 P19 지배 개체 추출 → 엄격 승격 게이트 전수 검증.

게이트 (MARATHON_p22.md): CL̂·DQ̂·ÔLdq·Ĥ ≤ 1.00, JŴ02·JŴ06·Ŝ2S·Ô6 ≤ 1.05.
(held-out·bench REPRODUCED는 후보 등록 단계에서 별도.)
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe


def main():
    import p22_eval as E
    ck = safe.read_json(HERE / "p22_nsga_ckpt.json")
    X = np.array(ck["X"], float)
    F = np.array(ck["F"], float)
    G = np.array(ck["G"], float)
    feas = (G <= 0).all(axis=1)
    dom = feas & (F[:, 0] <= 1.0) & (F[:, 1] <= 1.0)
    idx = np.where(dom)[0]
    print(f"ckpt gen={ck['gen']} — 지배 개체 {len(idx)}개", flush=True)
    # 중복 제거 (파라미터 공간 근접)
    keep = []
    for i in idx:
        if all(np.linalg.norm(X[i] - X[j]) > 1e-3 for j in keep):
            keep.append(i)
    print(f"dedup 후 {len(keep)}개 → full evaluate + 엄격 게이트", flush=True)
    anch = safe.read_json(HERE / "p22_eval_anchors.json")

    def ho_replay(v):
        """진단 전용 (게이트 아님): held-out 0324 통짜 재생 dq2 RMSE. P19 아카이브 = 2.926."""
        import p21_cma as C
        import numpy as np
        P, R = C._W["P"], C._W["R"]
        v = np.asarray(v, float)
        x32, sp = C.x32_of(v)
        model_f, _ = P.build_flip(x32, v[1], sp)
        dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
        es = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
            if ds != "jump_0324":
                continue
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            res = E.a_full(model_f, False, l_i, d, v, o1, o2, pre30=float(v[19]))
            es.append(res[0] if res else 9.9)
        return float(np.mean(es)) if es else float("nan")

    rows = []
    for n, i in enumerate(keep):
        r = E.evaluate(X[i])
        r["HO_OLDQ"] = ho_replay(X[i])
        oldq = float(np.mean([r["OLDQ"][s] / anch["OLDQ"][s] for s in E.OLDQ_SESS]))
        jw6 = 0.5 * r["J6J"] / anch["J6J"] + 0.5 * r["J6C"] / anch["J6C"]
        gate = dict(CL=r["CL"] / anch["CL"], DQ=r["DQ"] / anch["DQ"],
                    OLDQ=oldq, H=r["H"] / anch["H"],
                    JW2=r["JW2"] / anch["JW2"], JW6=float(jw6),
                    S2S=r["S2S"] / anch["S2S"], O6=r["O6"] / anch["O6"])
        hard = all(gate[k] <= 1.0 + 1e-9 for k in ("CL", "DQ", "OLDQ", "H"))
        soft = all(gate[k] <= 1.05 + 1e-9 for k in ("JW2", "JW6", "S2S", "O6"))
        r.pop("OLDQ_trials", None)
        rows.append(dict(i=int(i), x=[float(a) for a in X[i]], F=[float(a) for a in F[i]],
                         gate={k: float(v) for k, v in gate.items()},
                         PASS=bool(hard and soft), J_v5=r["J_v5"],
                         HO_OLDQ=r["HO_OLDQ"], full=r))
        print(f"[{n}] i={i} " +
              " ".join(f"{k}={gate[k]:.3f}" for k in gate) +
              f" J_v5={r['J_v5']:.4f} HOre={r['HO_OLDQ']:.2f}(P19 2.93) "
              f"{'★PASS' if hard and soft else 'fail'}", flush=True)
    safe.atomic_json_write(HERE / "p22_gate_check.json", dict(gen=ck["gen"], rows=rows))
    npass = sum(r["PASS"] for r in rows)
    print(f"\n게이트 통과 {npass}/{len(rows)} — p22_gate_check.json 저장", flush=True)


if __name__ == "__main__":
    main()
