---
name: next-goal22-mission
description: ★★ GOAL22 자율 마라톤 (07-08 11:00 cron) — dq·q 최우선 정밀화 + 샘플링 궤적최적화 트랙. 계획서 code/goal22/GOAL22_PLAN.md 필독.
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL22 — dq·q 정밀화 + 샘플링 최적화 마라톤

**시작**: 2026-07-08 11:00 cron (사용자 지시: 연구·서칭·디버깅·분석·적용·피드백 루프, dq/q 최우선·h 차선, NLP 필수 아님 — 샘플링 방법론 폭넓게)

**계획서 (필독)**: `Documents/jump-opt-digital-twin/code/goal22/GOAL22_PLAN.md`
- P1★★★ dq 계측 필터 규명 (로그 dq = 펌웨어 필터? → 심판 지표 교정 — 유령 정체 1순위)
- P2★★ 벨트 직렬 탄성(2차 SEA) 모델
- P3 P13f dq-가중 프런티어 / P4 노이즈-바닥 / P5 offset 독립 검증
- P6★★★ 샘플링 궤적최적화 3종 (CMA/MPPI/PredictiveSampling) vs NLP 정면 비교
- P7 외부 리서치 / P8+ 자율 확장

**절대 규칙**: 물리 케이지 유지 (M_p 150g LOCK·총 3.2kg·calf=CAD·offsets≤3°), 유령질량 부활 금지,
held-out 게이트 + 갤러리 심판, 창-단독 점수 불신, canonical json 덮어쓰기 금지 (새 파일).

**기준 모델**: `fourbar_honest_canonical.json` (P13e). 현 상태: 토크날짜 h 0.90/0.96/0.96 (최고),
dq2가 P10 대비 +5~18% 열세 (0602 최대) — 이 dq 회수가 P1~P3의 표적.

**진행 로그 (사용자 관람용 — 매 phase 갱신 필수)**:
- artifact `https://claude.ai/code/artifact/3e626825-aeb7-4f2f-9831-1e89cff212c5` (파일: scratchpad `g22_progress.html`, 같은 경로 재배포 = URL 유지, favicon 🏃)
- Notion GOAL22 페이지 `396ab81d2550814b9780f32285133840` (CONCEPT 아래) — 링크 게시됨, 중요 결과 요약도 추가
- (마라톤 진행 상황은 여기 아래에 갱신)

