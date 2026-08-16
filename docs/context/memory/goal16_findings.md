---
name: goal16_findings
description: "GOAL16 — plateau 탈출 시도. best Iter17 157.42 (KEEP 없음, DROP). 5D-global 단독 금지(규칙#9). worst-3 0424 고전류 floor 40.43"
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL16 (2026-06-21 ~17:50 시작, ~16h cron): GOAL15 **160~162 plateau 탈출** 시도. Baseline = GOAL15 Iter2 **160.79**, KEEP threshold **156.0**. 15-trial W_GRF=0.2. 8+ method 다양화(매 iter 다른 method, TPE 재사용 금지).

**★ Iter1-18 전부 DROP (KEEP 없음). BEST = Iter17 157.42 (+2.09%, BV=8)** = per-trial **12D NM ±40% +2 restart**(180 params). 2nd Iter16 159.15. **5D-global은 catastrophic**(avg 2551, 841~4728) → **NEW 규칙 #9: 5D-global 단독 최적화 금지**(per-trial 12D contact-friction-stiffness coupling 파괴). ≥7D 또는 per-trial fine refine만 허용.

**핵심 발견**:
- Group A CAD R/I(R1/R2/RC/RP, I1/I2/IC/IP) **gradient-flat**(nfev=1, scale=1.0) → CAD inertia 이미 optimal. GOAL13 α≈1.0 재확인.
- motor LPF(-133%)/backlash(-611%) **Mode A 부적합**(raw τ 주입). GOAL7 motor_tm=8.37ms는 **Mode-B 전용**.
- 센서: encoder bias 방향이 **0424 vs 0602 반대** → 날짜별 재캘리브레이션 가설. dq xcorr lag mean 4.63ms(real dq가 sim보다 지연).
- LOTO 15-fold: test 148.72±20.95, train 190.56±130.76, gen-gap −41.83(분포 bias).
- **★ worst-3 0424 고전류 floor (개선 불가)**: 0424_120_2.2_200_2.8=14.98, 0424_150_2.2_350_3.5=12.89, 0424_150_2.2_500_4=12.57 → **합 40.43**(Iter2/16/17 동일). 가설: 200/350/500A 고전류 모터 saturation/미모델 동역학.

**현재 best params (Iter17 per-trial 12D, 예 0424_60_0.75)**: m_base1.222, fv_hip0.816, fc_hip1.311, solref_tc0.00953, imp0 0.191, fv_knee0.0055, fc_knee0.168, m_thigh_scale1.012, **m_calf_scale0.480**, arm_knee0.0063, stiff_hip0.162, stiff_knee0.926.

**공식 final 커밋 아직 없음**(스냅샷 2026-06-21 19:50, Iter18 미완 "running"). 주요 커밋: Iter17 `2e09122d`, Iter16 `432c7492`, 종합표 `9b8b05ba`, Iter5/6/7 복구 `9998df1b`. Notion parent `386ab81d-2550-816d-a9dc-f1968d17a932`. Locks: Mode A, tau_scale=1.0, paper a_hat sgn(v), arm_hip=0, foot cylinder 42×13, tau_delay=0, W_GRF=0.2, guardrail 20%+BV≤8.

**Why:** plateau는 12D×15=180-param 모델 한계 — optimizer/score 변형으론 못 뚫음. 새 물리 DOF나 실측 필요.
**How to apply:** 5D-global 단독 금지. 다음(GOAL17)은 새 axis pool/실측. worst-3 floor가 핵심 타겟. [[goal15_findings]] [[goal13_findings]] [[next_goal17_mission]] [[goal7_stage20_motor_tm]]
