# GOAL5 (RESTART): MuJoCo Digital Twin Validation — 처음부터 제대로

**Model**: Sonnet OK
**상태**: GOAL5 V1-V9 시도 폐기. 처음부터 다시 시작. 모든 코드/모델/페이지 새로.

## ★ Mission Statement (변경 없음)

**MuJoCo sim이 실 robot처럼 움직이게 만든다.** Reference 적용했을 때, 실측 26.06.02 데이터와 **q/dq/τ/GRF가 매칭**되도록 환경 + robot model을 정확히 설정.

## ★ 이전 GOAL5 V1-V9에서 폐기할 잘못된 결론 (절대 반복 금지)

다음 결론은 **모두 틀림**:

1. ❌ **"PD ±18 Nm sat이 hard limit이라 환경 fit으로 못 줄임"**
   - **진실**: 실 robot도 ±18 Nm sat이었고 정상 동작. 만약 robot model 정확하면 같은 ref + 같은 PD + 같은 sat → 같은 motion. 즉 우리 sim이 sat에 막혀서가 아니라 **robot model이 잘못된 것**.

2. ❌ **"V20 자세가 PD-unstable이라 어쩔 수 없다"**
   - **진실**: 실 robot은 V20 자세에서 정확히 ref 따라가며 점프함. PD-unstable이 아니라 우리 MuJoCo 환경 자체가 잘못.

3. ❌ **"motor delay, Stribeck friction, gear backlash 등 정교화 필요"**
   - **진실**: 기본 MuJoCo 모델로도 실 robot처럼 움직여야 함. 정교화 전에 기본 model이 맞는지 검증.

4. ❌ **"GRF 매칭만 되면 OK"**
   - **진실**: GRF, τ, dq, q **모두** 매칭되어야 digital twin. GRF만 맞으면 우연일 가능성.

5. ❌ **"BO로 score 줄이면 best"**
   - **진실**: BO가 비현실적 fit (작은 foot, soft contact) 채택해서 바닥 뚫는 결과. 물리적 reasonable 제약 필요.

## ★ 진짜 원인 (사용자 ultrathink 검토 결과)

**Robot model이 실 robot과 다름**:
- Mass/inertia/com 부정확
- Joint friction 표현 다름
- Contact 모델 부적절
- 시작 자세에서 robot이 떨어짐 (정적 평형 못 잡음)

**부호 (sign) 검토 필요**:
- 좌표 변환 `q1_mu = q1_v20 + π/2`이 정확한지 ★ 검증
- dq, τ sign이 ref/actual/sim 모두 일치하는지 ★ 검증
- 만약 sim에서 robot이 ref와 다른 방향으로 움직이면 sign 반대로 보임 → robot model 잘못

**바닥 뚫림**:
- Contype/conaffinity 잘못 (link가 ground 충돌 안 함)
- Hard contact 안 적용 (penetration 허용)
- 시작 base_z가 너무 낮음 (robot이 즉시 ground 안에 들어감)
- 작은 foot_size (BO가 0.012 채택)

## ★ 새 접근 — Working Open Source 정확 따라

이번엔 **처음부터 검증된 open source** 정확 복사:

### 1순위: mujoco_menagerie Unitree Go1
- URL: https://github.com/google-deepmind/mujoco_menagerie/tree/main/unitree_go1
- 검증된 working environment
- Single-leg robot으로 단순화 (4 leg 중 1개 + base는 slide joint)

### 2순위: mujoco_mpc_deploy (사용자 강조)
- URL: https://github.com/johnzhang3/mujoco_mpc_deploy/tree/main
- Working PD tracking 확인
- 패턴 그대로 적응

### 3순위: mujoco_playground go1
- URL: https://github.com/google-deepmind/mujoco_playground/tree/main/mujoco_playground/_src/locomotion/go1
- MJX 환경 ref

## ★ Hard Constraints (재강조)

