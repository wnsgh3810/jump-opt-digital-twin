# GOAL14 — Fresh Methodology 도입 (Iter38 베이스 위, GOAL13 8-axis Exhaustion 이후)

> **시작일**: 사용자 결정 후 (즉시 자율 시작 X)
> **모드**: Mode A 단일 (★ tau_scale=1.0 + paper_a_hat LOCK — GOAL13 전체에서 변경 無)
> **데이터**: GOAL12/13과 동일 15 trial (`0424_*` 9 + `0602_*` 6)
> **출발점**: GOAL12 Iter38 (score 176.41, |Δh| avg 4.36 cm, pen 2.05 mm)
> **전임자**: GOAL13 Iter1–8 모두 DROP (8개 orthogonal physical axes 소진)
> **목표**: Iter38의 강력한 local minimum 너머 — 모델 구조 자체 또는 데이터 기반 접근 교체

---

## ★ 한 줄 미션

GOAL12 Iter38 베이스 위에서 **기존 parameter-tweak 방식의 한계를 인정하고**, 데이터 보강 / 미분가능 시뮬레이션 / 다목적 Pareto 최적화 중 사용자가 선택한 방향으로 fresh methodology를 도입한다.

---

## ★★★ GOAL12–13 핵심 교훈 (다음 GOAL 시작 전 필독)

### GOAL12 교훈 (7 항목)
1. **Iter42 overfit (128.57) 폐기** — m_calf_scale 7/15 trial 0.15–0.46 (CAD 50–85% 감소, 물리 불가). ALL-TIME score였으나 boundary chasing으로 확인 후 즉시 폐기. → Iter38 (176.41) 채택.
2. **boundary distance > 20% guardrail** — 어떤 파라미터도 search boundary 20% 이내 수렴 시 즉시 DROP. boundary push = overfitting 조기신호.
3. **m_calf_scale per-trial LOCK** — Iter38 per-trial 값 고정. mass-inertia double-counting 방지. 실 robot calf 복합체 (M2+M_C ≈ 0.893 kg) 저울 실측 아직 미완.
4. **Mode A LOCK 효력 입증** — Iter42 과적합이 Mode A에 번지지 않음. code-level score_mode_a() 호출 차단 필수.
5. **method 다양성** — Optuna CMA-ES / scipy LSQ / EKF / NN residual / Sobol 모두 시도. 단일 sampler 의존 금지.
6. **0602 저kd group 약점** — worst Δh 8.82–8.97 cm (0602_60_1.5, 0602_90). PD gain 의존성 = 시스템 ID 한계.
7. **추적성 유지** — 매 iter git commit + Notion KEEP/DROP 명시 필수.

### GOAL13 교훈 (8 항목 = GOAL12 7 + 신규 1)
8. **★★ 8-axis Exhaustion** — 8개 orthogonal physical axes 모두 DROP:
   - Iter1 (CAD r/I): alpha ≈ 1.0, CAD 이미 정확 → DROP
   - Iter2 (Stribeck): fs_excess→0, 경계 push → DROP_BOUNDARY
   - Iter3 (NN residual): val/train=15.1>1.5, cross-dataset overfit → DROP_OVERFIT
   - Iter4 (flex K+D): K=0 최적, 추가 stiffness 단조 악화 → DROP_AXIS_REJECTED
   - Iter5 (joint stiction): dfc→0, frictionloss 이미 충분 → DROP_BOUNDARY_PUSH
   - Iter6 (range limit): settle q2=2.548 > any upper limit, 구조적 불호환 → DROP_INCOMPATIBLE
   - Iter7 (torsional elasticity): k_t→5000(upper), b_t→0.01(lower), AK80-9 effectively rigid → DROP_RIGID_LIMIT
   - Iter8 (DC gain): g_h=g_k=1.0 정확히, Kt calibration 이미 정확 → DROP_UNITY_OPTIMAL
   
   → **Iter38이 현재 모델 구조에서 absolute local minimum 확정**

---

## ★★★ 8 strict 절대 준수 (GOAL9–13 일관 유지)

