---
name: 26-06-02-position-data-final-model
description: 26.06.02 position 데이터 기반 정확한 robot 모델 식별 최종 결과 — sit2stand vs jump 분리 분석, CAD 검증, RMSE 0.25 (s2s) / 1.7-2.9 (jump)
metadata:
  type: project
  originSessionId: jump-model-2026-06-03
---

# 26.06.02 Position Data Model Identification — 최종 (v15 BREAKTHROUGH)

## 핵심 결론

**v14/v15에서 motor 1st-order lag (τ_m ≈ 26ms) 추가가 핵심**.
이를 통해 jump LOO hip 1.45 / knee 1.16 Nm 도달 — 거의 목표 < 1.5 달성.
Sit2stand도 RMSE 0.12/0.13 (이전 0.25에서 개선).

AK80-9 driver internal control loop response time ~25ms이 unmodeled 였음.
이게 jump high-acceleration 시 측정 τ와 dynamics 사이 systematic mismatch의 주된 원인.

## 통합 모델 (CAD 고정, task-specific corrections)

### CAD parameters (검증됨)
- Is1 = 0.034471 (hip+knee composite inertia)
- Is2 = 0.004572 (knee composite inertia)
- Kv = 0.002891 (Coriolis coupling)
- gAv = 1.3588 N·m (hip gravity coefficient)
- gBv = -0.0715 N·m (knee gravity coefficient)

### Sit2stand task (GRF=0, 공중 매달림)
- Params: alpha=irrelevant, jf1=jf2=0, **off1=-0.682, off2=-0.136**
- Mean RMSE: **hip 0.256, knee 0.248 Nm** ✓
- Bias 해석: 모터 currentTorque sensor calibration offset (작음)

### Jump task (5 folders, no_cvt, GRF lag -4ms global)
- v10 model: CAD + alpha=0.60-0.85 + jf + bz·dz_body + mz·ddz_body + off
- LOO RMSE: **hip 2.91, knee 1.67 Nm**
- off1≈-3.3, off2≈-2.6 (sit2stand off보다 큼 → jump-specific term이 흡수)
- bz1≈-1.07 (rail-velocity coupling — body z velocity 의존)

## 시도 history (v2~v12)

| 버전 | 변경 | Jump RMSE (hip/knee) | 노트 |
|------|------|---------------------|------|
| v2 | constrained LS + foot circle | 3.3 / 2.5 | bounds saturate |
| v3 | spline smoothing | 6.5 / 3.4 | over-smoothed |
| v4 | quasi-static | 4.0 / 3.7 | ddq 노이즈 not the issue |
| v5 | CAD fixed + 5 corrections | 4.0 / 2.7 | alpha=0.73 stable |
| v6 | + Coulomb friction | 2.6 / 2.2 | best basic model |
| v7 | + GRF scale/offset | 2.6 / 2.2 | degenerate w/ alpha |
| v8 | combined s2s + jump | s2s 0.25!, jump 2.8 | **breakthrough** |
| v10 | + bz·dz_body + mz·ddz_body | 2.44 / 1.68 | best for knee |
| v11 | s2s off fixed | 2.93 / 3.07 | cf forced unphysical |
| v12 | + GRF timing lag | 2.43 / 1.57 | -4ms lag found |
| final | LOO with v10 + lag | 2.91 / 1.67 | generalization |

## 핵심 진단 발견

1. **잔차 ~ dz_body 강한 음의 상관 (-0.4 ~ -0.9)** → rail-velocity coupling 필요 (bz term)
2. **잔차 mean ~ -3 ~ -5 Nm in jump** → systematic offset (motor PD loop dynamics 의심)
3. **150_2.2_500_5 항상 outlier** → 극단적 PD gain (500) unmodeled driver dynamics
4. **60_*_60_* 시리즈는 우수 (knee < 1.5)** → 낮은 PD gain은 모델과 잘 맞음
5. **GRF 측정 lag -4ms** (작지만 의미 있음)

## 한계

- Hip jump RMSE plateau 2-3 Nm = 현재 데이터/모델 한계
- 가능한 원인 (해결 안 됨):
  - Motor PD loop transport delay (~5-10ms) — only GRF lag로 부분 보정
  - Serial elasticity (belt/gear) — 고가속 시 영향
  - Foot circle rolling contact의 시간 변화 — point 가정 한계
  - Sensor cross-coupling at high accel

## 파일 위치

- 메인 스크립트: `Data/26.06.02/position/model_search_v*.py` (v2~v12, final)
- 최종 결과: `Data/26.06.02/position/final_model/final_report.md`
- LOO CSV: `Data/26.06.02/position/final_model/loo.csv`
- Params npz: `Data/26.06.02/position/final_model/final_theta.npz`
- 진단: `Data/26.06.02/position/diagnose_signals.py`, `model_search_v9_apply_s2s/residual_correlations.csv`

## 다음 가능한 작업 (만약 더 개선 시도 시)

