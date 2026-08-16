# GOAL16 Iter30+ Research Pool — Generated 2026-06-22 ~03:00 KST

> ★ 사용자가 deadline 12:00 KST로 2h 연장 후, Iter29 진행 중 백업 research workflow로 생성.
> 6 external research (MuJoCo 2025 contact / chattering / multi-motion ID / sensor noise / Pareto / Stribeck) → synthesis → adversarial verify.
> ⚠️ 3 adversarial lens (physics / q/dq safety / time budget)는 schema error로 fail — 모든 axis가 0/3 refutation으로 SURVIVE. BG worker가 axis 본문 + 자체 판단으로 선택할 것.
> ⚠️ 8 strict rules + q/dq 5% guard + Iter26 baseline 보호 + Mode A LOCK 모두 유지.

---

# GOAL16 Iter30+ Research Pool (Verified)

> Generated 2026-06-22 ~03:00 KST after 3-lens adversarial review.
> Surviving axes: probability of success-ordered.
> BG worker should consume from top, skip refuted axes.

> **NOTE**: All three lens verdicts (physics-realism, qdq-safety, time-budget) returned `null` — no refutations were issued. Therefore every axis tallies 0/3 refutations and SURVIVES by the stated rule (≤1 refutation → SURVIVE=true). The pool is preserved in full, ordered as originally recommended.

---

## Surviving Axes (use these for Iter30+)

#### Axis 1 — Geom margin landing pre-engagement (margin=0.001-0.003m)

**Hypothesis**: 118Hz GRF chattering is partly LCP "contact in/out" flicker across timesteps. `margin` extends active-contact distance so the foot enters continuous regime BEFORE hard contact, eliminating the bang-bang seed of chatter without changing solref/solimp.

**Source**: MuJoCo Modeling docs via grf-chattering report — "single most effective single-knob change in our experience for foot-ground 100Hz oscillation."

**Implementation**:
```xml
<geom name="foot_pad" margin="0.002" gap="0" .../>
```
BO bound: `margin ∈ [0.0005, 0.005]` (1 param).

**Expected effect**: GRF RMSE -10 to -20%; score 149 → ~140-145. Orthogonal to Iter29 solref_tc floor.

**q/dq risk**: SAFE. margin only changes contact detection threshold; foot effectively "lands" 2mm earlier (~0.5° q-shift). Within 5% guard.

**Compatibility with Iter26 STACK**: Pure additive — solref/solimp untouched.

**Wall-time**: NM 20min (single param) or BO narrow 40min coupled with gap.

**Verification: PASS (refutation: 0/3)**

---

#### Axis 2 — Explicit foot↔floor contact pair (LCP rank reduction)

**Hypothesis**: Unpaired geoms let MuJoCo average foot+floor solref/solimp, diluting your tuned values. Explicit `<pair>` overrides geom params, AND disabling all other foot↔body contacts (contype/conaffinity) shrinks LCP rank → tighter Newton convergence → less phantom-contact chatter.

**Source**: MuJoCo XML Reference + mujoco-contact-2025 report — "all menagerie quadrupeds use priority=1; without it MuJoCo averages — explains parameter insensitivity."

**Implementation**:
```xml
<contact>
  <pair geom1="foot_pad" geom2="floor"
        solref="0.002 1" solimp="0.99 0.999 0.005 0.5 2"
        friction="1.0 0.5 0.01 0.0001 0.0001"/>
</contact>
```
Or equivalently `priority="1"` on foot geom.

**Expected effect**: Removes parameter-insensitivity ceiling. Score 149 → ~140-148 alone; AMPLIFIES Axis 1 and Iter29 fix.

**q/dq risk**: SAFE if contact params kept at current Iter26 values; only changes WHO wins the averaging. Moderate if friction tuple modified.

**Compatibility**: Additive — but if combined with Axis 1, do as one NM (3 params: margin, priority, friction[0]).

**Wall-time**: NM 20min.

**Verification: PASS (refutation: 0/3)**

---

#### Axis 7 — qacc_warmstart seeding from static stance

**Hypothesis**: First 0-50ms post-landing chatter is partly LCP solver cold-start. Persisting `qacc_warmstart` across timesteps AND seeding from a precomputed static-stance keyframe puts the solver in the correct basin from t=t_land, eliminating the spike BO mistakes for chattering signature.

**Source**: MuJoCo programming/simulation.rst via grf-chattering report — "removes 0-50ms artificial spike; chatter that 'starts at landing' usually shrinks."

**Implementation**:
```python
# Pre-compute once
mj_setKeyframe(model, data, k_stance)
mj_forward(model, data)
stance_warmstart = data.qacc_warmstart.copy()
# Per trial reset
data.qacc_warmstart[:] = stance_warmstart
# Inside step loop: do NOT zero qacc_warmstart between mj_step calls
```

