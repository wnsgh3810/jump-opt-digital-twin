"""GOAL21 P1 — analytic 2R momentum-form regressor, identified on s2s_air.

Frame: mujoco air model (base clamped). q1 = hip from vertical-down, q2 = knee rel.
phi2 = q1+q2 (calf absolute). CoM offsets below joints: r1=-ctz, r2=-ccz.

Energy (serial-equivalent; crank/coupler fold into the same base params):
  T = 1/2 A q1d^2 + 1/2 D (q1d+q2d)^2 + B q1d (q1d+q2d) cos q2 + 1/2 E q2d^2
  V = -g (k1 cos q1 + k2 cos phi2)
Base params theta = [A, D, B, E, k1, k2, fv1, fc1, fv2, fc2]  (B ~= L1*k2 is an
internal consistency CHECK, not imposed).

Momentum-form (no ddq anywhere): integrate Euler-Lagrange over window [a,b]:
  int tau1 = [p1]_a^b            + int dV/dq1 + fv1*Dq1 + fc1*int sgn(q1d)
  int tau2 = [p2]_a^b + int B q1d(q1d+q2d) s2 + int dV/dq2 + fv2*Dq2 + fc2*int sgn(q2d)
  p1 = A q1d + D(q1d+q2d) + B(2q1d+q2d) c2 ;  p2 = D(q1d+q2d) + B q1d c2 + E q2d

Step 1: numeric self-check vs MuJoCo (mj_fullM + qfrc_bias) on the serial air XML.
Step 2: momentum-window LS on s2s_air 15 cycles (dynamic windows only; near-zero-
velocity windows reserved as stiction probes). Report theta_hat vs CAD vs canonical
twin, condition number, residuals.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
from mshoot_s2s_air_holdout import load_air_cycles

G = 9.81
L1 = 0.25
BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
NAMES = ["A", "D", "B", "E", "k1", "k2", "fv1", "fc1", "fv2", "fc2"]


def analytic_M(q2, th):
    A, D, B, E = th[0], th[1], th[2], th[3]
    c2 = np.cos(q2)
    return np.array([[A + D + 2 * B * c2, D + B * c2],
                     [D + B * c2, D + E]])


def analytic_bias(q1, q2, dq1, dq2, th):
    """C(q,dq)dq + G(q)  (no friction) — for the MuJoCo cross-check only."""
    A, D, B, E, k1, k2 = th[:6]
    s2 = np.sin(q2)
    c1 = np.sin(q1)  # dV/dq1 uses sin
    # Coriolis/centrifugal from T: d/dt(dT/dqd) - dT/dq
    C1 = -B * s2 * (2 * dq1 * dq2 + dq2 ** 2)
    C2 = B * s2 * dq1 ** 2
    G1 = G * (k1 * np.sin(q1) + k2 * np.sin(q1 + q2))
    G2 = G * (k2 * np.sin(q1 + q2))
    return np.array([C1 + G1, C2 + G2])


def theta_from_model(m):
    """Base params read from the COMPILED MuJoCo model (exact, no XML rounding)."""
    bt = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "thigh")
    bc = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "calf")
    Mt, Mc2 = m.body_mass[bt], m.body_mass[bc]
    r1, r2 = -m.body_ipos[bt][2], -m.body_ipos[bc][2]
    It, Ic2 = m.body_inertia[bt][1], m.body_inertia[bc][1]   # Iyy (rotation about y)
    arm_hip, arm_knee = m.dof_armature[0], m.dof_armature[1]
    A = It + Mt * r1 ** 2 + Mc2 * L1 ** 2 + arm_hip
    D = Ic2 + Mc2 * r2 ** 2
    B = Mc2 * L1 * r2
    E = arm_knee
    k1 = Mt * r1 + Mc2 * L1
    k2 = Mc2 * r2
    return np.array([A, D, B, E, k1, k2, S.FV_HIP, S.FC_HIP, S.FV_KNEE, S.FC_KNEE])


def numeric_check():
    """Verify analytic M and bias against MuJoCo serial air model."""
    # canonical S state (round-1)
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = 0.0  # springs off for pure check
    m = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_air_6d(0.0, BD["arm_knee"]))
    d = mujoco.MjData(m)
    th = theta_from_model(m)
    rng = np.random.default_rng(3)
    errM = 0.0; errB = 0.0
    for _ in range(200):
        q = rng.uniform(-2.5, 2.5, 2); dq = rng.uniform(-20, 20, 2)
        d.qpos[:] = q; d.qvel[:] = dq
        mujoco.mj_forward(m, d)
        Mfull = np.zeros((2, 2))
        mujoco.mj_fullM(m, Mfull, d.qM)
        errM = max(errM, np.abs(Mfull - analytic_M(q[1], th)).max())
        # qfrc_bias = C*dq + G  (mujoco sign: force needed = bias)
        bias = d.qfrc_bias.copy()
        # remove mujoco joint damping? damping enters passive, not bias. frictionloss is constraint.
        errB = max(errB, np.abs(bias - analytic_bias(q[0], q[1], dq[0], dq[1], th)).max())
    print(f"[check] max|M_mj - M_analytic|    = {errM:.2e}")
    print(f"[check] max|bias_mj - analytic|   = {errB:.2e}")
    return errM < 1e-8 and errB < 1e-6


def window_rows(t, q1, q2, dq1, dq2, tau1, tau2, ia, ib):
    """Two regressor rows + targets for window [ia, ib]."""
    sl = slice(ia, ib + 1)
    tt = t[sl]
    c2 = np.cos(q2[sl]); s2 = np.sin(q2[sl])
    ph = q1[sl] + q2[sl]
    tr = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    sgn = lambda v: np.where(np.abs(v) > 0.05, np.sign(v), 0.0)
    # momenta terms at endpoints
    def dlt(f):
        return f[-1] - f[0]
    p1_A = dlt(dq1[sl]); p1_D = dlt(dq1[sl] + dq2[sl]); p1_B = dlt((2 * dq1[sl] + dq2[sl]) * c2)
    p2_D = p1_D; p2_B = dlt(dq1[sl] * c2); p2_E = dlt(dq2[sl])
    int_s2term = tr(dq1[sl] * (dq1[sl] + dq2[sl]) * s2, tt)
    g1_k1 = G * tr(np.sin(q1[sl]), tt); g_k2 = G * tr(np.sin(ph), tt)
    fv1 = dlt(q1[sl]); fv2 = dlt(q2[sl])
    fc1 = tr(sgn(dq1[sl]), tt); fc2 = tr(sgn(dq2[sl]), tt)
    row1 = [p1_A, p1_D, p1_B, 0.0, g1_k1, g_k2, fv1, fc1, 0.0, 0.0]
    row2 = [0.0, p2_D, p2_B + int_s2term, p2_E, 0.0, g_k2, 0.0, 0.0, fv2, fc2]
    y1 = tr(tau1[sl], tt); y2 = tr(tau2[sl], tt)
    return row1, row2, y1, y2


def build_dataset(win_s=0.10, stride_s=0.05, dyn_thresh=0.2):
    rows = []; ys = []; hold = []
    for c in load_air_cycles():
        t = np.asarray(c["t"])
        q1 = -np.asarray(c["q1"]) - np.pi / 2
        q2 = -np.asarray(c["q2"])
        dq1 = -np.asarray(c["dq1"]); dq2 = -np.asarray(c["dq2"])
        tau1 = -np.asarray(c["tau1"]); tau2 = -np.asarray(c["tau2"])
        dt = np.median(np.diff(t)); W = int(win_s / dt); st = int(stride_s / dt)
        for ia in range(0, len(t) - W, st):
            ib = ia + W
            r1, r2, y1, y2 = window_rows(t, q1, q2, dq1, dq2, tau1, tau2, ia, ib)
            spd = max(np.abs(dq1[ia:ib]).max(), np.abs(dq2[ia:ib]).max())
            if spd < dyn_thresh:
                # stiction probe: residual = needed hold torque mismatch
                hold.append((r1, r2, y1, y2))
            else:
                rows.append(r1); ys.append(y1)
                rows.append(r2); ys.append(y2)
    return np.array(rows), np.array(ys), hold


def main():
    ok = numeric_check()
    print("[check] analytic model matches MuJoCo:", "PASS" if ok else "FAIL")
    if not ok:
        return
    Y, b, hold = build_dataset()
    print(f"\n[data] dynamic rows: {len(b)}  | stiction-probe windows: {len(hold)}")
    # LS + identifiability
    U, sv, Vt = np.linalg.svd(Y, full_matrices=False)
    print("[ident] singular values:", np.array2string(sv, precision=4))
    print(f"[ident] condition number = {sv[0]/sv[-1]:.1f}")
    th, res, rank, _ = np.linalg.lstsq(Y, b, rcond=None)
    pred = Y @ th
    rms = np.sqrt(np.mean((pred - b) ** 2))
    rel = rms / np.sqrt(np.mean(b ** 2))
    print(f"[fit] residual RMS = {rms:.5f} N*m*s  (relative {100*rel:.1f}%)")
    # parameter covariance (approx)
    sigma2 = np.sum((pred - b) ** 2) / (len(b) - len(th))
    cov = sigma2 * np.linalg.inv(Y.T @ Y)
    se = np.sqrt(np.diag(cov))
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = 0.0
    m_ref = mujoco.MjModel.from_xml_string(S.build_xml_sit2stand_air_6d(0.0, BD["arm_knee"]))
    th_cad = theta_from_model(m_ref)
    print(f"\n{'param':<6}{'regression':>12}{'+/-':>10}{'XML(canonical)':>16}")
    for i, n in enumerate(NAMES):
        print(f"{n:<6}{th[i]:>12.5f}{se[i]:>10.5f}{th_cad[i]:>16.5f}")
    print(f"\n[consistency] B vs L1*k2: {th[2]:.5f} vs {L1*th[5]:.5f} "
          f"(ratio {th[2]/(L1*th[5]):.3f}; 1.0 = internally consistent)")
    # stiction probes: residual torque during holds under CAD/regressed dynamics
    if hold:
        rs = []
        for r1, r2, y1, y2 in hold:
            e1 = y1 - np.dot(r1, th); e2 = y2 - np.dot(r2, th)
            rs.append((e1, e2))
        rs = np.array(rs)
        print(f"\n[stiction] hold-window residual impulse per joint (N*m*s):")
        print(f"  hip : mean|.|={np.abs(rs[:,0]).mean():.4f}  knee: mean|.|={np.abs(rs[:,1]).mean():.4f}")
        print("  (0.1s 창 기준 -> 평균 유지토크 오차 [Nm]: hip %.3f, knee %.3f)"
              % (np.abs(rs[:, 0]).mean() / 0.1, np.abs(rs[:, 1]).mean() / 0.1))
    json.dump(dict(theta=dict(zip(NAMES, map(float, th))), se=dict(zip(NAMES, map(float, se))),
                   theta_xml=dict(zip(NAMES, map(float, th_cad))),
                   cond=float(sv[0] / sv[-1]), resid_rms=float(rms), rel=float(rel)),
              open(REPO / "code/goal21/air_regression.json", "w"), indent=1)
    print("\nsaved code/goal21/air_regression.json")


if __name__ == "__main__":
    main()
