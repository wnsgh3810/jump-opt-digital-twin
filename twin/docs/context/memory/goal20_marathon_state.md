---
name: goal20-marathon-state
description: "★★★ G20 자율 마라톤 (07.05 02:40~16:00 KST) 완료 — 4-bar 트윈 확정 + NLP 목적실증 3단(-14→-4.4%) + 헤드룸 +14cm + 배포 CSV 3종. 이 파일이 G20의 canonical 기록."
metadata:
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# G20 자율 마라톤 — ✅ 완료 (2026-07-05 16:00 마감)

## ★★★ 07-06 날짜별 정확도 최종 통합 이해 (사용자와 공동, 해설 페이지 395ab81d 심화 1~5)
- **R(sim/카메라) = B(관절/카메라) × M(sim/관절) 분해**: 전 날짜 B>1 (관절이 카메라보다 9~17% 높이 약속 — 원인 미확정: 카메라/FK방법/이륙손실. 다음 세션 이중측정 필요). 0324 "좋아보임"=B×M 상쇄 착시(M 0.814), 0421 overshoot=M≈1.04.
- **dq 렌즈**: 트윈은 dq 모양(corr 0.96-0.99)·타이밍(≤14ms) 전 날짜 정답, 오차는 **whip 진폭뿐**. 부호가 전송으로 갈림: 버그 날짜 sim 과대 whip(최대 4.3배, 얼려진 제동), 정상 강성 과소 whip(0.56-0.89, 얼려진 조력). 정확 페어(같은 지령+게인) 0421 vs 0424: dq 24-25배 차이.
- **★ 사용자 가설 채택 (최강 상관)**: 순수 PD(τ_ff=0)라 τ=100% 오차×게인 → 게인↑→추종↓(−0.89/−0.91)→토크·일↓(W+ −0.84, 25.8→18.7J)→**replay dq 적합도↓ (corr(W+,dq오차)=−0.86, 추종오차와 −0.72 "잘 따라갈수록 재현 나쁨")**. 0424 세션계단의 대부분이 "저일 영역 진입"으로 대체 설명(매칭 W+에서 잔차 1.4배). 메커니즘: 고정 0.5-1Nm급 ID 잔차가 저일에서 상대적 지배 + tight tracking일수록 τ가 순수 모델불일치 보상신호. 0324(버그)는 이 법칙 예외. 거칠기 계열(저크/계단/dτdt) 3연속 기각. 배포(τ_ff가 일 공급)는 유리한 조건.
- **a_hat sign(v) 보정 프로브 기각 (07-06)**: 유효 무릎 Coulomb 음수 허용 스윕 → 단조 악화(−0.3에서 +4.4%, −0.9에서 +45%), whip 0.62→0.63 무회복. fc_knee 하한 railing은 상수 보정 요구가 아니었음. **τ 잔차 계열 4중 기각 확정 (scale/poly/MLP/sign-v)** — 잔차는 상태의존·whip 구간(고속+고부하) 집중. 최우선 조준 실험 = **모터 벤치 고속·고부하(전압한계/back-EMF) 영역 토크-전류 곡선**. 파일 mshoot_ahat_probe.py.
- 다음 실험 체크리스트 추가: 유형C 재실행(같은 config 반복=세션요인 순수 측정), 카메라-관절 이중측정(B 원인), t_ff·dq_des 전송 검증, 저속 breakaway, **모터 벤치 whip-영역 우선**.

