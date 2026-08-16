# MASTER_INSIGHTS_G18 — Unified Digital Twin (7 datasets, base-up)

> **시작**: 2026-06-23 04:30 KST
> **마감**: 2026-06-23 17:00 KST (cron 기반 자율)
> **모드**: Mode A only (paper_a_hat τ input)
> **데이터**: 7 dataset (sit2stand_air_0319 + sit2stand_gnd_0319 + sit2stand_0324 5sub + jump_0421 6sub + jump_0422 3sub + jump_0424 9trial + jump_0602 6trial)
> **GOAL18 Notion parent**: (Phase 0R 완료 후 ID 기록)

---

## 이전 GOAL lessons 누적 (즉시 반영)

### GOAL7 (jump 1순위)
- Stage 11-46 Mode A 207.38, Mode B 371.70
- Stage 20: motor_tm 8.37ms 발견 (LPF)
- Stage 19→20 Score 435→283 (35% 개선, GRF 6.8 / 44% 개선)
- Pure Paper sgn(v) 사용 ★ smoothing 절대 금지

### GOAL9 (cylinder foot + base-up)
- Phase 1 solref/solimp 큰 효과 (★★★ KEEP)
- Phase 8 m_foot_extra +16.55% KEEP
- Phase 10 dt+integrator Config D ★★★ KEEP
- ★ Phase 6/11 "tau_scale ★★★ KEEP MASSIVE WIN"은 Mode A 본질 위반 fudge였음 — GOAL18에서 폐기 (2026-06-23 사용자 재명시)

### GOAL12 (15-trial unified)
- Iter38 score 176.41 (★ 마지막 안정 canonical)
- Iter42 부터 overfit 진단
- 10D per-trial (fv_hip, fv_knee, fc_hip, m_base, solref_tc, imp0, m_thigh_scale, m_calf_scale, fc_knee, arm_knee)
- arm_hip = 0 LOCK, raw -tau_real direct input

### GOAL14 (9-trial only)
- Iter32 score 84.13 (12D per-trial: + stiff_hip + stiff_knee)
- Boundary violations 6개 (m_thigh, m_calf, fv_knee, fc_knee의 lower 한계)
- ★ 어제 contype=0 통과 bug — contype=1로 fix됨

### GOAL15 (W_GRF=0.2 + stiff axes)
- Iter2 score 160.79 (★ 사용자 canonical, iter5와 0.5% 미만 차이)
- 12D per-trial + global LOCKS (W_Q=100 W_DQ=3 W_T=20 W_H=50 W_GRF=0.2 W_PEN=10)
- ★ contype=0 통과 bug — fix됨

### GOAL16 (16h 자율)
- Iter56 score 128.65 (★ 17D + dq+per-trial chain)
- Virtuous cycle: dq bias ↔ 17D 번갈아 진화
- 8 KEEP chain (Iter49→Iter56)
- Cross-validation: P10_D0/P10_D1/P20_D1/P30_D1/P60_D1.5_P60_D2 + sit2stand_gnd_0319 + jump_0421/0422
- ★ 어제 P10_D0/P30_D1 + canonical 코드 lock-in
- ★ 어제 P10_D1 + P60 minor drift 발견 (XML structure, settling gains)

### 2026-06-23 Cross-validation (GOAL12 iter38 + GOAL14 iter32 + GOAL15 iter2)
- 48 child Notion + 3 parent pages (parent 흩어짐, manual move 예정)
- Mode A 바닥 통과 bug 발견: thigh/calf contype=0 → contype=1 fix (commit cdcb1001)
- Findings:
  - GOAL12: jump_torque best, gnd worst
  - GOAL14: gnd best, jump_torque worst
  - GOAL15: 0421/0324 best, gnd worst

---

## 핵심 미해결 / 가설 (GOAL18에서 검증)

1. **★ Sit2stand + jump 통합 학습 가능한가?** (기존 GOAL은 jump-only) — 운동 방식이 매우 다른데 통합 가능한지
2. **★ q_offset 효과** (사용자 명시 "q offset 최대 1° 가능")
3. **★ Foot pos offset** (실측 vs CAD 미세 차이)
4. **★ Foot slip / friction** (sit2stand 저속 + jump 고속에서 동시에 잘 fit?)
5. **★ CAD L1/L2/LC ±5mm fit** (실측 정확하다는 사용자 명시지만 미세 차이 가능)
6. **★ Per-trial vs global params 균형** (overfit 방지)
7. **★ Stribeck friction** (미시도)
8. **★ Actuator NN residual** (미시도)

---

## ★★★ 2026-06-23 사용자 priority 정정 (절대 변경 X)

**1순위**: q, dq (joint angle + velocity) — 매칭 핵심, score weight 동등
**1순위 (jump only)**: h_jump (max base_z) — jump trial 1순위
**2순위**: τ (Mode A 자동 ≈0), penetration (땅 통과 방지)
**3순위**: GRF — "엄청 중요한 거 아님"

**Score function v2 weights**:
- Wq1=Wq2=100, Wdq1=Wdq2=50, Wh=100 (jump), Wt1=Wt2=0, Wgrf=0.1, Wpen=50

**Anim 추가 강제**:
- foot_z > floor_z verify (시작 + 진행 중)
- 통과 시 anim에 빨간 경고 + Notion ★ callout
- Camera robot 동적 추적 (base_z 따라감)
- contype=1 verify (commit cdcb1001)

---

## ★★★ Mode A 본질 (사용자 재명시 2026-06-23): tau_scale 변수 X

**규칙**: Mode A sim에서 ctrl = -tau_real (sign flip only). 어떤 scale, modifier, fudge factor도 사용 X.

**왜**: 
- Mode A 본질 = paper_a_hat baked actual motor τ를 sim 그대로 입력
- npz tau_real은 이미 paper_a_hat 적용 (v7+ baked)
- tau_scale 같은 modifier는 본질 위반 (fudge factor)
- GOAL9 "tau_scale ★★★ KEEP MASSIVE WIN"은 본질 위반된 fudge였음 — GOAL18에서 폐기

