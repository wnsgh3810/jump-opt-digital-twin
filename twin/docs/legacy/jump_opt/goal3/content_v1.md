# V1 — Baseline 12 params fit (BO + L-BFGS multi-start)

> **Phase 2 결과**. jump_opt baseline 식 그대로 (3-DOF, M·ddx + C + G + mom·GRF + viscous friction)을 사용자 10 trial에 fit. 결과: Boundary chase 92% (under-spec model 신호) + jump drift 17°/29° (큰 forward 발산).

---

## 1. 이 버전 무엇

V1 = jump_opt baseline 식 그대로 사용. 변수 12개 (M_tot, A, B, K, I_sig1, I_sig2, l1, l2, α, JF_v1, JF_v2, RAIL_F). CAD ±20% bound. 

**목적**: Baseline에서 출발해서 추가 항이 정말 필요한지 ablation으로 검증할 starting point 확보.

**Metric**:
- Forward drift (primary, 사용자 진짜 goal) — 실측 τ/GRF input → forward sim → 실측 q와 비교
- Inverse RMSE (secondary) — 측정 q,dq,ddq → predict τ → 측정 τ와 비교

---

## 2. V0 (no fit) 대비 알아낸 점

V0 baseline (CAD only) → V1 fit:
- Jump hip inverse: 9.4 → 5.4 Nm (42% 개선)
- Jump knee inverse: 1.5 → 3.5 Nm (악화 — fit이 다른 trial에 맞춰지면서)
- S2s no_cvt: 큰 변화 없음

**핵심 관찰**:
1. **Boundary chase 92%** (11/12 params boundary 도달) → V1 식이 너무 단순함을 의미
2. **Forward drift 17°/29° (점프)** → baseline 식은 100ms forward 안 됨. Motor lag, friction model 등 누락이 분명
3. **CVT trial 잔차 가장 큼** (hip 4.8, knee 12.9 평균) → clutch dynamics 누락 (MASTER_INSIGHTS §8)

---

## 3. 추가/달라진 항

V0 → V1: 변화 없음 (단지 fit). 모델 식은 그대로:

```
M_mat · [ddz, ddq1, ddq2] = RHS - C - G + F_friction
RHS = [eff_grf_z,
       tau1 - eff_grf_x·mom_h_x + eff_grf_z·mom_h_z,
       tau2 - eff_grf_x·mom_k_x + eff_grf_z·mom_k_z]
F_friction = [-RAIL_F·dz, -JF_v1·dq1, -JF_v2·dq2]
eff_grf = α · GRF
```

**12 parameters**:
| 변수 | V1 fit value | CAD | 의미 |
|---|---|---|---|
| M_tot | 3.39 | 3.27 | 전체 질량 (kg) |
| A | 0.097 ★ | 0.137 | hip gravity coeff (boundary) |
| B | -0.0051 ★ | -0.0076 | knee gravity coeff (boundary) |
| K | 0.00347 ★ | 0.00289 | hip-knee coupling (boundary) |
| I_sig1 | 0.0415 ★ | 0.0345 | hip 관성 (boundary) |
| I_sig2 | 0.00295 ★ | 0.00457 | knee 관성 (boundary) |
| l1 | 0.2625 ★ | 0.25 | thigh length (boundary) |
| l2 | 0.2375 ★ | 0.25 | shin length (boundary) |
| α | 0.50 ★ | 0.85 | contact coupling (lower bound) |
| JF_v1 | 0.50 ★ | 0.1 | hip viscous (upper bound) |
| JF_v2 | 0.50 ★ | 0.1 | knee viscous (upper bound) |
| RAIL_F | 0.024 ★ | 0.0 | rail viscous |

→ ★ = boundary chase. 거의 모든 params가 한계 도달 = **under-spec model**.

---

## 4. 새 용어 설명

| 용어 | 일상 비유 | 의미 |
|---|---|---|
| **Forward sim drift** | "GPS 없이 차로 가다가 점점 위치 어긋남" | 실측 τ로 시뮬 → 시간 따라 실측 q와 차이 누적 |
| **Inverse RMSE** | "어떤 힘으로 다리 움직였지? 역추적" | 측정 q,dq,ddq → 토크 계산 |
| **Boundary chase** | "최적화가 한계까지 밀어붙임" | 파라미터가 bound 경계 도달 (over-fit 또는 under-spec 신호) |
| **Under-spec model** | "방정식 부족해서 정답이 한 점에 안 모임" | 모델 항이 데이터를 다 설명 못 함 |
| **CAD ±20% bound** | "설계도 값에서 20% 자유" | physical realism 확보 |
| **Multi-start L-BFGS** | "여러 출발점에서 등반" | local minima 회피 |

---

## 5. 이유 (왜 baseline 12p로 시작)

