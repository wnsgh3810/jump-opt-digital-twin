---
name: V14 후 다음 액션 — Thorough BO + Multi-stage 탐색
description: V14 완료 후 Bayesian Optimization 기반 옵션 B 구현. Grid sweep boundary chasing 해결 + 시간 제약 없이 최대 탐색.
type: project
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
**액션 (사용자 결정 26.04.29)**: V14 종료 즉시 옵션 B 시작. **시간 제약 없음, 최대 탐색**으로 진행.

# 배경 — Grid sweep 한계

Grid sweep은 13-dim coupling ridge에서 boundary chasing에 빠짐. 한 dim 풀면 다른 dim 새 boundary. 매 sweep마다 ranges 재설계 + 7~13h 재계산. v9~v14 5번 반복.
v14 진행 중에도 여전히 5/13 boundary (alpha=0.8 LOWER, kc=5000 LOWER, sd=1.8 UPPER, M_tot=3.0 LOWER, fb=0 LOWER).

# 설계 원칙 (사용자 26.04.29)

> "시간 오래걸려도 되니까 탐색도 많이하고 stage가 많아도 stage 별 trial이 많아도 되니까 최대한 많은 경우의 수를 고려하더라도 최적값을 찾고 싶어"

→ **시간 제약 제거**. **Multi-stage, multi-sampler, multi-seed**로 global optimum 추구.

# 옵션 B 구조 (THOROUGH)

## Stage 0: Warm-start (CRITICAL)
- `multi_trial_top_combined.npz` 의 **2500 trials + v14 top 500 추가 = 3000 trials**를 `study.add_trial()` 로 주입
- v9~v14 누적 prior로 BO가 v14 best (~16.6) 부터 시작
- Distributions: 13 dim 모두 FloatDistribution (각 dim의 union 범위 + 여유 ±20% 확장)
- **Range 확장 의도**: boundary 닿는 dim들 (alpha, kc, sd, M_tot, fb)을 BO가 외부로 자유 탐색

## Stage 1: TPESampler 대규모 탐색 (N=5000)
- **목적**: TPE acquisition으로 promising 영역 자동 발견
- 13 dim continuous 공간
- Sampler: TPESampler(n_startup_trials=200, multivariate=True, group=True)
  - multivariate=True: dim 간 결합 학습
  - group=True: highly-correlated dim 함께 sample
- 추가 평가: **5000 trials**
- per-trial: 5 sim avg, run_sim_jit 재사용
- 시간 예상: ~50분 (5000 × 400ms / 14 worker)

## Stage 2: Multi-seed Exploration (5 seeds × 1500 trials = 7500)
- **목적**: TPE는 random seed에 민감 → 다른 시작점에서 multi-modal 탐색
- 5개 독립 study (seed=0,1,2,3,4) 각자 1500 trials
- 모두 같은 warm-start 사용 (3000 prior 동일 주입)
- 각 study의 best 비교 → multi-modal landscape 검증
- 시간 예상: ~75분 (병렬화 가능 — 5 study × 14 worker = 모두 독립)

## Stage 3: CmaEsSampler Refinement (1500 trials)
- **목적**: TPE와 다른 알고리즘으로 cross-validation
- Stage 1+2 best 영역에서 CMA-ES 시작
- CMA-ES = continuous local-to-global 강함, gradient-free
- 시간 예상: ~15분 (1500 × 400ms / 14)

## Stage 4: Top-K Cluster Analysis
- Stage 1~3 통합 best 100개 → DBSCAN/K-means로 cluster 식별
- 각 cluster center 주변 dense BO (각 200 trials)
- 가능한 multi-modal optimum 검증
- 시간 예상: ~10분 × cluster 수

## Stage 5: Narrow Grid Refinement (per cluster)
- 각 cluster best 주변 ±5% 영역에 정밀 grid (~500K configs each)
- 이전 sweep 인프라 재활용
- BO가 못 잡는 grid-level local 정밀도 보강
- 시간 예상: ~10분 per cluster

