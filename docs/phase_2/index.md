# Phase 2 — Joint friction (viscous + Coulomb)

**Status**: ✅ 완료 (2026-07-03)
**Phase 1 baseline**: 20,367.75 → **Phase 2 best: 15,744.40 (−22.7%)** → **누적 −61.9%** (vs Phase 0 41,271)

## Axis & method

4D CMA-ES (pop=10, 190 eval) on top of fixed Phase 1 mass model:

| Param | MuJoCo | best | drop-test |
|---|---|---:|---|
| `fv_hip` | joint `damping` | **0.926** | +13.95% ★ KEEP |
| `fv_knee` | joint `damping` | 0.127 | +2.43% DROP |
| `fc_hip` | joint `frictionloss` | 0.095 | +0.19% DROP |
| `fc_knee` | joint `frictionloss` | **0.809** | +10.86% ★ KEEP |

**물리 story**: hip = **점성(viscous) 지배** (bearing drag), knee = **쿨롱(Coulomb) 지배** (CVT+seal static friction). 각 관절이 서로 다른 마찰 유형이 지배적 — 물리적으로 타당. ([external sources](external_sources.md): MuJoCo damping=viscous, frictionloss=Coulomb.)

## Per-exp Phase 1 → Phase 2

| 그룹 | 변화 | 비고 |
|---|---|---|
| sit2stand (7) | **+50% ~ +71%** | 전부 대폭 개선. sit2stand_gnd 4097→1312 (발산 안정화) |
| jump_0424 high-PD (120_2, 150_2.2_*) | **+7% ~ +18%** | 고토크 점프 개선 |
| jump_torque_0422 P40 | +46% | |
| **jump_position_0421 저-gain (P70/P90/P100)** | **−124% ~ −156%** ⚠️ | 심한 regression |
| jump_0424/0602 저-gain | −11% ~ −22% | regression |

## ⚠️ 핵심 발견 — 새 tension (Phase 3 동기)

**hip 점성마찰(0.93)이 sit2stand(느림)엔 완벽하나 저-gain position-PD 점프(빠름)를 과도 감쇠** → P70/P90/P100 급격 악화. 반면 high-PD 점프는 개선. Net은 sit2stand 지배로 +22.7%.

→ **Phase 3 = Stribeck friction** 강력 후보: 저속에서 고마찰(sit2stand 유지) + 고속에서 저마찰(저-gain 점프 회복). 단일 C-V 모델의 속도-무관 한계를 정확히 해결.

## sit2stand_gnd 발산 — 부분 해결

Phase 1에서 q1 sim→−14 발산하던 것이 Phase 2 friction으로 **q1 sim ~0.5 안정화, dq 1초 후 0 정착** (plot 참조). 그러나 q-tracking은 여전히 부정확 (real은 느린 squat, sim은 정적 hold). Mode A 토크 replay가 이 GND trial의 squat을 재현 못 함 — 근본적 데이터/모델 한계. q_offset/sensor 재검토(후반) 또는 contact(Phase 5)에서 재확인.

## 채택

Phase 2 stack = full 4D friction (fv_hip=0.926, fv_knee=0.127, fc_hip=0.095, fc_knee=0.809). drop-test상 fv_hip+fc_knee가 핵심이나, 4D 전체가 최적(15,744)이고 물리적으로 모두 실재하므로 유지.

## Files

- Runner: `code/goal19/phase2/run_phase2_friction.py`
- Best: `phase2_best.json`
- Finalize (drop-test + per-exp + plots): `finalize_phase2.py` → `phase2_final_breakdown.json`
- Plots: `plots/` (sit2stand_gnd 안정화, 저-gain regression, high-PD 개선)
- External sources: [external_sources.md](external_sources.md)
