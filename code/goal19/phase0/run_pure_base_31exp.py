"""Phase 0 - Pure CAD Baseline for GOAL19.

Runs Mode A sim on all 31 sub-experiments with PURE_BASE overrides:
  - motor_tm = 0 (no LPF, per user directive)
  - m_base_scale = 1.0 (CAD)
  - mass scales (thigh/calf/pad_hip/pad_knee/foot_extra) = 1.0 / 0.0 (Pure CAD)
  - solref_tc = 0.006320, imp0 = 0.14301 (defaults)
  - fv/fc = 0.001 (near-zero friction)
  - arm_hip = 0.0, arm_knee = 0.00490 (CAD-derived)

Score per md formula:
  Wq=100, Wdq=50, Wt=0, Wh_jump=100, Wgrf=0.1, Wpen=50
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# Enable sub_sim_iter6v2 imports
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
sys.path.insert(0, str(TEMPLATES))

# Import BEFORE monkey-patching to grab canonical constants
import sub_sim_iter6v2 as S

# Monkey-patch to PURE_BASE (BEFORE any XML/model build)
S.MOTOR_TM_LOCK      = 0.0
S.M_BASE_SCALE_LOCK  = 1.0
S.SOLREF_TC_LOCK     = 0.006320
S.IMP0_LOCK          = 0.14301
S.MTS_LOCK           = 1.0
S.MCS_LOCK           = 1.0
S.MPS_LOCK           = 1.0
S.MCPS_LOCK          = 1.0
S.MFX_LOCK           = 0.0
S.FV_HIP = S.FV_KNEE = 0.001
S.FC_HIP = S.FC_KNEE = 0.001

# Weights per GOAL19 md
S.W_Q    = 100.0
S.W_DQ   = 50.0
S.W_H    = 100.0   # md says Wh=100 (not 200 as iter6v2 default)
S.W_T    = 0.0
S.W_GRF  = 0.1
S.W_PEN  = 50.0

# PURE_BASE arm values (CAD-derived)
ARM_HIP  = 0.0
ARM_KNEE = 0.00490


def main():
    # Load 31-exp offsets (per-trial q_offsets — Phase 0 uses whatever's inherited from iter1)
    offsets_path = Path("C:/Users/junho/Desktop/jump_opt/goal18/iter2/iter1_offsets.json")
    with open(offsets_path) as f:
        offsets = json.load(f)
    offset_map = {(o["ds"], o["sub"]): (o["q1_off"], o["q2_off"]) for o in offsets}

    # Load our loader to know which subs are canonical-loadable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data_loaders"))
    from load_31exp import list_experiments

    results = []
    total_score = 0.0
    n_ok = 0
    n_fail = 0
    t0 = time.time()
    print(f"[Phase 0] Pure CAD Base — 31 exp")
    print(f"Overrides: motor_tm=0, m_base_scale=1.0, mass_scales=1.0, mfx=0.0, arm_h=0, arm_k={ARM_KNEE}")
    print(f"Weights: Wq={S.W_Q} Wdq={S.W_DQ} Wt={S.W_T} Wh={S.W_H} Wgrf={S.W_GRF} Wpen={S.W_PEN}")
    print("-" * 100)

    for ds, sub, is_jump in list_experiments():
        q1_off, q2_off = offset_map.get((ds, sub), (0.0, 0.0))
        t_start = time.time()
        try:
            score, m = S.run_one_sub(ds, sub, q1_off, q2_off, ARM_HIP, ARM_KNEE, motor_tm=0.0)
        except Exception as e:
            print(f"  [ERR] {ds}/{sub}: {e}")
            results.append(dict(ds=ds, sub=sub, is_jump=is_jump, error=str(e), score=None))
            n_fail += 1
            continue
        elapsed = time.time() - t_start
        if score is None or m is None or not np.isfinite(score) or score > 5e5:
            print(f"  [FAIL] {ds}/{sub}: score={score}")
            results.append(dict(ds=ds, sub=sub, is_jump=is_jump, score=score, elapsed=elapsed))
            n_fail += 1
            continue
        total_score += float(score)
        n_ok += 1
        entry = dict(ds=ds, sub=sub, is_jump=is_jump, score=float(score), elapsed=elapsed,
                     q1_off=q1_off, q2_off=q2_off)
        for k, v in m.items():
            if isinstance(v, (int, float, np.floating, np.integer)):
                entry[k] = float(v)
        results.append(entry)
        h_info = f"h_sim={m.get('h_sim_m', 0):.3f}/h_real={m.get('h_real_m', 0):.3f}" if is_jump else ""
        print(f"  [{'JUMP' if is_jump else 'S2S '}] {ds}/{sub}: score={score:9.2f}  "
              f"rmse_q1={m.get('rmse_q1', 0):.3f}  rmse_q2={m.get('rmse_q2', 0):.3f}  "
              f"pen={m.get('pen_max_mm', 0):.2f}mm  {h_info}  ({elapsed:.1f}s)")

    total_elapsed = time.time() - t0
    print("-" * 100)
    print(f"[Phase 0 result] score_total={total_score:.2f}  n_ok={n_ok}  n_fail={n_fail}  ({total_elapsed:.1f}s)")

    out = dict(
        phase=0,
        label="Pure CAD Baseline (unified 31 exp)",
        overrides=dict(motor_tm=0.0, m_base_scale=1.0, mass_scales=1.0,
                       m_foot_extra=0.0, solref_tc=S.SOLREF_TC_LOCK, imp0=S.IMP0_LOCK,
                       fv=0.001, fc=0.001, arm_hip=ARM_HIP, arm_knee=ARM_KNEE),
        weights=dict(Wq=S.W_Q, Wdq=S.W_DQ, Wt=S.W_T, Wh=S.W_H, Wgrf=S.W_GRF, Wpen=S.W_PEN),
        score_total=total_score,
        n_ok=n_ok,
        n_fail=n_fail,
        elapsed_s=total_elapsed,
        per_exp=results,
    )
    out_path = Path(__file__).resolve().parent / "pure_base_31exp_result.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
