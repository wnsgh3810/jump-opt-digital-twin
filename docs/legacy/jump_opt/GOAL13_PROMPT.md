# GOAL13 — Mode A Digital Twin 4-axis Refine (post-Iter38, parsimony-first)

> **시작일**: 2026-06-17 (사용자 결정: 즉시 시작, calf 실측 deferred)
> **종료**: 시간 제한 없음 (자율 진행, 사용자 interrupt 시 종료)
> **모드**: Mode A 단일 (★ tau_scale=1.0 + paper_a_hat LOCK)
> **데이터**: GOAL12와 동일 15 trial (`0424_*` 9 + `0602_*` 6)
> **출발점**: GOAL12 Iter38 (score 176.41, |Δh| avg 4.36 cm, pen 2.05 mm)
> **목표**: parsimony 보존하며 worst-3 trial (0602 저kd group) Δh 8.8 cm 해소

---

## ★ Section A — calf 실측 deferred (사용자 결정 2026-06-17)

**사용자 명시**: "측정은 못할거 같애 시간은 오래 걸려도 돼" → calf 복합체 실측 deferred, GOAL13 즉시 시작.

### m_calf lock 정책 (★ 절대 준수, mass-inertia entanglement 방지)

- **Iter1 (CAD r/I LSQ) 진행 시**: `m_calf_scale` per-trial 값을 **Iter38 best 값으로 고정** (변경 X). r/I refit이 mass 오차를 다시 흡수하는 double-counting 방지.
- **이후 모든 iter**: m_calf는 lock 유지 (mass가 아닌 axis만 변경)
- **만약 GOAL13 Iter1-4 후 0602 저kd group Δh > 5 cm 잔존**: 실측이 필요한 신호 → fallback으로 사용자에게 measurement 요청

### Iter38 per-trial m_calf_scale (baseline, 변경 X)

`C:/Users/junho/Desktop/jump_opt/goal12/iter38/iter38_metrics.json` 의 per_trial[*].m_calf_scale 값을 그대로 사용.
- 0424 그룹 avg ≈ 0.93, 0602 그룹 avg ≈ 0.92
- (Iter42의 극단값 0.15-0.20은 OVERFIT 폐기 — 절대 사용 X)

ultrathink — 매 iter 끝까지 깊이 사고. boundary chase 발견 즉시 axis 폐기.

---

## ★ 한 줄 미션

GOAL12 Iter38 baseline 위에 **4개의 fresh axis** (CAD r/I LSQ → flex Mode B-only → Stribeck native MuJoCo → NN residual MJX-check) 를 base-up 방식으로 1개씩 시도. parsimony·boundary guardrail·Mode A LOCK 절대 유지. Iter42 overfit 재발 방지.

---

## ★★★ 위반 history (GOAL12까지의 6 + GOAL12 신규 추가, 절대 반복 X)

1. ★ tau_scale 적용 (Mode A 위반) — GOAL10 fix
2. ★ Plot 색 명시 (사용자 "색 X" 명시) — 3회 위반 fix
3. ★ **Anim MuJoCo가 아닌 다른 방식 사용** (사용자 "어제 계속 빠뜨림" 강조) — 3회 위반, 절대 X
4. ★ h_sim displacement 사용 (사용자 absolute 명시) — fix
5. ★ Notion 페이지 영어 작성 (사용자 한글 명시) — fix
6. ★ Locked Template 일부 skip — fix
7. ★★ **(GOAL12 신규) Iter42 overfit 폐기** — score 128.57 ALL-TIME best였으나 m_calf_scale이 7/15 trial에서 0.15-0.46 (CAD 50-85% 감소, 물리 불가) 하한 boundary push. 폐기 확정 commit c8bdd6c1. **→ GOAL13에서 boundary distance > 20% guardrail 절대 강제**

---

## ★ 8 strict 절대 준수 (GOAL12 그대로 + Mode A LOCK 강화)

### 매 sub-agent 작업 시작 시 반드시 read

- `C:/Users/junho/Desktop/jump_opt/GOAL13_PROMPT.md` (이 파일)
- `C:/Users/junho/Desktop/jump_opt/MASTER_INSIGHTS_G9.md` (GOAL10/11/12 누적 발견)

### 8가지 strict (불변)

