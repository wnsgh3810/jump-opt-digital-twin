# Phase 2 — External Sources (joint friction)

## 1. MuJoCo Coulomb-Viscous friction mapping

**Source**: [Extended Friction Models for the Physics Simulation of Servo Actuators (arXiv 2410.08650)](https://arxiv.org/pdf/2410.08650)

**Citation**: Simulators like MuJoCo implement the Coulomb-Viscous friction model, which approximates friction by a constant static friction and a linear viscous friction. The `damping` term in MuJoCo corresponds to the viscous friction coefficient, while the `frictionloss` parameter corresponds to Coulomb friction.

**Application to GOAL19**: Confirms our axis mapping — `fv_*` → joint `damping` (viscous, Nm·s/rad), `fc_*` → joint `frictionloss` (Coulomb, Nm). Exactly the two-parameter-per-joint model we fit (4D for hip+knee).

## 2. Friction identification from torque–velocity data

**Source**: [Physics-Informed Learning for the Friction Modeling of High-Ratio Harmonic Drives (arXiv 2410.12685)](https://arxiv.org/pdf/2410.12685)

**Citation**: Friction model parameters can be identified from experimental data of torque error between motor torque and joint velocity measurements. The Coulomb-viscous friction model is preferred due to its linear expression.

**Application**: Our robot uses AK80-9 with a gearbox (harmonic-drive-like). Coulomb + viscous is the right first model. Higher-ratio drives have larger friction — consistent with fitting non-trivial fc/fv. Stribeck (low-speed) is a Phase-later candidate if C-V insufficient.

## 3. Coulomb-viscous sufficiency + MuJoCo XML reference

**Source**: [MuJoCo XML Reference — joint damping/frictionloss](https://mujoco.readthedocs.io/en/stable/XMLreference.html)

**Citation**: The Coulomb-viscous friction model is sufficient for depicting frictional behavior in multibody dynamic systems, and can estimate and compensate for torque losses during impacts. `frictionloss` applies a constant friction torque opposing motion; `damping` applies torque linear in velocity.

**Application**: Motivates Phase 2 as a distinct axis from armature (Phase 1). Friction dissipates energy (should help stabilize the divergent sit2stand_gnd sim) whereas armature only adds inertia. Impact torque-loss note is relevant to jump landing.

## Phase 2 hypothesis

Joint friction (damping) adds **velocity-proportional dissipation** → should stabilize the sit2stand_gnd_0319 divergence (sim spins up to dq=38 rad/s uncontrolled). Coulomb friction adds a **dead-band resistance** → may slow the over-fast 0424 jumps back toward real. Risk: too much friction dampens the well-tracked 0421/0422 jumps. CMA-ES 4D balances across all 31.
