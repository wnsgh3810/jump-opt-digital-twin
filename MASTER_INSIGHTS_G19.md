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
| 1 | **로봇 동역학** (15D CMA-ES → drop-test) | ✅ | **20,367.75** | **−50.6%** | 2026-07-03 (full-15D best) |
| 2 | **joint friction** (fv/fc 4D CMA-ES) | ✅ | **15,744.40** | **−22.7%** (누적 −61.9%) | 2026-07-03 |
| 3 | Stribeck friction (저속 고마찰/고속 저마찰) — 저-gain 점프 회복 | ⏳ | — | — | — |
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

## Phase 1 — 로봇 동역학 ✅ (15D CMA-ES → drop-test)

**Status**: Complete (2026-07-03). Score **20,367.75** (−50.6% vs Phase 0).

**Method**: 15D CMA-ES (pop=12, 408 eval, 34 gen), then drop-test (3% threshold), then 5-KEEP refine (진행/완료).

**Full 15D best_x**:
```
M_base_s=1.152 M_thigh_s=0.949 M_calf_s=0.906 M_p_s=1.411 M_c_s=0.944
M_foot_ex=0.263 I_thigh_s=1.181 I_calf_s=1.325 I_p_s=1.042 I_c_s=1.073
com_dz_thigh=-0.005 com_dx_thigh=0.001 com_dz_calf=-0.018 com_dx_calf=-0.010 arm_knee=0.020
```

**★ Drop-test → 5 KEEP / 10 DROP**:
| KEEP | Δ% | DROP | Δ% |
|---|---|---|---|
| M_foot_ex | +24.9% | I_thigh_s | +2.3% |
| arm_knee | +21.3% | I_calf_s | +1.9% |
| M_base_s | +8.8% | com_dz_thigh | +1.4% |
| com_dz_calf | +8.4% | M_thigh_s | +1.0% |
| M_p_s | +5.6% | (외 6개 모두 <1%) | |

**핵심 발견**:
1. **Foot mass (M_foot_ex=263g) 최대 인자** (+24.9%). CAD 누락 foot 하드웨어. Jump h 재현 핵심.
2. **arm_knee (knee 반사관성) 2번째** (+21.3%). CVT+knee 모터 rotor inertia가 link inertia 지배.
3. **Link inertia scale (I_*) 전부 DROP.** armature가 회전 동역학 이미 흡수 → link I 무의미. → **Phase 3 armature를 이미 여기서 흡수. 별도 armature phase 불필요할 수 있음.**
4. **calf CoM −18mm** 유의미 (+8.4%).
5. **Boundary chasing**: M_foot_ex(0.30), M_p_s(1.5), arm_knee(0.02) 상한 → refine에서 확장.

**Per-exp 결과 (Phase 0→1)**:
- sit2stand (7): +34~76% 전부 개선
- jump_position_0421 (6): +5~84% 전부 개선
- jump_torque_0422 (3): +52~83% 전부 개선
- **jump_0424 (9): −47~+7% 대부분 regression** ⚠️
- jump_0602 (6): −31~+34% 혼재

**★★ 정직한 발견 (Phase 2+ 과제)**:
1. **다중 데이터셋 tension**: 통합 mass(무거운 foot+paddle)가 sit2stand/0421/0422엔 큰 도움이나 jump_0424 저-gain(60_0.75 −37%, 90_0.75 −47%)엔 해. Pure CAD에서 좋던 점프가 악화.
2. **sit2stand_gnd_0319 sim 발산**: score −63%지만 q sim 발산(q1→−14, q2→+22). Mode A GND 토크 replay 불안정. GRF spike 4600N. → contact/friction 최우선.

**★ clip 버그 (교훈)**: `eval_wrapper.clip_x`가 refine의 확장 bound를 silently clip. refine 20,533은 artifact. **full 15D best(20,367, M_foot_ex=0.263)가 진짜 최적**. foot mass 0.30 이상 확장은 악화. 향후 bound 확장 시 clip 범위도 확장 필수.

**시사점 (다음 Phase)**:
- arm_knee KEEP + 상한 chase → Phase 3(armature) 조기 통합. arm_hip 재검토 후보.
- inertia scale 무의미 → link I 재시도 불필요.
- 남은 주범: sit2stand_gnd 발산 + jump_0424 regression. → **Phase 2 = joint friction** (발산 안정화 + 저-gain 점프 복구 시도) 또는 **contact**.

**Files**: `phase1_best.json`(채택), `phase1_droptest.json`, `phase1_final_breakdown.json`, `docs/phase_1/`. refine 폐기.

---

## Phase 2 — Joint friction ✅ (fv/fc 4D)

**Status**: Complete (2026-07-03). Score **15,744.40** (−22.7% vs Phase 1, 누적 **−61.9%**).

**best**: fv_hip=0.926, fv_knee=0.127, fc_hip=0.095, fc_knee=0.809 (Phase 1 mass 모델 위 4D CMA-ES).

**Drop-test**: KEEP fv_hip(+14%), fc_knee(+11%). DROP fv_knee(+2.4%), fc_hip(+0.2%). → **hip=점성 지배, knee=쿨롱 지배** (물리적으로 타당).

**★★ 핵심 발견 (새 tension)**:
- sit2stand 전부 +50~71% (sit2stand_gnd 발산 안정화: q1 sim −14→+0.5, dq 1초 후 0 정착).
- high-PD 점프 (120_2, 150_2.2_*) +7~18%.
- **저-gain position-PD 점프 심한 regression**: 0421 P70 −138%, P90 −124%, P100 −156%. hip 점성마찰(0.93)이 느린 sit2stand엔 맞지만 빠른 저-gain 점프를 과도 감쇠.
- Net +22.7% (sit2stand 지배).

**→ Phase 3 = Stribeck friction**: 저속 고마찰(sit2stand 유지) + 고속 저마찰(저-gain 점프 회복). 속도-무관 C-V 한계 해결. [[G12 Iter32]] Stribeck 시도 참고.

**sit2stand_gnd 부분해결**: 발산은 잡음. 그러나 q-tracking 여전 부정확 (real 느린 squat, sim 정적). Mode A 토크 replay가 이 GND trial squat 재현 못 함. → q_offset/contact 재검토.

**Files**: `phase2_best.json`, `phase2_final_breakdown.json`, `docs/phase_2/`, `anim/sit2stand_gnd_phase2.gif`

---

(Phase 3~ skeleton — 실행 시 append)

## 🔗 관련 문서

- `GOAL19_PROMPT.md` — 미션 spec
- `CANONICAL_LOCK.md` — v14 렌더링 표준
- `MASTER_INSIGHTS_G18.md` — 이전 iter 발견 (참고만)
- Memory: `mode_A_purpose.md`, `ak80_9_torque_calibration.md`