1. **한국어** — 모든 Notion 페이지, 보고, 주석 한국어
2. **색 X** — matplotlib 색 명시 금지, auto cycle 사용. sim/real 매칭은 get_color()
3. **2-way 검증** — 매 iter KEEP/DROP 전 train-set / val-set 2중 확인
4. **MuJoCo Renderer** — 애니메이션은 mujoco.Renderer만 사용 (기타 방식 절대 X)
5. **h_sim absolute** — CoM 절대 높이 max 사용 (displacement 아님)
6. **Mode A LOCK** — tau_scale=1.0, paper_a_hat Pure Paper sgn(v) only, 절대 변경 X
7. **★★ (GOAL12 신규) Iter42 overfit 금지** — boundary distance > 20% guardrail 절대 강제
8. **★★★ (GOAL13 신규) axis exhaustion parsimony** — 8개 axes 모두 DROP 확정. 새로운 physics axis 추가 전 "이 axis가 Iter1–8과 진정 독립적인가?" 반드시 자문

---

## ★★★ 위반 history (절대 반복 X)

1. tau_scale 적용 (Mode A 위반) — GOAL10 fix
2. Plot 색 명시 (사용자 "색 X" 명시) — 3회 위반 fix
3. Anim MuJoCo가 아닌 다른 방식 사용 — 3회 위반 fix
4. h_sim displacement 사용 (사용자 absolute 명시) — fix
5. Notion 페이지 영어 작성 (사용자 한글 명시) — fix
6. Locked Template 일부 skip — fix
7. ★★ Iter42 overfit (128.57) 폐기 — m_calf boundary chasing, 물리 불가
8. ★★★ axis exhaustion without parsimony check — GOAL13 Iter1–8 소진으로 발견

---

## ★ GOAL14 후보 방향 (3개, ranked)

### Rank 1 — 데이터 보강 (Data Augmentation via PD 다양화)
**미션**: 현재 15 trial (0424 × 9 + 0602 × 6)에 PD gain 조합을 다양화한 신규 실험 데이터를 추가 수집 → 0602 저kd group 약점 (Δh 8.82–8.97 cm) 해소

**근거**:
- Iter38 local minimum이 강력한 이유 중 하나: 0602 저kd group (60_0.75, 60_1.5, 90_0.75)이 0424 그룹과 systematic bias를 가짐 (동일 PD이지만 점프 높이 5–10 cm 차이). 이 bias를 모델 파라미터로 흡수 시 0424 group 과적합 발생.
- 더 많은 PD 조합 (중간 kd 값: 1.0, 1.75 등) 추가 시 parameter landscape 자체가 변화 → 새 local minimum 발견 가능.
- 모델 구조 변경 없이 데이터 품질 개선 — parsimony 원칙 완전 보존.

**전제조건**: 실 robot 가용 + 추가 실험 세션 (2–3시간)

**선행작업**:
- 실 robot calf 복합체 (M2+M_C ≈ 0.893 kg) 저울 실측 (오래 deferred)
- 신규 PD 세트 결정 (예: 60_1.0_60_1.0 / 120_1.5_150_2.0 / 90_1.75_90_1.75)
- 기존 data_loader에 신규 trial 추가

**참고 논문**:
- arxiv 2604.10351 (Differentiable Simulation, data augmentation 섹션)
- arxiv 2504.20313 (multi-trial ID convergence)

---

### Rank 2 — 방법론 전환: Trajectory-based Differentiable Simulation
**미션**: MJX (MuJoCo JAX backend) + gradient-based system identification. 현재 BO/CMA-ES의 zero-order 최적화를 gradient-based 1st-order로 교체 → 더 나은 local minimum 탈출 가능성

**근거**:
- GOAL9–13 전체에서 zero-order (CMA-ES/TPE/Nelder-Mead/DE) 사용. Gradient signal 없으므로 flat landscape (Iter38 근방)에서 탈출 어려움.
- MJX는 `jax.grad`로 ∂score/∂param 계산 가능 → L-BFGS-B 또는 Adam으로 정밀 descent.
- arxiv 2604.10351 (Shi et al. 2026) — trajectory-matching 미분 시뮬레이션으로 sim-to-real gap 2× 감소 보고. 참조 코드: MJX + optax.

**전제조건**:
- MJX 설치 및 현재 GOAL12 sim과 호환 확인 (GOAL5R에서 partial 성공)
- contact dynamics의 미분가능성 한계 이해 (contact event에서 gradient explosion)
- 연속 접촉 구간 (flight phase X)에서만 gradient 사용 권장

**참고 논문**:
- arxiv 2604.10351 — Trajectory-level differentiable sim, MJX 기반
- arxiv 2410.16591 — Differentiable contact dynamics, gradient smoothing
- arxiv 2509.06342 — Sim-to-real via gradient-based ID
- IEEE 9846110 — MuJoCo MJX benchmark