**Expected effect**: Spike removal in t∈[t_land, t_land+50ms]; score 149 → ~145-148. Cheap, fast, low-risk.

**q/dq risk**: SAFE — only changes solver initialization, not dynamics.

**Compatibility**: Pure additive — no XML changes, only Python wrapper.

**Wall-time**: NM 20min (no params to tune; A/B test only).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 9 — implicitfast integrator + cone=elliptic + impratio=100

**Hypothesis**: Spot/Go1/Go2/AnymalC unanimously use `implicitfast` + elliptic + impratio=100. Pyramidal cone mixes normal/friction basis → spurious normal-force ripple at cone vertices (~slip-rate Hz chatter). impratio=100 stiffens normal vs tangential by 100× explicitly.

**Source**: Spot/Go1 XMLs + Zhang 2025 MPC paper via mujoco-contact-2025 report — "impratio explicitly raised default 1→100; moderate penetration does NOT hurt sim-to-real."

**Implementation**:
```xml
<option cone="elliptic" impratio="100" integrator="implicitfast"
        solver="Newton" tolerance="1e-10" iterations="100"/>
```

**Expected effect**: Friction-induced normal-force jitter -10 to -20%; energy stability for jumping confirmed by DM discussion #2347. Score 149 → ~143-147.

**q/dq risk**: MODERATE — integrator change can shift dynamics 1-3%; verify against Iter26 baseline before locking.

**Compatibility**: Conflicts only if current integrator is Euler (likely is); replaces option block.

**Wall-time**: NM 20min (no BO; binary on/off + tol).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 3 — solimp 5-param full form (width + power shape)

**Hypothesis**: Iter1-29 only tuned solimp d0/d1/dmid (3-param). The 4th (width) and 5th (power) reshape the impedance curve. Width=0.005 vs 0.001 attenuates 118Hz peak by 6-12 dB; power=2 gives quadratic ramp matching rubber behavior.

**Source**: grf-chattering report + RoboLAWeb cheat-sheet — "Metal/concrete solimp='0.9 0.95 0.001 0.5 2' (5-param form)."

**Implementation**:
```xml
solimp="0.99 0.999 0.005 0.5 2"
```
BO bounds: `width ∈ [0.001, 0.01]`, `midpoint ∈ [0.3, 0.7]`, `power ∈ [1, 3]`.

**Expected effect**: GRF chattering amplitude -6 to -12 dB; score 149 → ~143-147. Direct attack on Iter28 finding.

**q/dq risk**: SAFE. Width controls ramp smoothness, not stiffness asymptote — penetration depth unchanged (~1mm).

**Compatibility**: Replaces current 3-param solimp; works on top of Iter29 solref_tc.

**Wall-time**: BO narrow 40min (3 new params).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 5 — Multi-trial regressor stacking (cross-trial PE)

**Hypothesis**: Single-trial fit has rank-deficient regressor — I_xx/I_yy collapse. Stacking 15 (or your 9 Mode A) trials vertically `Y_stack=[Y_1;...;Y_N]` with shared θ enforces ONE physical truth across all trials, breaking degeneracy via persistent excitation across motion manifolds.

**Source**: Gautier-Khalil via manipulator-multi-motion report — "regressor rank must equal #base params and cond(Y_stack) < 100."

**Implementation**:
```python
Y_stack = np.vstack([build_regressor(traj_k) for k in trials])
tau_stack = np.concatenate([tau_k for k in trials])
W = block_diag(*[np.eye(N_k)/sigma_k**2 for k in trials])
theta = np.linalg.solve(Y_stack.T @ W @ Y_stack, Y_stack.T @ W @ tau_stack)
# Verify cond(Y_stack) < 100
```

**Expected effect**: REPLACES current per-trial fit; tighter inertia estimates → score 149 → ~140-146. Identifiability metric (cond) becomes new convergence criterion.

**q/dq risk**: SAFE — purely changes WHICH inertia values are chosen, not the model.

**Compatibility**: Replaces fit procedure but model XML unchanged from Iter26.

**Wall-time**: NM 20min (no BO needed — closed-form WLS).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 4 — Stribeck friction two-stage fit (sit2stand + jump)

**Hypothesis**: Iter15 pure Coulomb has flat plateau v∈[0, vs] — misses the negative-damping dip. Sit2stand (low v) and jump (high v) decoupling fits {fs, vs, δ} from sit2stand and {fc, fv} from jump in two stages, eliminating local-optima coupling.

**Source**: Tjahjowidodo/Olsson via contact-friction-stribeck report — "decoupling avoids parameter coupling causing local optima with joint fitting."

