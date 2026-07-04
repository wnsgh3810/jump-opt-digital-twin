"""GOAL19 Phase 11p — q/dq re-fit v2: widen CoM (railed in v1) + radial CoM + stiff, joint-interaction.

v1 (reopt_torque_qdq) railed com_dz_th/com_dz_ca to the -0.04 bound and stiff_knee to 2.5.
Record synthesis (G10-16): the biggest LEGITIMATE q/dq levers (tau_scale removed) are
joint stiffness (+85%), CoM redistribution (untried), knee viscous friction crossing the
~0.1 cliff (dq2 -64%), mass redistribution. Inertia tensors are DEAD (rank-deficient).

So v2: warm-start from v1 best, WIDEN com_dz to +-0.09, ADD radial com_dx (untried),
widen stiff_knee to [0,4.5], keep joint friction free (cross the fv_knee cliff), torque
data only, q/dq weighted. Single unified physical set (no per-trial, no tau_scale).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

S.W_Q = 250.0; S.W_DQ = 60.0; S.W_H = 60.0; S.W_GRF = 0.0

FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))
BASE = np.array(FM["mass_15d"]); FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
V1 = json.load(open(REPO / "code/goal19/phase11/reopt_torque_qdq_best.json", encoding="utf-8"))
V1M = dict(zip(V1["names"], V1["x"]))
OUT = REPO / "code/goal19/phase11/reopt_torque_qdq_v2_best.json"
LO = {"jump_0424": S.load_jump_0424, "jump_0602": S.load_jump_0602, "jump_torque_0422": S.load_jump_torque}

# name, mass_15d idx (int) or tag, warm(from v1 or base), lo, hi
def w(nm, fallback):
    return V1M.get(nm, fallback)

SPEC = [
    ("M_base",   0, w("M_base", BASE[0]), 0.60, 1.40), ("M_thigh", 1, w("M_thigh", BASE[1]), 0.60, 1.40),
    ("M_calf",   2, w("M_calf", BASE[2]), 0.45, 1.40), ("M_p",     3, w("M_p", BASE[3]), 0.60, 1.50),
    ("M_c",      4, w("M_c", BASE[4]), 0.55, 1.50), ("I_thigh", 6, w("I_thigh", BASE[6]), 0.40, 1.80),
    ("I_calf",   7, w("I_calf", BASE[7]), 0.40, 1.80), ("I_p",     8, w("I_p", BASE[8]), 0.40, 1.80),
    ("I_c",      9, w("I_c", BASE[9]), 0.40, 1.80),
    ("com_dz_th", 10, w("com_dz_th", BASE[10]), -0.090, 0.050),   # WIDENED
    ("com_dx_th", 11, 0.0, -0.050, 0.050),                        # NEW radial
    ("com_dz_ca", 12, w("com_dz_ca", BASE[12]), -0.090, 0.050),   # WIDENED
    ("com_dx_ca", 13, 0.0, -0.050, 0.050),                        # NEW radial
    ("arm_hip",  13.5, w("arm_hip", BASE[13]), 0.0003, 0.008),    # idx handled below (13->hip is idx13; but 13 used by dx_ca)
    ("arm_knee", 14, w("arm_knee", BASE[14]), 0.003, 0.012),
    ("m_foot",   "mf", w("m_foot", FM["m_foot_ex"]), 0.00, 0.35),
    ("stiff_knee", "sk", w("stiff_knee", FL["stiff_knee"]), 0.00, 4.50),   # WIDENED
    ("solref_tc", "sr", w("solref_tc", CT["solref_tc"]), 0.0018, 0.0060),
    ("imp0",     "im", w("imp0", CT["imp0"]), 0.08, 0.45),
    ("fv_hip",   "fvh", w("fv_hip", FR["fv_hip"]), 0.10, 1.30),
    ("fv_knee",  "fvk", w("fv_knee", FR["fv_knee"]), 0.00, 0.70),
    ("fc_hip",   "fch", w("fc_hip", FR["fc_hip"]), 0.02, 0.60),
    ("fc_knee",  "fck", w("fc_knee", FR["fc_knee"]), 0.10, 1.30),
]
# fix arm_hip index (mass_15d idx 13 is dx_ca; arm_hip is a separate tag in apply_phase1_params -> actually idx 13 IS arm? no)
# In apply_phase1_params the 15-vec is: (...,dz_th=10,dx_th=11,dz_ca=12,dx_ca=13,arm_k=14). arm_hip is returned 0.0 fixed.
# So arm_hip is NOT in mass_15d. Drop the bogus arm_hip entry; hip armature stays ~0 (physically right per records).
SPEC = [s for s in SPEC if s[0] != "arm_hip"]

NAMES = [s[0] for s in SPEC]
X0 = np.array([np.clip(s[2], s[3], s[4]) for s in SPEC])
LOb = np.array([s[3] for s in SPEC]); HIb = np.array([s[4] for s in SPEC])
ALL = [(ds, sub, isj) for ds, sub, isj in list_experiments()
       if (isj and ds != "jump_position_0421") or "gnd" in ds.lower()]


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
    d = set_params(x); tot = 0.0; nan = 0
    for ds, sub, isj in ALL:
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, d["arm_knee"], motor_tm=0.0)
        except Exception:
            s = None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        if v >= 5e5: nan += 1
        tot += v
    return tot, nan


def per_dataset(x):
    import mujoco
    from collections import defaultdict
    d = set_params(x); G = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])
    for ds, sub, isj in ALL:
        if not isj:
            continue
        td = LO[ds](sub)
        mdl = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, d["arm_knee"]))
        log = S.run_jump_sim(mdl, td, 0, 0, motor_tm=0.0)
        if log is None:
            continue
        tr = np.asarray(td["t"]); mk = (log["t"] >= 0) & (log["t"] <= tr[-1]); ts = log["t"][mk]
        q1s = np.interp(tr, ts, (-log["q"][:, 1] - np.pi/2)[mk]); q2s = np.interp(tr, ts, (-log["q"][:, 2])[mk])
        dq1s = np.interp(tr, ts, (-log["dq"][:, 1])[mk]); dq2s = np.interp(tr, ts, (-log["dq"][:, 2])[mk])
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        g = G[ds]; g[0] += r(q1s, td["q1"]); g[1] += r(q2s, td["q2"]); g[2] += r(dq1s, td["dq1"]); g[3] += r(dq2s, td["dq2"]); g[4] += 1
    return {ds: [g[0]/g[4], g[1]/g[4], g[2]/g[4], g[3]/g[4]] for ds, g in G.items()}


def main():
    import cma
    o0, n0 = evaluate(X0)
    print(f"WARM v2 (v1 best + widened CoM/stiff): total={o0:.0f} nan={n0}", flush=True)
    for ds, v in sorted(per_dataset(X0).items()):
        print(f"   WARM {ds.replace('jump_',''):14s} q1={v[0]:.3f} q2={v[1]:.3f} dq1={v[2]:.2f} dq2={v[3]:.2f}", flush=True)
    x0n = (X0 - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n, 0.18, {"bounds": [0, 1], "maxfevals": 300, "popsize": 16, "seed": 11, "verbose": -9})
    best = dict(obj=o0, x=[float(v) for v in X0], names=NAMES)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LOb + np.array(sn) * (HIb - LOb)
            o, n = evaluate(x)
            objs.append(o if n == 0 else o + 1e5 * n)
            if n == 0 and o < best["obj"]:
                best = dict(obj=o, x=[float(v) for v in x], names=NAMES)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best_total={best['obj']:.0f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nBEST v2 total={best['obj']:.0f}  (WARM {o0:.0f}, -{(1-best['obj']/o0)*100:.1f}%; v1 was 5038)")
    for ds, v in sorted(per_dataset(np.array(best["x"])).items()):
        print(f"   BEST {ds.replace('jump_',''):14s} q1={v[0]:.3f} q2={v[1]:.3f} dq1={v[2]:.2f} dq2={v[3]:.2f}")
    print("PARAMS:", {NAMES[i]: round(best["x"][i], 4) for i in range(len(NAMES))})


if __name__ == "__main__":
    main()
