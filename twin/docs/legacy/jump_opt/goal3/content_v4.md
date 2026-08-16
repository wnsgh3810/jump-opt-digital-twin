# V4 — V3 + Stribeck friction (19 params)

> **Phase 3c**. Stribeck (`F_s1, F_s2, v_s`)을 추가. Jump knee inverse 10% 개선 (3.24→2.91), drift_q2 17% 개선 (16.58°→13.81°). F_s2 효과적이지만 F_s1은 미식별.

---

## 1. 이 버전 무엇

V4 = V3 (16p) + Stribeck friction = **19 params**.

```
Stribeck(dq) = (F_s - F_c)·exp(-(dq/v_s)²)·tanh(dq/0.05) + F_c·tanh(dq/0.3)
```

**물리적 의미**: 정지에서 static friction `F_s`, 속도 증가 시 점점 작아져 Coulomb `F_c`로. 표준 마찰 모델 (Mechanical Engineering).

---

## 2. V3 대비

| 지표 | V3 | V4 | 변화 |
|---|---|---|---|
| Jump inv_hip | 4.898 | 4.875 | -0.02 (동일) |
| Jump inv_knee | 3.238 | **2.908** | -0.3 (10% ↓) |
| Jump drift_q1 | 11.22° | 11.20° | 동일 |
| **Jump drift_q2** | 16.58° | **13.81°** | -2.8° (17% ↓) |
| S2s inv_knee | 2.360 | 2.009 | -0.4 (15% ↓) |
| Boundary chase | 88% | 84% | -4% (개선) |

**핵심**:
- F_s2 = 1.5 (upper) ★ → knee static friction 더 큰 값 원함
- F_s1 = 0 ★ → hip은 식별 안 됨 (saturation 영역에서 hip τ가 dominant)
- v_s = 1.0 (upper) — Stribeck velocity 더 넓은 영역

---

## 3. 추가/달라진 항

```python
def stribeck(dq, F_s, F_c, v_s):
    return ((F_s - F_c) * np.exp(-(dq/v_s)**2) * np.tanh(dq/0.05)
            + F_c * np.tanh(dq/0.3))

fr1 = JFv1*dq1 + stribeck(dq1, F_s1, cf1, v_s)
fr2 = JFv2*dq2 + stribeck(dq2, F_s2, cf2, v_s)
```

V4에서 cf의 정의 변경: V3에선 단독 Coulomb, V4에선 Stribeck의 F_c parameter.

---

## 4. 새 용어

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| **Static friction `F_s`** | "정지된 책을 처음 밀 때 큰 힘" | 정지에서 최대 마찰 |
| **Stribeck velocity `v_s`** | "정→동 전환 속도" | F_s에서 F_c로 감소하는 timescale |
| **Smoothed Stribeck** | "Hyperbolic tangent로 미분 가능" | NLP-friendly version |

---

## 5. 이유

- V3 Coulomb은 dq>0에서 cf 상수. 그러나 실제 마찰은 dq=0 부근에서 더 큼 (정지 마찰)
- Stribeck: dq=0 → F_s, dq>v_s → F_c → 표준 모델
- AK80 paper a_hat의 friction은 이미 일부 흡수하지만 외부 마찰 (joint side) 보강

---

## 6. 결과 그래프

### 그림 1: V4 summary

(image_placeholder — summary.png)

### 그림 2: jump_120 V4

(image_placeholder — jump_120_2_120_2.png)

### 그림 3: s2s_no_cvt V4

(image_placeholder — s2s_no_cvt_no_load.png)

---

## 7. 다양한 이미지

10 trial별 plot + summary.

---

## 8. 추가 정보

### 발견: knee static friction이 효과적

- F_s2 = 1.5 ★ — knee에서 Stribeck 큰 효과
- 점프에서 knee가 stance 시작 시 정지 → 빠른 회전
- 정지 마찰이 커야 토크 정확

### Hip은 Stribeck 약함

- F_s1 = 0 → hip은 빠른 회전 (점프 중) → 항상 dynamic region
- Stribeck의 정지 마찰 영역에 잘 안 들어감

---

## 9. 다음 (V5) 계획

**V5 = V4 + 모든 나머지 항 한 번에**:
- foot radius (r_foot)
- kind-GRF (grf_scale/bias × jump/s2s)
- rotor inertia (ka1, ka2)
- state-dep bias (off1_c, off1_q1, off2_c, off2_q2)

총 11 추가 → 30 params.

---

## 10. 진행
- 시작: 23:25 KST
- 종료: 23:27 KST (10초 fit)
- 소요: ~2분
