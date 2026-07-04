"""G20-A — EXPLICIT four-bar knee transmission (closed kinematic loop).

The real robot drives the knee through a parallelogram 4-bar (l_i = LC = 30mm crank).
All previous models LUMPED the linkage: coupler P (0.137kg) rigidly into the thigh,
crank C (0.656kg, includes the CVT l_i adjuster!) into the CALF. But the real crank
rotates about a hip-anchored axis — it does NOT translate with the calf. The serial
lump therefore carries ~0.66kg of phantom translating mass on the calf — precisely
the "calf wants light mass + high rotational inertia" impossible-combo signature that
railed every mass refit (v4: M_calf->0.30 bound, I_calf->1.8 bound).

Topology (zero config = all hanging -z, loop closed by construction):
  base(base_z) -> thigh(hip)
                   |- crank(knee_motor: actuated, armature, motor friction) tip at -LC
                   |    -> coupler(pin joint) length L1, ||thigh
                   |- calf(knee: passive) with rocker point at (0,0,-LC) in calf frame
  <connect coupler_tip == calf rocker point>   (parallelogram => crank angle == knee angle)
Encoder = crank (qpos[2]) == measured q2 mapping (consistent with all serial fits).

Stage 1: pure CAD masses (no scales) + v3 friction/contact/arm/stiff -> window score
vs (a) serial pure-CAD control and (b) v3 fitted serial. Structure effect isolated.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_refit as R
from load_31exp import list_experiments
import build_xml_i3 as B

L1, L2, LC = B.L1_VAL, B.L2_VAL, B.LC_VAL


def calf_inertial(m2_s, m_foot, dz=0.0, i_s=1.0):
    """Calf = M2 only (+foot). No crank lump."""
    M2 = B.M2_CAD * m2_s; Mf = m_foot
    Mtot = M2 + Mf
    r2 = B.R2_VAL + dz
    cz = -(M2 * r2 + Mf * L2) / Mtot
    I = B.I2_VAL * i_s + M2 * (r2 + cz) ** 2 + Mf * (L2 + cz) ** 2
    return Mtot, cz, I


def build_xml_fourbar_jump(arm_knee, scales=None):
    sc = scales or {}
    s_th = sc.get("M_thigh", 1.0); s_ca = sc.get("M_calf", 1.0)
    s_p = sc.get("M_p", 1.0); s_c = sc.get("M_c", 1.0)
    s_b = sc.get("M_base", 1.0)
    i_th = sc.get("I_thigh", 1.0); i_ca = sc.get("I_calf", 1.0)
    dz_th = sc.get("com_dz_th", 0.0); dz_ca = sc.get("com_dz_ca", 0.0)
    m_foot = sc.get("m_foot", 0.0)
    M1 = B.M1_CAD * s_th
    R1 = B.R1_VAL + dz_th
    I1 = B.I1_VAL * i_th
    Mc2, ccz, Ic2 = calf_inertial(s_ca, m_foot, dz_ca, i_ca)
    MP = B.M_P_CAD * s_p; MC = B.M_C_CAD * s_c
    sr = S._solref_str(); si = S._solimp_str(); Mb = S._base_mass()
    return f"""<mujoco model="fourbar_jump">
<option cone="{S.CONE}" impratio="{S.IMPRATIO}" gravity="0 0 -9.81" timestep="{S.DT}" integrator="{S.JUMP_INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="{S._fric_str()}" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-200 200" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{S.FOOT_RADIUS:.4f}" priority="1" solref="{sr}" solimp="{si}" condim="6" friction="{S._fric_str()}" margin="0.001"/>
  </default>
