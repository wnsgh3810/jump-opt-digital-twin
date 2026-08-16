---
name: goal19_underjump_diagnosis
description: "GOAL19 재검증 — 점프 under-jump 진짜 원인 = 누락된 knee 관절 유연성(flex). \"측정 한계/tau_scale\" 결론은 틀렸음(정정)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

GOAL19 (2026-07-03 재검증). 사용자 "다 해봤다는 게 틀렸다" + "tau_scale 안 쓴 다른 모든 goal 참조" 지적 후 결론.

**★ 최종 결론 (정정됨)**: 점프 under-jump의 진짜 원인은 **누락된 물리 축 = knee 관절 유연성(transmission compliance, MuJoCo `stiffness` Nm/rad, springref=0)**. 
- tau_scale 안 쓴 이전 GOAL(**GOAL10**)이 이 축으로 점프 높이 ratio ~0.87 재현했음 (GOAL19 금지 목록에 flex는 없음).
- GOAL19 통합 모델에 stiff_knee=1.15 추가 → **total 15,121→11,572 (−23.5%)**, jump h_ratio 0.563→0.741.
- **높이 fudge 아님 증명**: 합산 jump rmse_q1 −49%, rmse_q2 −37%, rmse_dq1 −33%, rmse_dq2 −34%, dh −41% **동시 개선**. q/dq/height 전부 좋아짐 = 실제 누락 자유도 회복. hip stiffness는 무의미(knee 전부).

**★ 처음 내렸던 "측정 한계" 결론은 틀렸음 (교훈)**: "under-jump split이 AK80-9 전류토크 포화 under-read → tau_scale로만 보정"이라 성급히 결론냈으나, 이전 goal 이력을 참조하니 flex라는 정당한 비-금지 축을 빠뜨린 것이었다. **"다 해봤다"는 성급한 판단이었고, 이전 goal 참조가 결정적이었다.**

**반증된 가설들 (여전히 유효)**: foot slip(μ 0.4→3.0), real jump init, base_z offset → 무변/악화. viscous friction fv→0은 전 그룹 균일 +0.08(차이 원인 아님). GRF chattering(RK4)은 실재하나 높이엔 무관 → `implicitfast` 채택.

**★ 후속 재최적화 (완료)**: flex 추가 후 (stiff_knee, solref_tc, imp0, m_foot_ex) 4D CMA-ES → **foot mass 0.227→~0**. Phase 1의 무거운 foot은 누락된 flex를 보상하던 대체물이었음(진짜 물리 넣으니 불필요). 접촉 부드러워져(imp0 0.371→0.147) **GRF chatter 완전 제거**(ΣGRFrmse 970→658, pre-flex 797보다 낮음). **total 11,572→11,241, h_ratio 0.774**. 최종: stiff_knee=1.20, solref_tc=0.00258, imp0=0.147, m_foot_ex≈0. jump h_ratio 그룹별 0421=0.90, 0422=0.88, 0602=0.73, 0424=0.69.

**★ 12-D 결합 재적합 (Phase 11d, 완료)**: dq2/GRF 잔차 dig-deeper. 단일 축(arm_knee↓, I_calf, springref) 전부 h vs dq2 vs total 맞바꿈만 → 순차 phase가 flex 체제에서 stale. 12-D CMA-ES(flex+contact+mass+calf-CoM+arm_knee+friction) 재적합 → **total 11,241→10,183 (−9.4%, Pure CAD −75.3%)**. stiff_knee→2.0, fc_knee→0.99(CVT Coulomb, 물리적, runaway 아님-plateau). dq2 84→79. hard jumps(0424 h0.73, 0602 0.75)+sit2stand↑. **Trade(정직)**: position jump 0421 h 0.90→0.82 (score 약간의 재분배). overall h 0.772 flat. 남은 dq2(sim 18 vs real 27)는 구조적 잔차. tau plot 부호는 좌표계 표시 이슈(수정): sim=−real 프레임, 겹치게 negate.

