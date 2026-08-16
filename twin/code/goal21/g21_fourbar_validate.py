"""GOAL21 P5 final judge — gallery-metric comparison: canonical vs hybrid-selected.

Selection: from fourbar_hybrid_cands.jsonl pick min obj subject to held-out
fs_0324 rel <= 1.0. Judge: FB.validate_fulltraj (FULL replay incl. settle,
per-date q/dq RMSE in canonical frame + h_ratio) — the gallery numbers.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR

OFFDS = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
         "jump_0424": ("o1_0424", "o2_0424")}


def run(name, x, names):
    dd = dict(zip(names, x))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    offs = {ds: (dd[k1], dd[k2]) for ds, (k1, k2) in OFFDS.items()}
    r = FB.validate_fulltraj(dd["arm_knee"], dd, offs)
    print(f"\n=== {name} (full-replay, gallery metric) ===")
    print(f"{'dataset':<22}{'q1 deg':>8}{'q2 deg':>8}{'dq1':>7}{'dq2':>7}{'h_ratio':>9}")
    for ds, v in r.items():
        print(f"{ds:<22}{np.degrees(v['q1']):>8.2f}{np.degrees(v['q2']):>8.2f}"
              f"{v['dq1']:>7.2f}{v['dq2']:>7.2f}{v['h_ratio']:>9.3f}")
    return {ds: {k: float(vv) for k, vv in v.items()} for ds, v in r.items()}


def main():
    can = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    # select candidate: min obj s.t. heldout <= 1.0
    best = None
    for ln in open(REPO / "code/goal21/fourbar_hybrid_cands.jsonl"):
        c = json.loads(ln)
        if c["heldout"] <= 1.0 and (best is None or c["obj"] < best["obj"]):
            best = c
    print(f"selected candidate: obj={best['obj']:.4f} heldout={best['heldout']:.3f}")
    out = {}
    out["canonical"] = run("CANONICAL", can["x"], can["names"])
    out["hybrid"] = run(f"HYBRID-selected (obj {best['obj']:.3f})", best["x"], can["names"])
    out["selected"] = best
    json.dump(out, open(REPO / "code/goal21/fourbar_hybrid_validate.json", "w"), indent=1)
    print("\nsaved fourbar_hybrid_validate.json")


if __name__ == "__main__":
    main()
