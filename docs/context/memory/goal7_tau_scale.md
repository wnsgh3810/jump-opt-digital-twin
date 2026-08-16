---
name: goal7-tau-scale
description: GOAL7 발견 tau_scale 5-12% 실측 토크 underread 보정 필요
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL7 — tau_scale 5-12% 실측 토크 보정 (★★★ HUGE LEAP)

**날짜**: 2026-06-07 KST 05:00경 (GOAL7 autonomous loop)
**Stage**: 28 (Mode A weight + tau_scale)
**Score 변화**: Stage 20 283 → Stage 28 231.6 (18% 개선)

## 발견된 tau_scale 값들

| Source | tau_scale_h | tau_scale_k | 출처 |
|--------|-------------|-------------|------|
| Mode A Stage 28 | 1.053 | 1.124 | tau_scale only |
| Mode A Stage 29 | 1.192 + 0.0037·|tau|/10 | 1.162 + (-0.0116)·|tau|/10 | tau-mag dependency 시도 |
| Mode A Stage 31 | 1.127 | 1.163 | super-narrow refine |
| Mode A Stage 34 (best) | 1.137 | 1.182 | ultra-narrow ±2% |

## Why

- **Why**: 실 robot 측정 토크가 실 motor 출력보다 5-19% underread. Sensor calibration error 또는 motor delay amplitude 감소. 
- **검증**: Stage 29에서 tau magnitude dependency 거의 없음 (slope ≈ 0). 상수 scale이 충분.
- **★ 한쪽: KNEE > HIP**: KNEE에서 18% > HIP 13%. KNEE motor 측정 손실이 더 큼

## How to apply

미래 26.06.02 데이터로 MuJoCo digital twin 작업에:
- 실측 토크를 그대로 쓰지 말고 × tau_scale (HIP 1.13, KNEE 1.18) 적용
- 또는 BO로 데이터마다 재학습

## 적용 위치

- `C:\Users\junho\Desktop\jump_opt\goal6\stage28_modeA_q1weight.py` (tau_scale 처음 발견)
- `C:\Users\junho\Desktop\jump_opt\goal6\stage31\` (Mode A super-narrow best)
- `C:\Users\junho\Desktop\jump_opt\goal6\stage34\` (Mode A ultra-narrow best)
- `C:\Users\junho\Desktop\jump_opt\goal6\stage36\` (Mode A 최종 plateau 215.90)

## 추가 발견

- Mode A에 a_hat 적용 시 score 76% 악화 (Stage 27) → 실측 토크 = motor 출력 확인
- Mode B에서 tau_scale 효과 작음 (Stage 30 0.1% 개선) → Mode B의 a_hat이 이미 cmd→출력 변환

[[goal7-stage20-motor-tm]] [[ak80_9_torque_calibration]]
