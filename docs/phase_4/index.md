# Phase 4 — Jump vs sit2stand trade-off frontier (★ 핵심 분석)

**Status**: ✅ 완료 (2026-07-03)
**채택**: λ=1 joint re-opt → **15,189 (vs Phase 3 15,330, strict improvement)** → **누적 −63.2%**

## 동기

Phases 1–3에서 발견: **점프가 phase마다 under-jump 악화** (h_sim/h_real: P0 80% → P1 64% → P2 54%). Phase 1 mass(무거운 foot) + Phase 2 friction이 sit2stand를 대폭 개선하나 점프 에너지를 뺏음. tau_scale 금지 하 근본 trade-off.

## 방법

점프 vs sit2stand tension에 가장 관여하는 **3 param (M_foot_ex, fv_hip, fc_knee)**을 여러 jump 가중치 λ에서 재최적화:

`minimize  sit2stand_sum + λ · jump_sum` for λ ∈ {1, 2, 4, 8} (CMA-ES 3D).

나머지 param(Phase 1 mass 15p 중 나머지, fv_knee, fc_hip, contact)은 고정.

## Pareto frontier

| λ | sit2stand (7) | jump (24) | total | **h_ratio** | M_foot / fv_hip / fc_knee |
|---|---:|---:|---:|---:|---|
| phase3 default | 2809 | 12520 | 15330 | 0.542 | 0.263 / 0.926 / 0.809 |
| **1.0 (채택)** | 3053 | 12136 | **15189** | **0.563** | 0.227 / 0.787 / 0.524 |
| 2.0 | 3275 | 12018 | 15293 | 0.570 | 0.238 / 0.748 / 0.419 |
| 4.0 | 4475 | 11597 | 16072 | 0.614 | 0.256 / 0.190 / 0.060 |
| 8.0 | 4806 | 11535 | 16340 | 0.619 | 0.304 / 0.038 / 0.016 |

![frontier](../assets/frontier.png)

## ★★★ 3가지 핵심 발견

1. **λ=1 joint re-opt이 순차 phase를 능가**: 15,330 → **15,189** (+jump h 0.542→0.563). 순차 phase(1→2→3)의 greedy 최적화가 3param을 미세하게 suboptimal로 남겼고, 결합 재최적화가 개선. **strict improvement → 채택.**

2. **점프 under-jump의 주범 = friction** (fv_hip, fc_knee): λ↑ 시 fv_hip 0.79→0.038, fc_knee 0.52→0.016로 급감하며 h_ratio 0.56→0.62 회복. mass(M_foot)는 비교적 안정(0.23~0.30). **friction이 점프 에너지 dissipation의 핵심.**

3. **h_ratio가 λ=8(점프 8배 가중)에도 0.62 상한 (plateau)**: friction을 거의 제거해도 점프는 실측의 62%까지만. **~38% 잔여 결손은 friction/mass로 못 메우는 근본 한계** — Mode A는 실측 토크를 replay하는데, tau_scale 금지 상태에서 sim이 이 토크로 실측 높이의 절반만 도달. 원인: (a) 실측 토크 under-measurement (paper a_hat 변환의 한계, tau_scale로만 보정 가능하나 금지), (b) unmodeled energy input (예: 실 로봇의 spring/tendon), (c) 접촉·관절 손실.

## 시사점 (digital twin 결론)

- **sit2stand는 우수하게 재현** (mass+friction fit). **점프는 q/dq 형태는 재현하나 절대 에너지(높이)는 구조적으로 부족.**
- 단일 통합 param set + tau_scale 금지 하에서 이것이 **Pareto 최적 trade-off**. λ=1이 균형점.
- 점프 높이를 실측과 맞추려면 tau_scale(금지) 또는 새 물리(tendon/spring 에너지 저장) 필요 → 향후 실험 방향.

## 채택 모델 (Phase 4, unified best)

```
mass 15p (Phase 1) with M_foot_ex: 0.263 -> 0.227
friction: fv_hip=0.787, fv_knee=0.127, fc_hip=0.095, fc_knee=0.524
contact: solref_tc=0.00217, imp0=0.371
```
→ `phase4_adopted_model.json`. total=15,189, h_ratio=0.563.

## Files

- Runner: `code/goal19/phase4/run_phase4_frontier.py`
- Frontier: `phase4_frontier.json`, plot `frontier.png`
- Adopted model: `phase4_adopted_model.json`
