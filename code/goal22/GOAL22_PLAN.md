# GOAL22 — dq·q 정밀화 + 샘플링 최적화 자율 마라톤 (2026-07-08 11:00 cron 시작)

사용자 지시 (07-08 새벽): "계속 연구하고 서칭하고 디버깅하고 분석하고 적용하고 피드백하면서
**dq, q가 잘 맞아야** 할 것 같고 **h 맞으면 좋을** 것 같고, 나중에 최적화 문제 **NLP로 꼭 풀 필요 없고
샘플링 베이스 방법론도** 고민 — 더 다양하고 많은 방법을 폭넓게 깊게 연구·개선."

## 0. 시작 시 필독 (fresh context 가정)
- 메모리: `fourbar_structure_critical.md`(★위상·실측·버그), `next_goal21_mission.md`(P1~P13e 전체 서사),
  `goal19_qdq_error_sources.md`, 함정 사전 = Notion ⑧페이지 (메모리 `reference_master_class.md`)
- 기준 모델: **`code/goal21/fourbar_honest_canonical.json` (P13e 정직물리)** — 비교 참조 `fourbar_flip_canonical.json`(P10)
- 평가 인프라: `g21_p12_polish.py`(하이브리드 eval), `g21_p13_linkage.py`(+링키지 mods), `g21_p13e_honest.py`(물리 케이지),
  갤러리 심판 = `FB.validate_fulltraj` 패턴 (`g21_p13e_gallery_assets.py`)
- 갤러리 artifact: `859e050e-f81e-4894-af2e-dda9de3ed8a1` (같은 파일 경로로 재배포하면 URL 유지)

## 1. 절대 규칙 (전 phase 공통)
- **물리 케이지 유지**: M_p=1.0983 LOCK(150g 실측), calf [0.97,1.03](발 포함=CAD, 사용자 확인),
  M_thigh [0.92,1.08], M_c [0.45,1.0](클러치 교체로 <CAD), **TOTAL_MASS=3.2kg** (base 역산),
  m_foot ≤10g, I/CoM CAD 케이지, offsets ≤3°. **유령질량 부활 금지.**
- 심판 규율: 하이브리드 목적(창5+fs+habs) + **held-out fs_0324 게이트** + 갤러리 full-replay + h.
  창-단독 점수 절대 신뢰 금지 (게이밍 증명됨). in-obj best ≠ 채택 — 항상 검증-선택.
- 우선순위: **q·dq 최우선, h 차선**, GRF/ste는 심판 전용(fit 금지). Mode A 원칙 (PD fitting 금지).
- 렌더링은 canonical 파이프라인 불변. plot 색 자동(cycle), sim/real = 실선/점선.
- 매 phase: git commit(자동) + 메모리 갱신 + 중요 결과는 갤러리/Notion 반영. 장시간 작업은 백그라운드+Monitor.
- canonical json들 덮어쓰기 금지 — 새 파일로 (예: `fourbar_honest_v2.json`).

## 2. Phase 순서 (우선순위순 — 각 phase 완료 후 다음)

### P1 ★★★ dq 계측 필터 규명 (분석만, 최우선 — '유령의 정체' 1순위 용의자)
가설: 로그의 dq는 펌웨어 필터를 거친 값인데, sim dq는 raw → 우리가 "sim dq 잔떨림"이라 부르는
것의 상당 부분이 **비교 기준 불일치**일 수 있음 (유령 관성 172g = dq 평활 노브였던 것과 정합).
- 방법: 전 세션에서 실측 q의 수치미분 vs 로그 dq를 시간/주파수 영역 비교 → 펌웨어 필터 식별
  (차수/차단주파수; AK80-9 MIT 펌웨어 dq 필터 웹서치 병행)
- 필터 발견 시: **심판 지표 교정** — sim dq에 동일 필터 적용 후 RMSE 재산출 (전 모델 P10/P13e 재채점)
- 산출: 필터 파라미터 + 교정 전후 dq 지표 표 + 결론 ("P13e의 dq 열세가 사라지는가?")

### P2 ★★ 벨트 직렬 탄성(SEA형) 모델 — dq 평활의 물리 후보
근거: 실물은 벨트 구동(세션 텐션 드리프트 관찰), 유령 관성의 역할이 dq 평활이었음.
motor_tm(1차 LPF)은 기각됐지만 **공진 있는 2차 전달(관성-스프링-관성)**은 다른 물리.
- 구현: knee(필요시 hip) 모터측 rotor body(armature) ↔ crank 사이 회전 스프링-댐퍼.
  XML: crank를 둘로 (motor_rotor hinge + belt stiffness joint) 또는 기존 stiff_knee 확장(rotor 관성 분리)