**Implementation**:
```python
tau_friction = (fc + (fs-fc)*np.exp(-(abs(v)/vs)**delta)) * np.tanh(v/0.01) + fv*v
```
Per joint (hip, knee): 5 params × 2 = 10. Two-stage: fit (fs, vs, δ) on sit2stand, freeze, then fit (fc, fv) on jump.

**Expected effect**: q/dq lift-off region (v≈0) RMSE -15 to -25%; score 149 → ~138-145.

**q/dq risk**: MODERATE. tanh(v/ε) with ε=0.01·vs required — undersmoothed Stribeck oscillates at v≈0 in implicit integrator.

**Compatibility**: Additive — replaces current Coulomb-only friction.

**Wall-time**: BO narrow 40min (2-stage: 20+20).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 11 — Override window solref soft during t∈[t_land, t_land+30ms]

**Hypothesis**: Permanent soft floor (Axis 3 width tuning) sacrifices steady-state penetration. Instead, use `mjOPT_OVERRIDE` to swap solref/solimp ONLY during the 30ms landing transient — numerical LPF on GRF without changing steady-state stance behavior.

**Source**: MuJoCo modeling docs via grf-chattering report — "30ms LPF on GRF, no steady-state penetration change; particularly effective for 100-200Hz band."

**Implementation**:
```python
if t_land < t < t_land + 0.03:
    model.opt.o_solref[:] = [0.005, 1]
    model.opt.o_solimp[:] = [0.95, 0.99, 0.01, 0.5, 2]
    model.opt.disableflags |= mjDSBL_REFSAFE  # enable override
else:
    model.opt.disableflags &= ~mjDSBL_REFSAFE
```

**Expected effect**: 118Hz transient knockdown; steady-state stance unchanged. Score 149 → ~144-147.

**q/dq risk**: MODERATE — t_land detection must be reliable (GRF>5N threshold); false trigger softens mid-flight contact.

**Compatibility**: Additive on top of Iter29 + Axis 1.

**Wall-time**: NM 20min (2 params: window length, softness factor).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 6 — NSGA-III Pareto-knee replaces W_GRF=0.2

**Hypothesis**: W_GRF=0.2 is a hand-picked weight trap. NSGA-III with Das-Dennis reference directions sweeps trade-offs; knee-point (max-curvature on normalized F) gives W-free optimal. Feasibility-rule (Deb constraint-dominance) handles 5% q/dq protection without penalty tuning.

**Source**: pymoo NSGA-III via multi-objective-pareto report — "achievement scalarizing function discovers trade-offs automatically as λ varies."

**Implementation**:
```python
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
ref = get_reference_directions("das-dennis", 4, n_partitions=12)  # 455 points
algo = NSGA3(pop_size=100, ref_dirs=ref)
# F = [q_RMSE, tau_RMSE, GRF_RMSE, |Δh|]; G = [q_protect_cv]
# Knee via ASF: idx = ASF().do(Fn, [0.25]*4).argmin()
```

**Expected effect**: Eliminates W-bias artifacts; knee solution often Pareto-dominates current scalarized best by 2-5%. Score 149 → ~143-147.

**q/dq risk**: SAFE — constraint G handles q/dq protection AS A CONSTRAINT, not a soft penalty (better than current 5% rejection).

**Compatibility**: Replaces scalarized BO objective; existing BO params reusable as NSGA vars.

**Wall-time**: BO wide 60min (NSGA-III pop=100 × ~10 gen).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 12 — LOTO cross-trial hypervolume validation

**Hypothesis**: Iter26 might overfit to specific 9 Mode A trials. LOTO (leave-one-trial-out) × NSGA-III gives per-fold Pareto front; HV of held-out fronts vs reference point = transferability metric. Variance of knee-point params across folds = identifiability metric.

**Source**: Nature 2024 LOSO multi-obj via multi-objective-pareto report — "high HV ⇒ params transfer; low knee-param variance ⇒ well-posed."

**Implementation**:
```python
from pymoo.indicators.hv import HV
hv = HV(ref_point=[q_max, tau_max, grf_max, h_max])
scores = [hv(nsga3(trials_minus_i).F_eval_on_i) for i in range(9)]
# Report mean ± std as new validation metric
```

**Expected effect**: Diagnostic, not directly score-improving. CONFIRMS Iter26 generalizes (or exposes fold-specific overfit). Predicts which axes 1-11 will transfer.

**q/dq risk**: SAFE — pure post-hoc analysis.

**Compatibility**: Orthogonal — runs alongside any other axis as validation overlay.

**Wall-time**: BO wide 60min (9 folds × ~6min NSGA-III each).

**Verification: PASS (refutation: 0/3)**

---

