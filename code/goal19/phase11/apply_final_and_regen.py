"""GOAL19 re-open FINAL (with knee joint flex): apply full model, breakdown, regen artifacts.

Full model = mass_15d + friction(4) + contact(2) + joint_flex(stiff_knee) + implicitfast integrator.
Produces: per-group breakdown json, 4-panel plots (jump reps), 2 canonical anims.
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
P1_X = np.array(FM["mass_15d"]); P1_X[5] = FM["m_foot_ex"]
FR = FM["friction"]; CT = FM["contact"]; FLEX = FM["joint_flex"]


def apply_final():
    """Set every S global for the full final model. Returns arm dict."""
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP = FR["fv_hip"]; S.FV_KNEE = FR["fv_knee"]
    S.FC_HIP = FR["fc_hip"]; S.FC_KNEE = FR["fc_knee"]
    S.SOLREF_TC_LOCK = CT["solref_tc"]; S.IMP0_LOCK = CT["imp0"]
    S.STIFF_HIP = FLEX["stiff_hip"]; S.STIFF_KNEE = FLEX["stiff_knee"]
    S.JUMP_INTEGRATOR = FM.get("jump_integrator", "implicitfast")
    return ap


def breakdown():
    ap = apply_final()
    rows = []; groups = {}
    for ds, sub, isj in list_experiments():
        try:
            s, m = S.run_one_sub(ds, sub, 0, 0, 0.0, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        hr = hs = None
        if isj and m:
            hs = m.get("h_sim_m", 0); hr = m.get("h_real_m", 0)
        rows.append(dict(ds=ds, sub=sub, is_jump=isj, score=v, h_sim=hs, h_real=hr))
        g = groups.setdefault(ds, dict(n=0, score=0.0, hs=0.0, hr=0.0, jump=isj))
        g["n"] += 1; g["score"] += v
        if isj and m:
            g["hs"] += hs; g["hr"] += hr
    total = sum(r["score"] for r in rows)
    return rows, groups, total


if __name__ == "__main__":
    rows, groups, total = breakdown()
    print(f"\n=== GOAL19 FINAL (knee flex sk={FLEX['stiff_knee']}) total = {total:.0f} ===\n")
    print(f"{'group':<22}{'n':>3}{'mean_score':>12}{'h_ratio':>10}")
    for ds in sorted(groups):
        g = groups[ds]
        hr = (g["hs"] / g["hr"]) if g["hr"] else 0
        hs = f"{hr:.3f}" if g["jump"] else "  —"
        print(f"{ds:<22}{g['n']:>3}{g['score']/g['n']:>12.1f}{hs:>10}")
    out = REPO / "code/goal19/phase11/final_flex_breakdown.json"
    json.dump(dict(total=total, groups={k: {kk: vv for kk, vv in v.items()} for k, v in groups.items()},
                   rows=rows, stiff_knee=FLEX["stiff_knee"]), open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nsaved {out}")
