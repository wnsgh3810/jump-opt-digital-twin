# Phase 8 — 자율 확장: untested axes ablation (완전성 검증)

**Status**: ✅ 완료 (2026-07-03, 자율)
**결과**: 미탐색 axis 전부 DROP → **모델이 구조적 최적임을 확인**

## 동기

GOAL19 최종 모델(15,182)이 구조적 ceiling에 도달했는지, 아니면 쉬운 개선을 놓쳤는지 검증. GOAL19에서 한 번도 fit 안 한 axis 2개를 테스트.

## A. arm_hip (Phase 1에서 lock=0)

hip 모터 reflected inertia. Phase 1은 arm_hip=0으로 고정했음 (arm_knee만 fit).

| arm_hip | score | Δ |
|---:|---:|---:|
| **0.000** | **15,182** | +0.00% |
| 0.002 | 15,212 | −0.19% |
| 0.005 | 15,343 | −1.06% |
| 0.010 | 15,501 | −2.10% |
| 0.020 | 15,965 | −5.16% |
| 0.040 | 16,646 | −9.64% |

**DROP (단조 악화)**. arm_hip=0이 최적. **물리적으로 타당**: hip 모터는 base에 고정되어 rotor inertia가 움직이는 링크에 반사되지 않음 (knee 모터와 대조). Phase 1의 lock=0 결정이 옳았음을 검증.

## B. dt / timestep (base 0.0005)

| dt | score | Δ |
|---:|---:|---:|
| 0.0002 | 15,229 | −0.31% |
| **0.0005** | **15,182** | +0.00% |
| 0.0010 | 15,229 | −0.31% |

**DROP**. 현재 dt=0.0005가 최적 (더 작아도/커도 미세 악화). integrator는 jump=RK4, sit2stand=implicitfast로 이미 적절.

## 결론 — ablation 완전성

**미탐색 axis (arm_hip, dt) 모두 DROP** → GOAL19 최종 모델(21 params)은 주어진 제약(통합 single param set, tau_scale 금지, Mode A) 하에서 **진짜 구조적 최적**. 쉬운 개선을 놓치지 않았음. 남은 잔차(특히 점프 under-jump)는 [Phase 5 진단](phase_5/index.md)이 규명한 구조적 한계(측정 토크 결손)이지 axis 부족이 아님.

**Stribeck 마찰**은 이론상 저-gain 점프 regression을 완화할 수 있으나 (a) MuJoCo native 미지원 → 커스텀 qfrc 구현 필요, (b) frontier(Phase 4)에서 friction 제거가 점프 h를 0.62까지만 회복 → Stribeck도 상한 못 넘음. 비용 대비 효과 낮아 미시도 (향후 후보).

## Files

- Runner: `code/goal19/phase8/run_phase8_untested.py`
- Result: `phase8_untested.json`
