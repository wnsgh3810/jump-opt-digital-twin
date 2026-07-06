"""G20 — user question: refit on 0424+0602 only (the deployment-mode datasets).

Fit set = jump_0424(9) + jump_0602(6) + s2s_gnd (kept for slow-regime coverage).
Excluded from FIT: jump_0324, jump_position_0421 (dq_des-bug era) — but still
EVALUATED afterwards to quantify what specializing costs.
Offsets clamped to physical +/-2 deg (canonical policy). Warm from o2deg best.
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

KEEP = ("jump_0424", "jump_0602", "s2s_gnd_0319")
OUT = REPO / "code/goal19/phase11/fourbar_refit_46only.json"
OLIM = np.deg2rad(2.0)

LOb = FR.LOb.copy(); HIb = FR.HIb.copy()
for i, n in enumerate(FR.NAMES):
    if n.startswith("o"):
        LOb[i], HIb[i] = -OLIM, OLIM

warm = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_o2deg.json", encoding="utf-8"))
X0 = np.clip(np.array(warm["x"]), LOb, HIb)


def main():
    import cma
    FR.GROUPS = [g for g in FR.all_groups() if g[0] in KEEP]
    o0, per0 = FR.evaluate(X0)
    print(f"WARM (subset fit metric) = {o0:.0f}", flush=True)
    x0n = (X0 - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n, 0.15, {"bounds": [0, 1], "maxfevals": 240,
                                              "popsize": 14, "seed": 7, "verbose": -9})
    best = dict(obj=float(o0), x=[float(v) for v in X0], names=FR.NAMES)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LOb + np.array(sn) * (HIb - LOb)
            o, _ = FR.evaluate(x)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), x=[float(v) for v in x], names=FR.NAMES)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best={best['obj']:.0f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"SUBSET FIT: {o0:.0f} -> {best['obj']:.0f} ({100*(best['obj']/o0-1):+.1f}%)")

    # ---- full-set comparison: what improved, what got worse -------------------
    FR.GROUPS = None
    xb = np.array(best["x"])
    _, perA = FR.evaluate(X0)     # baseline (round-1, offsets clamped)
    _, perB = FR.evaluate(xb)     # 46-only specialized
    print("\nper-dataset window score (baseline clamp2 -> 46only):")
    for ds in perA:
        a, b = perA[ds]["score"], perB[ds]["score"]
        print(f"  {ds:<22} {a:8.0f} -> {b:8.0f}  ({100*(b/a-1):+.1f}%)")
    dd = dict(zip(FR.NAMES, best["x"]))
    print("\nPARAM SHIFTS (vs round-1):")
    base = dict(zip(warm["names"], warm["x"]))
    for k in FR.NAMES:
        if not k.startswith("o") and abs(dd[k] - base[k]) > 1e-4:
            print(f"  {k:<12} {base[k]:8.4f} -> {dd[k]:8.4f}")

    # held-out full-traj h on the two kept datasets
    import mshoot_fourbar as FB
    import sub_sim_iter6v2 as S
    for tag, xx in (("baseline", X0), ("46only", xb)):
        d = dict(zip(FR.NAMES, xx))
        S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = d["fc_hip"]; S.FC_KNEE = d["fc_knee"]
        S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        res = FB.validate_fulltraj(d["arm_knee"], d, offs=None)
        hs = {ds: v["h_ratio"] for ds, v in res.items()}
        print(f"\n[{tag}] held-out h_ratio:", {k: round(v, 3) for k, v in hs.items()})


if __name__ == "__main__":
    main()
