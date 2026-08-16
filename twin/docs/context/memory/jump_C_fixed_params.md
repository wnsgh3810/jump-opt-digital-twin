---
name: jump-c-user-fixed-params
description: "Jump Strategy C sweep/BO에서 alpha, fb, M_tot는 user-FIXED. 확장 금지."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Jump Strategy C — User-FIXED Parameters (절대 확장 금지)

**Rule**: jump_C sweep/BO에서 다음 3개 파라미터는 v5 grid 범위로 고정. 확장 금지.

- **alpha**: [0.70, 1.00]   (5 vals: 0.70, 0.78, 0.86, 0.94, 1.00)
- **fb**: [0.0, 0.40]       (7 vals: link bearing 마찰, 물리적 상한)
- **M_tot**: [2.80, 3.60]   (5 vals: 측정된 로봇 질량 범위)

**Why**: 사용자가 직접 물리적 근거로 결정한 범위. 확장하면 비현실적 영역 탐색.
- alpha: GRF 효율 손실 — 0.70 미만 비현실적
- fb: 베어링 마찰 — 0.4 Nm 초과 비현실적 (link bearing 물리 한계)
- M_tot: 로봇 질량 측정값 범위 — 외부 추정 불가능

**How to apply**:
- v5 grid 코드 주석에 `# (FIXED user)` 표기 명시
- BO bounds 설정 시 이 3개는 그대로
- 확장 가능한 건 chase boundary 걸린 다른 파라미터만 (예: Is2 LO, tm UP, Kv 등)
- 메모리만 보지 말고 sweep 코드 주석도 cross-check 필수

**확장 가능 파라미터** (boundary chase일 때):
- Is2, tm, Kv, gAv, gBv, Is1, sp, sd 등

**관련**: [[jump_C_bo_setup]] (BO 셋업), [[sweep_optimization_lessons]]

**2026-05-21 사건**: BO에서 alpha/M_tot/tm/fb 모두 확장 → 사용자 분노. 이 메모리 추가.
