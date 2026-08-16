# -*- coding: utf-8 -*-
"""P21 폴리시 — 제약 탐색: [전 v4 성분 ≤ P19] 안에서 개루프 통짜 dq(0429)·점프높이 최대 회복.

파레토 진단(2026-07-15): CLτ 최적과 개루프 안정성이 상충. 이 탐색은 타협점의 존재를 판정:
  min  (통짜dq/3.31) + 4·max(0, (h̄−0.985)/0.05) + 20·Σ max(0, 성분/P19 − 1)
자유 6축: fv_hip, fc_hip, c_qs, v0, stiff, ref (승자 근방). 나머지 = P21 승자 고정.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p21_cma as C

FREE = {"fv_hip": 2, "fc_hip": 3, "c_qs": 15, "v0": 16, "stiff": 0, "ref": 1}
FNAMES = list(FREE)
LO6 = np.array([0.10, 0.0, 0.0, 2.0, 0.3, 1.5])
HI6 = np.array([1.20, 0.15, 0.30, 40.0, 1.8, 2.3])
BASE7 = dict(CL=0.381, DQ=0.167, JW2=418.1, J6J=1235.9, J6C=299.3, S2S=4926.8, O6=164.5)

_V0 = None


def winit(base):
    C.winit_worker(dict(CL=1, DQ=1, JW2=1, J6J=1, J6C=1, S2S=1, O6=1, raw=True))


def a429_full(v):
    import p19_judge as P
    from cvt_core import load_0429, SUBS429, qpos_from_crank
    mj = P.J._P["mj"]; S = P.J._P["S"]
    x32, sp = C.x32_of(v)
    model, _ = P.build_cvt(x32, v[1], sp, 0.02508)
    rmse = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    es, hs = [], []
    for sub in SUBS429:
        d = load_0429(sub); t = d["t"]
        lam = C.lam_vec(d["traw2"], d["dq2"], v[15], v[16])
        t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
        md = mj.MjData(model)
        sq1, sq2 = -(d["q1"][0]) - np.pi / 2, -(d["q2"][0])
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, d["l_i"])[0]
        mj.mj_forward(model, md)
        fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
        md.qvel[:] = 0; mj.mj_forward(model, md)
        dt = model.opt.timestep
        N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
        tl = np.arange(N) * dt - P.J.T_SETTLE
        dq2s = np.zeros(N); bzs = np.zeros(N)
        for k in range(N):
            tc = tl[k]
            if tc < 0:
                q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
                c1 = S.SETTLE_KP * (-(sq1 + np.pi / 2) - q1c) - S.SETTLE_KD * (-md.qvel[1])
                c2 = S.SETTLE_KP * (-sq2 - q2c) - S.SETTLE_KD * (-md.qvel[2])
                s1 = float(P.J.ahat(P.A_PAPER, np.array([c1]), np.array([-md.qvel[1]]))[0])
                s2 = float(P.J.ahat(P.A_PAPER, np.array([c2]), np.array([-md.qvel[2]]))[0])
            else:
                tm_ = min(tc, t[-1])
                s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
                if tc > t[-1]:
                    s1 = s2 = 0.0
            md.ctrl[:] = [-s1, -s2]
            try:
                mj.mj_step(model, md)
            except Exception:
                return 9.9, 2.0
            dq2s[k] = -md.qvel[2]; bzs[k] = md.qpos[0]
        m = t <= t[-1]
        es.append(rmse(np.interp(t, tl, dq2s)[m], d["dq2"][m]))
        hs.append(float(bzs[tl > 0].max()))
    return float(np.mean(es)), float(np.mean(hs))


def eval_x(u):
    try:
        v = _V0.copy()
        for i, (name, idx) in enumerate(FREE.items()):
            v[idx] = u[i]
        jcl, jdq, jw02, (j6j, j6c), s2s, o6 = C.eval_parts(v)
        comp = dict(CL=jcl, DQ=jdq, JW2=jw02, J6J=j6j, J6C=j6c, S2S=s2s, O6=o6)
        pen = sum(max(0.0, comp[k] / BASE7[k] - 1.0) for k in BASE7)
        e429, h = a429_full(v)
        return (e429 / 3.31) + 4.0 * max(0.0, (h - 0.985) / 0.05) + 20.0 * pen
    except Exception:
        return 9.0


def _init(v0):
    global _V0
    _V0 = np.array(v0)
    winit(None)


def main():
    import multiprocessing as mp
    import cma
    global _V0
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    W = json.load(open(HERE / "p21_cma.json"))
    v0 = np.array(W["x"])
    _V0 = v0.copy()
    u0 = np.array([v0[i] for i in FREE.values()])
    u0 = np.clip(u0, LO6 + 1e-9, HI6 - 1e-9)
    pool = mp.Pool(9, initializer=_init, initargs=(v0,))
    es = cma.CMAEvolutionStrategy(((u0 - LO6) / (HI6 - LO6)).tolist(), 0.2,
                                  {"bounds": [0, 1], "maxfevals": maxfev,
                                   "popsize": 10, "seed": 83, "verbose": -9})
    best = (9e9, u0); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LO6 + np.array(s) * (HI6 - LO6) for s in sols]
        oo = pool.map(eval_x, xs)
        for x, o in zip(xs, oo):
            nev += 1
            if o < best[0]:
                best = (o, x)
                print(f"BEST nev={nev} J={o:.4f} " +
                      " ".join(f"{n}={val:.3g}" for n, val in zip(FNAMES, x)) +
                      f" [{(time.time()-t0)/60:.1f}m]", flush=True)
        es.tell(sols, oo)
        json.dump(dict(J=float(best[0]), u=[float(a) for a in best[1]],
                       fnames=FNAMES, nev=nev),
                  open(HERE / "p21_polish.json", "w"), indent=1)
    print(f"POLISH DONE nev={nev} J={best[0]:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
