---
name: goal15_findings
description: GOAL15 — 15-trial W_GRF=0.2. best Iter2 DE 160.79 (KEEP 없음). method-diversity 체인. 계획한 5개 물리축은 미실행
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL15 (2026-06-19, ~16h): **15-trial**(0424×9 + 0602×6), **W_GRF=0.2**(1.0→0.3→0.2 단계 하향, 사용자 결정). GOAL12 Iter38 + GOAL14 Iter32 synergy(arm_knee+stiff) seed. 사용자 directive = **매 iter 다른 optimization method**. Baseline(재채점) 194.45.

**★ KEEP 없음 — best = Iter2 DE 2D(solref_tc×imp0) 160.79 (−17.27%, BV=16, boundary-safe 최저)**. Iter5 basinhopping raw 최저 159.94지만 **BV=120 → DROP_BV(overfit, guardrail 기각)**. Plateau 159~162.
- Iter1 NM 12D(BV120), Iter2 DE 2D(best), Iter3 Sobol 12D screening(N/A), Iter4 NSGA-II 2-obj, Iter5 basinhopping(**TIMEOUT 11/15 trial**), Iter6 LOTO(**미실행, run_log 0 byte, orchestrator phase5=False**)

**★ method 다양성 ≠ score 개선** — 6 optimizer 전부 159~162 plateau = 물리모델 한계 재확인. contact params가 bottleneck(imp0_hi 7/15, solref_tc_lo 8/15 반복 경계). **boundary guardrail 도입**(KEEP = −3% AND BV<10). dh_avg **1.54cm**(GOAL14 cv0602 5.95cm보다 ~4× 좋음).

**★ 계획했던 5개 fresh 물리축은 전부 미실행** (per-PD αkp/αkd, kinematic l_thigh/l_calf offset, foot rolling friction μ_roll, per-trial m_base 0424/0602 분리, mcs 하한→0.3) → method-diversity 프로그램으로 pivot. **5축 모두 GOAL16/17로 이월**.

**⚠️ final 커밋 2개**: `5d9ec6b7` "GOAL15 Final Conclusion — best 160.79(Iter2 DE 2D, BV=16)"(authoritative, 06-19) **+** `c630a59e` "method diversity chain". Score scale ~160 = 15-trial × W_GRF=0.2(GOAL14 ~90과 비교 불가, 각자 Step0 대비 %만 비교). Notion `383ab81d-2550-8198-8688-e93cd90271fd`.

**Why:** 6개 다른 optimizer로도 plateau 못 뚫음 = contact param 물리 bounds 재설계 필요(optimizer 더 돌려도 무의미).
**How to apply:** GOAL15가 계획만 하고 못 한 5개 물리축이 다음 후보. W_GRF=0.2 확정. [[goal14_findings]] [[goal16_findings]] [[next_goal17_mission]]
