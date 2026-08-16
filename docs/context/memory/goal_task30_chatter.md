---
name: goal-task30-chatter
description: Task 30 (sit2stand+payload) 속도 chattering 해결 ongoing goal (2026-05-27 새벽 작업)
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

**Goal**: Task 30 (sit2stand + max payload) 속도/토크에서 chattering 없는 매끄러운 trajectory 확보. payload는 합리적 수준 유지 (목표 with_cvt ≥ 8 kg).

**Why**: 사용자가 7시간 자고 일어나기 전 결과 확인 예정. 현재 with_cvt 초반 0~0.5s에 dqm 진동 (chatter 또는 sharp transient). 비물리적 momentum trick은 절대 안 됨 (motor 역방향 사용 등).

**How to apply**:
- 다양한 smoothness 가중치 (J_smooth_v2, J_smooth_v, J_smooth) 조합 시도
- N (collocation) 조정 (100/120/150)
- 제약조건 추가 고려 (dqm bound, 단조성)
- 코드 분석 (cost, dynamics, IPOPT 옵션, 초기값)
- 최종 결과 노션 페이지 36cab81d-2550-8132-91e3-faf89fa965ba 맨 마지막에 첨부
- 각도 plot도 포함 (task_plot_helper의 pair_angles.png)

**Files**: 
- task30_payload_sit2stand_no_cvt.py
- task30_payload_sit2stand_with_cvt.py
- plots/regen/task30_*

**현재 baseline (B+ N=100 v2=0.5)**: with_cvt 8-9 kg, no_cvt 3.7 kg

연관: [[feedback_smooth_chatter]] (있다면), [[user_thinking_patterns]] (사기 패턴 거부)
