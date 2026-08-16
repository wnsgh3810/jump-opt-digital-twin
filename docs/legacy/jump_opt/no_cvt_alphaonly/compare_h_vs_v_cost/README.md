# h-cost vs v-cost comparison

Original source was not modified:

`C:\Users\junho\Desktop\jump_opt\no_cvt_alphaonly\jump_no_cvt_alphaonly.py`

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
- v-cost produced higher takeoff COM vertical velocity: `2.8163 m/s` vs `2.5670 m/s`.
- v-cost also produced higher computed `Base via CoM v_z` jump height: `0.8612 m` vs `0.7982 m`.
- v-cost used more output/input energy and higher peak GRF.

See `comparison_summary.csv` for numeric values.
