"""G20-A2 — JOINT refit: explicit four-bar structure + per-date offsets + physical params.

Stage-1 findings combined:
  - four-bar explicit @ pure CAD already -9.0% vs CAD-serial, within 3.2% of fitted v3
  - per-date offsets (user: Mar/Apr calibration was wrong; 0602=reference) -16.3%
Joint fit lets the better structure re-arbitrate offsets and scales together.
Params (26): 5 mass scales + 2 inertia scales + 2 CoM dz + arm_knee + m_foot +
stiff_knee(crank) + contact(2) + friction(4) + date offsets 0319s2s/0324/0421/0424 (8).
Datasets: 24 jumps + s2s_gnd (same four-bar XML — identical structure, floor present).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_refit as R
import mshoot_fourbar as FB
from mshoot_dateoff import prep_with_grad, shifted_view
from load_31exp import list_experiments

OUT = REPO / "code/goal19/phase11/fourbar_refit_o2deg.json"
V3 = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
V3D = dict(zip(V3["names"], V3["x"]))
DOFF = json.load(open(REPO / "code/goal19/phase11/dateoff_best.json"))["offs"]  # ±5° best
OLIM = np.deg2rad(2.0)

# name, warm, lo, hi
SPEC = [
    ("M_base",   1.0, 0.60, 1.40), ("M_thigh", 1.0, 0.60, 1.40),
    ("M_calf",   1.0, 0.50, 1.60), ("M_p",     1.0, 0.40, 2.50),
    ("M_c",      1.0, 0.40, 1.60), ("I_thigh", 1.0, 0.40, 1.80),
    ("I_calf",   1.0, 0.40, 1.80),
    ("com_dz_th", 0.0, -0.10, 0.10), ("com_dz_ca", 0.0, -0.10, 0.10),
    ("arm_knee", V3D["arm_knee"], 0.002, 0.025),
    ("m_foot",   V3D["m_foot"], 0.00, 0.30),
    ("stiff_knee", V3D["stiff_knee"], 0.00, 4.50),
    ("solref_tc", V3D["solref_tc"], 0.0018, 0.0100),
    ("imp0",     V3D["imp0"], 0.08, 0.45),
    ("fv_hip",   V3D["fv_hip"], 0.05, 1.30),
    ("fv_knee",  V3D["fv_knee"], 0.00, 0.70),
    ("fc_hip",   V3D["fc_hip"], 0.01, 0.60),
    ("fc_knee",  V3D["fc_knee"], 0.05, 1.30),
    ("o1_0319",  0.0, -OLIM, OLIM), ("o2_0319", 0.0, -OLIM, OLIM),
    ("o1_0324",  DOFF[0], -OLIM, OLIM), ("o2_0324", DOFF[1], -OLIM, OLIM),
    ("o1_0421",  DOFF[2], -OLIM, OLIM), ("o2_0421", DOFF[3], -OLIM, OLIM),
    ("o1_0424",  DOFF[4], -OLIM, OLIM), ("o2_0424", DOFF[5], -OLIM, OLIM),
]
NAMES = [s[0] for s in SPEC]
X0 = np.array([np.clip(s[1], s[2], s[3]) for s in SPEC])
LOb = np.array([s[2] for s in SPEC]); HIb = np.array([s[3] for s in SPEC])
if OUT.exists():
    try:
        _pb = json.load(open(OUT, encoding="utf-8"))
        if _pb.get("names") == NAMES:
            X0 = np.clip(np.array(_pb["x"]), LOb, HIb)
            print("warm-start from previous fourbar best", flush=True)
    except Exception:
        pass

# ---- prep (serial models, geometry identical; cached once) ------------------
_serial_jump = None
_serial_gnd = None


def get_serial_models():
    global _serial_jump, _serial_gnd
    if _serial_jump is None:
        _serial_jump = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, 0.005))
        _serial_gnd = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_gnd_6d(0.0, 0.005))
    return _serial_jump, _serial_gnd


def all_groups():
    groups = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        groups.append((ds, subs, MS.LOADERS[ds], True))
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, (lambda s, _t=tdir: MS.load_march(_t, s)), True))
    try:
        cycles, gid = MS.load_s2s_cycles()
        groups.append(("s2s_gnd_0319", list(range(len(cycles))),
                       (lambda ci, _c=cycles: _c[ci]), False))
    except Exception:
        pass
    return groups


GROUPS = None
OFFKEY = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
          "jump_0424": ("o1_0424", "o2_0424"), "s2s_gnd_0319": ("o1_0319", "o2_0319")}


def evaluate(x):
    global GROUPS
    d = dict(zip(NAMES, x))
    S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = d["fc_hip"]; S.FC_KNEE = d["fc_knee"]
    S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    try:
        model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(d["arm_knee"], d))
    except Exception:
        return 9e9, None
    mj, mg = get_serial_models()
    if GROUPS is None:
        GROUPS = all_groups()
    total = 0.0; per = {}
    for ds, subs, loader, isj in GROUPS:
        k1, k2 = OFFKEY.get(ds, (None, None))
        o1 = d[k1] if k1 else 0.0; o2 = d[k2] if k2 else 0.0
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            wins = FB.eval_windows_fourbar(model, shifted_view(pp, o1, o2))
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = dict(score=sc, n=nw, mean=acc / max(nw, 1))
    return total, per


def main():
    import cma
    o0, per0 = evaluate(X0)
    print(f"WARM (4bar CAD + dateoff5): total={o0:.0f}", flush=True)
    for ds, v in per0.items():
        m = v["mean"]
        print(f"   WARM {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f}", flush=True)
    x0n = (X0 - LOb) / (HIb - LOb)
    es = cma.CMAEvolutionStrategy(x0n, 0.18, {"bounds": [0, 1], "maxfevals": 220,
                                              "popsize": 16, "seed": 23, "verbose": -9})
    best = dict(obj=float(o0), x=[float(v) for v in X0], names=NAMES)
    gen = 0
    while not es.stop():
        sols = es.ask(); objs = []
        for sn in sols:
            x = LOb + np.array(sn) * (HIb - LOb)
            o, _ = evaluate(x)
            objs.append(o)
            if o < best["obj"]:
                best = dict(obj=float(o), x=[float(v) for v in x], names=NAMES)
                json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
        es.tell(sols, objs); gen += 1
        print(f"gen {gen}: best={best['obj']:.0f}", flush=True)
    json.dump(best, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nBEST total={best['obj']:.0f}  (WARM {o0:.0f}, {100*(best['obj']/o0-1):+.1f}%)")
    _, per = evaluate(np.array(best["x"]))
    for ds, v in per.items():
        m = v["mean"]
        print(f"   BEST {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f}")
    dd = dict(zip(NAMES, best["x"]))
    print("PARAMS:", {k: round(v, 4) for k, v in dd.items()})
    print("offsets(deg):", {k: round(np.rad2deg(dd[k]), 2) for k in NAMES if k.startswith("o")})


if __name__ == "__main__":
    main()
