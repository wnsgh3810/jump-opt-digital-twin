# -*- coding: utf-8 -*-
"""G20 — deployment pre-validation: closed-loop MIT-PD replay of the deploy CSVs.

Exactly the real deployment scenario: per joint
    tau_cmd = kp*(q_des - q) + kd*(dq_des - dq) + tau_ff,  clipped to +/-18 Nm,
with the README-recommended gains (hip kp90/kd0.75, knee kp90/kd2.0), replayed in
the four-bar twin. NOT fitting — a go/no-go check that PD+ff preserves the jump.
Sensitivity: GOAL6 suggested firmware may scale commanded kp by alpha_kp~0.19
(uncertain) — run both nominal and scaled gains.
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
import mshoot_fourbar as FB

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
KP_H, KD_H, KP_K, KD_K = 90.0, 0.75, 90.0, 2.0
TAU_CLIP = 18.0


def run_cl(npz, akp=1.0):
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    m = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))
    d = mujoco.MjData(m)
    t = npz["t"]; q1c = npz["q1"]; q2c = npz["q2"]; dq1c = npz["dq1"]; dq2c = npz["dq2"]
    tau1 = npz["tau1"]; tau2 = npz["tau2"]; z = npz["z"]
    q1m0 = -q1c[0] - np.pi / 2; q2m0 = -q2c[0]
    d.qpos[:] = [float(z[0]), q1m0, q2m0, -q2m0, q2m0]; d.qvel[:] = 0
    mujoco.mj_forward(m, d)
    dt = m.opt.timestep; T_SET = 0.4
    N = int((T_SET + t[-1] + 1.0) / dt) + 1
    bz = np.zeros(N); e1 = []; e2 = []; tau_use1 = []; tau_use2 = []
    for k in range(N):
        tc = k * dt
        if tc < T_SET:
            th = S.SETTLE_KP * (q1m0 - d.qpos[1]) + S.SETTLE_KD * (-d.qvel[1])
            tk = S.SETTLE_KP * (q2m0 - d.qpos[2]) + S.SETTLE_KD * (-d.qvel[2])
        elif tc < T_SET + t[-1]:
            tm = tc - T_SET
            # current state in canonical convention
            q1_now = -d.qpos[1] - np.pi / 2; dq1_now = -d.qvel[1]
            q2_now = -d.qpos[2]; dq2_now = -d.qvel[2]
            q1d = np.interp(tm, t, q1c); dq1d = np.interp(tm, t, dq1c)
            q2d = np.interp(tm, t, q2c); dq2d = np.interp(tm, t, dq2c)
            t1 = akp * KP_H * (q1d - q1_now) + KD_H * (dq1d - dq1_now) + np.interp(tm, t, tau1)
            t2 = akp * KP_K * (q2d - q2_now) + KD_K * (dq2d - dq2_now) + np.interp(tm, t, tau2)
            t1 = float(np.clip(t1, -TAU_CLIP, TAU_CLIP)); t2 = float(np.clip(t2, -TAU_CLIP, TAU_CLIP))
            e1.append(q1d - q1_now); e2.append(q2d - q2_now)
            tau_use1.append(abs(t1)); tau_use2.append(abs(t2))
            th, tk = -t1, -t2
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        mujoco.mj_step(m, d)
        bz[k] = d.qpos[0]
    return dict(h=float(bz.max()),
                rmse_q1_deg=float(np.degrees(np.sqrt(np.mean(np.array(e1) ** 2)))),
                rmse_q2_deg=float(np.degrees(np.sqrt(np.mean(np.array(e2) ** 2)))),
                peak_tau1=float(max(tau_use1)), peak_tau2=float(max(tau_use2)))


def main():
    out = {}
    for s, ol_h in ((0.70, 0.836), (0.85, 0.957), (1.00, 1.063)):
        npz = np.load(REPO / f"code/goal19/nlp_demo/traj_deploy_s{s:.2f}.npz")
        r_nom = run_cl(npz, akp=1.0)
        r_a19 = run_cl(npz, akp=0.19)
        out[f"s{s:.2f}"] = dict(openloop_h=ol_h, nominal=r_nom, alpha_kp019=r_a19)
        print(f"s{s:.2f}: open-loop h={ol_h:.3f}")
        print(f"   CL nominal   : h={r_nom['h']:.3f}  track q1={r_nom['rmse_q1_deg']:.2f}deg "
              f"q2={r_nom['rmse_q2_deg']:.2f}deg  peak tau=({r_nom['peak_tau1']:.1f},{r_nom['peak_tau2']:.1f})")
        print(f"   CL akp=0.19  : h={r_a19['h']:.3f}  track q1={r_a19['rmse_q1_deg']:.2f}deg "
              f"q2={r_a19['rmse_q2_deg']:.2f}deg  peak tau=({r_a19['peak_tau1']:.1f},{r_a19['peak_tau2']:.1f})")
    json.dump(out, open(REPO / "code/goal19/nlp_demo/deploy_cl_check.json", "w"), indent=1)
    print("saved deploy_cl_check.json")


if __name__ == "__main__":
    main()
