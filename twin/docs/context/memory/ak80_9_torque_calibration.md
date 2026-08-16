---
name: AK80-9 Motor Model from TMotorCANControl GitHub (CRITICAL — FULL MODEL)
description: AK80-9 정밀 5-파라미터 토크 모델(a_hat) + 모든 모터 상수. UMich Neurobionics Lab 측정값. v7+ sweep에서 고정값으로 사용.
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# 출처
- **GitHub**: https://github.com/neurobionics/TMotorCANControl
- **랩**: University of Michigan (UMich) Neurobionics Lab
- **파일**: `src/TMotorCANControl/mit_can.py:29~46` (params), `src/TMotorCANControl/test/mit_can/derive_torque_constants.py` (식별 코드)
- **사용자 결정 (26.04.27)**: 우리 motor 모델 미상이므로 UMich a_hat을 *참값으로 신뢰*하고 사용

# 우리 데이터의 currentTorque 컬럼
- **CAN MIT 모드에서 AK80-9 모터가 직접 보고한 raw iTM 값** (사용자 명시 확인, 26.04.27)
- 모터 펌웨어가 자기 데이터시트 Kt_TMotor=0.091 기준으로 current → torque 환산해서 보고
- 실제 출력 토크와 다름 (단순 비율 0.7457 또는 정밀 a_hat 모델로 변환 필요)

# AK80-9 모터 상수 (mit_can.py:29~46)

```python
'AK80-9': {
    'P_min':  -12.5,         # rad
    'P_max':  +12.5,         # rad
    'V_min':  -50.0,         # rad/s
    'V_max':  +50.0,         # rad/s
    'T_min':  -18.0,         # Nm (output side)
    'T_max':  +18.0,         # Nm
    'Kp_min':  0.0,
    'Kp_max':  500.0,        # Nm/rad
    'Kd_min':  0.0,
    'Kd_max':  5.0,          # Nm·s/rad
    'Kt_TMotor':       0.091,  # T-Motor 데이터시트 (1/Kvll)
    'Current_Factor':  0.59,   # qaxis current 보정 (d/q 정렬 손실)
    'Kt_actual':       0.115,  # ★ UMich 실측 (스펙보다 26% 큼)
    'GEAR_RATIO':      9.0,    # 9:1
    'Use_derived_torque_constants': True,   # AK80-9만 True
    'a_hat': [0.0, 1.15605006, 4.17389589e-04, 2.68556072e-01, 4.90424140e-02]
},
```

추가 (servo_can.py): `'NUM_POLE_PAIRS': 21` (자석 극쌍 수)

# 단순 변환식 (1차 근사, 대략용)

```
τ_actual_output = τ_reported × (Current_Factor × Kt_actual / Kt_TMotor)
                = τ_reported × (0.59 × 0.115 / 0.091)
                = τ_reported × 0.7457
```

# ★ 정밀 5-파라미터 모델 (a_hat) — v7+ sweep에 사용

## 모델 형태 (mit_can.py docstring + derive_torque_constants.py:56~63)

```
ε = 0.1   # rad/s (smooth sign threshold)
smooth(v) = |v| / (ε + |v|)

τ_actual = a₀
         + a₁ · gr·kt·i             ← 선형 전기 토크 (Kt 보정)
         − a₂ · gr·|i|·i             ← 전류 saturation (current²)
         − a₃ · sign(v)·smooth(v)    ← Coulomb 마찰 (smooth zero-cross)
         − a₄ · |i|·sign(v)·smooth(v) ← 부하 종속 기어박스 마찰
```

여기서:
- `gr = 9.0`, `kt = 0.091`
- `i` = qaxis current [A]
- `v` = output side velocity [rad/s] (관절 각속도)

## a_hat 파라미터 의미 (UMich 회귀 결과)

| 항 | 값 | 의미 |
|---|---|---|
| **a₀** | 0.0 | 토크 bias (UMich 모터에선 0) |
| **a₁** | 1.15605006 | 선형 Kt 보정 (실제 Kt_eff ≈ 1.156·0.091 = 0.1052 Nm/A) |
| **a₂** | 4.17389589e-04 | 전류 saturation 계수 (current² 항) — 고전류에서 효율↓ |
| **a₃** | 0.26855607 (Nm) | Coulomb 마찰 (속도 부호 따라, smooth) |
| **a₄** | 0.04904241 | 부하 종속 기어 마찰 (∝ \|current\|) |

