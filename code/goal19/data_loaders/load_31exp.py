"""Unified data loader for GOAL19 — 31 sub-experiments (7 datasets).

Load canonical .npz containing real robot data (q, dq, tau, grf) for each
sub-experiment. Data source paths point to jump_opt/goal18_v13 or goal16.
"""
from __future__ import annotations
from pathlib import Path
from typing import NamedTuple
import numpy as np

# Root of canonical data (Desktop/jump_opt/)
JUMP_OPT_ROOT = Path("C:/Users/junho/Desktop/jump_opt")


class ExpData(NamedTuple):
    """Real robot data for one sub-experiment."""
    dataset: str          # "jump_0424", "sit2stand_0324", ...
    sub: str              # "60_0.75_60_2", "P20_D1", "ROOT", ...
    is_jump: bool
    npz_path: Path
    # (below filled by load())
    t: np.ndarray = None          # time [s]
    q1: np.ndarray = None         # hip angle [rad] (real frame)
    q2: np.ndarray = None         # knee angle [rad] (real frame)
    dq1: np.ndarray = None
    dq2: np.ndarray = None
    tau1: np.ndarray = None       # motor torque [Nm] (paper_a_hat converted)
    tau2: np.ndarray = None
    grf: np.ndarray = None        # ground reaction force [N]
    h_real: float = 0.0           # actual jump height [m] (0 for sit2stand)


