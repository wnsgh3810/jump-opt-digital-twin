# -*- coding: utf-8 -*-
"""P19 CMA-3 (cma2 확장: I_ca/dz_th 바운드 확장 + 0429 q오프셋 2dim + 웜스타트) — 결합 목적: J = 0.5·CL τ-갭 + 0.3·ModeA(평행사변형 점프, x0 정규화)
+ 0.2·ModeA(0429 stance, x0 정규화). CL만 fit하면 PD가 오차를 흡수 (사용자 지적).
커맨드층(α 고정) + 물리 15 + tm, 전 31 CL trials + Mode A 점프."""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P
import p19_run as R

NAMES = ["stiff", "ref", "pre30", "fv_hip", "fc_hip", "fv_knee", "fc_knee",
         "solref", "imp0", "arm_knee", "M_c", "I_th", "I_ca", "dz_th", "dz_ca", "tm",
         "o1_429", "o2_429"]
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
LO = np.array([0.0, 1.5, 0.0, 0.05, 0.0, 0.0, 0.0, 0.002, 0.05, 0.0005, 0.40, 0.50, 0.55, -0.05, -0.08, 0.0, -0.09, -0.11])
HI = np.array([2.5, 2.7, 4.0, 2.50, 0.30, 0.15, 0.15, 0.030, 0.70, 0.020, 1.10, 1.50, 1.90, 0.16, 0.05, 0.020, 0.09, 0.02])


G6 = ["w_0421", "w_0424", "w_0602", "fs_0424", "fs_0602", "habs"]
BASE_A = None      # x0 정규화 기준 (main에서 설정)
BASE_429 = None
SUB4 = ["60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"]


def modeA_429(x32, ref, sp, o1=3.14 * np.pi / 180, o2=-3.0 * np.pi / 180):
    """0429 Mode A stance 점수 (P18b sc429 방식, 4-trial 부분집합)."""
    from cvt_run2 import sim_run, metrics2, score
    from cvt_core import load_0429
    import cvt_run2 as C
    A_save = C.A.copy(); C.A = np.asarray(P.A_PAPER, float)
    try:
        scs = []
        model = None
        for sub in SUB4:
            d = load_0429(sub)
            if model is None:
                model, _ = P.build_cvt(x32, ref, sp, d["l_i"])
            L, _ = sim_run(model, d, d["l_i"], "A", o1=o1, o2=o2)
            if L is None:
                return 9e3
            scs.append(score(metrics2(d, L, o1, o2)))
        return float(np.mean(scs))
    finally:
        C.A = A_save


def parts_x(v):
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(NAMES):
        if n in IDX:
            x32[IDX[n]] = v[i]
    sp = "calf" if v[0] > 1e-3 else "none"
    rows = R.eval_stack(x32, v[1], sp, P.A_PAPER, v[2], v[15], use_alpha=True,
                        q_off_0429=(v[16], v[17]))
    jcl = float(np.mean([r["g"] for r in rows if r["ds"] != "jump_0324"]))
    ot2 = {"jump_0424": v[2], "jump_0602": v[2], "jump_position_0421": v[2],
           "jump_0324": v[2]}
    ma = P.eval_modeA_jump(x32, v[1], sp, P.A_PAPER, ot2)
    j429 = modeA_429(x32, v[1], sp, o1=v[16], o2=v[17])
    return jcl, ma, j429


def eval_x(v):
    try:
        if not P.J._P:
            P.winit()
        jcl, ma, j429 = parts_x(v)
        ja = float(np.mean([ma[g] / BASE_A[g] for g in G6]))
        return 0.5 * jcl / BASE_CL + 0.3 * ja + 0.2 * j429 / BASE_429
    except Exception:
        return 3.0


def winit_base(base):
    global BASE_A, BASE_CL, BASE_429
    P.winit()
    BASE_A = base["A"]; BASE_CL = base["CL"]; BASE_429 = base["429"]


def main():
    import multiprocessing as mp
    import cma
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 1600
    X = P.X37
    W2 = json.load(open(HERE / "p19_cma3.json"))["x"]
    rng = np.random.default_rng(7)
    x0 = np.array(W2) * (1 + 0.10 * rng.standard_normal(len(W2)))
    x0 = np.clip(x0, LO + 1e-9, HI - 1e-9)
    P.winit()
    jcl0, ma0, j4290 = parts_x(x0)
    base = dict(A={g: float(ma0[g]) for g in G6}, CL=float(jcl0), _429=None)
    base["429"] = float(j4290)
    print(f"x0: CL {jcl0:.4f} | ModeA " +
          " ".join(f"{g}={ma0[g]:.0f}" for g in G6) + f" | 0429 {j4290:.1f}", flush=True)
    json.dump(base, open(HERE / "p19_cma3_base.json", "w"), indent=1)
    pool = mp.Pool(10, initializer=winit_base, initargs=(base,))
    j0 = 1.0
    print(f"x0 J = {j0:.4f} (정의상 1.0)", flush=True)
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.28,
                                  {"bounds": [0, 1], "maxfevals": maxfev,
                                   "popsize": 10, "seed": 53, "verbose": -9})
    best = (j0, x0); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LO + np.array(s) * (HI - LO) for s in sols]
        oo = pool.map(eval_x, xs)
        for x, o in zip(xs, oo):
            nev += 1
            if o < best[0]:
                best = (o, x)
                print(f"BEST nev={nev} J={o:.4f} " +
                      " ".join(f"{n}={v:.3g}" for n, v in zip(NAMES, x)) +
                      f" [{(time.time()-t0)/60:.1f}m]", flush=True)
        es.tell(sols, oo)
        json.dump(dict(J=float(best[0]), x=[float(v) for v in best[1]], names=NAMES,
                       nev=nev), open(HERE / "p19_cma3b.json", "w"), indent=1)
    print(f"CMA3b DONE nev={nev} J={best[0]:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
