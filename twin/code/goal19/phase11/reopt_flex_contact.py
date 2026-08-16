"""GOAL19 Phase 11 — joint re-opt of (stiff_knee, solref_tc, imp0, m_foot_ex).

Rationale: knee flex (sk=1.15) was added AFTER contact/mass were fit, and it
re-excited contact-solver GRF chatter. The old contact + heavy foot were fit
WITHOUT flex, so their optimum has shifted. Re-optimize these 4 together.

Objective = total_score + LAM_GRF * sum(jump rmse_grf)   [GRF weighted up so the
optimizer smooths the chatter rather than ignoring it under Wgrf=0.1].

CMA-ES, warm-started at current final model. Prints running best; saves json.
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
P1_X = np.array(FM["mass_15d"]); FR = FM["friction"]
LAM_GRF = 2.0

# param order: stiff_knee, solref_tc, imp0, m_foot_ex
X0 = np.array([1.15, FM["contact"]["solref_tc"], FM["contact"]["imp0"], FM["m_foot_ex"]])
LO = np.array([0.5, 0.0015, 0.10, 0.00])
HI = np.array([2.5, 0.0120, 0.60, 0.30])


def evaluate(x):
    sk, srtc, imp0, mfx = [float(v) for v in x]
    xm = P1_X.copy(); xm[5] = mfx
    ap = P4.apply_phase1_params(xm)
    S.FV_HIP = FR["fv_hip"]; S.FV_KNEE = FR["fv_knee"]
    S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = FR["fc_knee"]
    S.SOLREF_TC_LOCK = srtc; S.IMP0_LOCK = imp0
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = sk
    tot = 0.0; grf = 0.0; hs = 0.0; hr = 0.0
    for ds, sub, isj in list_experiments():
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        tot += v
        if isj and m:
            grf += m.get("rmse_grf", 0); hs += m.get("h_sim_m", 0); hr += m.get("h_real_m", 0)
    obj = tot + LAM_GRF * grf
    return obj, tot, grf, (hs / hr if hr else 0)


def main():
    import cma
    x0n = (X0 - LO) / (HI - LO)  # normalize to [0,1]
    es = cma.CMAEvolutionStrategy(x0n, 0.20, {"bounds": [0, 1], "maxfevals": 120,
                                              "popsize": 10, "seed": 7, "verbose": -9})
    best = dict(obj=1e18)
    gen = 0
    while not es.stop():
        sols = es.ask()
        objs = []
        for sn in sols:
            x = LO + np.array(sn) * (HI - LO)
            obj, tot, grf, hrat = evaluate(x)
            objs.append(obj)
            if obj < best["obj"]:
                best = dict(obj=obj, total=tot, grf=grf, h_ratio=hrat,
                            x=[float(v) for v in x],
                            names=["stiff_knee", "solref_tc", "imp0", "m_foot_ex"])
                print(f"  NEW BEST obj={obj:.0f} total={tot:.0f} grf={grf:.0f} "
                      f"h={hrat:.3f}  sk={x[0]:.3f} srtc={x[1]:.5f} imp0={x[2]:.3f} mfx={x[3]:.3f}",
                      flush=True)
        es.tell(sols, objs)
        gen += 1
        print(f"gen {gen}: best_obj={best['obj']:.0f} (total={best['total']:.0f} grf={best['grf']:.0f})", flush=True)
    out = REPO / "code/goal19/phase11/reopt_flex_contact_best.json"
    json.dump(dict(best=best, lam_grf=LAM_GRF, baseline=dict(total=11572, grf=970)),
              open(out, "w", encoding="utf-8"), indent=2)
    print("\nSAVED", out)
    print("BEST:", json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
