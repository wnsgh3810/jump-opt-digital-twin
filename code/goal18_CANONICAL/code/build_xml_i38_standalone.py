"""Self-contained build_xml_i38 — canonical XML generator for GOAL18 rendering.

Extracted from goal12/iter38/run_i38.py + goal12/iter3/build_xml_i3.py so
this file has NO external dependency. Regenerating leg.xml from scratch
requires only Python + numpy.

Used by regen_all.py:
    xml_str = build_xml_i38(**iter38_best_params)
    Path('leg.xml').write_text(xml_str, encoding='utf-8')

Fixed constants (CAD-verified, DO NOT CHANGE unless robot changes):
    L1 = L2 = 0.25 m (thigh, calf lengths)
    LC = 0.03 m (calf offset)
    Foot cylinder: radius 21mm × half-length 6.5mm (line contact y-axis)
    dt = 0.0005s, RK4 integrator, elliptic cone impratio 100
"""
import numpy as np

# ═══════════════════════════════════════════════════════════════════════
# MuJoCo solver options
# ═══════════════════════════════════════════════════════════════════════
DT         = 0.0005      # timestep [s]  — CRITICAL: settling steps depend on this
INTEGRATOR = 'RK4'
CONE       = 'elliptic'
IMPRATIO   = 100

# Contact defaults (Iter2 CMA-ES best; overrideable via params)
SOLREF_D_G = 1.6072
IMP1_G     = 0.72007
IMP_MID_G  = 0.005409

# ═══════════════════════════════════════════════════════════════════════
# CAD constants (link geometry + masses) — VERIFIED, DO NOT CHANGE
# ═══════════════════════════════════════════════════════════════════════
M1_CAD     = 0.91281     # thigh main body [kg]
M2_CAD     = 0.23704     # calf main body [kg]
M_C_CAD    = 0.65601     # calf motor [kg]
M_P_CAD    = 0.13657     # thigh motor [kg]
M_FOOT_EXTRA = 0.018461  # foot mass extra [kg]

R1_VAL = 0.05646; R2_VAL = 0.05884  # thigh/calf CoM radial offsets
RC_VAL = 0.02069; RP_VAL = 0.13258
L1_VAL = 0.25;    L2_VAL = 0.25;    LC_VAL = 0.03   # link lengths [m]
I1_VAL = 0.0092344; I2_VAL = 0.001805
IC_VAL = 0.0005797; IP_VAL = 0.0008858

FOOT_RADIUS   = 0.021    # 21mm cylinder radius
FOOT_HALF_LEN = 0.0065   # 6.5mm half-length (13mm total, y-axis)

# ═══════════════════════════════════════════════════════════════════════
# Iter2 joint params (defaults; overrideable)
# ═══════════════════════════════════════════════════════════════════════
STIFF_HIP_G  = 0.08012
STIFF_KNEE_G = 1.16157
FC_KNEE_G    = 0.02132
ARM_KNEE_G   = 0.00490
ARM_HIP_FIXED = 0.0


def composite_inertia_scaled(m_base, m_thigh_scale=1.0, m_calf_scale=1.0):
    """Compute composite inertias of thigh & calf assemblies with mass scales."""
    M1 = M1_CAD * m_thigh_scale; Mp = M_P_CAD * m_thigh_scale
    M2 = M2_CAD * m_calf_scale;  Mc = M_C_CAD * m_calf_scale; Mf = M_FOOT_EXTRA
    I1 = I1_VAL * m_thigh_scale; Ip = IP_VAL * m_thigh_scale
    I2 = I2_VAL * m_calf_scale;  Ic = IC_VAL * m_calf_scale
    M_thigh = M1 + Mp
    com_thigh_z = -(M1 * R1_VAL + Mp * RP_VAL) / M_thigh
    d_m1 = R1_VAL + com_thigh_z; d_mp = RP_VAL + com_thigh_z
    I_thigh = I1 + M1 * d_m1**2 + Ip + Mp * (d_mp**2 + LC_VAL**2)
    M_calf = M2 + Mc + Mf
    com_calf_z = -(M2 * R2_VAL + Mc * RC_VAL + Mf * L2_VAL) / M_calf
    d_m2 = R2_VAL + com_calf_z; d_mc = RC_VAL + com_calf_z; d_mf = L2_VAL + com_calf_z
    I_calf = I2 + M2 * d_m2**2 + Ic + Mc * d_mc**2 + Mf * d_mf**2
    return dict(M_base=m_base, M_thigh=M_thigh, com_thigh_z=com_thigh_z, I_thigh=I_thigh,
                M_calf=M_calf, com_calf_z=com_calf_z, I_calf=I_calf)