1. Motor PD loop dynamics 명시적 모델링 (transport delay + 1차 시상수)
2. Serial elasticity (joint compliance) 추가
3. Optuna BO + wider param space (예: 50K trials)
4. Hunt-Crossley contact model (smooth contact)
5. 더 많은 jump 데이터 (다양한 점프 조건) 수집

## v17~v24 추가 작업 (2026-06-04) — RMSE < 0.8 목표 달성

**핵심 추가 발견**:
- **Knee torque 43-62% saturated** (currentTorque raw ±35Nm, motor 한계 ±18)
- **Trajectory 자체가 motor 한계 초과** (peak ddq_des 7291 rad/s²)
- **모든 6 folder 동일 trajectory**, 다른 PD gain만

**v17 (soft sat in prediction)**: 실패 — model이 잘못된 형태
**v18 (weighted LS, sat 0.05 weight)**: knee unsat 0.86, hip 1.43
**v19 (clip + hip cross-coupling)**: LOO hip 0.90 / knee 0.66 ← target 거의
**v20b (CasADi NLP with motor lag state)**: CONVERGED. **jump h 0.948m (실측 0.94m 일치)** ✓
**v22 (random restart × 20)**: LOO hip 0.59 / knee 0.43 ← target 달성
**v24 (Optuna BO 500 trials + L-BFGS)**: **LOO hip 0.48 / knee 0.36** ← 최고

**v24 LOO 결과 (5 folders, 150_500 outlier 제외)**:
- 60_0.75: hip 0.40 / knee 0.38
- 60_1.5: hip 0.54 / knee 0.29
- 90_0.75: hip 0.27 / knee 0.25
- 120_2: hip 0.27 / knee 0.48
- 150_2.2_250: hip 0.93 / knee 0.38
- MEAN: hip 0.48 / knee 0.36 ✓✓ (목표 0.8 절반 미만)
- 4/5 folder는 둘 다 < 0.5 Nm

**최종 모델 (v24, 18 free params, jump fit)**:
- alpha = 0.36, jf1 = 1.59, jf2 = 0.92
- cf1 ≈ 0, cf2 ≈ 0
- bz1 = 0.79, bz2 = -7.46
- mz1 = 0.02, mz2 = 0.04
- off1: 9.54 - 5.72·q1 + 5.12·q2
- off2: 1.98 - 5.19·q1 + 1.89·q2
- hx1 = 0.017, hx2 = -0.020
- tau_m = 80 ms (motor 1차 지연)

**NLP 적용 가능 — v20b 검증**: CAD + alpha + jf + motor lag 단순 모델로
NLP 수렴, 점프 높이 0.948m 실측 일치. 더 복잡한 v22-v24 모델은 NLP 수렴 어려움 — 
forward simulation은 inverse identification으로 검증 (RMSE < 0.5).

## 사용자 목표 달성도 (2026-06-04 update)

**v15 (final 1) 기준**:
- **목표 RMSE < 1.0 Nm**:
  - Sit2stand 달성 ✓ (hip 0.12, knee 0.13)
  - Jump LOO hip 1.45 / knee 1.16 — 거의 목표
  - 일부 jump folder는 < 1.0 (60_0.75_60_2: hip 1.04, knee 0.84; 90_0.75: hip 0.86, knee 0.77)
- **6-조건 cross-val 일관성**: 5/6 일관 (150_2.2_500_5 outlier 제외)
- **Sit2stand + jump 통합 단일 모델**: 16-param 모델 (CAD + corrections + motor lag) 두 task 모두 적용 가능

## v15 최종 파라미터

CAD-fixed dynamics + 16 free correction params (jump):
- alpha = 0.60 (contact effective ratio)
- jf1 = 1.00, jf2 = 0.39 (viscous friction)
- cf1 = 0.97, cf2 = 0.00 (Coulomb)
- bz1 = +0.25, bz2 = -1.07 (rail velocity coupling)
- mz1 = +0.06, mz2 = -0.01 (rail accel coupling)
- off1 = state-dep (c=4.44, q1=-3, q2=+3), off2 = state-dep
- **tau_m = 26.2 ms (motor 1st-order lag)**

## v14/v15 발견 — Motor lag가 핵심

진단:
- v10-v13까지 jump hip RMSE 2.4-3.0 Nm plateau
- v14에서 motor τ_m 추가 → hip 0.79-1.80 (folder별), 평균 1.14
- LOO 일반화에서도 hip 1.45 (이전 2.91 대비 50% 개선)

물리 해석: AK80-9 driver는 CAN bus + internal current control loop를 가짐.
명령 토크(controller가 보낸 값)와 실제 motor 출력 사이에 1차 지연 (~25ms)이
있음. Jump 고속/고가속 영역에서 이게 systematic error 만듦. 
Sit2stand는 저속이라 영향 작았으나 추가 시 RMSE 50% 추가 개선.
