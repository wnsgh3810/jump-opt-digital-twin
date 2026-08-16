# GOAL18 — Unified Digital Twin (7 datasets, base-up, evolutionary)

> **시작**: 2026-06-23 04:30 KST
> **마감**: 2026-06-23 17:00 KST (≈ 12.5h 자율)
> **모드**: Mode A only (paper_a_hat τ input → 디지털 트윈)
> **데이터**: **7 데이터셋 통합** (sit2stand + jump 다 섞임)
> **기준점**: Pure base model (CAD + paper_a_hat, no fitted params)

ultrathink, 자율, continuous evolution, cron 기반.

---

## ★★★ NEVER-IDLE 규칙 (최상위)

1. **절대 "goal 완료" / "대기" / "사용자 confirm 기다림" 진입 X** — 17:00 KST cutoff 외에는 멈출 이유 없음.
2. **매 iter 즉시 다음 iter 결정** — 결과 보고서만 짧게 (≤200 words), 그 다음 즉시 axis 결정 + workflow launch.
3. **외부 search/research가 idle 아님** — Tier 2/3 axis 시 WebSearch ≥ 2-3 URL 항상 활용 (idle 시간 fill).
4. **막힘 시 sub-agent 위임** — 시간 낭비 없이 병렬.
5. **Score plateau (3 iter 연속 < 0.5% 개선) 시에도 stop X** — 다른 axis tier 진입 또는 stacked combination 시도.

---

## ★★★ 절대 금지 — 이전 GOAL의 "KEEP" 값을 LOCK으로 그대로 쓰지 마 (사용자 명시 2026-06-23)

**문제**: G7 motor_tm=8.37ms, G9 m_foot_extra ★ KEEP, G16 17D best 등을 그대로 LOCK으로 쓰면 새 데이터 (7 dataset 통합)에서 다른 optimal이 있을 수 있음.

**규칙**:
1. **이전 GOAL best는 starting point로만 사용**, 절대 fixed LOCK X
2. **매 axis마다 search/BO/NM/grid** 다시 수행 (새 데이터 7 dataset에서 optimal 확인)
3. **search 범위는 이전 best ± 50% (또는 더 넓게)** — 이전 발견과 다를 수 있음
4. **예외 (절대 LOCK)**: ctrl = -tau_real raw (어떤 modifier도 X — Mode A 본질), paper_a_hat=Pure Paper sgn(v) baked in tau_real (mode_A_purpose memo), thigh/calf contype 환경별 분리 — **sit2stand (air, gnd): contype=0 conaffinity=0 (canonical 그대로, goal16 P20_D1+gnd_0319), jump: contype=1 conaffinity=1 (cdcb1001 fix)**, L1=L2=0.25m + LC=0.03m (실측). **arm_hip은 fit axis로 포함** (사용자 정정 2026-06-23 — 이전 sub-agent 기록 잘못)
5. **재search 대상 (LOCK ❌, search ✓)**:
   - motor_tm (G7 8.37ms → 다시 search)
   - m_foot_extra (G9 KEEP → 다시 search)
   - solref_tc / imp0 / imp_mid (G9 KEEP → 다시 search)
   - dt / integrator (G9 Config D KEEP → 다른 config 다시 시도)
   - 17D global params (G16 Iter56 best → starting point, BO 다시)
   - CAD R/I/L per-component (G10/G12/G16 search → 새 데이터로 refit)
   - friction (G8 wider → 새 데이터로 다시)
   - stiff_hip / stiff_knee (G14 → 다시)
6. **결과 비교**: 이전 GOAL best vs GOAL18 best 표로 명시 (값이 얼마나 달라졌나)
7. **★ tau_scale (G9 KEEP)는 변수 자체 제거** — Mode A 본질 위반 (사용자 재명시 2026-06-23). BO/search 대상에서 영구 제외

---

## ★★★ MD 항상 read 규칙 (사용자 명시 2026-06-23)

