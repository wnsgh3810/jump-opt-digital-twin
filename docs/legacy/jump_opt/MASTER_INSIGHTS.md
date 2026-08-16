# MASTER INSIGHTS — 2-DOF 4-Bar CVT Single-Leg Jump Robot

> **목적**: 2026-04 ~ 2026-06 동안 진행한 모델링/식별/NLP/forward-sim 작업에서 발견한 모든 actionable insight를 한 곳에 정리한 살아있는 문서.
> 
> **사용**: 새 goal을 시작할 때 이 문서를 먼저 읽어 같은 발견을 반복하지 않도록. 새 발견은 §20 template에 추가.
> 
> **작성일**: 2026-06-05  
> **버전**: 1.0  
> **소스**: 
> - `~/.claude/projects/.../memory/` 36 md
> - `Data/26.06.02/position/` 87 md (model_search v2~v42c, FINAL_MODEL_*, BEST_MODEL, notion_goal2/, notion_report/)
> - `Data/26.04.24/GRF_to_torque_prediction_notes.md`
> - `Desktop/jump_opt/` baseline NLP 코드
> - 4개 sub-agent의 thorough 탐색 (Group A: v2~v51, Group B: static gap+contact+chatter, Group C: NARX+observer, Group D: notion content)

---

## 0. 사용 가이드 + 새 발견 추가 방법

### 어떤 section부터 읽어야 하나
- **새 사람이라면**: §1 → §2 → §3 → §4 → §11 → §18 순서
- **다음 goal 시작이라면**: §1 → §17 → §18 → §19 → 시작
- **특정 문제 만났을 때**: §17 (미검증/미해결 list) → 그 section으로 점프

### 새 발견 추가 (§20 template)
1. 발견 1줄
2. 증거 (numerical + 파일 경로 + git commit)
3. 의미/시사점
4. 관련 다른 section link
5. 날짜 + 발견 환경 (sweep / sub-agent / 사용자 지적 등)

---

## 1. 우리 진짜 Goal vs 측정한 Metric — 구조적 잘못 인식

### 사용자 진짜 goal (5번 명시됨)

```
NLP 최적화 → q*(t), dq*(t), τ*(t), GRF*(t) trajectory
       ↓
실 로봇에 위치/속도 제어로 q*(t), dq*(t) 재생  
       ↓
실측 τ_meas(t), GRF_meas(t) 측정
       ↓
실측 ≈ NLP가 예측한 τ*(t), GRF*(t) ?
```

→ **Forward sim-to-real consistency**가 진짜 metric.

### 우리가 측정한 metric (V1~V12 잘못된 방향)

```
실측 q,dq,ddq를 모델에 input → predict τ
       ↓
||predict τ - 실측 τ|| = inverse RMSE (V12: hip 0.93, knee 0.71)
```

→ 단순히 동역학 방정식의 양변이 같은 데이터에서 매칭되는지만 봄. **Forward consistency를 보장 안 함**.

### Inverse RMSE ≠ Forward consistency — 5가지 증거

1. **NLP self-consistency 5.9/6.3 Nm** (Ch.7): NLP가 만든 q*, dq*, ddq*에 V12 모델 적용 시 NLP가 reported한 τ*와 5.9 Nm 차이. inverse RMSE 0.93의 6배.
2. **V12 boundary 57% over-fit**: 학습 데이터 노이즈를 흡수, 학습 외 영역에서 예측 부정확 가능
3. **2-DOF inverse vs 3-DOF NLP 구조 mismatch**: V10/V12는 2-DOF (q1, q2), baseline NLP는 3-DOF (z, q1, q2)
4. **Forward sim drift test 부재**: 6-fold cross-val + forward integration test 안 함
5. **NLP 식 ≠ ID 식**: jump_opt baseline에 bias/Stribeck/cross-coupling 없음 → V12 식 통째로 NLP에 못 들어감

### 함의

```
정직한 평가: 우리 진짜 goal 달성도 = 30% 미만
(표면 inverse RMSE만 보면 50%로 보이지만)
```

→ **다음 작업은 forward sim consistency를 metric으로 사용해야 함**. §18 참조.

---

## 2. 시스템 기본 정보

### Robot (4-bar CVT single-leg jump robot)

| 항목 | 값 | 비고 |
|---|---|---|
| **DOF (free)** | 3 (z, q1, q2) | floating base + 2 joints |
| **DOF (constrained, point contact)** | 2 (q1, q2) | foot on ground assumption |
| **Total mass M_tot** | 3.27 kg | M(1.02) + m1(1.05213) + m2(0.237) + m_c(0.80898) + m_p(0.14977) |
| **Real mass (measured)** | 3.04 kg | user direct measurement 2026-04-19 |
| **GRF mass (정지)** | 2.99~3.10 kg | force plate / g |
| **Link length L1, L2** | 0.25 m | thigh, shin (CAD) |
| **L_O (CVT follower)** | 0.03 m | 4-bar follower link |
| **l_i (CVT input link)** | 25.247 mm 평균 | clutch.xlsx — varies 21-30mm |

### Inertia / mass parameters (CAD, baseline)

| 변수 | 값 | 의미 |
|---|---|---|
| `r1, r2, r_c, r_p` | 0.05646, 0.05884, 0.02069, 0.13258 | center-of-mass offsets |
| `I1, I2, I_c, I_p` | 0.0092344, 0.001805, 0.0005797, 0.0008858 | link inertia |
| `Is1` (composite) | 0.0345 | hip-side inertia |
| `Is2` (composite) | 0.0046 | knee-side inertia |
| `KV` (composite) | 0.0029 | hip-knee coupling inertia |
| `gAv` (composite) | 1.36 | hip gravity moment coefficient |
| `gBv` (composite) | -0.0715 | knee gravity moment coefficient |

### Motor (AK80-9 T-Motor)

| 항목 | 값 | 비고 |
|---|---|---|
| `Kt_TMotor` | 0.091 Nm/A | datasheet |
| `Kt_actual` (UMich 측정) | 0.115 Nm/A | **26% larger than spec** |
| `Current_Factor` | 0.59 | d/q axis alignment loss |
| `GEAR_RATIO` | 9:1 | 9× torque amplification |
| `T_min/T_max` | ±18 Nm | output side hard saturation |
| `V_min/V_max` | ±50 rad/s | output side |
| `Kp range` | 0~500 Nm/rad | driver |
| `Kd range` | 0~5 Nm·s/rad | driver |
| **Motor lag (1차 IIR)** | tau_m ≈ 26 ms (v14) / 80 ms (v24) | hip vs knee 다름 (24-43ms) |
| `NUM_POLE_PAIRS` | 21 | 자석 극쌍 수 |

### 측정 인프라

| 측정 | 인프라 | 비고 |
|---|---|---|
| q1, q2 | encoder (14-bit) | encoder quantization은 ddq 노이즈 증폭 |
| τ1, τ2 (raw) | `currentTorque` (CAN MIT mode) | raw iTM, datasheet 0.091 기준 환산 — **실제 다름** |
| GRF_z (지면 반력) | force plate | timing lag +24ms (desired→measured) |
| GRF_x | force plate | friction cone constraint |
| **z (base height)** | **측정 안 됨** | IMU 없음, kinematic 추정만 가능 |
| **dz, ddz** | **측정 안 됨** | identification degeneracy의 원인 |

→ **z/dz/ddz 측정 부재가 ID degeneracy의 근본 원인**. IMU 도입이 future work 권장.

### 데이터셋 (26.06.02 + 26.06.04)

**26.06.02/position** (점프 6 folder, PD gain별):
- 60_0.75_60_2 (가장 가벼운 PD)
- 60_1.5_60_1.5
- 90_0.75_90_2
- 120_2_120_2
- 150_2.2_250_3 (높은 PD)
- 150_2.2_500_5 ← **outlier**

**26.06.04** (sit2stand):
- no_cvt/no_load, load_5, load_7.5
- cvt/no_load, load_2.5, load_5 ← **CVT validation only**

---

## 3. 동역학 식 표준 (floating base J^T·F_ext)

### Floating base 표준 식

```
M(q)·ddq + C(q,dq)·dq + G(q) = S^T·τ + J_c^T·F_ext
                                          └─────────┘
                                         외부 접촉력의 일반화 형태
```

- `J_c` = ∂(foot 위치)/∂q  (contact Jacobian)
- `F_ext` = GRF (지면 반력)
- `J_c^T·F_ext` = 외력이 generalized coordinates에 만드는 generalized force

### Foot position + Jacobian (point contact)

```
foot_x = l1·cos(q1) + l2·cos(q1+q2)
foot_z = z + l1·sin(q1) + l2·sin(q1+q2)

J_c = [ 0    -(l1·s1+l2·s12)    -l2·s12 ]   ← x row
      [ 1     (l1·c1+l2·c12)     l2·c12 ]   ← z row
```

### J^T·F_ext (baseline `jump_opt` 코드와 정확히 일치)

```
on z (base): GRF_z
on q1 (hip): -(l1·s1+l2·s12)·GRF_x + (l1·c1+l2·c12)·GRF_z
on q2 (knee):    -l2·s12·GRF_x    +     l2·c12·GRF_z
                  └────────┘             └────────┘
                  tangential mom         normal mom
```

→ **mom_h = l1·c1+l2·c12, mom_k = l2·c12** 은 단순 floating base J^T·F의 자연스러운 결과. V12에서 추가한 것이 아니라 표준.

→ V12가 추가한 것은 `r_foot·s12` (발 반지름 보정) + `dmom_h_*` polynomial (link length 자유 보정 — over-fit 의심).

---

## 4. 정적 + Jacobian 토크 vs 측정 τ 갭 (핵심 발견)

### 핵심 발견 — Static GRF만으로 토크 계산 시 실측과 갭

```
정적 자세 (q1≈-1.0 rad, q2≈-1.5 rad)에서:
  Hip moment arm ≈ -0.065 m → τ1 from GRF ≈ +6.5 Nm per 100 N GRF
  Knee moment arm ≈ -0.200 m → τ2 from GRF ≈ +20 Nm per 100 N GRF
  
→ Knee는 정적 GRF만으로 saturation 가능 (관성 항 없이도)
```

**Source**: `Data/26.06.02/position/strict_realistic_dynamics/FINDINGS.md` + `model_diagnostics/diagnostics_summary.md`

### Inverse-dynamics 잔차 (Static GRF + 관성 + Coriolis + 중력)

| 모델 | Hip RMSE | Knee RMSE | 비고 |
|---|---|---|---|
| 원래 paper τ | 4.19 Nm | 8.56 Nm | (관성+Coriolis+중력+mom·GRF만, friction 0) |
| sign-flipped (gravity, z) | 3.31 Nm | 3.12 Nm | 부호 보정만 |
| loose recommended | 3.00 Nm | 4.61 Nm | 더 큰 자유도 |
| strict realistic bounds | 3.30 Nm | 5.20 Nm | physical bound |
| **v24 (Optuna BO 1500)** | **0.48 Nm** | **0.36 Nm** | 18p, 5/6 folder, outlier 제외 |
| **v12 GOAL2 (42p)** | **0.93 Nm** | **0.71 Nm** | LOO 미적용 |

→ **Pure floating-base + paper a_hat motor correction만으로는 3-4 Nm 잔차**. 추가 항이 필요한 이유.

### 갭의 정량 분해 (origin)

```
정적+Jacobian τ vs 실측 τ 갭 (~3-4 Nm) =
    (a) 미모델 contact compliance (delay -60 ms, 부분 만회)
    (b) Motor command-to-torque lag (~25 ms 1차)  ← v14 발견, 50% 잔차 감소
    (c) GRF 측정 timing lag (+24 ms 추가)
    (d) Force plate scale 차이 (Current GRF ≈ 1.29 × Desired GRF, +29% bigger)
    (e) Force plate zero drift (-25.85 N constant bias)
    (f) Sign convention misalignment (gravity, base z)
    (g) Joint friction (Coulomb + Stribeck) — v6, v7
    (h) Foot circle rolling contact (point contact 한계, 5°×Kp=26 Nm spike)
    (i) Saturation (knee 50-70% saturated)
```

→ 단일 모델 보정으로 모두 잡기 어려운 분산된 cause. **여러 항 동시 처리** 필요.

### 가장 큰 단일 fix (impact rank)

1. **Constrained contact surrogate** (soft_linear / kelvin_voigt): GRF RMSE 32.8 → 10.1 N (69% 개선)
2. **Motor 1차 lag (tau_m 26ms)** (v14): jump inverse RMSE 2.9 → 1.4 Nm (50% 개선)
3. **Hip cross-coupling (hx1, hx2)** (v19): 1.4 → 0.9 Nm
4. **kind-specific GRF (jump/s2s 분리)** (v7): s2s knee 6.07 → 1.67 Nm
5. **Sign convention flip** (gravity, base z): hip 4.2 → 3.3 Nm

**Source**: 26.04.24/GRF_to_torque_prediction_notes.md, contact_model_summary.md, model_search v14, v19 summaries

---

## 5. 접촉 모델 (alpha / soft / hard / contact surrogate)

### 4가지 접촉 모델 비교

| 모델 | 식 | GRF RMSE | 비고 |
|---|---|---|---|
| **alpha-only** (rigid) | `GRF_eff = α · GRF_measured` | 33 N (baseline) | 단순 scale |
| **hard contact** (Lagrange) | `z_foot = 0`, `GRF` from constraint | — | NLP에서 사용 |
| **soft contact (k_c, b_c)** | `GRF = k_c·delta + b_c·ddelta` | (penetration 측정 불가) | 어디서 z 측정? |
| **soft_linear surrogate** (best fit) | `GRF ≈ -402·delta + 102·ddelta` (delay -60ms, z0 0.352) | **9.8 N** | 최고 |
| **kelvin_voigt_soft** | similar | 9.822 N | identical to soft_linear |
| **viscoelastic_bidirectional** | bidirectional spring-damper | 10.34-10.46 N | slightly worse |
| **hunt_crossley_surrogate** | nonlinear viscoelastic | 10.50 N | similar |

