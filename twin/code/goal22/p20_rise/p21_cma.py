# -*- coding: utf-8 -*-
"""P21 CMA — dq 충실도 마라톤 (지표 v4: τ + dq 명시 + 다중 시간스케일 + 0429 창 포함).

진단 (2026-07-14): p20c의 0429-A 속도 참사(3.3→9.8)의 주범 = 감쇠 손실(fv_hip 3.5×↓)
+ 스프링 강성화 — 목적함수에 장호라이즌 dq 항이 없어 생긴 왜곡. 처방 = 지표 v4:
  J = 0.35·CLτ + 0.20·CLdq + 0.15·JW02 + 0.15·JW06(0429 포함) + 0.10·s2s + 0.05·0604
  (전 항 P19 기준 정규화 — "P19를 모든 전선에서 이겨라"가 목표 그 자체)
  · CLdq  : 폐루프 dq 상대 RMSE (배포 속도 충실도)
  · JW02  : 0.2s 창 (기존 Mode A 가드)
  · JW06  : 0.6s 창 — 장호라이즌 드리프트 처벌, l_i=30 점프 + **0429(A)** 포함
축 20: 플랜트15 + tm + [c_qs, v0] + [o1_429, o2_429] + pre30(자유 — 데이터가 담요 필요성 결정).
재시작 4: P19 출발×2(σ 0.12/0.25) + p20c 출발×2. held-out(0324)은 전 항에서 제외 (게이트 전용).
시동: run_p21_cma.bat 더블클릭. 체크포인트 p21_cma.json.
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
sys.path.insert(0, str(HERE.parent.parent / "bench"))

NAMES = ["stiff", "ref", "fv_hip", "fc_hip", "fv_knee", "fc_knee", "solref",
         "imp0", "arm_knee", "M_c", "I_th", "I_ca", "dz_th", "dz_ca", "tm",
         "c_qs", "v0", "o1_429", "o2_429", "pre30"]
IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
LO = np.array([0.0, 1.5, 0.05, 0.0, 0.0, 0.0, 0.002, 0.05, 0.0005, 0.40, 0.55,
               0.55, -0.12, -0.12, 0.0, 0.0, 1.0, -0.15, -0.15, 0.0])
HI = np.array([2.5, 2.7, 2.50, 0.30, 0.15, 0.25, 0.030, 0.70, 0.020, 1.10, 1.45,
               1.45, 0.12, 0.12, 0.020, 0.45, 40.0, 0.15, 0.15, 4.0])

_W = {}


def _prep_0429():
    """0429 10 subs의 A-창(0.6s)용 FK 사전계산 (기하 불변)."""
    import p19_judge as P
    from cvt_core import load_0429, closure, SUBS429
    mj = P.J._P["mj"]; S = P.J._P["S"]
    model, _ = P.build_cvt(np.array(P.X37[:32]), 1.6, "calf", 0.02508)
    data = mj.MjData(model)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    pre = []
    for sub in SUBS429:
        d = load_0429(sub)
        li = d["l_i"]; t = d["t"]
        q1mj = -(d["q1"]) - np.pi / 2
        qcmj = -(d["q2"])
        bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
        qk_prev = None
        for i in range(len(t)):
            qk, qp, _ = closure(float(qcmj[i]), li, qk_prev)
            data.qpos[:] = [1.0, q1mj[i], qcmj[i], qp, qk]
            data.qvel[:] = 0
            mj.mj_forward(model, data)
            bz[i] = 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS
            qks[i] = qk; qps[i] = qp; qk_prev = qk
        vbz = np.gradient(bz, t)
        starts = []
        for t0 in (0.0, 0.06, 0.12):
            i0 = int(np.searchsorted(t, t0))
            if i0 >= len(t) - 10:
                continue
            qk2, qp2, _ = closure(float(qcmj[i0]) + 1e-4, li, qks[i0])
            starts.append((i0, (qk2 - qks[i0]) / 1e-4, (qp2 - qps[i0]) / 1e-4))
        pre.append(dict(d=d, li=li, t=t, q1mj=q1mj, qcmj=qcmj, bz=bz, vbz=vbz,
                        qks=qks, qps=qps, starts=starts))
    return pre


def _prep_0604():
    import p20_cma2 as C2
    return C2._prep_0604()


def winit_worker(base):
    import p19_judge as P
    import p19_run as R
    import p20_run as P20
    P.winit()
    _W.update(P=P, R=R, P20=P20, base=base, P12=P.J._P["P12"],
              mj=P.J._P["mj"], pre429=_prep_0429(), pre604=_prep_0604())


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


def cl_metrics(v, x32, sp):
    """CL 스택 1회 실행 → (τ-갭 v3, dq-갭) 동시 산출. held-out 제외."""
    P, R, P20 = _W["P"], _W["R"], _W["P20"]
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f, _ = P.build_flip(x32, v[1], sp)
    model_c = None
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    gs, dqs = [], []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        if ds == "jump_0324":
            continue
        alphas = R.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(x32, v[1], sp, l_i)
            L = P20.cl_run20(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                             v[14], alphas, c_qs=v[15], v0=v[16], Cd=0.0,
                             o1=v[17], o2=v[18])
        else:
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = P20.cl_run20(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                             v[14], alphas, c_qs=v[15], v0=v[16], Cd=0.0,
                             o1=o1, o2=o2, preload=v[19])
        if L is None:
            gs.append(2.0); dqs.append(2.0)
            continue
        g, q2r = R.gap_v3(L, d, P.A_PAPER, m)
        gs.append(min(g, 2.0))
        t = d["t"]
        f = lambda k: np.interp(t, L["t"], L[k])
        num = np.sqrt(np.mean((f("dq1") - d["dq1"])[m] ** 2)
                      + np.mean((f("dq2") - d["dq2"])[m] ** 2))
        den = max(np.sqrt(np.mean(d["dq1"][m] ** 2) + np.mean(d["dq2"][m] ** 2)), 0.5)
        dqs.append(min(float(num / den), 2.0))
    return float(np.mean(gs)), float(np.mean(dqs))


def windows_score(model, x32, dss, v, W_override=None, pre30=0.0):
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
        lam = lam_vec(tr["raw2"], tr["v2"], v[15], v[16]) + pre30
        th = -(P.J.ahat(A, tr["raw1"], tr["v1"]))
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        if W_override:
            ppv["W"] = W_override
        ppo = P12._G["sv"](ppv, o1, o2)
        per.append(P12.eval_windows(model, ppo, None))
    return float(np.mean(per)) if per else 9e9


def win429_06(v, x32, sp):
    """0429 A-창 0.6s (사전계산 FK) — 장호라이즌 속도 드리프트 처벌."""
    P, mj = _W["P"], _W["mj"]
    MS = _W["P12"]._G["MS"]
    model, _ = P.build_cvt(x32, v[1], sp, 0.02508)
    per = []
    for pre in _W["pre429"]:
        d = pre["d"]; t = pre["t"]
        lam = lam_vec(d["traw2"], d["dq2"], v[15], v[16])
        th = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tk = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
        data = mj.MjData(model)
        dt = model.opt.timestep
        for i0, r_, gp in pre["starts"]:
            t0 = t[i0]; t1 = min(t0 + 0.6, t[-1])
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


def score_0604(v, x32, sp):
    import p20_cma2 as C2
    C2._W.update(_W)
    return C2.score_0604(np.concatenate([v[:19]]))


def eval_parts(v):
    x32, sp = x32_of(v)
    _W["x32_cur"] = x32
    jcl, jdq = cl_metrics(v, x32, sp)
    P = _W["P"]
    model_f, _ = P.build_flip(x32, v[1], sp)
    JDS = ("jump_position_0421", "jump_0424", "jump_0602")
    jw02 = windows_score(model_f, x32, JDS, v, pre30=v[19])
    jw06_j = windows_score(model_f, x32, JDS, v, W_override=0.6, pre30=v[19])
    jw06_c = win429_06(v, x32, sp)
    s2s = windows_score(model_f, x32, ("s2s_gnd_0319",), v, pre30=v[19])
    o6 = score_0604(v, x32, sp)
    return jcl, jdq, jw02, (jw06_j, jw06_c), s2s, o6


def eval_x(v):
    try:
        base = _W["base"]
        jcl, jdq, jw02, (j6j, j6c), s2s, o6 = eval_parts(v)
        jw06 = 0.5 * j6j / base["J6J"] + 0.5 * j6c / base["J6C"]
        return (0.35 * jcl / base["CL"] + 0.20 * jdq / base["DQ"]
                + 0.15 * jw02 / base["JW2"] + 0.15 * jw06
                + 0.10 * s2s / base["S2S"] + 0.05 * o6 / base["O6"])
    except Exception:
        return 3.0


def main():
    import multiprocessing as mp
    import cma
    import p19_adapter as AD
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    C19 = AD.load_candidate(HERE.parent / "p19_jump/fourbar_p19_candidate.json")
    v19 = np.array(C19["x"], float)
    # P19 → 21축 x0 (pre30=2.25, c_qs=0)
    x19 = np.array([v19[0], v19[1], v19[3], v19[4], v19[5], v19[6], v19[7], v19[8],
                    v19[9], v19[10], v19[11], v19[12], v19[13], v19[14], v19[15],
                    0.0, 6.0, v19[16], v19[17], v19[2]])
    C20 = AD.load_candidate(HERE / "fourbar_p20c_candidate.json")
    v20 = np.array(C20["x"], float)
    x20 = np.array([v20[0], v20[1], v20[3], v20[4], v20[5], v20[6], v20[7], v20[8],
                    v20[9], v20[10], v20[11], v20[12], v20[13], v20[14], v20[15],
                    C20["p20"]["c_qs"], min(C20["p20"]["v0"], 39.9),
                    v20[16], v20[17], 0.0])
    x19 = np.clip(x19, LO + 1e-9, HI - 1e-9)
    x20 = np.clip(x20, LO + 1e-9, HI - 1e-9)
    winit_worker(dict(CL=1, DQ=1, JW2=1, J6J=1, J6C=1, S2S=1, O6=1, raw=True))
    jcl0, jdq0, jw20, (j6j0, j6c0), s2s0, o60 = eval_parts(x19)
    base = dict(CL=jcl0, DQ=jdq0, JW2=jw20, J6J=j6j0, J6C=j6c0, S2S=s2s0, O6=o60)
    print(f"x0(P19): CLτ {100*jcl0:.1f}% CLdq {100*jdq0:.1f}% | JW02 {jw20:.1f} | "
          f"JW06 {j6j0:.1f}/{j6c0:.1f} | s2s {s2s0:.1f} | 0604 {o60:.1f}", flush=True)
    json.dump(base, open(HERE / "p21_cma_base.json", "w"), indent=1)
    pool = mp.Pool(9, initializer=winit_worker, initargs=(base,))
    gbest = (1.0, x19)
    t0 = time.time()
    plan = [(x19, 0.12, 61), (x20, 0.12, 67), (x19, 0.25, 71), (x20, 0.25, 73)]
    for k, (xs_, sg, seed) in enumerate(plan):
        es = cma.CMAEvolutionStrategy(((xs_ - LO) / (HI - LO)).tolist(), sg,
                                      {"bounds": [0, 1], "maxfevals": maxfev,
                                       "popsize": 14, "seed": seed, "verbose": -9})
        nev = 0
        while not es.stop():
            sols = es.ask()
            xs = [LO + np.array(s) * (HI - LO) for s in sols]
            oo = pool.map(eval_x, xs)
            for x, o in zip(xs, oo):
                nev += 1
                if o < gbest[0]:
                    gbest = (o, x)
                    print(f"BEST r{k} nev={nev} J={o:.4f} " +
                          " ".join(f"{n}={val:.3g}" for n, val in zip(NAMES, x)) +
                          f" [{(time.time()-t0)/60:.1f}m]", flush=True)
            es.tell(sols, oo)
            json.dump(dict(J=float(gbest[0]), x=[float(a) for a in gbest[1]],
                           names=NAMES, restart=k, nev=nev),
                      open(HERE / "p21_cma.json", "w"), indent=1)
        print(f"restart {k} 종료 (global {gbest[0]:.4f}) [{(time.time()-t0)/60:.1f}m]",
              flush=True)
    print(f"P21 CMA DONE J={gbest[0]:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
