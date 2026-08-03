# -*- coding: utf-8 -*-
"""p23_survey — verify baked tau provenance of 0422 npz caches used by load_31exp.
Compare npz tau_real vs clean xlsx->Paper ahat conversion (RMS ratio)."""
import sys, io
import numpy as np
import pandas as pd
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path("C:/Users/junho/Documents/jump-opt-digital-twin")
sys.path.insert(0, str(REPO / "code/goal22/p19_jump"))
sys.path.insert(0, str(REPO / "code/bench"))
import p19_judge as P

DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data/26_04_22/Torque Control")
JO = Path("C:/Users/junho/Desktop/jump_opt")

CANDS = [
    ("P40_D0.7",  JO / "goal16/cross_validation_modeA/jump_torque_0422/sim_data/jump_torque_0422_P40_D0.7.npz"),
    ("P70_D2",    JO / "goal16/cross_validation_modeA/jump_torque_0422/sim_data/jump_torque_0422_P70_D2.npz"),
    ("P100_D3",   JO / "goal16/cross_validation_modeA/jump_torque_0422/sim_data/jump_torque_0422_P100_D3.npz"),
    ("P70_D2",    JO / "goal18_v5_unified/Iter6/jump_torque_0422/P70_D2/mode_A/sim_data/cycle1.npz"),
]

def clean_tau(sub):
    out = {}
    for j in ("hip", "knee"):
        df = pd.read_excel(DATA / sub / f"{j}.xlsx")
        t = df["Time"].values - df["Time"].values[0]
        tau = P.J.ahat(P.A_PAPER, df["currentTorque"].values.astype(float),
                       df["currentAngleVelocity"].values.astype(float))
        out[j] = (t, tau)
    return out

cache = {}
for sub, npz in CANDS:
    if not npz.exists():
        print(f"[missing] {npz}"); continue
    d = np.load(npz, allow_pickle=True)
    keys = set(d.files)
    print(f"\n=== {sub}  {npz.relative_to(JO)} ===")
    print(f"  keys: {sorted(keys)[:14]}{'...' if len(keys)>14 else ''}")
    if sub not in cache:
        cache[sub] = clean_tau(sub)
    for j, tk in (("hip", "tau1_real"), ("knee", "tau2_real")):
        if tk not in keys:
            print(f"  {tk}: MISSING"); continue
        tau_n = np.asarray(d[tk], float)
        tn = np.asarray(d.get("t_real", d.get("t", np.arange(len(tau_n)) * 0.002)), float)
        tn = tn - tn[0]
        tc, tauc = cache[sub][j]
        tau_c_i = np.interp(tn, tc, tauc)
        m = np.abs(tau_c_i) > 2.0
        if m.sum() < 30:
            m = np.abs(tau_c_i) > 0.5
        # sign flip possible (loader plays -tau); use abs-slope
        slope = float(np.sum(np.abs(tau_n[m]) * np.abs(tau_c_i[m])) / np.sum(tau_c_i[m] ** 2))
        rms_n = float(np.sqrt(np.mean(tau_n ** 2)))
        rms_c = float(np.sqrt(np.mean(tau_c_i ** 2)))
        print(f"  {tk}: rms_npz={rms_n:.3f} rms_cleanPaper={rms_c:.3f} "
              f"rms_ratio={rms_n/rms_c:.4f} slopeLS(|.|)={slope:.4f} n={int(m.sum())}")
