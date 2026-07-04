"""GOAL19 Phase 11r — unified physical re-fit on the MULTIPLE-SHOOTING metric.

Objective = sum of window scores (mshoot.evaluate_all) over:
  jump_position_0421 + jump_0424 + jump_0602 + sit2stand_gnd   (user: 0422 excluded)
Pure tau_real replay inside windows — no PD, no gains, no fudge. Geometry locked.
22 params (mass/inertia/CoM dz+dx/arm_knee/m_foot/stiff_knee/contact/friction).
Warm start = current final model. Validation (separate): full-trajectory replay + h.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
import mshoot as MS

FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))
BASE = np.array(FM["mass_15d"]); FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
OUT = REPO / "code/goal19/phase11/mshoot_refit_best.json"

# name, mass_15d idx (int) or tag, warm, lo, hi
SPEC = [
    ("M_base",   0, BASE[0], 0.60, 1.40), ("M_thigh", 1, BASE[1], 0.60, 1.40),
    ("M_calf",   2, BASE[2], 0.45, 1.40), ("M_p",     3, BASE[3], 0.60, 1.50),
    ("M_c",      4, BASE[4], 0.55, 1.50), ("I_thigh", 6, BASE[6], 0.40, 1.80),
    ("I_calf",   7, BASE[7], 0.40, 1.80), ("I_p",     8, BASE[8], 0.40, 1.80),
    ("I_c",      9, BASE[9], 0.40, 1.80),
    ("com_dz_th", 10, BASE[10], -0.090, 0.050), ("com_dx_th", 11, BASE[11], -0.050, 0.050),
    ("com_dz_ca", 12, BASE[12], -0.090, 0.050), ("com_dx_ca", 13, BASE[13], -0.050, 0.050),
    ("arm_knee", 14, BASE[14], 0.003, 0.025),
    ("m_foot",   "mf", FM["m_foot_ex"], 0.00, 0.35),
    ("stiff_knee", "sk", FL["stiff_knee"], 0.00, 4.50),
    ("solref_tc", "sr", CT["solref_tc"], 0.0018, 0.0060),
    ("imp0",     "im", CT["imp0"], 0.08, 0.45),
    ("fv_hip",   "fvh", FR["fv_hip"], 0.10, 1.30),
    ("fv_knee",  "fvk", FR["fv_knee"], 0.00, 0.70),
    ("fc_hip",   "fch", FR["fc_hip"], 0.02, 0.60),
    ("fc_knee",  "fck", FR["fc_knee"], 0.10, 1.30),
]
NAMES = [s[0] for s in SPEC]
X0 = np.array([np.clip(s[2], s[3], s[4]) for s in SPEC])
LOb = np.array([s[3] for s in SPEC]); HIb = np.array([s[4] for s in SPEC])


def set_params(x):
    d = dict(zip(NAMES, x)); xm = BASE.copy()
    for nm, idx, *_ in SPEC:
        if isinstance(idx, int):
            xm[idx] = d[nm]
    xm[5] = d["m_foot"]
    P4.apply_phase1_params(xm)
    S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = d["fc_hip"]; S.FC_KNEE = d["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return d


def evaluate(x):
    d = set_params(x)
    try:
        total, per = MS.evaluate_all(0.0, d["arm_knee"])
    except Exception:
        return 9e9, None
    return total, per


def main():
    import cma
    o0, per0 = evaluate(X0)
    print(f"WARM (final model) mshoot total={o0:.0f}", flush=True)
    for ds, v in per0.items():
        m = v["mean"]
        print(f"   WARM {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f} (n={v['n']})", flush=True)
    x0n = (X0 - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n, 0.20, {"bounds": [0, 1], "maxfevals": 350,
                                              "popsize": 16, "seed": 13, "verbose": -9})
    best = dict(obj=float(o0), x=[float(v) for v in X0], names=NAMES)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LOb + np.array(sn) * (HIb - LOb)
            o, _ = evaluate(x)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), x=[float(v) for v in x], names=NAMES)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best={best['obj']:.0f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nBEST mshoot total={best['obj']:.0f}  (WARM {o0:.0f}, -{(1-best['obj']/o0)*100:.1f}%)")
    _, per = evaluate(np.array(best["x"]))
    for ds, v in per.items():
        m = v["mean"]
        print(f"   BEST {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f}")
    print("PARAMS:", {NAMES[i]: round(best["x"][i], 4) for i in range(len(NAMES))})


if __name__ == "__main__":
    main()
