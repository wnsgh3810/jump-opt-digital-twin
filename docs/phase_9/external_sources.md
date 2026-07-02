# Phase 9 — External Sources (Stribeck friction)

## 1. Stribeck model formula

**Source**: [Stribeck Effect — ScienceDirect Topics](https://www.sciencedirect.com/topics/engineering/stribeck-effect)

**Citation**: `F(v) = [Fc + (Fs − Fc)·exp(−(|v|/vs)^p)]·sign(v) + Fv·v`, where Fc = Coulomb, Fs = static (Fs > Fc), Fv = viscous, vs = Stribeck velocity (sliding velocity where only ~37% of the static excess remains). Transition from stick to slip decays exponentially, velocity-dependent.

**Application**: Our XML already provides `Fc` (frictionloss) + `Fv·v` (damping). Phase 9 ADDS the Stribeck excess `(Fs−Fc)·exp(−(|v|/vs)^2)·sign(v) = ds·exp(...)·sign(v)` via `mjcb_passive`, and jointly RE-FITS a lower `fv_hip`.

## 2. Extended friction models outperform Coulomb-Viscous

**Source**: [Extended Friction Models for the Physics Simulation of Servo Actuators (arXiv 2410.08650)](https://arxiv.org/pdf/2410.08650)

**Citation**: Extended friction models (incl. Stribeck) can outperform the standard Coulomb-Viscous model, achieving mean absolute error up to 2× lower across trajectories/gains.

**Application**: Motivates testing whether velocity-dependent friction breaks the Phase 4 trade-off (uniform C-V friction couples sit2stand stability and jump drag through the same fv).

## 3. MuJoCo has no native Stribeck (custom implementation needed)

**Source**: [Modeling static friction/stiction — MuJoCo issue #1366](https://github.com/google-deepmind/mujoco/issues/1366)

**Citation**: MuJoCo does not natively model Stribeck/stiction; the suggested approach is to set friction to stiction values at small tangential velocity or add a custom velocity-dependent term.

**Application**: We implement via `mujoco.set_mjcb_passive` (set AFTER model creation to avoid compile errors — setting before `from_xml_string` raises a Python-exception engine error). Callback adds `ds·exp(−(|v|/vs)^2)·sign(v)` to `qfrc_passive` on hip/knee.

## Phase 9 hypothesis (falsifiable)

sit2stand stability needs friction at LOW speed; jumps are hurt by VISCOUS drag at HIGH speed. Stribeck supplies low-speed friction as a static excess → allows LOWERING fv_hip (viscous) → jumps recover while sit2stand stays stable. **BUT**: Phase 5 showed jump h caps at ~0.62 from torque under-read regardless of friction — so Stribeck's upside is bounded by that structural ceiling. CMA-ES (fv_hip, ds_hip, ds_knee, vs) decides KEEP/DROP.
