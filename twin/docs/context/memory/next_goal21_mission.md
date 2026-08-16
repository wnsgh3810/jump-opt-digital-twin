---
name: next-goal21-mission
description: "★★ GOAL21 — 백지 해석적 회귀 System ID (사용자 제안 07-06). 계획서 code/goal21/GOAL21_PLAN.md. 새 세션 착수용."
metadata:
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL21 미션 — 백지 회귀 System ID

## ★★★★ P13/P14 (07-08) — η 사다리 붕괴(정정!) + 링키지 관성 첫 자유화 (둘 다 종결)
- **★★★ 사용자 지적 적중 → P1/P2 η 사다리는 인공물이었음**: l_i 고정이면 나사산 상대운동 0 → 스크류 효율 물리 부적용 (**스크류 카드 폐기**). 4-bar 정계수로 air 필요토크 재계산: knee 필요 0.04~0.07Nm (B≈0!) vs 실측 0.5Nm → η비율은 serial 오계수(B+0.175)로 나눈 허상. **실체 = knee 초과 쿨롱 ~0.45–0.55Nm (a_hat generic 대비, 속도방향 정렬), hip ~0.35Nm** — P6 시그널(a3_k↑)과 정합. 벤치 재교정 목표가 더 선명해짐. 방향 비대칭도 오계수 중력항 인공물 가능성. g21_eta_recheck.py
- **P13: crank/coupler CoM·관성 + 수동핀 마찰 6종 최초 자유화** (32-D CMA 1120평가, ho게이트): 선택해 obj 7.469 = 26-param 재적합(7.431)과 동일 수준 — **새 축들 무익**. s_rc 1.22/s_ip 1.11 등 미세 이동뿐. **M_p 가설 재기각: 1.82→2.41 (바운드로 질주)** → coupler+너트 실물 저울 측정이 유일 잔여 액션. p13_linkage.json
- 4-bar 모델링 개선 여지 종결 선언: 표현(1e-16)·구속강성(포화)·파라미터(26+6 전부 자유화 완료)·레거시 축(P12 전멸) — **남은 것은 모델이 아니라 실측 2건 (coupler 저울, knee 마찰 벤치) + 세션 보정**
- **★★ P13c (07-08): coupler 실측 150g (사용자) → M_p=1.098 LOCK.** 즉시 비용 +5.9% (비물리 M_p 1.82가 held-out 0324 full-stance를 떠받치고 있었음). 재적합 후: 창 −2~4%·habs −41% 개선 but fs_0324 +25%/s2s +8% 악화 = 트레이드 가족. **보상 흐름: 유령 ~100g이 thigh(+10%)·fv_hip(+45%)·CoM 안쪽 이동·offset(o2_0424 4.3→9.6°!)으로 분산 이사 — 해소 아님.** 결론: 질량 하나 잠그면 유령이 옆 파라미터로 숨음 → **crank·calf(가능하면 thigh·base) 저울 실측이 필요** (사용자에게 요청함). p13c_lockMp.json
- **P13b 바운드 확장 재적합 (사용자 지시)**: 레일링 5축 확장 (M_p→4.5, dz_th→0.2, arm_knee→5e-4, fc_knee→0, off→±17°). 결과 — ho게이트 선택해에서 M_p 3.23 내부 안착하나 **여유 준 만큼 계속 자람 (2.4→3.2) = 보상 방향, 물리 수렴 아님**; in-obj 추격해들은 M_p 3.6+에 ho 1.5~1.7 (과적합). 갤러리 비지배: 0421만 개선 (q2 44.8°, **h_ratio 1.000 역대최초 정확**), 0424/0602/0324 소폭 악화. o2_0424가 9.6°로 성장 = offset이 여전히 비물리 흡수. **판정: canonical = P10-selected 유지, M_p 저울 측정이 유일 결정타 재확인.** p13b_widen.json

