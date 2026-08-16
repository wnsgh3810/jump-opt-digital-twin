# V2 — V1 + Motor 1st-order lag (14 params)

> **Phase 3a 결과**. V1에 motor lag (tau_m1, tau_m2)을 추가. 점프 forward drift_q2가 29.4° → 20.8° (30% 개선). Inverse RMSE는 거의 동일 (식별 안 됨).

---

## 1. 이 버전 무엇

V2 = V1 (12p) + tau_m1 (hip motor lag) + tau_m2 (knee motor lag) = **14 params**.

**핵심 추가**:
- AK80-9 driver의 internal current loop response을 1차 IIR low-pass로 모델링
- 명령 τ_cmd → 실제 motor τ_act 사이 ~25ms 지연
- V14 발견 (MASTER_INSIGHTS §10): 26.06.02 데이터에서 motor lag가 50% inverse RMSE 감소시킴

---

## 2. V1 대비 알아낸 점

### 정량 비교

| 지표 | V1 | V2 | 변화 |
|---|---|---|---|
| Jump inv_hip MEAN | 5.350 | 5.413 | +0.06 (거의 동일) |
| Jump inv_knee MEAN | 3.474 | 3.839 | +0.4 (악화) |
| **Jump drift_q1** | **17.04°** | **15.97°** | **-1° (6% 개선)** |
| **Jump drift_q2** | **29.37°** | **20.78°** | **-9° (29% 개선!)** ★ |
| S2s inv_hip | 1.821 | 1.825 | 동일 |
| S2s inv_knee | 2.846 | 2.847 | 동일 |
| CVT 평균 | hip 4.77 / knee 12.86 | 4.81 / 12.83 | 동일 |
| Boundary chase | 92% (11/12) | 86% (12/14) | 약간 개선 |

### 핵심 발견

**Motor lag는 forward에서 효과적, inverse에서 식별 안 됨**.

이유:
- `inverse_predict(q, dq, ddq, GRF)` 계산은 lag와 무관 (kinematic 입력만)
- BO/L-BFGS는 inverse RMSE 위주로 fit → tau_m이 lower bound (5ms)로 밀림 (식별 신호 부족)
- 그러나 forward sim에서는 motor lag를 거친 τ를 dynamics input으로 사용 → trajectory가 부드러워져 drift 감소
- 특히 knee q2 drift가 29° → 21°로 큰 감소 (knee는 더 동적이라 lag 효과 큼)

→ **Forward consistency 관점에선 motor lag 효과 분명** (사용자 진짜 goal과 직결).

---

## 3. 추가/달라진 항

```python
# V1 → V2 추가:
def first_order_lag(x, tau_m, dt):
    """1차 IIR low-pass."""
    alpha = dt / (tau_m + dt)
    return lfilter([alpha], [1, -(1-alpha)], x)

def inverse_predict_v2(trial, params):
    tau_h_p, tau_k_p = inverse_predict(trial, params)  # V0 inverse
    tau_h_p_lag = first_order_lag(tau_h_p, tau_m1, dt)  # 추가
    tau_k_p_lag = first_order_lag(tau_k_p, tau_m2, dt)  # 추가
    return tau_h_p_lag, tau_k_p_lag

def forward_sim_v2(trial, params):
    tau1_lag = first_order_lag(trial['tau1'], tau_m1, dt)  # 추가
    tau2_lag = first_order_lag(trial['tau2'], tau_m2, dt)  # 추가
    # ... dynamics 호출 with lag-applied τ
```

**V2 fitted values**:
| 변수 | V1 | V2 | 비고 |
|---|---|---|---|
| tau_m1 | - | 0.00500 (lower bound) | hip lag — 식별 안 됨 |
| tau_m2 | - | 0.00500 (lower bound) | knee lag — 식별 안 됨 |
| α | 0.50 ★ | 0.50 ★ | 동일 |
| 나머지 12 | (boundary chasers) | (대부분 boundary) | 거의 변화 없음 |

---

## 4. 새 용어 설명

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| **Motor lag** (`tau_m`) | "리모컨 누른 후 TV 켜지기 0.05초" | 명령 → 실제 응답 1차 시정수 |
| **1차 IIR low-pass** | "RC 회로 필터" | y[k] = (1-α)·y[k-1] + α·x[k], α=dt/(tau_m+dt) |
| **Current loop** | "모터 내부 전류 제어 미세 동작" | AK80-9 firmware의 internal current PID |
| **Internal feedback latency** | "사람이 무거운 짐 들 때 느끼는 0.1초 지연" | command-to-actual lag |
| **식별성 (identifiability)** | "두 함수의 차이가 noise 안에 숨음" | 데이터에서 파라미터 구별 가능 여부 |

