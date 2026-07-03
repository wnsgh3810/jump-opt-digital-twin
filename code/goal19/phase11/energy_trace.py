"""GOAL19 Phase 11i — energy accounting of the honest jump sim.

Question: torque work (~27J) is enough, but honest sim only jumps 0.56 (converts
~12J). Where do the other ~15J go? Trace channels over a jump:
  W_pos / W_neg : actuator positive / negative (braking) work
  D_fric        : joint friction dissipation  (FV*dq^2 + FC*|dq|)
  dE_mech       : change in mechanical energy (KE+PE)
  D_resid       : W_net - dE_mech - D_fric  = contact + numerical loss
Reports the breakdown at takeoff (GRF->0) and apex.
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


def trace(td, use_flex, use_fric):
    ap = apply_final()
    S.STIFF_KNEE = S.STIFF_KNEE if use_flex else 0.0
    fvh, fvk, fch, fck = (S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE) if use_fric else (0, 0, 0, 0)
    S.FV_HIP, S.FV_KNEE, S.FC_HIP, S.FC_KNEE = fvh, fvk, fch, fck
    model = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
    model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    data = mujoco.MjData(model)
    sq1, sq2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    data.qpos[:] = [S.BASE_Z_INIT, sq1, sq2]; data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    dt = model.opt.timestep
    tr = td["t"]; tkin = -np.asarray(td["tau2_real"]); thin = -np.asarray(td["tau1_real"])
    Tm = float(tr[-1]); N = int((S.T_SETTLE + Tm + S.T_AFTER) / dt) + 1
    foot_gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    Wpos = Wneg = Dfric = 0.0
    E0 = None; base0 = None
    takeoff = None; apex_h = S.BASE_Z_INIT
    for i in range(N):
        tc = i * dt
        if tc < S.T_SETTLE:
            th = S.SETTLE_KP * (sq1 - data.qpos[1]) + S.SETTLE_KD * (0 - data.qvel[1])
            tk = S.SETTLE_KP * (sq2 - data.qpos[2]) + S.SETTLE_KD * (0 - data.qvel[2])
            data.ctrl[:] = [th, tk]; mujoco.mj_step(model, data)
            continue
        if E0 is None:
            E0 = data.energy[0] + data.energy[1]; base0 = data.qpos[0]
        if tc < S.T_SETTLE + Tm:
            tm = tc - S.T_SETTLE
            th = float(np.interp(tm, tr, thin)); tk = float(np.interp(tm, tr, tkin))
        else:
            th = tk = 0.0
        data.ctrl[:] = [th, tk]
        dqh, dqk = data.qvel[1], data.qvel[2]
        mujoco.mj_step(model, data)
        # actuator power (use realized actuator force)
        P = data.qfrc_actuator[1] * dqh + data.qfrc_actuator[2] * dqk
        Wpos += max(P, 0) * dt; Wneg += min(P, 0) * dt
        Dfric += (fvh * dqh**2 + fvk * dqk**2 + fch * abs(dqh) + fck * abs(dqk)) * dt
        # contact / takeoff
        gz = 0.0
        for c in range(data.ncon):
            cf = np.zeros(6); mujoco.mj_contactForce(model, data, c, cf)
            gz += (data.contact[c].frame.reshape(3, 3).T @ cf[:3])[2]
        if gz > 5.0:
            takeoff = tc - S.T_SETTLE
        apex_h = max(apex_h, data.qpos[0])
    Ef = data.energy[0] + data.energy[1]
    dE = Ef - E0
    Wnet = Wpos + Wneg
    Dresid = Wnet - dE - Dfric
    return dict(Wpos=Wpos, Wneg=Wneg, Wnet=Wnet, Dfric=Dfric, dEmech=dE,
                Dresid=Dresid, apex=apex_h, takeoff=takeoff, h_real=float(td["h_real"]))


def main():
    td = S.load_jump_0424("90_0.75_90_2")
    print("jump_0424/90_0.75_90_2  (real h=%.2f, ~22J to jump)\n" % float(td["h_real"]))
    for lbl, fx, fr in [("honest (flex OFF, fric OFF)", False, False),
                        ("+ friction (flex OFF)", False, True),
                        ("+ flex (final model)", True, True)]:
        r = trace(td, fx, fr)
        print(f"[{lbl}]  apex={r['apex']:.3f} takeoff@{r['takeoff']}")
        print(f"   W_pos={r['Wpos']:.1f}J  W_neg={r['Wneg']:.1f}J  -> W_net={r['Wnet']:.1f}J")
        print(f"   -> dE_mech={r['dEmech']:.1f}J | D_fric={r['Dfric']:.1f}J | D_contact+num={r['Dresid']:.1f}J\n")


if __name__ == "__main__":
    main()
