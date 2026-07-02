"""Phase 1 drop-test: for each axis in Phase 1, pin it back to Phase 0 value
and measure Δscore. Axis dropped if |Δscore| / best < 3%.

Runs 15 evaluations: each axis pinned individually.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase1"))
from run_phase1_cmaes import eval_wrapper, X0, BOUNDS

VAR_NAMES = ["M_base_s","M_thigh_s","M_calf_s","M_p_s","M_c_s","M_foot_ex",
             "I_thigh_s","I_calf_s","I_p_s","I_c_s",
             "com_dz_thigh","com_dx_thigh","com_dz_calf","com_dx_calf","arm_knee"]

def main():
    out_dir = Path(__file__).resolve().parent
    with open(out_dir / "phase1_best.json") as f:
        best = json.load(f)
    best_x = np.array(best["best_x"])
    best_score = best["best_score"]
    baseline = best.get("phase0_baseline", 41271.18)

    print(f"Baseline (Phase 0)  = {baseline:.2f}")
    print(f"Phase 1 best score  = {best_score:.2f}  (Δ={100*(baseline-best_score)/baseline:.1f}%)")
    print(f"Phase 1 best_x      = {[f'{v:.4f}' for v in best_x]}")
    print("-" * 90)

    results = []
    for i, name in enumerate(VAR_NAMES):
        x_test = best_x.copy()
        x_test[i] = X0[i]
        s = eval_wrapper(x_test)
        delta = s - best_score
        pct = 100 * delta / best_score
        keep = pct > 3.0
        print(f"  {name:20s}: pin {best_x[i]:8.4f}->{X0[i]:8.4f}  "
              f"score={s:9.2f}  Δ={delta:+8.2f} ({pct:+6.2f}%)  {'KEEP' if keep else 'DROP'}")
        results.append(dict(axis=name, best_val=float(best_x[i]), pin_val=float(X0[i]),
                            pinned_score=float(s), delta=float(delta),
                            delta_pct=float(pct), keep=bool(keep)))
    out_dir_p1 = out_dir / "phase1_droptest.json"
    out_dir_p1.write_text(json.dumps(dict(
        baseline=baseline, best_score=best_score, best_x=best_x.tolist(),
        results=results,
    ), indent=2))
    print(f"\nWritten: {out_dir_p1}")
    keep_axes = [r["axis"] for r in results if r["keep"]]
    drop_axes = [r["axis"] for r in results if not r["keep"]]
    print(f"KEEP: {keep_axes}")
    print(f"DROP: {drop_axes}")


if __name__ == "__main__":
    main()
