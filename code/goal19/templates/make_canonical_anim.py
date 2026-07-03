"""Produce v14-canonical animation for a GOAL19 sub with given params.

Uses the LOCKED canonical renderer (goal18_CANONICAL/code/make_anim.py) — never
modifies it. We only produce a canonical npz (t_sim, q1_sim, q2_sim) from our
best-params sim, then hand it to render_sit2stand (handles air + gnd).

canonical q1 = -mj_q1 - pi/2 ; canonical q2 = -mj_q2  (renderer re-applies inverse)
"""
import sys
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

TEMPLATES = Path(__file__).resolve().parent
sys.path.insert(0, str(TEMPLATES))
CANON = Path("C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
sys.path.insert(0, str(CANON))

import sub_sim_iter6v2 as S
import mujoco
from make_anim import render_sit2stand  # LOCKED renderer
import plot_4panel as P4

CANON_XML = CANON / "leg.xml"


def make_anim(ds, sub, out_gif, x=None, kind=None):
    """Render canonical animation for a sub using Phase-N params x (15D or None)."""
    ap = P4.apply_phase1_params(x)
    arm_hip, arm_knee = ap["arm_hip"], ap["arm_knee"]

    is_jump = ds in ("jump_0424", "jump_0602", "jump_position_0421", "jump_torque_0422")
    if is_jump:
        td, log, q1_off, q2_off = P4._run_jump_with_log(ds, sub, arm_hip, arm_knee)
        if log is None:
            print(f"  anim skip {ds}/{sub}: sim None"); return False
        # sim mj frame: hip=idx1, knee=idx2 ; canonical:
        mask = log['t'] >= 0
        t_sim = log['t'][mask]
        q1_canon = (-log['q'][:, 1] - np.pi/2)[mask]
        q2_canon = (-log['q'][:, 2])[mask]
        kind = kind or 'gnd'   # jump base moves — gnd-style base_z compute
        # Jump height: peak base_z (sim) vs measured (real). Keep label short so it fits.
        _h_sim = float(log['q'][:, 0].max())
        _h_real = float(td.get('h_real', 0.0)) if isinstance(td, dict) else 0.0
        _label = f"{sub}  Hsim {_h_sim:.2f} / Hreal {_h_real:.2f} m"
    else:
        from sub_sim_motor_tm import load_sit2stand_cycle, SIT2STAND_GND_ID
        is_gnd = (f"{ds}/{sub}" == SIT2STAND_GND_ID)
        cyc = load_sit2stand_cycle(f"{ds}/{sub}")
        if not cyc:
            print(f"  anim skip {ds}/{sub}: no cyc"); return False
        td = cyc[0]
        q1_off, q2_off = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        xml = S.build_xml_sit2stand_gnd_6d(arm_hip, arm_knee) if is_gnd else S.build_xml_sit2stand_air_6d(arm_hip, arm_knee)
        model = mujoco.MjModel.from_xml_string(xml)
        log = S.run_sit2stand_cycle(model, td, q1_off, q2_off, motor_tm=0.0, is_gnd=is_gnd)
        if log is None:
            print(f"  anim skip {ds}/{sub}: sim None"); return False
        hip, knee = log['hip_idx'], log['knee_idx']
        mask = log['t'] >= 0
        t_sim = log['t'][mask]
        q1_canon = (-log['q'][:, hip] - np.pi/2)[mask]
        q2_canon = (-log['q'][:, knee])[mask]
        kind = kind or ('gnd' if is_gnd else 'air')

    # Save canonical npz
    tmp_npz = Path(out_gif).with_suffix(".canon.npz")
    tmp_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(tmp_npz, t_sim=t_sim, q1_sim=q1_canon, q2_sim=q2_canon)

    _lbl = _label if is_jump else f"{ds}/{sub}"
    try:
        render_sit2stand(str(tmp_npz), str(CANON_XML), str(out_gif),
                         trial_label=_lbl, kind=kind)
    except Exception as e:
        print(f"  anim render err {ds}/{sub}: {e}"); return False
    return Path(out_gif).exists()


if __name__ == "__main__":
    ok = make_anim("jump_0424", "60_0.75_60_2",
                   str(TEMPLATES.parent / "phase1/_anim_smoke.gif"), x=None)
    print("anim smoke:", ok)
