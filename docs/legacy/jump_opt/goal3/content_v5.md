# V5 — V4 + Foot radius + Kind-GRF + Rotor inertia + State-bias (30 params)

> **Phase 3d (Phase 3 마무리)**. 4개 카테고리의 명백 정당 항을 모두 추가 (11 신규). **Drift_q1 86% 감소 (11.20°→1.59°)**, drift_q2 57% 감소. Jump inverse hip 29%, knee 43% 개선. 그러나 boundary 90% — over-fit 위험 증가.

---

## 1. 이 버전 무엇

V5 = V4 (19p) + **4가지 카테고리 11개 추가** = **30 params**.

### V5 추가 11개:
1. `r_foot` (foot radius)
2. `grf_scale_jump, grf_scale_s2s, grf_bias_jump, grf_bias_s2s` (kind-specific GRF calibration)
3. `ka1, ka2` (rotor inertia)
4. `off1_c, off1_q1, off2_c, off2_q2` (state-dep bias)

GOAL2의 정당성 분석 (MASTER_INSIGHTS §17): "명백히 정당 15개" 중 NLP-friendly 11개 distill.

---

## 2. V4 대비 — 큰 개선

| 지표 | V4 | V5 | 변화 |
|---|---|---|---|
| **Jump inv_hip** | 4.88 | **3.48** | -1.4 (29% ↓) ★ |
| **Jump inv_knee** | 2.91 | **1.65** | -1.3 (43% ↓) ★★ |
| **Jump drift_q1** | 11.20° | **1.59°** | **-9.6° (86% ↓)** ★★★ |
| **Jump drift_q2** | 13.81° | **5.90°** | -7.9° (57% ↓) ★★ |
| S2s_no_cvt inv | 2.11/2.01 | 1.70/7.41 | knee 악화 (drift_q2 51°!) |
| **CVT inv** | 4.93/11.79 | **1.57/8.25** | **큰 개선** ★ |
| Boundary chase | 84% | **90%** | over-fit 우려 |

**핵심 trade-off**:
- 점프 forward drift는 매우 작아짐 (1.6°, 5.9°) — 사용자 진짜 metric 거의 충족
- 그러나 boundary chase 90% → over-fit 신호
- s2s_no_cvt drift_q2 51° → 발산 (다른 trial과 inconsistency)

---

## 3. 추가/달라진 항

```python
# V4 → V5 추가:
# 1. Foot radius (mom_h, mom_k에 -r_foot·s12)
mom_h_z = l1*c1 + l2*c12 - r_foot*s12   # 새
mom_k_z = l2*c12 - r_foot*s12            # 새

# 2. Kind-specific GRF
if trial['kind'] == 'jump':
    grfz_eff = grf_scale_jump * grfz + grf_bias_jump
else:
    grfz_eff = grf_scale_s2s * grfz + grf_bias_s2s

# 3. Rotor inertia (M22, M33에 ka 추가)
M22 = Is1 + 2*K*c2 + ka1   # 새
M33 = Is2 + ka2            # 새

# 4. State-dep bias
bias1 = off1_c + off1_q1*q1
bias2 = off2_c + off2_q2*q2
RHS2 -= bias1
RHS3 -= bias2
```

| 변수 | V5 fit | 의미 |
|---|---|---|
| r_foot | **0.040 (upper) ★** | foot radius — 더 큰 값 원함 |
| grf_scale_jump | **1.20 (upper) ★** | jump GRF 더 큰 magnitude |
| grf_scale_s2s | **0.50 (lower) ★** | s2s GRF 작게 |
| grf_bias_jump | +20 (upper) ★ | jump bias |
| grf_bias_s2s | -20 (lower) ★ | s2s bias |
| ka1 | 0.050 (upper) ★ | hip rotor inertia |
| ka2 | 0.002 | knee rotor inertia (식별됨) |
| off1_c, off2_c | -0.5 (lower) ★ | bias 한계 |

---

## 4. 새 용어

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| **Foot radius `r_foot`** | "맨발 vs 신발의 발 두께 차이" | point contact 가정 깨짐. moment arm에 -r_foot·s12 보정 |
| **Kind-specific GRF** | "점프와 일어서기는 다른 측정 모드" | force plate response가 동작 종류 따라 다름 |
| **GRF scale, bias** | "체중계 영점/감도 보정" | force plate calibration |
| **Rotor inertia `ka`** | "자동차 엔진 자체 무게" | gear² reflected motor inertia |
| **State-dep bias** | "활시위처럼 자세에 비례하는 토크" | bias = off_c + off_q1·q1 (cable spring) |

---

## 5. 이유

각 항의 정당성 (MASTER_INSIGHTS §17 참조):

1. **r_foot**: point contact 가정 깨짐 (실제 발 두께 ~22mm, 모델 0)
2. **kind-GRF**: jump (200N+) vs s2s (50N 이내) force plate response 다름
3. **rotor inertia**: gear ratio² reflected, CAD에 없음 (gear² = 81배 amplification)
4. **state-dep bias**: 4-bar 링크의 cable spring stiffness

---

## 6. 결과 그래프

### 그림 1: V5 summary

(image_placeholder — summary.png)

→ **Drift bar chart에서 점프 모두 < 2° (목표 달성)**. CVT도 < 5°.

### 그림 2: V5 jump_120

(image_placeholder — jump_120_2_120_2.png)

→ Forward sim trajectory가 측정 q와 거의 일치.

### 그림 3: V5 s2s_no_cvt (drift 발산)

(image_placeholder — s2s_no_cvt_no_load.png)

→ s2s_no_cvt만 q2 발산 (51°). 다른 trial과 inconsistency — over-fit 신호.

---

## 7. 다양한 이미지

- 10 trial별 V5 plot
- summary

---

## 8. 추가 정보

### 발견 1: V5의 큰 forward 개선

drift_q1 11° → 1.6° (86% 감소). 핵심 영향:
- kind-GRF (jump vs s2s 분리) — 가장 큰 단일 영향
- r_foot (40mm upper bound) — moment arm 보정
- 두 효과가 함께 forward integration 안정화

### 발견 2: Boundary 90% — over-fit 신호

V5에서 30 params 중 27개 boundary 도달. V12 GOAL2의 57%보다 높음.
- V5의 식이 fit에는 잘 맞지만 generalization 위험
- 다른 trial에서 부정확할 가능성
- Phase 5 hold-out CV에서 검증 필요

### 발견 3: s2s_no_cvt drift 발산

특이하게 s2s_no_cvt만 drift_q2 51°:
- 다른 s2s_cvt (1-5°)와 inconsistency
- s2s_no_cvt는 GRF=Force plate, CVT trial은 약간 다른 GRF measurement
- kind-GRF가 jump/s2s 분리만 — no_cvt와 cvt 추가 분리 필요할 수도

### 향후 보강 방향
- bound 확장 (cf, F_s, r_foot, GRF scale) 또는 의심 항 제거
- Per-trial bias도 시도 가능 (V12의 outlier 분리 패턴)

---

## 9. 다음 (V6) 계획

**V6 = V5 식을 jump_opt NLP에 그대로 wire-in + Self-consistency check**:

목표:
- IPOPT가 V5 식으로 NLP 수렴
- NLP optimal q*, dq*, ddq*에 V5 inverse 적용 → ||predict τ - NLP τ*|| < 1 Nm
- V12의 self-consistency 5.9/6.3 Nm 격차 해결

---

## 10. 진행

- 시작: 2026-06-05 23:25 KST
- 종료: 2026-06-05 23:30 KST
- 소요: ~5분 (fit 33초)
- Deadline까지: ~12.5시간
