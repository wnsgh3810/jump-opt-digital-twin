---
name: feedback-pure-paper-formula
description: a_hat 모델은 항상 Pure Paper 식(sgn(v) only) 사용. GitHub s(v) smoothing 금지. 파라미터를 현실값으로 수렴시키는 게 목표.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

**규칙**: a_hat 모터 토크 모델은 항상 **Pure Paper (Nesler) 공식** 사용. GitHub(UMich)의 s(v) smoothing은 절대 쓰지 않는다.

**Pure Paper 공식**:
```
τ_motor = a_0 + a_1·GR·Kt·Iq - a_2·GR·|Iq|·Iq - a_3·sgn(v) - a_4·|Iq|·sgn(v)
Iq = (CF / (GR·Kt)) · iTM_cmd
```

GitHub와의 차이는 친마찰 항만:
- **Pure Paper**: `-a_3·sgn(v) - a_4·|Iq|·sgn(v)` (sgn(v) only) ✅
- GitHub: `-a_3·sgn(v)·s(v) - a_4·|Iq|·sgn(v)·s(v)` where s(v)=|v|/(0.1+|v|) ❌

**Why**: GitHub의 s(v) smoothing은 v≈0에서 friction 기여를 0으로 만들어 (CF, a_1) 식별 degeneracy를 야기한다. Pure Paper sgn(v)는 v≈0에서도 friction 살아있어 CF 식별 가능 (2026-05-24 26.05.20 데이터에서 Option A에서 CF=0.996 INTERIOR로 수렴 vs GitHub form에서는 CF=3.0 bound hit).

**목표**: 이 식 위에서 파라미터를 **현실적이고 오차(RMSE) 적은** 값으로 수렴시킨다. 예: 정적 데이터 fit에서 CF≈1.0, a_1≈1.5, a_2≈1.2e-3, a_3=0.37, a_4=0.088이 나오면 Paper 인용값과 비슷해서 합리적.

**How to apply**:
- 모든 새 refit/sweep/optimization 스크립트는 sgn(v) 사용
- 기존 코드에 `sgn(v)·s(v)` 있으면 사용자가 명시적으로 GitHub 원하지 않는 한 sgn(v)로 교체
- 시뮬 baking 시에도 Pure Paper 공식으로 통일
- Friction 항이 v=0 근처에서 discontinuous인 건 numerical 문제 아니라 의도된 동작

관련: [[ak80_9_torque_calibration]], [[pd_sim_purpose]]
