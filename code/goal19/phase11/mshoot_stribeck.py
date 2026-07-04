"""G20-C — Stribeck (velocity-dependent) friction on the four-bar model.

Constant Coulomb failed historically (-49%, kills jump propulsion); the untried form is
Stribeck: high static/low-speed friction that vanishes at speed. Injected in the eval
loop as smooth torque (XML frictionloss=0 on hip/crank):
    tau_fric = -(fc + (fs-fc)*exp(-(|v|/vs)^2)) * tanh(v/0.02)
Fit ONLY friction-related params (fv_hip, fv_knee + 6 Stribeck) on top of the frozen
four-bar round-2 best. Keep if > 2% window gain AND physical; else drop.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR
from mshoot_dateoff import prep_with_grad, shifted_view

OUT = REPO / "code/goal19/phase11/stribeck_best.json"
BASEJ = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BASEJ["names"], BASEJ["x"]))


def build_model(bd, zero_fl=True):
    S.FV_HIP = bd["fv_hip"]; S.FV_KNEE = bd["fv_knee"]
    S.FC_HIP = 0.0 if zero_fl else bd["fc_hip"]
    S.FC_KNEE = 0.0 if zero_fl else bd["fc_knee"]
    S.SOLREF_TC_LOCK = bd["solref_tc"]; S.IMP0_LOCK = bd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = bd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(bd["arm_knee"], bd))


def fric(v, fc, fs, vs):
    return -(fc + (fs - fc) * np.exp(-(abs(v) / max(vs, 1e-3)) ** 2)) * np.tanh(v / 0.02)


def eval_windows_stb(model, pp, fp):
    """fp = [fc_h, fs_h, vs_h, fc_k, fs_k, vs_k]"""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
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
            th = np.interp(tc, t, pp["tau_h"]) + fric(d.qvel[1], fp[0], fp[1], fp[2])
            tk = np.interp(tc, t, pp["tau_k"]) + fric(d.qvel[2], fp[3], fp[4], fp[5])
            d.ctrl[:] = [th, tk]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1a, pp["q1m"]), rq2=r(q2a, pp["q2m"]),
                        rdq1=r(dq1a, pp["dq1m"]), rdq2=r(dq2a, pp["dq2m"])))
    return out


def evaluate(x, model):
    """x = [fv_hip, fv_knee, fc_h, fs_h, vs_h, fc_k, fs_k, vs_k] — fv changes need rebuild."""
    bd = dict(BD); bd["fv_hip"] = x[0]; bd["fv_knee"] = x[1]
    m = build_model(bd)
    mj, mg = FR.get_serial_models()
    groups = FR.all_groups()
    total = 0.0
    for ds, subs, loader, isj in groups:
        k1, k2 = FR.OFFKEY.get(ds, (None, None))
        o1 = BD[k1] if k1 else 0.0; o2 = BD[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            wins = eval_windows_stb(m, shifted_view(pp, o1, o2), x[2:])
            total += MS.window_score(wins)
    return total


def main():
    import cma
    # reference: round-2 best WITH its XML frictionloss (no Stribeck)
    ref, _ = FR.evaluate(np.array(BASEJ["x"]))
    print(f"REF (fourbar best, XML Coulomb): {ref:.0f}", flush=True)
    # warm: Stribeck fc = XML fc values, fs = 2x, vs = 0.3
    x0 = np.array([BD["fv_hip"], BD["fv_knee"], BD["fc_hip"], 2 * BD["fc_hip"] + 0.1, 0.3,
                   BD["fc_knee"], 2 * BD["fc_knee"] + 0.1, 0.3])
    lo = np.array([0.0, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.01])
    hi = np.array([1.5, 0.8, 0.8, 3.0, 2.0, 0.8, 3.0, 2.0])
    m0 = build_model(dict(BD))
    o0 = evaluate(x0, m0)
    print(f"WARM Stribeck: {o0:.0f}", flush=True)
    x0n = (np.clip(x0, lo, hi) - lo) / (hi - lo)
    es = cma.CMAEvolutionStrategy(x0n, 0.25, {"bounds": [0, 1], "maxfevals": 150,
                                              "popsize": 10, "seed": 29, "verbose": -9})
    best = dict(obj=float(min(o0, ref)), x=[float(v) for v in x0])
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = lo + np.array(sn) * (hi - lo)
            o = evaluate(x, m0)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), x=[float(v) for v in x])
                json.dump(best, open(OUT, "w"), indent=2)
        es.tell(sols, objs)
        print(f"best={best['obj']:.0f}", flush=True)
    gain = 100 * (best["obj"] / ref - 1)
    print(f"\nRESULT: ref {ref:.0f} -> {best['obj']:.0f} ({gain:+.1f}%)")
    lab = ["fv_hip", "fv_knee", "fc_h", "fs_h", "vs_h", "fc_k", "fs_k", "vs_k"]
    print("PARAMS:", {lab[i]: round(best["x"][i], 4) for i in range(8)})
    print("VERDICT:", "KEEP" if gain < -2.0 else "DROP (<2% gain)")


if __name__ == "__main__":
    main()
