"""GOAL21 P4 — joint refit of the friction family WITH the knee Stribeck term
in the loop, against a 6-regime baseline-normalized objective.

Why: hand-tuned (c=3, vs=1) wins big on s2s_gnd/air/0421 but costs jumps +4-5%.
Hypothesis: canonical XML friction (fit WITHOUT the Stribeck term) absorbed part
of it -> double counting. Refit [c, vs, w, c_hip, fc_knee, fv_knee, fc_hip,
fv_hip] jointly; objective = sum_g score_g / baseline_g over
{0421, 0424, 0602, 0324, s2s_gnd, s2s_air} (canonical = 6.0).

Replay-side model (both joints, shared vs/w):
  extra = -c_j * tanh(v_j / w) * exp(-|v_j| / vs)   [Stribeck kinetic branch]

Parallel: one process per regime group (6 workers); MS prep caches per worker.
"""
import os, sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]

PNAMES = ["c", "vs", "w", "c_hip", "fc_knee", "fv_knee", "fc_hip", "fv_hip"]
LO = np.array([0.0, 0.2, 0.04, 0.0, 0.001, 0.001, 0.001, 0.001])
HI = np.array([6.0, 4.0, 0.60, 3.0, 2.5, 0.6, 1.5, 1.5])
# v2 HYBRID objective: window groups alone are GAMEABLE (v1 NM killed viscous +
# huge Stribeck -> all window groups improved 31% yet FULL-stance q2 2.4x worse,
# vto +18%: 0.1s state resets hide slow-bias accumulation). Add full-stance
# jump replay fidelity as first-class groups. Canonical objective = 8.0.
GROUPS = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324", "s2s_gnd", "s2s_air",
          "fs_0424", "fs_0602"]

_G = {}   # per-worker state


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import mshoot as MS
    import sub_sim_iter6v2 as S
    from apply_final_and_regen import apply_final
    ap = apply_final()
    _G.update(mujoco=mujoco, MS=MS, S=S, ap=ap, air=None)


def _replay_windows(model, pp, xd):
    mujoco, MS = _G["mujoco"], _G["MS"]
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    c, vs, w, ch = xd["c"], xd["vs"], xd["w"], xd["c_hip"]
    sc = 0.0
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        if model.nv == 3:
            d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0]]
            d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0]]
        else:
            d.qpos[:] = [pp["q1m"][i0], pp["q2m"][i0]]
            d.qvel[:] = [pp["dq1m"][i0], pp["dq2m"][i0]]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1 = np.empty(nst); q2 = np.empty(nst)
        dq1 = np.empty(nst); dq2 = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            vk = d.qvel[-1]; vh = d.qvel[-2]
            ek = -c * np.tanh(vk / w) * np.exp(-abs(vk) / vs)
            eh = -ch * np.tanh(vh / w) * np.exp(-abs(vh) / vs)
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) + eh,
                         np.interp(tc, t, pp["tau_k"]) + ek]
            try:
                d2 = d
                mujoco.mj_step(model, d2)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1[k] = d.qpos[-2]; q2[k] = d.qpos[-1]
            dq1[k] = d.qvel[-2]; dq2[k] = d.qvel[-1]
        if not ok:
            sc += MS.W_Q * 2.0 + MS.W_DQ * 20.0
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        sc += (MS.W_Q * (r(q1, pp["q1m"]) + r(q2, pp["q2m"]))
               + MS.W_DQ * (r(dq1, pp["dq1m"]) + r(dq2, pp["dq2m"])))
    return sc


def _prep_air_cycles():
    from scipy.signal import savgol_filter
    from mshoot_s2s_air_holdout import load_air_cycles
    MS = _G["MS"]
    out = []
    for td in load_air_cycles():
        t = np.asarray(td["t"])
        k1 = "tau1_real" if "tau1_real" in td else "tau1"
        k2 = "tau2_real" if "tau2_real" in td else "tau2"
        pp = dict(t=t, q1m=-np.asarray(td["q1"]) - np.pi / 2, q2m=-np.asarray(td["q2"]),
                  dq1m=savgol_filter(-np.asarray(td["dq1"]), 11, 3),
                  dq2m=savgol_filter(-np.asarray(td["dq2"]), 11, 3),
                  tau_h=-np.asarray(td[k1]), tau_k=-np.asarray(td[k2]), W=0.1)
        starts = []
        t0 = t[0]
        while t0 < t[-1] - 0.1:
            starts.append(int(np.argmin(np.abs(t - t0))))
            t0 += 0.05                      # air stride 0.05 (matches P3 duels)
        pp["starts"] = starts
        out.append(pp)
    return out


