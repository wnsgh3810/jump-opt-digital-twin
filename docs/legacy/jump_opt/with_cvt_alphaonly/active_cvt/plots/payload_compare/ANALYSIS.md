# Payload Compare — Active CVT가 +0.5kg payload 손실을 얼마나 보상하는가

## 설정

| Case | M_base | l_i 모드 | Dynamics |
|------|--------|---------|----------|
| **A** | 1.02 kg (default) | Static (fixed) | quasi-static (v1) |
| **B** | 1.52 kg (+0.5 kg) | Static (fixed) | quasi-static (v1) |
| **C** | 1.52 kg (+0.5 kg) | Active CVT (≤30 mm/s) | **full ∂/∂l_i (v2)** |

다른 robot params 모두 동일. 같은 NLP framework + 같은 curriculum.

---

## 핵심 결과

| Case | h_max | vs A | vs B |
|------|-------|------|------|
| A: Default static | **1.0110 m** | baseline | — |
| B: +0.5kg static | **0.9379 m** | **−7.23%** | baseline |
| C: +0.5kg active CVT | **1.0026 m** | **−0.84%** | **+6.90%** |

### 정량 통찰

★ **Active CVT가 mass-induced 점프 손실의 88.4%를 회복** (1.0110 − 0.9379 = 73.1 mm 손실 중 64.7 mm 회복)

★ **+0.5 kg payload (질량 +49%) 에도 불구하고 default 대비 점프 손실 −0.84%만** — 활성 CVT가 mass-related performance penalty의 거의 모두를 보상

★ **active CVT가 실용적 의미**: lead-screw 30 mm/s actuator만으로도 50% mass 증가에 대응 가능

---

## 어떻게 회복되는가? — Mechanism Analysis

### l_i 적응 패턴 (Case C)
- **초기 (stance 시작 ~50ms)**: l_i ≈ 22-23 mm — TR 상대적으로 작음 → torque 증폭 (heavier mass 들어올리기)
- **Take-off 직전 (100-130ms)**: l_i가 25.4 mm로 ramp up — TR 증가 → motor 속도를 다리 펴짐 속도로 더 효율적 변환
- **|dl_i/dt|max = 30 mm/s** — 한계까지 사용 (binding constraint)

### Trajectory 차이 (Case C vs A)
| 변수 | A | C | 차이 |
|------|---|---|------|
| Take-off dz | A | 유사 | 거의 동일 |
| Take-off τ_m | bounded | **bounded** | 비슷 (motor 한계 사용) |
| GRF_z peak | normal | **higher** | 무거운 mass 들어올리기 위해 더 큰 impulse |
| T_st | 125 ms | ~125 ms | 비슷 |

### 왜 88% 회복인가?
Active CVT가 **transmission ratio를 phase별로 최적화**해서:
1. Compression (stance 초기): TR↓ → 큰 torque 출력 (mass에 대항)
2. Extension (stance 후기): TR↑ → 빠른 motor 회전이 leg extension 속도로 효율 변환

Static CVT (Case B)는 단일 TR 값으로 모든 phase 대응 → trade-off 양보. Active CVT (Case C)는 phase별 다른 TR로 trade-off 해결.

---

## 한계와 가정

1. **Lead-screw actuator force F_li**는 NLP에서 free (mechanism으로 자동 결정). 실제로는 lead-screw 모터에도 torque/속도 한계 있음 — 30 mm/s만 enforce
2. **Payload는 base에만**, 아무 link inertia 변화 X (rigid attachment 가정)
3. **NLP convergence는 IPOPT Solve_Succeeded** (모든 stage)
4. v2 dynamics 사용 (Coriolis + ddq2→ddqm inversion에 ∂/∂l_i 모두 포함)
5. **모델 자체 정확성**: 30 mm/s 영역에서 v1≈v2 (1mm 이내 차이) — quasi-static 가정 valid

---

## 파일

- `01_hmax_bar.png` — headline bar chart with annotations
- `02_li_profile.png` — l_i(t) 3-way
- `03_dli_profile.png` — Case C의 dl_i (30 mm/s 한계까지 사용)
- `04_tr_profile.png` — TR(t) 비교
- `05_q_dq_tau.png` — joint state 6-panel
- `06_grf_dz.png` — GRF + base velocity
- `07_summary_4panel.png` — overall summary
- `../../payload_compare_results.pkl` — raw chain dict
- `../../payload_compare_summary.json` — numeric summary
- `../../payload_compare_log.txt` — full run log

---

## 다음 가능한 연구 방향

1. **Payload sweep**: +0.1, +0.2, ..., +2.0 kg에서 점프 손실 vs active CVT 회복률 — recovery 곡선
2. **Actuator limit sweep**: 10, 30, 50, 100, 200 mm/s에서 회복 ceiling
3. **Combined**: 다양한 (mass, l̇ᵢ_max) 조합의 contour plot — 어떤 payload까지 active CVT로 default 점프 수준 유지 가능?
4. **Energy analysis**: Case C가 더 많은 mechanical work를 lead-screw motor에서 input 받는지 (총 energy budget)