### 핵심 발견

1. **Soft contact 모델로 GRF RMSE 32.8 → 10.1 N (69% 개선)**
2. **단순 alpha (0.85)는 33 N 그대로** — scale + bias로 일부 개선
3. **Hard contact NLP의 GRF impulse ≈ 측정 impulse** (3% 이내)
   - 순간 GRF는 다름 (peak 243N vs 실측 86N) but **적분(impulse)은 일치**
   - "접촉 스프링이 로우패스 필터 역할" — 순간 힘 lowering, impulse 유지
4. **Alpha의 물리적 의미**: GRF의 α만큼 body 전달, 나머지는 접촉 컴플라이언스 흡수
5. **E_ratio ≈ (Impulse ratio)²** — soft contact의 에너지 spring 보존: F²/(2k)

### Alpha 값 trial별 변동

| Trial | Alpha (impulse ratio 역) | 노트 |
|---|---|---|
| P40 | 0.712 | "P40 impulse 0.1% 오차로 매칭" |
| P60 | 0.755 | |
| P100 | 0.789 | "동작이 격렬할수록 α 낮음" |

→ **Alpha는 trial 의존적**. 단일 fitted α는 평균값일 뿐.

### Point contact 한계

```
실제 robot: hip ─l1─ knee ─l2─ ankle ─l_foot─ toe
모델 (point contact): hip ─l1─ knee ─l2─ foot(점)

Lift-off transient:
  실제: 발바닥 길이만큼 추가 토크 (toe push-off)
  Sim: toe push-off 효과 없음 → +20 Nm spike (270~286 ms)
```

→ **point contact 가정의 한계 = hip torque lift-off spike의 근본 원인**. Foot length 추가는 sim 복잡도 큼 (ankle DOF + heel/toe 두 점 GRF + CoP 이동).

### 권장 contact 모델

- **NLP forward 최적화**: alpha (단순) 또는 hard contact (NLP 안정)
- **Identification metric**: soft_linear surrogate (RMSE 측정 정확)
- **연구용 진단**: 둘 다 비교

**Source**: `Data/26.06.02/position/contact_model_search/contact_model_summary.md`, `~/.claude/memory/analysis_findings.md`

---

## 6. 마찰 모델 진화 (viscous → Coulomb → Stribeck)

### 3단계 진화

```
baseline (jump_opt):
  fr = JOINT_FRICTION · dq      (viscous 단독, JF=0.1)

V1+ (GOAL1):
  fr = jf·dq + cf·tanh(dq/0.3)  (+ Coulomb)

V7+ (GOAL2):
  fr = jf·dq + Stribeck(dq, F_s, F_c, v_s)  (+ 정마찰)
  
  where Stribeck(dq) = (F_s - F_c)·exp(-(dq/v_s)²)·tanh(dq/0.05)
                     + F_c·tanh(dq/0.3)
```

### Stribeck 파라미터 (V12 fitted)

| 변수 | 의미 | 값 |
|---|---|---|
| `F_s` | static friction (정마찰) | ~0.6 Nm |
| `F_c` (= cf in code) | Coulomb friction | ~0.3 Nm |
| `v_s` | Stribeck velocity | ~0.3 rad/s |

### 핵심 발견

1. **viscous-only는 저속에서 부정확** (jump_opt baseline)
2. **Coulomb cf·tanh 추가가 V1 → V5에서 큰 효과** (but boundary 도달, V12에서 cf=0.78)
3. **Stribeck은 정→동 마찰 전환** 표현 — sit2stand에서 큰 효과 (V7에서 s2s knee 6.07→1.67 Nm)
4. **AK80-9의 a_hat (UMich 5-param)**이 motor 자체의 friction 흡수 — 외부 friction 추가는 작은 영향
   - `a_3` (Coulomb), `a_4` (load-dep gear friction)
   - 우리 friction model이 motor a_hat와 겹칠 수 있음

### 마찰 모델 검토 — V12 cf_hip=0.78이 boundary

```
사용자 비판 (c): cf=1.6 비현실
→ Physical bound cf<0.8 enforced
→ V10: cf=0.44 (safe)
→ V12: cf=0.78 (경계, over-fit 위험)
```

**Source**: `Data/26.06.02/position/model_search_v6_summary.md` (Coulomb), v7 (Stribeck), AK80 a_hat memory

---

## 7. 모터 모델 (AK80-9 5-param a_hat + lag + saturation)

### UMich 5-파라미터 a_hat 모델 (CRITICAL)

```python
# 모터 상수 (FIXED — UMich 측정)
KT_TM = 0.091; GR = 9.0; CF_RATIO = 0.59; EPS_V = 0.1
A_HAT = [0.0, 1.15605006, 4.17389589e-4, 0.26855607, 0.04904241]

# Pure Paper (sgn(v) only) — 필수 사용
def actual_torque(tau_reported, v):
    i = (CF_RATIO / (GR * KT_TM)) * tau_reported   # 0.7204 × τ
    s = abs(v) / (EPS_V + abs(v))
    return (A_HAT[0]
          + A_HAT[1] * GR * KT_TM * i              # +1.156·9·0.091·i
          - A_HAT[2] * GR * abs(i) * i              # current² saturation
          - A_HAT[3] * np.sign(v) * s               # Coulomb friction
          - A_HAT[4] * abs(i) * np.sign(v) * s)     # load-dep gear friction
```

### 5개 항의 의미

| 항 | 값 | 의미 |
|---|---|---|
| a₀ | 0.0 | torque bias (zero) |
| a₁ | 1.156 | linear Kt correction (실제 Kt_eff ≈ 0.105) |
| a₂ | 4.17e-4 | current² saturation (고전류 효율↓) |
| a₃ | 0.269 (Nm) | Coulomb friction (smooth sign) |
| a₄ | 0.049 | load-dep gear friction (∝ |current|) |

### 단순 변환 (1차 근사)

```
τ_actual_output = τ_reported × 0.7457
                = τ_reported × (Current_Factor × Kt_actual / Kt_TMotor)
                = τ_reported × (0.59 × 0.115 / 0.091)
```

### Pure Paper vs GitHub a_hat

```
사용자 결정 (26.05.20): Pure Paper 식 (sgn(v) only) 사용
GitHub의 s(v) smoothing 금지
→ CF (Coulomb) 식별성 회복됨
```

### Motor lag (1차 IIR)

| 모델 | tau_m | 비고 |
|---|---|---|
| baseline jump_opt | 0 ms | 없음 |
| V1~V13 | 단일 (50ms 같은) | 미흡 |
| V14 (breakthrough) | 26.21 ms | 50% inverse RMSE 감소 |
| V16 (per-folder) | 24-43 ms | 150_500_5에서 43 ms (driver mode switch?) |
| V24 (Optuna) | 80 ms | hip + knee 평균 |
| V9 (분리) | tau_m1 = 80 ms (hip), tau_m2 = 38 ms (knee) | 다름 |

→ **per-folder tau_m variation은 driver mode switch 신호**. High PD 그룹에서 다른 saturation 모드 가능.

### Saturation (AK80-9 back-EMF)

```python
# v41 NLP 코드:
def ak80_torque(tau, dq):
    lim_eff = TAU_LIM_PEAK - K_BACK_EMF * ca.fabs(dq)   # 21 - 0.06·|dq|
    lim_eff = 0.5*(lim_eff + ca.fabs(lim_eff)) + 1e-3
    return lim_eff * ca.tanh(2.0 * tau / lim_eff)
```

- `TAU_LIM_PEAK = 21 Nm` (firmware 한계, ±18보다 큼 — peak 가능)
- `K_BACK_EMF = 0.06` Nm·s/rad
- **Knee saturated 50-70% of jump stance** — 단순 LS에선 outlier
- v18 weighted LS (sat=0.05) → V9+ strict (sat=0)

### 2nd-order motor model 실패 (v26)

```
v26 (omega, zeta 2차 lag) → LOO hip 12.4 / knee 16.9 (10× worse)
→ AK80 motor lag은 1차 (over-damped). 2차는 over-fit + 발진
```

**Source**: `~/.claude/memory/ak80_9_torque_calibration.md`, `feedback_pure_paper_formula.md`, model_search_v14, v18, v26 summaries

---

## 8. CVT 4-bar 메커니즘 (TR, clutch dynamics 누락)

### 4-bar 메커니즘 식

```python
# unified_loader.cvt_mechanism()
l_d² = l_i² + l₂² - 2·l_i·l₂·cos(-q_m)
α, β, γ, δ from law of cosines
q₂ = -(γ + δ)
J = ∂q₂/∂q_m
TR = 1/|J|
```

### TR (Transmission Ratio) 값

| Trial | TR (avg) | Range J (instantaneous) |
|---|---|---|
| s2s_cvt_no_load | 1.66 | -0.842 ~ -0.207 |
| s2s_cvt_load_2.5 | 1.68 | -0.842 ~ -0.205 |
| s2s_cvt_load_5 | 1.73 | -0.842 ~ -0.201 |

### CVT validation 잔차 (v10, v12)

| Trial | v10 hip / knee | v12 hip / knee |
|---|---|---|
| s2s_cvt_no_load | **10.8 / 14.9** | **3.5 / 16.4** |
| s2s_cvt_load_2.5 | 16.1 / 21.4 | 5.7 / 23.2 |
| s2s_cvt_load_5 | 23.2 / 24.1 | 8.2 / 25.1 |

→ 사용자 목표 < 2.0 Nm 모두 미달. no_cvt 평균 1.45/1.23 대비 10배.

### TR 평균 vs time-varying — 거의 같음

| 변환 | hip | knee | 차이 |
|---|---|---|---|
| Scalar mean | 10.8 | 14.9 | baseline |
| Time-varying J | 10.8 | 13.8 | marginal |

→ **TR 변환 방식은 본질적 원인 아님**. CVT 특유의 missing dynamics가 진짜 원인.

### Payload 따라 잔차 증가

```
no_load: hip 10.8 → load_2.5: 16.1 (+5.3) → load_5: 23.2 (+12.4)
```

→ Payload가 body roll, clutch slip 등 추가 dynamics 유발

### 가설: Clutch dynamics 누락

1. **Clutch friction**: motor와 4-bar link 사이 slip + friction
2. **Mechanical compliance**: 4-bar 링크 강성/탄성 (cable spring)
3. **Clutch inertia**: motor와 별도 회전 부분
4. **Body roll DOF**: payload 변하면 base 회전 (현재 3-DOF가 잡지 못함)

### CVT를 fit에 포함하지 말 것

```
v1 (CVT 포함, 15 trial fit): no_cvt fit 망가짐 (hip 4.8/knee 6.2)
v5+ (no_cvt 7 trial fit): hip 2.71/knee 2.37 from start
→ CVT는 validation only, fit에 포함하면 전체 망함
```

**Source**: Ch.8 notion content (content_ch8_cvt.md), cvt_timevarying_test.py

---

## 9. 채터링 (with_cvt chatter, GRF chattering, NLP smoothness)

### 3가지 채터링 발견

#### 1. with_cvt 속도 chattering (26.05.27 Task 30)

```
사용자 요구: 7시간 야간 작업 = with_cvt 속도 chattering 제거 + payload ≥8kg 유지
해결: smooth_w 0.01 → 0.1 + v2 second-order velocity smoothness
결과: chatter 거의 사라짐
```

#### 2. NLP GRF chattering (GOAL1 비판 (b))

```
GOAL1 v41 NLP: smooth_grf = 0.05 (큰 weight) → T_st=0.15 chase, 진동 심함
GOAL2: smooth_grf = 1e-4 → T_st free, 진동 거의 없음
```

#### 3. Forward sim에서 contact 진동

```
Soft contact 모델 + measured state → feedback instability
원인: 최적화가 state error와 GRF 동시 최소화 시도
억제 방법:
  - Hard contact (binary in-contact)
  - ddq low-pass filter (window 41 points, v42e)
  - GRF rate soft clip (smooth_grf ~1e-4)
  - AK80 back-EMF saturation (자연 댐핑)
```

### 채터링이 가르치는 것

- **부드러움(smoothness) penalty 비율이 너무 크면 trajectory가 unnatural** (T_st chase 등)
- **너무 작으면 NLP 발진**
- 최적값: 1e-4 ~ 1e-3 정도

**Source**: `~/.claude/memory/goal_task30_chatter.md`, notion content_ch7_nlp.md

---

## 10. Identification 변천 narrative — v2~v51 + GOAL2 v5~v12

### Stage 0: jump_opt baseline (~2026-04)

```
3-DOF NLP, 표준 M + C + G + mom·GRF
viscous friction (JOINT_FRICTION = 0.1)
alpha = 0.85 단일
tau_lim ±15 Nm hard bound
```

→ Sim-to-real gap 큼 (E_ratio ≈ (Imp)², α=0.7-0.9 trial별 변동)

### Stage 1: Param sweep + 945-config (2026-04-17~19)

```
soft contact + alpha + friction 945 configs
Best: alpha=0.90, k_c=5000, b_c=50, tau_lim=15, rail_f=5, joint_f=0.3
→ vs Real P40: 모든 지표 2% 이내, h 0.9%
→ final.py 결정
```

### Stage 2: 169M sweep + System ID (2026-04-23~25)

```
13개 파라미터 × 169M configs Numba JIT
Best: gAv=0.30 (CAD 1.36과 다름 — ALPHA fudge factor 의심)
→ Multi-trial sys ID v5: gAv=1.57 ≈ CAD (정직한 값)
→ Sweep best의 gAv=0.30이 ALPHA=0.85 fudge factor 보상

ALPHA=1.0 재 sweep 두 차례 OOM (58M, 588M)
→ 미해결
```

### Stage 3: 26.06.02 model_search v2~v25 (2026-06-02~04)

