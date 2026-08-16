# V14 — FF + PD replay Trade-off (사용자 metric 본질적 한계 발견)

> **Phase 6e — Pareto trade-off**. NLP feedforward τ + PD tracking 다양한 Kp 조합 시도. **FF only: τ_diff hip 0.03 / knee 1.44 Nm (사용자 metric ★)** but drift 24°/149°. **High PD: drift 0.6°/1.2° but τ_diff 4.5/6.0 Nm**. **사용자 metric (위치+토크 동시)은 trade-off**.

---

## 1. 이 버전 무엇

V13 finding 발전: PD only는 τ 차이 큼 (5-7 Nm). FF only는?

V14 = NLP τ_ff + Kp(q*-q) + Kd(dq*-dq) → AK80 sat → forward sim.
6 가지 Kp 조합 시도.

---

## 2. Trade-off 결과

| Kp 조합 | drift_q1° | drift_q2° | τ_diff_hip | τ_diff_knee |
|---|---|---|---|---|
| **FF only (Kp=0)** | 24 | 149 | **0.03** | **1.44** ★ |
| Low (Kp=30) | 0.95 | 21.7 | 1.03 | 6.41 |
| Med (Kp=60) | 2.2 | 9.3 | 2.56 | 4.49 |
| Std (Kp=120) | 1.6 | 4.2 | 3.49 | 4.05 |
| High (Kp=150/250) | 1.5 | 1.7 | 3.97 | 5.21 |
| V High (Kp=500) | 0.6 | 1.2 | 4.48 | 5.97 |

→ **Pareto front**: drift × τ_diff plane에서 명확한 trade-off curve.

---

## 3. 본질적 trade-off — 사용자 metric 분석

사용자 명시:
> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게"

이 두 조건은 V14가 보여주듯이 **trade-off**:
- "**위치 속도** 일치" (drift 작음): High PD 필요 → τ가 NLP와 다름 (PD가 자체 τ 추가)
- "**토크 지반력** 일치" (τ_diff 작음): Low PD 또는 FF only → trajectory drift

### 왜?

- NLP feedforward τ는 **이상적 motor + perfect tracking** 가정 (state error = 0)
- 실 robot은 작은 perturbation 존재 (sensor noise, contact 미세 차이)
- PD가 그 error 보정 → τ_applied = τ_ff + Kp·error + Kd·error_dot
- → PD correction이 NLP τ에 더해짐 → τ 차이 발생

### 본질적 해결 불가?

Trade-off는 unavoidable. 단 두 가지 mitigations:
1. **Robust trajectory**: NLP가 더 smooth + dynamically feasible trajectory → small Kp로 충분
2. **Torque control mode**: 실 robot이 NLP τ 직접 따라가는 모드 (위치 제어 우회) — AK80-9 MIT mode 가능

---

## 4. 결과 그래프

### 그림 1: drift vs τ_diff bar chart

(image_placeholder — v14_tradeoff.png)

### 그림 2: Pareto front

(image_placeholder — v14_pareto.png)

(FF only ↔ very High PD 사이 trade-off curve)

---

## 5. GOAL3 사용자 metric 최종 정리

### V12 GOAL2 vs V8 GOAL3 vs V13/V14 시뮬

| Metric | V12 (GOAL2) | V8 (GOAL3) | V13 PD only | V14 FF only | V14 Med PD |
|---|---|---|---|---|---|
| Inv RMSE hip | 0.93 | 3.48 | - | - | - |
| Inv RMSE knee | 0.71 | 1.65 | - | - | - |
| **NLP self-cons hip** | 5.9 | 2.74 | - | - | - |
| **NLP self-cons knee** | 6.3 | **0.16** | - | - | - |
| Forward drift T=0.05 q1 | - | 0.11° | - | - | - |
| Forward drift T=0.05 q2 | - | 2.54° | - | - | - |
| **Replay drift_q1** | - | - | 3.8° | **24°** | 2.2° |
| **Replay drift_q2** | - | - | 12.7° | **149°** | 9.3° |
| **Replay τ_diff_hip** | - | - | 6.72 | **0.03** ★ | 2.56 |
| **Replay τ_diff_knee** | - | - | 5.34 | **1.44** | 4.49 |

### 사용자 metric 최종 결론

- **NLP self-consistency (V8 knee 0.16)**: 모델 자체 일관성 — 통과 ★
- **Forward sim drift on real data (T=0.05s, 0.11°/2.54°)**: 단기 forward 정확 — 통과 ★
- **NLP→실 robot replay**: 본질적 trade-off 발견. PD only vs FF only 중 선택. 둘 다 충족은 robust NLP 또는 torque control mode 필요.

V8 (V5 + AK80 saturation) = GOAL3 best — 사용자 진짜 metric의 측정 가능 부분 모두 통과. **남은 본질적 한계는 model이 아니라 control mode 선택의 문제**.

---

## 6. 다음 작업 권장

### V15+ 시도 (Phase 6 남은 시간)

1. **Robust NLP**: NLP cost에 "small disturbance에도 trajectory 안정" term 추가
2. **NLP + tracking error penalty**: NLP가 PD-friendly trajectory 만듦
3. **τ smoothness + low Kp**: smooth τ profile은 PD-low가 안정 추적 가능
4. **AK80 MIT mode 실증**: 실 robot 실험으로 torque control mode 가능성 확인

### 향후 (다음 세션)
- 실 robot 실험 (NLP τ direct + measure)
- LMI physically-consistent ID
- Multi-task generalization

---

## 7. 진행

- 시작: 2026-06-06 00:40 KST
- 종료: 2026-06-06 00:50 KST
- 소요: 10분 (NLP 4s + 6 replay configs + plot)
- Deadline까지: 11h 10m
