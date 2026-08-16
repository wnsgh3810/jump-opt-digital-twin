# GOAL12 — Mode A Digital Twin (Combined 26.04.24 + 26.06.02 = 15 trial)

> **시작일**: 2026-06-16 KST
> **종료**: **2026-06-17 12:00 KST** (~22h 자율)
> **모드**: Mode A 단일 (tau_scale=1.0 LOCK)
> **데이터**: 26.04.24 (9 trial) + 26.06.02 (6 trial) = **15 trial 합침**
> **출발점**: Pure GOAL7 Base (base-up + GOAL10 발견 reuse)
> **목표**: 15 trial uniform 일치율 high + Mode A 본질 strict 유지

---

## ★★★ 위반 history (절대 반복 X — 사용자 "이번엔 제대로")

1. ★ tau_scale 적용 (Mode A 위반) — GOAL10 fix
2. ★ Plot 색 명시 (사용자 "색 X" 명시) — 3회 위반 fix
3. ★ **Anim MuJoCo가 아닌 다른 방식 사용** (사용자 "어제 계속 빠뜨림" 강조) — **3회 위반, 절대 X**
4. ★ h_sim displacement 사용 (사용자 absolute 명시) — fix
5. ★ Notion 페이지 영어 작성 (사용자 한글 명시) — fix
6. ★ Locked Template 일부 skip (drop axis라 plot skip 등) — fix

## ★ 8 strict 절대 준수 (매 페이지 매 sub-agent 확인)

### 매 sub-agent 작업 시작 시 반드시 read:
- `C:/Users/junho/Desktop/jump_opt/GOAL12_PROMPT.md` (이 파일)
- `C:/Users/junho/Desktop/jump_opt/MASTER_INSIGHTS_G9.md` (GOAL10/GOAL11 발견)

### 8가지 strict

1. **★ Notion 페이지 한글 작성** (axis name/단위/paper title만 영어 OK)
2. **★ Plot 색 명시 절대 X** (matplotlib auto color cycle만, `l1.get_color()` 패턴)
3. **★ Plot 2-way only** (Real solid + sim dashed. 비교 라인 추가 X)
4. **★★★ Anim MuJoCo Renderer 강제** (matplotlib animation 절대 X, 사용자 3회 강조!)
5. **★ h_sim absolute** (`base_z.max()` ground=0 기준, init 빼지 X)
6. **★ Mode A 본질 STRICT** (tau_scale_h = tau_scale_k = **1.0 LOCK**)
7. **★ Flight phase PD hold X** (자연 마찰/댐핑이 dissipate)
8. **★ Locked Template strict** (plot 15 + anim 15 + 60+ table + image verify 30/30)

### MuJoCo Renderer 절대 강제 (사용자 3회 강조)

```python
import mujoco
renderer = mujoco.Renderer(model, width=640, height=480)
camera = mujoco.MjvCamera()
camera.azimuth = 135; camera.elevation = -15; camera.distance = 1.2; camera.lookat = [0, 0, 0.3]
# 매 frame: data.qpos[:] = qpos → mj_forward → renderer.update_scene(data, camera) → renderer.render()
# 절대 matplotlib animation X / 다른 viz X
```

---

## 📊 점수 함수 (GOAL10 동일)

```
score = Σ_trial [ W_q·RMSE(q1,q2) + W_dq·RMSE(dq1,dq2) + W_τ·RMSE(τ1,τ2)
                + W_h·|h_sim − h_real|       ← ★ 1순위 W_h=50
                + W_grf·max(0, GRF_dev − 0.25)²
                + W_pen·max(0, pen_max − 2)² ]
```

Weights: W_q=100, W_dq=3, W_τ=20, W_h=50, W_grf=1, W_pen=10.

★ 15 trial 모두 uniform 일치율 high — 단일 trial good + 나머지 worse 안 됨.

---

## 🎲 데이터 (★ GOAL10과 유일한 차이점)

### 26.04.24 (9 trial, dataset prefix `0424_`)
- `0424_60_0.75_60_2` (h_real 0.900)
- `0424_60_1.5_60_1.5` (0.910)
- `0424_90_0.75_90_2` (0.894)
- `0424_120_2_120_2` (0.840)
- `0424_120_2.2_150_2.5` (0.810)
- `0424_120_2.2_200_2.8` (0.795)
- `0424_150_2.2_250_3` (0.770)
- `0424_150_2.2_350_3.5` (0.770)
- `0424_150_2.2_500_4` (0.775)

### 26.06.02 (6 trial, dataset prefix `0602_`)
- `0602_60_0.75_60_2` (h_real 0.94)
- `0602_60_1.5_60_1.5` (0.96)
- `0602_90_0.75_90_2` (0.98)
- `0602_120_2_120_2` (0.94)
- `0602_150_2.2_250_3` (0.90)
- `0602_150_2.2_500_5` (0.80)