1. **★ Notion 페이지 한글 작성** (axis name/단위/paper title만 영어 OK)
2. **★ Plot 색 명시 절대 X** (matplotlib auto color cycle만, `l1.get_color()` 패턴)
3. **★ Plot 2-way only** (Real solid + sim dashed. 비교 라인 추가 X)
4. **★★★ Anim MuJoCo Renderer 강제** (matplotlib animation 절대 X, 사용자 3회 강조!)
5. **★ h_sim absolute** (`base_z.max()` ground=0 기준, init 빼지 X)
6. **★★ Mode A 본질 STRICT — tau_scale_h = tau_scale_k = 1.0 LOCK + paper_a_hat 불변** (★ GOAL13 추가: NN residual / flex 도입 시도 시 score_mode_a() 호출 금지를 코드 레벨에서 강제)
7. **★ Flight phase PD hold X** (자연 마찰/댐핑이 dissipate)
8. **★ Locked Template strict** (plot 15 + anim 15 + 60+ table + image verify 30/30)

### 추가 GOAL13 guardrail (★ Iter42 재발 방지)

- **boundary distance > 20%**: 모든 free param이 search range 양 끝 20% 안에 들어가면 axis 자동 reject
- **train/val ratio** 모니터: 0424 (9 trial = train) vs 0602 (6 trial = val) split score 차이 > 30% 발산 시 reject
- **per-trial fudge factor 폭증 금지**: 새 free param × 15 trial 형태 금지 (global single param 또는 group-shared만 허용)
- **physical feasibility**: 모든 axis 변경은 paper/CAD 근거 의무 (LMI, triangle inequality, sign convention)

---

## 📚 GOAL12 lessons learned (critique 추출 — ★ 매 iter 시작 시 재독)

1. **Iter42 ALL-TIME score 128.57 폐기 교훈** — m_calf_scale 7/15 trial 0.15-0.46 boundary push. parsimony 위배 + physical plausibility 붕괴 = score만 좋은 overfit. 모든 새 axis는 'boundary distance > 20%' guardrail 필수.

2. **KEEP chain (4→7→16→21→30→35→38) 가 6.24%/7분 유지 핵심**은 8 strict + Locked Template 22 sections 매 iter 점검. 자동화된 reject rule이 사용자 개입 없이 overfit 차단. GOAL13에서도 매 iter 22 section = 위반 시 KEEP 불가.

3. **Mode A LOCK 효력 입증** — Iter42 polution이 Mode A로 번지지 않은 것은 tau_scale=1.0 + paper_a_hat 불변 덕분. NN residual / flex 도입 시 score_mode_a() 호출 금지 코드 레벨 강제 필요.

4. **method 다양성 강제** — Iter38의 11D Optuna CMA-ES + warm start + sigma schedule(0.025→0.008)은 효과적이었지만 단일 알고리즘 의존은 BO TPE DB size limit (메모리 50GB) + boundary chasing 위험. GOAL13은 CMA-ES / NSGA-II / closed-form LSQ / scipy curve_fit 의무 rotate.

5. **flex 단순 재시도 무의미** — GOAL10 Iter20에서 -0.127% DROP. 재시도 정당화 = Mode B-only scope + 2-objective NSGA-II (Δh + GRF_dev trade-off) + K ≥ 5000 Nm/rad 제약처럼 method/scope 모두 새로워야.

6. **0602 저kd group은 mass refit 한계 도달** — worst Δh 8.82-8.97 cm (0602_90_0.75, 60_1.5_60_1.5). m_calf_scale=0.75 하한 + m_thigh=0.905 + fv_hip=1.05-1.23 maxed. take-off impulse 부족 + rmse_dq1≈0.8 = transmission elasticity 또는 stiction 미모델. → 다른 axis(CAD r/I 또는 Stribeck v_s) 필수.

7. **최고PD trial (0602_150_2.2_500_5) actuator-level 잔차** — rmse_dq1=1.509 (전체 최대) + Δh 3.45 cm + pen 2.013 mm. mass/friction axis로는 trade-off만. motor LPF tm 미스매치 또는 NN residual로만 잡힘.

