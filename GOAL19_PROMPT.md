# GOAL19 — Unified 7-Dataset Mode A Digital Twin

## 🔄 CURRENT STATE (Claude가 매 phase 완료 후 여기 갱신)

- **Now**: Phase 5 준비 (q_offset 재검토 또는 최종 ablation + 종합 보고)
- **Last completed**: Phase 4 ✅ trade-off frontier. λ=1 joint re-opt 채택 → **15,189 (누적 −63.2%)**. frontier plot + Mode-A 에너지 결손 규명.
- **Next action**: Phase 5 = q_offset(encoder bias) 재검토 (per-trial fudge 회피) OR 최종 ablation table + 종합 보고서 (alarm 대비). 남은 개선 여지 적음(frontier plateau) → 종합 정리 우선 고려.
- **Alarm**: 2026-07-03 22:00 KST cron `f2752ee6` (자동 fire)
- **Best score so far**: **15,189** (Phase 4, λ=1)
- **채택 모델 (Phase 4 unified best)**: mass 15p (M_foot_ex 0.263→0.227) + friction(fv_hip=0.787,fv_knee=0.127,fc_hip=0.095,fc_knee=0.524) + contact(solref_tc=0.00217,imp0=0.371). → `phase4_adopted_model.json`
- **★★★ 핵심 결론**: (1) 점프 under-jump 주범=friction, (2) h_ratio가 λ=8에도 0.62 plateau = Mode-A 근본 에너지 결손(~38%), tau_scale 금지 하 못 메움, (3) sit2stand 우수 재현/점프는 형태 O 절대에너지 X. **단일 param set의 Pareto 최적.**
- **미해결(구조적)**: 점프 절대 높이 (tau_scale 또는 tendon 물리 필요), sit2stand_gnd q-tracking.
- **주의**: eval_wrapper clip 버그 — bound 확장 시 clip_x 범위도 확장.
- **다음 후보**: q_offset → 최종 ablation + 종합 보고 (Notion parent 갱신)

> **작업 loop 규칙**: 매 phase 시작 전 이 md 재read → CURRENT STATE 확인 → 진행 → 완료 후 CURRENT STATE 갱신 + commit.

---

**Created**: 2026-07-02 (KST)
**Alarm**: 2026-07-03 22:00 KST cron (~24h autonomous loop)
**Repo**: `C:/Users/junho/Documents/jump-opt-digital-twin/` (git, MkDocs + GH Pages)
**Data root**: `C:/Users/junho/Desktop/jump_opt/` (canonical .npz, unchanged)

---

## 🎯 한 줄 미션

**Pure CAD Base부터 시작해서 7-dataset × 31 sub-experiment Mode A를 단 하나의 통합 param set으로 재현한다. 각 axis는 물리적 근거 + 외부 출처 3개 + drop-test로 검증한다. 07.03 22:00 KST cron alarm까지 자율 loop.**

---

## ⚠️ 사용자 최종 결정 (2026-07-02 승인)

### A. Modeling
1. **Starting point = Pure CAD Base** (모든 fudge 제거, iter6_v2 계승 X). Phase 0 baseline = 59,736 (iter0R inherited).
2. **Sim mode = Mode A only** (`ctrl = -tau_real`). Mode B 금지.
3. **완전 통합 single param set** — per-trial fudge, date-group fudge 모두 금지 대상 (필요 시 Phase 후반 검토).
4. **로봇 동역학 우선** — mass + inertia + CoM per part 한 번에 많이 (15D+ NM/CMA-ES). 각 부품 오차 가정.
5. **바닥 - 로봇 충돌 항상 ON** (contype/conaffinity 1 유지).

