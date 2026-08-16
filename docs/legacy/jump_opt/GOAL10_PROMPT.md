# GOAL10 — Mode A Digital Twin (Pure Mode A + Natural Friction Tuning)

## ★★★ 사용자 명시 절대 위반 금지 (반복 위반 후 강조)

### 위반 history (메인이 못 지킨 사항들)
1. ★ tau_scale 적용 (Mode A 위반) — fix됨
2. ★ Plot 색 명시 (사용자 명시 "색 X") — fix됨, **또 위반**
3. ★ Anim MuJoCo Renderer 아닌 다른 방식 — fix됨
4. ★ h_sim displacement (사용자 명시 absolute) — fix됨
5. ★ **Notion 페이지 영어 작성** (사용자 명시 한글) — **fix 진행**

### ★ 절대 strict (매번 매 페이지 확인)

1. **★ Notion 페이지는 한글로 작성** — 사용자 한국어. 영어 작성 X.
   - Section heading: 한글 (예: "학습 목표", "기본 모델 상태", "변경 axis 상세")
   - Bullet content: 한글 (영어 axis name + 단위는 OK, 예: "solref_tc (s)")
   - Caption: 한글 (예: "60_0.75_60_2 trial — Real (실선) vs Sim (점선)")
   - Code toggle 안의 코드: 영어 OK (코드 자체)
   - 외부 paper title: 영어 OK + 한국어 풀이 같이
   - 표 header: 한글 (예: "axis 이름", "단위", "의미")

2. **★ Plot 색 명시 절대 X** — matplotlib auto color cycle만
   - `color='red'`, `c='b'`, `cmap='viridis'` 등 모든 색 spec 금지
   - linewidth, linestyle만 차별 (Real solid, Sim dashed)

3. **★ Plot 2-way only** — Real (solid) + 그 phase sim (dashed) 만. P0/이전 phase 비교 라인 X.

4. **★ Anim MuJoCo Renderer 강제** — matplotlib animation X, pyglet X.

5. **★ h_sim absolute** — `base_z.max()`, init position 빼지 X.

6. **★ Mode A 본질** — tau_scale_h = tau_scale_k = 1.0 LOCK 절대 변경 X.

7. **★ Flight phase PD hold X**.

8. **★ Locked Template strict 매 페이지** — plot 9, anim 9, 60+ axis table, image verify, 압축 X.

★ 매 sub-agent task 시작 시 GOAL10_PROMPT.md 처음부터 read 필수. 위반 사항 발견 시 즉시 fix.

---


> **시작**: 2026-06-15 22:30 KST (사용자 명시 후)
> **종료**: **2026-06-16 12:00 KST** (~13.5시간 자율)
> **출발점**: GOAL9 발견 정보 (`MASTER_INSIGHTS_G9.md`) + Mode A 본질 STRICT 회복
> **Mission**: tau_scale 제거 (옵션 A) + 마찰/댐핑 narrow 차분히 적용 → 공중 회전 자연 정지 + h_jump 1순위 회복

---

## ⚠️ GOAL9와 다른 점 (사용자 명시 수정)

### 1. ★★★ Mode A 본질 STRICT (옵션 A) — 절대 변경 X
- `tau_scale_h = tau_scale_k = 1.0` **LOCK**
- `paper_a_hat(currentTorque)` 그대로 input
- sim ctrl = tau_real (no × scale)
- P6/P11 (tau_scale) **완전 제거**

### 2. 마찰/댐핑 차분히 적용 (Narrow refine)
- GOAL9 P4 wide range [0.001, 5.0]에서 winner damp=2.17 → h_jump 1순위 destroy
- GOAL10: **narrow refine** (예: damp_hip/knee ∈ [0.01, 0.5], fc/fv/fs도 small)
- 1순위 h_jump 보존하며 flight phase 공중 회전 자연 정지

### 3. PD hold 안 함 (사용자 명시 거부)
- Flight phase (t > T_motion): ctrl = [0, 0]
- 실 robot은 stance phase에서만 PD command (T_motion 까지)
- 공중 회전은 마찰/댐핑이 자연 dissipate (사용자 직관)

### 4. Locked Template STRICT (★ 사용자 강력 명시 반복)
**모든 페이지 매번 강제 포함** (절대 빠뜨림 X):
1. **plot 9 trial 4-panel** (q, dq, τ, GRF) — Real (solid) + sim (dashed) **2-way ONLY**
2. **anim 9 trial 전부** (★ 80f 60ms each, 9 anim per page)
3. **Full axis comparison table 60+ rows** (사용자 예시 형식)
4. **image verify 매번** (file_uploads status="uploaded" + page block count = 18)

