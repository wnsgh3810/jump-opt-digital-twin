# 🔒 CANONICAL RENDERING PIPELINE — LOCKED

**절대 이 파일을 지우거나 이동시키지 말 것. 저장소 최상단에 배치되어 있는 것이 목적임.**

---

## 📌 상태 (2026-07-01 LOCKED)

앞으로 **모든 sit2stand + jump 시뮬레이션 애니메이션 렌더링**은 아래 파이프라인을 기준으로 한다.
**모델 params가 바뀌어도 시각화 코드는 절대 변경하지 않는다.**

### 원본 위치
- **Canonical folder**: `goal18_CANONICAL/`
- **Code**: `goal18_CANONICAL/code/`
  - `make_anim.py` — 핵심 렌더러
  - `regen_all.py` — 30 sub-folder orchestrator
  - `gen_mode_B_pd.py` — PD sim mode_B 생성기
  - `build_xml_i38_standalone.py` — self-contained XML 생성기
  - `leg.xml` — 시각화 XML
  - `iter38_best_params.json` — 참조 params
- **Final output**: `goal18_v13/Iter6/` (30 subs / 217 gifs / 224 plots)
- **Documentation**: `goal18_CANONICAL/README_CANONICAL_RENDERING.md`

### Git tags (annotated)
- `v14-canonical` — canonical folder freeze
- `LOCKED-2026-07-01` — permanent lock marker

### Notion
- Parent: CONCEPT (`115ab81d255080fdaae6f28f55e3e205`)
- Page: [GOAL18 CANONICAL — Sit2stand & Jump Animation Pipeline (v14 LOCKED)](https://app.notion.com/p/390ab81d255081ce9a92f1128080783e)
- 모든 코드가 toggle 안에 실제 파일 그대로 저장됨

---

## 🔑 7가지 LOCK 원칙 (변경 금지)

1. **좌표 변환**: `mj_q1 = -q1_canonical - π/2`, `mj_q2 = -q2_canonical`
2. **Angle wrap**: `(-π, +π]`
3. **카메라**: azim=135°, elev=-15°, dist=1.2, lookat=(0, 0, 0.3)
4. **색상**: base(0.5,0.5,0.5) / thigh(0.6,0.6,0.7) / calf(0.5,0.6,0.6) / foot(0.5,0.5,0.5)
5. **Real-time pace**: `n_frames = clamp(30, 200, round(cyc_dur / 0.04))`, 40ms/frame
6. **GND settling**: `mj_step` × **1500회** (500 → 29.3cm 정지 버그)
7. **AIR base**: `base_z = 0.55` 고정 (overlay `"base = 0 (air, fixed)"`)

## 🚫 절대 금지

- Canonical `q`를 그대로 `data.qpos`에 → 좌표 변환 필수
- 60-frame 고정 렌더 → 속도 불통일
- `mj_forward`로 gnd 렌더 → contact 무시
- 500-step 이하 settling → 자유낙하 0.25s만
- matplotlib figure + imshow → 흰 padding
- 오렌지+그린 leg 색상 → jump 스타일 유지

## ⚙️ 모델 수정 시

- **Params (mass/inertia/PD)**: `regen_all.py::load_pm()` 또는 `iter38_best_params.json`만 수정
- **XML 재생성**: `build_xml_i38_standalone.py`로 새 `leg.xml` 생성 (joint 이름 `hip`/`knee`, geom `foot` 필수)
- **시각화 코드 (`make_anim.py`)**: 절대 건드리지 X

---

## 📝 이 파일이 만들어진 이유

2026-06-15 ~ 2026-07-01 사이 10+ iteration (v10 → v11 → v12 → v13 rev1-4 → v14) 동안
사용자가 반복적으로 지적한 시각적 요구사항의 최종 결과.

사용자 명시 (2026-07-01):
> "지금 다 완벽한거 같애 이거 모든 코드 저장해 커밋도 해 노션에도 저장하고 토글로 이 코드 절대 안잊도록 하고 **앞으로 모든 시뮬레이션은 이거 기준으로 하는거야 앞으로 모델이 수정되도 시뮬레이션은 이거 기준으로 하는거야** 이 코드들을 기준으로 수정해서 쓰는거야"

## 🔗 관련 문서

- `goal18_CANONICAL/README_CANONICAL_RENDERING.md` — 전체 스펙
- Memory: `~/.claude/projects/C--Users-junho-Desktop/memory/goal18_canonical_pipeline.md`
- Memory: `~/.claude/projects/C--Users-junho-Desktop/memory/feedback_animation_standard.md`
- Notion: https://app.notion.com/p/390ab81d255081ce9a92f1128080783e
