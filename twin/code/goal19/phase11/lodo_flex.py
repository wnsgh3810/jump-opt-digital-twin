"""GOAL19 Phase 11f — Leave-One-Dataset-Out generalization check for the flex model.

For each held-out jump dataset D: refit the 12-D params on all trials EXCEPT D,
then score D (held-out). Compare held-out mean score to the all-data model's mean
on D. ratio ~1 => generalizes; ratio >>1 => the re-param overfit to D.

Shorter CMA (72 evals) per fold. Saves json.
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
BASE_X = np.array(FM["mass_15d"]); FR = FM["friction"]; CT = FM["contact"]; FL = FM["joint_flex"]
LAM_GRF = 2.0
ALL = list(list_experiments())
HOLDOUTS = ["jump_0424", "jump_0602", "jump_position_0421", "jump_torque_0422"]

SPEC = [  # name, warm, lo, hi  (warm = current final)
    ("stiff_knee", FL["stiff_knee"], 0.60, 2.00), ("solref_tc", CT["solref_tc"], 0.0018, 0.0060),
    ("imp0", CT["imp0"], 0.08, 0.45), ("m_foot_ex", FM["m_foot_ex"], 0.00, 0.15),
    ("M_base_s", BASE_X[0], 0.90, 1.35), ("M_p_s", BASE_X[3], 0.80, 1.50),
    ("M_calf_s", BASE_X[2], 0.75, 1.15), ("com_dz_calf", BASE_X[12], -0.025, 0.005),
    ("arm_knee", BASE_X[14], 0.010, 0.025), ("fv_hip", FR["fv_hip"], 0.30, 1.20),
    ("fv_knee", FR["fv_knee"], 0.00, 0.50), ("fc_knee", FR["fc_knee"], 0.20, 1.00),
]
NAMES = [s[0] for s in SPEC]
X0 = np.clip(np.array([s[1] for s in SPEC]), [s[2] for s in SPEC], [s[3] for s in SPEC])
LO = np.array([s[2] for s in SPEC]); HI = np.array([s[3] for s in SPEC])


def set_params(x):
    d = dict(zip(NAMES, x)); xm = BASE_X.copy()
    xm[5] = d["m_foot_ex"]; xm[0] = d["M_base_s"]; xm[3] = d["M_p_s"]
    xm[2] = d["M_calf_s"]; xm[12] = d["com_dz_calf"]; xm[14] = d["arm_knee"]
    ap = P4.apply_phase1_params(xm)
    S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = d["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return d


def score_set(x, subset):
    d = set_params(x); tot = 0.0; grf = 0.0; n = 0
    for ds, sub, isj in subset:
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, d["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        tot += v; n += 1
        if isj and m:
            grf += m.get("rmse_grf", 0)
    return tot, grf, n


def fit(train):
    import cma
    x0n = (X0 - LO) / (HI - LO)
    es = cma.CMAEvolutionStrategy(x0n, 0.18, {"bounds": [0, 1], "maxfevals": 72, "popsize": 12, "seed": 5, "verbose": -9})
    best = (1e18, X0)
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LO + np.array(sn) * (HI - LO)
            t, g, _ = score_set(x, train); o = t + LAM_GRF * g
            objs.append(o)
            if o < best[0]:
                best = (o, x)
        es.tell(sols, objs)
    return best[1]


def main():
    # all-data model mean per dataset (reference)
    ref = {}
    for D in HOLDOUTS:
        sub = [e for e in ALL if e[0] == D]
        t, _, n = score_set(X0, sub); ref[D] = t / n
    print("all-data model per-dataset mean:", {k: round(v, 1) for k, v in ref.items()}, flush=True)
    results = {}
    for D in HOLDOUTS:
        train = [e for e in ALL if e[0] != D]
        heldout = [e for e in ALL if e[0] == D]
        xstar = fit(train)
        t, _, n = score_set(xstar, heldout)
        ho_mean = t / n
        results[D] = dict(heldout_mean=ho_mean, alldata_mean=ref[D], ratio=ho_mean / ref[D])
        print(f"LODO {D}: held-out mean={ho_mean:.1f} vs all-data {ref[D]:.1f} => ratio {ho_mean/ref[D]:.3f}", flush=True)
    out = REPO / "code/goal19/phase11/lodo_flex_result.json"
    json.dump(results, open(out, "w", encoding="utf-8"), indent=2)
    ratios = [r["ratio"] for r in results.values()]
    print(f"\nGENERALIZATION: mean ratio {np.mean(ratios):.3f}, max {np.max(ratios):.3f}  (~1 good, >>1 overfit)")
    print("SAVED", out)


if __name__ == "__main__":
    main()