# ── Registry: 31 sub-experiments and their canonical source paths ──────
# Structure: (dataset, sub_folder, sub_key, is_jump)
REGISTRY = [
    # sit2stand_air_0319 (1)
    ("sit2stand_air_0319", "ROOT", False, JUMP_OPT_ROOT / "goal16/cross_validation_motion/sit2stand_air_0319/mode_A/sim_data"),
    # sit2stand_gnd_0319 (1) — use clean (has proper both modes)
    ("sit2stand_gnd_0319", "ROOT", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_gnd_0319/mode_A/sim_data"),
    # sit2stand_0324 (4)
    ("sit2stand_0324", "P10_D0", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_0324/P10_D0/mode_A/sim_data"),
    ("sit2stand_0324", "P10_D1", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_0324/P10_D1/mode_A/sim_data"),
    ("sit2stand_0324", "P20_D1", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_0324/P20_D1/mode_A/sim_data"),
    ("sit2stand_0324", "P30_D1", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_0324/P30_D1/mode_A/sim_data"),
    ("sit2stand_0324", "P60_D1.5_P60_D2", False, JUMP_OPT_ROOT / "goal16/cross_validation_clean/sit2stand_0324/P60_D1.5_P60_D2/mode_A/sim_data"),
    # jump_position_0421 (6) — v4 has individual sub folders
    ("jump_position_0421", "P60_D0.75_P60_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P60_D0.75_P60_D2/sim_data"),
    ("jump_position_0421", "P70_D0.75_P70_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P70_D0.75_P70_D2/sim_data"),
    ("jump_position_0421", "P80_D0.75_P80_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P80_D0.75_P80_D2/sim_data"),
    ("jump_position_0421", "P90_D0.75_P90_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P90_D0.75_P90_D2/sim_data"),
    ("jump_position_0421", "P100_D0.75_P100_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P100_D0.75_P100_D2/sim_data"),
    ("jump_position_0421", "P200_D1.5_P200_D4", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_position_0421/P200_D1.5_P200_D4/sim_data"),
    # jump_torque_0422 (3)
    ("jump_torque_0422", "P40_D0.7", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_torque_0422/P40_D0.7/sim_data"),
    ("jump_torque_0422", "P70_D2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_torque_0422/P70_D2/sim_data"),
    ("jump_torque_0422", "P100_D3", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_torque_0422/P100_D3/sim_data"),
    # jump_0424 (9)
    ("jump_0424", "60_0.75_60_2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/60_0.75_60_2/sim_data"),
    ("jump_0424", "60_1.5_60_1.5", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/60_1.5_60_1.5/sim_data"),
    ("jump_0424", "90_0.75_90_2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/90_0.75_90_2/sim_data"),
    ("jump_0424", "120_2_120_2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/120_2_120_2/sim_data"),
    ("jump_0424", "120_2.2_150_2.5", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/120_2.2_150_2.5/sim_data"),
    ("jump_0424", "120_2.2_200_2.8", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/120_2.2_200_2.8/sim_data"),
    ("jump_0424", "150_2.2_250_3", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/150_2.2_250_3/sim_data"),
    ("jump_0424", "150_2.2_350_3.5", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/150_2.2_350_3.5/sim_data"),
    ("jump_0424", "150_2.2_500_4", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0424/150_2.2_500_4/sim_data"),
    # jump_0602 (6)
    ("jump_0602", "60_0.75_60_2", True, JUMP_OPT_ROOT / "goal18/iter1/jump_0602/60_0.75_60_2/sim_data"),
    ("jump_0602", "60_1.5_60_1.5", True, JUMP_OPT_ROOT / "goal18/iter1/jump_0602/60_1.5_60_1.5/sim_data"),
    ("jump_0602", "90_0.75_90_2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0602/90_0.75_90_2/sim_data"),
    ("jump_0602", "120_2_120_2", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0602/120_2_120_2/sim_data"),
    ("jump_0602", "150_2.2_250_3", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0602/150_2.2_250_3/sim_data"),
    ("jump_0602", "150_2.2_500_5", True, JUMP_OPT_ROOT / "goal18_v4/Iter6/jump_0602/150_2.2_500_5/sim_data"),
]

assert len(REGISTRY) == 31, f"expected 31, got {len(REGISTRY)}"


def list_experiments():
    """Return list of (dataset, sub, is_jump) for all 31 experiments."""
    return [(r[0], r[1], r[2]) for r in REGISTRY]


def load_experiment(dataset: str, sub: str) -> ExpData:
    """Load a single sub-experiment's canonical data."""
    entry = next((r for r in REGISTRY if r[0] == dataset and r[1] == sub), None)
    if entry is None:
        raise ValueError(f"unknown experiment: {dataset}/{sub}")
    _, _, is_jump, sim_dir = entry
    if not sim_dir.exists():
        return ExpData(dataset=dataset, sub=sub, is_jump=is_jump, npz_path=sim_dir)
    npz_files = sorted(sim_dir.glob("*.npz"))
    if not npz_files:
        return ExpData(dataset=dataset, sub=sub, is_jump=is_jump, npz_path=sim_dir)
    npz_path = npz_files[0]
    d = np.load(npz_path, allow_pickle=True)
    keys = set(d.files)
    # Determine schema: real fields (t_real, q1_real, q2_real, tau*_real, grf_real) or 'raw' (t, q, ...)
    t = np.asarray(d.get('t_real', d.get('t', [])))
    q1 = np.asarray(d.get('q1_real', d.get('q1', [])))
    q2 = np.asarray(d.get('q2_real', d.get('q2', [])))
    dq1 = np.asarray(d.get('dq1_real', d.get('dq1', np.gradient(q1, t) if len(t) > 1 else [])))
    dq2 = np.asarray(d.get('dq2_real', d.get('dq2', np.gradient(q2, t) if len(t) > 1 else [])))
    # tau: paper_a_hat converted preferred
    tau1 = np.asarray(d.get('tau1_real_motor', d.get('tau1_real', d.get('tau1', []))))
    tau2 = np.asarray(d.get('tau2_real_motor', d.get('tau2_real', d.get('tau2', []))))
    grf = np.asarray(d.get('grf_real', d.get('grf', d.get('grf_z', np.zeros_like(t)))))
    # h_real: from external table
    h_real = _H_REAL.get(f"{dataset}/{sub}", 0.0)
    return ExpData(
        dataset=dataset, sub=sub, is_jump=is_jump, npz_path=npz_path,
        t=t, q1=q1, q2=q2, dq1=dq1, dq2=dq2, tau1=tau1, tau2=tau2, grf=grf, h_real=h_real,
    )


# Real jump heights (m) — from Real Data.txt files across dates
_H_REAL = {
    "jump_position_0421/P60_D0.75_P60_D2": 0.90,
    "jump_position_0421/P70_D0.75_P70_D2": 0.90,
    "jump_position_0421/P80_D0.75_P80_D2": 0.85,
    "jump_position_0421/P90_D0.75_P90_D2": 0.85,
    "jump_position_0421/P100_D0.75_P100_D2": 0.80,
    "jump_position_0421/P200_D1.5_P200_D4": 0.75,
    "jump_torque_0422/P40_D0.7": 0.90,
    "jump_torque_0422/P70_D2": 0.85,
    "jump_torque_0422/P100_D3": 0.80,
    "jump_0424/60_0.75_60_2": 0.90,
    "jump_0424/60_1.5_60_1.5": 0.91,
    "jump_0424/90_0.75_90_2": 0.894,
    "jump_0424/120_2_120_2": 0.84,
    "jump_0424/120_2.2_150_2.5": 0.81,
    "jump_0424/120_2.2_200_2.8": 0.795,
    "jump_0424/150_2.2_250_3": 0.77,
    "jump_0424/150_2.2_350_3.5": 0.77,
    "jump_0424/150_2.2_500_4": 0.775,
    "jump_0602/60_0.75_60_2": 0.94,
    "jump_0602/60_1.5_60_1.5": 0.96,
    "jump_0602/90_0.75_90_2": 0.98,
    "jump_0602/120_2_120_2": 0.94,
    "jump_0602/150_2.2_250_3": 0.90,
    "jump_0602/150_2.2_500_5": 0.80,
    # sit2stand: 0
}


if __name__ == "__main__":
    print(f"Registry has {len(REGISTRY)} experiments")
    ok = 0
    missing = []
    for ds, sub, is_jump in list_experiments():
        d = load_experiment(ds, sub)
        if d.t is not None and len(d.t) > 0:
            ok += 1
            print(f"  ✅ {ds}/{sub}: {len(d.t)} samples, h_real={d.h_real}")
        else:
            missing.append(f"{ds}/{sub}")
            print(f"  ❌ {ds}/{sub}: MISSING at {d.npz_path}")
    print(f"\n{ok}/{len(REGISTRY)} loaded successfully")
    if missing:
        print(f"Missing: {missing}")
