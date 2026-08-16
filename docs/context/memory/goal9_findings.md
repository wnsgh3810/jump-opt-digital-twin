---
name: goal9_findings
description: "GOAL9 — Mode A 디지털트윈 base-up. Baseline 74,609→848.85 (98.86%). Config D + 5 Mode-A insights (actuator=ideal torque)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL9 (2026-06-09~06-16, 7일 자율루프): MuJoCo **Mode A** 디지털트윈을 26.04.24 **9-trial**에 fit. 입력 = `paper_a_hat(currentTorque, dq)` (Pure Paper sgn(v))을 actuator 토크로 주입 → sim q/dq/τ + 점프높이가 실측 재현 목표. 11-phase base-up, phase마다 ≥4 method BO (scipy DE/CMA-ES/TPE/Grid).

**KEEP chain**: Baseline(P0) **74,609.6** → Final **848.85** (**98.86%**).
- P1 solref/solimp (DE, +97.59%): solref_tc=0.005563, solref_d=1.31978, imp0=0.45596, imp1=0.93988, imp_mid=0.014445
- P6→11 tau_scale (CMA-ES, +35.92%): tau_scale_h=1.0074, tau_scale_k=1.1557
- P8 m_foot_extra (TPE, +16.55%): 0.018461 kg
- P10 **Config D** (RK4, +10.82%): dt=0.0005, RK4, cone=elliptic, impratio=100
- DROP: μ_floor, armature=0, joint damping=0(점프높이 -54% override), motor_tm=0, tau_delay=0, fl-refine(<3%)

**★ 5 Mode-A insights (durable)**: paper_a_hat은 **최종 기계 관절토크**(rotor inertia·viscous·전기 LPF·CAN/ADC delay 이미 포함) → armature/damping/motor_tm/tau_delay 추가 = double-counting → 더 나빠짐. 그래서 전부 0이 best. **Config D(수치정확도)가 critical**: GRF dev 36.9%→5.6%, foot pen 3.31mm→0.00mm.

Score scale: 9-trial **합**, W_q100/W_dq3/W_τ20/W_h50/W_grf1/W_pen10. 결과 avg|Δh|=29.6cm(목표<3 미달, 물리한계), GRF dev 8.2%✓, pen 0✓. Notion parent `380ab81d-2550-814d-80c2-fa7bd1b61ec4`. 커밋은 rolling "GOAL9 checkpoint t+Nh" 방식(전용 해시 없음). XML `goal9/phase_final/leg_g9_FINAL.xml`.

**Why:** 전체 Mode A 디지털트윈의 토대. Config D와 5 Mode-A insight는 이후 모든 goal의 기반.
**How to apply:** 새 Mode A sim은 Config D(dt0.0005/RK4/elliptic/impratio100)에서 시작. actuator 내부동역학(armature/LPF/delay) 추가 금지. [[mode_A_purpose]] [[goal7_base_model]] [[pd_sim_purpose]]
