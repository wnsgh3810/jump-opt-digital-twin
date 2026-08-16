"""G20 — leave-one-date-out generalization of the FINAL four-bar model.

For each held-out date group: refit the 26-param model (warm from round-1 best,
short CMA) on the remaining dates, then evaluate the held-out date's windows.
Compare held-out error under LODO-fit vs under the full-fit round-1 best.
Ratio ~1 => the model generalizes (parameters are not date-specific memorization).
Note: held-out date keeps its own date-offsets from the full fit (offsets are
calibration constants, not dynamics — they cannot be predicted for an unseen session).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import mshoot as MS
import mshoot_fourbar_refit as FR

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
X_FULL = np.array(BEST["x"])
FOLDS = {"0324+0421": ["jump_0324", "jump_position_0421"],
         "0424": ["jump_0424"], "0602": ["jump_0602"]}


def eval_split(x, exclude):
    """Return (train_total, held_total) splitting FR.evaluate per-dataset results."""
    o, per = FR.evaluate(x)
    if per is None:
        return 9e9, 9e9
    tr = sum(v["score"] for ds, v in per.items() if ds not in exclude)
    hd = sum(v["score"] for ds, v in per.items() if ds in exclude)
    return tr, hd


def main():
    import cma
    _, held_full = {}, {}
    print("LODO of final four-bar model (warm from full best, 120 evals/fold)", flush=True)
    for name, hdsets in FOLDS.items():
        tr0, hd0 = eval_split(X_FULL, hdsets)
        x0n = (X_FULL - FR.LOb) / (FR.HIb - FR.LOb)
        es = cma.CMAEvolutionStrategy(np.clip(x0n, 0, 1), 0.10,
                                      {"bounds": [0, 1], "maxfevals": 120, "popsize": 10,
                                       "seed": 41, "verbose": -9})
        best = dict(obj=tr0, x=X_FULL.copy())
        while not es.stop():
            sols = es.ask(); objs = []
            for sn in sols:
                x = FR.LOb + np.array(sn) * (FR.HIb - FR.LOb)
                trs, _ = eval_split(x, hdsets)
                objs.append(trs)
                if trs < best["obj"]:
                    best = dict(obj=trs, x=x.copy())
            es.tell(sols, objs)
        _, hd1 = eval_split(best["x"], hdsets)
        print(f"fold {name:>10}: held-out {hd0:.0f}(full-fit) vs {hd1:.0f}(LODO-fit)  "
              f"ratio={hd1/hd0:.3f}  train {tr0:.0f}->{best['obj']:.0f}", flush=True)


if __name__ == "__main__":
    main()
