"""Iter6: 31 sub-experiment simulator with arm_hip + arm_knee as 2D axis.

Iter5 LOCKS (chain KEEP):
  - motor_tm = 0.032s
  - m_base_scale = 1.0358
  - solref_tc = 0.007085
  - imp0 = 0.2526
  - M_thigh_scale = 0.9315 (iter5 best)
  - M_calf_scale  = 1.0148 (iter5 best)
  - M_p_scale     = 0.8175 (iter5 best)
  - M_c_scale     = 0.7813 (iter5 best, actual eval 104)
  - M_foot_extra  = 0.6015 (iter5 best)
  - friction      = 0
  - Mode A: ctrl = -tau_filt (no scale)
  - thigh/calf contype=1 conaffinity=1
  - per-trial q_offsets from iter1

Iter6 AXIS (★ user correction first applied):
  - arm_hip  ∈ [0.001, 0.05]  (was 0 in iters 1-5)
  - arm_knee ∈ [0.001, 0.05]  (was 0 in iters 1-5)

Weights (★ Wh=200 jump-only):
  Wq=100, Wdq=50, Wh=200 (jump only), Wt=0, Wgrf=0.1, Wpen=50, pen_free=2mm
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings('ignore')

import mujoco

GOAL12_DIR = Path("C:/Users/junho/Desktop/jump_opt/goal12")
GOAL18_DIR = Path("C:/Users/junho/Desktop/jump_opt/goal18")
sys.path.insert(0, str(GOAL12_DIR / "iter3"))
sys.path.insert(0, str(GOAL12_DIR / "data_loaders"))
sys.path.insert(0, str(GOAL18_DIR / "iter2"))
sys.path.insert(0, str(GOAL18_DIR / "iter3"))
sys.path.insert(0, str(GOAL18_DIR / "iter4"))
sys.path.insert(0, str(GOAL18_DIR / "iter5"))

from build_xml_i3 import (
    base_z_init as BASE_Z_INIT,
    q1_mu_init as Q1_MU_INIT, q2_mu_init as Q2_MU_INIT,
    SOLREF_D as SOLREF_D_G,
    IMP1 as IMP1_G, IMP_MID as IMP_MID_G,
    FOOT_RADIUS, FOOT_HALF_LEN, L1_VAL, L2_VAL,
    CONE, IMPRATIO, DT,
    M_BASE_CAD,
    M1_CAD, M2_CAD, M_P_CAD, M_C_CAD,
    R1_VAL, R2_VAL, RP_VAL, RC_VAL, LC_VAL, I1_VAL, I2_VAL, IP_VAL, IC_VAL,
)

from sub_sim import (
    load_jump_0424, load_jump_0602, load_jump_position, load_jump_torque,
    T_SETTLE, T_AFTER, SETTLE_KP, SETTLE_KD,
)
from sub_sim_motor_tm import (
    load_sit2stand_cycle, SIT2STAND_NPZ, SIT2STAND_GND_ID,
)


# Iter5 chain locks (15+ params)
MOTOR_TM_LOCK     = 0.032
M_BASE_SCALE_LOCK = 1.0358
SOLREF_TC_LOCK    = 0.007085
IMP0_LOCK         = 0.2526

# Iter5 best mass scales (frozen)
MTS_LOCK  = 0.9315059554829954
MCS_LOCK  = 1.0148252312906139
MPS_LOCK  = 0.8175172505295485
MCPS_LOCK = 0.7813326611103126
MFX_LOCK  = 0.6014600524487825


# ★ Iter6 weights: Wh = 200 (jump-only)
W_Q = 100.0
W_DQ = 50.0
W_H = 200.0
W_T = 0.0
W_GRF = 0.1
W_PEN = 50.0
PEN_FREE_MM = 2.0

FV_HIP = 0.0
FC_HIP = 0.0
FV_KNEE = 0.0
FC_KNEE = 0.0

# ── GOAL19 continuation: previously-untested axes (defaults = original behavior) ──
FOOT_MU_SLIDE = 1.0     # tangential (foot slip). was hardcoded 1.0
FOOT_MU_TORSION = 0.02  # torsional
FOOT_MU_ROLL = 0.01     # rolling
USE_REAL_JUMP_INIT = False  # True: jump settles to trial's real start pose (not fixed Q_MU_INIT)
BASE_Z_INIT_OFF = 0.0   # additive offset to BASE_Z_INIT
JUMP_INTEGRATOR = "implicitfast"  # ADOPTED (re-open): RK4 chattered on stiff contact; implicitfast smooths GRF, total 15182->15121
IMP1_OVERRIDE = None        # solimp max impedance (None=use IMP1_G). higher=firmer contact
SOLIMP_WIDTH_OVERRIDE = None  # solimp width (None=IMP_MID_G). wider=smoother transition
# Joint flex / transmission compliance (GOAL10 tau_scale-free precedent: hip 0.0999, knee 1.0854, springref=0)
STIFF_HIP = 0.0    # hip joint stiffness Nm/rad (parallel elastic; springref=0 -> assists extension from crouch)
STIFF_KNEE = 0.0   # knee joint stiffness Nm/rad


def _fric_str():
    return f"{FOOT_MU_SLIDE:.5f} {FOOT_MU_TORSION:.5f} {FOOT_MU_ROLL:.5f}"


# ── Composite inertia (same as iter5) ────────────────────────────────────────
def ci_locked():
    """Composite mass + COM + I using iter5-locked mass scales."""
    M1 = M1_CAD * MTS_LOCK
    Mp = M_P_CAD * MPS_LOCK
    M2 = M2_CAD * MCS_LOCK
    Mc = M_C_CAD * MCPS_LOCK
    Mf = float(MFX_LOCK)

    I1 = I1_VAL * MTS_LOCK
    Ip = IP_VAL * MPS_LOCK
    I2 = I2_VAL * MCS_LOCK
    Ic = IC_VAL * MCPS_LOCK

    Mt = M1 + Mp
    ctz = -(M1 * R1_VAL + Mp * RP_VAL) / Mt
    dm1 = R1_VAL + ctz
    dmp = RP_VAL + ctz
    It = I1 + M1 * dm1**2 + Ip + Mp * (dmp**2 + LC_VAL**2)

    Mc2 = M2 + Mc + Mf
    ccz = -(M2 * R2_VAL + Mc * RC_VAL + Mf * L2_VAL) / Mc2
    dm2 = R2_VAL + ccz
    dmc = RC_VAL + ccz
    dmf = L2_VAL + ccz
    Ic2 = I2 + M2 * dm2**2 + Ic + Mc * dmc**2 + Mf * dmf**2

    return Mt, ctz, It, Mc2, ccz, Ic2


def _solref_str():
    return f"{SOLREF_TC_LOCK:.6f} {SOLREF_D_G}"

def _solimp_str():
    imp1 = IMP1_OVERRIDE if IMP1_OVERRIDE is not None else IMP1_G
    width = SOLIMP_WIDTH_OVERRIDE if SOLIMP_WIDTH_OVERRIDE is not None else IMP_MID_G
    imp0_eff = min(IMP0_LOCK, imp1 * 0.99)
    return f"{imp0_eff:.6f} {imp1:.5f} {width:.6f} 0.5 2"


def _base_mass():
    return M_BASE_CAD * M_BASE_SCALE_LOCK


# ── Jump XML with arm_hip + arm_knee armature ────────────────────────────────
def build_xml_jump_6d(arm_hip, arm_knee):
    Mt, ctz, It, Mc2, ccz, Ic2 = ci_locked()
    sr = _solref_str(); si = _solimp_str()
    M_base = _base_mass()
    return f"""<mujoco model="iter6_jump_6d">
