"""Unified data loader for GOAL19 - 31 sub-experiments (7 datasets).

Load canonical .npz containing real robot data (q, dq, tau, grf) for each
sub-experiment. Searches multiple candidate paths per sub.
"""
from __future__ import annotations
from pathlib import Path
from typing import NamedTuple, List, Optional
import numpy as np

JUMP_OPT_ROOT = Path("C:/Users/junho/Desktop/jump_opt")


class ExpData(NamedTuple):
    dataset: str
    sub: str
    is_jump: bool
    npz_path: Optional[Path]
    t: Optional[np.ndarray] = None
    q1: Optional[np.ndarray] = None
    q2: Optional[np.ndarray] = None
    dq1: Optional[np.ndarray] = None
    dq2: Optional[np.ndarray] = None
    tau1: Optional[np.ndarray] = None
    tau2: Optional[np.ndarray] = None
    grf: Optional[np.ndarray] = None
    h_real: float = 0.0


# Registry: (dataset, sub, is_jump). Path search is dynamic.
REGISTRY = [
    ("sit2stand_air_0319", "ROOT", False),
    ("sit2stand_gnd_0319", "ROOT", False),
    ("sit2stand_0324", "P10_D0", False),
    ("sit2stand_0324", "P10_D1", False),
    ("sit2stand_0324", "P20_D1", False),
    ("sit2stand_0324", "P30_D1", False),
    ("sit2stand_0324", "P60_D1.5_P60_D2", False),
    ("jump_position_0421", "P60_D0.75_P60_D2", True),
    ("jump_position_0421", "P70_D0.75_P70_D2", True),
    ("jump_position_0421", "P80_D0.75_P80_D2", True),
    ("jump_position_0421", "P90_D0.75_P90_D2", True),
    ("jump_position_0421", "P100_D0.75_P100_D2", True),
    ("jump_position_0421", "P200_D1.5_P200_D4", True),
    ("jump_torque_0422", "P40_D0.7", True),
    ("jump_torque_0422", "P70_D2", True),
    ("jump_torque_0422", "P100_D3", True),
    ("jump_0424", "60_0.75_60_2", True),
    ("jump_0424", "60_1.5_60_1.5", True),
    ("jump_0424", "90_0.75_90_2", True),
    ("jump_0424", "120_2_120_2", True),
    ("jump_0424", "120_2.2_150_2.5", True),
    ("jump_0424", "120_2.2_200_2.8", True),
    ("jump_0424", "150_2.2_250_3", True),
    ("jump_0424", "150_2.2_350_3.5", True),
    ("jump_0424", "150_2.2_500_4", True),
    ("jump_0602", "60_0.75_60_2", True),
    ("jump_0602", "60_1.5_60_1.5", True),
    ("jump_0602", "90_0.75_90_2", True),
    ("jump_0602", "120_2_120_2", True),
    ("jump_0602", "150_2.2_250_3", True),
    ("jump_0602", "150_2.2_500_5", True),
]

assert len(REGISTRY) == 31, f"expected 31, got {len(REGISTRY)}"


# Required canonical keys for a "loadable" npz
REQ_KEYS_FULL = {"t_real", "q1_real", "q2_real", "dq1_real", "dq2_real",
                 "tau1_real", "tau2_real"}


def _candidate_paths(dataset: str, sub: str) -> List[Path]:
    """Return ordered list of candidate .npz files for this (dataset, sub)."""
    r = JUMP_OPT_ROOT
    if dataset == "sit2stand_air_0319":
        return [
            r / "goal12/xval_v2/sit2stand_air_0319/ROOT/cycle_final.npz",
            r / "goal12/xval_v2/sit2stand_air_0319/ROOT/cycle_verified.npz",
            r / "goal16/cross_validation_motion/sit2stand_air_0319/cycle_final.npz",
        ]
    if dataset == "sit2stand_gnd_0319":
        base = r / "goal16/cross_validation_clean/sit2stand_gnd_0319"
        return list((base / "mode_A/sim_data").glob("cycle*.npz")) + [
            base / "cycle_final.npz", base / "cycle_verified.npz",
            r / "goal12/xval_v2/sit2stand_gnd_0319/ROOT/cycle_final.npz",
        ]
    if dataset == "sit2stand_0324":
        base = r / f"goal16/cross_validation_clean/sit2stand_0324/{sub}"
        return [base / "cycle_final.npz", base / "cycle_verified.npz"] + list((base / "mode_A/sim_data").glob("cycle*.npz"))
    # jumps
    cands: List[Path] = []
    # iter0R (has full canonical for some subs, e.g. P80_D0.75_P80_D2)
    cands.append(r / f"goal18/iter0R/{dataset}/{sub}/sim_data/{dataset}_{sub}_iter0R_modeA.npz")
    for root in ["goal18_v5_unified/Iter6", "goal18_v4/Iter6", "goal18/iter1"]:
        base = r / root / dataset / sub
        cands += [base / "mode_A/sim_data/cycle01.npz",
                  base / "sim_data/run_log.npz",
                  base / "sim_data/iter6_sim.npz",
                  base / "sim_data/cycle_final.npz",
                  base / "sim_data/cycle01.npz"]
        cands += list((base / "sim_data").glob("cycle*.npz")) if (base / "sim_data").exists() else []
        cands += list((base / "mode_A/sim_data").glob("cycle*.npz")) if (base / "mode_A/sim_data").exists() else []
    # goal16 cross_validation_modeA (jump_torque_0422 P40/P100)
    sub_us = sub.replace(".", "p")
    cands += [
        r / f"goal16/cross_validation_modeA/{dataset}/sim_data/{dataset}_{sub}.npz",
        r / f"goal15/xval_v2/{dataset}/{sub}/sim_data/sim_{sub_us}.npz",
        r / f"goal15/cross_validation/{dataset}/sim_data/sim_{sub_us}.npz",
        r / f"goal14/xval_v2/{dataset}/{sub}/sim_data/logs.npz",
        r / f"goal12/xval_v2/{dataset}/{sub}/sim_data/logs.npz",
    ]
    return cands