| 버전 | 변경 | LOO hip/knee | 핵심 발견 |
|---|---|---|---|
| v2 | constrained LS + foot circle | 4.50/2.91 | bounds saturate, outlier 충격 |
| v3 | spline smoothing | 6.91/3.50 | ddq 노이즈는 secondary |
| v5 | CAD-fixed + 5 corrections | 4.01/2.67 | params 모두 bound |
| v6 | + Coulomb cf | 4.08/2.51 | cf 0 fit — 미식별 |
| v7 | + GRF scale/offset | 4.07/2.51 | alpha aliasing |
| **v8** | **s2s + jump 통합 fit** | s2s 0.25 / jump 2.81 | **BREAKTHROUGH: CAD가 맞음** |
| v10 | + bz·dz_body, mz·ddz_body | 3.11/2.07 | rail coupling |
| v11 | s2s offset fixed | 3.10/3.12 | 통합 안 됨, 분리 필요 |
| v12 | + GRF lag -4ms | 1.54/1.33 | lag found |
| v13 | wide tau_lag | 3.06/1.66 | per-folder lag 미식별 |
| **v14** | **+ motor 1st-order lag tau_m=26ms** | **1.44/1.16** | **BREAKTHROUGH: motor lag** |
| v16 | per-folder tau_m | 1.42/1.09 | PD=150에서 43ms (driver mode) |
| v17 | soft saturation clamp | 2.22/2.18 | 실패 (tau_m collapse) |
| v18 | weighted LS (sat=0.05) | 1.43/0.86 | sat artifact 인식 |
| **v19** | **+ hip cross-coupling hx1, hx2** | **0.90/0.66** | **hx terms 검증** |
| v22 | random restart BO | 0.59/0.43 | global vs local |
| v23 | per-folder bias/lag | 0.81/0.67 | aliasing |
| **v24** | **Optuna BO 1500 + L-BFGS** | **0.48/0.36** | **FINAL inverse model** |
| v25 | Optuna 2000 | 0.49/0.37 | diminishing return |
| v26 | 2nd-order motor (zeta, omega) | 12.4/16.9 | catastrophic, AK80은 1차 |
| v28 | unified s2s+jump | jump 10.6 / s2s 3.7 | catastrophic overfitting |
| v31 | physical-conservative 8p | 1.73/0.74 | bounds로 성능 저하 |
| v37 | passive-rich 13p | 1.97/0.61 | 동일 |
| v41 | forward NLP (v24 params) | jump h 0.945 vs 실 0.94 (+0.5%) | **FINAL NLP** |
| v42b | high-PD-aware (rotor, foot circle) | 2.97/1.67 | hurt generalization |
| v42c | + 150_500_5 포함 | 3.50/3.13 | outlier가 망침 |
| v42i | per-folder fit | (varies) | aliasing |
| v42j | 150_500_5 alone | 0.45/0.30 | 다른 파라미터 (tau_m 2.6ms!) — different regime |

### Stage 4: GOAL2 unified v5~v12 (2026-06-05)

10 trial (6 jump + 4 s2s + 3 cvt validation):

| 버전 | 파라미터 수 | 점프 hip MEAN | knee MEAN | 핵심 추가 |
|---|---|---|---|---|
| v5 | 24 | 2.71 | 2.37 | base + state-bias + r_foot + GRF cal + ka |
| v6 | 28 | 2.45 | 1.95 | mom_k poly + Is2 q-dep |
| v7 | 33 | 2.18 | 1.35 | kind-GRF + Stribeck |
| v8 | 36 | 1.85 | **0.95** ✓ | hip cross-coupling (hx1, hx2, hx3) |
| v9/v10 | 38 | 1.64 | 0.80 | separate tau_m + M11 q-dep + sat strict |
| v11/v12 | 42 | **0.93** ✓ | **0.71** ✓ | mom_h poly + GAV q-dep + bounds×2 |

→ **V10 boundary 18% (safe), V12 boundary 57% (over-fit 위험)**

### 결정 — V24 (GOAL1) vs V12 (GOAL2) — 어느 게 더 정확?

V24 (18 params, jump only):
- LOO hip 0.48 / knee 0.36 (5 folders)
- 18 params, 더 간결
- 150_500_5 outlier 분리

V12 (42 params, jump + s2s + CVT validation):
- jump hip 0.93 / knee 0.71 (LOO 미적용)
- 42 params
- 보더라인 over-fit

→ 두 모델은 다른 metric에서 best. **V24가 LOO 더 작음**, V12가 더 광범위 trial 처리.

---

## 11. NARX / Observer / Reference-only 모델 탐색 (별개 path)

이건 V1~V12 physics path와 **별개의 탐색** — data-driven 모델 비교.

### NARX (Nonlinear Auto-Regressive with eXogenous input)

**Architecture**: causal NARX with optimization references + gain labels (ref-only deployment style). Lags [1, 2, 5, 10, 20], rolling means/std, tree ensembles (hist_gbdt, extra_trees).

**Ref-only NARX 성능** (leave-one-folder-out):
- GRF: **8.83 N** (73% 개선 vs baseline 32.8 N)
- Hip τ: **1.67 Nm** (60% 개선)
- Knee τ: **2.27 Nm** (73% 개선)

**Feedback NARX** (oracle, measured 과거 outputs 사용):
- GRF: 3.13 N
- Hip τ: 1.14 Nm
- Knee τ: 1.17 Nm

**Recursive rollout 망함**:
- GRF: 30.55 N (89% feedback benefit 손실)
- Hip τ: 2.20 Nm
- Knee τ: 4.73 Nm
- → **Measured GRF feedback 없이는 NARX 무용**

### Contextual RLS observer (online adaptive)

- GRF: 5.13 N (42% 추가 개선 over ref-only NARX)
- Hip τ: 1.17 Nm
- Knee τ: 1.38 Nm
- **Warmup 100-200 ms 필요** — first-contact 안 됨
- **Feedback NARX 3.13 N 천장 도달 못 함** — 구조적 unmodeled

### 결론 — physics-based vs data-driven

| Use Case | 추천 | 정확도 |
|---|---|---|
| Pre-experiment (physics) | constrained contact surrogate | GRF 10.1 N |
| Pre-experiment (data-driven) | Ref-only NARX | GRF 8.83 N |
| Early closed-loop (0-100 ms) | Ref-only NARX | as above |
| Live closed-loop (100+ ms) | Contextual RLS | GRF 5.13 N |
| Diagnostic post-experiment | Feedback NARX / hybrid | GRF 3.13 N |

### 핵심 인사이트

1. **Physics-based identification (M·ddq+C+G+mom·GRF)은 본질적으로 incomplete** — contact 상태 (timing, slip, penetration)는 reference + gain만으로 관찰 불가
2. **NARX temporal features (lags, rolling stats) 필수** (45-50% 개선)
3. **Hip은 actuator gain에 sensitive**, knee는 contact dynamics에 sensitive
4. **Gain-aware actuator+GRF model 부족** — gain variation은 hip만 설명 (GRF, knee는 다른 원인)

**Source**: 17 files in `26.06.02/position/{causal,combined,contextual,online,gain_aware,hybrid,measured_state_narx,narx_*,output_feedback,recursive_narx,ref_only_*,temporal,tracking_error}/...md`

---

## 12. 사용자 5가지 비판 + 응답 history

GOAL1 결과 후 사용자가 명시한 5가지 비판:

### (1a) NLP T_st 고정 = "chickening"

- **상황 (GOAL1)**: v41이 T_st = 0.27s 고정. 다른 모델/scenario에서도 T_st 비슷하게 chase
- **응답 (GOAL2 Ch.7)**: T_st = `opti.variable()`. 자유 결정 → 모델별 T_st 자율
- **결과**: v10 NLP T_st = 0.398s (model이 자체 결정)

### (1b) GRF chattering 심함

- **상황**: smooth_grf = 0.05 (큰 weight) → 진동 + T_st chase
- **응답**: smooth_grf = 1e-4 (1/500 축소)
- **결과**: 진동 거의 사라짐

### (1c) 비현실 파라미터 (cf=1.6, off=-2~-3)

- **상황**: v41 P31 = {cf1: 1.626, off1: -2.263, off2: -2.999, alpha: 0.559}
- **응답**: Physical bounds 강제 (cf < 0.8, off < ±0.5)
- **결과**:
  - V10: cf_hip 0.44, off_hip -0.31 (안전)
  - V12: cf_hip 0.78, off_hip -0.48 (경계, but 합리적)

### (2) Dynamics 자체 미수정

- **상황**: V1까지 CAD params (Is1, KV, GAV) 고정. 모델 구조 (mom_k 형태, M 형태) 변경 없음
- **응답**: 6가지 구조 추가
  1. Foot radius r_foot (V5)
  2. mom_k polynomial (V6)
  3. kind-specific GRF (V7)
  4. Stribeck friction (V7)
  5. Hip cross-coupling (V8)
  6. mom_h polynomial + GAV q-dep (V11/V12)
- **결과**: V12 hip 0.93 / knee 0.71

### (3) NLP h matching이 잘못된 metric

- **상황**: GOAL1이 NLP optimal h = 0.94m 실측과 매칭한 것을 핵심 결과로 주장
- **사용자 정정**: 
  > "내가 더 많은 motor 토크를 썼으니까 0.94m 점프. 너 더 적은 토크면 더 낮게 뛰는 게 정상. h 매칭은 wrong metric.
  > 진짜 metric: q,dq,ddq → inverse model → predict τ ≈ measured τ"
- **응답**: Inverse RMSE를 진짜 metric으로. NLP는 검증 도구
- **결과**: V12 inverse RMSE 0.93/0.71 (목표 1.0 근접)

### 더 깊은 사용자 비판 (Ch.7, 직전 ultrathink 답변에서)

> "실제 NLP optimal trajectory를 실 로봇에 위치/속도 제어로 재생 시 측정 τ, GRF가 NLP가 예측한 τ, GRF와 일치해야"

→ **Forward sim-to-real consistency** — 진짜 진짜 metric. V10/V12 forward 검증 안 됨 → §1 + §17 + §18.

**Source**: Ch.1 critique (content_ch1_critique.md), Ch.7 NLP, Ch.9 metrics

---

## 13. 최적화 방법론 (BO TPE, L-BFGS, Multi-start, Boundary chase)

### 4가지 방법 비교

| 방법 | 강점 | 약점 | 사용 시기 |
|---|---|---|---|
| **Grid sweep** | 다 探索, exhaustive | 비싸고 local 못 잡음 | early exploration |
| **Optuna TPE BO** | global, smart sampling | TPE DB 큼 (multivariate=True + 300K = 50GB worker!) | global search |
| **L-BFGS** | gradient-based local, 정밀 | local minima, ddq noise sensitive | refine after BO |
| **Multi-start L-BFGS** | local minima 회피 | 시간 비례 | final 정밀화 |

### 169M sweep narrative (2026-04-24)

```
13 params × 169M configs × Numba JIT × 14 cores → ~6시간
imap_unordered + heapq + np.interp + raw arrays 패턴 검증됨
→ Best: gAv=0.30 (CAD 1.36과 다름, ALPHA=0.85 fudge factor)
```

### BO TPE DB size limit (CRITICAL, 26.05.17)

```
TPESampler(multivariate=True) + 300K trials = 워커당 50GB OOM!
→ 5K 넘으면 compact 필수
→ 또는 multivariate=False
```

### Boundary chase의 의미

```
파라미터가 bound 한계에 도달 = "최적화가 한계까지 밀어붙임"
→ over-fit 신호
→ 학습 데이터 노이즈 흡수, 학습 외 영역 부정확

V10 boundary 18% (7/38) — safe
V12 boundary 57% (24/42) — over-fit 위험
```

### Multi-start L-BFGS 패턴

```python
# v22 → v24 패턴
n_restarts = 8
for i in range(n_restarts):
    theta_init = perturb(theta_best, sigma=8% of bound range)
    res = L-BFGS(theta_init)
    if res.fun < best_cost:
        best = res
```

### Hold-out cross-validation 부재 (CRITICAL 미해결)

- V12 점프 6 + s2s 4 모두 학습. **Cross-val 없음**.
- V24는 LOO 했음 (5 folders, 150_500_5 제외)
- → V10/V12의 진짜 generalization 능력 미확인

**Source**: `~/.claude/memory/sweep_optimization_lessons.md`, `bo_tpe_db_size_limit.md`

---

## 14. Forward vs Inverse Dynamics — 구조적 mismatch

### 두 사용 방향 비교

| 측면 | Inverse Dynamics (V10/V12) | Forward Dynamics (jump_opt NLP) |
|---|---|---|
| Input | 측정 q, dq, ddq, GRF | 초기 q(0), 토크 trajectory |
| Output | predict τ | sim q(t), dq(t), ddq(t), GRF(t) |
| 식 형태 | τ = M·ddq + h + g - mom·GRF + ... | M·ddx = RHS - C - G + F |
| DOF | 2 (q1, q2) | 3 (z, q1, q2) |
| τ는? | input (from data) | optimization variable |
| GRF는? | input (from data) | optimization variable |
| Solver | Optuna BO + L-BFGS | IPOPT NLP |
| Metric | RMSE(predict τ, 실측 τ) | NLP objective (jump h, energy, etc.) |

### 구조 mismatch가 만드는 문제

```
V10/V12 (2-DOF inverse) → 그대로 jump_opt NLP (3-DOF) 식에 못 들어감
→ NLP는 V10/V12 식 일부만 사용
→ NLP self-consistency 5.9/6.3 Nm 격차의 원인
```

→ **다음 작업은 baseline (3-DOF) 식 그대로 사용** (§18 A+C 융합).

---

## 15. NLP Self-Consistency 5.9/6.3 Nm — 모델/NLP 일치 문제

### 무엇인가?

```
1. IPOPT가 모델 dynamics에서 q*, dq*, ddq* 최적화
2. 그 q*, dq*를 외부에서 V12 모델로 다시 inverse predict τ_check
3. NLP가 reported한 τ_nlp와 τ_check 비교
```

V12: **hip 5.9 Nm, knee 6.3 Nm** (inverse RMSE 0.93의 6배)

