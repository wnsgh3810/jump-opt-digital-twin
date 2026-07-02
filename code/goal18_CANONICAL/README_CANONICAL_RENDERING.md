# GOAL18 Canonical Rendering Pipeline (v14 Final — 2026-07-01)

> **🔒 STATUS: LOCKED CANONICAL.** 앞으로 모든 시뮬레이션 렌더링은 이 코드를 기준으로 한다.
> 모델이 수정되어도 시각화는 이 파이프라인을 그대로 사용한다.
> Iteration history: v3-air ref → v10 jump XML → v11 (bug) → v12 (padding) → v13 rev1~4 (fixes) → **v14 final (30/30 mode_A+B)**

---

## 🎯 목적

- **입력**: canonical `.npz` (`t_sim`, `q1_sim`, `q2_sim`, optional `base_z_sim` / `grf_sim`)
- **출력**: `.gif` 640×480, 40ms/frame (25fps), real-time playback
- **적용 대상**: 모든 sit2stand + jump 데이터셋 (`sit2stand_0324`, `sit2stand_air_0319`, `sit2stand_gnd_0319`, `jump_0424`, `jump_0602`, `jump_position_0421`, `jump_torque_0422`)

## 📁 파일 구성

```
goal18_CANONICAL/
├── README_CANONICAL_RENDERING.md   ← 이 문서 (사용법 + 원칙)
├── code/
│   ├── make_anim.py         ← 핵심 렌더러 (sit2stand + jump 통합)
│   ├── regen_all.py         ← 30개 sub-folder 일괄 orchestrator
│   ├── gen_mode_B_pd.py     ← canonical 없는 jump mode_B 생성 (PD sim)
│   └── leg.xml              ← 시각화용 MuJoCo XML (build_xml_i38 output)
└── final_output → goal18_v13/Iter6/  (30 subs, 217 gifs, 224 plots)
```

## 🔑 핵심 원칙 (LOCK)

### 1. 좌표 변환 (CRITICAL — 초반 버그 원인)
Canonical `q1_sim`/`q2_sim`는 v3 `to_real_frame_A`가 저장한 **REAL frame** 값이다 (변수명이 오해 유발). MuJoCo에 넣을 때는 반드시 변환:
```python
mj_q1 = -q1_canonical - π/2   # hip
mj_q2 = -q2_canonical           # knee
```
안 하면 무릎이 **반대 방향**으로 굽힘 (sit pose 정반대 렌더).

### 2. Angle wrap
sim 발산으로 canonical q가 unwrap된 경우 (예: -226°, +325°) 시각화 시 `(-π, π]`로 wrap 필수.

### 3. 카메라
```python
cam.azimuth = 135.0
cam.elevation = -15.0
cam.distance = 1.2
cam.lookat = np.array([0.0, 0.0, 0.3])
```

### 4. 색상 (jump XML 통일)
```python
REF_RGBA = {
    'base':  (0.5, 0.5, 0.5, 1.0),   # 회색 박스
    'thigh': (0.6, 0.6, 0.7, 1.0),   # 흰-보라
    'calf':  (0.5, 0.6, 0.6, 1.0),   # 연두-회색
    'foot':  (0.5, 0.5, 0.5, 1.0),
}
```

### 5. Real-time pace (모든 cycle 통일 속도)
```python
n_frames = clamp(30, 200, round(cyc_dur / 0.04))
DT_FRAME_S = 0.040   # 40ms/frame = 25fps
```
→ 8s cycle은 200 frames × 40ms = 8s playback (real-time)
→ 2s cycle은 50 frames × 40ms = 2s playback (real-time)
→ 절대 60-frame 고정 X (cycle마다 속도 달라지는 문제 발생)

### 6. GND foot-on-floor (contact 자연 안착)
`mj_forward` (kinematics only)는 contact 무시. `mj_step`으로 미니 물리 시뮬:
```python
data.qpos[0] = 0.6   # base placeholder
data.qpos[1] = mj_q1
data.qpos[2] = mj_q2
data.qvel[:] = 0.0
for _ in range(1500):   # ★ 1500 필수 (500은 부족 → 29.3cm에서 정지)
    data.ctrl[0] = 1000 * (mj_q1 - data.qpos[1]) - 50 * data.qvel[1]
    data.ctrl[1] = 1000 * (mj_q2 - data.qpos[2]) - 50 * data.qvel[2]
    mujoco.mj_step(model, data)
```

### 7. AIR base
`base_z = 0.55` 고정 (leg dangling). Overlay 표시: `"base = 0 (air, fixed)"`.

