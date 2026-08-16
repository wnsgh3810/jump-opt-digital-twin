"""GOAL19 Phase 11h+ — CLEAN series-elastic (SEA) test.

Fixes the 2-body base-jump bug: keep the LEG as the ORIGINAL rigid model (jumps
fine), and integrate the MOTOR as an EXTERNAL 1-DOF coupled to the leg by a spring.
- measured motor torque -> motor;  leg receives the spring torque.
- compare motor angle qm to q2_real (motor-side measurement).
- leg (calf) determines GRF/height.

At high k -> recovers rigid (motor~leg, h~0.68, dq2~18). At lower k -> motor
decouples and dq2 spikes toward real 27. Goal: a k that jumps AND spikes AND tracks.
"""
import sys
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
from apply_final_and_regen import apply_final
import sub_sim_iter6v2 as S


def run_sea(td, k_sea, c_sea, I_m, arm_hip, arm_knee, want_log=False):
    S.STIFF_KNEE = 0.0  # SEA replaces the parallel flex
    model = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(arm_hip, arm_knee))
    data = mujoco.MjData(model)
    sq1, sq2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    data.qpos[:] = [S.BASE_Z_INIT, sq1, sq2]; data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    dt = model.opt.timestep
    tr = td["t"]; tkin = -np.asarray(td["tau2_real"]); thin = -np.asarray(td["tau1_real"])
    Tm = float(tr[-1]); N = int((S.T_SETTLE + Tm + S.T_AFTER) / dt) + 1
    qm, dqm = sq2, 0.0
    q2m_log = []; q2leg_log = []; dq2m_log = []; base_log = []; t_log = []
    for i in range(N):
        tc = i * dt
        qleg = data.qpos[2]; dqleg = data.qvel[2]
        if tc < S.T_SETTLE:
            tau_h = S.SETTLE_KP * (sq1 - data.qpos[1]) + S.SETTLE_KD * (0 - data.qvel[1])
            tau_leg = S.SETTLE_KP * (sq2 - qleg) + S.SETTLE_KD * (0 - dqleg)
            qm = qleg; dqm = 0.0
        else:
            if tc < S.T_SETTLE + Tm:
                tmv = tc - S.T_SETTLE
                tau_motor = float(np.interp(tmv, tr, tkin))
                tau_h = float(np.interp(tmv, tr, thin))
            else:
                tau_motor = 0.0; tau_h = 0.0
            e = qm - qleg; de = dqm - dqleg
            tau_spring = k_sea * e + c_sea * de
            tau_leg = tau_spring                 # leg receives spring torque
            ddqm = (tau_motor - tau_spring) / I_m  # external motor
            dqm += ddqm * dt; qm += dqm * dt
        data.ctrl[:] = [tau_h, tau_leg]
        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None
        tj = tc - S.T_SETTLE
        if tj >= 0:
            t_log.append(tj); q2m_log.append(-qm); q2leg_log.append(-data.qpos[2])
            dq2m_log.append(-dqm); base_log.append(data.qpos[0])
        if abs(data.qpos[0]) > 5.0:
            return None
    out = dict(h_sim=float(np.max(base_log)), dq2m_pk=float(np.max(np.abs(dq2m_log))))
    if want_log:
        out.update(t=np.array(t_log), q2m=np.array(q2m_log), q2leg=np.array(q2leg_log),
                   dq2m=np.array(dq2m_log))
    return out


def main():
    ap = apply_final()
    td = S.load_jump_0424("90_0.75_90_2")
    I_m = ap["arm_knee"]  # motor reflected inertia
    real_dq2 = float(np.max(np.abs(td["dq2"]))); real_h = float(td["h_real"])
    print(f"real: dq2pk={real_dq2:.1f} h={real_h:.2f} | rigid sim ~ dq2 18, h 0.68")
    print(f"{'k_sea':>8}{'c':>6}{'h_sim':>8}{'motor_dq2pk':>13}")
    for k in [8, 15, 30, 60, 120, 300, 1000]:
        r = run_sea(td, k, 0.05, I_m, ap["arm_hip"], ap["arm_knee"])
        if r:
            print(f"{k:>8}{0.05:>6}{r['h_sim']:>8.3f}{r['dq2m_pk']:>13.1f}")
        else:
            print(f"{k:>8}{0.05:>6}   FAIL")


if __name__ == "__main__":
    main()
