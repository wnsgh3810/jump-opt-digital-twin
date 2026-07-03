"""GOAL19 Phase 11j — WIDE-RANGE UNIFIED re-fit (CAD-assembly-error hypothesis).

User insight: per-trial fitting is the problem, NOT wide ranges. And the CAD
per-part masses may have accumulated large error during ASSEMBLY (4-bar mechanism
mass mis-lumped into thigh/calf). So: keep ONE unified param set (no per-trial), but
WIDEN the mass/inertia/CoM bounds far beyond +-25%, and see if a single physical-ish
set closes the under-jump WHILE still generalizing (LODO checked separately).

Legit if: closes under-jump + LODO ~1. Overfit if: only aggregate improves + LODO blows up.
Geometry (L1=L2=0.25, LC, foot) stays LOCKED — only mass/inertia/CoM widen.
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

FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))
BASE = np.array(FM["mass_15d"]); FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
LAM_GRF = 2.0
OUT = REPO / "code/goal19/phase11/reopt_wide_unified_best.json"

# name, mass_15d idx (or None), warm, lo, hi   — WIDE bounds
SPEC = [
    ("M_base",  0, BASE[0], 0.40, 1.50), ("M_thigh", 1, BASE[1], 0.40, 1.50),
    ("M_calf",  2, BASE[2], 0.30, 1.50), ("M_p",     3, BASE[3], 0.40, 1.60),
    ("M_c",     4, BASE[4], 0.40, 1.60), ("I_thigh", 6, BASE[6], 0.30, 2.00),
    ("I_calf",  7, BASE[7], 0.30, 2.00), ("I_p",     8, BASE[8], 0.30, 2.00),
    ("I_c",     9, BASE[9], 0.30, 2.00), ("com_dz_th", 10, BASE[10], -0.04, 0.04),
    ("com_dz_ca", 12, BASE[12], -0.04, 0.04), ("arm_knee", 14, BASE[14], 0.008, 0.030),
    ("m_foot",  "mf", FM["m_foot_ex"], 0.00, 0.40),
    ("stiff_knee", "sk", FL["stiff_knee"], 0.50, 2.50),
    ("solref_tc", "sr", CT["solref_tc"], 0.0018, 0.0060),
    ("imp0", "im", CT["imp0"], 0.08, 0.45),
    ("fv_hip", "fvh", FR["fv_hip"], 0.20, 1.20),
    ("fv_knee", "fvk", FR["fv_knee"], 0.00, 0.60),
    ("fc_knee", "fck", FR["fc_knee"], 0.20, 1.20),
]
NAMES = [s[0] for s in SPEC]
X0 = np.clip(np.array([s[2] for s in SPEC]), [s[3] for s in SPEC], [s[4] for s in SPEC])
LO = np.array([s[3] for s in SPEC]); HI = np.array([s[4] for s in SPEC])
ALL = list(list_experiments())


def evaluate(x):
    d = dict(zip(NAMES, x)); xm = BASE.copy()
    for nm, idx, *_ in SPEC:
        if isinstance(idx, int):
            xm[idx] = d[nm]
    xm[5] = d["m_foot"]
    ap = P4.apply_phase1_params(xm)
    S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = d["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    tot = 0.0; grf = 0.0; hs = 0.0; hr = 0.0; nan = 0
    for ds, sub, isj in ALL:
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, d["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        if v >= 5e5: nan += 1
        tot += v
        if isj and m:
            grf += m.get("rmse_grf", 0); hs += m.get("h_sim_m", 0); hr += m.get("h_real_m", 0)
    return tot + LAM_GRF * grf, tot, grf, (hs / hr if hr else 0), nan


def main():
    import cma
    x0n = (X0 - LO) / (HI - LO)
    es = cma.CMAEvolutionStrategy(x0n, 0.22, {"bounds": [0, 1], "maxfevals": 240,
                                              "popsize": 16, "seed": 3, "verbose": -9})
    o, t, g, h, n = evaluate(X0)
    best = dict(obj=o, total=t, grf=g, h_ratio=h, x=[float(v) for v in X0], names=NAMES)
    print(f"WARM total={t:.0f} grf={g:.0f} h={h:.3f} nan={n}", flush=True)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LO + np.array(sn) * (HI - LO)
            o, t, g, h, n = evaluate(x)
            objs.append(o if n == 0 else o + 1e5 * n)
            if n == 0 and o < best["obj"]:
                best = dict(obj=o, total=t, grf=g, h_ratio=h, x=[float(v) for v in x], names=NAMES)
                print(f"  NEW BEST total={t:.0f} grf={g:.0f} h={h:.3f}", flush=True)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best_total={best['total']:.0f} h={best['h_ratio']:.3f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print("\nSAVED", OUT); print(json.dumps({k: best[k] for k in ['total','grf','h_ratio']}, indent=2))
    print("PARAMS:", {NAMES[i]: round(best['x'][i], 4) for i in range(len(NAMES))})


if __name__ == "__main__":
    main()
