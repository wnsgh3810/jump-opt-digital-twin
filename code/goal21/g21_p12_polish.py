"""P12 — flipped-phase polish + axis re-validation on the NEW structure.

Stage A: refit 26 params with h-AUGMENTED hybrid objective:
  groups = windows x5 + full-stance x2 (0424/0602) + habs (ballistic apex error
  from fs takeoff state, 0424+0602) -> reference obj = 8.0 at x_ref (P10-selected).
  held-out gate = fs_0324 (traces). h uses apex = bz_to + max(vbz_to,0)^2/2g.

Stage B: on Stage-A winner, 1-D re-sweeps of historical + new axes (the phase
change invalidates all old drop-tests; Stribeck-as-structure-proxy precedent):
  connect_solref (loop compliance — NEVER tuned, hardcoded 0.0008s),
  arm_hip (hip rotor inertia — was 0 in every fit; same motor as knee!),
  motor_tm (input LPF), sens_delay (tau vs q timeline shift),
  strib_knee (ctrl-side Stribeck — rejected on WRONG phase, retry),
  foot_dz (foot position offset along calf), mu_floor.
KEEP rule: obj >=2% better AND heldout <=1.02.
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
_G = {}
GJ = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]
OBJ_GROUPS = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
OFFKEY = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
          "jump_0424": ("o1_0424", "o2_0424"), "s2s_gnd_0319": ("o1_0319", "o2_0319")}
GKEY = {"jump_position_0421": "w_0421", "jump_0424": "w_0424", "jump_0602": "w_0602",
        "jump_0324": "w_0324", "s2s_gnd_0319": "w_s2s"}


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal21"))
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import g21_fourbar_flip as FL
    FL.winit()
    import mshoot as MS
    import mshoot_fourbar_refit as FR
    from mshoot_dateoff import prep_with_grad, shifted_view
    from scipy.signal import savgol_filter
    _G.update(mujoco=mujoco, FL=FL, S=FL._G["S"], FB=FL._G["FB"], MS=MS, FR=FR,
              pwg=prep_with_grad, sv=shifted_view, sg=savgol_filter, trials=None)


def build_trials():
    FR, MS = _G["FR"], _G["MS"]
    mj, mg = FR.get_serial_models()
    T = []
    for ds, subs, loader, isj in FR.all_groups():
        for sub in subs:
            td = loader(sub)
            pp = _G["pwg"]((ds, sub), td, mj if isj else mg)
            hr = float(td.get("h_real", np.nan)) if isj else np.nan
            T.append(dict(ds=ds, sub=sub, isj=isj, pp=pp, td=td, h_real=hr))
    _G["trials"] = T


def mod_tau(pp, t, mods):
    """Replay-side input mods: motor_tm LPF + sensor delay. Returns pp view."""
    tm = mods.get("motor_tm", 0.0); dly = mods.get("sens_delay", 0.0)
    if tm <= 0 and dly == 0:
        return pp
    th, tk = np.asarray(pp["tau_h"]), np.asarray(pp["tau_k"])
    if dly != 0:
        th = np.interp(t - dly, t, th); tk = np.interp(t - dly, t, tk)
    if tm > 0:
        dt = np.median(np.diff(t)); a = dt / (tm + dt)
        f1 = np.copy(th); f2 = np.copy(tk)
        for i in range(1, len(t)):
            f1[i] = f1[i - 1] + a * (th[i] - f1[i - 1])
            f2[i] = f2[i - 1] + a * (tk[i] - f2[i - 1])
        th, tk = f1, f2
    return dict(pp, tau_h=th, tau_k=tk)


def knee_extra(mods):
    c = mods.get("strib_knee", 0.0)
    if c <= 0:
        return None
    return lambda v: -c * np.tanh(v / 0.3) * np.exp(-abs(v) / 1.0)


def eval_windows(model, pp, extra):
    mujoco, MS = _G["mujoco"], _G["MS"]
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    sc = 0.0
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            ek = extra(d.qvel[2]) if extra else 0.0
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"]) + ek]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            sc += MS.W_Q * 2.0 + MS.W_DQ * 20.0
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        sc += (MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
               + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"])))
    return sc


def stance_range(td, t):
    grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
    gg = _G["sg"](grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
    st = np.where(gg > 15)[0]
    if len(st) < 10:
        return None
    brk = np.where(np.diff(st) > 3)[0]
    return st[0], (st[brk[0]] if len(brk) else st[-1])


def fs_metric(model, pp, td, extra):
    """Full push-off replay -> (trace score, apex h prediction)."""
    mujoco, MS = _G["mujoco"], _G["MS"]
    t = pp["t"]
    rng = stance_range(td, t)
    if rng is None:
        return 0.0, np.nan
    i0, i1 = rng
    if t[i1] - t[i0] < 0.1:
        return 0.0, np.nan
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
        ek = extra(d.qvel[2]) if extra else 0.0
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"]) + ek]
        try:
            mujoco.mj_step(model, d)
        except Exception:
            return MS.W_Q * 2.0 + MS.W_DQ * 20.0, np.nan
        out[k] = [tc + dt, d.qpos[1], d.qpos[2], d.qvel[1], d.qvel[2]]
    if not np.all(np.isfinite(out)):
        return MS.W_Q * 2.0 + MS.W_DQ * 20.0, np.nan
    h_pred = float(d.qpos[0]) + max(float(d.qvel[0]), 0.0) ** 2 / (2 * 9.81)
    msk = (t >= out[0, 0]) & (t <= out[-1, 0])
    if msk.sum() < 3:
        return 0.0, h_pred
    r = lambda c, real: float(np.sqrt(np.mean((np.interp(t[msk], out[:, 0], out[:, c]) - real[msk]) ** 2)))
    sc = (MS.W_Q * (r(1, pp["q1m"]) + r(2, pp["q2m"]))
          + MS.W_DQ * (r(3, pp["dq1m"]) + r(4, pp["dq2m"])))
    return sc, h_pred


def apply_xml_mods(xml, mods):
    cs = mods.get("connect_solref", 0.0008)
    if cs != 0.0008:
        xml = xml.replace('solref="0.0008 1"', f'solref="{cs:.6f} 1"')
    ah = mods.get("arm_hip", 0.0)
    if ah > 0:
        xml = xml.replace('name="hip" type="hinge" armature="0"',
                          f'name="hip" type="hinge" armature="{ah:.8f}"')
    fdz = mods.get("foot_dz", 0.0)
    if fdz != 0.0:
        xml = xml.replace('pos="0 0 -0.25" euler="90 0 0"',
                          f'pos="0 0 -{0.25 + fdz:.4f}" euler="90 0 0"')
    mu = mods.get("mu_floor", 0.0)
    if mu > 0:
        xml = xml.replace("1.00000 0.02000 0.01000", f"{mu:.5f} 0.02000 0.01000")
    return xml


def eval_p12(args):
    """returns group dict incl fs_0324 + habs; None on failure."""
    try:
        x, mods = args
        if _G["trials"] is None:
            build_trials()
        mujoco, FL, S, FR, MS = _G["mujoco"], _G["FL"], _G["S"], _G["FR"], _G["MS"]
        dd = dict(zip(FR.NAMES, x))
        S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
        S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        xml = apply_xml_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], dd), mods)
        model = mujoco.MjModel.from_xml_string(xml)
        extra = knee_extra(mods)
        res = {"habs": 0.0}
        for tr in _G["trials"]:
            ds = tr["ds"]
            k1, k2 = OFFKEY.get(ds, (None, None))
            o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
            ppv = mod_tau(tr["pp"], tr["pp"]["t"], mods)
            ppo = _G["sv"](ppv, o1, o2)
            res[GKEY[ds]] = res.get(GKEY[ds], 0.0) + eval_windows(model, ppo, extra)
            if ds in ("jump_0424", "jump_0602", "jump_0324"):
                fsk = "fs_" + ds.split("_")[-1]
                sc, h_pred = fs_metric(model, ppo, tr["td"], extra)
                res[fsk] = res.get(fsk, 0.0) + sc
                if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr["h_real"]):
                    res["habs"] += abs(h_pred - tr["h_real"])
        return res
    except Exception:
        return None


AXES = {
    "connect_solref": [0.0003, 0.002, 0.005, 0.012],
    "arm_hip": [0.001, 0.0035, 0.008],
    "motor_tm": [0.004, 0.008, 0.016],
    "sens_delay": [-0.004, -0.002, 0.002, 0.004],
    "strib_knee": [1.0, 2.0, 3.0],
    "foot_dz": [-0.005, 0.005, 0.010],
    "mu_floor": [0.6, 1.5],
}


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = _G["FR"]
    ref = json.load(open(REPO / "code/goal21/fourbar_flip_canonical.json"))
    x_ref = np.array(ref["x"]); NAMES = ref["names"]
    pool = mp.Pool(10, initializer=winit)
    base = eval_p12((x_ref, {}))
    print("BASE(P10-selected, flipped):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        if r is None:
            return 99.0, 99.0
        o = sum(r[g] / base[g] for g in OBJ_GROUPS)
        return o, r["fs_0324"] / base["fs_0324"]

    LOb, HIb = FR.LOb, FR.HIb
    es = cma.CMAEvolutionStrategy(((x_ref - LOb) / (HIb - LOb)).tolist(), 0.06,
                                  {"bounds": [0, 1], "maxfevals": 1200, "popsize": 20,
                                   "seed": 31, "verbose": -9})
    cands = []
    best = dict(obj=8.0, ho=1.0, x=x_ref.tolist(), res=base)
    nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval_p12, [(x, {}) for x in xs])
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.05:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x],
                                  habs=float(r["habs"] / base["habs"])))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x],
                            res={k: float(v) for k, v in r.items()})
                print(f"A-BEST nev={nev} obj={o:.4f} ho={ho:.3f} habs={r['habs']/base['habs']:.3f} "
                      f"[{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    xsel = np.array(sel["x"]) if sel else x_ref
    print(f"STAGE-A done nev={nev}: selected obj={sel['obj']:.4f} ho={sel['ho']:.3f} "
          f"habs={sel['habs']:.3f}" if sel else "STAGE-A: none passed; keep x_ref", flush=True)
    json.dump(dict(selected=sel, names=NAMES, base={k: float(v) for k, v in base.items()}),
              open(REPO / "code/goal21/p12_stageA.json", "w"), indent=1)

    # Stage B — axis sweeps on xsel
    baseB = eval_p12((xsel, {}))
    print("\nSTAGE-B axis re-validation (ref obj=8.0 at Stage-A winner):", flush=True)
    rows = {}
    for ax, vals in AXES.items():
        args = [(xsel, {ax: v}) for v in vals]
        rs = pool.map(eval_p12, args)
        for v, r in zip(vals, rs):
            if r is None:
                print(f"  {ax}={v}: CRASH", flush=True)
                continue
            o = sum(r[g] / baseB[g] for g in OBJ_GROUPS)
            ho = r["fs_0324"] / baseB["fs_0324"]
            keep = "KEEP?" if (o < 7.84 and ho <= 1.02) else ""
            rows.setdefault(ax, []).append(dict(v=v, obj=float(o), ho=float(ho),
                                                habs=float(r["habs"] / baseB["habs"])))
            print(f"  {ax}={v}: obj={o:.4f} ho={ho:.3f} habs={r['habs']/baseB['habs']:.3f} {keep}", flush=True)
    json.dump(dict(stageA=sel, axes=rows, baseB={k: float(v) for k, v in baseB.items()}),
              open(REPO / "code/goal21/p12_axes.json", "w"), indent=1)
    print("P12 DONE — saved p12_stageA.json / p12_axes.json", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