**금지**:
- ❌ 점프 높이 매칭 — wrong metric
- ❌ "PD sat 때문에 못한다" 변명
- ❌ "V20 자세가 unstable" 변명
- ❌ Reference 변경
- ❌ Robot이 바닥 뚫음 — sim이 비현실적이면 무조건 fix
- ❌ BO score 최소화만 추구 — 물리적 reasonable 검증 필요

**필수**:
- ✓ **로봇이 절대 바닥을 안 뚫음** (link, foot 모두)
- ✓ **부호 (sign)** 검증: 좌표 변환, dq, τ 모두 일치
- ✓ **시작 자세 정적 평형** 검증 (robot 자세 hold 가능)
- ✓ **q/dq/τ/GRF 모두** 매칭 priority
- ✓ Working open source 정확 따라 (Go1 menagerie)

## ★ Data Sources

### 1. Reference Trajectory
- `C:\Users\junho\Desktop\jump_opt\no_cvt_alphaonly\jump_no_cvt_alphaonly_results.xlsx`
- q_ref(t), dq_ref(t), τ_ref, GRF_ref
- 125 samples, dt=2ms, 248ms stance phase
- 시작: q1=-0.297, q2=-2.548 (V20 좌표)

### 2. 실측 6 trial
- `C:\Users\junho\Desktop\Research\4-Bar Link CVT\Data\26.06.02\position\`
- 6 폴더: `60_0.75_60_2`, `60_1.5_60_1.5`, `90_0.75_90_2`, `120_2_120_2`, `150_2.2_250_3`, `150_2.2_500_5`
- 각 폴더: hip.xlsx, knee.xlsx, GRF.xlsx
- Time, currentAngle, desiredAngle, currentAngleVelocity, desiredAngleVelocity, currentTorque, desiredTorque

### 3. Paper a_hat (torque correction)
- Pure Paper formula (sgn(v) only, NO smoothing)
- `feedback_pure_paper_formula.md`, `ak80_9_torque_calibration.md`

## ★ Approach (제대로)

### Phase 0: 데이터 로드 + sign 검증
1. Reference + 6 trial 로드
2. Paper a_hat 적용 → tau_real
3. **★ Sign 검증** ✩ critical:
   - V20 frame ref vs MuJoCo frame variables의 sign이 일치
   - 좌표 변환 검증: `q1_mu = q1_v20 + π/2` 정확한지
   - 시작 자세에서 robot의 thigh/shank/foot 위치를 실 robot 자세와 비교
4. Phase 0 Notion 페이지

### Phase 1: mujoco_menagerie Go1 정확 fetch + adapt
1. `unitree_go1/go1.xml`, `scene.xml` 그대로 fetch (WebFetch agent 사용)
2. Single-leg robot으로 추출:
   - Trunk → 우리 base (slide joint)
   - 1개 leg (RF or FR) 사용
   - 나머지 3 leg 제거
3. **Position actuator** 사용 (Go1 표준, `<position kp=... kv=... forcerange=...>`)
4. Keyframe에서 시작 자세 = V20 ref 시작 자세
5. Phase 1 Notion 페이지: MJCF 구조 + 시각화

### Phase 2: ★ 시작 자세 정적 평형 검증 (필수)
**이게 모든 것의 시작점**:
1. ctrl = q_init (PD가 자세 hold)
2. 5초 simulate
3. 검증:
   - q drift < 0.05 rad ✓ → robot이 자세 hold OK
   - GRF ≈ M·g (32N) ✓ → contact stable
   - **foot_z, link_z 모두 ground 위** ✓ → 바닥 안 뚫음
4. **만약 hold 못 하면**:
   - robot model 잘못 (mass, inertia, friction)
   - inertia/com BO로 fit → 다시 검증
5. Phase 2 Notion 페이지: standing test 결과 + 영상

### Phase 3: Reference Apply + 비교
1. Phase 2 통과한 model에 reference 적용
2. ctrl(t) = q_ref(t) 시간에 따라 변경
3. Record: q_sim, dq_sim, tau_sim, GRF_sim
4. 6 trial 각각 (PD gain 다르게)
5. 4 metric 비교 그래프 (ref / actual / mujoco)
6. **Sign 일치 검증** (sim의 dq, τ가 ref와 같은 방향)
7. Phase 3 Notion 페이지: 첫 비교 결과

### Phase 4: 환경/Model fit (필요 시)
1. Phase 3 RMSE 큰 부분 진단
2. Tunable:
   - Joint armature, damping, frictionloss
   - Mass/inertia/com (실 robot CAD 값에서 시작)
   - Contact friction (foot, floor)
3. **★ 바닥 안 뚫음** + **시작 자세 정적 평형** 유지하면서 fit
4. Optuna BO with constraints (penetration penalty = 1e9, drift penalty)
5. iteration별 Notion 페이지

### Phase 5: Final validation
- 6 trial 모두 만족
- **q/dq/τ/GRF 매칭** + **sign 일치** + **바닥 안 뚫음**
- Final Notion summary 페이지

## ★ 검증 체크리스트 (모든 V마다 확인)

```
□ 시작 시점: foot bottom z ≥ 0 (ground 위 또는 touching)
□ 시작 시점: link 모두 ground 위
□ 시작 시점: GRF ≈ M·g (정적 평형)
□ 시뮬 도중: foot_z 항상 ≥ -1mm (numerical 허용)
□ 시뮬 도중: thigh/shank z 항상 ≥ 0
□ Sign: ref dq vs sim dq 같은 방향
□ Sign: ref τ vs sim τ 같은 방향 (sat 무관하게 같은 sign)
□ 6 trial 모두 위 5개 통과
```

이 체크리스트를 통과 못 하면 그 V는 invalid. score만 낮다고 best 아님.

## ★ Notion 보고서 — 작성 가이드라인 (유지)

### 페이지 구조
1. **새 Parent 페이지** 생성: "GOAL5 RESTART: MuJoCo Digital Twin (26.06.02)"
2. **이전 V1-V9 페이지는 archive** (또는 그대로 두되 새 parent 사용)
3. **자식 페이지를 Phase별로**:
   - Phase 0: 데이터 + sign 검증
   - Phase 1: Go1 menagerie fetch + adapt
   - Phase 2: 정적 평형 검증
   - Phase 3: 첫 reference apply
   - V1, V2, ... iteration별

### 각 자식 페이지 필수 내용 (이 순서)
1. **헤딩 + 1줄 요약**
2. **용어 정리** (★ 항상)
3. **방법 / Setup** (쉽게 + 코드 toggle)
4. **체크리스트 결과** (★ 새 추가):
   - 시작 시점 검증 (foot z, link z, GRF, 정적 평형)
   - Sign 검증 (좌표 변환, dq, τ)
   - 시뮬 도중 검증 (바닥 안 뚫음)
5. **그래프 (4개, 별도 image block)**:
   - Block 1: q (hip + knee)
   - Block 2: dq
   - Block 3: τ (paper-corrected)
   - Block 4: GRF_z
   - 3 line per subplot: Reference (검은 점선), Actual (빨강), MuJoCo (파랑)
6. **애니메이션 GIF** (★ 항상)
7. **결과 해석** (쉽게)
8. **수치 표** (RMSE per trial per joint)

### 작성 스타일
- 압축 X, 빈 paragraph block X
- 쉽게 설명 (학부생 수준)
- 비유 + 논리 + 수식 모두
- Korean: `font.family: 'Malgun Gothic'`

### Notion API
- Token: `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`
- file_uploads 3-step (imgur 금지)
- Callout emoji는 unicode (예: '⭐', '✅', '❌'), 'star' 같은 string 금지
- Rate limit 30분 대기

### ★ 이미지/애니메이션 업로드 검증 (필수)
- 페이지 만들고 끝내지 말 것
- GET `/v1/blocks/{page_id}/children` → image block 확인
- file_upload status `uploaded` 확인 (`pending`이면 재시도)
- 실패 시: delete → 재업로드 → 재생성 → 재검증
- 모든 검증 통과 후 user에게 URL 전달

## ★ Tools

- **MuJoCo** (latest)
- **mujoco_menagerie Go1** (정확 복사)
- **mujoco_mpc_deploy** (참고)
- **Python + numpy + scipy + matplotlib + pandas**
- **Optuna** (BO, multivariate TPE)
- **Notion API** (file_uploads)

## ★ Anti-patterns

1. ❌ "이전 GOAL5 V5 best 사용" — 폐기
2. ❌ 작은 foot_size (< 0.020 m) — Go1 standard 0.023
3. ❌ Soft contact (solref tc > 0.05) — Go1 default 0.02
4. ❌ Robot link contype=0 — 충돌 활성화 필수
5. ❌ BO가 비현실적 mass (예: thigh > 1.5 kg)
6. ❌ Body geom 충돌 비활성화

## ★ Memory References

- `position_data_26_06_02_model.md` — 26.06.02 final model
- `ak80_9_torque_calibration.md` — paper a_hat (CRITICAL)
- `feedback_pure_paper_formula.md` — pure paper sgn(v) only
- `digital_twin_priority.md` — q/dq/τ/GRF 매칭 priority
- `feedback_notion_image_upload.md` — file_uploads workflow
- `feedback_notion_image_verification.md` — verify upload
- `feedback_goal5_model.md` — Sonnet OK
- `goal4_lessons_learned.md` — V20 자세 PD-unstable 결론은 틀림
- `goal5_progress_v4.md` — 이전 GOAL5 V1-V9 시도 (참고용)

## ★ Starting Command

```
GOAL5 RESTART. C:\Users\junho\Desktop\jump_opt\GOAL5_PROMPT.md 읽고 진행해. 이번엔 처음부터 제대로.

