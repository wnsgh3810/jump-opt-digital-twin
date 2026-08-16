# GOAL4 Priority 1: 실 robot torque-mode 검증 protocol

## 한 줄

> **GOAL3 V15 NLP가 만든 τ_traj(t)를 AK80-9 torque control mode로 직접 입력 → 실측 τ, q, dq, GRF 측정 → 시뮬과 일치 여부 검증 (사용자 진짜 metric).**

## Mission 정의

사용자 metric:
> **"NLP가 만든 q*, dq*만으로 실 robot 제어 시 실측 τ, GRF가 NLP와 일치"**

여기서 "NLP가 만든 q*, dq*"의 진짜 의미는 두 가지로 갈림:
1. **Inverse 검증**: NLP optimal q*, dq*를 PD-tracking → 실측 τ vs NLP τ 비교
2. **Forward 검증**: NLP optimal τ*만 직접 입력 (FF only, no PD) → 실측 q, dq vs NLP q*, dq* 비교

**GOAL3 V15 결과 (시뮬레이션 surrogate)**: Forward 검증에서 τ_diff 0.0001/0.003 Nm 달성

**GOAL4 미션**: 실 robot에서 forward 검증 ✓

## 사전 준비

### 1. NLP solution 준비 (GOAL3 V15)

```python
# Load V15 robust NLP solution
import numpy as np

sol = np.load("goal3/v25_ahat_refit/v15_jump_robust.npz")
t_traj   = sol['t']        # [N+1] time
q_traj   = sol['q']        # [N+1, 2] joint pos (hip, knee)
dq_traj  = sol['dq']       # [N+1, 2] joint vel
tau_traj = sol['tau']      # [N, 2]   joint torque (NLP output)
grf_traj = sol['grf']      # [N, 2]   GRF (kinetic, derived)
ste_traj = sol['ste']      # scalar    lift-off time

print(f"NLP duration: {t_traj[-1]:.3f}s, lift-off: {ste_traj:.3f}s")
print(f"τ_max: hip {np.abs(tau_traj[:, 0]).max():.2f}, knee {np.abs(tau_traj[:, 1]).max():.2f} Nm")
```

### 2. AK80-9 torque mode 설정

AK80-9는 default가 **position mode** + internal PD (Kp, Kd). torque mode 진입:

```c
// MIT mini cheetah motor CAN protocol
// 0x01: torque-only mode (Kp=0, Kd=0)
// 0x07: torque + light damping (Kp=0, Kd=1)

void enter_torque_mode(uint8_t motor_id) {
    can_send(motor_id, 0xFFFFFFFFFFFFFFFC);  // Enter motor mode
    set_kp_kd(motor_id, 0.0, 0.0);             // Pure torque mode
}

void send_torque_cmd(uint8_t motor_id, float tau_nm) {
    // Pack τ → 12-bit CAN frame (±18 Nm range)
    uint16_t tau_packed = float_to_uint(tau_nm, -TAU_MAX, TAU_MAX, 12);
    can_send(motor_id, [0, 0, 0, 0, 0, 0, tau_packed >> 4, tau_packed & 0xFF]);
}
```

**중요**: a_hat 변환 적용 → 실제 commanded τ는 NLP τ가 아니라 **a_hat ∘ NLP τ**:

```python
def cmd_torque(tau_nlp, dq):
    """Apply V25 a_hat to convert NLP τ to motor command."""
    # Paper a_hat 5-param (sgn(v) only, pure paper formula)
    a0, a1, a2, a3, a4 = THETA_V25['a_hat']
    sign_dq = np.sign(dq)
    tau_cmd = (tau_nlp - a0 * sign_dq - a1 * dq) / (a2 + a3 * abs(tau_nlp) + a4 * sign_dq * tau_nlp)
    return np.clip(tau_cmd, -18, 18)
```

### 3. Logging spec

500 Hz minimum (NLP grid 100 Hz × 5 oversample). 항목:

| 신호 | 출처 | 해석 |
|---|---|---|
| `t [s]` | clock | 시간 |
| `tau_cmd [Nm] × 2` | command | 보낸 토크 명령 |
| `tau_measured [Nm] × 2` | CAN feedback | 실측 토크 (currentTorque) |
| `q [rad] × 2` | encoder | hip, knee 각도 |
| `dq [rad/s] × 2` | encoder differential | 각속도 |
| `grf_z [N]` | F/T sensor | 수직 GRF (점프 GRF) |
| `grf_x [N]` | F/T sensor | 수평 GRF (사면 미끄럼) |
| `imu_acc_z [m/s²]` | IMU | 본체 가속 |
| `state` | FSM | crouch / launch / flight / land |

### 4. 안전 envelope

- τ_cmd hard clip: ±15 Nm (AK80 18Nm 보수적)
- q_min/q_max breach → emergency stop (NLP boundary 5° margin)
- dq > 30 rad/s → emergency stop
- 통신 timeout 100ms → stop

## Protocol steps

### Step 1: Crouch hold (1s)

NLP 시작 자세 (q1 = -1.20, q2 = -2.50) 유지 → 외란 흡수 + 측정 0점.

### Step 2: τ_traj playback (open-loop)