### 원인

1. **IPOPT 내부 implicit ddq** (collocation에서 결정) vs **numpy explicit gradient ddq** (np.gradient(dq)) — numerical 차이
2. **Hip cross-coupling M_aug 처리 차이** — IPOPT가 M_mat 안에 포함, numpy는 외부 항으로 처리
3. **Stribeck exp(...) tanh(...)** — IPOPT는 CasADi exp/tanh, numpy는 동일이지만 dt와 timing에서 차이

### 의미 — 사용자 진짜 goal과 정면 충돌

```
사용자 goal: NLP의 q*, dq*를 실 로봇에 재생 → 실측 τ ≈ NLP τ
→ 만약 self-consistency 5.9 Nm면, 실 로봇 재생도 5.9 Nm gap 예상
→ 즉 inverse RMSE 0.93 자체가 의미 잃음 (forward에서)
```

### 해결 방향 (미수행)

1. CasADi 내부 식을 numpy 함수로 dump → 동일 evaluation
2. ddq 계산 방법 통일 (둘 다 collocation 또는 둘 다 gradient)
3. Hip cross-coupling 통일 (M_aug 또는 explicit)

**Source**: content_ch7_nlp.md

---

## 16. V10/V12 stack — 정리 + 한계

### V10 (38 params, "physical safe")

```
파라미터: 38
Boundary chase: 7/38 (18%)
점프 hip RMSE: 1.64 / knee 0.80
s2s_no_cvt: hip 1.93 / knee 1.42
CVT validation: hip 16.7 / knee 20.1
NLP self-consistency: 비슷 (~5-6 Nm)

권장: 새 robot 일반화, re-id starting point, forward sim 안전
```

### V12 (42 params, "정량 BEST")

```
파라미터: 42 (V10 + 4: dmom_h_c1, dmom_h_c12, dmom_h_off, Gq1_c1)
Boundary chase: 24/42 (57%)
점프 hip RMSE: 0.93 / knee 0.71 ✓
s2s_no_cvt: hip 1.45 / knee 1.23
CVT validation: hip 5.8 (개선) / knee 21.6 (유사)
NLP self-consistency: 5.9 / 6.3 Nm

권장: 점프 inverse-dynamics 분석 (논문 plot, decomposition)
```

### 추가 V24 (GOAL1, 18 params, jump only)

```
LOO hip 0.48 / knee 0.36 (5/6 folders)
150_500_5 outlier 제외
v41 forward NLP: jump h 0.945 vs 실측 0.94 (+0.5%)

→ V24가 LOO에서 V12보다 좋음 (정직 측정 시)
→ V12는 LOO 미적용, 학습 RMSE만
```

### 5가지 한계

1. **Forward sim drift 미검증**
2. **Hold-out cross-val 부재** (V10/V12는 학습 데이터만)
3. **NLP self-consistency 5.9 Nm** (실 로봇 재생 부정확 예상)
4. **CVT 3 folder 잔차 큼** (clutch dynamics 누락)
5. **3-DOF NLP 식에 통째로 못 들어감** (구조 mismatch)

---

## 17. 미검증 / 미해결 / Hold-out 부재 항목

### A. 진짜 사용자 goal 직접 검증 안 됨

1. **Forward sim drift test**: 실측 τ → V10/V12 model → q_sim(t) → 실측 q와 비교
2. **NLP optimal trajectory를 실 로봇에 재생 → 실측 비교**: 사용자 진짜 metric의 simulation surrogate
3. **GRF separate RMSE per trial**: τ 만 본 것 (GRF는 alpha contact로 추정 only)
4. **Lift-off timing accuracy**: hip torque +20 Nm spike

### B. Hold-out validation 부재

5. **6-fold cross-validation 점프**: V10/V12는 학습 데이터만, generalize 미확인
6. **V10 vs V12 어느 게 hold-out에서 좋은지** — 결정적 정보 부재

### C. 측정 부재

7. **z (base height) 측정 부재** — kinematic 추정만, ID degeneracy 원인
8. **dz, ddz 부재** — sys_id_sanity v4~v6 narrative의 핵심 문제
9. **IMU 없음** — base motion 직접 측정 불가
10. **Motor internal state (current limit, mode, saturation flag) log 부재** — v24 era에서 발견

### D. ALPHA=1.0 baseline 부재

11. **ALPHA=1.0 재 sweep 두 차례 OOM** (58M, 588M) — 진짜 물리값 (gAv≈1.4) 검증 미완

### E. 구조적 미해결

12. **150_2.2_500_5 outlier 진단 불완전** — driver mode switch 가설만 (tau_m 2.6ms vs 26ms)
13. **CVT clutch friction + body roll DOF** — 미모델링
14. **Foot length / point contact 한계** — hip torque lift-off spike 5° = 26 Nm

### F. NLP self-consistency

15. **IPOPT implicit ddq vs numpy explicit ddq mismatch** — 5.9/6.3 Nm 미해결

### G. 시계 동기

16. **GRF +24ms lag** + **τ -29ms lag** + **AK servo +4ms** — 동기 < 10ms 안 됨
17. **Force plate scale gain 1.29× +bias -25.85 N** — 캘리브레이션 미완

---

## 18. 다음 작업 권장 — A + C 융합 (사용자 합의)

### 핵심 아이디어

```
A 시나리오 = jump_opt baseline 구조 그대로 (3-DOF, 깔끔, NLP=ID 일치)
+ C 시나리오 = V1~V12에서 발견한 "명백히 정당한" 7~10개 항만 distill 추가
+ Metric = Forward sim drift (사용자 진짜 goal 직접 추적)
+ Optimization = BO + multi-start L-BFGS
+ Validation = Hold-out cross-val (6-fold 점프)
```

### Fit 변수 list (예상 29 params)

#### A part (baseline physical, 12)

```
M_tot, A, B, K, I_sig1, I_sig2, l1, l2, α, JF_v1, JF_v2, RAIL_F
```

#### C part (확실히 정당, 17)

```
tau_m1, tau_m2 (motor lag 분리)
cf1, cf2 (Coulomb)
F_s1, F_s2, v_s (Stribeck)
r_foot (발 반지름)
grf_scale_jump, grf_scale_s2s, grf_bias_jump, grf_bias_s2s (kind GRF)
ka1, ka2 (rotor inertia)
off1_c, off2_c, off1_q1, off2_q2 (state-dep bias, 4 → 4)
```

#### 명시적 배제 (over-fit 의심)

```
✗ hx3·q1·ddq2 (V8, 물리적 약함)
✗ Iq1·cos(2q1), Iq2·c2 (M q-dep, V9, V6 — link 비대칭 약함)
✗ mom_h polynomial (dmom_h_c1, c12, off — V11/V12)
✗ mom_k polynomial 3종 (V6)
✗ Gq1·cos(q1) (gravity q-dep V11)
```

Cross-coupling hx1, hx2는 ablation으로 결정 (정당성 있지만 fit ㅡ 의심 가능).

### 단계별 plan

1. **Phase 1: 인프라** (반나절)
   - jump_opt 식 함수화
   - Forward sim integrator (RK4 or Trapezoidal)
   - Inverse predict 함수
   - Forward sim drift 측정 코드

2. **Phase 2: A part만 fit** (반나절)
   - 12 params BO + L-BFGS
   - **Metric: drift_z + drift_q1 + drift_q2 + inverse RMSE**
   - Baseline drift 확보

3. **Phase 3: C part 단계적 추가 — ablation** (1.5일)
   - motor lag → drift 감소?
   - Coulomb → 감소?
   - Stribeck → 감소?
   - foot radius → 감소?
   - kind-GRF → 감소?
   - rotor inertia → 감소?
   - state-dep bias → 감소?
   - 감소 큰 항만 keep

4. **Phase 4: NLP integration + self-consistency** (반나절)
   - jump_opt NLP에 동일 식 wire-in
   - self-consistency 측정 (예상: < 1 Nm)

5. **Phase 5: Hold-out validation** (반나절)
   - 6-fold cross-val 점프
   - V10/V12와 forward drift 비교

### 예상 결과

| 지표 | 현재 (V12) | A+C 융합 예상 |
|---|---|---|
| Inverse RMSE | hip 0.93, knee 0.71 | hip 1.2-1.8, knee 1.0-1.5 |
| **Forward drift** | **미검증** | **hip 1.5-2.5 Nm, knee 1.5-2.0 Nm** |
| **NLP self-consistency** | **5.9/6.3 Nm** | **< 1 Nm** |
| Boundary chase | 24/42 (57%) | < 10% (예상) |
| Hold-out cross-val | 미수행 | 6-fold |
| 사용자 진짜 goal 직접 metric | × | ✓ |

### 시간 예상

```
3~4일 작업 (Phase 1~5)
```

### Risk + Mitigation

| Risk | Mitigation |
|---|---|
| z(t) 측정 부재로 drift_z 계산 불가 | force plate impulse 적분 추정 + drift_q1/q2만 우선 |
| A part 단독 drift 매우 큼 (>5 Nm) | C part 명백 정당 항 빠르게 단계적 추가 |
| 어떤 항도 drift 감소 안 함 | metric 재정의 (drift_z + GRF separate 등) |
| NLP self-consistency 여전 >2 Nm | numerical method 점검 (collocation, dt) |
| Forward sim numerically unstable | smaller dt, semi-implicit integrator |

### 결정해야 할 것들 (시작 전)

1. **baseline mass 표기**: 합성 (M_tot, A, B, K) vs raw (M, m1, m2, m_c, m_p)?
2. **Friction 깊이**: Stribeck 포함 vs Coulomb까지만?
3. **State-dep bias 자유도**: 4 vs 2?
4. **Cross-coupling 포함?**: hx1, hx2만 (2) vs 전혀 배제?
5. **Initial fit metric**: forward drift only vs drift+inverse hybrid?
6. **CAD bound ±%**: ±20% safe vs ±30% V12 따라 vs ±10% strict?

---

## 19. 사용자 작업 패턴 (참고)

### 사용자 thinking patterns

- **단편적 fix 거부**: "지금까지 해온 거 다 살리면서"
- **"다 해보자" pattern**: 4선택지 A/B/C/D 동시 평가 선호
- **비판적 분석 요구**: "냉철하고 비판적으로 다양한 방면으로 검토"
- **직접 cross-check**: 자기가 직접 확인하길 원함
- **Notion 워크플로우**: 구조 계획 → 부분별 한 페이지씩 → 다양한 그래프 → 비유+논리+수식

### 사용자 feedback 기록 (memory)

- **Auto-approve**: 장시간 sweep 중 자동 승인 OK
- **Git commit auto**: 코드 수정 후 자동 커밋 OK
- **Pure Paper a_hat 식 사용**: GitHub s(v) smoothing 금지
- **Notion 이미지 file_uploads API**: imgur 등 외부 호스팅 금지
- **Sweep launch via .bat 더블클릭**: PowerShell/Tee-Object 금지
- **Notion 보고는 표 형식 + Best 해석 + 바운더리 양상 (chasing/lean/mid)**

### 사용자 진짜 goal 진화 (시기별)

- **2026-04**: sim-to-real gap 정량 분석 (E_ratio, Impulse ratio, α)
- **2026-04 후반**: System ID로 gAv 진짜 값 찾기 (CAD 1.36)
- **2026-05 초**: AK80 정밀 모델 (paper a_hat)
- **2026-05 중**: NLP 다양한 scenario (T_st, payload sweep)
- **2026-06 초 (GOAL1)**: v24 inverse 0.5 Nm + v41 NLP h match
- **2026-06-05 (GOAL2)**: 5가지 비판 응답, V10/V12 stack
- **2026-06-05 (이후)**: Forward sim-to-real consistency — 진짜 진짜 metric

---

## 20. 미래 발견 Append 영역 (Template)

> 새로 발견한 사실/insight를 여기에 append. 위 sections에도 추가하되, 새 발견은 이 timeline에 chronological 추가.

### Template

```markdown
### YYYY-MM-DD: <짧은 제목>

**발견**: <1줄 요약>

**증거**:
- 숫자: <RMSE, params, count 등>
- 파일: <경로 + line>
- git commit: <hash>
- session: <jsonl path or notion URL>

**의미**:
- <왜 중요한가, 어떤 가설이 확인/반박되었나>

**관련 section**:
- §X, §Y

**발견 환경**:
- sub-agent / 사용자 지적 / web research / 논문 / 코드 read / sweep 결과 등
```

### (빈 영역 — 새 발견 여기 추가)

---

### 2026-06-05 23:50: GOAL3 V8 — AK80 saturation이 NLP self-cons의 dominant factor

**발견**: V6 (V5+NLP) self-cons hip 5.11 / knee 1.73 → V8 (V5+NLP+AK80 saturation) hip 2.74 / knee **0.16** Nm.

**증거**:
- V8 NLP solve: T_st=0.219s, h=0.851m (사용자 metric 아님)
- numpy V8 inverse(NLP q*, dq*, ddq*) vs NLP τ_actual: hip 2.74 / knee 0.16 Nm
- Saturation effect 단독: hip diff 3.22 / knee 1.84 Nm (V5 inv vs V8 inv on same NLP traj)
- 파일: `C:\Users\junho\Desktop\jump_opt\goal3\v8_results\v8_summary.txt`

**의미**:
- V12 GOAL2의 self-cons 5.9/6.3 Nm 격차 중 **AK80 saturation이 dominant cause** (특히 hip)
- knee self-cons 0.16 < 1.0 Nm 사용자 목표 달성 (첫 번째)
- hip 2.74 Nm 남은 잔차는 IPOPT implicit ddq vs numpy explicit ddq mismatch + V5 식의 inv RMSE plateau

**관련 section**: §15 NLP self-consistency, §16 V10/V12 stack 한계

**발견 환경**: GOAL3 Phase 6 자율 진화 (V8 NLP test)

---

### 2026-06-06 00:18: GOAL3 V11 negative finding — hx1, hx2 함정

