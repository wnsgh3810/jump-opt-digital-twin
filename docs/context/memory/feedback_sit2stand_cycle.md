---
name: sit2stand-cycle-definition
description: sit2stand 데이터 cycle 정의 — valley-based motion + ±0.5s pad + sim 전 real data 검증 필수
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

**규칙**: sit2stand 데이터를 cycle로 분할할 때 반드시 다음 알고리즘 사용:

1. **Cycle 정의**:
   - **valley-based** (sit_bottom 기준): `find_peaks(-q2_smooth, distance=2*fs, prominence=0.5, height=2.0)`
   - 각 valley 주변 motion 시작/끝 검출: `q2 ≈ stand_q2 (-1.571)` + `|dq2| < 0.05 rad/s`
   - **양쪽 0.5s padding** (사용자 명시, "약간의 시간만")

2. **★ 절대 위반 X**:
   - Cycle 길이 통일 X (자연스러운 길이 — 데이터가 점점 빨라지는 경우 cycle 길이도 점점 짧아짐)
   - 한 cycle 안에 valley 정확히 1개 (multi-valley cycle 절대 X)
   - peak-to-peak X (반대 방향 motion 합쳐짐), trough-to-trough X (sit→stand→sit 동시 포함)

3. **★ Sim 전 real data 검증 필수** (사용자 ultrathink):
   - 각 cycle 자르고 real q2 시계열 추출
   - 검증: `n_minima_in_cycle == 1`, `n_maxima_in_cycle == 0`, `q2_start ≈ -1.57`, `q2_end ≈ -1.57`, `q2_min < -2.4`
   - 검증 통과 후에야 sim 실행
   - Sim으로 cycle 검증 X (real data only)

4. **Animation duration**: 데이터가 점점 빨라지는 구조면 `anim_play_time = cycle_duration × 1.5x slow proportional` (모든 cycle 동일 play time X)
   - sit2stand_gnd_0319: 점점 빨라짐 (8.71s → 1.58s) ★ 확인됨
   - sit2stand_0324: 점점 빨라짐 (8.6s → 1.6s, 5 subfolder 모두) ★ 확인됨 (사용자 명시 2026-06-23)

5. **★ Self-verify per cycle (사용자 ultrathink 명시 2026-06-23)**:
   - 각 cycle 자른 후 즉시 검증: n_minima==1, n_maxima==0, q2_start/end ≈ STAND, q2_min < -2.4
   - FAIL이면 그 cycle 영구 skip (sim X)
   - 사용자가 cycle 잘못된 거 직접 발견하지 않게 자동 detect

6. **★ 공중 (air) 데이터 base 모델링 (사용자 명시 2026-06-23)**:
   - sit2stand_air_0319, sit2stand_0324 = 외부 fixture로 base 공중 매달림
   - sim XML: `<joint name="base_z" type="slide" axis="0 0 1" range="0 0"/>` (완전 freeze)
   - floor z=-10 (foot 절대 안 닿음)
   - 지면 (gnd) 데이터는 base_z slide free + foot floor contact

7. **★ Anim 저장 방법 (2026-06-23 P10_D0 bug 발견)**:
   - ❌ `FuncAnimation(blit=True) + PillowWriter` 절대 X (PIL palette bug, 모든 frame이 한 frame만 반복 저장)
   - ✅ **`imageio.mimsave(path, frames, duration=FRAME_INTERVAL_S)`** 사용
   - frames = list of numpy arrays (MuJoCo Renderer 출력)

8. **★ MuJoCo Renderer camera (2026-06-23)**:
   - base_z=1.5m 공중 고정 시 camera `lookat=[0,0,1.0]` (robot base 중심) — world origin 보면 robot 화면 밖
   - distance=1.4, azimuth=135, elevation=-15

**Why**:
- 사용자 명시: "각도가 한 번 왔다갔다 하는 구간만"
- 점점 빨라지는 데이터 (sit2stand_gnd_0319: 8.71s → 1.58s)에 동일 play time = 부자연스러운 slow motion
- Sim으로 cycle 검증 = 시간 낭비, real data로 충분히 검증 가능
- Multi-valley cycle = sit-stand 여러 번 한 cycle에 들어가서 분석 무의미

**How to apply**:
- 모든 sit2stand 데이터 cross-validation에 동일 적용
- Sub-agent 위임 시 spec에 정확히 명시 (이전 5번 cycle 잘못 정의 후 사용자 반복 지적)
- 참조: `goal16/cross_validation_clean/sit2stand_gnd_0319/cycle_final.npz` + `real_plots/`

관련: [[mode_A_purpose]] (Mode A 디지털 트윈, sit2stand에서 한계 노출 발견)

---

