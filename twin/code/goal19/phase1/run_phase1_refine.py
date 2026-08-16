"""Phase 1 refine: parsimonious KEEP-only model + expanded bounds on boundary-chasers.

From drop-test, KEEP axes = {M_base_s, M_p_s, M_foot_ex, com_dz_calf, arm_knee}.
DROP axes pinned to Pure CAD (X0). Boundary-chasers (M_foot_ex, M_p_s, arm_knee)
hit upper bounds -> expand.

5D CMA-ES. Compare parsimonious-best vs full-15D-best (20367.75).
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase1"))
from run_phase1_cmaes import eval_wrapper, X0  # 15D eval

VAR_NAMES = ["M_base_s","M_thigh_s","M_calf_s","M_p_s","M_c_s","M_foot_ex",
             "I_thigh_s","I_calf_s","I_p_s","I_c_s",
             "com_dz_thigh","com_dx_thigh","com_dz_calf","com_dx_calf","arm_knee"]

# Full best_x from CMA-ES
with open(Path(__file__).resolve().parent / "phase1_best.json") as f:
    FULL_BEST = json.load(f)
FULL_X = np.array(FULL_BEST["best_x"])
FULL_SCORE = FULL_BEST["best_score"]
BASELINE = FULL_BEST["phase0_baseline"]

# KEEP axis indices in the 15D vector
KEEP_IDX = [0, 3, 5, 12, 14]  # M_base_s, M_p_s, M_foot_ex, com_dz_calf, arm_knee
KEEP_NAMES = [VAR_NAMES[i] for i in KEEP_IDX]

# Expanded bounds for the 5 KEEP axes (boundary-chasers widened)
KEEP_BOUNDS = np.array([
    [0.90, 1.40],    # M_base_s
    [0.80, 1.80],    # M_p_s (was 1.5, expand)
    [0.0,  0.60],    # M_foot_ex (was 0.30, expand)
    [-0.030, 0.010], # com_dz_calf (widen negative)
    [0.001, 0.050],  # arm_knee (was 0.020, expand)
])


def build_full_x(keep_vals):
    """Insert 5 KEEP vals into a Pure-CAD (X0) base vector."""
    x = X0.copy()
    for idx, v in zip(KEEP_IDX, keep_vals):
        x[idx] = v
    return x


def eval_keep(keep_vals):
    return eval_wrapper(build_full_x(keep_vals))


def main():
    out_dir = Path(__file__).resolve().parent
    # 1) parsimonious KEEP-only at full-best values (pin drops to CAD)
    keep_at_best = FULL_X[KEEP_IDX]
    s_parsi = eval_keep(keep_at_best)
    print(f"Full 15D best      = {FULL_SCORE:.2f}")
    print(f"Parsimonious(5 KEEP, drops->CAD) = {s_parsi:.2f}  "
          f"(loses {s_parsi-FULL_SCORE:+.1f} vs full)")
    print("-" * 70)

    # 2) 5D CMA-ES with expanded bounds
    import cma
    lo = KEEP_BOUNDS[:, 0]; hi = KEEP_BOUNDS[:, 1]; span = hi - lo
    to_norm = lambda x: (x - lo) / span
    from_norm = lambda u: np.clip(u, 0, 1) * span + lo
    u0 = to_norm(np.clip(keep_at_best, lo, hi))
    es = cma.CMAEvolutionStrategy(u0, 0.20, {
        'bounds': [[0.0]*5, [1.0]*5], 'maxfevals': 200, 'popsize': 10,
        'verbose': -9, 'seed': 7,
    })
    best_s = s_parsi; best_keep = keep_at_best.copy()
    hist = []
    t0 = time.time()
    while not es.stop():
        U = es.ask()
        S = []
        for u in U:
            kv = from_norm(u)
            s = eval_keep(kv)
            S.append(s)
            if s < best_s:
                best_s = s; best_keep = kv.copy()
        es.tell(U, S)
        hist.append(dict(gen=int(es.countiter), best=float(best_s),
                         nfev=int(es.countevals), elapsed=time.time()-t0))
        print(f"gen {es.countiter:2d}  best={best_s:9.2f}  nfev={es.countevals:3d}  ({time.time()-t0:.0f}s)")
        (out_dir / "phase1_refine_progress.json").write_text(json.dumps(dict(
            best_score=float(best_s), best_keep=best_keep.tolist(),
            keep_names=KEEP_NAMES, history=hist), indent=2))

    # Build final full-x (KEEP refined + drops CAD)
    final_x = build_full_x(best_keep)
    print("-" * 70)
    print(f"Refined 5D best = {best_s:.2f}  (Δ vs Phase0 = {100*(BASELINE-best_s)/BASELINE:.1f}%)")
    for n, v in zip(KEEP_NAMES, best_keep):
        print(f"  {n:16s} = {v:.5f}")
    out = dict(
        parsimonious_score=float(s_parsi),
        refined_score=float(best_s),
        full_15d_score=float(FULL_SCORE),
        baseline=float(BASELINE),
        improvement_pct=float(100*(BASELINE-best_s)/BASELINE),
        keep_names=KEEP_NAMES,
        keep_idx=KEEP_IDX,
        best_keep=best_keep.tolist(),
        final_x_15d=final_x.tolist(),
        var_names=VAR_NAMES,
        keep_bounds=KEEP_BOUNDS.tolist(),
        history=hist,
    )
    (out_dir / "phase1_refine_best.json").write_text(json.dumps(out, indent=2))
    print(f"Written: {out_dir/'phase1_refine_best.json'}")


if __name__ == "__main__":
    main()
