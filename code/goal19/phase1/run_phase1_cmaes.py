"""Phase 1 - Robot dynamics (mass + inertia + CoM per part) CMA-ES.

15D search on top of Phase 0 Pure CAD base:
  x[0] = M_base_scale  ∈ [0.75, 1.30]
  x[1] = M_thigh_scale ∈ [0.75, 1.30]
  x[2] = M_calf_scale  ∈ [0.75, 1.30]
  x[3] = M_p_scale     ∈ [0.5, 1.5]
  x[4] = M_c_scale     ∈ [0.5, 1.5]
  x[5] = M_foot_extra  ∈ [0.0, 0.30]  kg
  x[6] = I_thigh_scale ∈ [0.5, 1.5]
  x[7] = I_calf_scale  ∈ [0.5, 1.5]
  x[8] = I_p_scale     ∈ [0.5, 1.5]
  x[9] = I_c_scale     ∈ [0.5, 1.5]
  x[10] = com_shift_thigh_z ∈ [-0.020, 0.020] m
  x[11] = com_shift_thigh_x ∈ [-0.020, 0.020] m
  x[12] = com_shift_calf_z  ∈ [-0.020, 0.020] m
  x[13] = com_shift_calf_x  ∈ [-0.020, 0.020] m
  x[14] = arm_knee     ∈ [0.001, 0.020]  (arm_hip locked at 0)

Motor LPF, tau_scale forbidden. Contact ON. Mode A only. 31 exp.
Phase 0 baseline = 41,271.18.
"""
import sys, json, time, os
from pathlib import Path
from multiprocessing import Pool, cpu_count
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/templates"))
sys.path.insert(0, str(REPO / "code/goal19/data_loaders"))

# Load Phase 0 offsets
OFFSETS_PATH = Path("C:/Users/junho/Desktop/jump_opt/goal18/iter2/iter1_offsets.json")
with open(OFFSETS_PATH) as f:
    OFFSETS = json.load(f)
OFFSET_MAP = {(o["ds"], o["sub"]): (o["q1_off"], o["q2_off"]) for o in OFFSETS}


# 15D bounds
BOUNDS = np.array([
    [0.75, 1.30],   # 0: M_base
    [0.75, 1.30],   # 1: M_thigh
    [0.75, 1.30],   # 2: M_calf
    [0.5,  1.5],    # 3: M_p (paddle hip)
    [0.5,  1.5],    # 4: M_c (paddle knee)
    [0.0,  0.30],   # 5: M_foot_extra kg
    [0.5,  1.5],    # 6: I_thigh
    [0.5,  1.5],    # 7: I_calf
    [0.5,  1.5],    # 8: I_p
    [0.5,  1.5],    # 9: I_c
    [-0.020, 0.020],  # 10: com_shift_thigh_z
    [-0.020, 0.020],  # 11: com_shift_thigh_x
    [-0.020, 0.020],  # 12: com_shift_calf_z
    [-0.020, 0.020],  # 13: com_shift_calf_x
    [0.001, 0.020],   # 14: arm_knee
])
X0 = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.0,  1.0, 1.0, 1.0, 1.0,
               0.0, 0.0, 0.0, 0.0, 0.00490])

N_DIM = len(BOUNDS)


def clip_x(x):
    return np.clip(x, BOUNDS[:, 0], BOUNDS[:, 1])


