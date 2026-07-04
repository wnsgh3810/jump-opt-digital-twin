"""GOAL19 Phase 11k — INVERSE-DYNAMICS identification (methodology upgrade).

Instead of fitting forward-sim RMSE (black-box, lets flex/friction absorb EoM error),
identify physical inertial params by minimizing the EoM residual directly.

Clean contact handling: model STANCE as an INVERTED chain with the foot fixed to the
world (foot=root, calf->thigh->base going up). No contact, no GRF confound — pure
rigid-body inverse dynamics via mj_rne. Then optimize inertial scales to minimize the
residual (mj_rne torque vs measured torque) across all jump-stance samples.

Purpose-safe: SINGLE unified param set, physical bounds, no per-trial fudge.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco
from scipy.signal import savgol_filter

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments
FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))


def build_inverted(Mt, ctz, It, Mc2, ccz, Ic2, M_base):
    """Foot at world origin (fixed); calf -> thigh -> base going UP. Joints: knee, hip."""
    L1, L2 = S.L1_VAL, S.L2_VAL
    calf_com = L2 + ccz    # CoM height above foot (ccz<0 from knee)
    thigh_com = L1 + ctz   # CoM height above knee (ctz<0 from hip)
    return f"""<mujoco model="inv_stance">
<option gravity="0 0 -9.81" integrator="implicitfast"/>
<worldbody>
  <body name="calf" pos="0 0 0">
    <inertial pos="0 0 {calf_com:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
    <geom type="capsule" size="0.015" fromto="0 0 0 0 0 {L2}" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 {L2}">
      <joint name="knee" type="hinge" axis="0 1 0"/>
      <inertial pos="0 0 {thigh_com:.5f}" mass="{Mt:.5f}" diaginertia="{It:.6f} {It:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 {L1}" contype="0" conaffinity="0"/>
      <body name="base" pos="0 0 {L1}">
        <joint name="hip" type="hinge" axis="0 1 0"/>
        <inertial pos="0 0 0" mass="{M_base:.6f}" diaginertia="0.005 0.005 0.005"/>
        <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
      </body>
    </body>
  </body>
</worldbody>
</mujoco>"""


def verify_geometry():
    """Check the inverted model's base position matches the normal model for a test pose."""
    ap = P4.apply_phase1_params(np.array(FM["mass_15d"]))
    Mt, ctz, It, Mc2, ccz, Ic2 = S.ci_locked(); Mb = S._base_mass()
    # normal jump model
    mn = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
    dn = mujoco.MjData(mn)
    q1m, q2m = -1.0, 2.3  # test pose (mj frame)
    dn.qpos[:] = [0.5, q1m, q2m]; mujoco.mj_forward(mn, dn)
    fg = mujoco.mj_name2id(mn, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    base_bid = mujoco.mj_name2id(mn, mujoco.mjtObj.mjOBJ_BODY, "base")
    foot_to_base_normal = dn.xpos[base_bid] - dn.geom_xpos[fg]
    # inverted model — try both sign conventions
    mi = mujoco.MjModel.from_xml_string(build_inverted(Mt, ctz, It, Mc2, ccz, Ic2, Mb))
    di = mujoco.MjData(mi)
    bb = mujoco.mj_name2id(mi, mujoco.mjtObj.mjOBJ_BODY, "base")
    for s1, s2 in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
        di.qpos[:] = [s2 * q2m, s1 * q1m]; mujoco.mj_forward(mi, di)  # [knee, hip]
        ft2b = di.xpos[bb]  # foot at origin
        err = np.linalg.norm(np.abs(ft2b[[0, 2]]) - np.abs(foot_to_base_normal[[0, 2]]))
        print(f"  sign(hip={s1},knee={s2}): inv foot->base={ft2b[[0,2]].round(3)} normal={foot_to_base_normal[[0,2]].round(3)} err={err:.4f}")


def clean_residual(td, xm=None):
    """Constrained inverse-dyn residual: EoM projected to eliminate the (unmeasured)
    foot contact force. Residual = part of (M ddq + C + G - S^T tau) NOT in range(J_foot^T)."""
    ap = P4.apply_phase1_params(xm if xm is not None else np.array(FM["mass_15d"]))
    m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
    d = mujoco.MjData(m)
    fg = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    t = np.asarray(td["t"]); grf = savgol_filter(np.asarray(td["grf_z"]), 11, 3)
    q1m = -np.asarray(td["q1"]) - np.pi / 2; q2m = -np.asarray(td["q2"])
    dq1 = savgol_filter(-np.asarray(td["dq1"]), 11, 3); dq2 = savgol_filter(-np.asarray(td["dq2"]), 11, 3)
    tau1 = np.asarray(td["tau1_real"]); tau2 = np.asarray(td["tau2_real"])
    # base_z(t) from FK (foot on ground)
    bz = np.zeros(len(t))
    for i in range(len(t)):
        d.qpos[:] = [1.0, q1m[i], q2m[i]]; mujoco.mj_forward(m, d)
        bz[i] = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    bz = savgol_filter(bz, 11, 3)
    dbz = np.gradient(bz, t); ddbz = np.gradient(dbz, t)
    ddq1 = np.gradient(dq1, t); ddq2 = np.gradient(dq2, t)
    stance = grf > 15
    res = []
    for i in np.where(stance)[0]:
        d.qpos[:] = [bz[i], q1m[i], q2m[i]]; d.qvel[:] = [dbz[i], dq1[i], dq2[i]]
        mujoco.mj_forward(m, d)
        d.qacc[:] = [ddbz[i], ddq1[i], ddq2[i]]
        lhs = np.zeros(m.nv); mujoco.mj_rne(m, d, 1, lhs)   # M ddq + C + G
        Stau = np.array([0.0, -tau1[i], -tau2[i]])          # applied (mj sign)
        b = lhs - Stau
        jacp = np.zeros((3, m.nv)); mujoco.mj_jac(m, d, jacp, None, d.geom_xpos[fg], m.geom_bodyid[fg])
        A = jacp[[0, 2], :].T                                # contact force acts via J_foot^T (x,z)
        lam, *_ = np.linalg.lstsq(A, b, rcond=None)
        res.append(b - A @ lam)                              # unexplainable residual
    return np.array(res)  # (Nstance, 3): [base_z, hip, knee] residual


if __name__ == "__main__":
    print("=== CLEAN constrained inverse-dyn residual (contact force projected out) ===")
    tot = {"base": [], "hip": [], "knee": []}
    for fn, sub in [(S.load_jump_0424, "90_0.75_90_2"), (S.load_jump_0602, "90_0.75_90_2"),
                    (S.load_jump_0424, "120_2.2_150_2.5"), (S.load_jump_position, "P70_D0.75_P70_D2")]:
        r = clean_residual(fn(sub))
        tau2pk = float(np.max(np.abs(fn(sub)["tau2_real"])))
        print(f"{fn.__name__.replace('load_jump_',''):<6}/{sub:<16} "
              f"|res| base={np.mean(np.abs(r[:,0])):.2f} hip={np.mean(np.abs(r[:,1])):.2f} "
              f"knee={np.mean(np.abs(r[:,2])):.2f} Nm  (tau2pk={tau2pk:.1f})")
        tot["knee"].append(np.mean(np.abs(r[:, 2])))
    print("\\n=> if knee residual << applied torque (~19): model dynamics OK, gap is contact/integration.")
    print("   if knee residual comparable to torque: rigid dynamics (mass/inertia) genuinely wrong.")
