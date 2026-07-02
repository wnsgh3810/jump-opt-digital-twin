"""Generate mode_B via PD sim for jump subs (pseudo mode_B).

For each entry:
  - Load mode_A source npz (has t, q, dq in MuJoCo coords)
  - Use q as pseudo-q_des reference
  - Run PD sim with entry.pd_gains tracking that reference
  - Save cycle00.npz in canonical form (t_sim, q1_sim, q2_sim, base_z_sim,
    q1_des_sim, q2_des_sim, tau1_cmd_sim, tau2_cmd_sim)
  - Render animation via render_sit2stand kind='gnd' (label prefixed "[pseudo]")
  - Copy mode_A plots to mode_B/plots/

Task per user:
  1. Apply coord conversion: mj_q_des already in MuJoCo (mode_A saves MuJoCo state)
  2. Settle 500 steps to initial pose using strong PD.
  3. Then run: ctrl = kp * (q_des - q) + kd * (dq_des - dq).
  4. If PD sim diverges (base falls too fast, or NaN), mark 'failed'.
"""
from __future__ import annotations
import sys, json, shutil, traceback
from pathlib import Path
import numpy as np
import mujoco

V13_ITER6 = Path("C:/Users/junho/Desktop/jump_opt/goal18_v13/Iter6")
XML_PATH = V13_ITER6 / "leg.xml"

sys.path.insert(0, str(V13_ITER6))
from _make_anim_sit2stand import render_sit2stand  # noqa: E402

DT_SIM = 5e-4       # matches xml opt.timestep and mode_A dt
N_SETTLE = 500
SETTLE_KP = 500.0
SETTLE_KD = 10.0
DIVERGE_BASE_M = 5.0