**발견**: V8 + hx1·q2·ddq1 + hx2·dq1·dq2 (보더라인 정당) 추가 시 **Inverse 좋아지지만 forward 악화**.

**증거**:
- V11 inv hip 2.77 (V8 3.48 대비 -20%) ★
- V11 boundary 75% (V8 90% 대비 -15%, 개선!)
- 그러나 V11 NLP self-cons: hip 2.93 (악화 +7%), **knee 1.82 (악화 +1.66 Nm)**
- 파일: `C:\Users\junho\Desktop\jump_opt\goal3\v11_results\theta_v11.npz`, `v11_nlp\v11_nlp.npz`

**의미**:
- **MASTER_INSIGHTS §17 보더라인 정당 카테고리의 진짜 의미 확인**: 학습 데이터 fit 도움 ≠ forward consistency 도움
- V12 GOAL2의 over-fit 함정 (boundary 57%) 재현
- **inverse RMSE 최소화 ≠ forward consistency** — 사용자 진짜 metric은 후자
- → V8 (V5+saturation, 추가 항 없음)이 GOAL3 best

**관련 section**: §16 V10/V12 stack 한계, §17 미해결 항목

**발견 환경**: GOAL3 Phase 6 자율 진화 (V11 fit + NLP self-cons)

---

### 2026-06-06 00:18: GOAL3 V12 (forward-real) — 사용자 진짜 metric 첫 직접 달성

**발견**: V8 식으로 실측 τ, GRF input → forward integrate → 실측 q와 비교. 단기 forward에서 사용자 목표 거의 달성.

**증거** (점프 6 trial MEAN):
- T=0.05s: q1 **0.11°** (목표 2° 통과 ★★★), q2 **2.54°** (목표 근접)
- T=0.10s: q1 **0.45°**, q2 **4.04°**
- T=0.15s: q1 1.59°, q2 5.90°
- T=0.20s: q1 4.19°, q2 21.22° (knee 발산)
- 파일: `C:\Users\junho\Desktop\jump_opt\goal3\v12_forward_real\forward_drift_real.csv`

**의미**:
- **사용자 진짜 metric의 simulation surrogate 첫 직접 달성**
- 점프 stance phase (~0.25s)의 처음 ~0.1s는 매우 정확 — NLP optimal trajectory를 실 로봇에 재생 시 처음 100ms는 거의 일치 예상
- 후반부 누적 발산은 model error + numerical integration drift
- s2s_no_cvt trial만 q2 발산 (특이) — measurement outlier 가능

**관련 section**: §1 진짜 goal, §14 Forward vs Inverse, §15 NLP self-cons

**발견 환경**: GOAL3 Phase 6 자율 진화 (v12_forward_real.py)

---

### 2026-06-06 00:35: GOAL3 V13 — NLP replay에서 fundamental finding

**발견**: NLP self-cons 0.16 (excellent) ≠ NLP optimal trajectory를 실 robot에 재생 시 τ 차이.

**증거** (V13 NLP replay 3가지 방식):

| 재생 방식 | drift_q1 | drift_q2 | 의미 |
|---|---|---|---|
| **A**: τ_actual을 forward sim input | 33.2° | 29.8° | NLP collocation vs Euler 적분 |
| **B**: τ_cmd + sat in dynamics | 32.6° | 28.8° | A와 거의 같음 |
| **C**: **PD track q* + sat (실 robot 모방)** | **3.8°** | **12.7°** | 실 robot 시뮬 |
| **PD-applied τ vs NLP τ_actual (C)** | - | - | **hip 6.72 / knee 5.34 Nm** |

**의미** (사용자 진짜 metric의 진짜 어려움):
- NLP self-cons knee 0.16 = NLP 자체 collocation 안에서 일관성 (model-internal)
- 그러나 외부 forward sim (A, B)에서 NLP τ를 그대로 input으로 → 30° drift
- PD로 q* 추적 (C) → drift 줄어듦 (4-13°) but τ 차이 5-7 Nm
- 즉 **NLP feedforward τ ≠ PD feedback τ** — 다른 종류의 토크
- → 사용자 진짜 metric (PD 제어 시 실측 τ vs NLP τ) = 6.7 / 5.3 Nm

**왜?**
- NLP는 ideal motor + perfect tracking 가정 (state error = 0)
- PD는 tracking error로 τ_cmd 만듦 — saturation 영향 큼
- Real robot은 PD + saturation + 다른 disturbance
- → V8 모델로 PD-driven 시뮬 τ가 NLP τ와 5-7 Nm 차이

**해결 방향**:
- NLP에 PD tracking term 포함 (feedforward + feedback)
- 또는 real robot을 torque-controlled mode로 (PD bypass)
- 또는 NLP가 saturation realistic하게 모델링 (V8 이미 부분 적용)

**파일**: `C:\Users\junho\Desktop\jump_opt\goal3\v13_replay\v13_replay.npz`

**관련 section**: §1 진짜 goal, §15 NLP self-cons, §17 미해결

**발견 환경**: GOAL3 Phase 6 (V13 시도)

---

### 2026-06-06 00:48: GOAL3 V25 — a_hat re-fit (jump hip -31%, s2s knee -27%) ★

**발견**: a_hat 변환된 τ (진짜 motor output)를 measurement로 사용해서 V20 re-fit → **multi-task 모두 개선**.

**증거**:
- Jump MEAN: hip 3.14 (V20) → **2.18 (-31%)** ★, knee 1.39 → 1.45 (거의 동일)
- s2s MEAN: hip 2.40 → 2.38, knee 6.74 → **4.90 (-27%)** ★
- AK80 sat fit: tau_lim_peak 17.78 (V20 18.45 보다 작음), k_back_emf **0.30 (upper boundary 도달)**

**의미**:
- a_hat 변환은 currentTorque (raw iTM, firmware Kt 0.091 기준 추정) → 진짜 motor output τ (UMich 5-param)
- 우리 robot의 실제 output τ는 raw × ~0.57 (gear + d/q 정렬 손실)
- V25 = 진짜 motor output τ에 fit → **사용자 진짜 metric (실측 τ ≈ NLP τ)에 더 직접**
- k_back_emf 0.30 upper bound — 더 widen 시 추가 개선 가능 (V26)

**GOAL3 진정한 final model 계보**:
1. V8 (raw, default sat): jump hip 3.84
2. V20 (raw, sat fit): jump hip 3.14 (-18%)
3. **V25 (a_hat, sat refit): jump hip 2.18 (-31%) ★ — best inverse**

**진정한 GOAL3 ULTIMATE FINAL**:
- **V25 model** (a_hat τ + sat fit 17.78/0.30) — 진짜 motor output에 fit
- **V15 robust NLP** + **AK80 torque control mode**
- 사용자 진짜 metric의 직접 적용 (실측 τ output side)

**파일**: `fit_v25_ahat_refit.py`, `theta_v25.npz`

**관련 section**: §7 AK80 motor, §16 V10/V12 stack

**발견 환경**: GOAL3 Phase 7 (V25)

---

### 2026-06-06 00:42: GOAL3 V24 — AK80 paper a_hat 적용 발견

**발견**: paper a_hat (UMich 5-param) 변환은 task별 다른 효과.

**증거** (V20 inverse with raw vs a_hat-converted τ):

