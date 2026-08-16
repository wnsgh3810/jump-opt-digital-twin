# GOAL8 — Mode B Digital Twin 정밀화 (PD sim 기반 fit)

## 🎯 핵심 미션 (한 줄)
**Mode B를 진짜 PD sim 기준으로 다시 fit하여 디지털 트윈 완성도 ↑** — 위치/속도/토크/지반력이 잘맞는 모델 발견. 점프 높이는 결과/검증 지표일 뿐 목표 아님.

---

## ⚠️⚠️⚠️ 발견 저장 규칙 (절대 잊지 말 것)

**모든 발견 (외부 논문/웹/오픈소스 + 자체 BO/실험)은 즉시 `MASTER_FINDINGS_UNIFIED.md`에 누적 추가.**

★ **통합 파일**: `C:/Users/junho/Desktop/jump_opt/MASTER_FINDINGS_UNIFIED.md` (3908+ lines)
- 4개 MD 통합: MASTER_FINDINGS (G5R/6/7) + MASTER_INSIGHTS + NEXT_GOAL8 spec + MASTER_FINDINGS_GOAL8
- 모든 외부 정보 + 자체 발견 + mission spec을 한 곳에서 관리
- 분산 저장 ❌, 단일 source of truth ✓

### 저장해야 할 것
1. **외부 정보 발견**: 논문, 웹, GitHub 오픈소스 코드, 데이터시트, 포럼 토론
2. **우리 실험 발견**: BO 결과, ablation 결과, NEGATIVE 결과, plateau 탈출 메커니즘
3. **이전 GOAL 발견 누적**: GOAL5R/6/7에서 검증된 사실
4. **버그/우회**: 코드 버그, 환경 설정 함정, debug 패턴

### 저장 방식
- 파일: `C:/Users/junho/Desktop/jump_opt/MASTER_FINDINGS_GOAL8.md`
- Phase별 섹션: "Phase N — [핵심 axis]"
- 외부 정보: "## 📚 외부 정보 — [논문 제목]"
- Ablation 결과: "## 🔬 [Stage N] Ablation"
- 형식: 결과 + Why + How to apply + 외부 cross-check

### 메모리도 함께
- `~/.claude/projects/.../memory/goal8_findings_phase14_18.md` (또는 비슷한 파일)
- MEMORY.md 인덱스 업데이트

### NOT
- 메모리만 저장하지 말 것 (md 누적이 핵심)
- 노션 페이지만 만들고 끝내지 말 것
- 발견 잊지 말 것 — 매 phase 끝나면 즉시 추가

---

## ⚠️ 가장 중요한 원칙 (절대 잊지 말 것)

### 1. 우리의 목적은 매칭이지 점프가 아님
- ✅ **목표**: q (각도), dq (속도), τ (토크), GRF (지반력) — 4개 metric 모두 실측과 일치
- ❌ **목표 아님**: 점프 높이 매칭. 점프 높이는 결과/검증 지표일 뿐. q/dq/τ/GRF가 잘 맞으면 자연스럽게 점프 높이도 비슷해짐
- **왜 이것이 중요한가**: 점프 높이만 맞추면 모델이 "수치만 맞는" overfit 가능. 우리는 **물리적으로 정확한 모델** 필요 (실 robot 배포 시 다른 조건에서도 generalize)
- **검증 metric으로서 점프 높이**: q/τ가 다 맞아도 점프 높이가 크게 다르면 dynamics 어딘가 틀린 것 → 디버깅 신호

### 2. Mode B의 본질
- **Mode A** = open-loop sim (실측 토크를 그대로 motor에 인가). modeling error만 측정 — 검증용
- **Mode B** = closed-loop PD sim (q_des → PD output → motor). 실 robot 배포 시 (cmd가 q_des) 정확히 동작하는지 검증 — **실용성 ★★★★**
- **왜 Mode B 정밀화가 중요한가**: 실 robot은 q_des cmd 받음. Mode B가 정확해야 sim에서 본 결과를 실 robot에서 재현 가능

### 3. PD ref의 정확한 정의
실 robot 제어 방식 그대로:
- **Stance phase** (점프 전): q_des(t) 실측 trajectory + dq_des = 0
- **공중/Flight phase** (점프 후): **last q_des 위치 hold + dq_des = 0** (이전 GOAL7 마지막에 적용)
- **PD output**: `τ_pd = αkp·kp_folder·(q_des - q) + αkd·kd_folder·(0 - dq)` (dq_des = 0 항상)

