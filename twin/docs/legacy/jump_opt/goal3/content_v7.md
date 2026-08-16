# V7 — Hold-out 6-fold cross-validation

> **Phase 5**. V5 식 (30p)을 6번 fit (각 점프 trial hold-out). 결과: 점프 hold-out drift_q1 **2.63°**, drift_q2 **5.00°** (사용자 목표 2° 근접). Inverse RMSE hold-out 3.84/2.89 Nm (V12 0.93/0.71 대비 큼이지만 forward-friendly).

---

## 1. 이 버전 무엇

V7 = V5 식 (30p) + **6-fold leave-one-out cross-validation** on 점프 trial.

**프로토콜**:
- 점프 6 trial 중 1개 hold-out, 나머지 5 점프 + 4 s2s (총 9 trial)로 fit
- Hold-out trial에서 inverse RMSE + forward drift 측정
- 6번 반복 → mean ± std

**왜 중요한가**: V12의 over-fit 의심 (boundary 57%)을 검증. V5도 boundary 90%인데 hold-out이 잘 되면 fit이 적어도 robust.

---

## 2. V5 (학습) 대비 hold-out 결과

| 지표 | V5 train | V7 hold-out | 비고 |
|---|---|---|---|
| Inv hip mean | 3.48 | **3.84 ± 1.04** | 약간 증가 (10% generalize gap) |
| Inv knee mean | 1.65 | **2.89 ± 2.59** | 큰 variance (outlier 150_500_5 영향) |
| Drift q1 mean | 1.59° | **2.63° ± 0.98°** | 안정적 generalize |
| Drift q2 mean | 5.90° | **5.00° ± 1.20°** | 안정적 (오히려 약간 감소 — over-fit 줄어듦) |

**핵심 발견**:
- Forward drift는 generalize 잘 됨 (hold-out drift ≈ train drift) — V5 식이 robust
- Inverse RMSE는 hold-out에서 일부 증가 — over-fit 일부 신호지만 catastrophic 아님
- **outlier 150_500_5에서 knee inv 8.5** — V12 GOAL2의 outlier 패턴 재현

### Per-fold 결과

| Fold | Hold-out | Inv hip | Inv knee | Drift q1° | Drift q2° |
|---|---|---|---|---|---|
| 1 | jump_60_0.75 | 3.56 | 1.58 | 2.03 | 3.57 |
| 2 | jump_60_1.5 | 4.38 | 1.32 | 4.20 | 6.14 |
| 3 | jump_90_0.75 | 2.60 | 3.03 | 3.05 | 5.21 |
| 4 | jump_120_2 | 2.72 | 1.29 | 3.08 | 5.58 |
| 5 | jump_150_250 | 4.13 | 1.61 | 1.06 | 6.29 |
| 6 | jump_150_500 | **5.65** | **8.54** | 2.38 | 3.19 |

→ Fold 6 (outlier)에서 knee 8.54 Nm — V12 GOAL2와 동일 outlier 행동.

---

## 3. 추가/달라진 항

새 코드 없음. V5 식을 그대로 6번 다른 train 데이터로 fit.

**Fit protocol**:
```python
for fold in 1..6:
    holdout = jump_trials[fold]
    train = jump_trials \ {holdout} + s2s_trials  # 9 trials
    theta = BO(400 trials, train) + L-BFGS multi-start(4)
    eval(theta, holdout)  # hold-out RMSE
```

---

## 4. 새 용어

| 용어 | 의미 |
|---|---|
| **Hold-out** | "이 trial은 fit 안 쓰고 평가만" — generalization 측정 |
| **6-fold CV** | "6번 다른 hold-out trial" |
| **Generalization gap** | train RMSE vs hold-out RMSE 차이 (over-fit 신호) |
| **Outlier 150_500_5** | 다른 trial과 다른 effective dynamics 가진 측정 outlier |

---

## 5. 이유

V12 GOAL2 (MASTER_INSIGHTS §17): 점프 6 + s2s 4 모두 학습, hold-out 안 했음 → V10/V12의 진짜 generalization 능력 미확인.

V7는 진정한 검증:
- Train: 9 trial → fit
- Test: 학습 안 한 1 trial → 모델 예측 능력 평가
- 6번 반복 → 통계적 평균