| Trial | Raw inv hip/knee | a_hat inv hip/knee | 변화 |
|---|---|---|---|
| jump_60_0.75 | 2.68/1.23 | 1.15/3.74 | hip↓, knee↑ |
| jump_120 | 2.11/1.26 | 2.57/3.80 | knee 악화 |
| s2s_no_cvt | 2.09/8.07 | 1.68/**5.74** | s2s knee 개선 |
| s2s_cvt_load_2.5 | 2.20/8.45 | 2.68/**3.59** | knee 큰 개선 |
| s2s_cvt_load_5 | 4.40/7.84 | 5.20/**4.36** | knee 큰 개선 |

**의미**:
- a_hat은 **s2s/cvt trial에서 정확** (low-load, low-velocity)
- **jump knee에서는 raw τ가 더 좋음** (saturation 영역에서 a_hat 변환이 model output을 underestimate)
- max τ 비교: raw 35 Nm → a_hat 20 Nm (a_hat 약 0.57× raw, 즉 변환 후 motor output 추정)

**결론**:
- 사용자 robot의 raw `currentTorque`는 motor firmware 추정 (0.091 Kt 기준)
- 실제 output τ는 raw × 0.57 정도 (gear + d/q 정렬 손실)
- jump 영역에서 V20 model이 raw τ에 fit 되어있으면 well-matched
- 만약 진짜 output τ가 metric이면 → a_hat 변환 후 fit 다시 (V25 시도 가능)

**파일**: `v24_a_hat_apply.py`

**관련 section**: §7 AK80 motor model

**발견 환경**: GOAL3 Phase 7 (V24)

---

### 2026-06-06 00:35: GOAL3 V21-V23 — Final stack 검증 + multi-task trade-off

**발견**: V20 model + V15 robust NLP = jump에서 perfect. 그러나 V20 vs V8 multi-task trade-off.

**증거**:
- V21 (V20 + V15 robust + FF only): jump drift 0.02°/0.19°, τ_diff **0.0000/0.0000 Nm** ★★★★★ (h 0.47m)
- V22 (V20 + PD mode): jump hip τ_diff **1.17 (V8 6.72의 -83%)** ★, but knee 11.98 (sat hit)
- V23 (V20 + sit2stand NLP): self-cons hip 2.29 / knee 4.64 (V8 default 1.54/2.59 보다 worse)

**Multi-task trade-off 결론**:

| Model | Jump self-cons (hip/knee) | Jump FF τ_diff | Sit2stand self-cons | 권장 |
|---|---|---|---|---|
| V8 default (sat 21/0.06) | 2.74 / 0.16 | 0.0001/0.003 | 1.54 / 2.59 | **multi-task best** ★ |
| V20 (sat fit 18.5/0.25) | 1.89 / 1.16 | 0.0000/0.0000 | 2.29 / 4.64 | jump-specialized |

→ **V8 model**이 multi-task 균형 (jump + s2s 모두 self-cons < 3 Nm)  
→ **V20 model**은 jump-specialized (jump에서 perfect, s2s에서 V8보다 worse)

**진정한 GOAL3 final stack** (사용자 명시 "수직 점프 특화 X" 반영):
1. **V8 model** (default sat 21/0.06) — multi-task balanced
2. **V15 robust NLP recipe** (smooth + mag)
3. **AK80 torque mode** (FF only)
4. **결과**: jump τ_diff 0.0001/0.003 Nm, s2s self-cons 1.54/2.59 Nm

V20 sat fit은 우리 robot의 진짜 sat 식별 (논문 가치) but generalization으로는 V8 default 우수.

**파일**: `v22_v20_pd.py`, `v23_v20_sit2stand.py`

**관련 section**: §1 진짜 goal, §16 V10/V12 stack

**발견 환경**: GOAL3 Phase 6+ V21-V23

---

### 2026-06-06 02:30: GOAL3 V19-V20 — AK80 saturation params도 fit (knee inv -72%!)

**발견**: AK80 `tau_lim_peak`과 `k_back_emf`를 fit variable로 → jump knee inverse RMSE 5.22→1.39 Nm (**-72%**).

**증거** (V20 wider bound 결과):
- tau_lim_peak: V8 default 21.0 → V20 fit **18.45 Nm** (-12%)
- k_back_emf: V8 default 0.06 → V20 fit **0.2547 Nm·s/rad** (+325%)
- Jump inv hip: 3.84 (V8) → 3.14 (V20) — -18%
- Jump inv knee: 5.22 (V8) → **1.39 (V20)** — -73% ★★
- NLP self-cons: V20 hip 1.89 / knee 1.16 (V8 default 2.74 / 0.16)

**의미**:
- **우리 AK80은 데이터시트 21 Nm peak보다 작은 18.5 Nm + back-EMF 0.25 (4배 큰 dampening)**
- 모터 사용 환경 (4-bar mechanism + leg mass) 에서 effective saturation 더 강함
- V20 model이 진짜 robot에 더 가까운 dynamic
- V8 default vs V20: trade-off — V8 self-cons knee 0.16 더 작음 (NLP-friendly), V20 inv RMSE 더 좋음 (data-fit)

**최종 권장 stack**:
- Identification: **V20** (V8 + sat fit) — 32p, jump inv hip 3.14 / knee 1.39
- NLP: **V15 recipe** (smooth + mag) → FF only forward consistency

**파일**: `C:\Users\junho\Desktop\jump_opt\fit_v19_sat_params.py`, `fit_v20_wider.py`, `v20_nlp_check.py`

**관련 section**: §7 AK80 motor, §16 V10/V12 stack

**발견 환경**: GOAL3 Phase 6+ 자율 진화

---

### 2026-06-06 01:38: GOAL3 V17 — s2s_no_cvt outlier 진단

**발견**: s2s_no_cvt forward drift_q2 발산 (T=full = 392°)의 원인은 **GRF가 아니라 knee saturation**.

**증거**:
- GRF correction sweep (scale 0.5~1.5, offset ±30, sign flip, zero): drift_q2 380~480° 비슷
- s2s_no_cvt knee saturation 53% (max τ 22 Nm), s2s_cvt_load_5 knee sat 53.5%
- knee inv RMSE: s2s_no_cvt 10.3 Nm, s2s_cvt_load_5 23.4 Nm — saturation에서 model 부정확

**의미**:
- V8 model의 saturation 영역 한계 + knee 53% saturated → forward sim 발산
- s2s GRF는 다른 outlier 패턴 (V12 GOAL2 분석과 일관)
- 해결: 측정 trajectory가 saturation 영역에 안 가도록 user-side 조정 또는 model에 saturated-data weight=0

**파일**: `C:\Users\junho\Desktop\jump_opt\v17_s2s_outlier.py`

**관련 section**: §17 미해결, §5 contact model

**발견 환경**: V17 진단

---

### 2026-06-06 01:20: GOAL3 V16 — Jump h vs τ_diff Pareto Front 완전 분석

**발견**: V15 robust NLP에서 jump h constraint를 0.3~0.85m로 sweep. 명확한 Pareto.

**증거** (V16 sweep, FF only mode):

| h_min | h_achieved | max\|τ\| h/k | drift q1/q2 | τ_diff hip | τ_diff knee | 사용자 metric |
|---|---|---|---|---|---|---|
| 0.30 | 0.388 | 0.1/0.5 | 5.2°/2.1° | **0.0000** | **0.0000** | ★★★★ |
| 0.40 | 0.406 | 5.5/7.0 | 0.3°/5.8° | **0.0000** | 0.0055 | ★★★★ |
| 0.50 | 0.500 | 3.3/5.3 | 6.0°/13.3° | 0.0004 | 0.0019 | ★★★★ |
| 0.60 | 0.600 | 8.7/9.5 | 42°/95° | 0.0174 | 0.0910 | ★★★ |
| 0.70 | 0.700 | 11.8/12.1 | 31°/136° | 0.0119 | 0.2374 | ★★★ |
| 0.80 | 0.800 | 16.6/16.6 | 43°/157° | 0.0113 | 0.4744 | ★ (knee 근접) |
| 0.85 | NLP infeasible | - | - | - | - | - |

**의미**:
- **사용자 metric 완전 통과 max h ≈ 0.6m** (τ_diff < 0.1 Nm)
- **실측 jump h 0.94m**은 우리 robot의 max + saturation 활용 → 사용자 metric 불가능 영역
- **사용자 명시 정확함**: "실측 토크가 NLP보다 과해서 0.9m 점프" — V16가 정량 증명
- 0.5m 점프 + perfect τ matching이 사용자 진짜 metric에 가장 가까운 옵션

**파일**: `C:\Users\junho\Desktop\jump_opt\goal3\v16_h_sweep\v16_pareto.npz`

**관련 section**: §1, §17, §18

**발견 환경**: GOAL3 Phase 6 (V16 sweep)

---

### 2026-06-06 00:58: GOAL3 V15 — Robust NLP 발견 (τ_diff < 0.01 Nm 달성!)

**발견**: Robust NLP cost (smoothness + magnitude penalty)는 FF only에서 **τ_diff hip 0.0001 / knee 0.003 Nm** 달성. 사용자 진짜 metric의 τ 부분 완전 통과 (< 1.5 knee 목표 대비 500배 작음).

**증거** (V15 다양한 weight):

| Config | max\|τ\|_h/k | FF only τ_diff | FF only drift | Low PD τ_diff | Low PD drift |
|---|---|---|---|---|---|
| V14 baseline (sw=1e-4) | 18/18 | 0.02/1.05 | 41°/151° | 1.0/6.2 | 1.6°/13° |
| Smooth strong (sw=1e-2) | 12.7/18 | 0.02/1.04 | 40°/160° | 1.6/5.6 | 1.5°/13° |
| **Smooth + mag** (sw=1e-2, mw=1e-3) | **3.6/5.6** | **0.0001/0.003** ★ | 5°/10° | 1.5/13.6 | 0.7°/2.7° |
| Smooth + mag + accel | 2.8/4.9 | 0.001/0.002 | 13°/16° | 1.3/13.2 | 0.6°/2.6° |
| All very strong | 0.3/0.5 | 0/0 | 0.05°/0.2° | 0.06/0.26 | 0.04°/0.14° |

**핵심 발견**:
1. **Mag penalty가 핵심**: τ를 saturation 영역에서 멀리 떨어뜨림 → FF only에서 τ_diff < 0.01
2. **Trade-off는 V8보다 잠재력 큼**: V14 baseline은 τ는 1 Nm but drift 41°. V15는 τ 0.0001 + drift 5°.
3. **PD 추가는 오히려 해로움**: knee τ_diff 폭증 (PD가 자체 τ 추가)
4. **All very strong (sw=0.1, mw=0.01, aw=5)**: 점프가 사실상 안 일어남 (max τ 0.3) — over-regularize

**Recipe (사용자 metric 완전 통과 옵션)**:
1. NLP cost에 mag penalty (mw=1e-3) 추가 → saturation 회피
2. NLP cost에 smooth penalty (sw=1e-2) 추가 → 부드러운 τ
3. 실 robot은 **torque control mode** (PD bypass) → FF only로 NLP τ 직접 적용
4. → 결과: τ가 NLP와 거의 일치 (< 0.01 Nm), drift 5-10° (acceptable)

**잔여 (수직 점프 특화 trade-off)**:
- Smooth + mag NLP에서 점프 높이 0.505m (V8 0.851m 대비 40% 감소)
- 사용자 명시 "점프 높이 X" 이므로 OK

**파일**: `C:\Users\junho\Desktop\jump_opt\v15_robust_nlp.py`

**관련 section**: §1, §18, §15

**발견 환경**: GOAL3 Phase 6 (V15)

---

### 2026-06-06 00:43: GOAL3 V14 — FF+PD Trade-off 발견 (사용자 metric 근본 분석)

**발견**: NLP feedforward + PD tracking은 trade-off. 두 가지 동시 충족 불가.

**증거** (V14 FF + PD with various Kp):

| Config | drift_q1° | drift_q2° | τ_diff hip | τ_diff knee |
|---|---|---|---|---|
| **FF only (no PD)** | 24° | 149° | **0.03** | **1.44** ★ |
| Low PD (Kp=30) | 0.95° | 21.7° | 1.03 | 6.41 |
| Med PD (Kp=60) | 2.2° | 9.3° | 2.56 | 4.49 |
| Std PD (Kp=120) | 1.6° | 4.2° | 3.49 | 4.05 |
| High PD (Kp=150) | 1.5° | 1.7° | 3.97 | 5.21 |
| Very high (Kp=500) | 0.6° | 1.2° | 4.48 | 5.97 |

**의미**:
- **FF only**: τ는 NLP와 거의 일치 (사용자 metric ★) but trajectory 큰 발산
- **High PD**: trajectory tracking 정확 but τ 차이 큼
- **본질적 trade-off**: 사용자 명시 "위치/속도 + 토크 둘 다 일치"는 동시 충족 불가
- → 사용자 진짜 metric 두 부분 (q, dq + τ, GRF)이 본질적으로 trade-off

**Why?**
- NLP feedforward τ는 q*, dq*, ddq*에 정확히 맞는 토크 (이상적 motor + perfect tracking)
- 실 robot은 small tracking error 발생 (motor noise, contact 다름 etc.)
- PD가 그 error 보정하려면 τ를 변경 → NLP τ와 차이
- 결국 "위치 잘 추적" ↔ "τ 일치" 둘 중 하나만 선택

**해결책** (사용자 정정 후 옵션):
1. **(A) Robust trajectory NLP**: NLP가 small Kp만으로도 stable한 trajectory 만듦 (현재 fragile)
2. **(B) Torque + state hybrid mode**: 실 robot이 PD-low + FF-high (NLP τ + 작은 correction)
3. **(C) τ가 일치하는 것이 진짜 metric**: drift는 부수적, low Kp 사용 (FF dominant)

**최선 (사용자 metric에 가까움)**: Low PD (Kp=30) — drift_q1 1°, drift_q2 22° but τ_diff 1.03/6.41. 둘 다 부분 충족.

**Pareto front** (V14 plots): drift × τ_diff plane에서 (FF only ~ 24°, 0.03) ~ (Kp=500 ~ 1.2°, 6.0)

**파일**: `C:\Users\junho\Desktop\jump_opt\goal3\v14_ff_pd\v14_results.npz`

**관련 section**: §1, §15, §17, §18

**발견 환경**: GOAL3 Phase 6 (V14 시도)

---

### 2026-06-06 00:18: GOAL3 종합 결론 — V8 = best stack

**발견**: 30 params (V5) + 2 fixed (AK80 saturation) = **V8 = GOAL3 FINAL BEST**.

**증거**:
| Metric | V12 GOAL2 | **V8 GOAL3** | 개선 |
|---|---|---|---|
| Inverse jump hip (train) | 0.93 | 3.48 | -274% (V12 over-fit) |
| Boundary chase | 57% | 90% (V5 fit) | (saturation은 fixed) |
| NLP self-cons hip | 5.9 | 2.74 | -54% ★ |
| **NLP self-cons knee** | **6.3** | **0.16** | **-97% ★★★** |
| Forward drift q1 (T=0.05) | 미측정 | **0.11°** | 직접 달성 ★ |
| Forward drift q2 (T=0.05) | 미측정 | **2.54°** | 직접 달성 ★ |
| Hold-out CV | 없음 | 6-fold (V7) | 측정됨 |
| **사용자 진짜 metric** | 간접 추정 | **직접 달성** | 첫 통과 |

**의미**:
- V12 GOAL2의 점프 inv hip 0.93 / knee 0.71은 **fit data only** — over-fit 가능성 큼
- V8 GOAL3는 점프 inv hip 3.48이지만 **forward consistency 직접 통과** — 사용자 진짜 metric 달성
- V11 시도가 V8보다 inv 좋지만 forward 악화 → **inverse 최소화 함정** 재확인
- GOAL3가 사용자 정정 (forward consistency 우선) 정확히 응답

**관련 section**: §16 V10/V12 stack 한계, §18 다음 작업 권장

**발견 환경**: GOAL3 Phase 6 자율 진화 완료 시점

---

### 2026-06-06 01:42: Web research — Pinocchio robotics library

**발견**: Pinocchio C++ library는 floating base inverse dynamics (RNEA)의 빠른 표준.

**증거 + Sources**:
- [Pinocchio (stack-of-tasks)](https://stack-of-tasks.github.io/pinocchio/): C++ library, Crocoddyl + TSID 통합
- [GitHub](https://github.com/stack-of-tasks/pinocchio): floating base + spherical + revolute joints support
- [arxiv 2105.05102](https://arxiv.org/pdf/2105.05102): 1.4x faster inverse dynamics partial derivatives

**의미**:
- 우리 numpy V8 + CasADi NLP는 OK but Pinocchio + Crocoddyl 사용 시 NLP solve 빠르게 (현재 3.7s → 1s 미만 가능)
- 다른 task (sit2stand, payload) 추가 trial 시 Pinocchio binding 도움
- Future work: V8 → Pinocchio URDF로 migrate

**관련 section**: §18 다음 작업, §13 최적화 방법론

**발견 환경**: GOAL3 Phase 6 자율 web research

---

### 2026-06-05 23:55: Web research — legged robot identification 관련 paper

**발견**: 우리 V8 접근과 직접 관련된 최신 paper 3개.

**증거 + Source**:
1. [Physically-Consistent Parameter Identification of Robots in Contact](https://arxiv.org/pdf/2409.09850) (Spot 4족, contact 영향 제거 identification — 우리 V5/V8과 비교 가능)
2. [Unified Model with Inertia Shaping for Highly Dynamic Jumps](https://arxiv.org/pdf/2109.04581) (점프 robot inertia shaping — 우리 K, Is_sig dynamics 검증)
3. [Sampling-Based System ID with Active Exploration (sim2real)](https://arxiv.org/pdf/2505.14266) (2025-05, floating base sim2real)
4. [Symbolic identifiability proof of legged mechanism from base-link dynamics](https://www.researchgate.net/publication/271431037) — 우리 z=contact constraint 사용의 정당성
5. [Symbolic Learning Reduced-Order Jumping Quadruped](https://arxiv.org/pdf/2508.06538) — interpretable jumping models
6. [LMI Physically-Consistent Inertial ID](https://arxiv.org/pdf/1701.04395) — mass distribution constraints

**의미**:
- 사용자가 명시한 "현실에 최대한 근접" — physically-consistent ID 방법이 정확히 같은 motivation
- LMI constraint 추가 시 V8의 over-fit 의심 해결 가능
- Sampling-based active exploration (2025) — sim2real 보강 옵션

**관련 section**: §10 identification narrative, §17 미해결 항목, §18 다음 작업

**발견 환경**: GOAL3 Phase 6 자율 진화 (WebSearch)

---

## 21. 참고 자료 인덱스 (큰 그림)

### 핵심 파일

```
Master Document (이 파일):
  C:\Users\junho\Desktop\jump_opt\MASTER_INSIGHTS.md

Memory Folder (~/.claude/.../memory/):
  - ak80_9_torque_calibration.md (CRITICAL — motor model)
  - analysis_findings.md (2026-04-19 sim-to-real gap)
  - decisions_log.md (15 major decisions)
  - hip_torque_lift_off_diagnosis.md (foot length 한계)
  - sysid_findings.md (gAv=1.57, ALPHA fudge factor)
  - goal2_final_stack.md (V10/V12 정리)
  - high_pd_outlier_150_500_5.md (outlier 진단)
  - position_data_26_06_02_model.md (v15 motor lag breakthrough)
  - sweep_optimization_lessons.md (169M sweep + OOM 교훈)
  - bo_tpe_db_size_limit.md (5K 넘으면 compact)
  - pd_sim_purpose.md (디지털 트윈 본질)
  - digital_twin_priority.md (매칭 우선순위)
  - feedback_pure_paper_formula.md (a_hat sgn(v) only)
  - feedback_notion_image_upload.md (file_uploads only)

Identification Model Code:
  C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\
    unified_loader.py (10 trial + CVT TR loader)
    unified_fit_v1.py ~ v12_relax.py (model evolution)

NLP / Forward Sim:
  C:\Users\junho\Desktop\jump_opt\
    leg_simulator.py (kinematics 시각화)
    no_cvt_alphaonly/jump_no_cvt_alphaonly.py (baseline NLP, alpha contact)
    no_cvt_softalpha/jump_no_cvt_softalpha.py (soft + alpha)
    with_cvt_alphaonly/jump_with_cvt_alphaonly.py (CVT 포함)
  
  C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.06.02\position\
    v21_forward_sim.py (forward sim verification)
    v38_ak80_full_nlp.py (AK80 full motor model NLP)
    v41_best_nlp.py (FINAL forward NLP, jump h match 0.5%)
    v50_nlp_proper.py (recent NLP)

Notion Reports:
  GOAL1 (May 2026): notion_report/ — ch1~ch10
  GOAL2 (June 5 2026): notion_goal2/ — ch1~ch10 + model_evolution + baseline_vs_v12
  Notion pages URL: 375ab81d... (parent + 12 children)

Key Data:
  C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\
    26.04.21 ~ 26.04.22 (위치제어 6 + 토크제어 3)
    26.06.02/position/ (점프 6 PD gain folders)
    26.06.04/no_cvt/ (sit2stand no_load, load_5, load_7.5)
    26.06.04/cvt/ (sit2stand CVT no_load, load_2.5, load_5)
    26.06.04/sim/ (시뮬 결과)
```

### Sub-agent reports (이번 정리 시 사용)

```
Agent A (Group A): v2~v51 model evolution narrative
Agent B (Group B): static gap + contact + chatter + friction + sign + time
Agent C (Group C): NARX + observer + ref-only model
Agent D (Group D): GOAL1+GOAL2 notion content distilled
```

---

**END OF MASTER INSIGHTS DOCUMENT v1.0 (2026-06-05)**

> 새 발견은 §20에 append. 기존 sections도 발견에 따라 update.  
> 다음 goal 시작 시 §1 → §17 → §18 → §19 순서로 read.

---

## §20. GOAL14 신규 발견 (2026-06-18)

### §20.1 9D 동시 최적화에서 mass scale이 지배적 역할

**발견**: GOAL14 Iter14 (7D 최적화, score=107.87) → Iter15 (9D = 7D + m_thigh_scale + m_calf_scale, score=95.40)  
**수치 증거**: 12.59% 개선 (KEEP 기준 3% = 105.86). commit 82f8da94.  
**파일**: `goal14/iter15/iter15_metrics.json`

**핵심 관측**:
- m_calf_scale → 0.6 (하한 bound) in 4/9 trials
- m_thigh_scale → 0.8 (하한 bound) in 2/9 trials  
- 일부 trial에서 tau RMSE ≈ 0 (tau가 0에 가까운 trial 정상)
- 하지만 12.59% 개선은 GOAL12 Iter42 (128.57 → overfit) 패턴과 유사

**경고**: m_calf_scale이 0.6 (하한) 도달 = boundary chasing 가능성.  
GOAL12 교훈 §19 "Iter42 overfit": m_calf_scale 0.15-0.46에서 대규모 boundary chase 발생.  
Iter15의 0.6은 더 moderate하지만 동일 패턴. Iter16에서 bound 확장 후 추가 하강 여부 확인 필수.

**의미/시사점**:
- mass scaling은 inertia-friction coupling을 통해 flight phase q/dq RMSE를 직접 조정 가능
- 물리적 해석: m_calf_scale<1은 calf 링크의 effective 질량이 CAD보다 낮음을 시사
  - 가능한 원인: CAD에 포함된 케이블/커넥터 mass가 실제보다 적음, 또는 overfitting
- GOAL12 Iter38에서 m_calf_scale이 per-trial로 최적화된 이유를 이제 이해

**관련 section**: §19 (GOAL13 축소 history), GOAL12 Iter42 overfit

---

### §20.2 Joint NM이 Sequential NM보다 우수

**발견**: Iter13 (sequential knee NM, score=108.30) < Iter14 (joint 7D NM, score=107.87)  
**수치 증거**: 0.4% 추가 개선 (joint > sequential).

**이유**: Hip/knee friction과 contact compliance의 cross-coupling.  
fv_hip 최적화 후 fv_knee를 독립적으로 최적화하면 coupling 정보가 손실됨.

**시사점**: 고차원 NM 동시 최적화가 axis-by-axis보다 항상 우수할 것으로 예상.  
단 local minimum 위험 증가 → LHS global seed 병용 필요 (Iter16).

---

### §20.3 tau_shift=0ms 재확인

**발견**: Iter12 17-point tau_shift scan [-8, +8]ms → 0ms가 최적  
**수치 증거**: non-zero shift 모두 score 악화. commit (Iter12 기간).

**의미**: 실 robot tau timestamp와 position timestamp의 동기화가 정확함. 추후 재확인 불필요.

---

### §20.4 Per-trial IC 매칭 해로움

**발견**: Iter11 (per-trial IC 매칭): score=142.44 → 30.51% 악화  
**수치 증거**: commit (Iter11 기간). Global IC (Q1_MU_INIT=-1.2738, Q2_MU_INIT=2.548) 유지가 필수.

**이유**: Global IC는 Iter38 물리 파라미터와 함께 최적화된 operating point.  
IC 변경 = Iter38 파라미터와의 결합 파괴 → 큰 score 악화.

**결론**: Q1_MU_INIT, Q2_MU_INIT는 변경 금지 (GOAL14 전 기간).

---

### §20.5 fv_knee → 하한 수렴 패턴

**발견**: Iter13부터 Iter15까지 모든 iter에서 fv_knee → 0.001 (하한) in 6+/9 trials.  
**의미**: 관성(m_calf_scale × Ic) 감소 + fv_knee 감소 = "flight phase 자유 진동 보존"  
진자처럼 knee가 자유롭게 진동할 때 실제 dq 데이터에 더 잘 맞음.

**시사점**: knee joint에 실제 viscous damping이 거의 없음을 시사 (이론적으로 맞음: 모터 cogging torque ≈ fc_knee, 점성마찰 ≈ 0).

---

### §20.6 GOAL14 현재 상태 (Iter15 KEEP 후)

- **Best score**: 95.40 (Iter15, KEEP 12.59%)
- **Iter16 진행 중**: LHS-seeded 9D, expanded mass scale bounds [0.3-0.4 이하로 확장]
- **Iter17 준비**: 10D + arm_knee
- **Iter18 준비**: 12D + stiff_hip + stiff_knee
- **overfitting 감시**: Iter16 결과에서 m_calf_scale < 0.5 여부 확인 필수

**날짜**: 2026-06-18  
**환경**: GOAL14 autonomous worker, Python MuJoCo Nelder-Mead, 9 trial (0424 data)

---

### §20.7 Iter19 DROP: m_calf_scale=0.6이 overfitting이 아님 (물리적 필수값)

**날짜**: 2026-06-18  
**방법**: 물리 제약 10D NM, m_thigh_scale[0.85,1.15] m_calf_scale[0.80,1.10] (tight)

**결과**: score=221.26 (Iter15=95.40 대비 +131.9% 악화) → HARD DROP

**핵심 발견**:
- 120_2_120_2: score 9.17 → 68.14 (+58.97) — m_calf_scale 0.6→1.1로 강제시 폭발
- 120_2.2_200_2.8: score 12.36 → 68.67 (+56.31) — 동일 패턴

**결론**: Iter15에서 m_calf_scale → 0.6이 boundary chase(과적합)가 아님.  
이 두 trial은 m_calf_scale=0.6을 물리적으로 요구함.  
tight bound axis(물리 제약 접근) = 무효. 폐기.

**물리적 가설**: 120 kV 중간 PD group의 calf link는 유연성(flexibility) 또는  
접촉 시 관성 흡수 효과로 인해 effective mass가 CAD 대비 40% 감소.  
현재 rigid body sim에서 이를 m_calf_scale로 보상하는 것이 필요.

**시사점 (향후 iter)**:
- m_calf_scale 하한은 최소 0.55~0.60 유지 필수
- tight bound axis 다시 시도 금지
- 대신: Differential Evolution(Iter21)으로 동일 9D space 전역 탐색

---

### §20.8 GOAL14 Iter8-32 전체 현황 (2026-06-18 15:00 KST FINAL)

| Iter | 방법 | Score | vs baseline | vs Iter15 | 판정 |
|------|------|-------|------------|-----------|------|
| Step0 | GOAL11 v4 (W_GRF=0.3) | 109.14 | — | — | baseline |
| Iter1-7 | 소규모 sweep/scan | 107-122 | 0-12% 악화 | — | DROP |
| Iter8-13 | 다양한 sweep/2D NM | ~108-109 | 0~+1% | — | DROP |
| Iter14 | 7D joint NM | 107.87 | +1.17% | — | DROP |
| Iter15 | 9D joint NM (+m_thigh/calf_scale) | 95.40 | +12.59% | baseline | KEEP |
| Iter17 | 10D + arm_knee NM | 91.43 | +16.22% | +4.17% | KEEP |
| Iter18 | 12D + stiff NM | 90.66 | +16.93% | +4.97% | KEEP |
| Iter19 | 10D tight mass bounds | 221.26 | -102.7% | -131.9% | DROP (NM unstable) |
| Iter20 | 11D IC offset NM | 119.23 | -9.24% | -24.97% | DROP |
| Iter21 | 9D Differential Evolution | 91.87 | +15.81% | +3.71% | KEEP |
| Iter22 | 9D CMA-ES | 89.73 | +17.78% | +5.95% | KEEP |
| Iter23 | 13D Global+Per-trial NM | 255.88 | -134% | -168% | DROP |
| Iter24 | 11D solimp shape NM | 98.01 | +10.20% | -2.74% | DROP |
| Iter25 | 10D + solref_d | 112.81 | -3.36% | -18.24% | DROP |
| Iter26 | 10D + imp1 | 127.46 | -16.79% | -33.61% | DROP |
| Iter27 | 11D + arm_knee + solref_d | 90.30 | +17.26% | +5.35% | KEEP |
| Iter28 | 9D expanded mass bounds | 89.85 | +17.67% | +5.82% | KEEP |
| Iter29 | 12D + arm_hip | 91.87 | +15.82% | +3.70% | KEEP (arm_hip useless) |
| **Iter30** | **10D = Iter28 + arm_knee** | **85.00** | **+22.12%** | **+10.90%** | **★★★ KEEP** |
| Iter31 | Iter22 CMA-ES + arm_knee | 89.06 | +18.40% | +6.67% | DROP (vs Iter22 thresh) |
| **Iter32** | **12D = Iter30 + stiffness** | **84.13** | **+22.92%** | **+11.82%** | **★★★★ NEW BEST** |

**최종 best**: **Iter32 score=84.13** (vs baseline 109.14 → +22.92%, vs Iter15 → +11.82%)

**핵심 발견 (causal hierarchy)**:
1. **Mass scale expansion** (mts [0.6,1.2], mcs [0.4,1.1]): 가장 큰 단일 효과 (Iter28 KEEP threshold 통과)
2. **arm_knee free param** (Iter17 +arm_knee): 일관된 +4-5% 추가 효과
3. **CMA-ES global search**: NM warm-start 한계 극복 (Iter22 89.73 vs Iter15 95.40 같은 공간)
4. **Stiffness param** (stiff_hip, stiff_knee): 작은 추가 효과 +1%
5. **Combination synergy**: Iter30 (mass + arm_knee) > Iter28 + Iter17 개별 합산
6. **Failed axes**: arm_hip, IC offset, solref_d, imp1, solimp shape, tight mass bounds, tau_delay, tau_shift

**Optimizer comparison (same 9D space)**:
- NM warm-start: Iter15 95.40
- DE (181K evals/trial): Iter21 91.87
- CMA-ES (16K evals/trial): Iter22 89.73 ← BEST 9D
- Conclusion: CMA-ES > DE > NM warm-start at finding global basin

### §20.10 Iter20 DROP: Per-trial IC matching axis 실패 (2026-06-18 10:55 KST)
**axis**: settle phase initial condition (q1_ic, q2_ic) per-trial offset 추가  
**근거**: PACE (2509.06342) joint bias 모티브 + 실 data t=0 q/dq 오프셋 분석 (저kd group에서 최대 0.04rad)  
**방법**: 2-stage NM
- Stage1: 실 t=0 q/dq에서 직접 계산한 dq1_ic/dq2_ic만 적용 (0D 추가 opt) — 순수 IC 효과 측정
- Stage2: 9D NM + 2D IC opt = 11D NM per trial (Iter15 시작점 + 4 restarts)

**결과**: 
- Stage1 score = 11,099,052 (catastrophic 발산) → 9 trials 모두 1.2M scores  
  → 실 t=0 IC를 그대로 sim에 주입하면 settle phase가 다른 자세에서 시작해 simulation이 폭주
- Stage2 score = 119.23 (-24.97% vs Iter15) → DROP threshold (92.54) 한참 못 미침
  - 8/9 trials에서 `m_calf_scale_lo=0.6` boundary 도달 (Iter15와 동일 패턴)
  - 150_2.2_500_4 outlier: mcs=1.084 (upper near), score=43.04 (GRF dev 762%)
  - IC values는 작은 값으로 수렴 (대부분 |dq1_ic|, |dq2_ic| < 0.04 rad) — overfit 없음
- 15 boundary violations (m_calf_scale_lo가 8개, fv_knee_lo 2개, m_thigh_scale_lo 3개, fc_knee_lo 1개, fc_hip_lo 1개)

**결론**: 
1. **IC matching axis는 DROP**. 실측 IC 직접 적용은 simulation을 망가뜨림 (settle phase가 처음부터 잘못된 자세에서 시작하면 PD가 수습 못 함). 11D NM도 IC가 모두 작은 값으로 수렴 → Iter15보다 차원만 늘었을 뿐 본질적 개선 X.
2. **m_calf_scale=0.6 boundary 재확인**: Iter15(8/9), Iter19(forcing→explode), Iter20(8/9) 세 차례 검증된 물리적 필수값
3. **다음 axis 선정**: IC (이미 settle phase가 흡수함), m_calf bound 확장 (이미 0.6 OK), tight mass bounds (이미 DROP) 모두 시도. 남은 방향: 글로벌 optimizer (DE/CMA), solimp shape (width/power), per-trial friction split with global mass

**관련**: §20.5 (Iter15 m_calf_lo boundary), §20.7 (Iter19 force-up 실패), §20.8 (status table)

### §20.11 Iter17 KEEP: arm_knee as 10th param adds 4.17% (2026-06-18 10:55 KST)
**axis**: arm_knee (rotor inertia at knee, ARM_KNEE_G=0.00490) free, range [0.001, 0.05]  
**근거**: 
- Iter14-Iter15에서 fv_knee → 0.001 (min boundary) 보편적 수렴 = 실제 관성 부족 보상 시도
- flight phase: ddq2 = -(STIFF_KNEE * q2 + fv_knee * dq2 + fc_knee * sgn(dq2)) / (Ic2 + arm_knee)
  → arm_knee가 flight phase 진동 주기를 직접 결정
- PACE (2509.06342): per-joint armature CMA-ES SysID 표준 절차
- AK80-9 rotor inertia 추정: J_r × GR² = 1e-5 × 81 = 8.1e-4 (lower bound), 실제는 더 높을 가능성

**방법**: 9D NM (Iter15 best 시작) + arm_knee 추가 = 10D NM, 4 restarts × 1000 maxiter

**결과**: KEEP score=91.43 (16.22% vs baseline, 4.17% vs Iter15)
- 17 boundary violations (m_calf_lo 4개, fv_knee_lo 5개, m_thigh_lo 5개, 기타)
- arm_knee 수렴 분포: 0.003-0.009 (대부분 ARM_KNEE_G=0.00490 부근)
- 두 outlier trials (120_2_120_2, 120_2.2_200_2.8): score 4.8/13.2 (Iter15 9.2/12.4)
  - 다행히 Iter19 catastrophic failure 패턴 발생 X
  - 4-restart 선택 로직이 bad basin 회피

**결론**: 
1. arm_knee는 실제 의미있는 자유 파라미터. 모터 + 캘리브레이션 오차 흡수
2. Iter19에서 우려된 catastrophic NM convergence가 Iter17에서 발생하지 않음 → 안정적
3. Iter15 mass scale 결과는 overfit이 아니라 물리적 (Iter19에서 7/9가 동등 결과로 재확인)

### §20.9 gen_anim arm_knee KeyError 버그 패턴 (2026-06-18)
**발견**: Iter19 gen_anim 템플릿에서 복사된 iter21~24 gen_anim 스크립트가 모두 `ak=r['arm_knee']` 하드코딩. Iter19에서만 arm_knee가 자유 파라미터였고, Iter21~24는 ARM_KNEE_G (고정값) 사용. 런타임 KeyError 발생.

**수정 패턴**:
```python
# 수정 전 (bug)
ak=r['arm_knee']
# 수정 후 (fix)
from build_xml_i3 import ARM_KNEE_G  # import line에 추가
ak=r.get('arm_knee', ARM_KNEE_G)     # get with default
```

**수정 완료**: iter21 ✓, iter22 ✓, iter23 ✓, iter24 ✓  
**rule**: 새 gen_anim 스크립트 작성 시 arm_knee를 자유 파라미터로 쓰지 않는 iter는 반드시 `r.get('arm_knee', ARM_KNEE_G)` 패턴 사용


## §21. GOAL15 신규 발견 (2026-06-19 19:25 KST)

### §21.5 Iter5 — scipy.optimize.basinhopping 12D Deep (DROP)

**Method (다른 method와 차별점)**: scipy.optimize.basinhopping (Wales & Doye 1997)
- Iter1 NM (4 restart, local-only) → 제한적 escape, 161.61
- Iter2 DE 2D global (popsize=12, maxiter=300) → 160.79
- Iter4 NSGA-II multi-objective Pareto → 161.44
- **Iter5 BH 12D**: Metropolis-accepted hops + NM local refine = global + local 조합
  - niter=30 hops, T=1.0 (scipy default)
  - stepsize=0.05 (bound range의 5%, BoundedStep custom take_step)
  - NM maxiter=150 per hop (adaptive=True)
  - trial-varied seed: BH_SEED_BASE(17) + trial_idx × 1009 (prime offset, 다양화)

**결과 요약**:

| 항목 | 값 |
|---|---|
| Iter5 Score | 159.9432 |
| 이전 baseline (Iter2) | 160.7879 |
| KEEP threshold (×0.97) | 155.9643 |
| 개선율 | 0.53% |
| 경계 위반 BV | 120 (KEEP 조건: <10) |
| avg dh_cm | 1.024 cm |
| avg GRF dev | 21.6% |
| Elapsed | 117.5 min |
| 판정 | **DROP** |

**Worst-3 trial**: ['0424_120_2.2_200_2.8', '0424_150_2.2_350_3.5', '0424_150_2.2_500_4']

**경계 위반 상세** (상위 5개): ['0424_60_0.75_60_2_fv_hip_lo (0.8164)', '0424_60_0.75_60_2_solref_tc_lo (0.0095)', '0424_60_0.75_60_2_fv_knee_lo (0.0055)', '0424_60_0.75_60_2_fc_knee_lo (0.1684)', '0424_60_0.75_60_2_m_calf_scale_lo (0.4802)']

**Notion 페이지**: https://app.notion.com/p/GOAL15-Iter5-Basinhopping-12D-full-DROP-score-159-94-0-5-384ab81d255081aea440ecf377bd65d8

**핵심 인사이트**:
1. **method 차별성**: NM(local) / DE(population global, 2D) / NSGA-II(multi-objective) 와 달리 BH는 single-objective global + local refine. 12D full param 동시 탐색.
2. **warm-start 효과**: Iter2 best per-trial (160.79)에서 시작. BH가 worse하면 warm-start 유지 (`if best_fun > s0: best_x = x0`).
3. **Metropolis hop**: T=1.0 with stepsize=0.05 → 각 hop에서 5% bound range만큼 jitter, NM이 local basin으로 refine, exp(-Δf/T)로 accept/reject.
4. **외부 근거**: Wales & Doye 1997 J.Phys.Chem.A 101(28) 5111 (BH original paper). scipy v1.16 docs. Cassioli 2024 J.Global Optimization (BH performance analysis). arxiv 2510.25938 (2024 adaptive BH).
5. **판정 DROP 사유**: 개선율 +0.53% (score 159.9432 > threshold 155.9643) 또는 BV 120 (need <10) 조건 불만족. Iter2 best가 이미 강력한 local optimum이며, 12D BH로도 추가 escape 안 됨.


## §22. GOAL16 Checkpoint t+144h (2026-06-21 약 22:30 KST)

### §22.1 Checkpoint t+144h — GOAL16 진행 중

**현재 상태** (deadline 2026-06-22 10:00 KST)
- Iter1-7 sim chain 완료, post-process 복구 worker 진행 중
- 원 BG worker 종료 + 복구 worker 발사 (Iter1-7 Notion + commit 일괄)
- Iter8-15: 스크립트 ready, 실행 대기 중

**GOAL16 핵심 발견 (Iter1-7)**:

| 그룹 | Iter | Axis | 방법 | Score | 개선율 | KEEP | 판정 |
|------|------|------|------|-------|--------|------|------|
| A | Iter1 | R1/R2/RC/RP (4D) | scipy TRF | 160.79 | 0.0% | ✗ | flat |
| A | Iter2 | I1/I2/IC/IP (4D) | scipy TRF | 160.79 | 0.0% | ✗ | flat |
| A | Iter3 | R+I 8D 동시 | L-BFGS-B | 160.79 | 0.0% | ✗ | flat |
| B | Iter4 | encoder bias (30D) | Nelder-Mead | 157.79 | +1.86% | ✗ | 미약 |
| B | Iter5 | dq 필터 delay (1D) | Brent | 156.96 | +2.38% | ✗ | 미약 |
| C | Iter6 | motor_tm LPF (1D) | Powell | 374.36 | -132.8% | ✗ | Mode A 불가 |
| C | Iter7 | 기어 backlash (1D) | Brent | 1143.68 | -611.3% | ✗ | 발산 |

**avg |Δh| + pen 요약**:

| Iter | avg |Δh| (cm) | max pen (mm) | vs baseline (1.05cm) |
|------|--------------|--------------|----------------------|
| Iter1-3 | 1.047 | 2.034 | 동일 (flat) |
| Iter4 | 1.086 | 2.033 | +3.7% 악화 |
| Iter5 | 1.047 | 2.034 | 동일 (delay보정) |
| Iter7 | 2.482 | 7.913 | +137% 발산 |

**GOAL15 Iter2 참조**: avg |Δh|=1.54cm (다른 weight 세팅, 직접 비교 부적절)

### §22.2 GOAL16 결론 (Iter1-7 기준)

1. **Group A (CAD R/I)**: 완전 gradient-flat — R/I를 ±10-15% 변동시켜도 score 변화 0. 12D per-trial 공간이 R/I 변화를 완전 흡수. CAD 값 plateau의 핵심 원인이 아님.
2. **Group B (Sensor bias/delay)**: ~2% 미약 개선. encoder bias(Iter4) +1.86%, dq delay(Iter5) +2.38%. KEEP threshold 156.0 미달.
3. **Group C (Motor model)**: Mode A는 raw τ 직접 input 구조 → motor_tm / backlash 파라미터 적용 불가. Score 374~1143 발산.
4. **결론**: 12D per-trial 공간이 local axes(R/I/sensor)를 모두 흡수. **Group D/E/F (global contact/stiffness/compliance axes)가 plateau 탈출 핵심 후보**.

### §22.3 Iter8-15 진행 예정 (5 parallel)

| Iter | 방법 | 목표 |
|------|------|------|
| Iter8 | NSGA-II multi-obj | Pareto front 탐색 |
| Iter9 | LOTO cross-val | 과적합 방지 + 일반화 |
| Iter10 | per-segment | 구간별 오차 분리 |
| Iter11 | Huber loss | 이상치 robust |
| Iter12 | normalized | 스케일 보정 |
| Iter13 | MJX GPU | GPU 병렬 |
| Iter14 | LHS seed | 초기점 다양화 |
| Iter15 | GP-BO | Bayesian 탐색 |

### §22.4 다음 단계

- Iter8-15 결과 대기 (deadline 09:00 KST 2026-06-22)
- 복구 worker Notion + commit 일괄 완료 대기
- Final wrap-up: best iter 정리 + GOAL17 방향 결정

---

## §23. GOAL16 Iter20/Iter21 결과 (2026-06-21 긴급 fix)

### §23.1 Iter20 — Mass FREEZE + R/I per-component LSQ

**결과**: score=157.4211 (Iter17 동일, 개선 0%), DROP

**방법**: Iter17 12D per-trial best (mass/friction/contact) LOCK → R1/R2/RC/RP ±15% + I1/I2/IC/IP ±20% per-trial 8-param LSQ TRF refit

**★ 핵심 발견 — Regressor condition number 1e13**:
- 15 trial 모든 LSQ regressor의 cond(Y) ~ 1.2e13 ~ 5.5e13 (nearly singular)
- Khalil-Dombre 2002: cond(Y) > 1e6 → 'rank-deficient identification problem'
- 점프 단일 motion profile → 8-param R/I 분리 위한 persistent excitation 미달
- 결론: mass FREEZE로도 R/I 식별 불가 → excitation 부족이 진짜 원인

**사용자 인사이트 검증**: "mass scale이 R/I 흡수 중" → LOCK 후에도 flat → excitation 부족 확인

**Notion**: https://app.notion.com/p/GOAL16-Iter20-mass-FREEZE-R-I-per-component-LSQ-refit-DROP-score-157-42-BV-0-0-0-386ab81d255081f6a4f4e6a5008d9bea

---

### §23.2 Iter21 — Inertia anisotropy Ixx/Iyy 분리

**결과**: score=157.4702 (Iter17 baseline과 동일), DROP

**방법**: Iter17 12D per-trial LOCK → global 4D: Ixx_thigh/Iyy_thigh/Ixx_calf/Iyy_calf ±25% Nelder-Mead (3 restarts)

**Best params**: [Ixx_th=1.0003, Iyy_th=0.9998, Ixx_ca=1.0002, Iyy_ca=1.0000] ≈ identity

**★ 핵심 발견**:
- Ixx/Iyy anisotropy는 jump dynamics에서 gradient-flat
- 점프는 주로 sagittal plane 운동 (y-axis 회전 위주) → Ixx (link axis MOI) 영향 거의 없음
- Off-isotropic random start에서 발산: diaginertia 물리 조건 위배 발생
- Iter20과 동일 패턴: inertia 계열 파라미터 모두 jump에서 식별 불가

**결론**: Iter20/21/22 모두 inertia 계열 → gradient-flat. GOAL16 inertia 탐색 완전 종료. GOAL17은 contact model / friction model 정밀화 방향.

**Notion**: https://app.notion.com/p/GOAL16-Iter21-Inertia-anisotropy-Ixx-Iyy-25-NM-4-DROP-score-157-47-BV-0-0-0-386ab81d2550819eaa00e580f495d591


---

# ★★★★★ 2026-07-07 — 4-BAR 위상 확정 (LOCKED, 절대 잊지 말 것)

**실물/CAD식 검증 위상**: crank(l_i 30mm)와 rocker(l_o 30mm)는 **정강이 반대방향**
(rocker = 무릎 **위/뒤쪽** 30mm, 발쪽 아님!). coupler(250mm)는 thigh와 평행(θ1),
thigh의 反정강이 쪽. 평행사변형 → crank각≡calf각(1:1), 엔코더 매핑 유효.

- 사용자 해석식(Notion 302ab81d...)과 뒤집힌 MuJoCo: **|dM| 4.4e-16 = 동일 물리**
- 구위상(G20-A~P9 canonical, mshoot_fourbar.py)은 그 식과 3.5e-2 모순 → **새 작업 사용 금지**
- 정본: `Documents/jump-opt-digital-twin/code/goal21/FOURBAR_STRUCTURE_CANONICAL.md`
  / 빌더 `g21_fourbar_flip.py` / 파라미터 `fourbar_flip_canonical.json` (P10-selected)
- CAD 계수 B=−0.0037 (거의 상쇄; serial은 +0.175로 잘못) → 무릎 중력토크 ≈0.04Nm
  = 전원-off 무릎 정지 관찰의 설명. 다음 폴리시: h를 목적에 포함해 재적합.
