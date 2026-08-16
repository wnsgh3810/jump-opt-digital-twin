---
name: goal4-phase1-state
description: GOAL4 Phase 1 (2026-06-06) — JAX direct + V15 robust 부분 재현 + Notion G4V1/V3, 실 robot protocol .md, MJX/Warp infra 완료
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# GOAL4 Phase 1 결과 (2026-06-06)

## 시뮬레이터 인프라

### MuJoCo MJX
- `goal4/urdf/leg_mjx.xml` (V20 inertia 그대로) ✓
- MuJoCo CPU 시뮬 작동 ✓
- MJX GPU 시뮬 step 작동 ✓
- **Reverse-mode autodiff 미지원**: MJX solver 내부 lax.while_loop. iterations=4 static 명시해도 안 됨 → **JAX direct dynamics path로 우회**
- forward-mode jacfwd: 240s timeout (compilation hung)

### NVIDIA Warp
- `goal4/g4v2_warp_test.py` ✓
- Warp 1.13.0 + CUDA 12.9 + RTX 5080 16GB
- Tape autodiff 정상 (∂(−base_z)/∂(base_z_init) = −1.0 sanity)
- ⚠ NVIDIA Newton (2026-03 release) pypi 없음, GitHub source build 필요 → 다음 phase

### JAX Direct (채택 path)
- `goal4/g4v1d_jax_direct.py`: 3-DOF planar Lagrangian + V20 inertia + alpha penalty ground
- ✓ jax.lax.scan rollout (200 step) JIT 0.24s, cached 0.000s
- ✓ Reverse-mode jax.grad ∂(peak_z)/∂(ctrl) 0.32s (200 step × 2 actuator)
- ✓ Adam optimization 30 iter peak_z 변동 (unstable, hyperparam tune 필요)

## V15 robust JAX 재현 — 진행

### G4V3c SUCCESS (peak_z 0.504m)
- W_peak 50× 강화 + W_smooth/W_mag 약화
- 100 iter Adam in 2.6s (RTX 5080) vs CasADi NLP 30s → 10× faster
- τ saturation 17.71 Nm (V21 18 Nm와 일치)
- GRF peak 1042 N (M·g 32.6배)

### G4V4 V21 deterministic replay 완벽
- τ_diff hip = 0.000000 Nm (V21 target 0.0001 — perfect)
- τ_diff knee = 0.000000 Nm (V21 target 0.003 — perfect)
- 5% noise robustness: τ_diff 0.27 Nm, q drift 3-4° (실 robot 합격 기준 통과)

### V15 robust JAX 재현 (G4V3)

### 1차 시도 (g4v3_v15_robust_jax.py): NaN
- 원인: gravity sign 오류, K_ground=5e4 너무 강함, dt=0.002 Euler 부족, lc1/lc2 잘못
- iter 60 발산

### 2차 시도 (g4v3b_v15_fixed.py): Gravity 정확 검증
- **GRF initial = 33.51 N ≈ M_tot·g = 32 N ✓** (V20 inertia + gravity 식 정확)
- **τ smoothness 0.0001 (Δτ rms) — V21 perfect 매칭** ★
- ✗ peak_z = 0.25m unchanged (robot 점프 안 함)
- 원인: mag_w · 9000 = 9 > peak_z 0.5 → mag penalty 압도
- Fix: W_peak 확대 또는 jump h target Lagrangian 다음 시도

### V20 dynamics 정확성 인증
- Gravity: G_q1 = (m1·lc1 + m2·l1) · g · sin(q1) + m2·lc2·g·sin(q1+q2) ✓
- Mass matrix: M11/M12/M22/M23/M33 V21 GOAL3와 일치
- RK4 integration + dt=0.001 → 안정

## Notion 페이지

- Parent: 376ab81d2550816ebc12e4d871d53c9d (GOAL4)
- G4V1: 376ab81d25508129b1a3eb26a9cbb8ea — URDF + MJX + JAX Direct
- G4V3: 376ab81d255081418cb2dcaf16954567 — V15 robust JAX 진단

## 실 robot torque mode protocol (Priority 1)

- `goal4/real_robot_protocol.md`: 6-step protocol
- D-day: 2026-06-07 (실험실 access)
- 5 trial × 3 height × 2 task = 30 trial
- 합격 기준: τ_diff ≤ 0.5 Nm, q RMSE ≤ 5°, GRF RMSE ≤ 30 N

## 미해결 (다음 phase)

1. V15 robust hyperparam re-tune: W_peak ↑, W_mag ↓ 또는 jump h target constraint
2. V20 full 32-param JAX porting (motor lag, friction, CVT, AK80 a_hat)
3. NLP→FF replay 시뮬 (G4V4): GOAL3 V21 τ_diff 0.0001 재현
4. CasADi vs JAX 결과 직접 비교 (G4V5)
5. Newton/IsaacLab GitHub build (G4V6+)
6. 실 robot 실험 D-day

관련: [[goal3_final_stack]], [[next-goal4-mission]]
