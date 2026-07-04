"""GOAL19 Phase 11s — SEA hypothesis test in the multiple-shooting frame.

v4 verdict: calf group demands 'light mass + high rotational inertia' (impossible) =>
structural missing dynamics at the knee. Hypothesis: series compliance (transmission)
between knee MOTOR (encoder side) and calf.

Model: base -> thigh(hip) -> rotor(knee_motor, armature=arm_knee, small real inertia)
       -> calf(knee_spring: stiffness k_sea, damping c_sea, springref 0).
Encoder = knee_motor (qpos[2]) — scored against measured q2/dq2 exactly as rigid.
Window init: motor=measured, spring deflection quasi-static delta0 = -tau_mj/k
(spring transmits the measured torque), d(delta)/dt from tau derivative.
No parallel stiff_knee in the SEA XML (hypothesis: series compliance is the physics
the parallel spring was crudely proxying).

Scan k_sea x c_sea on JUMP windows with v3 params fixed; compare to v3 rigid.
Freeze check: windows start in motion — the settle-equilibrium freeze should not occur.
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


def build_sea_xml(arm_knee, k_sea, c_sea):
    """Jump XML with series-elastic knee. Uses current S-module globals (set_params first)."""
    Mt, ctz, It, Mc2, ccz, Ic2 = S.ci_locked()
    sr = S._solref_str(); si = S._solimp_str(); Mb = S._base_mass()
    L1, L2 = S.L1_VAL, S.L2_VAL
    return f"""<mujoco model="mshoot_sea">
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
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1}" contype="1" conaffinity="1"/>
      <body name="rotor" pos="0 0 -{L1}">
        <joint name="knee_motor" type="hinge" armature="{arm_knee:.8f}" damping="{S.FV_KNEE:.6f}" frictionloss="{S.FC_KNEE:.6f}"/>
        <inertial pos="0 0 0" mass="0.05" diaginertia="2e-5 2e-5 2e-5"/>
        <body name="calf" pos="0 0 0">
          <joint name="knee_spring" type="hinge" stiffness="{k_sea:.4f}" damping="{c_sea:.4f}" springref="0"/>
          <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
          <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2}" contype="1" conaffinity="1"/>
          <geom name="foot" class="foot" type="cylinder" size="{S.FOOT_RADIUS:.4f} {S.FOOT_HALF_LEN:.4f}" pos="0 0 -{L2}" euler="90 0 0"/>
        </body>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee_motor" gear="1"/>
</actuator>
</mujoco>"""


def build_sea_xml_tendon(arm_knee, k_sea, c_sea):
    """SEA via FIXED TENDON coupling (standard MuJoCo idiom, avoids in-chain rotor
    ill-conditioning): calf hangs directly from thigh via real knee joint; rotor is a
    flywheel on the thigh; tendon (coef +1 knee, -1 knee_motor) with stiffness k couples
    them elastically. Actuator drives knee_motor. qpos=[bz, hip, knee_motor, knee]."""
    Mt, ctz, It, Mc2, ccz, Ic2 = S.ci_locked()
    sr = S._solref_str(); si = S._solimp_str(); Mb = S._base_mass()
    L1, L2 = S.L1_VAL, S.L2_VAL
    return f"""<mujoco model="mshoot_sea_tendon">
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
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1}" contype="1" conaffinity="1"/>
      <body name="rotor" pos="0 0 -{L1}">
        <joint name="knee_motor" type="hinge" armature="{arm_knee:.8f}" damping="{S.FV_KNEE:.6f}" frictionloss="{S.FC_KNEE:.6f}"/>
        <inertial pos="0 0 0" mass="0.05" diaginertia="2e-5 2e-5 2e-5"/>
        <geom type="sphere" size="0.005" contype="0" conaffinity="0"/>
      </body>
      <body name="calf" pos="0 0 -{L1}">
        <joint name="knee" type="hinge"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2}" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot" type="cylinder" size="{S.FOOT_RADIUS:.4f} {S.FOOT_HALF_LEN:.4f}" pos="0 0 -{L2}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<tendon>
  <fixed name="trans" stiffness="{k_sea:.4f}" damping="{c_sea:.4f}" springlength="0">
    <joint joint="knee" coef="1"/>
    <joint joint="knee_motor" coef="-1"/>
  </fixed>
</tendon>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee_motor" gear="1"/>
</actuator>
</mujoco>"""


def eval_windows_sea(model, pp, k_sea):
    """SEA window replay. qpos=[bz,hip,knee_motor,knee_spring]. Score motor side."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        tau_k0 = pp["tau_k"][i0]
        # quasi-static spring deflection: spring torque on calf (-k*q_s) == transmitted tau
        qs0 = -tau_k0 / k_sea
        i0m = max(i0 - 1, 0); i0p = min(i0 + 1, len(t) - 1)
        dqs0 = -(pp["tau_k"][i0p] - pp["tau_k"][i0m]) / (t[i0p] - t[i0m]) / k_sea
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0], qs0]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0], dqs0]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q2 = np.empty(nst); dq2 = np.empty(nst)
        q1 = np.empty(nst); dq1 = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1[k] = d.qpos[1]; q2[k] = d.qpos[2]     # motor side = encoder
            dq1[k] = d.qvel[1]; dq2[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1, pp["q1m"]), rq2=r(q2, pp["q2m"]),
                        rdq1=r(dq1, pp["dq1m"]), rdq2=r(dq2, pp["dq2m"])))
    return out


