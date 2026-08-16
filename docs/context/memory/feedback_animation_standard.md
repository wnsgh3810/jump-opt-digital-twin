---
name: feedback-animation-standard
description: 앞으로 모든 시뮬레이션 애니메이션은 goal18_CANONICAL 코드를 표준으로 사용. 모델이 바뀌어도 시각화 파이프라인은 이거 기준.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 애니메이션 렌더링 표준 (v14 LOCKED — 2026-07-01)

**규칙**: sit2stand + jump 애니메이션 렌더링은 무조건 `goal18_CANONICAL/code/`의 코드를 사용한다. 모델이 수정되어도 시각화 로직/카메라/색상/속도/좌표 변환은 절대 바꾸지 않는다.

**Why**: 2026-06-15 ~ 2026-07-01 사이 v10→v14 (10+ iteration) 동안 사용자가 반복적으로 지적한 시각적 요구사항을 최종 반영한 결과. 이 스펙에서 벗어난 렌더링은 매번 재작업이 발생함. 사용자 명시: "앞으로 모든 시뮬레이션은 이거 기준으로 하는거야 앞으로 모델이 수정되도 시뮬레이션은 이거 기준으로 하는거야".

**How to apply**:
- 새로운 sit2stand/jump 렌더링 코드가 필요한 상황 → **먼저** `C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/make_anim.py`를 import
- 모델 params (mass/inertia/PD gain 등)이 바뀌면: `regen_all.py::load_pm()`만 수정, 나머지는 그대로
- XML이 바뀌면: `build_xml_i38`로 새 leg.xml 생성 (joint 이름 `hip`/`knee`, geom `foot` 필수)

**★★ 렌더러 정확한 위치 (2026-07-05 확정 — 새 렌더러 작성 절대 금지)**:
- **sit2stand**: `goal18_CANONICAL/code/make_anim.py :: render_sit2stand(npz, xml, gif, label, kind)` — real-time pace (40ms 물리시간/frame), gnd=발바닥 접지 base_z 계산, air=base 0.55 고정.
- **jump**: `C:/Users/junho/Desktop/jump_opt/goal18_v9/_make_anim_universal_colored.py :: make_anim_universal_colored(npz, xml, gif, trial_label, h_real_m)` — canonical 트리의 jump GIF들은 regen_all이 v10에서 cp한 것이고 그 원본 렌더러가 이것. **640×480, 60 frames, 40ms, iso 카메라(azimuth 135/elev −15/dist 1.2/lookat 0,0,0.3), 팔레트 강제(base 회색/thigh 청회/calf 청록), 오버레이 trial/t/base_z(cyan)/GRF(yellow)/h_sim(green)/h_real(orange)**. npz 포맷: `t`, `q`[N,3 mj-frame], `grf_z`[N]. ("60-frame 금지" 규칙은 sit2stand용 — jump는 이 60f 규격이 canonical.)
- **아카이브 사본**: `Documents/jump-opt-digital-twin/code/goal19/canonical_render/_make_anim_universal_colored.py` (원본 불변, 참조용). 드라이버 예: `code/goal19/phase11/make_anim_v3_canonical.py`.

**★ 위반 사건 (2026-07-05, 교훈)**: GOAL19 v3 애니메이션을 새 렌더러(make_anim_v3.py)로 만들었다가 사용자 지적. canonical make_anim.py가 s2s 전용인 걸 보고 "jump 렌더러 없음"으로 성급 판단 — 실제로는 goal18_v9에 있었음. **교훈: 렌더링 요청 시 반드시 이 메모리의 경로부터 확인, 없어 보여도 새로 짜지 말고 원본 렌더러를 추적할 것.**
- **절대 금지**:
  - 60-frame 고정 렌더 (real-time pace 위반)
  - Canonical `q`를 `data.qpos`에 그대로 삽입 (좌표 변환 필수)
  - `mj_forward`로 gnd 렌더 (contact 무시)
  - 500-step 이하 settling (29.3cm 정지 버그)
  - matplotlib figure + imshow (흰 padding)
  - 오렌지+그린 leg 색상 (jump 스타일 유지)

**★ 위반 사건 2 (2026-07-18, 교훈)**: P25-task0 캠페인에서 "제약·그림은 AVT task0 스타일" 요청에 끌려
PD 배포 시뮬 GIF까지 AVT animate_results(스틱피겨)로 렌더 → 사용자 정정 ("디지털 트윈 실험 시뮬은
canonical로 해야지"). **교훈: 스타일 이식 요청은 정적 그림(plot)에만 적용 — 시뮬레이션 렌더링은 요청에
명시가 없는 한 무조건 canonical.** AVT 스틱피겨는 보조 시각화로만.

**관련 파일**:
- `[[goal18_canonical_pipeline]]` — 전체 스펙 + 사용법
- Notion: [GOAL18 CANONICAL](https://app.notion.com/p/390ab81d255081ce9a92f1128080783e)
- Git: v14 tagged in `jump_opt` repo