---

### Rank 3 — 다목적 Pareto 최적화 (Multi-objective: |Δh|, GRF, pen 3-obj frontier)
**미션**: 단일 weighted score → (|Δh|, GRF_dev, pen) 3-목적 Pareto frontier explicit. NSGA-III / pymoo로 trade-off 시각화 후 사용자가 knee point 선택

**근거**:
- 현재 score = weighted sum (W_h=50, W_grf=1, W_pen=10). 가중치 선택이 임의적 → 다른 가중치에서 다른 local minimum 존재 가능.
- Pareto frontier를 명시적으로 그리면 "h 매칭을 1 cm 희생하면 GRF 20% 개선" 등 trade-off 가시화.
- NSGA-III (3-objective) + pymoo: pop=50, gen=100이면 ~5000 evals, 현재 BO보다 가벼움.
- arxiv 2504.20313 — multi-objective ID Pareto frontier 실험 로봇 적용.

**전제조건**:
- pymoo 설치 (`pip install pymoo`)
- 3-objective score function 분리 구현 (현재 weighted sum 해체)
- Pareto knee point 선택 기준 사전 정의 (예: ε-constraint method)

---

## ★ 사용자 결정 필요 사항

GOAL14는 자율 시작 X — 아래 3가지 결정 후 시작:

| 번호 | 결정 사항 | 선택지 |
|------|-----------|--------|
| 1 | **방향 선택** | (a) 데이터 보강 / (b) 미분 시뮬레이션 / (c) Pareto / 복합 |
| 2 | **데이터 추가 여부** | 즉시 실험 가능 vs. 기존 15 trial만 사용 |
| 3 | **robot transfer 검토** | 현재 디지털 트윈 완성도로 실 robot 제어 시도 가능한지 판단 |

---

## ★ Locked 파라미터 (GOAL14에서도 변경 X)

| 파라미터 | 값 | 근거 |
|---|---|---|
| tau_scale_h, tau_scale_k | 1.0 | Mode A LOCK, GOAL9 이후 불변 |
| paper_a_hat formula | Pure Paper sgn(v) only | CF 식별성 회복 (26.05.20), 변경 X |
| m_calf_scale (per-trial) | Iter38 값 | 실측 deferred, entanglement 방지 |
| A_HAT | [0, 1.15605, 4.174e-4, 0.26856, 0.04904] | UMich 정밀모델 baking |
| KT, GR, CF | 0.091, 9.0, 0.59 | AK80-9 V2 spec 확정 |

---

## ★ Iter38 베이스라인 (불변 참조점)

| 항목 | 값 |
|---|---|
| score | 176.41 |
| avg \|Δh\| | 4.36 cm |
| max pen | 2.05 mm |
| pass (< 3 cm) | 4/15 (26.7%) |
| worst trial | 0602_60_1.5 (8.97 cm), 0602_90 (8.82 cm) |
| commit | beffded4 (공식 best) |

---

## ★ 외부 논문 5편 (GOAL13 final 조사)

| # | arxiv/DOI | 제목 요약 | GOAL14 관련성 |
|---|---|---|---|
| 1 | arxiv 2604.10351 | Trajectory-level differentiable sim (MJX), sim-to-real 2× | Rank 2 핵심 기반 |
| 2 | arxiv 2410.16591 | Differentiable contact dynamics, gradient smoothing | Rank 2 contact gradient 안정화 |
| 3 | arxiv 2509.06342 | Gradient-based sim-to-real ID, real robot 적용 | Rank 2 robot transfer |
| 4 | arxiv 2504.20313 | Multi-trial ID, Pareto frontier 실험 | Rank 1/3 공통 |
| 5 | IEEE 9846110 | MuJoCo MJX benchmark, JAX 가속 실측 | Rank 2 MJX 성능 |

---

## ★ Cron / Alarm Setup (사용자 결정 시)

- GOAL13까지 cron 45edffe7 (6h checkpoint) 유지됨
- GOAL14 시작 시 새 cron ID 설정 필요
- 자율 시작 조건: **사용자 명시적 "시작" 지시 후**

---

ultrathink — 각 axis 시도 시 "GOAL13 Iter1–8과 진정 독립적인가?" 자문 후 진행.
boundary guardrail 20% 절대 유지. Mode A LOCK. parsimony first.
