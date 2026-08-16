---
name: unified-model-26-06-04
description: "26.06.02 점프 + 26.06.04 sit2stand+CVT load 통합 모델 (10 trials, 24 params). 점프 over-torque 원인 = M·ddq inertia."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 통합 dynamics 모델 (jump + sit2stand + CVT load 동시 식별)

**작업 시각**: 2026-06-04 새벽~오전 (GOAL 자율)

## 데이터 (10 trials)
- 26.06.02/position/* (jump, no_cvt, 6 PD configs)
- 26.06.04/no_cvt/no_load (sit2stand baseline)
- 26.06.04/cvt/{no_load, load_2.5, load_5} (sit2stand with CVT + payload)

## CVT TR 처리
- clutch.xlsx의 평균 l_i = 25.247 mm (사용자 권장: 평균으로 정적 계산)
- mechanism: l_2=0.25, l_o=0.03, l_i=0.02525
- 평균 TR ≈ 1.66-1.73 (load 따라 약간 다름)
- τ_joint = τ_motor / J_mean (scalar division, no spike)
- dq_joint = J_mean × dq_motor
- 코드: `unified_loader.cvt_mechanism(qm, l_i, l_2, l_o)` returns (q2, J, TR)

## 점프 over-torque 원인 (사용자 핵심 질문)
**답: M·ddq inertia 항이 점프 high-PD에서 폭증**
- 150_2.2_500_5 hip: τ_inertia peak = **49.8 Nm** (ddq=1740, M11=0.034) → 모터 한계 ±18 압도
- knee: τ_grf(α=1) 25-28 Nm + τ_inertia 1-17 Nm → 합 30+ Nm > 18 → measured saturated
- sit2stand에서는 ddq 작아 τ_inertia 미미 → τ_meas ≈ τ_grf

## 식별 결과 (unified_fit_v5, 24 params, fit MEAN hip 2.71 / knee 2.37 Nm)
- CAD ±30% free:
  - Is1 = 0.044 (CAD +28%)
  - Is2 = 0.0044 (CAD -5%)
  - KV = 0.0032 (CAD +10%)
  - GAV = 1.14 (CAD -16%)
  - GBV = -0.072 (CAD 그대로)
  - L1 = 0.265 (high boundary), L2 = 0.236
- Identification (physical bounds):
  - alpha = 0.81 (GRF effective)
  - jf hip/knee = 0.5/0.36, cf hip/knee = 0.76/0.07
  - off_c hip/knee = 0.21/-0.48
  - off_q1, q2 항 small (±0.5 안)
  - tau_m = 74 ms
- Calibration: grf_scale=0.88, grf_bias=+6.0 N (force plate scale 약간 작음)
- Missing physics: r_foot = 29 mm, ka1 = 0.015, ka2 ≈ 0

## NLP 검증
- v4 NLP (T_st 변수, smooth 0.0001 each): T_st=0.332s, **jump h=0.874m** (실측 0.94, -7%), max τ saturated 18-20, GRF 120N
- v5 NLP self-consistency: **hip 1.0 / knee 0.7 Nm** (목표 <1 달성)
- 사용자 권장: v5 inverse 식별 + v4 NLP forward

## 코드 위치
- `unified_loader.py`: 10 trials 통합 + CVT TR
- `torque_decomposition.py`: τ 항별 분해 plot per folder
- `unified_fit_v5.py`: 24-param BO + L-BFGS
- `nlp_v5_with_check.py`: NLP + inverse self-consistency
- `nlp_unified_v1.py`: NLP smoothness sweep (best h=0.87)
- per-folder static_hip.png/static_knee.png/decomp_hip.png/decomp_knee.png

## How to apply
- Jump optimization: use v4 theta in `nlp_unified_v1.py`, T_st variable, smoothness 0.0001
- System ID: use v5 theta in `unified_fit_v5.predict`
- 새 점프 trial 추가: load_trial + load_all() 사용
- CVT no_load 외 load는 TR mean이 1.66 → 1.73 변함 (작은 차이)

## 한계
- s2s_cvt validation 큰 잔차 (hip 4-12, knee 13-22) — TR 평균 단순화의 한계
- 점프 fit MEAN 2.7 Nm — 목표 1.0 미달 (saturated 영역 weight 0.05 효과)
- NLP forward: state-dep bias 있으면 small trajectory 선호 (v4 사용 권장)

## UPDATE (2026-06-05 새벽 GOAL2)
사용자가 v41 NLP h 매칭 추구는 잘못된 강조라고 정정.
**진짜 목표: inverse-dynamics RMSE (측정 q,dq,ddq → predict τ ≈ 측정)**

### v5 → v9+LBFGS iteration (모델 항 단계적 추가)
| v | params | Fit MEAN hip | Fit MEAN knee | 주요 추가 |
|---|---|---|---|---|
| v5 | 24 | 2.71 | 2.37 | base + state-dep bias (±0.5) |
| v6 | 28 | 2.66 | 1.95 | + mom_k polynomial + Is2 q-dep |
| v7 | 33 | 2.61 | 1.20 | + kind-specific GRF (jump vs s2s) + Stribeck |
| v8 | 36 | 2.39 | 0.95 | + hip cross-coupling (q·ddq, dq·dq) |
| **v8+LBFGS** | 36 | 1.77 | 0.78 | local refine |
| v9 | 38 | 2.28 | 0.90 | + separate tau_m, Iq1·cos(2q1), sat=0 strict |
| **v9+LBFGS** | 38 | **1.69** | **0.71** | local refine ← BEST |

**v9+LBFGS 권장. theta: unified_fit_v9_refine/theta.npz**

**핵심 발견 (사용자 비판 → 모델 개선 매핑)**:
1. mom_k가 자세에 따라 부정확 → polynomial expansion (dL2_c12, mom_s12_extra, dmom_off)
2. s2s에서 GRF coupling 다름 → kind-specific (grf_scale_jump≈1.0 vs grf_scale_s2s≈0.7)
3. 저속 영역 friction 부족 → Stribeck (F_s, v_s)
4. Hip rotor inertia, knee inertia q-의존 (ka1, ka2, Iq2_c2)

### Knee 목표 < 1.0 Nm 달성 ✓
- jump_120_2: knee RMSE 0.42 Nm
- jump_150_500_5: 1.48 Nm (high PD, 한계 근접)
- s2s_no_cvt: 1.64 Nm

### Hip 잔차 2.39 Nm (목표 미달)
원인: saturated 영역 + 트라젝토리 의존 ddq 영향
v9에서 strict sat=0 + separate tau_m으로 시도 중

### 사용자 인사이트
- NLP의 jump h 매칭 추구는 잘못 (실 로봇은 saturate된 채로 더 많은 토크 써서 점프함)
- inverse-dynamics RMSE가 진짜 평가 지표
- 모델 구조 자체 개선해야 (단순 fit으로 잔차 줄이지 말고 physically grounded 항)

연관: [[ak80_9_torque_calibration]] [[digital_twin_priority]] [[high_pd_outlier_150_500_5]]
