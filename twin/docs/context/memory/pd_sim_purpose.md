---
name: PD Sim 본질적 목적 (CRITICAL — 잊지 말 것)
description: pd_sim의 목표는 p_des/v_des 입력 시 실제 로봇과 동일한 응답을 내는 시뮬레이터. 모든 sweep·식별·검증의 기준점.
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# 핵심 목적 (사용자 명시, 26.04.27)

> **"pd_sim의 목적은 p_des, v_des를 줬을 때 실제 로봇이랑 똑같이 움직이는 시뮬레이터를 만드는 게 목표"**

# 무엇을 의미하나

**입력**: 실제 모터에 보내는 명령 (= 실험 데이터의 desiredAngle, desiredAngleVelocity)
**출력**: 실제 모터/링크가 보일 응답 (q, dq, tau, GRF)
**판정**: 같은 입력 시 sim 출력이 real 데이터(currentAngle, currentAngleVelocity, currentTorque, GRF.Current_GRF)와 *모든 시점에서* 일치

# Why (왜 이 목적이 모든 결정의 기준)

- 우리 robot 연구 전반의 *디지털 트윈*. 안 맞으면 control 설계, MPC 튜닝, RL 학습, 점프 최적화 모두 무의미
- 단순히 "어떤 sim이 잘 fit하는지"가 아니라 "**진짜 물리값에 수렴하는 sim**"이 목적 — 따라서 fudge factor에 의존하면 가짜
- v6 sweep의 boundary hugging 6개가 *진짜 비물리*임을 사용자가 명확히 인식. 그래서 motor model 도입(v7)으로 이 fudge들을 풀어내려 함

# How to apply (모든 작업에 적용 기준)

1. **Sweep score 설계 시**: 단순히 RMSE 합 최소화가 아니라, 결과 파라미터가 *물리적으로 합리적인 범위*에 있는지가 더 중요. boundary hugging은 model error 신호.
2. **모델 선택 시**: 더 정확한 motor model(a_hat)이 있으면 *반드시* 채택. 우리 sweep이 이를 흉내내려 fudge로 빠지면 가짜 답.
3. **검증 시**: 학습 trial뿐 아니라 holdout trials에서도 잘 맞아야 함 (다양한 gain 영역에서 일반화). 단일 trial overfit은 실패.
4. **파라미터 해석 시**: gAv ≈ 1.36 (CAD 일치), alpha ≈ 1.0 (full GRF transmission), sp ≈ 1.0 (모터 PD 이상적), Is1/Is2 ≈ CAD 측정값 — 이런 게 진짜 sim. v6 best는 이게 아님.
5. **새 dim 추가/제거 결정 시**: "이 항이 *실제 로봇에 존재하는 물리*인가?"가 기준. 단순 fit improvement는 함정.

# v6 결과로 본 *현재 상태*

- v6 best: 학습 영역(Kp=150)에서 q1e 0.4° (완벽 fit), but Kp=60에서 q1e 7.6° (완전 실패) — *일반화 실패*
- 6개 boundary hugging — *비물리값*
- **사용자 결론**: motor model을 a_hat으로 명시적 도입한 v7에서 이 두 가지가 동시에 풀려야 진정한 의미의 pd_sim 달성

# 다음 단계 시 항상 점검

- 새 sweep 결과가 나올 때마다:
  - sp ≈ 1.0인지? (motor PD 이상적)
  - alpha ≈ 1.0인지? (GRF 전달 효율)
  - gAv ≈ 1.36 인지? (CAD)
  - boundary hugging 풀렸는지?
  - holdout 8 trial에서 일반화 잘 되는지?
- 답이 No이면 — 또 다른 model error가 있다는 신호. 무엇이 누락되어 있는지 진단 필요.
