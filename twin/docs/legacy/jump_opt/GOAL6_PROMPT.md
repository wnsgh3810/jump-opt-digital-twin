# GOAL6 START PROMPT (붙여넣기용)

---

GOAL6 시작해. `C:\Users\junho\Desktop\jump_opt\GOAL6_PROMPT.md` 읽고 진행.

## 미션
26.06.02 6 trial 모두 q/dq/τ/GRF 4 metric 완벽 매칭. **±18 sat 가설 폐기** + **폴더 이름의 PD gain은 AK80-9 motor 내부 firmware PD라서 실 mechanical PD와 다름 → 같이 fit**.

## 직전 GOAL5R V25에서 확인된 핵심 사실 (절대 변명/재시도 금지)

### ① ±18 sat 가설 폐기
- `tau1_real`/`tau2_real` 측정값이 **실제로 ±18 넘음**
- 예: 150_2.2_500_5의 tau2_real = -18.71 ~ +19.63
- 60_0.75_60_2의 tau2_real = +20.18 (저 PD인데도 +20)
- → sim의 `clip(tau, -18, 18)` 완전 폐기. 절대 다시 적용 금지.

### ② tau_des ≠ tau_real (firmware PD 따로 있음)
- 모든 trial의 `tau1_des`/`tau2_des` **동일**: tau1_des ∈ [-14.76, +0.03], tau2_des ∈ [0, +15.00]
- `tau1_real`/`tau2_real`는 trial별 매우 다름
- → 폴더 이름 (kp_h, kd_h, kp_k, kd_k)는 AK80-9 firmware PD gain. 진짜 mechanical PD 별도.

### ③ Mode A (tau_real 직접 ctrl 입력) 검증 결과: dynamics 자체 부족
- V25 mass/inertia/friction + ctrl=tau_real → q/dq/GRF 안 맞음
- 예: 150_2.2_500_5 q1 RMSE 0.246 rad, q2 0.657 rad, GRF range sim 0~313 vs real 0~115
- → **mass/CoM/inertia/friction이 실 robot과 다름**. dynamics fit 필요.

### ④ MuJoCo XML range hidden bug (절대 다시 추가 금지)
- `range="-3 3"` 추가하면 V20 자세에서 86,000배 artificial force 발생
- 모든 `<joint>`에 range 속성 절대 추가 금지 (V22 XML에서 제거됨)

## 시작점
- XML: `C:\Users\junho\Desktop\jump_opt\goal5_restart\urdf\leg_g5r_v25.xml`
- Data: `C:\Users\junho\Desktop\jump_opt\goal5\data_loaded.npz` (ref + 6 trial)
- 6 trial: `60_0.75_60_2`, `60_1.5_60_1.5`, `90_0.75_90_2`, `120_2_120_2`, `150_2.2_250_3`, `150_2.2_500_5`
- Mode A 검증 코드: `goal5_restart/goal6_mode_a_verify.py`
- V25 BO 코드: `goal5_restart/v25_bo_fit.py` (Optuna 100 trials, 10-dim contact/joint fit)

## Stage 1 — Dynamics Fit (Mode A 기반)
**입력**: tau_real을 ctrl로 직접 입력 (open-loop). PD/sat 없음.
**Fit 변수 (13-15 dim)**:
- Mass: `M_base`, `M_thigh`, `M_calf` (V25 baseline 2.0/0.8/0.47 ± 30%)
- CoM: `thigh_com_z`, `calf_com_z` (V25 -0.0565/-0.0588 ± 30%)
- Inertia: `thigh_iyy`, `calf_iyy`, `armature_hip`, `armature_knee`
- Damping: `joint_damp_hip`, `joint_damp_knee` (V25 0.38 baseline)
- Friction: `joint_frictionloss`, `foot_friction_tan`
- Contact: `solref_tc`, `solimp_mid` (V25 0.02/0.018 baseline)

**Score**: 6 trial 동시
```
score = Σ_trial Σ_metric w·RMSE(sim, real)
w = {q1: 100, q2: 100, dq1: 1, dq2: 1, GRF: 0.1}
```

**진행**: Optuna BO (TPESampler multivariate, 300 trials, 50 startup). 사용자가 .bat 더블클릭으로 시작.

## Stage 2 — Motor Model Fit (Stage 1 dynamics 고정)
**입력**: Reference motion + firmware PD (폴더 PD gain) → motor model → tau_real → MuJoCo
**Motor model 후보**:
- AK80-9 a_hat 5-param 모델 (paper a_hat: 전기변환 + saturation + 마찰 + 부하종속)
- Per-trial PD scaling factor (4 scaling × 6 trial = 24 dim)
- Per-trial motor delay `tm` + saturation limit
- 또는 transfer function (firmware PD → mechanical tau)