### B. 절대 금지 axis
- ❌ `tau_scale` (date-group, per-trial 모두)
- ❌ `motor_tm` LPF (delay 유발)
- ❌ `motor_tm` dataset별 dispersion
- ❌ CAD 값 변경 (L1=L2=0.25m, LC=0.03m, foot 21mm×13mm)
- ❌ Mode B
- ❌ `kneeCurrentTorquePaper` CSV
- ❌ 좌표 변환 없이 canonical q 사용 (렌더 시 mj_q1 = −q1−π/2, mj_q2 = −q2)
- ❌ Pure Paper sgn(v) 이외 마찰 smoothing (GitHub s(v) 금지)
- ❌ matplotlib animation (canonical make_anim.py 유일)

### C. Autonomy
6. **사전 axis 순서 고정 X** — 로봇 동역학 우선 원칙만 지키고 나머지는 자율. 동시 진행 OK.
7. **자율 axis 발견** — 잔차 분석 + WebSearch + MASTER doc 참고. 새 후보 자율 도출.
8. **다양한 optimizer 자유롭게 사용** — Optuna TPE, scipy NM, CMA-ES, differential evolution, grid + refine. 상황별 선택.
9. **Weights 유지 + 자율 조정 가능** — Wq=100, Wdq=50, Wt=0, Wh_jump=100, Wgrf=0.1, Wpen=50. 필요 시 조정 근거 기록.
10. **07.03 22:00 KST cron alarm까지 자율 loop.** Plan 완료해도 멈추지 않고 자율 확장.

### D. Documentation
11. **Vault = MkDocs Material** (Obsidian-compatible markdown) at `docs/`.
12. **Public site = GitHub Pages** (auto-deploy via Actions on push to main).
13. **Notion = 최소** — parent page 하나 + phase 요약 정도. child page per iter 요구 없음.
14. **매 phase에 git commit + push → GH Pages 자동 배포**.

---

## 📊 7 Datasets × 31 Sub-experiments

| Date | Dataset | Subs | Note |
|---|---|---|---|
| 03.19 | sit2stand_air_0319 | 1 (ROOT) | 공중, base 고정 |
| 03.19 | sit2stand_gnd_0319 | 1 (ROOT) | 지면, base slide |
| 03.24 | sit2stand_0324 | 5 | firmware PD × 5 (P10_D0, P10_D1, P20_D1, P30_D1, P60_D1.5_P60_D2) |
| 04.21 | jump_position_0421 | 6 | Position PD × 6 |
| 04.22 | jump_torque_0422 | 3 | Torque control × 3 |
| 04.24 | jump_0424 | 9 | Mixed × 9 |
| 06.02 | jump_0602 | 6 | Mixed × 6 |
| **Total** | | **31** | |

**Canonical source (read-only)**: `Desktop/jump_opt/goal18_v13/Iter6/{dataset}/{sub}/mode_A/sim_data/cycle*.npz`
(sit2stand_air_0319, sit2stand_gnd_0319, sit2stand_0324는 `goal16/cross_validation_*` 경로 — registry에서 관리)

**Loader**: `code/goal19/data_loaders/load_31exp.py` — REGISTRY 31개 + `load_experiment(dataset, sub) → ExpData`. 실행 시 `assert len(REGISTRY) == 31`. (현재 30 → 1 누락. 실행 즉시 fix.)

---

## 📋 Phase Plan (로봇 동역학 우선 + 자율)

**원칙**: 로봇 동역학 (mass/inertia/CoM per part)을 **먼저** 큰 dim으로 열고 fit. 이후 자율.

### Phase 0 — Pure CAD Baseline (기준 측정)
- **Params 손대는 것**: 없음.
- **XML**: `build_xml_i38_standalone.py` default에서 fudge 제거:
  ```python
  PURE_BASE = dict(
      fv_hip=0.001, fv_knee=0.001, fc_hip=0.001, fc_knee=0.001,
      m_base=1.21623,  m_thigh_scale=1.0, m_calf_scale=1.0,
      arm_hip=0.0, arm_knee=0.00490,
      solref_tc=0.006320, imp0=0.14301,
  )
  ```