**매 iter 시작 시 반드시 read**:
1. `C:/Users/junho/Desktop/jump_opt/GOAL18_PROMPT.md` (이 파일)
2. `C:/Users/junho/Desktop/jump_opt/MASTER_INSIGHTS_G18.md` (이전 iter 결과 누적)
3. `C:/Users/junho/Desktop/jump_opt/MASTER_INSIGHTS_G9.md` (이전 GOAL lessons, 참고)
4. memory `feedback_sit2stand_cycle.md` (canonical 코드 spec)
5. memory `feedback_plot_colors.md` (auto color + get_color())
6. memory `feedback_notion_image_upload.md` (file_uploads 3-step)
7. memory `mode_A_purpose.md` (Mode A 본질 LOCK)
8. memory `feedback_pure_paper_formula.md` (Pure Paper sgn(v))
9. memory `goal7_stage20_motor_tm.md` (motor_tm 이전 발견 — search starting point로만)
10. memory `digital_twin_priority.md` (priority 정정 사항)

read 결과 → axis 결정에 활용. **MD 안 읽고 iter 진행 X**.

**새 발견 발생 시 즉시 MASTER_INSIGHTS_G18 append** — 다음 iter에서 read 가능하게.

---

## ★★★ MD 활용 3-way (사용자 재명시 2026-06-23, ultrathink)

**참고 (Read) — 가이드로 활용**:
- 이전 GOAL의 axis history (예: G9 solref/solimp 큰 효과 발견 → GOAL18에서 우선 axis 후보)
- KEEP/DROP 결론 (어떤 axis가 효과 있었는지)
- 외부 research URL + paper title + 핵심 인용
- 물리 직관 (예: motor LPF AK80-9 1-50ms 범위가 일반적)
- 폐기된 가설 (saturation κ, smooth(v), tau_scale fudge 등 — 재시도 X)
- 발견된 bug + fix (contype=0→1, P10_D0 anim PillowWriter 등)

**그대로 사용 X — 숫자 LOCK 절대 X (사용자 명시)**:
- motor_tm = 8.37ms (G7 발견) → BO 범위 [1ms, 50ms] starting center 8ms ★ 새로 search
- m_foot_extra = 0.04kg (G9 KEEP) → BO 범위 [0, 0.5] starting center 0.04 ★ 새로 search
- 17D Iter56 best params (G16) → BO/NM starting point only ★ 다시 fit
- CAD R/I/L per-component (G10/G12/G16) → search ★
- solref_tc / imp0 / imp_mid (G9 KEEP) → ★ search
- dt/integrator Config D (G9) → 다른 config 시도 ★

→ **이전 best는 starting point + 직관 source일 뿐, fixed value 절대 X**

**즉시 정리 (Write append) — 매 iter 새 발견 시**:
- 새 axis 효과 (KEEP/DROP + score 변화 %)
- 폐기된 가설 (이 데이터에서 효과 없음)
- 외부 research 인용 (URL + 한 줄 요약)
- 코드 lesson (bug fix 또는 패턴 발견)
- 진단 (어느 trial에서 worst RMSE, 왜)

→ **MASTER_INSIGHTS_G18.md "## Iter[N]" section에 즉시 append**. 다음 iter cron fire에서 read해서 활용.

★ Recursive learning: read → fit → discover → write → 다음 iter read → ...

---

## ★★★ Sub-agent Verification Gate (사용자 비판 2026-06-23, 반복 spec 위반 lesson)

**매 iter 시작 시 sub-agent에 명시 (강제)**:
1. **Weight 절대 고정**: Wq=100, Wdq=50, Wh=200(jump only), Wt=0, Wgrf=0.1, Wpen=50. **사용자 명시. 자체 변경 X.** (Iter1에서 sub-agent가 Wq=1로 변경 — 잘못된 KEEP 판정 유발)
2. **31 sub 강제**: sit2stand 7 + jump 24 모두. **skip 절대 X.** (Iter2에서 sub-agent가 sit2stand 7 skip — partial 정보 기반 wrong conclusion)
3. **tau_scale axis 절대 사용 X**: Mode A 본질 (sub-agent가 next axis로 tau_scale 권장 시 무시 — Iter4에서 발생)
4. **canonical script verbatim**: sub-agent rewrite/skip 금지 (어제 cross-val lesson)
5. **Drop-test 강제**: 각 axis KEEP 판정 전, 그 axis 빼고 score 다시 계산. 단순 baseline 비교 X.
6. **n_sub_success verify**: 결과 JSON에 n_sub_success ≥ 31 확인. 미달 시 KEEP/DROP 판정 무효.

---

## ★★★ Final Wrap-up Spec (KST 16:30 직전 trigger)

cron prompt에서 KST > 16:30 감지 시:
1. **모든 iter 통합 best 모델 식별**:
   - KEEP chain stack 적용 (q_offset + motor_tm + m_base + solref + imp0 + 이후 KEEP axes)
   - DROP된 axes는 제외
