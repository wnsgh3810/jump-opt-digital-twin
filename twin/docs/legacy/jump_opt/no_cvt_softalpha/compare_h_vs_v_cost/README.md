# h-cost vs v-cost comparison

Original source was not modified:

`C:\Users\junho\Desktop\jump_opt\no_cvt_softalpha\jump_no_cvt_softalpha.py`

Comparison folders:

- `h_cost_original`: copied original code, objective unchanged.
- `v_cost_modified`: copied code with only the main objective term changed from `h_base_via_com` to `v_com_z_end`.

Objective definitions:

```python
# h-cost
opti.minimize(-2000.0 * h_base_via_com + 0.1 * J_smooth + 20.0 * J_smooth_v2)

# v-cost
opti.minimize(-2000.0 * v_com_z_end + 0.1 * J_smooth + 20.0 * J_smooth_v2)
```

Main result:

- Both optimizations converged.
- v-cost produced slightly higher takeoff COM vertical velocity: `2.9782 m/s` vs `2.9240 m/s`.
- v-cost also produced slightly higher computed `Base via CoM v_z` jump height: `0.9211 m` vs `0.9056 m`.
- The change is much smaller than in the alpha-only comparison.

See `comparison_summary.csv` for numeric values.
