"""P10 — 4-bar PHASE FLIP test (user hardware correction 07-07).

User: the shin rocker (l_o) extends UP/BACKWARD from the knee (along the calf
axis extension), NOT down toward the foot. Mirrored parallelogram: crank at hip
also points up/backward; coupler still 250mm parallel to thigh but offset to
the OTHER side. Kinematics identical (crank angle == calf angle, loop closes
with same qpos init); dynamics differ: coupler position shifts ~60mm, crank CoM
flips (~0.1-0.2 Nm gravity-torque class — same scale as our residuals).

Hypothesis worth testing: canonical's M_p = +72% CAD anomaly partially
compensated the wrong coupler placement.

Stage 0: flipped XML + canonical 26 params -> hybrid scores vs canonical.
Stage 1: short CMA refit (warm at canonical, sigma 0.05) with held-out gate.
Stage 2: gallery full-replay judge + M_p/M_c drift report.
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "code/goal21/fourbar_flip_result.json"
_G = {}


def build_xml_fourbar_flip(arm_knee, scales=None):
    """Mirrored-phase copy of FB.build_xml_fourbar_jump: crank/rocker point +z."""
    FB = _G["FB"]; S = _G["S"]; B = _G["B"]
    L1, L2, LC = B.L1_VAL, B.L2_VAL, B.LC_VAL
    sc = scales or {}
    s_th = sc.get("M_thigh", 1.0); s_ca = sc.get("M_calf", 1.0)
    s_p = sc.get("M_p", 1.0); s_c = sc.get("M_c", 1.0)
    i_th = sc.get("I_thigh", 1.0); i_ca = sc.get("I_calf", 1.0)
    dz_th = sc.get("com_dz_th", 0.0); dz_ca = sc.get("com_dz_ca", 0.0)
    m_foot = sc.get("m_foot", 0.0)
    M1 = B.M1_CAD * s_th
    R1 = B.R1_VAL + dz_th
    I1 = B.I1_VAL * i_th
    Mc2, ccz, Ic2 = FB.calf_inertial(s_ca, m_foot, dz_ca, i_ca)
    MP = B.M_P_CAD * s_p; MC = B.M_C_CAD * s_c
    sr = S._solref_str(); si = S._solimp_str(); Mb = S._base_mass()
    return f"""<mujoco model="fourbar_flip">
<option cone="{S.CONE}" impratio="{S.IMPRATIO}" gravity="0 0 -9.81" timestep="{S.DT}" integrator="{S.JUMP_INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="{S._fric_str()}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-200 200" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{S.FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{S._fric_str()}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{S._fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1"/>
    <inertial pos="0 0 0" mass="{Mb:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="0" damping="{S.FV_HIP:.6f}" frictionloss="{S.FC_HIP:.6f}"/>
      <inertial pos="0 0 -{R1:.5f}" mass="{M1:.5f}" diaginertia="{I1:.6f} {I1:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1}" contype="1" conaffinity="1"/>
      <body name="crank" pos="0 0 0">
        <joint name="knee_motor" type="hinge" armature="{arm_knee:.8f}" damping="{S.FV_KNEE:.6f}" frictionloss="{S.FC_KNEE:.6f}" stiffness="{S.STIFF_KNEE:.6f}" springref="{S.SPRINGREF_KNEE:.5f}"/>
        <inertial pos="0 0 {B.RC_VAL:.5f}" mass="{MC:.5f}" diaginertia="{B.IC_VAL:.6f} {B.IC_VAL:.6f} {B.IC_VAL:.6f}"/>
        <geom type="capsule" size="0.008" fromto="0 0 0 0 0 {LC}" contype="0" conaffinity="0"/>
        <body name="coupler" pos="0 0 {LC}">
          <joint name="cpin" type="hinge"/>
          <inertial pos="0 0 -{B.RP_VAL:.5f}" mass="{MP:.5f}" diaginertia="{B.IP_VAL:.6f} {B.IP_VAL:.6f} 0.00005"/>
          <geom type="capsule" size="0.006" fromto="0 0 0 0 0 -{L1}" contype="0" conaffinity="0"/>
        </body>
      </body>
      <body name="calf" pos="0 0 -{L1}">
        <joint name="knee" type="hinge" damping="0.001"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2}" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot" type="cylinder" size="{S.FOOT_RADIUS:.4f} {S.FOOT_HALF_LEN:.4f}" pos="0 0 -{L2}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<equality>
  <connect body1="coupler" body2="calf" anchor="0 0 -{L1}" solref="0.0008 1"/>
