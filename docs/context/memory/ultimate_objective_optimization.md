---
name: ultimate_objective_optimization
description: ★★★★★ 사용자 최종 목적 (07-09 재강조) — 트윈 최적화 결과로 PD 배포 시 "측정 τ ≈ 계획 τ*" (PD 주입→0). 모든 지표·모델선택·최적화 설계의 판단 기준. 절대 흐리지 말 것.
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# ★★★★★ 2026-07-09 사용자 직접 재강조 (어시스턴트가 흐리게 말해 정정받음)

**"디지털 트윈을 제대로 이루고 → 그 모델로 최적화(NLP든 sampling이든) → 그 결과로 PD 제어했을 때
나오는(측정되는) 토크가 최적화 결과와 차이가 적게 나오는 것."** — h/상태 전이만이 목적이 아니다.
**τ-수준 sim2real 일치가 성공 지표다.** "목적은 τ 일치가 아니라 상태 전이"라고 말하는 것은 오답 (07-08 실수).

**논리 사슬 (왜 q·dq 최우선 지시인가)**: τ_meas = τ_ff + Kp·e_q + Kd·e_dq (+a_hat 변환 잔차)
→ **τ-갭 = PD 주입 = Kp·e_q + Kd·e_dq**. kp 120–200에서 e_q 1° ≈ 2–3.5Nm, kd 2–5에서 e_dq 1rad/s ≈ 2–5Nm.
q·dq 정밀도 지시는 이 두 통로 그 자체. 폐루프 오차는 PD 응답 시간창(수십 ms)에서 결정
→ **0.1s 창 심판(mshoot)이 이 목적의 정합 지표**, full-horizon 개루프 발산은 예측력 없음 (G22 P4 정량 입증).

**파생 원칙 (2026-07-09)**:
1. **역할 분리 유지**: fitting = Mode A 창 (07-05 원칙: PD로 fitting 금지). **배포 검증 = 폐루프 τ-갭** (RMS/max PD 주입).
2. **배포 심판 신설**: 트윈-인-더-루프 교차 리허설 (계획 모델 ≠ 플랜트 모델, 프런티어 앙상블 e/f/g/h) → 예상 τ-갭 산출.
3. **PD-여유 제약**: τ_ff가 토크 한계에 붙으면 PD 보정 단방향 → 최적화에 margin(≈3–5Nm) 1급 제약. 한계 타는 해(G22 CMA 100%)는 이 목적에 부적합.
4. **실기 프로토콜**: 로봇에서 τ_meas − τ_ff 로깅 = 트윈 품질의 직접 측정 + 다음 fit의 표적 잔차 (단 τ_meas 자체의 under-read 몫 분리).
5. **★ 스탠스 널-공간 (07-09 사용자 관찰→검증)**: 발 고정+레일 = 1-DOF → 운동은 a(q)·τ 한 조합만 결정, 직교(널) 방향의 hip↔knee 재분배(canonical 부호로 Δτ1≈+2·Δτ2)는 q/dq에 **불가시**. fit−label 토크차 에너지의 90%+(중앙값 95%)가 널 방향 (g22_p12_tradeoff.py 검증). → 상태-만 적합으로 스탠스 토크 분배 식별 불가 — **Mode A 창 심판에 τ-잔차 채널 추가 필요**, 수평 GRF 측정이 분배를 직접 관측(현 플레이트 수직만 — 실험실 항목).

---

**사용자 최종 목적 (2026-07-03 명시, 절대 잊지 말 것)**:
1. **디지털 트윈을 최대한 완벽하게** 만든다 (지금 GOAL19 Mode A 작업).
2. 그 트윈으로 **궤적 최적화**(NLP/trajectory opt)를 돌린다.
3. 나온 최적 궤적이 **실제 로봇에서 잘 작동(sim-to-real transfer)** 해야 한다.

즉 트윈 자체가 목적이 아니라 **"transfer 잘 되는 최적 궤적 생성"** 이 최종 목적. 모든 결정은 이 기준으로 판단.

**실제 제어 전략 (2026-07-03 명시)**: 최적화 궤적의 q*, dq*를 **PD 제어기에 넣고**, 필요하면 최적화 τ*를 **피드포워드 토크**로 추가. PD 게인은 **적당히 높게** 해서 위치/속도를 잘 추종. **핵심 바람: 실제 τ_applied가 최적화 τ*와 최대한 비슷하게 나오는 것.** → τ_applied = τ_ff + Kp·e_q + Kd·e_dq 이므로, **모델이 정확할수록 추종오차 e→0, PD보정→0, τ_applied→τ***. 즉 "τ_applied≈τ*"는 곧 모델 정확도의 척도. 모델 정확도 ↑ → sim2real gap ↓ 는 이 전략에서 **직접적으로 맞음**. 단 Mode A만으론 부족 — raw current-torque 입력 자체가 부정확(under-jump이 증거)하므로 **a_hat(전류→실토크) actuator 모델이 torque 채널 일관성의 전제조건**. + 최적화에 T-N 토크한계 제약 넣어야 τ* 전달 가능.

**★ 핵심 전략 인사이트 (2026-07-03, 정정판)**: Mode A는 **τ→운동(passive dynamics)** 검증. 최적화는 **command→τ→운동** 필요. **★★ 정정: a_hat(paper)은 이미 적용돼 있음** — GOAL19의 canonical tau_real = `paper_a_hat(raw currentTorque, v)` (전기변환+포화+마찰 5-param, A_HAT=[0,1.156,4.17e-4,0.2686,0.049], KT=0.091,GR=9,CF=0.59). 모든 dynamics 파라미터는 **이미 a_hat 토크로 fit됨** → a_hat 때문에 재fit 필요 없음. **그런데도 under-jump 지속** → 뜻: (1) a_hat 파라미터(generic paper값, LOCK)가 이 로봇에 안 맞아 손실 과대추정, 또는 (2) a_hat 마찰항 ⊕ dynamics 관절마찰(fv/fc) **이중계산**, 또는 (3) 잔여 dynamics gap. 이전 GOAL들이 a_hat 위에 **tau_scale로 다시 키운 이유가 바로 이 잔차 보정**. 최적화 목적엔 "a_hat 추가"가 아니라 **a_hat 재식별(모터 실험) 또는 마찰 이중계산 해소**가 필요, 그러면 dynamics 재fit도 동반. + optimizer는 한계에서 노니까 T-N 포화 제약 + real-in-the-loop 보정 필요.

관련: [[pd_sim_purpose]] [[digital_twin_priority]] [[goal19_underjump_diagnosis]] [[ak80_9_torque_calibration]] [[ak80_9_V2_spec]] [[mode_A_purpose]]
