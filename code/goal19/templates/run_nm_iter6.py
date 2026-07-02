"""Iter6: 2D Nelder-Mead over (arm_hip, arm_knee).

Iter5 chain locks (15+ params):
  - motor_tm = 0.032s, m_base_scale = 1.0358, solref_tc = 0.007085, imp0 = 0.2526
  - M_thigh_scale = 0.9315, M_calf_scale = 1.0148
  - M_p_scale = 0.8175,    M_c_scale = 0.7813
  - M_foot_extra = 0.6015
  - friction = 0
  - per-trial q_offsets (iter1)
  - Mode A: ctrl = -tau_filt (no scale)
  - Wh = 200 (jump-only)  ← ★ change vs iter5

Axis (2D, ★ user correction first applied):
  - arm_hip  ∈ [0.001, 0.05]  init 0.005
  - arm_knee ∈ [0.001, 0.05]  init 0.005

Loss = sum of per-sub scores
   (Wq=100, Wdq=50, Wh=200 jump-only, Wgrf=0.1, Wpen=50)
"""
import sys, json, time
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter6")
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter5")
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter4")
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter3")
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter2")
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from multiprocessing import Pool, cpu_count
import io
from contextlib import redirect_stderr
import numpy as np
from scipy.optimize import minimize

ROOT = Path("C:/Users/junho/Desktop/jump_opt/goal18/iter6")
ROOT.mkdir(exist_ok=True, parents=True)

OFFSETS_PATH = Path("C:/Users/junho/Desktop/jump_opt/goal18/iter2/iter1_offsets.json")

# ── Bounds ────────────────────────────────────────────────────────────────────
AH_LO, AH_HI = 0.001, 0.05  # arm_hip
AK_LO, AK_HI = 0.001, 0.05  # arm_knee

# X0 init
X0 = np.array([0.005, 0.005])

# Iter5 reported score (Wh=100). Recomputed under Wh=200 at arm=0 (baseline) for fair comparison.
ITER5_SCORE_OLD_WEIGHTS = 31101.58945521695


def _eval_sub(args):
    ds, sub, q1, q2, ah, ak = args
    import sys
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter6")
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter5")
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter4")
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter3")
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18/iter2")
    from sub_sim_6d import run_one_sub
    err_buf = io.StringIO()
    try:
        with redirect_stderr(err_buf):
            score, metrics = run_one_sub(ds, sub, q1, q2, ah, ak)
        if score is None:
            return (ds, sub, 1e6, None, "score=None")
        return (ds, sub, float(score), metrics, None)
    except Exception as e:
        import traceback
        return (ds, sub, 1e6, None, f"{type(e).__name__}: {e}\n{traceback.format_exc()[:400]}")


def evaluate_x(x, offsets, pool, label=""):
    ah = float(np.clip(x[0], AH_LO, AH_HI))
    ak = float(np.clip(x[1], AK_LO, AK_HI))
    args_list = [(o["ds"], o["sub"], o["q1_off"], o["q2_off"], ah, ak)
                 for o in offsets]
    t0 = time.time()
    results = pool.map(_eval_sub, args_list)
    elapsed = time.time() - t0
    n_ok = sum(1 for r in results if r[2] < 1e6)
    total = sum(r[2] for r in results)
    print(f"  [{label}] ah={ah:.5f} ak={ak:.5f} -> {total:.2f} n_ok={n_ok}/{len(results)} ({elapsed:.1f}s)")
    return total, results


