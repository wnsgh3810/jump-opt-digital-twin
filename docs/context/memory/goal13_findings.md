---
name: goal13_findings
description: GOAL13 — Iter38(176.41) 위 8개 orthogonal 축 전부 DROP (0 KEEP). Iter38은 absolute local min. 잔차=미모델 물리
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL13 (2026-06-18, ~12h, ~6h 조기종료): GOAL12 **Iter38(176.41) 고정 baseline** 위에서 fresh **orthogonal** 물리축을 base-up으로 테스트 + "boundary distance >20%" guardrail + method-diversity 강제. Iter38이 진짜 local minimum인지 판정.

**결과: 8 iter 전부 DROP, ZERO KEEP** (threshold 171.11). Iter38은 **절대 local minimum / 강한 attractor**:
- Iter1 CAD r/I scale → 176.49 DROP, **α≈1.0**(CAD inertia 이미 정확)
- Iter2 Stribeck → 186.05 DROP_BOUNDARY(fs_excess→0)
- Iter3 NN actuator residual(JAX MLP 32×32) → DROP_OVERFIT, **val/train=15.13**(0424 train 0.115 / 0602 val 1.737, cross-dataset 실패)
- Iter4 joint flex K+D → 7,657 DROP_AXIS(K=0 optimal)
- Iter5 joint stiction → 177.46 DROP_BOUNDARY(dfc→0)
- Iter6 knee range limit → 31,357 DROP_INCOMPATIBLE(settle q2=2.548rad > 어떤 limit보다 큼)
- Iter7 transmission torsion → 9,857 DROP_RIGID(AK80-9 9:1 사실상 rigid)
- Iter8 DC gain apply-side → 176.41 DROP_UNITY(Powell→g=1.0000, Kt 보정 이미 정확)

**핵심 결론**: 잔차 오차 = **미모델 물리**(per-trial 지면 컴플라이언스, 열적 Kt drift, backlash)이지 calibration 아님. 탈출하려면 (a) 새 실험데이터 or (b) differentiable-sim 모델 교체. 매 iter optimizer 교체(CMA-ES/JAX/NM/DE/Sobol/Powell). 같은 15-trial score scale(7,657 등은 축-붕괴, scale 변화 아님). 커밋 prep `a1935ca8`.

**Why:** Iter38이 현 물리모델의 한계점임을 8축으로 증명 — 추가 calibration은 무의미.
**How to apply:** 같은 모델 안에서 더 짜내지 말 것. 다음 개선은 실측 데이터/새 DOF/diff-sim. val/train<1.5 overfit gate, boundary>20% guardrail 유지. [[goal12_findings]] [[goal14_findings]] [[goal16_findings]]
