---
name: Sim-to-Real Gap Analysis Findings
description: 2026-04-19 종합 분석 결과 — 접촉 컴플라이언스, 에너지/임펄스 비율, 토크 효율, alpha, 최적화 방향
type: project
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
## 실측 점프 높이 (사용자 직접 측정)
- P40_D0.7: 0.78 m
- P60_D1.5: 0.76 m
- P100_D3: 0.73 m
- (Real Data.txt의 "Estimated" 값 0.86/0.83/0.77과 다름 — 그건 운동학 추정값)

## 실측 질량
- M_real = 3.04 kg (사용자 확인)
- M_model = 3.268 kg (코드 파라미터 합산)
- M_grf (정지 GRF/g) = 2.99~3.10 kg (로드셀 기반)

## 핵심 발견

### 1. E_ratio ≈ (Impulse ratio)²
- P40: E=2.03, (Imp)²=1.97, E/(Imp)²=1.03
- P60: E=1.86, (Imp)²=1.75, E/(Imp)²=1.06
- P100: E=1.83, (Imp)²=1.58, E/(Imp)²=1.16
- **Why:** 접촉 스프링 에너지 E=F²/(2k), GRF가 1/α배면 E는 (1/α)²배

### 2. Alpha (Impulse 비율 역수)
- P40: α=0.712, P60: α=0.755, P100: α=0.789
- **α=0.712로 P40 impulse 예측 오차 0.1%**
- trial마다 다름: 동작이 격렬할수록 α 낮음

### 3. Knee 토크 적분 ~1.9배
- 관절 속도는 desired와 거의 동일 (dq2 peak: ~25 rad/s)
- 그런데 Knee ∫|τ|dt는 desired 대비 1.85~1.91배
- **같은 속도에 ~2배 토크가 필요한 이유: GRF 반력이 더 크므로**

### 4. Hard contact impulse ≈ measured impulse
- Hard inv-dyn GRF impulse / measured impulse = 0.97 (3% 이내)
- 순간 GRF는 진동(peak 243N vs 실측 86N)이지만 적분은 일치
- 접촉 스프링이 "로우패스 필터" 역할: 순간 힘은 낮추지만 적분(impulse)은 유지

### 5. Gap의 근본 원인
- Hard contact: GRF는 "공짜" 구속력 (발끝 고정, 일 안 함)
- Soft contact: GRF는 "실제 힘" (발끝 움직임, 일을 함)
- **같은 관절 궤적 + soft contact → 더 큰 GRF 반력 → Knee가 더 많은 일 필요**
- 이것이 동역학 수준에서의 설명

### 6. 최적화 코드 탐색 결과 (param_sweep 4차)
- 어떤 단일 파라미터 조합도 h + Impulse + Energy를 동시에 완벽히 매칭 못함
- 이유: 최적화는 "최적 궤적"을 찾지만, 실제는 "9Nm 계획 궤적을 PD 추적"
- 가장 가까운 설정: Soft H14K18 rf20 jf0.2 (h=0.79m, dq2=27.9)

## 최종 최적 파라미터 (945개 sweep, 2026-04-19)
- **Contact**: Soft + Alpha (soft_alpha)
- **alpha = 0.90**, k_c = 5000 N/m, b_c = 50 N·s/m
- **tau_lim = 15 Nm**
- **rail_friction = 5 N·s/m, joint_friction = 0.3 Nm·s/rad**
- vs Real P40: dq2 0.4%, Impulse 1.2%, Energy 1.9%, h 0.9%, E/(Imp)²=1.023
- Score = 4/945 (best)
- 코드: `C:\Users\junho\CVT\AVT LEG\optimization\final.py`

## Alpha별 경향 (0.70~1.0 sweep)
- α=0.70~0.80: E/(Imp)² < 0.8 → 물리적으로 부적합
- α=0.85: E/(Imp)²=0.899, score=26
- **α=0.90: E/(Imp)²=1.023, score=4 ← 최적**
- α=0.95: E/(Imp)²=1.003, score=10
- α=1.00: E/(Imp)²=1.108, score=14
