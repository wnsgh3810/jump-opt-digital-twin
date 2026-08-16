# GOAL15 Iter4 — Sobol-informed targeted refinement

## 사전 조건
- Iter3 Sobol 결과 (`iter3/iter3_sobol.json`) 존재
- top-3 S1 axis 식별 완료

## 설계 (Iter3 결과 의존, runtime 결정)

Iter3에서 식별된 top-1 S1 axis에 대해 1D L-BFGS-B (gradient-based local)
또는 1D scipy.optimize.minimize_scalar (golden section) 적용.

- Method: scipy.optimize.minimize_scalar (Brent / Bounded)
- 이유: 1D narrow local, smooth landscape에서 가장 효율적
- 외부 근거: Brent 1973 "Algorithms for Minimization Without Derivatives"

## 다음 후보 axis (Iter3 미실행 시 default 순서)

1. m_calf_scale (CAD overestimate 의심, GOAL14 Iter32 lower bound)
2. solref_tc (contact dynamics, 0602 group)
3. fc_knee (Coulomb friction, joint level)
4. stiff_knee (passive elasticity, jump dynamics)

## 파일 (Iter3 완료 후 생성 예정)

- `run_i4_targeted.py` — scipy.optimize.minimize_scalar 1D refine
- `gen_plots_i4.py`, `gen_anim_i4.py`, `upload_notion_i4.py`
- `run_post_i4.bat`
