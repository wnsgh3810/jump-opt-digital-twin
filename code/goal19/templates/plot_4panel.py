"""Reusable 4-panel compare plotter for GOAL19 (V20 convention).

Panels: (1) q1/q2 angles, (2) dq1/dq2 velocities, (3) tau applied, (4) GRF_z.
Sim (solid) vs Real (dashed). Colors auto (matplotlib cycle) per feedback_plot_colors.

Usage:
    from plot_4panel import apply_phase1_params, plot_sub
    apply_phase1_params(best_x)   # 15D vector (or None for Pure CAD)
    plot_sub("jump_0424", "60_0.75_60_2", out_png)
"""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

TEMPLATES = Path(__file__).resolve().parent
sys.path.insert(0, str(TEMPLATES))
import sub_sim_iter6v2 as S
import mujoco

# per-trial offsets
OFFSETS_PATH = Path("C:/Users/junho/Desktop/jump_opt/goal18/iter2/iter1_offsets.json")
with open(OFFSETS_PATH) as f:
    _OFFS = json.load(f)
OFFSET_MAP = {(o["ds"], o["sub"]): (o["q1_off"], o["q2_off"]) for o in _OFFS}


def apply_pure_cad():
    """Set S module to Phase 0 Pure CAD."""
    S.MOTOR_TM_LOCK = 0.0
    S.M_BASE_SCALE_LOCK = 1.0
    S.SOLREF_TC_LOCK = 0.006320
    S.IMP0_LOCK = 0.14301
    S.MTS_LOCK = S.MCS_LOCK = S.MPS_LOCK = S.MCPS_LOCK = 1.0
    S.MFX_LOCK = 0.0
    S.FV_HIP = S.FV_KNEE = S.FC_HIP = S.FC_KNEE = 0.001
    S.W_Q, S.W_DQ, S.W_H, S.W_T, S.W_GRF, S.W_PEN = 100.0, 50.0, 100.0, 0.0, 0.1, 50.0
    return dict(arm_hip=0.0, arm_knee=0.00490)


def apply_phase1_params(x):
    """Apply 15D Phase 1 vector. Returns (arm_hip, arm_knee)."""
    apply_pure_cad()
    if x is None:
        return dict(arm_hip=0.0, arm_knee=0.00490)
    (M_base_s, M_thigh_s, M_calf_s, M_p_s, M_c_s, M_foot_ex,
     I_thigh_s, I_calf_s, I_p_s, I_c_s,
     dz_th, dx_th, dz_ca, dx_ca, arm_k) = x
    S.M_BASE_SCALE_LOCK = float(M_base_s)
    S.MTS_LOCK = float(M_thigh_s); S.MCS_LOCK = float(M_calf_s)
    S.MPS_LOCK = float(M_p_s); S.MCPS_LOCK = float(M_c_s)
    S.MFX_LOCK = float(M_foot_ex)
    from build_xml_i3 import (M1_CAD, M2_CAD, M_P_CAD, M_C_CAD,
        R1_VAL, R2_VAL, RP_VAL, RC_VAL, LC_VAL, L2_VAL,
        I1_VAL, I2_VAL, IP_VAL, IC_VAL)

    def ci_phase1():
        M1 = M1_CAD * M_thigh_s; Mp = M_P_CAD * M_p_s
        M2 = M2_CAD * M_calf_s; Mc = M_C_CAD * M_c_s; Mf = float(M_foot_ex)
        I1 = I1_VAL * I_thigh_s; Ip = IP_VAL * I_p_s
        I2 = I2_VAL * I_calf_s; Ic = IC_VAL * I_c_s
        r1s = R1_VAL + dz_th; rps = RP_VAL + dz_th
        Mt = M1 + Mp; ctz = -(M1*r1s + Mp*rps)/Mt
        dm1 = r1s + ctz; dmp = rps + ctz; lc_eff = LC_VAL + dx_th
        It = I1 + M1*dm1**2 + Ip + Mp*(dmp**2 + lc_eff**2)
        r2s = R2_VAL + dz_ca; rcs = RC_VAL + dz_ca; l2s = L2_VAL + dz_ca
        Mc2 = M2 + Mc + Mf; ccz = -(M2*r2s + Mc*rcs + Mf*l2s)/Mc2
        dm2 = r2s + ccz; dmc = rcs + ccz; dmf = l2s + ccz
        Ic2 = I2 + M2*dm2**2 + Ic + Mc*dmc**2 + Mf*dmf**2 + Mc2*dx_ca**2
        return Mt, ctz, It, Mc2, ccz, Ic2
    S.ci_locked = ci_phase1
    return dict(arm_hip=0.0, arm_knee=float(arm_k))


