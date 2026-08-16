# GOAL15 Starting Prompt

**미션**: Iter28 베이스 위에서 fresh axis를 탐색하여 디지털 트윈 정밀도를 추가로 개선한다.

---

## 배경 (GOAL14 요약)

- **공식 best**: Iter28 score=89.847 (Step 0 109.14 대비 -17.65%)
- **KEEP chain**: Step 0 → Iter15(95.40) → Iter17(91.43) → Iter18(90.66) → Iter28(89.85)
- **9-trial 환경**: 0424 계열(4) + 0602 계열(5) = 총 9개 PD jump trial

### GOAL14 핵심 교훈

1. **mass scale이 가장 강한 신호**: m_calf_scale 하한 0.4에서 3개 trial 경계 도달 → 실제 calf 질량이 CAD 대비 60% 이하. GOAL12 발견(7.9% over) 9-trial에서 재확인.
2. **per-trial 독립 NM이 유일 효과적 구조**: Global optimizer (DE/CMA-ES/SHGO) 전부 DROP. Global Alternating NM(Iter23) 발산 255.88.
3. **8-axis contact 모델 포화**: solimp shape / solref_d / imp1 / arm_hip 모두 DROP.
4. **tight mass bounds 금지**: Iter19 (m_calf[0.80,1.10]) → score 221.26 재앙. m_calf_scale [0.4, 1.1] 유지.
5. **W_GRF=0.3 유지**: GRF 중요도 낮춰 q/dq/τ/h_jump 1순위 매칭.

---

## GOAL15 목표

**한 줄 미션**: Iter28 best params 위에서, GOAL14에서 탐색하지 않은 fresh axis로 디지털 트윈 q/dq/τ 매칭을 추가 개선한다.

---

## 탐색 후보 축 (priority 순)

| Priority | 축 | 물리 의미 | GOAL14 탐색? | 예상 효과 |
|----------|-----|---------|------------|---------|
| 1 | per-PD αkp/αkd scaling (trial별 gain 보정) | firmware PD가 trial별 실제 gain 다를 수 있음 | 미탐색 | dq 매칭 개선 |
| 2 | kinematic 보정 (l_thigh/l_calf offset, mm 단위) | CAD vs 실 robot 링크 길이 오차 | 미탐색 | q1/q2 RMSE 개선 |
| 3 | foot rolling friction (μ_roll, cylinder model) | 발이 실제로 원통형에 가까움 | 미탐색 | GRF 파형 개선 |
| 4 | per-trial m_base 분리 (0424 그룹 vs 0602 그룹) | 두 날짜 계열 페이로드 다를 수 있음 | 부분 탐색 | 체계적 bias 제거 |
| 5 | mcs 하한 [0.3, 1.1]으로 추가 확장 | Iter28에서 3개 trial 0.4 경계 도달 | bounds 확장 | 기존 best 미세 개선 |

---

## 8 strict 규칙 (GOAL14~에서 유지)

1. **Mode A LOCK**: paper a_hat formula (sgn(v) only), GitHub s(v) smoothing 금지. actual tau injection.
2. **W_GRF=0.3** 고정 (W_Q=100, W_DQ=3, W_T=20, W_H=50, W_PEN=10)
3. **per-trial 독립 NM** 구조 유지 (global optimizer 금지)
4. **m_calf_scale 하한 0.4 이상** (0.3으로 확장할 경우 사용자 확인 필수)
5. **KEEP 기준 -3%**: 89.847 × 0.97 = **87.15** threshold
6. **mass scale alpha/fb/M_tot** 사용자 물리적 결정 고정값 유지
7. **Pure Paper a_hat** (sgn(v) only): CF 식별성 유지
8. **Notion 페이지** KEEP/DROP 모두 생성 (이미지 업로드 포함)

---

## 시작 방법

### 즉시 읽을 파일

1. `MASTER_INSIGHTS_G9.md` 끝 ~2000 lines (§20 + Final Conclusion)
2. `goal14/iter28/iter28_metrics.json` (official best params)
3. `goal14/step0_baseline/` (baseline XML + metrics)
4. `goal14/iter29/`, `iter30/` (완료 여부 확인)

### Step 0: Iter29/Iter30 결과 처리

- iter29: 실행 중(3/9 trials 완료 시점). 완료 후 score 확인 → threshold 87.15
- iter30: prep 완료 대기 중. iter29 결과 보고 실행 여부 결정
- KEEP이면: new best 갱신, Notion 업로드, commit
- DROP이면: GOAL15 fresh axis 탐색 시작

### Step 1: Iter31 (per-PD αkp scaling, Priority 1)

```python
# per-trial 9D NM (Iter28 best 기반) + αkp_scale [0.8, 1.2] 추가 → 10D
# αkp_scale: 실제 kp = kp_nominal × αkp_scale (trial별 독립)
# Iter28 params warm start
```

- 근거: firmware PD 실제 gain이 설정값과 다를 수 있음. GOAL6에서 α_kp=0.19 발견과 연결.
- 탐색 범위: αkp_scale [0.7, 1.3], αkd_scale [0.7, 1.3]

### Step 2: Iter32 (kinematic l_thigh/l_calf offset, Priority 2)

```python
# per-trial NM + Δl_thigh [mm] + Δl_calf [mm]
# 링크 길이 오차: CAD vs 실 robot
# Iter28 params warm start
```

---

## GOAL12-14 lessons (fresh axis 선택 근거)

| Goal | 핵심 교훈 | GOAL15 적용 |
|------|---------|------------|
| GOAL12 | m_calf 7.9% over (CAD vs real) | mass scale 우선순위 유지 |
| GOAL13 | 8-axis 탐색 포화, W_GRF=0.3 도입 | 새 weight scheme 고정 |
| GOAL14 | per-trial NM 유일 효과적 구조, contact 포화 | fresh axis는 kinematics/PD 방향 |

---

## 사용자 결정 필요 항목

1. **실 robot calf 실측** (강력 권장): m_calf_scale 0.4 하한이 물리적으로 의미 없어질 수 있음. 실측값으로 calf 질량 고정하면 자유도 1개 절약.
2. **mcs 하한 추가 확장** ([0.3, 1.1]): Iter28에서 0.4 경계 3개 trial 도달. 더 낮출지 사용자 판단.
3. **per-PD αkp/αkd** 우선순위: GOAL6 α_kp=0.19 발견과 연결되는 축. 사용자가 firmware gain 정보 보유 여부 확인.

---

## 참조 파일

| 파일 | 역할 |
|------|------|
| `goal14/iter28/iter28_metrics.json` | 공식 best params (per-trial 9D 결과) |
| `goal14/iter28/leg_g14_i28_best.xml` | Iter28 베이스 XML |
| `goal14/step0_baseline/` | Step 0 기준 (score=109.14) |
| `MASTER_INSIGHTS_G9.md §20` | GOAL14 전체 iter 기록 |
| `MASTER_INSIGHTS_G9.md § Final Conclusion` | GOAL14 요약 및 Action items |

---

*GOAL15 시작 전 MASTER_INSIGHTS_G9.md §20 + Final Conclusion 전체 읽기 필수.*
*Mode A LOCK + 8 strict 규칙 반드시 확인.*
