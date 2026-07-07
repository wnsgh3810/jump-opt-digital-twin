"""GOAL21 P6 judge — gallery full-replay: canonical(paper a_hat) vs stage-A vs
stage-B validation-selected (min obj s.t. held-out fs_0324 <= 1.0).

For each config: recompute per-trial tau via candidate a_hat (Iq from exact
paper inversion), full replay incl. settle, per-date q/dq RMSE + h_ratio.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR
from load_31exp import list_experiments
from g21_ahat_refit import invert_ahat, ahat_fwd, AH0

OFFDS = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
         "jump_0424": ("o1_0424", "o2_0424")}


def jump_groups():
    gs = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        gs.append((ds, subs, MS.LOADERS[ds]))
    for ds, tdir, subs in MS.MARCH:
        gs.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    return gs


def run(name, x26, ah, names):
    dd = dict(zip(names, x26))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(dd["arm_knee"], dd))
    a0, a1, a2, a3h, a4h, a3k, a4k = ah
    from collections import defaultdict
    G = defaultdict(lambda: [0.0] * 6 + [0])
    for ds, subs, loader in jump_groups():
        k1, k2 = OFFDS.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            v1 = np.asarray(td["dq1"], float); v2 = np.asarray(td["dq2"], float)
            Iq1 = invert_ahat(np.asarray(td["tau1_real"], float), v1)
            Iq2 = invert_ahat(np.asarray(td["tau2_real"], float), v2)
            tdv = dict(td)
            tdv["tau1_real"] = ahat_fwd(Iq1, v1, a0, a1, a2, a3h, a4h)
            tdv["tau2_real"] = ahat_fwd(Iq2, v2, a0, a1, a2, a3k, a4k)
            log = FB.run_jump_sim_fourbar(model, tdv)
            if log is None:
                continue
            tr = np.asarray(td["t"])
            mk = (log["t"] >= 0) & (log["t"] <= tr[-1])
            q1s = np.interp(tr, log["t"][mk], (-log["q1"] - np.pi / 2)[mk])
            q2s = np.interp(tr, log["t"][mk], (-log["q2"])[mk])
            dq1s = np.interp(tr, log["t"][mk], (-log["dq1"])[mk])
            dq2s = np.interp(tr, log["t"][mk], (-log["dq2"])[mk])
            r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
            g = G[ds]
            g[0] += r(q1s, td["q1"] + o1); g[1] += r(q2s, td["q2"] + o2)
            g[2] += r(dq1s, td["dq1"]); g[3] += r(dq2s, td["dq2"])
            g[4] += float(log["base_z"].max()); g[5] += float(td["h_real"]); g[6] += 1
    out = {ds: dict(q1=g[0] / g[6], q2=g[1] / g[6], dq1=g[2] / g[6], dq2=g[3] / g[6],
                    h_ratio=g[4] / g[5]) for ds, g in G.items() if g[6]}
    print(f"\n=== {name} ===")
    print(f"{'dataset':<22}{'q1 deg':>8}{'q2 deg':>8}{'dq1':>7}{'dq2':>7}{'h_ratio':>9}")
    for ds, v in out.items():
        print(f"{ds:<22}{np.degrees(v['q1']):>8.2f}{np.degrees(v['q2']):>8.2f}"
              f"{v['dq1']:>7.2f}{v['dq2']:>7.2f}{v['h_ratio']:>9.3f}")
    return {ds: {k: float(vv) for k, vv in v.items()} for ds, v in out.items()}


def main():
    can = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    NAMES = can["names"]
    out = {}
    out["canonical"] = run("CANONICAL (paper a_hat)", can["x"], AH0, NAMES)
    sa = json.load(open(REPO / "code/goal21/ahat_stageA.json"))
    out["stageA"] = run(f"STAGE-A a_hat-only (obj {sa['obj']:.3f}, ho {sa['res']['fs_0324']/sa['base']['fs_0324']:.2f})",
                        can["x"], sa["ah"], NAMES)
    best = None
    try:
        for ln in open(REPO / "code/goal21/ahat_cands.jsonl"):
            c = json.loads(ln)
            if c["heldout"] <= 1.0 and (best is None or c["obj"] < best["obj"]):
                best = c
    except FileNotFoundError:
        pass
    if best is not None:
        out["stageB"] = run(f"STAGE-B selected (obj {best['obj']:.3f}, ho {best['heldout']:.3f})",
                            best["x"][:26], best["x"][26:], NAMES)
        out["selectedB"] = best
    else:
        print("\n(no stage-B candidate passed the held-out gate)")
    json.dump(out, open(REPO / "code/goal21/ahat_validate.json", "w"), indent=1)
    print("\nsaved ahat_validate.json")


if __name__ == "__main__":
    main()
