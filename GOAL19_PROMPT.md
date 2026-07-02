# GOAL19 — Unified 7-Dataset Mode A Digital Twin (BASE-UP, Autonomous until 2026-07-03 22:00 KST)

**Created**: 2026-07-02 22:00 KST
**Alarm**: 2026-07-03 22:00 KST cron (약 24시간 자율 loop)
**Start**: 지금 세션에서 즉시 Phase 0 (Pure Base)부터 시작

## 🎯 한 줄 미션

**Base 모델 (CAD only + joint friction=0.1)부터 시작해서 7-dataset × 31 sub-experiment Mode A 통합 fit. 사전 정의된 8 axis plan 진행 → 완료 후 자율 확장 (원인 분석 + 서칭 + 새 axis 발견).**

## ⚠️ 사용자 결정 (2026-07-02 22:00 승인)

1. **Starting point** = **Base 모델 (Pure CAD, 모든 fudge 제거)** — GOAL18 iter6_v2 안 이어감
2. **Sim mode** = Mode A only (ctrl = -tau_real)
3. **Params** = 완전 통합 single params
4. **Time budget** = 2026-07-03 22:00 KST alarm까지 자율 loop
5. **매 iter Notion child page 생성** ★★★
6. **Plan 완료 후 자율 확장** — 원인 분석, WebSearch, 새 axis 발견, MASTER doc 참고하며 계속 진화

## 🔒 절대 변경 금지 (v14 CANONICAL LOCK 준수)

- `goal18_CANONICAL/code/make_anim.py` — 렌더러 절대 수정 X
- `goal18_CANONICAL/code/build_xml_i38_standalone.py` — XML 생성기 그대로
- 7 LOCK 원칙 (`CANONICAL_LOCK.md` 참조): 좌표 변환 / wrap / 카메라 / 색상 / real-time pace / GND mj_step 1500 / AIR base_z=0.55
- CAD 값 (L1=L2=0.25m, LC=0.03m, foot 21mm×13mm cylinder)
- Mode B 접근 X
- CSV `kneeCurrentTorquePaper` X → canonical `tau_real` 유일 source
- Pure Paper sgn(v) only (GitHub s(v) smoothing X)

## 📊 7 datasets × 31 sub-experiments

| Dataset | Subs | Description |
|---|---|---|
| sit2stand_air_0319 (03.19 air) | 1 (ROOT) | 공중, base 고정 |
| sit2stand_gnd_0319 (03.19 gnd) | 1 (ROOT) | 지면, base slide |
| sit2stand_0324 (03.24) | 4 | 지면, PD firmware (P10_D0/P20_D1/P30_D1/P60_D1.5_P60_D2) |
| jump_position_0421 (04.21) | 6 | position PD (P60~P200 D*) |
| jump_torque_0422 (04.22) | 3 | torque mode (P40_D0.7/P70_D2/P100_D3) |
| jump_0424 (04.24) | 9 | mixed (60_0.75~150_2.2 각 gain) |
| jump_0602 (06.02) | 6 | mixed (60_0.75~150_2.2 각 gain) |
| **Total** | **31** | |

Canonical data: `goal18_v13/Iter6/{dataset}/{sub}/mode_A/sim_data/cycle*.npz`

## 📋 사전 정의된 Axis Plan (Phase 0 → 7)

**중요**: 이 8개 phase는 사전 계획. 각 phase 완료 후 반드시 drop-test + Notion child page. 모두 끝나도 멈추지 않고 **자율 확장** 진입.

### Phase 0: Pure CAD Base (기준 측정)
- **모델**: `build_xml_i38_standalone.py`의 default (fv_hip=fv_knee=0.001, fc_hip=fc_knee=0.001, arm_hip=0, arm_knee=0.00490, m_base=1.216, m_thigh/calf/p/c/foot = CAD 값)
- **손대는 axis**: 없음 (baseline 측정만)
- **목적**: 31 exp 순수 CAD score = Phase 0 baseline. 모든 후속 phase는 이 대비 개선율 측정.
- **결과**: Notion child page "Phase 0 — Pure CAD Baseline" + MASTER_INSIGHTS_G19.md §Phase 0

### Phase 1: motor LPF (motor_tm) 1D BO
- **손대는 axis**: `motor_tm_s` ∈ [0.001, 0.100] seconds
- **물리 근거**: AK80-9 CAN 통신 지연 + firmware low-pass. GOAL7에서 8.37ms, GOAL18에서 32ms 발견.
- **WebSearch**: "AK80-9 T-Motor communication delay", "MuJoCo motor first-order lag", "actuator time constant leg robot"
- **BO**: Optuna TPE 30 trials, warm start motor_tm=0.032 (GOAL18 best)
- **Drop-test**: Phase 0 vs Phase 1 score. 개선 <3% → drop.