이전 GOAL5 V1-V9 시도 (Desktop/jump_opt/goal5/ 폴더)와 잘못된 결론 모두 폐기:
- "PD ±18 sat이 hard limit" 절대 변명 금지
- "V20 자세 PD-unstable" 절대 변명 금지
- "motor delay, Stribeck 필요" 절대 변명 금지

진짜로 mujoco_menagerie Go1 정확 fetch + single-leg adapt. 

Phase 0: 데이터 로드 + sign 검증 (좌표, dq, τ)
Phase 1: Go1 menagerie 정확 fetch (WebFetch agent) + single-leg MJCF 만들기
Phase 2: ★ 시작 자세 정적 평형 검증 (robot 5초 hold 가능?)
- foot bottom z ≥ 0
- link z 모두 ≥ 0 (바닥 안 뚫음)
- GRF ≈ M·g (정적 평형)
- 통과 못 하면 robot model 잘못 → mass/inertia/com fit
Phase 3: Reference apply + 4 metric 비교
Phase 4+: 환경 fit (체크리스트 통과 유지)

새 Notion parent 페이지 "GOAL5 RESTART: MuJoCo Digital Twin (26.06.02)" 생성. Phase별 자식 페이지:
- 용어 정리 항상
- 체크리스트 결과 항상
- 위치/속도/토크/지반력 4개 비교 그래프 (별도 image block)
- 애니메이션 GIF 항상
- 압축 X, 빈 paragraph block X
- Notion API file_uploads (imgur 금지)
- 업로드 후 GET 검증 필수
- Callout emoji는 unicode ('⭐' '✅' '❌')

진행 중 막히면 ultrathink. 실 robot처럼 sim 움직여야 함. 점프 높이 매칭 X, q/dq/τ/GRF 모두 매칭 + sign 일치 + 바닥 안 뚫음.
```
