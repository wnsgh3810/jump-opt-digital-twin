# GOAL16 — 다양한 방법론 + 새 axis pool로 GOAL15 plateau 탈출

> **시작**: 2026-06-21 ~17:50 KST
> **종료**: **2026-06-22 12:00 KST** (~18.3h 자율, cron 3e000a7f + Windows GOAL16_Alarm) — ★ 사용자 2h 연장 (06-22 04:xx)
> **모드**: Mode A 단일 (★ tau_scale=1.0 + paper_a_hat LOCK)
> **데이터**: 15 trial (`0424_*` 9 + `0602_*` 6)
> **Baseline**: **GOAL15 Iter2 = 160.79** (W_GRF=0.2)
> **목표**: GOAL15 plateau 탈출 + 새 axis pool 검증 + methodology 다각화

ultrathink — 매 iter 깊이 사고, plateau 깰 새로운 각도 찾기.

---

## ★ 한 줄 미션

GOAL15 (6 method 모두 160-162 plateau)에서 못 본 **새 axis pool** + **methodology shift** 적용. CAD R/I per-component / sensor bias / actuator low-pass 재검토 / Multi-objective Pareto / LOTO / MJX diff sim 등 **8+ 방법론** 시도. 사용자 강조 q/dq/h 매칭 우선 (W_GRF=0.2 유지).

---

## ★★★ 위반 절대 X (8가지, GOAL12-15 누적)

1. `tau_scale` 적용 (Mode A 위반)
2. Plot 색 명시
3. ★ Anim MuJoCo 아닌 방식 (matplotlib.animation 절대 X, mujoco.Renderer만)
4. `h_sim` displacement (base_z.max() absolute 사용)
5. Notion 영어 (한국어만)
6. Locked Template skip
7. ★ Iter42 overfit (boundary push, m_calf 0.15-0.20)
8. ★ GOAL14 Iter22 41 BV (boundary-degenerate)

---

## ★ 8 strict 매 페이지

1. Notion 한국어 / 2. 색 X (`l1.get_color()`) / 3. 2-way plot (Real solid + sim dashed) / 4. ★ Anim MuJoCo Renderer (`azim=135 elev=-15 dist=1.2` + malgun 24pt overlay) / 5. `h_sim` absolute (`base_z.max()`) / 6. **Mode A `tau_scale_h = tau_scale_k = 1.0` LOCK** / 7. Flight phase PD hold X / 8. Locked Template 22 sections + image verify 30/30 (15 plot + 15 anim)

---

## ★ Lock 정책 (GOAL12-15 누적 lessons)

- **Mode A LOCK**: `tau_scale=1.0`, `paper_a_hat` 변경 절대 X
- **CAD link length LOCK** (L1_VAL, L2_VAL, LC_VAL — 실측 정확, GOAL13 확인)
- **arm_hip LOCK = 0** (GOAL14 Iter29 boundary chase 확인)
- **Foot cylinder 42×13mm y-axis LOCK** (사용자 명시)
- **tau_delay = 0** (GOAL14 Iter2 단조증가 확인)
- **W_GRF=0.2 strict** (q/dq/h 1순위)
- **Boundary guardrail 20% + BV ≤10** 매 iter 점검

★ **CAD R/I (R1/R2/RC/RP/I1/I2/IC/IP) 는 부정확 가능** (사용자 명시) — GOAL13 Iter1 α-scale (isotropic)은 DROP했지만 **per-component independent refit은 fresh axis** (Iter1-3).

---

## ★ 진행 전략 — base-up + method 다각화

### Step 0: Baseline 재확인
- GOAL15 Iter2 best params + W_GRF=0.2 → 15 trial baseline 재측정
- per-trial 표 + worst-3 식별 (전 chain 기준 0424_120_2.2_200_2.8 worst)
- KEEP threshold: **156.0** (160.79 × 0.97)

### Iter chain (axis 1개씩, method 1개씩, 매 iter 다른 method)

**Group A — CAD R/I per-component refit** (★ GOAL13 Iter1 α-scale isotropic 한계 극복)
- **Iter1: R per-component refit** (R1/R2/RC/RP 4-param **독립** ±10%)
  - Method: scipy.optimize.**least_squares** (linear-in-param manipulator regressor)
  - Reference: Khalil-Dombre 2002 ch5, Atkeson-An-Hollerbach 1986
- **Iter2: I per-component refit** (I1/I2/IC/IP 4-param ±15%)
  - Method: scipy least_squares (R fixed) + EKF cross-check
- **Iter3: R+I joint TLS** (8-param)
  - Method: Total Least Squares (q̈ noisy 고려, Savitzky-Golay smoothing)

**Group B — Sensor side**
- **Iter4: per-trial encoder bias** (q1_init, q2_init offset ±0.5°)
  - Method: per-trial 2D NM
  - 가설: 실 robot encoder zero 오차 → q RMSE 직접 영향
- **Iter5: dq filter delay narrow** (real robot 미분 noise filter latency ±5ms)
  - Method: 1D scipy curve_fit (sim dq vs real dq cross-correlation)