</default></default>
<worldbody>
  <geom name="floor" size="0 0 0.05" type="plane" solref="{sr}" solimp="{si}" friction="{S._fric_str()}" margin="0.001"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1"/>
    <inertial pos="0 0 0" mass="{Mb:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="0" damping="{S.FV_HIP:.6f}" frictionloss="{S.FC_HIP:.6f}"/>
      <inertial pos="0 0 -{R1:.5f}" mass="{M1:.5f}" diaginertia="{I1:.6f} {I1:.6f} 0.0002"/>
      <geom type="capsule" size="0.02" fromto="0 0 0 0 0 -{L1}" contype="1" conaffinity="1"/>
      <body name="crank" pos="0 0 0">
        <joint name="knee_motor" type="hinge" armature="{arm_knee:.8f}" damping="{S.FV_KNEE:.6f}" frictionloss="{S.FC_KNEE:.6f}" stiffness="{S.STIFF_KNEE:.6f}" springref="{S.SPRINGREF_KNEE:.5f}"/>
        <inertial pos="0 0 -{B.RC_VAL:.5f}" mass="{MC:.5f}" diaginertia="{B.IC_VAL:.6f} {B.IC_VAL:.6f} {B.IC_VAL:.6f}"/>
        <geom type="capsule" size="0.008" fromto="0 0 0 0 0 -{LC}" contype="0" conaffinity="0"/>
        <body name="coupler" pos="0 0 -{LC}">
          <joint name="cpin" type="hinge"/>
          <inertial pos="0 0 -{B.RP_VAL:.5f}" mass="{MP:.5f}" diaginertia="{B.IP_VAL:.6f} {B.IP_VAL:.6f} 0.00005"/>
          <geom type="capsule" size="0.006" fromto="0 0 0 0 0 -{L1}" contype="0" conaffinity="0"/>
        </body>
      </body>
      <body name="calf" pos="0 0 -{L1}">
        <joint name="knee" type="hinge" damping="0.001"/>
        <inertial pos="0 0 {ccz:.5f}" mass="{Mc2:.5f}" diaginertia="{Ic2:.6f} {Ic2:.6f} 0.00005"/>
        <geom type="capsule" size="0.015" fromto="0 0 0 0 0 -{L2}" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot" type="cylinder" size="{S.FOOT_RADIUS:.4f} {S.FOOT_HALF_LEN:.4f}" pos="0 0 -{L2}" euler="90 0 0"/>
      </body>
    </body>
  </body>
</worldbody>
<equality>
  <connect body1="coupler" body2="calf" anchor="0 0 -{L1}" solref="0.0008 1"/>
</equality>
<actuator>
  <motor name="hip_motor" joint="hip" gear="1"/>
  <motor name="knee_motor" joint="knee_motor" gear="1"/>