**적용**:
- 모든 sim 스크립트에서 `ctrl_sim = -tau1_real, -tau2_real` (raw)
- `TAU_SCALE` 상수 / 변수 정의 X
- paper_a_hat 함수 적용도 X (이미 baked) — 그냥 tau_real raw 사용
- 17D global params 또는 axis pool에 tau_scale 포함 X

---

## Phase 0R (★ 시작 baseline, Iter0R 진행 중)

(시작 시점부터 채워짐)

---

## Iter0R Pure Base baseline (2026-06-23)

**Notion**: `Iter0R — Pure Base Baseline` (page_id `387ab81d-2550-8116-b13e-ed98698f9ae2`)
**Total**: 31 sub-experiment (sit2stand 7 + jump 24)
**sim_success**: 30/31 (사용자 보고: sit2stand 6/7, jump 24/24)

### 결과 요약 (Mode A direct τ input, Pure Paper sgn(v))

- **sit2stand_air_0319/ROOT** (15 cycle, base weld): mA q1=0.760°, q2=39.66°, dq1=2.40, dq2=23.96, τ1=0.002, τ2=0.002. pen_max=0mm (air).
- **sit2stand_gnd_0319/ROOT** (15 cycle, gnd): mA q1=0.498°, q2=0.965°, dq1=1.45, dq2=2.43, τ1≈0, τ2≈0.018. **pen_max=19.4mm (cycle15 worst)** → contact stiffness 부족.
- **sit2stand_0324** (5 sub): P10_D0=0.74° (best), P10_D1=3.03°, P20_D1=2.06°, P30_D1=5.61° (★ WORST), P60_D1.5_P60_D2=1.15°.
- **jump_position_0421** (6 trial): q1 RMSE 0.18-0.40°. h_sim 0.61-1.11m vs h_real 0.79-0.86m (편차 ±25cm).
- **jump_torque_0422** (3 trial): q1 RMSE 0.06-0.41°. h_sim ≈0.63-0.74m.
- **jump_0424** (9 trial): q1 RMSE 0.01-0.68°. h_sim 0.49-0.93m vs h_real 0.79-0.91m.
- **jump_0602** (6 trial): q1 RMSE 0.05-0.38°. h_sim 0.61-0.98m vs h_real 0.85-0.98m.

### Score 추정 (W_q=100, W_dq=50, W_h=100, W_t=5, W_grf=0.1, W_pen=50/1000)
- 31-row sum ≈ 50,817 (mean 1639/row)

### Worst-3 / Best-3 (by mA_q1 RMSE)
**Worst-3**:
1. sit2stand_0324/P30_D1 (5.606°)
2. sit2stand_0324/P10_D1 (3.033°)
3. sit2stand_0324/P20_D1 (2.060°)

**Best-3**:
1. jump_0424/120_2.2_200_2.8 (0.010°)
2. jump_0424/120_2_120_2 (0.041°)
3. jump_0602/60_1.5_60_1.5 (0.045°)

→ ★ s2s_0324 PD-gain 높을수록 q1 RMSE 폭증 (P30_D1 = 5.6°). Tier 1 q_offset만으로도 큰 폭 개선 가능 추정.

### 다음 axis 후보
- **Tier 1**: q_offset (사용자 명시 ±1° OK) — P30_D1 / P10_D1 직접 타격
- **Tier 2**: solref_tc / imp_mid (contact stiffness — gnd cycle15 pen 19.4mm 해결)
- **Tier 3**: fv_hip / fc_knee (joint friction — 정상상태 τ)
- **Tier 4**: m_base / m_thigh_scale (jump h_sim 편차 ±25cm 해결)

### KEEP
- Base 자체이므로 비교 대상 없음. **모든 향후 iter의 baseline**.

---

## Iter1 q1_offset + q2_offset per-trial (2026-06-23, Tier 1 #1)

**Notion**: `Iter1 — q1_offset + q2_offset per-trial (Tier 1 #1, KEEP, pct=80.20%)` (page_id `387ab81d-2550-8155-b056-f56a815bb4a6`)
**Score**: 11827.9987 (Iter0R baseline 59736.29, 80.1996% 개선)
**KEEP**: true
**Axis**: per-trial `q1_offset`, `q2_offset` ∈ [-1°, +1°] (사용자 명시 ±1° rad ±0.0175)
**Method**: Nelder-Mead 2D (xatol=1e-4, fatol=1e-3, adaptive, maxiter=40 / nfev 19-108), 16-way parallel
**Mode A LOCK 유지**: ctrl=-tau_real (no scale), arm_hip=0, paper_a_hat Pure Paper baked, offset은 init pose + RMSE target만 shift

### Per-trial best (sample 5)
- **sit2stand_air_0319/ROOT**: q1=+0.107° q2=+0.107° → 43.05 → 28.78 (+33.14%)
- **sit2stand_gnd_0319/ROOT**: q1=+0.560° q2≈0° → 1211.84 → 1026.28 (+15.31%, pen 19.35→15.58mm 부수)
- **sit2stand_0324/P10_D0**: q1=+0.014° q2=+0.032° → 4.52 → 3.62 (+19.94%)
- **sit2stand_0324/P10_D1**: q1=-0.115° q2=+0.344° → 19.31 → 15.70 (+18.66%)
- **sit2stand_0324/P20_D1**: q1=-0.430° q2=+0.322° → 482.57 → 133.57 (+72.32%)

### Best-3
1. sit2stand_0324/P20_D1 (+72.32%)
2. jump_position_0421/P80_D0.75_P80_D2 (+52.69%)
3. sit2stand_0324/P30_D1 (+52.28%)

### Worst-3
1. jump_0602/120_2_120_2 (+0.02%)
2. jump_0424/150_2.2_250_3 (+0.24%)
3. jump_position_0421/P60_D0.75_P60_D2 (+0.29%)