2. **Unified weight 재계산**: 모든 iter score를 동일 weight로 재계산 (Iter0R/1 patched)
3. **Notion final summary 페이지** (GOAL18 parent 아래 child "Final"):
   - 모든 iter 표 (axis, KEEP/DROP, score, pct, params)
   - Best model 전체 params 표
   - 31 sub-experiment best model sim 결과 (RMSE, h_sim/h_real, pen)
   - 4-panel plot per sub + 6 anim (PillowWriter)
   - 다음 GOAL19 prompt 제안
4. **MASTER_INSIGHTS_G18.md** "## Final Wrap-up" section append
5. **git commit "GOAL18 Final wrap-up — best stack model"**
6. **CronList → CronDelete** (자율 cron 종료)

---

## ★★★ 노션 페이지 + child 활용 규칙

1. **GOAL18 parent (1)** — CONCEPT (115ab81d255080fdaae6f28f55e3e205) 아래 신규.
2. **매 iter = parent 아래 child 1개** (Iter0R, Iter1, Iter2, ..., IterN, Final). 절대 같은 페이지 update X — 매번 새 child.
3. **각 child 내 sub-child 적극 활용**:
   - 31 sub-experiment 각각 sub-child (옵션, 시간 여유 시) 또는 toggle block으로 expand
   - 외부 research URL 인용 sub-section
   - 코드 toggle block (sim script + plot script + anim script)
4. **이미지 group**: per-trial 4-panel plot + anim을 2-per-row column layout (memory: 사용자 선호 v5 split-plot style)
5. **표는 매번 만들기**:
   - Base vs This iter 비교 표 (★ 사용자 명시)
   - MuJoCo 용어 정리 표 (★ 사용자 명시 11항목)
   - 31 sub-experiment per-trial RMSE 표
   - h_sim vs h_real 표 (jump only, 사용자 명시 1순위)
   - GRF 표 + penetration 표 (gnd only)

---

## ★★★ Plot / Anim 품질 — 최근 commit과 동일하게

**참조 commit**:
- `98af40b0` — sit2stand canonical 코드 lock-in
- `449e5e6e` — 48-page cross-validation (4-panel auto color)
- `cdcb1001` — contype=1 contact fix (★ **jump-only valid**; sit2stand는 canonical contype=0 그대로 — 2026-06-23 진단)

**Plot 매번 반드시**:
- 4-panel sharex (figsize=(11,12) or (11,13), dpi=110)
- Panel: [0] q1/q2 / [1] dq1/dq2 / [2] tau1/tau2 / [3] GRF or q_des 기준 궤적
- ★ **색 명시 X (auto cycle)** — memory `feedback_plot_colors`
- ★ **sim/real 매칭**: `lr, = ax.plot(t, q_real, ...); ax.plot(t, q_sim, color=lr.get_color(), linestyle='--')`
- Mode B q_des: 같은 색 dotted (`:` alpha=0.7)
- 한국어 라벨, malgun.ttf
- `axes.unicode_minus=False`

**Anim 매번 반드시**:
- ★ **PillowWriter + FuncAnimation** (NOT imageio for sit2stand — memory feedback_sit2stand_cycle PillowWriter 검증된 버전)
- SLOW_FACTOR=1.5, FRAME_INTERVAL_S=0.060
- n_frames = max(30, min(150, round(cycle_dur * 1.5 / 0.060))) — 1.5x slow proportional
- MuJoCo Renderer (height=400, width=600)
- camera: lookat=[0,0,1.2] (air) / [0,0,0.2] (gnd/jump), dist=1.4 (air) / 1.2 (gnd), azim=135, elev=-15
- overlay 한국어 텍스트 (white text on black 0.5-alpha bbox)

★ ★ 사용자 비판 (2026-06-23): "anim 일부 여백 보임" — 여백 없음 강제:
- `fig.add_axes([0, 0, 1, 1])`  # padding 0, 전체 figure 차지
- `ax.axis('off')`  # 축 표시 X
- overlay text는 `transform=ax.transAxes` 사용 (figure 좌표 X)
- `anim.save(... savefig_kwargs={'pad_inches': 0, 'bbox_inches': None})`
- canonical script (P20_D1 run_modeAB.py)의 make_anim_A/B 함수 그대로 사용 — 자체 코드 작성 X
- 검증: anim GIF 파일 size = (MuJoCo Renderer width × dpi/100) × (height × dpi/100) — 여백 없으면 비율 일치

