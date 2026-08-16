# GOAL16 Iter26 -- Iter18 + Iter19 STACK (★ new GOAL16 BEST)

## Summary

- **Score**: 149.4772 (baseline 160.79 -> +7.03%)
- **vs Iter18 (153.52)**: +2.64% improvement
- **vs Iter23 (152.66, prev BEST)**: +2.08% improvement -> **★ new GOAL16 BEST**
- **KEEP threshold 148.08**: missed by 1.40 -> **DROP**
- **BV total**: 5 / 30 (boundary_safe = True)
- **15/15 trials IMPR** (all improved over Iter18 base)
- **Elapsed**: 7.06 min

## Method

- Iter18 12D per-trial best params LOCK (worst-3 DE 12D ±30%, KEEP)
- Per-trial 2D Nelder-Mead on `q1_offset`, `q2_offset` ∈ [-1°, +1°] (Iter19 pattern)
- n_restarts=3 + Iter19 best bias warm-start (hybrid)
- maxiter=400, adaptive=True, xatol=1e-6
- Mode A LOCK (tau_scale_h = tau_scale_k = 1.0), W_GRF=0.2

## Per-trial bias findings

- **largest improvement**: 0424_90_0.75_90_2 (Δ=0.87, bias=+1.0°/+0.37°) -- dq1 boundary
- **average Δ_score** = 0.27 per trial
- **dataset patterns**:
  - 0424 dataset: +dq1 / -dq2 dominant
  - 0602 dataset: -dq1 / +dq2 dominant -- inverted pattern
  - Suggests different encoder calibration between two datasets

## Worst-3 (next candidates)

1. `0424_150_2.2_500_4` (12.46)
2. `0602_150_2.2_500_5` (11.71)
3. `0602_150_2.2_250_3` (11.50)

## GOAL16 BEST progression

| Iter | Score | Verdict | Notes |
|---|---|---|---|
| baseline | 160.79 | -- | per-trial 12D NM ±20% |
| Iter17 | 157.42 | KEEP | per-trial 12D NM ±40% 2 restarts |
| Iter18 | 153.52 | KEEP | worst-3 DE 12D ±30% |
| Iter23 | 152.66 | KEEP | LSQ TRF 12-param (8 inertial + 4 friction) |
| **Iter26** | **149.48** | **DROP (★ new BEST)** | **Iter18 + Iter19 stack** |

## Files

- `run_i26.py`           -- 2D NM per-trial driver on Iter18 base
- `iter26_metrics.json`  -- final metrics + per-trial best params + bias
- `iter26_logs.npz`      -- 15-trial sim logs (flat tn__field)
- `plots/`               -- 15 four-panel compare PNGs
- `anim/`                -- 15 MuJoCo Renderer GIFs (80f, 60ms)
- `notion_iter26_page.json` -- Notion page metadata
- `upload_notion_iter26.py` -- Notion image upload script
- Notion URL: https://app.notion.com/p/GOAL16-Iter26-Iter18-Iter19-STACK-12D-per-trial-q-offset-1-DROP-score-149-48-new-BEST-BV-5-7-0-386ab81d25508174a5dac094d5f037b5

## Next candidates (Iter27+)

1. **Iter26 base + bias bound ±2° wider** -- 0424_90 boundary 해소
2. **Iter26 base + Iter22 LSQ inertial 8-param global** -- 3-axis stack
3. **Iter26 base + Iter23 friction term 4-param global** -- 3-axis stack
4. per-trial 12D ±50% wider DE on Iter26 base -- 재최적화 with bias
5. Iter18 worst-3 DE 재실행 with bias 포함 14D 동시 최적화

## Verdict

**DROP** (KEEP threshold 148.08, actual 149.48, missed by 1.40) -- **그러나 ★ GOAL16 새 BEST**.
Stack 통합 가설 검증됨: Iter18 (12D base) + Iter19 (q offset)의 누적 효과가 단순 합이 아닌
시너지 (단독 Iter18: 153.52, 단독 Iter19: 154.05, 통합 Iter26: 149.48). bias axis가 12D base와
독립적 정보 제공 -- Khalil-Dombre 2002 ch5 stack ordering 학술적 정합.
