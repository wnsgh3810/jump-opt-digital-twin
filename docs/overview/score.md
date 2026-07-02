# Score Function (unified)

```python
def score_per_exp(sim, real, is_jump):
    Wq, Wdq, Wt, Wh, Wgrf, Wpen = 100, 50, 0, 100 if is_jump else 0, 0.1, 50
    s = Wq*(rmse_q1+rmse_q2) + Wdq*(rmse_dq1+rmse_dq2) + Wt*(rmse_tau1+rmse_tau2)
    s += Wh * abs(h_sim - h_real)
    grf_dev = abs(max(sim.grf) - max(real.grf)) / max(real.grf, 1)
    s += Wgrf * max(0, grf_dev - 0.25)**2 * 10000
    s += Wpen * max(0, sim.foot_pen_max_mm - 2.0)**2
    return s

score_total = sum(score_per_exp(sim_i, real_i, is_jump_i) for i in 31_exp)
```