### 5. ★ CAD parameter도 BO 대상 (사용자 명시 추가)
- mass/inertia/r/I 모두 narrow refine (±10-20%)
- 단 a_hat 5-param은 lock (Mode A 본질 + fudge 의심)
- CAD measurement 정밀도 ±5-10% 정상 변동 — refit OK
- ★★★ flex_h/k (joint compliance) 추가 — 사용자 예시 highlight

---

## 🎯 점수 함수 (GOAL9와 동일, locked)

```
score = Σ_trial [ W_q·RMSE(q1,q2) + W_dq·RMSE(dq1,dq2) + W_τ·RMSE(τ1,τ2)
                + W_h·|h_sim - h_real|       ← ★ 1순위 W_h=50
                + W_grf·max(0, GRF_dev - 0.25)²
                + W_pen·max(0, pen_max - 2)² ]
```
Weights: W_q=100, W_dq=3, W_τ=20, W_h=50, W_grf=1, W_pen=10.

★ τ RMSE는 Mode A에서 자동 0 (input = ctrl) — score에 기여 거의 없음.

---

## 🚀 GOAL10 Phase 0 = ★ Pure GOAL7 Base (★ 사용자 명시 base-up)

★ 사용자 명시: "base model부터 시작 + 하나씩 천천히 + 효과 없으면 drop"

| Variable | GOAL10 Phase 0 (Pure Base) |
|---|---|
| solref_tc | **0.02** (MuJoCo default) |
| solref_d | **1.0** (MuJoCo default) |
| imp_0 | **0.9** (MuJoCo default) |
| imp_1 | **0.95** (MuJoCo default) |
| imp_mid | **0.001** (MuJoCo default) |
| mu | **1.0** (MuJoCo default) |
| dt | **0.002** s (GOAL7 Base) |
| integrator | **Euler** (GOAL7 Base) |
| cone | **pyramidal** (GOAL7 Base) |
| impratio | **1** (GOAL7 Base) |
| fl_hip, fl_knee | **0.1** (P0 base) |
| **tau_scale_h** | **1.0 LOCK** (★ Mode A 본질) |
| **tau_scale_k** | **1.0 LOCK** (★ Mode A 본질) |
| 그 외 모든 axis (armature/damp/Stribeck/m_foot/motor_tm/tau_delay/flex/bias/stiff/nl/base_z/etc.) | **0** (default) |
| Foot 형상 | cylinder ⌀42mm × 13mm y-axis (G9 결정) |
| CAD (M/m/r/I) | original values |

★ Predicted Phase 0 baseline: score ~74,610 (GOAL9 Phase 0와 동일)

### Phase 0의 의미
- Mode A 본질 시작점 = pure base
- 모든 후속 phase는 이 baseline 대비 effectiveness 측정
- G9 발견된 KEEP axis도 **다시 검증** (Pure Mode A 환경에서 effective인지 재확인)
- G9 발견 정보는 prior/BO range/method choice로만 reuse

## ⚠️ 진행 중 Sub-agent 처리

Sub-agent `a0aa8d83076c73f06`는 잘못된 "G9 stack inherit baseline"으로 작업 중. 그 결과는 **Phase 0a — G9 Inherit Reference** 이름으로 저장. 진짜 GOAL10 시작은 **Phase 0R — Pure GOAL7 Base** 부터.

---

## 🔬 GOAL10 Phase 진행 전략

### Phase 0R — ★ Pure GOAL7 Base (★ 사용자 명시 base-up 시작점)
- Pure base XML (모든 axis default/0/identity)
- 9-trial sim + Locked Template Notion 페이지
- 공중 회전 + h_jump + GRF + pen 모든 baseline 측정
- score 예상 ~74,610 (GOAL9 Phase 0 동일)

### Phase 1 — solref/solimp (★ G9 prior reuse, narrow BO)
- G9 P1 best가 시작점/center: tc=0.00556, d=1.32, i0=0.456, i1=0.940, mid=0.01444
- narrow BO range: ±20% around G9 P1
- Method: TPE + CMA-ES (4-method 비교)
- 자연 판단 (개선되면 keep, 안 되면 다음 hypothesis) (G9에서 KEEP됐지만 Mode A 환경 재검증)
- 외부 출처 ≥3 (MuJoCo Menagerie convention)

