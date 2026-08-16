---
name: goal18-canonical-pipeline
description: GOAL18 LOCKED canonical animation pipeline for sit2stand + jump datasets. Use this exact code for ALL future simulation rendering regardless of model changes.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL18 CANONICAL Rendering Pipeline (v14 LOCKED — 2026-07-01)

**앞으로 모든 시뮬레이션 렌더링은 이 코드를 기준으로 한다.** 모델 params가 바뀌어도 시각화 로직은 그대로 사용.

## 파일 위치

- **Canonical folder**: `C:/Users/junho/CVT/jump_opt/goal18_CANONICAL/`
  - `README_CANONICAL_RENDERING.md` — 전체 스펙
  - `code/make_anim.py` — 핵심 렌더러
  - `code/regen_all.py` — 30 sub-folder orchestrator
  - `code/gen_mode_B_pd.py` — PD sim mode_B 생성 (jump_0424/0602)
  - `code/leg.xml` — 시각화용 XML
- **최종 output**: `C:/Users/junho/CVT/jump_opt/goal18_v13/Iter6/` — 30 subs, 217 gifs, 224 plots
- **Notion**: [GOAL18 CANONICAL page](https://app.notion.com/p/390ab81d255081ce9a92f1128080783e) — parent = CONCEPT (`115ab81d255080fdaae6f28f55e3e205`)

## LOCK 원칙 (절대 변경 금지)

1. **좌표 변환**: `mj_q1 = -q1_canonical - π/2`, `mj_q2 = -q2_canonical` — canonical 필드명 `q1_sim/q2_sim`는 misnomer (실은 REAL frame)
2. **Angle wrap** `(-π, +π]` — sim 발산 unwrap 처리
3. **카메라**: azim=135, elev=-15, dist=1.2, lookat=(0,0,0.3)
4. **색상**: base/thigh/calf/foot = jump XML 스타일 (흰-회색 톤)
5. **Real-time pace**: `n_frames = clamp(30, 200, round(cyc_dur / 0.04))`, 40ms/frame
6. **GND**: `mj_step` × **1500회** (500 부족 → 29.3cm 정지 버그), PD kp=1000 kd=50
7. **AIR**: `base_z = 0.55` 고정, overlay `"base = 0 (air, fixed)"`

## 최종 결과

30/30 sub-folders 완비:
- sit2stand_0324 (4 subs) + sit2stand_air_0319 + sit2stand_gnd_0319: 168 gifs
- jump_0424 (9) + jump_0602 (6) + jump_position_0421 (6) + jump_torque_0422 (3): 49 gifs

**jump_0424/0602 mode_B**: canonical 없어서 PD sim으로 pseudo 생성 (`[pseudo]` 라벨).

## 모델 수정 시 대응

- **Model params (mass/inertia/friction/PD)**: `regen_all.py::load_pm()` 만 수정
- **XML**: `build_xml_i38`로 새 leg.xml 재생성 (joint 이름 `hip`/`knee`, geom `foot` 유지 필수)
- **시각화 로직 (`make_anim.py`)**: 절대 건드리지 X

## 관련 memory

- `[[feedback_animation_standard]]` — 렌더링 표준 강제 규칙
- `[[master_insights_pointer]]` — 전체 통합 문서 pointer

## 사용법

```python
import sys
sys.path.insert(0, 'C:/Users/junho/CVT/jump_opt/goal18_CANONICAL/code')
from make_anim import render_sit2stand

render_sit2stand(
    canon_npz_path='.../cycle01.npz',
    model_xml_path='.../leg.xml',
    out_gif_path='.../cycle01.gif',
    trial_label='...',
    kind='air'  # or 'gnd'
)
```

전체 재생성: `python C:/Users/junho/CVT/jump_opt/goal18_CANONICAL/code/regen_all.py`
