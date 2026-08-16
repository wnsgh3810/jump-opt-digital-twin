---
name: next-goal5-restart
description: GOAL5 RESTART (V1-V9 폐기). mujoco_menagerie Go1 정확 fetch + single-leg adapt. PD sat 변명 금지
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL5 RESTART (2026-06-06 저녁)

**Status**: 이전 GOAL5 V1-V9 모두 폐기. 처음부터 다시.

**Full prompt**: `C:\Users\junho\CVT\jump_opt\GOAL5_PROMPT.md`

## 사용자 결정적 지적
1. **PD ±18 sat이 hard limit이라는 분석은 틀림**. 실 robot도 sat이었고 정상 동작.
2. **V20 자세 PD-unstable 분석도 틀림**. 실 robot은 그 자세에서 정확히 점프.
3. **G5V5 그래프에서 robot이 바닥 뚫음** — 절대 안 됨.
4. **velocity, torque 부호 반대** — 좌표/model 잘못.
5. **mujoco_mpc_deploy / mujoco_menagerie Go1 정확 따라**.

## 절대 변명 금지 list
- ❌ "PD sat이 hard limit이라 못 줄임"
- ❌ "V20 자세가 PD-unstable"
- ❌ "motor delay, Stribeck 정교화 필요"
- ❌ "GRF만 맞으면 OK"
- ❌ Robot이 바닥 뚫음

## 새 접근
1. mujoco_menagerie Go1 fetch (WebFetch agent)
2. Single-leg adapt (4 leg 중 1개 + base는 slide)
3. Position actuator (Go1 표준)
4. **시작 자세 정적 평형 검증** (5초 hold 가능)
5. Reference apply → 결과
6. Iteration별 Notion 페이지

## 체크리스트 (모든 V마다 검증)
```
□ 시작: foot bottom z ≥ 0
□ 시작: link z 모두 ≥ 0
□ 시작: GRF ≈ M·g
□ 시뮬 도중: foot_z ≥ -1mm
□ 시뮬 도중: thigh/shank z ≥ 0
□ Sign: ref dq vs sim dq 같은 방향
□ Sign: ref τ vs sim τ 같은 sign
□ 6 trial 모두 통과
```

## 새 Notion parent
- 제목: "GOAL5 RESTART: MuJoCo Digital Twin (26.06.02)"
- 이전 V1-V9 페이지는 archive (참고용)

**Related**: [[next_goal5_mission]] (구버전), [[goal5_progress_v4]] (이전 시도 기록), [[goal4_lessons_learned]]
