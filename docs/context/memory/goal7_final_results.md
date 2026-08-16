---
name: goal7-final-results
description: GOAL7 종합 결과 — Mode A 207.38 / Mode B 371.70 / 70.6% 개선 / 모든 plateau 확정
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL7 Final Results (2026-06-07 KST 07:00)

## 🏆 최종 라이브 베스트

| Mode | Stage | Score | Total 개선 | Plateau |
|------|-------|-------|------------|---------|
| **Mode A** | **44** | **207.38** | ★★★ 70.6% | 209-211 confirmed (4 weightings) |
| Mode B | 39 | 371.70 | 75% | 374.5 ± 2.6 (3 seeds) |

## 검증된 발견 (실 robot 측정 가능)

1. **Motor LPF 8-10ms** — AK80-9 paper torque rise time 일치
2. **★ tau_scale 5-19%** — 실측 토크 underread. KNEE > HIP
3. **★ KNEE motor 1.6x faster than HIP** (motor_tm 1.18ms vs 1.92ms)
4. **KNEE a1=1.11 ≈ paper 1.156** (96% 일치)
5. **HIP Coulomb 2x KNEE** (gear friction 비대칭)
6. **foot 2-point heel/toe** (±0.5cm) 효과
7. **cone="elliptic" > pyramidal** for 점프 contact
8. **a_hat 효과 5%만** (LPF + scale로도 비슷)
9. **Mode A vs Mode B 비대칭** — Mode A: LPF only. Mode B: a_hat + LPF 필수
10. **Mode A/B body 본질 다름** — 서로 다른 best body 추정

## NEGATIVE 발견들

- Stage 27: Mode A + a_hat 부적합 (실측 = motor 출력 확인)
- Stage 30: Mode B + tau_scale 효과 작음 (a_hat이 변환 내장)
- Stage 35: L_motor 수식 unstable
- Stage 37: Mode B + Mode A body forcing 안 됨
- Stage 42: Mode B q2-strong 효과 작음 (Mode A에선 효과적)
- Stage 46: Mode B + extended foot 32% 악화 (Mode A는 효과적)

## External Research Applied

- SAASBO BO + digital twin (arxiv 2512.03772, 2025.12)
- Dual digital twin Webots+MuJoCo (MDPI 2026)
- UPN BO 25 iterations literature 패턴

## Stage 진화 timeline (Stage 11-46)

```
Mode A: S14 706 → S20 283 → S28 231.6 → S40 209.97 → S44 207.38 (70.6% 개선)
Mode B: S9 1476 → S16 1370 → S22 506 → S26 380 → S39 371.70 (75% 개선)
```

## Best XML 파일 위치

- Mode A best: `C:\Users\junho\CVT\jump_opt\goal6\stage44\urdf\leg_g6s40_best.xml`
- Mode B best: `C:\Users\junho\CVT\jump_opt\goal6\stage26\urdf\leg_g6s26_best.xml`

## Visualization

- `goal6/final_viz/mode_a_position.png`, `mode_a_grf.png`, `mode_a_evolution.png`

[[goal7-stage20-motor-tm]] [[goal7-tau-scale]] [[ak80_9_torque_calibration]]
