---
name: goal19_qdq_error_sources
description: "GOAL19 q/dq 미스매치 광범위 오차원 종합 — 회귀 진단 + MASTER_INSIGHTS(G9~G16) 정독. 물리 lever 랭킹 + 죽은축 + per-trial tension"
metadata:
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

GOAL19 (2026-07-04). 사용자 "q/dq 너무 안맞음, 폭넓게 고려, 모든 기록 봐" 요청 후 회귀 진단 + 서브에이전트 2개로 MASTER_INSIGHTS(main+G18+G19, G9~G16) 정독한 종합.

**★ 회귀 진단 (핵심)**: 열린루프 토크replay drift의 원인을 분해. constrained EoM 잔차 R을 [τ, dq, sgn, 1]로 회귀 → **R ≈ 0.6·τ (fit R²~0.65)**, April/June 일관. 수학적으로 R≈(M_model/M_real−1)·τ → **모델 유효관성이 실제보다 ~1.6배 큰 신호**. 단 관성을 mass×0.4까지 줄여도 τ계수 0.65→0.33 반만 떨어지고 |res| 안 줄어듦 → **순수 bulk 관성 아님**. 일부 관성/CoM/접촉, 일부 irreducible floor(tau_scale이 fudge로 흡수하던 부분). 0422는 별개 regime(R²0.33, 4월 나쁜 데이터).

**★★ 물리 lever 랭킹 (tau_scale 제거 후 G10~16이 실제로 찾은 것)**:
1. **관절강성/flex (stiff_knee)** — **+85%, 로그 전체 최대 q/dq+h win**. knee≫hip. GOAL19 2.0 적용중, 재적합이 상한 railing.
2. **CoM 재분배 (링크별 dz/dx)** — 미착수였음. torque_qdq refit이 com_dz 양쪽 하한(−0.04) railing = 더 원함. **widen 필요.**
3. **질량 재분배 (m_calf~0.57-0.6)** — +12.6%. 물리적 필수(강제 상향시 sim 폭발, 3회 검증). 적용됨.
4. **무릎 점성마찰 fv_knee (0.095~0.1 cliff 넘기)** — **dq2 −64% (최대 dq2 lever)**. under→over-damped 전이, 8-D joint 상호작용 탐색만 넘김.
5. **접촉 solref/imp0 재적합** — G9 최대 q/dq축(~50%). motor_tm 없는 지금 여지.

**★★ 죽은 축 (시간낭비 금지)**: 관성텐서 I1/I2/Ixx≠Iyy(gradient-flat, regressor cond~1e13, rank-deficient, 단일 평면점프론 excitation 불가), **tau_scale(영구금지, Mode A 위배 — 필요하면 물리 mass/CoM/contact로 드러나야)**, **motor_tm(Mode A선 −132%, 이중필터. 8.37ms는 GOAL7 Mode-B 결과라 transfer 안 됨. "무지연 필터로 회수" 아이디어 철회)**, backlash(0.5°→+206%, 1°→+533%), per-trial IC 주입(11M-score 발산), transmission torsion(J_m 추가시 baseline 붕괴), foot geometry(<3%, 실린더=line contact라 half_len 무감), μ_floor(1.0 sweet spot, <0.7만 slip으로 점프실패), tau_delay(0 optimal), backlash/stiction/DC-gain/NN residual/range-limit 전부 DROP.

**★★★ 근본 tension (GOAL16 결정적)**: 물리 lever들을 **per-trial(12-D)로 fit해야 q/dq가 크게 떨어짐** (fv_knee per-trial dq2 −64%, per-trial fc_hip +28.6%). **단일 global 5-param은 ~16배 나쁨.** 즉 per-trial=q/dq 잘맞음=overfit=최적화 transfer엔 못씀. **단일 통합 물리모델은 q/dq에 진짜 floor 있고, dq2 종단 spike(특히 90_0.75_90_2 low-kd trial)가 병목.** 억지 아닌 데이터 excitation 한계.

**★ 데이터 regime**: q/dq 미스매치는 **torque-control + high-PD sit2stand에 집중**(mass/CoM/h 민감), **position 0421은 PD가 q 추종해 잘맞음**(단 open-loop replay drift). 6월(0602) q2 4.2° 이미 좋음, 4월(0424/0422) 나쁨. 0422는 별개 outlier.

**진행**: `reopt_torque_qdq.py`(v1, torque만 −8.8%: 0424 dq2 3.48→2.66, 0602 1.80→1.48, CoM/stiff railing) → `reopt_torque_qdq_v2.py`(CoM widen+반경dx추가+stiff확대+joint상호작용, 백그라운드). arm_knee 물리값(~0.01) 확정.

관련: [[goal19_underjump_diagnosis]] [[ultimate_objective_optimization]] [[mode_A_purpose]] [[digital_twin_priority]] [[jump_C_fixed_params]]
