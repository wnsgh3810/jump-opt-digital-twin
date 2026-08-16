"""Phase 3 - Contact compliance (solref_tc, imp0) on top of Phase 1+2.

Residual analysis (Phase 2): dq RMSE dominates ALL jump groups (69-87%), and
h_sim=0.456 << h_real=0.844 (sim jumps half as high). Mode A replays real torque,
so under-jump = excess effective inertia OR energy deficit. tau_scale forbidden.
=> Softer contact stores + returns energy at push-off -> higher take-off velocity
   -> better dq + h match. This directly targets the dominant residual.

2D: solref_tc (contact time constant, s), imp0 (impedance floor).
Base = Phase 1 mass + Phase 2 friction (all fixed). Phase 2 baseline = 15,744.40.
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
sys.path.insert(0, str(REPO / "code/goal19/phase2"))

import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

# Fixed base: Phase 1 mass + Phase 2 friction
P1_X = np.array(json.load(open(REPO / "code/goal19/phase1/phase1_best.json"))["best_x"])
P2_FRIC = json.load(open(REPO / "code/goal19/phase2/phase2_best.json"))["best_x"]
PHASE2_BASELINE = 15744.40

# 2D contact bounds
BOUNDS = np.array([
    [0.002, 0.040],   # solref_tc (larger = softer = more energy storage)
    [0.02,  0.60],    # imp0
])
X0 = np.array([0.006320, 0.14301])  # Phase 0/1/2 default
N_DIM = 2


def apply_base():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE = [float(v) for v in P2_FRIC]
    return ap


def eval_contact(solref_tc, imp0):
    ap = apply_base()
    S.SOLREF_TC_LOCK = float(solref_tc)
    S.IMP0_LOCK = float(imp0)
    total = 0.0
    for ds, sub, isj in list_experiments():
        q1, q2 = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        try:
            s, _ = S.run_one_sub(ds, sub, q1, q2, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s = None
        total += 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
    return total


def eval_vec(x):
    x = np.clip(x, BOUNDS[:, 0], BOUNDS[:, 1])
    return eval_contact(*x)


def main():
    out = Path(__file__).resolve().parent
    print(f"[Phase 3] Contact (solref_tc, imp0) on Phase 2 base (={PHASE2_BASELINE})")
    t0 = time.time()
    s0 = eval_vec(X0)
    print(f"X0 (default contact) = {s0:.2f}  [should ~= Phase 2 {PHASE2_BASELINE}]  ({time.time()-t0:.1f}s)")

    import cma
    lo, hi = BOUNDS[:, 0], BOUNDS[:, 1]; span = hi - lo
    to_norm = lambda x: (x - lo)/span; from_norm = lambda u: np.clip(u,0,1)*span+lo
    es = cma.CMAEvolutionStrategy(to_norm(np.clip(X0, lo, hi)), 0.28, {
        'bounds': [[0.0]*N_DIM, [1.0]*N_DIM], 'maxfevals': 120, 'popsize': 8,
        'verbose': -9, 'seed': 5})
    best_s = s0; best_x = X0.copy(); hist=[]
    while not es.stop():
        U = es.ask(); Sc=[]
        for u in U:
            xx=from_norm(u); s=eval_vec(xx); Sc.append(s)
            if s<best_s: best_s=s; best_x=xx.copy()
        es.tell(U, Sc)
        hist.append(dict(gen=int(es.countiter), best=float(best_s), nfev=int(es.countevals), elapsed=time.time()-t0))
        print(f"gen {es.countiter:2d} best={best_s:9.2f} solref={best_x[0]:.5f} imp0={best_x[1]:.4f} nfev={es.countevals:3d} ({time.time()-t0:.0f}s)")
        (out/"phase3_progress.json").write_text(json.dumps(dict(
            best_score=float(best_s), best_x=best_x.tolist(),
            var_names=["solref_tc","imp0"], phase2_baseline=PHASE2_BASELINE, history=hist), indent=2))

    dpct=100*(PHASE2_BASELINE-best_s)/PHASE2_BASELINE
    print(f"\n[Phase 3 done] best={best_s:.2f}  Δ vs Phase2={dpct:+.1f}%  cumulative={100*(41271.18-best_s)/41271.18:.1f}%")
    print(f"  solref_tc={best_x[0]:.5f}  imp0={best_x[1]:.4f}")
    (out/"phase3_best.json").write_text(json.dumps(dict(
        best_score=float(best_s), best_x=best_x.tolist(), var_names=["solref_tc","imp0"],
        phase2_baseline=PHASE2_BASELINE, improvement_pct=dpct, history=hist), indent=2))
    print(f"Written: {out/'phase3_best.json'}")


if __name__ == "__main__":
    main()