## ⚠️ 07-06 사후 정정 (사용자 지적, CRITICAL)
0. **0424+0602 전용 재피팅 실험 (사용자 질문)**: 배포 모드 데이터만으로 재피팅해도 **0.0% 개선** (240 CMA evals, warm=round-1, ±2° offset 제약, s2s 포함) — round-1이 그 부분집합에 대해서도 이미 최적. **데이터셋들은 충돌하지 않으며(0324/0421이 fit을 끌어내리지 않음), 잔여 창 오차(q2~1.4°)는 데이터 가중이 아니라 모델 클래스 한계.** 저토크 정확도(사용자 요구)는 재피팅으로 불가 — 신규 실험(저속 램프 breakaway/공중 chirp) + 비평활 마찰 요소 필요. τ_ff는 하드웨어 미사용 경로(사용자 확정, desiredTorque 컬럼=참고 로깅) → 배포 전 전송 검증 필수(README 반영). 파일: mshoot_refit_46.py.
1. **per-date offset 재해석**: fitted 3–8°는 엔코더 캘리브레이션 오차 아님 (사용자: 물리 상한 1–2°). 검증 — ±2° 클램프 시 +4.4%뿐(0324에만 +31.5% 집중, 0424/0421 큰 값은 flat 허수, s2s는 개선), ±2° 재적합은 0.0% 개선·물리 파라미터 불변 = 어떤 물리 축도 대체 불가한 순수 각도기준선 성격. **offset = 과거 세션 채점용 nuisance (±2° 제약 채택), 전이 목적 무영향 (트윈/배포/held-out h는 offset 미사용)**. 0324 무릎 ~6° 상당 계통차 — 추가 검증으로 정체 좁힘: l_i 전 세션 30mm(사용자 확인, 기하 기각) + 시작 crouch 판독 날짜간 1~3° 일치(정적 기준선 문제 아님) + 발끝고정 운동학 테스트는 confounded(rolling/슬립, 0602도 6° 나옴 → 무효 폐기). **결론: 저토크(peak 11Nm)·완만한 3월 궤적 영역에서 커지는 미상의 모델/측정 잔차의 대리 흡수** (3월 측정체계 품질 이력과 일관). 파일: fourbar_refit_o2deg.json.
2. **0424 drift 메커니즘 철회**: "착지 충격→slip/이완/발열"은 과잉 추측이었음. 사실만 유지: 순서 vs h_ratio 상관 −0.63, trial3→4 계단, 0602 동일 게인 무편차(±0.014) — 메커니즘 미확정. 날짜별 그래프 품질 차이의 종합 진단: 모델·궤적·제어방식 아님(측정으로 기각), 세션 고유 계통오차를 full-replay가 증폭하는 구조. 0421은 별개(ill-posed 소점프 replay, 계통적 overshoot 1.155).

## ★ 완료 요약 (압축 후 이 섹션만 읽어도 전체 파악)

**최종 모델 (round-1 canonical, `code/goal19/phase11/fourbar_refit_best.json` → baked `goal20_final_model.json`)**: 4절링크 명시 구조 + per-date offset + 26-param joint refit. 창 q2 1.2-1.5°(4날짜 균일)/dq2 0.83-1.00, held-out h 0424 0.878/0602 0.941/0324 0.925, LODO fold2/3 ratio 1.000, fudge 0, multi-seed 안정, 불확실성 stiff_knee ±4.6% 최강. round-2/polish/MLP 3중 기각으로 fit-일반화 frontier 최적점 확정.

**신규 발견 (07-05 마라톤분)**:
1. **NLP 목적실증 3단 체인**: 무마찰 gap −14.0%/0.998m → +식별마찰 −6.4%/1.051m → +접촉 k_eq 매칭 **−4.4%/1.063m (+6.5cm)** — "모델 정확도↑=실물 성과↑" 정량 증명
2. **접촉이 gap 부호 결정**: soft=에너지 착취 over-predict / hard=+3.3% 보수 / **k_eq(실측 1.3e5 N/m, 하중스윕)=스윕 최적대와 일치 (상호검증)**. 실무: NLP k_c≈1.3e5+식별마찰
3. **헤드룸 +14cm**: 실측최고(0602 0.980m) replay 0.929 vs NLP τ* 1.063, 카메라환산 ≈1.12m. T-N 데이터 포락선: knee=실증범위 내, **hip 8-14rad/s 미개척 영역=이득의 원천**
4. **배포 CSV 3종** (`nlp_demo/deploy/`): τ예산 70/85/100% 각각 재최적화. 사다리 +1.5%/−0.9%/−4.4% = **준최대 거의 완벽 전이**. CL 사전검증: PD+ff는 −11cm 구조적(knee 포화+참조 고정) → **1차 기대 0.95-0.97m**, 상한은 ff-위주/ILC/트윈 위 직접 TO
5. **s2s_air stiction 발견**: 준정적 hold(τ<2Nm)는 리드스크류 비역구동성 — smooth 마찰족 화해 불가(air −10% vs guard +36%) → **트윈 유효범위 = 동적 영역 전용**

