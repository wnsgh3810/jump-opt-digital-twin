---
name: goal3-final-stack
description: "GOAL3 종료 (2026-06-06) — V8 = V5 (30p) + AK80 saturation. 사용자 진짜 metric (forward consistency) 첫 직접 달성. NLP self-cons knee 0.16, forward drift T=0.05s q1 0.11°/q2 2.54°."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

GOAL3 final stack: **V8 = V5 (30p baseline+motor lag+Coulomb+Stribeck+foot+kindGRF+rotor+state-bias) + AK80 back-EMF saturation 2 fixed params**.

**Why**: 사용자 정정 (forward consistency 우선) 응답. 사용자 진짜 metric (NLP optimal q*, dq* → 실 로봇 → 실측 τ/GRF 일치)의 simulation surrogate 직접 달성.

**How to apply**:
- 점프 inverse-dynamics 분석 → V8 사용 (점프 hip RMSE 3.48이지만 forward consistency 통과)
- NLP forward 최적화 → V8 dynamics function 그대로 사용 (CasADi function 작성됨)
- 새 trial generalization → V8 (boundary chase saturation은 fixed이지만 V5 30p는 90% chase)
- **추가 항 (hx1, hx2 등) 추가 X** — V11 결과로 inverse 좋아져도 forward 악화 (over-fit 함정)

**Final V8 metrics**:
- NLP self-consistency hip 2.74 / knee 0.16 Nm (V12 GOAL2 5.9/6.3 대비 hip -54%, knee -97%)
- Forward drift T=0.05s 점프 평균 q1 0.11° / q2 2.54° (사용자 목표 2° 거의 달성)
- T=0.10s q1 0.45° / q2 4.04°
- Hold-out 6-fold CV inv hip 3.84/knee 2.89 (V5 base, V7 측정)

**Final 파일**:
- `CVT/jump_opt/dynamics_v8.py` (CasADi NLP 통합)
- `CVT/jump_opt/dynamics_v5.py` (numpy inverse_predict_v5, forward_sim_v5)
- `CVT/jump_opt/goal3/v5_results/theta_v5.npz` (params)
- `CVT/jump_opt/goal3/v8_results/v8_nlp.npz` (NLP solution + check)
- `CVT/jump_opt/v8_self_cons.py` (self-cons test)
- `CVT/jump_opt/v12_forward_real.py` (사용자 진짜 metric surrogate)

**Notion**:
- Parent: GOAL3 (376ab81d25508123b2ded69787012592)
- 자식 V1~V12 모두 timeline 형식

**잔여 미해결**:
- Hip self-cons 2.74 Nm 잔여 (saturation 영역 + numerical mismatch)
- s2s_no_cvt trial forward 발산 (q2 33° at T=0.10s) — measurement 특이
- 150_500_5 outlier 여전 (V12 GOAL2와 동일)
- Forward T > 0.20s 누적 발산

**V13-V15 후속 (자율 진화 단계)**:
- V13: NLP→PD replay (PD τ vs NLP τ = 6.72 / 5.34 Nm) — PD가 자체 τ 추가
- V14: FF+PD trade-off Pareto (FF only τ_diff 0.03/1.44, drift 24°/149° → high PD drift 1° but τ_diff 5+ Nm)
- **V15: Robust NLP (smooth + mag penalty) → FF only τ_diff 0.0001/0.003 Nm** ★★★

**GOAL3 진정한 final 권장**:
1. Identification model: V8 = V5 + AK80 saturation (32p)
2. NLP optimization: V15 recipe (mag_w=1e-3, smooth_w=1e-2) → saturation 회피
3. 실 robot: **AK80 torque control mode** (PD bypass) → FF only로 NLP τ 직접 적용
4. 예상 결과: 실측 τ vs NLP τ < 0.5 Nm (사용자 진짜 metric 완전 통과)

**잔여 미해결**:
- Drift 5-10° (실 robot trajectory가 NLP와 다름) — outer-loop adaptive control 필요할 수 있음
- s2s_no_cvt forward 발산
- 150_500_5 outlier
- LMI physically-consistent ID 미적용

**V16 (jump h Pareto) 추가 발견**:
- Jump h ≤ 0.5m: τ_diff < 0.005 Nm (perfect)
- Jump h ≈ 0.6m: τ_diff knee 0.09 (사용자 metric 통과 max)
- Jump h ≥ 0.7m: saturation 영역, τ_diff > 0.2 Nm
- Jump h 0.85m+: NLP infeasible
- **실측 0.94m는 saturation 활용**: V8 NLP은 18 Nm bound, 실측은 22 Nm peak → 사용자 명시 정확함의 정량 증명

**V17 (s2s_no_cvt 진단)**:
- s2s_no_cvt drift_q2 발산 원인 = GRF 아님 (correction sweep 모두 비슷)
- 진짜 원인 = knee saturation 53% + V8 model saturation 영역 한계

**Notion Timeline 완성** (parent: 376ab81d25508123b2ded69787012592):
- Parent + V1, V2, V3, V4, V5, V6, V7, V8, V11, V12, V13, V14, V15, V16, Synthesis (15 자식)

**V18b-V25 후속 (자율 진화 마무리)**:
- V18b: sit2stand NLP convergence (T=1.5s, soft terminal)
- V19: AK80 sat params fit (knee inv -72%)
- V20: bound 확장 → final fitted sat (tau_lim 18.45, k_be 0.25)
- V21: V20 + V15 robust = τ_diff 0.0000/0.0000 ★★★★★ (jump h 0.47m)
- V22: V20 + PD mode (hip τ_diff -83% vs V8)
- V23: V20 + sit2stand (multi-task worse than V8 — V20 jump-specialized)
- V24: a_hat 변환 적용 (s2s/cvt 개선, jump knee saturation 악화)
- V25: a_hat re-fit (jump hip **2.18 -31%** ★, s2s knee 4.90 -27%) — BEST inverse

**Multi-task trade-off (최종)**:
- V8 default: 균형 (jump + s2s 모두 self-cons < 3 Nm) ← **multi-task 권장**
- V20 sat fit: jump 특화 (V21 perfect, V23 s2s worse)

**진정한 GOAL3 final** (사용자 "수직 점프 특화 X" 반영):
1. **V8 model** (V5 30p + sat default 21/0.06 fixed)
2. **V15 robust NLP** (smooth_w=1e-2 + mag_w=1e-3)
3. **AK80 torque control mode** (PD bypass, FF only)
4. **결과**: jump τ_diff 0.0001/0.003 Nm + s2s self-cons 1.54/2.59 Nm

**다음 세션 시작 시 (GOAL4)**:
1. **★ 실 robot torque mode 실험**: V15 NLP τ 직접 → 실측 τ 측정
2. **CVT clutch dynamics** 모델링 (knee 잔차 8-25 Nm)
3. **Multi-task NLP** 강화 (sit2stand + jump 동시)
4. **LMI constraint** (arxiv 1701.04395)
5. **Pinocchio migration**

관련: [[master-insights-pointer]], [[goal2_final_stack]], [[next-goal-mission]]