- 물리 케이지 재적합 + 게이트 + 갤러리. 파라미터: k_belt, b_belt, J_rotor(=arm 재해석)
- 판정: dq 개선이 h/q 훼손 없이 오는가. P1 교정 후 잔여 dq 갭에 대해 수행

### P3 ★ P13f — dq-가중 재적합 (정직 물리의 dq 프런티어)
- 물리 케이지 그대로, 목적의 W_DQ 상향(예: 50→150) 변형 + habs 유지 → dq-우선 해 확보
- 산출: (dq, h) 프런티어 2~3점 (P13e, P13f, 중간) — 사용자 선택지 제공

### P4 노이즈-바닥 (트윈-온-트윈) — 달성가능 한계 정량
- P13e 트윈이 만든 궤적에 실측 노이즈(τ 0.014Nm, dq 0.053rad/s, q 0.0054°, IC 오차) 주입해
  자기 자신 open-loop 재생 → 환원 불가능한 q/dq 발산 바닥 vs 실데이터 오차 곡선 (창 길이 스윕)
- 산출: "남은 갭 중 모델 잘못 vs 물리 한계" 분해 — 마라톤 후반 방향 결정 기준

### P5 offset 3°-레일 독립 검증
- settle/정지 구간에서 중력 균형 (τ_meas = G(q+offset))으로 세션별 offset을 fit 무관하게 직접 추정
- 3° 이상이 실측되면 케이지 완화 (측정 기반), 아니면 잔여 미모델 효과로 확정

### P6 ★★★ 샘플링-베이스 궤적 최적화 트랙 (사용자 명시 — NLP 대안)
트윈(P13e) 위 직접 최적화 3종 구현·비교. 마스터클래스 ④ 설계 시트 참조.
- 공통: 변수 = hip/knee τ 스플라인 노트 각 10개, 초기값 = G20 deploy CSV (100%), rollout = 스탠스+비행,
  비용 = −h_apex + τ한계(14.4Nm) 벌점 + 착지자세 벌점 + 스무스니스. 10코어 병렬.
- (a) CMA-ES  (b) MPPI (colored noise/λ 튜닝, 반복 30~50)  (c) Predictive Sampling (최단순 기준선)
- 산출 표: 방법별 최종 h / 제약위반 / rollout 수 / 벽시계 / τ 파형 비교 + **NLP(G20) 해와 정면 비교**
- 심화: 최적해 강건성 (IC/파라미터 노이즈에서 h 분포) — 뾰족 vs 평평 최적점
- 결론: "우리 점프에서 샘플링 vs NLP" 실증 판정 + 하이브리드(NLP warm→트윈 폴리시) 확정판

### P7 외부 리서치 (WebSearch, phase 사이사이)
- AK80-9/CubeMars 펌웨어 velocity filter, belt drive dynamics legged robot, MPPI jumping robot,
  2025-26 sampling trajopt, closed-chain sysid 후속 — 적용 아이디어는 즉시 백로그에 기록

### P8+ 자율 확장
- 잔차 지도 갱신 → 새 축은 [외부근거 → 구현 → 게이트 → 채택/기각 기록] 사이클
- 매 중요 결과: 갤러리 재생성(같은 경로 재배포), Notion 마스터클래스/해설 페이지에 반영 검토

## 3. 진행 로그 페이지 (사용자 관람용 — 필수 유지)
- **artifact URL: https://claude.ai/code/artifact/3e626825-aeb7-4f2f-9831-1e89cff212c5**
- 파일: scratchpad `g22_progress.html` — **매 phase 완료 시 갱신 후 같은 경로로 Artifact 재배포** (URL 유지, favicon 🏃 유지)
- 갱신 내용: Phase 현황판 상태(대기→진행중→완료/기각) + 결과 한 줄, 타임라인 로그에 항목 추가(최신 위), 필요 시 핵심 그림 임베드
- Notion GOAL22 페이지 `396ab81d2550814b9780f32285133840` (CONCEPT 아래)에 링크 게시됨 — 중요 결과는 여기에도 요약 추가

## 4. 종료/보고
- 사용자 복귀 시: 종합 보고 (phase별 표 + 채택/기각 + 갤러리 링크 + 다음 실험실 액션)
- 메모리 `next_goal22_mission.md`에 진행 상황 지속 갱신 (중단 대비)