**산출물**: 보고서(artifact 7eeaec44…, 10섹션+그래프24+포락선), Notion G20 페이지 393ab81d… + 상세해설 자식 394ab81d…, 애니 25(canonical), repo 전부 커밋(트리 클린). **다음 실험**: 새 세션 q-offset 캘리브 → s0.70 CSV 재생(hip 추종 관찰) → s0.85 → s1.00 → 편차를 트윈에 피드백.

---

# 이하 마라톤 진행 기록 (시간 역순 아카이브)

**★★★★★ 최종 목적 (사용자 04:12 재강조 "목적도 절대 잊지마")**: 트윈은 수단. **목적 = 트윈으로 궤적 최적화 → sim-to-real 잘 되는 최적 궤적 획득.** 제어 = 최적화 q*,dq*를 고게인 PD + τ* 피드포워드, **τ_applied ≈ τ*가 되게**. 모든 판단 기준: (i) 일반화가 fit 점수보다 우선 (최적화는 새 궤적 생성 = 학습 데이터 밖), (ii) NLP에 들어갈 수 있는 형태(smooth, CasADi 호환), (iii) T-N 한계 제약, (iv) fudge는 transfer를 깨므로 금지. 큐의 NLP 데모(c)가 이 목적의 첫 end-to-end 실증.

**★★★★★ 제0규칙 (사용자 03:15 재강조: "그래프와 시뮬레이션은 우리 기준이 되는 코드 그걸 기준으로 해야해! 항상!!")**:
- **그래프** = `make_viz.py` 스타일 그대로: matplotlib 기본 색 cycle (sim 파랑 실선 C0, real 주황 점선 C1), 색 명시 금지
- **jump 애니메이션** = `goal18_v9/_make_anim_universal_colored.py` (드라이버 `make_anim_v3_canonical.py`) — 새 렌더러 작성 절대 금지
- **s2s 애니메이션** = `goal18_CANONICAL/code/make_anim.py :: render_sit2stand`
- 4-bar 모델 시각화도 동일: sim log(t,q,grf_z npz — q는 렌더용 [bz,hip,knee] 3열로 crank→knee 좌표 추출) + canonical 렌더러에 투입. 렌더러 내부는 건드리지 않는다.

**사용자 지시 (2026-07-05 02:40 + 03:15, VERBATIM 정신)**: "가능성 높은 것부터 다 해보자, 여기 있는 것 말고도 더, 이전 goal/MD/논문/오픈소스 다 참고, 07.05 16:00 KST까지 끊임없이 찾고 적용하고 개선하고 디버깅, 내가 아무말 안해도 알아서 계속." + **"나 모든 걸 승인할 테니까 16:00까지 절대 멈추는 일이 없도록. 선택해야 할 게 있으면 그냥 다 해버려. 나 중간에 봐줄 수 없어."** → AskUserQuestion 금지, 분기점은 전부 실증 비교로 해결, ScheduleWakeup으로 루프 유지.

**마감 산출물 (16:00 cron e2fb9d95이 트리거)**: ① 최고 모델 확정+baking ② canonical 규격 그래프(기본 파랑/주황)+애니메이션(jump=goal18_v9/_make_anim_universal_colored.py, 절대 새 렌더러 금지) ③ **초상세 self-contained HTML 보고서** (현 대시보드보다 훨씬 자세히, 그 페이지만 읽어도 전부 이해, 모든 링크 정리) — artifact URL https://claude.ai/code/artifact/7eeaec44-536d-4a56-9556-444c0f874d04 재배포 ④ **Notion 페이지 생성+정리** ⑤ 전체 커밋+메모리.