**Score**: tau_real 매칭 + (q/dq/GRF 보조)

**진행**: BO 200-500 trials. tau_des와 tau_real 관계 모델링.

## Stage 3 — Full Free Fit (선택, 시간 남으면)
Stage 1 + Stage 2 동시 BO.

## Sweep 인프라 (이전 169M 검증 패턴)
- MuJoCo는 multiprocessing pickle 안 됨 → 각 worker에서 build_xml + load
- Optuna BO만 사용 (단일 프로세스) — 50-300 trials. .bat으로 외부 cmd 실행
- 또는 multiprocessing 필요시 maxtasksperchild=10000, chunksize=100, imap_unordered + heapq top-K
- `np.interp` 사용 (scipy 아님)
- 결과 저장: `study.pkl` + 매 stage best XML

## 노션 페이지 (절대 지켜야 함)

### Parent 페이지 새로 생성
- 제목: "GOAL6: Full Match (no sat, fit PD+dynamics)"
- 위치: 새 페이지 (이전 GOAL5R parent와 분리)

### Stage별 자식 페이지 (각 stage 별도)
필수 구성:
- **용어 정리** (5-10개 항목, bullet) — 항상
- **체크리스트 결과** (검증 항목/기준/결과/상태 표) — 항상
- **위치/속도/토크/지반력 4개 비교 그래프** — 각각 **별도 image block** (한 block에 합치기 금지)
- **6 trial별 그래프** (한 트라이얼이 한 그래프에 모이게, default color, 색 지정 X) — 24개 그래프
- **애니메이션 GIF** (각 stage 끝에 한 trial GIF, 조명 정상 확인)
- **압축 X, 빈 paragraph block X**
- **Notion API file_uploads 사용** (imgur 외부 호스팅 절대 금지)
- **업로드 후 GET 검증 필수** (`status == "uploaded"` assert)
- **Callout emoji unicode** ('⭐' '✅' '❌' '🔍' '📊' '⚠️')
- Korean font 'Malgun Gothic'
- code block language "html" (XML), "plain text" (수식), "python"

### Notion token
`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`

### Notion API 3-step 파일 업로드 + GET 검증 패턴
```python
# Step 1
r = requests.post("https://api.notion.com/v1/file_uploads", headers=HEADERS, json={})
uid = r.json()["id"]
# Step 2
with open(path, "rb") as f:
    requests.post(f"https://api.notion.com/v1/file_uploads/{uid}/send",
                  headers={"Authorization":...,"Notion-Version":"2022-06-28"},
                  files={"file": (path.name, f, "image/png")})
# Step 3 (필수)
rg = requests.get(f"https://api.notion.com/v1/file_uploads/{uid}", headers=HEADERS)
assert rg.json()["status"] == "uploaded"
```

### XML 작성 시 visual/light 빠지지 않게 (V25 어두웠던 사고 방지)
```xml
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" .../>
  <texture type="2d" name="groundplane" builtin="checker" .../>
  <material name="groundplane" texture="groundplane" .../>
</asset>
<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <!-- floor + bodies with rgba -->
</worldbody>
```

## 진행 순서 (체크리스트)
1. ⬜ GOAL6 parent 페이지 생성
2. ⬜ Stage 1 dynamics fit BO 300 trials
3. ⬜ Stage 1 결과 노션 자식 페이지 (용어/체크리스트/4 metric 별도 그래프/24 trial 그래프/GIF)
4. ⬜ Stage 2 motor model fit BO 200-500 trials
5. ⬜ Stage 2 결과 노션 자식 페이지
6. ⬜ (선택) Stage 3 통합 BO
7. ⬜ Stage 3 결과 노션 자식 페이지
8. ⬜ Memory update: `goal6_findings.md`, MEMORY.md
9. ⬜ Git commit (사용자 git commit 자동 선호)

## ★ 진행 중 막히면 무조건 ultrathink

**아래 상황 발생 시 절대 변명/회피하지 말고 ultrathink 깊이 분석**:
- BO best score가 50 trial 이상 plateau → ultrathink + 변수/score/baseline 재설계
- sim 결과가 분석상 말이 안 됨 (예전 GOAL5R range bug 같은 hidden constraint 의심) → mj_solveM vs mj_forward 비교 등 격리 테스트
- 어떤 parameter 변경해도 metric 안 움직임 → 다른 root cause (XML hidden 설정, sign 잘못, 좌표계, integrator, contact mode)
- 사용자가 "말이 안 되지" "이상한데" "기억나지?" → 즉시 ultrathink + 메모리 검색
- 5번 이상 같은 실패 반복 → 가설 자체 폐기하고 fresh thinking
- "physically 불가능" 결론 내리기 전에 무조건 ultrathink (이전 V20 unstable 결론은 완전히 틀렸음)

