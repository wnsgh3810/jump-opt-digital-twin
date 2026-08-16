"""GOAL21 P2 — stance ENERGY-form regression (jump 0424/0602 + s2s_gnd, rail friction).

Why energy form: during stance the actual motion satisfies the foot-contact
constraint, so constraint forces are WORKLESS -> they vanish from the energy
balance without needing GRF or any projection algebra. No ddq anywhere.

System (mujoco frame): base height z on vertical rail, hip q1, knee q2.
  T = 1/2 Mtot zd^2 + 1/2 A q1d^2 + 1/2 D ph_d^2 + B q1d ph_d c2 + 1/2 E q2d^2
      + k1 zd q1d s1 + k2 zd ph_d s_ph            (ph = q1+q2)
  V = g (Mtot z - k1 cos q1 - k2 cos ph)
Energy balance over window [a,b]:
  Delta(T+V) = int(tau1 q1d + tau2 q2d) dt  - fv1 int q1d^2 - fc1 int|q1d|
               - fv2 int q2d^2 - fc2 int|q2d| - f_rail int|zd|
theta = [A, D, B, E, k1, k2, Mtot, fv1, fc1, fv2, fc2, f_rail]  — all linear.

Step 1: synthetic self-check — simulate the serial jump model (known params,
friction off), verify the energy identity holds (residual << signal).
Step 2: LS on real stance windows; compare theta vs CAD vs air-regression
(air gave transmission-shrunk params; stance at high torque should land near CAD
if the torque path is ~fully engaged in the dynamic regime).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
from load_31exp import list_experiments
import g21_air_regressor as R

G = 9.81
L1 = 0.25
BD = R.BD
NAMES = ["A", "D", "B", "E", "k1", "k2", "Mtot", "fv1", "fc1", "fv2", "fc2", "f_rail"]
TRAP = np.trapezoid if hasattr(np, "trapezoid") else np.trapz


def theta_stance_from_model(m):
    th_air = R.theta_from_model(m)             # A D B E k1 k2 (+frictions)
    Mtot = float(np.sum(m.body_mass))
    return np.concatenate([th_air[:6], [Mtot], [S.FV_HIP, S.FC_HIP, S.FV_KNEE, S.FC_KNEE, 0.0]])


def energy_row(t, z, zd, q1, q2, dq1, dq2, tau1, tau2, ia, ib):
    sl = slice(ia, ib + 1)
    tt = t[sl]
    ph = q1[sl] + q2[sl]; phd = dq1[sl] + dq2[sl]
    s1 = np.sin(q1[sl]); sph = np.sin(ph); c2 = np.cos(q2[sl])
    def dlt(f):
        return f[-1] - f[0]
    col_A = dlt(0.5 * dq1[sl] ** 2)
    col_D = dlt(0.5 * phd ** 2)
    col_B = dlt(dq1[sl] * phd * c2)
    col_E = dlt(0.5 * dq2[sl] ** 2)
    col_k1 = dlt(zd[sl] * dq1[sl] * s1) - G * dlt(np.cos(q1[sl]))
    col_k2 = dlt(zd[sl] * phd * sph) - G * dlt(np.cos(ph))
    col_M = dlt(0.5 * zd[sl] ** 2) + G * dlt(z[sl])
    col_fv1 = TRAP(dq1[sl] ** 2, tt); col_fc1 = TRAP(np.abs(dq1[sl]), tt)
    col_fv2 = TRAP(dq2[sl] ** 2, tt); col_fc2 = TRAP(np.abs(dq2[sl]), tt)
    col_rail = TRAP(np.abs(zd[sl]), tt)
    y = TRAP(tau1[sl] * dq1[sl] + tau2[sl] * dq2[sl], tt)
    return [col_A, col_D, col_B, col_E, col_k1, col_k2, col_M,
            col_fv1, col_fc1, col_fv2, col_fc2, col_rail], y


def synthetic_check():
    """Flight-state mass-matrix comparison (contact-free): validates T structure."""
    S.FV_HIP = 0.0; S.FV_KNEE = 0.0; S.FC_HIP = 0.0; S.FC_KNEE = 0.0
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = 0.0
    m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, BD["arm_knee"]))
    d = mujoco.MjData(m)
    th = theta_stance_from_model(m)
    A, D, B, Ee, k1, k2, Mtot = th[:7]
    rng = np.random.default_rng(5)
    err = 0.0
    for _ in range(200):
        q = rng.uniform(-2.5, 2.5, 2)
        d.qpos[:] = [rng.uniform(1, 2), q[0], q[1]]; d.qvel[:] = 0
        mujoco.mj_forward(m, d)
        Mfull = np.zeros((3, 3)); mujoco.mj_fullM(m, Mfull, d.qM)
        s1 = np.sin(q[0]); ph = q[0] + q[1]; sph = np.sin(ph); c2 = np.cos(q[1])
        Ma = np.array([[Mtot, k1 * s1 + k2 * sph, k2 * sph],
                       [k1 * s1 + k2 * sph, A + D + 2 * B * c2, D + B * c2],
                       [k2 * sph, D + B * c2, D + Ee]])
        err = max(err, np.abs(Mfull - Ma).max())
        gv = np.array([G * Mtot, G * (k1 * s1 + k2 * sph), G * k2 * sph])
        err = max(err, np.abs(d.qfrc_bias - gv).max())
    print(f"[check] flight M & dV/dq max err = {err:.2e}")
    return err < 1e-9


def _old_synthetic_check():
    """(retired) energy identity with contact — invalid: soft contact does work."""
    S.FV_HIP = 0.0; S.FV_KNEE = 0.0; S.FC_HIP = 0.0; S.FC_KNEE = 0.0
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = 0.0
    m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, BD["arm_knee"]))
    d = mujoco.MjData(m)
    th = theta_stance_from_model(m)
    q1m0, q2m0 = S.Q1_MU_INIT, S.Q2_MU_INIT
    d.qpos[:] = [S.BASE_Z_INIT, q1m0, q2m0]; d.qvel[:] = 0
    mujoco.mj_forward(m, d)
    dt = m.opt.timestep
    N = int(1.0 / dt)
    log = np.zeros((N, 8))
    for k in range(N):
        tc = k * dt
        if tc < 0.4:
            th_c = 60 * (q1m0 - d.qpos[1]) - 2 * d.qvel[1]
            tk_c = 60 * (q2m0 - d.qpos[2]) - 2 * d.qvel[2]
        else:
            th_c = 6 * np.sin(8 * tc); tk_c = 9 * np.sin(11 * tc + 1)
        d.ctrl[:] = [th_c, tk_c]
        mujoco.mj_step(m, d)
        log[k] = [k * dt, d.qpos[0], d.qvel[0], d.qpos[1], d.qpos[2],
                  d.qvel[1], d.qvel[2], 0]
        log[k, 7] = th_c * d.qvel[1] + tk_c * d.qvel[2]
    t = log[:, 0]; z = log[:, 1]; zd = log[:, 2]
    q1 = log[:, 3]; q2 = log[:, 4]; dq1 = log[:, 5]; dq2 = log[:, 6]
    # windows in the excited phase
    errs = []; sigs = []
    tau1 = np.zeros_like(t); tau2 = np.zeros_like(t)  # power already logged
    for ia in range(220, N - 26, 12):
        ib = ia + 25
        row, _ = energy_row(t, z, zd, q1, q2, dq1, dq2, tau1, tau2, ia, ib)
        y_true = TRAP(log[ia:ib + 1, 7], t[ia:ib + 1])
        pred = float(np.dot(row, th))
        errs.append(pred - y_true); sigs.append(abs(y_true))
    errs = np.array(errs)
    print(f"[check] energy identity residual: rms={np.sqrt((errs**2).mean()):.5f} "
          f"vs signal rms={np.sqrt(np.mean(np.array(sigs)**2)):.4f} J "
          f"(relative {100*np.sqrt((errs**2).mean())/max(np.sqrt(np.mean(np.array(sigs)**2)),1e-9):.2f}%)")
    return np.sqrt((errs ** 2).mean()) / max(np.sqrt(np.mean(np.array(sigs) ** 2)), 1e-9) < 0.05


def build_dataset():
    """Stance windows from jump 0424/0602 + s2s_gnd."""
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    mj = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, BD["arm_knee"]))
    mg = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_gnd_6d(0.0, BD["arm_knee"]))
    rows = []; ys = []; tags = []
    jobs = []
    for ds in ("jump_0424", "jump_0602"):
        for d2, sub, isj in list_experiments():
            if d2 == ds:
                jobs.append((ds, sub, MS.LOADERS[ds](sub), mj, True, 15, 7))
    try:
        cycles, _ = MS.load_s2s_cycles()
        for ci, td in enumerate(cycles):
            jobs.append(("s2s_gnd", ci, td, mg, False, 50, 25))
    except Exception as e:
        print("s2s load fail:", e)
    from scipy.signal import savgol_filter
    for ds, sub, td, model, isj, W, stq in jobs:
        pp = MS.get_prep((f"g21_{ds}", sub), td, model, isj)
        t = pp["t"]
        grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
        gg = savgol_filter(grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
        st = np.where(gg > 15)[0]
        if len(st) < W + 4:
            continue
        if isj:
            # push-off ONLY: first contiguous stance run. FK bz is invalid in
            # flight; landing impact excluded. Takeoff = first gap > 3 samples.
            brk = np.where(np.diff(st) > 3)[0]
            i1 = st[brk[0]] - 2 if len(brk) else st[-1] - 2
            i0 = st[0]
        else:
            i0, i1 = st[0], st[-1]
        if i1 - i0 < W + 2:
            continue
        for ia in range(i0, i1 - W, stq):
            ib = ia + W
            row, y = energy_row(t, pp["bz"], pp["vbz"], pp["q1m"], pp["q2m"],
                                pp["dq1m"], pp["dq2m"], pp["tau_h"], pp["tau_k"], ia, ib)
            row.append(float(gg[ib] ** 2 - gg[ia] ** 2))  # contact elastic work col: c=1/(2k)
            spd = max(np.abs(pp["dq2m"][ia:ib]).max(), np.abs(pp["dq1m"][ia:ib]).max())
            if spd < 0.15:
                continue
            ttk = float(t[i1] - t[ia]) if isj else float("nan")   # time-to-takeoff
            rows.append(row); ys.append(y)
            tags.append((ds, str(sub), float(np.mean(np.abs(pp["dq2m"][ia:ib]))), ttk))
    return np.array(rows), np.array(ys), tags


NAMES13 = NAMES + ["c_cw"]   # + contact elastic work param 1/(2k)


def fit_subset(Y, b, tags, mask, th_fix, label, free_idx):
    Ym = Y[mask]; bm = b[mask]
    known_idx = [i for i in range(len(th_fix)) if i not in free_idx]
    b_red = bm - Ym[:, known_idx] @ th_fix[known_idx]
    Yr = Ym[:, free_idx]
    sv = np.linalg.svd(Yr, compute_uv=False)
    th_free, *_ = np.linalg.lstsq(Yr, b_red, rcond=None)
    th = th_fix.copy(); th[free_idx] = th_free
    pred = Ym @ th
    rms = np.sqrt(np.mean((pred - bm) ** 2)); rel = rms / np.sqrt(np.mean(bm ** 2))
    sigma2 = np.sum((pred - bm) ** 2) / max(len(bm) - len(free_idx), 1)
    se = np.zeros(len(th))
    se[free_idx] = np.sqrt(np.diag(sigma2 * np.linalg.inv(Yr.T @ Yr)))
    print(f"\n=== fit [{label}]  rows={mask.sum()}  cond={sv[0]/sv[-1]:.1f}  "
          f"resid {rms:.4f} J ({100*rel:.1f}%)")
    return th, se, dict(cond=float(sv[0] / sv[-1]), rms=float(rms), rel=float(rel), n=int(mask.sum()))


def main():
    ok = synthetic_check()
    print("[check] stance formulas:", "PASS" if ok else "FAIL")
    if not ok:
        return
    Y, b, tags = build_dataset()
    isj = np.array([tg[0].startswith("jump") for tg in tags])
    print(f"\n[data] rows: {len(b)} (jump push-off {isj.sum()}, s2s_gnd {(~isj).sum()})")
    # references
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.STIFF_KNEE = 0.0
    m_ref = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(0.0, BD["arm_knee"]))
    th_cad = np.concatenate([theta_stance_from_model(m_ref), [0.0]])   # + c_cw=0
    air = json.load(open(REPO / "code/goal21/air_regression.json", encoding="utf-8"))["theta"]
    out = {}
    # (a) JUMP push-off only: inertials + rail + contact compliance free
    free_j = [0, 1, 2, 3, 4, 5, 11, 12]     # A D B E k1 k2 f_rail c_cw
    th_j, se_j, meta_j = fit_subset(Y, b, tags, isj, th_cad, "jump push-off", free_j)
    print(f"{'param':<7}{'jump-reg':>12}{'+/-':>9}{'canonical':>12}{'air-reg':>10}")
    for i, n in enumerate(NAMES13):
        av = air.get(n, float("nan")) if n in ("A", "D", "B", "E", "k1", "k2") else float("nan")
        print(f"{n:<7}{th_j[i]:>12.5f}{se_j[i]:>9.5f}{th_cad[i]:>12.5f}{av:>10.5f}")
    print(f"[consistency] B vs L1*k2: {th_j[2]:.5f} vs {L1*th_j[5]:.5f} "
          f"(ratio {th_j[2]/(L1*th_j[5]+1e-12):.3f})")
    if th_j[12] > 1e-9:
        print(f"[contact] effective stiffness from c_cw: k = {1/(2*th_j[12]):.0f} N/m")
    out["jump"] = dict(theta=dict(zip(NAMES13, map(float, th_j))),
                       se=dict(zip(NAMES13, map(float, se_j))), **meta_j)
    # residual atlas vs time-to-takeoff (whip region lives at small ttk)
    pred = Y @ th_j; res = pred - b
    ttk = np.array([tg[3] for tg in tags])
    print("[atlas] jump residual vs time-to-takeoff:")
    for lo, hi in [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 5.0)]:
        mk = isj & (ttk >= lo) & (ttk < hi)
        if mk.sum() > 5:
            print(f"  ttk {lo*1000:3.0f}-{hi*1000:4.0f} ms: mean {res[mk].mean():+.4f} J "
                  f"rms {np.sqrt((res[mk]**2).mean()):.4f} (n={mk.sum()})")
    # (b) s2s_gnd: eta measurement given CAD theta (low speed => transmission regime).
    #     eta = measured work / mechanically required work per window
    need = Y[~isj, :11] @ th_cad[:11]       # required: Delta(T+V) + friction integrals
    got = b[~isj]
    keep = np.abs(need) > 0.05
    eta = got[keep] / need[keep]
    print(f"\n=== s2s_gnd eta (measured/required, CAD theta): "
          f"median {np.median(eta):.3f}  IQR [{np.percentile(eta,25):.3f}, {np.percentile(eta,75):.3f}]  n={keep.sum()}")
    spd2 = np.array([tg[2] for tg in tags])[~isj][keep]
    for lo, hi in [(0, 0.5), (0.5, 1.5), (1.5, 6)]:
        mk = (spd2 >= lo) & (spd2 < hi)
        if mk.sum() > 5:
            print(f"  |dq2| {lo}-{hi} rad/s: median eta {np.median(eta[mk]):.3f} (n={mk.sum()})")
    out["s2s_eta"] = dict(median=float(np.median(eta)),
                          q25=float(np.percentile(eta, 25)), q75=float(np.percentile(eta, 75)),
                          n=int(keep.sum()))
    out["theta_cad"] = dict(zip(NAMES13, map(float, th_cad)))
    json.dump(out, open(REPO / "code/goal21/stance_regression.json", "w"), indent=1)
    print("\nsaved code/goal21/stance_regression.json")


if __name__ == "__main__":
    main()