ENTRIES = [
    {"dataset": "jump_0424", "sub": "120_2.2_150_2.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2.2_150_2.5/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2.2, "kp_knee": 150, "kd_knee": 2.5}},
    {"dataset": "jump_0424", "sub": "120_2.2_200_2.8",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2.2_200_2.8/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2.2, "kp_knee": 200, "kd_knee": 2.8}},
    {"dataset": "jump_0424", "sub": "120_2_120_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2_120_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2, "kp_knee": 120, "kd_knee": 2}},
    {"dataset": "jump_0424", "sub": "150_2.2_250_3",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_250_3/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 250, "kd_knee": 3}},
    {"dataset": "jump_0424", "sub": "150_2.2_350_3.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_350_3.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 350, "kd_knee": 3.5}},
    {"dataset": "jump_0424", "sub": "150_2.2_500_4",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_500_4/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 500, "kd_knee": 4}},
    {"dataset": "jump_0424", "sub": "60_0.75_60_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/60_0.75_60_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 0.75, "kp_knee": 60, "kd_knee": 2}},
    {"dataset": "jump_0424", "sub": "60_1.5_60_1.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/60_1.5_60_1.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 1.5, "kp_knee": 60, "kd_knee": 1.5}},
    {"dataset": "jump_0424", "sub": "90_0.75_90_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/90_0.75_90_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 90, "kd_hip": 0.75, "kp_knee": 90, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "120_2_120_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/120_2_120_2/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2, "kp_knee": 120, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "150_2.2_250_3",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/150_2.2_250_3/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 250, "kd_knee": 3}},
    {"dataset": "jump_0602", "sub": "150_2.2_500_5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/150_2.2_500_5/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 500, "kd_knee": 5}},
    {"dataset": "jump_0602", "sub": "60_0.75_60_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18/iter1/jump_0602/60_0.75_60_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 0.75, "kp_knee": 60, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "60_1.5_60_1.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18/iter1/jump_0602/60_1.5_60_1.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 1.5, "kp_knee": 60, "kd_knee": 1.5}},
    {"dataset": "jump_0602", "sub": "90_0.75_90_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/90_0.75_90_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 90, "kd_hip": 0.75, "kp_knee": 90, "kd_knee": 2}},
]


def _to_canonical(mj_q1, mj_q2):
    """MuJoCo hip/knee -> canonical q1_sim/q2_sim."""
    q1c = -(mj_q1 + np.pi / 2.0)
    q2c = -mj_q2
    return q1c, q2c


def run_pd_sim(model, t_A, q_A, dq_A, pd_gains):
    """Run PD sim tracking mode_A trajectory.

    t_A: (N,) mode_A time (canonical, may start negative)
    q_A: (N, 3) mode_A MuJoCo qpos [base_z, mj_q1, mj_q2]
    dq_A: (N, 3) mode_A MuJoCo qvel
    pd_gains: dict with kp_hip, kd_hip, kp_knee, kd_knee

    Returns dict with logs, or None on divergence.
    """
    kp_h = float(pd_gains["kp_hip"])
    kd_h = float(pd_gains["kd_hip"])
    kp_k = float(pd_gains["kp_knee"])
    kd_k = float(pd_gains["kd_knee"])

    dt = float(model.opt.timestep)
    N_track = len(t_A)
    N_total = N_SETTLE + N_track

    # Reference q_des trajectories (MuJoCo hip/knee) and dq_des
    mj_q1_des = q_A[:, 1].astype(float)
    mj_q2_des = q_A[:, 2].astype(float)
    # dq_des: use provided dq_A if available (both from mode_A), else numerical gradient
    mj_dq1_des = dq_A[:, 1].astype(float) if dq_A is not None else np.gradient(mj_q1_des, t_A)
    mj_dq2_des = dq_A[:, 2].astype(float) if dq_A is not None else np.gradient(mj_q2_des, t_A)

    # Initial pose: use mode_A t=0 (or first sample)
    data = mujoco.MjData(model)
    data.qpos[0] = float(q_A[0, 0])
    data.qpos[1] = float(mj_q1_des[0])
    data.qpos[2] = float(mj_q2_des[0])
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    log_t = np.empty(N_total, dtype=float)
    log_q = np.empty((N_total, 3), dtype=float)
    log_dq = np.empty((N_total, 3), dtype=float)
    log_tau_cmd = np.empty((N_total, 2), dtype=float)
    log_tau_applied = np.empty((N_total, 2), dtype=float)
    log_qdes_hip = np.empty(N_total, dtype=float)
    log_qdes_knee = np.empty(N_total, dtype=float)

    # Time base: pre-settle then t_A. Use dt-spaced settle time before t_A[0].
    t_settle = t_A[0] - dt * (N_SETTLE - np.arange(N_SETTLE))
    log_t[:N_SETTLE] = t_settle
    log_t[N_SETTLE:] = t_A

    q_init_hip = float(mj_q1_des[0])
    q_init_knee = float(mj_q2_des[0])

    for k in range(N_total):
        if k < N_SETTLE:
            q_des_h = q_init_hip
            q_des_k = q_init_knee
            dq_des_h = 0.0
            dq_des_k = 0.0
            kp_h_now, kd_h_now = SETTLE_KP, SETTLE_KD
            kp_k_now, kd_k_now = SETTLE_KP, SETTLE_KD
        else:
            j = k - N_SETTLE
            q_des_h = float(mj_q1_des[j])
            q_des_k = float(mj_q2_des[j])
            dq_des_h = float(mj_dq1_des[j])
            dq_des_k = float(mj_dq2_des[j])
            kp_h_now, kd_h_now = kp_h, kd_h
            kp_k_now, kd_k_now = kp_k, kd_k

        tau_h = kp_h_now * (q_des_h - data.qpos[1]) + kd_h_now * (dq_des_h - data.qvel[1])
        tau_k = kp_k_now * (q_des_k - data.qpos[2]) + kd_k_now * (dq_des_k - data.qvel[2])
        data.ctrl[0] = float(tau_h)
        data.ctrl[1] = float(tau_k)

        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None

        log_q[k] = data.qpos
        log_dq[k] = data.qvel
        log_tau_cmd[k] = [tau_h, tau_k]
        log_tau_applied[k] = data.qfrc_actuator[1:3]
        log_qdes_hip[k] = q_des_h
        log_qdes_knee[k] = q_des_k

        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
            return None
        if abs(data.qpos[0]) > DIVERGE_BASE_M:
            return None

    return dict(
        t=log_t, q=log_q, dq=log_dq,
        tau_cmd=log_tau_cmd, tau_applied=log_tau_applied,
        qdes_hip=log_qdes_hip, qdes_knee=log_qdes_knee,
    )


def save_cycle_npz(out_path, log):
    """Save mode_B cycle npz in canonical form for render_sit2stand."""
    q_all = log['q']
    dq_all = log['dq']
    q1_sim, q2_sim = _to_canonical(q_all[:, 1], q_all[:, 2])
    q1_des_sim, q2_des_sim = _to_canonical(log['qdes_hip'], log['qdes_knee'])
    base_z_sim = q_all[:, 0]

    # tau in canonical frame (sign flip)
    tau1_cmd_sim = -log['tau_cmd'][:, 0]
    tau2_cmd_sim = -log['tau_cmd'][:, 1]

    np.savez_compressed(
        str(out_path),
        t_sim=log['t'].astype(float),
        q1_sim=q1_sim.astype(float),
        q2_sim=q2_sim.astype(float),
        base_z_sim=base_z_sim.astype(float),
        q1_des_sim=q1_des_sim.astype(float),
        q2_des_sim=q2_des_sim.astype(float),
        tau1_cmd_sim=tau1_cmd_sim.astype(float),
        tau2_cmd_sim=tau2_cmd_sim.astype(float),
    )


def copy_mode_A_plots(dataset, sub, dst_plots_dir):
    """Best-effort copy of any existing mode_A plots for symmetry."""
    src_dir = V13_ITER6 / dataset / sub / "mode_A" / "plots"
    n_copied = 0
    if src_dir.exists():
        dst_plots_dir.mkdir(parents=True, exist_ok=True)
        for p in src_dir.glob("*.png"):
            shutil.copy2(str(p), str(dst_plots_dir / p.name))
            n_copied += 1
    return n_copied


def process_entry(entry, model):
    dataset = entry["dataset"]
    sub = entry["sub"]
    src_path = Path(entry["mode_A_source"])
    pd_gains = entry["pd_gains"]

    out_root = V13_ITER6 / dataset / sub / "mode_B"
    out_sim = out_root / "sim_data"
    out_anim = out_root / "anims"
    out_plots = out_root / "plots"

    if not src_path.exists():
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"mode_A source missing: {src_path}")

    try:
        d = np.load(str(src_path), allow_pickle=True)
    except Exception as e:
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"load fail: {e!r}")

    keys = set(d.files)
    if not {'t', 'q'}.issubset(keys):
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"missing keys (need t,q); got={sorted(keys)}")

    t_A = np.asarray(d['t'], dtype=float)
    q_A = np.asarray(d['q'], dtype=float)
    dq_A = np.asarray(d['dq'], dtype=float) if 'dq' in keys else None

    if q_A.shape[1] != 3:
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"q.shape={q_A.shape}, expected (N,3)")

    out_sim.mkdir(parents=True, exist_ok=True)
    out_anim.mkdir(parents=True, exist_ok=True)

    log = run_pd_sim(model, t_A, q_A, dq_A, pd_gains)
    if log is None:
        return dict(sub=sub, status="failed", n_cycles=0,
                    notes="PD sim diverged (NaN or |base|>5m)")

    # Final sanity: peak |base_z| within reasonable jump range
    base_peak = float(np.abs(log['q'][:, 0]).max())
    if not np.isfinite(base_peak) or base_peak > 3.0:
        return dict(sub=sub, status="failed", n_cycles=0,
                    notes=f"base_z out of range: peak={base_peak:.2f} m")

    # Save cycle_00.npz (single "cycle" for jump)
    cycle_npz = out_sim / "cycle_00.npz"
    save_cycle_npz(cycle_npz, log)

    # Render animation with render_sit2stand kind='gnd'
    trial_label = f"[pseudo] {dataset} {sub} mode_B kp_h={pd_gains['kp_hip']} kd_h={pd_gains['kd_hip']} kp_k={pd_gains['kp_knee']} kd_k={pd_gains['kd_knee']}"
    gif_out = out_anim / "cycle_00.gif"
    try:
        render_sit2stand(
            canon_npz_path=str(cycle_npz),
            model_xml_path=str(XML_PATH),
            out_gif_path=str(gif_out),
            trial_label=trial_label,
            kind='gnd',
        )
    except Exception as e:
        return dict(sub=sub, status="failed", n_cycles=1,
                    notes=f"render failed: {e!r}")

    n_plots = copy_mode_A_plots(dataset, sub, out_plots)

    # Summary metrics
    q_end = log['q'][-1]
    peak_h = float(log['q'][:, 0].max())

    return dict(
        sub=sub,
        status="ok",
        n_cycles=1,
        notes=(
            f"peak base_z={peak_h*100:.1f}cm, q_end=[{q_end[0]:.3f},{q_end[1]:.3f},{q_end[2]:.3f}], "
            f"n_plots_copied={n_plots}, gif={gif_out.name}"
        ),
    )


