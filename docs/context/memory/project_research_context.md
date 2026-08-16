---
name: 2DOF Single-Leg Jump Robot Research Context
description: 전체 연구 배경 — 4-bar link CVT 로봇의 2자유도 점프 최적화 및 실험, Sim-to-Real Gap 분석, 코드 구조 상세
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
## 연구 개요

**목표**: 2자유도(Hip + Knee) single-legged robot의 최대 점프 높이 최적화 궤적 생성 → 실제 로봇 적용 → Sim-to-Real Gap 제거

**Why:** 4-Bar Link CVT(Continuously Variable Transmission) 메커니즘 탑재 단족 로봇. `Jump_No_Tr`은 CVT(Transmission) 없이 수행한 점프 실험 데이터.

---

## 코드 위치 및 구조

### 1. `C:\Users\junho\CVT\AVT LEG\utils\session_backup\recovered_files\2DOF Leg Jumping Optimization.py` (648줄)
- 이전 Claude가 작성한 코드
- CasADi IPOPT, Direct Collocation (사다리꼴 적분법), N=60 노드
- 3가지 Contact Model 선택: `'hard'` | `'alpha'` | `'soft'` (현재 `CONTACT_MODEL = 'soft'`)
- 결정변수: X=[z,θ1,θ2], V=[dz,dθ1,dθ2], U_tau=[τ1,τ2], U_grf
  - hard/alpha: U_grf=[Fx,Fz] 자유
  - soft: U_grf_x=[Fx]만 자유, Fz는 Kelvin-Voigt (k_c*delta + b_c*delta_dot)
- 목적함수: `-2000*h_base_via_com + 0.03*J_smooth`
- 현재 파라미터: K_C=5665, B_C=62.2, ALPHA=0.714
- 토크 한계: ±15 Nm, 속도 한계: ±50 rad/s
- T-N curve: speed = -0.731019*|τ| + 48.476878
- 스탠스 시간 T_st: 0.05~0.3s 범위
- 출력: 5개 Figure (Kinematics&Dynamics, Stick Figure, Energy&GRF, Contact Dynamics, GRF Decomposition)

### 2. `C:\Users\junho\CVT\AVT LEG\sys_id\Identify_Contact_Params.py` (447줄)
- 이전 Claude가 작성한 코드
- 역방향 EOM 분석으로 soft contact 파라미터 식별
- 핵심 방법: ddz_kin(운동학) vs ddz_true(GRF 기반) 차이 → delta(침투깊이) → 선형회귀
- 4-parameter regression: GRF = k_c*D_base - b_c*V_base + C0 + C1*t
- 3개 폴더 모두 분석, 비교 시각화 포함

### 로봇 파라미터 (양쪽 코드 공통)
- M=1.02 kg (body), m1=1.05213 kg, m2=0.237 kg
- m_c=0.80898, m_p=0.14977, l1=l2=0.25 m
- M_tot = M + m1 + m2 + m_c + m_p = 약 3.27 kg (코드 내)
- 참고: 실제 로봇 전체 질량 M_actual = 3.40 kg (레일 캐리지 0.64 kg 포함)

---

## 실험 데이터 (`Jump_No_Tr` 폴더)

### 실험 흐름
1. 최적화 코드로 최적 궤적(q1, q2 reference) 생성
2. 실제 로봇에 위치 reference 값 전송
3. AK80-9 모터의 PD 위치 제어로 점프 실행 (P/D는 모터 드라이버 내부 설정값)
4. 실험 데이터 수집: 관절 각도/속도/토크 + 로드셀 GRF

### 폴더 구조 (3가지 PD 게인 설정)
- `P40_D0.7/` → P_drv=40, D_drv=0.7 ← **가장 좋은 점프 성능** (0.861 m)
- `P60_D1.5/` → P_drv=60, D_drv=1.5 (0.826 m)
- `P100_D3/`  → P_drv=100, D_drv=3 (0.769 m)

### 데이터 파일 구조 (각 폴더 공통)
- **hip.xlsx / knee.xlsx**: Time, currentAngle, desiredAngle, currentAngleVelocity, desiredAngleVelocity, currentTorque, desiredTorque
- **GRF.xlsx**: Time, Current_GRF, Desired_GRF
- **Real Data.txt**: 요약 결과 (GRF impulse, 에너지, 점프 높이 등)
- **기타**: .fig(MATLAB), .png(그래프), .mp4(실험 영상)
- 샘플링: 2ms 간격, 약 157~161 데이터포인트 (약 0.31~0.32초 스탠스)

### 데이터 범위 (P40_D0.7 기준)
- Hip angle: current [-1.38, -0.29] rad, desired [-1.15, -0.30] rad
- Knee angle: current [-2.67, -0.52] rad, desired [-2.53, -0.85] rad
- GRF: Current [~0, 109.94] N, Desired [0, 83.57] N
- **Desired GRF는 3개 폴더 동일** → 같은 최적 궤적 사용, PD게인만 다름

### 실험 결과 수치

| 실험 | 스탠스 시간 | GRF Impulse 실제 | GRF Impulse 목표 | 총 에너지 실제 | 점프 높이 |
|------|------------|-----------------|-----------------|--------------|----------|
| P40_D0.7 | 0.320 s | 20.35 N·s | 14.48 N·s | 36.91 J | 0.861 m |
| P60_D1.5 | 0.312 s | 19.17 N·s | 14.48 N·s | 33.63 J | 0.826 m |
| P100_D3  | 0.314 s | 18.26 N·s | 14.45 N·s | 33.23 J | 0.769 m |

목표(Desired) 에너지: Hip 4.59 J + Knee 13.63 J = 18.22 J (3가지 공통)

**핵심 관찰**: 
- 낮은 PD 게인(P40) → 실제 GRF가 더 크고 점프 더 높음 (추적 오차가 오히려 이득)
- 실제 에너지가 목표 대비 ~2배 → Sim-to-Real Gap의 핵심

---

## Sim-to-Real Gap 분석

| 실험 | GRF 비율(real/sim) | Energy 비율(real/sim) | GRF² 비율 |
|------|----|----|---|
| P40_D0.7 | 1.405 | 2.026 | 1.975 ← Energy 비율과 거의 일치 |
| P60_D1.5 | 1.324 | 1.846 | 1.753 |
| P100_D3  | 1.263 | 1.824 | 1.595 |

**핵심 발견**: Energy ratio ≈ GRF ratio² → Spring contact 모델이 물리적으로 적합

**물리적 해석**:
- Hard contact: GRF가 즉시 100% 몸통에 전달 가정
- 실제: 접촉 컴플라이언스(스프링)가 GRF를 증폭, 에너지 저장 (E ∝ F²/k)
- 이륙 시 spring release → 추가 속도 부여

### 식별 결과 (2026-04-14, P40_D0.7 기준)
- K_C = 5665 N/m, B_C = 62.2 N·s/m (R² = 0.845)
- delta_max ≈ 16 mm, delta_static ≈ 5.9 mm
- 이륙 시 spring release 속도: delta_dot_T = -1.49 m/s
- 운동학적 v_com @ liftoff = 1.31 m/s vs 실제 2.72 m/s → 차이 1.41 m/s = spring release

### Soft Contact 모델 물리
- `delta = -(z + l1*sin(q1) + l2*sin(q1+q2))`: 발끝 침투 깊이
- `GRF_z = k_c * delta + b_c * delta_dot` (Kelvin-Voigt)
- 초기조건: 정적 평형 침투 = M_tot*g / k_c
- 종료조건: GRF_z[-1] = 0 (이륙)
