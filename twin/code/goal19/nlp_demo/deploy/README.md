# G20 NLP-optimal jump — deployment package (2026-07-05)

## Files
- `jump_optimal_s0.70_taulim12.6Nm.csv` — tau budget 12.6 Nm, NLP pred 0.824 m, twin check 0.836 m, stance 248 ms
- `jump_optimal_s0.85_taulim15.3Nm.csv` — tau budget 15.3 Nm, NLP pred 0.966 m, twin check 0.957 m, stance 209 ms
- `jump_optimal_s1.00_taulim18.0Nm.csv` — tau budget 18.0 Nm, NLP pred 1.112 m, twin check 1.063 m, stance 184 ms

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

## Pre-flight check (CRITICAL)
- **Verify dq_des is actually transmitted to the motors** before the first run. On 03.19/03.24/04.21 a
  code bug silently sent dq_des=0 while logging the planned values — if that happens with these CSVs,
  the kd term becomes pure braking (-kd*dq) during extension and the jump will underperform badly.
  (User confirmed the bug was fixed from 04.24 onward — this is a quick sanity confirmation, not an expected failure.)
  Quick check: command a slow sine on dq_des with kp=0, kd>0 and confirm the joint follows.
- **Verify tau_ff is actually transmitted** (user confirmed 07-06: t_ff has NEVER been used on this
  hardware — all past experiments were pure PD; the logged desiredTorque column was reference-only).
  Quick check: kp=kd=0, command a small constant t_ff (e.g. 1 Nm) and confirm measured torque responds.

## Safety
- Torque ff is within AK80-9 V2 peak (18 Nm) at every sample; knee rides the limit (bang-bang) — expect saturation flags at 100%.
- Trajectories end at takeoff; after `t_end` command zero torque + flight posture hold (PD on landing pose).
- Twin validity: dynamic phase only (quasi-static holds are outside the model envelope — stiction).

Twin: `code/goal19/goal20_final_model.json` (round-1 canonical). Source: `traj_deploy_*.npz`, solver g20_vertjump_fric.py (k_c=1.3e5=k_eq, identified friction).