---

## 📊 출발점 (현재 Mode B 상태)

### Mode B FINAL = Stage 39
- **BO score (옛 sim)**: 371.70 (실측 토크 인가 sim 기준)
- **PD sim 결과 (공중 hold 적용)**:
  - q1 RMSE 평균: 0.028 rad
  - q2 RMSE 평균: 0.053 rad
  - τ1 RMSE 평균: 6.40 Nm
  - GRF RMSE 평균: 25.36 N
  - 점프 높이: 62.9 ~ 74.2 cm (6 trial)
- **사용된 모델 axis**: a_hat 10p (per-joint, Stage 26) + αkp/αkd per-joint (Stage 24) + motor LPF (Stage 22) + 8 axis (Stage 14) + tau_delay

### Mode A FINAL = Stage 53, Score 206.48
- 70.8% 개선 (706 → 206.48)
- Mode B는 Mode A 대비 ~80% 큼 — 큰 잠재력

### 핵심 문제
**Mode B BO는 옛 sim (실측 토크 인가)으로 fit됨** — 즉 진짜 PD sim 응답을 BO가 못 본 채 fit. 새 PD sim (공중 hold)으로 다시 fit 필요.

---

## 🚀 Phase별 향상 전략

### Phase 1 ⭐⭐⭐ — BO 재실행 (PD sim 기반)
**가장 큰 효과 예상 (30-50% 향상)**

- **변경**: BO score function이 옛 sim → 공중 hold PD sim 결과 사용
- **유지**: Stage 26 axis (10p a_hat + αkp/αkd + LPF + 8 axis) baseline
- **새 BO**: 같은 axis 공간, 새 sim으로 다시 fit
- **왜 이게 효과적인가**: 옛 BO best는 실측 토크 인가 sim의 local optimum. 진짜 PD sim의 best는 다른 지점일 수 있음
- **예상 결과**: ~250~300대 score, q1 RMSE < 0.025

### Phase 2 ⭐⭐⭐ — Motor torque saturation ±18 Nm
- **추가**: PD output → clip(τ_pd, -18, 18) → motor 인가
- **새 용어**: 
  - **Torque saturation**: 모터가 출력 가능한 최대 토크. AK80-9는 ±18 Nm 한계. PD가 30 Nm 명령해도 motor는 18 Nm까지만 출력
  - **왜 모델링해야 하는가**: 실 robot PD는 high-PD trial (150_500_5)에서 saturation 자주 발생. 이걸 sim에서 무시하면 sim 토크가 비현실적으로 큼 → q deviation 큼
- **예상 효과**: high-PD trial (150_500_5)의 매칭 큰 개선 (q2 RMSE 0.05 → 0.03)

### Phase 3 ⭐⭐ — Firmware D term LPF
- **변경**: dq 측정값에 1차 LPF 적용 (firmware의 derivative noise filter 모델)
- **수식**: `dq_filtered += (dt / d_tm) · (dq_meas - dq_filtered)` → PD에 dq_filtered 사용
- **새 용어**:
  - **D term**: PD의 derivative 부분. αkd·(dq_des - dq)
  - **D term noise**: 실 robot의 dq 측정은 encoder differentiation → high-frequency noise. 직접 사용하면 진동
  - **firmware LPF**: 실 motor 펌웨어가 내부적으로 dq 필터링. d_tm ~5-20ms 추정
- **왜 필요한가**: Stage 23-24에서 αkd_slope=1.30 발견 — D term이 비선형 응답. LPF 모델 추가로 정확

### Phase 4 ⭐ — Gear backlash (정/역 전환 dead zone)
- **변경**: gear input/output 사이에 dead zone (±backlash) 추가
- **새 용어**:
  - **Gear backlash**: 기어 톱니 사이 미세한 틈. 정회전 → 역회전 시 그 틈만큼 dead zone 발생 (force 전달 안 됨)
  - **AK80-9 typical**: 약 0.1~0.5도 (0.002~0.009 rad)
- **왜 필요한가**: 토크 방향 자주 바뀌는 stance 종료 시점에서 매칭 어려움

