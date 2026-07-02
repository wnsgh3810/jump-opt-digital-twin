"""Phase 2 finalize: drop-test (4 friction axes) + per-exp breakdown + plots.
Confirms whether friction fixed sit2stand_gnd divergence + jump_0424 regression.
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
P2 = REPO / "code/goal19/phase2"
sys.path.insert(0, str(P2))
sys.path.insert(0, str(REPO / "code/goal19/templates"))
sys.path.insert(0, str(REPO / "code/goal19/data_loaders"))
sys.path.insert(0, str(REPO / "code/goal19/phase1"))

from run_phase2_friction import eval_vec, eval_friction, X0, PHASE1_BASELINE, P1_X
import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

BEST = json.load(open(P2 / "phase2_best.json"))
BEST_X = np.array(BEST["best_x"])   # fv_hip, fv_knee, fc_hip, fc_knee
VAR = BEST["var_names"]
BEST_S = BEST["best_score"]


def apply_full(fric):
    """Apply Phase1 mass model + Phase2 friction to S."""
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE = [float(v) for v in fric]
    return ap


def breakdown(fric):
    apply_full(fric)
    ap = P4.apply_phase1_params(P1_X)  # returns arm; friction already set is overwritten -> reset
    S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE = [float(v) for v in fric]
    rows = {}
    for ds, sub, isj in list_experiments():
        q1, q2 = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        s, m = S.run_one_sub(ds, sub, q1, q2, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
        rows[(ds, sub)] = (float(s) if s is not None else None, m)
    return rows


def main():
    print(f"Phase 2 best = {BEST_S:.2f}  fric={[round(v,4) for v in BEST_X]}")
    # Drop-test: pin each friction axis to 0
    print("\nDrop-test (pin axis -> 0):")
    dt = []
    for i, name in enumerate(VAR):
        x = BEST_X.copy(); x[i] = 0.0
        s = eval_vec(x)
        d = s - BEST_S; pct = 100*d/BEST_S
        keep = pct > 3.0
        print(f"  {name:8s}: {BEST_X[i]:.4f}->0  score={s:9.2f}  Δ={d:+8.1f} ({pct:+6.2f}%)  {'KEEP' if keep else 'DROP'}")
        dt.append(dict(axis=name, best=float(BEST_X[i]), pinned=float(s), delta=float(d), pct=float(pct), keep=bool(keep)))

    # Per-exp breakdown: Phase1 (no friction) vs Phase2
    p1_rows = breakdown([0,0,0,0])       # Phase 1 model (friction 0)
    p2_rows = breakdown(BEST_X)
    print("\nPer-exp Phase1 -> Phase2:")
    focus = []
    p2_total = 0.0
    per_exp = []
    for (ds, sub, isj) in list_experiments():
        s1 = p1_rows[(ds, sub)][0]; s2, m2 = p2_rows[(ds, sub)]
        p2_total += s2
        dpct = 100*(s1 - s2)/s1 if s1 else 0
        per_exp.append(dict(ds=ds, sub=sub, is_jump=isj, p1=s1, p2=s2, dpct=dpct,
                            **{k: float(v) for k, v in (m2 or {}).items() if isinstance(v, (int, float, np.floating, np.integer))}))
        mark = ""
        if (ds, sub) in [("sit2stand_gnd_0319","ROOT"),("jump_0424","90_0.75_90_2"),("jump_0424","60_0.75_60_2")]:
            mark = "  <-- focus"
        print(f"  {ds+'/'+sub:38s} {s1:9.1f} -> {s2:9.1f}  ({dpct:+6.1f}%){mark}")

    out = dict(best_score=float(BEST_S), best_x=BEST_X.tolist(), var_names=VAR,
               phase1_baseline=PHASE1_BASELINE, phase0_baseline=41271.18,
               cumulative_pct=100*(41271.18-BEST_S)/41271.18,
               droptest=dt, per_exp=per_exp)
    (P2 / "phase2_final_breakdown.json").write_text(json.dumps(out, indent=2))
    print(f"\nWritten: {P2/'phase2_final_breakdown.json'}")

    # Plots for focus subs (sit2stand_gnd divergence, regressed 0424, good jump)
    ap = apply_full(BEST_X)
    S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE = [float(v) for v in BEST_X]
    plots = P2 / "plots"
    for ds, sub in [("sit2stand_gnd_0319","ROOT"), ("jump_0424","90_0.75_90_2"),
                    ("jump_0424","60_0.75_60_2"), ("jump_torque_0422","P100_D3")]:
        try:
            ok = P4.plot_sub(ds, sub, str(plots / f"{ds}__{sub}.png"),
                             arm_hip=ap["arm_hip"], arm_knee=ap["arm_knee"], title_extra="  [Phase 2]")
            print(f"  plot {ds}/{sub}: {ok}")
        except Exception as e:
            print(f"  plot {ds}/{sub} ERR: {e}")


if __name__ == "__main__":
    main()
