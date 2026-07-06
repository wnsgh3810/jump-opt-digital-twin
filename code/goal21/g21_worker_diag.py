"""Diagnose worker-vs-serial score discrepancy: run one eval in a spawned worker
and in the master, dump S-global numeric state + per-sub scores + window counts."""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
_G = {}


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import mshoot as MS
    import sub_sim_iter6v2 as S
    from apply_final_and_regen import apply_final
    ap = apply_final()
    _G.update(mujoco=mujoco, MS=MS, S=S, ap=ap)


def diag(_=None):
    if not _G:
        winit()
    mujoco, MS, S, ap = _G["mujoco"], _G["MS"], _G["S"], _G["ap"]
    m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
    ds, tdir, subs = MS.MARCH[0]
    per = {}
    for sub in subs:
        td = MS.load_march(tdir, sub)
        pp = MS.get_prep((ds, sub), td, m, True)
        per[sub] = dict(score=float(MS.window_score(MS.eval_windows(m, pp))),
                        nwin=len(pp["starts"]), n=len(pp["t"]),
                        q1m0=float(pp["q1m"][0]), tau_k_max=float(np.max(np.abs(pp["tau_k"]))))
    sg = {k: float(v) for k, v in vars(S).items()
          if isinstance(v, (int, float)) and not k.startswith("_")}
    return dict(per=per, S=sg, arm=dict(ap))


if __name__ == "__main__":
    import multiprocessing as mp
    with mp.Pool(1, initializer=winit) as pool:
        wk = pool.map(diag, [None])[0]
    sr = diag()
    print("== per-sub scores ==")
    for sub in sr["per"]:
        print(f"  {sub:<10} serial {sr['per'][sub]['score']:>8.1f} ({sr['per'][sub]['nwin']}w)"
              f"   worker {wk['per'][sub]['score']:>8.1f} ({wk['per'][sub]['nwin']}w)"
              f"   tau_k_max s/w {sr['per'][sub]['tau_k_max']:.3f}/{wk['per'][sub]['tau_k_max']:.3f}")
    ks = set(sr["S"]) | set(wk["S"])
    diffs = [(k, sr["S"].get(k), wk["S"].get(k)) for k in sorted(ks)
             if not np.isclose(sr["S"].get(k, np.nan), wk["S"].get(k, np.nan), equal_nan=True)]
    print("== S-global diffs (serial vs worker) ==")
    for k, a, b in diffs:
        print(f"  {k}: {a} vs {b}")
    if not diffs:
        print("  (none)")
    print("== arm ==", sr["arm"], wk["arm"])
