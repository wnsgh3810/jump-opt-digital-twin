# 기억 목차 (133건 · 2026-08-16 통합)

> **읽기 전 알아 둘 것.** 이 목차는 원래 **네 군데로 갈라져 있던 기억을 합친 것**이다.
> Claude 의 기억은 대화를 시작한 폴더별로 따로 쌓이는데, 몇 달 동안 폴더를 바꿔 가며
> 작업해서 8월분(40건) · 7월분(27건) · 6월 이전(66건)이 서로를 못 보고 있었다.
> 2026-08-16 에 C:\Users\junho\CVT 로 합쳤다.
>
> **시기가 곧 신뢰도다.** 나중에 뒤집힌 사실이 실제로 여러 건 있었다
> (예: 짐 지고 일어서기 실험의 유효 범위가 한동안 반대로 적혀 있었다).
> **아래에서 충돌이 보이면 언제나 더 최근 것이 맞다.** 옛 기억을 근거로 삼기 전에
> 같은 주제의 최신 항목이 있는지 먼저 확인할 것.
> 날짜는 "그 파일이 마지막으로 갱신된 시점"이며, 처음 쓰인 날보다 늦을 수 있다.


## 2026년 8월 — 현행 (가장 믿을 수 있음) — 40건

- `2026-08-16` [short-window-hides-a-general-model-error](short-window-hides-a-general-model-error.md) — 일어서기만 틀린 게 아니다 — 같은 0.2초 창으로 재면 점프와 오차가 같다 (7~12°) · 점프가 잘 맞아 보인 건 창이 짧고 많이 움직여서다 (08-16)
- `2026-08-16` [cvt-session-invisible-in-figures](cvt-session-invisible-in-figures.md) — 유일한 변속 세션 26.04.29 가 비교 그림 코드에서 통째로 건너뛰어져 있었다 — 채점엔 들어가는데 눈으로는 못 봤다 (08-16 사용자 발견)
- `2026-08-14` [v9-seeds-were-start-points-not-random-seeds](v9-seeds-were-start-points-not-random-seeds.md) — "배포 궤적 v9a~d의 \"시드 4개\"는 난수 씨앗이 아니라 출발점 4개였다 (난수 씨앗은 11로 전부 동일) · 로그 문구는 고정 문자열이라 믿으면 안 된다"
- `2026-08-14` [torque-limit-15-is-a-design-choice](torque-limit-15-is-a-design-choice.md) — 축 토크 15 N·m는 하드웨어 한계가 아니라 사용자가 궤적 최적화에 거는 설계 목표다 — 다시 묻지 말 것 (반복 질문 3회 이상)
- `2026-08-14` [sign-check-without-model](sign-check-without-model.md) — 부호 의심은 모델 없이 판별한다 — PD 제어에서 토크는 위치 오차와 같은 부호. 36기록 전수 정상이었고 덤으로 결함 2건을 잡았다
- `2026-08-14` [no-window-splitting-verified](no-window-splitting-verified.md) — "창 분할 금지 규칙을 어겼고 근거가 틀렸다 — 게다가 통짜가 나눈 것보다 3.5배 더 잘 구분한다 (규칙이 성능이기도 했다)"
- `2026-08-14` [knee-loss-is-torque-proportional-not-mass](knee-loss-is-torque-proportional-not-mass.md) — 무릎 손실은 짐 무게가 아니라 명령 토크에 비례한다 (= 전달 효율) — 내 표현 오류 · 그리고 훑기가 원하는 값이 실측의 3.8배라 마찰 아닌 것이 섞여 있다
- `2026-08-14` [jump-data-cannot-separate-friction-from-torque](jump-data-cannot-separate-friction-from-torque.md) — 점프 창만으로는 마찰과 명령→축토크 환산을 구별 못 한다 (식별 불능) — 3~5회차 점프 점수가 제자리인 진짜 이유
- `2026-08-14` [deployed-jump-saturated-motor](deployed-jump-saturated-motor.md) — "26.07.27 배포 계획은 \"축 토크 14.65로 끝난다\"고 약속했으나 실제로는 22.56 요구·명령이 하드웨어 천장 초과 — 계획의 약속이 거짓이었던 사례"
- `2026-08-14` [board-average-hides-the-one-session-that-matters](board-average-hides-the-one-session-that-matters.md) — 채점판이 8세션을 평균해서 최종 목표를 재는 그 한 세션(26.07.27)이 희생됐다 — 6회차 승격 실패의 직접 원인 · 잠금을 안 넣은 내 실수
- `2026-08-13` [torque-map-flat-vs-measured](torque-map-flat-vs-measured.md) — 모델의 명령→축토크 환산이 전 구간 0.65~0.68로 평평하다 — 분동 실측은 저토크 1.26·고토크 0.86. 매달린 실험 구간에서 1.85배 어긋남
- `2026-08-13` [tau-fidelity-first-measurement](tau-fidelity-first-measurement.md) — "최종 지표(측정 토크≈계획 토크) 사상 첫 실측 — 무릎 28%/힙 46%(피크 1.49배), 힙 초과는 게인 비례"
- `2026-08-13` [scorer-self-reference-and-silent-drop](scorer-self-reference-and-silent-drop.md) — "채점의 자를 후보가 만지면 안 되고(자기참조), 기대 목록은 적재 결과가 아니라 등록부에서 — 08-14 세 구멍 실측"
- `2026-08-13` [score-composition-vs-final-goal](score-composition-vs-final-goal.md) — 무게를 준 대로 비중이 실리지 않는다 — 값 크기가 다르면 큰 항이 점수를 지배 · 5회차에서 점수 −20%인데 최종 지표는 악화
- `2026-08-13` [s2s-error-lives-in-transmission](s2s-error-lives-in-transmission.md) — 일어서기 오차는 변속기 저비율 구간에서 터진다 — 원인은 공통 물리(마찰·하중반영)이고 그 자리가 민감도 극대점 · 마찰은 하중비례 0.39 N·m/kg 실측
- `2026-08-13` [plan-alpha-outdated-twin](plan-alpha-outdated-twin.md) — 배포 계획의 힙 토크가 1.49배 틀린 원인 — 계획은 실효게인 축소(α 0.40/0.656)로 만들었는데 현행 트윈은 축소가 필요 없다
- `2026-08-13` [measured-value-transferability](measured-value-transferability.md) — 실측값이라고 모델의 그 자리에 넣을 수 있는 건 아니다 — 세 실측값을 전수 시험하니 답이 각각 달랐다 (무릎마찰 O · 힙관성 부분 · 토크환산 X)
- `2026-08-13` [load-proportional-knee-loss-confirmed](load-proportional-knee-loss-confirmed.md) — 하중비례 무릎 손실(fc1≈0.30)이 일어서기 3.16→1.54 **와 동시에** 최종 지표까지 개선(힙 −4.8% 무릎 −23.6%) · 6회차 1순위 축
- `2026-08-12` [relative-gates-miss-absolute-failure](relative-gates-miss-absolute-failure.md) — "직전보다 나빠지지 않았나"만 보는 게이트는 처음부터 망가진 것을 영원히 통과시킨다 — 변속기 24배 오차가 그렇게 숨어 있었다
- `2026-08-12` [prime_agent_billing_verdict](prime_agent_billing_verdict.md) — "Prime Agent(pi) — Claude 구독은 앤트로픽이 400으로 차단, ChatGPT(Codex) 구독은 정상 작동. 둘 다 2026-08-13 실측"
- `2026-08-12` [physics-split-across-rollout-paths](physics-split-across-rollout-paths.md) — 같은 물리가 재생 경로 둘 중 한쪽에만 구현돼 있으면 PD가 감춰 주는 판에서는 안 보이고 개루프 판에서만 터진다 (변속기 손실 08-12)
- `2026-08-12` [hip-inertia-freeswing](hip-inertia-freeswing.md) — "힙 모터축 관성은 현행 0.010이 아니라 0.014~0.019 (모터 끈 자유 흔들림 실측, 08-12) · 물리 판에는 무해하고 폐루프만 걸린다"
- `2026-08-11` [transmission-efficiency-knee-vs-hip](transmission-efficiency-knee-vs-hip.md) — "무릎만 전달효율 88%(힘비례 손실), 힙은 100% — 무게추 왕복의 상행-하행 절반차로 직접 측정"
- `2026-08-11` [quasistatic-is-lower-bound](quasistatic-is-lower-bound.md) — 느리게 잰 값은 탐색 범위의 하한일 뿐 — 실측을 그대로 고정하면 고속 몫이 들어갈 자리가 없어진다
- `2026-08-10` [report-format](report-format.md) — 사용자 지정 보고 형식 — 결론 한 줄 → 적용/미적용 before-after 표 → 전 후보 판정표(탈락 사유) → 발견 → 결정 대기 → 이월 → 랩업 상태 · 전 항목을 "고등학생에게 완벽히 이해시킨다" 수준으로 풀어서
- `2026-08-09` [cvt-link-length-source](cvt-link-length-source.md) — CVT 링크 길이 l_i 는 trial 별 Clutch.xlsx 실측 — 구 코드의 0.02499 는 실측이 아니라 점수 튜닝값이었다
- `2026-08-08` [video-scale-foot-ruler](video-scale-foot-ruler.md) — 영상 px→mm 자는 발 롤러 금속판 30mm (바깥 40mm) — 영상마다 재측정 · 추적창은 적응+수직구속 · 평활 금지
- `2026-08-08` [slip-measurement-facts](slip-measurement-facts.md) — "발 슬립 전수 측정(55 trial) 확정 사실 — 하강=세션상수, 푸시=59fps에서만 측정가능, CVT는 슬립 무영향"
- `2026-08-08` [measurement-vs-computation](measurement-vs-computation.md) — 결과가 일관되게 벌어졌을 때 판별자 — 측정량과 계산량을 따로 볼 것
- `2026-08-07` [payload-s2s-0604-validity](payload-s2s-0604-validity.md) — "26.06.04 페이로드 s2s — no_cvt는 0kg만 유효, load_5/7.5는 전부 기립 실패 (데이터 사전에 반대로 적혀 있었음)"
- `2026-08-07` [marathon-g-transmission-260808](marathon-g-transmission-260808.md) — "마라톤G — 접착제 canon_cap 의 정체 = 효율 75% 전동계 (독립 3중 확인), J_G 0.7519, 인공층 전멸"
- `2026-08-07` [jump-height-definition](jump-height-definition.md) — "점프높이 = 지면 기준 베이스 중심의 최고 높이 (Real Data.txt \"실제 점프 높이\" = 영상 실측 A급). 같은 파일 Expected 블록·GRF 체공시간은 높이 지표 금지 — 혼동 3회 재발"
- `2026-08-02` [robot-mass-slip-facts](robot-mass-slip-facts.md) — "실물 계측 사실 — 총질량 3.26kg(케이블 제거, 정합 허용 3.26~3.3) · 23일 딥스쿼트 중 발 슬립 8~10mm · 발 플레이트 120mm"
- `2026-08-02` [metric-provenance-rule](metric-provenance-rule.md) — 지표는 원본(Real Data.txt·xlsx·영상)에서 직접 재유도해 정의를 확인한 뒤 쓴다 — 파생 JSON을 사실로 승계하지 말 것. 점프높이 사건의 근본 원인
- `2026-08-02` [mass-ledger-truth](mass-ledger-truth.md) — "부위별 질량의 진짜 출처와 경계 (사용자 확정 08-02) — thigh 1.05kg은 knee모터 포함 묶음, crank/base는 적합, \"CAD VERIFIED\" 블록은 실은 적합값"
- `2026-08-02` [marathon-f-conserve-260802](marathon-f-conserve-260802.md) — "마라톤F(08-02) — supp 실체 = 저속 유지-보조 규명 (escrow 실패·속도게이트 held-out −41%), 선고정 기준 승격 없음, 벨트 SEA 차기 1순위"
- `2026-08-02` [goal23-knowledge-inventory](goal23-knowledge-inventory.md) — OLD α(p24) 이후 알아낸 것들의 검증 등급 목록 — 재정합 시작점 (2026-08-02 재정리)
- `2026-08-01` [marathon-e-slip-260802](marathon-e-slip-260802.md) — "마라톤E(08-02) — fs16=fs15+FS_PRESLIDE=0.86,0.85 확정 (Karnopp stick-slip 이력), J 0.854→0.824 전가드 통과, 레일 축 기각"
- `2026-08-01` [marathon-d-deploy-260801](marathon-d-deploy-260801.md) — "마라톤D(08-01, 진행중) — fs15 후보 (스큐+실게인, J 0.854·q2 −38%·dq2 −44%), 점프높이 sim 과대 발견, 소산 5J 실재하나 지지층 에너지 백도어로 주입 전패"
- `2026-08-01` [foot-rolling-vs-slip](foot-rolling-vs-slip.md) — 발 이동 = 구름 + 미끄럼 (혼용 금지) — 마라톤D P13 선행 판정을 E에서 잊고 재발견한 사건과 재발 방지 규약