<option cone="{CONE}" impratio="{IMPRATIO}" gravity="0 0 -9.81" timestep="{DT}" integrator="{JUMP_INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="{_fric_str()}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{_fric_str()}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{_fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{arm_hip:.8f}" damping="{FV_HIP:.8f}" frictionloss="{FC_HIP:.8f}" stiffness="{STIFF_HIP:.6f}" springref="0"/>
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1_VAL}" contype="1" conaffinity="1"/>
      <body name="calf" pos="0 0 -{L1_VAL}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}" damping="{FV_KNEE:.8f}" frictionloss="{FC_KNEE:.8f}" stiffness="{STIFF_KNEE:.6f}" springref="0"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2_VAL}" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot" type="cylinder" size="{FOOT_RADIUS:.4f} {FOOT_HALF_LEN:.4f}" pos="0 0 -{L2_VAL}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


def build_xml_sit2stand_air_6d(arm_hip, arm_knee):
    Mt, ctz, It, Mc2, ccz, Ic2 = ci_locked()
    sr = _solref_str(); si = _solimp_str()
    M_base = _base_mass()
    return f"""<mujoco model="iter6_s2s_air">
<option cone="{CONE}" impratio="{IMPRATIO}" gravity="0 0 -9.81" timestep="{DT}" integrator="implicitfast"/>
<default><default class="leg">
  <geom friction="{_fric_str()}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{_fric_str()}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" pos="0 0 -10.0" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{_fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 1.5" childclass="leg">
    <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{arm_hip:.8f}" damping="{FV_HIP:.8f}" frictionloss="{FC_HIP:.8f}" stiffness="{STIFF_HIP:.6f}" springref="0"/>
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1_VAL}" contype="0" conaffinity="0"/>
      <body name="calf" pos="0 0 -{L1_VAL}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}" damping="{FV_KNEE:.8f}" frictionloss="{FC_KNEE:.8f}" stiffness="{STIFF_KNEE:.6f}" springref="0"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2_VAL}" contype="0" conaffinity="0"/>
        <geom name="foot" class="foot" type="cylinder" size="{FOOT_RADIUS:.4f} {FOOT_HALF_LEN:.4f}" pos="0 0 -{L2_VAL}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


def build_xml_sit2stand_gnd_6d(arm_hip, arm_knee):
    Mt, ctz, It, Mc2, ccz, Ic2 = ci_locked()
    sr = _solref_str(); si = _solimp_str()
    M_base = _base_mass()
    return f"""<mujoco model="iter6_s2s_gnd">
