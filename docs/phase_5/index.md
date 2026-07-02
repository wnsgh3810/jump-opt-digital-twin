# Phase 5 — Torque-deficit 진단 (DIAGNOSTIC ONLY, tau_scale 미채택)

**Status**: ✅ 완료 (2026-07-03, 진단)
**목적**: Phase 4 frontier plateau(점프 h 0.62 상한)의 근본 원인 정량화.

> ⚠️ **tau_scale은 모델에 절대 미채택** (사용자 금지). 이 phase는 순수 진단 — 점프 under-jump의 원인을 규명하기 위해서만 가상 tau_scale을 sweep. 채택 모델은 Phase 4(tau_scale=1.0) 그대로.

## 논리

Phase 4 frontier에서 λ=8(friction≈0)에도 점프 h_ratio=0.62 plateau → **sim 에너지 손실이 원인이 아님**. 남은 가능성은 **입력 토크 자체가 실제 점프를 못 만듦**. 이를 확인하려 채택 모델(Phase 4)에 가상 tau_scale을 점프에만 적용하여 h_real 복원에 필요한 scale 측정.

## 결과

| tau_scale (가상) | mean jump h_ratio |
|---:|---:|
| 1.00 (채택 모델) | 0.563 |
| 1.10 | 0.653 |
| 1.20 | 0.730 |
| 1.30 | 0.790 |
| 1.40 | 0.845 |
| 1.50 | 0.892 |
| h_ratio=1.0 필요 | **~1.6 (외삽)** |

## ★★★ 결론 — 점프 under-jump의 근본 원인

점프 실측 높이(0.84m)를 재현하려면 **가상 tau_scale ~1.6**이 필요. 즉 채택 모델의 점프는 실측 대비 **~56% 에너지**. 이 결손은 3요소의 복합:

1. **Mass over-estimate for jumps**: Phase 1이 sit2stand 재현 위해 foot mass(+227g)+paddle mass를 늘림 → 점프엔 과중한 leg → 낮은 점프. (통합 단일 param set의 대가.)
2. **Friction dissipation**: 채택 fv_hip=0.787이 push-off 에너지 소산.
3. **AK80-9 torque under-read**: 실측 currentTorque가 raw iTM이라 고토크에서 under-measure ([[ak80_9_torque_calibration]], GOAL7 tau_scale 5-19%). 점프 peak 토크(~20Nm)에서 더 클 수 있음.

**핵심**: 이 3요소를 tau_scale 하나로 통합 보정하면 ~1.6. 그러나 **tau_scale 금지 + mass/friction은 통합 fit에 고정** → 점프는 구조적으로 56% ceiling. **digital twin은 "측정된 토크가 만드는 것"을 충실히 재현**; 실측 높이와의 gap은 측정·통합모델의 한계이지 sim 버그가 아님.

## 향후 방향 (사용자 결정 필요)

- 점프 절대 높이를 맞추려면: tau_scale 허용(현재 금지) OR tendon/spring 에너지 저장 물리 추가 OR 점프 전용 mass(per-regime, 통합 원칙 위배).
- 현 통합 모델은 **q/dq/GRF 형태 + sit2stand 절대값은 우수, 점프 절대 높이만 구조적 부족**.

## Files

- Runner: `code/goal19/phase5/run_phase5_energy_audit.py`
- Result: `phase5_energy_audit.json`