## ★★★★★ P11 (07-07) — 사용자 해석식 기계정밀도 검증 + 위상 확정: canonical은 이제 FLIPPED
- **사용자의 Notion 4-bar 유도 페이지(302ab81d...) 전항 검증**: 항별 재유도 + 뒤집힌 MuJoCo와 무작위 300상태 대조 → **|dM| 4.4e-16, |dbias| 3.6e-14 = 동일 물리**. 경미 지적 3건만 (l_p=l_t 암묵, τ2=stator-on-thigh 가정, θ2 규약 토글 불일치) — 콜아웃 추가
- **정정 전 canonical은 사용자 자신의 식과 3.5e-2 불일치** (회전항 ~100% 상대) — 사용자 유도가 처음부터 옳은 위상(crank=정강이+180°)이었음
- **★ CAD 물리 발견: B = m_s r_s − m_c r_c − m_p l_c = −0.0037 (거의 완전 상쇄)** vs serial 뭉침 +0.175 (부호 반대 48배). 무릎축 중력토크 ≈0.04Nm → 전원-off 무릎 정지 관찰의 독립 설명. K=0.0029도 미소 = 4-bar가 base-무릎 결합을 거의 끊음
- **위상 뒤집기 = 물리적 필수 (교체 확정)**. 파라미터는 **P10-selected 권장** (obj 6.698/ho 0.938, 갤러리 3/4 개선, h 준유지: 0421 47.3°/1.076, 0324 10.8, 0602 3.48, 0424 11.8)
- v2 (1500평가, obj 6.577/ho 0.927): 트레이스는 최고 (0421 dq2 −26%, 0324 dq2 −37%)지만 **h_ratio 전 토크날짜 하락** (0.856/0.917/0.880) + 0424 q2 +47% — h가 목적에 없어서 창-지표 편향이 에너지를 깎음. **다음 폴리시: h/full-replay 에너지를 목적에 포함**
- v2 질량 재배분 계속: M_p 1.72→2.03, M_c 0.82→0.53 (미해결 축)
- 파일: g21_userEq_check.py, fourbar_flip_result{,_v2}.json, fourbar_flip{,2}_gallery.json

## ★★★★ P10 (07-07) — 사용자 하드웨어 정정: 4-bar 위상이 뒤집혀 있었음 → 뒤집은 모델이 첫 유효 승리 후보
- **사용자 정정**: 실물 l_o(rocker)는 무릎 **위/뒤쪽** 30mm (모델은 발쪽으로 넣었었음). 거울상 평행사변형 (crank도 같은 방향) — 기구학 1:1 동일, coupler·crank 질량 위치가 반대편 (~60mm)
- Stage0 (canonical 파라미터 그대로 + 뒤집기): obj 7.73으로 악화 **but held-out fs_0324 −29.5%** — 위상이 중요하다는 첫 신호
- Stage1 재적합 (600평가, ho게이트): **선택 후보 obj 6.698 / ho 0.938 — P5 원위상 최선(6.783)을 이긴 최초의 검증-통과 후보**
- 갤러리 full-replay: 0421 q2 50.8→47.3 (dq2 −15%, h 1.155→1.076), 0324 10.8 (dq2 −22%), 0602 3.48 — 3/4 날짜 개선; 0424만 q2 +17% 악화, h 소폭 혼조
- M_p 보상 가설은 불충족 (1.72→1.82). com_dz_th 0.059→0.094
- **판정: 물리적으로 옳은 위상이 성능도 동급 이상 — canonical 교체 후보.** 확정 전 잔여 검증: 0424 악화 원인, s2s_air/전체 지표, 렌더 확인. 파일: g21_fourbar_flip.py, fourbar_flip_result.json, fourbar_flip_gallery.json. Notion ④ 페이지 그림 v3+정정 콜아웃 반영
- **교훈: 구조 공간의 'local minimum'은 이렇게 탈출된다 — 옵티마이저가 아니라 하드웨어 지식 한 마디로** (P8 프로브 논증의 실증 사례)

## ★★★ P6 완결 (07-07, 사용자 지시 실험) — a_hat 공동 최적화: 같은 플래토, canonical 유지 + knee 마찰항 과감산 시그널 3중 수렴
- 사용자 지시로 Pure Paper 형태(sgn(v)) 유지한 채 a0~a4 자유화 (전기 공유 + 마찰항 관절별 = 7). Newton 역산으로 저장 τ→Iq 복원 (오차 3.6e-15, CSV 재읽기 불필요)
- Stage A (a_hat만): obj −8%, held-out 2.1배 = 과적합. 갤러리: 0424/0602 개선하나 0324 폭발 (11.9°→18.6°)
- Stage B (26+7 공동, 1543평가, 후보풀 19): 검증-선택 (ho 0.887) obj −3.5% — 갤러리에서 비지배 (0424 q2 +7%, 0602 h 악화, 0324 q2 +39%) → **canonical 유지 (플래토 4중 확인: 0424+0602 refit / P5 / P6)**
- **★ 물리 시그널 (3개 독립 프로브 일치)**: 옵티마이저가 항상 a3_k ↑ (0.27→0.49/0.56) + a4_k 음수 요구 = **범용 UMich a_hat의 knee sgn(v) 마찰항이 우리 유닛에서 고|Iq| 시 과감산** (hip은 정상). ahat_probe(fc_eff<0 선호)·η 사다리와 같은 방향 → **모터 벤치에서 a3_k/a4_k 재교정이 지목된 실험**
- 파일: g21_ahat_refit.py (역산+병렬 CMA 2-stage), ahat_stageA/B.json, ahat_cands.jsonl, g21_ahat_validate.py, ahat_validate.json
- 참고: 데이터 500Hz / sim 2kHz implicitfast (fit 유효 해상도 500Hz)

