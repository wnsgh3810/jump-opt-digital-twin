# V3 — V2 + Coulomb friction (16 params)

> **Phase 3b**. V2에 Coulomb friction (`cf1, cf2`)을 추가. Jump knee inverse 16% 개선 (3.84→3.24), drift_q1 30% 개선 (16°→11°). cf 둘 다 upper bound (0.8) — Coulomb 효과 분명, 더 큰 값 원함.

---

## 1. 이 버전 무엇

V3 = V2 (14p) + Coulomb friction (cf1 hip, cf2 knee) = **16 params**.

**핵심 추가**:
- `fr = JF·dq + cf·tanh(dq/0.3)` (viscous + Coulomb 부드러운 형태)
- 저속에서 viscous-only는 마찰 거의 0 → 비현실. Coulomb는 부호만 잡음.
- AK80-9 paper a_hat 모델의 `a_3` 항 (Coulomb friction)과 같은 motivation.

---

## 2. V2 대비 알아낸 점

| 지표 | V2 | V3 | 변화 |
|---|---|---|---|
| Jump inv_hip | 5.413 | **4.898** | -0.5 (9% ↓) |
| Jump inv_knee | 3.839 | **3.238** | -0.6 (16% ↓) |
| **Jump drift_q1** | 15.97° | **11.22°** | **-4.8° (30% ↓)** ★ |
| **Jump drift_q2** | 20.78° | **16.58°** | -4.2° (20% ↓) |
| S2s inv_hip | 1.825 | 1.777 | 동일 |
| S2s inv_knee | 2.847 | 2.360 | -0.5 (17% ↓) |
| **Boundary chase** | 86% | **88%** | (cf 추가됐는데 식별 잘 됨) |

**핵심 발견**: Coulomb friction `cf1=0.80, cf2=0.80` 둘 다 upper bound 도달 → 더 큰 값 원함. V4에서 bound 확장.

---

## 3. 추가/달라진 항

```python
# V2 → V3 추가 (dynamics_v3.py):
def dynamics_3dof_v3(...):
    # ...
    fr1 = JFv1*dq1 + cf1*np.tanh(dq1/0.3)   # V3 new: + Coulomb
    fr2 = JFv2*dq2 + cf2*np.tanh(dq2/0.3)
```

| 변수 | V3 fit | V2 | 의미 |
|---|---|---|---|
| cf1 | **0.80 (upper) ★** | - | Hip Coulomb friction (Nm) |
| cf2 | **0.80 (upper) ★** | - | Knee Coulomb friction (Nm) |
| 나머지 14 | (대부분 boundary) | 거의 동일 | 변화 미미 |

---

## 4. 새 용어 설명

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| **Coulomb friction** | "녹슨 경첩의 일정한 저항" | 속도 부호만 결정, magnitude 일정 |
| **`tanh(dq/0.3)`** | "부호 함수의 부드러운 버전" | sign(dq)에 smooth approximation |
| **a_3 (UMich a_hat)** | "AK80 motor 내부 Coulomb 항" | paper a_hat의 Coulomb 부분 |

---

## 5. 이유

V2에선 viscous-only friction이 저속에서 토크 거의 0 → 비현실:
- V2: dq=0에서 fr=0
- 실 robot: 정지 마찰 명확히 존재 (정지 → 운동 전환 시 큰 마찰)

`cf·tanh(dq/0.3)`은 smooth하면서도 dq≠0에선 cf 근처 magnitude. NLP-friendly (미분 가능).

---

## 6. 결과 그래프

### 그림 1: V3 summary

(image_placeholder — summary.png)

### 그림 2: jump_120_2_120_2 V3

(image_placeholder — jump_120_2_120_2.png)

### 그림 3: s2s_no_cvt V3

(image_placeholder — s2s_no_cvt_no_load.png)

---

## 7. 다양한 이미지

- 10 trial별 V3 plot
- summary

---

## 8. 추가 정보

### 발견: Coulomb friction 효과 큼

`cf` 추가만으로 drift_q1 30% 감소. 이유:
- 점프 stance 초기 (저속 영역) 마찰 표현 정확
- forward integration 시 누적 오차 감소

### cf upper bound 신호

V12에서 cf=0.78 (upper 0.8)이 사용자 비판 (c) "비현실 파라미터" 핵심이었음.  
V3에서도 cf=1.2 까지 확장 시도 (V4)에서 확인.

---

## 9. 다음 (V4) 계획

**V4 = V3 + Stribeck friction**:
- `F_s` (static friction), `v_s` (Stribeck velocity)
- 정→동 마찰 전환 (정지 시 큰 마찰, 속도↑ → 작아짐)

---

## 10. 진행

- 시작: 2026-06-05 23:21 KST
- 종료: 2026-06-05 23:25 KST
- 소요: ~4분