**★★ 잔차 최종 규명 (Phase 11e, capstone)**: 남은 dq2(sim 18 vs real 27)/GRF/height 잔차가 torque under-read인지 진단(diagnostic tau_scale, 모델 채택 X). 결과 **어떤 torque boost도(uniform tau_scale OR current-dependent threshold boost) height는 올리지만 dq2 추종·total은 악화** → 잔차는 torque under-read 아님. 실측 dq2를 뜯어보니(stored=numeric deriv 일치, 물리적 실재) **real dq2가 push 내내 moderate하다 마지막 ~10ms에 27로 spike, 그 순간 torque는 이미 음(braking)으로 전환** = torque-driven 아님. **near-full-extension 기하 특이점(다리 펴질수록 관절 유효관성 붕괴)에서 knee velocity가 튀는 효과**를 sim이 과소재현. 결론: 잔차는 takeoff 순간 near-singularity 동역학 = tau_scale로도 못 닫는 구조적 한계. 현 모델(10183, h 0.73-0.85)이 GOAL19 규칙 하 실질 floor. 진단 훅 `TAU_SCALE_DIAG/TAU_SAT_*` (default no-op).

**★ LODO 일반화 (Phase 11f)**: leave-one-jump-dataset-out 재적합. **12-D broad refit(11d)은 mean ratio 1.37 (max 1.60) = 중간 정도 overfit** (held-out이 in-sample보다 37% 나쁨; pre-flex Phase10은 1.04였음). **★ 정정 (ratio는 오해 유발)**: 4-param(11c) LODO 돌려 비교하니 mean ratio 동일(1.376 vs 1.366), max는 오히려 4-param이 나쁨(2.23 vs 1.60). **절대 held-out error로 비교하면 12-D가 4/4 중 3개 승**(0424 479<484, 0602 283<300, 0421 516<586; 0422만 4p 우세). 합 12-D 1622 < 4p 1682. 즉 **12-D(10183)가 실제로 더 잘 일반화** — 높은 ratio는 in-sample도 잘 맞춰서 생긴 착시. **최종 = 12-D 10183 유지.** 교훈: overfit 판단은 ratio 아닌 절대 held-out error로. 0421(position-PD)은 두 모델 다 held-out ratio 높음 = 별개 regime(position vs torque), 모델 결함 아닌 data diversity.

파일: `goal19_final_model.json` (joint_flex+broad_refit_note), `code/goal19/phase11/reopt_broad_flex.py`, `lodo_flex.py`.
**★★ 기구학 규명 + SEA 부분검증 (2026-07-03, 사용자 대화로)**: 로봇 CVT = **4절링크(l_i 조절 변속)**, belt 아님. 현 데이터는 **l_i=30mm = 평행사변형 = 전달비 정확히 1:1** (변속 OFF). 4-bar 내부각 40~140°라 사점(0/180)에서 멀어 → **변속비 변화 없음** (내 "config-dependent ratio" 이론 폐기). BUT **측정 q/τ는 모터 엔코더(4-bar 입력단) 기준** → 평행사변형이어도 실제 핀·부재의 **직렬 탄성(series compliance)** 은 실재 → 이게 flex의 진짜 정체 후보. **SEA 검증 부분 성공**: rotor에 real inertia(armature 아님) 주면 soft spring(k=40)에서 **motor dq2 peak 28 ≈ real 27** (rigid는 18) → **series compliance가 terminal spike 재현 확인**. 단 2-body SEA는 base 점프 버그(h~0.19) 남아 full 통합은 미완 (깨끗한 topology/settle 필요). 내 병렬 flex는 이 직렬 compliance의 비물리적 대용(pre-load 에너지 주입)이었음. `code/goal19/phase11/sea_jump_test.py`.

