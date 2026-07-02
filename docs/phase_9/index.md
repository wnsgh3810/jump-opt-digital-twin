# Phase 9 — Stribeck friction (trade-off 돌파 시도 → DROP)

**Status**: ✅ 완료 (2026-07-03, 자율)
**결과**: **+0.54% → DROP**. 속도-의존 마찰도 trade-off를 못 깸 → torque ceiling이 지배함을 최종 확인.

## 가설

Phase 4 frontier: 마찰을 *균일하게* 줄이면 점프는 회복되나 sit2stand가 악화 (같은 fv가 양쪽 지배). **Stribeck** = 저속 고마찰(static excess) + 고속 저마찰. sit2stand 안정성을 저속 static으로 공급하면서 **viscous(fv_hip)를 낮추면** → 저속 안정 + 고속 drag 감소 → trade-off 돌파 가능?

## 구현

`F(v) = [Fc + (Fs−Fc)exp(−(|v|/vs)²)]sign(v) + Fv·v`. XML의 Fc+Fv 위에 Stribeck 초과분 `ds·exp(−(|v|/vs)²)·sign(v)`을 `mjcb_passive` 콜백으로 추가 ([external sources](external_sources.md): MuJoCo native 미지원). ★ 콜백은 model 생성 **후** 설정 (전에 걸면 컴파일 에러). 4D CMA-ES: fv_hip, ds_hip, ds_knee, vs.

## 결과

| | value |
|---|---|
| best score | 15,099.65 |
| baseline (uniform friction) | 15,182 |
| **Δ** | **+0.54% → DROP** |
| fv_hip | 0.835 (원래 0.787, 거의 불변) |
| ds_hip | 0.007 (무의미) |
| ds_knee | 0.709 |
| vs | 0.045 rad/s |

## ★★★ 결론 — torque ceiling이 지배

- **fv_hip이 거의 안 낮아짐** (0.787→0.835): viscous를 낮추면 sit2stand 손실 > Stribeck static 보상 → optimizer가 안 낮춤. **trade-off는 Stribeck으로도 안 깨짐.**
- 순 개선 +0.54% (< 3% threshold) → DROP.
- **점프 under-jump의 진짜 병목은 마찰 구조가 아니라 측정 토크 결손** ([Phase 5](phase_5/index.md): tau_scale ~1.6 필요). 어떤 마찰 모델도 이 ceiling(h≈0.62)을 못 넘음.

**최종 확인**: GOAL19 통합 모델(21 params, 15,182)은 주어진 제약 하 진짜 구조적 최적. Coulomb-Viscous 균일 마찰이 velocity-dependent Stribeck과 동등 (후자 이점 없음). 남은 잔차는 측정·통합모델의 근본 한계.

## Files

- Runner: `code/goal19/phase9/run_phase9_stribeck.py`
- Result: `phase9_best.json`
- External sources: [external_sources.md](external_sources.md)
