# UPDATE (2026-07-03): rotor needs REAL inertia (diaginertia, triangle-ineq valid), NOT armature —
# then motor DOES move. RESULT: soft spring (k=40) -> motor dq2 peak 28 == real 27 (rigid gives 18)!
# => series compliance REPRODUCES the terminal spike. But base-jump still buggy (h~0.19): 2-body push-off
# needs cleaner topology/settle. Velocity-spike hypothesis CONFIRMED; full jump integration = future work.
# WIP/BUGGY (2026-07-03): series spring does not transmit motion to link even when rigid
# (sea_k=5000 -> link constant, no jump). Topology/settle/sign bug. INCONCLUSIVE test.
# Kept as starting point for a proper SEA reimplementation.
"""GOAL19 Phase 11h - Series-Elastic Actuator (SEA) test for the jump terminal spike.

My "structural floor" claim used a PARALLEL spring (stiff_knee to ground). Real
transmission compliance is SERIES: motor --spring--> link. A SEA stores energy
during the push and releases it as a velocity SNAP at takeoff -- exactly the
terminal dq2 spike (real 27, sim 18) I called unreachable. This tests whether the
correct topology reproduces it.

Knee split: knee_rotor(motor, armature) --knee_flex(SEA spring)--> calf(link).
q2_link = -(qpos[knee] + qpos[knee_flex]).  Compares dq2 peak + h vs real, sweeping SEA_K.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
from apply_final_and_regen import apply_final
import sub_sim_iter6v2 as S


def build_sea_xml(arm_hip, arm_knee, sea_k, sea_d):
    Mt, ctz, It, Mc2, ccz, Ic2 = S.ci_locked()
    sr = S._solref_str(); si = S._solimp_str(); M_base = S._base_mass()
    fr = S._fric_str()
    return f"""<mujoco model="sea_jump">
<option cone="{S.CONE}" impratio="{S.IMPRATIO}" gravity="0 0 -9.81" timestep="{S.DT}" integrator="{S.JUMP_INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="{fr}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{S.FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{fr}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{fr}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{arm_hip:.8f}" damping="{S.FV_HIP:.8f}" frictionloss="{S.FC_HIP:.8f}" stiffness="{S.STIFF_HIP:.6f}" springref="0"/>
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{S.L1_VAL}" contype="1" conaffinity="1"/>
      <body name="knee_rotor" pos="0 0 -{S.L1_VAL}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}" damping="{S.FV_KNEE:.8f}" frictionloss="{S.FC_KNEE:.8f}"/>
        <inertial pos="0 0 0" mass="0.0001" diaginertia="1e-7 1e-7 1e-7"/>
        <body name="calf" pos="0 0 0">
          <joint name="knee_flex" type="hinge" armature="0" damping="{sea_d:.6f}" frictionloss="0" stiffness="{sea_k:.6f}" springref="0"/>
          <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
          <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{S.L2_VAL}" contype="1" conaffinity="1"/>
          <geom name="foot" class="foot" type="cylinder" size="{S.FOOT_RADIUS:.4f} {S.FOOT_HALF_LEN:.4f}" pos="0 0 -{S.L2_VAL}" euler="90 0 0"/>
        </body>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


def run_sea(td, sea_k, sea_d, arm_hip, arm_knee):
    t_real = td["t"]
    tau_h_in = -np.asarray(td["tau1_real"]); tau_k_in = -np.asarray(td["tau2_real"])
    set_q1, set_q2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    model = mujoco.MjModel.from_xml_string(build_sea_xml(arm_hip, arm_knee, sea_k, sea_d))
    data = mujoco.MjData(model)
    data.qpos[:] = [S.BASE_Z_INIT, set_q1, set_q2, 0.0]  # base, hip, knee(motor), knee_flex
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    dt = model.opt.timestep
    T_motion = float(t_real[-1]); N = int((S.T_SETTLE + T_motion + S.T_AFTER) / dt) + 1
    q2_link = np.zeros(N); dq2_link = np.zeros(N); basez = np.zeros(N); tlog = np.zeros(N)
    for k in range(N):
        t_cur = k * dt
        if t_cur < S.T_SETTLE:
            tau_h = S.SETTLE_KP * (set_q1 - data.qpos[1]) + S.SETTLE_KD * (0 - data.qvel[1])
            # settle motor so LINK (knee+flex) -> set_q2
            link = data.qpos[2] + data.qpos[3]
            tau_k = S.SETTLE_KP * (set_q2 - link) + S.SETTLE_KD * (0 - (data.qvel[2] + data.qvel[3]))
        elif t_cur < S.T_SETTLE + T_motion:
            tm = t_cur - S.T_SETTLE
            tau_h = float(np.interp(tm, t_real, tau_h_in))
            tau_k = float(np.interp(tm, t_real, tau_k_in))
        else:
            tau_h = 0.0; tau_k = 0.0
        data.ctrl[:] = [tau_h, tau_k]
        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None
        tlog[k] = t_cur - S.T_SETTLE
        q2_link[k] = -(data.qpos[2] + data.qpos[3])
        dq2_link[k] = -(data.qvel[2] + data.qvel[3])
        basez[k] = data.qpos[0]
        if abs(data.qpos[0]) > 5.0:
            return None
    m = tlog >= 0
    return dict(t=tlog[m], q2=q2_link[m], dq2=dq2_link[m], h_sim=float(basez.max()))


def main():
    ap = apply_final()
    subs = [(S.load_jump_0424, "90_0.75_90_2"), (S.load_jump_0602, "90_0.75_90_2"),
            (S.load_jump_0424, "120_2.2_150_2.5")]
    # rigid reference (current model, parallel spring) dq2 peak for comparison
    print("SEA test: does series compliance produce the terminal dq2 spike?")
    print(f"{'trial':<22}{'real dq2pk':>10}{'real h':>8} | SEA sweep (k: dq2pk / h_sim)")
    for loader, sub in subs:
        td = loader(sub)
        real_dq2pk = float(np.max(np.abs(td["dq2"]))); real_h = float(td["h_real"])
        row = f"{loader.__name__.replace('load_jump_',''):<6}/{sub:<14}{real_dq2pk:>10.1f}{real_h:>8.2f} | "
        for sea_k in [20, 40, 80, 150]:
            r = run_sea(td, sea_k, sea_d=0.05, arm_hip=ap["arm_hip"], arm_knee=ap["arm_knee"])
            if r is None:
                row += f"k{sea_k}:FAIL  "
            else:
                row += f"k{sea_k}:{np.max(np.abs(r['dq2'])):.0f}/{r['h_sim']:.2f}  "
        print(row, flush=True)


if __name__ == "__main__":
    main()