### 8. Overlay (모든 sit2stand 공통)
- Trial 라벨 (line 1)
- 시간 ms (line 2)
- base info (line 3, air/gnd별)
- hip° (line 4, 초록)
- knee° (line 5, 주황)
- 폰트: `C:/Windows/Fonts/malgun.ttf` size 24
- 스타일: PIL `_draw_text_outlined` — 검은 stroke + 색상 fill

## 🚀 사용법

### 기본 렌더 (한 cycle)
```python
import sys
sys.path.insert(0, 'C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code')
from make_anim import render_sit2stand

render_sit2stand(
    canon_npz_path='.../cycle01.npz',
    model_xml_path='.../leg.xml',
    out_gif_path='.../cycle01.gif',
    trial_label='sit2stand_0324 P20_D1 mode_A cyc01',
    kind='air'   # or 'gnd' for ground contact
)
```

### 전체 재생성
```bash
python C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/regen_all.py
```

### PD sim으로 mode_B 생성 (canonical 없을 때)
```bash
python C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/gen_mode_B_pd.py
```
* PD gain은 폴더 이름에서 파싱 (예: `60_0.75_60_2` → kp_hip=60, kd_hip=0.75, kp_knee=60, kd_knee=2)

## ⚙️ 모델이 바뀌면?

**시뮬레이션 model params (mass, inertia, friction, PD gains 등)이 바뀌면**:
- `regen_all.py::load_pm()` 내부의 파라미터만 수정
- **시각화 로직 (`make_anim.py`), 좌표 변환, 카메라, 색상, 속도는 절대 변경 X**

**XML이 바뀌면** (build_xml_i38 이후 새 build):
- `leg.xml` 재생성만
- Canonical joint 이름 (`hip`, `knee`, foot geom name `foot`) 유지 필수

## 🚫 절대 금지 (지금까지의 실수 방지)

1. **canonical q를 그대로 `data.qpos`에 넣기** → 좌표 변환 필수
2. **60-frame 고정 렌더** → 속도 통일 안 됨. real-time pace 사용
3. **`mj_forward`로 gnd 렌더** → contact 무시. `mj_step` 필수
4. **500-step 이하 settling** → 자유낙하만으로는 부족. 1500 step 이상
5. **matplotlib figure + imshow** → 흰 padding 생김. PIL `Image.fromarray` 사용
6. **jump 렌더에 v3 sit2stand_air 스타일 (오렌지/그린) 적용** → jump 색상 스타일 유지
7. **다른 axis convention의 XML** → build_xml_i38 base 필수

## 📊 최종 결과 (goal18_v13/Iter6/, 검증 완료)

| Dataset | Subs | mode_A gifs | mode_B gifs | Total |
|---|---|---|---|---|
| sit2stand_0324 | 4 | 54 | 54 | 108 |
| sit2stand_air_0319 | 1 | 15 | 15 | 30 |
| sit2stand_gnd_0319 | 1 | 15 | 15 | 30 |
| jump_0424 | 9 | 10 | 9 | 19 |
| jump_0602 | 6 | 6 | 6 | 12 |
| jump_position_0421 | 6 | 6 | 6 | 12 |
| jump_torque_0422 | 3 | 3 | 3 | 6 |
| **TOTAL** | **30** | **109** | **108** | **217** gifs, 224 plots |

- 모든 gif: 640×480, 40ms/frame, 25fps
- mode_B for jump_0424/0602 (15 subs): PD sim으로 생성한 pseudo-mode_B (mode_A output을 pseudo-q_des로 사용). `[pseudo]` prefix로 라벨 명시.
- 그 외 mode_B (15 subs): real robot canonical 기반.

## 📝 Iteration History (교훈)

| Version | 시도 | 결과 |
|---|---|---|
| v10 | Original jump XML rendering | sit2stand robot 안 보임 |
| v11 | Camera lookat 조정 | 여전히 문제, sit2stand_air/gnd 렌더 실패 |
| v12 | v3 sit2stand_air 스타일 (오렌지+그린 leg) | 사용자 거부, jump 스타일 원함 |
| v13 rev1 | Jump XML + shim | 좌표 변환 미적용으로 leg 반대 방향 |
| v13 rev2 | 좌표 변환 적용 + real-time pace + mj_step 500 | gnd 29.3cm 정지 (settling 부족) |
| v13 rev3 | Angle wrap 추가 | 여전히 gnd 정지 |
| v13 rev4 | mj_step 500 → 1500 | ✓ gnd 정상 안착 |
| **v14** | **mode_B 30/30 완비** | ✅ **최종** |

## 🔗 Notion

Canonical 전체 문서 + 코드 토글: (Notion 페이지 URL은 memory에 저장됨)
