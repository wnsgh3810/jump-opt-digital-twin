# -*- coding: utf-8 -*-
"""P18b iter3 — (a) 오프셋 NM 폴리시 (b) 평행사변형 배치 동일성 증명 (c) stiff 민감도."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from cvt_run2 import build_cvt2, sim_run, metrics2, score
from cvt_core import load_0429, SUBS429
import p14_judge as J

D2R = np.pi / 180
_pool = None


def eval_off(args):
    o1, o2, sub, stiff_mul = args
    if not J._P:
        J.winit()
    d = load_0429(sub)
    x32 = np.array(json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))["x"][:32])
    if stiff_mul != 1.0:
        x32[11] *= stiff_mul          # stiff_knee index (FR.NAMES[11])
    model, _ = build_cvt2(d["l_i"], "calf", "crank", x32=x32)
    L, _ = sim_run(model, d, d["l_i"], "A", o1=o1, o2=o2)
    if L is None:
        return 1e9, None
    m = metrics2(d, L, o1, o2)
    return score(m), m


def obj(v, stiff_mul=1.0):
    o1, o2 = v
    if abs(o1) > 5 * D2R or abs(o2) > 5 * D2R:
        return 1e6
    rs = _pool.map(eval_off, [(o1, o2, s, stiff_mul) for s in SUBS429])
    return float(np.mean([r[0] for r in rs]))


def main():
    global _pool
    import multiprocessing as mp
    from scipy.optimize import minimize
    _pool = mp.Pool(10, initializer=J.winit)

    # (b) 평행사변형 동일성: l_i=30mm에서 spring@crank vs @calf 궤적 diff
    J.winit()
    d = load_0429("120_2_120_2")
    outs = {}
    for sp in ("crank", "calf"):
        model, _ = build_cvt2(0.030, sp, "crank")
        L, _ = sim_run(model, d, 0.030, "A")
        outs[sp] = L
    dq2m = float(np.max(np.abs(outs["crank"]["q2"] - outs["calf"]["q2"])))
    dbzm = float(np.max(np.abs(outs["crank"]["bz"] - outs["calf"]["bz"])))
    print(f"[equiv l_i=30] max|dq2| = {dq2m:.3e} rad, max|dbz| = {dbzm:.3e} m", flush=True)

    # (a) NM 폴리시
    r0 = minimize(obj, [3 * D2R, -3 * D2R], method="Nelder-Mead",
                  options=dict(xatol=2e-4, fatol=0.05, maxfev=70))
    o1, o2 = r0.x
    print(f"[NM] o1={np.degrees(o1):+.2f}deg o2={np.degrees(o2):+.2f}deg score={r0.fun:.1f}",
          flush=True)

    # (c) stiff_knee 민감도 (참고용 — 채택은 이중심판 필요)
    for sm in (0.7, 0.85, 1.0, 1.15, 1.3):
        s = obj([o1, o2], stiff_mul=sm)
        print(f"[stiff x{sm:.2f}] score={s:.1f}", flush=True)

    # 최종 구성 상세 지표
    rs = _pool.map(eval_off, [(o1, o2, s, 1.0) for s in SUBS429])
    ms = [m for _, m in rs if m]
    g = lambda k: float(np.mean([m[k] for m in ms]))
    print(f"[final A] q1 {g('q1'):.3f} q2 {g('q2'):.3f} dq1 {g('dq1'):.2f} dq2 {g('dq2'):.2f} "
          f"dtoff {g('dtoff')*1000:.1f}ms h {g('h'):.3f}/{g('h_real'):.3f}", flush=True)
    json.dump(dict(o1=float(o1), o2=float(o2), score=float(r0.fun),
                   equiv_dq2=dq2m, equiv_dbz=dbzm),
              open(HERE / "p18b_iter3.json", "w"), indent=1)
    print("saved p18b_iter3.json", flush=True)
    _pool.close(); _pool.join()


if __name__ == "__main__":
    main()