<option cone="{CONE}" impratio="{IMPRATIO}" gravity="0 0 -9.81" timestep="{DT}" integrator="implicitfast"/>
<default><default class="leg">
  <geom friction="{_fric_str()}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{_fric_str()}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{_fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{arm_hip:.8f}" damping="{FV_HIP:.8f}" frictionloss="{FC_HIP:.8f}" stiffness="{STIFF_HIP:.6f}" springref="0"/>
      <inertial pos="0 0 {ctz:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1_VAL}" contype="0" conaffinity="0"/>
      <body name="calf" pos="0 0 -{L1_VAL}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}" damping="{FV_KNEE:.8f}" frictionloss="{FC_KNEE:.8f}" stiffness="{STIFF_KNEE:.6f}" springref="0"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2_VAL}" contype="0" conaffinity="0"/>
        <geom name="foot" class="foot" type="cylinder" size="{FOOT_RADIUS:.4f} {FOOT_HALF_LEN:.4f}" pos="0 0 -{L2_VAL}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


Q1_WAIT_SIM = -(-np.pi/4) - np.pi/2
Q2_WAIT_SIM = -(-np.pi/2)


def run_jump_sim(model, td, q1_offset, q2_offset, motor_tm=MOTOR_TM_LOCK):
    t_real = td['t']
    tau_h_input_raw = -td['tau1_real']
    tau_k_input_raw = -td['tau2_real']

    # Settle target: fixed Q_MU_INIT (original) OR the trial's REAL start pose.
    if USE_REAL_JUMP_INIT:
        q1_start_eff = float(td['q1'][0]) + q1_offset
        q2_start_eff = float(td['q2'][0]) + q2_offset
        set_q1 = -q1_start_eff - np.pi / 2
        set_q2 = -q2_start_eff
    else:
        set_q1, set_q2 = Q1_MU_INIT, Q2_MU_INIT

    data = mujoco.MjData(model)
    data.qpos[:] = [BASE_Z_INIT + BASE_Z_INIT_OFF, set_q1, set_q2]
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    dt = model.opt.timestep
    T_motion = float(t_real[-1])
    N = int((T_SETTLE + T_motion + T_AFTER) / dt) + 1

    t_log = np.arange(N) * dt - T_SETTLE
    q = np.zeros((N, 3))
    dq = np.zeros((N, 3))
    tau_app = np.zeros((N, 2))
    grf_z = np.zeros(N)
    pen_mm = np.zeros(N)
    foot_z_log = np.zeros(N)

    tau_h_filt = 0.0
    tau_k_filt = 0.0
    alpha = dt / (dt + motor_tm) if (motor_tm and motor_tm > 0) else 1.0

    foot_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")

    for k in range(N):
        t_cur = k * dt
        if t_cur < T_SETTLE:
            tau_h = SETTLE_KP * (set_q1 - data.qpos[1]) + SETTLE_KD * (0 - data.qvel[1])
            tau_k = SETTLE_KP * (set_q2 - data.qpos[2]) + SETTLE_KD * (0 - data.qvel[2])
            tau_h_filt = tau_h
            tau_k_filt = tau_k
        elif t_cur < T_SETTLE + T_motion:
            tm = t_cur - T_SETTLE
            tau_h_raw = float(np.interp(tm, t_real, tau_h_input_raw))
            tau_k_raw = float(np.interp(tm, t_real, tau_k_input_raw))
            tau_h_filt = (1 - alpha) * tau_h_filt + alpha * tau_h_raw
            tau_k_filt = (1 - alpha) * tau_k_filt + alpha * tau_k_raw
            tau_h = tau_h_filt
            tau_k = tau_k_filt
        else:
            tau_h = 0.0; tau_k = 0.0
            tau_h_filt = 0.0; tau_k_filt = 0.0
        data.ctrl[:] = [tau_h, tau_k]
        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None
        q[k] = data.qpos
        dq[k] = data.qvel
        tau_app[k] = data.qfrc_actuator[1:3].copy()
        if foot_geom_id >= 0:
            foot_z_log[k] = float(data.geom_xpos[foot_geom_id][2])
        gz = 0.0; pn = 0.0
        for c in range(data.ncon):
            cf = np.zeros(6)
            mujoco.mj_contactForce(model, data, c, cf)
            frame = data.contact[c].frame.reshape(3, 3)
            gz += (frame.T @ cf[:3])[2]
            dist = data.contact[c].dist
            if dist < 0:
                pn = max(pn, -dist * 1000.0)
        grf_z[k] = gz
        pen_mm[k] = pn
        if abs(data.qpos[0]) > 5.0:
            return None

    return dict(t=t_log, q=q, dq=dq, tau_app=tau_app, grf_z=grf_z, pen_mm=pen_mm,
                foot_z=foot_z_log)


