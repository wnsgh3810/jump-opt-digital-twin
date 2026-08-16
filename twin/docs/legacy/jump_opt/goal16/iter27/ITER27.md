# GOAL16 Iter27 -- LOTO 15-fold cross-validation on Iter26 BEST

## Summary

- **Method**: sklearn LeaveOneOut, 15 folds, per-trial 12D+2D NM warm-started
  from Iter26 best (149.48). Train on 14 trials, aggregate to mean params/bias,
  evaluate mean-model on 1 held-out test trial.
- **Verdict: OVERFIT** (6/15 folds gap/train > 0.5).
  - `avg_train_RMSE`: 353.13 (mean-model on 14 train trials)
  - `avg_test_RMSE`: 343.24 (mean-model on 1 held-out trial)
  - `avg_gap`: -9.89 (test - train)
  - `max_gap`: +748.46 at fold 14 (held-out `0602_150_2.2_500_5`)
  - 6/15 folds exceed overfit threshold (gap/train > 0.5)
- **Elapsed**: 18.66 min (15 folds × per-trial NM refit).
- Mode A LOCK (tau_scale_h = tau_scale_k = 1.0).

## Key finding — mean-model is unsuitable for per-trial fits

The Iter26 axis (per-trial 12D + 2D bias) achieves total=149.48 because each
of the 15 trials has its own optimized 12D+2D params. Averaging those 15
parameter sets into a single "mean model" gives ~353 RMSE on the 14 train
trials themselves — i.e. the mean is far from any individual optimum.

This reproduces the Iter9 (LOTO 5D global) finding: per-trial optimal
parameters do not collapse to a single mean model. Per-trial fit is itself
the trial signature, not a generalizable global parameter set.

## Per-fold pattern

- **Low-current 0424 + 0602 trials** (folds 0-2, 9-13): test_RMSE < 50,
  much smaller than train_RMSE ≈ 350 → negative gap (mean model happens to
  predict these short, low-jump trials roughly well, although not optimally).
- **High-current 0424 trials** (folds 3-8): test_RMSE 457-865, huge positive
  gap → mean model fails on these trials. They demand different 12D params.
- **Worst fold (14)**: `0602_150_2.2_500_5` test_RMSE = 1028.46
  (gap/train = +267%). This trial is an extreme outlier; the other 14 trials'
  mean fails to predict it.

## Interpretation

1. **Iter26 axis = trial-specific fit** — not an overfit in the sense that
   individual trial fits are bad, but the aggregation strategy (simple mean)
   is the wrong way to test generalization.
2. **Generalization route**: instead of mean params, use a trial-conditioned
   model where 12D+2D params are predicted from trial features (current limit,
   joint init angles, payload). This was hinted at in `next_action_BO_hybrid.md`
   memory.
3. **Two dataset clusters** (0424 / 0602): the LOTO results show distinct
   patterns by dataset. Per-dataset mean models might generalize within a
   dataset but not across. This matches the Iter4/Iter19 finding of opposite
   encoder bias polarity between 0424 and 0602.

## Files

- `run_i27.py`             -- LOTO 15-fold driver (sklearn LeaveOneOut)
- `iter27_metrics.json`    -- aggregate + per-fold metrics (25,619 bytes)
- `iter27_logs.npz`        -- held-out trial logs (one per fold)
- `gen_plots_i27.py`       -- per_fold_bar + train_test_scatter
- `gen_anim_i27.py`        -- 15 held-out trial GIFs (MuJoCo Renderer)
- `upload_notion_iter27.py` -- Notion upload (22 sections + 30 images)
- `plots/per_fold_bar.png`
- `plots/train_test_scatter.png`
- `anim/anim_fold_NN_*.gif`  -- 15 fold-specific anims (~89.6 MB total)
- `notion_iter27_page.json`

## Notion

- Page URL: https://app.notion.com/p/386ab81d255081ae8c7ac76f5ffbd472
- Title: "GOAL16 Iter27 -- LOTO 15-fold CV (OVERFIT, avg_test=343.24,
  avg_gap=-9.89, overfit=6/15)"
- Image blocks: 30/30 verified.

## Mode A LOCK

This iteration does not modify any motor-side parameter. tau_scale_h =
tau_scale_k = 1.0 throughout. The score function and XML builder are
identical to Iter26.

## Next candidates

1. Per-dataset (0424/0602) mean model — check if generalization works within
   a dataset cluster.
2. Trial-conditioned regressor: map (current limit, gear ratio, init angles)
   → 12D+2D params (e.g. Gaussian process or simple polynomial).
3. Robust statistics (median, trimmed mean) instead of arithmetic mean for
   parameter aggregation across folds.
4. Hierarchical model: per-trial 12D random effects + dataset-level fixed
   effects (mixed-effects identification).