## 2026년 7월 — 대체로 유효 (8월에 뒤집힌 것이 있을 수 있음) — 27건

- `2026-07-31` [marathon-c-track-260801](marathon-c-track-260801.md) — "마라톤C(08-01) — 결손 3분해(오프셋≤1°/마찰0/토크요구), 발배치 상태변수, τ_lim 유령 철회(사용자 반증), 진짜 축=커맨드층 PD 형태(0421 dq_des 미인가)"
- `2026-07-29` [sea_marathon_260728](sea_marathon_260728.md) — "SEA 마라톤 완주 (07-28~29 10:00) — H1~H25: 마찰성 직렬스프링(커맨드층 α 대체, CL −48~79% 전세션 승)+엔드스톱+유효질량+슬립지도. 후보 A/B 승격 대기. 차기 1순위=말기 hip 권위(12.2→2.8°)"
- `2026-07-29` [goal23_fullspan_260729](goal23_fullspan_260729.md) — "GOAL23 FULLSPAN 마라톤 (07-29~08-01, 3일) — 전 구간(*2) 데이터 백지 재구축 디지털 트윈. 플랜트 내장 스프링 재도전, 세션 상수=준정적 하강 창 캘리브, 졸업=변형C 대비 비악화+핵심 30%+게이지 2.5°"
- `2026-07-29` [ARCHIVE_INDEX](ARCHIVE_INDEX.md) — Archive Index — 과거 기록 색인 (필요할 때만 Read; 본문 파일은 전부 보존)
- `2026-07-28` [plant_marathon_260724](plant_marathon_260724.md) — "플랜트 마라톤 (07-24 자율) — (SUPERSEDED 07-28: 미끄럼→hip 직렬탄성 k_s≈160으로 재귀속, exp5 영상+ModeA 삼중수렴) 원결론: hip 과부하=발끝 미끄럼"
- `2026-07-28` [feedback_plain_language](feedback_plain_language.md) — "사용자 피드백 — 보고/설명에서 자기만 아는 용어 금지, 항상 풀어서 설명 (세션 중 3회 이상 반복 지적)"
- `2026-07-28` [feedback_notion_workflow](feedback_notion_workflow.md) — 노션 보고서/문서 만들 때 사용자가 원하는 방식 — 구조 계획 → 부분별 한 페이지씩 → 다양한 그래프 → 비유+논리+수식
- `2026-07-28` [deploy_first_real_experiment](deploy_first_real_experiment.md) — 첫 실기 배포 실험 (07-22) — CL 순수PD pd15 궤적 + 클립 리라이언스 제거 교훈 + α=1 검정
- `2026-07-20` [p25_deploy_rehearsal](p25_deploy_rehearsal.md) — "P25 배포 리허설 마라톤 (07-17) — 6방법 최적화×4배포전략×게인8종×토크캡 2종 전수, 최종 권고 = PPO t18 + FF+PD"
- `2026-07-18` [feedback_animation_standard](feedback_animation_standard.md) — 앞으로 모든 시뮬레이션 애니메이션은 goal18_CANONICAL 코드를 표준으로 사용. 모델이 바뀌어도 시각화 파이프라인은 이거 기준.
- `2026-07-17` [p20_rise_marathon](p20_rise_marathon.md) — "★★★ P20 마라톤 (07-13 진행중) — pre30 해체. 모터측(a_hat) 축 전체 기각(0429 교차게이트), 기준선 가설군 사용자 강등. 남은 카드 = raw 언랩 감사·TR_JUMP 19.5mm·벤치."
- `2026-07-13` [p18b_spring_identity](p18b_spring_identity.md) — ★★★★ stiff_knee 스프링의 정체 규명 (P18b 마라톤 07-09) — 약한 무릎 유연 0.40@calf + l_i=30 전용 보정토크 +2Nm (★07-13 '클러치 프리로드' 기구 해석은 기각됨, 항 자체는 유지). 0429 CVT 세션이 평행사변형 축퇴
- `2026-07-10` [p19_tau_fidelity](p19_tau_fidelity.md) — "★★★ P19 마라톤 (07-10 새벽) — 점프 CL τ-갭 지표 확립 + 커맨드 층 발견 (실효게인≠라벨 전 세션, 클립, α). 43.7→38.1% (바닥 ≈28%). Paper 보정식이 이 지표에선 A_fit보다 우월."
- `2026-07-09` [ultimate_objective_optimization](ultimate_objective_optimization.md) — ★★★★★ 사용자 최종 목적 (07-09 재강조) — 트윈 최적화 결과로 PD 배포 시 "측정 τ ≈ 계획 τ*" (PD 주입→0). 모든 지표·모델선택·최적화 설계의 판단 기준. 절대 흐리지 말 것.
- `2026-07-09` [next_goal22_mission](next_goal22_mission.md) — ★★ GOAL22 자율 마라톤 (07-08 11:00 cron) — dq·q 최우선 정밀화 + 샘플링 궤적최적화 트랙. 계획서 code/goal22/GOAL22_PLAN.md 필독.
- `2026-07-09` [fourbar_structure_critical](fourbar_structure_critical.md) — ★★★★★ 4-bar 링키지 확정 구조 (2026-07-07) — crank/rocker는 정강이 반대방향(무릎 위/뒤). 구위상 XML 사용 금지. 모든 4-bar 작업의 기준.
- `2026-07-09` [feedback_plot_colors](feedback_plot_colors.md) — matplotlib plot 작성 시 색을 명시 지정하지 말고 자동 cycle 색 사용
- `2026-07-09` [ak80_9_V2_spec](ak80_9_V2_spec.md) — "사용자 robot은 AK80-9 V2 (V3 아님). Peak 18 Nm, Rated 9 Nm."
- `2026-07-08` [reference_master_class](reference_master_class.md) — "마스터 클래스 노션 (MuJoCo 폐루프·접촉·최적화·샘플링 완전 정리, 07-07) — 부모 396ab81d2550814995dfc2e3a712ee01. 사용자 개념 질문 시 이 페이지 참조/확장."
- `2026-07-08` [next_goal21_mission](next_goal21_mission.md) — "★★ GOAL21 — 백지 해석적 회귀 System ID (사용자 제안 07-06). 계획서 code/goal21/GOAL21_PLAN.md. 새 세션 착수용."
- `2026-07-06` [goal20_marathon_state](goal20_marathon_state.md) — "★★★ G20 자율 마라톤 (07.05 02:40~16:00 KST) 완료 — 4-bar 트윈 확정 + NLP 목적실증 3단(-14→-4.4%) + 헤드룸 +14cm + 배포 CSV 3종. 이 파일이 G20의 canonical 기록."
- `2026-07-06` [goal19_control_architecture](goal19_control_architecture.md) — "★★★ 실 robot 제어 아키텍처 2종 + AK80-9 MIT 제어법 + closed-loop Mode A 돌파구. q/dq 미스매치의 진짜 해법"
- `2026-07-04` [real_jump_heights](real_jump_heights.md) — 26.06.02 실 robot 점프 높이 데이터 (Real Data.txt) — 정확한 값 출처
- `2026-07-04` [goal19_underjump_diagnosis](goal19_underjump_diagnosis.md) — "GOAL19 재검증 — 점프 under-jump 진짜 원인 = 누락된 knee 관절 유연성(flex). \"측정 한계/tau_scale\" 결론은 틀렸음(정정)"
- `2026-07-04` [goal19_qdq_error_sources](goal19_qdq_error_sources.md) — "GOAL19 q/dq 미스매치 광범위 오차원 종합 — 회귀 진단 + MASTER_INSIGHTS(G9~G16) 정독. 물리 lever 랭킹 + 죽은축 + per-trial tension"
- `2026-07-03` [goal19_final](goal19_final.md) — "GOAL19 완료 — 7-dataset 31-exp 통합 Mode A digital twin, 최종 모델·핵심 발견·구조적 한계"
- `2026-07-01` [goal18_canonical_pipeline](goal18_canonical_pipeline.md) — GOAL18 LOCKED canonical animation pipeline for sit2stand + jump datasets. Use this exact code for ALL future simulation rendering regardless of model 

