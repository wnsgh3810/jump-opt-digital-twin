"""G20-D — smooth actuator-map residual (a_hat refinement), LODO-gated.

a_hat came from another lab's AK80-9 unit. A small SMOOTH correction
    delta_tau_j = c1*tau + c2*tau|tau|/18 + c3*dq*|tau|/20      (per joint, 6 coeffs)
is fitted on window score ON TOP of the frozen fourbar round-1 best. This contains a
tau-linear term, so the ONLY way it is legitimate (not the forbidden tau_scale fudge)
is GENERALIZATION: leave-one-date-out — fit on 2 date-groups, evaluate held-out date.
KEEP only if held-out improves on ALL folds; else DROP and record.
Folds: A={0324,0421} B={0424} C={0602} (s2s always in-fit, tiny torques).
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

OUT = REPO / "code/goal19/phase11/resid_best.json"
BASEJ = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BASEJ["names"], BASEJ["x"]))
FOLDS = {"A": ["jump_0324", "jump_position_0421"], "B": ["jump_0424"], "C": ["jump_0602"]}


def build_model():
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))


def eval_windows_res(model, pp, c):
    """c = [c1h,c2h,c3h, c1k,c2k,c3k]; delta applied to ctrl."""
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
            th0 = np.interp(tc, t, pp["tau_h"]); tk0 = np.interp(tc, t, pp["tau_k"])
            v1 = d.qvel[1]; v2 = d.qvel[2]
            th = th0 + c[0] * th0 + c[1] * th0 * abs(th0) / 18 + c[2] * v1 * abs(th0) / 20
            tk = tk0 + c[3] * tk0 + c[4] * tk0 * abs(tk0) / 18 + c[5] * v2 * abs(tk0) / 20
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


def score_subset(c, model, dsets):
    mj, mg = FR.get_serial_models()
    total = 0.0
    for ds, subs, loader, isj in FR.all_groups():
        if isj and ds not in dsets:
            continue
        k1, k2 = FR.OFFKEY.get(ds, (None, None))
        o1 = BD[k1] if k1 else 0.0; o2 = BD[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            total += MS.window_score(eval_windows_res(model, shifted_view(pp, o1, o2), c))
    return total


def fit_on(model, dsets, seed):
    import cma
    lo = np.array([-0.3, -0.3, -0.3] * 2); hi = np.array([0.3, 0.3, 0.3] * 2)
    es = cma.CMAEvolutionStrategy(np.full(6, 0.5), 0.25,
                                  {"bounds": [0, 1], "maxfevals": 90, "popsize": 8,
                                   "seed": seed, "verbose": -9})
    best = dict(obj=score_subset(np.zeros(6), model, dsets), c=[0.0] * 6)
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            c = lo + np.array(sn) * (hi - lo)
            o = score_subset(c, model, dsets)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), c=[float(v) for v in c])
        es.tell(sols, objs)
    return best


def main():
    model = build_model()
    alld = [d for f in FOLDS.values() for d in f]
    print("LODO gate: fit on 2 folds, eval held-out; keep only if ALL folds improve.", flush=True)
    verdicts = []
    for hold, hdsets in FOLDS.items():
        train = [d for d in alld if d not in hdsets]
        b = fit_on(model, train, seed=31 + ord(hold))
        held0 = score_subset(np.zeros(6), model, hdsets)
        held1 = score_subset(np.array(b["c"]), model, hdsets)
        g = 100 * (held1 / held0 - 1)
        verdicts.append(g)
        print(f"fold {hold} (hold {hdsets}): held-out {held0:.0f} -> {held1:.0f} ({g:+.1f}%)  c={np.round(b['c'],3).tolist()}", flush=True)
    if all(g < -1.0 for g in verdicts):
        b = fit_on(model, alld, seed=101)
        json.dump(dict(obj=b["obj"], c=b["c"]), open(OUT, "w"), indent=2)
        print(f"VERDICT: KEEP (all folds improve). Full-fit c={np.round(b['c'],3).tolist()}")
    else:
        print("VERDICT: DROP — residual does not generalize across dates (tau_scale-fudge would).")


if __name__ == "__main__":
    main()