## ★★★★ P5 완결 (07-07) — 4-bar canonical은 게이밍 안 됐음: 하이브리드 refit도 트레이드오프만, canonical 유지
- 질문: canonical 4-bar도 창-단독 fit이니 v1-스타일 게이밍 사각지대가 있는가? → **아니오 (serial과 결정적 대조)**
- CMA 1500평가 (창5+fs2, canonical=7.0) + held-out fs_0324 게이트 + 검증-기반 선택:
  raw best −7.4%는 held-out 1.83배 = 과적합 (v1 300평가도 2.2배 — **두 번 반복된 패턴: 하이브리드 목적조차 held-out 게이트 없으면 과적합**)
- 검증 통과 후보(−3.1%, ho 0.987)를 갤러리 full-replay로 심판: 0421 dq2 −21%/0324 dq2 −30% 개선 **BUT 0424 q2 +37% 악화, h_ratio 토크 날짜 전부 악화** → 지배 아닌 트레이드 → **canonical 유지**
- sharp-optimum 증거: sigma 0.10에서 480/480 전패 (canonical = 좁고 날카로운 최적점)
- ★ 종합: serial은 하이브리드로 −29% 진짜 개선 / 4-bar는 0% — **명시적 4-bar 구조가 게이밍 여지 자체를 제거**했었음. 26-param 재가중으론 더 못 감 (0424+0602 refit 0.0%과 정합 = 식별성 플래토 3중 확인)
- 다음 개선 경로 = 파라미터가 아니라: ① 리드스크류 물리식 (스크류 리드/피치경 스펙 사용자 대기), ② 새 데이터 (모터 벤치/가진 궤적/레일 낙하), ③ 폐루프 지표 전환 (τ=PD 출력이므로 폐루프 full-horizon이 배포 시나리오와 동형)
- 파일: g21_fourbar_hybrid.py (병렬 CMA+후보풀), fourbar_hybrid_best.json, fourbar_hybrid_cands.jsonl, g21_fourbar_validate.py, fourbar_hybrid_validate.json

## ★★★★ P4 완결 (07-06 자율 연장) — 하이브리드 refit 승리 + 4-bar 포팅 기각 (양쪽 다 결정적)
- **★★★ 방법론 대발견: 창-단독 mshoot 목적은 게이밍됨.** v1 refit(창 6그룹): 전 그룹 30%+ 개선하면서 full-stance q2 2.4배 악화, vto +18% — 0.1s 상태 리셋이 저속 편향 누적을 숨김. **모든 미래 fit에 full-trajectory 그룹 필수** (v2: 창6+fs2, canonical=8.0)
- **v2 하이브리드 최종 (serial goal19_final 스택)**: knee fc 0.99→0.47 + fv 0.36→0.16 + Stribeck(c=4.94, vs=1.46, w=0.44); **hip fv 0.71→0, fc→0** (hip 점성이 push-off 파워를 갉아먹고 있었음 = 구조적 under-jump 부분 원인). obj 8.0→5.68
- full-stance: q2 −24/−31%, dq2 −42/−48%, **whip 0.54/0.73 → 0.73/0.95** (고질 실패지점 해소), out-of-sample 0324 dq2 −54%/whip 0.87 (단 q2 +35%), vto +20~26%
- **★★★ 4-bar 포팅 기각 = 구조 검증**: GATE 14984.4 정확 재현 후 8구성 전부 +28~57% 악화 (s2s 2배) — **serial의 Stribeck 항은 명시적 4-bar 구조의 대리물**. 4-bar canonical엔 불필요 (G20-A 구조 결정의 독립 증거)
- **적용처: CasADi NLP 모델 (serial 2-link!)** — 항이 smooth/미분가능, NLP 동역학을 4-bar/실물에 근접시키는 direct 후보
- 미결: hip 마찰≈0의 물리성 (air-hip 에너지 손실 0.9Nm과 긴장), 0324 q2 +35%, air 극영역 잔여, ★η사다리 재해석 필요(η<1 일부는 serial 구조 오차 = 4-bar 가변 감속비일 수 있음 — 순수 산일 아님)
- 파일: g21_stribeck_refit.py(병렬 8-worker, ~2s/eval), stribeck_refit_best.json(v2)/[v1_windowonly], g21_fullstance_check.py, g21_fourbar_stribeck.py, fourbar_stribeck_duel.json
- GitHub push 거부 지속 (repository rule, 62+ 커밋 적체) — 사용자 확인 필요