8. **추적성**: 매 iter git commit + Notion page + KEEP/DROP 명시. Iter42 폐기를 추적 가능하게 만든 핵심. GOAL13에서도 commit 43fca9e6 (iter38) / c8bdd6c1 (iter42 폐기) 패턴 유지 = 회귀 시 즉시 roll-back.

---

## 🎲 데이터 (GOAL12 동일 + 사용자 결정 사항)

- **15 trial 기본**: 26.04.24 (9 trial `0424_*`) + 26.06.02 (6 trial `0602_*`)
- **`goal12/data_loaded_combined.npz` 재사용** (paper_a_hat 변환 완료)
- **★ 사용자 결정 필요** — 신규 trial (예: 26.06.16 이후 실험) 추가 여부. 추가 시 데이터 로더 확장 + Iter38 baseline 재검증 후 GOAL13 시작.

### ★ 사용자 prerequisite (시작 전 필수)

> **실 robot calf 복합체 mass 저울 측정** — Iter38 m_calf_scale avg ≈ 0.921 → CAD 대비 약 **7.9% (≈ 71 g) 과대 추정** 시사. M2 + M_C ≈ 0.893 kg (CAD 기준) 의 실측값 확인 필요. 측정값이 CAD와 크게 다르면 → CAD XML 우선 갱신 후 Iter38 baseline 재실행 (score 변화 확인) → GOAL13 시작.

---

## 📊 점수 함수 (GOAL10/12 동일, 변경 X)

```
score = Σ_trial [ W_q·RMSE(q1,q2) + W_dq·RMSE(dq1,dq2) + W_τ·RMSE(τ1,τ2)
                + W_h·|h_sim − h_real|       ← W_h=50 (1순위)
                + W_grf·max(0, GRF_dev − 0.25)²
                + W_pen·max(0, pen_max − 2)² ]
```

Weights: W_q=100, W_dq=3, W_τ=20, W_h=50, W_grf=1, W_pen=10.

★ 15 trial uniform 일치율 high — 단일 trial good + 나머지 worse 안 됨.

---

## 🔬 진행 전략 — base-up 다음 axis 1개씩

### Iteration cycle (★ GOAL12 cycle + boundary guardrail 추가)

1. **MD read** (GOAL13_PROMPT + MASTER_INSIGHTS_G9 GOAL12 sections 매 iter)
2. **GOAL12 Iter38 baseline 재검증** (calf 실측 반영 후 score 재측정 → 새 baseline 확정)
3. **★ WebSearch external research** (≥2-3 sources, 매 iter 다른 topic)
4. **Tier 1 axis 1개 선택 → 시도** (보수, single base param 또는 global)
5. **★ method rotate** (BO 만 X — CMA-ES / NSGA-II / scipy curve_fit / closed-form LSQ)
6. **Run** → 15-trial sim
7. **boundary check** (free param 20% 안 위반 시 즉시 reject)
8. **train/val (0424 vs 0602) split score** 확인 (>30% 발산 reject)
9. **Plot 15 + Anim 15** (★ 8 strict)
10. **자연 판단** (KEEP -1% 보수)
11. **MD evolve** + **Notion page** + **git commit**

### method 다양성 규칙 (★ Iter38 단일 의존 약점 보완)

- 4 axes에서 각각 다른 algorithm 사용 의무
- **CAD r/I → closed-form LSQ (scipy.linalg.lstsq + cond check)**
- **flex Mode B-only → NSGA-II 2-objective (Δh + GRF_dev Pareto)**
- **Stribeck native → scipy.optimize.curve_fit (per-joint 4-param)**
- **NN residual → JAX/MJX-check (autograd + small MLP)**
- BO/CMA-ES는 최후 fallback (≥5000 trial DB 시 OOM 위험)

---

## 🏆 Locked priority ranking (★ critique 4-5 axes, 절대 순서 유지)

