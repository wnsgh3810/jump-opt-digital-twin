"""P10 그림만 재생성 (sim 재실행 없이 저장된 궤적 npz + p10_cl.json 사용)."""
import json
import numpy as np
from pathlib import Path
from g22_p10_cl import fig_trial, load_trial_xlsx
from g22_p10_pdlaw import SETS

TRAJ = Path(__file__).parent / "p10_cl_traj"
cl = json.load(open(Path(__file__).parent / "p10_cl.json"))
n = 0
for ds, (root, subs) in SETS.items():
    for sub in subs:
        key = f"{ds}/{sub}"
        if key not in cl:
            continue
        d = load_trial_xlsx(ds, root, sub)
        for tag in ["label", "fit"]:
            f = TRAJ / f"{ds}__{sub}__{tag}.npz"
            m = cl[key][tag]
            if not f.exists() or m is None:
                continue
            z = np.load(f)
            L = {k: z[k] for k in ["t", "q1", "q2", "dq1", "dq2", "sh1", "sh2", "grf", "bz"]}
            L["o"] = tuple(z["o"])
            fig_trial(ds, sub, d, L, m, tag)
            n += 1
        print("refig", key, flush=True)
print(f"DONE {n} figs", flush=True)