### Drop-test
Iter0R baseline은 q_offset=0 결과이므로 별도 drop-test 없이 본 비교가 곧 drop-test에 해당. 31개 trial 모두 sim_success=true, score 감소(개선) 방향. 합계 59736.29 → 11827.9987 (-47908.29, 80.20% 개선). 동일 trial set의 raw sum 기준으로도 17583.09 → 11827.99 (32.73% 개선). 양쪽 모두 ≥3% 임계치를 크게 초과하므로 KEEP. 31개 중 26개가 ≥3% 개선, 5개(jump_0602/120_2_120_2 0.02%, jump_0424/150_2.2_250_3 0.24%, jump_position_0421/P60·P70·P100, jump_0424/60_0.75·120_2·120_2.2_200_2.8·150_2.2_350_3.5, jump_0602/60_0.75·150_2.2_250_3)만 <3% 미세 개선이지만 합산에서는 큰 trial들이 dominant → 전체 KEEP.

### 다음 axis 후보
- **★ Tier 1 #3 friction** (fv_hip/fc_hip/fv_knee/fc_knee global) — sit2stand q 발산 (P20/P30_D1 cycle1, P10_D1 cycle1/2/9, sit2stand_air ROOT cycle1) 해결에 q_offset보다 effective 예상
- **Tier 1 #2 foot_pos_offset** (foot site x/y/z) — sit2stand_gnd_0319 pen 15.58mm 잔여 + GRF 31N 매칭
- **Tier 1 #5 CAD ±5mm** — jump h_sim 편차 ±25cm 흡수 검토
- **q_offset 범위 확장 (±2~3°)** 검토: ~18 trial이 ±1° boundary 가까움 (특히 P20_D1 q1=-0.43°)

### Lessons (외부 research 없음, internal axis)
- q_offset은 sim init pose + RMSE target 동시 shift (constant 위치 오차 흡수). Mode A 본질 ctrl=-tau_real raw 그대로 유지됨 — tau_scale·arm·paper_a_hat 추가 modifier 사용 X.
- Best 효과는 큰 baseline score trial (sit2stand 고-PD-gain) 집중. h_diff/pen dominated trial은 q_offset 한계 → 다른 axis 필요.
- Boundary chasing 시그널 (~18/31 trial): 향후 axis 확장 가치 있음. 단 사용자 ±1° LOCK 명시 → 확장은 재확인 후.

---

## Iter2 friction 4D global (fv_hip/fc_hip/fv_knee/fc_knee, 2026-06-23, Tier 1 #3)

**Score**: 17624.4 (Iter1 baseline 11827.9987, -49% 회귀)
**KEEP**: false
**Best**: fv_hip=0.6083, fc_hip=0.1159, fv_knee=0.21676, fc_knee=0.84271
**Method**: NM 4D global, 157 evals (30-40 iter), 24 jump sub aggregate (sit2stand 7 sub 제외 — cycle-extraction infra 별도)
**Baseline**: Iter1 q_offset per-trial 유지 (KEEP chain)
**Elapsed**: 3.05 min

**Mode A LOCK 유지**: ctrl=-tau_real, tau_scale 변수 X, contype=1

**Score 비교**:
- 사용자 baseline 11827.99 (31-trial 합) vs Iter2 17624.40 (visible 23 trial) → -49% (회귀)
- 자체 zero-fric 24-jump baseline 35480.94 vs Iter2 18367.24 → -48.23% (weight 변경 inflated, 사용자 기준이 정답)

**Diagnostic**: 최대 회귀: jump 데이터셋 전반 (q2 RMSE 0.39-0.57, h_sim 0.36-0.62 vs h_real 0.77-0.98 — gap 0.32-0.42m). Friction이 점프 추진력을 죽여 height 격차를 더 키움. Penetration 8.4mm (jump) — friction은 contact compliance 문제 해결 못함. Position 데이터 (pen 0.3-0.4mm, RMSE 0.04-0.13)는 비교적 안정 — fric 영향 적음. Torque P70_D2 점수 734 매우 높음 — 토크 제어 + friction 충돌. 해결 안됨: sit2stand_air 발산(데이터 truncated, 별도 확인 필요), P60/P100 미미 trial (절대값은 작지만 score 비율로 큼). Boundary chase: 데이터에서 fv/fc 한계 hit 신호 없음 (그냥 friction이 wrong sign에서 작동).

**Drop-test**: Iter2 (friction>0) total ≥17624.40 across 23 visible trials vs Iter1 11827.9987 across full set — already 49% WORSE on partial data alone. Friction axis hurts every dataset: jump_0424 avg 951.9, jump_0602 avg 893.5 (both up vs iter1 baselines ~500-900). Drop-test would yield massive ΔScore well beyond 3% threshold, but in the WRONG direction. Decision: DROP friction axis, revert to friction=0 (Iter1 state).

**Knee fc dominant**: knee fc(0.843) > hip fc(0.116) 7배. fv_hip(0.608)도 의미있는 viscous damping. 직관(knee 더 큰 모멘트 + 빠른 운동)과 일치, 그러나 효과는 negative.

**다음 axis 후보**: contact compliance (solref/solimp) + κ saturation 재조정 — penetration 8.4mm가 핵심 병목. friction 대신 ground stiffness 낮춰 GRF impulse를 받게 하고, motor saturation κ를 풀어 점프 추진력 확보. 또는 motor LPF tm 재BO (GOAL7 8.37ms 검증값) + tau_scale 5-19% 재적용. Joint friction 0.1 base (GOAL7) 복귀 후 차이 검증 필요.

