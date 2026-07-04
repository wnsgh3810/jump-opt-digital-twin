"""G20 — deep-learning actuator residual (tiny MLP), LODO-screened.

User directive: try DL too. Tiny per-joint MLP delta_tau = w2·tanh(W1·[tau/18, dq/20,
sin(q)] + b1) (3 hidden units, 32 weights total both joints), injected in the window
loop like the poly residual. Screen: fit on folds B+C (0424+0602), evaluate held-out
fold A (0324+0421). Poly already failed LODO; a higher-capacity MLP is expected to
memorize harder — this is the empirical check. KEEP only if held-out improves >1%.
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
from mshoot_resid import build_model  # same frozen-base builder

BASEJ = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BASEJ["names"], BASEJ["x"]))
NH = 3  # hidden units per joint


def unpack(w):
    """w (32,) -> per-joint (W1(3x3), b1(3), w2(3), b2 omitted)."""
    out = []
    k = 0
    for _ in range(2):
        W1 = w[k:k+9].reshape(NH, 3); k += 9
        b1 = w[k:k+3]; k += 3
        w2 = w[k:k+3]; k += 3
        out.append((W1, b1, w2))
    return out


def mlp_dt(net, tau, dq, q):
    W1, b1, w2 = net
    f = np.array([tau / 18.0, dq / 20.0, np.sin(q)])
    return float(w2 @ np.tanh(W1 @ f + b1))


def eval_windows_mlp(model, pp, nets):
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
            th = th0 + mlp_dt(nets[0], th0, d.qvel[1], d.qpos[1])
            tk = tk0 + mlp_dt(nets[1], tk0, d.qvel[2], d.qpos[2])
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


def score_subset(w, model, dsets):
    nets = unpack(w)
    mj, mg = FR.get_serial_models()
    total = 0.0
    for ds, subs, loader, isj in FR.all_groups():
        if isj and ds not in dsets:
            continue
        if not isj:
            continue  # jumps only for this screen
        k1, k2 = FR.OFFKEY.get(ds, (None, None))
        o1 = BD[k1] if k1 else 0.0; o2 = BD[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            total += MS.window_score(eval_windows_mlp(model, shifted_view(pp, o1, o2), nets))
    return total


def main():
    import cma
    model = build_model()
    train = ["jump_0424", "jump_0602"]
    hold = ["jump_0324", "jump_position_0421"]
    w0 = np.zeros(32)
    tr0 = score_subset(w0, model, train)
    hd0 = score_subset(w0, model, hold)
    print(f"base: train {tr0:.0f}  held {hd0:.0f}", flush=True)
    es = cma.CMAEvolutionStrategy(np.zeros(32), 0.15,
                                  {"bounds": [-0.6, 0.6], "maxfevals": 160, "popsize": 10,
                                   "seed": 61, "verbose": -9})
    best = dict(obj=tr0, w=w0)
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            o = score_subset(np.array(sn), model, train)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), w=np.array(sn))
        es.tell(sols, objs)
        print(f"train best={best['obj']:.0f}", flush=True)
    hd1 = score_subset(best["w"], model, hold)
    print(f"\ntrain {tr0:.0f}->{best['obj']:.0f} ({100*(best['obj']/tr0-1):+.1f}%)  "
          f"HELD-OUT {hd0:.0f}->{hd1:.0f} ({100*(hd1/hd0-1):+.1f}%)")
    print("VERDICT:", "promising -> full LODO" if hd1 < hd0 * 0.99 else "DROP (MLP memorizes, does not transfer)")


if __name__ == "__main__":
    main()