**Group C — Motor side (Mode A 호환)**
- **Iter6: actuator low-pass τ_motor 재검토**
  - GOAL9 P5에서 8.37ms KEEP → GOAL10에서 DROP → 15 trial + W_GRF=0.2 환경 재검토
  - Method: 1D scipy Powell, narrow [5ms, 15ms]
- **Iter7 (조건부): backlash dead-zone** (GOAL13 lookahead pool)
  - Method: scipy curve_fit per-joint, threshold q̇ < 0.05 rad/s

**Group D — Methodology shift**
- **Iter8: Multi-objective explicit Pareto** (★ NSGA-II 3-obj: |Δh|, RMSE_q, RMSE_dq)
  - pymoo NSGA-II, pop=80, n_gen=40
  - Pareto frontier 시각화 + 최적 trade-off knee point 선정
  - 사용자가 trade-off 명시적 선택 가능
- **Iter9: LOTO 15-fold cross-validation** (★ GOAL15 Iter6 미실행 이월)
  - sklearn LeaveOneOut, 14 trial fit + 1 trial test × 15회
  - overfit 진단: gap/train > 0.5 = overfit
  - 결과: best model 일반화 능력 정량
- **Iter10: per-segment weighted score**
  - 점수 함수 재설계: stance/lift-off/flight/landing 별 RMSE 가중치 다름
  - W_stance × RMSE_stance + W_flight × RMSE_flight + ...
  - 각 phase 별 best fit 강조 가능

**Group E — Score reformulation**
- **Iter11 (조건부): robust score** (max instead of sum, worst-trial 강조)
  - 또는 median + IQR (outlier-resistant)
- **Iter12 (조건부): per-trial normalized score**
  - 각 trial 별 baseline 대비 ratio

**Group F — Methodology research 시도**
- **Iter13 (조건부, 시간 여유 시): MJX differentiable simulation**
  - JAX + MJX 인프라 구축 (~3-4h)
  - gradient-based 12D fit → local minimum 탈출 가능성
  - Reference: arxiv 2604.10351 (Trajectory-based actuator ID)
- **Iter14 (조건부): PySR symbolic regression**
  - 데이터에서 friction / inertia 형태 자동 발견
- **Iter15 (조건부): GP regression residual**
  - GaussianProcessRegressor sklearn으로 actuator residual (small data 적합)

---

## ★ Method diversity 매 iter (TPE 회피)

- Iter1: scipy least_squares (LSQ)
- Iter2: LSQ + EKF
- Iter3: TLS
- Iter4: NM
- Iter5: scipy curve_fit
- Iter6: scipy Powell
- Iter7: scipy curve_fit
- Iter8: pymoo NSGA-II 3-obj
- Iter9: sklearn LeaveOneOut
- Iter10: NM with custom score
- Iter11-12: robust statistics
- Iter13: JAX/MJX gradient
- Iter14: PySR
- Iter15: GP regression

**같은 method 2 iter 연속 사용 X**.

---

## ★ Boundary guardrail (Iter42 + Iter22 lessons)

- **best param이 bound +20% 이내 → axis 폐기** (Iter42 overfit 재발 X)
- **BV ≤ 10** strict (Iter22 41 BV 재발 X)
- score 통과 but BV >10 → DROP

---

## ★ Locked Template 22 sections (한국어 매 페이지)

Status / 학습 목표 / 기본 모델 / 변경 axis / 물리 의미 / 외부 근거 ≥3 URLs (매 iter WebSearch 새 논문) / **60+axis Base vs Current 표** / MuJoCo 용어 / **방법 비교표** / BO 결과 / **15 trial RMSE 표** / ★ **점프 높이 15 표** / **GRF + pen 표 (W_GRF=0.2 명시)** / ★ **4-panel plot 15 (2-way 색 X)** / ★ **MuJoCo Renderer anim 15** (80f 60ms malgun overlay) / 해석 / 자연 판단 / 인사이트 / 다음 후보 / 코드 토글 / 외부 참조 / footer. **verify 30/30** (file_uploads uploaded).

---

## ★ Cycle 매 iter

1. **MD read** (특히 §Method Pool + GOAL15 Final + 이전 iter 결과)
2. **15 trial 약점 진단** (worst-3 trial phase 분해)
3. **External research** WebSearch ≥ 2-3 URLs **매 iter 새 논문/repo**
4. **Hypothesize + method 선언** (TPE 회피, 매 iter 다른 method)
5. **코드 작성** `goal16/iterN/run_iN.py`
6. **15-trial measure** (W_GRF=0.2 score)
7. **자연 판단** (KEEP threshold + boundary guardrail + physical plausibility)
8. **4-panel plot 15 + MuJoCo Renderer anim 15**
9. **Notion page** (`notion_locked_template.py` → `build_iter_page`) + image verify 30/30
10. **MD section append** (한국어 자세히) + git commit (HEREDOC + Co-Authored-By: Claude Opus 4.7)

---