def _run_jump_with_log(ds, sub, arm_hip, arm_knee):
    from sub_sim import load_jump_0424, load_jump_0602, load_jump_position, load_jump_torque
    LOADERS = {"jump_0424": load_jump_0424, "jump_0602": load_jump_0602,
               "jump_position_0421": load_jump_position, "jump_torque_0422": load_jump_torque}
    td = LOADERS[ds](sub)
    q1_off, q2_off = OFFSET_MAP.get((ds, sub), (0.0, 0.0))
    xml = S.build_xml_jump_6d(arm_hip, arm_knee)
    model = mujoco.MjModel.from_xml_string(xml)
    log = S.run_jump_sim(model, td, q1_off, q2_off, motor_tm=0.0)
    return td, log, q1_off, q2_off


def plot_sub(ds, sub, out_png, arm_hip=0.0, arm_knee=0.00490, title_extra=""):
    """4-panel sim-vs-real. Currently supports jump datasets (full q/dq/tau/grf)."""
    is_jump = ds in ("jump_0424", "jump_0602", "jump_position_0421", "jump_torque_0422")
    if not is_jump:
        return _plot_sit2stand(ds, sub, out_png, arm_hip, arm_knee, title_extra)

    td, log, q1_off, q2_off = _run_jump_with_log(ds, sub, arm_hip, arm_knee)
    if log is None:
        print(f"  plot skip {ds}/{sub}: sim returned None")
        return False

    t_real = td['t']
    mask = (log['t'] >= 0) & (log['t'] <= t_real[-1])
    ts = log['t'][mask]
    q1_sim = (-log['q'][:, 1] - np.pi/2)[mask]
    q2_sim = (-log['q'][:, 2])[mask]
    dq1_sim = (-log['dq'][:, 1])[mask]
    dq2_sim = (-log['dq'][:, 2])[mask]
    # tau_app is in MuJoCo joint frame (= -tau_real by Mode A construction).
    # Convert to canonical/real frame (negate) so it overlays tau_real, exactly
    # as the angles are converted (q_sim = -q_mj - pi/2). Otherwise the two curves
    # look like mirror images of the SAME torque.
    tau1_sim = (-log['tau_app'][:, 0])[mask]
    tau2_sim = (-log['tau_app'][:, 1])[mask]
    grf_sim = log['grf_z'][mask]

    q1_real = td['q1'] + q1_off
    q2_real = td['q2'] + q2_off

    fig, ax = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(f"{ds}/{sub}  (Mode A){title_extra}", fontsize=12)

    # Panel 1: angles
    l1, = ax[0,0].plot(ts, q1_sim, label="q1 sim")
    ax[0,0].plot(t_real, q1_real, '--', color=l1.get_color(), label="q1 real")
    l2, = ax[0,0].plot(ts, q2_sim, label="q2 sim")
    ax[0,0].plot(t_real, q2_real, '--', color=l2.get_color(), label="q2 real")
    ax[0,0].set_title("Joint angles [rad]"); ax[0,0].legend(fontsize=8); ax[0,0].grid(alpha=0.3)

    # Panel 2: velocities
    l3, = ax[0,1].plot(ts, dq1_sim, label="dq1 sim")
    ax[0,1].plot(t_real, td['dq1'], '--', color=l3.get_color(), label="dq1 real")
    l4, = ax[0,1].plot(ts, dq2_sim, label="dq2 sim")
    ax[0,1].plot(t_real, td['dq2'], '--', color=l4.get_color(), label="dq2 real")
    ax[0,1].set_title("Joint velocities [rad/s]"); ax[0,1].legend(fontsize=8); ax[0,1].grid(alpha=0.3)

    # Panel 3: tau (applied sim vs real input)
    l5, = ax[1,0].plot(ts, tau1_sim, label="tau1 sim(applied)")
    ax[1,0].plot(t_real, td['tau1_real'], '--', color=l5.get_color(), label="tau1 real")
    l6, = ax[1,0].plot(ts, tau2_sim, label="tau2 sim(applied)")
    ax[1,0].plot(t_real, td['tau2_real'], '--', color=l6.get_color(), label="tau2 real")
    ax[1,0].set_title("Joint torque [Nm]"); ax[1,0].legend(fontsize=8); ax[1,0].grid(alpha=0.3)

    # Panel 4: GRF
    l7, = ax[1,1].plot(ts, grf_sim, label="GRF sim")
    ax[1,1].plot(t_real, td['grf_z'], '--', color=l7.get_color(), label="GRF real")
    ax[1,1].set_title("GRF_z [N]"); ax[1,1].legend(fontsize=8); ax[1,1].grid(alpha=0.3)

    for a in ax.flat:
        a.set_xlabel("t [s]")
    fig.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    return True