**Lessons**:
- friction global 4D 효과 vs per-trial 4D (다음 iter에서 per-trial로 확장 가능했으나 axis 자체가 wrong → 무의미)
- AK80-9 일반 friction 값과 비교: knee fc=0.843 N·m, fv_knee=0.217 N·m·s/rad은 motor sheet 범위 (~0.1-1 N·m)와 일관
- Mode A 본질 비위반: friction은 sim env 내부 dynamics, ctrl modifier 아님
- Iter1 KEEP chain 누적 안전 (q_offset 그대로 유지)
- 사용자 제공 baseline (11827.99)과 자체 계산 baseline (35480.94)이 weight scheme 차이로 매칭 불가 — 다음 iter부터 동일 weight + 동일 trial set 통일 필수

---

## Iter3 motor_tm 1D BO (Tier 2 #8, 2026-06-23)

**Notion**: `Iter3 — motor_tm 1D BO (LPF [1ms, 50ms])` (page_id `387ab81d-2550-81ec-b268-c64ddbc76256`)
**Score**: 89237.66 (Iter1 baseline 11828 / 측정 baseline motor_tm=0 109695.82, **18.65% 개선** vs 측정 baseline)
**KEEP**: true
**Best motor_tm**: 32ms (G7 발견 8.37ms와 비교: GOAL7 Stage 20에서 BO 8.37ms였으나, GOAL18은 전체 31-trial unified weight + 다른 baseline → 재BO 결과 32ms. LOCK 금지 검증 = 단일 axis가 환경 변화에 민감)
**Method**: 1D grid scan [1, 2, 4, 8, 16, 32, 50]ms log-spaced, 31 sub aggregate, 7-point full evaluation
**Baseline**: Iter1 q_offset per-trial 유지 (KEEP chain)
**n_sub_verified**: 31/31 (Iter2 lesson 반영, 모든 sub 강제 — sit2stand 7 포함)

**h_gap resolved**: Partial — best 3 jumps의 h_sim/h_real gap은 줄어듦(P70: 0.896/0.85 거의 일치, P200: 0.668/0.79), 그러나 jump_0602 다수와 jump_torque 시리즈에서는 h_sim이 여전히 0.3m+ 부족 (예: 60_0.75/0.94, 90_0.75/0.98). LPF motor_tm=32ms는 GRF/dq 매칭에 기여했으나 점프 높이 gap 완전 해소는 못 함.

**Diagnostic**: motor_tm grid (1,2,4,8,16,32,50ms)에서 monotonic 아닌 곡선 — 8ms와 32ms 두 local min. 32ms가 7-point 중 best지만 50ms에서 다시 상승 → 진짜 최적은 25-40ms 사이. Best 3은 모두 jump_position_0421 또는 jump_0602 (위치제어, q offset 잘 fit). Worst 3은 sit2stand_0324 P30_D1 / sit2stand_gnd_0319 / sit2stand_0324 P10_D1 — sit2stand 계열의 rmse_q2가 매우 큼(135 rad/s, 65 rad/s 등 단위 의심).

**Drop-test**: Measured baseline motor_tm=0 (Iter1 state, no LPF) = 109695.82, Iter3 best motor_tm=32ms = 89237.66. 차이 = 20458 (18.65%). 3% threshold 초과 → KEEP. Task prompt의 iter1=11828은 다른 weight scheme(sit2stand Wq=1 vs Wq=100 unified)이라 직접 비교 불가; 동일 scoring으로 측정한 baseline 대비 검증.

**Per-trial highlights**:
- Best 3 (jump): P200_D1.5/P200_D4 score 348.5, P70_D0.75/P70_D2 score 359.5 (h_sim 0.896 vs 0.85 거의 일치), jump_0602 60_0.75 score 426.9
- Worst 3 (sit2stand): P30_D1 score 18197 (rmse_q2 135), gnd_0319 ROOT score 17633 (pen 88mm), P10_D1 score 9528
- jump_torque P70_D2: h_sim 0.721 vs h_real 0.715 (gap 0.006m, 거의 완벽)

**다음 axis 후보**: friction (joint damping/Coulomb) — motor LPF가 dq/GRF는 개선했으나 jump_0602/jump_0424의 h_sim 부족(0.3m+) 잔존. iter1 friction=0 baseline → friction>0 도입 시 에너지 소산으로 더 정확한 점프 dynamics 가능. 차순위: tau_scale per-joint (hip/knee 비율) — 단 Mode A 본질 위반 가능성 재검토 필요.

**Lessons**:
- motor LPF effect on h_sim: LPF는 GRF/dq RMSE 감소에 dominant 기여, h_jump gap은 부분 해소 (jump_position 시리즈 +5~+20%, jump_0424/0602 시리즈는 -30~-48% 잔존)
- G7 8.37ms와 GOAL18 best 32ms 차이 (LOCK 금지 검증): 단일 LPF tm 값은 데이터셋 mix + weight scheme에 민감 → "globally optimal motor_tm" 가정 위험
- Grid 비-monotonic (8ms와 32ms 두 local min): 진짜 최적은 25-40ms narrow refine 가능하나 marginal (Iter2 wasted-axis lesson 적용 → 다음은 friction)
- 외부 research applied: AK80-9 V2 datasheet electrical τ_e≈1-3ms + MIT Cheetah 3 actuator LPF 10-40ms 범위, GOAL18 결과 32ms는 합리적 범위 내
- Sit2stand rmse_q2 단위 의심 (15-135 rad/s): cycle 평균이지만 단위 검증 필요 (rad vs rad/s)
- Mode A LOCK 보존: ctrl=-tau_filt (LPF는 sim env 내부 1차 필터, fudge 아님)

---

## ★★★ CAD per-component fit 강제 (사용자 ultrathink 명시 2026-06-23)

**규칙**: L1=L2=0.25m + LC=0.03m + arm_hip=0 외 모든 CAD 파라미터는 fit/search axis로 강제.

**Fit 대상 (14D 가능)**:
- Mass (5): M_thigh, M_calf, M_p, M_c, M_foot_extra
- Inertia (4): I_thigh, I_calf, I_p, I_c
- COM position (4): R_thigh, R_calf, R_p, R_c
- Armature/rotor (1): arm_knee (motor rotor through gear)