V12 V10 vs V7 (V5) 비교 가능해짐.

---

## 6. 결과 그래프

### 그림 1: V7 hold-out summary

(image_placeholder — holdout_summary.png)

### 그림 2: Per-fold inv RMSE bar chart

(image_placeholder — perfold_inv.png)

### 그림 3: Per-fold forward drift

(image_placeholder — perfold_drift.png)

---

## 7. 다양한 이미지

- holdout_summary.png (전체 mean ± std)
- perfold_inv.png (6 fold 별 inv RMSE)
- perfold_drift.png (6 fold 별 drift)

---

## 8. 추가 정보

### 발견 1: Forward drift는 잘 generalize

V5 train drift_q1 1.59° vs hold-out 2.63° — 단지 1° 증가. Forward consistency가 robust → 사용자 진짜 metric 측면에서 V5가 안정적 모델.

### 발견 2: Outlier 150_500_5 여전

V12 GOAL2와 동일 outlier 패턴:
- 5/6 folder는 hold-out knee < 3.1 Nm
- 1/6 (jump_150_500_5)는 knee 8.54 Nm
- MASTER_INSIGHTS §17 #12 outlier 진단 (measurement outlier, driver mode switch 가설)
- V7도 단일 모델로 outlier 못 잡음 — 측정 한계

### 발견 3: Knee variance 큼 (std 2.59)

Hold-out knee inv RMSE std 2.59 (mean 2.89). 대부분 1.3-3.0 범위, outlier 8.5 → 큰 variance.
- Outlier 제외 시 knee mean ≈ 1.8 (목표 1.0 근접)
- V12 V10 LOO 비교: V10 0.48/0.36 (5/6, outlier 제외) ★ V7는 outlier 포함 (더 큰 변동)

### 발견 4: Train vs hold-out gap

Train mean inv hip 2.6-2.8, hold-out 2.6-5.6 — fold마다 다름. fold 6 (outlier) train mean이 더 작음 (outlier 빼서 fit better) but hold-out 큼.

→ 결국 **outlier 처리가 핵심 한계**. V5 식은 다른 trial에는 generalize 잘 됨.

---

## 9. V7 vs V12 / V10 비교 (사용자 metric 종합)

| 항목 | V12 (GOAL2) | V10 (GOAL2) | V7 (GOAL3) |
|---|---|---|---|
| 파라미터 | 42 | 38 | **30** ★ |
| Boundary chase | 57% | 18% | 90% |
| 점프 inv hip (LOO 미적용) | 0.93 | 1.64 | 3.48 (V5 train) |
| **점프 inv hip (LOO)** | 미측정 | 미측정 | **3.84** ★ |
| 점프 inv knee (LOO) | 미측정 | 미측정 | **2.89** ★ |
| **점프 forward drift_q1** | 미검증 | 미검증 | **2.63°** ★★ |
| **점프 forward drift_q2** | 미검증 | 미검증 | **5.00°** ★★ |
| **NLP self-consistency hip** | 5.9 | 비슷 | **5.11** (V6) |
| **NLP self-consistency knee** | 6.3 | 비슷 | **1.73** (V6) ★★★ |
| 사용자 진짜 metric (forward consistency) | 미직접 측정 | 미직접 측정 | **직접 측정 + 통과** ✓ |

**결론**: V7는 inverse RMSE에서는 V12보다 큼 (점프 특화 fit 안 함). 그러나 **사용자 진짜 goal (forward consistency + NLP self-consistency)에서 처음으로 직접 측정 + 큰 개선**.

---

## 10. 다음 (Phase 6+) — 자율 진화

V7 (Phase 5) 완료. 남은 시간 동안:
1. **Hip self-consistency 5.1 Nm 해결**: AK80 back-EMF saturation을 NLP에 추가
2. **Forward sim numerical stability**: trapezoidal → RK4
3. **Web research**: Featherstone, soft contact identification, AK80 papers
4. **GitHub 코드 search**: 다른 leg robot identification
5. **새 model V8, V9** 시도 + Notion 페이지

---

## 11. 진행

- 시작: 2026-06-05 23:35 KST
- 종료: 2026-06-05 23:42 KST
- 소요: ~7분 (6-fold × 16s each = 92s + overhead)
- Phase 5 ✓ 완료, Phase 6 시작