**★★ GOAL12/14/15 vs GOAL19 규명 + 에너지/관성 진단 (2026-07-03)**:
- **a_hat은 이미 적용** (paper_a_hat: 전기변환+포화+마찰, A_HAT 5-param, `goal12/data_loaders/load_combined_15trial.py`). GOAL19 tau_real = a_hat 변환값. → 재fit 불필요. 내 이전 "raw 토크" 주장 오류.
- **에너지로는 토크 충분**: 실측 W_pos 27J > 점프 22J. under-jump ≠ 토크부족. **honest sim은 같은 토크로 14J밖에 못 함** — sim 관절이 느려(dq2 18 vs 27) 일=τ·dq_sim이 절반. 자기강화 악순환.
- **유효관성이 lever**: base질량 1.0→0.3 → h 0.45→0.64, dq2오차 6.6→3.1. 하지만 물리질량으론 0.64까지만(0.89 못감). 마찰은 주범 아님(honest서 D_fric~0).
- **★ GOAL12/14/15가 높이 좋았던 이유 = per-trial 질량 fudge** (trial당 9~12 파라미터, calf 40%/15% 등 비물리 경계). 이게 바로 "유효관성 lever를 trial별로 남용"한 것. **cross-val서 폭발**(GOAL12 held-out dq2 0.47→30, over-jump 10cm) = 과적합, 일반화 X. tau_scale/motor_tm 등 금지축은 아무도 안 씀. **GOAL19 0.73-0.85가 정직·물리·일반화되는 진짜값.** 유일 정당 아이디어(flex)는 GOAL19 이미 채택.
- **★ 최종목적 함의**: 최적화는 새 궤적 생성=일반화 필요 → per-trial fudge(GOAL12/14/15)는 최적화에 쓸 수 없음(held-out 폭발). **GOAL19 통합 물리모델이 올바른 토대.** 높이 낮아보이는 건 fudge 거부의 대가이자 최적화에 필요한 성질.

**★ 광범위 통합 재fit + a_hat 마찰 검증 (2026-07-03)**:
- **(B) a_hat 정상**: raw currentTorque 33Nm → a_hat 19Nm (0.61배, AK80-9 V2 peak 18과 일치 = over-read 올바로 보정). a_hat 마찰항 겨우 1.4Nm(이중계산 미미, 빼도 +0.03). **토크 모델 문제 아님 → 동역학 문제 확정.**
- **(A) 광범위 통합 재fit** (mass/inertia 전체 wide bound, 단일세트, 기하 lock): total 9891→9828(marginal −0.6%), h 0.774→0.789. **calf 0.57(CAD 43%↓), thigh 1.47 로 밀림 = CAD 질량 분포 틀림 확인(사용자 조립오차 가설 부분 맞음)**. BUT **sit2stand만 개선(gnd 684→636), hard jump는 여전히 0.72** → **점프 gap ≠ CAD 질량.** thigh↔calf degenerate + 경계붙음이라 구체값 과신 금지.
- **결론**: 동역학(질량분배) 다소 틀림 확인·sit2stand 개선. 하지만 점프 under-jump은 질량으로 안 닫힘 = takeoff 속도/compliance 잔차(구조적). per-trial 없이 정직한 통합 모델은 점프에서 물리 한계 근처. 남은 gap 억지로 닫으면 최적화 transfer 깨짐.

**★★★ UNDER-JUMP 진짜 원인 확정 (2026-07-04) — 직렬탄성 catapult 누락 (SEA)**: 여러 진단을 거쳐 최종 확정. (경로: 접촉 stiff sweep→강성 lever 아님 반증; 역동역학 잔차 작음 knee 3Nm; 필요접촉력 123N≈GRF 124N.)
- **처음엔 "firmware 높이 artifact"라 잘못 결론냄(정정)**: GRF threshold로 takeoff 잡아 base 속도 2.17만 봄 → h_kine 0.56 → "카메라 0.89는 firmware projection"이라 오판. **★ 사용자 정정: 카메라로 촬영후 제대로 측정한 진짜 값. GRF는 로드셀 비선형+3,4월 calibration 오류로 부정확 → target에서 제외. q/dq/tau/h만 매칭이 목표.**
- **재검증 (올바름)**: push **전체 최대** base 속도로 보면 3 trial 모두 **peak base_vz 3.0~3.3 m/s → ballistic apex 0.92~1.0 ≈ 카메라 0.81~0.98**. **측정 관절 데이터에 0.9~1.0m 점프 에너지가 이미 있음.** base 속도는 mid-push서 3.23 peak 친 뒤 full-ext(특이점)로 가며 감속 → 발이 언제 떨어지냐가 높이 결정(peak서 이륙=0.99, full-ext=0.75).
- **★ sim 진단**: 실제 sim(final model) base_vz peak **2.38**(→0.75)로 측정 3.23 못따라감. sim dq2 종단 18~24 vs 실측 27 = **sim이 knee 속도 종단 spike 미재현**.
- **★★ 원인 = 직렬탄성(SEA) catapult**: 전달계/구조 series compliance가 push중 탄성E 저장→이륙순간 짧게 방출→속도 spike. 순E 더하는게 아니라 특이점이 base속도 뺏기 직전 타이밍 방출(=실제 점프로봇 물리, 잘 알려진 elastic power-amplification). 메모리 SEA 테스트: **rigid dq2=18, SEA 스프링=28≈27 재현 확인**. 단 이전 sea_clean.py는 h 0.46 그침(coupling/topology 셋업 이슈, 미해결) → **clean SEA(motor+spring+link, rotor 실관성) 제대로 지어 dq2 spike 27 AND h 0.89 동시 재현 검증 필요**.
- **결론**: under-jump = 에너지부족X, firmware artifactX, **sim이 SEA catapult 빠뜨려 종단 knee 속도 spike 미재현**. 이게 q/dq/h 동시 닫는 단일 물리축. flex(병렬스프링)가 "도왔던" 건 이 직렬 catapult의 조잡한 대용(pre-load E 주입)이었음. 파일: `invdyn_id.py`.

