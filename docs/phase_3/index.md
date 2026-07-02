# Phase 3 — Contact compliance (solref_tc, imp0)

**Status**: ✅ 완료 (2026-07-03)
**Phase 2 baseline**: 15,744.40 → **Phase 3 best: 15,329.66 (+2.6%)** → **누적 −62.9%**

## Axis & method

잔차 분해(Phase 2)에서 **모든 점프 그룹 dq RMSE 지배(69~87%)** + **h_sim=0.456 << h_real=0.844**. Mode A 실토크 replay인데 sim under-jump → 에너지 부족. tau_scale 금지. → 접촉 compliance가 남은 에너지 lever.

2D CMA-ES (pop=8, 128 eval) on Phase 1 mass + Phase 2 friction:

| Param | best | default | drop-test |
|---|---:|---:|---|
| `solref_tc` | **0.00217** | 0.00632 | +0.87% weak |
| `imp0` | **0.371** | 0.143 | +0.74% weak |

결합 +2.6% (borderline KEEP — 개별 <1%이나 결합 유의, 물리적 실재).

## 발견

**CMA-ES가 solref_tc를 더 stiff(0.00632→0.00217)로 이동** → [external sources](external_sources.md)의 "brief stiff contacts = sharp propulsive impulse" 확인. **softer contact은 push-off 에너지 dissipate → 점프에 해**. 접촉 energy return 가설(softer 유리)은 기각. 대신 stiffer + 높은 imp0(0.371)이 미세하게 유리.

**★ 그러나 contact은 modest lever (2.6%)** — dq/under-jump 잔차의 근본 원인은 접촉이 아님. → **점프 under-jump는 통합 mass/friction이 sit2stand 최적화로 점프 에너지를 희생한 결과** (Phase 4에서 정면 분석).

## 채택

Phase 3 stack = Phase 1 mass + Phase 2 friction + contact(solref_tc=0.00217, imp0=0.371).

## Files

- Runner: `code/goal19/phase3/run_phase3_contact.py`
- Best: `phase3_best.json`
- External sources: [external_sources.md](external_sources.md)