def main():
    model = mujoco.MjModel.from_xml_path(str(XML_PATH))
    if abs(model.opt.timestep - DT_SIM) > 1e-9:
        print(f"[WARN] xml dt={model.opt.timestep} differs from DT_SIM={DT_SIM}")

    per_sub = []
    ok = skip = 0
    total_gifs = 0
    for i, entry in enumerate(ENTRIES):
        try:
            r = process_entry(entry, model)
        except Exception as e:
            tb = traceback.format_exc().splitlines()[-3:]
            r = dict(sub=entry["sub"], status="failed", n_cycles=0,
                     notes=f"exception: {e!r} | {' | '.join(tb)}")
        # attach dataset for disambiguation (jump_0424 vs jump_0602 subs overlap)
        r_full = {"dataset": entry["dataset"], **r}
        per_sub.append(r_full)
        if r["status"] == "ok":
            ok += 1
            total_gifs += r["n_cycles"]
        else:
            skip += 1
        print(f"[{i+1:2d}/{len(ENTRIES)}] {entry['dataset']}/{entry['sub']}: "
              f"{r['status']} - {r['notes']}")

    summary = {
        "subs_processed": ok,
        "subs_skipped": skip,
        "total_gifs": total_gifs,
        "per_sub": per_sub,
    }
    out_json = V13_ITER6 / "_mode_B_pd_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                        encoding='utf-8')
    print("\nSummary written to", out_json)
    print(json.dumps({"subs_processed": ok, "subs_skipped": skip,
                      "total_gifs": total_gifs}, indent=2))
    return summary


if __name__ == "__main__":
    main()
