---
name: reference-master-class
description: "마스터 클래스 노션 (MuJoCo 폐루프·접촉·최적화·샘플링 완전 정리, 07-07) — 부모 396ab81d2550814995dfc2e3a712ee01. 사용자 개념 질문 시 이 페이지 참조/확장."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# 마스터 클래스 노션 (2026-07-07)

- **부모**: `396ab81d2550814995dfc2e3a712ee01` — "마스터 클래스 — MuJoCo 폐루프·접촉·최적화·샘플링"
- child 9장 + sub 7장 (07-08 심화 증축 후 총 ~950블록): ①폐루프 진실(100블록, 암시적 심화 2.5절) ②접촉(77+②-a solref수학 38) ③궤적최적화(68+③-a IPOPT 32) ④MPPI(79) ⑤gradient(79+⑤-a 토이실험 37) ⑥4족MPC(77+⑥-a QP유도 37) ⑦RL(75) ⑧처방전(110+⑧-a 용어총사전 61용어) ⑨폐루프 계보(83+⑨-a 자코비안 해부 46 — 표현법 5종, 우리vs BRUCE 2×2, RoMeLa C→A 전환, 사용자 폴더 Desktop/Parallel_Actuation_ClosedChain_Targeted_Papers 11편 매핑)
- 심화 증축 방식: Fable이 사실 브리프 작성 → Sonnet 에이전트가 확장 주입 (스크립트 code/goal21/notion_agents/agent_p1~p9.py) — 사용자가 명시 선호한 패턴
- 그림 8종 스크립트: `code/goal21/notion_master_figs.py` (scratchpad p9_explain/m1~m8)
- 별도: "트윈 최적화 완전 해설" 부모 `396ab81d25508135aa98fd9b55b791ac` (child ①~⑪: 루프·로봇 반영·접촉·4bar·파라미터 사전·a_hat·NLP 대조·함정 사전·오차 지도·용어 사전·배포 체크리스트)
- 검증된 핵심 인용: MJPC/Predictive Sampling arXiv:2212.00541, Suh 2022 arXiv:2202.00817, Di Carlo 2018, Todorov 2014, Posa 2014, Williams 2017 MPPI
- 사용자가 개념 질문("~어떻게 되는거야") 시: 채팅 답 + 해당 child 확장이 선호 패턴