## 핵심 발견 (03:10 기준)
1. **★★★ 4절링크 명시 모델 (G20-A)**: crank C링크(0.656kg, l_i=30mm CVT 조절기구 포함, CAD R_C=0.0207)가 역대 전 모델에서 CALF에 lumping → 유령 병진질량 = "가벼운 calf+높은 회전관성" railing의 진짜 원인. 명시 parallelogram loop(crank→coupler(P,0.137kg)→calf rocker, **connect solref="0.0008 1" 필수** — 기본값은 물러서 crank가 1 rad 분리 헛돎) = **fitting 0회 pure CAD로 CAD-serial 대비 −9.0%, 풀피팅 v3 대비 +3.2%**. 인코더=crank(qpos[2])=기존 q2 매핑과 일치.
2. **★★ per-date offset (G20-B)**: 0602(6월,양호)=기준, 0319s2s/0324/0421/0424 세션별 q1/q2 offset. ±5°에서 **−16.3%** (0324 +3.9/+3.7°, 0421 +0.1/−4.9°, 0424 +3.8/+4.7°) — 사용자 증언 "3,4월 calibration 오류"와 일치.
3. **A2 joint refit round1 완료 (03:20)**: 16914→14984. **창 q2 전 데이터셋 1.2-1.5° 균일, dq2 0.83-1.00.** 물리성 회복: M_calf 0.92(rail 해소), fc_knee 0.057(마찰 흡수재 소멸), arm 0.0035+crank 관성 0.0009≈AK 물리값 0.0044. **held-out h_ratio: 0424 0.878 / 0602 0.941 / 0324 0.925** (여정 시작 0.73-0.77). 남은 rail: com_dz_th@0.06, o2_0324@8°, solref@0.006 → round2(bound 확장: dz±0.10, off±12°, solref 0.010, warm) 진행 중. eval ~1.7s/개라 300evals≈10분.
4. **전 가설 심판 완료 (04:00)**: round2 기각(flat-direction, held-out 패배 — window 동률시 held-out+물리성 중재 원칙). Stribeck 기각(−1.7%<2%). 잔차 τ-poly 기각(LODO fold B 악화 = tau_scale 금지 소급검증). LODO: fold 2/3 ratio 1.000, 0424 fold 1.285.
5. **산출물 1차 완료 (03:55)**: goal20_final_model.json baking / 그래프 24(4-bar, 파랑/주황) / 애니 24(canonical, anim_final/) / **한국어 초상세 보고서 배포** (artifact 7eeaec44… 동일 URL) / **Notion 페이지 393ab81d255081e89a2ce5c6966328b1** (CONCEPT 아래) / 전부 커밋.
6. **사용자 추가 지시 (04:10): "개선할 게 없어 보여도 절대 멈추지 말 것 — 논문/코드 서치, 새 인사이트, 딥러닝/강화학습 등 다른 방법 적용, 계속 연구 발전."** 확장 큐 (우선순위순):
   a. multi-seed 안정성 (러닝) → held-out 재검증 후 채택 판단
   b. CasADi 축약 등가성 (serial+등가 knee armature ≈ 4-bar?) — 최적화 단계 실용
   c. **★ NLP 데모 — 최종 목적 미리보기**: 새 트윈(축약모델)으로 max-height jump 궤적최적화(direct collocation, T-N 18Nm 제약) → 4-bar sim에서 검증 → "트윈→최적화→검증" 파이프라인 실증. 최고 가치.
   d. **딥러닝**: Hwangbo식 소형 MLP 액추에이터 잔차 (창 잔차 학습, LODO 게이트 — poly 실패했으니 MLP도 기각 예상되나 지시대로 실증)
   e. 불확실성 정량화: CMA 표본으로 핵심 파라미터(arm_knee/stiff_knee/offsets) 신뢰구간 → 보고서 error bar
   f. s2s_air 보너스 검증 (fit 제외 데이터로 추가 held-out)
   g. 논문/코드 서치 세션 (jump 최적화 sim2real, mini-cheetah 점프 등) → 보고서 related-work 보강
   h. 15:00~ 모든 신규 결과로 보고서/Notion 최종 갱신 → 16:00 마감