def main():
    t0 = time.time()
    print("=" * 80)
    print("Iter6: NM 2D (arm_hip, arm_knee)")
    print(f"  X0 = {X0}")
    print(f"  Bounds: arm_hip=[{AH_LO},{AH_HI}] arm_knee=[{AK_LO},{AK_HI}]")
    print(f"  ★ Iter5 chain KEEP. Wh=200 jump-only (changed from Wh=100).")
    print("=" * 80)

    with open(OFFSETS_PATH) as f:
        offsets = json.load(f)
    print(f"Loaded {len(offsets)} sub offsets")

    n_workers = min(16, cpu_count() - 1)
    print(f"Using {n_workers} parallel workers")

    pool = Pool(processes=n_workers)

    eval_history = []
    n_evals = [0]
    best = [None, None, None]

    # Reference: re-eval at "iter5 chain at arm=0" under NEW Wh=200 weights
    print("\n[REFERENCE] Re-evaluating iter5 chain at arm_hip=arm_knee=0 with Wh=200:")
    ref_total, _ = evaluate_x(np.array([0.0, 0.0]), offsets, pool, "ref_arm0_Wh200")
    iter5_score_new_weights = ref_total
    n_evals[0] = 0  # reset (don't include ref in NM history)

    def loss_fn(x):
        n_evals[0] += 1
        label = f"eval{n_evals[0]:02d}"
        total, results = evaluate_x(x, offsets, pool, label)
        eval_history.append({
            "iter": n_evals[0],
            "arm_hip": float(x[0]),
            "arm_knee": float(x[1]),
            "score_total": float(total),
            "n_ok": int(sum(1 for r in results if r[2] < 1e6)),
        })
        if best[1] is None or total < best[1]:
            best[0] = np.array(x, copy=True)
            best[1] = total
            best[2] = results
            print(f"    *** NEW BEST: total={total:.2f}")
        return total

    # Per-axis scale for NM. Range 0.001..0.05, step ≈ 0.005
    SCALES = np.array([0.005, 0.005])

    def loss_normalized(z):
        x = X0 + z * SCALES
        return loss_fn(x)

    z0 = np.zeros(2)
    # Initial simplex: vertex at z0, +1 in each axis (≈ +0.005 each)
    initial_simplex = np.zeros((3, 2))
    initial_simplex[0] = z0
    initial_simplex[1] = np.array([1.0, 0.0])
    initial_simplex[2] = np.array([0.0, 1.0])

    try:
        res = minimize(loss_normalized, z0, method='Nelder-Mead',
                       options=dict(maxiter=30, xatol=0.05, fatol=20.0,
                                    initial_simplex=initial_simplex,
                                    disp=True, adaptive=True))
        x_best_nm = X0 + res.x * SCALES
        print(f"\nNM result: x_best={x_best_nm}, fun={res.fun:.2f}, nit={res.nit}, nfev={res.nfev}")
    except Exception as e:
        import traceback
        print(f"NM failed: {e}\n{traceback.format_exc()}")

    pool.close()
    pool.join()

    x_best = best[0]
    score_best = best[1]
    results_best = best[2]
    ah_b = float(np.clip(x_best[0], AH_LO, AH_HI))
    ak_b = float(np.clip(x_best[1], AK_LO, AK_HI))

    print(f"\n[BEST OVERALL] arm_hip={ah_b:.6f} arm_knee={ak_b:.6f}  score={score_best:.2f}")
    pct = (iter5_score_new_weights - score_best) / iter5_score_new_weights * 100.0
    print(f"vs iter5_chain@arm=0 (Wh=200): {iter5_score_new_weights:.2f} -> {score_best:.2f}  ({pct:+.2f}%)")
    print(f"vs iter5 published (Wh=100): {ITER5_SCORE_OLD_WEIGHTS:.2f} -> {score_best:.2f}  (NOTE: different Wh)")

    per_sub_best = []
    for ds, sub, sc, m, err in results_best:
        e = {"ds": ds, "sub": sub, "score": sc}
        if m is not None:
            e.update({k: float(v) if isinstance(v, (int, float, np.floating)) else v for k, v in m.items()})
        if err:
            e["error"] = err[:300]
        per_sub_best.append(e)

    out = {
        "iter": 6,
        "method": "2D NM (arm_hip, arm_knee), iter5 chain KEEP, Wh=200",
        "n_subs": len(offsets),
        "n_workers": n_workers,
        "x0": X0.tolist(),
        "scales": SCALES.tolist(),
        "bounds": {
            "arm_hip": [AH_LO, AH_HI],
            "arm_knee": [AK_LO, AK_HI],
        },
        "locks": {
            "motor_tm_s": 0.032,
            "m_base_scale": 1.0358,
            "solref_tc": 0.007085,
            "imp0": 0.2526,
            "M_thigh_scale": 0.9315059554829954,
            "M_calf_scale": 1.0148252312906139,
            "M_p_scale": 0.8175172505295485,
            "M_c_scale": 0.7813326611103126,
            "M_foot_extra": 0.6014600524487825,
        },
        "best": {
            "arm_hip": ah_b,
            "arm_knee": ak_b,
            "score_total": score_best,
        },
        "score_iter5_old_weights_Wh100": ITER5_SCORE_OLD_WEIGHTS,
        "score_iter5_chain_at_arm0_new_weights_Wh200": iter5_score_new_weights,
        "score_iter6": score_best,
        "pct_improvement_vs_iter5_at_arm0": pct,
        "n_evals": n_evals[0],
        "eval_history": eval_history,
        "per_sub_best": per_sub_best,
        "elapsed_s": time.time() - t0,
        "weights": {"Wq": 100.0, "Wdq": 50.0, "Wh": 200.0, "Wgrf": 0.1, "Wpen": 50.0, "pen_free_mm": 2.0},
    }
    out_path = ROOT / "nm_2d_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")
    print(f"Elapsed: {(time.time()-t0)/60:.2f} min")
    return out


if __name__ == "__main__":
    main()
