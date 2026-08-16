---
name: research_scope_cvt_multitask
description: ★★★ 연구의 진짜 범위 (CRITICAL) — 수직 점프 하나가 아님. 4-bar CVT가 수직점프+수평점프+sit2stand 최대하중 여러 task에서 이득을 줌을 증명하는 연구. 디지털트윈은 수단
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

★★★ **연구 범위를 좁게 보지 말 것.** 이건 "점프 디지털트윈"이 아니라 **4-bar 링크 CVT가 단족 로봇 성능을 여러 task에서 향상시킴을 증명하는 연구**다. (디지털트윈/시스템ID는 NLP가 실 로봇에 전이되게 하는 수단일 뿐.)

**로봇**: 2-DOF 단족 hopper (hip+knee), 2× AK80-9(9:1), ~3.0-3.27kg, **수직 레일** 위(free DOF z/q1/q2). **무릎이 4-bar 링크 CVT로 구동** — 자세에 따라 변속비 TR 연속 변화(TR avg≈1.66~1.73, 순간 최대 ~20), τ_joint=τ_motor·TR → 필요할 때 토크 증폭.

**핵심 주장 = CVT vs no-CVT(고정변속)를 같은 로봇으로 3개 regime에서 A/B 비교**:
1. **수직 점프 (max height)**: CVT ~+23% 점프높이. 실 점프 77~98cm.
2. **수평/전방 점프 (멀리뛰기, forward jump, 수평 점프)**: NLP 최적화로 **수평 거리 +41.2%** (no_cvt −0.989m → with_cvt −1.397m, l_i=16.2mm). cost `+1000·d_foot_land`, friction cone μ=0.3 binding, ALPHA=0.85. v5(`task29_2d_v6`)가 최신. 실 로봇은 **boom bar/pivot**으로 scoped(NLP-검증 위주). ※ "forward sim/forward_real"(v21_forward_sim 등)은 다른 의미(수치 forward 적분 검증)이니 혼동 금지.
3. **sit-to-stand 최대하중 (payload/max load) — CVT의 간판 이득**: NLP상 **CVT ≈8~9kg vs no-CVT ≈3.7kg (≈2.3×)**. HW 실측은 CVT load_2.5/5kg, no_cvt load_5/7.5kg(26.06.04). 목표 with-CVT ≥8kg. TR가 하중 따라 1.66→1.73로 증폭 쪽 shift.

**방법론 2축**:
- **NLP 궤적 최적화** (CasADi/IPOPT direct collocation), task마다 CVT vs no-CVT. 코드: **`C:\Users\junho\CVT\AVT LEG\optimization_tasks\`** (task9 forward, task28/task30 payload s2s, task29 2D). 진짜 metric = **forward sim-to-real consistency**(NLP q*/dq* → 실 로봇 재생 → 실측 τ/GRF ≈ 예측). [[master_insights_pointer]] §1.
- **디지털트윈/시스템ID** (GOAL1~17, `jump_opt/`): NLP를 신뢰·전이 가능하게 + CVT 숨은 동역학 검증.

**실험 캠페인(26.02~26.06)**: 점프(position/torque/feedforward, PD sweep, Tr/noTr), sit2stand(air/ground, chirp ID), CVT vs no_cvt, payload(26.06.04), AK80-9 a_hat 캘리브레이션, loadcell 토크 검증, P-sweep. 데이터 `Research\4-Bar Link CVT\Data\`.

**통합 모델**: 10-trial(점프 6@26.06.02 + sit2stand 4@26.06.04, CVT 포함) 동시 fit, 24/42-param. CVT trial은 TR로 motor→joint 변환. ([[unified_model_26_06_04]])

**Why:** 사용자가 2번 "범위가 좁다"고 정정함. CVT의 다중-task 이득 증명이 본질, 점프높이/디지털트윈은 수단·검증.
**How to apply:** 연구를 설명/계획할 때 항상 multi-task(점프+수평점프+최대하중) + CVT vs no-CVT 비교 프레임으로. [[project_research_context]] [[goal_task30_chatter]] [[pd_sim_purpose]] [[digital_twin_priority]]
