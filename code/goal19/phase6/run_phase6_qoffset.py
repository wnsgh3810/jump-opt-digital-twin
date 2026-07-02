"""Phase 6 - q_offset ablation: per-trial vs date-group vs zero.

User wants to AVOID per-trial fudge. Current model uses per-trial iter1 offsets
(31x2 = 62 fudge params). This quantifies how much the fudge contributes and
whether date-group (6x2=12) or zero offsets can replace it.

Base = Phase 4 adopted model.
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

AM = json.load(open(REPO/"code/goal19/phase4/phase4_adopted_model.json"))
P1_X = np.array(AM["mass_15d"]); P1_X[5] = AM["m_foot_ex_override"]
FR = AM["friction"]; CT = AM["contact"]

# Per-trial offsets (current)
PER_TRIAL = dict(P4.OFFSET_MAP)

# Date-group mean offsets
def date_of(ds):
    if "0319" in ds: return "0319"
    if "0324" in ds: return "0324"
    if "0421" in ds: return "0421"
    if "0422" in ds: return "0422"
    if "0424" in ds: return "0424"
    if "0602" in ds: return "0602"
    return "?"

groups = {}
for (ds, sub), (o1, o2) in PER_TRIAL.items():
    g = date_of(ds); groups.setdefault(g, []).append((o1, o2))
DATE_GROUP = {}
for (ds, sub) in PER_TRIAL:
    g = date_of(ds)
    arr = np.array(groups[g])
    DATE_GROUP[(ds, sub)] = (float(arr[:,0].mean()), float(arr[:,1].mean()))

ZERO = {k: (0.0, 0.0) for k in PER_TRIAL}


def apply_adopted():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=FR["fv_hip"]; S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


def eval_with_offsets(offmap):
    ap = apply_adopted()
    s2s=0.0; jmp=0.0
    for ds, sub, isj in list_experiments():
        q1, q2 = offmap.get((ds, sub), (0.0, 0.0))
        try:
            s, _ = S.run_one_sub(ds, sub, q1, q2, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s = None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        if isj: jmp += v
        else: s2s += v
    return s2s+jmp, s2s, jmp


def main():
    out = Path(__file__).resolve().parent
    print("[Phase 6] q_offset ablation (per-trial vs date-group vs zero)")
    res={}
    for name, omap in [("per_trial (current, 62 fudge)", PER_TRIAL),
                       ("date_group (12 fudge)", DATE_GROUP),
                       ("zero (0 fudge)", ZERO)]:
        t0=time.time()
        tot, s2s, jmp = eval_with_offsets(omap)
        print(f"  {name:32s}: total={tot:8.0f}  s2s={s2s:7.0f}  jump={jmp:7.0f}  ({time.time()-t0:.0f}s)")
        res[name]=dict(total=tot, s2s=s2s, jump=jmp)
    base = res["per_trial (current, 62 fudge)"]["total"]
    print(f"\nDate-group cost vs per-trial: {100*(res['date_group (12 fudge)']['total']-base)/base:+.1f}%")
    print(f"Zero cost vs per-trial:       {100*(res['zero (0 fudge)']['total']-base)/base:+.1f}%")
    (out/"phase6_qoffset.json").write_text(json.dumps(dict(
        results=res, date_group_offsets={f"{k[0]}/{k[1]}": v for k,v in DATE_GROUP.items()}), indent=2, default=float))
    print(f"Written: {out/'phase6_qoffset.json'}")


if __name__ == "__main__":
    main()