## Stage 6: Sensitivity Analysis at Final Best
- 13 dim 각자 ±20% 1D sweep (~50 points × 13 dim = 650 evals)
- best 안정성 / sharp peak vs flat plateau 진단
- 시간 예상: ~3분

# 총 시간 예상

| Stage | Trials | Time |
|-------|--------|------|
| 0 Warm-start | 3000 (주입) | <1분 |
| 1 TPE | 5000 | 50분 |
| 2 Multi-seed | 7500 | 75분 |
| 3 CMA-ES | 1500 | 15분 |
| 4 Cluster BO | ~600 | 10분 |
| 5 Narrow grid | ~500K × clusters | 30분 |
| 6 Sensitivity | 650 | 3분 |
| **합계** | **~14600 BO + 1.5M grid** | **~3시간** |

vs 현재 grid 7~13h → 시간도 단축 + 훨씬 더 많은 영역 탐색.

# 구현 단계

1. `bo_sweep.py` — Stage 0~3 (메인 BO 파이프라인)
   - Optuna study 생성, FloatDistribution 13 dim
   - warm-start: combined.npz + v14_checkpoint top500 → study.add_trial()
   - Stage 1: 단일 TPE study, n_trials=5000
   - Stage 2: 5 study × 1500 trials, 각자 별도 storage
   - Stage 3: CmaEsSampler study, 1500 trials
   - n_jobs=14 병렬, per-trial = run_sim_jit × 5 trials avg

2. `bo_cluster.py` — Stage 4
   - Stage 1~3 모든 trial 통합 → top 100 추출
   - sklearn DBSCAN (eps 자동) or K-means(k=5) cluster
   - 각 cluster center 주변 dense BO (200 trials each)

3. `bo_narrow_grid.py` — Stage 5
   - 각 cluster best → ±5% grid (기존 sweep 인프라 재활용)
   - 13 dim × 5점 = ~1.2M configs per cluster

4. `bo_sensitivity.py` — Stage 6
   - 1D sweep around final best, 13 dim 독립

5. 결과 통합:
   - 모든 stage trials → `bo_results_combined.npz` (별도 파일)
   - 최종 best → `multi_trial_top_combined.npz`에 version='v15_bo' 태그로 추가

# 의존성

- `pip install optuna` (필요시 설치)
- `pip install scikit-learn` (DBSCAN/K-means용)
- 기존 numba JIT 사용 (run_sim_jit, score_one_trial)

# 기대 효과

- **Boundary chasing 완전 해소**: continuous 탐색 + range 확장
- **Multi-modal 검증**: 5 seed + cluster + CMA-ES 다중 검증
- **Coupling 자동 처리**: TPE multivariate=True
- **Sensitivity 가시화**: Stage 6으로 best 안정성 확인
- **재현성**: 모든 trial logged, 사후 분석 가능

# 주의사항

- Range 확장 시 비물리적 영역 들어갈 수 있음 (alpha>1 등) → 각 dim에 hard physical limit 두기
  - alpha: [0.7, 1.05] (1.0 약간 초과 허용, > 1.05면 비물리)
  - kc: [3000, 25000]
  - sd: [0.3, 2.5]
  - M_tot: [2.8, 5.5]
  - fb: [0, 0.4]
- 14600 trial × 5 sim = 73000 sim. 메모리/디스크 누수 방지 (Optuna in-memory storage 권장)
- 중간 checkpoint: 매 1000 trial마다 study.trials_dataframe() → CSV 저장
- 사용자가 중간에 결과 보고싶어할 수 있음 → 매 stage 끝나면 best report 출력

# 사용자 의도

- v9~v14 grid sweep의 boundary chasing 패러다임 종료
- 시간 무제한, 최대 탐색으로 true global optimum 추구
- "냉철하게 판단해봐" 패턴 → 단순 BO보다 multi-stage multi-sampler 정당화 가능
- 디지털 트윈 목표 → 모든 dim true value 식별이 종착점
