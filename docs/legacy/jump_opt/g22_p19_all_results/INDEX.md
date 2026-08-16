# g22_p19_all_results — P19 현행 스택 전 데이터 결과 (2026-07-13)

**모델**: P19 승격 스택 (`code/goal22/p19_jump/fourbar_p19_candidate.json`, 2026-07-12 승격)
= 플랜트 x32 (스프링 0.9@calf, 프리로드 l_i=30 전용 2.25Nm 등) × 커맨드층 (실효게인 α + raw 클립 ±35.5 + 지연 tm 0.31ms) × 변환식 A=Paper.
생성 코드: `code/goal22/p19_jump/p19_all_results.py`, `s2s_0604_p19.py`.

## 폴더 구조 (세션별 차일드)

각 폴더에 `png/`(그래프) · `gif/`(시뮬레이션 렌더, goal18_CANONICAL 규격+표준 오버레이) · `traj/`(npz 원시 궤적).
파일명 `<트라이얼>__<모드>.{png,gif,npz}` — 모드 **CL**=폐루프 PD(커맨드층 반영, 배포 관점) / **A**=실측 τ replay(트윈 관점).
그래프는 **png_v2 표준 규격** (`bench/render_kit.fig_trial_std` = cvt_results_v2 출처): 2×3
[q(deg)+q_des | dq1 hip | dq2 crank / hip τ | knee(crank) τ | GRF], 제목에 q2 RMSE·dq2·h_sim/h_real (metrics2 기준).

| 폴더 | trial 수 | CL τ-갭 | q2 RMSE | 비고 |
|---|---|---|---|---|
| `jump_0324_heldout/` | 3 | **35.7%** | 0.206 | **held-out** (fit 미포함, FF 토크 세션) |
| `jump_position_0421/` | 6 | 34.1% | 0.044 | 위치제어 세션 |
| `jump_0424/` | 9 | 34.9% | 0.051 | dq_des 인가 |
| `jump_0602/` | 6 | 35.6% | 0.029 | dq_des 인가 |
| `jump_0429_cvt/` | 10 | 44.8% | 0.096 | **CVT l_i=25.08mm**, α=[1.18,0.37,1.58,0.93] |
| `s2s_gnd_0319/` | 3 | — | — | Mode A만 (mshoot 창 리셋 replay) — P19는 점프 전용 fit, 참고용 |
| `s2s_0604_payload/` | 4×2 | — | — | 페이로드 s2s (cvt 0/2.5/5kg + no_cvt 0kg), 게인=P18c 회귀 실효게인, dq_des 인가 |

FIT 평균 38.1% / held-out 35.7% (재구성 바닥 26~28%, CURRENT_STACK.md 참조).

## 읽는 법 (함정)

- 그래프의 "real tau (a_hat)"은 raw iTM을 Paper a_hat으로 변환한 축토크. knee 채널은 **크랭크(모터)측**.
- s2s_gnd_0319의 knee τ에서 sim이 실측보다 ~2.25Nm 위 = l_i=30 클러치 프리로드 (플랜트측 인가분 포함 표시).
- CL은 커맨드층(α·클립·tm)이 반영된 시뮬 — 라벨 게인 그대로 돌린 것이 아님.
- 0429 q 비교는 심판 관례대로 q-오프셋(o1,o2) 제거 후 표시.
- s2s_gnd_0319는 0.2s multiple-shooting 창마다 실측 상태로 리셋하는 replay (심판 동일 프로토콜) — GRF의 주기적 스파이크는 리셋 과도.
- s2s_0604의 τ-갭 수치(그림 제목)는 s2s가 P19 fit 도메인 밖임을 보여주는 정직한 수치 (점프 지표와 비교 불가).
- GIF 오버레이: trial/t/base_z/hip/knee/h_sim/h_real/l_i (render_kit 표준).
