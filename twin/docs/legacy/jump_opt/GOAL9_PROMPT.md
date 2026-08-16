# GOAL9 — Mode A Digital Twin (Base-up, Cylinder Foot, 7-Day Autonomous Loop)

> **시작일**: 2026-06-09 KST
> **종료**: 2026-06-16 KST 12:00 (≈ 7일 자율 진행)
> **모드**: Mode A 단일 (Mode B 폐기)
> **출발점**: GOAL7 Base Model (CAD + fl_hip=fl_knee=0.1, **cylinder foot 42mm × 13mm y-axis**)

---

## 🎯 한 줄 미션

**26.04.24 9 trial 데이터** (`C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.04.24\{trial}\`)의 **`paper_a_hat(currentTorque, dq)` (Pure Paper sgn(v) only)** 변환된 actual motor torque를 MuJoCo sim에 input → sim의 **q, dq, τ, 실제 점프 높이 (각 trial 폴더의 `Real Data.txt` 첫 줄에 명시, 77–91 cm 범위)** 가 실측과 일치하는 **현실적 디지털 트윈**을 base-up으로 axis 1개씩 검증/유지·폐기하며 7일 동안 끊임없이 발전시킨다. GRF는 soft (25% band) — 크게 어긋나지만 않으면 OK.

### 데이터 source (★ 명시)
- **경로**: `C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.04.24\`
- **9 trial 폴더** (PD gain set 정렬):
  - `60_0.75_60_2/`
  - `60_1.5_60_1.5/`
  - `90_0.75_90_2/`
  - `120_2_120_2/`
  - `120_2.2_150_2.5/`
  - `120_2.2_200_2.8/`
  - `150_2.2_250_3/`
  - `150_2.2_350_3.5/`
  - `150_2.2_500_4/`
- 각 폴더 내용:
  - `hip.xlsx`, `knee.xlsx`, `GRF.xlsx` — raw measurement (time, currentAngle, currentAngleVelocity, currentTorque, desiredAngle, ..., Current_GRF)
  - **`Real Data.txt`** — ★ **첫 줄에 실제 점프 높이** (예: `"실제 점프 높이 : 0.9m"`). GRF 요약, mechanical power, peak event 등 분석 자료 포함.
  - 기타 plot PNG, MP4, `jump_results.xlsx`, `Real Data_ahat.txt` 등
- **정제된 데이터**: `phase0_data_load.py` 패턴을 따라 위 xlsx 9 trial을 load + `paper_a_hat` 변환 → 새 `goal9/data_loaded_26_04_24.npz`에 저장 (또는 phase 0에서 신규 작성). Mode A sim의 `tau_real` source.

---

## ⚠️ GOAL8과 다른 점 (정정 사항, 절대 반복 X)

1. **Mode B 폐기** — Mode A 단일. Mode B 코드/페이지/score 생성 금지.
2. **Stage 39/53 chain 폐기** — 출발점은 **GOAL7 Base Model**: CAD inertia + `fl_hip=fl_knee=0.1`, 그 외 모든 추가 axis (a_hat, αkp/αkd, motor_tm, q_delay, armature, foot 2-point, flex, friction Stribeck 등) **모두 0/∞/identity 로 reset**.
3. **점프 높이 (85–98 cm) 1순위 metric** — 점수 함수에 명시. per-trial RMSE < 3 cm 빡빡한 기준.
4. **GRF down-weight** — 25% band 안이면 통과. 사용자: "엄청 벗어나지만 않으면 될 거 같애".
5. **★ Foot geometry 변경**: sphere(2-point heel/toe) → **cylinder 42mm × 13mm, axis = y축 (lateral, hinge axis와 평행)**. Disc face가 robot 좌측·우측 봄, 옆면이 바닥과 line contact. 자전거 바퀴 형태.
6. **saturation κ 가설 영구 폐기** — Mode A 입력이 이미 hardware saturated. κ 추가 = 이중 saturation.
7. **csv `kneeCurrentTorquePaper` 사용 금지** — `data_loaded.npz['tau_real']` 단일 source.
8. **Pure Paper sgn(v) only** — GitHub smooth(v) 형태 금지.
9. **외부 prior 기반 axis 추가** — 모든 새 axis는 paper/오픈소스 출처 ≥ 3개 cite + 중심값 명시 후 BO. fudge factor 금지.
10. **Drop-test 필수** — axis 제거 시 score 변화 < 3%면 drop (minimal model).

---

## 🔒 절대 변경 금지 (Hard constraints)

- 실 robot CAD: `M=1.02, m1=1.05213, m2=0.237, m_c=0.80898, m_p=0.14977`, 모든 r/I/l_c/l_o, `l1=l2=0.25 m`
- AK80-9 V2 motor spec: `gr=9, kt=0.091, CF=0.59`, peak ±18 Nm
- **Foot = cylinder 42mm × 13mm, axis = y축 (lateral)** ← ★ GOAL9 최종 확정
- `range="-3 3"` joint range 금지 (GOAL5R hidden bug)
- Capsule foot 금지 (cylinder만)
- XML에 `<asset>`, `<visual>`, `<light>` 항상 포함 (GIF 조명)
- 9 trial PD set 그대로 (26.04.24): `60_0.75_60_2`, `60_1.5_60_1.5`, `90_0.75_90_2`, `120_2_120_2`, `120_2.2_150_2.5`, `120_2.2_200_2.8`, `150_2.2_250_3`, `150_2.2_350_3.5`, `150_2.2_500_4`
- Mode A ctrl = `tau_real` 직접 입력 (sim PD X)

---

## 📐 Foot Geometry 최종 사양 (★ GOAL9 새 사항)

### 물리적 설명
- **모양**: 원기둥 (cylinder)
- **치수**: 지름 **42 mm** (radius 0.021), 두께 **13 mm** (half-length 0.0065)
- **Axis 방향**: ★ **y축 (lateral, robot의 좌-우 방향)** — hinge joint axis와 평행
- **Disc face**: robot의 **좌측, 우측** (양옆)을 바라봄
- **Cylindrical surface**: 바닥(ground plane, x-y plane at z=0)과 **line contact** (line along y, length 13 mm)
- **굴러가는 방향**: sagittal plane (x-z) 내에서 **forward/backward (x축)** — 자전거 바퀴 / Raibert hopper / 일반 단족 점프 robot 표준

### MuJoCo XML 표현 (둘 중 하나, fromto 권장)
```xml
<!-- 권장: fromto로 axis 명시 -->
<default class="foot">
  <geom type="cylinder" fromto="0 -0.0065 0  0 0.0065 0" size="0.021"
        priority="1" condim="6"
        solref="..." solimp="..."/>
</default>
<!-- 사용 시: -->
<geom name="foot" class="foot" pos="0 0 -0.25" rgba="0.5 0.5 0.5 1"/>
```
또는
```xml
<geom type="cylinder" size="0.021 0.0065" euler="90 0 0"
      pos="0 0 -0.25" .../>
```

### MuJoCo 좌표계 (참고)
- **z축 = 위/아래** (gravity 방향)
- **x축 = 앞/뒤 (sagittal)** — robot이 forward 점프하는 방향
- **y축 = 좌/우 (lateral)** — hinge joint axis (`axis="0 1 0"`)

### 이전 sphere foot 폐기
- Stage 53 XML의 `foot_heel`(x=−fs) + `foot_toe`(x=+fs) 두 sphere convention 완전 제거
- 단일 cylinder로 대체. `foot_sep`, `foot_r` 파라미터 폐기.

### 현실적 contact 기대
- Sphere의 single-point contact (∞ pressure) → cylinder의 line contact (분산 force)
- MuJoCo가 cylinder-plane contact를 multiple edge/face contact으로 처리 → penetration depth 작아짐
- 사용자 명시 기준 **penetration < 2 mm** (모든 trial / 모든 시점)을 cylinder geometry + Phase 1 solref/solimp tuning으로 달성

---

## 📊 점수 함수 (GOAL9 최종)

```
score = Σ_trial [ W_q1·RMSE(q1) + W_q2·RMSE(q2)
                + W_dq1·RMSE(dq1) + W_dq2·RMSE(dq2)
                + W_τ1·RMSE(τ1)  + W_τ2·RMSE(τ2)
                + W_h·|h_sim − h_real|                    ← ★ 1순위
                + W_grf·max(0, GRF_dev_pct − 0.25)²       ← 3순위 soft
                + W_pen·max(0, foot_pen_max_mm − 2)²      ← penetration penalty
              ]
```

### 가중치 (절대 변경 금지)
| Term | Weight | 비고 |
|---|---|---|
| W_q1, W_q2 | **100** | 1순위 |
| W_dq1, W_dq2 | **3** | 1순위 |
| W_τ1, W_τ2 | **20** | 1순위 |
| **W_h** | **50** | ★ 점프 높이 1순위 (사용자 명시) |
| W_grf | **1** | 3순위 soft, band=25% |
| **W_pen** | **10** | ★ foot penetration penalty, band=2mm |

### Metric 정의
- `h_sim = max_t (base_z(t))` — Mode A sim의 base z 최댓값 (m 단위, 비행 phase 포함 ballistic 계산 필요)
- `h_real`: ★ **각 trial 폴더의 `Real Data.txt` 첫 줄**에서 읽음 (`"실제 점프 높이 : X.XXm"`). 절대 추정값/memory 값 사용 X — 매번 `Real Data.txt`를 직접 parse.
  - **26.04.24 9 trial h_real** (Real Data.txt verbatim 추출, 26.06.09 검증):
    | Trial | h_real (m) |
    |---|---|
    | 60_0.75_60_2 | 0.900 |
    | 60_1.5_60_1.5 | 0.910 |
    | 90_0.75_90_2 | 0.894 |
    | 120_2_120_2 | 0.840 |
    | 120_2.2_150_2.5 | 0.810 |
    | 120_2.2_200_2.8 | 0.795 |
    | 150_2.2_250_3 | 0.770 |
    | 150_2.2_350_3.5 | 0.770 |
    | 150_2.2_500_4 | 0.775 |
  - 범위: **0.770 ~ 0.910 m** (low-PD ↑, high-PD ↓ — PD ↑일수록 점프 높이 ↓ trend 명확)
  - Loader: phase 0에서 `Real Data.txt` parse 추가 → `data_loaded_26_04_24.npz`에 `h_real_per_trial` field 저장
  - **3 cm RMSE 기준**: h_real 77-91 cm 범위에서 3 cm = 3.3-3.9% — 빡빡한 1순위 metric
- `GRF_dev_pct = |GRF_sim_peak − GRF_real_peak| / GRF_real_peak`
- `foot_pen_max_mm` = sim 전 시간에 걸쳐 foot이 ground (z<0) 통과한 max depth in mm

---

## 🚀 Phase 진행 전략 (axis 1개씩, drop-test 강제)

### Phase 0 — Base Baseline 측정 (즉시 시작, BO 없음)
- Base XML: CAD + jf=0.1 + cylinder foot 42mm×13mm y-axis + MuJoCo default solref/solimp
- 9 trial Mode A sim 실행 (`ctrl = tau_real × 1.0`, tau_scale 미적용)
- 측정: per-trial q/dq/τ RMSE, h_sim/h_real, GRF, penetration
- 4-panel plot 6장 + V25 animation 1+ trial
- Notion 페이지 "Phase 0 — Base Baseline" 생성 (Locked Template)
- MASTER_INSIGHTS_G9.md 초기화 + "## Phase 0" section 작성
- git commit

### Phase 1 — solref/solimp (contact rigidity) ★ 사용자 결정 첫 axis
- **외부 검색 (최소 30분)**:
  - MuJoCo docs: `https://mujoco.readthedocs.io/en/stable/modeling.html`
  - mujoco_menagerie: cassie, go1, spot, h1 scene.xml의 solref/solimp
  - legged_gym (RSL ETH): contact tuning
  - Hwangbo 2019 ANYmal (Sci Robotics): k_spring, b_damper for foot
  - Park 2021 KAIST hound, Raibert 1986
  - WebSearch query: "MuJoCo solref hopping robot", "cylinder contact mujoco penetration"
- **MASTER_INSIGHTS_G9에 외부값 모두 (≥ 3 출처) 적고** prior 중심 + 우리 BO range 결정
- **BO** (Optuna TPE, n_trials=400, warm start from Phase 0):
  - Free: `solref_tc ∈ [0.005, 0.05]`, `solref_d ∈ [0.5, 2.5]`, `imp_0 ∈ [0.7, 0.95]`, `imp_1 ∈ [0.92, 0.99]`, `imp_mid ∈ [0.0001, 0.005]`
- **결과 분석**: score, per-trial RMSE, h, GRF, penetration
- **Drop-test**: 기본값으로 되돌리면 score 변화 < 3%면 drop
- **Notion 페이지 "Phase 1 — solref/solimp"** (Locked Template)
- MASTER_INSIGHTS_G9 append + git commit

### Phase 2+ — 한 번에 1개 axis (현실성·영향 ranking)

각 phase는 동일 procedure: **검색 → MASTER_INSIGHTS_G9 append → BO → 결과 → drop-test → 노션 페이지 → commit**.

**추천 axis 순서** (현실성 + 점프 task 영향력):
1. ✅ solref/solimp (Phase 1) — contact rigidity
2. Floor friction `μ ∈ [0.5, 1.5]` (paper 값 0.6–1.2)
3. Joint armature (gr² × I_rotor) — AK80-9 paper 값 ≈ 0.0049 kg·m²
4. Joint damping (viscous, `damp_hip`, `damp_knee`) — motor data sheet
5. Motor LPF (`motor_tm`) — AK80-9 paper ≈ 8.37 ms (memory `goal7_stage20_motor_tm`)
6. tau_scale_h, tau_scale_k — Paper a_hat 잔여 보정 (이전 ~1.13, ~1.18)
7. Tau delay (`tau_delay_ms`) — CAN bus + ADC + firmware ≈ 1–5 ms
8. Foot mass extra (`m_foot_extra`) — compliant pad 가능
9. RK4 vs Euler integrator + dt 검토 (현재 dt=0.001 OK)
10. (optional, drop-test 후 추가) Stribeck friction `fs`, `vs`; gear backlash; mass ±5% refit

### 자율 loop 진행 흐름
- 매 phase 종료 후 다음 phase 즉시 시작 (자동)
- 시간 limit (6/16 12:00 KST) 또는 plateau (3 phase 연속 < 3% 개선) 도달 시 종료
- 종료 시 Phase Final — 모든 keep axis 통합 + ablation 최종 정리 페이지

---

## 📋 노션 페이지 Locked Template (★ 매 phase 동일)

페이지 절대 압축 X. 자세하고 친절하게 (memory `feedback_notion_workflow`).

### 페이지 sections (순서대로)

#### 0. Title + Status callout (yellow_background)
```
"Phase N — [axis 이름]. Mode A 디지털 트윈 base-up. 우선순위 q/dq/τ/h_jump 1순위, GRF soft."
"Status: [in_progress / converged / dropped]"
"Date: 2026-06-XX KST"
```

#### 1. 📖 이 페이지를 읽으면 얻는 것 (5–7개 bullet, 학습용)
- 이 phase에서 어떤 axis를 추가했는가
- 왜 이 axis가 현실적인가 (paper/repo 근거)
- 적용 결과 어떻게 변했나
- 다음 phase 후보는 무엇인가
- 등등

#### 2. 🆚 Base Model vs This Stage 비교 표 ★ (사용자 명시 매 페이지)
- Base column = ★ **항상 GOAL7 Base (CAD + jf=0.1 + cylinder foot 42×13 y-axis + MuJoCo default solref/solimp)** — 모든 phase 동일 기준
- This Stage column = 현재 Phase BO best
- ★ 표시 = 이 phase에서 변경된 axis
- 모든 axis (Base에서 추가될 수 있는 모든 항목) 행 포함
- 예:
  | Variable | Base | Phase N best | 단위 | 의미 |
  |---|---|---|---|---|
  | solref_tc | 0.02 | (best) | s | ★ contact spring time constant |
  | solref_d | 1.0 | (best) | — | ★ contact damping ratio |
  | imp_0 | 0.9 | (best) | — | ★ contact impedance min |
  | imp_1 | 0.95 | (best) | — | ★ contact impedance max |
  | imp_mid | 0.001 | (best) | m | ★ contact transition depth |
  | μ_floor | 1.0 | 1.0 | — | floor friction (not added yet) |
  | armature_hip | 0 | 0 | kg·m² | rotor reflected inertia (not added) |
  | damp_hip | 0 | 0 | Nms/rad | joint viscous damping |
  | fl_hip | 0.1 | 0.1 | Nm | joint Coulomb friction |
  | motor_tm | 0 | 0 | s | motor LPF |
  | tau_scale_h | 1.0 | 1.0 | — | tau scale correction |
  | tau_delay_ms | 0 | 0 | ms | actuator delay |
  | foot_radius | 0.021 | 0.021 | m | cylinder radius |
  | foot_thickness | 0.013 | 0.013 | m | cylinder thickness (y-axis) |
  | ... 등등 ... |

#### 3. 📖 MuJoCo / 모델 용어 정리 ★ (사용자 명시 매 페이지)
- Stage 53 페이지에 추가했던 11항목 패턴 (`add_mujoco_param_explanations.py` template 재사용)
- 항목: `solref_tc`, `solref_d`, `imp_0/1/mid`, `μ_floor`, `armature_hip/knee`, `damp_hip/knee`, `fl_hip/knee`, `motor_tm`, `tau_scale_h/k`, `tau_delay_ms`, `m_foot_extra`, `foot_radius`, `foot_thickness`, `base_arm`, `base_fl`, `fs_hip/knee`, `vs`, `a_hat (a₀~a₄)`, `sgn(v)`, `Iq (qaxis current)`
- 각 항목: 한 줄 정의 + 우리 컨텍스트에서 의미 + 값 범위 + 단위

#### 4. 🔬 변경 axis 상세 (1개)
- 📋 From → To (값 + 단위)
- 🌍 외부 출처 (★ 최소 3개, paper title + URL + 인용 줄)
  - 예: "MuJoCo Menagerie cassie/scene.xml line 23: solref='0.015 1.5' — https://github.com/google-deepmind/mujoco_menagerie/..."
- 🔬 물리적 메커니즘 (수식, 모델)
- 🤔 왜 이 axis를 선택했나 (이전 phase의 어떤 문제 해결)
- 🎮 sim 영향 (어떤 dynamics 변화 기대)
- 🌊 다른 axis와의 interaction

#### 5. 🏁 BO 결과
- score (절대값 + Base 대비 변화 %)
- per-trial RMSE 표 (q1/q2/dq1/dq2/τ1/τ2)
- **★ 점프 높이 표** (사용자 1순위, 매 페이지):
  | Trial | h_real (m) | h_sim (m) | |Δh| (cm) | 통과 < 3cm? |
  |---|---|---|---|---|
  | 60_0.75_60_2 | 0.94 | (sim) | (Δ) | ✓/✗ |
  | ... | ... | ... | ... | ... |
- **GRF band 25% 분석 표** (per-trial GRF peak sim vs real)
- **Foot penetration 표** (per-trial max penetration mm, < 2mm 통과 여부)

#### 6. 📈 4-panel compare plot (per-trial, 9 trial 모두)
- Panel: q (rad) / dq (rad/s) / τ (Nm) / GRF (N)
- X: time (s, 시작 0)
- sim/real 동일 변수 동일 색, sim 점선 (memory `feedback_plot_colors` — matplotlib auto color cycle)
- caption: 각 panel의 X/Y 축, 색 의미, peak 값
- 코드: `gen_compare_plots_v3.py` 패턴 (V20 convention 변환)

#### 7. 🎬 V25 Animation (1+ trial)
- 80 frames, GIF duration 60ms
- 흰 글자 + 검은 outline, malgun.ttf 한글
- 카메라 azimuth=135, elev=−15, dist=1.2
- Overlay: t (ms), base_z (cm, 바닥 기준), GRF (N), h_max
- 코드: `gen_anim_v4_clean.py` 패턴

#### 8. 🔍 결과 해석
- 왜 좋아졌나/안 좋아졌나
- **★ 점프 높이 매칭** (1순위 분석)
- **★ Foot penetration** (< 2mm 달성?)
- GRF band 25% 안인가
- 다음 axis 후보 추천 (현실성 ranking + 영향력 예상)

#### 9. 💎 Drop-test 결과
- 이 phase의 axis를 0/∞로 되돌린 sim 결과 vs phase best
- score 변화 %
- < 3% → **drop**, ≥ 3% → **keep**
- 명확히 표시

#### 10. 💾 코드 토글
- BO script, best XML, plot/anim script

#### 11. 🌐 외부 참조 + cross-link
- paper/repo URL + 인용 줄
- MASTER_INSIGHTS_G9.md 해당 section 링크
- 이전 phase 페이지 cross-link

### 페이지 verify (★ 매번)
```python
# 1. file_uploads 모두 status="uploaded"
for fu_id in uploaded_ids:
    r = requests.get(f"https://api.notion.com/v1/file_uploads/{fu_id}", headers=HEADERS)
    assert r.json()["status"] == "uploaded", f"failed {fu_id}"

# 2. page children 중 image block 개수 = 업로드 개수
def list_image_blocks(page_id):
    blocks = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if cursor: url += f"&start_cursor={cursor}"
        r = requests.get(url, headers=HEADERS).json()
        blocks.extend([b for b in r["results"] if b["type"]=="image"])
        if not r.get("has_more"): break
        cursor = r["next_cursor"]
    return blocks

img_blocks = list_image_blocks(page_id)
assert len(img_blocks) == expected_count, f"missing {expected_count-len(img_blocks)} images"
```
누락 시 즉시 재업로드.

---

## 🔁 검색 → MASTER_INSIGHTS_G9 → 적용 cycle

### 외부 검색 (★ 매 phase 시작 시 최소 30분)
- WebSearch queries (axis별 다름):
  - `"MuJoCo solref" hopping`, `"MuJoCo solimp" cylinder contact`
  - `"legged_gym contact tuning"`, `"mujoco_menagerie cassie scene"`
  - `"AK80-9 armature inertia"`, `"actuator gear ratio reflected inertia paper"`
  - `"Hwangbo 2019 ANYmal contact"`, `"Park 2021 hound jumping robot"`
  - `"Raibert hopping robot contact stiffness"`
- GitHub fetch:
  - `google-deepmind/mujoco_menagerie/*/scene.xml`
  - `leggedrobotics/legged_gym/*/base_task.py`
  - `cassie-mj/cassie_description/*.xml`
- Paper:
  - Hwangbo et al. 2019 *Sci. Robotics* — "Learning agile and dynamic motor skills"
  - Park, Wensing 2021 — MIT Cheetah 3
  - Tan et al. 2018 — *Sim-to-Real: Learning Agile Locomotion*
  - Raibert 1986 — *Legged Robots That Balance*

### MASTER_INSIGHTS_G9.md (★ 단일 통합 file, 분산 저장 금지)
- 경로: `C:\Users\junho\Desktop\jump_opt\MASTER_INSIGHTS_G9.md`
- 최상단: GOAL9 mission 요약 + GOAL9 Notion parent page ID 기록
- 각 phase별 section 형식:
```markdown
## Phase N — [axis 이름]

### 📚 외부 출처 (≥ 3)
1. [paper title or repo] — URL — 인용 verbatim "값 = X, p.Y"
2. [paper/repo] — URL — 인용
3. [paper/repo] — URL — 인용

### 🔢 Prior 값 + BO range
- 외부 평균: ...
- 다른 robot: Cassie=..., Go1=..., Spot=..., ANYmal=...
- 우리 BO range: ...

### 🧪 BO 결과
- Best params: ...
- Score: 절대값 (Base 대비 변화 %)
- 9 trial RMSE 요약: q1/q2/dq1/dq2/τ1/τ2 평균
- 점프 높이 평균 |Δh| (cm)
- GRF peak 평균 |Δ| (%)
- Foot penetration max (mm)

### 💎 Drop-test
- 0/∞로 되돌리면 score: ... (변화 %)
- 결정: keep / drop

### 🚦 결론 + 다음 후보
- keep / drop 이유
- 다음 phase 추천 axis (현실성 ranking)
```

- 매 phase 종료 즉시 append. 미루지 말 것.
- git commit "GOAL9 Phase N — [axis]: keep/drop, score X"

---

## 🔬 식별 / 최적화 방법 다양화 (★ BO만 사용 X, 사용자 명시)

이전 GOAL5~8은 Optuna TPE BO 거의 단독. GOAL9는 axis 별로 가장 적합한 method 선택 + 여러 method 비교하며 발전. 매 phase 노션 페이지에 "사용한 method + 다른 method와 비교" section 추가.

### A. Optuna sampler 다양화
| Sampler | 강점 | 적합 axis / 시점 |
|---|---|---|
| **TPE** | sample efficient, tree-structured Parzen | 일반 (default) |
| **CMA-ES** | covariance adapt, continuous smooth surface | solref/imp (5+ correlated params) |
| **NSGA-II** | multi-objective Pareto | q vs τ vs h_jump trade-off 발견 (특히 high-PD trial) |
| **GP (botorch)** | uncertainty quantification | 작은 dim (<5) + n_trial 적을 때 |
| **Random** | baseline | 새 axis 첫 wide exploration |

### B. Classical optimization (scipy)
- `differential_evolution` — global, robust, BO보다 wide 탐색 (10+ generations × 15 popsize)
- `dual_annealing` — global + local refine, 비선형 multimodal
- `L-BFGS-B` — gradient available 시 (diff sim 적용 시)
- `Nelder-Mead` — gradient X, 작은 dim, fine-tuning

### C. System identification (수식 기반, 비-iterative)
- **Least-squares (linear-in-param)**: `τ = Y(q, q̇, q̈) · π` — manipulator equation으로 mass/inertia closed-form. **Phase 2+ joint armature·damping 식별에 적용**. Khalil-Dombre 표준.
- **EKF/UKF**: state + param augmented state, recursive estimation
- **MLE**: noise model (Gaussian) → likelihood max → asymptotic optimal
- **Total least squares**: measurement noise 양쪽 모두 고려 (currentTorque 자체에 noise 있음 → 적절)

### D. Data-driven / NN
- **Actuator NN (Hwangbo 2019)**: 4 min 데이터 → 3×32 MLP → 0.74 Nm RMSE. **Mode A residual learning**: physical model + NN correction. ★ 후반 phase에 시도 (axis 식별 다 한 후 잔여 model error 학습).
- **NARX / GRU**: lag/delay 자동 학습 (motor_tm, tau_delay 등 hard-to-fit param에 유리)
- **Gaussian Process Regression**: data-driven function + uncertainty
- **Symbolic regression (PySR, SINDy)**: 데이터에서 explicit equation 발견 — interpretable

### E. Differentiable simulation
- **MJX (JAX MuJoCo)**: sim 자체 미분 → gradient SysID. Contact discontinuity 한계 but mass/inertia/damping에 적용 OK. **이전 GOAL4에서 V15 robust 부분 재현**.
- **Brax / Warp / Newton**: 대안 diff sim 프레임워크

### F. Statistical analysis (★ phase 순서 결정에 사용)
- **Sobol indices / Morris screening**: axis별 sensitivity 정량화 — 어떤 axis가 가장 영향력? **Phase 순서 결정 가이드** (현재 ranking은 직관 기반 — Sobol로 정량 검증)
- **Active learning (ASID Fisher info)**: 정보 가치 큰 trial / 시점 선택 → BO sample efficient ↑
- **Bayesian model selection (AIC/BIC)**: axis keep/drop 통계적 결정 (drop-test 보완)
- **Leave-one-trial-out CV**: 9 trial 중 1개 hold-out → 일반화 검증 (overfit 방지)

### G. Hybrid / ensemble
- **Method 비교**: 같은 axis에 TPE + CMA-ES + classical 동시 적용 → 결과 일치도 검증 (consensus)
- **Model averaging**: 여러 best의 ensemble (weighted by holdout score)
- **Warm-start chaining**: 이전 phase best → 다음 BO 초기 trial (Optuna `enqueue_trial`)
- **Bilevel optimization**: outer = axis 조합 선택 (categorical) / inner = 그 조합에서 BO

### Method 선택 가이드 (phase별 추천)
| Phase axis | 추천 method (1순위 → 2순위) |
|---|---|
| 1. solref/solimp | CMA-ES (correlated params) → TPE 검증 |
| 2. μ_floor | Random / grid (1D scan, 단순) → TPE refine |
| 3. armature | Least-squares (linear-in-param) → BO 비교 |
| 4. damping | Least-squares + TPE |
| 5. motor_tm | TPE + NARX/GRU 비교 (lag dynamics) |
| 6. tau_scale | 1D scan + Sobol sensitivity |
| 7. tau_delay | TPE + delay-specific NARX |
| 8. m_foot_extra | TPE (단순 1D) |
| Late phase | Actuator NN residual learning |
| 모든 phase | LOTO CV + Sobol sensitivity |

각 phase 페이지에 **"방법 비교 표"** 추가 (사용한 method, score 결과, 일치도). MASTER_INSIGHTS_G9에도 method 결과 누적.

---

## 🛠️ 코드 패턴 재사용 위치 (이전 GOAL 작업 검증된 파일)

| 작업 | 참고 파일 |
|---|---|
| **Mode A τ_real source** | `C:\Users\junho\Desktop\jump_opt\goal5\phase0_data_load.py` (paper_a_hat, sgn(v) only) — **★ TRIALS_DIR을 26.04.24로 변경**, TRIALS 리스트 9개로 update, `Real Data.txt` parse 추가 |
| **데이터 npz** | 신규 `goal9/data_loaded_26_04_24.npz` 생성 (Phase 0에서). `tau_real`, `q`, `dq`, `grf_z`, **`h_real_per_trial`** 포함 |
| **Reference NLP (h target)** | `C:\Users\junho\Desktop\jump_opt\no_cvt_alphaonly\jump_no_cvt_alphaonly_results.xlsx` |
| **Base XML 시작점** | `C:\Users\junho\Desktop\jump_opt\goal6\stage53\urdf\leg_g6s53_best.xml` (모든 추가 axis 0/∞ reset 후 cylinder foot 추가) |
| **Mode A sim 패턴** | `stage53_modeA_dt_large.py` (`run_trial`, `score`) — ctrl = tau_real ×... |
| **4-panel compare plot** | `goal6/gen_compare_plots_v3.py` (V20 convention, sim 점선) |
| **V25 animation** | `goal6/gen_anim_v4_clean.py` (80f, 60ms, malgun.ttf) |
| **MuJoCo 용어 정리 block** | `goal6/add_mujoco_param_explanations.py` (11항목 template) |
| **Notion 페이지 생성** | `goal6/stage{N}_plots_and_notion.py` (file_uploads 3-step + verify) |
| **BO Optuna** | TPESampler, n_trials=200–400, warm start from prev best |

### Notion infra
- Token: `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`
- CONCEPT parent: `115ab81d255080fdaae6f28f55e3e205`
- **GOAL9 parent** (Phase 0에서 생성, CONCEPT 아래): Title = `"GOAL9 — Mode A Digital Twin (Base-up, Cylinder)"`. ID는 MASTER_INSIGHTS_G9.md 최상단에 기록.

---

## 🚦 7일 자율 Loop 가이드 (2026-06-09 KST ~ 06-16 12:00 KST)

### 진행 cadence
- **6시간 checkpoint** (★ wall-clock 주기, phase 진행과 별도):
  - **목적**: 7일 자율 loop 중 작업 손실 방지 + 진행 가시화 + 자동 commit + verify
  - **실행**: phase 중간이라도 6h timer hit → 다음 BO trial / sim 완료 후 즉시 break하여 보고
  - **보고 내용**:
    - 현재 phase 진행률 (시작 / BO 진행 / drop-test / 노션 페이지 작성 / commit)
    - 누적 keep axis 수 / drop axis 수
    - 9 trial 평균 score (Base 대비 변화 %)
    - 점프 높이 평균 |Δh| (★ 1순위 metric)
    - Foot penetration max (mm)
    - 다음 6h 계획 (axis 후보 + 시도할 method)
  - **자동 작업**:
    - MASTER_INSIGHTS_G9.md commit
    - 모든 노션 phase 페이지 image block verify
    - git commit "GOAL9 checkpoint t+Nh"
  - **빈도**: 7일 / 6h ≈ **28 checkpoint**. Phase가 6h보다 짧으면 phase 종료 시점에 checkpoint 통합. Phase가 6h보다 길면 mid-phase 보고.
- **24시간 daily summary**: 매 24시간마다 (4번째 checkpoint)
  - 누적 keep axis 수 + drop axis 수
  - 9 trial 평균 score (Base 대비 %) + 1순위 metric 변화
  - 누적 axis ranking (영향력 순)
  - 다음 24시간 계획 (axis 후보 + method)

### 종료 조건
1. **시간 도달**: 2026-06-16 12:00 KST → Phase Final 정리
2. **Plateau**: 3 phase 연속 keep 결과 score < 3% 개선 → Phase Final 정리
3. **사용자 interrupt**: 즉시 현재 phase 마무리 + 종료

### Phase Final (종료 시)
- 모든 keep axis 통합 XML `goal9_final/leg_g9_final.xml`
- 9 trial 최종 결과 (score, h, RMSE, penetration, GRF)
- 통합 노션 페이지 "Phase Final — Summary" + ablation 표 (각 axis 기여도)
- MASTER_INSIGHTS_G9.md 최종 정리

---

## 📌 매 phase 종료 self-check (★ 모두 통과)

- [ ] 외부 출처 ≥ 3 (URL + 인용 + paper title) MASTER_INSIGHTS_G9에 기록
- [ ] Base vs This Stage 비교 표 노션 페이지에 ★
- [ ] MuJoCo / 모델 용어 정리 노션 페이지에 ★
- [ ] 4-panel compare plot 9 trial 모두 (q/dq/τ/GRF, auto color, sim 점선)
- [ ] V25 animation 80f 60ms 1+ trial
- [ ] h_sim vs h_real per-trial 표 + RMSE 3cm 이내 (1순위 metric)
- [ ] GRF band 25% 이내 분석 (per-trial)
- [ ] Foot penetration < 2mm 모든 trial (★ 사용자 명시)
- [ ] Drop-test 결과 keep/drop 명시 (3% threshold)
- [ ] Notion 페이지 image block 개수 = 업로드 개수 verify
- [ ] MASTER_INSIGHTS_G9 append 완료
- [ ] git commit "GOAL9 Phase N — [axis]: keep/drop"

---

## 🚀 시작 trigger + Phase 0 즉시 task list

### 시작 시 즉시 수행 (이 순서대로)

#### Step 1 — 읽기 (모두 verbatim)
1. 이 prompt (`GOAL9_PROMPT.md`)
2. memory:
   - `mode_A_purpose.md` (★ 가장 중요)
   - `ak80_9_torque_calibration.md`
   - `real_jump_heights.md`
   - `mujoco_range_bug.md`
   - `feedback_pure_paper_formula.md`
   - `feedback_notion_workflow.md`
   - `feedback_plot_colors.md`
   - `feedback_notion_image_upload.md`
   - `feedback_notion_image_verification.md`
3. `C:\Users\junho\Desktop\jump_opt\goal5\phase0_data_load.py` (paper_a_hat 함수 + 9 trial loader)
4. `C:\Users\junho\Desktop\jump_opt\goal6\stage53\urdf\leg_g6s53_best.xml` (XML reset 시작점, 모든 axis 0/∞)
5. `C:\Users\junho\Desktop\jump_opt\goal6\stage53_modeA_dt_large.py` (Mode A sim 패턴 + score)
6. `C:\Users\junho\Desktop\jump_opt\goal6\gen_compare_plots_v3.py` (4-panel plot)
7. `C:\Users\junho\Desktop\jump_opt\goal6\gen_anim_v4_clean.py` (V25 anim)
8. `C:\Users\junho\Desktop\jump_opt\goal6\add_mujoco_param_explanations.py` (용어 template)

#### Step 2 — 인프라 생성
1. **`MASTER_INSIGHTS_G9.md` 신규 생성** (`C:\Users\junho\Desktop\jump_opt\MASTER_INSIGHTS_G9.md`)
   - 헤더: GOAL9 mission 요약, 진행 기간, 우선순위
   - 자리 mark: parent Notion page ID, 9 trial info, Base Model 정의
2. **GOAL9 parent Notion page 생성** (CONCEPT `115ab81d255080fdaae6f28f55e3e205` 아래)
   - Title: `"GOAL9 — Mode A Digital Twin (Base-up, Cylinder)"`
   - 본문: mission, 우선순위, phase 진행 방식, 진행 중 page 링크 자리, 7일 종료일
   - Page ID를 MASTER_INSIGHTS_G9.md 최상단에 기록

#### Step 3 — Phase 0 실행
1. 새 directory: `C:\Users\junho\Desktop\jump_opt\goal9\phase0\`
2. **Base XML 작성** (`goal9/phase0/leg_g9_base.xml` 또는 build_xml 함수):
   - CAD inertia (M=1.02, m1=1.05213, ...), fl_hip=fl_knee=0.1
   - Cylinder foot: `fromto="0 -0.0065 0  0 0.0065 0" size="0.021" pos="0 0 -0.25"`
   - Floor + foot의 solref/solimp = MuJoCo default (`"0.02 1"`, `"0.9 0.95 0.001 0.5 2"`)
   - 모든 다른 axis 0/∞/identity
3. **Run script** (`goal9/phase0/run_baseline.py`):
   - data_loaded.npz의 tau_real 9 trial load
   - run_trial_modeA: T_settle (0.4s static PD hold) → T_motion (tau_real apply) → T_after (0.2s)
   - log q/dq/tau_filt/grf_z/foot_penetration
4. **Metrics 계산**:
   - per-trial RMSE q1/q2/dq1/dq2/τ1/τ2
   - h_sim = max(base_z) + 비행 phase ballistic
   - h_real per-trial (Real Data.txt 또는 memory)
   - GRF peak sim vs real
   - foot penetration max mm
5. **4-panel plots 6장 + V25 anim 1+ trial 생성**
6. **Notion 페이지 "Phase 0 — Base Baseline"** (GOAL9 parent 아래):
   - Locked Template 모든 section
   - Base vs Base (reference 형식)
   - MuJoCo 용어 정리 ★
   - 결과 표 + h_real vs h_sim + GRF + penetration
   - 모든 plot/anim 첨부 + verify
7. **MASTER_INSIGHTS_G9 update**: `## Phase 0 — Base Baseline` section
8. **git commit** "GOAL9 Phase 0 — Base baseline established"

#### Step 4 — Phase 1 자동 시작
1. WebSearch + GitHub fetch (solref/solimp priors, ≥ 3 sources)
2. MASTER_INSIGHTS_G9 `## Phase 1 — solref/solimp` section 작성 (외부 출처 + prior range)
3. BO script `goal9/phase1/bo_solref.py`:
   - Optuna TPE, n_trials=400, warm start from Phase 0
   - Search: `solref_tc, solref_d, imp_0, imp_1, imp_mid`
   - Score function (위 정의)
4. BO 실행 → best XML → 9 trial sim
5. Drop-test: solref/solimp을 default로 되돌린 sim → score 비교
6. Notion 페이지 "Phase 1 — solref/solimp"
7. MASTER_INSIGHTS_G9 BO 결과 append + commit

### 이후 자동 진행
- Phase 2 ~ Phase N (axis ranking에 따라)
- 6시간 checkpoint + 24시간 summary
- 종료 조건 도달까지 자율 진행

---

## 📚 외부 참고 자료 (Phase 1+ 검색 시작점)

### Papers
- Hwangbo et al. 2019 — "Learning agile and dynamic motor skills for legged robots" *Sci. Robotics*. DOI: 10.1126/scirobotics.aau5872
- Tan et al. 2018 — "Sim-to-Real: Learning Agile Locomotion For Quadruped Robots" *RSS*
- Park, Wensing, Kim 2021 — MIT Cheetah 3 / Mini Cheetah
- Raibert 1986 — *Legged Robots That Balance* MIT Press
- Lee, Hwangbo et al. 2020 — "Learning quadrupedal locomotion over challenging terrain" *Sci. Robotics*
- Howell, Tassa et al. 2022 — "Predictive Sampling: Real-time Behavior Synthesis with MuJoCo"

### Repos (clone 또는 fetch)
- `google-deepmind/mujoco_menagerie` (Unitree Go1, Spot, ANYmal C, Cassie, H1)
- `leggedrobotics/legged_gym`
- `google/brax`
- `Improbable-AI/walk-these-ways`
- `cassie-mujoco-sim`
- `kbieging/cassie_mj_description`

### MuJoCo docs
- Modeling: https://mujoco.readthedocs.io/en/stable/modeling.html
- XML reference: https://mujoco.readthedocs.io/en/stable/XMLreference.html
- Computation: https://mujoco.readthedocs.io/en/stable/computation.html (solref, solimp 식)

### AK80-9
- T-Motor datasheet (V2)
- Neurobionics Lab GitHub: https://github.com/neurobionics/TMotorCANControl
- UMich AK80-9 a_hat 회귀: `src/TMotorCANControl/test/mit_can/derive_torque_constants.py`

---

**Mission start.**