## ★★★ P3 완료 (07-06) — knee Stribeck 초과손실 = 3-영역 통일 KEEP 후보
- 대칭 fc_knee 스윕: s2s는 ~2.0 원함, 점프는 ~1.0 원함 (상충) → 방향 분리 실패 (push-off와 s2s 기립 = 같은 신전 방향) → **속도 분리 성공**
- **KEEP 후보: τ_extra = −c·tanh(v₂/0.15)·exp(−|v₂|/vs), c≈3.0Nm, vs≈1.0 rad/s** (canonical fc_knee 0.988 위에 추가, replay ctrl-측 항)
- 성적 (baseline duel 27386 / air 207436): c3/vs1 → duel 22699 (−17.1%), air 139185 (−33%). s2s_gnd −58%, 0421 −10%, 0424/0602 +4~5% (비용), 0324 중립. 점프 h 무영향 (push-off 속도에서 exp(−15)≈0)
- 부하비례(β·|τ|) 기각: duel 대등하나 air −0.7%뿐 — **air 무릎은 stall이 정답인데 loss<|τ|라 stall 불가**
- ★ 에너지 사다리와의 정합: 동적 손실(에너지 창) ≈ 1Nm(v≥1), 정적/breakaway ≈ 3Nm (무운동=에너지 지도에 안 보임) = 전형적 Stribeck. 전원-off 관찰 재확인: knee 1.72Nm 정지 (3.0>1.72 ✓), hip 2.78Nm 낙하 ✓
- Frontier: air는 c=4.5까지 계속 개선 (−46%) but 점프 +8.5% — 균형점 c=3/vs=1 권장. vs=0.7이 duel 최적(22628), vs↑는 air쪽 유리
- ★ 남은 P4: Stribeck 포함 전체 재fit(관성 미세보정) + LODO 검증 + NLP smooth 항 이식 (미분가능 → 최적화 바로 사용 가능). 주의: duel 점수는 튜닝=평가 동일 (air만 순수 out-of-sample)
- 파일: g21_fc_knee_duel.py, g21_dir_loss_duel.py, stribeck_duel.json (air 포함), loadprop_duel.json

## ★★★ P2 완료 (07-06) — 스탠스 에너지 회귀 → η(부하) 사다리 + 상수 손실 통일
- 설계 교훈: 스탠스는 구속-투영 대신 **에너지 형**이 정답 (접촉력=무일, ddq 불필요). 단 ① bz는 FK라 비행 무효 → push-off 연속 스탠스만, ② 소프트 접촉 일 → Δ(GRF²) 컬럼(c=1/2k)으로 선형 흡수, ③ 합성검증은 비행 M-대조로 (접촉 있는 에너지 창 검증은 원리적 무효)
- **스탠스 1-DOF 매니폴드에서 관성 식별 불가** (cond 5e5) — 식별 가능량 = 일 비율 η
- **★ η(부하) 사다리**: air(≈1Nm) knee 0.05–0.13/hip 0.41–0.49 → s2s_gnd(≈4Nm) 0.694 [0.65,0.73] → jump push-off(≈13Nm) 0.94 (**mid-push 0.99 = CAD 관성 에너지 검증**). GOAL19 "구조적 under-jump" = η≈0.94로 정량화
- 날짜 구조: 0424 0.77–0.97 vs 0602 0.88–1.13 (>1 존재!), 두 날짜 모두 저게인 trial이 높음 (W+ 연결)
- **★★ 사다리가 상수로 붕괴**: η = 1 − a/|τ|, a≈0.9Nm (양 관절) — 그리고 **canonical 4-bar refit의 fc_knee=0.988과 독립 수렴** (에너지 회계 vs q/dq replay 두 방법 일치 = 교차 검증)
- fc_knee 대칭 스윕: 총점 최적 ≈2.0 (s2s −52%!) 그러나 점프 +8~14% 악화 — 대칭 상수의 한계, **방향 비대칭(자기잠금) duel 진행 중** (g21_dir_loss_duel.py: 올림 유지 + 내림 추가 손실 예측)
- 파일: g21_stance_energy.py, stance_regression.json, eta_load_map.png, fc_knee_duel.json

