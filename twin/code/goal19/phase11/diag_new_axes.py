"""Phase 11 diagnostic: test previously-untested axes on the FINAL model.
  - real jump init pose (vs fixed)
  - foot friction mu (slip)
  - base_z_init offset
Reports total + jump h_ratio for each, to see which axes matter.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
for p in ["templates","data_loaders","phase1","phase2","phase3","phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

FM = json.load(open(REPO/"code/goal19/goal19_final_model.json"))
P1_X = np.array(FM["mass_15d"]); P1_X[5]=FM["m_foot_ex"]; FR=FM["friction"]; CT=FM["contact"]


def apply_final():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=FR["fv_hip"]; S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


def eval_all():
    ap = apply_final()
    tot=0.0; hs=[]; hr=[]; s2s=0.0; jmp=0.0
    for ds, sub, isj in list_experiments():
        try:
            s,m = S.run_one_sub(ds, sub, 0.0, 0.0, 0.0, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s,m=None,None
        v = 5e5 if (s is None or not np.isfinite(s) or s>5e5) else float(s)
        tot += v
        if isj:
            jmp += v
            if m: hs.append(m.get("h_sim_m",0)); hr.append(m.get("h_real_m",0))
        else: s2s += v
    ratio = sum(hs)/sum(hr) if hr else 0
    return tot, s2s, jmp, ratio


def reset_axes():
    S.FOOT_MU_SLIDE=1.0; S.FOOT_MU_TORSION=0.02; S.FOOT_MU_ROLL=0.01
    S.USE_REAL_JUMP_INIT=False; S.BASE_Z_INIT_OFF=0.0


def main():
    print("[Phase 11 diag] untested axes on FINAL model (base 15,182)\n")
    reset_axes()
    t,s2s,j,r = eval_all()
    print(f"  DEFAULT              : total={t:8.1f} s2s={s2s:7.1f} jump={j:7.1f} h_ratio={r:.3f}")

    reset_axes(); S.USE_REAL_JUMP_INIT=True
    t,s2s,j,r = eval_all()
    print(f"  real jump init       : total={t:8.1f} s2s={s2s:7.1f} jump={j:7.1f} h_ratio={r:.3f}")

    for mu in [0.4, 0.7, 1.5, 3.0]:
        reset_axes(); S.FOOT_MU_SLIDE=mu
        t,s2s,j,r = eval_all()
        print(f"  foot_mu_slide={mu:<4}   : total={t:8.1f} s2s={s2s:7.1f} jump={j:7.1f} h_ratio={r:.3f}")

    for bz in [-0.02, 0.02, 0.05]:
        reset_axes(); S.BASE_Z_INIT_OFF=bz
        t,s2s,j,r = eval_all()
        print(f"  base_z_off={bz:<6}    : total={t:8.1f} s2s={s2s:7.1f} jump={j:7.1f} h_ratio={r:.3f}")

    # combined: real init + best-looking mu
    reset_axes(); S.USE_REAL_JUMP_INIT=True; S.FOOT_MU_SLIDE=0.7
    t,s2s,j,r = eval_all()
    print(f"  real_init + mu=0.7   : total={t:8.1f} s2s={s2s:7.1f} jump={j:7.1f} h_ratio={r:.3f}")
    reset_axes()


if __name__ == "__main__":
    main()