def _patch_and_eval_all(x):
    """Apply Phase 1 params to sim engine, evaluate all 31 subs, return total score."""
    import sub_sim_iter6v2 as S
    from load_31exp import list_experiments

    # Base Pure CAD (Phase 0) overrides
    S.MOTOR_TM_LOCK      = 0.0
    S.SOLREF_TC_LOCK     = 0.006320
    S.IMP0_LOCK          = 0.14301
    S.FV_HIP = S.FV_KNEE = 0.001
    S.FC_HIP = S.FC_KNEE = 0.001
    S.W_Q = 100.0
    S.W_DQ = 50.0
    S.W_H = 100.0
    S.W_T = 0.0
    S.W_GRF = 0.1
    S.W_PEN = 50.0

    # Phase 1 variables
    (M_base_s, M_thigh_s, M_calf_s, M_p_s, M_c_s, M_foot_ex,
     I_thigh_s, I_calf_s, I_p_s, I_c_s,
     dz_th, dx_th, dz_ca, dx_ca, arm_k) = x

    S.M_BASE_SCALE_LOCK = float(M_base_s)
    S.MTS_LOCK = float(M_thigh_s)
    S.MCS_LOCK = float(M_calf_s)
    S.MPS_LOCK = float(M_p_s)
    S.MCPS_LOCK = float(M_c_s)
    S.MFX_LOCK = float(M_foot_ex)

    # Override ci_locked with independent I scales + CoM shifts
    from build_xml_i3 import (
        M1_CAD, M2_CAD, M_P_CAD, M_C_CAD,
        R1_VAL, R2_VAL, RP_VAL, RC_VAL, LC_VAL, L2_VAL,
        I1_VAL, I2_VAL, IP_VAL, IC_VAL,
    )

    def ci_phase1():
        M1 = M1_CAD * M_thigh_s
        Mp = M_P_CAD * M_p_s
        M2 = M2_CAD * M_calf_s
        Mc = M_C_CAD * M_c_s
        Mf = float(M_foot_ex)
        # Independent inertia scales (decoupled from mass)
        I1 = I1_VAL * I_thigh_s
        Ip = IP_VAL * I_p_s
        I2 = I2_VAL * I_calf_s
        Ic = IC_VAL * I_c_s
        # Thigh composite (thigh+hip paddle) with CoM shift on thigh
        r1_shift = R1_VAL + dz_th
        rp_shift = RP_VAL + dz_th  # paddle attaches to thigh, shift together
        Mt = M1 + Mp
        ctz = -(M1 * r1_shift + Mp * rp_shift) / Mt
        dm1 = r1_shift + ctz
        dmp = rp_shift + ctz
        # LC lateral offset for paddle + potential x-shift on thigh
        lc_eff = LC_VAL + dx_th  # thigh x-shift approx via paddle lateral
        It = I1 + M1 * dm1**2 + Ip + Mp * (dmp**2 + lc_eff**2)
        # Calf composite (calf+knee paddle+foot) with CoM shift on calf
        r2_shift = R2_VAL + dz_ca
        rc_shift = RC_VAL + dz_ca
        l2_shift = L2_VAL + dz_ca
        Mc2 = M2 + Mc + Mf
        ccz = -(M2 * r2_shift + Mc * rc_shift + Mf * l2_shift) / Mc2
        dm2 = r2_shift + ccz
        dmc = rc_shift + ccz
        dmf = l2_shift + ccz
        # calf x-shift: add small offset via dx_ca
        Ic2 = I2 + M2 * dm2**2 + Ic + Mc * dmc**2 + Mf * dmf**2 + (M2 + Mc + Mf) * dx_ca**2
        return Mt, ctz, It, Mc2, ccz, Ic2

    S.ci_locked = ci_phase1

    # Evaluate all 31 subs sequentially
    total = 0.0
    n_ok = 0
    for ds, sub, is_jump in list_experiments():
        q1_off, q2_off = OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        try:
            score, _ = S.run_one_sub(ds, sub, q1_off, q2_off, 0.0, float(arm_k), motor_tm=0.0)
        except Exception:
            score = None
        if score is None or not np.isfinite(score) or score > 5e5:
            total += 5e5
        else:
            total += float(score)
            n_ok += 1
    return total, n_ok


def eval_wrapper(x):
    x = clip_x(x)
    total, n_ok = _patch_and_eval_all(x)
    return float(total)


def main():
    import cma
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(exist_ok=True)

    print(f"[Phase 1] CMA-ES over {N_DIM}D robot dynamics")
    print(f"Phase 0 baseline = 41271.18")
    print(f"X0 = {X0}")

    # Verify X0 == Phase 0 gives ~41271
    t0 = time.time()
    s0 = eval_wrapper(X0)
    print(f"X0 eval: score={s0:.2f} ({time.time()-t0:.1f}s)")

    # CMA-ES config
    sigma0 = 0.15  # broad initial spread over normalized bounds
    lo = BOUNDS[:, 0]; hi = BOUNDS[:, 1]
    span = hi - lo
    def to_norm(x): return (x - lo) / span
    def from_norm(u): return u * span + lo
    def eval_norm(u):
        return eval_wrapper(from_norm(np.clip(u, 0.0, 1.0)))

    u0 = to_norm(X0)
    es = cma.CMAEvolutionStrategy(u0, sigma0, {
        'bounds': [[0.0]*N_DIM, [1.0]*N_DIM],
        'maxfevals': 400,
        'popsize': 12,
        'verbose': -9,
        'seed': 42,
    })

    hist = []
    best_score = s0
    best_x = X0.copy()
    t_start = time.time()

    while not es.stop():
        pop_u = es.ask()
        scores = []
        for u in pop_u:
            s = eval_norm(u)
            scores.append(s)
            if s < best_score:
                best_score = s
                best_x = from_norm(np.clip(u, 0.0, 1.0))
        es.tell(pop_u, scores)
        gen = es.countiter
        elapsed = time.time() - t_start
        hist.append(dict(gen=int(gen), best=float(best_score),
                         pop_mean=float(np.mean(scores)),
                         pop_min=float(min(scores)), pop_max=float(max(scores)),
                         elapsed=elapsed, nfev=int(es.countevals)))
        print(f"gen {gen:3d}  best={best_score:9.2f}  pop_min={min(scores):9.2f}  "
              f"mean={np.mean(scores):9.2f}  nfev={es.countevals:4d}  ({elapsed:.0f}s)")
        # Save incremental
        (out_dir / "phase1_progress.json").write_text(json.dumps(dict(
            best_score=float(best_score), best_x=best_x.tolist(),
            history=hist, phase0_baseline=41271.18,
        ), indent=2))

    print(f"\n[Phase 1 done] best={best_score:.2f}  Δ={(41271.18-best_score)/41271.18*100:.1f}%")
    (out_dir / "phase1_best.json").write_text(json.dumps(dict(
        best_score=float(best_score),
        best_x=best_x.tolist(),
        var_names=["M_base_s","M_thigh_s","M_calf_s","M_p_s","M_c_s","M_foot_ex",
                   "I_thigh_s","I_calf_s","I_p_s","I_c_s",
                   "com_dz_thigh","com_dx_thigh","com_dz_calf","com_dx_calf","arm_knee"],
        phase0_baseline=41271.18,
        history=hist,
    ), indent=2))
    print(f"Written: {out_dir/'phase1_best.json'}")


if __name__ == "__main__":
    main()
