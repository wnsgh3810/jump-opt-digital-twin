"""Phase 5 - DIAGNOSTIC: torque-deficit audit (why jumps cap at h_ratio 0.62).

The frontier (Phase 4) showed jumps plateau at 62% of real height even with
near-zero friction (lambda=8). This rules out sim energy loss => the measured
torque itself under-produces the real jump. This DIAGNOSTIC sweeps a hypothetical
tau_scale on jumps only, to quantify the torque deficit that explains the ceiling.

*** tau_scale is FORBIDDEN in the model (user directive). This is diagnostic ONLY,
    NOT adopted — purely to explain the root cause of the jump under-jump. ***

Base = Phase 4 adopted model. Jumps only (24 subs).
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


def apply_adopted():
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=FR["fv_hip"]; S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


# Wrap jump loaders to scale tau_real (diagnostic only)
_ORIG_LOADERS = dict(S.JUMP_LOADERS)

def _scaled_loader(orig, scale):
    def wrapped(sub):
        td = orig(sub)
        td = dict(td)  # shallow copy
        td['tau1_real'] = np.asarray(td['tau1_real']) * scale
        td['tau2_real'] = np.asarray(td['tau2_real']) * scale
        return td
    return wrapped


def jumps_h_ratio(tau_scale):
    """Run jumps with hypothetical tau_scale (diagnostic). Return mean h_sim/h_real + per-sub."""
    ap = apply_adopted()
    # patch loaders
    S.JUMP_LOADERS = {k: _scaled_loader(v, tau_scale) for k, v in _ORIG_LOADERS.items()}
    hs=[]; hr=[]; rows=[]
    try:
        for ds, sub, isj in list_experiments():
            if not isj: continue
            q1, q2 = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
            try:
                s, m = S.run_one_sub(ds, sub, q1, q2, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
            except Exception:
                m = None
            if m:
                hs.append(m["h_sim_m"]); hr.append(m["h_real_m"])
                rows.append(dict(ds=ds, sub=sub, h_sim=m["h_sim_m"], h_real=m["h_real_m"]))
    finally:
        S.JUMP_LOADERS = dict(_ORIG_LOADERS)
    ratio = sum(hs)/sum(hr) if hr else 0
    return ratio, rows


def main():
    out = Path(__file__).resolve().parent
    print("[Phase 5] DIAGNOSTIC torque-deficit audit (tau_scale NOT adopted)")
    print("Sweeping hypothetical tau_scale on jumps to find what recovers h_real.\n")
    res=[]
    for ts in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
        t0=time.time()
        ratio, rows = jumps_h_ratio(ts)
        print(f"  tau_scale={ts:.2f}: mean jump h_ratio={ratio:.3f}  ({time.time()-t0:.0f}s)")
        res.append(dict(tau_scale=ts, h_ratio=ratio))
    # Find scale where h_ratio ~ 1.0 (linear interp)
    import numpy as np
    ts_arr=np.array([r["tau_scale"] for r in res]); hr_arr=np.array([r["h_ratio"] for r in res])
    if hr_arr[-1] >= 1.0:
        ts_needed = float(np.interp(1.0, hr_arr, ts_arr))
    else:
        ts_needed = None
    print(f"\ntau_scale to reach h_ratio=1.0: {ts_needed if ts_needed else '>1.5'}")
    out_json = dict(diagnostic=True, note="tau_scale FORBIDDEN in model; audit only",
                    sweep=res, tau_scale_for_h1=ts_needed)
    (out/"phase5_energy_audit.json").write_text(json.dumps(out_json, indent=2))
    print(f"Written: {out/'phase5_energy_audit.json'}")


if __name__ == "__main__":
    main()
