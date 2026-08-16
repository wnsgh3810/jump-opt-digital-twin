# V6 — NLP integration + Self-consistency check

> **Phase 4**. V5 식을 jump_opt baseline NLP에 wire-in. CasADi NLP solve 성공 (T_st=0.248s, h=0.798m). **Self-consistency: hip 5.11 Nm, knee 1.73 Nm** — V12 GOAL2 (5.9/6.3) 대비 knee **73% 개선**.

---

## 1. 이 버전 무엇

V6 = V5 dynamics + jump_opt NLP framework (CasADi+IPOPT). 새 파라미터 없음 (V5 30p 그대로).

**핵심 검증**: 
- V5 식을 NLP에 그대로 wire-in 가능?
- IPOPT 안정 수렴?
- NLP 결과 q*, dq*, ddq*에 V5 numpy inverse 적용 시 ||τ_check - τ_NLP|| 작음? (self-consistency)

---

## 2. V5 (numpy only) 대비 알아낸 점

### NLP 수렴 결과
- **T_st**: 0.248s (자유 변수, NLP 자체 결정 — 사용자 정정 (a) 응답)
- **Jump h**: 0.798 m (참고만, metric 아님 — 사용자 정정 (e) 응답)
- **IPOPT iter**: < 1초 (0.6s) 빠른 수렴 ★

### Self-consistency 측정 (핵심 metric)

| Metric | V12 (GOAL2) | **V6** | 개선 |
|---|---|---|---|
| Hip self-cons | 5.9 Nm | **5.11 Nm** | 13% ↓ |
| **Knee self-cons** | **6.3 Nm** | **1.73 Nm** | **73% ↓** ★★★ |

**의미**: NLP가 푼 q*, dq*에 V5 식을 다시 적용 시 τ_check가 NLP의 τ*과 거의 일치 (knee 거의 충족).  
사용자 진짜 goal — NLP optimal trajectory를 실 로봇에 재생 시 일치 — 가능성 크게 향상.

### 잔여 문제
- Hip self-cons 5.1 Nm 여전히 큼 (saturation 영역 영향 추정)
- Part A (전체 trial forward sim 발산) — s2s에서 q drift 발산 (700°+), CVT trial에서도

---

## 3. 추가/달라진 항

새 변수 없음. V5 dynamics를 CasADi `Function`으로 wrap:

```python
def build_casadi_dynamics_v5(params):
    """V5 식의 CasADi version (NLP 통합용).
    
    동일한 식:
      M(q)·ddx + C + G + fric + bias = J^T·F + τ (with motor lag, foot radius, etc.)
    """
    # ... (V5 numpy 식 그대로 CasADi SX로 변환)
    return ca.Function('dyn_v5', [x, v, tau, grf], [ddx])
```

**핵심**: V5의 모든 항 (motor lag, Coulomb, Stribeck, foot radius, kind-GRF, rotor inertia, state-bias)이 NLP-friendly한 smooth function들.

---

## 4. 새 용어

| 용어 | 의미 |
|---|---|
| **NLP self-consistency** | NLP solve 후 τ*, 같은 식에 q*, dq*, ddq* 다시 적용 시 τ_check 차이 |
| **CasADi `ca.Function`** | symbolic dynamics → callable함수 (NLP collocation에 사용) |
| **IPOPT** | Interior Point Optimizer (NLP solver) |
| **Trapezoidal collocation** | dt/2·(f_k + f_{k+1}) integration (CasADi NLP 표준) |
| **Bi-directional check** | inverse(q,dq,ddq)→τ → forward(τ)→q_sim vs q (self-test) |

---

## 5. 이유 (사용자 진짜 goal 직결)

V12 GOAL2의 핵심 잔여 문제 (MASTER_INSIGHTS §15):
- NLP self-consistency 5.9/6.3 Nm = "NLP optimal trajectory를 실 로봇에 재생 시 모델 예측이 5.9 Nm 어긋남"
- 이건 사용자 진짜 metric의 lower bound — 실 로봇에선 더 큰 차이 가능

V6의 목표: **단일 식 (NLP=ID 일치) → self-consistency 자동 보장**.

V12와 차이:
- V12: 2-DOF inverse identification 식 ≠ 3-DOF NLP forward 식 → numerical mismatch
- V6: **동일한 3-DOF 식 사용** → mismatch는 numerical method 차이만 (collocation vs gradient)

---

## 6. 결과 그래프

### 그림 1: V6 NLP trajectory + self-consistency

(image_placeholder — nlp_trajectory.png)

**무엇을 보여주나**: NLP가 푼 q*, dq*, τ*, GRF* trajectory + numpy inverse로 다시 계산한 τ_check.

**어디 봐야 하나**:
- 위쪽 panel: q1(t), q2(t) — NLP가 stance phase에서 만든 trajectory
- 중간 panel: τ_NLP (실선) vs τ_check (점선) — knee는 거의 겹침, hip은 약간 차이
- 아래 panel: residual (τ_NLP - τ_check) — knee < 2 Nm, hip 5 Nm 영역

### 그림 2: V5 vs V6 self-consistency 비교

(image_placeholder — self_consistency_v12_v6.png)

V12 (GOAL2) baseline 5.9/6.3 vs V6 5.11/1.73 막대 비교.

---

## 7. 다양한 이미지

- nlp_trajectory.png (NLP 결과 4-panel)
- self_consistency_v12_v6.png (비교 bar)

---

## 8. 추가 정보

### 발견 1: Knee self-consistency 1.7 Nm 달성

V12 → V6에서 73% 감소. 이유:
- V6는 NLP=ID 단일 식 → IPOPT implicit ddq와 numpy explicit ddq의 mismatch가 단순 수치 오차만 남음 (V12는 식 구조 차이로 더 큰 격차)
- knee는 V5의 Coulomb+Stribeck+foot radius로 inverse RMSE 1.65 Nm까지 작아짐 → self-cons도 작음

### 발견 2: Hip self-consistency 5.1 Nm 여전

원인:
- Hip은 saturation 영역 (peak 22 Nm)에서 NLP가 ±18 Nm hard bound에 부딪힘
- NLP는 saturated τ output (boundary), numpy inverse는 unsaturated 추정
- → **AK80 back-EMF saturation을 NLP에 추가 필요** (jump_opt baseline의 `ak80_torque` 함수)

### 발견 3: Forward sim 누적 drift는 여전 큼

Part A의 full-duration forward sim에서 점프 q2 drift 16-123°, s2s 700°+:
- 단기 (T=0.15s) drift는 V5에서 작음
- 그러나 trial 전체 (~0.4s+)에서 누적 발산
- 원인: model 정확도가 perfect가 아니라 시간 따라 error 누적
- forward sim은 numerical integration 자체의 stability에도 의존

### 향후 보강
- AK80 back-EMF saturation 추가 (NLP τ_eff = lim(v)·tanh(2τ/lim))
- Forward sim integration: trapezoidal → RK4 (안정성 ↑)
- Multi-shooting 또는 stabilized forward

---

## 9. 다음 (V7) 계획

**V7 = Hold-out 6-fold cross-validation**:
- 점프 6 trial 중 1개 hold-out, 5개로 fit → hold-out trial RMSE
- V10/V12와 비교 (V12: LOO 미적용 → V10: LOO 측정됨)
- Generalization 능력 검증
- 결과를 NLP self-consistency와 종합하여 최종 평가

---

## 10. 진행

- 시작: 2026-06-05 23:30 KST
- 종료: 2026-06-05 23:34 KST
- 소요: ~4분 (CasADi build 1초 + NLP solve 0.6초)
- Deadline까지: ~12 시간