- **Output**: 31 exp per-exp score + total. 후속 phase의 개선 기준.
- **Deliverable**: `docs/phase_0/index.md` + git commit.

### Phase 1 — 로봇 동역학 (Mass + Inertia + CoM per part)
- **Params (15D+)**:
  - Per part (base / thigh / calf / foot / paddle_hip / paddle_knee):
    - `M_scale` (CAD mass ×)
    - `I_scale` (CAD inertia ×; 3-axis or lumped)
    - `com_shift_x`, `com_shift_z` (part-local, ±10mm range)
- **물리 근거**: CAD-실제 편차 (제작 tolerance, 도색, 나사, 케이블 wrap). 부품별 오차 독립 가정.
- **Optimizer**: CMA-ES or NM (15-25D). 자율 선택.
- **WebSearch (≥3)**: "CAD actual mass discrepancy legged robot", "component inertia calibration SolidWorks error", "CoM shift bipedal identification"
- **Drop-test**: 개선 <3%인 축은 pin.
- **Deliverable**: `docs/phase_1/index.md` + drop-test 표 + commit.

### Phase 2+ — 자율 (아래 후보 중 자율 선택)
사전 순서 없음. 잔차 분석 → 후보 결정 → 실행 → drop-test.

**후보 axis**:
- Joint friction (fv_hip, fv_knee, fc_hip, fc_knee) — 4D
- Motor armature (arm_hip, arm_knee) — 2D
- Contact params (solref_tc, imp0) — 2D
- Stribeck low-speed friction — 2D
- Backlash (high-PD dq peak 대응) — 1-2D
- dt / integrator (RK4 vs implicit) — 재평가
- Sensor bias (q_offset — encoder zero drift) — Phase 후반 결정, per-trial fudge 회피 최선
- Foot geometry refinement (foot_pen > 2mm 있으면)
- 새 후보 — MASTER doc + WebSearch로 자율 도출

**각 후보 진행 시 필수**:
- 외부 출처 ≥ 3 (URL + 논문/GitHub 인용)
- BO/NM/CMA-ES 중 자유 선택 (근거 기록)
- Drop-test — axis 뺐을 때 score 변화 <3% → drop
- 4-panel plot (V20 convention) + v14 canonical animation
- `docs/` 페이지 + MASTER append + git commit

---

## 📊 Score Function (unified, 31 exp aggregated)

```python
def score_per_exp(sim, real, is_jump):
    Wq, Wdq, Wt, Wh, Wgrf, Wpen = 100, 50, 0, 100, 0.1, 50
    s  = Wq  * (rmse_q1 + rmse_q2)
    s += Wdq * (rmse_dq1 + rmse_dq2)
    # Wt=0 (tau_scale 금지 원칙 반영 — tau는 real input이므로 매칭 X)
    if is_jump:
        s += Wh * abs(h_sim - h_real)
    grf_dev = abs(max(sim.grf) - max(real.grf)) / max(real.grf, 1)
    s += Wgrf * max(0, grf_dev - 0.25)**2 * 10000
    s += Wpen * max(0, sim.foot_pen_max_mm - 2.0)**2
    return s

score_total = sum(score_per_exp(sim_i, real_i, is_jump_i) for i in 31 exp)
```

**Wh (jump height)**: `_H_REAL` table (Real Data.txt 기반, sit2stand=0).

**Weights 자율 조정**: 특정 metric 무시되면 재조정 근거를 phase log에 기록.

---

## 📋 매 Phase Checklist

- [ ] 외부 출처 ≥ 3 (URL + 인용 줄)
- [ ] Optimizer 실행 (수렴 로그 저장)
- [ ] 31 exp per-trial RMSE 표
- [ ] Jump h_sim vs h_real 표 (jump only)
- [ ] Drop-test 표
- [ ] 4-panel compare plot × N sub (V20 convention)
- [ ] Animation = **v14 canonical `goal18_CANONICAL/code/make_anim.py`** ★
- [ ] `docs/phase_N/index.md` 작성 (plot 링크 포함)
- [ ] `MASTER_INSIGHTS_G19.md §Phase N` append
- [ ] git commit + push (GH Pages 자동 배포)
- [ ] (Optional) Notion parent page의 phase 요약 1문장 update

