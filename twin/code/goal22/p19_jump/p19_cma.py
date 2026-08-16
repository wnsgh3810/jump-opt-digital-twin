# -*- coding: utf-8 -*-
"""P19 CMA-1 — A=Paper 고정, 물리 16-param을 점프 CL τ-갭에 직접 적합.
부분집합(~14 trials)으로 fit, 승자는 전체 검증. 크래시=2.5, 갭 캡 2.0."""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P

NAMES = ["stiff", "ref", "pre30", "fv_hip", "fc_hip", "fv_knee", "fc_knee",
         "solref", "imp0", "arm_knee", "M_c", "I_th", "I_ca",
         "dz_th", "dz_ca", "kp1s_0421"]
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6,
           dz_th=7, dz_ca=8)
LO = np.array([0.0, 1.6, 0.0, 0.05, 0.0, 0.0, 0.0, 0.002, 0.10, 0.002, 0.40, 0.7, 0.7, -0.03, -0.05, 0.4])
HI = np.array([1.6, 2.6, 4.0, 1.20, 0.15, 0.10, 0.10, 0.020, 0.60, 0.020, 1.10, 1.3, 1.3, 0.05, 0.03, 1.2])


def x0_from_p18b():
    X = P.X37
    return np.array([P.W18[0], P.W18[1], 2.06,
                     X[14], X[16], X[15], X[17], X[12], X[13], X[9], X[4],
                     X[5], X[6], X[7], X[8], 0.6])


def subset_rows():
    """fit 부분집합: ds별 절반 간격 샘플 + 0429 1/3."""
    subs = {}
    for tr in P.J._P["cl"]:
        subs.setdefault(tr["ds"], []).append(tr["sub"])
    pick = {}
    for ds, ss in subs.items():
        if ds == "jump_0324":
            continue
        step = 3 if ds == "jump_position_0421" else 2
        pick[ds] = sorted(ss)[::step]
    from cvt_core import SUBS429
    pick["jump_0429"] = sorted(SUBS429)[::3]
    return pick


PICK = None


def eval_x(v):
    global PICK
    try:
        if not P.J._P:
            P.winit()
        if PICK is None:
            PICK = subset_rows()
        x32 = np.array(P.X37[:32])
        for i, n in enumerate(NAMES):
            if n in IDX:
                x32[IDX[n]] = v[i]
        ref, pre, kp1s = v[1], v[2], v[15]
        A = P.A_PAPER
        sp = "calf" if v[0] > 1e-3 else "none"
        # no_cvt CL (부분집합만)
        model, _ = P.build_flip(x32, ref, sp)
        dd = dict(zip(P.J._P["FR"].NAMES, x32[:26]))
        gaps = []
        for tr in P.J._P["cl"]:
            if tr["ds"] == "jump_0324" or tr["sub"] not in PICK.get(tr["ds"], []):
                continue
            ks = kp1s if tr["ds"] == "jump_position_0421" else 1.0
            L = P.run_cl_pre(model, dd, tr, A, pre, kp1s=ks)
            if L is None:
                gaps.append(2.5); continue
            g1, g2, _ = P.tau_gap(L, tr, A)
            gaps.append(min(0.5 * (g1 + g2), 2.0))
        # cvt CL (부분집합)
        from cvt_run2 import sim_run
        import cvt_run2 as R
        from cvt_core import load_0429, label_gains_429
        o1q, o2q = 3.14 * np.pi / 180, -3.0 * np.pi / 180
        A_save = R.A.copy(); R.A = np.asarray(A, float)
        try:
            model_c = None
            for sub in PICK["jump_0429"]:
                d = load_0429(sub)
                if model_c is None:
                    model_c, _ = P.build_cvt(x32, ref, sp, d["l_i"])
                L, _ = sim_run(model_c, d, d["l_i"], "CL",
                               gains=label_gains_429(sub), o1=o1q, o2=o2q)
                if L is None:
                    gaps.append(2.5); continue
                t = d["t"]
                g = d["grf_real"]; pk = int(np.argmax(g))
                below = np.where(g[pk:] < 0.02 * g[pk])[0]
                toff = t[pk + below[0]] if len(below) else t[-1]
                m = t <= min(t[-1], toff + 0.1)
                tp1 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
                tp2 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
                s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
                g1 = float(np.sqrt(np.mean((s1 - tp1)[m] ** 2)) / max(np.sqrt(np.mean(tp1[m] ** 2)), 0.3))
                g2 = float(np.sqrt(np.mean((s2 - tp2)[m] ** 2)) / max(np.sqrt(np.mean(tp2[m] ** 2)), 0.3))
                gaps.append(min(0.5 * (g1 + g2), 2.0))
        finally:
            R.A = A_save
        return float(np.mean(gaps))
    except Exception:
        return 3.0


def main():
    import multiprocessing as mp
    import cma
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 350
    pool = mp.Pool(10, initializer=P.winit)
    x0 = np.clip(x0_from_p18b(), LO + 1e-9, HI - 1e-9)
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.18,
                                  {"bounds": [0, 1], "maxfevals": maxfev,
                                   "popsize": 10, "seed": 19, "verbose": -9})
    j0 = pool.apply(eval_x, (x0,))
    print(f"x0(P18b+paper) subset J = {j0:.4f}", flush=True)
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
        json.dump(dict(J=float(best[0]), x=[float(v) for v in best[1]],
                       names=NAMES, nev=nev),
                  open(HERE / "p19_cma1.json", "w"), indent=1)
    print(f"CMA1 DONE nev={nev} J={best[0]:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
