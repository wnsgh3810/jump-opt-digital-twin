"""cl_p14 + fit3 — P14 모델·a_hat 위에서 q1/dq2 우선 게인 적합.

목적식 = fit3와 동일: 구간(초0.5/푸시2/비행1) × 채널 정규화(기준 = P14 label 런),
채널 가중 q1=3, dq2=3, q2=dq1=tau1=tau2=1 (τ 채널 유지 = 널-드리프트 감시).
실측 τ 참조 = P14 a_hat 변환 (−1.5ms). 게인 4개 log NM, init=라벨.
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from g22_p10_pdlaw import SETS, label_gains
from g22_p10_cl import load_trial_xlsx, SD
from g22_p13_phases import phases
from run_all import run_cl_p14, metrics, X, A, OLD, DST, TRAJD

CHANNELS = ("q1", "q2", "dq1", "dq2", "tau1", "tau2")
CH_W = {"q1": 3.0, "q2": 1.0, "dq1": 1.0, "dq2": 3.0, "tau1": 1.0, "tau2": 1.0}
PW = {"early": 0.5, "push": 2.0, "flight": 1.0}
RATIO_CLIP = 10.0
OUT = HERE / "fit3_result.json"
(DST / "png_fit3").mkdir(exist_ok=True)
(DST / "gif_fit3").mkdir(exist_ok=True)
_G = {}


def winit():
    J.winit()
    _G["model"], _G["dd"] = J.build_model(X[:32])


def seg_detail(L, d, on, toff):
    t = d["t"]
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, d["tau1_p14"]); tp2 = np.interp(t - SD, t, d["tau2_p14"])
    sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                tau1=g("sh1"), tau2=g("sh2"))
    reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"], tau1=tp1, tau2=tp2)
    segs = dict(early=slice(0, on), push=slice(on, min(toff, len(t))),
                flight=slice(min(toff, len(t)), len(t)))
    out = {}
    for sn, sl in segs.items():
        if sl.stop - sl.start < 5:
            continue
        out[sn] = {ch: float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2)))
                   for ch in CHANNELS}
    return out


def score_from(det, base):
    tot = wsum = 0.0
    for sn in det:
        if sn not in base:
            continue
        num = den = 0.0
        for ch in CHANNELS:
            b = base[sn].get(ch, np.nan)
            if not np.isfinite(b) or b < 1e-9:
                continue
            num += CH_W[ch] * min(det[sn][ch] / b, RATIO_CLIP)
            den += CH_W[ch]
        if den > 0:
            tot += PW[sn] * (num / den); wsum += PW[sn]
    return tot / max(wsum, 1e-9)


def fit_one(args):
    ds, sub = args
    from scipy.optimize import minimize
    if not _G:
        winit()
    model, dd = _G["model"], _G["dd"]
    d = load_trial_xlsx(ds, SETS[ds][0], sub)
    d["tau1_p14"] = J.ahat(A, d["traw1"], d["dq1"])
    d["tau2_p14"] = J.ahat(A, d["traw2"], d["dq2"])
    on, toff = phases(d)
    lg = np.array(label_gains(ds, sub))
    ffk = (ds == "jump_0324"); dqdes = ds in ("jump_0424", "jump_0602")
    L0 = run_cl_p14(model, dd, ds, d, lg, ffk, dqdes)
    base = seg_detail(L0, d, on, toff)

    def obj(lx):
        g = np.clip(np.exp(lx), 0.02, 800.0)
        L = run_cl_p14(model, dd, ds, d, g, ffk, dqdes)
        if L is None:
            return 1e6
        return score_from(seg_detail(L, d, on, toff), base)

    r = minimize(obj, np.log(np.maximum(lg, 0.05)), method="Nelder-Mead",
                 options={"maxfev": 160, "xatol": 0.02, "fatol": 0.002})
    gf = np.clip(np.exp(r.x), 0.02, 800.0)
    Lf = run_cl_p14(model, dd, ds, d, gf, ffk, dqdes)
    det = seg_detail(Lf, d, on, toff)
    hr = (OLD.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real", float("nan"))
    m = metrics(ds, d, Lf, hr)
    np.savez(TRAJD / f"{ds}__{sub}__p14fit3.npz",
             t=Lf["t"], q1=Lf["q1"], q2=Lf["q2"], bz=Lf["bz"],
             dq1=Lf["dq1"], dq2=Lf["dq2"], sh1=Lf["sh1"], sh2=Lf["sh2"],
             grf=Lf["grf"], o=np.array(Lf["o"]))
    return dict(ds=ds, sub=sub, obj=float(score_from(det, base)),
                gains_label=[float(v) for v in lg], gains_fit3=[float(v) for v in gf],
                detail=det, base=base, metrics=m)


def main():
    import multiprocessing as mp
    jobs = [(ds, sub) for ds, (root, subs) in SETS.items() for sub in subs]
    pool = mp.Pool(10, initializer=winit)
    res = {}
    for r in pool.imap_unordered(fit_one, jobs):
        key = f"{r['ds']}/{r['sub']}"
        res[key] = r
        gl, gf = r["gains_label"], r["gains_fit3"]
        print(f"{key}: obj={r['obj']:.3f}  hip {gl[0]:.0f}/{gl[1]:.2f}->{gf[0]:.1f}/{gf[1]:.2f}"
              f"  knee {gl[2]:.0f}/{gl[3]:.2f}->{gf[2]:.1f}/{gf[3]:.2f}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("\n=== push 지표 중앙값 (P14 label -> P14 fit3) ===", flush=True)
    for ds in SETS:
        ks = [k for k in res if k.startswith(ds + "/")]
        if not ks:
            continue
        line = f"[{ds}] "
        for ch in ("q1", "dq2", "tau1", "tau2"):
            lab = np.median([res[k]["base"]["push"][ch] for k in ks if "push" in res[k]["base"]])
            f3 = np.median([res[k]["detail"]["push"][ch] for k in ks if "push" in res[k]["detail"]])
            line += f"{ch} {lab:.3f}->{f3:.3f}  "
        print(line, flush=True)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