def compute_score_jump(td, log, q1_off, q2_off, is_jump=True):
    if log is None:
        return 1e6, None
    t_real = td['t']
    mask = (log['t'] >= 0) & (log['t'] <= t_real[-1])
    if not mask.any():
        return 1e6, None
    q1_sim = -log['q'][:, 1] - np.pi / 2
    q2_sim = -log['q'][:, 2]
    dq1_sim = -log['dq'][:, 1]
    dq2_sim = -log['dq'][:, 2]

    interp = lambda v: np.interp(t_real, log['t'][mask], v[mask])
    rmse = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))

    q1_real_eff = td['q1'] + q1_off
    q2_real_eff = td['q2'] + q2_off

    rmse_q1 = rmse(q1_real_eff, interp(q1_sim))
    rmse_q2 = rmse(q2_real_eff, interp(q2_sim))
    rmse_dq1 = rmse(td['dq1'], interp(dq1_sim))
    rmse_dq2 = rmse(td['dq2'], interp(dq2_sim))
    rmse_grf = rmse(td['grf_z'], interp(log['grf_z']))

    h_sim = float(log['q'][:, 0].max())
    h_real = float(td['h_real'])
    pen_max_mm = float(log['pen_mm'].max())

    score = (W_Q * (rmse_q1 + rmse_q2)
             + W_DQ * (rmse_dq1 + rmse_dq2)
             + (W_H * abs(h_sim - h_real) if is_jump else 0.0)
             + W_GRF * rmse_grf
             + W_PEN * max(0.0, pen_max_mm - PEN_FREE_MM))

    metrics = dict(
        rmse_q1=rmse_q1, rmse_q2=rmse_q2,
        rmse_dq1=rmse_dq1, rmse_dq2=rmse_dq2,
        rmse_grf=rmse_grf,
        h_sim_m=h_sim, h_real_m=h_real,
        pen_max_mm=pen_max_mm,
        foot_z_min_m=float(np.min(log['foot_z'])) if 'foot_z' in log else 0.0,
    )
    return score, metrics