## ★ Reference (strict import, 재작성 X)

- Mode A: `goal9/phase0/run_baseline.py`
- paper_a_hat: `goal9/phase0/load_26_04_24.py` L13-19
- 15 trial loader: `goal12/data_loaders/load_combined_15trial.py`
- gen_plots 색 X 2-way: `goal14/iter32/gen_plots_i32.py`
- ★ gen_anim MuJoCo Renderer: `goal9/phase0/gen_anim.py`
- Notion module: `goal12/notion_locked_template.py`
- GOAL15 Iter2 best XML: `goal15/iter2/`
- GOAL12 Iter38 best XML: `goal12/iter38/`
- GOAL14 Iter32 best XML: `goal14/iter32/` (12D synergy 구조)

---

## ★ MD 정책 (사용자: "이전 했던 md 재활용해서 이번 버전 md 만들자")

- **단일 통합 MD 유지**: `MASTER_INSIGHTS_G9.md` 계속 사용 (현재 9000+ lines, GOAL9~15 모든 chain 누적)
- **GOAL16 section append** (한국어 자세히 매 iter)
- **bidirectional**: 이전 GOAL12-15 lessons read + 새 발견 append
- ★ 이전 MD 재활용 필수 section: §Method Diversity Pool / §GOAL15 Final Conclusion / §Lock 정책 / §Iter42 overfit / §Iter22 BV / §m_calf 7.9% over 발견 / §양 GOAL 비교 등

---

## ★ Notion infra

- Token: `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`
- CONCEPT parent: `115ab81d255080fdaae6f28f55e3e205`
- **GOAL16 parent**: 새로 생성 (Step 0 / Iter1 시작 시), ID는 MD GOAL16 section top에 기록
- 참조 (cross-link): 
  - GOAL15 parent `383ab81d-2550-8198-8688-e93cd90271fd`
  - GOAL12 Iter38 페이지 `381ab81d25508114ac97d9bfbbe98410`
  - GOAL14 Iter32 페이지 `383ab81d2550810397e3e63796c760b4`
  - 비교 페이지 `383ab81d255081f4994cf2fa7fc5b1a7`

---

## ★ 디렉토리

- `goal16/step0/` (baseline 재측정)
- `goal16/iter1/`, `iter2/`, ...
- 각 iter: `run_iN.py` + `iterN_metrics.json` + `plots/` + `anim/` + `notion_page_id.txt`

---

## ★ Sub-agent (sonnet) 활용

- 단순 작업 (BO 실행, plot/anim 생성, Notion API call) 위임 OK
- 메인 = 자율 결정 + critical review + commit
- ★ **.bat 더블클릭 의존 X** (사용자 자율 모드, 모든 단계 `python` 직접 실행)

---

## ★ Cron / Alarm / Checkpoint

- 6h cron checkpoint `c62a2b13` 유지 (계속 fire)
- **16h stop cron `81a0693b`** (2026-06-22 10:00 KST)
- **Windows `GOAL16_Alarm`** 10:00 KST popup
- **Final wrap-up phase 09:00 KST 시작** (1h buffer for Final Conclusion + GOAL17_PROMPT draft + Notion final + commit)

---

## ★ 시간 분배 (16.3h)

- Step 0 baseline: 30min
- **Iter1-3 (CAD R/I refit Group A)**: 각 1-2h = ~5h ★ priority
- Iter4-5 (Sensor): 각 1h = 2h
- Iter6-7 (Motor): 각 1h = 2h
- **Iter8 (NSGA-II 3-obj Pareto)**: 2h ★
- **Iter9 (LOTO 15-fold)**: 2-3h ★
- Iter10 (per-segment weighted): 1-2h
- Iter13+ (MJX 등 시간 여유 시)
- Final wrap-up: 1h (09:00-10:00)

---

## ★ 핵심 목표

**GOAL15 Iter2 (160.79) 를 다양한 fresh axis + methodology로 추월**:
- 목표 1: best score < 156 (3% KEEP)
- 목표 2: per-trial uniform 일치율 향상 (15 trial 모두 |Δh| < 3 cm 시도)
- 목표 3: 일반화 검증 (LOTO Iter9)
- 목표 4: Pareto frontier 명시화 (Iter8) — 사용자 trade-off 선택
- ★ Mode A LOCK + boundary guardrail + 8 strict 절대 유지

---

## ★ 사용자 directive 준수

- "다양한 방법론 여러 가지 진행" → axis pool A-F + method diversity 매번 다름
- "이전 MD 재활용" → MASTER_INSIGHTS_G9.md 계속 사용 (단일 통합)
- "한국 시간 오전 10시까지" → 2026-06-22 10:00 KST stop
- ultrathink → 매 iter 깊이 사고, plateau 깨는 새 각도 발견 우선

ultrathink로 16.3h 자율. 매 iter 다른 method, 외부 research continuous, MD bidirectional, Notion 자세히. GOAL15 plateau 탈출 = 본 미션. Iter42/Iter22 overfit/BV 절대 재발 X.