## 2026-06-22 Mode A + Mode B sim 결과 (sit2stand_gnd_0319)

**검증된 cycle**: 15개 (real data only), durations [8.712, 4.878, 3.616, 2.974, 2.586, 2.330, 2.146, 1.996, 1.866, 1.814, 1.748, 1.694, 1.632, 1.632, 1.578] s

**LOCK 유지** (변경 X): Iter56 17D 전체, q-offset=0, tau_scale=1.0, arm_hip=0, paper_a_hat Pure Paper (sgn(v)) — GitHub s(v) smoothing 금지

**Mode A** (paper_a_hat τ direct, 0.68 min):
- q1 RMSE 0.37-2.24 rad, q2 2.53-5.49 rad, dq2 4.6-14.2 rad/s, GRF 23-102 N, pen 2.2-16.0 mm
- τ RMSE ~0 (직접 입력) but q/dq 누적 drift → 디지털 트윈 한계 노출
- 15/15 발산 없음

**Mode B** (PD KP=40 KD=0.7, settling 5s = Phase A 1s @500/10 + B 4s @2000/50 + trans 1s @2000/50, dt=0.0005, 44 s):
- q1 mean 0.0345 rad, q2 0.0744, dq1 0.279, dq2 0.544, τ1 1.66 Nm, τ2 1.85 Nm, GRF 12.91 N, pen_max 1.30 mm
- Per-cycle trend: cycle 00 (q1=0.027) → cycle 14 (q1=0.046, dq2=1.84) — 빠른 motion → PD tracking error 자연 증가
- 15/15 PASS

**Mode A vs Mode B**: q1 22x 차이 (0.76 vs 0.0345 rad) — 환경 차이만으로 (LOCK 17D 동일).

**산출물**:
- `goal16/cross_validation_clean/sit2stand_gnd_0319/mode_A/{plots,anim,sim_data}/cycle00-14.{png,gif,npz}` + `metrics_modeA.json`
- `goal16/cross_validation_clean/sit2stand_gnd_0319/mode_B/{plots,anim,sim_data}/cycle00-14.{png,gif,npz}` + `metrics_modeB.json`
- Scripts: `run_mode_A.py`, `run_mode_B.py`

**Notion**: page `387ab81d-2550-819c-8d40-edb1205e61a0`, 60 image (30 png + 30 gif) 첨부 검증 완료.

---

## 2026-06-23 ★ Sub-agent inconsistency 발견 + Reference clone 원칙

**문제**: 동일 작업 (sit2stand_0324 5 subfolder cross-validation)을 5개 sub-agent에 위임 → 같은 spec이라도 sub-agent마다 미세하게 다르게 구현 → 일부 bug 발생.
- **P10_D0 v2 bug**: `imageio.mimsave` 사용 → palette 변환 우려
- **P30_D1 v2 bug**: 일부 cycle에서 sim 첫 frame이 leg-extended (다리 펴진 상태) → coord 변환 적용 미스

**해결**: 정상 작동 reference (P20_D1 v2 page `387ab81d-2550-8109-8dc2-d26c0aa96d02`)의 script 5개 (`run_modeAB.py`, `detect_cycles.py`, `finalize_*.py`, `_detect.py`, `notion_upload.py`)를 **통째로 clone** → PD gain (KP/KD_h/KD_k)과 경로만 minimal diff 수정 → 두 페이지 spec 완전 동일 보장.

**결과 (2026-06-23)**:
- P10_D0 v3: `387ab81d-2550-8117-a0e1-d4ebfb79cc2b` (9 valid, 36 images, q2_sim[0]=-1.55 정상)
- P30_D1 v3: `387ab81d-2550-8178-af83-cefec74a31aa` (15 valid, 60 images, q2_sim[0]=-1.5671 정상)
- 두 페이지 모두 PillowWriter + coord 변환 정상 (P20_D1 검증 패턴 carryover)

**★ 원칙 (사용자 명시)**:
1. 동일 작업 N회 반복할 때 sub-agent 위임 X — **정상 reference clone**이 가장 안전
2. Clone diff는 PD gain, 경로, 페이지 ID 같은 minimal change만
3. Sub-agent 위임 시에도 reference path 명시 ("**P20_D1 script을 그대로 복사**" 식 명령)
4. v2 archive + v3 신규 패턴 유지 (image 재업로드 보장)

**Why**: Sub-agent는 같은 spec을 받아도 LLM 비결정성으로 미세 다른 구현 생성. Bug detect 어렵고 user가 직접 발견할 때까지 잠복. Reference clone은 비결정성 제거.

관련: [[feedback_notion_image_verification]] (이미지 업로드 검증 필수), [[mode_A_purpose]]

---

## ★ 2026-06-23 Canonical 코드 lock-in (사용자 명시)

