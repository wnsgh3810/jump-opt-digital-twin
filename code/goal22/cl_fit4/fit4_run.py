"""cl_fit4 — 게인-적합 v4: tau 채널 제거 + q1·dq2 우선 (사용자 07-09).

fit4에서 tau1/tau2 채널 제거 (fit1처럼 상태만). 채널 가중: q1=3, dq2=3, q2=1, dq1=1.
모델 = P13h 고정, v5 물리 (무클립+a_hat). 게인 4개(log) Nelder-Mead, init=라벨.
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import g22_p10_cl as CL
from g22_p10_pdlaw import SETS, label_gains
from g22_p13_phases import phases

TRAJD = HERE / "traj"; TRAJD.mkdir(exist_ok=True)
OUT = HERE / "fit4_result.json"
CHANNELS = ("q1", "q2", "dq1", "dq2")
CH_W = {"q1": 3.0, "q2": 1.0, "dq1": 1.0, "dq2": 3.0}
PW = {"early": 0.5, "push": 2.0, "flight": 1.0}
RATIO_CLIP = 10.0
BASE = json.load(open(HERE.parent / "p13_phases.json"))


def winit():
    CL.winit()


def seg_score(L, d, on, toff, base):
    t = d["t"]
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - CL.SD, t, d["tau1_paper"])
    tp2 = np.interp(t - CL.SD, t, d["tau2_paper"])
    sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                tau1=g("sh1"), tau2=g("sh2"))
    reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"], tau1=tp1, tau2=tp2)
    segs = dict(early=slice(0, on), push=slice(on, min(toff, len(t))),
                flight=slice(min(toff, len(t)), len(t)))
    tot = wsum = 0.0
    detail = {}
    for sn, sl in segs.items():
        if sl.stop - sl.start < 5 or sn not in base:
            continue
        num = den = 0.0
        detail[sn] = {}
        for ch in CHANNELS:
            b = base[sn].get(ch, np.nan)
            if not np.isfinite(b) or b < 1e-9:
                continue
            rmse = float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2)))
            detail[sn][ch] = rmse
            num += CH_W[ch] * min(rmse / b, RATIO_CLIP)
            den += CH_W[ch]
        if den > 0:
            tot += PW[sn] * (num / den); wsum += PW[sn]
    return tot / max(wsum, 1e-9), detail


def fit_one(args):
    ds, sub = args
    from scipy.optimize import minimize
    if CL._L == {}:
        winit()
    root = SETS[ds][0]
    d = CL.load_trial_xlsx(ds, root, sub)
    on, toff = phases(d)
    base = BASE[f"{ds}/{sub}"]["label"]
    lg = np.array(label_gains(ds, sub))
    ffk = (ds == "jump_0324")
    dqdes = ds in ("jump_0424", "jump_0602")

    def obj(lx):
        g = np.clip(np.exp(lx), 0.02, 800.0)
        L = CL.run_cl(ds, d, g, ffk, dqdes)
        if L is None:
            return 1e6
        s, _ = seg_score(L, d, on, toff, base)
        return s

    r = minimize(obj, np.log(np.maximum(lg, 0.05)), method="Nelder-Mead",
                 options={"maxfev": 160, "xatol": 0.02, "fatol": 0.002})
    gf = np.clip(np.exp(r.x), 0.02, 800.0)
    Lf = CL.run_cl(ds, d, gf, ffk, dqdes)
    sf, det_f = seg_score(Lf, d, on, toff, base)
    m = CL.metrics(ds, d, Lf)
    np.savez(TRAJD / f"{ds}__{sub}__fit4.npz",
             t=Lf["t"], q1=Lf["q1"], q2=Lf["q2"], bz=Lf["bz"],
             dq1=Lf["dq1"], dq2=Lf["dq2"], sh1=Lf["sh1"], sh2=Lf["sh2"],
             grf=Lf["grf"], o=np.array(Lf["o"]))
    return dict(ds=ds, sub=sub, obj=float(sf), gains_label=[float(v) for v in lg],
                gains_fit4=[float(v) for v in gf],
                detail={k: {c: float(x) for c, x in v.items()} for k, v in det_f.items()},
                metrics={k: (float(v) if not isinstance(v, tuple) else [float(u) for u in v])
                         for k, v in m.items()})


def main():
    import multiprocessing as mp
    jobs = [(ds, sub) for ds, (root, subs) in SETS.items() for sub in subs]
    pool = mp.Pool(10, initializer=winit)
    res = {}
    for r in pool.imap_unordered(fit_one, jobs):
        key = f"{r['ds']}/{r['sub']}"
        res[key] = r
        gl, gf = r["gains_label"], r["gains_fit4"]
        print(f"{key}: obj={r['obj']:.3f}  hip {gl[0]:.0f}/{gl[1]:.2f}->{gf[0]:.1f}/{gf[1]:.2f}"
              f"  knee {gl[2]:.0f}/{gl[3]:.2f}->{gf[2]:.1f}/{gf[3]:.2f}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