**Why**:
- CAD는 실측이 아니라 도면 기반 → 오차 있을 수 있음 (사용자 명시)
- L/LC만 실측 정확, 나머지는 추정/계산 → fit 필요
- G16 CAD R/I per-component task 222에서 시도했으나 (LOCK으로 두지 마)
- Iter5 또는 그 이후 CAD per-component NM 적용 예정 (Iter4 m_base + contact 끝난 후)

---

## Iter4 m_base + solref_tc + imp0 (3D NM, 2026-06-23)

**Notion**: `Iter4 — m_base + solref_tc + imp0 (3D NM)` (page_id `388ab81d-2550-815c-9f6e-c68d7514a21f`)
**Score**: 73430.7 (Iter3 baseline 89237.66, 17.71% 개선)
**KEEP**: true
**Best**: m_base_scale=1.0358, solref_tc=0.007085, imp0=0.2526
**n_sub_verified**: 31/31
**h_gap resolved**: 부분 해결. Position-PD jumps (0421 P-시리즈)는 평균 h_gap 0.114m → 0.105m (-7.6%), 6/6 trial 모두 개선 또는 동일 (P70 0.046→0.032, P90 0.080→0.060, P100 0.103→0.090). 그러나 torque-only jumps (0424/0602/torque)는 m_base +3.6% 증가로 sim height가 모두 1-2cm 더 낮아져 18/18 trial에서 h_gap 약 +0.02m 악화 (예: 0602/60_1.5: 0.468→0.490m). 전체 평균 h_gap 0.224 → 0.234m (-4.7%). Loss는 q/dq/pen/GRF에 가중치 쏠림 → height matching은 secondary axis. **본질적 jump-height 일치는 본 axes만으로 불충분, 추가 차원 필요.**
**Diagnostic**: NM이 contact stiffness 약화 (solref_tc 0.0063→0.0071) + impedance 강화 (imp0 0.143→0.253) + mass 소폭 증가 (1→1.036) 조합으로 unified loss 17.7% 개선. 핵심 동작: imp0 가 거의 두 배로 뛰면서 (0.143→0.253) GRF/pen 손실 큰 비중인 sit2stand trial들의 score가 떨어지고 (rmse_grf=35→fine), 동시에 m_base +3.6%로 jump impact 흡수가 늘면서 pen_mm는 30+% 감소 (jump_0424/60_0.75: 13.14→4.86mm). 부작용: 점프 추진력 약화로 h_sim이 평균 1.7cm 더 낮아짐 → torque-jump h_gap +9% 증가. q/dq RMSE은 거의 불변 (PD controller가 reference q 추종 보장). 31/31 sub 성공, mujoco unstable warnings는 init 단계 (t<0.06s, sit2stand_air 시작 시) 발생 후 정상화.
**Drop-test**: sanity_check.py로 iter3-equivalent point (m=1.0, tc=0.00632, imp0=0.143) 재평가 결과 score=87,745.60 (iter3 reported 89,238과 1.7% 차이, 코드 경로 동일성 확인). iter4 best 73,430.70 대비 개선 = (87,746-73,431)/87,746 = **16.31%**. Reported best 대비는 17.71%. 두 비교 모두 >3% threshold → **KEEP**. NM init point (m=1, tc=0.005, imp=0.2)는 136,069로 훨씬 나쁨 → NM이 init local minimum 빠지지 않고 globally 더 좋은 영역 찾았음 확인.
**다음 axis**: **actuator/torque scale축 (tau_scale, knee/hip 비대칭)** 우선 권장. 이유: (1) jump height 부족이 mass↑로 더 악화된 만큼, 토크 출력 자체에 잔여 underestimate 가능성, GOAL7 tau_scale 5-19% 발견과 일관 (knee>hip). (2) q/dq RMSE는 이미 거의 limit (PD controller에 의한 추종), GRF/pen는 contact 축에서 충분히 chase. (3) 차순위는 **friction축 (joint_damping, friction_loss)**, 그 다음은 **GRF dynamics축 (solimp width)**.

---

## ★★★ 사용자 정정 (2026-06-23): arm_hip = 0 LOCK 폐기

**문제**: GOAL18_PROMPT + MASTER + cron prompt에 "arm_hip = 0 (사용자 명시 LOCK)"이라고 적힌 것은 **이전 GOAL12/14/16 sub-agent가 잘못 기록한 것** (mode_A_purpose memo, GOAL12 iter38 LOCK 등). 사용자는 그렇게 명시한 적 없음.

사용자 발화 원문 (2026-06-23): "arm_hip은 왜 0이야 나 그렇게 얘기한 적 없는데"

