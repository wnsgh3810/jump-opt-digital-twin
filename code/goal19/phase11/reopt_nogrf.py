"""GOAL19 Phase 11n — NO-GRF re-fit (user directive 2026-07-04).

User: GRF is unreliable (load cell nonlinear + Mar/Apr calibration wrong). Match
q, dq, tau, h only. h is camera-measured base-center apex (real). Drop GRF entirely.

=> Set W_GRF=0 and re-fit the unified physical param set on JUMP + sit2stand_GND
(sit2stand air is hard to match per user). Single unified set, geometry LOCKED,
physical bounds. arm_knee allowed down toward the physical reflected rotor inertia
(~0.005; AK80-9 rotor 6.05e-5 x gear 9^2) — the diagnostic showed the current 0.0206
over-damps the knee velocity spike (dq2 18 vs real 27), and lowering it recovers the
spike (dq2->26) AND raises h (0.68->0.74) — a physical correction, not a fudge.

Objective per exp = W_Q*(rq1+rq2) + W_DQ*(rdq1+rdq2) + W_H*|h_sim-h_real|  (NO GRF).
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

S.W_GRF = 0.0  # ★ drop GRF from the per-exp score

FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))
BASE = np.array(FM["mass_15d"]); FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
OUT = REPO / "code/goal19/phase11/reopt_nogrf_best.json"

# name, mass_15d idx (or tag), warm, lo, hi
SPEC = [
    ("M_base",   0, BASE[0], 0.60, 1.40), ("M_thigh", 1, BASE[1], 0.60, 1.40),
    ("M_calf",   2, BASE[2], 0.50, 1.40), ("M_p",     3, BASE[3], 0.60, 1.50),
    ("M_c",      4, BASE[4], 0.60, 1.50), ("I_thigh", 6, BASE[6], 0.40, 1.80),
    ("I_calf",   7, BASE[7], 0.40, 1.80), ("I_p",     8, BASE[8], 0.40, 1.80),
    ("I_c",      9, BASE[9], 0.40, 1.80), ("com_dz_th", 10, BASE[10], -0.04, 0.04),
    ("com_dz_ca", 12, BASE[12], -0.04, 0.04), ("arm_hip", 13, BASE[13], 0.0005, 0.010),
    ("arm_knee", 14, BASE[14], 0.003, 0.025),
    ("m_foot",   "mf", FM["m_foot_ex"], 0.00, 0.35),
    ("stiff_knee", "sk", FL["stiff_knee"], 0.00, 2.50),
    ("solref_tc", "sr", CT["solref_tc"], 0.0018, 0.0060),
    ("imp0",     "im", CT["imp0"], 0.08, 0.45),
    ("fv_hip",   "fvh", FR["fv_hip"], 0.10, 1.20),
    ("fv_knee",  "fvk", FR["fv_knee"], 0.00, 0.60),
    ("fc_knee",  "fck", FR["fc_knee"], 0.10, 1.20),
]
NAMES = [s[0] for s in SPEC]
X0 = np.clip(np.array([s[2] for s in SPEC]), [s[3] for s in SPEC], [s[4] for s in SPEC])
LO = np.array([s[3] for s in SPEC]); HI = np.array([s[4] for s in SPEC])
# JUMP + sit2stand_gnd only
ALL = [(ds, sub, isj) for ds, sub, isj in list_experiments()
       if isj or "gnd" in ds.lower() or "sit2stand_gnd" in ds.lower()]


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
    tot = 0.0; qsum = 0.0; dqsum = 0.0; hs = 0.0; hr = 0.0; nan = 0; nj = 0
    for ds, sub, isj in ALL:
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, d["arm_hip"], d["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        if v >= 5e5:
            nan += 1
        tot += v
        if m:
            qsum += m.get("rmse_q1", 0) + m.get("rmse_q2", 0)
            dqsum += m.get("rmse_dq1", 0) + m.get("rmse_dq2", 0)
            if isj:
                hs += m.get("h_sim_m", 0); hr += m.get("h_real_m", 0); nj += 1
    return tot, qsum, dqsum, (hs / hr if hr else 0), nan


def main():
    import cma
    o0, q0, dq0, h0, n0 = evaluate(X0)
    print(f"WARM (W_GRF=0): total={o0:.0f} q={q0:.2f} dq={dq0:.2f} h_ratio={h0:.3f} nan={n0}", flush=True)
    x0n = (X0 - LO) / (HI - LO)
    es = cma.CMAEvolutionStrategy(x0n, 0.20, {"bounds": [0, 1], "maxfevals": 200,
                                              "popsize": 14, "seed": 5, "verbose": -9})
    best = dict(obj=o0, q=q0, dq=dq0, h_ratio=h0, x=[float(v) for v in X0], names=NAMES)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LO + np.array(sn) * (HI - LO)
            o, q, dq, h, n = evaluate(x)
            objs.append(o if n == 0 else o + 1e5 * n)
            if n == 0 and o < best["obj"]:
                best = dict(obj=o, q=q, dq=dq, h_ratio=h, x=[float(v) for v in x], names=NAMES)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
                print(f"  NEW BEST total={o:.0f} q={q:.2f} dq={dq:.2f} h_ratio={h:.3f}", flush=True)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best_total={best['obj']:.0f} h_ratio={best['h_ratio']:.3f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print("\nSAVED", OUT)
    print("PARAMS:", {NAMES[i]: round(best["x"][i], 4) for i in range(len(NAMES))})


if __name__ == "__main__":
    main()
