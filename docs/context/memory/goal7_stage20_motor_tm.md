---
name: goal7-stage20-motor-tm
description: GOAL7 Stage 20 BO 발견 motor LPF tm=8.37ms — 이전 33ms 가설 업데이트
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL7 Stage 20 — Motor LPF tm 8.37ms 발견 (★★★ HUGE LEAP)

**날짜**: 2026-06-07 KST 05:00경 (GOAL7 autonomous loop)
**Stage**: 20 (Mode A refine 4 + motor LPF + tau delay + foot extra)
**Score 개선**: 435 (Stage 19) → 283 (35% 개선)

## 발견된 motor 파라미터 (BO 400 trials)

| Param | BO best | 이전 가설 | 비교 |
|-------|---------|----------|------|
| motor_tm (motor LPF) | **8.37ms** | 33ms (goal6_findings.md) | ★ 4배 짧음 |
| tau_delay | 1.44ms | ~5ms (CAN typical) | 더 빠름 |
| m_foot_extra | 10.5g | 0 | 작음 |

**Why**: Stage 20 BO는 q/dq/τ/GRF 동시 매칭. motor_tm은 8.37ms로 수렴 (lower 1ms upper 50ms 중). GRF RMSE 12.1 → 6.8 (44% 개선)의 주요 동력.

**How to apply**: 미래 MuJoCo digital twin 작업에 motor_tm baseline 8.37ms 사용. 또는 새 데이터마다 BO로 재발견.

## 이전 33ms 가설과의 차이

- goal6_findings.md: "motor LPF 33ms" — 다른 setup (Stage 1 sat=±18 가설 검증, Stage 9 PD-driven 등)에서 추정
- Stage 20: V20 lumped + Mode A (real tau ctrl) + 6 trials joint BO. 더 정밀
- 8.37ms가 AK80-9 paper의 torque rise time ~10ms와 일치 → 신뢰 가능

## 적용 위치

- `C:\Users\junho\Desktop\jump_opt\goal6\stage20_modeA_motor_lpf.py`
- `C:\Users\junho\Desktop\jump_opt\goal6\stage20\stage20_study.pkl`
- `C:\Users\junho\Desktop\jump_opt\goal6\stage20\urdf\leg_g6s20_best.xml`

[[goal6-findings]]