def _plot_sit2stand(ds, sub, out_png, arm_hip, arm_knee, title_extra):
    full_id = f"{ds}/{sub}"
    from sub_sim_motor_tm import load_sit2stand_cycle, SIT2STAND_GND_ID
    is_gnd = (full_id == SIT2STAND_GND_ID)
    cyc = load_sit2stand_cycle(full_id)
    if not cyc:
        print(f"  plot skip {full_id}: no cycles")
        return False
    td = cyc[0]
    q1_off, q2_off = OFFSET_MAP.get((ds, sub), (0.0, 0.0))
    xml = S.build_xml_sit2stand_gnd_6d(arm_hip, arm_knee) if is_gnd else S.build_xml_sit2stand_air_6d(arm_hip, arm_knee)
    model = mujoco.MjModel.from_xml_string(xml)
    log = S.run_sit2stand_cycle(model, td, q1_off, q2_off, motor_tm=0.0, is_gnd=is_gnd)
    if log is None:
        return False
    hip, knee = log['hip_idx'], log['knee_idx']
    t_real = td['t']
    mask = (log['t'] >= 0) & (log['t'] <= t_real[-1])
    ts = log['t'][mask]
    q1_sim = (-log['q'][:, hip] - np.pi/2)[mask]
    q2_sim = (-log['q'][:, knee])[mask]
    dq1_sim = (-log['dq'][:, hip])[mask]
    dq2_sim = (-log['dq'][:, knee])[mask]

    fig, ax = plt.subplots(2, 2, figsize=(13, 8))
    fig.suptitle(f"{full_id}  (Mode A, sit2stand){title_extra}", fontsize=12)
    l1, = ax[0,0].plot(ts, q1_sim, label="q1 sim")
    ax[0,0].plot(t_real, td['q1']+q1_off, '--', color=l1.get_color(), label="q1 real")
    l2, = ax[0,0].plot(ts, q2_sim, label="q2 sim")
    ax[0,0].plot(t_real, td['q2']+q2_off, '--', color=l2.get_color(), label="q2 real")
    ax[0,0].set_title("Joint angles [rad]"); ax[0,0].legend(fontsize=8); ax[0,0].grid(alpha=0.3)
    l3, = ax[0,1].plot(ts, dq1_sim, label="dq1 sim")
    ax[0,1].plot(t_real, td['dq1'], '--', color=l3.get_color(), label="dq1 real")
    l4, = ax[0,1].plot(ts, dq2_sim, label="dq2 sim")
    ax[0,1].plot(t_real, td['dq2'], '--', color=l4.get_color(), label="dq2 real")
    ax[0,1].set_title("Joint velocities [rad/s]"); ax[0,1].legend(fontsize=8); ax[0,1].grid(alpha=0.3)
    if is_gnd and 'grf_z' in td:
        l7, = ax[1,1].plot(ts, log['grf_z'][mask], label="GRF sim")
        ax[1,1].plot(t_real, td['grf_z'], '--', color=l7.get_color(), label="GRF real")
        ax[1,1].set_title("GRF_z [N]"); ax[1,1].legend(fontsize=8); ax[1,1].grid(alpha=0.3)
    ax[1,0].plot(ts, log['pen_mm'][mask]); ax[1,0].set_title("Foot penetration [mm]"); ax[1,0].grid(alpha=0.3)
    for a in ax.flat:
        a.set_xlabel("t [s]")
    fig.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    return True


if __name__ == "__main__":
    apply_pure_cad()
    ok = plot_sub("jump_0424", "60_0.75_60_2",
                  str(TEMPLATES.parent / "phase1/_plot_smoke.png"))
    print("smoke plot:", ok)
