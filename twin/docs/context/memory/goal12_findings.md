---
name: goal12_findings
description: GOAL12 — 15-trial 통합. 공식 best Iter38 176.41. Iter42 128.57는 OVERFIT으로 기각. CAD m_calf 7.9% 과대 재확인
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL12 (2026-06-16~17, ~22h 자율루프): Mode A STRICT(tau_scale=1.0 LOCK) 디지털트윈을 **15-trial = 26.04.24(9) + 26.06.02(6)** 통합에 fit. per-trial 차원을 2D→…→12D base-up(한 축씩). 주력 optimizer = Optuna **CMA-ES**(가장 안정), 보조 TPE/LSQ/EKF/NN residual/Sobol.

**KEEP chain (15-trial 총합)**: Phase 0R **103,860** → Iter1 343.63(GOAL10 v4 stack 전이) → Iter4 235.67(3D fc_hip) → Iter21 206.43(6D contact) → Iter30 194.24(8D mass, m_calf 7.9% over 발견) → Iter35 188.15(9D fc_knee) → **Iter38 = 공식 BEST 176.41**(11D m_calf_scale per-trial, +6.24%). |Δh| avg **4.36cm**, pen max 2.05mm, 4/15 trial <3cm. vs Phase0R 99.83%.

**★★ Iter42 128.57(역대 최저)는 OVERFIT으로 REJECT**: 12D m_calf+m_thigh, 7/15 trial m_calf_scale 0.15~0.46, 0602 group avg 0.22 (비물리, noise-fit). → **m_calf_scale 하한 ≥0.4 권장**.

**★★ CAD M_calf 7.9% 과대추정** (m_calf_scale avg 0.921, calf 복합체 ~71g 가벼움) — GOAL14에서도 재현. **사용자 action item: 실 robot calf 무게 측정**(deferred). CAD M_thigh는 신뢰(scale≈0.97~0.985).

Score: `Σ_trial[W_q·rmse_q + W_dq·rmse_dq + W_τ·rmse_τ + W_h·|Δh| + W_grf·max(0,grf_dev-0.25)² + W_pen·max(0,pen-2)²]`, **W_grf=1.0**. 15-trial 총합이라 수렴값 ~120-180 (9-trial goal과 비교 불가). 커밋 Final `a74c0e0a`, overfit-진단 `c8bdd6c1`. Notion `381ab81d25508199a10afe43e572fa4b`.

**Why:** Iter38이 가장 물리적으로 신뢰되는 in-sample best. m_calf 발견이 standing action item.
**How to apply:** m_calf_scale 하한 ≥0.4 유지(overfit 방지). 한 축씩 base-up + drop-test(≥3%). [[goal13_findings]] [[goal14_findings]] [[real_jump_heights]] [[decisions_log]]