### Phase 2 — dt/integrator (★ G9 P10 reuse, A/B/C/D/E 재비교)
- G9 P10에서 Config D 발견. Pure Mode A에서도 동일 효과인지 검증
- A/B/C/D/E 다시 측정 + Drop-test

### Phase 3 — m_foot_extra (★ G9 P8 reuse)
- G9 P8 sweet spot 18.5g. narrow BO [0.005, 0.05] kg
- TPE adaptive (Grid는 sweet spot miss 가능)
- Drop-test

### Phase 4 — joint damping narrow refine (★ 사용자 통찰)
- BO range: `damp_hip ∈ [0.01, 0.5]`, `damp_knee ∈ [0.01, 0.5]` (narrow!)
- Method: 2D log-grid (6×6 = 36) + TPE refine 80 trials
- 목표: 공중 회전 막기 + h_jump 1순위 보존
- G9 P4 (wide BO)에서 damp=2.17이 h_jump destroy → narrow [0.01, 0.5] 재검토
- 외부 출처 ≥ 3 (Menagerie Go1/Spot/ANYmal damping, AK80-9 viscous spec)

### Phase 5 — Stribeck friction (joint level)
- BO axis: `fc_hip/knee`, `fv_hip/knee`, `fs_hip/knee`, `vs` (총 7-param)
- Narrow range: fc ∈ [0, 0.3], fv ∈ [0, 0.1], fs ∈ [0, 0.3], vs ∈ [0.05, 0.5]
- Method: CMA-ES (7-dim) + TPE 비교 (200 trials each)
- 외부 출처: AK80-9 friction calibration, Khalil-Dombre 표준

### Phase 6 — fl_hip/knee narrow refine
- BO range: `fl ∈ [0.02, 0.3]` (P0 default 0.1 ± wider보다 narrow)
- Method: 2D Grid (10×10) + TPE refine
- 외부 출처: T-Motor static friction spec

### Phase 7 — foot 형상 refine
- BO axis: `foot_radius` ∈ [0.018, 0.024], `foot_half_len` ∈ [0.005, 0.008]
- Method: 2D scan + TPE
- 외부 출처: 사용자 robot CAD 실측

### Phase 8 — base_z slide damping/friction
- BO axis: `b_c` (base slide damping), `base_fl` (slide frictionloss), `base_arm`
- Narrow range, BO method 다양화

### Phase 9 — CAD refit (★ 사용자 명시 명시적 추가)
- BO axis (모두 narrow ±10-20%):
  - `M` ∈ [0.92, 1.12] kg (1.02 ± 10%)
  - `m1` ∈ [0.95, 1.16] kg, `m2` ∈ [0.21, 0.26], `m_c` ∈ [0.73, 0.89], `m_p` ∈ [0.13, 0.17]
  - `r1, r2, r_c, r_p` ±15%
  - `I1, I2, I_c, I_p` ±20% (log scale)
- Method: CMA-ES (13-dim correlated) + TPE 비교
- 외부 출처: 실제 robot CAD 정밀도 측정 변동성, 일반 CAD ±5-10% 허용

### Phase 10 — joint flex compliance (★★★ 사용자 예시 highlight)
- BO axis: `flex_h ∈ [0, 1e-3] rad/Nm`, `flex_k ∈ [0, 1e-3] rad/Nm`
- Joint이 stiff bar가 아닌 spring-like compliance
- Sim: `q_actual = q_motor - flex × τ` (load-dependent angle deflection)
- 외부 출처: harmonic drive flex (T-Motor gear), Hwangbo 2019 actuator NN, MIT Cheetah motor flex

### Phase 11 — joint bias (encoder offset)
- BO axis: `bias_h ∈ [-0.05, 0.05] rad`, `bias_k ∈ [-0.05, 0.05] rad`
- Sim 초기 자세 vs real measurement 초기 정렬 보정
- 외부 출처: encoder calibration variance

### Phase 12 — joint stiffness
- BO axis: `stiff_hip ∈ [0, 5] Nm/rad`, `stiff_knee ∈ [0, 5] Nm/rad`
- Mechanical spring-back (예: tendon, cable)
- Stress test (Mode A에서 영향 작을 가능성)

### Phase 13 — nonlinear damping (nl)
- BO axis: `nl_hip ∈ [0, 0.5]`, `nl_knee ∈ [0, 0.5]`
- τ_nl = -nl × dq × |dq| (quadratic damping)
- 고속 motion에서 정상 마찰보다 큰 dissipation