**규칙**: sit2stand 작업 시 새 sub-agent가 cycle/sim/anim/plot/notion 코드 다시 작성 X. 검증된 reference를 verbatim 복사하고 데이터 경로 + PD gain만 변경.

### Reference 1: gnd (ground contact)
- 폴더: `goal16/cross_validation_clean/sit2stand_gnd_0319/`
- Notion: https://app.notion.com/p/Canonical-sit2stand_gnd_0319-cycle-sim-plot-anim-notion-reference-387ab81d255081fcac46f86d45b537b2 (page id 387ab81d-2550-81fc-ac46-f86d45b537b2)
- Base: slide free + foot cylinder floor contact + penetration 측정
- 검증된 cycle 15/15

### Reference 2: air (외부 fixture 매달림)
- Template 폴더: `goal16/cross_validation_clean/sit2stand_0324/P20_D1/` (★ ONLY verified canonical)
- Notion: https://app.notion.com/p/Canonical-sit2stand_0324-air-P20_D1-template-cycle-sim-plot-anim-notion-reference-387ab81d2550817dac48e3849583c590 (page id 387ab81d-2550-817d-ac48-e3849583c590)
- Base: slide range="0 0" weld + floor z=-10 untouched
- 5 subfolder all PD-gain-vary verified (P10_D0/P10_D1/P20_D1/P30_D1/P60_D1.5_P60_D2)

### ★ 다음 작업 시
1. cp -r template/ → new_folder/
2. sed로 data path + PD gain 4값만 교체 (KP_HIP_B/KP_KNEE_B/KD_HIP_B/KD_KNEE_B)
3. notion_upload.py OLD_PAGE_ID + 타이틀 갱신
4. Sub-agent에 "다시 작성" 위임 X — drift 발생
5. q2_sim[0] ≈ -1.567 (STAND -π/2) verify, leg-extended bug 자동 detect
6. Anim 첫 frame robot 보임 verify, 한 frame 반복 bug 자동 detect

### 7 카테고리 script 매핑 (둘 다)
- detect: `_detect.py` (valley find_peaks + raw cycle 자르기)
- cycle_verify: `detect_cycles.py` (self-verify per cycle, n_min/n_max/q2_start/end/q2_min)
- sim: `run_modeAB.py` (Mode A + Mode B + plot + anim 한 번에)
- finalize: `finalize_*.py` (summary.json + metrics_per_cycle + fail_details)
- plot: `run_modeAB.py` 내부 plot_fn (4-panel auto color)
- anim: `run_modeAB.py` 내부 anim_fn (PillowWriter + FuncAnimation, 1.5x slow)
- notion_upload: `notion_upload.py` (4 image group + file_uploads 3-step)

### ★ Verify 발견된 drift (참고용 — 다음 clone 시 회피)
- **P10_D0**: `_detect.py` suptitle/`_summary.json` PD_gain 문자열 stale (kp=20 잔존, 동작 무관 metadata bug). `finalize_p10d0.py` mean_q1/q2 의미 P20_D1과 다름 (trajectory mean vs RMSE).
- **P10_D1**: XML base_z slide range="-1e-9 1e-9" (3-DOF qpos, spec 위반 — spec은 "0 0" or weld), SETTLE/TRANS gains 약함 (50/2 → 200/10, spec 500/10 → 500/20), Panel 4 비교 그래프 다름, cycle_verified 흐름 별도 스크립트 분리. 사실상 별도 구현체 → clone X
- **P30_D1**: `notion_upload.py`만 rewrite (sim/cycle은 verbatim). 다음 clone 시 P20_D1 notion_upload 재사용 권장
- **P60_D1.5_P60_D2**: SETTLE_KP=2000/SETTLE_KD=50 (spec 500/20 위반), camera dist=1.2 (spec 1.4), cycle_verified 흐름 별도 스크립트. paper_a_hat 로컬 재정의 (import 안 함). detect/finalize 파일 셋 다름.
- **결론**: 진정한 verbatim canonical은 **P20_D1 + P30_D1 (sim/cycle만)**. 다음 air clone은 반드시 P20_D1 기준.

관련: [[feedback_notion_image_verification]], [[mode_A_purpose]], [[feedback_pure_paper_formula]]

---

## ★ 2026-06-23 Cross-references — Canonical 코드가 3 model × 5 dataset에서 사용됨

**Scope**: GOAL12 (Iter38, 11D) / GOAL14 (Iter32, 10D) / GOAL15 (Iter2, 12D) 세 best 모델을 각각 5개 데이터셋(sit2stand_air_0319, sit2stand_gnd_0319, sit2stand_0324 5 subfolder, jump_position_0421 6 sub, jump_torque_0422 3 sub)에 적용.

