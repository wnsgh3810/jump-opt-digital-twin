---
name: goal19_control_architecture
description: "★★★ 실 robot 제어 아키텍처 2종 + AK80-9 MIT 제어법 + closed-loop Mode A 돌파구. q/dq 미스매치의 진짜 해법"
metadata:
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

**★★★ 실 robot 제어 아키텍처 (사용자 명시 2026-07-05, 정정판 2026-07-05 — 반드시 기억)**:
- **03.19, 03.24, 04.21**: AK80-9 **내부 MIT PD** 사용, 단 **dq_des=0** — ★ 원인 확정 (사용자 2026-07-06): **코드 버그로 최적화 결과 dq_des를 전송 못하고 0을 전송**. xlsx의 desiredAngleVelocity 컬럼은 계획값(≠전송값)이므로 로그만 보고 판단 금지. kd항이 순수 제동(−kd·dq)으로 작동 → 신전 구간에서 다리를 붙잡아 계획-실제 궤적 괴리의 원인. **s2s(03.19 gnd/air)도 동일하게 v_des=0** (사용자 재확인 07-06). **04.24부터 정상 전송 (사용자 확인 07-06)**. ★ **t_ff는 한 번도 실사용된 적 없음 (사용자 확정 07-06)**: xlsx desiredTorque 컬럼(nonzero 87-91%, 9/15Nm 클립)은 참고용으로 로깅만 한 계획값이고, 실제 지령은 q_des+dq_des뿐 = **과거 측정 τ는 100% PD 출력**. 함의: ① 배포(τ_ff 포함)는 하드웨어에서 **최초 사용 경로 → dq_des 버그 전례처럼 사전 전송 검증 필수** (kp=kd=0 + 작은 상수 t_ff로 토크 응답 확인), ② 모델 관점에선 문제 없음 — 트윈은 총 측정 τ로 fit됐고 액추에이터는 지령 출처를 구분 안 함. — 즉 0424/0602 데이터와 현행 코드베이스는 dq_des 정상. 배포 체크리스트의 dq_des 실전송 검증은 "빠른 확인" 성격 (버그 재발 시 kd 항이 제동으로 뒤집히므로 확인 자체는 유지).
- ★ **날짜별 지령 궤적이 다름** (2026-07-06 확인, xlsx desiredAngle): 날짜 내 전 trial 동일 reference(폴더명=게인), 날짜 간 상이 — q2_des 최종신전 0324 −49°/0421·0424 −36°/0602 −45°, stance 0.32/0.27/0.27/0.25s. 실측은 지령을 초과/미달 (0324: −48 지령→−24 실측 23° overshoot ballistic; 0602 soft: −45→−57 미달=중간영역 체류=최정확). **날짜별 replay 정확도 차이의 최종 인과: 지령 차이×게인 → 상태공간 영역 차이(깊은 신전=오차 증폭기) × 세션 측정 품질(4월) — G20 07-06 진단 참조.**
- **★ 04.22만 유일하게 외부 프로그램 루프**: 외부에서 PD 계산 → 토크를 AK에 전송 (torque mode). rate/지연 문제 → 이후 폐기.
- **04.24, 06.02**: AK 내부 MIT PD, **q_des+dq_des 동시** 전송 ("그 문제 해결"판).
- (내 최초 기록 "03.19~04.22 전부 외부루프"는 오독 — 사용자 정정: "외부 루프인 거는 04.22뿐, 나머지는 전부 AK 모터 드라이버의 PD, 속도를 0으로 줬냐 dq_des를 같이 줬냐 차이뿐". **이 정정이 데이터 증거와 정확히 일치**: 유일한 외부루프 0422만 토크-운동 불일치(R²0.33), 내부PD인 0421/0324는 창 오차 건강.)
- **AK80-9 MIT 제어법**: **τ = kp·(q_des − q) + kd·(dq_des − dq) + t_ff** (내부 firmware). 매뉴얼 `D:\Out of Research\Manual\ak80-9 manual.pdf` MIT Power Mode, `pack_cmd(p_des,v_des,kp,kd,t_ff)`, P±95.5rad, V±30, **kp 0-500, kd 0-5, T±18**.
- **★ 폴더명 = MIT gain**: `90_0.75_90_2` = kp_hip 90, kd_hip 0.75, kp_knee 90, kd_knee 2. `120_2.2_150_2.5` = 120/2.2/150/2.5. `150_2.2_500_5` = 500,5는 max gain.
- **원시 CSV엔 desired 위치 없음** (torque/GRF만: hipDesiredTorque=t_ff?/hipCurrentTorque=측정). q_des/dq_des 미로깅.