def _stance_range(td, t):
    from scipy.signal import savgol_filter
    grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
    gg = savgol_filter(grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
    st = np.where(gg > 15)[0]
    brk = np.where(np.diff(st) > 3)[0]
    return st[0], (st[brk[0]] if len(brk) else st[-1])


def _fullstance_metric(model, pp, td, xd):
    """Open-loop replay over the whole push-off; W_Q/W_DQ metric on q1,q2,dq1,dq2."""
    mujoco, MS = _G["mujoco"], _G["MS"]
    t = pp["t"]; dt = model.opt.timestep
    i0, ito = _stance_range(td, t)
    d = mujoco.MjData(model)
    d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0]]
    d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0]]
    mujoco.mj_forward(model, d)
    nst = int(round((t[ito] - t[i0]) / dt))
    out = np.empty((nst, 5))
    c, vs, w, ch = xd["c"], xd["vs"], xd["w"], xd["c_hip"]
    for k in range(nst):
        tc = t[i0] + k * dt
        vk = d.qvel[2]; vh = d.qvel[1]
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) - ch * np.tanh(vh / w) * np.exp(-abs(vh) / vs),
                     np.interp(tc, t, pp["tau_k"]) - c * np.tanh(vk / w) * np.exp(-abs(vk) / vs)]
        try:
            mujoco.mj_step(model, d)
        except Exception:
            return MS.W_Q * 2.0 + MS.W_DQ * 20.0
        out[k] = [tc + dt, d.qpos[1], d.qpos[2], d.qvel[1], d.qvel[2]]
    msk = (t >= out[0, 0]) & (t <= out[-1, 0])
    if msk.sum() < 3:
        return 0.0
    r = lambda col, real: float(np.sqrt(np.mean((np.interp(t[msk], out[:, 0], out[:, col]) - real[msk]) ** 2)))
    return (MS.W_Q * (r(1, pp["q1m"]) + r(2, pp["q2m"]))
            + MS.W_DQ * (r(3, pp["dq1m"]) + r(4, pp["dq2m"])))


def eval_group(args):
    group, x = args
    try:
        mujoco, MS, S, ap = _G["mujoco"], _G["MS"], _G["S"], _G["ap"]
        xd = dict(zip(PNAMES, x))
        S.FC_KNEE = xd["fc_knee"]; S.FV_KNEE = xd["fv_knee"]
        S.FC_HIP = xd["fc_hip"]; S.FV_HIP = xd["fv_hip"]
        if group.startswith("fs_"):
            ds = "jump_" + group[3:]
            from load_31exp import list_experiments
            m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
            sc = 0.0
            for d2, sub, isj in list_experiments():
                if d2 == ds:
                    td = MS.LOADERS[ds](sub)
                    sc += _fullstance_metric(m, MS.get_prep((ds, sub), td, m, True), td, xd)
            return group, sc
        if group == "s2s_air":
            if _G["air"] is None:
                _G["air"] = _prep_air_cycles()
            m = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_air_6d(ap["arm_hip"], ap["arm_knee"]))
            return group, sum(_replay_windows(m, pp, xd) for pp in _G["air"])
        if group == "s2s_gnd":
            m = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_gnd_6d(ap["arm_hip"], ap["arm_knee"]))
            cycles, _ = MS.load_s2s_cycles()
            return group, sum(_replay_windows(m, MS.get_prep(("s2s_gnd", ci), td, m, False), xd)
                              for ci, td in enumerate(cycles))
        m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
        if group in MS.LOADERS:
            from load_31exp import list_experiments
            subs = [sub for d2, sub, isj in list_experiments() if d2 == group]
            if not subs:   # 0421 subs not in list_experiments: pull from loader registry
                subs = MS.SUBS_0421 if hasattr(MS, "SUBS_0421") else []
            sc = 0.0
            for sub in subs:
                td = MS.LOADERS[group](sub)
                sc += _replay_windows(m, MS.get_prep((group, sub), td, m, True), xd)
            return group, sc
        for ds, tdir, subs in MS.MARCH:
            if ds == group:
                sc = 0.0
                for sub in subs:
                    td = MS.load_march(tdir, sub)
                    sc += _replay_windows(m, MS.get_prep((ds, sub), td, m, True), xd)
                return group, sc
        return group, 1e9
    except Exception as e:
        return group, 1e9


