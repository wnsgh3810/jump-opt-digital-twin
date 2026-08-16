---
name: goal14_findings
description: GOAL14 — 9-trial W_GRF=0.3. 공식 KEEP best Iter28 89.847. Iter32 84.13은 raw 최저지만 keep=False. final 커밋 2개 주의
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL14 (2026-06-18, ~10h + ~6h post-stop): **9-trial**(0424×4 + 0602×5)에서 **W_GRF=0.3**(1.0→0.3 하향)으로 per-trial 정밀도 추가 개선. fresh 축(mass scale, arm_knee, stiffness) + global optimizer 테스트. Baseline 109.139.

**★ 공식 KEEP best = Iter28 89.847 (−17.65%)**. KEEP chain: Step0 109.14 → Iter15(95.40) → Iter17(91.43, +arm_knee) → Iter18(90.66, +stiff) → **Iter28(89.85, mass 확장)**.

**★★ Iter32 raw 84.126 (−22.92%, 전체 최저)지만 keep=False** (threshold 82.455, **6 boundary violation**). post-stop 연장체인 Iter28→Iter30(85.00, +arm_knee)→**Iter32(+stiff_hip/knee, per-trial 12D NM)**. Iter32 |Δh| avg **0.04cm**(~0.4mm, Iter38의 4.36cm보다 ~100× 좋음) 대신 grf_dev 0.238. cv0602: total 85.32, |Δh| 5.96cm.

**⚠️ final 커밋 2개 실존(혼동 주의)**: `c538b5f1` "GOAL14 Final Conclusion — Iter28 89.847"(공식 KEEP) **+** `a65c8a7b` "GOAL14 FINAL summary — Iter32 84.13"(post-stop raw best, **keep=False**). checkpoint `3dd41813`. → **공식 best는 Iter28**, Iter32는 "숫자상 최저지만 게이트 미통과".

**핵심**: m_calf_scale→0.4 하한을 3 trial이 hit(calf<60% CAD, GOAL12 재확인). Iter19 tight bounds[0.80,1.10]→재앙 221.26. **per-trial 독립 NM이 유일 효과 구조**(global Iter23 발산 255.88). 8-axis contact 포화(solimp-shape/solref_d/imp1/arm_hip DROP). **arm_hip 축 degenerate→폐기**. 32 iter / 8 KEEP / 24 DROP. Weights W_Q100/W_DQ3/W_T20/W_H50/**W_GRF0.3**/W_PEN10. Notion `383ab81d255081b3bd6bc8510f8c3f6d`. 비교 dir `goal_compare_g12_g14`.

**Why:** W_GRF↓로 q/dq/τ/h 우선 매칭 → Iter32 점프높이 거의 완벽. 하지만 KEEP 게이트는 Iter28.
**How to apply:** "best" 인용 시 Iter28(공식)/Iter32(raw, keep=False) 구분. arm_hip=0 LOCK. [[goal12_findings]] [[goal15_findings]] [[mode_A_purpose]]
