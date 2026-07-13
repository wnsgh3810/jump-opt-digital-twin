# -*- coding: utf-8 -*-
"""P20 조인트 재적합 CMA — "정직한 물리 + 준정적층만으로 P19를 이기는가" 결판.

배경: 현행 플랜트 15개 물리값은 pre30 담요가 있는 세계에서 적합됨. 새 구조
(준정적 25%층, 스펀지 Cd=0 고정)에는 불공정 → 플랜트+층 공동 재적합이 정당한 시험.
파라미터 17: 플랜트 15 (P19와 동일 축) + tm + [c_qs, v0].
목적: J = 0.5·CL_FIT + 0.3·점프창 + 0.2·s2s창 (x0 정규화). held-out(0324)은 게이트 전용.
시동: run_p20_cma.bat 더블클릭 (철칙 3). 체크포인트: p20_cma.json (매 세대 저장).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p19_jump"))

NAMES = ["stiff", "ref", "fv_hip", "fc_hip", "fv_knee", "fc_knee", "solref",
         "imp0", "arm_knee", "M_c", "I_th", "I_ca", "dz_th", "dz_ca", "tm",
         "c_qs", "v0"]
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
LO = np.array([0.0, 1.5, 0.05, 0.0, 0.0, 0.0, 0.002, 0.05, 0.0005, 0.40, 0.55,
               0.55, -0.05, -0.08, 0.0, 0.05, 1.0])
HI = np.array([2.5, 2.7, 2.50, 0.30, 0.15, 0.15, 0.030, 0.70, 0.020, 1.10, 1.45,
               1.45, 0.08, 0.05, 0.020, 0.45, 15.0])

_W = {}


def winit_worker(base):
    import p19_judge as P
    import p19_run as R
    import p20_run as P20
    P.winit()
    _W["P"] = P; _W["R"] = R; _W["P20"] = P20; _W["base"] = base
    _W["P12"] = P.J._P["P12"]


def x32_of(v):
    P = _W["P"]
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(NAMES):
        if n in IDX:
            x32[IDX[n]] = v[i]
    return x32, ("calf" if v[0] > 1e-3 else "none")


def windows_score(model, dss, c_qs, v0):
    """점프/s2s 창 점수 (준정적층 입력 벡터) — p20_exp1.eval_set 축약 이식."""
    P, P12 = _W["P"], _W["P12"]
    A = P.A_PAPER
    dd = None
    per = []
    for tr in P12._G["trials"]:
        if tr["ds"] not in dss:
            continue
        if dd is None:
            dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(_W["x32_cur"])[:26]))
        k1, k2 = P12.OFFKEY.get(tr["ds"], (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0
        o2 = dd.get(k2, 0.0) if k2 else 0.0
        t = tr["pp"]["t"]
        lam = c_qs * P.J.ahat(A, tr["raw2"], tr["v2"]) * _W["P20"].gate(tr["v2"], v0)
        th = -(P.J.ahat(A, tr["raw1"], tr["v1"]))
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        ppo = P12._G["sv"](ppv, o1, o2)
        per.append(P12.eval_windows(model, ppo, None))
    return float(np.mean(per)) if per else 9e9


def eval_x(v):
    try:
        if "P" not in _W:
            return 3.0
        P, R, P20, base = _W["P"], _W["R"], _W["P20"], _W["base"]
        x32, sp = x32_of(v)
        _W["x32_cur"] = x32
        rows = P20.eval_stack20(x32, v[1], sp, P.A_PAPER, v[14],
                                c=v[15], v0=v[16], Cd=0.0)
        jcl = float(np.mean([r["g"] for r in rows if r["ds"] != "jump_0324"]))
        model_f, _ = P.build_flip(x32, v[1], sp)
        jw = windows_score(model_f, ("jump_position_0421", "jump_0424", "jump_0602"),
                           v[15], v[16])
        s2s = windows_score(model_f, ("s2s_gnd_0319",), v[15], v[16])
        return (0.5 * jcl / base["CL"] + 0.3 * jw / base["JW"]
                + 0.2 * s2s / base["S2S"])
    except Exception:
        return 3.0


def main():
    import multiprocessing as mp
    import cma
    import p19_judge as P

    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    # x0 = P20 후보(=P19 플랜트) + c_qs 0.25, v0 6.0
    sys.path.insert(0, str(HERE.parent.parent / "bench"))
    import p19_adapter as AD
    cand = AD.load_candidate(HERE / "fourbar_p20_candidate.json")
    v19 = np.array(cand["x"], dtype=float)
    # P19 names: [stiff, ref, pre30, fv_hip, fc_hip, fv_knee, fc_knee, solref, imp0,
    #             arm_knee, M_c, I_th, I_ca, dz_th, dz_ca, tm, o1_429, o2_429]
    x0 = np.array([v19[0], v19[1], v19[3], v19[4], v19[5], v19[6], v19[7], v19[8],
                   v19[9], v19[10], v19[11], v19[12], v19[13], v19[14], v19[15],
                   0.25, 6.0])
    x0 = np.clip(x0, LO + 1e-9, HI - 1e-9)
    winit_worker(dict(CL=1.0, JW=1.0, S2S=1.0))
    j_parts_cl = None
    # x0 기준값 산출
    P.winit()
    _W["base"] = dict(CL=1.0, JW=1.0, S2S=1.0)
    x32, sp = x32_of(x0)
    _W["x32_cur"] = x32
    import p20_run as P20
    import p19_run as R
    rows = P20.eval_stack20(x32, x0[1], sp, P.A_PAPER, x0[14], c=x0[15], v0=x0[16], Cd=0.0)
    cl0 = float(np.mean([r["g"] for r in rows if r["ds"] != "jump_0324"]))
    model_f, _ = P.build_flip(x32, x0[1], sp)
    jw0 = windows_score(model_f, ("jump_position_0421", "jump_0424", "jump_0602"), x0[15], x0[16])
    s2s0 = windows_score(model_f, ("s2s_gnd_0319",), x0[15], x0[16])
    base = dict(CL=cl0, JW=jw0, S2S=s2s0)
    print(f"x0: CL {100*cl0:.1f}% | 점프창 {jw0:.1f} | s2s {s2s0:.1f}", flush=True)
    json.dump(base, open(HERE / "p20_cma_base.json", "w"), indent=1)

    pool = mp.Pool(9, initializer=winit_worker, initargs=(base,))
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.15,
                                  {"bounds": [0, 1], "maxfevals": maxfev,
                                   "popsize": 9, "seed": 31, "verbose": -9})
    best = (1.0, x0); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LO + np.array(s) * (HI - LO) for s in sols]
        oo = pool.map(eval_x, xs)
        for x, o in zip(xs, oo):
            nev += 1
            if o < best[0]:
                best = (o, x)
                print(f"BEST nev={nev} J={o:.4f} " +
                      " ".join(f"{n}={val:.3g}" for n, val in zip(NAMES, x)) +
                      f" [{(time.time()-t0)/60:.1f}m]", flush=True)
        es.tell(sols, oo)
        json.dump(dict(J=float(best[0]), x=[float(val) for val in best[1]],
                       names=NAMES, nev=nev),
                  open(HERE / "p20_cma.json", "w"), indent=1)
    print(f"P20 CMA DONE nev={nev} J={best[0]:.4f} [{(time.time()-t0)/60:.1f}m]",
          flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