def run_sit2stand_cycle(model, td, q1_offset, q2_offset, motor_tm=MOTOR_TM_LOCK, is_gnd=False):
    t_real = td['t']
    tau_h_raw_arr = -td['tau1_real']
    tau_k_raw_arr = -td['tau2_real']

    q1_start_real_eff = float(td['q1'][0]) + q1_offset
    q2_start_real_eff = float(td['q2'][0]) + q2_offset
    q1_start_sim = -q1_start_real_eff - np.pi / 2
    q2_start_sim = -q2_start_real_eff

    data = mujoco.MjData(model)
    if is_gnd:
        data.qpos[:] = [BASE_Z_INIT, q1_start_sim, q2_start_sim]
        hip_idx = 1; knee_idx = 2
    else:
        data.qpos[:] = [q1_start_sim, q2_start_sim]
        hip_idx = 0; knee_idx = 1
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    dt = model.opt.timestep
    SETTLE_KP_LOC = 500.0
    SETTLE_KD_LOC = 20.0
    T_SETTLE_LOC = 0.3
    N_SETTLE_LOC = int(T_SETTLE_LOC / dt)
    for _ in range(N_SETTLE_LOC):
        err_h = q1_start_sim - data.qpos[hip_idx]
        err_k = q2_start_sim - data.qpos[knee_idx]
        tau_h = SETTLE_KP_LOC * err_h + SETTLE_KD_LOC * (0 - data.qvel[hip_idx])
        tau_k = SETTLE_KP_LOC * err_k + SETTLE_KD_LOC * (0 - data.qvel[knee_idx])
        data.ctrl[:] = [tau_h, tau_k]
        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    T_motion = float(t_real[-1])
    T_after = 0.05
    N = int((T_motion + T_after) / dt) + 1

    t_log = np.arange(N) * dt
    q = np.zeros((N, len(data.qpos)))
    dq = np.zeros((N, len(data.qvel)))
    tau_app = np.zeros((N, 2))
    pen_mm = np.zeros(N)
    grf_z = np.zeros(N)

    tau_h_filt = 0.0
    tau_k_filt = 0.0
    alpha = dt / (dt + motor_tm) if (motor_tm and motor_tm > 0) else 1.0

    for k in range(N):
        t_cur = k * dt
        if t_cur < T_motion:
            tau_h_raw = float(np.interp(t_cur, t_real, tau_h_raw_arr))
            tau_k_raw = float(np.interp(t_cur, t_real, tau_k_raw_arr))
            tau_h_filt = (1 - alpha) * tau_h_filt + alpha * tau_h_raw
            tau_k_filt = (1 - alpha) * tau_k_filt + alpha * tau_k_raw
            tau_h = tau_h_filt
            tau_k = tau_k_filt
        else:
            tau_h = 0.0; tau_k = 0.0
            tau_h_filt = 0.0; tau_k_filt = 0.0
        data.ctrl[:] = [tau_h, tau_k]
        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None
        q[k] = data.qpos
        dq[k] = data.qvel
        if is_gnd:
            tau_app[k] = data.qfrc_actuator[1:3].copy()
        else:
            tau_app[k] = data.qfrc_actuator[0:2].copy()
        gz = 0.0; pn = 0.0
        for c in range(data.ncon):
            cf = np.zeros(6)
            mujoco.mj_contactForce(model, data, c, cf)
            frame = data.contact[c].frame.reshape(3, 3)
            gz += (frame.T @ cf[:3])[2]
            dist = data.contact[c].dist
            if dist < 0:
                pn = max(pn, -dist * 1000.0)
        grf_z[k] = gz
        pen_mm[k] = pn

    return dict(t=t_log, q=q, dq=dq, tau_app=tau_app,
                grf_z=grf_z, pen_mm=pen_mm, hip_idx=hip_idx, knee_idx=knee_idx)