## 04:15~ 추가 결과 (최종 보고서에 반영할 것)
- **NLP 데모 (목적 폐루프)**: task0 NLP(해석 4-bar EoM — GOAL3 NLP가 원래 옳았고 MuJoCo lumping이 어긋났던 것) + G20 파라미터 + τ≤18: h_pred 1.160 vs 트윈 replay 0.998 (**−14%**). NLP→트윈→실제 체인(−14%→−6~12%) 정량화 = 트윈이 중간 필터. 파일 code/goal19/nlp_demo/.
- **MLP 잔차 DROP**: train −3.1% vs held-out +0.1% = 딥러닝도 날짜 암기. tau_scale 금지 3중 실증(상수/다항/신경망).
- **민감도**: stiff_knee 최강 식별(+10%→+8.8%), M_c −10%→+3.7%; M_c/M_p +10%에 소폭 개선 여지 → mass polish 진행.
- **multi-seed**: 3 seed 동일 수렴 = 안정 최적점.
- **related-work 추가분**: arxiv 2110.06764(3D 점프 TO, 토크포화-contact timing), 2309.07038(단족 RL), 2309.01813(contact-implicit MPC), 2509.06342(sim2real 체계화), 2504.12854(compliant 도약).
- **polish 기각** (held-out 전 지표 악화 — round-1이 일반화 최적점 3중 확인: round2/MLP/polish).
- **★★★ NLP gap 분해 (05:40, 보고서 하이라이트)**: NLP 무마찰 h_pred 1.160→트윈 0.998 (−14.0%) / **NLP+G20 마찰 h_pred 1.122→트윈 1.051 (−6.4%)**. gap 절반 + **트윈 점프 5.3cm 상승** = "NLP 모델 정확도↑→실물 성과↑" 목적 명제의 정량 증명. 잔여 −6.4% = 접촉 유연성+stiff+쿨롱. 파일 nlp_demo/g20_vertjump_fric.py.
- **★★★ NLP 접촉모델 스윕 (05:20, 07-05)**: NLP 접촉 강성이 gap 부호·크기 결정. soft(k=5천~4만)=스프링 에너지 착취→over-predict(−6~−12%); **hard=보수적(+3.3%, 트윈이 예측 초과)**; **트윈 강성대 k=1e5→실현높이 최고 1.065m / k=2e5→gap 최소 −2.8%**. 마찰이 지배적(전 마찰변형 ≥1.007 vs 무마찰 0.998). `nlp_demo/contact_sweep_results.json` 커밋됨. 관련논문: Impedance Matching arXiv 2404.15096 (같은 결론). 기존 데모가 ALPHA=0.85 구fudge로 돌던 것도 발견→α=1 재검증 포함.
- **★★ s2s_air held-out (06:40, 07-05) — 새 물리 영역 발견**: fit에 안 쓴 air 15 cycles에서 실 다리는 τ≈0.04Nm로 정지 유지(중력 요구 0.3-1Nm)하는데 트윈은 낙하 = **저토크 준정적 stiction/CVT 리드스크류 비역구동성** (점프 10-50Nm에선 비중 미미해서 안 보임). 진짜 stiction 하이브리드(frictionloss=fs + 이동시 assist 복귀) 3중 프로브: fs=(2.5,3) air −10%/guard +36%, VS=0.5 air −1.3%/guard +7.3% → **DROP, smooth 마찰족으론 두 영역 화해 불가**(이력성 비역구동 추정). 보고서에 "트윈 유효 범위 = 동적 영역(τ>수 Nm), 준정적 hold 제외" 명시. 파일: mshoot_s2s_air_holdout.py / mshoot_stiction.py / *.json 커밋됨. G20-C Stribeck이 −1.7%였던 이유도 규명(tanh 주입은 v=0 유지토크 0 = stiction 표현 불가).
- **★ 불확실성 (1% iso-score 구간, 06:50)**: 강식별 stiff_knee ±4.6% / M_thigh ±5.5% / M_c ±8.4% / imp0 ±12% / solref_tc ±22% / arm_knee ±37%; 약식별 fv_hip ±32%, fv_knee ±123%; **flat(음곡률=국소 ridge/노이즈)**: M_calf, fc_knee, o1/o2_0324 (o2_0324는 8° 부근 boundary-lean, round-2 held-out 기각으로 확장 안함). uncertainty_iso1.json. 보고서 error bar 소스.
- **✅ 상세 해설 Notion 페이지 (13:40, 사용자 직접 요청)**: 마라톤 전 과정 서사 해설 (용어 정의 포함, 12섹션+표5) — G20 페이지 자식 `394ab81d255081c0866bf56af22a8b8c`. 원문 `code/goal19/G20_MARATHON_EXPLAINED.md` 커밋. 내용=Fable 작성, 업로드=Sonnet 서브에이전트 (사용자 지시 패턴: "내용은 높은 모델, mcp는 소넷").
- **★★ 배포 CL 사전검증 (13:10)**: closed-loop PD+ff(kp90/kd0.75·2.0, ±18 클립)는 open-loop 대비 **−11cm (1.063→0.954)**, 추종 1°인데도 — PD가 NLP 참조 운동학에 트윈 고정+knee 포화로 +보정여력 0 (구조적; hold 무효, kp150 +1.4cm뿐, α_kp=0.19 시 0.936). **정직한 1차 기대 0.95-0.97m ≈ 현 최고 동급 이상**; 상한 1.06은 저게인 ff-위주/ILC/트윈 위 직접 TO. deploy_cl_check.json 커밋, 보고서·Notion 반영.
- **★★★ 배포 패키지 (12:00)**: `nlp_demo/deploy/` — τ 예산 70/85/100% 각각 재최적화 CSV 3종(t·q_des·dq_des·τ_ff canonical) + README(게인 kp90/kd0.75·2.0, 점진 프로토콜, 안전). **사다리: 70% +1.5% / 85% −0.9% / 100% −4.4% gap — 준최대 궤적 거의 완벽 전이, 85%만으로 현 실측최고 수준(0.957 vs 0.929)**. NLP 최적 canonical 애니 anim_final/nlp_optimal_jump.gif (goal18_v9 렌더러, apex 1.063 표기). 전부 커밋(3439336)·보고서·Notion 반영.
- **★★★ 실전 헤드룸 +14cm (10:45)**: 같은 트윈·같은 τ≤18에서 실측 최고 trial(0602 90_0.75_90_2, 카메라 0.980m) replay 0.929 vs NLP τ* 1.063 = **+13.4cm(+14.4%), 카메라 환산 ≈1.12m**. T-N 데이터 포락선 검증: knee=실증 범위 내(로봇이 이미 21.1Nm·29.6rad/s 실증, bang-bang 18Nm 유지 가능), **hip=스펙 내지만 8-14rad/s 미개척 영역 사용 = optimizer 추가 높이의 원천**. 다음 실험 권장: 최적 궤적 70→100% 점진 재생. nlp_envelope_check.png(§7 임베드), headroom_results.json. 보고서·Notion·커밋 반영.
- **★★★ NLP 완결판 (09:35)**: k_c=k_eq=1.3e5 정확 재실행 → **h_pred 1.112→트윈 1.063, gap −4.4%**. 최종 3단 체인: 무마찰 −14.0%/0.998m → +마찰 −6.4%/1.051m → **+접촉 매칭 −4.4%/1.063m (+6.5cm)**. 보고서(verdict 카드 −14→−4.4%)+Notion+JSON+커밋 전부 반영, artifact 재배포(keq-definitive-run). §7 완성.
- **★★ k_eq 자기일관성 (08:40)**: 트윈 접촉 등가강성 실측(하중 스윕 0.5-8g, 힘-침투 선형 fit) **k_eq≈1.3×10⁵ N/m** = NLP 접촉 스윕 최적대(1e5-2e5)와 정확 일치 — 두 실험 상호 검증. 실무지침 정량화: NLP k_c≈1.3e5 + 식별 마찰. 보고서·Notion 반영, artifact 재배포(label keq-self-consistency), 커밋 완료.
- **✅ 보고서 v2 배포 완료 (07:40)**: NLP 마찰분해+접촉스윕 표(§7 신규), iso-1% 불확실성 표, MLP/polish/stiction 기각 카드, 유효범위, related-work(임피던스매칭·Linderoth stiction·리드스크류) 전부 반영해 artifact 재배포 완료. 빌더 repo 보존(code/goal19/report_builder.py). **15:00 최종 갱신 잔여**: Notion 페이지에 신규 발견 반영(§7 요약+air stiction+불확실성), 이후 신규 결과 있으면 재빌드·재배포, 대표 GIF/그래프 SendUserFile, 최종 커밋+요약보고.

