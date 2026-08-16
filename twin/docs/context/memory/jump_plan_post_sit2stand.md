---
name: jump-plan-post-sit2stand
description: 점프 식별 계획 — sit2stand BO 종료 후 진행할 순서와 모델 변경 사항
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

sit2stand BO 종료 후 점프 식별 계획 (2026-05-19 사용자 지시).

**순서:**
0. sit2stand BO 종료 즉시 BO best params로 **sit2stand 4-trial 비교 그래프 재생성** (v9 best 3.8704 위에 BO가 개선했는지 확인)
1. 같은 BO best params로 점프 데이터 비교 그래프 생성 (현 v17 모델 그대로)
2. 점프 모델 수정: `kc`, `bc` (스프링-댐퍼 컨택트) 제거. 소프트 컨택트는 `alpha`만 유지
3. sit2stand BO 결정 8개 파라미터 (gAv, gBv, Is1, Is2, Kv, sp, sd, tm, fb) FIX
4. 점프 grid sweep — alpha 등 남은 파라미터만, boundary chase 없을 때까지 반복
5. 그 데이터로 점프 BO → 최종 alpha 결정
6. 최종 파라미터로 점프 결과 그래프

**Why (사용자 발언):**
"점프 스윕에서 kc,bc를 모델에서 지우자 소프트 컨택트는 알파만 남기자 오히려 스프링 댐퍼 모델이 갭을 키우는거 같애"

스프링-댐퍼 페널티 컨택트가 실제와 sim 사이 갭을 더 벌린다는 관찰. alpha 단독으로 GRF 스케일링하는 게 더 적합.

**How to apply (CasADi `contact_model='alpha'` 패턴 그대로 sim으로 이식):**
- 참조: `optimization/final_v16.py` line 147-211. `contact_model='alpha'`이 정답.
- **Rigid contact constraints**:
  - `foot_z = z + l1*sin(q1) + l2*sin(q1+q2) == 0`
  - `foot_x = l1*cos(q1) + l2*cos(q1+q2) == 0`
- `dz_grf` = Lagrange multiplier (vertical GRF), 매 step DAE로 풀이
- **Body z dynamics에만 alpha 스케일**: `body_grf_z = alpha * dz_grf`
- **Joint dynamics는 raw dz_grf 사용**: 
  - `RHS_q1 = tau1 - dx*(l1*s1+l2*s12) + dz_grf*(l1*c1+l2*c12)`
  - `RHS_q2 = tau2 - dx*(l2*s12) + dz_grf*(l2*c12)`
- v17의 `kc*delta + bc*delta_dot` penalty 완전 제거
- 점프 새 모델: `jump_sim_alpha_rigid_jit` 같은 이름으로 별도 파일에 작성
- Stance/flight 전환: stance 중 `dz_grf < 0`이면 lift-off 종료
- 이 결정의 맥락은 [[digital_twin_priority]] (q/dq/tau/GRF 매칭 우선)와 일치
