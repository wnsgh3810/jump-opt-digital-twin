---
name: feedback-plot-colors
description: matplotlib plot 작성 시 색을 명시 지정하지 말고 자동 cycle 색 사용
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Plot 색 지정 금지 — matplotlib auto color 사용

**Rule**: matplotlib plot 작성 시 `'b-'`, `'r-'`, `color='blue'` 등 색을 명시 지정하지 말 것. matplotlib의 자동 color cycle 사용.

**Why**: 사용자가 자연스러운 색 (default tab10 cycle 등)을 선호. 명시 색 지정은 부자연스럽고 contrast 강함. 반복 피드백 (여러 번 지적).

**How to apply**:
- ❌ `ax.plot(t, y, 'b-', lw=2)` — 색 명시
- ❌ `ax.plot(t, y, color='red', linestyle='--')` — 색 명시
- ✅ `ax.plot(t, y, lw=2)` — auto color
- ✅ `ax.plot(t, y, ls='--')` — linestyle만 지정 OK

**Sim vs Real 매칭 패턴** (같은 변수를 sim/real 모두 같은 색):
```python
l1 = ax.plot(t_real, real['q1'], lw=2, label='q1 real')[0]
ax.plot(t_sim, q1_sim, lw=1.5, ls='--', color=l1.get_color(), label='q1 sim')
```
real을 먼저 plot → auto color → sim에 같은 color 적용 (`l1.get_color()`).

색 구분이 필요한 경우에만 `get_color()`로 그룹화. 단순 plot은 그냥 color 지정 없이.

**합침 패널 예외 (2026-07-09, τ-fidelity 실험)**: 한 패널에 여러 변수×(sim/real/des)를 합칠 때
6색 자동 cycle은 "색이 너무 많다"고 지적받음 → **기본 3색만**: `"C0"`=sim, `"C1"`=real,
`"C2--"`=des(점선). 변수(q1/q2)는 값 대역으로 구분. 선 스타일: des만 점선, 나머지 전부 실선
(사용자 07-09 — 기존 sim점선 관례를 이 실험 그래프들에선 전부 실선으로 덮음).
