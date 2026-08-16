---
name: next_goal17_mission
description: ★ 다음 GOAL17 미션 — GOAL16 Iter17(157.42) 위 새 axis pool/실측으로 plateau 탈출. GOAL17_PROMPT.md 참조
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

★ **다음 세션 시작점.** GOAL16 종료(Iter17 157.42 best, DROP) 후 **GOAL17**이 다음 예정(현재 `CVT/jump_opt/GOAL17_PROMPT.md`만 존재, 작업 미시작).

**Baseline** = GOAL16 Iter17 **157.42**, KEEP **156.0**(−1.42, 0.9% 필요). plateau = 12D×15=**180-param 모델 한계** → **새 axis pool 필수**(기존 optimizer/score 변형은 GOAL13/16에서 다 실패).

**계획 그룹 (GOAL16에서 미탐색)**:
- **Group G — 실 robot 재측정 (top 후보)**: calf 질량+COM(4회째 deferred), link L1/L2/LC 정밀(±2mm), foot cylinder 크기, CVT gear ratio.
- **Group H — 새 DOF**: floor restitution e∈[0,0.5](현재 0), base COM offset, hip armature(rotor inertia), friction anisotropy μ₂, floor 별도 solreffrict.
- **Group I — ≥7D global**: 5D+solref_tc+imp0(7D) → +stiff_hip/knee(9D), per-trial 12D는 LOCK 유지.
- **Group J — trial subset**: 9-trial 0424-only vs 6-trial 0602-only per-trial NM(encoder-bias 반전 가설 검증).
- **Group K — score refine (Iter16 base 위, 5D-solo 아님)**: Huber/segmented, W_T 20→10, W_H 50→25.

**권장 순서**: Step0 Iter16(159.15) 재현 → link-length ±2mm grid → hip armature[0,0.01] → floor restitution Brent → 7D NM → 0424/0602 subset → Iter16+Group K.

**Locks(GOAL16 계승)**: Mode A, tau_scale=1.0, paper a_hat sgn(v), arm_hip=0, foot cylinder 42×13mm, tau_delay=0, W_GRF=0.2, boundary guardrail 20%+BV≤8, **5D-global 단독 금지(규칙#9)**.

**★ Open question**: worst-3 0424 고전류 floor(합 **40.43**, 200/350/500A)을 새 물리 DOF(restitution/armature)나 재측정 mass로 드디어 뚫을 수 있는가?

**Why:** 모델은 한계점에 도달 — 진짜 개선은 실측/새 DOF뿐. calf 측정은 4회 미룬 standing item.
**How to apply:** GOAL17 시작 시 GOAL17_PROMPT.md + [[master_insights_pointer]](MASTER_INSIGHTS_G9.md) 필독. [[goal16_findings]] [[goal12_findings]] [[real_jump_heights]]