def eval_windows_sea_tendon(model, pp, k_sea):
    """Tendon-SEA windows. qpos=[bz,hip,knee_motor,knee(abs)]. Score motor side qpos[2]."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        delta0 = -pp["tau_k"][i0] / k_sea         # tendon torque on knee == transmitted tau
        i0m = max(i0 - 1, 0); i0p = min(i0 + 1, len(t) - 1)
        ddelta0 = -(pp["tau_k"][i0p] - pp["tau_k"][i0m]) / (t[i0p] - t[i0m]) / k_sea
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0], pp["q2m"][i0] + delta0]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0], pp["dq2m"][i0] + ddelta0]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1 = np.empty(nst); q2 = np.empty(nst)
        dq1 = np.empty(nst); dq2 = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1[k] = d.qpos[1]; q2[k] = d.qpos[2]      # motor = encoder
            dq1[k] = d.qvel[1]; dq2[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1, pp["q1m"]), rq2=r(q2, pp["q2m"]),
                        rdq1=r(dq1, pp["dq1m"]), rdq2=r(dq2, pp["dq2m"])))
    return out


def jump_score_sea_tendon(arm_knee, k_sea, c_sea):
    model = mujoco.MjModel.from_xml_string(build_sea_xml_tendon(arm_knee, k_sea, c_sea))
    total = 0.0; per = {}
    from load_31exp import list_experiments
    groups = [(ds, [sub for d2, sub, isj in list_experiments() if d2 == ds], MS.LOADERS[ds])
              for ds in MS.LOADERS]
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    for ds, subs, loader in groups:
        sc = 0.0; acc = np.zeros(4); nw = 0
        for sub in subs:
            td = loader(sub)
            pp = MS.get_prep((ds, sub), td, model, True)
            wins = eval_windows_sea_tendon(model, pp, k_sea)
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = acc / max(nw, 1)
    return total, per


def jump_score_sea(arm_knee, k_sea, c_sea):
    """Jump-window total under SEA (uses MS._PREP cache, same windows as rigid)."""
    model = mujoco.MjModel.from_xml_string(build_sea_xml(arm_knee, k_sea, c_sea))
    total = 0.0; per = {}
    from load_31exp import list_experiments
    for ds, loader in MS.LOADERS.items():
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        sc = 0.0; acc = np.zeros(4); nw = 0
        for sub in subs:
            td = loader(sub)
            pp = MS.get_prep((ds, sub), td, model, True)  # FK geometry identical
            wins = eval_windows_sea(model, pp, k_sea)
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = acc / max(nw, 1)
    for ds, tdir, subs in MS.MARCH:
        sc = 0.0; acc = np.zeros(4); nw = 0
        for sub in subs:
            td = MS.load_march(tdir, sub)
            pp = MS.get_prep((ds, sub), td, model, True)
            wins = eval_windows_sea(model, pp, k_sea)
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = acc / max(nw, 1)
    return total, per


def jump_score_rigid():
    """v3 rigid jump-window total for exact comparison (same windows, no s2s)."""
    best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    d = R.set_params(np.array(best["x"]))
    total, per = MS.evaluate_all(0.0, d["arm_knee"])
    jump_total = sum(v["score"] for ds, v in per.items() if ds != "sit2stand_gnd")
    return jump_total, {ds: v["mean"] for ds, v in per.items() if ds != "sit2stand_gnd"}, d


if __name__ == "__main__":
    rigid_total, rigid_per, dparams = jump_score_rigid()
    print(f"RIGID v3 jump-window total = {rigid_total:.0f}")
    for ds, m in rigid_per.items():
        print(f"   {ds:<20} q2={m[1]:.4f} dq2={m[3]:.2f}")
    print("\nSEA scan (v3 params fixed, stiff_knee removed, series k added):")
    print(f"{'k_sea':>7} {'c_sea':>6} | {'total':>7} {'vs rigid':>9}")
    S.STIFF_KNEE = 0.0  # series replaces parallel proxy
    ak = dparams["arm_knee"]
    for k_sea in [50, 100, 200, 350, 500, 800, 1500, 3000]:
        for c_sea in [0.1, 0.5]:
            tot, per = jump_score_sea(ak, k_sea, c_sea)
            print(f"{k_sea:>7} {c_sea:>6} | {tot:>7.0f} {100*(tot/rigid_total-1):>+8.1f}%")