### Phase 2: joint friction (fv, fc) 4D NM
- **손대는 axis**: `fv_hip`, `fv_knee`, `fc_hip`, `fc_knee`
- **물리 근거**: 관절 viscous (bearing) + Coulomb (seal). CAD에 없음.
- **WebSearch**: "T-Motor joint friction identification", "Coulomb viscous friction hip knee", "friction model Stribeck legged"
- **BO ranges**: fv[0.001, 3.5], fc[0.05, 3.0]
- **Warm start**: iter38 best (fv_hip=0.442, fv_knee=0.0052, fc_hip=2.046, fc_knee=0.186)
- **NM 50 iter with sigma=0.05 → sigma=0.01 refine**

### Phase 3: motor armature (reflected inertia) 2D NM
- **손대는 axis**: `arm_hip`, `arm_knee`
- **물리 근거**: 모터 rotor inertia × gearbox ratio² = reflected inertia. GOAL18 arm_hip≈0 (motor at base), arm_knee=0.01983 (motor+CVT knee-side).
- **WebSearch**: "T-Motor rotor inertia", "gearbox reflected inertia calculation", "AK80 armature MuJoCo"
- **BO ranges**: arm[0, 0.02]
- **Warm start**: arm_hip=0.001, arm_knee=0.01983

### Phase 4: mass scale (CAD tolerance) 5D NM
- **손대는 axis**: `M_thigh_scale`, `M_calf_scale`, `M_p_scale` (thigh motor), `M_c_scale` (calf motor), `M_foot_extra`
- **물리 근거**: CAD와 실제 부품 mass 편차 (±15% 예상)
- **WebSearch**: "CAD actual mass discrepancy robot", "component mass calibration", "SolidWorks mass properties error"
- **BO ranges**: [0.75, 1.25] (CAD ±25% tolerance)
- **Warm start**: iter5 v2 best (0.9315 / 1.0148 / 0.8175 / 0.7813 / 0.6015)

### Phase 5: contact params (solref/solimp) 2D BO
- **손대는 axis**: `solref_tc`, `imp0`
- **물리 근거**: Rubber foot + concrete floor. GOAL18 solref_tc=0.007085, imp0=0.2526.
- **WebSearch**: "MuJoCo solref solimp contact", "Hwangbo 2019 contact rigidity", "mujoco_menagerie foot contact"
- **BO ranges**: solref_tc[0.001, 0.05], imp0[0.03, 0.60]
- **Optuna TPE 40 trials**

### Phase 6: base mass extension (m_base_scale) 1D BO
- **손대는 axis**: `m_base_scale` × M_base_CAD
- **물리 근거**: CVT/mounting/전선 등 CAD에 없는 base assembly mass
- **WebSearch**: "CVT mass estimation", "unmodeled mass legged robot base"
- **BO range**: [0.8, 1.5]
- **Warm start**: 1.0358

### Phase 7: q_offset (per-trial? or date-group?) 검증
- **손대는 axis**: 
  - Option A: **완전 제거** — physical model만으로 재현
  - Option B: date-group (3개, 3월/4월/6월) 평균 offset
  - Option C: per-trial (GOAL18 방식, 마지막 fudge)
- **물리 근거**: Encoder zero calibration systematic drift
- **WebSearch**: "encoder zero calibration drift", "joint offset systematic bias", "sensor bias identification"
- **결정**: Phase 6까지 score와 비교 후 필요 시에만 추가

### **자율 확장 (Phase 8+)** — Plan 종료 후
사전 계획 axis 8개 완료해도 멈추지 않고:
- 원인 분석: 어느 sub-exp에서 잔차 크나? 어떤 metric이 안 맞나?
- WebSearch 추가: 잔차 원인 관련 논문/GitHub
- MASTER_INSIGHTS_G19.md의 발견 참고하며 새 axis 후보 도출:
  - Stribeck low-speed friction
  - backlash (high-PD dq peak)
  - date-group tau_scale (calibration drift)
  - motor_tm dispersion (dataset별)
  - dt/integrator 재평가
  - 접촉 refinement (foot_pen > 2mm 있으면)
  - 사용자 인사이트 추가

## 📊 Score Function (unified)