</actuator>
</mujoco>"""


def eval_windows_fourbar(model, pp):
    """Windows on the 5-DOF loop model. qpos=[bz,hip,crank,cpin,knee]. Encoder=crank."""
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
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
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]      # crank = encoder
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            out.append(dict(rq1=1.0, rq2=1.0, rdq1=10.0, rdq2=10.0))
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        out.append(dict(rq1=r(q1a, pp["q1m"]), rq2=r(q2a, pp["q2m"]),
                        rdq1=r(dq1a, pp["dq1m"]), rdq2=r(dq2a, pp["dq2m"])))
    return out


def score_fourbar(arm_knee, scales=None):
    model = mujoco.MjModel.from_xml_string(build_xml_fourbar_jump(arm_knee, scales))
    total = 0.0; per = {}
    groups = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        groups.append((ds, subs, MS.LOADERS[ds]))
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    for ds, subs, loader in groups:
        sc = 0.0; nw = 0; acc = np.zeros(4)
        for sub in subs:
            td = loader(sub)
            pp = MS.get_prep((ds, sub), td, model, True)  # FK identical (serial geometry)
            wins = eval_windows_fourbar(model, pp)
            sc += MS.window_score(wins); nw += len(wins)
            for w in wins:
                acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
        total += sc; per[ds] = dict(score=sc, mean=acc / max(nw, 1))
    return total, per


def run_jump_sim_fourbar(model, td):
    """Full-trajectory Mode A replay on the 4-bar model (held-out validation).
    Mirrors S.run_jump_sim: settle PD on hip+crank, then tau_real replay, log h."""
    t_real = td["t"]
    tau_h_in = -np.asarray(td["tau1_real"]); tau_k_in = -np.asarray(td["tau2_real"])
    sq1, sq2 = S.Q1_MU_INIT, S.Q2_MU_INIT
    d = mujoco.MjData(model)
    d.qpos[:] = [S.BASE_Z_INIT + S.BASE_Z_INIT_OFF, sq1, sq2, -sq2, sq2]
    d.qvel[:] = 0.0
    mujoco.mj_forward(model, d)
    dt = model.opt.timestep
    T_motion = float(t_real[-1])
    N = int((S.T_SETTLE + T_motion + S.T_AFTER) / dt) + 1
    t_log = np.arange(N) * dt - S.T_SETTLE
    q2c = np.zeros(N); dq2c = np.zeros(N); q1a = np.zeros(N); dq1a = np.zeros(N); bz = np.zeros(N)
    for k in range(N):
        tc = k * dt
        if tc < S.T_SETTLE:
            th = S.SETTLE_KP * (sq1 - d.qpos[1]) + S.SETTLE_KD * (0 - d.qvel[1])
            tk = S.SETTLE_KP * (sq2 - d.qpos[2]) + S.SETTLE_KD * (0 - d.qvel[2])
        elif tc < S.T_SETTLE + T_motion:
            tm = tc - S.T_SETTLE
            th = float(np.interp(tm, t_real, tau_h_in))
            tk = float(np.interp(tm, t_real, tau_k_in))
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        try:
            mujoco.mj_step(model, d)
        except Exception:
            return None
        q1a[k] = d.qpos[1]; dq1a[k] = d.qvel[1]
        q2c[k] = d.qpos[2]; dq2c[k] = d.qvel[2]     # crank = encoder
        bz[k] = d.qpos[0]
        if abs(d.qpos[0]) > 5.0:
            return None
    return dict(t=t_log, q1=q1a, dq1=dq1a, q2=q2c, dq2=dq2c, base_z=bz)


def validate_fulltraj(arm_knee, scales, offs=None):
    """Held-out: full replay per jump dataset -> q/dq RMSE + h_ratio. offs: canonical per-date."""
    model = mujoco.MjModel.from_xml_string(build_xml_fourbar_jump(arm_knee, scales))
    offs = offs or {}
    from collections import defaultdict
    G = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0])
    groups = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        groups.append((ds, subs, MS.LOADERS[ds]))
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    for ds, subs, loader in groups:
        o1, o2 = offs.get(ds, (0.0, 0.0))
        for sub in subs:
            td = loader(sub)
            log = run_jump_sim_fourbar(model, td)
            if log is None:
                continue
            tr = np.asarray(td["t"])
            mk = (log["t"] >= 0) & (log["t"] <= tr[-1])
            q1s = np.interp(tr, log["t"][mk], (-log["q1"] - np.pi / 2)[mk])
            q2s = np.interp(tr, log["t"][mk], (-log["q2"])[mk])
            dq1s = np.interp(tr, log["t"][mk], (-log["dq1"])[mk])
            dq2s = np.interp(tr, log["t"][mk], (-log["dq2"])[mk])
            r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
            g = G[ds]
            g[0] += r(q1s, td["q1"] + o1); g[1] += r(q2s, td["q2"] + o2)
            g[2] += r(dq1s, td["dq1"]); g[3] += r(dq2s, td["dq2"])
            g[4] += float(log["base_z"].max()); g[5] += float(td["h_real"]); g[6] += 1
    return {ds: dict(q1=g[0]/g[6], q2=g[1]/g[6], dq1=g[2]/g[6], dq2=g[3]/g[6],
                     h_ratio=g[4]/g[5]) for ds, g in G.items() if g[6]}


if __name__ == "__main__":
    best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    d = R.set_params(np.array(best["x"]))   # sets v3 friction/contact/stiff in S
    # reference (a): v3 fitted serial, jumps only
    t_v3, per_v3 = MS.evaluate_all(0.0, d["arm_knee"])
    j_v3 = sum(v["score"] for ds, v in per_v3.items() if ds != "sit2stand_gnd")
    print(f"[ref] v3 fitted serial (jump windows): {j_v3:.0f}")
    # reference (b): pure-CAD serial control (scales=1 under the SAME S globals)
    xm = np.array(json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))["mass_15d"])
    xm[:5] = 1.0; xm[5] = 0.0; xm[6:10] = 1.0; xm[10:14] = 0.0
    import plot_4panel as P4
    P4.apply_phase1_params(xm)  # pure CAD lumped
    # re-apply v3 friction/contact (P4.apply resets them)
    dd = dict(zip(best["names"], best["x"]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    t_cad, per_cad = MS.evaluate_all(0.0, dd["arm_knee"])
    j_cad = sum(v["score"] for ds, v in per_cad.items() if ds != "sit2stand_gnd")
    print(f"[ref] pure-CAD serial control        : {j_cad:.0f}")
    # four-bar explicit, pure CAD
    tot, per = score_fourbar(dd["arm_knee"], dict(m_foot=dd["m_foot"]))
    print(f"[NEW] FOUR-BAR explicit, pure CAD    : {tot:.0f}  (vs CAD-serial {100*(tot/j_cad-1):+.1f}%, vs v3 {100*(tot/j_v3-1):+.1f}%)")
    for ds, v in per.items():
        m = v["mean"]
        print(f"   {ds:<20} q1={m[0]:.4f} q2={m[1]:.4f} dq1={m[2]:.2f} dq2={m[3]:.2f}")
