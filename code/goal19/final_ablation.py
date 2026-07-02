"""GOAL19 final ablation + per-exp breakdown with FINAL unified model (zero offset)."""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
for p in ["templates","data_loaders","phase1","phase2","phase3","phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))

import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

FM = json.load(open(REPO/"code/goal19/goal19_final_model.json"))
P1_X = np.array(FM["mass_15d"]); P1_X[5] = FM["m_foot_ex"]
FR = FM["friction"]; CT = FM["contact"]


def apply_final():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=FR["fv_hip"]; S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


def main():
    out = REPO/"code/goal19"
    ap = apply_final()
    rows=[]; total=0.0
    for ds, sub, isj in list_experiments():
        # zero offset (final)
        s, m = S.run_one_sub(ds, sub, 0.0, 0.0, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
        total += float(s)
        r = dict(ds=ds, sub=sub, is_jump=isj, score=float(s))
        for k,v in (m or {}).items():
            if isinstance(v,(int,float,np.floating,np.integer)): r[k]=float(v)
        rows.append(r)
    print(f"FINAL model total = {total:.2f}")

    # Ablation table (from committed jsons)
    ablation = [
        dict(phase=0, name="Pure CAD Baseline", score=41271.18, note="CAD only, no fudge"),
        dict(phase=1, name="+ robot dynamics (15D mass/inertia/CoM)", score=20367.75, note="-50.6%; foot mass + knee armature dominate"),
        dict(phase=2, name="+ joint friction (fv/fc 4D)", score=15744.40, note="-22.7%; hip viscous + knee Coulomb; stabilized sit2stand_gnd"),
        dict(phase=3, name="+ contact (solref/imp0)", score=15329.66, note="+2.6%; stiffer contact"),
        dict(phase=4, name="+ frontier re-opt (lambda=1)", score=15189.0, note="joint re-opt beats sequential"),
        dict(phase=6, name="- per-trial q_offset (62->0 fudge)", score=15182.0, note="fudge eliminated at zero cost"),
    ]
    out_json = dict(final_total=total, final_model=FM, per_exp=rows, ablation=ablation,
                    cumulative_pct=100*(41271.18-total)/41271.18)
    (out/"final_ablation.json").write_text(json.dumps(out_json, indent=2))

    # Per-group summary
    import collections
    agg = collections.defaultdict(lambda: dict(n=0, score=0, hs=0, hr=0))
    for r in rows:
        g = 'sit2stand' if not r['is_jump'] else r['ds']
        a=agg[g]; a['n']+=1; a['score']+=r['score']
        if r['is_jump']: a['hs']+=r.get('h_sim_m',0); a['hr']+=r.get('h_real_m',0)
    print(f"\n{'group':22s} {'n':>3s} {'score':>8s} {'mean':>7s} {'h_ratio':>8s}")
    for g,a in sorted(agg.items(), key=lambda x:-x[1]['score']):
        hr = a['hs']/a['hr'] if a['hr'] else 0
        print(f"{g:22s} {a['n']:3d} {a['score']:8.0f} {a['score']/a['n']:7.0f} {hr if hr else 0:8.3f}")
    print(f"\nWritten: {out/'final_ablation.json'}")


if __name__ == "__main__":
    main()