</equality>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee_motor" gear="1"/>
</actuator>
</mujoco>"""


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal21"))
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
        sys.path.insert(0, str(REPO / "code/goal19" / p))
    import mujoco
    import sub_sim_iter6v2 as S
    import build_xml_i3 as B
    import mshoot_fourbar as FB
    _G.update(mujoco=mujoco, S=S, B=B, FB=FB)
    FB.build_xml_fourbar_jump = lambda arm_knee, scales=None: build_xml_fourbar_flip(arm_knee, scales)
    import g21_fourbar_hybrid as GH
    GH.winit()
    _G["GH"] = GH


def eval_flip(x):
    return _G["GH"].eval_hybrid(np.asarray(x))


def main():
    import multiprocessing as mp
    import cma
    maxfev = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    sigma = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
    tag = sys.argv[3] if len(sys.argv) > 3 else ""
    global OUT
    if tag:
        OUT = REPO / f"code/goal21/fourbar_flip_result_{tag}.json"
    winit()
    GH = _G["GH"]; FR = GH._G["FR"]
    can = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
    x_can = np.array(can["x"]); NAMES = can["names"]
    base = json.load(open(REPO / "code/goal21/fourbar_hybrid_best.json"))["base"]
    G7 = GH.OBJ_GROUPS
    pool = mp.Pool(10, initializer=winit)

    # sanity: flipped loop must close (parallelogram) — quick closure check
    import mujoco
    m = mujoco.MjModel.from_xml_string(build_xml_fourbar_flip(0.005, dict(zip(NAMES, x_can))))
    d = mujoco.MjData(m)
    q2 = 2.0
    d.qpos[:] = [1.0, -1.0, q2, -q2, q2]
    mujoco.mj_forward(m, d)
    err = float(np.max(np.abs(d.efc_pos))) if d.nefc else 0.0
    print(f"[sanity] flipped-loop closure residual = {err:.2e} m ({'PASS' if err < 1e-6 else 'FAIL'})", flush=True)

    r0 = eval_flip(x_can)
    o0 = sum(r0[g] / base[g] for g in G7)
    print("STAGE0 flipped @ canonical params: obj=%.4f (orig-phase 7.0)" % o0, flush=True)
    print("  " + "  ".join(f"{g.split('_')[-1]}:{r0[g]/base[g]:.3f}" for g in G7) +
          f"  heldout:{r0['fs_0324']/base['fs_0324']:.3f}", flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    LOb, HIb = FR.LOb, FR.HIb
    x0w = x_can
    prev = REPO / "code/goal21/fourbar_flip_result.json"
    if tag and prev.exists():
        pj = json.load(open(prev))
        if pj.get("selected"):
            x0w = np.array(pj["selected"]["x"])
            print("warm-start from P10 selected", flush=True)
    es = cma.CMAEvolutionStrategy(((x0w - LOb) / (HIb - LOb)).tolist(), sigma,
                                  {"bounds": [0, 1], "maxfevals": maxfev, "popsize": 20,
                                   "seed": 21, "verbose": -9})
    cands = []
    best = dict(obj=float(o0), ho=float(r0["fs_0324"] / base["fs_0324"]), x=x_can.tolist())
    nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval_flip, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.05:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} [{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"STAGE1 done nev={nev}. selected: obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "STAGE1: no candidate passed heldout", flush=True)
    xsel = np.array(sel["x"]) if sel else x_can
    dd = dict(zip(NAMES, xsel))
    print("mass drift (canonical -> flip-refit):", flush=True)
    for n in ["M_p", "M_c", "M_thigh", "M_calf", "com_dz_th", "com_dz_ca", "stiff_knee", "fv_hip"]:
        i = NAMES.index(n)
        print(f"  {n:<10} {x_can[i]:8.4f} -> {xsel[i]:8.4f}", flush=True)
    json.dump(dict(stage0=dict(obj=float(o0), per={k: float(v) for k, v in r0.items()}),
                   selected=sel, names=NAMES, base=base),
              open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