**진행 (07-08 마라톤, 06:00~11:00 — cron은 종료알람으로 정정됨)**:
- P1 ✅ 기각: 로그 dq=raw 1-샘플 백워드차분 (fc>250Hz 평탄, delay≤1ms, CAN 12bit ±50rad/s 스텝 0.0244, q 16bit 3.815e-4). 심판 공정 → dq2 열세는 진짜 물리 결손. 커밋 14a5393
- P2 ❌ 기각: 벨트 SEA(모터측 엔코더 재해석 포함) — 유연할수록 전 그룹 단조 악화, rigid 극한이 최선. 실물 벨트≈강체. k=2e4는 수치불안정(J_red 8.5e-4, 한계 k≈7e3). 커밋 f58c856
- P3 ✅ **P13f 승리**: W_DQ 150 재적합 → 표준심판 obj 7.83(−2.1%), ho 0.937(−6.3%), 갤러리 거의 전 지표 개선(dq2 15.8→14.5, 3.6→3.2), h 비용 ≤1.2%p. `code/goal22/p3_dqw150.json` (selected). W_DQ=300 극단점: obj 7.91/ho 0.914 (`p3_dqw300.json`). P13e가 자기 목적 최적점이 아니었음 (dq-가중=재시동 효과)
- P4 ✅ 노이즈바닥: dq2 오차의 38~89%(0421 88.7%)가 환원불가, q2 36~63%. hip은 q1 17~21%/dq1 10~35%만 바닥 → **개선 여지는 hip축이 5~9배**. `p4_noisefloor.json`
- P5 ⚠️ 불능판정+발견: 크라우치 정적 τ가 모델과 ~3-4Nm 불일치(offset 감도의 40배) → 정적 offset ID 불가. 동적은 잘 맞으므로 = **레일 스틱션**(미모델, hip ~3Nm 대신 부담) + **stiff_knee 스프링 정적편향(−3.3Nm)**. 실험실 벤치 표적 추가
- P6 ✅: 샘플링 3종 vs NLP — 착취 2회 적발·교정 후(과신전 하드스톱 + **토크-속도 곡선 포화를 rollout 물리에 내장**: 20rad/s까지 18Nm→59.7rad/s에서 0 선형) 최종 **CMA 1.209m > PS 1.161 > MPPI 1.115 > NLP replay 1.009** (2400 rollouts=6초/방법). 이득 원천=hip 활용(dq1 18.6 vs 12.4, 322W vs 138W)=G20 헤드룸 확인. 배포 CSV `deploy_g22/jump_g22cma_s1.00_h1.209m.csv`+`s0.85_h0.975m.csv`. 교훈: 봉투는 벌점 말고 물리로, 비행 whip에 벌점 금지(h는 이륙 시 결정)
- P8 ✅: 레일 kinetic Coulomb 기각(0.25N부터 전면 악화) → 레일=스틱션-only(정지 시 hip ~3Nm, 운동 시 <0.25N). 역대 축 7종 P13f 위 재검증 전멸
- **P8c-d ✅ 계측 스큐 발견**: sens_delay=−1.5ms 단봉 최적 (τ 로그가 q보다 1.5ms 앞섬; 전류식 τ 즉시 vs q 샘플링+CAN 지연 정합). 보정 고정 재적합 → **P13h: 표준 obj 7.413(−7.3%), ho 0.898(−10.2%), habs 0.851** = 종합 최강 후보. `code/goal22/fourbar_p13h_candidate.json` (사용 시 τ replay에 −1.5ms 시프트 필수)
- **최종 프런티어 (canonical 미교체, 사용자 선택 대기)**: P13e(현) / P13f(균형, 갤러리 0421 최고) / P13g(dq 최소·ho 0.907) / **P13h(종합 추천)**. 갤러리 859e050e에 4-모델 아님 3-모델(e/f/g) 24-trial 오버레이 게시됨
- P9 ❌ hip Stribeck 기각 (c=0.2 노이즈, 이후 단조 악화) — P4의 hip 헤드룸은 분산 원인. P6b: CMA 시드 ±1mm 일관, 9600 rollouts(34초) 1.233m 포화. P6c: LP-MPPI α=0.8 +1.9cm(1.134)이나 CMA 열세 확정
- 노션 GOAL22 페이지에 요약 게시, 진행 로그 artifact 최신 상태. 커밋 체인 14a5393→634854a

