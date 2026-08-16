# -*- coding: utf-8 -*-
"""공통 l_i 캘리브레이션 오프셋 δ 프로브 (사용자 가설 2026-07-13).

가설: 링크길이 측정계(볼스크류 영점)에 전 세션 공통 오프셋 δ가 있어
  무변속 실제 l_i = 30.00−δ, 0429 실제 = Clutch값−δ.
검사: (무변속 창 replay 점수 vs [l_i × pre λ] 격자) + (0429 Mode A 점수 vs δ).
성공 판정: 어떤 δ>0에서 무변속이 λ<2.25로 현행(30.00, λ=2.25) 수준 도달 + 0429 무악화.
스텝핑 = P12.eval_windows 프로토콜 (리셋만 closure 일반화), 0429 = cvt_run2.sim_run 정본.
0324(held-out) 미사용.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_adapter as AD

AD.ensure_init()
import p19_judge as P
from cvt_core import closure, load_0429

CAND = AD.load_candidate(HERE / "fourbar_p19_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)
A = P.A_PAPER
P12 = P.J._P["P12"]
mj = P.J._P["mj"]
MS = P12._G["MS"]
DD = dict(zip(P.J._P["FR"].NAMES, np.asarray(X32)[:26]))


def win_scores(model, is_cvt, l_i, tr, lam):
    k1, k2 = P12.OFFKEY.get(tr["ds"], (None, None))
    o1 = DD[k1] if k1 else 0.0
    o2 = DD[k2] if k2 else 0.0
    pp0 = tr["pp"]; t = pp0["t"]
    th = -P.J.ahat(A, tr["raw1"], tr["v1"])
    tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
    ppv = dict(pp0, tau_h=np.interp(t - P.SD, t, th), tau_k=np.interp(t - P.SD, t, tk))
    pp = P12._G["sv"](ppv, o1, o2)
    d_ = mj.MjData(model); dt = model.opt.timestep
    out = []
    for i0 in [int(i) for i in pp["starts"]]:
        t1 = min(t[i0] + pp["W"], t[-1])
        qc = float(pp["q2m"][i0]); dqc = float(pp["dq2m"][i0])
        if is_cvt:
            try:
                qk, qp, _ = closure(qc, l_i, None)
                qk2, qp2, _ = closure(qc + 1e-4, l_i, qk)
                r_ = (qk2 - qk) / 1e-4; gp = (qp2 - qp) / 1e-4
            except Exception:
                return None
            d_.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], qc, qp, qk]
            d_.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dqc, gp * dqc, r_ * dqc]
        else:
            d_.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], qc, -qc, qc]
            d_.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dqc, -dqc, dqc]
        mj.mj_forward(model, d_)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d_.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mj.mj_step(model, d_)
            except Exception:
                ok = False; break
            ts[k] = tc + dt
            q1a[k] = d_.qpos[1]; q2a[k] = d_.qpos[2]
            dq1a[k] = d_.qvel[1]; dq2a[k] = d_.qvel[2]
        if not ok:
            out.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
        mk = (t >= ts[0]) & (t <= ts[-1])
        if mk.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
        out.append(MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
                   + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"])))
    return out


def sc429(delta_mm):
    """0429 Mode A 점수 (cma2.modeA_429 프로토콜, l_i에 −δ 적용)."""
    from cvt_run2 import sim_run, metrics2, score
    import cvt_run2 as C
    SUB4 = ["60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"]
    o1, o2 = 3.14 * np.pi / 180, -3.0 * np.pi / 180
    A_save = C.A.copy(); C.A = np.asarray(A, float)
    try:
        scs = []
        model = None
        for sub in SUB4:
            d = load_0429(sub)
            li = d["l_i"] - delta_mm * 1e-3
            if model is None:
                model, _ = P.build_cvt(X32, V[1], SP, li)
            L, _ = sim_run(model, d, li, "A", o1=o1, o2=o2)
            if L is None:
                return float("nan")
            scs.append(score(metrics2(d, L, o1, o2)))
        return float(np.mean(scs))
    finally:
        C.A = A_save


def main():
    trials = {}
    for ds_w, sub_w in [("jump_0602", "120_2_120_2"), ("jump_0424", "150_2.2_350_3.5"),
                        ("jump_position_0421", "P90_D0.75_P90_D2")]:
        trials[(ds_w, sub_w)] = next(t_ for t_ in P12._G["trials"]
                                     if t_["ds"] == ds_w and str(t_["sub"]) == sub_w)
    model_f, _ = P.build_flip(X32, V[1], SP)
    print("== 무변속: 창 replay 점수 (행=l_i[mm], 열=pre λ) — 기준: flip 30.00/λ2.25 ==")
    for key, tr in trials.items():
        ref = np.mean(win_scores(model_f, False, 0.030, tr, 2.25))
        print(f"\n[{key[0]}/{key[1]}]  기준(30.00, λ2.25) = {ref:.1f}")
        print(f"{'l_i':>6} | " + " ".join(f"λ={l:<5}" for l in (0.0, 0.75, 1.5, 2.25)))
        for li_mm in (28.2, 28.6, 29.0, 29.4, 29.8):
            model_c, _ = P.build_cvt(X32, V[1], SP, li_mm * 1e-3)
            row = []
            for lam in (0.0, 0.75, 1.5, 2.25):
                sc = win_scores(model_c, True, li_mm * 1e-3, tr, lam)
                row.append(f"{np.mean(sc):7.1f}" if sc else "  실패 ")
            print(f"{li_mm:6.1f} | " + " ".join(row), flush=True)
    print("\n== 0429 Mode A 점수 vs δ (기준 δ=0) ==")
    for dm in (0.0, 0.2, 0.4, 0.6, 1.0, 1.5, 2.0):
        print(f"δ={dm:4.1f}mm → score {sc429(dm):8.2f}", flush=True)


if __name__ == "__main__":
    main()