def build_xml_i38(fv_hip, fv_knee, fc_hip, m_base, solref_tc, imp0,
                  m_thigh_scale, m_calf_scale, fc_knee=FC_KNEE_G, arm_knee=ARM_KNEE_G):
    """Generate MuJoCo XML for GOAL18 canonical rendering.

    Structure:
      - 3-DoF: base_z slide + hip hinge + knee hinge (all axis y)
      - Floor at z=0 (checker texture, groundplane material)
      - Base body at z=0 with slide joint
      - Thigh capsule length L1=0.25m, radius 18mm, rgba light-purple
      - Calf capsule length L2=0.25m, radius 14mm, rgba teal-gray
      - Foot cylinder line-contact (fromto y-axis), radius 21mm × 13mm
      - Contact: floor + foot (thigh/calf/base contype=1 but only foot collides
        with floor; thigh/calf conaffinity=1 for self-collision if needed)
      - Actuators: hip_act, knee_act (motor gear=1)
    """
    ci = composite_inertia_scaled(m_base, m_thigh_scale, m_calf_scale)
    M_thigh = ci['M_thigh']; com_thigh_z = ci['com_thigh_z']; I_thigh = ci['I_thigh']
    M_calf  = ci['M_calf'];  com_calf_z  = ci['com_calf_z'];  I_calf  = ci['I_calf']
    imp0_v = min(max(imp0, 0.001), IMP1_G * 0.95)
    solref = f"{solref_tc:.6f} {SOLREF_D_G}"
    solimp = f"{imp0_v:.5f} {IMP1_G:.5f} {IMP_MID_G:.6f} 0.5 2"

    return f"""<mujoco model="g12_iter38_11d">
<option cone="{CONE}" impratio="{IMPRATIO}" gravity="0 0 -9.81" timestep="{DT}" integrator="{INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="1.0 0.02 0.01" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{FOOT_RADIUS:.4f}" priority="1"
       solref="{solref}" solimp="{solimp}" condim="6"/>
  </default>
</default></default>
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
  <texture type="2d" name="groundplane" builtin="checker" mark="edge"
           rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>
  <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
</asset>
<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"
        solref="{solref}" solimp="{solimp}"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{m_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" rgba="0.5 0.5 0.5 1" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{ARM_HIP_FIXED:.8f}"
             damping="{fv_hip:.8f}" frictionloss="{fc_hip:.8f}"
             stiffness="{STIFF_HIP_G:.8f}" springref="0"/>
      <inertial pos="0 0 {com_thigh_z:.5f}" mass="{M_thigh:.5f}"
                diaginertia="{I_thigh:.6f} {I_thigh:.6f} 0.0002"/>
      <geom type="capsule" size="0.018" fromto="0 0 0 0 0 -{L1_VAL:.4f}"
            rgba="0.6 0.6 0.7 1" contype="1" conaffinity="1"/>
      <body name="calf" pos="0 0 -{L1_VAL:.4f}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}"
               damping="{fv_knee:.8f}" frictionloss="{fc_knee:.8f}"
               stiffness="{STIFF_KNEE_G:.8f}" springref="0"/>
        <inertial pos="0 0 {com_calf_z:.5f}" mass="{M_calf:.5f}"
                  diaginertia="{I_calf:.6f} {I_calf:.6f} 0.0001"/>
        <geom type="capsule" size="0.014" fromto="0 0 0 0 0 -{L2_VAL:.4f}"
              rgba="0.5 0.6 0.6 1" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot"
              fromto="0 -{FOOT_HALF_LEN:.4f} -{L2_VAL:.4f}  0 {FOOT_HALF_LEN:.4f} -{L2_VAL:.4f}"
              rgba="0.5 0.5 0.5 1"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_act" joint="hip" gear="1"/>
  <motor name="knee_act" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


# ═══════════════════════════════════════════════════════════════════════
# Iter38 best params (0424_60_0.75_60_2 trial × Iter6 overrides)
# ═══════════════════════════════════════════════════════════════════════
ITER38_BEST_PARAMS_ITER6 = dict(
    fv_hip=0.44242008,      # hip viscous damping
    fv_knee=0.005157814,    # knee viscous damping
    fc_hip=2.04564549,      # hip Coulomb friction
    fc_knee=0.18582999,     # knee Coulomb friction
    m_base=1.28966501,      # 1.2450909688928333 × 1.0358 (iter6 override)
    solref_tc=0.007085,     # iter6 override
    imp0=0.2526,            # iter6 override
    m_thigh_scale=0.94569,  # 1.0154887550602512 × 0.9315
    m_calf_scale=0.76172,   # 0.7505875318271736 × 1.0148
    arm_knee=0.01983,       # iter6 override
)


if __name__ == '__main__':
    # Generate canonical leg.xml
    from pathlib import Path
    xml = build_xml_i38(**ITER38_BEST_PARAMS_ITER6)
    out = Path(__file__).parent / 'leg.xml'
    out.write_text(xml, encoding='utf-8')
    print(f'Wrote canonical leg.xml ({len(xml)} bytes) to {out}')
