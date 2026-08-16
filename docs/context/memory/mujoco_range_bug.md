---
name: mujoco-range-bug
description: MuJoCo XML의 joint range가 V20-like init 자세에서 huge artificial force 발생시키는 hidden bug (GOAL5R V23에서 발견). range 제거 또는 wide 설정 필수.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

★ MuJoCo XML의 `range="..."` joint 속성은 hidden joint limit constraint를 발생시킴. range 안에서도 limit 근처에서 soft penalty force가 적용되어 dynamics 망침.

**Why:** GOAL5R V11-V17에서 `range="-3 3"` + V20 init q2=+2.548 (limit +3.0에서 0.452 rad 차이). MuJoCo default margin이 V20 자세에서 86,000배 큰 artificial force 적용 → 100ms 안에 robot이 vertical로 변형. mj_solveM=(-9.81,0,0) 이론값이지만 mj_forward의 qacc=(162, 3093, -6230). 차이의 원인 = joint limit constraint.

**How to apply:**
- MuJoCo MJCF 작성 시 init pose가 range limit 근처에 있으면 무조건 range 제거 또는 wide(`-10 10`) 설정
- 새 sim에서 PD가 hold 못 하면 의심해야 할 첫 번째 — XML의 range 속성
- Debug 패턴: mj_solveM(-qfrc_bias) vs mj_forward의 qacc 비교 — 다르면 hidden constraint 있음
- 노션 페이지: GOAL5 RESTART parent (377ab81d-2550-81aa-8e1f-e5a5777b60ef) 아래 "Concept: Range XML Bug" (377ab81d-2550-8101-a4ea-c68f5bd7c575)

**관련 메모리:** [[goal4_phase1_state]], [[position_data_26_06_02_model]]