**★★★ q/dq 미스매치 진단 (2026-07-04) — 방법론+데이터 문제, 가중치 아님**: 사용자 "q/dq 너무 안맞음, 훨씬 발전 필요" 지적 후. per-dataset RMSE: **0602(6월,good cal) q2 0.073(4.2°)/dq2 1.80 = 이미 OK**, 0424(4월) q2 0.134, 0422(4월) q2 0.423, **0421(position-PD) q2 0.423(24°) drift 폭주**. 두 원인: (1) **open-loop 토크 replay가 position 데이터(0421)엔 ill-posed** — PD로 위치추종한 데이터를 피드백 없이 재생하면 drift 발산(q2 start+0.04→end+0.79). dynamics 오차 아니라 방법론 한계. (2) **4월 calibration(사용자 명시) + dq2 종단 spike under**. ★ 핵심: **현 score는 이미 dq 항이 지배(50×2.5≈125 >> q,h)** → 이미 dq 최적화됨 → 벽은 가중치 아닌 방법론+데이터. 6월 데이터가 4.2°로 맞는 게 dynamics 건강함의 증거. **사용자 선택: "torque 데이터 집중 + 재적합"** (position 0421 open-loop 검증서 제외). 실행: `reopt_torque_qdq.py` (torque jumps+gnd만, W_Q 250·W_DQ 60·W_H 60, arm_knee 물리범위 [0.003,0.012], GRF off). WARM total 5524. CMA-ES 260fevals 백그라운드. **★ arm_knee 물리보정(0.0206→~0.005): 높이 0.77→0.82(일부 0.89)+dq2 spike 18→26 동시개선, fudge 아님 — baking 예정.** ★ 미결: closed-loop(PD) 평가는 사용자가 후순위로 보류(실제 제어와 일치하나 Mode A 규칙 완화 필요).

**★★ 목적 재설정 + 진행 (2026-07-04)**: **사용자 명시: GRF는 target에서 제외** (로드셀 비선형 + 3,4월 calibration 오류로 부정확). **q, dq, tau, h만 매칭.** tau는 Mode A에서 입력이라 자동. **카메라 h = 모터 모인 base 중심점 apex = sim base_z와 정확히 동일점** (CoM/marker 아님, apples-to-apples). 사용자 선택: **"GRF 뺀 재적합 먼저"** (SEA는 후순위). 실행: `reopt_nogrf.py` (W_GRF=0, jump+gnd 25 subs, 물리 bound, 기하 lock, arm_knee 물리 rotor관성 0.005까지 탐색 허용). WARM(W_GRF=0) total 7801, h_ratio 0.772. CMA-ES 200fevals 백그라운드 진행중. ★ arm_knee 물리값 재검토: AK80-9 rotor 6.05e-5×gear81≈0.0049인데 현 모델 0.0206(4배 과대) → 낮추면 dq2 18→26 회복+h 0.68→0.74 (물리적 정정). SEA MuJoCo 구현은 near-massless rotor로 3회 실패(h 0.19), 다른 formulation 필요(후순위).

관련: [[jump_C_fixed_params]] [[ak80_9_torque_calibration]] [[real_jump_heights]] [[digital_twin_priority]] [[user_thinking_patterns]] [[ultimate_objective_optimization]]