## 파일맵 (`CVT/twin/code/goal19/phase11/`)
- `mshoot.py` 창 하네스(0.1s/0.05 jump, FK캐시) + MARCH loader(0324 3trial, 0319 제외)
- `mshoot_refit_best.json` = **v3 serial canonical** (jump창 13239, held-out h 0.84-0.94)
- `mshoot_fourbar.py` 4-bar XML+창eval / `mshoot_fourbar_refit.py` joint refit / `fourbar_refit_best.json` (결과)
- `mshoot_dateoff.py` date offset / `dateoff_best.json` (±5° best)
- `mshoot_sea.py` SEA 기각 기록 / `make_viz.py` 그래프(파랑/주황) / `make_anim_v3_canonical.py` 애니 드라이버
- 로그: scratchpad/{fourbar_refit,dateoff5,...}.log

## 대기 큐 (완료 시 다음으로)
1. A2 refit 결과 → held-out 전체궤적 검증(h!) + 물리성 판정 → best로 채택 여부
2. **G20-C**: Stribeck 마찰 (4-bar 구조 위에서) — 착지창은 데이터에 착지 없음 확인되면 스킵
3. **G20-D**: 잔차 액추에이터 poly 모델 + LODO (통과시만 채택)
4. 여유 시: hip에도 4-bar? (hip은 직결이라 없음), 미분가능 fitting(MJX), coupler CoM/관성 fit축
5. FINAL: 산출물 (위 마감 산출물 목록)

## 규칙 (변경 금지)
- 금지: tau_scale, motor_tm, per-trial fudge, backlash, 관성텐서 단독 fit(rank-deficient), 새 렌더러
- 그래프: matplotlib 기본 색 cycle (sim 파랑 실선, real 주황 점선)
- 애니: jump=goal18_v9/_make_anim_universal_colored.py (사본 code/goal19/canonical_render/), s2s=goal18_CANONICAL/make_anim.py
- 검증: 창=fit, 전체궤적+카메라h=held-out, LODO 권장. GRF는 target 아님(참고 표기만).
- 제외 데이터: jump_torque_0422(유일 외부PD루프, 토크 불일치), jump_0319 NO_TR(데이터 불량)
- 제어 아키텍처: 03.19/03.24/04.21=AK 내부 MIT PD(dq_des=0), 04.22만 외부루프, 04.24/06.02=MIT(q+dq)
- 커밋 트레일러: Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com> + Claude-Session: https://claude.ai/code/session_018tXRZDWy9RG1Z1qWD21UNo

관련: [[goal19_control_architecture]] [[goal19_qdq_error_sources]] [[feedback_animation_standard]] [[ultimate_objective_optimization]]