★ **★★ 사용자 명시 (2026-06-23): "애니메이션 로봇이 땅으로 사라지지 않게" ★★**:
1. **시작 frame verify**: foot_min_z > floor_z (foot가 floor 위에 위치) — 시작 자세 통과 X
2. **진행 중 verify**: 매 frame max(foot_z) > floor_z - 0.005 (5mm tolerance) — anim 중 통과 검출
3. **통과 detect 시**: 그 cycle/trial의 anim 별도 label "★ FLOOR PENETRATION at t=X.XXs" 추가
4. **Camera**: robot이 항상 화면 안에 들어오게 (camera lookat을 robot base position에 동적으로 추적, base_z 변동 시 camera 따라감)
5. **Floor visualize**: anim에서 floor 평면이 보이게 (floor checkerboard 또는 회색 plane MuJoCo 기본 rendering)
6. **MuJoCo `geomgroup`**: floor는 group 0 (visible), thigh/calf/foot도 visible
7. **★ contype 환경별 verify** (2026-06-23 진단 후 정정):
   - **sit2stand XML (air, gnd)**: thigh+calf contype=0 conaffinity=0 (canonical P20_D1 / gnd_0319 그대로) — grep + assert
   - **jump XML** (commit cdcb1001): thigh+calf contype=1 conaffinity=1 — grep + assert
   - universal 적용 금지 (sit2stand에 contype=1 적용 시 WAIT pose self-collision 발생)
8. **Bottom-through bug catch**: anim 마지막 frame foot_z가 floor 아래면 자동으로 그 frame을 빨간색 outline + Notion 페이지에 ★ 경고 callout 추가

**Notion 이미지 upload (매번)**:
- file_uploads 3-step API (POST /file_uploads → multipart upload_url → image block file_upload)
- `time.sleep(0.35)` per file (rate limit)
- 끝나면 GET children → image count = expected verify (memory feedback_notion_image_verification)

---

## ★ 미션

GOAL12/14/15/16의 jump-only digital twin을 **sit2stand + jump 둘 다** 포함한 unified model로 확장. base-up 시작 (모든 fitted params reset). 이전 GOAL 작업에서 알아낸 사실들 (memory + MASTER_INSIGHTS_G9~G17) 하나씩 reflective하게 반영. 매 iter마다 노션 페이지 + commit. cron으로 한국시간 17:00까지 자율 진화.

---

## ★ 7 데이터셋

| Dataset | 종류 | 갯수 | 환경 |
|---|---|---|---|
| 26.03.19 sit2stand_air | sit2stand | 1 trial | base 공중 weld + floor z=-10 |
| 26.03.19 sit2stand_gnd | sit2stand | 1 trial | base slide free + foot floor contact |
| 26.03.24 sit2stand | sit2stand | 5 PD gain subfolders (P10_D0~P60_D2) | base 공중 weld |
| 26.04.21 jump_position | jump | 6 PD gain subfolders (P60~P200) | base slide free + foot contact |
| 26.04.22 jump_torque | jump | 3 torque levels (P40_D0.7/P70_D2/P100_D3) | base slide free + foot contact |
| 26.04.24 jump | jump | 9 trial (PD various) | base slide free + foot contact |
| 26.06.02 jump | jump | 6 trial | base slide free + foot contact |

총 ~31 sub-experiments (sit2stand 7 + jump 24). 각 trial별로 sim 실행 + RMSE 계산.

**★ 핵심 차이 주의** (이전 GOAL 작업에서 lock-in된 lesson):
- **sit2stand_air**: base 공중 weld (slide range="0 0"), floor z=-10 → GRF 없음, q2_des 만 추종
- **sit2stand_gnd**: base slide free, floor z=0, foot cylinder contact → 모든 metric 측정
- **jump**: base slide free, floor z=0, ballistic phase 발생 (foot 공중)

→ XML / settling spec이 **3가지 환경** 모두 정확하게 처리되어야 함. 어제 lock-in한 canonical (P20_D1 air + gnd_0319 + jump existing) 코드 verbatim 사용.

---

## ★ Base Model (Iter0R)