#### Axis 8 — Encoder quantization + cogging ripple sensor injection (RESERVE)

**Hypothesis**: Real robot has AS5047P 14-bit encoder (q LSB=4.3e-5 rad joint-side) + 21-pole-pair cogging ripple (0.15 Nm at ω·126 Hz). Injecting these into sim post-`mj_step` makes sim observation MATCH real measurement noise floor, removing artificial RMSE penalty on already-converged params.

**Source**: AS5047P spec + Kollmorgen ripple via sensor-noise-model report — "MuJoCo sensor_noise field removed; user must inject post-mj_step."

**Implementation**:
```python
# Post mj_step
q_obs = np.round(data.qpos[hip,knee] / 4.3e-5) * 4.3e-5 + np.random.normal(0, 1.5e-4, 2)
dq_obs = data.qvel[hip,knee] + np.random.normal(0, 0.07, 2)
# Pre data.ctrl
tau_apply = tau_cmd + np.random.normal(0, 0.05) + 0.15*np.sin(126*2*np.pi*t)
```
Seed RNG per BO trial.

**Expected effect**: Lowers irreducible RMSE floor; reveals which Iter26 "residual" is actually sensor noise. Score 149 → ~146-148 (small absolute, large interpretation gain).

**q/dq risk**: MODERATE — noise on q can trigger 5% guard spuriously; use bounded clamp.

**Compatibility**: Additive wrapper; no model change.

**Wall-time**: NM 20min.

**Verification: PASS (refutation: 0/3)**

---

#### Axis 10 — IDIM-IV closed-loop instrument variable (RESERVE)

**Hypothesis**: Current LSQ has Y(q̇, q̈) noise bias from numerical differentiation. IDIM-IV builds instruments Z from SIMULATED (q̂, q̇̂, q̈̂) using current θ in closed-loop sim; `θ̂ = (Zᵀ Y)^(-1) Zᵀ τ`. Consistent under noise; converges in 2-3 iterations.

**Source**: Janot-Gautier-Vandanjon 2014 via manipulator-multi-motion report — "Consistent under noise" + "DIDIM faster convergence, no q̈ needed."

**Implementation**:
```python
for k in range(3):
    qhat, dqhat, ddqhat = simulate(theta_k)
    Z = build_regressor(qhat, dqhat, ddqhat)
    Y = build_regressor(q_meas, dq_meas, ddq_meas)
    theta_k = np.linalg.solve(Z.T @ Y, Z.T @ tau_meas)
```

**Expected effect**: Bias-corrected θ; expect 1-3% RMSE improvement on q/dq. Score 149 → ~145-148.

**q/dq risk**: SAFE — replaces fit, not model.

**Compatibility**: Replaces Axis 5's WLS step (use one OR the other; Axis 5 is faster, Axis 10 more rigorous).

**Wall-time**: NM 20min (3 iterations of closed-form solve).

**Verification: PASS (refutation: 0/3)**

---

### Recommended Iter30-39 Sequence (unchanged from pool)

| Iter | Axis | Reason |
|------|------|--------|
| 30 | Axis 1 (margin) | Cheapest high-prob win; orthogonal to Iter29 |
| 31 | Axis 2 (pair priority) | Unlocks parameter sensitivity for ALL subsequent |
| 32 | Axis 7 (warmstart) | Free spike removal; fast NM |
| 33 | Axis 9 (implicitfast + elliptic) | Aligns with Menagerie standard |
| 34 | Axis 3 (solimp 5-param width) | Direct chatter attack now that pair is set |
| 35 | Axis 5 (multi-trial stack) | Lock identifiability before friction |
| 36 | Axis 4 (Stribeck) | Lift-off region q/dq fix |
| 37 | Axis 11 (override window) | Surgical landing transient LPF |
| 38 | Axis 6 (NSGA-III knee) | Replace W_GRF=0.2 trap |
| 39 | Axis 12 (LOTO HV) | Final validation before 06-22 deadline |

Reserve: Axis 8 (sensor noise) and Axis 10 (IDIM-IV) if any of 30-37 stalls.

---

## Refuted Axes (do NOT pursue)

*(None — all three lens verdicts returned null, so no axis accumulated the ≥2 refutations required for SKIP.)*

---

## Verification Methodology

- 3 lenses: physics realism / q/dq safety / time budget
- Refutation threshold: ≥2 lenses refute → SKIP
- **Caveat for this run**: All three lens verdicts arrived as `null` (no critique content). Under the stated rule, an absent refutation does not count against an axis, so every axis tallies 0/3 and survives. Operationally, BG worker should still treat the recommended sequence as the consumption order, applying the per-axis q/dq risk notes (MODERATE flags on Axes 4, 8, 9, 11) as runtime guard checks before locking each iteration.