### 데이터 로드
- 각 trial xlsx (hip, knee, GRF) → paper_a_hat 변환 → npz 저장
- `goal12/data_loaded_combined.npz`
- Reference: `goal9/phase0/load_26_04_24.py` + `goal5/phase0_data_load.py`

---

## 🚀 Phase 0R Pure GOAL7 Base (★ base-up 시작점, GOAL10 동일)

| Variable | Phase 0R (Pure Base) |
|---|---|
| solref_tc | 0.02 (MuJoCo default) |
| solref_d | 1.0 |
| imp_0 | 0.9 |
| imp_1 | 0.95 |
| imp_mid | 0.001 |
| mu_floor | 1.0 |
| dt | 0.002 s |
| integrator | Euler |
| cone | pyramidal |
| impratio | 1 |
| fl_hip, fl_knee | 0.1 Nm |
| **tau_scale_h** | **1.0 LOCK** |
| **tau_scale_k** | **1.0 LOCK** |
| 그 외 모든 axis | 0 (default) |
| Foot 형상 | cylinder ⌀42mm × 13mm y-axis |
| CAD (M/m/r/I) | original values |

★ 모든 후속 iter는 이 baseline 대비 effectiveness 측정.

---

## 🔬 진행 방식 — Evolutionary Research Loop (GOAL10 동일)

### Iteration cycle (★ 매 iter)

1. **MD read**: `GOAL12_PROMPT.md` + `MASTER_INSIGHTS_G9.md` GOAL10/GOAL11/GOAL12 sections
2. **Diagnose 현재 stack** (15 trial uniform 일치율 분석)
3. **★ WebSearch external research** (≥2-3 sources, 매 iter 다른 topic)
4. **Hypothesize axis** (자율, 1-2개)
5. **★ 다양한 method 자율 선택** (BO만 X — TPE/CMA-ES/NSGA-II/scipy/Least-squares/EKF/NN/MJX/Sobol 등)
6. **Try** → 15-trial sim
7. **★ Plot 15 + Anim 15** (★ 8 strict — 한글, 색 X, 2-way, **MuJoCo Renderer**)
8. **자연 판단** (% threshold X)
9. **MD evolve** (continuous append GOAL12 section)
10. **Notion 페이지** (★ Locked Template 22 sections, 한글, stand-alone learning, 30 image verify)
11. **Git commit**

### GOAL10/11 발견 reuse (prior/BO range)

| Axis | GOAL10/11 발견 |
|---|---|
| solref/solimp | tc=0.00585, d=1.303, i0=0.613, i1=0.959, mid=0.00996 (Iter21) |
| Config D | dt=0.0005, RK4, elliptic, impratio=100 (KEEP) |
| mass refit | M_base 1.216 (+19.2%), m1/m2/m_c 모두 refit |
| m_foot_extra | 18.46g (KEEP) |
| stiffness | hip=0.0801, knee=1.142 |
| armature | hip=0.00186, knee=0.00490 |
| fc | hip=0.934, knee=0.0213 (광역 드리프트) |
| per-trial fv | kd 의존 이질성 (저kd↑, 고kd↓) |
| DROP axes | mu_floor, motor_tm, tau_delay, foot 형상, base_z slide, kd 회귀, flex, contact compliance, dual_annealing |

### 후보 axis pool (★ 자율 선택)

1. GOAL10/11 KEEP axes 15 trial 재검증
2. per-trial fv 2D refit (GOAL11 T2 핵심 발견)
3. fc_hip [0.93, 1.5] 추가 확장
4. mass tolerance ±15% wider
5. CAD r/I refit
6. flex_h/k 재시도 (15 trial로)
7. Actuator NN residual (Hwangbo 2019)
8. Per-PD α 시도 (GOAL8 P13 inspired)
9. Sobol indices + LOTO CV (학습 9 vs 검증 6)
10. dual_annealing 전체 (GOAL11 T6 inspired)
11. multi-objective Pareto (NSGA-II)
12. dataset-specific fv (0424 vs 0602)

★ ★ 매 iter 다른 method 시도.

---

## 📋 매 페이지 Locked Template (★ 22 sections, 한글, stand-alone learning)

