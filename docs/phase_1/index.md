# Phase 1 — 로봇 동역학 (mass + inertia + CoM per part)

**Status**: 진행 중 (CMA-ES running)
**Phase 0 baseline**: 41,271.18 → **Best so far: 24,060.78 (-42%)** at gen 2

## 목표

Pure CAD 상태에서 확인된 잔차 (특히 sit2stand_gnd 39mm 침투, jump h_sim 0.61m << h_real 0.83m)를 해결하기 위해 **부품별 mass/inertia/CoM 오차**를 동시 fit한다.

## 15D search space

| # | Param | Range | X0 (Pure CAD) |
|---|---|---|---|
| 0 | `M_base_scale` | [0.75, 1.30] | 1.0 |
| 1 | `M_thigh_scale` | [0.75, 1.30] | 1.0 |
| 2 | `M_calf_scale` | [0.75, 1.30] | 1.0 |
| 3 | `M_p_scale` (paddle hip) | [0.5, 1.5] | 1.0 |
| 4 | `M_c_scale` (paddle knee) | [0.5, 1.5] | 1.0 |
| 5 | `M_foot_extra` (kg) | [0.0, 0.30] | 0.0 |
| 6 | `I_thigh_scale` | [0.5, 1.5] | 1.0 |
| 7 | `I_calf_scale` | [0.5, 1.5] | 1.0 |
| 8 | `I_p_scale` | [0.5, 1.5] | 1.0 |
| 9 | `I_c_scale` | [0.5, 1.5] | 1.0 |
| 10 | `com_shift_thigh_z` (m) | [-0.020, 0.020] | 0.0 |
| 11 | `com_shift_thigh_x` (m) | [-0.020, 0.020] | 0.0 |
| 12 | `com_shift_calf_z` (m) | [-0.020, 0.020] | 0.0 |
| 13 | `com_shift_calf_x` (m) | [-0.020, 0.020] | 0.0 |
| 14 | `arm_knee` | [0.001, 0.020] | 0.00490 |

## Optimizer

**CMA-ES** (cma 4.4.4). Population 12, maxfevals 400, sigma0 = 0.15 (normalized). Bounds via [0,1] normalization. Seed=42.

Rationale (see [external sources](external_sources.md)):
- Non-differentiable score (MuJoCo forward sim, contact events)
- Multi-modal (different jump PDs may have local minima)
- Coupled (mass × inertia)
- CMA-ES robust to noise + no gradient required

## Progress (auto-updated)

*(phase1_progress.json에서 실시간)*

| Gen | Best score | Pop mean | Elapsed |
|---|---|---|---|
| 1 | 25,283 | 41,685 | 66s |
| 2 | 24,060 | 31,385 | 132s |

## Key insight — early convergence direction

At gen 2 best_x:
- **M_thigh_scale = 1.226** (CAD +22.6% mass on thigh)
- **I_thigh_scale = 1.168** (CAD +16.8% inertia on thigh)
- **M_p_scale = 1.195** (paddle_hip heavier)
- **M_c_scale = 0.760** (paddle_knee lighter)
- **M_foot_extra = 0.094 kg** (94g extra on foot)

This aligns with the [Bridging Sim-to-Real paper](external_sources.md) which reported thigh inertia noticeably higher than CAD while shank consistent. Our CMA-ES independently confirmed the same signature.

## Drop-test (upon CMA-ES completion)

Runner: `code/goal19/phase1/run_droptest.py`. For each of 15 axes, pin to X0 (Pure CAD value), evaluate 31-exp score. Axis **DROPS** if `|Δscore| / best < 3%`.

## Files

- Runner: `code/goal19/phase1/run_phase1_cmaes.py`
- Live progress: `code/goal19/phase1/phase1_progress.json`
- Final result: `code/goal19/phase1/phase1_best.json` (produced on completion)
- Drop-test: `code/goal19/phase1/run_droptest.py`
- External sources: [external_sources.md](external_sources.md)
