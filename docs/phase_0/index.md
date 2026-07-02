# Phase 0 — Pure CAD Baseline

**Status**: Complete (2026-07-02)
**Score total**: **41,271.18** (31/31 exp, 6.2s)
**Purpose**: Establish unified baseline against which every subsequent axis is measured.

## Setup

**Base params (Pure CAD, no fudge)**:

| Param | Value | Note |
|---|---|---|
| `motor_tm` | 0.0 s | LPF forbidden (사용자 directive) |
| `m_base_scale` | 1.0 | CAD |
| `m_thigh_scale` | 1.0 | CAD |
| `m_calf_scale` | 1.0 | CAD |
| `m_p_scale` (paddle_hip) | 1.0 | CAD |
| `m_c_scale` (paddle_knee) | 1.0 | CAD |
| `m_foot_extra` | 0.0 kg | Pure CAD (iter5 had 0.60) |
| `arm_hip` | 0.0 | CAD |
| `arm_knee` | 0.00490 | CAD-derived |
| `solref_tc` | 0.006320 s | default |
| `imp0` | 0.14301 | default |
| `fv_hip, fv_knee` | 0.001 | epsilon (near-zero) |
| `fc_hip, fc_knee` | 0.001 | epsilon |
| Integrator | RK4 | canonical |
| Mode | A (`ctrl = -tau_real`) | |

**Weights**: Wq=100, Wdq=50, Wt=0, Wh_jump=100, Wgrf=0.1, Wpen=50

## Per-experiment breakdown

| Dataset | Sub | Type | Score | rmse_q1 | rmse_q2 | pen(mm) | h_sim/h_real |
|---|---|---|---:|---:|---:|---:|---|
| sit2stand_air_0319 | ROOT | S2S | 2571.02 | 0.880 | 17.775 | 0.00 | — |
| sit2stand_gnd_0319 | ROOT | S2S | 10262.53 | 6.476 | 46.301 | 39.11 | — |
| sit2stand_0324 | P10_D0 | S2S | 1794.54 | 0.727 | 12.203 | 0.00 | — |
| sit2stand_0324 | P10_D1 | S2S | 1968.38 | 0.796 | 11.792 | 0.00 | — |
| sit2stand_0324 | P20_D1 | S2S | 1484.98 | 0.785 | 7.856 | 0.00 | — |
| sit2stand_0324 | P30_D1 | S2S | 810.89 | 0.756 | 3.337 | 0.00 | — |
| sit2stand_0324 | P60_D1.5_P60_D2 | S2S | 1895.87 | 0.792 | 12.045 | 0.00 | — |
| jump_position_0421 | P60_D0.75_P60_D2 | JUMP | 1049.19 | 0.195 | 0.572 | 0.37 | 1.043 / 0.860 |
| jump_position_0421 | P70_D0.75_P70_D2 | JUMP | 499.02 | 0.085 | 0.243 | 0.36 | 0.933 / 0.850 |
| jump_position_0421 | P80_D0.75_P80_D2 | JUMP | 1416.09 | 0.272 | 0.847 | 0.38 | 1.036 / 0.890 |
| jump_position_0421 | P90_D0.75_P90_D2 | JUMP | 705.76 | 0.118 | 0.357 | 0.39 | 0.974 / 0.860 |
| jump_position_0421 | P100_D0.75_P100_D2 | JUMP | 806.77 | 0.138 | 0.395 | 0.37 | 0.970 / 0.850 |
| jump_position_0421 | P200_D1.5_P200_D4 | JUMP | 386.50 | 0.055 | 0.129 | 3.70 | 0.704 / 0.790 |
| jump_torque_0422 | P40_D0.7 | JUMP | 1852.58 | 0.370 | 1.417 | 0.53 | 0.746 / 0.740 |
| jump_torque_0422 | P70_D2 | JUMP | 1402.06 | 0.211 | 0.682 | 7.27 | 0.610 / 0.715 |
| jump_torque_0422 | P100_D3 | JUMP | 2927.20 | 0.302 | 1.136 | 28.97 | 0.628 / 0.715 |
| jump_0424 | 60_0.75_60_2 | JUMP | 364.55 | 0.206 | 0.336 | 0.39 | 0.655 / 0.900 |
| jump_0424 | 60_1.5_60_1.5 | JUMP | 635.31 | 0.210 | 0.436 | 5.24 | 0.584 / 0.910 |
| jump_0424 | 90_0.75_90_2 | JUMP | 338.85 | 0.157 | 0.245 | 0.40 | 0.703 / 0.894 |
| jump_0424 | 120_2_120_2 | JUMP | 823.60 | 0.242 | 0.452 | 7.89 | 0.540 / 0.840 |
| jump_0424 | 120_2.2_150_2.5 | JUMP | 822.86 | 0.237 | 0.512 | 6.75 | 0.469 / 0.810 |
| jump_0424 | 120_2.2_200_2.8 | JUMP | 752.97 | 0.214 | 0.425 | 7.06 | 0.530 / 0.795 |
| jump_0424 | 150_2.2_250_3 | JUMP | 740.71 | 0.199 | 0.381 | 7.59 | 0.538 / 0.770 |
| jump_0424 | 150_2.2_350_3.5 | JUMP | 731.48 | 0.205 | 0.406 | 7.00 | 0.516 / 0.770 |
| jump_0424 | 150_2.2_500_4 | JUMP | 764.60 | 0.189 | 0.419 | 7.17 | 0.517 / 0.775 |
| jump_0602 | 60_0.75_60_2 | JUMP | 339.47 | 0.152 | 0.325 | 1.69 | 0.615 / 0.940 |
| jump_0602 | 60_1.5_60_1.5 | JUMP | 691.40 | 0.097 | 0.380 | 6.39 | 0.475 / 0.960 |
| jump_0602 | 90_0.75_90_2 | JUMP | 413.66 | 0.179 | 0.368 | 0.25 | 0.630 / 0.980 |
| jump_0602 | 120_2_120_2 | JUMP | 698.58 | 0.148 | 0.403 | 5.99 | 0.580 / 0.940 |
| jump_0602 | 150_2.2_250_3 | JUMP | 388.26 | 0.129 | 0.313 | 0.53 | 0.680 / 0.900 |
| jump_0602 | 150_2.2_500_5 | JUMP | 931.49 | 0.145 | 0.388 | 11.37 | 0.611 / 0.800 |

