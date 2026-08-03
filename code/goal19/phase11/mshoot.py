"""GOAL19 Phase 11q — MULTIPLE-SHOOTING evaluation harness (Mode A principle, fixed metric).

User direction (2026-07-05): KEEP Mode A (pure torque replay, no PD, no gains — PD absorbs
model error and effective gains are uncertain, cf. GOAL6 alpha_kp=0.19). Fix the METRIC:
full-trajectory open-loop replay is divergence-contaminated (residual double-integrates,
score measures accumulated drift not local model quality, pushed fits to non-physical
absorbers, killed external-loop datasets).

Multiple shooting: split each trial into short windows. Each window starts at the MEASURED
state (base_z/vz from foot-planted FK during stance — geometry is LOCKED so FK is
param-independent and cached). Replay tau_real open-loop inside the window. Score q/dq
RMSE over the window. Windows may extend past takeoff (captures the whip transition).

Datasets (user 2026-07-05): all jumps EXCEPT jump_torque_0422 (external-PD-loop era;
regression showed inconsistent torque, R2 0.33) + sit2stand_gnd.
=> jump_position_0421 (6) + jump_0424 (9) + jump_0602 (6) + sit2stand_gnd cycles.
Validation (held out from fitting): full-trajectory Mode A replay + camera h + LODO.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco
from scipy.signal import savgol_filter

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4

W_Q, W_DQ = 100.0, 50.0
W_JUMP, STR_JUMP = 0.10, 0.05     # jump window / stride [s]
W_S2S, STR_S2S = 0.25, 0.15      # sit2stand window / stride [s]
N_S2S_CYC = 3

LOADERS = {"jump_position_0421": S.load_jump_position,
           "jump_0424": S.load_jump_0424,
           "jump_0602": S.load_jump_0602}

# ── March jumps (user 2026-07-05: include; not in canonical 31-exp) ──────────
# Same file layout as 0424 (hip.xlsx/knee.xlsx/GRF.xlsx/Real Data.txt) => reuse load_one_trial.
DATA_ROOT = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
MARCH = [
    # jump_0319 NO_TR_JUMP EXCLUDED (user 2026-07-05): confirmed data outlier — fit spent
    # ~16% of score on it yet q2 stayed 0.33 (10x others); different posture; h_real unparseable.
    ("jump_0324", DATA_ROOT / "26_03_24/Jump/Jump_No_Tr", ["P40_D0.7", "P60_D1.5", "P100_D3"]),
]


def load_march(tdir, trial):
    sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal12/data_loaders")
    from load_combined_15trial import load_one_trial
    td = load_one_trial(Path(tdir), trial, fallback_h=0.85)
    if float(td["h_real"]) > 3.0:      # cm logged instead of m (0324 P100_D3: 74.00)
        td["h_real"] = np.float64(float(td["h_real"]) / 100.0)
    n = min(len(td[k]) for k in ("t", "q1", "q2", "dq1", "dq2", "tau1_real", "tau2_real", "grf_z"))
    for k in ("t", "q1", "q2", "dq1", "dq2", "tau1_real", "tau2_real", "grf_z"):
        td[k] = td[k][:n]              # P100_D3: grf 158 vs motor 157
    return td

_PREP = {}   # cache: key -> prepped trial dict (FK base, windows) — param-independent


def _prep_arrays(td, model, is_jump):
    """FK base trajectory + window start indices. Geometry locked => cache-safe."""
    d = mujoco.MjData(model)
    fg = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    t = np.asarray(td["t"]); n = len(t)
    q1m = -np.asarray(td["q1"]) - np.pi / 2
    q2m = -np.asarray(td["q2"])
    dq1m = savgol_filter(-np.asarray(td["dq1"]), 11, 3)
    dq2m = savgol_filter(-np.asarray(td["dq2"]), 11, 3)
    tau_h = -np.asarray(td["tau1_real"]); tau_k = -np.asarray(td["tau2_real"])
    bz = np.zeros(n)
    for i in range(n):
        d.qpos[:] = [1.0, q1m[i], q2m[i]]
        mujoco.mj_forward(model, d)
        bz[i] = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    bz = savgol_filter(bz, 11, 3)
    vbz = np.gradient(bz, t)
    grf = np.asarray(td.get("grf_z", np.full(n, 100.0)))
    grf = savgol_filter(grf, 11, 3) if len(grf) == n else np.full(n, 100.0)
    stance = np.where(grf > 15)[0]
    if len(stance) < 5:
        stance = np.arange(n)
    W = W_JUMP if is_jump else W_S2S
    stride = STR_JUMP if is_jump else STR_S2S
    t_lo, t_hi = t[stance[0]], t[stance[-1]]
    starts = []
    t0 = t_lo
    while t0 <= t_hi - 1e-9:
        i0 = int(np.argmin(np.abs(t - t0)))
        if t[-1] - t[i0] > 0.5 * W:
            starts.append(i0)
        t0 += stride
    return dict(t=t, q1m=q1m, q2m=q2m, dq1m=dq1m, dq2m=dq2m,
                tau_h=tau_h, tau_k=tau_k, bz=bz, vbz=vbz, starts=starts, W=W)


def get_prep(key, td, model, is_jump):
    if key not in _PREP:
        _PREP[key] = _prep_arrays(td, model, is_jump)
    return _PREP[key]


def eval_windows(model, pp):
    """Replay each window open-loop; return list of per-window rmse dicts."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0]]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0]]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1 = np.empty(nst); q2 = np.empty(nst)
        dq1 = np.empty(nst); dq2 = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1[k] = d.qpos[1]; q2[k] = d.qpos[2]
            dq1[k] = d.qvel[1]; dq2[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))  # crash penalty
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1, pp["q1m"]), rq2=r(q2, pp["q2m"]),
                        rdq1=r(dq1, pp["dq1m"]), rdq2=r(dq2, pp["dq2m"])))
    return out


