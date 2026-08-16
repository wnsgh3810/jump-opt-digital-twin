---
name: digital-twin-priority-q-dq-tau-grf-matching-above-lift-off-timing
description: "매칭 우선순위 — 위치/속도/토크/지반력은 핵심, lift-off 시점은 부수적. 최적화가 실 결과 반영 목적."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 사용자 선언 (2026-05-18)

> "lift-off 시점은 별로 안중요하다고 생각해 나는 위치, 속도, 토크, 지반력이 잘 맞는게 가장 중요하다고 생각해 그렇게 디지털 트윈이 잘 이루어져서 최적화도 실제 결과를 잘 반영하는 최적화를 만드는게 목표"

## 핵심

**디지털 트윈 매칭 우선순위**:
1. **q (위치)** — 핵심
2. **dq (속도)** — 핵심
3. **tau (토크)** — 핵심
4. **GRF (지반력)** — 핵심
5. **ste (lift-off 시점)** — **부수적, 낮은 비중**

**Why**: 디지털 트윈의 목적은 sim 기반 최적화가 실 로봇에서도 잘 작동하게 하는 것. 컨트롤러는 매 timestep의 q/dq/tau/GRF 예측 정확도에 의존. lift-off 시점은 점프 사이클의 한 순간이라 가중치 낮아도 됨.

**How to apply**:
- score 함수 설계 시 ste weight를 낮게 유지 (현재 0.2도 검토 필요, 0.1 또는 0.05로 낮춰도 됨)
- q/dq/tau/GRF 매칭이 안 좋으면 ste 좋아도 의미 없음
- BO/sweep best 평가 시 ste보다 다른 4개 컴포넌트 정밀도 우선 확인
- 최종 결과 검증 plot에서도 lift-off보다 q/dq/tau/GRF 시간경로 매칭에 집중

관련: [[pd_sim_purpose]]