- CAD M1/M2/MP/MC/M_FOOT_EXTRA, R1/R2/RP/RC, I1/I2/IP/IC, L1=L2=0.25, LC=0.03
- paper_a_hat (Pure Paper, sgn(v) only — GitHub smoothing 절대 금지) — npz `tau_real`에 이미 baked
- ctrl_sim = -tau_real (sign flip only, NO scale modifier — Mode A 본질)
- arm_hip = default (BO/NM search 대상, 사용자 정정 2026-06-23 — Tier 1 #4d armature 그룹에서 fit)
- foot: cylinder 42×13mm, y-axis (lateral, hinge 평행)
- **★ thigh/calf capsule contype 환경별 (2026-06-23 진단 후 분리)**:
  - **sit2stand (air, gnd)**: contype="0" conaffinity="0" — canonical P20_D1/gnd_0319 그대로 (WAIT pose self-collision 방지)
  - **jump**: contype="1" conaffinity="1" — cdcb1001 fix (Mode A leg-floor 통과 방지)
  - universal 적용 절대 금지
- floor: type="plane", z=0 (gnd 모드)
- integrator: implicitfast, RK4 비교 가능
- 모든 fitted params 초기값: 0 / 1 / default

---

## ★ 우선 axis pool (자율 결정, 외부 research 활용)

### Tier 1 — 즉시 시도

1. **★ q1_offset / q2_offset** (사용자 명시: "각도가 한번만 왔다갔다 하는 구간만"이라는 이전 발견 + "q offset 최대 1° 가능")
   - per-trial bias [-1°, +1°]
   - sit2stand는 0, jump trials은 양/음 가능
2. **★ Foot 위치 offset** (사용자 명시)
   - foot pos x: ±5mm, foot pos y: ±5mm, foot pos z: ±5mm
   - per-trial or global
3. **★ Foot slip (foot 미끄러짐)** (사용자 명시)
   - friction_t (tangential): 기본 1.0 → [0.3, 5.0]
   - friction_r (rolling): 0 → 0.001-0.1
4. **★ CAD params 개별 수정** (사용자 명시)
   - L1, L2, LC: ±5mm fit
   - R1/R2/RC: ±10mm
   - I1/I2/IC: ±20%

### Tier 1 #4 — CAD per-component fit (★ 사용자 ultrathink 명시 2026-06-23)

**LOCK (실측 정확, 변경 X)**:
- L1 = L2 = 0.25m (thigh, calf length)
- LC = 0.03m

(★ arm_hip은 LOCK 아님 — Tier 1 #4d armature 그룹에서 fit. 사용자 정정 2026-06-23)

**Fit/Search 대상 (나머지 모든 CAD 파라미터, 오차 있을 수 있음)**:

4a. **Mass per-component** (각 ±15-20% search)
   - M_thigh ∈ [M_thigh_CAD × 0.85, × 1.15]
   - M_calf ∈ [M_calf_CAD × 0.85, × 1.15]
   - M_p (pulley) ∈ [× 0.8, × 1.2]
   - M_c (chain/contact) ∈ [× 0.8, × 1.2]
   - M_foot_extra ∈ [0, 0.5] kg (G9 발견 +16.55% but starting point만, BO 다시)
   - M_base ∈ [0.5, 2.0] scale (Iter4 이미 시도)

4b. **Inertia per-component** (각 ±20% search)
   - I_thigh ∈ [I_thigh_CAD × 0.8, × 1.2]
   - I_calf ∈ [I_calf_CAD × 0.8, × 1.2]
   - I_p ∈ [× 0.8, × 1.2]
   - I_c ∈ [× 0.8, × 1.2]

4c. **Center of Mass position per-component** (각 ±15% search)
   - R_thigh ∈ [R_thigh_CAD × 0.85, × 1.15] (link 시작점부터 COM까지 거리)
   - R_calf ∈ [× 0.85, × 1.15]
   - R_p ∈ [× 0.85, × 1.15]
   - R_c ∈ [× 0.85, × 1.15]

4d. **Armature + Motor rotor inertia** (★ 사용자 정정 2026-06-23 — arm_hip 추가)
   - **arm_hip ∈ [0.001, 0.05]** (motor rotor through gear at hip — AK80-9 rotor mass × gear_ratio² 반영)
   - **arm_knee ∈ [0.001, 0.05]** (rotor inertia × gear^2 reflected at knee joint)
   - motor_rotor_I ∈ [I_typical × 0.5, × 2.0] (별도, 또는 arm_hip/arm_knee로 통합 표현)

**물리적 의미**: AK80-9 BLDC motor rotor mass 상당 + gear ratio 9 → 반영 관성 의미 있음 (0 절대 아님). 이전 GOAL12 iter38 LOCK "arm_hip=0"은 sub-agent inference 오류였음.

**총 자유도**: 5 (mass) + 4 (inertia) + 4 (R) + 2 (arm_hip + arm_knee) = **15 CAD axes**

**Method**:
- 작은 묶음 (예: mass 4D NM, inertia 4D NM, R 4D NM)
- 또는 full 14D NM/CMA-ES (시간 budget 허용 시)
- ★ 이전 GOAL best 값은 starting point만, LOCK 금지 (사용자 명시)

5. **17D global params** (GOAL16 lock-in)
   - m_thigh_scale, m_calf_scale, m_base, fv/fc_hip/knee, solref_tc, imp0, imp_mid, stiff_hip/knee, etc.

### Tier 2 — 외부 research 후 시도

6. **Stribeck friction** (sit2stand 저속 + jump 고속 결합) — memory에 미시도
7. **Actuator NN residual** (memory G13에 시도하다 만 task)
8. **motor LPF (motor_tm)** — 8.37ms 발견 (memory `goal7_stage20_motor_tm.md`)
9. **m_foot_extra** (G9에서 +16.55% 효과 검증)
10. **Foot 2-point heel/toe** (sphere 대신) — G10 후보
11. **Flex joint compliance** — G10 사용자 highlight

### Tier 3 — 더 깊은 axes

12. **Per-PD αkp/αkd scaling** (G8 lesson)
13. **Sensor delay** (G8 lesson)
14. **Gear backlash** (G8 lesson)
15. **Implicit/elliptic cone + impratio=100** (G7 stage11)

---

## ★ 절대 규칙 (이전 lessons 누적)

1. **★ thigh/calf capsule contype 환경별 (2026-06-23 진단)**:
   - **sit2stand (air, gnd)**: contype=0 conaffinity=0 (canonical 그대로 — WAIT pose self-collision 방지)
   - **jump**: contype=1 conaffinity=1 (cdcb1001 fix — Mode A에서 leg floor 통과 방지)
   - universal 적용 절대 금지
2. **★ Mode A LOCK**: ctrl = -tau_real raw (sign flip only, 어떤 modifier도 X), paper_a_hat Pure Paper sgn(v) baked in tau_real, **thigh/calf contype 환경별** (jump=1, sit2stand=0 — 2026-06-23 정정), arm_hip은 fit axis (사용자 정정 2026-06-23)
3. **★ CAD L1/L2/LC**: 실측이라 거의 LOCK, ±5mm fit만 허용
4. **★ Foot cylinder 42×13mm y-axis** (사용자 명시 26.06.09)
5. **★ Sit2stand cycle**: valley-based motion + ±0.5s pad + self-verify per cycle (n_min=1, n_max=0, q2_start/end≈STAND, q2_min<-2.4)
6. **★ Sit2stand canonical**: P20_D1 (air weld) + gnd_0319 (gnd contact) verbatim
7. **★ Anim**: PillowWriter + FuncAnimation (NOT imageio for sit2stand sub-folder canonical) — gnd_0319도 PillowWriter
8. **★ Camera**: lookat=[0,0,1.2] (air) or [0,0,0.2] (gnd), dist=1.4 (air) / 1.2 (gnd), azim=135, elev=-15
9. **★ Coord 변환**: q1_sim = -q1_real - π/2, q2_sim = -q2_real, dq*_sim = -dq*_real, tau_input_sim = -tau_real
10. **★ Plot**: 4-panel, matplotlib 색 명시 X (auto cycle), sim/real 매칭 get_color() (memory feedback_plot_colors)
11. **★ Anim 1.5x slow proportional** (점점 빨라지는 cycle 데이터)
12. **★ Notion 이미지**: file_uploads 3-step + 0.35s rate limit (memory feedback_notion_image_upload)
13. **★ Notion verify**: GET children 후 image block 개수 = expected (memory feedback_notion_image_verification)
14. **★ saturation κ 가설 폐기** (G7~G9 검증)
15. **★ csv `Paper` column 사용 금지** — npz `data_loaded.npz['tau_real']` 단일 source
16. **★ smooth(v) 금지** — Pure Paper sgn(v) only (memory feedback_pure_paper_formula)
17. **★ MuJoCo XML range** "-3 3" 금지 (memory mujoco_range_bug — V20 init artifact)

---

## ★ 점수 함수 (★ 2026-06-23 사용자 priority 정정 반영)

### 사용자 명시 priority (절대 변경 X)

**1순위 (최우선)**:
- **q1, q2** (joint angle) — 매칭 핵심
- **dq1, dq2** (joint velocity) — 매칭 핵심 (q와 동등 중요)
- **h_jump** (jump trial 한정, max base_z) — jump 1순위

**2순위 (부수적)**:
- **tau1, tau2** (Mode A에서 입력이라 RMSE ≈ 0 자동, score 의미 X)
- **penetration** (땅 통과 방지 — 사용자 명시 "애니메이션 로봇이 땅으로 사라지지 않게")

**3순위 (참고용, 엄청 중요 X)**:
- **GRF** — 사용자 명시 "엄청 중요한 거 아님"

### 새 score function (GOAL18 v2)

```
score_total = Σ_trial [
    Wq1 * RMSE(q1_real, q1_sim)             # 1순위
  + Wq2 * RMSE(q2_real, q2_sim)             # 1순위
  + Wdq1 * RMSE(dq1_real, dq1_sim)          # 1순위 (q와 동등)
  + Wdq2 * RMSE(dq2_real, dq2_sim)          # 1순위
  + Wt1 * RMSE(tau1_real, tau1_sim)         # Mode A 자동 ≈ 0, score 무의미
  + Wt2 * RMSE(tau2_real, tau2_sim)         # Mode A 자동 ≈ 0, score 무의미
  + Wh * |h_sim - h_real|                   # 1순위 (jump only)
  + Wgrf * max(0, GRF_dev_pct - 0.25)^2     # 3순위 (gnd only, 매우 약함)
  + Wpen * max(0, pen_mm - 2.0)             # 2순위 (gnd/jump, 땅 통과 방지)
]
```

**Weights (v2.1, 사용자 priority 정정 2026-06-23)**:
- **Wq1 = Wq2 = 100** (1순위)
- **Wdq1 = Wdq2 = 50** (1순위, q와 동등 priority — RMSE scale 고려 50)
- **Wt1 = Wt2 = 0** (Mode A 자동 ≈ 0, score 무의미 — ctrl = -tau_real 그대로 입력이므로 RMSE는 정의상 0)
- **Wh = 200** (★ jump only, 1순위, jump 한정 강화 — v2 100 → v2.1 200, sit2stand q-dominant score offset)
- **Wgrf = 0.1** (낮춤, "엄청 중요한 거 아님")
- **Wpen = 50** (높임, "땅으로 사라지지 X" 강하게 방지)

**Wh=200 변경 사유 (2026-06-23 사용자 ultrathink)**:
- sit2stand q RMSE × Wq=100 ≈ ~1000 scale 1순위 dominate
- jump h_gap 0.3m × Wh=100 = 30 → score 비중 너무 작음
- Wh=200 시 0.3m × 200 = 60 → 점프 1순위 적절히 반영, 그러나 여전히 sit2stand가 dominate 가능
- 차후 jump 매칭이 plateau 시 Wh 추가 상향 검토

**Score 적용 메모**:
- sit2stand trials: q + dq 매칭이 score dominate (tau는 Mode A 입력이라 0)
- jump trials: q + dq + h 매칭이 dominate
- GRF/penetration: 약한 정규화 (sim 발산만 방지)

---

## ★ Iter 진행 패턴 (매 iter strict cycle)

1. **MD read** (3-way 활용):
   - GOAL18_PROMPT.md (이 spec) — 참고
   - MASTER_INSIGHTS_G18.md last 5 sections — 참고 (이전 iter 발견 + KEEP/DROP)
   - MASTER_INSIGHTS_G9.md, memory feedback_*.md, mode_A_purpose.md 등 — 참고 (이전 GOAL lessons)
   - 이전 iter best params — **starting point만**, fixed value 사용 X
2. **Axis 결정** — Tier 우선 + 외부 research (WebSearch ≥ 2 URL Tier 2/3 시)
3. **`goal18/iterN/run_iN.py` 작성** — 17 strict 규칙 모두 준수
4. **Sim 실행** — 7 dataset × 31 sub-experiments 모두 + 검증
5. **★ 검증**:
   - sit2stand: q2_sim[0] ≈ -1.567 (STAND), n_cycles 정상 분할
   - jump: q*_sim[0] ≈ real, h_sim 발산 X, pen_max < 5mm
6. **Plot**: 4-panel per sub-experiment + 그룹 summary
7. **Anim**: MuJoCo Renderer + PillowWriter
8. **Notion child page** (Locked Template):
   - Mission/status callout
   - Base vs This iter 비교 표 ★
   - MuJoCo 용어 정리 ★
   - 변경 axis 상세 (From → To, 외부 URL, 물리 메커니즘)
   - per-trial RMSE 표 + h_sim vs h_real (jump) + penetration (gnd)
   - 4-panel compare plot 31장 (또는 dataset별 그룹)
   - V25 animation 일부 (시간 절약 위해 worst-3 + best-3만)
   - 결과 해석 + 다음 axis 후보
   - Drop-test 결과 (3% 미만이면 drop)
9. **git commit** — 즉시 즉시
10. **MASTER_INSIGHTS_G18.md append (★ mandatory)**:
    - "## Iter[N]" section append
    - 내용: axis 결정, 사용 params (이전 best 대비 차이 명시), score + KEEP/DROP, per-trial RMSE worst-3+best-3, 새 발견, 다음 axis 후보
    - **새 lesson** (외부 research, 폐기 가설, 코드 bug 등)도 별도 sub-section 추가
11. **즉시 다음 iter 또는 cron 다음 fire 대기**

---

## ★ Cron 자율 진행

매 시간 정각 + 13분 cron fire (UTC 20:13 ~ 07:13 = KST 05:13 ~ 16:13).
- 각 fire 시: read GOAL18_PROMPT.md + MASTER_INSIGHTS_G18.md → 마지막 iter 확인 → 다음 axis 결정 → 1 workflow 실행
- 시간 check: 현재 KST > 17:00이면 final wrap-up + CronDelete

---

## ★ 외부 Research 활용

각 Tier 2/3 axis 시 매번 WebSearch ≥ 2-3 URL:
- mujoco_menagerie (Go1/Spot/Go2 contact params)
- IsaacLab / legged_gym / Newton actuator models
- Hwangbo 2019, Park 2021, Raibert papers
- Stribeck friction (LuGre)
- MuJoCo 2025 best practices

URL 인용을 MASTER_INSIGHTS_G18에 명시.

---

## ★ Sub-agent / 하위 행동 활용

- Phase별로 sub-agent 위임 (sit2stand sim / jump sim / plot / anim / notion 각각)
- 단, **sub-agent rewrite 금지** — canonical script verbatim clone + data/params 만 교체 (어제 inconsistency bug lesson)
- 16-way 병렬 활용 (workflow concurrency cap)
- Sonnet sub-agents OK for heavy work

---

## ★ Notion 페이지 구조

GOAL18 parent (CONCEPT 아래 새로 생성):
- Iter0R 페이지 (Base baseline)
- Iter1 페이지 (axis 1)
- Iter2 페이지 (axis 2)
- ...
- Final wrap-up 페이지

각 iter 페이지 = Locked Template (위 9번)

---

## ★ 시작 trigger

지금 즉시:
1. `goal18/iter0R/` 디렉토리 + 데이터 unified loader (7 dataset 로드)
2. Pure Base model XML 작성 (CAD + paper_a_hat + **contype 환경별**: sit2stand XML contype=0 / jump XML contype=1 — 2026-06-23 진단)
3. 31 sub-experiment sim 실행
4. RMSE 계산 + score_total 계산 (baseline)
5. Notion parent + Iter0R child 페이지
6. MASTER_INSIGHTS_G18 신규 생성 + Iter0R section
7. git commit

이후 cron fire마다 다음 iter 진행 (axis 결정 → 실행 → 페이지 → 커밋).

---

## ★ 17:00 KST 최종 wrap-up

마지막 cron fire (또는 시간 check):
1. 모든 iter 결과 통합 (best iter, KEEP chain, drop axes)
2. Notion parent에 summary 표 (iter × score × KEEP × dataset별 best)
3. MASTER_INSIGHTS_G18 final section
4. git commit (final tag 또는 commit message에 ★ FINAL)
5. CronDelete (자동 + 명시적)

ultrathink, 자율, 끊김없이 계속, 사용자 답변 안 기다림.
