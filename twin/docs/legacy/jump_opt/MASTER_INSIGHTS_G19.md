# MASTER_INSIGHTS_G19 — Unified 7-Dataset Mode A Digital Twin (BASE-UP)

**Created**: 2026-07-02 22:00 KST
**Alarm**: 2026-07-03 22:00 KST cron one-shot
**Notion parent**: `391ab81d-2550-81b9-a252-ea9233db7a87` — https://app.notion.com/p/391ab81d255081b9a252ea9233db7a87
**Cron alarm**: `f2752ee6` (0 22 3 7 *) one-shot
**Git branch**: master

---

## 🎯 미션

Base 모델 (CAD only)부터 시작해서 7 dataset × 31 sub-experiment Mode A 통합 fit. 사전 정의 Phase 0-7 axis plan 진행 → 완료 후 자율 확장 (원인 분석 + 서칭 + 새 axis).

## 🚨 사용자 방향 (2026-07-02 22:15 update)

**금지**:
- ❌ **`tau_scale`** 절대 사용 X (사용자 명시)
- ❌ **`motor_tm` (tau LPF)** 사용 X — delay 유발. 노이즈만 줄이는 대안 모색 (예: kalman-like, EMA on measurement)
- ❌ `motor_tm` dataset별 dispersion X — 물리적으로 dataset별로 달라질 이유 없음

**필수**:
- ✅ **로봇 동역학 우선** — 각 부품(thigh, calf, motor_p, motor_c, foot, base)의 **mass + inertia + CoM 거리** 전부 오차 있다고 가정
- ✅ **바닥-로봇 충돌 항상 ON** (thigh/calf contype=1 conaffinity=1)
- ✅ **Notion nested child pages** — 매 Phase child 안에 dataset/cycle별 sub-child (plot + sim 전부)

## 📊 진행 현황 (수정된 Phase plan)

| Phase | Axis | 상태 | Score | Δ | 완료 시각 |
|---|---|---|---|---|---|
| 0 | Pure CAD Base (inherited iter0R) | ✅ | 59,736 | baseline | 2026-07-02 22:15 |
| 1 | **로봇 동역학** (mass + inertia + CoM per part, 7-10D) | ⏳ | — | — | — |
| 2 | joint friction (fv/fc 4D) | ⏳ | — | — | — |
| 3 | motor armature (arm_hip, arm_knee 2D) | ⏳ | — | — | — |
| 4 | contact (solref/imp0 2D) — 바닥충돌 항상 ON | ⏳ | — | — | — |
| 5 | base mass extension (m_base_scale 1D) | ⏳ | — | — | — |
| 6 | q_offset 결정 (제거/date-group/per-trial) | ⏳ | — | — | — |
| 7+ | 자율 확장 (tau noise reduction 대안, Stribeck, backlash, dt, integrator) | ⏳ | — | — | — |

**폐기된 Phase**: 원래 P1 (motor LPF motor_tm) — 사용자 금지

## 🔒 LOCK (변경 금지)

- CAD 위치/치수: L1=L2=0.25m, LC=0.03m, foot 21mm×13mm cylinder (mass/inertia/CoM은 tolerance 인정)
- v14 rendering pipeline (`goal18_CANONICAL/code/`)
- Mode A only
- Pure Paper sgn(v) — GitHub s(v) smoothing 금지
- CSV `kneeCurrentTorquePaper` 사용 X — canonical `tau_real` 유일
- **`tau_scale` 금지** ★
- **`motor_tm` LPF 금지** ★

## 📋 Weights (iter0R 유지)

- Wq=100, Wdq=50, Wt=0, Wh=100 (jump only), Wgrf=0.1, Wpen=50, pen_free=2mm

---

## Phase 0 — Pure CAD Baseline ✅ INHERITED

**Status**: Completed (2026-07-02 22:15 KST, inherited from GOAL18 iter0R)

**Rationale**: GOAL18 iter0R 이미 동일한 Pure CAD 설정으로 31 exp 실행 완료. 물리적으로 재실행해도 동일 결과. 계승하여 시간 절약.

**Params (PURE_BASE, from iter0R)**:
```python
PURE_BASE = dict(
    # Iter0R = Pure GOAL7 Base
    fv_hip=0.001, fv_knee=0.001, fc_hip=0.001, fc_knee=0.001,
    m_base=1.21623,       # M_BASE_CAD
    solref_tc=0.006320,   # SOLREF_TC default (Iter2)
    imp0=0.14301,         # IMP0 default (Iter2)
    m_thigh_scale=1.0, m_calf_scale=1.0,
    arm_knee=0.00490,     # ARM_KNEE_G default
    arm_hip=0.0,          # build_xml_i38 LOCK
    motor_tm=0.0,         # LPF 없음 (직접 τ 입력)
)
```

**Weights (iter0R)**: Wq1=Wq2=100, Wdq1=Wdq2=50, Wh=100 (jump), Wt=0, Wgrf=0.1, Wpen=50

**Score**: **59,736.29** (baseline for all subsequent improvement calculations)

**Best sub-experiment**: `jump_0602/60_1.5_60_1.5` (228.1)
**Worst sub-experiment**: `jump_torque_0422/P100_D3` (5,883.9)

**결과 파일**: `goal19/phase0/pure_base_aggregate.json` (iter0R 계승)

**Notion child page**: (다음 단계 생성)

---

(Phase 1~7 skeleton — 실행 시 append)

## 🔗 관련 문서

- `GOAL19_PROMPT.md` — 미션 spec
- `CANONICAL_LOCK.md` — v14 렌더링 표준
- `MASTER_INSIGHTS_G18.md` — 이전 iter 발견 (참고만)
- Memory: `mode_A_purpose.md`, `ak80_9_torque_calibration.md`
