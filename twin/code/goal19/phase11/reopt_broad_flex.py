"""GOAL19 Phase 11d — BROAD joint re-fit in the flex regime.

The sequential phase fit (mass -> friction -> contact) is stale now that knee
flex was added and foot mass went to ~0. Individual-axis probes (arm_knee,
I_calf, springref) all trade height vs dq2 vs total. So re-fit the 12 most
impactful params TOGETHER, warm-started at the current model, to find the true
unified optimum and establish the floor of the flex regime.

Objective = total + LAM_GRF * sum(jump rmse_grf)  (keep GRF smooth).
CMA-ES, ~180 evals. Saves best incrementally.
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
BASE_X = np.array(FM["mass_15d"]); BASE_X[5] = FM["m_foot_ex"]
FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
LAM_GRF = 2.0
OUT = REPO / "code/goal19/phase11/reopt_broad_flex_best.json"

# names, warm-start, lo, hi
SPEC = [
    ("stiff_knee",   FL["stiff_knee"],      0.60, 2.00),
    ("solref_tc",    CT["solref_tc"],       0.0018, 0.0060),
    ("imp0",         CT["imp0"],            0.08, 0.45),
    ("m_foot_ex",    FM["m_foot_ex"],       0.00, 0.15),
    ("M_base_s",     BASE_X[0],             0.90, 1.35),
    ("M_p_s",        BASE_X[3],             0.80, 1.50),
    ("M_calf_s",     BASE_X[2],             0.75, 1.15),
    ("com_dz_calf",  BASE_X[12],           -0.025, 0.005),
    ("arm_knee",     BASE_X[14],            0.010, 0.025),  # >=0.010 for stability
    ("fv_hip",       FR["fv_hip"],          0.30, 1.20),
    ("fv_knee",      FR["fv_knee"],         0.00, 0.50),
    ("fc_knee",      FR["fc_knee"],         0.20, 1.00),
]
NAMES = [s[0] for s in SPEC]
X0 = np.array([s[1] for s in SPEC]); LO = np.array([s[2] for s in SPEC]); HI = np.array([s[3] for s in SPEC])
X0 = np.clip(X0, LO, HI)


def evaluate(x):
    d = dict(zip(NAMES, x))
    xm = BASE_X.copy()
    xm[5] = d["m_foot_ex"]; xm[0] = d["M_base_s"]; xm[3] = d["M_p_s"]
    xm[2] = d["M_calf_s"]; xm[12] = d["com_dz_calf"]; xm[14] = d["arm_knee"]
    ap = P4.apply_phase1_params(xm)
    S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]
    S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = d["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    tot = 0.0; grf = 0.0; hs = 0.0; hr = 0.0
    for ds, sub, isj in list_experiments():
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, d["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        tot += v
        if isj and m:
            grf += m.get("rmse_grf", 0); hs += m.get("h_sim_m", 0); hr += m.get("h_real_m", 0)
    return tot + LAM_GRF * grf, tot, grf, (hs / hr if hr else 0)


def main():
    import cma
    x0n = (X0 - LO) / (HI - LO)
    es = cma.CMAEvolutionStrategy(x0n, 0.18, {"bounds": [0, 1], "maxfevals": 200,
                                              "popsize": 12, "seed": 11, "verbose": -9})
    best = dict(obj=1e18)
    # seed the warm-start explicitly first
    o, t, g, h = evaluate(X0)
    best = dict(obj=o, total=t, grf=g, h_ratio=h, x=[float(v) for v in X0], names=NAMES, warm=True)
    print(f"WARM total={t:.0f} grf={g:.0f} h={h:.3f} obj={o:.0f}", flush=True)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LO + np.array(sn) * (HI - LO)
            o, t, g, h = evaluate(x)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=o, total=t, grf=g, h_ratio=h, x=[float(v) for v in x], names=NAMES)
                print(f"  NEW BEST obj={o:.0f} total={t:.0f} grf={g:.0f} h={h:.3f}", flush=True)
                json.dump(dict(best=best, lam_grf=LAM_GRF), open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best_total={best['total']:.0f} grf={best['grf']:.0f} h={best['h_ratio']:.3f}", flush=True)
    json.dump(dict(best=best, lam_grf=LAM_GRF), open(OUT, "w", encoding="utf-8"), indent=2)
    print("\nSAVED", OUT)
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
