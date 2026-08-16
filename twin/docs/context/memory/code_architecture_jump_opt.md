---
name: code_architecture_jump_opt
description: "jump_opt 코드 아키텍처 — pipeline, score 함수, 12 per-trial params, simulator 설정, orchestration, a_hat 모델"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

`C:\Users\junho\CVT\jump_opt\` 디지털트윈 최적화 코드 구조 (GOAL9~16).

**A. Pipeline**: real data → a_hat τ 변환 → XML build → MuJoCo rollout(Mode A) → score vs real → optimizer loop → metrics.json → plots/anim/Notion/git.
- Data+a_hat: `goal12/data_loaders/load_combined_15trial.py` (hip/knee/GRF xlsx, `currentTorque`→`paper_a_hat`, h_real from Real Data.txt, 15 trial = 9×0424 + 6×0602, cache `goal12/data_loaded_combined.npz`)
- XML 상수/CAD inertia: `goal12/iter3/build_xml_i3.py`
- rollout+score+optimizer: per-iter `goal16/iterN/run_iN.py`(build_xml, run_trial_sim, trial_score, optimizer 인라인)
- viewer(시각화 전용): `leg_simulator.py`(4-bar CVT kinematics calc_q2/calc_TR, L1=L2=0.25)

**B. Score 함수** (W_Q=100, W_DQ=3, W_T=20, W_H=50, **W_GRF=0.2**(goal16; goal12=1.0, goal14=0.3), W_PEN=10; GRF_BAND=0.25, PEN_BAND_MM=2.0):
```
s = W_Q*(rmse_q1+rmse_q2) + W_DQ*(rmse_dq1+rmse_dq2) + W_T*(rmse_t1+rmse_t2)
    + W_H*|h_sim-h_real| + W_GRF*max(0,grf_dev-0.25)² + W_PEN*max(0,pen_mm-2)²
```
- 부호변환 v20: q1=-q[:,1]-π/2, q2=-q[:,2], tau=-tau_cmd. h_sim=max(base_z). grf_dev=|grf_pk_sim-grf_pk_real|/grf_pk_real. **total = trial 합**(mean 아님; 고전류 0424 trial이 dominant). 실패 sim=1e6.
- **KEEP**: total < KEEP_THRESH (고정). **BV(boundary violation)**: param이 box edge 20% 이내면 flag(`v<lb+0.2·rng or v>ub-0.2·rng`), total_bv 합. guardrail = KEEP은 −3% AND BV<8(goal16).

**C. 12 per-trial params (ALL_PARAM_KEYS 순서, LB/UB)**: m_base(0.5/2.5), fv_hip(0.001/6), fc_hip(0.01/10), solref_tc(0.001/0.05), imp0(0.01/0.8), fv_knee(0.0001/3), fc_knee(0.001/3), m_thigh_scale(0.3/2), m_calf_scale(0.3/2), arm_knee(0.0001/0.05), stiff_hip(0.001/3), stiff_knee(0.001/3). `ci_scaled()`가 thigh/calf scale로 복합체 mass/COM/inertia 재계산. ARM_HIP_FIXED=0.0.

**D. Simulator 설정** (`build_xml_i3.py`): DT=0.0005(2kHz), INTEGRATOR=RK4, CONE=elliptic, IMPRATIO=100. Foot cylinder(radius0.021, half_len0.0065, condim6, priority1, friction"1.0 0.02 0.01", margin0.001, euler 90° 라인접촉). solref="{tc} 1.6072", solimp="{imp0} 0.72007 0.005409 0.5 2". 3 DOF(base_z slide, hip hinge, knee hinge). **Mode A τ 주입**: 0.4s PD settle(Kp500/Kd10) → motion window에 측정 τ를 `np.interp`로 actuator ctrl 직접 주입(tau_h=-tau1_real, tau_k=-tau2_real) → 0.5s release(ctrl=0). motor actuator gear=1.

**E. Orchestration**: `goal15/master_orchestrator.py`(고정 phase list, ITER_SCRIPTS dict, subprocess + metrics.json 폴링 60-120s + plots/anim/notion/MD + git_commit, DEADLINE 자동중지) + `goal15/auto_monitor.py`(경량 watcher). cron wakeup이 재진입해 폴링 재개(metrics.json 존재 = idempotent checkpoint).

**F. a_hat (Pure Paper sgn(v))**: KT=0.091, GR=9.0, CF=0.59, A_HAT=[0, 1.15605, 4.1739e-4, 0.26856, 0.04904]:
```
Iq = (CF/(GR*KT))*tau_reported
a_hat = A_HAT[1]*GR*KT*Iq - A_HAT[2]*GR*|Iq|*Iq - A_HAT[3]*sign(v) - A_HAT[4]*|Iq|*sign(v)
```
GitHub s(v) smoothing 금지(2026-05-20 결정). 최신 NLP: `dynamics_v11.py`(V5+saturation+hip cross-coupling 32p), fit: `fit_v25_ahat_refit.py`.

[[ak80_9_torque_calibration]] [[feedback_pure_paper_formula]] [[ak80_9_V2_spec]] [[goal16_findings]] [[code_files_index]]
