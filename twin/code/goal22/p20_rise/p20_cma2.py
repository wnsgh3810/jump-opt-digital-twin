# -*- coding: utf-8 -*-
"""P20 조인트 재적합 2라운드 — 경계 확장 + 0429 오프셋 해방 + 0604 채점 포함 + 다중 재시작.

1라운드(p20_cma) 대비:
  · 경계 확장: dz_th/dz_ca ±0.12, v0≤40, fc_knee≤0.25, c_qs≥0 (층의 완전 소거 허용)
  · o1_429/o2_429 자유 (19축)
  · 목적: J = 0.5·CL + 0.25·점프창 + 0.15·s2s + 0.10·0604창 (x0 정규화, held-out 제외)
  · 재시작 3회(시드 41/43/47) × maxfev — 지역최적 방지
시동: run_p20_cma2.bat 더블클릭. 체크포인트: p20_cma2.json (+ 재시작별 r{k}.json).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))

NAMES = ["stiff", "ref", "fv_hip", "fc_hip", "fv_knee", "fc_knee", "solref",
         "imp0", "arm_knee", "M_c", "I_th", "I_ca", "dz_th", "dz_ca", "tm",
         "c_qs", "v0", "o1_429", "o2_429"]
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
LO = np.array([0.0, 1.5, 0.05, 0.0, 0.0, 0.0, 0.002, 0.05, 0.0005, 0.40, 0.55,
               0.55, -0.12, -0.12, 0.0, 0.0, 1.0, -0.15, -0.15])
HI = np.array([2.5, 2.7, 2.50, 0.30, 0.15, 0.25, 0.030, 0.70, 0.020, 1.10, 1.45,
               1.45, 0.12, 0.12, 0.020, 0.45, 40.0, 0.15, 0.15])

_W = {}


def _prep_0604():
    """0604 두 trial의 FK 기하 사전계산 (기하는 후보 간 불변)."""
    import p19_judge as P
    import s2s_0604 as S0
    from cvt_core import closure
    mj = P.J._P["mj"]; S = P.J._P["S"]
    pre = []
    for grp, sub, load in (("cvt", "no_load", 0.0), ("cvt", "load_5", 5.0)):
        d = S0.load_0604(grp, sub)
        li = d["l_i"]
        model, _ = P.build_cvt(np.array(P.X37[:32]), 1.6, "calf", li)
        data = mj.MjData(model)
        t = d["t"]
        q1mj = -(d["q1"]) - np.pi / 2
        qcmj = -(d["q2"])
        bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
        qk_prev = None
        fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        for i in range(len(t)):
            qk, qp, _ = closure(float(qcmj[i]), li, qk_prev)
            data.qpos[:] = [1.0, q1mj[i], qcmj[i], qp, qk]
            data.qvel[:] = 0
            mj.mj_forward(model, data)
            bz[i] = 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS
            qks[i] = qk; qps[i] = qp; qk_prev = qk
        vbz = np.gradient(bz, t)
        starts = []
        for t0 in np.arange(0.3, t[-1] - 0.3, 0.5):
            i0 = int(np.searchsorted(t, t0))
            qk2, qp2, _ = closure(float(qcmj[i0]) + 1e-4, li, qks[i0])
            starts.append((i0, (qk2 - qks[i0]) / 1e-4, (qp2 - qps[i0]) / 1e-4))
        pre.append(dict(d=d, li=li, load=load, t=t, q1mj=q1mj, qcmj=qcmj,
                        bz=bz, vbz=vbz, qks=qks, qps=qps, starts=starts))
    return pre


def winit_worker(base):
    import p19_judge as P
    import p19_run as R
    import p20_run as P20
    P.winit()
    _W.update(P=P, R=R, P20=P20, base=base, P12=P.J._P["P12"],
              mj=P.J._P["mj"], pre604=_prep_0604())


def x32_of(v):
    P = _W["P"]
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(NAMES):
        if n in IDX:
            x32[IDX[n]] = v[i]
    return x32, ("calf" if v[0] > 1e-3 else "none")


def lam_vec(raw2, dq2, c, v0):
    P, P20 = _W["P"], _W["P20"]
    return c * P.J.ahat(P.A_PAPER, raw2, dq2) * P20.gate(dq2, v0)


def windows_score(model, x32, dss, c, v0):
    P, P12 = _W["P"], _W["P12"]
    A = P.A_PAPER
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    per = []
    for tr in P12._G["trials"]:
        if tr["ds"] not in dss:
            continue
        k1, k2 = P12.OFFKEY.get(tr["ds"], (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0
        o2 = dd.get(k2, 0.0) if k2 else 0.0
        t = tr["pp"]["t"]
        lam = lam_vec(tr["raw2"], tr["v2"], c, v0)
        th = -(P.J.ahat(A, tr["raw1"], tr["v1"]))
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        ppo = P12._G["sv"](ppv, o1, o2)
        per.append(P12.eval_windows(model, ppo, None))
    return float(np.mean(per)) if per else 9e9


def score_0604(v):
    """0604 창 점수 (사전계산 FK, 층 적용, λ그리드 없음 — 단일 재생)."""
    P, mj, P20 = _W["P"], _W["mj"], _W["P20"]
    MS = _W["P12"]._G["MS"]
    x32, sp = x32_of(v)
    per = []
    for pre in _W["pre604"]:
        d = pre["d"]; t = pre["t"]
        model, _ = P.build_cvt(x32, v[1], sp, pre["li"])
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += pre["load"]
        data = mj.MjData(model)
        dt = model.opt.timestep
        lam = lam_vec(d["traw2"], d["dq2"], v[15], v[16])
        th = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tk = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
        for i0, r_, gp in pre["starts"]:
            t0 = t[i0]; t1 = min(t0 + 0.2, t[-1])
            dqc = -d["dq2"][i0]
            data.qpos[:] = [pre["bz"][i0], pre["q1mj"][i0], pre["qcmj"][i0],
                            pre["qps"][i0], pre["qks"][i0]]
            data.qvel[:] = [pre["vbz"][i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
            mj.mj_forward(model, data)
            nst = int(round((t1 - t0) / dt))
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                data.ctrl[:] = [-float(np.interp(tc, t, th)),
                                -float(np.interp(tc, t, tk))]
                try:
                    mj.mj_step(model, data)
                except Exception:
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
                dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
            if not ok:
                per.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                continue
            r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            per.append(MS.W_Q * (r(q1a, pre["q1mj"]) + r(q2a, pre["qcmj"]))
                       + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
    return float(np.mean(per)) if per else 9e9


def eval_parts(v):
    P, R, P20 = _W["P"], _W["R"], _W["P20"]
    x32, sp = x32_of(v)
    rows = P20.eval_stack20(x32, v[1], sp, P.A_PAPER, v[14], c=v[15], v0=v[16],
                            Cd=0.0, q_off_0429=(v[17], v[18]))
    jcl = float(np.mean([r["g"] for r in rows if r["ds"] != "jump_0324"]))
    model_f, _ = P.build_flip(x32, v[1], sp)
    jw = windows_score(model_f, x32, ("jump_position_0421", "jump_0424", "jump_0602"),
                       v[15], v[16])
    s2s = windows_score(model_f, x32, ("s2s_gnd_0319",), v[15], v[16])
    o6 = score_0604(v)
    return jcl, jw, s2s, o6


def eval_x(v):
    try:
        base = _W["base"]
        jcl, jw, s2s, o6 = eval_parts(v)
        return (0.5 * jcl / base["CL"] + 0.25 * jw / base["JW"]
                + 0.15 * s2s / base["S2S"] + 0.10 * o6 / base["O6"])
    except Exception:
        return 3.0


def main():
    import multiprocessing as mp
    import cma
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
    W1 = json.load(open(HERE / "p20_cma.json"))
    v1 = np.array(W1["x"])
    x0 = np.concatenate([v1, [0.0548, -0.0524]])
    x0 = np.clip(x0, LO + 1e-9, HI - 1e-9)
    winit_worker(dict(CL=1, JW=1, S2S=1, O6=1))
    jcl0, jw0, s2s0, o60 = eval_parts(x0)
    base = dict(CL=jcl0, JW=jw0, S2S=s2s0, O6=o60)
    print(f"x0(1라운드 승자): CL {100*jcl0:.1f}% | 점프창 {jw0:.1f} | s2s {s2s0:.1f} | 0604 {o60:.1f}",
          flush=True)
    json.dump(base, open(HERE / "p20_cma2_base.json", "w"), indent=1)
    pool = mp.Pool(9, initializer=winit_worker, initargs=(base,))
    gbest = (1.0, x0)
    t0 = time.time()
    for k, seed in enumerate((41, 43, 47)):
        sigma = 0.10 if k == 0 else 0.25
        es = cma.CMAEvolutionStrategy(((x0 - LO) / (HI - LO)).tolist(), sigma,
                                      {"bounds": [0, 1], "maxfevals": maxfev,
                                       "popsize": 14, "seed": seed, "verbose": -9})
        best = (1e9, None); nev = 0
        while not es.stop():
            sols = es.ask()
            xs = [LO + np.array(s) * (HI - LO) for s in sols]
            oo = pool.map(eval_x, xs)
            for x, o in zip(xs, oo):
                nev += 1
                if o < best[0]:
                    best = (o, x)
                    if o < gbest[0]:
                        gbest = (o, x)
                        print(f"BEST r{k} nev={nev} J={o:.4f} " +
                              " ".join(f"{n}={val:.3g}" for n, val in zip(NAMES, x)) +
                              f" [{(time.time()-t0)/60:.1f}m]", flush=True)
            es.tell(sols, oo)
            json.dump(dict(J=float(gbest[0]), x=[float(a) for a in gbest[1]],
                           names=NAMES, restart=k, nev=nev),
                      open(HERE / "p20_cma2.json", "w"), indent=1)
        print(f"restart {k} 종료 J={best[0]:.4f} (global {gbest[0]:.4f}) "
              f"[{(time.time()-t0)/60:.1f}m]", flush=True)
    print(f"P20 CMA2 DONE J={gbest[0]:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