def window_score(wins):
    return sum(W_Q * (w["rq1"] + w["rq2"]) + W_DQ * (w["rdq1"] + w["rdq2"]) for w in wins)


def load_s2s_cycles():
    from sub_sim_motor_tm import load_sit2stand_cycle, SIT2STAND_GND_ID
    cyc = load_sit2stand_cycle(SIT2STAND_GND_ID)
    return cyc[:N_S2S_CYC], SIT2STAND_GND_ID


def evaluate_all(arm_hip, arm_knee):
    """Window score over all included datasets with CURRENT S-module params."""
    total = 0.0
    per_ds = {}
    xml_j = S.build_xml_jump_6d(arm_hip, arm_knee)
    mj = mujoco.MjModel.from_xml_string(xml_j)
    for ds, loader in LOADERS.items():
        from load_31exp import list_experiments
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for sub in subs:
            td = loader(sub)
            pp = get_prep((ds, sub), td, mj, True)
            wins = eval_windows(mj, pp)
            sc += window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc
        per_ds[ds] = dict(score=sc, n=nw, mean=acc / max(nw, 1))
    # March jumps
    for ds, tdir, subs in MARCH:
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for sub in subs:
            try:
                td = load_march(tdir, sub)
            except Exception:
                continue
            pp = get_prep((ds, sub), td, mj, True)
            wins = eval_windows(mj, pp)
            sc += window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc
        per_ds[ds] = dict(score=sc, n=nw, mean=acc / max(nw, 1))
    # sit2stand gnd
    try:
        cycles, gid = load_s2s_cycles()
        xml_s = S.build_xml_sit2stand_gnd_6d(arm_hip, arm_knee)
        ms = mujoco.MjModel.from_xml_string(xml_s)
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for ci, td in enumerate(cycles):
            pp = get_prep(("s2s_gnd", ci), td, ms, False)
            wins = eval_windows(ms, pp)
            sc += window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc
        per_ds["sit2stand_gnd"] = dict(score=sc, n=nw, mean=acc / max(nw, 1))
    except Exception as e:
        per_ds["sit2stand_gnd"] = dict(score=0.0, n=0, mean=np.zeros(4), err=str(e))
    return total, per_ds


if __name__ == "__main__":
    from apply_final_and_regen import apply_final
    ap = apply_final()
    total, per = evaluate_all(ap["arm_hip"], ap["arm_knee"])
    print(f"MULTIPLE-SHOOTING baseline (final model)  total={total:.0f}")
    print(f"{'dataset':<22}{'score':>8}{'#win':>6}{'q1':>8}{'q2':>8}{'dq1':>7}{'dq2':>7}")
    for ds, v in per.items():
        m = v["mean"]
        print(f"{ds:<22}{v['score']:>8.0f}{v['n']:>6}{m[0]:>8.4f}{m[1]:>8.4f}{m[2]:>7.2f}{m[3]:>7.2f}")