## currentTorque → qaxis current 변환

```python
i_qaxis = (Current_Factor / (GEAR_RATIO × Kt_TMotor)) × τ_reported
        = (0.59 / (9 × 0.091)) × τ_reported
        = 0.7204 × τ_reported
```

## 수치 검증 (예: τ_reported = 20 Nm, v = 5 rad/s)

```
i = 0.7204 × 20 = 14.4 A
smooth = 5 / (0.1 + 5) = 0.980

τ_actual = 0
         + 1.156 × 9 × 0.091 × 14.4         = +13.62 Nm
         − 4.17e-4 × 9 × 14.4 × 14.4         = −0.78 Nm
         − 0.269 × (+1) × 0.980              = −0.26 Nm
         − 0.049 × 14.4 × (+1) × 0.980       = −0.69 Nm
                                             = 11.89 Nm

(단순 비율 0.7457로 계산 시 = 14.91 Nm — a_hat 정밀 모델은 약 20% 더 작음)
```

# Why (왜 이 모델을 사용)

- a_hat은 외부 ADC 토크 센서로 *직접* 측정한 회귀 결과 → 우리 sweep score(간접 추정)보다 우선
- 5개 항 모두 물리적 motivation 있음 (전기 변환 + 전류 saturation + 친마찰 + 부하 종속)
- AK80-9는 UMich이 *직접 측정한 유일한 모터* (다른 AK 모델들은 모두 `UNTESTED CONSTANT!` 표기)

# How to apply (sim 적용 방법)

```python
# 모터 상수 (FIXED)
KT_TM = 0.091; GR = 9.0; CF_RATIO = 0.59; EPS_V = 0.1
A_HAT = [0.0, 1.15605006, 4.17389589e-4, 0.26855607, 0.04904241]

def actual_torque(tau_reported, v):
    """모터 보고 토크(iTM) + 관절 속도 → 실제 관절 토크"""
    i = (CF_RATIO / (GR * KT_TM)) * tau_reported   # 0.7204 × tau_reported
    s = abs(v) / (EPS_V + abs(v))
    return (A_HAT[0]
          + A_HAT[1] * GR * KT_TM * i
          - A_HAT[2] * GR * abs(i) * i
          - A_HAT[3] * np.sign(v) * s
          - A_HAT[4] * abs(i) * np.sign(v) * s)

# 1. PD 단계 (sp, sd가 모터 PD 비이상성 흡수)
tau_cmd = sp * Kp_drv * (qd - q) + sd * Kd_drv * (dqd - dq)

# 2. a_hat으로 실제 관절 토크
tau_actual = actual_torque(tau_cmd, v)

# 3. 동역학에 *실제* 토크 투입 (uno joint friction model 더 추가 안 함 — a_hat이 흡수)
M·ddq + C·dq + G - J^T·F_grf = tau_actual
```

# v6 sweep과의 차이

v6는 motor 모델 *없이* `tau_cmd`를 그대로 dynamics에 사용 → boundary hugging 다수 (sp=0.7, alpha=0.9, gBv=1.0, Is2=0.035, Kv=0.002, bc=20, cf=0.05, jf=0.35).
v7은 a_hat을 baking → motor 측 model error 제거 → boundary hugging이 dynamics에서 풀려야 함.

# v7에서 제거된 우리 모델 항 (a_hat이 흡수)

- `cf · tanh(dq/0.3)` (Coulomb)  → a₃
- `jf · dq` (viscous)            → a_hat에 없음 (의도적)
- `nv · dq³` (cubic)             → a_hat에 없음 (필요 없음 결정)
- `sb · exp · tanh` (Stribeck)   → a_hat에 없음 (smooth Coulomb이 대체)
- `off` (bias)                   → a₀ (=0)
- `tm` (1차 LPF)                 → 별도 물리 (transient), 우리 dt=1ms와 비슷 → 0으로 고정

# 한계 인식

- a_hat은 **UMich 한 대의 AK80-9** 측정값. 우리 motor와 ±5~10% 차이 가능
- 만약 v7 결과에서 sp/sd가 또 boundary면 → 우리 데이터로 a_hat refit 필요 (Option B/C)
