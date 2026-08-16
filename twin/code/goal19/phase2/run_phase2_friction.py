"""Phase 2 - Joint friction (viscous fv + Coulomb fc) on top of Phase 1 model.

4D: fv_hip, fv_knee (damping, Nm*s/rad), fc_hip, fc_knee (frictionloss, Nm).
Base = Phase 1 full 15D best (mass/inertia/CoM/arm_knee fixed).

Targets: (1) stabilize sit2stand_gnd_0319 divergence, (2) recover jump_0424 regression.
Phase 1 baseline = 20,367.75.
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/templates"))
sys.path.insert(0, str(REPO / "code/goal19/data_loaders"))
sys.path.insert(0, str(REPO / "code/goal19/phase1"))

import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

# Phase 1 model (fixed base)
with open(REPO / "code/goal19/phase1/phase1_best.json") as f:
    P1_X = np.array(json.load(f)["best_x"])

PHASE1_BASELINE = 20367.75

# 4D friction bounds
BOUNDS = np.array([
    [0.0, 3.0],   # fv_hip  (damping)
    [0.0, 3.0],   # fv_knee
    [0.0, 3.0],   # fc_hip  (frictionloss)
    [0.0, 3.0],   # fc_knee
])
X0 = np.array([0.001, 0.001, 0.001, 0.001])  # Phase 1 had ~0 friction
N_DIM = 4


def eval_friction(fv_hip, fv_knee, fc_hip, fc_knee):
    """Apply Phase 1 model + friction, evaluate all 31 exp."""
    ap = P4.apply_phase1_params(P1_X)   # sets mass/inertia/ci/arm
    S.FV_HIP = float(fv_hip); S.FV_KNEE = float(fv_knee)
    S.FC_HIP = float(fc_hip); S.FC_KNEE = float(fc_knee)
    arm_hip, arm_knee = ap["arm_hip"], ap["arm_knee"]
    total = 0.0
    for ds, sub, isj in list_experiments():
        q1, q2 = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        try:
            s, _ = S.run_one_sub(ds, sub, q1, q2, arm_hip, arm_knee, motor_tm=0.0)
        except Exception:
            s = None
        total += 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
    return total


def eval_vec(x):
    x = np.clip(x, BOUNDS[:, 0], BOUNDS[:, 1])
    return eval_friction(*x)


def main():
    out = Path(__file__).resolve().parent
    print(f"[Phase 2] Joint friction 4D on Phase 1 base (={PHASE1_BASELINE})")
    t0 = time.time()
    s0 = eval_vec(X0)
    print(f"X0 (near-zero friction) = {s0:.2f}  ({time.time()-t0:.1f}s)  "
          f"[should ~= Phase 1 {PHASE1_BASELINE}]")

    import cma
    lo, hi = BOUNDS[:, 0], BOUNDS[:, 1]; span = hi - lo
    to_norm = lambda x: (x - lo) / span
    from_norm = lambda u: np.clip(u, 0, 1) * span + lo
    es = cma.CMAEvolutionStrategy(to_norm(np.clip(X0, lo, hi)), 0.25, {
        'bounds': [[0.0]*N_DIM, [1.0]*N_DIM], 'maxfevals': 180, 'popsize': 10,
        'verbose': -9, 'seed': 11,
    })
    best_s = s0; best_x = X0.copy(); hist = []
    while not es.stop():
        U = es.ask(); Sc = []
        for u in U:
            xx = from_norm(u); s = eval_vec(xx); Sc.append(s)
            if s < best_s: best_s = s; best_x = xx.copy()
        es.tell(U, Sc)
        hist.append(dict(gen=int(es.countiter), best=float(best_s),
                         nfev=int(es.countevals), elapsed=time.time()-t0))
        print(f"gen {es.countiter:2d} best={best_s:9.2f} nfev={es.countevals:3d} ({time.time()-t0:.0f}s)")
        (out / "phase2_progress.json").write_text(json.dumps(dict(
            best_score=float(best_s), best_x=best_x.tolist(),
            var_names=["fv_hip","fv_knee","fc_hip","fc_knee"],
            phase1_baseline=PHASE1_BASELINE, history=hist), indent=2))

    dpct = 100*(PHASE1_BASELINE - best_s)/PHASE1_BASELINE
    print(f"\n[Phase 2 done] best={best_s:.2f}  Δ vs Phase1 = {dpct:+.1f}%")
    for n, v in zip(["fv_hip","fv_knee","fc_hip","fc_knee"], best_x):
        print(f"  {n:8s} = {v:.5f}")
    (out / "phase2_best.json").write_text(json.dumps(dict(
        best_score=float(best_s), best_x=best_x.tolist(),
        var_names=["fv_hip","fv_knee","fc_hip","fc_knee"],
        phase1_baseline=PHASE1_BASELINE, improvement_pct=dpct,
        history=hist), indent=2))
    print(f"Written: {out/'phase2_best.json'}")


if __name__ == "__main__":
    main()
