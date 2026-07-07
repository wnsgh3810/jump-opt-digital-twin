"""GOAL21 P6 — free the a_hat actuator-model parameters (user-sanctioned experiment).

Pure Paper FORM is kept (sgn(v), no smoothing — user rule):
  tau = a0 + a1*GR*KT*Iq - a2*GR*|Iq|*Iq - a3*sgn(v) - a4*|Iq|*sgn(v)
Paper values: A = [0, 1.15605006, 4.17389589e-4, 0.26855607, 0.04904241]

We do NOT have raw current columns in the canonical tds, but the stored tau_real
was produced by this exact formula (CSV column verified == recomputation), so Iq
is recovered per sample by Newton inversion (monotonic, slope ~0.95). Then any
candidate a_hat produces new tau arrays instantly — no CSV access, no re-prep
(FK/base prep is tau-independent).

Free params (7): a0, a1, a2 shared (same electrical model both motors);
a3, a4 PER JOINT (friction-like terms; evidence: knee>hip under-read).
Stage A: canonical 26 frozen, fit 7.        (fast)
Stage B: joint CMA 26+7=33, hybrid objective, fs_0324 held-out gate + cand pool.
Judge:  gallery full-replay (q/dq RMSE + h_ratio) canonical vs A vs B-selected.
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
KT, GR = 0.091, 9.0
A_PAPER = np.array([0.0, 1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
AH_NAMES = ["a0", "a1", "a2", "a3_h", "a4_h", "a3_k", "a4_k"]
AH0 = np.array([0.0, 1.15605006, 4.17389589e-4, 0.26855607, 0.04904241, 0.26855607, 0.04904241])
AH_LO = np.array([-0.5, 0.70, 0.0, 0.0, -0.05, 0.0, -0.05])
AH_HI = np.array([0.5, 1.60, 2.5e-3, 0.9, 0.20, 0.9, 0.20])
OBJ_GROUPS = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324",
              "s2s_gnd_0319", "fs_0424", "fs_0602"]
_G = {}


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import mshoot as MS
    import mshoot_fourbar as FB
    import mshoot_fourbar_refit as FR
    from mshoot_dateoff import prep_with_grad, shifted_view
    from scipy.signal import savgol_filter
    _G.update(mujoco=mujoco, MS=MS, FB=FB, FR=FR, pwg=prep_with_grad, sv=shifted_view,
              sg=savgol_filter, trials=None)


def ahat_fwd(Iq, v, a0, a1, a2, a3, a4):
    s = np.sign(v)
    return a0 + a1 * GR * KT * Iq - a2 * GR * np.abs(Iq) * Iq - a3 * s - a4 * np.abs(Iq) * s


def invert_ahat(tau, v):
    """Recover Iq from paper-converted tau (Newton, exact paper params)."""
    a0, a1, a2, a3, a4 = A_PAPER
    s = np.sign(v)
    Iq = (tau - a0 + a3 * s) / (a1 * GR * KT)
    for _ in range(10):
        f = ahat_fwd(Iq, v, *A_PAPER) - tau
        df = a1 * GR * KT - 2 * a2 * GR * np.abs(Iq) - a4 * np.sign(Iq) * s
        Iq = Iq - f / np.clip(df, 0.4, None)
    return Iq


def build_trials():
    """Load all groups once; per trial store prep + inverted Iq + v arrays."""
    FR = _G["FR"]
    mj, mg = FR.get_serial_models()
    trials = []
    err_max = 0.0
    for ds, subs, loader, isj in FR.all_groups():
        for sub in subs:
            td = loader(sub)
            pp = _G["pwg"]((ds, sub), td, mj if isj else mg)
            v1 = np.asarray(td["dq1"], dtype=float); v2 = np.asarray(td["dq2"], dtype=float)
            t1 = np.asarray(td["tau1_real"], dtype=float); t2 = np.asarray(td["tau2_real"], dtype=float)
            Iq1 = invert_ahat(t1, v1); Iq2 = invert_ahat(t2, v2)
            err_max = max(err_max,
                          float(np.max(np.abs(ahat_fwd(Iq1, v1, *A_PAPER) - t1))),
                          float(np.max(np.abs(ahat_fwd(Iq2, v2, *A_PAPER) - t2))))
            trials.append(dict(ds=ds, sub=sub, isj=isj, pp=pp, td=td,
                               Iq1=Iq1, Iq2=Iq2, v1=v1, v2=v2))
    _G["trials"] = trials
    return err_max


def tau_view(tr, ah):
    """pp copy with tau recomputed under candidate a_hat (mujoco frame = negated)."""
    a0, a1, a2, a3h, a4h, a3k, a4k = ah
    t1 = ahat_fwd(tr["Iq1"], tr["v1"], a0, a1, a2, a3h, a4h)
    t2 = ahat_fwd(tr["Iq2"], tr["v2"], a0, a1, a2, a3k, a4k)
    return dict(tr["pp"], tau_h=-t1, tau_k=-t2), t1, t2


def _stance_range(td, t):
    grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
    gg = _G["sg"](grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
    st = np.where(gg > 15)[0]
    if len(st) < 10:
        return None
    brk = np.where(np.diff(st) > 3)[0]
    return st[0], (st[brk[0]] if len(brk) else st[-1])


def _fs_metric(model, pp, td):
    mujoco, MS = _G["mujoco"], _G["MS"]
    t = pp["t"]
    rng = _stance_range(td, t)
    if rng is None:
        return 0.0
    i0, i1 = rng
    if t[i1] - t[i0] < 0.1:
        return 0.0
    d = mujoco.MjData(model)
    q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
    d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
    d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
    mujoco.mj_forward(model, d)
    dt = model.opt.timestep
    nst = int(round((t[i1] - t[i0]) / dt))
    out = np.empty((nst, 5))
    for k in range(nst):
        tc = t[i0] + k * dt
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
        try:
            mujoco.mj_step(model, d)
        except Exception:
            return MS.W_Q * 2.0 + MS.W_DQ * 20.0
        out[k] = [tc + dt, d.qpos[1], d.qpos[2], d.qvel[1], d.qvel[2]]
    if not np.all(np.isfinite(out)):
        return MS.W_Q * 2.0 + MS.W_DQ * 20.0
    msk = (t >= out[0, 0]) & (t <= out[-1, 0])
    if msk.sum() < 3:
        return 0.0
    r = lambda c, real: float(np.sqrt(np.mean((np.interp(t[msk], out[:, 0], out[:, c]) - real[msk]) ** 2)))
    return (MS.W_Q * (r(1, pp["q1m"]) + r(2, pp["q2m"]))
            + MS.W_DQ * (r(3, pp["dq1m"]) + r(4, pp["dq2m"])))


def eval_hybrid(args):
    """args = (x26, ah7). Returns per-group scores incl fs_0324."""
    try:
        x26, ah = args
        FR, FB, MS, mujoco = _G["FR"], _G["FB"], _G["MS"], _G["mujoco"]
        if _G["trials"] is None:
            build_trials()
        import sub_sim_iter6v2 as S
        dd = dict(zip(FR.NAMES, x26))
        S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
        S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(dd["arm_knee"], dd))
        res = {}
        for tr in _G["trials"]:
            ds = tr["ds"]
            k1, k2 = FR.OFFKEY.get(ds, (None, None))
            o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
            ppv, _, _ = tau_view(tr, ah)
            ppo = _G["sv"](ppv, o1, o2)
            res[ds] = res.get(ds, 0.0) + MS.window_score(FB.eval_windows_fourbar(model, ppo))
            if ds in ("jump_0424", "jump_0602", "jump_0324"):
                fsk = "fs_" + ds.split("_")[-1]
                res[fsk] = res.get(fsk, 0.0) + _fs_metric(model, ppo, tr["td"])
        return res
    except Exception:
        return None


def main():
    import multiprocessing as mp
    import cma
    winit()
    err = build_trials()
    print(f"[sanity] inversion max |tau_recon - tau_stored| = {err:.2e} Nm "
          f"({'PASS' if err < 1e-6 else 'CHECK'})", flush=True)
    FR = _G["FR"]
    can = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    x_can = np.array(can["x"]); NAMES = can["names"]
    pool = mp.Pool(10, initializer=winit)
    log = open(REPO / "code/goal21/ahat_refit_log.txt", "a", buffering=1)

    base = eval_hybrid((x_can, AH0))
    print("BASE(paper):", " ".join(f"{k}:{v:.0f}" for k, v in base.items()), flush=True)
    print("BASE expect: 0421 2992 / 0424 3422 / 0602 2733 / 0324 1696 / s2s 4142 / fs 1360 577 488", flush=True)
    log.write("BASE " + json.dumps(base) + "\n")

    def obj_of(r):
        return 99.0 if r is None else sum(r[g] / base[g] for g in OBJ_GROUPS)

    # ---- Stage A: a_hat only (canonical 26 frozen) --------------------------
    esA = cma.CMAEvolutionStrategy(((AH0 - AH_LO) / (AH_HI - AH_LO)).tolist(), 0.12,
                                   {"bounds": [0, 1], "maxfevals": 360, "popsize": 12,
                                    "seed": 11, "verbose": -9})
    bestA = dict(obj=7.0, ah=[float(v) for v in AH0], res=base)
    nev = 0
    while not esA.stop():
        sols = esA.ask()
        ahs = [AH_LO + np.array(s) * (AH_HI - AH_LO) for s in sols]
        results = pool.map(eval_hybrid, [(x_can, ah) for ah in ahs])
        objs = [obj_of(r) for r in results]
        for ah, r, o in zip(ahs, results, objs):
            nev += 1
            if r is not None:
                log.write(f"A {nev} obj={o:.4f} " +
                          " ".join(f"{n}={v:.4f}" for n, v in zip(AH_NAMES, ah)) +
                          f" ho:{r['fs_0324']/base['fs_0324']:.3f}\n")
            if o < bestA["obj"]:
                bestA = dict(obj=float(o), ah=[float(v) for v in ah],
                             res={k: float(v) for k, v in r.items()})
                print(f"A-BEST nev={nev} obj={o:.4f} ho={r['fs_0324']/base['fs_0324']:.3f}  " +
                      " ".join(f"{n}={v:.3f}" for n, v in zip(AH_NAMES, ah)), flush=True)
        esA.tell(sols, objs)
    json.dump(dict(bestA, base=base, names=AH_NAMES),
              open(REPO / "code/goal21/ahat_stageA.json", "w"), indent=1)
    print(f"STAGE-A DONE obj={bestA['obj']:.4f} (paper 7.0)", flush=True)

    # ---- Stage B: joint 26+7 ------------------------------------------------
    LOb = np.concatenate([FR.LOb, AH_LO]); HIb = np.concatenate([FR.HIb, AH_HI])
    x0 = np.concatenate([x_can, np.array(bestA["ah"])])
    esB = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.08,
                                   {"bounds": [0, 1], "maxfevals": 1200, "popsize": 20,
                                    "seed": 13, "verbose": -9})
    cand = open(REPO / "code/goal21/ahat_cands.jsonl", "w", buffering=1)
    bestB = dict(obj=bestA["obj"], x=x0.tolist(), res=bestA["res"])
    t0 = time.time()
    while not esB.stop():
        sols = esB.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        results = pool.map(eval_hybrid, [(x[:26], x[26:]) for x in xs])
        objs = [obj_of(r) for r in results]
        for x, r, o in zip(xs, results, objs):
            nev += 1
            if r is not None:
                ho = r["fs_0324"] / base["fs_0324"]
                log.write(f"B {nev} obj={o:.4f} ho:{ho:.3f}\n")
                if o < 7.0 and ho <= 1.05:
                    cand.write(json.dumps(dict(obj=float(o), heldout=float(ho),
                                               x=[float(v) for v in x])) + "\n")
            if o < bestB["obj"]:
                bestB = dict(obj=float(o), x=[float(v) for v in x],
                             res={k: float(v) for k, v in r.items()})
                print(f"B-BEST nev={nev} obj={o:.4f} ho={r['fs_0324']/base['fs_0324']:.3f} "
                      f"[{(time.time()-t0)/60:.0f}min]", flush=True)
        esB.tell(sols, objs)
    json.dump(dict(bestB, base=base, names=NAMES + AH_NAMES),
              open(REPO / "code/goal21/ahat_stageB.json", "w"), indent=1)
    print(f"STAGE-B DONE obj={bestB['obj']:.4f} (paper-canonical 7.0)", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
