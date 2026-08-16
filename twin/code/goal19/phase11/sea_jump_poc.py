"""GOAL19 Phase 11m — SERIES-ELASTIC (SEA) knee proof-of-concept.

Diagnosis (2026-07-04): measured joint data supports h~0.9-1.0 (peak base_vz 3.0-3.3),
but the rigid sim only reaches base_vz 2.38 (h~0.75) because it misses the terminal
knee-velocity spike (sim dq2 18-24 vs real 27). The spike = series-elastic catapult:
transmission/structure compliance stores energy during the push, releases it at takeoff.

This POC inserts a torsional spring between the knee MOTOR (rotor, encoder side) and the
calf (link). Encoder reads the MOTOR angle (qpos[2]); the calf angle = motor + spring
deflection. Mode A: feed tau_real to hip + knee_motor. Goal: reproduce dq2 spike ~27 AND
base apex ~0.89 simultaneously — closing q/dq/h with ONE physical axis (no GRF, no fudge).

Objective per user (2026-07-04): match q, dq, tau, h. DROP GRF (load cell nonlinear +
Mar/Apr calibration wrong). h is camera-measured base-center apex (real).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))


def build_sea_jump(arm_hip, k_sea, c_sea, I_rot):
    """Jump XML with a series-elastic KNEE: thigh -> knee_motor(rotor) -> knee_spring -> calf."""
    Mt, ctz, It, Mc2, ccz, Ic2 = S.ci_locked()
    sr = S._solref_str(); si = S._solimp_str(); M_base = S._base_mass()
    L1, L2 = S.L1_VAL, S.L2_VAL
    return f"""<mujoco model="sea_jump">
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
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{S._fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{arm_hip:.8f}" damping="{S.FV_HIP:.8f}" frictionloss="{S.FC_HIP:.8f}" stiffness="{S.STIFF_HIP:.6f}" springref="0"/>
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1}" contype="1" conaffinity="1"/>
      <body name="rotor" pos="0 0 -{L1}">
        <joint name="knee_motor" type="hinge" armature="0" damping="{S.FV_KNEE:.8f}" frictionloss="{S.FC_KNEE:.8f}"/>
        <inertial pos="0 0 0" mass="1e-4" diaginertia="{I_rot:.6f} {I_rot:.6f} {I_rot:.6f}"/>
        <body name="calf" pos="0 0 0">
          <joint name="knee_spring" type="hinge" stiffness="{k_sea:.5f}" damping="{c_sea:.5f}" springref="0"/>
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


def run_sea(td, arm_hip, k_sea, c_sea, I_rot):
    """Mode A on the SEA model. qpos=[base_z, hip, knee_motor, knee_spring]."""
    m = mujoco.MjModel.from_xml_string(build_sea_jump(arm_hip, k_sea, c_sea, I_rot))
    d = mujoco.MjData(m)
    t_real = td["t"]
    tau_h_in = -np.asarray(td["tau1_real"]); tau_k_in = -np.asarray(td["tau2_real"])
    set_q1, set_q2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    d.qpos[:] = [S.BASE_Z_INIT + S.BASE_Z_INIT_OFF, set_q1, set_q2, 0.0]; d.qvel[:] = 0.0
    mujoco.mj_forward(m, d)
    dt = m.opt.timestep; T_motion = float(t_real[-1])
    N = int((S.T_SETTLE + T_motion + S.T_AFTER) / dt) + 1
    q2m = np.zeros(N); dq2m = np.zeros(N); bz = np.zeros(N)
    for k in range(N):
        tc = k * dt
        if tc < S.T_SETTLE:
            th = S.SETTLE_KP * (set_q1 - d.qpos[1]) + S.SETTLE_KD * (0 - d.qvel[1])
            tk = S.SETTLE_KP * (set_q2 - d.qpos[2]) + S.SETTLE_KD * (0 - d.qvel[2])
        elif tc < S.T_SETTLE + T_motion:
            tm = tc - S.T_SETTLE
            th = float(np.interp(tm, t_real, tau_h_in)); tk = float(np.interp(tm, t_real, tau_k_in))
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        try:
            mujoco.mj_step(m, d)
        except Exception:
            return None
        q2m[k] = d.qpos[2]         # knee MOTOR angle = encoder
        dq2m[k] = d.qvel[2]        # knee MOTOR velocity = encoder-derived dq2
        bz[k] = d.qpos[0]
        if abs(d.qpos[0]) > 5.0:
            return None
    # compare knee motor angle to measured q2 (mj frame: q2m_meas = -q2)
    q2_meas = -np.asarray(td["q2"]); dq2_meas = -np.asarray(td["dq2"])
    tgrid = np.arange(N) * dt - S.T_SETTLE
    q2_sim_on = np.interp(t_real, tgrid, q2m)
    rmse_q2 = float(np.sqrt(np.mean((q2_sim_on - q2_meas) ** 2)))
    return dict(h_sim=float(bz.max()), dq2_peak=float(np.max(np.abs(dq2m))),
                rmse_q2=rmse_q2, dq2_meas_peak=float(np.max(np.abs(dq2_meas))))


if __name__ == "__main__":
    td = S.load_jump_0424("90_0.75_90_2")
    ap = P4.apply_phase1_params(np.array(FM["mass_15d"]))
    arm_hip = ap["arm_hip"]; arm_knee = ap["arm_knee"]
    print(f"SEA knee POC — jump_0424/90_0.75_90_2  (camera h=0.89, real dq2 peak~27)")
    print(f"rigid baseline arm_knee={arm_knee:.5f}. Sweep k_sea, c_sea, I_rot:\n")
    print(f"{'k_sea':>6} {'c_sea':>6} {'I_rot':>7} | {'h_sim':>6} {'dq2pk':>6} {'rmseq2':>7}")
    for I_rot in [arm_knee, 2 * arm_knee, 4 * arm_knee]:
        for k_sea in [8, 15, 30, 60, 120]:
            for c_sea in [0.05, 0.2]:
                r = run_sea(td, arm_hip, k_sea, c_sea, I_rot)
                if r:
                    print(f"{k_sea:>6} {c_sea:>6} {I_rot:>7.4f} | {r['h_sim']:>6.3f} {r['dq2_peak']:>6.1f} {r['rmse_q2']:>7.4f}")
                else:
                    print(f"{k_sea:>6} {c_sea:>6} {I_rot:>7.4f} | FAIL")