def main():
    import multiprocessing as mp
    from scipy.optimize import minimize
    log = open(REPO / "code/goal21/stribeck_refit_log.txt", "a", buffering=1)
    pool = mp.Pool(8, initializer=winit)

    def eval_all(x):
        res = dict(pool.map(eval_group, [(g, x) for g in GROUPS]))
        return res

    # TRUE canonical XML friction for THIS stack = goal19_final_model.json friction
    # (fv_hip 0.7129, fv_knee 0.3623, fc_hip 0.0947, fc_knee 0.9884). First refit
    # attempt wrongly used fourbar values -> invalid baseline (jump -29%, s2s +25%).
    FRJ = json.load(open(REPO / "code/goal19/goal19_final_model.json"))["friction"]
    x_can = np.array([0.0, 1.0, 0.15, 0.0, FRJ["fc_knee"], FRJ["fv_knee"], FRJ["fc_hip"], FRJ["fv_hip"]])
    t0 = time.time()
    base = eval_all(x_can)
    print(f"BASE ({time.time()-t0:.0f}s): " + "  ".join(f"{g}:{base[g]:.0f}" for g in GROUPS), flush=True)
    print("BASE expected: 0421 3911 / 0424 7386 / 0602 3861 / 0324 3947 / gnd 8281 / air 207436", flush=True)
    log.write("BASE " + json.dumps(base) + "\n")

    state = {"n": 0, "best": (1e18, None, None)}

    def obj(x):
        xc = np.clip(x, LO, HI)
        pen = 50.0 * float(np.sum(((x - xc) / (HI - LO)) ** 2))
        res = eval_all(xc)
        o = sum(res[g] / base[g] for g in GROUPS) + pen
        state["n"] += 1
        line = (f"ITER {state['n']:3d} obj={o:.4f} " +
                " ".join(f"{n}={v:.4f}" for n, v in zip(PNAMES, xc)) + " | " +
                " ".join(f"{g.split('_')[-1]}:{res[g]/base[g]:.3f}" for g in GROUPS))
        log.write(line + "\n")
        if o < state["best"][0]:
            state["best"] = (o, xc.copy(), res)
            print(f"BEST iter {state['n']}: obj={o:.4f}  " +
                  " ".join(f"{n}={v:.3f}" for n, v in zip(PNAMES, xc)), flush=True)
        return o

    x0 = np.array([3.0, 1.0, 0.15, 0.2, FRJ["fc_knee"], FRJ["fv_knee"], FRJ["fc_hip"], FRJ["fv_hip"]])
    steps = np.array([0.8, 0.35, 0.07, 0.35, 0.35, 0.12, 0.06, 0.20])
    simplex = [x0] + [x0 + np.eye(8)[i] * steps[i] for i in range(8)]
    r = minimize(obj, x0, method="Nelder-Mead",
                 options=dict(initial_simplex=np.array(simplex), maxfev=220,
                              fatol=0.003, xatol=0.005))
    # restart at best (NM shrinkage recovery)
    xb0 = state["best"][1]
    simplex2 = [xb0] + [xb0 + np.eye(8)[i] * steps[i] * 0.35 for i in range(8)]
    r = minimize(obj, xb0, method="Nelder-Mead",
                 options=dict(initial_simplex=np.array(simplex2), maxfev=140,
                              fatol=0.002, xatol=0.003))
    o, xb, res = state["best"]
    out = dict(obj=float(o), obj_canonical=6.0,
               params=dict(zip(PNAMES, map(float, xb))),
               scores={g: float(res[g]) for g in GROUPS},
               base={g: float(base[g]) for g in GROUPS},
               rel={g: float(res[g] / base[g]) for g in GROUPS},
               nfev=state["n"])
    json.dump(out, open(REPO / "code/goal21/stribeck_refit_best.json", "w"), indent=1)
    print("DONE obj=%.4f (canonical 6.0)  saved stribeck_refit_best.json" % o, flush=True)
    print("  " + "  ".join(f"{g}:{res[g]/base[g]:.3f}" for g in GROUPS), flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