```python
def score_per_exp(sim, real, is_jump):
    Wq, Wdq, Wt, Wh, Wgrf, Wpen = 100, 50, 20, 100, 0.1, 50
    s  = Wq  * (rmse_q1 + rmse_q2)
    s += Wdq * (rmse_dq1 + rmse_dq2)
    s += Wt  * (rmse_tau1 + rmse_tau2)
    if is_jump:
        s += Wh  * abs(h_sim - h_real)  # Wh=200 for jump
    grf_dev = abs(max(sim.grf) - max(real.grf)) / max(real.grf, 1)
    s += Wgrf * max(0, grf_dev - 0.25)**2 * 10000
    s += Wpen * max(0, sim.foot_pen_max_mm - 2.0)**2
    return s

score_total = sum(score_per_exp(sim_i, real_i, is_jump_i) for i in 31 exp)
```

## 📋 매 Iteration Checklist (Phase 완료 시)

- [ ] 외부 출처 ≥ 3 (URL + paper title + 인용 줄)
- [ ] BO/NM 실행 완료 + best params 확보
- [ ] 31 exp per-trial RMSE 표 생성
- [ ] Jump h_sim vs h_real 표
- [ ] Drop-test 실행 (axis 필요성)
- [ ] 4-panel compare plot (V20 convention)
- [ ] Animation = v14 canonical `goal18_CANONICAL/code/make_anim.py` 사용 (신규 렌더러 X) ★★★
- [ ] MASTER_INSIGHTS_G19.md §Phase N append
- [ ] **Notion child page 생성 (매 phase마다!)** ★★★
- [ ] Image block count = upload count
- [ ] git commit + push

## 🚦 자율 loop 종료 조건

- **알람**: 2026-07-03 22:00 KST cron alarm (사용자 확인 시점)
- **OR score plateau**: 3 phase 연속 <3% 개선
- **OR 사용자 interrupt**

## 🔗 참조 파일 (재사용)

### Base model 시작점 (Phase 0)
- `goal18_CANONICAL/code/build_xml_i38_standalone.py` — XML generator
  - Default params: `ITER38_BEST_PARAMS_ITER6` 있음. Phase 0에서는 이걸 안 쓰고 **Pure CAD** 값으로 override:
    ```python
    PURE_BASE_PARAMS = dict(
        fv_hip=0.001, fv_knee=0.001, fc_hip=0.001, fc_knee=0.001,
        m_base=1.21623,   # M_BASE_CAD
        solref_tc=0.006320,  # SOLREF_TC default
        imp0=0.14301,        # IMP0 default
        m_thigh_scale=1.0, m_calf_scale=1.0,
        arm_knee=0.00490,    # ARM_KNEE_G default
    )
    # arm_hip = 0.0 (LOCKED in build_xml)
    ```

### Sim engine (Phase 0에서 즉시 사용)
- `goal19/templates/sub_sim_iter6v2.py` — copied from `goal18/iter6_v2/sub_sim_6d.py`
- `goal19/templates/run_nm_iter6.py` — copied from `goal18/iter6/run_nm_2d.py`

### GOAL18/GOAL9 lessons
- `MASTER_INSIGHTS_G18.md` — 이전 iter 발견 (참고만, 시작점 아님)
- `MASTER_INSIGHTS_G9.md` (있으면) — base-up 진행 방식 참고
- Memory: `mode_A_purpose.md`, `ak80_9_torque_calibration.md`, `real_jump_heights.md`

### Canonical rendering (v14 LOCKED — 절대 변경 X)
- `goal18_CANONICAL/code/make_anim.py`
- `goal18_CANONICAL/code/build_xml_i38_standalone.py`
- `CANONICAL_LOCK.md`

### Data
- `goal18_v13/Iter6/{dataset}/{sub}/mode_A/sim_data/cycle*.npz` — 31 exp canonical

### Notion infra
- Token: `(env NOTION_TOKEN)`
- CONCEPT parent: `115ab81d255080fdaae6f28f55e3e205`
- **GOAL19 parent**: 지금 세션에서 CONCEPT 아래 생성. ID → `MASTER_INSIGHTS_G19.md` 최상단 기록.
- **매 phase Notion child** ★

## 💾 즉시 실행 순서

1. Notion parent page 생성 → ID 기록
2. `MASTER_INSIGHTS_G19.md` skeleton 작성 (parent ID 포함)
3. `goal19/data_loaders/load_all_31exp.py` — 31 exp canonical loader
4. `goal19/phase0/run_pure_base.py` — Pure CAD base sim + score
5. Phase 0 완료 → Notion child page + MASTER append + git commit
6. Phase 1~7 순차 진행 (각 phase에 WebSearch, BO/NM, drop-test, Notion child, commit)
7. Phase 7 완료 후에도 계속: 원인 분석 + 서칭 + 새 axis
8. 07.03 22:00 KST alarm 울리면 진행 상황 요약 + 사용자 확인
