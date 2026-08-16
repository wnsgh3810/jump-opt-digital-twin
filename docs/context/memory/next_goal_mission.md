---
name: next-goal-mission
description: 다음 goal mission statement + 사용자 정정 핵심. 2026-06-05 master insights 정리 후 사용자 명시한 진짜 진짜 goal. 새 세션 시작 시 첫 read.
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 다음 Goal Mission (2026-06-05 사용자 정정)

## 한 줄 Mission

> **NLP가 만든 q*(t), dq*(t)만으로 제어할 때 실측 τ, GRF가 NLP가 예측한 τ*, GRF*와 동일하게 나오는 generalized 동역학 모델.**

## 사용자 명시 (인용)

> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게 나오도록 하는게 우리의 최종 목표!"
>
> "그래도 local minima에 빠진 해라면 그건 안되고 최적화가 수렴할 수 있는 모델, 파라미터를 찾는게 우리의 최종 목표"
>
> "수직 점프만 최적화할 건 아니니까 점프에 특화된 모델, 파라미터로 정하면 안되는거고 **현실에 최대한 근접하도록 찾아야 하는 거**"

## 3가지 의미

1. **Forward consistency** — q*, dq* → 실 robot → 실측 τ/GRF ≈ NLP τ*/GRF*
2. **NLP convergence** — 식이 smooth, well-conditioned, IPOPT 수렴 가능
3. **Generalization** — jump + sit2stand + 다른 task 모두에서 동작

## ❌ 절대 사용 금지 metric

- **점프 높이 매칭** — "0.94m" 같은 숫자는 잘못된 결과
  - 사용자 명시: "실측 토크가 최적화보다 과하게 나왔잖아. 같은 sat에 걸렸으면 그렇게 점프 못 했을 거니까"
  - GOAL1 v41이 jump h 0.945m vs 실 0.94m을 자랑한 게 잘못
- **Inverse RMSE 단독 최저화** — V12 0.93/0.71 같은 숫자는 forward consistency 보장 X
- **점프 특화 fit** — 다른 task 동작 안 함

## ✅ 사용할 metric

- **Forward sim drift** (실측 τ, GRF → forward integrate → 실측 q와 일치)
- **NLP self-consistency** (현재 V12 5.9/6.3 Nm → 목표 < 1 Nm)
- **Hold-out cross-val inverse RMSE** (학습 외 trial에서)
- **Physical 합리성** (cf < 0.8, off < ±0.5, boundary < 15%)

## Time Budget (사용자 명시 2026-06-05)

> "다음날 한국시간으로 오후 12시까지 작업"

- 다음 세션 시작 시점 기준: 다음날 12:00 KST가 deadline
- 작성 시점 (2026-06-05 22:57 KST) 기준: 13시간
- 시간 끝나면 멈추지 말고: 웹 search / 논문 / GitHub 코드 / 추가 적용 / md 정리 자율 진행

## Notion 워크플로우 (사용자 명시)

- **Parent 페이지 1개** (goal 시작 시): mission + plan + timeline
- **Version별 자식 페이지** (각 version 끝):
  1. 이 버전 무엇 (intro)
  2. 이전 버전 대비 알아낸 점
  3. 추가/달라진 항 (코드 + 식)
  4. 새 용어 설명
  5. 이유 (왜)
  6. 결과 그래프
  7. 다양한 이미지
  8. 추가 정보 (논문/웹 reference)
  9. 다음 version 계획
- 사용자가 timeline 보고 판단 가능하게
- 이해하기 쉽게 (비유 + 용어 + 그림 설명)

## 다음 작업

`C:\Users\junho\Desktop\jump_opt\NEXT_GOAL_PROMPT.md` 참조.

요약: jump_opt baseline 식 + V1~V12 발견 중 명백 정당 7-10개 distill + forward drift metric + hold-out validation. ~24-28 params, V1~V8 + 자율 진화.

## 관련 메모리

- [[master-insights-pointer]] — 모든 발견 통합 문서
- [[goal2_final_stack]] — V10/V12 한계
- [[ak80_9_torque_calibration]] — motor 5-param
- [[digital_twin_priority]] — 매칭 우선순위

## 시작 시 user 합의 6가지

1. Mass 표기 (합성 vs raw)
2. Friction 깊이 (viscous + Coulomb + Stribeck vs subset)
3. State-dep bias 자유도 (6p vs 2p)
4. Cross-coupling 포함? (hx1, hx2만 vs 전혀)
5. Initial fit metric (drift only vs hybrid)
6. CAD bound ±% (±10% strict vs ±20% safe vs ±30%)

권장: 합성 / Stribeck 포함 / 6p / hx1+hx2 / drift only / ±20% safe → ~29 params
