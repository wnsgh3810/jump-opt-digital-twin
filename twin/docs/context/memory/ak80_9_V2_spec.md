---
name: ak80-9-v2-spec
description: "사용자 robot은 AK80-9 V2 (V3 아님). Peak 18 Nm, Rated 9 Nm."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# AK80-9 V2 정확한 사양 (사용자 robot)

## ★ 사용자 robot = AK80-9 V2 (V1/V2 standard) — V3.0 아님

### Spec
- **Peak torque: 18 Nm** (V3.0의 22 Nm 아님)
- **Rated/Continuous torque: 9 Nm**
- **Gear ratio: 9:1**
- **KV: 100**
- **PD gain firmware limit**: KP_MAX=500, KD_MAX=5

### V2 vs V3 차이
| Spec | V2 (우리) | V3.0 |
|------|----------|------|
| Peak torque | **18 Nm** | 22 Nm |
| Rated | 9 Nm | 9 Nm |
| Rated speed | n/a | 390 RPM |

## Why
- GOAL8 Phase 2 tanh saturation 모델에서 κ range 적용 시 V2 18 Nm 기준
- Stage 2 BO best: κ_h=12.32 (peak 보다 strict), κ_k=26.26 (peak 보다 큼)
- κ BO range는 [8, 20] 정도가 합리적 (현재 [10, 30] too wide)

## How to apply
- Phase 2 narrow refine 또는 Phase 추가 시 κ range 좁히기: [8, 22]
- 실 robot 한계 (V2 peak 18) 기준 sanity check

## ★ 2026-07-09 데이터 발견 (τ-fidelity 실험, 사용자 정정 반영 정정판)
- **MIT PD 경로에 소프트웨어 토크 클립 없음** (사용자 하드웨어 확인).
- **토크 로그 채널은 12bit ±18Nm 모듈러 랩** (스텝 0.00879=36/4095) → xlsx의 currentTorque는
  사용자 MATLAB 언랩(`Data/export_sign_unwrap_continuous.m`: span=36, max_wrap=1 → 복원한계 ±54,
  점프 연속성 + 전역 DP 정제)으로 복원된 **진짜 토크**. dq도 gradient 언랩(±50, max_wrap 2).
- **공급 토크 천장 ≈35.5 (raw iTM)**: 0424/0602에서 게인(60~500) 무관 플래토 = 드라이버 전류 한계 추정
  (spec 피크 18의 ~2배 순간치). 0324 max 18.8/0421 max 29는 한계가 아니라 **수요가 안 닿은 것**.
- raw 35 → paper a_hat 통과 후 shaft ≈ 20 Nm (a_hat 전체 압축률 ~0.68 — CF=0.59 지배).
- **시뮬 재현 최종 (v5, 사용자 07-09)**: 캡/클립 일절 금지 — PD 커맨드 → a_hat만. 천장 ~35.5는 속도 무관
  평탄(back-EMF 봉투 아님) = 하드웨어 전류 한계 추정이나 **정체 미확정** (R-Link 상위컴 전류 한계 설정값 확인 대기).
  sim에 인위 반영하지 않기로 함 → 깊은 포화 구간에서 sim τ가 실측을 정의상 상회할 수 있음을 해석 시 유념.

[[next-goal8-mission]] [[ultimate_objective_optimization]]