### Phase 14+ — 추가 axes (시간 따라)
- Actuator NN residual (Hwangbo 2019)
- motor_tm two-pole (G8 P18 — Mode A 호환 시 적용)
- Score function rebalancing (사용자 confirm 필요)

### ★ Skip (Mode A 본질 무관)
- kappa_h/k (saturation) — input이 이미 hardware saturated
- αkp/αkd PD scaling — Mode A는 PD command 안 씀
- akp_slope — same
- q_delay_to_PD — same

### Phase Final
- 통합 + ablation + final Notion 페이지

---

## ⏰ Cron Alarm (★ 사용자 명시)

### Stop alarm (Jun 16 12:00 KST one-shot)
- CronCreate one-shot "0 12 16 6 *"
- Prompt: "★ GOAL10 종료. 최종 commit + Windows toast 확인 + 사용자에게 최종 결과 보고."

### Windows OS-level alarm
- PowerShell `schtasks /Create` Jun 16 12:00 toast notification

### 6h checkpoint cron (기존 c62a2b13 유지)
- 6h마다 progress 보고 + commit + Notion verify

---

## 📋 매 phase Locked Template (★ 사용자 명시 STRICT)

### 페이지 sections (모두 매번)

1. **Status callout** (yellow_background)
2. **이 페이지를 읽으면 얻는 것** (5-8 bullets)
3. **🆚 Base vs This Stage Full Axis 비교 표** (60+ rows)
   - 모든 axis 포함: CAD mass/inertia/r/I, solref/solimp (5), mu, armature_hip/knee, damp_hip/knee, fc/fv/fs/nl, fl_hip/knee, motor_tm_h/k, tau_scale, tau_delay, m_foot_extra, foot 형상, dt/integrator/cone/impratio, vs, base_arm/b_c/base_fl, margin
   - ★ 표시: 이 phase에서 변경된 axis
4. **MuJoCo / 모델 용어 정리** (재사용 + phase 추가)
5. **변경 axis 상세** + 외부 출처 (≥ 3, URL + 인용)
6. **방법 비교 표** (사용한 method + 결과)
7. **BO 결과** (score + improvement)
8. **per-trial RMSE 표** (9 trial q/dq/τ)
9. **★ 점프 높이 표** (1순위 metric)
10. **GRF band 25% + pen band 2mm 표**
11. **★ 4-panel plot 9 trial** (q/dq/τ/GRF, Real solid + sim dashed 2-way ONLY, V20 convention)
12. **★ V25 animation 9 trial 전부** (80f 60ms, 흰글자+검은outline, malgun.ttf)
13. **결과 해석** (5-8 bullets)
14. **Drop-test** (3% threshold)
15. **다음 phase** (후보 + 추천 method)
16. **코드 토글**
17. **외부 참조 + cross-link** (이전 phase 페이지)
18. **divider + footer**

### Verify 매번 (절대 skip X)
- 모든 file_uploads `GET /v1/file_uploads/{id}` → status="uploaded"
- 페이지 image block count = 18 (9 plot + 9 anim)
- Base vs Stage 표 존재 + 60+ rows

### 절대 위반 금지
- plot/anim/표 빠뜨림 X
- 압축 X
- Locked Template 외 section 추가는 OK (보충 자료, 외부 paper 그림 등)
- "drop axis라 plot skip OK" 같은 자체 판단 절대 X

---

## 🔍 외부 검색 + MD update + commit (매 phase)

### 매 phase 외부 검색 (≥ 3 출처)
- WebSearch + WebFetch
- MuJoCo Menagerie 다양한 robot
- legged_gym, walk-these-ways, mujoco_menagerie
- AK80-9 V2 spec (CubeMars, UMich neurobionics)
- Hwangbo 2019 ANYmal Sci. Robotics
- Khalil-Dombre 표준 manipulator equation
- Stribeck friction paper (Armstrong 1991)
- 필요 시 추가 paper/repo search

### MASTER_INSIGHTS_G9.md update (★ 새 G10 section 추가)
- 매 phase 끝나면 immediate append
- GOAL10 section 시작 부분에 GOAL9 결과 cross-reference
- 외부 출처 URL + 인용 verbatim
- BO 결과 + per-trial metric
- 결론 + 다음 후보

### Git commit 매 phase
- "GOAL10 Phase N — [axis]: keep/drop, score X"
- Notion page ID 명시
- MD section 추가 명시

