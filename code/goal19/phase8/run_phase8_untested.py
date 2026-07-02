"""Phase 8 - Autonomous expansion: test untested axes for ablation completeness.

On top of the FINAL model (goal19_final_model.json, zero offset), test axes never
fit in GOAL19:
  A. arm_hip  (Phase 1 locked it at 0) — hip motor reflected inertia
  B. dt / integrator — timestep + RK4 vs implicit
Each with drop-test logic (does it improve >3%?). Report KEEP/DROP.
FINAL baseline (zero offset) = 15,182.
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
for p in ["templates","data_loaders","phase1","phase2","phase3","phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))

import sub_sim_iter6v2 as S
import plot_4panel as P4
import mujoco
from load_31exp import list_experiments

FM = json.load(open(REPO/"code/goal19/goal19_final_model.json"))
P1_X = np.array(FM["mass_15d"]); P1_X[5]=FM["m_foot_ex"]; FR=FM["friction"]; CT=FM["contact"]
BASE = 15182.0


def apply_final():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=FR["fv_hip"]; S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


def eval_all(arm_hip=0.0):
    ap = apply_final()
    total=0.0
    for ds, sub, isj in list_experiments():
        try:
            s,_ = S.run_one_sub(ds, sub, 0.0, 0.0, arm_hip, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s=None
        total += 5e5 if (s is None or not np.isfinite(s) or s>5e5) else float(s)
    return total


def main():
    out = Path(__file__).resolve().parent
    print(f"[Phase 8] Autonomous — untested axes (FINAL baseline={BASE})")
    results = {}

    # ---- Axis A: arm_hip (1D sweep) ----
    print("\nA. arm_hip (Phase 1 locked=0) — hip motor reflected inertia:")
    best_ah=(0.0, BASE)
    for ah in [0.0, 0.002, 0.005, 0.01, 0.02, 0.04]:
        t0=time.time(); s=eval_all(arm_hip=ah)
        print(f"   arm_hip={ah:.3f}: score={s:9.2f}  Δ={100*(BASE-s)/BASE:+.2f}%  ({time.time()-t0:.0f}s)")
        if s<best_ah[1]: best_ah=(ah, s)
    imp_ah = 100*(BASE-best_ah[1])/BASE
    print(f"   best arm_hip={best_ah[0]:.3f} → {best_ah[1]:.2f} ({imp_ah:+.2f}%) → {'KEEP' if imp_ah>3 else 'DROP (weak)'}")
    results["arm_hip"]=dict(best=best_ah[0], score=best_ah[1], improve_pct=imp_ah, keep=imp_ah>3)

    # ---- Axis B: dt (timestep) ----
    print("\nB. dt / timestep (base 0.0005, RK4 jump / implicitfast s2s):")
    DT0 = S.DT
    best_dt=(DT0, BASE)
    for dt in [0.0002, 0.0005, 0.001]:
        S.DT = dt
        t0=time.time(); s=eval_all(arm_hip=0.0)
        print(f"   dt={dt:.4f}: score={s:9.2f}  Δ={100*(BASE-s)/BASE:+.2f}%  ({time.time()-t0:.0f}s)")
        if s<best_dt[1]: best_dt=(dt, s)
    S.DT = DT0
    imp_dt = 100*(BASE-best_dt[1])/BASE
    print(f"   best dt={best_dt[0]:.4f} → {best_dt[1]:.2f} ({imp_dt:+.2f}%) → {'KEEP' if imp_dt>3 else 'DROP (weak)'}")
    results["dt"]=dict(best=best_dt[0], score=best_dt[1], improve_pct=imp_dt, keep=imp_dt>3)

    (out/"phase8_untested.json").write_text(json.dumps(dict(baseline=BASE, results=results), indent=2))
    print(f"\nWritten: {out/'phase8_untested.json'}")
    keep=[k for k,v in results.items() if v['keep']]
    print(f"KEEP: {keep or 'none (model at ceiling — all untested axes DROP)'}")


if __name__ == "__main__":
    main()
