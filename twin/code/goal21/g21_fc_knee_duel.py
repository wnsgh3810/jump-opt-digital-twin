"""GOAL21 P3 — does the energy-identified ~0.9 Nm knee output loss survive the
multiple-shooting duel?  Sweep fc_knee in the canonical twin, full-dataset score.

Energy ladder said: constant joint-output loss a ~ 0.9 Nm collapses air/s2s/jump
efficiencies onto one law (eta = 1 - a/|tau|).  MuJoCo frictionloss IS that term.
Canonical has fc_knee = 0.057 -> 15x smaller.  If the ladder is real and replay-
relevant, some fc_knee > canonical should win the window score; per-dataset
breakdown shows who pays (stiff under-whip dates should worsen, bug over-whip
dates improve, s2s improve).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import mshoot as MS
import sub_sim_iter6v2 as S
from apply_final_and_regen import apply_final

ap = apply_final()
FC0 = S.FC_KNEE
print(f"canonical fc_knee = {FC0}", flush=True)
res = {}
for fck in [FC0, 0.3, 0.6, 0.9, 1.2]:
    S.FC_KNEE = fck
    total, per = MS.evaluate_all(ap["arm_hip"], ap["arm_knee"])
    res[f"{fck:.3f}"] = dict(total=float(total),
                             per={k: float(v["score"]) for k, v in per.items()})
    line = "  ".join(f"{k}:{v['score']:.0f}" for k, v in per.items())
    print(f"fc_knee={fck:.3f}  TOTAL={total:.0f}   {line}", flush=True)
json.dump(res, open(REPO / "code/goal21/fc_knee_duel.json", "w"), indent=1)
print("saved fc_knee_duel.json")