def compute_score_sit2stand(td, log, q1_off, q2_off, is_gnd=False):
    if log is None:
        return 1e6, None
    t_real = td['t']
    mask = (log['t'] >= 0) & (log['t'] <= t_real[-1])
    if not mask.any():
        return 1e6, None
    hip_idx = log['hip_idx']; knee_idx = log['knee_idx']
    q1_sim = -log['q'][:, hip_idx] - np.pi / 2
    q2_sim = -log['q'][:, knee_idx]
    dq1_sim = -log['dq'][:, hip_idx]
    dq2_sim = -log['dq'][:, knee_idx]

    interp = lambda v: np.interp(t_real, log['t'][mask], v[mask])
    rmse = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))

    q1_real_eff = td['q1'] + q1_off
    q2_real_eff = td['q2'] + q2_off

    rmse_q1 = rmse(q1_real_eff, interp(q1_sim))
    rmse_q2 = rmse(q2_real_eff, interp(q2_sim))
    rmse_dq1 = rmse(td['dq1'], interp(dq1_sim))
    rmse_dq2 = rmse(td['dq2'], interp(dq2_sim))
    pen_max_mm = float(log['pen_mm'].max())

    rmse_grf = 0.0
    if is_gnd and 'grf_z' in td:
        rmse_grf = rmse(td['grf_z'], interp(log['grf_z']))

    score = (W_Q * (rmse_q1 + rmse_q2)
             + W_DQ * (rmse_dq1 + rmse_dq2)
             + (W_GRF * rmse_grf if is_gnd else 0.0)
             + W_PEN * max(0.0, pen_max_mm - PEN_FREE_MM))

    metrics = dict(
        rmse_q1=rmse_q1, rmse_q2=rmse_q2,
        rmse_dq1=rmse_dq1, rmse_dq2=rmse_dq2,
        rmse_grf=rmse_grf if is_gnd else 0.0,
        pen_max_mm=pen_max_mm,
    )
    return score, metrics


JUMP_LOADERS = {
    "jump_0424": load_jump_0424,
    "jump_0602": load_jump_0602,
    "jump_position_0421": load_jump_position,
    "jump_torque_0422": load_jump_torque,
}


def run_one_sub(ds, sub, q1_off, q2_off, arm_hip, arm_knee,
                motor_tm=MOTOR_TM_LOCK):
    full_id = f"{ds}/{sub}"

    if ds in JUMP_LOADERS:
        loader = JUMP_LOADERS[ds]
        td = loader(sub)
        xml = build_xml_jump_6d(arm_hip, arm_knee)
        model = mujoco.MjModel.from_xml_string(xml)
        log = run_jump_sim(model, td, q1_off, q2_off, motor_tm)
        return compute_score_jump(td, log, q1_off, q2_off, is_jump=True)

    if full_id in SIT2STAND_NPZ:
        is_gnd = (full_id == SIT2STAND_GND_ID)
        cyc_list = load_sit2stand_cycle(full_id)
        if cyc_list is None or len(cyc_list) == 0:
            return None, None
        if is_gnd:
            xml = build_xml_sit2stand_gnd_6d(arm_hip, arm_knee)
        else:
            xml = build_xml_sit2stand_air_6d(arm_hip, arm_knee)
        model = mujoco.MjModel.from_xml_string(xml)

        scores = []
        metrics_list = []
        for td in cyc_list:
            log = run_sit2stand_cycle(model, td, q1_off, q2_off, motor_tm, is_gnd=is_gnd)
            score, m = compute_score_sit2stand(td, log, q1_off, q2_off, is_gnd=is_gnd)
            if score is not None and score < 1e5 and m is not None and not np.isnan(score):
                scores.append(score)
                metrics_list.append(m)
        if not scores:
            return 1e6, None
        mean_score = float(np.mean(scores))
        mean_metrics = {}
        for k in metrics_list[0].keys():
            mean_metrics[k] = float(np.mean([m[k] for m in metrics_list]))
        mean_metrics['n_cycles_valid'] = len(scores)
        mean_metrics['n_cycles_total'] = len(cyc_list)
        return mean_score, mean_metrics

    return None, None


if __name__ == "__main__":
    import time
    with open(GOAL18_DIR / "iter2/iter1_offsets.json") as f:
        offsets = json.load(f)
    print(f"Loaded {len(offsets)} sub offsets")
    # Smoke test
    o = [x for x in offsets if x['ds'] == 'jump_0424' and x['sub'] == '60_0.75_60_2'][0]
    t0 = time.time()
    s, m = run_one_sub(o['ds'], o['sub'], o['q1_off'], o['q2_off'], 0.005, 0.005)
    print(f"jump smoke (arm_hip=0.005, arm_knee=0.005): score={s:.2f} ({time.time()-t0:.2f}s)")
    if m is not None:
        print(f"  rmse_q1={m['rmse_q1']:.3f} h_sim={m['h_sim_m']:.3f} h_real={m['h_real_m']:.3f}")

    o = [x for x in offsets if x['ds'] == 'sit2stand_air_0319'][0]
    t0 = time.time()
    s, m = run_one_sub(o['ds'], o['sub'], o['q1_off'], o['q2_off'], 0.005, 0.005)
    print(f"s2s_air smoke: score={s:.2f} ({time.time()-t0:.2f}s)")