## ★★★ P1 완료 (07-06, 세션 내 착수) — 전달계 특성 규명
- 도구 검증: 해석 2R 모멘텀 회귀 = MuJoCo와 1e-14 일치, cond 37, B≈L1k2 (g21_air_regressor.py)
- **★ 대발견: air에서 측정 τ는 하중의 일부만 봄** — 전달 효율 η(v)=측정τ/CAD요구τ: **knee 0.05→0.13** (0.05~6 rad/s), **hip 0.41→0.49**. 방향 비대칭이 자기잠금 시그니처: **knee raise 0.40/lower −0.18** (내림은 나사가 전담), hip 0.60/0.34
- 사용자 전원-off 관찰과 정량 일치: hip 중력 2.78Nm@−45°에 "스르르" 낙하(마찰~2Nm급), knee 최대부하 1.72Nm 유지(비역구동). q_des 주면 그 자세에 정지
- 잔차는 속도-부호가 아니라 **하중 모양** — 고전 쿨롱 아닌 부하-지탱 전달계. 점프 fit의 작은 마찰(fc 0.057)과 모순 없음: 점프(고속·고부하)에선 η≈1 (창 fit CAD급 성립이 방증) — **η(v,방향,부하) 지도가 P2에서 스탠스 데이터로 확장 필요**
- 함의: air는 관성 식별용 불가/전달계 특성용 최적. 진짜 관성 ID는 P2(스탠스 투영). 트윈 확장 후보 = 방향·속도 의존 전달 효율 요소 (점프 영역 η≈1이라 현 점프 트윈은 무영향)
- 파일: g21_air_regressor.py, air_regression.json, efficiency_curve_air.json

**사용자 제안 (2026-07-06)**: a_hat 유지, dynamics를 백지에서 — 해석적 EoM + 회귀 ID.
joint 마찰/발끝 마찰/미끄러짐/q offset/4-bar compliance/**레일 마찰(신규)** 포함, s2s_gnd도 fit.

**계획서**: `CVT/twin/code/goal21/GOAL21_PLAN.md` (커밋됨) — 데이터 전략(s2s_air=무접촉 주력, 스탠스=구속 투영으로 GRF 소거), 1단계 선형(base params+마찰+레일+offset 선형화, ddq 필터 가중), 2단계 잔차 지도 기반 비선형, 3자 검증(회귀 vs CAD vs canonical 트윈 → 최종 multiple shooting 대결).

**착수 전 알아야 할 07-06 교훈** (goal20_marathon_state.md 07-06 섹션 필독):
- τ 잔차 계열 4중 기각 (scale/poly/MLP/sign-v) — 잔차는 whip(고속+고부하) 집중 상태의존
- W+ 법칙: 저일 trial일수록 replay 나쁨 (corr −0.86), "잘 추종할수록 재현 나쁨" −0.72 (순수 PD라 τ=100% 피드백)
- dq: 모양·타이밍 완벽, whip 진폭만 오차 (버그 날짜 과대/정상 강성 과소)
- B(관절/카메라)는 방법 의존 — 0324만 robust B>1. 비행 기반 레일마찰 추정 불가 확인
- 0424+0602 전용 재피팅 0.0% (데이터셋 무충돌), offset ±2° 물리 제약 확정
- 신규 실험 큐: **레일 낙하시험(30초, f_rail 직접)**, 카메라-관절 이중측정, 유형C 재실행(90_0.75_90_2 반복), t_ff/dq_des 전송 검증, 저속 breakaway, 모터 벤치 whip 영역(전압한계/back-EMF)

관련: [[goal20-marathon-state]] [[goal19_control_architecture]] [[ultimate_objective_optimization]]
