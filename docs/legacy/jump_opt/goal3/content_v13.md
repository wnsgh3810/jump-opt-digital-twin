# V13 — NLP optimal trajectory replay (사용자 진짜 metric의 진짜 어려움)

> **Phase 6d — Fundamental Finding**. NLP optimal q*, τ*을 3가지 방식으로 forward 재생:
> A) NLP τ_actual을 input (실 robot이 ideal motor torque control)
> B) NLP τ_cmd + saturation (실 robot이 commanded τ + AK80 hardware sat)
> C) PD 제어로 q* tracking (실 robot의 진짜 PD 모드)
>
> **결과: A/B drift 30°+, C drift 4-13°, C의 PD τ vs NLP τ = hip 6.72 / knee 5.34 Nm**

---

## 1. 이 버전 무엇

V13 = V8 final stack을 사용한 NLP→forward replay 시뮬레이션. **사용자 진짜 metric의 진짜 어려움 발견**.

**사용자 진짜 metric (재확인)**:
> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게 나오도록"

V13는 실 robot 실험 simulation surrogate. **NLP self-cons (V8: 0.16 Nm)와 매우 다른 결과**.

---

## 2. 3가지 Replay 방식 결과

### Replay A: NLP τ_actual → V8 forward sim
- Input: 시간별 NLP-reported τ_actual (saturation 적용된)
- Output: V8 forward integrate → q_sim(t)
- 결과: **drift_q1 33.2°, drift_q2 29.8°**

### Replay B: NLP τ_cmd → V8 forward sim with sat
- Input: NLP commanded τ (saturation 적용 전), V8 sim에서 sat 적용
- 결과: **drift_q1 32.6°, drift_q2 28.8°** (A와 거의 같음)

### Replay C: PD 제어로 q* 추적 (실 robot 모방)
- PD law: `τ_cmd = Kp(q* - q) - Kd·dq` (Kp=120, Kd=2)
- AK80 saturation 적용 → actual τ
- V8 dynamics로 forward
- 결과: **drift_q1 3.8°, drift_q2 12.7°** ★ (A/B 대비 훨씬 좋음)

### Replay C: PD τ vs NLP τ (사용자 진짜 metric)
- **Hip: 6.72 Nm**
- **Knee: 5.34 Nm**

→ **NLP self-cons 0.16과 매우 다름**.

---

## 3. 의미 — Fundamental Finding

| Metric | 결과 |
|---|---|
| NLP self-cons (V8 collocation internal) | hip 2.74, **knee 0.16 Nm** |
| Forward sim drift (실측 input, T=0.05s) | 0.11° / 2.54° |
| **NLP τ vs PD-replay τ** | **hip 6.72 / knee 5.34 Nm** |

**왜?**

1. **NLP는 ideal feedforward τ**: state error = 0, perfect tracking 가정
2. **PD는 feedback τ**: q* - q_actual error로 τ 만듦
3. **두 종류의 토크는 본질적으로 다름**:
   - NLP feedforward = 동역학 식에 정확히 맞는 토크
   - PD feedback = tracking error 보정 토크
4. **합치면**: 실 robot은 feedforward + feedback. NLP만 사용 시 ≠ PD만 사용 시.

---

## 4. 사용자 진짜 metric 재정의

원래 사용자 명시:
> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게"

V13가 보여준 reality:
- **위치/속도만으로 PD 제어** → PD τ가 NLP τ와 5-7 Nm 차이
- 이건 model 부정확이 아니라 **제어 방식 (feedforward vs feedback) 본질적 차이**

→ 사용자 metric 충족 위해선 두 가지 옵션:
   - (a) 실 robot을 NLP τ_cmd를 직접 따라가는 **torque control mode**로 운영 (드라이버 모드 변경)
   - (b) NLP에 PD tracking term 포함하여 **feedforward + feedback τ 합산**이 NLP τ와 일치하게 설계

---

## 5. 결과 그래프

### 그림 1: V13 replay 비교 (4-panel)

(image_placeholder — v13_replay_compare.png)

**무엇을 보여주나**: 3가지 방식의 q1, q2 trajectory + PD τ vs NLP τ.

**어디 봐야 하나**:
- 좌상 q1: A, B 큰 발산 / C (PD)는 NLP에 가까움
- 우상 q2: knee 더 큰 차이
- 좌하 Hip τ: PD τ (점선) vs NLP τ (실선) — 6.72 Nm 차이
- 우하 Knee τ: 5.34 Nm 차이

### 그림 2: Drift bar chart

(image_placeholder — v13_drift_compare.png)

A: 33°/30°, B: 33°/29°, C: 4°/13° — PD 제어가 실 robot에 가장 유사.

---

## 6. 결론

### V8 GOAL3 stack의 위치

| Metric | V8 결과 | 의미 |
|---|---|---|
| Inverse RMSE (train) | hip 3.48 / knee 1.65 | model fit 정확 |
| NLP self-cons (collocation) | hip 2.74 / **knee 0.16** | NLP 자체 안 일관성 |
| Forward drift T=0.05 (실측) | q1 0.11° / q2 2.54° | 단기 forward 정확 |
| **PD-replay τ vs NLP τ** | **hip 6.72 / knee 5.34** | **실 robot 시뮬에서 큰 차이** |

→ V8 model의 한계가 아닌, **NLP feedforward vs PD feedback의 본질적 차이**가 사용자 진짜 metric을 어렵게 함.

### 향후 작업

1. **NLP+PD hybrid optimization**: NLP가 PD tracking term까지 고려한 τ trajectory 만듦
2. **Real robot torque control mode**: NLP τ를 직접 input (PD bypass)
3. **추가 study**: V8 + state-dependent PD gain? Adaptive control?

---

## 7. Master Insights update

V13 fundamental finding 추가 (MASTER_INSIGHTS.md §20):
- NLP self-cons ≠ NLP→실 robot replay accuracy
- PD-replay τ vs NLP τ = 5-7 Nm (사용자 진짜 metric의 진짜 차이)
- 해결책: (a) torque control mode (b) NLP+PD hybrid

---

## 8. 진행

- 시작: 2026-06-06 00:25 KST
- 종료: 2026-06-06 00:35 KST
- 소요: 10분 (NLP 4s + 3 replay + plot)
- Deadline까지: 11.5h
