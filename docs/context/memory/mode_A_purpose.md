---
name: mode-a-purpose
description: Mode A 본질 — Paper 변환 actual motor torque 입력 시 sim이 실측 q/dq/GRF 그대로 재현하면 디지털 트윈 달성. saturation κ 무관 (이미 hardware saturated 값).
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Mode A의 본질 (★ 사용자 명시 26.06.09, 절대 잊지 말 것)

> **"real torque를 줬을 때 실제 q, dq, GRF 대로 움직여야 하는 게 Mode A의 목표"**
> **"저장된 xlsx 파일의 currentTorque는 Paper 식으로 해석해야 모터가 실제로 낸 토크값"**

## 입력/출력 정의

- **입력**: `currentTorque` (raw iTM, motor 펌웨어가 Kt=0.091로 환산해 보고한 값) → `paper_a_hat(τ_raw, dq)` 변환 → **모터가 실제로 낸 actual output torque**
- **Sim ctrl input** = 이 actual output torque (× tau_scale 보정)
- **출력**: sim의 q, dq, τ_filt, GRF
- **판정**: 같은 input 시 sim 출력이 실측 (q, dq, currentTorque, Current_GRF)와 모든 시점에서 일치

## Why (왜 이게 디지털 트윈)

- 실 motor가 실제로 낸 토크를 그대로 input → 같은 dynamics 거치면 같은 응답이어야 함
- Sim과 real이 같은 input에서 다른 출력 = ★ **dynamics 모델 부정확** (mass/inertia/friction/flex/contact)
- → Mode A로 motor 외부 동역학 (link mass, joint friction, contact, flex)을 정확히 식별 가능

## 핵심 정정 (자주 잊는 함정)

★ **Saturation κ는 Mode A에서 무관**: input이 이미 motor saturation 거친 actual output. sim에서 추가 saturation 모델 X.

★ **csv의 `kneeCurrentTorquePaper`와 npz의 `tau2_real`이 numerical 다름**:
- `phase0_data_load.py`의 `paper_a_hat` (sgn(v) only, no smooth) → npz `tau_real` (≈20 Nm knee peak)
- csv의 `Paper` column → 다른 변환 모듈일 가능성 (~24-25 Nm knee peak)
- ★ **Stage 53/Mode A sim의 진짜 input source는 `data_loaded.npz`의 `tau_real`** — csv 단순 max로 분석 금지

★ **Pure Paper sgn(v) only** 원칙 ([[feedback_pure_paper_formula]]):
```python
def paper_a_hat(tau_reported, v):
    Iq = (CF / (GR * KT)) * tau_reported   # CF=0.59, GR=9, KT=0.091
    return (A_HAT[0]
            + A_HAT[1] * GR * KT * Iq
            - A_HAT[2] * GR * np.abs(Iq) * Iq
            - A_HAT[3] * np.sign(v)              # ← sign(v) only, NO smooth(v)
            - A_HAT[4] * np.abs(Iq) * np.sign(v)) # ← sign(v) only
```

## Mode A vs Mode B 구별 (메모리 [[pd_sim_purpose]]와 함께 보기)

| 항목 | Mode A | Mode B |
|---|---|---|
| 입력 | `paper_a_hat(currentTorque)` (실 motor output τ) | `q_des, dq_des` (PD setpoint) |
| Sim ctrl | direct torque input | sim 내부 PD가 τ 계산 |
| Saturation κ | 무관 (이미 saturated input) | 필요 (sim PD output을 saturate) |
| 사용 위치 | Stage 14~ (high-fidelity sysid) | Stage 1~13 초기 (PD sim) |

## How to apply (분석 시 절대 기준)

1. **Mode A 분석 시 saturation κ 가설 즉시 폐기** (이미 hardware saturated input)
2. **데이터 source 확인**: sim에 들어가는 `tau_real`은 `data_loaded.npz` (phase0의 paper_a_hat). csv는 다른 모듈일 수 있어 verify.
3. **PD trial 비교 시 sim vs real dq peak 둘 다 확인**:
   - Real dq peak: PD ↑일수록 ↑ (hardware reality, motor가 강하게 추종해 큰 가속)
   - Sim dq peak: PD ↑일수록 ↓ (model 부정확) — ★ 진짜 model error 신호
4. **PD ↑일수록 sim-real dq gap ↑가 진짜 model error 진단 패턴**

## ★ 2026-06-23 정정 — arm_hip = 0 LOCK 폐기

**기존 잘못된 기록 (이전 sub-agent inference, 사용자 명시 X)**:
- "arm_hip = 0 LOCK" — GOAL12 iter38에서 sub-agent가 적어놓은 것. 사용자는 이렇게 명시한 적 없음.

**사용자 발화 원문 (2026-06-23)**: "arm_hip은 왜 0이야 나 그렇게 얘기한 적 없는데"

**정정 후**:
- **arm_hip은 fit axis** (Tier 1 #4 CAD per-component, armature 그룹)
- range: [0.001, 0.05] (arm_knee와 동등)
- 의미: hip motor rotor inertia × gear_ratio² (AK80-9의 rotor 무게 무시 X)

## ★ Mode A LOCK (사용자 명시 정확, 절대 변경 X)

**진짜 사용자 명시 LOCK 항목**:
- **tau_scale=1.0 LOCK** (Mode A 본질 — ctrl=-tau_real raw, 어떤 modifier도 X)
- **paper_a_hat Pure Paper sgn(v) only** (no smoothing, npz tau_real에 baked)
- **ctrl_sim = -tau_real** (sign flip only)
- L1=L2=0.25m, LC=0.03m (실측 정확)
- thigh/calf contype=1 conaffinity=1 (commit cdcb1001 fix)

**일반 lesson**: 이전 GOAL12/14/16에 "LOCK"으로 표시된 항목은 **사용자 명시인지 sub-agent inference인지 구분 필요**. 의심나면 사용자 재확인. 특히 default-0 또는 default-1 값이 "LOCK"으로 적힌 경우는 sub-agent 자동 inference 가능성 높음.

## 관련 메모리

[[pd_sim_purpose]] [[digital_twin_priority]] [[feedback_pure_paper_formula]] [[ak80_9_torque_calibration]] [[goal8_findings_phase14_18]]