- **3 parent Notion page + 48 child page** 모두 success (sit2stand 21/21 + jump 27/27).
- **canonical sit2stand 코드** (gnd ROOT + 0324/P20_D1 air template)이 GOAL12/14/15 xval_v2 전 sit2stand 폴더에서 verbatim 재사용됨 — sub-agent rewrite 0건, drift 0건.
- 위치: `goal12/xval_v2/sit2stand_*/`, `goal14/xval_v2/sit2stand_*/`, `goal15/xval_v2/sit2stand_*/`
- 결과 요약: `MASTER_INSIGHTS_G9.md` 끝 "GOAL12/14/15 xval_v2 Cross-Validation Wrap-up" 섹션.

**Lesson reinforced**: 반복 sub-agent 위임에서도 canonical reference clone (P20_D1 air, gnd ROOT) 원칙이 16 × 3 = 48 case에서 0 drift로 검증됨. 이후 새 sit2stand 작업도 같은 패턴 강제.

관련: [[mode_A_purpose]] (cross-validation 결과로 본 Mode A 한계), [[feedback_notion_image_verification]]

---

## ★ 2026-06-23 Mode A 바닥 통과 bug (GOAL14/15) — GOAL12 참조 fix

**현상**: GOAL14 iter32, GOAL15 iter2의 Mode A sim에서 로봇이 바닥 통과 (penetration 큼). GOAL12 iter38는 정상 충돌.

**원인** (진단 후 확정): ★ 핵심 원인: **thigh / calf capsule의 contype/conaffinity 값 차이**. GOAL12 (iter38 + xval 둘 다)는 `contype="1" conaffinity="1"` — 즉 thigh/calf 캡슐도 floor와 충돌. GOAL14/15 (iter32/iter5 + xval 둘 다)는 `contype="0" conaffinity="0"` — foot 실린더만 충돌. Mode A에서는 실측 τ가 실제 로봇이 만든 contact force를 포함한 net torque이므로, 자유로운 다리에 그대로 입력하면 무릎/발이 floor를 향해 가속됨. GOAL12는 foot가 floor를 지나가도 calf capsule (radius 0.014m)이 floor에 걸려 다리 전체가 "걸리는" 시각효과 → "정상 충돌"처럼 보임. GOAL14/15는 foot cylinder가 회전·각도 어긋남으로 contact 회피하면 calf/thigh가 free로 floor를 뚫고 내려감 → "통과" 시각효과.

**Fix 위치**:
- `goal14/xval_v2/**/run_modeAB.py` (또는 run_cv_jump_*.py)
- `goal15/xval_v2/**/run_modeAB.py`
- 수정 헤더 코멘트로 표시됨 ("# FIX 2026-06-23: bottom-through fix")

**Fix 내용**:
- thigh capsule: `contype="0" conaffinity="0"` → `contype="1" conaffinity="1"`
- calf capsule: `contype="0" conaffinity="0"` → `contype="1" conaffinity="1"`
- (선택) GOAL14 sit2stand에서 `solver="Newton" iterations="200" tolerance="1e-10"` 제거 (학습-검증 일치)

**다음 sim 시 적용 규칙**:
1. 새 cross-validation 작성 시 GOAL12 `xval_v2/sit2stand_gnd_0319/` (또는 jump_*) 스크립트를 verbatim 차용
2. 모델 best params만 교체 (다른 environment/contact 설정은 LOCK)
3. Mode A τ 입력 시 paper_a_hat 적용 여부 모델 LOCK에 맞춰 결정
4. 첫 cycle (또는 첫 jump trial)에서 `pen_max < 5mm` verify — 초과 시 즉시 stop + 진단

**Why**: ★ 사용자 인지 검증: pen_max 수치만 보면 GOAL12가 가장 큼 (39.8mm Mode A) — 즉 "GOAL12=정상"은 visual perception이지 수치적 사실이 아님. 모든 모델이 Mode A에서 motion_realistic_count ~1/15로 leg가 거의 정지(q2_sim_excursion≈0). 이는 본질적으로 **Mode A 자체의 한계** (mode_A_purpose memo 참조). 시각적 차이는 GOAL12의 calf capsule이 floor와 충돌하여 leg가 buckled 자세로 "걸려있음", GOAL14/15는 leg가 free하게 floor 아래로 내려감.

**검증 risk**: m_calf=0.48 (GOAL15 iter5), m_thigh=0.60 (GOAL14 iter32)는 leg 충돌 없는 가정에서 학습된 fudge factor mass. contype=1로 바꾸면 학습-검증 불일치 risk — 동일 score 재현 여부는 재실행 검증 필요.

관련: [[mode_A_purpose]], [[mujoco_range_bug]]