---

## 🚦 종료 조건

1. **Cron alarm**: 2026-07-03 22:00 KST — 사용자 확인 시점 (자율 loop 완주 후).
2. **User interrupt**: 사용자 명시적 중단.
3. **Score plateau**: 3 phase 연속 <3% 개선 시 자율 loop 유지 + 다른 axis / meta-analysis로 전환.

---

## 🔗 참조 (Read-only)

### Base model
- `Desktop/jump_opt/goal18_CANONICAL/code/build_xml_i38_standalone.py` — XML generator
- `Desktop/jump_opt/goal18_CANONICAL/code/make_anim.py` — v14 canonical renderer
- `CANONICAL_LOCK.md` — 7 LOCK 원칙

### Sim engine templates (copied)
- `code/goal19/templates/sub_sim_iter6v2.py` — Mode A pure sim
- `code/goal19/templates/sub_sim_iter5.py` — fallback
- `code/goal19/templates/run_nm_iter6.py` — NM driver

### Prior insights
- `MASTER_INSIGHTS_G18.md` — 이전 iter 발견 (참고만, 시작점 아님)
- Memory: `mode_A_purpose`, `ak80_9_torque_calibration`, `real_jump_heights`, `goal18_canonical_pipeline`

### Notion (최소 사용)
- Token: env `NOTION_TOKEN` (never commit)
- CONCEPT parent: `115ab81d255080fdaae6f28f55e3e205`
- GOAL19 parent: `391ab81d-2550-81b9-a252-ea9233db7a87` (created)
- Update: phase 요약 append (child page 강제 X)

### Data (read-only)
- `Desktop/jump_opt/goal18_v13/Iter6/**/mode_A/sim_data/cycle*.npz` (jump datasets)
- `Desktop/jump_opt/goal16/cross_validation_*/{dataset}/{sub}/mode_A/sim_data/*.npz` (sit2stand datasets)

---

## 💾 즉시 실행 순서 (사용자 승인 후)

1. `code/goal19/data_loaders/load_31exp.py` REGISTRY 31 fix (현재 30 → 1 누락 찾기)
2. `code/goal19/phase0/run_pure_base.py` — Pure CAD 31 exp 실행 + score aggregate
3. Phase 0 baseline 확정 → `docs/phase_0/index.md` + git commit + push
4. Phase 1 (로봇 동역학 15D+) — CMA-ES 자율
5. Drop-test + `docs/phase_1/index.md` + commit
6. Phase 2+ 자율 (잔차 분석 + WebSearch + 후보 선택)
7. 매 phase git commit → GH Pages 자동 배포
8. 07.03 22:00 KST alarm 울리면 진행 요약 + 사용자 확인

---

## 🛠 인프라 상태 (사용자 확인 완료)

- ✅ Repo: `Documents/jump-opt-digital-twin/` (329KB clean, Desktop/.git 분리 완료)
- ✅ GitHub: `wnsgh3810/jump-opt-digital-twin` public repo pushed
- ✅ Notion token 히스토리에서 제거 완료 (env NOTION_TOKEN 참조)
- ✅ GitHub Pages Actions workflow: `.github/workflows/deploy.yml` (push to main → build → deploy)
- ✅ MkDocs Material config: `mkdocs.yml` (Korean nav, tabs, dark mode)
- ✅ Cron alarm: `f2752ee6` (0 22 3 7 * → 07.03 22:00 KST one-shot)
- ⏳ Registry 30 → 31 fix 필요
- ⏳ GH Pages first live check 필요 → https://wnsgh3810.github.io/jump-opt-digital-twin/

---

**이 프롬프트를 승인하면 즉시 실행 순서 1번부터 시작합니다.**
