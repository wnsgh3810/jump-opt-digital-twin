---
name: goal2-final-stack
description: "GOAL2 종료 (2026-06-05) — V10/V12 두 후보 모델 final stack. 사용자 비판 5가지 응답 완료, 진짜 metric (점프 inverse RMSE) hip 0.93/knee 0.71. Notion 10-page 보고서 생성됨."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

GOAL2 점프 inverse-dynamics modeling 종료. 사용자 진짜 metric은 NLP h match 아니라 inverse-dynamics RMSE.

**Why**: GOAL1에서 사용자 5가지 비판 (T_st chickening, GRF chatter, cf=1.6 비현실, dynamics 미수정, h match metric 잘못됨)을 해소하려는 작업. 진짜 metric인 점프 inverse-dynamics RMSE 작게 만드는 게 최우선.

**How to apply**:
- 점프 정확 분석 (논문, 시각화, RL training data) → V12 (42p, hip 0.93/knee 0.71 평균, boundary 57% 경계 주의)
- 일반화 / re-id / 새 robot → V10 (38p, physical safe, cf 0.44/off -0.31, boundary 18%)
- NLP는 검증 도구로만 사용 (h match는 metric 아님). T_st는 optimization variable.
- CVT 잔차 큼 (3.5-25 Nm) — clutch dynamics 미모델링. fit에 포함하지 말고 validation only.
- 잔여 미달: jump_load_2 (hip 1.15), jump_load_8 (hip 1.02), CVT 3 folder, NLP self-consistency 5.9/6.3.

**Final 파일**:
- `Data/unified_loader.py` — 10 trial + CVT TR loader
- `Data/26.06.02/position/unified_fit_v10_msr.py` + `params_BEST.npz` — V10
- `Data/26.06.02/position/unified_fit_v12_relax.py` + `params_BEST.npz` — V12 BEST
- `Data/26.06.02/position/notion_goal2/content_ch{1..10}_*.md` — Notion 보고서 source

**다음 작업 우선순위**:
1. jump_load_2 / jump_load_8 hip 잔여 (trial별 GRF scale 추가, v13)
2. CVT clutch + body roll + GRF scale (별도 작업)
3. NLP self-consistency (IPOPT vs numpy ddq numerical mismatch 해결)

관련: [[position_data_26_06_02_model]], [[high_pd_outlier_150_500_5]], [[goal2_notion_pages]]