1. **NLP=ID 단일 식 원칙** (사용자 명시): jump_opt NLP가 3-DOF baseline 식을 사용 → identification도 같은 식 사용해야 forward consistency 보장
2. **V12의 over-fit 교훈** (MASTER_INSIGHTS §16): 42 params boundary 57% → 의심 항 (mom_h poly, hx3, Gq1) 모두 배제하고 시작
3. **Generalization 우선** (사용자 명시): 점프 특화 X → 단일 모델로 점프 6 + s2s 4 모두 fit
4. **Ablation으로 항별 영향 측정**: V2~V5에서 항 하나씩 추가하며 drift 감소량 측정

---

## 6. 결과 그래프

### 그림 1: V1 summary — 각 trial별 inverse RMSE + forward drift

(image_placeholder — summary.png)

**무엇을 보여주나**: 10 trial의 V1 결과를 한 번에. 좌측 inverse RMSE, 우측 forward drift.

**어디 봐야 하나**:
- Inverse RMSE: 점프 hip 5-7 Nm, knee 3-4 Nm. s2s_no_cvt만 < 3 Nm.
- Forward drift: 점프 q1 15-18°, q2 23-48°. CVT는 매우 큼 (50° q1, 30° q2).
- **사용자 목표 (1 Nm inverse, 2° drift)에 모두 미달** — 추가 항 필요.

### 그림 2-7: 각 trial별 4-panel (τ_hip, τ_knee, q1 forward, q2 forward)

(image_placeholder — jump_120_2_120_2.png)
(image_placeholder — s2s_no_cvt_no_load.png)

**무엇을 보여주나**: 한 trial에서 model predict vs 측정의 시간 trajectory.

**어디 봐야 하나**:
- τ_hip predict (빨강 점선) vs 측정 (파랑): peak 시기 비슷, magnitude 다름 (motor lag 누락 의심)
- Forward q1 (빨강 점선) vs 측정 (파랑): 시간 따라 누적 발산 — model 부정확
- Forward q2: knee에서 더 큰 drift

---

## 7. 다양한 이미지

- summary.png — bar chart 비교
- jump_60_0.75_60_2.png ~ jump_150_2.2_500_5.png (6개 점프)
- s2s_no_cvt_no_load.png (s2s no CVT)
- s2s_cvt_no_load.png, s2s_cvt_load_2.5.png, s2s_cvt_load_5.png (CVT validation)

---

## 8. 추가 정보

### 발견 1: Baseline 식의 fundamental 한계

V1의 boundary chase 92%는 **단순 over-fit이 아니라 under-spec** 신호:
- 12 params 거의 다 한계로 밀림 → 더 자유로운 모델이 필요
- 점프 hip 5 Nm은 V14의 motor lag 발견 (MASTER_INSIGHTS §10) 이전 수준
- **V2에서 motor lag 추가 시 50% 감소 예상**

### 발견 2: CVT trial 잔차 폭증

CVT 3 trial: hip 4.8, knee 12.9 평균 (s2s_no_cvt의 5-6배).
- TR (transmission ratio) 적용했지만 clutch dynamics 미모델링 (MASTER_INSIGHTS §8 참조)
- V2~V7 끝나도 CVT는 별도 작업 권장

### 발견 3: α=0.5 lower bound

V1에서 α=0.50 (bound 하한):
- baseline은 α=0.85 (CAD 가정)
- fit이 α를 아래로 밀어내는 = GRF 영향을 줄이려 함
- 다른 항 (motor lag, friction)이 GRF 결합을 보정해야 함을 의미

### 참고 문헌
- Featherstone, *Rigid Body Dynamics Algorithms* — floating base J^T·F_ext 표준
- Murray-Li-Sastry, *A Mathematical Introduction to Robotic Manipulation*
- Hunt-Crossley contact model 논문 (soft contact alternatives)

---

## 9. 다음 version (V2) 계획

**V2 = V1 + Motor 1st-order lag (tau_m1, tau_m2)** [+2 params = 14p]

### 가설

AK80-9 driver의 internal current loop response 시간 ~25ms (UMich a_hat 측정).
명령 τ → 실제 motor τ에 1차 지연 발생.

```
τ_actual(t) = LPF(τ_cmd(t), tau_m)
```

V14 발견 (MASTER_INSIGHTS §10): 26.06.02 모델에서 motor lag 26ms 추가 → jump hip RMSE 2.9 → 1.4 Nm (50% 개선).

### 예상 결과

- Inverse RMSE jump hip: 5.3 → **2.5-3.5 Nm**
- Forward drift q1 (T=0.15s): 17° → **8-12°**
- Boundary chase: 92% → **50-60%** (개선 but 충분치 않음)

### V2 실행 후 다음 step

- V3: Coulomb friction (저속에서 viscous-only 부정확 해결)
- V4: Stribeck (정→동 마찰 전환)
- V5: foot radius + kind-GRF + rotor inertia + state-bias

---

## 10. V1 진행 시간

- 시작: 2026-06-05 23:05 KST
- 종료: 2026-06-05 23:11 KST
- 소요: ~6분 (코드 작성 4분 + fit 6초 + plot 1분)
- Phase 2 (V1) ✓ 완료, Phase 3 (V2~V5) 시작
