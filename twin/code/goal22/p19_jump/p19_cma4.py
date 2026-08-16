# -*- coding: utf-8 -*-
"""P19 CMA-4 — hip 스프링 해방 (역대 STIFF_HIP=0 고정) + 민감 9종 재조정.
hip 스프링은 컴파일 후 jnt_stiffness/qpos_spring 주입 (Mode A·CL 일관)."""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P
import p19_run as R
from p19_cma3 import modeA_429, G6

NAMES = ["k_hip", "ref_hip", "stiff", "ref", "pre30", "fv_hip", "fv_knee",
         "solref", "imp0", "o1_429", "o2_429"]
LO = np.array([0.0, -2.2, 0.0, 1.5, 0.0, 0.05, 0.0, 0.002, 0.05, -0.09, -0.11])
HI = np.array([4.0, -0.2, 2.5, 2.7, 4.0, 2.50, 0.15, 0.030, 0.70, 0.09, 0.02])
W3 = json.load(open(HERE / "p19_cma2.json"))["x"] if False else json.load(open(HERE / "p19_cma3.json"))["x"]
IDX = dict(stiff=11, fv_hip=14, fv_knee=15, solref=12, imp0=13,
           fc_hip=16, fc_knee=17, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
HIPFIX = dict(k=0.0, ref=-1.0)

_bf, _bc = P.build_flip, P.build_cvt


def _hip_spring(model):
    mj = P.J._P["mj"]
    jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "hip")
    model.jnt_stiffness[jid] = HIPFIX["k"]
    model.qpos_spring[model.jnt_qposadr[jid]] = -HIPFIX["ref"] - np.pi / 2
    return model


def build_flip2(x32, ref, sp):
    m, dd = _bf(x32, ref, sp)
    return _hip_spring(m), dd


def build_cvt2_(x32, ref, sp, l_i):
    m, dd = _bc(x32, ref, sp, l_i)
    return _hip_spring(m), dd


P.build_flip = build_flip2
P.build_cvt = build_cvt2_
BASE = None


def x32_of(v):
    x32 = np.array(P.X37[:32])
    for n, i in [("stiff", 2), ("fv_hip", 5), ("fv_knee", 6), ("solref", 7), ("imp0", 8)]:
        x32[IDX[n]] = v[i]
    # cma3 승자의 나머지 물리 유지
    for n, wi in [("fc_hip", 4), ("fc_knee", 6), ("arm_knee", 9), ("M_c", 10),
                  ("I_th", 11), ("I_ca", 12), ("dz_th", 13), ("dz_ca", 14)]:
        x32[IDX[n]] = W3[wi]
    return x32


def parts4(v):
    HIPFIX["k"] = v[0]; HIPFIX["ref"] = v[1]
    x32 = x32_of(v)
    sp = "calf" if v[2] > 1e-3 else "none"
    rows = R.eval_stack(x32, v[3], sp, P.A_PAPER, v[4], W3[15], use_alpha=True,
                        q_off_0429=(v[9], v[10]))
    jcl = float(np.mean([r["g"] for r in rows if r["ds"] != "jump_0324"]))
    ot2 = {ds: v[4] for ds in ("jump_0424", "jump_0602", "jump_position_0421", "jump_0324")}
    ma = P.eval_modeA_jump(x32, v[3], sp, P.A_PAPER, ot2)
    j429 = modeA_429(x32, v[3], sp, o1=v[9], o2=v[10])
    return jcl, ma, j429


def eval_x(v):
    try:
        if not P.J._P:
            P.winit()
        jcl, ma, j429 = parts4(v)
        ja = float(np.mean([ma[g] / BASE["A"][g] for g in G6]))
        return 0.5 * jcl / BASE["CL"] + 0.3 * ja + 0.2 * j429 / BASE["429"]
    except Exception:
        return 3.0


def winit_base(base):
    global BASE
    P.winit()
    BASE = base


def main():
    import multiprocessing as mp
    import cma
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    x0 = np.array([0.5, -1.0, W3[0], W3[1], W3[2], W3[3], W3[5], W3[7], W3[8],
                   W3[16], W3[17]])
    x0 = np.clip(x0, LO + 1e-9, HI - 1e-9)
    P.winit()
    base = json.load(open(HERE / "p19_cma3_base.json"))   # cma3와 같은 정규화 기준
    global BASE
    BASE = base
    j0 = eval_x(x0)
    print(f"x0(hip 0.5/−1.0) J = {j0:.4f} (cma3 최종 0.9794 대비)", flush=True)
    pool = mp.Pool(10, initializer=winit_base, initargs=(base,))
    es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), 0.2,
                                  {"bounds": [0, 1], "maxfevals": maxfev,
                                   "popsize": 10, "seed": 41, "verbose": -9})
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
                      " ".join(f"{n}={val:.3g}" for n, val in zip(NAMES, x)) +
                      f" [{(time.time()-t0)/60:.1f}m]", flush=True)
        es.tell(sols, oo)
        json.dump(dict(J=float(best[0]), x=[float(val) for val in best[1]],
                       names=NAMES, w3=[float(w) for w in W3], nev=nev),
                  open(HERE / "p19_cma4.json", "w"), indent=1)
    print(f"CMA4 DONE nev={nev} J={best[0]:.4f}", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