**ultrathink 적용 패턴**:
1. 이론 분석 (M·a = F, gravity moment 계산 등)을 실제 sim 값과 정량적으로 비교
2. minimal isolation test (1-body, no contact 등)로 layer 별 격리
3. mj_solveM(M⁻¹b) vs mj_forward(qacc) 일치 확인 — 다르면 hidden force
4. parameter 1개씩 toggle하면서 영향 비교
5. 코드 line-by-line으로 단위/sign 검증
6. 메모리(`mujoco_range_bug.md` 등)에서 유사 패턴 검색

**진짜 robot처럼 sim 동작해야**. 점프 높이 매칭 X. q/dq/τ/GRF 모두 매칭 + sign 일치 + 바닥 안 뚫음. 그래프 그릴 때 속도/토크 방향(sign) 신경 쓰기.

## ★ 노션 페이지 생성 후 무조건 검증

**페이지 만들고 끝내지 말 것**. 만들고 나서 반드시:

1. **모든 이미지 블록 GET 검증**:
   - `requests.get(f"/v1/blocks/{page_id}/children")` 로 children 가져옴
   - 각 image block의 `file_upload.id` 확인
   - 다시 `requests.get(f"/v1/file_uploads/{uid}")` 로 status="uploaded" 확인
   - **하나라도 status≠uploaded → 즉시 재업로드**

2. **GIF 검증**:
   - GIF는 image type이지만 별도 mime "image/gif" 필요
   - 페이지에 추가된 GIF block id로 GET → status 확인
   - 페이지 reload 시 깨지면 재업로드

3. **블록 개수 검증**:
   - 작성한 blocks 개수 vs 실제 페이지에 들어간 children 개수 비교
   - 빠진 게 있으면 chunk 단위로 다시 PATCH

4. **이미지 시각 검증 (가능하면)**:
   - GIF/image 다시 다운로드 (file_uploads/{uid}/download?) 하거나
   - 페이지 URL을 사용자에게 보내서 직접 확인 요청
   - 조명 어두움/색 잘못/누락 발견 시 즉시 재렌더링 + 재업로드

5. **자주 발생하는 누락 패턴**:
   - 24개 image block 모두 들어갔는지 (1개씩 빠짐 자주 발생)
   - GIF 1개가 image type 헤더 잘못 (mime 다름)
   - chunk 단위 PATCH 실패 → 그 chunk만 누락
   - 페이지 50 block 한계 → split 안 하면 나머지 누락
   - heading/divider/table 누락은 보고 vs callout/image 누락은 PATCH 실패

6. **MuJoCo render 전 XML에 visual/asset 확인**:
   - BO build_xml 함수 만들 때 절대 minimal XML로 만들지 말 것
   - `<asset>` (skybox/material), `<visual>` (headlight/ambient), `<light>` (directional) 빠지면 GIF 어두워짐
   - V25 GIF 어두웠던 사고 다시 발생 금지

**사용자가 "이미지 안 보여" "조명 어둡네" "그래프 안 들어갔어" 하면 부끄러운 일**. 페이지 만들기 전에 이 검증 단계를 코드에 포함.

## 사용자가 "기억나지?" 하면
즉시 메모리 검색:
```python
# C:\Users\junho\.claude\projects\C--Users-junho-Desktop\memory\MEMORY.md 읽고
# 관련 .md 파일 모두 참조
```
관련 메모리: `mujoco_range_bug.md`, `sysid_findings.md`, `analysis_findings.md`, `sweep_optimization_lessons.md`, `ak80_9_torque_calibration.md`, `pd_sim_purpose.md`, `digital_twin_priority.md`

## 사용자 선호 (기억)
- Sweep 시작: 사용자가 `.bat` 직접 더블클릭 (PowerShell/Tee-Object 절대 금지)
- 장시간 sweep 중 자동 승인 OK
- 코드 수정 후 자동 git commit OK
- 노션 페이지 만들고 끝내지 말 것. GIF 조명/status 확인. 실패 시 재업로드
- 보고는 표 형식 + Best 해석 + 바운더리 양상
- Phase별 자식 페이지 한 번에 하나씩 자세히
- 다양한 그래프 + 비유+논리+수식
