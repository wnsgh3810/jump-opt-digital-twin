---
name: goal8-findings-phase14-18
description: "GOAL8 Phase 14-18 핵심 발견 — sensor delay, multi-trial weighting, narrow refinement, trade-off 분석"
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL8 Phase 14-18 핵심 발견 (2026-06-08)

## Phase 진행 + 결과 요약

| Phase | Score (unweighted) | 변화 | 핵심 axis | 상태 |
|---|---|---|---|---|
| Stage 14 | 2026.66 | baseline (sensor delay 추가) | q_delay_ms=1.0 | ★ plateau 탈출 |
| Stage 15 | 2026.66 | 0 | friction wider | ❌ NEGATIVE |
| Stage 16 | 1960.99 | -3.2% | multi-trial weighting | ★★ 큰 진전 |
| Stage 17 | 2026.66 | 0 | Pareto multi-warm-start | ❌ NEGATIVE |
| **Stage 18** | **1695.97** | **-13.5%** | narrow refinement | ★★★ Best |

## ★★★ 핵심 발견 1: Multi-trial Weighting (Phase 16)

각 trial에 다른 weight 부여 (high-PD ↓, low-PD ↑):
- `60_0.75_60_2  : w = 1.5`
- `150_2.2_500_5 : w = 0.5`

**Why**: high-PD trial은 motor saturation으로 q tracking이 motor 한계에 의해 제한 → 정보 가치 ↓. Low-PD trial 집중 → 모터 외부 동역학 (mass/inertia/friction) 정확화 → high-PD도 자연스럽게 개선.

**How to apply**: 동등 weighting에 갇혔을 때 multi-trial weighting 시도. Score function 변경이 새 basin 발견 가능.

## ★★★ 핵심 발견 2: Narrow Refinement 효과 (Phase 18)

Stage 16의 핵심 axis에 narrow range:
- `q_delay_ms ∈ [3, 8]` (Stage 16: 5.2)
- `akp_k_slope ∈ [1, 3.5]` (Stage 16: 2.12)
- `κ_h ∈ [10, 16]`, `κ_k ∈ [16, 20]`

**Why**: Wide range는 다양한 탐색에 강함 but 좁은 sweet spot 못 찾을 수 있음. Narrow는 fine tuning에 효과적.

**How to apply**: 새 basin 발견 후 narrow refinement로 fine tuning. Phase 18에서 single-phase 13.5% (largest yet) 개선.

## ★★ 핵심 발견 3: Plateau 탈출 axis ≠ 단순 axis 추가

NEGATIVE phases가 보여준 것:
- Phase 5 (backlash) ❌
- Phase 12 (m_foot_extra) ❌
- Phase 13 (per-PD) ❌
- Phase 15 (friction wider) ❌
- Phase 17 (multi-warm-start) ❌

**Why**: Sim 내부 axis 추가만으로는 plateau 못 깸. 실 robot "진짜 다른 부분" 추가 (sensor delay) 또는 score function 변경 (multi-trial weighting)이 필요.

**How to apply**: 새 axis 추가 vs 새 weighting 둘 다 시도. NEGATIVE도 valuable — 어떤 axis가 효과 없는지 검증.

## ★★ 핵심 발견 4: q_delay 진짜 값 ~5 ms (Stage 18: ?)

Phase 14: q_delay 1.0 ms (local optimum, CAN bus 1kHz)
Phase 16: q_delay 5.20 ms (실제 CAN + ADC + processing 합)
Phase 18: q_delay 추가 fine tuning

**Why**: CAN bus 1ms + encoder ADC + microcontroller processing = ~5 ms 총 latency. 1ms는 wide range BO에서 local optimum이었음.

**How to apply**: Sensor delay 모델 사용 시 [1, 10] ms range로 BO 추천. 1ms 근처에 안주하지 말 것.

## ★★ 핵심 발견 5: 비대칭 κ (HIP vs KNEE)

Phase 14: κ_h = κ_k = 18 Nm (default)
Phase 16: κ_h = 12.45, κ_k = 19.44
Phase 18: κ_h ≈ ?, κ_k ≈ ?

**Why**: 모터 동일 (AK80-9 V2)지만 mounting + load + 마찰 차이로 effective saturation 다름. HIP은 더 작은 effective max torque.

**How to apply**: κ_h와 κ_k를 따로 BO. Symmetric 가정 금지.

## ★★ Trade-off 분석 (Stage 16 vs Stage 18)

| Metric | Stage 16 | Stage 18 | 우수 |
|---|---|---|---|
| Total score | 1960.99 | **1695.97** | S18 |
| τ1, τ2 RMSE | 3.0-6.3 | **1.9-5.7** | S18 |
| GRF RMSE | 15-27 N | **12-19 N** | S18 |
| q1 RMSE | **0.017-0.042** | 0.018-0.053 | S16 |
| q2 RMSE | **0.016-0.078** | 0.062-0.080 | S16 |
| sim 점프 높이 | 83-86 cm | 72-80 cm | S16 (Real 85-98) |

**Why**: Score weighting에서 W_TAU + W_GRF 비중이 W_Q2 대비 큼 → BO가 τ + GRF 매칭에 집중 → q2 매칭 손해.

**How to apply**: q2 매칭이 우선이면 W_Q2 ↑ 재BO. 점프 높이 매칭이 부수적이면 Stage 18 ok.

## ★ Real Jump Heights (Real Data.txt 정확)

| Trial | Real h (m) |
|---|---|
| 60_0.75_60_2 | 0.94 |
| 60_1.5_60_1.5 | 0.96 |
| 90_0.75_90_2 | 0.98 |
| 120_2_120_2 | 0.94 |
| 150_2.2_250_3 | 0.90 |
| 150_2.2_500_5 | 0.85 |

범위: 85-98 cm. 이전 페이지 "62-74 cm"는 잘못된 추정 (Real Data.txt 미확인).

## ★ 버그 발견: stage14_modeA_richer.py 모듈-level BO

`run_trial_modeB_v7.py` → `stage14_modeA_richer.py` import 시 300-trial GOAL7 BO 자동 실행 (`if __name__ == '__main__':` guard 없음).

**우회**: `goal8_clean_helpers.py` (build_xml inline) + `run_trial_modeB_v8.py` (constants inline) 사용.

**How to apply**: GOAL8 새 phase는 모두 v8 imports 사용. v7은 deprecated.

## 다음 단계 (Phase 19+)

1. **Phase 19**: q2 weight ↑ 재BO (q2 매칭 우선)
2. **Phase 20**: Stage 18 multi-seed (seed 7, 99) — robustness
3. **Phase 21**: Stage 16 + Stage 18 ensemble (avg or interpolate)
4. **Phase 22+**: 새 axis (variable timestep, contact variants)

## 코드 위치

- `CVT/jump_opt/goal6/goal8_stage14_bo.py` (Phase 14)
- `CVT/jump_opt/goal6/goal8_stage15_bo.py` (Phase 15)
- `CVT/jump_opt/goal6/goal8_stage16_bo.py` (Phase 16) — `goal8_clean_helpers` + v8
- `CVT/jump_opt/goal6/goal8_stage17_bo.py` (Phase 17)
- `CVT/jump_opt/goal6/goal8_stage18_bo.py` (Phase 18)
- `CVT/jump_opt/goal6/run_trial_modeB_v8.py` (clean Mode B, no stage14 import)
- `CVT/jump_opt/goal6/goal8_clean_helpers.py` (build_xml + weights)

## 관련 memory

[[real_jump_heights]] [[ak80_9_V2_spec]] [[next_goal8_mission]] [[pd_sim_purpose]] [[digital_twin_priority]]