### Phase 5 ⭐ — Per-phase PD scaling
- **변경**: stance와 flight phase에서 다른 αkp/αkd 사용 가능
- **가설**: 실 robot firmware가 phase에 따라 PD gain 조정할 수 있음
- **위험**: 모델 overfit 가능 → 충분한 ablation 필요

### Phase 6 — Weighting 재조정
- **변경**: 현재 q1=q2=100, GRF=5 → 새 weighting
- **추가**: τ1 RMSE, τ2 RMSE를 weighting에 명시 추가
- **이유**: τ RMSE 6-20 Nm로 큼. tau weight ↑로 PD modeling 우선 개선
- **새 weighting 후보**: q1=80, q2=130, dq1=2, dq2=2, **tau1=5, tau2=5**, GRF=5

### Phase 7 — Non-linear PD scaling (advanced)
- **변경**: αkp가 (q-q_des) 또는 dq에 의존
- **예**: αkp(error) = base + slope·|error| → large error에서 다른 gain
- **위험**: parameter 많음, identifiability 문제 가능

### Phase 8 — Final integration + ablation
- 각 Phase의 contribution 측정
- 단순 모델로 충분한지 (Occam's razor)

---

## 📋 각 Stage 진행 시 노션 페이지 작성 규칙

### 페이지 맨 위 (필수)
1. **🅱️ Mode B 정보 callout** — PD sim 설명, 공중 hold, ctrl 입력 방식
2. **📚 Stage 개요** — 이번에 무엇을 시도하는지 (1 단락)

### 본문 (필수 — ★ 자세하게)

3. **🆚 이전 Stage 상태** — 출발점 (어디서 왔는지) 자세히
   - 이전 stage의 score, RMSE 값 명시
   - 어떤 axis 사용 중인지
   - 미해결 문제 (예: "점프 높이 over-prediction")

4. **✨ 변경 사항** — 각 axis별 ★ 매우 자세하게:
   - 📋 **From → To**: 정확한 값
   - 🔬 **물리적 메커니즘**: 변경이 물리적으로 무엇을 바꾸는가 (수식, 모델 설명, 실 robot 의미)
   - 🤔 **왜 이렇게 변경**: 가설/동기/근거 (이전 stage의 어떤 문제 해결, 어떤 논문/외부 정보 인사이트, 다른 axis와의 관계)
   - 🎮 **시뮬레이션 영향**: sim 동작 변화 (어떻게 다른지 가시적으로/dynamics에서)
   - **🌊 추가/변경에 의한 변화/영향**: 이 변경으로 인해 어떤 효과 (RMSE 어떤 변화, 점프 높이 어떻게 변하는지, 다른 axis와의 interaction)

5. **🎨 시각적 변화** — XML/render 변화 자세히 (mosaic image 비교 포함)
   - 이전 stage 대비 visual difference
   - sim 영상에서 가시 변화 (점프 trajectory, contact, 자세)

6. **💡 Why 통합** — 전체 변경의 통합 이유 (이 stage의 핵심 가설)

7. **🏁 결과** — score, RMSE (q/dq/τ/GRF), 점프 높이
   - 절대값 + 이전 stage 대비 변화 %
   - per-trial breakdown 표

8. **🔍 결과 해석** — ★ 매우 자세하게:
   - 왜 좋아졌나 (또는 왜 안 좋아졌나/악화)
   - 어떤 axis가 핵심 기여
   - 다른 axis와의 trade-off
   - 점프 높이 vs RMSE 분리 분석 (점프는 검증, RMSE가 목표)
   - 예상 vs 실제 비교 (가설 검증)

9. **📖 새 용어 자세한 설명** — 이 stage에서 등장한 모든 새 개념
10. **💎 학습 포인트** — 인사이트, generalize 가능한 패턴

### 그래프/이미지 섹션 (필수)
11. **🅱️📊 PD sim 결과 종합** — 자세한 표 (Trial별 jump/RMSE)
12. **🎬 애니메이션** — 6 trial 각각 H3 heading + GIF
    - settle → 점프 → 공중 → 착지 풀 timeline (T_after ≥ 0.8s)
    - V25 스타일: 검은 박스 없음, 흰 글자 + 검은 outline, 한글 폰트 (malgun.ttf)
    - Overlay: t, base_z (cm 바닥부터), GRF (N), Max
13. **📈 Sim vs Real 비교 그래프** — 6 trial × 4-panel (q/dq/τ/GRF)
    - **색 자동 (matplotlib auto cycle), 절대 명시 지정 금지**
    - sim/real 같은 변수 같은 색, sim은 점선 (`get_color()` 사용)
    - τ 그래프: sim = PD output, real = motor 출력 → 다른 값
14. **🦘 점프 높이 표** — bottom에서 max base_z (절대 거리)
    - 시작 자세 base_z = 19.4 cm
    - 다리 다 펴진 max = 54.8 cm
    - 점프 높이 = max base_z (보통 60-70 cm)

### 페이지 완성 후 확인 (필수)
- ⚠️ **각 페이지 만들고 나서 이미지/애니메이션 정확히 들어갔는지 직접 fetch해서 확인**
- 누락 시 즉시 재업로드
- 그래프 색이 자동 색인지 확인 (지정 색 발견 시 재생성)

### ★ Variable Base/BO Best 비교 표 (필수, GOAL7 stage 페이지 형식)

★★★ **모든 stage 페이지의 표는 "GOAL7 Base Model"과 "현재 stage BO Best"의 비교** ★★★

#### Base Model 정의 (절대 기준, 모든 stage 동일)
**GOAL7 Base Model = CAD + joint frictionloss 0.1, 다른 모든 추가 axis 0/∞:**
- **Body (CAD 값 그대로)**: M=1.02, m1=1.05213, m2=0.237, m_c=0.80898, m_p=0.14977, r1=0.05646, r2=0.05884, r_c=0.02069, r_p=0.13258, I1=0.0092344, I2=0.001805, I_c=0.0005797, I_p=0.0008858, l1=l2=0.25, l_c=0.03, l_o=0.03
- **Joint friction**: fl_hip = fl_knee = **0.1 Nm** (이것만 non-zero)
- **다른 모든 axis = 0** (또는 ∞): damping=0, stiffness=0, armature=0, fc/fs/fv=0, base_arm/fl/b_c=0, nl=0, motor_tm=∞ (즉시 응답), tau_delay=0, kappa=∞ (no saturation), bias=0, αkp=αkd=1.0 (folder 그대로)
- **Contact**: default solref/solimp, foot 단일 sphere (r=0.023m, foot_sep=0)
- **Integrator**: Euler default (RK4 변경은 stage 12+에서)

#### 표 형식

| Variable | Base (CAD+jf=0.1) | BO Best | 단위 | 의미 |
| --- | --- | --- | --- | --- |
| I1 | 0.0092 kgm² | (현재 stage best값) | kgm² | thigh inertia (CAD) |
| M | 1.0200 kg | (best값) | kg | base mass (CAD) |
| fl_hip | **0.1000 Nm** | (best값) | Nm | ★ joint frictionloss (jf=0.1) |
| arm_hip | **0.0000 kgm²** | (best값) | kgm² | rotor armature (없음 → 추가) |
| damp_hip | **0.0000 Nms/rad** | (best값) | Nms/rad | joint damping (없음 → 추가) |
| motor_tm | **∞ (instant)** | (best값) | s | ★ motor LPF (없음 → 추가) |
| kappa_h | **∞ (no sat)** | (best값) | Nm | ★ tanh saturation (없음 → 추가) |
| bias_h | **0.0000 rad** | (best값) | rad | ★ joint bias (없음 → 추가) |

- **Base column = GOAL7 Base Model 그대로 (모든 stage 동일 기준)** ★
- **BO Best column = 현재 stage의 best params (해당 stage까지 식별된 최적값)** ★
- 단위 명시
- ★ 표시 = 이 stage에서 새로 추가/변경된 axis
- 모든 GOAL8 stage 페이지 (Stage 1, 2, 3, 4, ...) 모두 같은 Base 기준 → stage 진화 추적 가능

### ★ 애니메이션 V25 스타일 (GOAL7 Stage 53 visual)

XML에 다음 visual 요소 필수:
```xml
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
  <texture type="2d" name="gp" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
           markrgb="0.8 0.8 0.8" width="300" height="300"/>
  <material name="gp" texture="gp" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
</asset>
<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
```

Animation overlay (frame 별):
- 흰 글자 + 검은 stroke (V25 스타일, 검은 박스 ❌)
- malgun.ttf 한글 폰트 (한글 깨짐 방지)
- 카메라: azimuth=135, elevation=-15, distance=1.2
- 80 frames, duration 60ms
- T_after=0.8s (착지까지 capture)
- Overlay 정보: t (ms), base_z (cm, 바닥부터), GRF (N), Max (cm)

---

## 🎓 사용자가 이해하기 어려울 수 있는 내용 (항상 추가 설명)

다음 개념들이 등장할 때 **반드시 자세한 보충 설명** (마스터용):

### BO 관련
- **BO basin**: parameter space의 local optimum 영역. narrow refine은 같은 basin 정밀화, wider exploration은 새 basin 찾기
- **warm start**: 이전 best 근처에서 BO 시작. 수렴 빠름. high-dim BO에서 필수
- **multi-seed verification**: 같은 setting 다른 random seed → 같은 결과면 global confirmed

### PD/모터 관련
- **αkp, αkd**: folder 표기 PD gain에 곱하는 scaling factor. 실 robot 진짜 PD가 표기와 다를 수 있어서
- **PD-dependent scaling**: αkp가 kp_folder에 linear 변화 (Stage 23). slope ≠ 0이면 firmware nonlinear
- **a_hat 5-param**: AK80-9 paper motor model. 5 term (a0~a4)으로 motor 비선형 응답 표현
- **motor LPF**: 1차 저역통과 필터. motor의 전기/기계 응답 시간 모델 (~8.37ms)
- **tau_scale**: 실측 토크 sensor calibration error 보정 (5-12% underread)

### 시뮬레이션 관련
- **RK4 integrator**: 4차 정확 ODE solver. Euler 대비 100배 정확
- **Stribeck friction**: 3-term friction (Coulomb + viscous + static peak)
- **cone elliptic vs pyramidal**: contact friction direction 표현 방식
- **contact margin**: ground 가까이서 soft contact 시작 거리
- **dt sensitivity**: Mode A는 dt에 sensitive, Mode B는 robust (PD가 noise 흡수)

### Foot/Contact 관련
- **foot 2-point (heel/toe)**: 단일 sphere → 2개 sphere (빨강 heel + 초록 toe). stance rolling 가능
- **foot_sep**: heel/toe 분리 거리 (예: 0.005m = 발 길이 1cm)
- **solref [tc, d]**: contact spring time constant + damping ratio
- **solimp**: contact impedance (deformation에 따른 stiffness 변화)

### 이번 GOAL8에서 새로 등장할 개념
- **Torque saturation**: 모터 최대 출력 토크 한계 (±18 Nm)
- **D term LPF**: derivative noise filter (firmware)
- **Gear backlash**: 기어 톱니 dead zone
- **per-phase PD**: stance vs flight 다른 gain
- **residual learning**: NN으로 modeling 오차 보정

---

## 🛠️ 코드 규칙 (절대 준수)

### Sim
- `run_trial_modeB.py` 사용 (공중 hold + dq_des=0)
- `T_settle = 0.2`, `T_after = 0.8` (착지까지)
- Mode B sim 토크 log: V20 convention PD output

### 점프 높이 측정
- **정의**: `max(base_z) (바닥 z=0부터 절대 거리)`
- **NOT**: `max - base_z_init` (시작값에서 delta가 아님)
- 시작 자세 base_z ≈ 19.4 cm (다리 굽힘)
- 다리 다 펴진 max ≈ 54.8 cm
- 실제 점프 (공중 상승 포함) ≈ 60-70 cm

### Plot 색
- ❌ `'b-'`, `color='red'`, `ls='--' color='blue'` 등 색 명시 금지
- ✅ matplotlib auto color cycle 사용
- ✅ sim/real 매칭 시 `get_color()` 패턴:
  ```python
  l = ax.plot(t_real, real['q1'], lw=2, label='q1 real')[0]
  ax.plot(t_sim, q1_sim, lw=1.5, ls='--', color=l.get_color(), label='q1 sim')
  ```

### 애니메이션
- malgun.ttf 한글 폰트
- 검은 배경 박스 ❌
- 흰 글자 + 검은 outline (`stroke_width`)
- 80 frames, duration 60ms
- 카메라: azimuth=135, elevation=-15, distance=1.2

### Notion 업로드
- `file_uploads` API (3-step: create → send → image block)
- imgur 등 외부 호스팅 절대 금지
- 각 trial별 H3 heading + image block 분리 (V25 스타일)
- 페이지 완성 후 fetch로 누락 확인

---

## 📐 검증 기준 (Stage별 평가)

각 Stage 결과 평가 시:

### 1차 metric (목적)
- **q1 RMSE** < 0.025 rad (target: ~0.020)
- **q2 RMSE** < 0.045 rad (target: ~0.035)
- **τ1 RMSE** < 5 Nm (target: ~3 Nm)
- **τ2 RMSE** < 5 Nm
- **GRF RMSE** < 20 N (target: ~15 N)

### 2차 metric (검증 — 목표 아님)
- 점프 높이: 6 trial에서 실측과 비슷한 범위 (60-70 cm)
- 큰 outlier 없음
- 6 trial 간 consistency (PD-dep 정확)

### 종합 score (BO objective)
- 새 weighted score: `Q1·q1 + Q2·q2 + DQ1·dq1 + DQ2·dq2 + T1·tau1 + T2·tau2 + G·grf`
- 시작값 가이드: q1=80, q2=130, dq=2, **tau=5**, grf=5
- weighting BO 자체에 추가 가능

---

## 🎯 최종 목표

### 정량 목표
- **Mode B score ~250대** (Mode A 수준 근접)
- **q1 RMSE ~0.020, q2 RMSE ~0.035, τ RMSE ~3 Nm, GRF RMSE ~15 N**
- 6 trial 모두 일관성

### 정성 목표
- **디지털 트윈 완성도**: sim에서 본 PD 응답이 실 robot에서 그대로 재현
- **모델 generalize**: 다른 PD gain, 다른 trajectory에도 적용 가능
- **물리적 정합성**: 각 axis가 실 robot 물리적 의미와 일치

### 실 robot 배포 가능성 검증
- 새 PD gain trial에서도 sim ≈ real
- 새 q_des trajectory에서도 매칭

---

## 🚦 Stage 시작 절차

각 Stage 시작 시 항상:

1. **이전 Stage 상태 점검** — RMSE, score, best params 확인
2. **이번 Stage 변경 사항** 명확히 정의 (어떤 axis 추가/변경)
3. **변경 이유** 문서화 (Phase 어떤 단계인가, 가설은 무엇인가)
4. **BO 실행**:
   - warm start (이전 best params 근처)
   - n_trials ≥ 500 (high-dim 권장)
   - multi-seed verification (seeds=42/99/1234)
5. **결과 분석**:
   - q/dq/τ/GRF RMSE 측정
   - 점프 높이 측정 (검증 metric)
   - 6 trial 별 분석
6. **노션 페이지 작성** (위 규칙 따라)
7. **이미지/anim 누락 확인** (페이지 fetch)
8. **메모리 저장** (성공/실패 finding)
9. **commit** (auto preference)

---

## ⚡ 빠른 시작 명령

다음 작업으로 GOAL8 시작:

```bash
# 1. Phase 1 (BO 재실행) 첫 stage 진행
python -X utf8 goal8_stage1_BO_pd_sim.py
# - Stage 39 baseline (Mode B FINAL) 시작점
# - 공중 hold PD sim score function
# - n_trials = 1000, warm start from Stage 39 best params

# 2. 결과 분석
python -X utf8 analyze_goal8_stage1.py

# 3. 노션 페이지 생성 (위 규칙 따라)
python -X utf8 create_goal8_stage1_page.py
```

---

## 📌 핵심 reminder (출력 전 항상 자문)

매 stage 진행 시:
1. ✅ q/dq/τ/GRF 매칭이 목적인가? (점프 높이 매칭이 아님)
2. ✅ 이번 변경 이유가 명확한가?
3. ✅ 새 용어 자세히 설명했는가?
4. ✅ 그래프 색 자동인가 (지정 ❌)?
5. ✅ 애니메이션이 V25 스타일인가?
6. ✅ 점프 높이는 바닥부터 max base_z로 측정했는가?
7. ✅ 페이지 만든 후 이미지/anim 누락 확인했는가?
8. ✅ 이전 stage 대비 무엇이 변했는지 명확히 설명했는가?

**Mission start.**