**Aggregates**:
- Total: **41,271.18**
- Sit2stand mean: 2,969.74 (7 subs)
- Jump mean: 837.63 (24 subs)
- Worst offender: `sit2stand_gnd_0319/ROOT` (10,262 = 25% of total; 39mm foot pen)
- Best jump: `jump_0424/90_0.75_90_2` (338.85)

## Immediate observations (Phase 1 direction)

1. **sit2stand_gnd_0319 outlier** (10,262). 39mm foot penetration + rmse_q2=46 rad. Contact/base fixed model issue. Priority axis.
2. **Jump heights systematically LOW** (h_sim mean 0.61m vs h_real mean 0.83m). Pure CAD lacks mass/inertia calibration - expected, targeted in Phase 1.
3. **High-PD subs (150_2.2_500, 120_2_120_2, P100_D3) penetration 7-29mm**. Contact / mass / inertia coupling.
4. **jump_position_0421 P70/P90 excellent** (rmse_q1 < 0.15). Position PD tracks well with Pure CAD.

## Next: Phase 1 — 로봇 동역학 (15D+)

Per-part `M_scale`, `I_scale`, `com_shift_x`, `com_shift_z` for {base, thigh, calf, foot, paddle_hip, paddle_knee}. CMA-ES on 15-25D. Target: drive worst-offender scores down while maintaining jump subs.

## Reproducibility

- Runner: `code/goal19/phase0/run_pure_base_31exp.py`
- Loader: `code/goal19/data_loaders/load_31exp.py` (31/31 canonical .npz located)
- Sim engine: `code/goal19/templates/sub_sim_iter6v2.py` (monkey-patched to Pure CAD)
- Results JSON: `code/goal19/phase0/pure_base_31exp_result.json`
- Data source: `Desktop/jump_opt/goal18_v4/Iter6/**`, `goal16/cross_validation_*/`, `goal18/iter0R/`, `goal12/xval_v2/`
