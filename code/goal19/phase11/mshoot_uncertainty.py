"""G20 — parameter uncertainty via 1%-iso-score intervals (no fake statistics).

The window score is not a calibrated likelihood, so instead of pseudo-sigmas we
report the honest, decision-relevant quantity: how far each parameter can move
from the round-1 optimum before the total window score degrades by 1%.
Quadratic model per axis from +/-delta probes:  ds(p) ~ 0.5*k*(p-p0)^2
  -> iso1% halfwidth = sqrt(2*0.01*S0/k).
Tight interval = strongly identified; huge interval = flat direction (identified
only weakly by this data — honest error bar for the report).
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
import mshoot_fourbar_refit as FR

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
X0 = np.array(BEST["x"]); NAMES = BEST["names"]

PROBE = {   # param -> absolute probe delta (small but resolvable)
    "arm_knee": 0.0008, "stiff_knee": 0.10, "M_calf": 0.05, "M_c": 0.05,
    "M_thigh": 0.05, "fv_hip": 0.05, "fv_knee": 0.005, "fc_knee": 0.02,
    "solref_tc": 0.0008, "imp0": 0.03,
    "o1_0324": np.deg2rad(0.5), "o2_0324": np.deg2rad(0.5),
    "o1_0424": np.deg2rad(0.5), "o2_0424": np.deg2rad(0.5),
}


def main():
    S0, _ = FR.evaluate(X0)
    print(f"S0 = {S0:.0f}", flush=True)
    rows = []
    for pname, dlt in PROBE.items():
        i = NAMES.index(pname)
        xp = X0.copy(); xp[i] += dlt
        xm = X0.copy(); xm[i] -= dlt
        sp, _ = FR.evaluate(xp)
        sm, _ = FR.evaluate(xm)
        k = (sp + sm - 2 * S0) / dlt ** 2          # curvature
        grad = (sp - sm) / (2 * dlt)
        if k <= 0:
            half = float("inf")
        else:
            half = float(np.sqrt(2 * 0.01 * S0 / k))
        p0 = X0[i]
        rel = 100 * half / abs(p0) if abs(p0) > 1e-9 else float("nan")
        rows.append(dict(param=pname, value=float(p0), iso1_half=half, rel_pct=rel,
                         grad=float(grad), curv=float(k)))
        deg = " (deg)" if pname.startswith("o") else ""
        v0 = np.rad2deg(p0) if pname.startswith("o") else p0
        hw = np.rad2deg(half) if (pname.startswith("o") and np.isfinite(half)) else half
        print(f"{pname:<11} = {v0:8.4f}{deg}  +/- {hw:8.4f}  ({rel:6.1f}% rel)  "
              f"curv={k:.3g} grad={grad:.3g}", flush=True)
    json.dump(rows, open(REPO / "code/goal19/phase11/uncertainty_iso1.json", "w"), indent=1)
    print("saved uncertainty_iso1.json")


if __name__ == "__main__":
    main()
