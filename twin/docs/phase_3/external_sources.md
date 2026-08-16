# Phase 3 — External Sources (contact compliance)

## 1. solref timeconst → contact stiffness/softness

**Source**: [solref/solimp Parameter Cheat Sheet (ROBOLAWEB)](https://robolaweb.gitbook.io/robolaweb-docs/basic-concept/solref-solimp-parameter-cheat-sheet) + [MuJoCo XML Reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html)

**Citation**: The `timeconst` parameter in `solref` controls the rise time of contact constraint forces — larger values produce slower, softer contact responses. `solimp[0]` (imp0) sets the impedance floor.

**Application**: Our `solref_tc` = solref timeconst, `imp0` = solimp[0]. 2D axis directly controls foot-floor compliance.

## 2. Contact compliance ↔ jump push-off (⚠️ bidirectional)

**Source**: [Whole-Body MPC of Legged Robots with MuJoCo (arXiv 2503.04613)](https://arxiv.org/pdf/2503.04613) + [Achieving Stable and Elastic Jumps in MuJoCo (Discussion #2347)](https://github.com/google-deepmind/mujoco/discussions/2347)

**Citation**: A quadruped's gait relies on brief, stiff ground contacts to deliver sharp propulsive impulses; increased compliance reduces the effective push-off force per step and degrades dynamic tasks like jumping. **Conversely**, some solref values (e.g. [4e-2, 1]) produce energy that decreases then increases after floor contact (elastic return).

**Application (nuance)**: Contact compliance can go **either way** on jumps — softer may dissipate push-off OR return elastic energy depending on timing vs the torque profile. Our residual analysis shows jumps under-jump (h_sim 0.46 vs h_real 0.84) with dq RMSE dominating. CMA-ES 2D search lets the data decide the direction; the axis is motivated, the sign is empirical.

## 3. Compliant-leg jumping energy regulation

**Source**: [Stable and Fast Planar Jumping Control for a Compliant One-Legged Robot (PMC9415179)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9415179/)

**Citation**: Compliant one-legged robots use spring-loaded inverted pendulum models with energy-based leg rest-length regulation to track jump height while compensating for energy dissipation.

**Application**: Confirms leg/contact compliance is a legitimate energy-storage mechanism for jumps. If contact tuning cannot recover the under-jump, it points to a fundamental Mode-A energy deficit (real torque + sit2stand-optimized mass leaves jumps under-powered) — an honest limitation to document, since `tau_scale` is forbidden.

## Phase 3 hypothesis (empirical)

Jumps under-jump (dq residual dominant, h ~half). tau_scale forbidden, mass fixed for sit2stand. Contact compliance is the remaining energy lever. CMA-ES 2D (solref_tc, imp0) finds whether elastic return helps or stiffer push-off helps. Either outcome is informative.
