---
name: next-goal5-mission
description: GOAL5 — 26.06.02 점프 데이터로 MuJoCo digital twin 검증. Reference 적용해서 토크/속도/GRF 일치까지 환경 파라미터 fitting
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL5: MuJoCo Digital Twin Validation

**Mission**: MuJoCo 환경 설정을 실제 robot과 매칭시켜 digital twin 완성.
**Full prompt**: `C:\Users\junho\CVT\jump_opt\GOAL5_PROMPT.md`

## Data Sources
- **Reference**: `CVT\jump_opt\no_cvt_alphaonly\jump_no_cvt_alphaonly_results.xlsx` (q_ref, dq_ref)
- **실측**: `Research\4-Bar Link CVT\Data\26.06.02\position\` 6 trial (60_0.75_60_2, 60_1.5_60_1.5, 90_0.75_90_2, 120_2_120_2, 150_2.2_250_3, 150_2.2_500_5)
- **Torque correction**: paper a_hat (pure paper, sgn only) → `ak80_9_torque_calibration.md`

## Validation Metric (이 순서)
1. **τ** (paper-corrected) — 가장 중요
2. **dq**
3. **GRF_z**
4. q tracking error

**금지**: 점프 높이 매칭 (wrong metric)

## Approach
- Phase 0: 데이터 로드 + paper a_hat torque correction
- Phase 1: mujoco_menagerie Go1 환경 시작점 → single-leg adapt
- Phase 2: Tunable env params (floor solref/solimp, foot, joint armature/damping/frictionloss, mass, inertia)
- Phase 3: Reference apply + multi-trial measurement
- Phase 4: BO/grid search for env param fitting (6 trial combined)
- Phase 5: Validation + Notion 보고서

**Why**: 같은 robot에서 자세에 따라 GRF 32N (stable) vs 2707N (폭주) — 자세 차이 아니라 sim 환경이 실제와 안 맞아서. 환경 파라미터 fitting으로 fix.

**Related**: [[digital_twin_priority]] [[position_data_26_06_02_model]] [[ak80_9_torque_calibration]] [[feedback_pure_paper_formula]] [[goal4_phase1_state]]
