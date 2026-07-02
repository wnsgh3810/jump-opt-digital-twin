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
| 0 | **Pure CAD Base (unified 31 exp, real)** | ✅ | **41,271.18** | baseline | 2026-07-02 (Phase 0 complete) |
| 1 | **로봇 동역학** (mass + inertia + CoM per part, 15D+) | ⏳ | — | — | — |
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

## Phase 0 — Pure CAD Baseline ✅ COMPLETE

**Status**: Completed (2026-07-02, freshly run in Documents/jump-opt-digital-twin repo)

**Params (PURE_BASE)**:
```python
PURE_BASE = dict(
    fv_hip=0.001, fv_knee=0.001, fc_hip=0.001, fc_knee=0.001,
    m_base_scale=1.0,      # CAD (M_BASE_CAD = 1.21623 unmodified)
    solref_tc=0.006320, imp0=0.14301,
    m_thigh_scale=1.0, m_calf_scale=1.0, m_p_scale=1.0, m_c_scale=1.0,
    m_foot_extra=0.0,      # Pure CAD (iter5 had 0.60)
    arm_knee=0.00490, arm_hip=0.0,
    motor_tm=0.0,          # LPF forbidden
)
```

**Weights**: Wq=100, Wdq=50, Wh_jump=100, Wt=0, Wgrf=0.1, Wpen=50

**Score total**: **41,271.18** (unified 31 exp) — baseline for all subsequent Δ%.

**Aggregates**:
- Sit2stand mean: 2,969.74 (7 subs)
- Jump mean: 837.63 (24 subs)

**Best sub**: `jump_0424/90_0.75_90_2` (338.85)
**Worst sub**: `sit2stand_gnd_0319/ROOT` (10,262.53 = 25% of total; 39mm foot penetration, rmse_q2=46 rad)

**Key observations for Phase 1**:
1. **sit2stand_gnd_0319** — worst offender. Contact + base fixed model needs work. Priority.
2. **Jump heights systematically LOW** (h_sim 0.61m mean vs h_real 0.83m mean) — mass/inertia calibration expected fix.
3. **High-PD subs (150_2.2_500, 120_2_120_2, P100_D3)** — 7-29mm penetration. Contact / inertia coupling.
4. **jump_position_0421 P70/P90 excellent** (rmse_q1 < 0.15) — position PD already tracks well.

**Files**:
- Runner: `code/goal19/phase0/run_pure_base_31exp.py`
- Result JSON: `code/goal19/phase0/pure_base_31exp_result.json`
- Docs: `docs/phase_0/index.md`

---

(Phase 1~7 skeleton — 실행 시 append)

## 🔗 관련 문서

- `GOAL19_PROMPT.md` — 미션 spec
- `CANONICAL_LOCK.md` — v14 렌더링 표준
- `MASTER_INSIGHTS_G18.md` — 이전 iter 발견 (참고만)
- Memory: `mode_A_purpose.md`, `ak80_9_torque_calibration.md`