```python
T_total = t_traj[-1]   # e.g., 0.5s NLP duration
log = []
dt_real = 0.002        # 500 Hz
N_steps = int(T_total / dt_real)

for k in range(N_steps):
    t = k * dt_real
    # Interp NLP τ at current t
    tau_nlp = np.array([
        np.interp(t, t_traj[:-1], tau_traj[:, 0]),
        np.interp(t, t_traj[:-1], tau_traj[:, 1])
    ])
    # Read state
    q_cur, dq_cur = read_motors()
    # a_hat convert
    tau_cmd = cmd_torque(tau_nlp, dq_cur)
    # Send
    send_torque_cmd(MOTOR_HIP, tau_cmd[0])
    send_torque_cmd(MOTOR_KNEE, tau_cmd[1])
    # Measure
    tau_meas = read_torque()  # currentTorque from CAN
    grf = read_grf()
    log.append([t, tau_cmd, tau_meas, q_cur, dq_cur, grf])
    sleep_until(t + dt_real)

save_log("torque_mode_jump_001.npz")
```

### Step 3: Repeat 5 trials

- Baseline (no payload, level ground)
- Trial 1-5: 동일 NLP τ_traj
- Run-to-run variability 측정 (실 robot stochasticity)

### Step 4: Compare to NLP

```python
import numpy as np
log = np.load("torque_mode_jump_001.npz")

# 1. Tau matching
tau_diff_hip = np.abs(log['tau_meas'][:, 0] - log['tau_nlp'][:, 0]).mean()
tau_diff_knee = np.abs(log['tau_meas'][:, 1] - log['tau_nlp'][:, 1]).mean()
print(f"τ_diff: hip {tau_diff_hip:.4f}, knee {tau_diff_knee:.4f} Nm")
# 예상: GOAL3 V15 simulation 0.0001/0.003 Nm
# 현실: a_hat residual + measurement noise + saturation 영역 외 → 0.1~0.5 Nm 예상

# 2. q matching
q_rmse_hip = np.sqrt(((log['q'][:, 0] - q_traj_interp[:, 0])**2).mean()) * 180/np.pi
q_rmse_knee = np.sqrt(((log['q'][:, 1] - q_traj_interp[:, 1])**2).mean()) * 180/np.pi
print(f"q RMSE: hip {q_rmse_hip:.2f}°, knee {q_rmse_knee:.2f}°")
# 예상: GOAL3 V21 시뮬 0.1°/2.5° (T=0.05s)
# 현실: contact compliance + saturation + 외란 → 5-15° 예상

# 3. GRF matching
grf_rmse = np.sqrt(((log['grf'][:, 1] - grf_nlp_interp)**2).mean())
print(f"GRF RMSE: {grf_rmse:.2f} N")
# 예상: 시뮬 ~5N
# 현실: 알파 + foot model + 측정 노이즈 → 20-50 N

# 4. Lift-off time
ste_real = first_grf_zero(log['grf'])
ste_diff = abs(ste_real - sol['ste'])
print(f"Lift-off: NLP {sol['ste']:.3f}s vs real {ste_real:.3f}s")
```

## 합격/불합격 기준

| Metric | GOAL3 시뮬 | 합격 기준 | 의미 |
|---|---|---|---|
| τ_diff hip [Nm] | 0.0001 | ≤ 0.5 | a_hat 변환 정확 |
| τ_diff knee [Nm] | 0.003 | ≤ 0.5 | a_hat 변환 정확 |
| q RMSE hip [°] | 0.1 | ≤ 5 | 누적 발산 최소 |
| q RMSE knee [°] | 2.5 | ≤ 10 | 누적 발산 최소 |
| GRF RMSE [N] | 5 | ≤ 30 | 접촉 모델 일치 |
| Lift-off Δt [ms] | 0 | ≤ 5 | 점프 타이밍 일치 |
| Jump h Δ [m] | 0 | ≤ 0.05 | 결과 일치 |

**핵심**: 사용자 강조 "점프 높이 매칭은 wrong metric" — h 일치는 부수적, τ/q 일치가 진짜 metric.

## 예상 실패 mode + 대응

1. **τ_diff > 1 Nm**: a_hat 변환 불충분 (Stribeck or saturation 영역)
   → V25 + temperature compensation 추가 (Priority 4)

2. **q RMSE 발산 (>20°)**: open-loop unstable
   → outer-loop adaptive control (FF + small PD correction)

3. **GRF 부정확 (>50 N)**: foot model 한계 (alpha 단일 contact)
   → multi-point foot + softer contact (Priority 2/5)

4. **Lift-off 어긋남 (>20ms)**: V8 model의 stance phase 부정확
   → CVT clutch dynamics (Priority 2)

5. **Saturation 영역에서 발산**: AK80 thermal limit (실험실 온도에 따라 변동)
   → temperature 측정 + thermal model

## 후속 작업

1. Trial 1 결과 확보 → GOAL4 V6 (실험 실측 데이터 추가 ID)
2. 발산 mode 진단 → V7-V10 모델 개선
3. MJX/Warp simulator에서 실 robot 실측 재현 (digital twin)

## 일정

- D-day: 2026-06-07 (다음날) 실험실 access
- 사전: 코드 작성 + dry-run 시뮬 (오늘 끝)
- D-day: 5 trial × 3 height (0.3, 0.5, 0.7m NLP) × 2 task (jump, s2s) = 30 trial
- D+1: 분석 + Notion 보고서
