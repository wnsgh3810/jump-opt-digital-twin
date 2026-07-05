# -*- coding: utf-8 -*-
"""G20 — export NLP-optimal trajectories as robot-ready deployment files.

Three consistent optima (torque budget 70/85/100% of 18 Nm, each RE-SOLVED so
q*,dq*,tau* stay dynamically consistent) -> CSV per scale:
    t[s], q1_des[rad], dq1_des[rad/s], tau1_ff[Nm], q2_des[rad], dq2_des[rad/s], tau2_ff[Nm]
Convention = robot canonical (same as encoder logs / MIT-mode commands).
Each CSV gets a twin-replay expected-height check; README.md documents usage.
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
DEP = REPO / "code/goal19/nlp_demo/deploy"
DEP.mkdir(exist_ok=True)


def twin_h(npz):
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    m = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))
    d = mujoco.MjData(m)
    t = npz["t"]; q1c = npz["q1"]; q2c = npz["q2"]; tau1 = npz["tau1"]; tau2 = npz["tau2"]; z = npz["z"]
    q1m0 = -q1c[0] - np.pi / 2; q2m0 = -q2c[0]
    d.qpos[:] = [float(z[0]), q1m0, q2m0, -q2m0, q2m0]; d.qvel[:] = 0
    mujoco.mj_forward(m, d)
    dt = m.opt.timestep; T_SET = 0.4
    N = int((T_SET + t[-1] + 1.0) / dt) + 1
    bz = np.zeros(N)
    for k in range(N):
        tc = k * dt
        if tc < T_SET:
            th = S.SETTLE_KP * (q1m0 - d.qpos[1]) + S.SETTLE_KD * (-d.qvel[1])
            tk = S.SETTLE_KP * (q2m0 - d.qpos[2]) + S.SETTLE_KD * (-d.qvel[2])
        elif tc < T_SET + t[-1]:
            tm = tc - T_SET
            th = float(np.interp(tm, t, -tau1)); tk = float(np.interp(tm, t, -tau2))
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        mujoco.mj_step(m, d)
        bz[k] = d.qpos[0]
    return float(bz.max())


def main():
    meta = []
    for s, tag in ((0.70, "s0.70"), (0.85, "s0.85"), (1.00, "s1.00")):
        f = REPO / f"code/goal19/nlp_demo/traj_deploy_s{s:.2f}.npz"
        npz = np.load(f)
        t = npz["t"]; z = npz["z"]; dz = npz["dz"]
        h_pred = float(z[-1] + max(dz[-1], 0) ** 2 / (2 * 9.81))
        h_tw = twin_h(npz)
        arr = np.column_stack([t, npz["q1"], npz["dq1"], npz["tau1"],
                               npz["q2"], npz["dq2"], npz["tau2"]])
        out = DEP / f"jump_optimal_{tag}_taulim{18*s:.1f}Nm.csv"
        np.savetxt(out, arr, delimiter=",", fmt="%.6f",
                   header="t_s,q1_des_rad,dq1_des_rad_s,tau1_ff_Nm,q2_des_rad,dq2_des_rad_s,tau2_ff_Nm",
                   comments="")
        pk1 = float(np.abs(npz["tau1"]).max()); pk2 = float(np.abs(npz["tau2"]).max())
        meta.append(dict(scale=s, csv=out.name, tau_lim=18 * s, h_pred=h_pred, h_twin=h_tw,
                         peak_tau_hip=pk1, peak_tau_knee=pk2, T=float(t[-1]), n=len(t)))
        print(f"{tag}: tau_lim={18*s:.1f}  h_pred={h_pred:.3f}  h_twin={h_tw:.3f}  "
              f"peak tau=({pk1:.1f},{pk2:.1f})  T={t[-1]:.3f}s  -> {out.name}")
    readme = DEP / "README.md"
    readme.write_text(f"""# G20 NLP-optimal jump — deployment package (2026-07-05)

## Files
{chr(10).join(f"- `{m['csv']}` — tau budget {m['tau_lim']:.1f} Nm, NLP pred {m['h_pred']:.3f} m, twin check {m['h_twin']:.3f} m, stance {m['T']*1000:.0f} ms" for m in meta)}

## Column convention (robot canonical — same as encoder logs)
`t_s, q1_des_rad, dq1_des_rad_s, tau1_ff_Nm, q2_des_rad, dq2_des_rad_s, tau2_ff_Nm`
- q1 = hip, q2 = knee(crank encoder). Interpolate to controller rate (t is the NLP grid, non-uniform density possible).
- AK80-9 MIT mode per joint: `tau_cmd = kp*(q_des - q) + kd*(dq_des - dq) + tau_ff`.

## Recommended gains (MIT mode)
Start from the best executed trial's gains: **kp=90, kd=0.75 (hip) / kp=90, kd=2.0 (knee)**
(folder 90_0.75_90_2 — highest real jump 0.980 m). High-gain tracking + tau_ff carries the profile.

## Protocol (progressive)
1. Run `s0.70` (12.6 Nm budget) — verify hip tracking in 8–14 rad/s region (NLP uses it harder than any past trial).
2. `s0.85`, then `s1.00`. Expected best-case apex (camera scale): ~1.12 m vs current best 0.980 m.
3. After each: compare measured q/dq/tau vs the CSV — deviations localize model error (feed back into twin).

## Safety
- Torque ff is within AK80-9 V2 peak (18 Nm) at every sample; knee rides the limit (bang-bang) — expect saturation flags at 100%.
- Trajectories end at takeoff; after `t_end` command zero torque + flight posture hold (PD on landing pose).
- Twin validity: dynamic phase only (quasi-static holds are outside the model envelope — stiction).

Twin: `code/goal19/goal20_final_model.json` (round-1 canonical). Source: `traj_deploy_*.npz`, solver g20_vertjump_fric.py (k_c=1.3e5=k_eq, identified friction).
""", encoding="utf-8")
    json.dump(meta, open(DEP / "deploy_meta.json", "w"), indent=1)
    print("README + meta ->", DEP)


if __name__ == "__main__":
    main()
