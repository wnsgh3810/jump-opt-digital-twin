---
name: Desktop Code Files Index
description: Desktop에 있는/있었던 .py 파일들의 용도와 상태 색인 (active/superseded/abandoned)
type: reference
originSessionId: c82aa01d-1bc5-42d3-ad69-d2998821e712
---
# 옛 `C:\Users\junho\Desktop\` 시절 Python 파일 색인 (과거 기록)

> 2026-08-16 이사 안내: 아래 경로들은 **그 당시의 자리**다. 살아남은 파일들은 지금
> `C:\Users\junho\CVT\AVT LEG\` 아래로 옮겨져 있다 (`optimization\`, `sweep\`, `sys_id\`, `utils\`).
> 파일 이름으로 찾는 것이 확실하다.

10일 세션 동안 80+ 개 파일이 생성/수정됨. 4/24 오후 사용자 지시로 중간 sweep 파일들 대량 삭제됨. 현재 active 파일과 history를 함께 정리.

---

## Active (현재 사용 중)

### 메인 코드
- `final.py` — 메인 궤적 최적화 (CasADi IPOPT, soft_alpha contact, 입력 토크 sat, z_kin 제약, 마찰 포함) | 활성, 4/19 alpha=0.90/kc=5000/bc=50/rf=5/jf=0.3/tau_lim=15 반영, 4/22 grf_z_spring/grf_z_body/tau_input 마지막 행 보정 추가
- `pd_sim.py` — PD 시뮬레이션 (RK4, soft contact, MIT mode v_des=0, 모터 lag) | 활성, 4/24 169M sweep 결과 반영 (Is1=0.065 Is2=0.005 Kv=0.011 gAv=0.30 gBv=0.50 alpha=0.85 kc=7000 bc=80 Kp=300 Kd_h=3.0 Kd_k=8.0 cf=0.40 jf=0.080 tau_lim=30 tau_motor=10ms)
- `pd_sim_tl30.py` — pd_sim의 6개 실험(P60-P200) 검증 + hip/knee 위치/속도/토크/GRF 그래프 생성 | 활성, last-active 4/24
- `pd_sim_validate.py` — 6개 실험 통합 비교 검증 (텍스트 표) | 활성, 4/24
- `sweep.py` — 최적화 파라미터 sweep tool (final.py 기반) | 활성
- `sys_id.py` — sit2stand 데이터로 2DOF dynamics System ID (비선형 마찰 모델 포함) | 활성, 4/23 마지막 수정
- `Identify_Contact_Params.py` — 4-parameter 선형 회귀로 soft contact (k_c, b_c) 식별 | 활성 (이전 클로드 작성)
- `2DOF Leg Jumping Optimization.py` — 원본 최적화 코드 (이전 클로드 작성, hard contact 9Nm 버전) | 참고용

### System ID 진행 중 파일 (4/25)
- `sys_id_jump.py` — Jumping 데이터로 직접 ID v1 (17 params, hip R²=-0.70 실패) | 진행 중
- `sys_id_jump2.py` — v2 (Av/Bv CAD 고정, R²=0.87이지만 gAv=-31 비물리적) | 진행 중
- `sys_id_jump3.py` — v3 (5 params, friction 고정, Is1=-0.04 음수) | 진행 중
- `sys_id_jump4.py` — v4 (soft contact ddz, Av=0.131 CAD와 일치, hip R²=-0.17) | 진행 중
- `sys_id_sanity.py` — Forward sim 합성 데이터로 regressor 식 검증 (TRUE ddz 100% 정확) | 진행 중
- `sys_id_jump_multi.py` — Multi-trial (P60-P200) 결합 ID (friction 고정, **gAv=1.57≈CAD 1.36 발견**) | 핵심 결과 파일
- `sys_id_jump_full.py` — Multi-trial + free friction (overfitting) | 진행 중

### 진행 중 sweep 파일 (4/25 세션 끝 시점)
- `pd_sweep_mp_a1.py` — ALPHA=1.0 고정 + gAv 0.8~1.9 (CAD 중심) sweep, 58M configs | 4/25 오후 백그라운드 실행 중
- `pd_sweep_mp.py` — 169M configs, numba JIT, 14 cores, imap_unordered + heap top-K | 4/24 완료, 결과 pd_sim.py 반영됨

### 분석 코드 (참고용)
- `exp_analysis.py` — 9개 실험(26.04.21-22) Impulse/Energy/추적/지연 종합 분석 | 4/22
- `deep_analysis.py` / `deep_analysis2.py` — 다양한 시간 구간(11개 + 슬라이딩) RMS/적분 심층 분석 + 그래프 5장 생성 | 4/22
- `gap_reduction_analysis.py` — Sim-to-Real Gap 원인 다각도 분석 | 4/22
- `profile_analysis.py` — 토크 프로파일 형태 + GRF deficit 원인 (Q4 분할) | 4/22

### 이전 코드 (참고용)
- `혹시2.py` — 이전 클로드의 alpha 모델 추가 버전 | 4/17 alpha 곱하기 수정
- `혹시.py` — 더 이전 버전

---

## Superseded / Deleted (4/24 사용자 지시로 삭제됨)

### 중간 PD sweep 시도들 (모두 pd_sweep_mp.py로 대체)
- `pd_param_fit.py` (300 cfg, 4/22) — 1차, tau_lim=15 saturation 발견 | superseded
- `pd_param_fit2.py` (2400, 4/23) — tau_lim 확장 | superseded
- `pd_param_fit3.py` (3600, 4/23) — tau profile shape 추가 | superseded
- `pd_param_fit4.py` — back-EMF 모델 (사용자가 reject) | abandoned
- `pd_param_fit5.py` — 비율 기반 scoring | superseded
- `pd_param_fit_fine.py` (35K) — sim 시간 연장 발견 | superseded
- `pd_param_fit_fine2.py` (36K) — kpk 임계값 탐색 | superseded
- `pd_param_fit_traj.py` / `pd_param_fit_traj2.py` — 궤적 매칭 도입 (q2 RMSE 0.57°) | superseded by pd_sweep_mp.py
- `pd_refit.py` (5400) — sys ID 적용 후 첫 refit | superseded
- `pd_refit2.py` (10.8K) — 모터 지연 추가 | superseded
- `pd_refit3.py` (14.4K) — fine sweep | superseded
- `pd_refit_full.py` (16.2K) — gAv/gBv도 sweep | superseded
- `pd_refit_final.py` (86.4K) — v_des=0 적용 | superseded
- `pd_refit_alpha.py` (136K) — alpha 0.5-1.0 sweep, alpha=0.5가 1위 | superseded
- `pd_refit_imp.py` (1.9M) — RK4 alpha bug 수정 + alpha 0.5-1.0/kc 3000-7000/bc 30-80 | superseded by 169M

### 중간 friction sweep
- `friction_sweep.py` / `friction_sweep2.py` (320 cfg) | superseded by friction_sweep3
- `friction_sweep3.py` (945 cfg → 3600) — α=0.90/kc=5000/bc=50 best | results in final.py, file deleted

### 초기 분석 코드 (대부분 결과만 반영되고 코드는 deleted)
- `gap_analysis.py` (4/18) — Knee 토크 포화 60% 발견 | findings in analysis_findings.md
- `gap_physics_analysis.py` (4/18) — alpha=0.712 검증 (P40 0.1% 오차) | findings reflected
- `liftoff_analysis.py` / `liftoff_analysis2.py` (4/18) — 확장 데이터로 v_spring=2.0 m/s 발견 | findings reflected
- `dynamics_decomp.py` (4/18) — ddz_kin 노이즈 한계 확인 | findings reflected
- `rigorous_analysis.py` (4/18) | superseded
- `Identify_Contact_Params_SharedFit.py` — 사용자 작성, 3 trial 공유 fitting (R² 0.823/0.842/0.667 — 원본보다 못함) | abandoned
- `identify_and_compare.py` (4/18) — E/(Imp)² ≈ 1.0 확인 | findings reflected
- `forward_sim.py` (4/18) — 실측 궤적 forward sim, R² 낮음 | findings reflected
- `torque_velocity_analysis.py` (4/18) — Knee W_grf gap 발견 | findings reflected
- `run_compare.py` (4/18) — hard/alpha 6 config 비교 | superseded
- `param_sweep.py` ~ `param_sweep4.py` (15 → 32 → 비대칭+마찰) | superseded
- `notion_sysid.py` (4/23) — Notion 페이지 생성 | run-once

### Notion 관련
- `create_notion_page.py` (4/18) — Identify_Contact_Params 분석 노션 생성 | run-once
- `create_gap_notion.py` (4/22) — Gap reduction 분석 노션 생성 | run-once
- `Identify_Contact_Params_Analysis.md` — 노션용 markdown | preserved

### 결과 텍스트 파일 (모두 4/24 삭제됨)
- `pd_fit_results.txt`, `pd_fit_results2-5.txt`, `pd_fit_fine_results.txt` 등
- `pd_refit*_results.txt` (모든 refit 결과)
- `friction_sweep3_results.txt` / `friction_sweep3_out.txt`
- `pd_sweep_mp_results.txt` (169M 결과, 그 후 새로 생성됨)
- `pd_refit_clean.txt`

### 그래프 파일 (모두 4/24 삭제됨, 그 후 일부 재생성)
- `liftoff_detail.png`, `liftoff_summary.png`, `pd_sim_result.png`, `pd_sim_P60_tl30.png` ~ `pd_sim_P200_tl30.png`, `gap_*.png`, `exp_*.png`

---

## 파일 명명 패턴 (시간순 진화)

```
gap_*.py              (4/18 초반)
liftoff_*.py          (4/18 확장 데이터)
param_sweep*.py       (4/18-19 최적화 sweep)
friction_sweep*.py    (4/19 마찰 추가)
exp/deep_analysis*.py (4/22 신규 실험 분석)
profile_analysis.py   (4/22 토크 프로파일)
pd_sim.py             (4/22 PD 시뮬레이터 시작)
pd_param_fit*.py      (4/22-23 PD 게인 피팅)
pd_param_fit_traj*.py (4/23 궤적 매칭 전환)
sys_id*.py            (4/23 sit2stand ID)
pd_refit*.py          (4/23 sys ID 적용 후 refit)
pd_refit_final/alpha/imp.py (4/23-24 alpha sweep)
pd_sweep_mp*.py       (4/24 169M numba+MP sweep)
sys_id_jump*.py       (4/25 jumping data ID)
sys_id_sanity.py      (4/25 ID 검증)
sys_id_jump_multi/full.py (4/25 multi-trial)
pd_sweep_mp_a1.py     (4/25 ALPHA=1.0 재sweep)
```
