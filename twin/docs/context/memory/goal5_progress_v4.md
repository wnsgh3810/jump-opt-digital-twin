---
name: goal5-progress-v4
description: GOAL5 GRF spike 해결 진전 - V1 2723N → V4 95N (실측 108-141N 일치). τ/q 정체 (PD sat 한계)
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL5 Progress — V1 to V4 (2026-06-06)

## Notion 페이지
- **Parent**: https://app.notion.com/p/GOAL5-MuJoCo-Digital-Twin-Validation-26-06-02-377ab81d2550813a8104cba12f294f2a
- **Phase 0**: 데이터 로드 + paper a_hat
- **Phase 1/V1**: Go1 baseline
- **V3**: Grid sweep 225 configs (4 dim)
- **V4**: Optuna BO TPE (10 dim, 1000 trials)

## 핵심 결과 — GRF 매칭 성공

| | GRF peak | GRF RMSE | Peak base | τ RMSE | dq RMSE | q RMSE |
|---|---|---|---|---|---|---|
| V1 baseline | 2723 N | 422 | 2.3 m | 24.36 | 17.50 | 154.7° |
| V3 grid 4d | 150 N | 46.3 | 0.42 m | 24.37 | 14.10 | 78.3° |
| V4 BO 10d | 93-100 N | 27.4 | 0.22 m | 24.35 | 12.92 | 73.9° |
| **실측** | 108-141 N | - | ~ - | - | - | - |

★ **GRF 15배 감소**. 실측과 거의 일치.

## V4 best parameters
- fl_h=0.081, fl_k=5.749 (frictionloss)
- sr_tc=0.192, si_d0=0.041 (contact soft)
- armature_h/k=0.005 (rotor inertia 작음)
- damping_h=3.81, damping_k=5.00 (강한 damping)
- base_mass=3.44 kg
- foot_size=0.019 m

## 정체 — τ/q
- τ RMSE 24 (V1 → V4 변화 없음): PD ±18 sat이 hard limit
- q RMSE V1 155° → V4 74°: 진전 있지만 큰 차이
- 다음 V5에서 분석 필요: 실 robot의 q tracking 정확도 확인 (desiredAngle vs currentAngle RMSE)
  - 실 robot도 비슷한 tracking 차이면 우리 sim 충분
  - 아니면 robot model의 mass/CoM/inertia 추가 fit

## 파일 위치
- 디렉토리: `CVT/jump_opt/goal5/`
- MJCF: urdf/leg_g5v1.xml, v2, v3, v4
- 코드: phase0_*, phase1_*, phase3_*
- 결과: phase1_v1_results.npz, phase3_v2/v3/v4_results.npz, phase3_v4_bo_study.pkl

## V5-V9 추가 진행 (2026-06-06)

| | GRF peak | GRF RMSE | q° | Penetration | 평가 |
|---|---|---|---|---|---|
| V5 | 107N | 35.5 | 66° | -11mm ✗ | GRF best but penetration |
| V6 | - | - | 71° | -1.5mm OK | penalty 추가 |
| V7 | 3400N | - | 117° | -1.5mm | hard contact spike |
| V8 | 850N | 206 | 89° | -55mm ✗ | V5 + foot 0.023 worse |
| **V9** | 1927N | 254 | 71° | **-0.8mm ★** | hard contact + BO joints only |

## 핵심 trade-off
- **Soft contact** (V5): GRF 매칭 best but visual penetration
- **Hard contact** (V9): no penetration but GRF spike (V20 자세에서 robot 떨어짐)

## 실 robot vs 우리 sim q tracking (★ 결정적 발견)
실 robot은 ref 정확 따라감 (hip 2-8°, knee 5-20°). 우리 sim 50-100°.
→ Robot model 본질 차이 (mass/inertia/friction 추가 fit 필요)

## 다음 V10 계획
- Settle phase 추가 (V20 자세 정적 평형 안정화)
- Initial pose가 PD로 hold 가능한지 검증
- 또는 시작 base_z를 정적 평형 자세로 자동 조정

**Related**: [[next_goal5_mission]] [[digital_twin_priority]] [[ak80_9_torque_calibration]]
