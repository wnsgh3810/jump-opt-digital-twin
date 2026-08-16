"""Phase 1 finalize: adopt refined 5-param stack, run full 31-exp breakdown,
generate representative 4-panel plots + 1 canonical animation.

Phase 1 FINAL model (refined 5 KEEP, drops->CAD):
  M_base_s=1.088, M_p_s=1.565, M_foot_ex=0.403, com_dz_calf=-0.024, arm_knee=0.024
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
P1 = REPO / "code/goal19/phase1"
sys.path.insert(0, str(P1))
sys.path.insert(0, str(REPO / "code/goal19/templates"))
sys.path.insert(0, str(REPO / "code/goal19/data_loaders"))

from run_phase1_cmaes import eval_wrapper, X0

# Phase 1 FINAL model = FULL 15D CMA-ES best (legitimate optimum, within bounds).
# NOTE: the "refine" (phase1_refine_best.json) was DISCARDED — eval_wrapper's clip_x
# silently clipped expanded bounds, so its 20,533 was a clipped artifact. The genuine
# best is the full 15D (20,367.75); expanding foot mass beyond 0.30 actually hurts.
with open(P1 / "phase1_best.json") as f:
    BEST = json.load(f)
FINAL_X = np.array(BEST["best_x"])
VAR_NAMES = ["M_base_s","M_thigh_s","M_calf_s","M_p_s","M_c_s","M_foot_ex",
             "I_thigh_s","I_calf_s","I_p_s","I_c_s",
             "com_dz_thigh","com_dx_thigh","com_dz_calf","com_dx_calf","arm_knee"]
KEEP_NAMES = VAR_NAMES
BEST_KEEP = FINAL_X.tolist()


def per_exp_breakdown():
    """Run all 31 exp with FINAL_X, return per-exp scores + metrics."""
    import sub_sim_iter6v2 as S
    import plot_4panel as P4
    P4.apply_phase1_params(FINAL_X)   # configures S with final model
    ap = P4.apply_phase1_params(FINAL_X)
    arm_hip, arm_knee = ap["arm_hip"], ap["arm_knee"]
    from load_31exp import list_experiments

    rows = []
    total = 0.0
    for ds, sub, is_jump in list_experiments():
        q1_off, q2_off = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        try:
            score, m = S.run_one_sub(ds, sub, q1_off, q2_off, arm_hip, arm_knee, motor_tm=0.0)
        except Exception as e:
            rows.append(dict(ds=ds, sub=sub, is_jump=is_jump, score=None, err=str(e)))
            continue
        if score is None or not np.isfinite(score):
            rows.append(dict(ds=ds, sub=sub, is_jump=is_jump, score=None))
            continue
        total += float(score)
        row = dict(ds=ds, sub=sub, is_jump=is_jump, score=float(score))
        for k, v in (m or {}).items():
            if isinstance(v, (int, float, np.floating, np.integer)):
                row[k] = float(v)
        rows.append(row)
    return total, rows


def main():
    t0 = time.time()
    total, rows = per_exp_breakdown()
    print(f"Phase 1 FINAL (refined 5-param) total = {total:.2f}  ({time.time()-t0:.1f}s)")
    print(f"  vs Phase 0 baseline 41271.18  =>  {100*(41271.18-total)/41271.18:.1f}%")

    # Load Phase 0 per-exp for comparison
    with open(REPO / "code/goal19/phase0/pure_base_31exp_result.json") as f:
        p0 = json.load(f)
    p0_map = {(r["ds"], r["sub"]): r.get("score") for r in p0["per_exp"]}

    print(f"\n{'sub':40s} {'P0':>9s} {'P1':>9s} {'Δ%':>7s}")
    for r in rows:
        if r.get("score") is None: continue
        key = (r["ds"], r["sub"])
        p0s = p0_map.get(key)
        dpct = 100*(p0s - r["score"])/p0s if p0s else 0
        print(f"  {r['ds']+'/'+r['sub']:38s} {p0s:9.1f} {r['score']:9.1f} {dpct:+6.1f}")

    out = dict(
        model="Phase 1 FINAL (refined 5-param KEEP)",
        keep_names=KEEP_NAMES, best_keep=BEST_KEEP,
        final_x_15d=FINAL_X.tolist(),
        score_total=total,
        baseline=41271.18,
        improvement_pct=100*(41271.18-total)/41271.18,
        per_exp=rows,
    )
    (P1 / "phase1_final_breakdown.json").write_text(json.dumps(out, indent=2))
    print(f"\nWritten: {P1/'phase1_final_breakdown.json'}")

    # Representative 4-panel plots
    import plot_4panel as P4
    plots_dir = P1 / "plots"
    reps = [
        ("sit2stand_gnd_0319", "ROOT"),      # worst offender
        ("jump_0424", "90_0.75_90_2"),        # best jump
        ("jump_0424", "150_2.2_500_4"),       # high-PD
        ("jump_0602", "90_0.75_90_2"),        # 0602 best
        ("jump_torque_0422", "P100_D3"),      # torque high-PD
        ("jump_position_0421", "P70_D0.75_P70_D2"),  # position PD
    ]
    ap = P4.apply_phase1_params(FINAL_X)
    for ds, sub in reps:
        try:
            ok = P4.plot_sub(ds, sub, str(plots_dir / f"{ds}__{sub}.png".replace(".","p",1)),
                             arm_hip=ap["arm_hip"], arm_knee=ap["arm_knee"],
                             title_extra="  [Phase 1 final]")
            print(f"  plot {ds}/{sub}: {ok}")
        except Exception as e:
            print(f"  plot {ds}/{sub} ERR: {e}")


if __name__ == "__main__":
    main()
