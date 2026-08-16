---
name: goal10_11_findings
description: "GOAL10(+11) — Pure Mode A, tau_scale=1.0 LOCK. Final v4 Iter27 132.84 (9-trial). per-trial fv의 kd-종속성이 dominant"
metadata: 
  node_type: memory
  type: project
  originSessionId: 63705ea5-db81-4f09-83d9-aa9b74dfbbc4
---

GOAL10 (2026-06-15~16, ~13.5h + 연장): GOAL9의 tau_scale를 버리고 **tau_scale_h=tau_scale_k=1.0 LOCK**(Mode A 순수성 복원), 점프높이는 자연 friction/inertia(fc/fv/arm/stiff) narrow 튜닝으로 회복. 같은 26.04.24 9-trial. 31 iter. (문서가 iter26-31/Final v4를 "GOAL11"로 라벨하지만 실제로는 `goal10/` 디렉토리 — goal11 dir 없음.)

**KEEP chain**: Phase 0R(Pure GOAL7 base) **74,609.6** → Final v3 **139.408**(Iter25) → **Final v4 132.839**(Iter27, 공식 final, 99.82%).
- Iter1-3 solref+ConfigD+mass(~91.7%), Iter13 6p DE(263.27), Iter14 8p DE(253.92), Iter21 CMA-ES 8p(231.23), Iter24 per-trial fv_knee Brent(+27.67% 최대단일), Iter25 per-trial fv_hip(139.41), **Iter27 per-trial fv_hip+fv_knee 2D joint TPE(132.84, +4.71%)**

**★ per-trial fv의 kd-종속성이 dominant lever**: low-kd(0.75~2)→high fv, high-kd(2.5~4)→low fv (hip/knee 공통). 2D joint refit > sequential 1D by 4.71%. Mass refit critical(M_base +19.2%, m2 +284.5%). **motor_tm 3회 전부 reject**(iter12/15/29, Mode A에서 h_sim 붕괴). flex/tau_delay/foot-shape/bias/CAD-I 전부 DROP.

Final v4 params: fc_hip=0.9339, fc_knee=0.02132, arm_hip=0.00186, arm_knee=0.00490, stiff_hip=0.08012, stiff_knee=1.16157; **per-trial fv_hip 0.025~0.599, fv_knee 0.005~0.177**. avg|dh|=7.74cm, pen 0. 90_0.75_90_2가 persistent 최대갭(|dh|=11.17cm). XML `goal10/iter27_per_trial_fv2d/leg_g10_i27_best.xml`. 26.06.02 6-trial CV: score 484.97, **B- 등급**(5/6 ok, 150_2.2_500_5 GRF 1701N spike). Notion Final v4 `381ab81d-2550-8175-afe5-c2e6c568ce67`.

Score scale: 9-trial 합, W_grf=1. **tau_scale=1.0 LOCK이 GOAL9(848.85)와의 결정적 차이.**

**Why:** tau_scale fudge 없이 per-trial 자연마찰만으로 132.84 달성 = Mode A 순수 디지털트윈의 첫 성공.
**How to apply:** per-trial fv는 kd에 종속(반비례)으로 설정. tau_scale=1.0 절대 LOCK. [[mode_A_purpose]] [[goal9_findings]] [[feedback_pure_paper_formula]]