def _load_npz(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        d = np.load(path, allow_pickle=True)
        return {k: np.asarray(d[k]) for k in d.files}
    except Exception:
        return None


def list_experiments():
    return list(REGISTRY)


def load_experiment(dataset: str, sub: str) -> ExpData:
    entry = next((r for r in REGISTRY if r[0] == dataset and r[1] == sub), None)
    if entry is None:
        raise ValueError(f"unknown experiment: {dataset}/{sub}")
    _, _, is_jump = entry
    # Try candidates in order, prefer full schema
    best_path = None
    best_d = None
    best_score = -1
    for p in _candidate_paths(dataset, sub):
        d = _load_npz(p)
        if d is None:
            continue
        keys = set(d.keys())
        score = 0
        if "q1_real" in keys: score += 10
        if "tau1_real" in keys: score += 10
        if "dq1_real" in keys: score += 5
        if "grf_real" in keys or "grf_z_real" in keys: score += 5
        if "t_real" in keys or "t" in keys: score += 2
        if score > best_score:
            best_score = score; best_d = d; best_path = p
            if score >= 30:  # full schema found
                break
    if best_d is None:
        return ExpData(dataset=dataset, sub=sub, is_jump=is_jump, npz_path=None)

    d = best_d
    t = d.get("t_real", d.get("t", np.zeros(0)))
    if t.size == 0:
        return ExpData(dataset=dataset, sub=sub, is_jump=is_jump, npz_path=best_path)
    q1 = d.get("q1_real", d.get("q1", np.zeros_like(t)))
    q2 = d.get("q2_real", d.get("q2", np.zeros_like(t)))
    dq1 = d.get("dq1_real", d.get("dq1", np.gradient(q1, t) if len(t) > 1 else np.zeros_like(t)))
    dq2 = d.get("dq2_real", d.get("dq2", np.gradient(q2, t) if len(t) > 1 else np.zeros_like(t)))
    tau1 = d.get("tau1_real_motor", d.get("tau1_real", d.get("tau1", np.zeros_like(t))))
    tau2 = d.get("tau2_real_motor", d.get("tau2_real", d.get("tau2", np.zeros_like(t))))
    grf = d.get("grf_real", d.get("grf_z_real", d.get("grf", d.get("grf_z", np.zeros_like(t)))))
    h_real = _H_REAL.get(f"{dataset}/{sub}", 0.0)
    return ExpData(
        dataset=dataset, sub=sub, is_jump=is_jump, npz_path=best_path,
        t=np.asarray(t), q1=np.asarray(q1), q2=np.asarray(q2),
        dq1=np.asarray(dq1), dq2=np.asarray(dq2),
        tau1=np.asarray(tau1), tau2=np.asarray(tau2),
        grf=np.asarray(grf), h_real=h_real,
    )


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
}


if __name__ == "__main__":
    import json, sys
    print(f"Registry has {len(REGISTRY)} experiments")
    ok_full, ok_partial, missing = [], [], []
    summary = []
    for ds, sub, is_jump in list_experiments():
        d = load_experiment(ds, sub)
        entry = dict(dataset=ds, sub=sub, is_jump=is_jump, npz=str(d.npz_path) if d.npz_path else None,
                     n=len(d.t) if d.t is not None else 0, h_real=d.h_real)
        if d.t is None or d.t.size == 0:
            missing.append(f"{ds}/{sub}")
            print(f"  [MISS] {ds}/{sub}")
        else:
            has_tau = np.any(d.tau1 != 0) or np.any(d.tau2 != 0)
            has_grf = np.any(d.grf != 0)
            entry["has_tau"] = bool(has_tau); entry["has_grf"] = bool(has_grf)
            if has_tau:
                ok_full.append(f"{ds}/{sub}")
                print(f"  [FULL] {ds}/{sub}: n={len(d.t)}, tau={has_tau}, grf={has_grf}, h={d.h_real}")
            else:
                ok_partial.append(f"{ds}/{sub}")
                print(f"  [PARTIAL] {ds}/{sub}: n={len(d.t)}, tau={has_tau}, grf={has_grf}, h={d.h_real}")
        summary.append(entry)
    print(f"\nFULL: {len(ok_full)}, PARTIAL: {len(ok_partial)}, MISSING: {len(missing)} / {len(REGISTRY)}")
    out = Path(__file__).parent / "load_status.json"
    out.write_text(json.dumps(dict(full=ok_full, partial=ok_partial, missing=missing,
                                    total=len(REGISTRY), summary=summary), indent=2))
    print(f"Written: {out}")