---

## 🚦 자율 Loop (13.5h)

### 종료 조건
1. **시간**: 2026-06-16 12:00 KST (cron 알람)
2. **사용자 interrupt**
3. **Plateau** (5 phase 연속 < 3% 개선)

### 6h checkpoint (cron c62a2b13)
- 진행률 + score 변화 + Δh + foot penetration
- Notion 페이지 image verify
- MD commit + git commit "GOAL10 checkpoint t+Nh"

### 매 phase 종료 self-check (모두 통과)
- [ ] 외부 출처 ≥ 3 (URL + 인용 verbatim) MD에 기록
- [ ] **Full axis 비교 표 60+ rows** ★ (사용자 강조)
- [ ] **plot 9 trial 4-panel Real+sim 2-way** ★
- [ ] **anim 9 trial 전부** ★
- [ ] MuJoCo 용어 정리
- [ ] BO/method 비교 표
- [ ] per-trial RMSE 표
- [ ] 점프 높이 표 (1순위)
- [ ] GRF band 25% / pen band 2mm 분석
- [ ] 자연 판단 (개선되면 keep, 안 되면 다음 hypothesis) threshold
- [ ] Notion 페이지 image block count = 18 verify
- [ ] MASTER_INSIGHTS_G9 append (GOAL10 section)
- [ ] git commit

---

## 🛠️ 코드 패턴 재사용

| 작업 | 파일 |
|---|---|
| run_trial (Mode A) | `goal9/phase0/run_baseline.py` (★ tau_scale_h=tau_scale_k=1.0 default 강제 STRICT) |
| build XML Phase 0 baseline | `goal9/phase_final/build_xml_final.py` (tau_scale 제거 버전 + G10 신규) |
| build XML phase 별 | G10 phase 별 신규 (`goal10/phase_n/`) |
| BO multi-method | `goal9/phase1/bo_multi_method.py` template |
| plot 9 trial 2-way | `goal9/phase11/gen_plots_anim_p11.py` template (4-way → 2-way로 단순화) |
| anim 9 trial | 신규 작성 (9 trial each, 80f 60ms) |
| Notion API | `goal6/stage{N}_plots_and_notion.py` template + 3-step file_upload |
| Cron alarm | CronCreate + Windows schtasks |

### Notion infra
- Token: `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`
- CONCEPT parent: `115ab81d255080fdaae6f28f55e3e205`
- **GOAL10 parent**: Phase 0에서 생성 → MASTER_INSIGHTS_G9.md `## GOAL10` section 최상단에 ID 기록

---

## 📚 외부 참고 자료 (각 phase 검색 시작점)

### Papers
- Hwangbo et al. 2019 — Sci. Robotics (joint actuator dynamics)
- Khalil-Dombre — Modeling, Identification, Control of Robots
- Armstrong-Hélouvry 1991 — Control of Machines with Friction (Stribeck)
- Tan et al. 2018 — Sim-to-Real legged
- Park, Wensing, Kim 2021 — MIT Cheetah

### Repos
- google-deepmind/mujoco_menagerie (Go1/Spot/H1/ANYmal/Cassie/Barkour)
- leggedrobotics/legged_gym
- Improbable-AI/walk-these-ways
- machines-in-motion/mujoco_utils (Solo12)
- neurobionics/TMotorCANControl (AK80-9 a_hat 5-param)

---

## 🚀 시작 trigger

### Step 1: 인프라
1. Notion GOAL10 parent page 생성 (CONCEPT 아래)
2. MASTER_INSIGHTS_G9.md `## GOAL10 — Pure Mode A Friction Tuning` section append (parent ID 기록)
3. Cron one-shot Jun 16 12:00 stop alarm
4. Windows schtasks Jun 16 12:00 toast notification

### Step 2: Phase 0 (baseline)
1. `goal10/phase0/` 생성
2. Baseline XML = G9 best (P1+P8+P10) - tau_scale
3. 9-trial Mode A sim
4. Plot 9 (Real+sim 2-way) + Anim 9 + Full axis 표
5. Notion 페이지 (Locked Template strict, image verify)
6. MD append + commit

### Step 3+: 자율 자동 진행
- Phase 1 damping narrow refine
- Phase 2 Stribeck
- Phase 3 fl narrow
- Phase 4 foot 형상
- Phase 5+ 추가 axes
- 매 6h checkpoint
- 12:00 KST 종료

---

**Mission start.**
