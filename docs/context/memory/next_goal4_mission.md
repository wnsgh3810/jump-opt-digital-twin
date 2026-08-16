---
name: next-goal4-mission
description: GOAL4 mission - GOAL3 시뮬 결과를 실 robot으로 검증 + 모델 정밀화. 2026-06-06 GOAL3 V0-V25 완료 후 시작.
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL4 Mission

## 한 줄

> **GOAL3의 시뮬레이션 결과를 실 robot 실험으로 검증 + 모델 정밀화 + 다양한 task 일반화.**

## GOAL3 final stack (이어서 사용)

- **V8** (multi-task balanced, default sat 21/0.06) — 권장
- **V25** (best inverse, a_hat refit, sat 17.78/0.30) — jump 특화
- V15 robust NLP (smooth_w=1e-2 + mag_w=1e-3)
- AK80 torque control mode

## GOAL3 시뮬 metric (이미 통과)

- NLP self-cons knee 0.16 (V12 GOAL2 6.3 대비 -97%)
- NLP→FF replay τ_diff 0.0001/0.003 (목표 500배 작음)
- Forward sim drift T=0.05s real 0.11°/2.54°
- Hold-out 6-fold inv hip 3.84 / knee 2.89

## GOAL4 7가지 우선순위 (사용자 추가: 2026-06-06)

1. **★ 실 robot torque mode 실험** (가장 중요): NLP τ 직접 입력 → 실측 τ 비교
2. CVT clutch dynamics 모델링
3. Multi-task NLP (jump + s2s 통합)
4. LMI physically-consistent ID (arxiv 1701.04395)
5. Pinocchio migration
6. Per-trial GRF bias (outlier 150_500_5 해결)
7. **★ CAD → URDF → Multi-simulator (MuJoCo MJX / Newton / IsaacLab)**:
   - CAD 파일 → URDF/MJCF 변환
   - 각 simulator에서 V8/V25 dynamics 재구현
   - Gradient-based optimization (MJX JAX, Newton Warp, IsaacLab PyTorch)
   - 동일 task들 (jump, s2s, payload) 재현 + CasADi NLP와 비교

**References (Priority 7)**:
- MuJoCo Playground 2025: https://playground.mujoco.org
- DiffMJX 2025: https://arxiv.org/html/2506.14186v1
- NVIDIA Newton 2025-03: https://developer.nvidia.com/blog/announcing-newton-an-open-source-physics-engine-for-robotics-simulation/
- Onshape-to-robot URDF tool: https://github.com/Rhoban/onshape-to-robot

## Notion 워크플로우

- **새 GOAL4 Parent 페이지** 생성 (`GOAL4 — Real Robot Validation + Model Refinement (2026-06-06)`)
- Parent location: GOAL3와 동일 CONCEPT (115ab81d255080fdaae6f28f55e3e205)
- G4V1, G4V2... 자식 페이지 timeline 형식 (GOAL3와 동일 9가지 구조)
- 이미지 모두 Notion file_uploads API only

## 다음 작업 명령

`C:\Users\junho\CVT\jump_opt\NEXT_GOAL4_PROMPT.md` 참조.

시작 시 user paste용 메시지 prompt 끝에 명시.

## GOAL3 결과 파일 (계속 사용)

- `goal3/v25_ahat_refit/theta_v25.npz` — BEST inverse params
- `goal3/v20_wider/theta_v20.npz` — V20 sat fit
- `goal3/v5_results/theta_v5.npz` — V5 base
- `dynamics_v8.py` — CasADi NLP
- `v15_robust_nlp.py` — NLP recipe

관련: [[goal3_final_stack]], [[master-insights-pointer]]
