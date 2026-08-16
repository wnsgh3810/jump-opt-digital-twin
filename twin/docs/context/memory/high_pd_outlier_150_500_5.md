---
name: high-pd-outlier-150-500-5
description: 26.06.02 jump data의 150_2.2_500_5 폴더가 measurement outlier — 단일 모델 fit 불가
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

26.06.02 position 데이터의 6개 PD 폴더 중 **150_2.2_500_5** (Kp_hip=150, Kd_hip=2.2, Kp_knee=500, Kd_knee=5)는 다른 5 폴더와 다른 effective dynamics를 가짐.

**Why**: v42a 진단:
- max τ1 = 21.8 Nm (다른 폴더 9-19)
- max ddq1 = 1740 rad/s², noise_ddq = 182 (다른 폴더보다 큼)
- v24 모델 적용시 hip 1.31 / knee 1.44 Nm RMSE
- 다른 5 폴더는 unsat 0.2-0.6 Nm로 fit 됨

**Single-fit attempts that failed** (v42b-v47):
- v42b: v32 + foot circle + rotor + quad viscous → MEAN 1.88/0.84
- v42c: v19 + foot + rotor → MEAN 2.41/2.70
- v42f: v19 refit on all 6 → MEAN 2.04/2.46
- v43: per-trial alpha → MEAN 2.16/2.27
- v46: v19 + ddq window 41 smoothed → 5-fold MEAN 1.90/1.36 (still worse)
- v47: per-trial bias offsets → MEAN 2.63/1.96

**Local refine on 150_500_5 alone** (v42j) achieves 0.45/0.30 — 구조는 충분.
But required params: tau_m 80→2.6ms, alpha 0.30→0.60, off1_c 9.5→3.2 (불가능 different regime)

**How to apply**: 
1. v24 model 사용 시 150_500_5는 outlier로 제외해도 됨 (5/6에서 0.5 Nm 목표 달성)
2. 새 데이터 받으면 150_500_5 비슷한 outlier 있는지 확인 (high knee PD ≥ 500이거나 noise_ddq > 150)
3. NLP에는 v41 (T_st=0.27, AK80 back-EMF) 사용; jump h 매칭 0.5%

**Diagnostic features**:
- α-coupling test: corr(ddq1, residual) — high PD에서 -0.7 이상이면 의심
- Lift-off RMSE > 2 Nm → foot circle 영향
- Per-trial bias 발견 시 measurement drift 가능성
