# GOAL15 Iter5 — scipy.optimize.basinhopping 12D DEEP

## 사전 조건
- Iter1 (NM 4-restart) 완료: 161.61
- Iter2 (DE 2D global) 완료: **160.79 (warm-start 기준)**
- Iter4 (NSGA-II Pareto) 완료: 161.44

## 설계 (다른 method 명시)

| Iter | Method | Score | Dim |
|---|---|---|---|
| Iter1 | NM (4-restart, local) | 161.61 | 10D |
| Iter2 | DE (popsize=12, maxiter=300, global) | **160.79** | 2D (solref_tc × imp0) |
| Iter4 | NSGA-II (multi-objective Pareto) | 161.44 | varies |
| **Iter5** | **Basinhopping (Wales-Doye 1997, global+local)** | **TBD** | **12D full** |

**Iter5 다른 점**:
- BH = Metropolis-accepted random hop + NM local refine 조합
- 12D **full param** 동시 탐색 (다른 iter는 부분 axis 또는 sequential)
- Trial별 seed 다양화 (BH_SEED_BASE + trial_idx × 1009, prime offset)
- niter=50 hops × NM_maxiter=200 (각 hop adaptive=True)
- BoundedStep 5% (custom take_step), Iter2 best per-trial warm-start

## 외부 근거 (≥3 URL)
- Wales & Doye 1997 *J.Phys.Chem.A* 101(28) 5111 — BH original paper
- scipy.optimize.basinhopping docs (v1.16)
- Cassioli et al. 2024 *J.Global Optimization* — BH performance analysis
- arxiv 2510.25938 (2024) — adaptive BH parallel implementation

## 파일

- `run_i5_basinhopping.py` — 12D BH per-trial, niter=50
- `gen_plots_i5.py` — 4-panel × 15 trial
- `gen_anim_i5.py` — MuJoCo Renderer 80f × 15 trial
- `upload_notion_i5.py` — Locked Template 22 sections + 30 image
- `update_master_insights_i5.py` — MD §21.5 append

## KEEP/DROP 판정
- threshold = Iter2 best × 0.97 = 160.79 × 0.97 = **156.0**
- boundary guardrail = 20%, BV count < 10 required