**07-09 τ-fidelity 실험 시리즈 (P10~P13i, 커밋 ~8e3abb4)**:
- P10 폐루프 재현 v5 확정: 라벨게인+무클립+a_hat (계측: PD무클립·12bit±18랩+언랩·τ스큐−1.5ms·0421 실효게인 ~0.7×라벨). 결과물 `Desktop/jump_opt/g22_cl_results/` + artifact 6e33131f (τ-fidelity 페이지)
- P11: PD-only는 완벽모델도 τ-갭 3.3/5.2Nm 구조적 → **t_ff 송신 필수**. 모델교차 기여 ≤0.06Nm
- P12: **스탠스 널-공간** (fit−label τ차 95%가 불가시방향, 발끝 x힘으로만 발현)
- P13 구간분해: fit은 dq2-지배 목적 → q1 희생. reg(회귀 실효게인) 제3기준
- **P13i (p13i/ 폴더)**: 폐루프 τ-채널 심판 재적합 → CL심판 −13.4% (0421 τ1 −39%) BUT **Mode A obj +32% 악화 — 두 심판이 마찰 배치(fv/fc_hip↑ vs h↓)를 두고 충돌** = a_hat 손실항⊕관절마찰 이중계산이 병목이라는 실증. **모터 벤치 a_hat 재식별이 두 심판 동시 만족의 유일 경로로 확정**
- **cl_fit2 (cl_fit2/ 폴더)**: 게인-적합 v2 (τ채널+정규화+구간가중) → 널-드리프트 봉쇄 (78-99%→19-69%), fit_old의 hip τ 폭파(4.5-6.5Nm) → label보다 좋아짐 (0421 0.93 vs 4.18). **★0421 실효 hip kp ≈ 0.6×라벨 이중 확증** (fit2 39-115 ≈ 회귀 45-111, 독립 수렴; 0421 널비율 98%는 게이밍 아닌 라벨 오류의 표현). 고게인 knee(250-500)는 전류천장 탓 유효강성 ~0.5-0.7×. 결과: `Desktop/jump_opt/g22_cl_fit2_results/`
- **cl_fit3/cl_fit4**: 프런티어 완성 — fit3(τ유지+q1·dq2가중): q1 최고급+τ건전, dq2 −30%. fit4(τ제거): q1·dq2 역대 최고지만 τ_hip 6-9.6Nm 폭파+널 92-96% 복귀. **게인 공간에서 상태↔τ 보존법칙 4점 실증**. COST_fit1~4.txt 각 폴더 기록
- **★★P14 (p14_ahat/)**: 이중 심판(ModeA+CL τ채널) 동시 적합 + **a_hat 4계수 해방** → **충돌 해소 (JA 0.985 + JC 0.911 동시 개선**, P13i는 −13%/+32% 분열). 데이터 식별 a_hat: **A1·CF 0.682→0.714(+4.7%), A4 −51%, A3 −9%, A2 ×2**; 관절 점성이 흡수(fv_knee 0.048). habs −36%, dq2 전반 개선. **한계: full-replay 언더점프 미해소(0424 0.907/0602 0.938), w_s2s +25% 대가 — 저속(s2s)·고속(점프) 영역이 다른 a_hat 요구 = paper 모델 구조 한계, 속도의존 항 부재 힌트. 최종 확정은 모터 벤치** (fitted 곡선 = 벤치 검증용 정량 예측, p14_ahat_curve.png). 후보: `p14_ahat/fourbar_p14_candidate.json`
- **P15 (p15_vterm/)**: 사용자 제안 최소판 — a_hat에 A5·v만 추가, Mode A 단독 적합 + 미학습 폐루프 시험지. 판정: ① **A5→0 (속도 텀 기각** — 관절 fv와 중복, Mode A가 선택 안 함); 대신 P14 방향 단독 재발견 (A1·CF→0.736, A3 −26%, obj −3.9%). ② **미학습 폐루프 전이 미약** (dq1만 일관 개선 0.77→0.61/0.74→0.68, 나머지 중립) — Mode A 단독 a_hat 수정은 τ-fidelity로 자동 전이 안 됨 → 이중 심판(P14 구조)이 필수임을 재확인
- **P16 (p16_structure/, 07-09 저녁)**: 사용자 지시로 동역학 구조 감사 → ① **springref 해방 = 승리** (역대 미검증 1-D; drop-test로 stiff_knee 실재 재확인 JA×4.9; ref=0 LOCK이 P5 정적편향의 원인이었음). 37-dim 이중심판 통합 재적합 → **ref=2.07, 정적편향 −80%, obj 추가 −2.8%, 양 게이트 통과** → `fourbar_p16_candidate.json` = **현 최강 스택** (CL: P13h 1.0 → P14 0.91 → P16 ≈0.88). ② 레일 stick-slip 기각 (0602 악화, 균일 Fs 불가). ③ 발 형상 = 실물 그대로(사용자 확인, 실린더 맞음 — 닫힘). ④ 하중비례 관절마찰 = 사용자 보류(과함). **벤치 대안: 중력-벤치** (다리 공중 자세유지 = 중력이 알려진 부하; 발끝 추 걸면 중부하) — 사용자가 나중에 직접 하기로
- **a_hat 항등 대조실험 (07-09)**: 폐루프에서 a_hat 빼면 h는 불변(PD가 게인 오차 흡수)이나 **q2 추종 모양이 2.4~3.1배 악화** — a_hat은 폐루프에서 에너지가 아니라 응답 강성/모양으로 필요. **사용자 아키텍처 판정: identify→optimize→deploy 본류에서 sim 모터는 이상적이어도 됨; a_hat은 경계 3곳만** (①데이터→식별입력 ②최적화 제약 번역 ③t_ff=a_hat⁻¹(τ*) 내보내기 + sim게인→실기 환산 1/0.68)

관련: [[fourbar-structure-critical]] [[next-goal21-mission]] [[reference-master-class]]
