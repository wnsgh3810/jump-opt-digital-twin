# -*- coding: utf-8 -*-
"""P19 커맨드 층 — 세션별 실효 게인 스케일 α 적합 (데이터 전용, sim 없음).
모델: c = αp·kp·e + αd·kd·ė → 1차 지연(tm=8ms) → clip ±35.5 → a_hat(Paper).
0324(held-out)는 라벨 유지. 지표 v3 (관절 합산 정규화)."""
import sys, json
import numpy as np
from pathlib import Path
from scipy.optimize import minimize

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P

TM = 0.008
CLIP = 35.5


def lag(u, t, tm):
    if tm <= 0:
        return u
    y = np.empty_like(u); y[0] = u[0]
    for k in range(1, len(u)):
        dt = t[k] - t[k - 1]
        y[k] = y[k - 1] + (dt / max(tm, dt)) * (u[k] - y[k - 1])
    return y


def trials_by_session():
    from cvt_core import load_0429, label_gains_429, SUBS429
    J = P.J
    out = {}
    for tr in J._P["cl"]:
        d = tr["d"]
        dqd1 = d["dqd1"] if tr["dqdes"] else np.zeros_like(d["t"])
        dqd2 = d["dqd2"] if tr["dqdes"] else np.zeros_like(d["t"])
        tend = min(d["t"][-1], d["t"][min(tr["toff"], len(d["t"]) - 1)] + 0.1)
        out.setdefault(tr["ds"], []).append(
            (d, tr["gains"], dqd1, dqd2, d["t"] <= tend, tr["ffk"]))
    for sub in SUBS429:
        d = load_0429(sub)
        g = d["grf_real"]; pk = int(np.argmax(g))
        below = np.where(g[pk:] < 0.02 * g[pk])[0]
        toff = d["t"][pk + below[0]] if len(below) else d["t"][-1]
        z = np.zeros_like(d["t"])
        out.setdefault("jump_0429", []).append(
            (d, label_gains_429(sub), z, z, d["t"] <= min(d["t"][-1], toff + 0.1), False))
    return out


def sess_gap(trs, al):
    ap1, ad1, ap2, ad2 = al
    A = P.A_PAPER; J = P.J
    gs = []
    for d, gains, dqd1, dqd2, m, ffk in trs:
        kp1, kd1, kp2, kd2 = gains
        t = d["t"]
        c1 = ap1 * kp1 * (d["qd1"] - d["q1"]) + ad1 * kd1 * (dqd1 - d["dq1"])
        c2 = ap2 * kp2 * (d["qd2"] - d["q2"]) + ad2 * kd2 * (dqd2 - d["dq2"])
        if ffk:
            c2 = c2 + d["tdes2"]
        c1 = np.clip(lag(c1, t, TM), -CLIP, CLIP)
        c2 = np.clip(lag(c2, t, TM), -CLIP, CLIP)
        s1 = J.ahat(A, c1, d["dq1"]); s2 = J.ahat(A, c2, d["dq2"])
        tp1 = np.interp(t - P.SD, t, J.ahat(A, d["traw1"], d["dq1"]))
        tp2 = np.interp(t - P.SD, t, J.ahat(A, d["traw2"], d["dq2"]))
        num = np.sqrt(np.mean((s1 - tp1)[m] ** 2) + np.mean((s2 - tp2)[m] ** 2))
        den = max(np.sqrt(np.mean(tp1[m] ** 2) + np.mean(tp2[m] ** 2)), 0.5)
        gs.append(num / den)
    return float(np.mean(gs))


def main():
    P.winit()
    T = trials_by_session()
    alphas = {}
    for ds, trs in sorted(T.items()):
        if ds == "jump_0324":
            g0 = sess_gap(trs, [1, 1, 1, 1])
            print(f"[{ds:20s}] held-out, 라벨 유지 gap {100*g0:.1f}%", flush=True)
            alphas[ds] = [1.0, 1.0, 1.0, 1.0]
            continue
        g0 = sess_gap(trs, [1, 1, 1, 1])
        best = (g0, np.array([1.0, 1.0, 1.0, 1.0]))
        for x0 in ([1, 0.4, 1, 0.4], [0.7, 0.3, 0.9, 0.6], [1.3, 0.6, 1.1, 0.8]):
            r = minimize(lambda v: sess_gap(trs, np.clip(v, [0.3, 0.05, 0.3, 0.05],
                                                         [2.0, 1.6, 2.0, 1.6])),
                         x0, method="Nelder-Mead",
                         options=dict(maxfev=120, xatol=1e-3, fatol=1e-4))
            if r.fun < best[0]:
                best = (r.fun, np.clip(r.x, [0.3, 0.05, 0.3, 0.05], [2.0, 1.6, 2.0, 1.6]))
        alphas[ds] = [float(v) for v in best[1]]
        print(f"[{ds:20s}] gap {100*g0:.1f}% -> {100*best[0]:.1f}%  "
              f"a=[{best[1][0]:.2f},{best[1][1]:.2f},{best[1][2]:.2f},{best[1][3]:.2f}]",
              flush=True)
    json.dump(dict(TM=TM, CLIP=CLIP, alphas=alphas),
              open(HERE / "p19_cmdlayer.json", "w"), indent=1)
    print("saved p19_cmdlayer.json", flush=True)


if __name__ == "__main__":
    main()
