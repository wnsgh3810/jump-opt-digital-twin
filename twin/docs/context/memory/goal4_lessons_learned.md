---
name: goal4-lessons-learned
description: GOAL4 V36-V55에서 배운 핵심 교훈 + 잘못된 분석 수정. 진짜 원인은 MuJoCo 환경 설정
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL4 Lessons Learned (V36-V55)

## 잘못된 결론 (수정)

**기각**: "V20 자세 [q1=+1.094, q2=-2.474]는 본질적으로 PD-unstable in MuJoCo"

이 결론은 **틀림**. 같은 자세가 실제 robot에서 작동했음. MuJoCo에서 안 되는 건 환경 설정 자체가 잘못된 거.

**Why**: 26.06.02 점프 데이터 = 실제 robot이 그 reference로 점프한 결과. 즉 reference는 dynamically feasible. MuJoCo가 정확하면 같은 결과 나와야.

## 진짜 원인

**MuJoCo 환경 설정이 실제 robot과 안 맞아서** robot이 자세 hold 못 함.
- Floor solref/solimp 부적절 가능성
- Foot geom (size, solimp) 부적절 가능성
- Joint armature/damping/frictionloss 실측치 안 반영
- Base/link mass, inertia 부정확
- Contact margin, impratio 설정 미흡

같은 robot에서 vertical leg standing → GRF=32N stable이지만 V20 자세 → GRF=2707N 폭주. **자세 차이가 아니라 환경 차이**.

## 시도 패턴 (V36-V55)

### 좌표 변환 (확인됨)
- `q1_mu = q1_v20 + π/2`, `q2_mu = q2_v20` ★ 정확
- Gravity, inertia 방향 일관됨
- Stick figure 시각화: V36 GIF (cam azimuth=270)

### Best practice 적용 (모두 시도)
- `mj_forward` warmstart after qpos init
- `margin="0.001"` on default geom
- `impratio="100"`, `cone="elliptic"`
- Foot `priority="1"`, `solimp="0.015 1 0.023"`, `condim="6"`
- Floor `solref="0.02 1"`, `solimp="0.9 0.95 0.001 0.5 2"` 명시
- Position actuator `kp=100`, `forcerange=±18`
- Joint `armature=0.01`, `damping=2`, `frictionloss=0.2`

### 실패 시도
- V42: 300ms settle → robot launch
- V44: 500ms settle + hard contact → robot launch
- V50-V53: Go1 정확 패턴 → 같은 자세에서 launch
- V54: 30cm drop → vertical leg로 안착 (V20 자세 안 됨)
- V55: 바닥 닿은 시작 + 1초 hold + V20 motion → 50ms 만에 launch

### 검증된 fact
- V52 case A (vertical leg): standing perfect, GRF=32N
- V52 case C (V20 자세): 즉시 launch, GRF=2707N
- 자세 별 차이 = 환경 mismatch evidence

## 결론

**Reference 이슈 아님 + 좌표 변환 정확 + GRF spike만 fix 시도해도 안 됨**.
→ 환경 파라미터 자체 fit 필요 = GOAL5 mission.

**Related**: [[next_goal5_mission]] [[digital_twin_priority]] [[ak80_9_torque_calibration]]
