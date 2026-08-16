---
name: bo-tpe-multivariate-has-hard-db-size-limit-5k-trials
description: TPESampler(multivariate=True) RAM cost scales with DB trial count; 300K trials = OOM crash on 64 GB
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Discovery — 2026-05-17

**Rule**: When running Optuna BO with `TPESampler(multivariate=True, group=True)`, the per-trial RAM cost during `sample_relative` (KDE fitting + candidate scoring) scales roughly linearly with the number of historical trials in the study. With:

- 300K trials, 13 dims, `n_ei_candidates=500` → **~50 GB per worker during sample_relative**
- 2K trials, 13 dims, `n_ei_candidates=100` → ~0.3 GB per worker

So a 64 GB machine cannot run even 1 worker on a 300K-trial study with default TPE multivariate.

**Why**: Multivariate TPE fits a kernel density estimate on the elite trial set, then evaluates `n_ei_candidates` candidate points against it. Memory is O(N × D × C) where N=elites, D=dims, C=candidates. With `gamma=0.05` of 300K = 15K elites × 13 dims × 500 candidates = ~100M float intermediates per sample call. Numpy broadcasts create large intermediate arrays.

**How to apply**:
1. When DB exceeds ~5K trials in a multivariate-TPE study, **compact it** before resuming — keep top-N + random-sample, drop the rest. See `bo_v19_compact_db.py` for the SQLite-level template (avoids loading via Optuna API).
2. Set `n_ei_candidates ≤ 100` (default 24 is fine; 500 is wasteful) and `gamma ≤ 0.10` if you must run on many trials.
3. **Test single worker RAM before launching multi-worker** — see `bo_v19_single_test.py` template with auto-abort at threshold.
4. Always run `bo_guardian.py` (50 GB cap) alongside any large BO sweep.

**Why this rule exists**: 2026-05-17 14 workers were OOM-killed when restarting V19 sweep with 300K-trial DB; user's computer froze (RAM 100%). Even 1 worker hit 50 GB during a single `sample_relative` call. Recovery: compacted DB to 2K trials → per-worker RAM dropped to 0.3 GB.

Related: [[session_recovery_state]], [[next_action_BO_hybrid]], [[sweep_optimization_lessons]]
