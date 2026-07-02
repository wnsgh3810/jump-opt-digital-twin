# Phase 1 — 로봇 동역학 (mass + inertia + CoM per part)

!!! warning "진행 중"
    각 부품(thigh, calf, motor_p, motor_c, foot, base)의 mass + inertia + CoM 거리가 CAD와 다르다고 가정 → NM/CMA-ES 동시 fit.

## 🎯 Axis (예상 7-10D)

| Axis | Range | Warm start |
|---|---|---|
| `m_thigh_scale` | [0.75, 1.25] | 1.0 |
| `m_calf_scale` | [0.75, 1.25] | 1.0 |
| `M_p_scale` (thigh motor) | [0.75, 1.25] | 1.0 |
| `M_c_scale` (calf motor) | [0.75, 1.25] | 1.0 |
| `M_foot_extra` | [0.0, 1.0] | 0.018 |
| `I_thigh_scale` | [0.75, 1.25] | 1.0 |
| `I_calf_scale` | [0.75, 1.25] | 1.0 |
| (선택) CoM offsets | ±10mm | 0 |

## 🔬 물리 근거

- **CAD-실제 편차**: 조립 tolerance, 재료 밀도 편차, 부품 modification (전선, 나사 등)
- **Featherstone 2008**: "not always practically feasible to model in CAD all components"
- **실측 사례**: CAD vs measured up to 4.2% 편차 documented (Fraunhofer publica)

## 🛠️ 방법

- Optuna CMA-ES 100 trials + Nelder-Mead refine 50 iter
- Warm start = CAD값 (모두 1.0)
- Drop-test: axis 뺐을 때 score 변화 < 3% → drop

## 📚 외부 출처

*(WebSearch 진행 중 3+ 확보 예정)*

## 📈 결과

*(자율 loop 진행 중 업데이트)*
