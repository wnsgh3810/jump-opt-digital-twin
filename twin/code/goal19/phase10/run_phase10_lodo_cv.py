"""Phase 10 - Leave-One-Dataset-Out cross-validation (generalization vs overfit).

The final model was fit on ALL 31 exp. Is it a genuine digital twin or overfit?
LODO-CV: for each of the 7 date-datasets, refit the 3 key params
  (M_foot_ex, fv_hip, fc_knee)  — the ones Phase 4 showed drive the fit —
on the OTHER datasets, then evaluate the held-out dataset. Compare held-out
per-exp mean score to the in-sample (full-model) per-exp mean.

If held-out ≈ in-sample → generalizes. If held-out >> in-sample → overfit.
Other 12 mass params + contact fixed at final (they are stable / physical).
"""
import sys, json, time
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
P1_X = np.array(FM["mass_15d"]); FR=FM["friction"]; CT=FM["contact"]

DATES = ["sit2stand_air_0319","sit2stand_gnd_0319","sit2stand_0324",
         "jump_position_0421","jump_torque_0422","jump_0424","jump_0602"]

# 3 key params: [M_foot_ex, fv_hip, fc_knee]
B3 = np.array([[0.0,0.40],[0.0,2.0],[0.0,2.0]])
DEFAULT3 = np.array([FM["m_foot_ex"], FR["fv_hip"], FR["fc_knee"]])


def apply(params3):
    m_foot, fv_hip, fc_knee = np.clip(params3, B3[:,0], B3[:,1])
    x = P1_X.copy(); x[5] = m_foot
    ap = P4.apply_phase1_params(x)
    S.FV_HIP=float(fv_hip); S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=float(fc_knee)
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


def eval_subset(params3, include=None, exclude=None):
    """Mean per-exp score over a subset of datasets."""
    ap = apply(params3)
    tot=0.0; n=0
    for ds, sub, isj in list_experiments():
        if include and ds not in include: continue
        if exclude and ds in exclude: continue
        try:
            s,_ = S.run_one_sub(ds, sub, 0.0, 0.0, 0.0, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s=None
        v = 5e5 if (s is None or not np.isfinite(s) or s>5e5) else float(s)
        tot += v; n += 1
    return tot/max(n,1), n


def refit_on(train_dates):
    """3D CMA-ES minimizing mean per-exp score over train datasets."""
    import cma
    lo,hi=B3[:,0],B3[:,1]; span=hi-lo
    to_n=lambda x:(x-lo)/span; from_n=lambda u:np.clip(u,0,1)*span+lo
    es=cma.CMAEvolutionStrategy(to_n(np.clip(DEFAULT3,lo,hi)),0.3,{
        'bounds':[[0.0]*3,[1.0]*3],'maxfevals':60,'popsize':7,'verbose':-9,'seed':21})
    best=(1e18,DEFAULT3.copy())
    while not es.stop():
        U=es.ask(); O=[]
        for u in U:
            p=from_n(u); m,_=eval_subset(p, include=train_dates); O.append(m)
            if m<best[0]: best=(m,p.copy())
        es.tell(U,O)
    return best[1]


def main():
    out = Path(__file__).resolve().parent
    print("[Phase 10] Leave-One-Dataset-Out CV (generalization test)")
    # In-sample per-exp mean per dataset (full final model)
    print("\nIn-sample (full model) per-exp mean by dataset:")
    insample={}
    for d in DATES:
        m,n = eval_subset(DEFAULT3, include=[d])
        insample[d]=m
        print(f"  {d:22s}: mean={m:8.1f} (n={n})")

    print("\nLODO: refit on other 6, evaluate held-out:")
    rows=[]
    for d in DATES:
        t0=time.time()
        train=[x for x in DATES if x!=d]
        p = refit_on(train)
        held,n = eval_subset(p, include=[d])
        ratio = held/insample[d] if insample[d] else 0
        print(f"  hold-out {d:22s}: held={held:8.1f} vs in-sample={insample[d]:8.1f}  ratio={ratio:.2f}  "
              f"refit(M_foot,fv_hip,fc_knee)=[{p[0]:.3f},{p[1]:.3f},{p[2]:.3f}]  ({time.time()-t0:.0f}s)")
        rows.append(dict(dataset=d, held_out=float(held), in_sample=float(insample[d]),
                         ratio=float(ratio), refit=p.tolist()))
        (out/"phase10_lodo_cv.json").write_text(json.dumps(dict(insample=insample, folds=rows), indent=2))

    ratios=[r["ratio"] for r in rows]
    print(f"\nMean held-out/in-sample ratio = {np.mean(ratios):.2f} (1.0=perfect generalization, >>1=overfit)")
    print(f"Written: {out/'phase10_lodo_cv.json'}")


if __name__ == "__main__":
    main()