| Rank | Axis | Method | Expected Δh | Risk |
|---|---|---|---|---|
| **1** | **CAD r/I closed-form regressor LS** (global single r_x, r_y, I_zz per link, mass LOCK) | scipy.linalg.lstsq + Savitzky-Golay q̈ + cond(Y)<1e8 + LMI check | 0.6 cm | regressor cond 폭주 / q̈ noise / mass-r coupling |
| **2** | **Mode B-only flex** (K_hip, K_knee, D_hip, D_knee 4 param, 15 trial 전체 NSGA-II) | NSGA-II 2-objective (Δh + GRF_dev) + K ≥ 5000 Nm/rad 제약 | ~0.4 cm | GOAL10 Iter20 -0.127% DROP — scope 변경 정당화 필수 |
| **3** | **Stribeck native MuJoCo** (`frictionloss`+`damping`+사후 Stribeck dip 합성) | scipy.optimize.curve_fit per-joint (fc,fs,fv,v_s) + 사후 dip 합성 (MJX 미사용) | 0.3 cm | GOAL10 Iter5 metric만 저장 (XML 미반영) 재현 위험 / mjcb_act_dyn 미사용 |
| **4** | **NN actuator residual** (Hwangbo 2019 style small MLP, Mode A 입력에만 적용) | JAX/Flax 2-layer MLP (residual_torque = MLP(q, q̇, τ_input)) + MJX-check | 0.2 cm | Mode A LOCK 깨질 위험 — score_mode_a() 호출 금지 코드 레벨 강제 |
| (B) | (fallback) per-trial fv 2D refit 재시도 (저kd group only) | scipy curve_fit per-group | 0.1 cm | GOAL11 T2 이미 시도 — 추가 개선 한계 |

### Tier 1 (axis 1, 2) — 우선 시도 / Tier 2 (axis 3, 4) — Tier 1 효과 확인 후

★ **Iter42 폐기 lesson** 적용: 매 axis 종료 시 boundary distance + train/val split + per-trial fudge factor 폭증 여부 점검. 위반 시 즉시 reject (KEEP 불가).

---

## 📋 매 페이지 Locked Template (★ 22 sections, GOAL12 동일)

1. Status callout (yellow_background, 🎯)
2. **🎓 학습 목표** (이 페이지 다 읽으면 무엇을 마스터)
3. **📖 기본 모델 상태** (Iter38 baseline + 이전 iter stack)
4. **🔬 이 iter 변경 axis** (★ 무엇 + 왜 + 어떻게)
5. **🧮 물리적 의미 / 수식**
6. **🌍 외부 근거** (paper/repo ≥3, URL + 한국어 인용 풀이)
7. **🆚 Full axis 비교 표 60+ rows** (Iter38 baseline vs Current)
8. **📖 MuJoCo / 모델 용어 정리**
9. **🔬 방법 비교 표** (사용 method + 비교)
10. **🏁 Optimization 결과** (★ boundary distance + train/val split 표)
11. **📊 per-trial RMSE 표 15 trial**
12. **★ 점프 높이 표 15 trial** (h_real abs / h_sim abs / |Δh| cm / < 3cm?)
13. **GRF band 25% + pen band 2 mm 표**
14. **★ 4-panel plot 15 trial** (q/dq/τ/GRF, Real solid + sim dashed, 색 X)
15. **★ anim 15 trial 전부** (★ MuJoCo Renderer 80f 60ms, malgun.ttf overlay)
16. 결과 해석 (5-8 bullets 한글)
17. 자연 판단 (★ boundary distance + train/val split 명시)
18. **💡 인사이트**
19. **🚀 다음 axis 후보**
20. 코드 토글
21. 외부 참조 + cross-link
22. divider + footer

### Verify 매번 (절대 skip X) — GOAL12 동일

- 모든 file_uploads status="uploaded" (30개)
- 페이지 image block count = **30** (15 plot + 15 anim)
- Iter38 baseline vs Current 표 존재 + 60+ rows
- 한글 작성 확인
- **★ boundary distance + train/val split 표 명시 (GOAL13 추가)**

---

## ⏰ Cron + Windows alarm (사용자 시작 trigger 시 setup)

- **CronCreate one-shot** "0 HH DD MM *" (사용자 결정 시간)
- **Windows schtasks** `GOAL13_Alarm` popup + sound
- **6h checkpoint cron** 재활용 (기존 c62a2b13 또는 신규)

---

## 🛠️ Reference 코드 (GOAL12 그대로 + Tier 1 신규)

