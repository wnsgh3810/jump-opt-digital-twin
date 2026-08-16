---
name: goal6-findings
description: "GOAL6 (full match no sat) Stage 1+2 결과. tau_real이 ±18 sat 안 함, 폴더 PD는 firmware PD (실 mechanical PD α_kp=0.19), motor LPF 33ms."
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

## GOAL6 결과 (2026-06-07)

### 핵심 발견 (검증됨)
1. **tau_real ±18 sat 가설 폐기** — 실 측정 tau2_real 범위 -18.71 ~ +20.22 (sat 안 됨)
2. **tau_des ≠ tau_real** — tau_des는 모든 trial 동일 [-14.76, +0.03]/[0, 15] (feedforward command), tau_real은 trial별 다름 (motor 실제 출력)
3. **폴더 이름 PD ≠ 실 mechanical PD** — Stage 2 BO 결과 α_kp=0.19 (폴더 PD의 19%만 효과), α_kd=1.14, α_ff=0.21, motor LPF tm=33ms

### Stage 1 — Dynamics Fit (Mode A: tau_real ctrl 직접 입력)
- BO 300 trials, 16 dim, best score 101.38
- Best params: M_base=1.41, M_thigh=0.53, M_calf=0.39 (M_total=2.33kg, V25 baseline 3.27보다 작음)
- thigh_com=-0.065, calf_com=-0.092
- joint damping hip 0.20 knee 0.05, foot_fric 1.31
- 6 trial RMSE 평균: q1=0.043, q2=0.067, GRF=24.2

### Stage 2 — Motor Model Fit (Stage 1 dynamics 고정)
- BO 200 trials, 4 dim, best score 222.80
- 수식: `tau_cmd = α_kp·kp·err + α_kd·kd·err_dot + α_ff·tau_des`, 후 motor LPF (tm)
- Best: α_kp=0.192, α_kd=1.138, α_ff=0.214, tm=33ms
- 6 trial tau RMSE: τ1 평균 1.59, τ2 평균 2.99 Nm (V25 5-7보다 개선)

### Notion
- Parent: https://app.notion.com/p/GOAL6-Full-Match-no-sat-fit-PD-dynamics-377ab81d2550818daee1ddea3ff9d64e
- Stage 1: https://app.notion.com/p/Stage-1-Dynamics-Fit-Mode-A-377ab81d2550812aa306ff43557274b1
- Stage 2: https://app.notion.com/p/Stage-2-Motor-Model-Fit-377ab81d255081b19d92dcb66abcbd90

### XML
- Stage 1 best: `Desktop/jump_opt/goal6/urdf/leg_g6s1_best.xml`
- Code: `goal6/stage1_bo.py`, `stage2_bo.py`, `stage1_plots_and_notion.py`, `stage2_plots_and_notion.py`

### 향후 (Stage 3 선택)
- Stage 1 + 2 통합 BO (dynamics + motor 동시)
- Per-trial PD scaling (현재 unified, 각 trial별 다른 α_kp 시도)
- AK80-9 a_hat 5-param 모델 직접 적용 (현재 단순 LPF + scaling)

관련 메모리: [[mujoco_range_bug]], [[ak80_9_torque_calibration]], [[sysid_findings]]
