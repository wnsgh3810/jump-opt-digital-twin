# GOAL3 — Generalized Forward-Consistent Robot Model (2026-06-06)

> 4-Bar CVT Single-Leg Jump Robot의 동역학 모델을 forward consistency 관점에서 다시 식별.
> 사용자 정정 4가지 반영 (점프 높이 매칭 X, forward consistency O, NLP 수렴 가능, generalization).

---

## 📌 한 줄 Mission

> **"NLP가 만든 q*(t), dq*(t)만으로 실 robot 제어 시, 실측 τ와 GRF가 NLP가 예측한 τ*, GRF*와 동일하게 나오는 generalized 동역학 모델."**

---

## 🎯 진짜 진짜 Goal (사용자 정정 인용)

> "최적화에서 나온 위치 속도만으로 제어를 했을 때 실제 토크, 지반력도 최적화와 동일하게 나오도록 하는게 우리의 최종 목표!"
>
> "최적화 점프 높이는 중요하지 않아! 그래도 local minima에 빠진 해라면 그건 안되고 최적화가 수렴할 수 있는 모델, 파라미터를 찾는게 우리의 최종 목표"
>
> "수직 점프만 최적화할 건 아니니까 점프에 특화된 모델, 파라미터로 정하면 안되는거고 현실에 최대한 근접하도록 찾아야 하는거"

### 4가지 의미

| # | 의미 | Metric |
|---|---|---|
| 1 | Forward consistency | 실측 τ, GRF → forward sim → 실측 q와 drift 작음 |
| 2 | NLP convergence | IPOPT 안정 수렴, self-consistency ≈ 0 |
| 3 | Generalization | jump + s2s + payload + 다른 task 모두 OK |
| 4 | Physical realism | cf < 0.8, off < ±0.5, boundary chase < 15% |

---

## ❌ 절대 금지

1. **점프 높이 매칭** — "0.94m"는 잘못된 metric. 실측 토크가 최적화보다 과해서 그렇게 점프한 것이지, 모델 정확성과 무관
2. **점프 특화 fit** — 단일 모델로 모든 trial fit
3. **Inverse RMSE 단독 최저화** — V12 0.93/0.71 같은 over-fit 함정
4. **mom_h polynomial 같은 link length 자유 보정** — over-fit 의심
5. **2-DOF inverse 형태로 분리** — 3-DOF NLP 식 그대로

---

## ✅ 시간 Budget (2026-06-06 12:00 KST까지)

| Phase | Hours | 결과 |
|---|---|---|
| 1: 인프라 + Notion parent | 1h | dynamics_v0.py, drift metric |
| 2: V1 baseline 12p fit | 2h | V1 자식 |
| 3: V2~V5 ablation | 4h | 각 version 자식 |
| 4: V6 NLP integration | 2h | self-consistency 자식 |
| 5: V7 hold-out CV | 2h | 최종 validation 자식 |
| 6+: 자율 진화 (web/논문/코드) | 1-2h | 추가 발견 자식 |

---

## 📊 V0 Baseline Smoke Test (시작점)

**V0 = jump_opt baseline 식 그대로 (12 params, fit 안 함)**

```
params = {
    M_tot: 3.27 kg (CAD)
    A, B, K, I_sig1, I_sig2: CAD 합성값
    l1, l2: 0.25 m
    alpha: 0.85 (단일)
    JF_v1, JF_v2: 0.1 (viscous)
    RAIL_F: 0.0
}
```

### Inverse RMSE (no fit)

| Trial | Hip RMSE | Knee RMSE |
|---|---|---|
| jump_60_0.75_60_2 | 10.06 | 1.19 |
| jump_60_1.5_60_1.5 | 10.93 | 1.29 |
| jump_90_0.75_90_2 | 9.40 | 1.73 |
| jump_120_2_120_2 | 8.72 | 1.30 |
| jump_150_2.2_250_3 | 6.74 | 0.98 |
| jump_150_2.2_500_5 | 5.45 | 3.34 |
| s2s_no_cvt_no_load | 2.58 | 1.09 |
| s2s_cvt_no_load | 4.52 | 9.81 |
| s2s_cvt_load_2.5 | 8.33 | 18.27 |
| s2s_cvt_load_5 | 13.17 | 19.61 |

→ baseline (fit 없이) 점프 hip 5-11 Nm, s2s CVT는 매우 큼 (clutch dynamics 누락 영향).

### Forward drift (T=0.1s, no fit)

| Trial | drift_q1 (rad) | drift_q2 (rad) |
|---|---|---|
| jump_60_0.75_60_2 | 0.293 | 0.508 |
| ... | (~0.3, ~0.5 typical) | |

→ baseline forward 시 100ms 내 hip 17°, knee 29° drift. 완전 부정확. V1 fit 후 큰 감소 예상.

---

## 🗺 Version Timeline

각 version의 자식 페이지가 아래 toggle list에 자동 추가됩니다.

### V0 — Baseline (CAD only, no fit) ✅
- 12 params, jump_opt 식 그대로
- Inverse RMSE: jump hip 5-11, knee 1-3
- Forward drift: ~0.3 rad

### V1 — Baseline fit (12p, Optuna + L-BFGS) ⏳
- Goal: forward drift baseline 확보, inverse RMSE 줄이기

### V2 — + Motor lag (tau_m1, tau_m2)
### V3 — + Coulomb friction (cf1, cf2)
### V4 — + Stribeck friction (F_s, v_s)
### V5 — + Foot radius + kind-GRF + rotor inertia + state-bias
### V6 — NLP integration + self-consistency check
### V7 — Hold-out 6-fold cross-validation + final

---

## 📁 파일 위치

```
NEXT_GOAL_PROMPT.md: C:\Users\junho\Desktop\jump_opt\NEXT_GOAL_PROMPT.md
MASTER_INSIGHTS.md:  C:\Users\junho\Desktop\jump_opt\MASTER_INSIGHTS.md
Baseline code:       C:\Users\junho\Desktop\jump_opt\dynamics_v0.py
Plots/results:       C:\Users\junho\Desktop\jump_opt\goal3\
Notion content:      C:\Users\junho\Desktop\jump_opt\goal3\content_*.md
```

---

## 📈 Goal3 진행률

```
[██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 1: 인프라 + Notion ⏳ (시작)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 2: V1 baseline fit
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 3: V2~V5 ablation
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 4: V6 NLP integration
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 5: V7 hold-out CV
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Phase 6+: 자율 진화
```

**현재 KST**: 2026-06-05 23:10  
**Deadline**: 2026-06-06 12:00 (남은 12.83시간)  
**Update**: 매 phase 종료 시