- run_trial: `goal12/iter38/run_iter38.py` (Mode A MuJoCo, h_sim absolute)
- paper_a_hat: `goal9/phase0/load_26_04_24.py` L13-19 (Pure Paper sgn(v) only)
- gen_plots 패턴: `goal12/iter38/gen_plots_i38.py` (색 X, 2-way, l1.get_color())
- ★ gen_anim 패턴: `goal9/phase0/gen_anim.py` (★ MuJoCo Renderer 절대 강제)
- **★ 신규 Tier 1 / cad_ri_closed_form 코드 skeleton — research note 참조**
  (scipy.signal.savgol_filter + np.linalg.lstsq + cond(Y) + LMI feasibility)
- 26.06.02 데이터 로더: `goal12/data_loaders/load_combined.py`

---

## 📚 외부 research continuous (★ 매 iter)

- WebSearch / WebFetch ≥ 2-3 sources per iter
- 후보 sources:
  - **Atkeson-An-Hollerbach 1986** (Estimation of Inertial Parameters) — CAD r/I LSQ
  - **Khalil-Dombre 2002 Ch.5** — manipulator base parameters
  - **Gautier-Khalil 1992** — excitation / cond(Y)
  - **Wensing 2017 / Traversaro 2016** — LMI / manifold projection
  - **Armstrong-Hélouvry 1994 Survey** — Stribeck friction reference
  - **Hwangbo 2019 ANYmal** — actuator NN residual
  - **NSGA-II** (Deb 2002) — multi-objective Pareto
  - MuJoCo Menagerie (frictionloss/damping XML reference)
  - AK80-9 V2 spec (★ 사용자 robot)

---

## 🚦 자율 Loop (사용자 결정 시간, 예: ~22h)

### 종료 조건
1. 시간: 사용자 결정 (cron + Windows alarm)
2. 사용자 interrupt
3. Plateau (5 iter 연속 < 3% 개선)
4. **★ boundary push 발견 → 해당 axis 폐기 후 다음 axis로 이동** (Iter42 재발 방지)

### 6h checkpoint
- 매 6h 진행률 + score 변화 + boundary 점검 + MD commit + Notion verify + git commit

### 매 iter 종료 self-check

- [ ] MD read 확인 (GOAL13_PROMPT + MASTER_INSIGHTS_G9 GOAL12 sections)
- [ ] 외부 research ≥ 2-3 sources URL/인용
- [ ] Full axis 60+ rows table (Iter38 baseline vs Current)
- [ ] plot 15 trial 2-way 색 X
- [ ] anim 15 trial MuJoCo Renderer (matplotlib X)
- [ ] h_sim absolute 적용
- [ ] **tau_scale=1.0 + paper_a_hat LOCK 확인 (★ Mode A 본질)**
- [ ] Notion 한글 작성
- [ ] image verify 30/30
- [ ] **★ boundary distance > 20% guardrail 충족 확인**
- [ ] **★ train/val (0424 vs 0602) split score 차이 < 30% 확인**
- [ ] MD GOAL13 section append
- [ ] git commit

---

## 🚀 시작 trigger (★ 사용자 calf 실측 후)

### Step 0 (prerequisite, ★ 사용자 작업)
- **실 robot calf 복합체 mass 저울 측정** → 결과 알림
- (선택) 신규 trial 데이터 추가 여부 결정

### Step 1: 인프라
1. Notion GOAL13 parent page 생성 (CONCEPT 아래)
2. MASTER_INSIGHTS_G9.md `## GOAL13 — 4-axis Refine` section append
3. Cron one-shot (사용자 결정 시간)
4. Windows schtasks (사용자 결정 시간)

### Step 2: Baseline 재검증
1. calf 실측 반영 → CAD XML 갱신
2. Iter38 stack 그대로 → 15-trial sim 재실행 → 새 baseline score 확정
3. Notion page (baseline 재검증 결과 한글)

### Step 3+: Tier 1 axis 시도
1. **Iter G13-1: CAD r/I closed-form LSQ** (mass LOCK, scipy + Savitzky-Golay)
2. **Iter G13-2: Mode B-only flex NSGA-II** (Tier 1 효과 확인 후)
3. **Iter G13-3: Stribeck native MuJoCo** (Tier 1 효과 확인 후)
4. **Iter G13-4: NN actuator residual** (Tier 1/2 효과 확인 후)
5. Final stack consolidation + 사용자 보고

---

**Mission ready — 사용자 calf 실측 결과 대기.**