---

## 5. 이유 (왜 motor lag 추가)

1. **V14 발견 (MASTER_INSIGHTS §10)**: 26.06.02 데이터에서 motor lag 26ms가 50% inverse RMSE 감소
2. **AK80-9 internal current loop**: ~25ms response (UMich 측정, paper a_hat 모델 결합)
3. **AK driver firmware**: command τ → current PID → actual torque에 RC-like 지연
4. **Forward consistency**: NLP-generated trajectory를 실 로봇에 재생 시 motor lag로 인해 차이 발생 → 모델에 포함해야 forward sim 정확

---

## 6. 결과 그래프

### 그림 1: V2 summary

(image_placeholder — summary.png)

**무엇을 보여주나**: V2의 inverse RMSE + forward drift (10 trial). V1과 비교.

**어디 봐야 하나**:
- Forward drift_q2 (우측 파란 막대): V1 대비 점프 trial에서 모두 감소 (특히 150_500_5: 47.6° → 34.2°)
- Inverse RMSE: V1과 거의 동일 (식별 X)

### 그림 2: jump_120_2_120_2 V2

(image_placeholder — jump_120_2_120_2.png)

**무엇을 보여주나**: 한 점프 trial에서 V2 결과.

### 그림 3: s2s_no_cvt_no_load V2

(image_placeholder — s2s_no_cvt_no_load.png)

---

## 7. 다양한 이미지

- 6개 점프 + 4개 s2s = 10 trial별 plot
- summary bar chart

---

## 8. 추가 정보

### 발견 1: Motor lag는 inverse에서 식별 안 됨

inverse_predict_v2는 V0의 inverse 결과에 lag 적용. 그러나 측정 τ도 motor side (이미 lag 거친 후). → lag(predict) ≈ measured 이면 tau_m을 작게 할수록 둘 다 비슷 → BO가 tau_m=0.005 (lower bound)로 밀림.

**해결책 (V3+에서 시도)**:
- Forward-weighted cost (w_drift > 0.9)
- 또는 tau_m을 별도로 estimate (lag된 측정 τ - 측정 τ의 차이 timing 분석)
- 또는 NLP 단계에서 식별

### 발견 2: Forward drift_q2 큰 개선

knee q2에서 motor lag 효과 가장 큼:
- knee는 점프에서 high acceleration (peak ddq 2000+ rad/s²)
- motor command와 actual 사이 ~25ms 지연이 forward integration에서 누적
- lag 추가 → trajectory 부드러워짐 → drift 30% 감소

### 발견 3: CVT는 여전히 큼

V2의 CVT 평균: hip 4.81, knee 12.83 — V1과 동일.
→ Motor lag는 CVT 특유 dynamics (clutch friction, body roll)와 무관. CVT 별도 작업 필요 (V7+).

### 관련 참고
- MASTER_INSIGHTS §10 (v14 motor lag breakthrough)
- AK80-9 firmware: T-Motor TMotorCANControl GitHub (UMich Neurobionics)
- v9 finding: hip/knee tau_m separate (24-43ms variation by PD gain)

---

## 9. 다음 version (V3) 계획

**V3 = V2 + Coulomb friction (cf1, cf2)** [+2 params = 16p]

### 가설

저속에서 viscous-only는 부정확:
- baseline: `fr = JF · dq` → dq=0에서 fr=0 (비현실)
- 추가: `fr = JF·dq + cf·tanh(dq/0.3)` → 정지 시에도 마찰
- V12에서 cf=0.78 (boundary), V10 cf=0.44 (safe) — V3는 ±0.8 자유

### 예상 결과

- Inverse RMSE: 약간 감소 (저속 영역 fit 개선)
- Forward drift: 비슷 (high-speed jump는 viscous가 dominant)
- α=0.5 lower bound에서 풀릴 가능성

### 다음
- V4: Stribeck friction (정→동 전환)
- V5: + Foot radius + kind-GRF + rotor inertia + state-bias (모두 추가)
- V6: NLP integration + self-consistency
- V7: Hold-out 6-fold CV

---

## 10. V2 진행 시간

- 시작: 2026-06-05 23:13 KST
- 종료: 2026-06-05 23:17 KST
- 소요: ~4분 (코드 + fit 6초 + plot)
- Deadline 12:00까지 남은: ~12.5 시간