## 2026년 6월 이전 — 초기 기록 (뒤집힌 것이 섞여 있다. 근거로 쓰기 전 최신 항목과 대조할 것) — 66건

- `2026-06-23` [mode_A_purpose](mode_A_purpose.md) — Mode A 본질 — Paper 변환 actual motor torque 입력 시 sim이 실측 q/dq/GRF 그대로 재현하면 디지털 트윈 달성. saturation κ 무관 (이미 hardware saturated 값).
- `2026-06-23` [feedback_sit2stand_cycle](feedback_sit2stand_cycle.md) — sit2stand 데이터 cycle 정의 — valley-based motion + ±0.5s pad + sim 전 real data 검증 필수
- `2026-06-22` [research_scope_cvt_multitask](research_scope_cvt_multitask.md) — ★★★ 연구의 진짜 범위 (CRITICAL) — 수직 점프 하나가 아님. 4-bar CVT가 수직점프+수평점프+sit2stand 최대하중 여러 task에서 이득을 줌을 증명하는 연구. 디지털트윈은 수단
- `2026-06-21` [user_thinking_patterns](user_thinking_patterns.md) — 사용자의 의사결정 패턴, 분석 깊이 선호, 거부 시그널 — Claude가 어떻게 응답해야 하는지의 가이드
- `2026-06-21` [user_profile](user_profile.md) — 사용자 연구 배경 — 로봇공학 연구자, 단족 점프 로봇 및 CVT 메커니즘 연구
- `2026-06-21` [unified_model_26_06_04](unified_model_26_06_04.md) — "26.06.02 점프 + 26.06.04 sit2stand+CVT load 통합 모델 (10 trials, 24 params). 점프 over-torque 원인 = M·ddq inertia."
- `2026-06-21` [sysid_findings](sysid_findings.md) — Multi-trial system ID 분석 — gAv≈1.57이 CAD(1.36)에 일치, sweep의 0.30이 ALPHA fudge factor 보상이었음
- `2026-06-21` [sweep_report_format](sweep_report_format.md) — V16+ sweep loop wakeup마다 표 형식 + 바운더리 양상 포함 보고
- `2026-06-21` [sweep_optimization_lessons](sweep_optimization_lessons.md) — 대규모 multiprocessing sweep에서 OOM/속도 문제 해결한 패턴들 — 169M sweep으로 검증됨
- `2026-06-21` [subagent_analyses_index](subagent_analyses_index.md) — 이전 세션에서 실행한 7개 Subagent(Task) 작업의 목적·결과·보존 위치 인덱스
- `2026-06-21` [session_recovery_state](session_recovery_state.md) — OOM 두 차례로 죽은 세션 상태 복구 — 어디까지 했고 어디서 다시 시작하는지
- `2026-06-21` [project_research_context](project_research_context.md) — 전체 연구 배경 — 4-bar link CVT 로봇의 2자유도 점프 최적화 및 실험, Sim-to-Real Gap 분석, 코드 구조 상세
- `2026-06-21` [position_data_26_06_02_model](position_data_26_06_02_model.md) — 26.06.02 position 데이터 기반 정확한 robot 모델 식별 최종 결과 — sit2stand vs jump 분리 분석, CAD 검증, RMSE 0.25 (s2s) / 1.7-2.9 (jump)
- `2026-06-21` [pd_sim_purpose](pd_sim_purpose.md) — pd_sim의 목표는 p_des/v_des 입력 시 실제 로봇과 동일한 응답을 내는 시뮬레이터. 모든 sweep·식별·검증의 기준점.
- `2026-06-21` [next_goal_mission](next_goal_mission.md) — 다음 goal mission statement + 사용자 정정 핵심. 2026-06-05 master insights 정리 후 사용자 명시한 진짜 진짜 goal. 새 세션 시작 시 첫 read.
- `2026-06-21` [next_goal8_mission](next_goal8_mission.md) — "GOAL8 미션 — Mode B Digital Twin 정밀화. PD sim 기반 fit, q/dq/τ/GRF 매칭 목적"
- `2026-06-21` [next_goal5_restart](next_goal5_restart.md) — GOAL5 RESTART (V1-V9 폐기). mujoco_menagerie Go1 정확 fetch + single-leg adapt. PD sat 변명 금지
- `2026-06-21` [next_goal5_mission](next_goal5_mission.md) — GOAL5 — 26.06.02 점프 데이터로 MuJoCo digital twin 검증. Reference 적용해서 토크/속도/GRF 일치까지 환경 파라미터 fitting
- `2026-06-21` [next_goal4_mission](next_goal4_mission.md) — GOAL4 mission - GOAL3 시뮬 결과를 실 robot으로 검증 + 모델 정밀화. 2026-06-06 GOAL3 V0-V25 완료 후 시작.
- `2026-06-21` [next_goal17_mission](next_goal17_mission.md) — ★ 다음 GOAL17 미션 — GOAL16 Iter17(157.42) 위 새 axis pool/실측으로 plateau 탈출. GOAL17_PROMPT.md 참조
- `2026-06-21` [next_fine_sweep_plan](next_fine_sweep_plan.md) — v3 sweep 완료 후 fine grid sweep으로 최적값 정밀 탐색하는 계획 — best 중심 narrow ranges
- `2026-06-21` [next_action_BO_hybrid](next_action_BO_hybrid.md) — V14 완료 후 Bayesian Optimization 기반 옵션 B 구현. Grid sweep boundary chasing 해결 + 시간 제약 없이 최대 탐색.
- `2026-06-21` [mujoco_range_bug](mujoco_range_bug.md) — MuJoCo XML의 joint range가 V20-like init 자세에서 huge artificial force 발생시키는 hidden bug (GOAL5R V23에서 발견). range 제거 또는 wide 설정 필수.
- `2026-06-21` [master_insights_pointer](master_insights_pointer.md) — 2-DOF jump robot 프로젝트의 모든 깨달은 점/발견을 한 곳에 모은 master 문서의 위치 + 사용법. 새 goal 시작 시 반드시 read.
- `2026-06-21` [jump_plan_post_sit2stand](jump_plan_post_sit2stand.md) — 점프 식별 계획 — sit2stand BO 종료 후 진행할 순서와 모델 변경 사항
- `2026-06-21` [jump_C_fixed_params](jump_C_fixed_params.md) — "Jump Strategy C sweep/BO에서 alpha, fb, M_tot는 user-FIXED. 확장 금지."
- `2026-06-21` [jump_C_bo_setup](jump_C_bo_setup.md) — jump_C_bo 셋업 — widened bounds + LHS seed + HybridSampler (TPE 70% + Random 30%)
- `2026-06-21` [hip_torque_lift_off_diagnosis](hip_torque_lift_off_diagnosis.md) — Sim hip 토크 lift-off transient에 +20Nm spike 발생 원인의 정량 분석 — 5°×Kp(300)=26Nm 산술과 foot length 부재로 설명됨
- `2026-06-21` [high_pd_outlier_150_500_5](high_pd_outlier_150_500_5.md) — 26.06.02 jump data의 150_2.2_500_5 폴더가 measurement outlier — 단일 모델 fit 불가
- `2026-06-21` [goal_task30_chatter](goal_task30_chatter.md) — Task 30 (sit2stand+payload) 속도 chattering 해결 ongoing goal (2026-05-27 새벽 작업)
- `2026-06-21` [goal9_findings](goal9_findings.md) — "GOAL9 — Mode A 디지털트윈 base-up. Baseline 74,609→848.85 (98.86%). Config D + 5 Mode-A insights (actuator=ideal torque)"
- `2026-06-21` [goal9_16_commit_map](goal9_16_commit_map.md) — "GOAL9~16 git 커밋 맵 (repo C:\\Users\\junho\\Desktop, 677 commits). GOAL14/15는 final 커밋 2개씩 존재"
- `2026-06-21` [goal8_findings_phase14_18](goal8_findings_phase14_18.md) — "GOAL8 Phase 14-18 핵심 발견 — sensor delay, multi-trial weighting, narrow refinement, trade-off 분석"
- `2026-06-21` [goal7_tau_scale](goal7_tau_scale.md) — GOAL7 발견 tau_scale 5-12% 실측 토크 underread 보정 필요
- `2026-06-21` [goal7_stage20_motor_tm](goal7_stage20_motor_tm.md) — GOAL7 Stage 20 BO 발견 motor LPF tm=8.37ms — 이전 33ms 가설 업데이트
- `2026-06-21` [goal7_final_results](goal7_final_results.md) — GOAL7 종합 결과 — Mode A 207.38 / Mode B 371.70 / 70.6% 개선 / 모든 plateau 확정
- `2026-06-21` [goal7_base_model](goal7_base_model.md) — GOAL7 base model 정의 — CAD 모델 + joint friction 0.1만 있던 초기 baseline
- `2026-06-21` [goal6_findings](goal6_findings.md) — "GOAL6 (full match no sat) Stage 1+2 결과. tau_real이 ±18 sat 안 함, 폴더 PD는 firmware PD (실 mechanical PD α_kp=0.19), motor LPF 33ms."
- `2026-06-21` [goal5_progress_v4](goal5_progress_v4.md) — GOAL5 GRF spike 해결 진전 - V1 2723N → V4 95N (실측 108-141N 일치). τ/q 정체 (PD sat 한계)
- `2026-06-21` [goal4_phase1_state](goal4_phase1_state.md) — GOAL4 Phase 1 (2026-06-06) — JAX direct + V15 robust 부분 재현 + Notion G4V1/V3, 실 robot protocol .md, MJX/Warp infra 완료
- `2026-06-21` [goal4_lessons_learned](goal4_lessons_learned.md) — GOAL4 V36-V55에서 배운 핵심 교훈 + 잘못된 분석 수정. 진짜 원인은 MuJoCo 환경 설정
- `2026-06-21` [goal3_final_stack](goal3_final_stack.md) — "GOAL3 종료 (2026-06-06) — V8 = V5 (30p) + AK80 saturation. 사용자 진짜 metric (forward consistency) 첫 직접 달성. NLP self-cons knee 0.16, forward drift T=0.05s 
- `2026-06-21` [goal2_final_stack](goal2_final_stack.md) — "GOAL2 종료 (2026-06-05) — V10/V12 두 후보 모델 final stack. 사용자 비판 5가지 응답 완료, 진짜 metric (점프 inverse RMSE) hip 0.93/knee 0.71. Notion 10-page 보고서 생성됨."
- `2026-06-21` [goal16_findings](goal16_findings.md) — "GOAL16 — plateau 탈출 시도. best Iter17 157.42 (KEEP 없음, DROP). 5D-global 단독 금지(규칙#9). worst-3 0424 고전류 floor 40.43"
- `2026-06-21` [goal15_findings](goal15_findings.md) — GOAL15 — 15-trial W_GRF=0.2. best Iter2 DE 160.79 (KEEP 없음). method-diversity 체인. 계획한 5개 물리축은 미실행
- `2026-06-21` [goal14_findings](goal14_findings.md) — GOAL14 — 9-trial W_GRF=0.3. 공식 KEEP best Iter28 89.847. Iter32 84.13은 raw 최저지만 keep=False. final 커밋 2개 주의
- `2026-06-21` [goal13_findings](goal13_findings.md) — GOAL13 — Iter38(176.41) 위 8개 orthogonal 축 전부 DROP (0 KEEP). Iter38은 absolute local min. 잔차=미모델 물리
- `2026-06-21` [goal12_findings](goal12_findings.md) — GOAL12 — 15-trial 통합. 공식 best Iter38 176.41. Iter42 128.57는 OVERFIT으로 기각. CAD m_calf 7.9% 과대 재확인
- `2026-06-21` [goal10_11_findings](goal10_11_findings.md) — "GOAL10(+11) — Pure Mode A, tau_scale=1.0 LOCK. Final v4 Iter27 132.84 (9-trial). per-trial fv의 kd-종속성이 dominant"
- `2026-06-21` [feedback_sweep_launch](feedback_sweep_launch.md) — User launches sweeps by double-clicking .bat files manually, NOT via PowerShell/Bash automation
- `2026-06-21` [feedback_sweep_consolidation](feedback_sweep_consolidation.md) — Multi-trial sweep(v9~)이 완료될 때마다 multi_trial_top_combined.npz 업데이트해야 함
- `2026-06-21` [feedback_pure_paper_formula](feedback_pure_paper_formula.md) — a_hat 모델은 항상 Pure Paper 식(sgn(v) only) 사용. GitHub s(v) smoothing 금지. 파라미터를 현실값으로 수렴시키는 게 목표.
- `2026-06-21` [feedback_notion_image_verification](feedback_notion_image_verification.md) — Notion 페이지에 이미지/애니메이션 업로드 후 항상 verification. GIF 특히 주의. 실패 시 재업로드
- `2026-06-21` [feedback_notion_image_upload](feedback_notion_image_upload.md) — Notion 페이지에 이미지 첨부할 때 항상 Notion API file_uploads 사용. imgur 등 외부 호스팅 금지. 작업 방법 + 토큰 + 패턴 전부.
- `2026-06-21` [feedback_goal5_model](feedback_goal5_model.md) — GOAL5는 Sonnet 모델로 진행 OK. Opus 불필요
- `2026-06-21` [feedback_git_commit](feedback_git_commit.md) — 코드 수정 후 자동으로 커밋하고 했다고만 알려주기
- `2026-06-21` [feedback_auto_approve](feedback_auto_approve.md) — User grants blanket permission for sweep-related operations during overnight runs
- `2026-06-21` [exp_validation_results](exp_validation_results.md) — soft+alpha 최적화 결과를 실제 로봇에서 실험한 결과 분석 (위치제어 6개 + 토크제어 3개)
- `2026-06-21` [digital_twin_priority](digital_twin_priority.md) — "매칭 우선순위 — 위치/속도/토크/지반력은 핵심, lift-off 시점은 부수적. 최적화가 실 결과 반영 목적."
- `2026-06-21` [decisions_log](decisions_log.md) — Sim-to-Real gap 연구 진행 중 내려진 주요 모델링/파라미터/방법 결정과 그 근거
- `2026-06-21` [code_files_index](code_files_index.md) — Desktop에 있는/있었던 .py 파일들의 용도와 상태 색인 (active/superseded/abandoned)
- `2026-06-21` [code_architecture_jump_opt](code_architecture_jump_opt.md) — "jump_opt 코드 아키텍처 — pipeline, score 함수, 12 per-trial params, simulator 설정, orchestration, a_hat 모델"
- `2026-06-21` [bo_tpe_db_size_limit](bo_tpe_db_size_limit.md) — TPESampler(multivariate=True) RAM cost scales with DB trial count; 300K trials = OOM crash on 64 GB
- `2026-06-21` [attempts_history](attempts_history.md) — 10일간의 Sim-to-Real Gap 분석 시도들의 시간순 narrative — 무엇을 시도했고 왜 다음 단계로 갔는지
- `2026-06-21` [analysis_findings](analysis_findings.md) — 2026-04-19 종합 분석 결과 — 접촉 컴플라이언스, 에너지/임펄스 비율, 토크 효율, alpha, 최적화 방향
- `2026-06-21` [ak80_9_torque_calibration](ak80_9_torque_calibration.md) — AK80-9 정밀 5-파라미터 토크 모델(a_hat) + 모든 모터 상수. UMich Neurobionics Lab 측정값. v7+ sweep에서 고정값으로 사용.

