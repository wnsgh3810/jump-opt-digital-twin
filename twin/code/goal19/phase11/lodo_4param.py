"""LODO for the CLEANER 4-param model (11c: stiff_knee, solref_tc, imp0, m_foot_ex)
on top of the ORIGINAL physically-grounded mass/friction (pre-broad-refit).
Compares generalization vs the 12-D broad re-fit (LODO ratio 1.37)."""
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
# ORIGINAL physically-grounded base (pre-broad-refit values):
BASE_X = np.array(FM["mass_15d"]).copy()
BASE_X[0] = 1.1515772718093662   # M_base (11c)
BASE_X[2] = 0.9056234978136585   # M_calf
BASE_X[3] = 1.410583919223634    # M_p
BASE_X[12] = -0.017879151477970524  # com_dz_calf
BASE_X[14] = 0.01995192315480968    # arm_knee
FR = dict(fv_hip=0.7872008105393102, fv_knee=0.1270313864143112,
          fc_hip=0.09467027772217118, fc_knee=0.5241222129696196)
LAM_GRF = 2.0
ALL = list(list_experiments())
HOLDOUTS = ["jump_0424", "jump_0602", "jump_position_0421", "jump_torque_0422"]
# free params: stiff_knee, solref_tc, imp0, m_foot_ex  (11c warm start)
NAMES = ["stiff_knee", "solref_tc", "imp0", "m_foot_ex"]
X0 = np.array([1.2019, 0.002583, 0.14705, 0.00115])
LO = np.array([0.6, 0.0018, 0.08, 0.0]); HI = np.array([2.5, 0.006, 0.45, 0.15])


def set_params(x):
    d = dict(zip(NAMES, x)); xm = BASE_X.copy(); xm[5] = d["m_foot_ex"]
    ap = P4.apply_phase1_params(xm)
    S.FV_HIP = FR["fv_hip"]; S.FV_KNEE = FR["fv_knee"]; S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = FR["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return ap


def score_set(x, subset):
    ap = set_params(x); tot = 0.0; grf = 0.0; n = 0
    for ds, sub, isj in subset:
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, ap["arm_knee"], motor_tm=0.0)
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
    es = cma.CMAEvolutionStrategy(x0n, 0.20, {"bounds": [0, 1], "maxfevals": 60, "popsize": 10, "seed": 5, "verbose": -9})
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
    ref = {}
    for D in HOLDOUTS:
        sub = [e for e in ALL if e[0] == D]
        t, _, n = score_set(X0, sub); ref[D] = t / n
    print("4-param (11c) all-data per-dataset mean:", {k: round(v, 1) for k, v in ref.items()}, flush=True)
    res = {}
    for D in HOLDOUTS:
        train = [e for e in ALL if e[0] != D]; heldout = [e for e in ALL if e[0] == D]
        xstar = fit(train); t, _, n = score_set(xstar, heldout); ho = t / n
        res[D] = dict(heldout_mean=ho, alldata_mean=ref[D], ratio=ho / ref[D])
        print(f"LODO {D}: held-out {ho:.1f} vs {ref[D]:.1f} => ratio {ho/ref[D]:.3f}", flush=True)
    ratios = [r["ratio"] for r in res.values()]
    print(f"\n4-PARAM GENERALIZATION: mean ratio {np.mean(ratios):.3f}, max {np.max(ratios):.3f}")
    print("(compare 12-D broad refit: mean 1.366, max 1.595)")
    json.dump(res, open(REPO / "code/goal19/phase11/lodo_4param_result.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    main()