**★★★ Mode A fitting 함의**:
- **측정 τ_real은 CLOSED-LOOP PD 출력**. open-loop 재생(Mode A)은 안정화 피드백을 버려 drift. **데이터셋별 차이 설명**: 내부 MIT 루프(빠름·tight)=0602 잘맞음, 외부 루프(지연)=0421 drift 폭주.
- **closed-loop replay 실험**: τ_twin = τ_real + kp·(q_real−q_sim)+kd·(dq_real−dq_sim), 폴더 gain → q2 9°→2°. **★★ 그러나 사용자 정정(2026-07-05, 옳음): 이건 모델 개선이 아님.** kp·e = 90×0.038 ≈ 3.4Nm = invdyn 잔차 3.15Nm와 동일 — **같은 오차가 q채널→correction채널로 이동해 안 보이게 된 것.** PD가 모델오차 흡수 + gain 불확실(GOAL6 α_kp=0.19 기록: 폴더PD≠실효PD) + PD목발 fit→NLP τ* 오염. **closed-loop은 FITTING 금지. 용도는 배포 리포트 전용**(fit된 모델의 correction 크기 = 실 로봇 τ_applied−τ* gap 예측).
- **SEA under PD**: rotor 토크 직접 입력 freeze는 PD 구동시 사라짐(calf whip 26≈27, h 튜닝가능). 단 PD 가림막 하의 결과라 모델 검증은 아님 — SEA는 multiple-shooting 틀에서 가설로 심판.
- **★★★ 재정립된 방향 (2026-07-05)**: **Mode A 원칙 유지**(순수 토크, 무피드백 — 사용자 결정 옳음). 결함은 원칙이 아니라 **metric**: 전체궤적 open-loop replay는 발산 오염(누적발산이 점수 지배→비물리 흡수재로 도망→fudge 패턴 근원, 0421/0422 정보 죽음). **해법 = multiple shooting**: ~0.2s 창 분할, 창 시작=측정상태 리셋, 창 내 순수 τ_real replay, 창끝 오차로 fit. 피드백/gain 0, 발산 오염 0, 0421/0422 부활, NLP 제약(단구간 예측)과 정합. + 보조: invdyn clean_residual. + 검증(held-out): 전체궤적 replay+카메라h+LODO.
- **★★ 데이터셋 확정 (사용자 2026-07-05)**: **0422 제외**(외부 PD 루프 + 회귀 R²0.33 inconsistent). **fit = 0421(6) + 0424(9) + 0602(6) 점프 전부 + sit2stand_gnd**. sit2stand air 제외 유지.
- **★★ mshoot baseline (final model, `mshoot.py`)**: total 23438. **0421 창 평균 q2=0.047(2.7°) — full-replay 0.423(24°) 대비 → drift는 순수 누적, 0421 데이터 건강, fitting 부활 확정.** 0424 q2 0.063/dq2 1.98(최약), 0602 0.043/1.51, s2s 0.086/0.76. 창: jump 0.10s/stride 0.05(takeoff 관통 허용=whip 포함), s2s 0.25/0.15, FK base 캐시(기하 LOCK이라 param 무관). `mshoot_refit.py` 22-param CMA-ES 진행.
- **★★★ mshoot refit v1~v3 결과 (2026-07-05, 대성공)**: v1(−42%: 23438→13543) — **비물리 흡수재 자발 이완**: stiff_knee 2.5rail→0.78, m_foot→0, fc_knee 1.17→0.27, CoM railing 해소. **held-out h_ratio 0.77→0.79-0.99 (h는 목적함수에 없었음 = 독립 검증).** v2: 3월 데이터 추가(0324 3trial 깨끗, 0319 NO_TR_JUMP 이상치). **0319 제외 확정(사용자)**: fit이 점수 16% 쏟고도 q2 0.334→0.325 무변 = 데이터 불량 확정(자세 상이, h 파싱불가). v3(최종): **arm_knee 0.0031rail→0.0054 ≈ AK80-9 물리값(0.0049) 자발 정착.** 창 오차 전 데이터셋 q2 1.5-2.2°/dq2 0.9-1.2 균일. **held-out h_ratio: 0324 0.941, 0602 0.913, 0424 0.840** (원래 0.73-0.77). 최종 fit set = **0324(3)+0421(6)+0424(9)+0602(6)=24 jumps + s2s_gnd** (제외: 0422 외부PD불량, 0319 데이터불량 — 각각 증거 기반). ★ 남은 boundary cluster = **thigh쪽 그룹**(M_calf 0.458@LB, com_dz_th −0.09@LB, com_dx_th −0.05@LB, M_p 1.43 near UB) = 4절링크 질량 lumping — 사용자 CAD 조립오차 가설과 일치, 남은 물리 조사 대상. 파일: `mshoot_refit_best_v3.json`.

- **★★★ v4 + SEA 최종 심판 (2026-07-05)**: v4(thigh/4-bar bound 확대) — CoM/M_p는 내부 정착(4-bar lumping 부분 식별=사용자 조립오차 가설 부분 확인)했으나 **calf 그룹이 "질량30%+회전관성180%" 불가능 조합으로 chasing 지속** = 구조적 신호. 질량 축 소진, v3 canonical 유지. **SEA 3단 심판**: ① in-chain rotor 토폴로지 = 창에서도 모터 stall (RK4 dt=1e-4 재현→적분기 아님; k=1e6 폭주→**무관성 DOF가 하중 사슬 내부에 있을 때 mass matrix ill-conditioning** — 역대 SEA 실패 전부의 원인 규명). ② **tendon 결합 SEA**(표준 관용구: thigh 플라이휠 rotor + 진짜 knee joint + fixed tendon stiffness) = 수치 건강, k~2000 최소 존재하나 **전 k에서 rigid v3보다 +43.5% 나쁨**. ③ 대조군 rigid stiff=0 = +38.8% → **SEA 최적이 stiff-뺀-rigid보다도 나쁨 = series compliance 기여 0**. **결론: 무릎 compliance 신호는 PARALLEL(v3 stiff_knee=1.08)이 맞고 series 아님. SEA 기각, v3 최종.** 남은 한계(정직): dq2 종단 whip 일부 + h 0.84-0.94 gap은 rigid+parallel 모델의 잔여 한계로 문서화. 파일: `mshoot_sea.py`(tendon idiom 포함), `mshoot_refit_best.json`(=v3).

관련: [[goal19_qdq_error_sources]] [[goal19_underjump_diagnosis]] [[ultimate_objective_optimization]] [[ak80_9_torque_calibration]] [[mode_A_purpose]]