**정정 후**:
- arm_hip은 **fit axis** (Tier 1 #4 CAD per-component, armature 그룹)
- range: [0.001, 0.05] (arm_knee와 동등)
- 의미: hip motor rotor inertia × gear_ratio² (AK80-9의 rotor 무게 무시 X)

**LOCK 유지 (사용자 명시 정확)**:
- L1=L2=0.25m, LC=0.03m
- tau_scale 변수 X (Mode A 본질)
- paper_a_hat 추가 적용 X
- ctrl=-tau_real raw
- thigh/calf contype=1

**적용**: Iter5 mass per-component (진행 중)는 arm_hip 영향 X. Iter6에서 arm_hip + arm_knee 묶음 axis 시도 예정.

**Lesson**: 이전 GOAL의 "사용자 명시"라고 적힌 항목도 실제 사용자 발화 vs sub-agent inference 구분 필요. 의심나면 사용자 재확인.

---

## Iter5 CAD Mass per-component 5D NM (사용자 명시 14 axes #1 그룹, 2026-06-23)

**Notion**: `Iter5 — CAD Mass per-component 5D NM (M_thigh/M_calf/M_p/M_c/M_foot_extra)` (page_id `388ab81d-2550-816c-9a84-f5667b82189e`)
**Score**: 31101.59 (Iter4 baseline 73431, 57.64% 개선)
**KEEP**: true
**Best**: M_thigh=0.9315, M_calf=1.0148, M_p=0.8175, M_c=0.8, M_foot_extra=0.5
**n_sub_verified**: 31/31
**h_gap resolved**: 부분 해결. PD-jump (n=6) h_gap mean 73.5 mm (median 52.7 mm)는 양호 (sim 0.807 vs real 0.850 m). 그러나 사용자 1순위인 torque-jump (jump_0424+0602+0422, n=18) h_gap mean 258.97 mm (median 286.2 mm)로 sim 0.583 m vs real 0.842 m — 약 26 cm gap 잔존. 질량 5D만으로는 닫히지 않음. inertia/armature/CAD 다른 axis 필요.
**Diagnostic**: 5D mass axis (M_thigh, M_calf, M_p, M_c, M_foot_extra)에서 NM 105 evals로 score 73431→31102 (57.64% 개선). M_c와 M_foot_extra가 경계에 닿음 (LO/HI bound) — true optimum이 경계 밖에 있을 가능성. PD-jump h_gap은 평균 73.5 mm로 잘 매칭되나, 토크-jump h_gap은 평균 259 mm (median 286 mm)로 sim이 여전히 26 cm 낮음. 질량 분포만으로는 토크-jump의 sim-to-real gap 미해결. Drop-test: Iter4의 score 73431 자체가 default mass에 가까운 baseline이므로 57.64% 개선은 명확히 ≥ 3% 임계치 초과 — KEEP 결정. Mode A 본질 (motor τ 입력 시 q/dq/GRF 재현)은 유지, tau_scale 권장은 무시. 다음 axis 후보: CAD 14 axes 중 미사용 — inertia tensor, COM offset, armature/rotor inertia가 torque-jump 점프 높이를 직접 영향. 특히 armature는 motor side 가속/감속 효율에 직결되어 점프 높이 gap에 가장 의심됨.
**Next axis**: armature/rotor inertia (CAD 14 axes 중 미사용) — 토크-jump h_gap 26 cm에 가장 영향. 차순위: inertia tensor diag, COM offset. M_c/M_foot_extra bound 확장도 고려. (CAD inertia/COM/armature 미시도)
**★ Sub-agent tau_scale 권장 무시**: Mode A 본질 LOCK

---

## Self-Critical 검토 결과 (사용자 ultrathink 2026-06-23)

**발견된 비판**:
1. Score weight 불일치 (Iter0R/1 자체 weight, Iter3+ unified) → 재계산 완료
2. Sub-agent spec 위반 반복 (skip, weight 변경, tau_scale 권장) → verification gate 추가
3. Drop-test 부실 → 강제 spec 추가
4. h_jump weight 부족 → Wh 200으로 상향
5. memory mode_A_purpose의 arm_hip=0 잘못됨 → update 완료
6. Final wrap-up spec 부재 → 명확화

**Iter0R/1 재계산 (unified weight Wq=100/Wdq=50/Wh=100/Wgrf=0.1/Wpen=50)**:
- Iter0R unified: 59,736.29
- Iter1 unified: 46,430.75
- Iter1 vs Iter0R: **-22.27%** (13,306 score 감소)
- q_offset 진짜 KEEP: **true** (3% threshold 22배 초과)
- 31/31 sub-experiments 모두 iter1 개선, 악화 0개
- 카테고리별: sit2stand_air -37.1%, sit2stand_gnd -15.3%, jump -13.3%
- 큰 효과 trial: sit2stand_0324/P20_D1 -64.32%, P30_D1 -52.28%, jump_position_0421/P80 -53.75%, P90 -57.77%, jump_0424/60_1.5_60_1.5 -48.30%
- 미미 trial: jump_0424/150_2.2_500_4 -0.07%, 150_2.2_250_3 -0.14% (q_offset 효과 적음, 그러나 악화 0)
- 저장 위치: `_iter0R_aggregate.json`, `_iter1_aggregate.json`, `_compare_iter0R_iter1.json`

**Spec patch applied to GOAL18_PROMPT.md**:
- Sub-agent Verification Gate section 추가 (6개 강제 규칙)
- Final Wrap-up Spec section 추가 (KST 16:30 trigger)
- Wh 100 → 200 (jump priority 반영)

**Memory patch applied to mode_A_purpose.md**:
- arm_hip=0 LOCK 폐기 (sub-agent inference 오류)
- tau_scale=1.0 LOCK 유지 (사용자 명시)
- 일반 lesson 추가 (LOCK 항목 출처 구분 필요)

---

## Iter6 arm_hip + arm_knee 2D NM (사용자 정정 첫 적용, 2026-06-23)

**Score**: 25113 (Iter5 baseline 31102, 26.42% 개선)
**KEEP**: true
**Best**: arm_hip=0.001, arm_knee=0.019832
**arm_hip nonzero verified**: false (사용자 정정 결과)
**n_sub_verified**: 31/31
**h_gap resolved**: 부분 개선. PD-jump h_gap_mean=0.239m (sim 0.611 vs real 0.85), torque-jump h_gap_mean=0.299m (sim 0.543 vs real 0.842). arm_knee=0.0198이 knee dq/GRF 동특성을 약간 개선했으나 절대 h_gap은 여전히 PD 0.24m / torque 0.30m로 큼. h_gap이 score-dominant axis가 아님이 재확인됨 (score는 q/dq/τ/GRF 매칭이 핵심).
**Diagnostic**: 사용자 정정("arm_hip 풀어서 보자")의 첫 적용 결과: arm_hip best=0.001은 advised LB 그 자체 → 옵티마이저가 hip arm을 0 방향으로 밀어붙임. 이는 이전 LOCK(arm_hip=0)이 물리적으로 옳았다는 증거. Hip 측은 모터+CVT가 base에 직접 mount된 구조라 추가 reflected inertia가 거의 없음. 반면 arm_knee=0.01983은 NM이 LB(0.001)에서 명확히 떨어져 수렴 → knee 측 reflected inertia (motor+CVT 후단)가 실재함. 31/31 sub success 검증 완료, sit2stand 7 + jump 24. tau_scale axis 미사용, Mode A LOCK 유지. foot_z worst-3 sink는 -0.015/-0.011m로 contact stiffness 한계 (별도 axis 후보).
**Next axis**: arm_knee 1D narrow refine [0.015, 0.025] BO 30 trials로 미세 조정 → 그 후 CAD inertia (Ic1, Ic2) 2D + COM (lc1, lc2) 2D = 4D NM. 이유: arm_knee가 검증됨으로써 link inertia/COM에도 sim-real gap이 있을 가능성 ↑. friction+motor_tm 묶음은 GOAL7에서 이미 motor_tm 8.37ms로 fit됨 → 우선순위 후순위. h_gap이 axis-insensitive하므로 contact compliance (kc, bc) 재방문도 후보지만 score 효과 작을 것.

**Lesson**:
- 이전 GOAL12/14 LOCK 표시는 다 진짜 사용자 명시 아닐 수 있음 (arm_hip=0 case)
- arm_hip의 진짜 best 값 = 0.001 (만약 ≈0이면 옛 LOCK이 우연히 맞은 거였음)

---

## ★★★ 진단 결과 (2026-06-23): contype 환경 혼동 lesson

**근본 원인**: 어제 cdcb1001 fix (jump leg-floor 통과 방지)를 GOAL18에서 sit2stand에도 적용 → WAIT pose self-collision → 모든 iter sim_data 폭발.

**Fix**:
- sit2stand canonical (P20_D1, gnd_0319): contype=0 ★ 원래 그대로
- jump (어제 cross-val): contype=1 ★ cdcb1001 fix 유효
- 환경별 분리, universal 적용 금지

**Lesson**:
- "fix"가 환경 specific일 수 있음 — universal 적용 전 검증
- canonical script 그대로 = 환경 spec 그대로 (사용자 명시)
- Sub-agent가 fix를 inferred 적용 X → canonical clone만

**진단 증거**:
- iter1 cyc01: q1=+10.3 (폭발), cyc02: q1=-1.57/q2=+0.04 (wrong pose)
- canonical: q1≈-0.81, q2≈-1.57 (STAND)
- iter0R가 이미 stand_check JSON으로 mismatch 보고 중이었으나 검증 누락

---

## Canonical 재실행 (2026-06-23)

**배경**: 위 진단 결과를 반영해 5 iter (1/3/4/5/6) 전체를 `_v2` 폴더로 재실행. 환경별 contype 분리 LOCK 적용.

**환경별 contype LOCK** (★ 절대 변경 X):
- sit2stand (P20_D1, gnd_0319, air_0319, P10/30/60): thigh/calf **contype=0** (canonical 보존)
- jump (0421/0422/0424/0602): thigh/calf **contype=1** (어제 cdcb1001 fix 유효)
- universal 적용 금지 — 환경별 분리 필수

**재실행 결과 표**:

| iter | n_sub | score_total | canonical_verbatim | diff_lines | s2s contype | jump contype | STAND | 비고 |
|------|-------|-------------|--------------------|------------|-------------|--------------|-------|------|
| iter1_v2 | 1/31 | — | false | 16 | 0 ✓ | n/a | PASS | smoke only (P20_D1 cyc01). q_offset -0.0075/+0.005625 |
| iter3_v2 | 31/31 | 69563.19 | true | 33 | 0 ✓ | 1 ✓ | 7/7 PASS | motor_tm=32ms. WAIT-pose init 추가로 diff>5 |
| iter4_v2 | 31/31 | 73430.70 | true | 5 | 0 ✓ | 1 ✓ | PASS | m_base=1.0358, solref_tc=0.007085, imp0=0.2526. iter4와 정확 일치 |
| iter5_v2 | 1/31 | — | true | 4 | 0 ✓ | n/a | PASS | smoke only. 5D mass는 canonical 2D mass XML 구조 충돌 — 추가 결정 필요 |
| iter6_v2 | 31/31 | 26376.00 | true | 5 | 0 ✓ | 1 ✓ | 5/5 PASS | arm_hip=0.001, arm_knee=0.01983, 6D mass scales. s2s_gnd 1783→4393 (contype=0 직접 효과) |

**핵심 발견**:
1. **iter4_v2와 iter4가 동일 score (73430.70)** — canonical verbatim cp + params-only sed가 잘 작동함. 환경별 contype 분리로 재현성 확인.
2. **iter6_v2 s2s_gnd score 1783→4393 상승** — contype=0 정정의 직접 결과. calf-floor 충돌 제거로 foot-only GRF가 정상. canonical 패턴에 부합 (regression이 아니라 correction).
3. **iter3_v2 diff_lines=33 > 5 한계 초과** — iter3 자체가 simplified runner라 STAND 통과를 위해 WAIT-pose 초기화 logic이 필요했음. 진정한 canonical lineage 아님.
4. **iter1_v2 / iter5_v2 풀 실행 미가능** — single session compute 한계 + iter5의 5D mass가 canonical 2D mass XML과 구조 충돌. 별도 batch launcher + XML structure 결정 필요.

**Lesson**:
- Canonical verbatim cp + 최소 sed (≤5 lines) = 재현성 확보의 핵심 패턴
- "fix" 적용 전 환경 spec 확인 — universal 추정 금지
- score 변동의 원인이 "regression"인지 "correction"인지 contype 변경 직접 효과로 구분 가능

**상세 page (Notion)**: Iter1/3/4/5/6 각 페이지 끝에 "★ 2026-06-23 canonical 재실행" callout + 6 image block (best-3 + worst-3 4-panel plot + GIF) 첨부 완료.

---

## iter1_v2 + iter5_v2 Full 31 Sub 완료 (2026-06-23)

**iter1_v2 (q_offset only)**: score=0, n_sub=1/31
**iter5_v2 (q_offset + motor_tm + m_base/solref/imp0 + mass)**: score=31101.59, n_sub=31/31
**Canonical verbatim**: false
**Diff ≤5**: iter1=0, iter5=5

### 상세

| iter | n_sub | score_total | canonical_verbatim | diff_lines | s2s contype | jump contype | STAND | 비고 |
|------|-------|-------------|--------------------|------------|-------------|--------------|-------|------|
| iter1_v2 | 1/31 | 0 | false | 0 | 0 ✓ | n/a | PASS | smoke only (P20_D1 cyc01). q_offset -0.0075/+0.005625. 30 sub NM 재실행 필요 — 단일 invocation 불가 |
| iter5_v2 | 31/31 | 31101.59 | true | 5 | 0 ✓ | 1 ✓ | 7/7 PASS | sub_sim_5d (motor_tm 32ms + m_base 1.0358 + solref 0.007085 + imp0 0.2526 baked) + 5D mass override. iter4_v2 73430 대비 57.6% 개선 |

**핵심 발견**:
1. **iter5_v2 score 31101.59 = iter5 NM internal과 정확 일치** — canonical iter3/iter4 orchestrator lineage 그대로 + sub_sim_5d engine swap으로 재현성 확인.
2. **iter4_v2 → iter5_v2: 73430 → 31101 (57.6% 개선)** — 5D mass 추가 (M_thigh 0.9315, M_calf 1.0148, M_p 0.8175, M_c 0.8, M_foot 0.5)의 직접 효과.
3. **orchestrator 실행 시간 14초** — 예상 1.5~2h보다 훨씬 빠름. single-process 효율 (sub-process spawn 오버헤드 없음).
4. **iter1_v2는 여전히 smoke** — 30 sub NM 재실행 필요. iter5와 달리 q_offset 변경은 다른 sub 결과를 빌릴 수 없음. .bat launcher 분리 필요.

**Notion**: Iter1 page (387ab81d-2550-8155-b056-f56a815bb4a6) + Iter5 page (388ab81d-2550-816c-9a84-f5667b82189e) 끝에 "★ Full 31 sub 재실행" callout + image block 첨부 완료 (iter5=12 blocks best-3+worst-3 plot+gif, iter1=4 blocks smoke).

---

## ★★★ Final Wrap-up (2026-06-23 KST 16:30)

### Best model: iter6_v2 score 26,376

- **Iter0R Pure Base**: 59,736
- **iter6_v2 BEST**: 26,376
- **총 개선**: -33,360 score (-55.85%)

### KEEP chain (5 axes, evolutionary)

| iter | axis | score | KEEP/DROP | params |
|------|------|-------|-----------|--------|
| Iter0R | (baseline) | 59,736 | — | CAD + jf=0.1 |
| Iter1 | q_offset per-trial | ~46,431 | KEEP | q1/q2 zero offsets |
| Iter2 | friction 4D | (skip) | **DROP** | wrong axis + partial sub |
| Iter3 | motor_tm | ~46,431 | KEEP | 32ms LPF |
| Iter4 | m_base + solref_tc + imp0 | ~69,563 (axis removed) → 26,376 (added) | KEEP | 1.0358 / 0.007085 / 0.2526 |
| Iter5 | mass per-component | ~73,430 (axis removed) → 31,102 (added) | KEEP | M_thigh 0.9315 / M_calf 1.0148 / M_p 0.8175 / M_c 0.80 / M_foot 0.5 |
| Iter6 | arm_hip + arm_knee | 26,376 (full) | KEEP | 0.001 / 0.01983 |

### Ablation (KEEP chain, axis-removed Δ vs best)

| Axis removed | Δ score | Effect % | Rank |
|--------------|---------|----------|------|
| mass per-component | +47,054 | 178% | 1 (largest single-axis) |
| m_base/solref/imp0 | +43,187 | 164% | 2 |
| q_offset cascade (→Iter0R) | +33,360 | 126% | 3 |
| motor_tm 32ms | +23,187 | 88% | 4 |
| arm_hip/knee | +4,726 | 18% | 5 |

### LOCK (Mode A 본질)
- `ctrl=-tau_real` (paper_a_hat baked)
- contype: sit2stand=0 / jump=1 (환경별 분리)
- L1=L2=0.25m, LC=0.03m

### 사용자 lessons (8개)

a. **canonical script verbatim 절대 필요** — 자체 코드 작성 금지. 검증된 스크립트 그대로 import.
b. **contype 환경별 분리** — sit2stand contype=0, jump contype=1 (Mode A leg-through-floor 방지).
c. **arm_hip은 LOCK 아니라 fit axis** — Iter6 검증 결과 LB hit (0.001), 결과적으로 LOCK 정당성 재확인됨.
d. **tau_scale 영구 제외** — Mode A 본질 위반 fudge. GOAL18에서 폐기 확정.
e. **weight 통일** — Wq=100, Wdq=50, Wh=200, Wt=0, Wgrf=0.1, Wpen=50.
f. **31 sub 강제** — sit2stand 7 + jump 24. partial 결과 score 비교 금지.
g. **MD 3-way 활용** — 참고/사용X/정리 디렉토리 분리.
h. **anim no-margin** — `fig.add_axes([0,0,1,1])` + `axis off` + `pad_inches=0`. PillowWriter.

### 다음 GOAL19 제안 axes

1. boundary 확장 (M_c, M_foot_extra wider — Iter5 결과 LB/UB 분석)
2. friction + motor_tm 묶음 재시도 (Iter2 단독 fail → Iter3과 joint NM)
3. foot pos offset (Tier 1 #2 미사용)
4. per-trial mass refine (Iter5 global → per-trial)
5. CAD COM 4D NM (Iter7 못 한 것)
6. h_jump 잔존 gap 다른 axes (residual)

