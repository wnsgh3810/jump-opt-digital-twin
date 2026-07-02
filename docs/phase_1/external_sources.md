# Phase 1 — External Sources (≥3 required)

## 1. Bridging Sim-to-Real for Legged Robots — mass distribution deviation

**Source**: [Towards bridging the gap: Systematic sim-to-real transfer for diverse legged robots (arXiv 2509.06342)](https://arxiv.org/pdf/2509.06342)

**Relevant citation** (paraphrased): One legged robot's mass distribution deviated from its CAD model, with hardware measurements indicating a rearward weight shift of about 60% despite the model placing the base center of mass within 1 cm of its geometric center. Additionally, comparing measured inertia to CAD measurements showed the thigh inertia was noticeably higher, while the shank remained consistent.

**Why it applies to GOAL19**: Confirms that CAD-vs-real deviation is (1) part-specific (thigh vs shank different signature), (2) affects both mass and inertia independently, (3) can be dominated by CoM shift not accounted for in geometric center assumption. Phase 1 axes chosen exactly to expose these three modes per part.

## 2. MuJoCo CAD-to-MJCF calibration workflow

**Source**: [Simulating YOUR robot in MuJoCo — how to create a MJCF file from a CAD model (yasunori.jp)](https://yasunori.jp/en/2024/07/13/mujoco-model-yourself.html)

**Relevant citation**: By default, mass is automatically calculated for each geometry from the mesh shape assuming density of water. Setting the mass in the geometry to the actual measured mass allows the rotational moment of inertia to be automatically calculated based on the geometry's shape.

**Why it applies to GOAL19**: The default density assumption is a systematic bias. Our CAD has explicit component masses so density-of-water shouldn't apply — but the inertia is auto-computed from geometry, which assumes uniform density. Non-uniform density (dense motor cores + light shells) makes actual `I` differ from geometric `I` even with correct mass. Justifies independent `I_scale` axes.

## 3. CMA-ES in noisy robot optimization

**Source**: [Improving CMA-ES Convergence Speed, Efficiency, and Reliability in Noisy Robot Optimization Problems (arXiv 2601.09594)](https://arxiv.org/pdf/2601.09594)

**Relevant citation**: CMA-ES is well suited for experimental robot optimization because it does not require derivative information, and is robust in cost functions with noise, nonconvexity, parameter interaction, and multi-modality.

**Why it applies to GOAL19**: Our score function is:
- Non-differentiable (MuJoCo forward sim, contact events)
- Multi-modal (different jump PDs may find local minima)
- Coupled (mass & inertia affect similar residuals)
- Noisy at contact (foot_pen chatter)

CMA-ES chosen over NM (local, sensitive to init) and DE (slower on this dim range). Population 12, maxfevals 400 → adequate for 15D.

## Optional additional (Phase 1 supporting)

- [CMA-ES Survey (Springer)](https://link.springer.com/article/10.1007/s11831-026-10557-z) — comprehensive variants and hybrids
- [Whole-Body MPC with MuJoCo (arXiv 2503.04613)](https://arxiv.org/abs/2503.04613) — MJX + JAX gradient approach as alt path
