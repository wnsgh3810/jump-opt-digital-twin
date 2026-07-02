# Phase 0 — Pure CAD Baseline (계승)

!!! success "완료 (계승)"
    GOAL18 iter0R가 이미 동일한 Pure CAD 설정으로 31 exp 실행 완료. 물리적 동일해서 계승. **Score = 59,736.29** (모든 후속 개선율의 기준).

## 🔑 Params

```python
PURE_BASE = dict(
    fv_hip=0.001, fv_knee=0.001, fc_hip=0.001, fc_knee=0.001,
    m_base=1.21623,       # M_BASE_CAD
    solref_tc=0.006320,   # Iter2 default
    imp0=0.14301,         # Iter2 default
    m_thigh_scale=1.0, m_calf_scale=1.0,
    arm_knee=0.00490,     # ARM_KNEE_G default
    arm_hip=0.0,          # LOCK
    motor_tm=0.0,         # ❌ LPF 없음
)
# tau_scale=1.0 (사용자 금지)
```

## 📊 Weights (iter0R)

| Weight | Value |
|---|---|
| Wq1, Wq2 | 100 |
| Wdq1, Wdq2 | 50 |
| Wh (jump only) | 100 |
| Wt1, Wt2 | 0 |
| Wgrf | 0.1 |
| Wpen | 50 |
| pen_free_mm | 2.0 |

## 📈 결과

- **Total score**: **59,736.29**
- **Best sub**: `jump_0602/60_1.5_60_1.5` (228.1)
- **Worst sub**: `jump_torque_0422/P100_D3` (5,883.9)

### 데이터셋별 요약

*(자율 loop 진행 중 채워질 예정)*

## 🔍 개선 원인 후보

- **W_pen**: pen_max > 2mm 여러 sub → Phase 4 contact tuning 필요
- **rmse_dq 높음**: high-PD trial 재현 어려움 → Phase 1 dynamics + Phase 3 armature
- **h_gap 큼**: sim h 실측보다 작음 → Phase 1 dynamics (mass/CoM) + Phase 4 contact

## 📁 원본 데이터

- `code/goal19/phase0/pure_base_aggregate.json` — iter0R 상세

## 🔗 다음

[Phase 1 — 로봇 동역학](../phase_1/index.md) (진행 중)