1. Status callout (yellow_background, 🎯)
2. **🎓 학습 목표** (이 페이지 다 읽으면 무엇을 마스터)
3. **📖 기본 모델 상태** (Pure Base + 이전 iter stack, 자세히, 이전 페이지 안 읽어도 이해 가능)
4. **🔬 이 iter 변경 axis** (★ 무엇 + 왜 + 어떻게)
5. **🧮 물리적 의미 / 수식**
6. **🌍 외부 근거** (paper/repo ≥3, URL + 한국어 인용 풀이)
7. **🆚 Full axis 비교 표 60+ rows** (Base vs Current, ★ 변경 axis)
8. **📖 MuJoCo / 모델 용어 정리** (모든 axis 자세히 정의)
9. **🔬 방법 비교 표** (사용 method + 비교)
10. **🏁 BO 결과**
11. **📊 per-trial RMSE 표 15 trial**
12. **★ 점프 높이 표 15 trial** (h_real abs / h_sim abs / |Δh| cm / < 3cm?)
13. **GRF band 25% + pen band 2 mm 표**
14. **★ 4-panel plot 15 trial** (q/dq/τ/GRF, Real solid + sim dashed **2-way**, **색 X**)
15. **★ V25 anim 15 trial 전부** (**80f 60ms, MuJoCo Renderer**, malgun.ttf overlay)
16. 결과 해석 (5-8 bullets 한글)
17. 자연 판단 (% threshold X)
18. **💡 인사이트**
19. **🚀 다음 iter 후보** (자율 결정)
20. 코드 토글
21. 외부 참조 + cross-link
22. divider + footer

### Verify 매번 (절대 skip X)
- 모든 file_uploads status="uploaded" (30개)
- 페이지 image block count = **30** (15 plot + 15 anim)
- Base vs Current 표 존재 + 60+ rows
- 한글 작성 확인

---

## ⏰ Cron + Windows alarm

- **CronCreate one-shot** "0 12 17 6 *" (Jun 17 12:00 KST stop)
- **Windows schtasks** `GOAL12_Alarm` 6/17 12:00 popup + sound
- **6h checkpoint cron** (기존 c62a2b13 active, 매 6h)

---

## 🛠️ Reference 코드 (절대 strict — 자체 재작성 X, import 사용)

- run_trial: `goal9/phase0/run_baseline.py` (Mode A MuJoCo, h_sim absolute)
- paper_a_hat: `goal9/phase0/load_26_04_24.py` L13-19 (Pure Paper sgn(v) only)
- gen_plots 패턴: `goal10/phase0r/gen_plots_p0r.py` (색 X, 2-way, l1.get_color())
- ★ **gen_anim 패턴: `goal9/phase0/gen_anim.py`** (★ MuJoCo Renderer 절대 강제)
- 26.06.02 데이터 로더 patterns: `goal5/phase0_data_load.py`

---

## 📚 외부 research continuous (★ 매 iter)

- WebSearch / WebFetch ≥ 2-3 sources per iter
- 후보 sources:
  - MuJoCo Menagerie (Cassie, Go1, Spot, ANYmal, H1, Barkour)
  - legged_gym, walk-these-ways
  - Hwangbo 2019 ANYmal, MIT Cheetah, Park 2021
  - AK80-9 V2 spec (CubeMars, UMich neurobionics)
  - Khalil-Dombre manipulator equation
  - Stribeck friction (Armstrong 1991)
  - Sim-to-Real papers
- 새 paper/repo 발견 시 MD GOAL12 section append

---

## 🚦 자율 Loop (~22h)

### 종료 조건
1. 시간: 2026-06-17 12:00 KST (cron + Windows alarm)
2. 사용자 interrupt
3. Plateau (5 iter 연속 < 3% 개선)

### 6h checkpoint (cron c62a2b13)
- 매 6h 진행률 + score 변화 + MD commit + Notion verify + git commit

### 매 iter 종료 self-check
- [ ] MD read 확인 (GOAL12_PROMPT + MASTER_INSIGHTS_G9)
- [ ] 외부 research ≥ 2-3 sources URL/인용
- [ ] **Full axis 60+ rows table** (Base vs Current)
- [ ] **plot 15 trial 2-way 색 X**
- [ ] **anim 15 trial MuJoCo Renderer** (matplotlib X)
- [ ] h_sim absolute 적용
- [ ] tau_scale=1.0 LOCK 확인
- [ ] **Notion 한글** 작성
- [ ] image verify 30/30
- [ ] MD GOAL12 section append
- [ ] git commit

---

## 🚀 시작 trigger

### Step 1: 인프라
1. Notion GOAL12 parent page 생성 (CONCEPT 아래)
2. MASTER_INSIGHTS_G9.md `## GOAL12 — Combined 26.04.24 + 26.06.02` section append
3. Cron one-shot 6/17 12:00 stop
4. Windows schtasks 6/17 12:00 toast

### Step 2: 데이터 로더
1. `goal12/data_loaders/load_combined.py` 작성
2. 26.04.24 9 trial + 26.06.02 6 trial → paper_a_hat 변환 → `data_loaded_combined.npz`
3. trial naming: `0424_*`, `0602_*` prefix

### Step 3: Phase 0R Pure Base
1. `goal12/phase0r/` 디렉토리
2. Pure GOAL7 Base XML
3. 15-trial sim (Mode A, tau_scale=1.0, h_sim absolute)
4. Plot 15 + Anim 15 (★ MuJoCo Renderer) + Notion 한글 페이지

### Step 4+: 자율 iteration loop
- iter 1~N 자율 (다양한 method, MD evolve, external research)
- Final stack consolidation

---

**Mission start.**
