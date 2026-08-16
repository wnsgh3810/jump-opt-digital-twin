---
name: jump-c-bo-setup-2026-05-21
description: jump_C_bo 셋업 — widened bounds + LHS seed + HybridSampler (TPE 70% + Random 30%)
metadata: 
  node_type: memory
  type: project
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Jump Strategy C BO Setup (2026-05-21)

**상태**: v5 grid plateau (best 23.24, 4개 chase boundary) → BO refinement 시작

## 구성

- **DB**: `sweep/results/jump_C_bo.db`
- **스크립트**: `sweep/jump_C_bo.py` (setup/worker/monitor/save_best/compact 서브명령)
- **Seed 스크립트**: `sweep/jump_C_bo_seed_widened.py` (Latin-Hypercube 800 samples in widened bounds)
- **Compact 스크립트**: `sweep/jump_C_compact_topK.py` (v1/v2/v3 거대 npz → top-5K npz)
- **.bat**: `sweep/run_jump_C_bo.bat` (사용자 더블클릭)

## Warmstart 구성 (총 11,515 trials)

1. **Grid top-5K (10,810)**: v1 602 + v2 1556 + v3 3652 + v5 5000
2. **Widened LHS seed (705)**: 800 LHS샘플 평가 → SCORE_CAP=200 통과 705개
   - Min sc=25.97 (v5 best 23.24와 근접)

## Widened bounds (v5 chase 경계 확장)

```
alpha  [0.50, 1.10]      v5 chase LO 0.70 → DOWN
gAv    [0.40, 1.20]
gBv    [0.10, 3.0]
Is1    [0.015, 0.20]
Is2    [0.005, 0.08]     v5 chase LO 0.020 → DOWN
Kv     log[1e-4, 1e-2]
sp     [0.55, 1.60]
sd     [0.40, 2.10]
tm     log[1e-5, 1e-2]   v5 chase UP 0.003 → UP
fb     [0.0, 0.50]
M_tot  [2.20, 3.80]      v5 chase LO 2.80 → DOWN
```

## RAM 안전장치 (참고: [[bo_tpe_db_size_limit]])

- `n_ei_candidates=100` (default 24, 500 위험)
- `gamma = min(0.10*n, 500)` cap
- TPE multivariate, group=True
- HybridSampler: TPE 70% + Random 30% (sit2stand 25%보다 더 random — 넓힌 영역 탐색)
- 8 workers (jump JIT heavy, sit2stand 6보다 약간↑)
- ram_monitor.py 별도 창 (50GB auto-kill)
- DB > 1GB 시: `python jump_C_bo.py compact` (top 3K + random 2K 유지)

## 다음 단계

- BO 결과 best 확인 후 plot으로 비교
- 메모리 [[next_action_BO_hybrid]] 다음 단계 narrow grid 진행 여부 판단
