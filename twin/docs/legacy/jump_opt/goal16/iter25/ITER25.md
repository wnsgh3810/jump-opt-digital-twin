# GOAL16 Iter25 -- per-trial friction (fc/fv) wider NM on Iter18 base

## Summary

- **Score**: 152.8154 (baseline 160.79 -> +4.96%)
- **vs Iter18 (153.52)**: +0.46% improvement
- **KEEP threshold 149.0**: missed by 3.82 -> **DROP**
- **BV total**: 7 / 60 (15 trials x 4D = 60D total)
- **15/15 trials IMPR** (all improved over Iter18 base)
- **Elapsed**: 7.99 min

## Method

- Per-trial 4D Nelder-Mead on `fc_hip`, `fv_hip`, `fc_knee`, `fv_knee`
- Bounds: +/-50% wider than Iter18 default (with global hard cap)
- 3 restarts (baseline + 2 perturbed), adaptive=True, max_iter=80
- Other 8D parameters LOCKED at Iter18 per-trial best
- Mode A LOCK, W_GRF=0.2

## Worst-3 (next candidates)

1. `0424_150_2.2_500_4` (12.57)
2. `0424_120_2.2_200_2.8` (11.79)
3. `0602_150_2.2_500_5` (11.73)

## Per-trial friction patterns

- `fc_hip` variance large: 0.04 (0602_60_1.5) ~ 3.62 (0424_60_1.5) Nm
  -> two-dataset hip friction reversal pattern
- `fv_hip`: 0.12 ~ 1.34 (moderate)
- `fc_knee`: 0.008 ~ 0.31 (small + consistent, knee gear friction small)
- `fv_knee`: 0.001 ~ 0.22 (mostly very small)

## Files

- `run_i25.py`         -- 4D NM per-trial driver
- `iter25_metrics.json` -- final metrics + per-trial best params
- `iter25_logs.npz`     -- 15-trial sim logs (flat tn__field)
- `plots/`              -- 15 four-panel compare PNGs
- `anim/`               -- 15 MuJoCo Renderer GIFs (80f, 60ms)
- `notion_iter25_page.json` -- Notion page metadata
- Notion URL: https://app.notion.com/p/GOAL16-Iter25-per-trial-friction-fc-fv-wider-NM-50-4D-15-DROP-score-152-82-BV-7-5-0-386ab81d25508130a969f741044de34a

## Next candidates

1. Iter18 base + fc/fv per-trial DE (global of Iter25 NM)
2. Stribeck friction (fc + fv*dq + fs*exp(-(dq/dqs)^2)*sign(dq)) 5D per-trial
3. Iter23 (joint LSQ + friction 12-param) base + fc/fv per-trial NM
4. Per-trial friction variance pattern analysis -> dataset-specific friction signature

## Verdict

**DROP** -- although 15/15 IMPR direction is correct, accumulated improvement of 0.71
(152.81 vs 153.52) is below the KEEP threshold. Friction-only refinement on Iter18
base has marginal effect; truly KEEP-passing improvement requires re-optimizing the
12D base itself with friction-aware bounds.
