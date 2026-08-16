"""GOAL19 Phase 11 — comprehensive visualization for user review.

Per jump trial: 3x3 figure
  row0: q1(sim/real), q2(sim/real), base_z(sim) + measured-FK + camera h
  row1: dq1, dq2, base_vz(sim) + measured-FK  (shows the takeoff-velocity gap)
  row2: tau1, tau2, GRF (marked UNRELIABLE — not a fit target)
Plus a height-summary bar chart across all jump trials.

Uses the current final model. GRF de-emphasized (user: load cell unreliable).
"""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import plot_4panel as P4
from apply_final_and_regen import apply_final
from load_31exp import list_experiments

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (REPO / "code/goal19/phase11/viz")
OUT.mkdir(parents=True, exist_ok=True)
FM = json.load(open(REPO / "code/goal19/goal19_final_model.json", encoding="utf-8"))

import mshoot as MS
import mshoot_refit as R

LOADERS = {"jump_position_0421": S.load_jump_position,
           "jump_0424": S.load_jump_0424, "jump_0602": S.load_jump_0602}
# 0422 excluded (external-PD, bad torque); 0319 excluded (data outlier) — per user.


def measured_fk_base(td, m, d, fg):
    t = np.asarray(td["t"])
    q1m = -np.asarray(td["q1"]) - np.pi / 2
    q2m = -np.asarray(td["q2"])
    bz = np.zeros(len(t))
    for i in range(len(t)):
        d.qpos[:] = [1.0, q1m[i], q2m[i]]
        mujoco.mj_forward(m, d)
        bz[i] = 1.0 - float(d.geom_xpos[fg][2]) + S.FOOT_RADIUS
    bz = savgol_filter(bz, 11, 3)
    return t, bz, np.gradient(bz, t)


FOURBAR = None   # set to dict(params) to use the four-bar final model as sim source


def one_trial(ds, sub, ap, td=None):
    if td is None:
        td = LOADERS[ds](sub)
    if FOURBAR is not None:
        import mshoot_fourbar as FB
        d = FOURBAR
        mfb = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(d["arm_knee"], d))
        fl = FB.run_jump_sim_fourbar(mfb, td)
        if fl is None:
            return None
        n = len(fl["t"])
        tr0 = np.asarray(td["t"])
        tau1i = np.interp(np.clip(fl["t"], 0, tr0[-1]), tr0, -np.asarray(td["tau1_real"]))
        tau2i = np.interp(np.clip(fl["t"], 0, tr0[-1]), tr0, -np.asarray(td["tau2_real"]))
        log = dict(t=fl["t"], q=np.column_stack([fl["base_z"], fl["q1"], fl["q2"]]),
                   dq=np.column_stack([np.gradient(fl["base_z"], fl["t"]), fl["dq1"], fl["dq2"]]),
                   tau_app=np.column_stack([tau1i, tau2i]), grf_z=fl["grf_z"])
        # calibrated real (per-date offsets)
        offk = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
                "jump_0424": ("o1_0424", "o2_0424")}
        if ds in offk:
            td = dict(td)
            td["q1"] = np.asarray(td["q1"]) + d[offk[ds][0]]
            td["q2"] = np.asarray(td["q2"]) + d[offk[ds][1]]
        xml = S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"])  # FK helper model only
        m = mujoco.MjModel.from_xml_string(xml)
    else:
        xml = S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"])
        m = mujoco.MjModel.from_xml_string(xml)
        log = S.run_jump_sim(m, td, 0, 0, motor_tm=0.0)
    if log is None:
        return None
    fg = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "foot")
    d = mujoco.MjData(m)
    t_real = np.asarray(td["t"])
    mask = (log["t"] >= 0) & (log["t"] <= t_real[-1])
    ts = log["t"][mask]
    q1s = (-log["q"][:, 1] - np.pi / 2)[mask]; q2s = (-log["q"][:, 2])[mask]
    dq1s = (-log["dq"][:, 1])[mask]; dq2s = (-log["dq"][:, 2])[mask]
    tau1s = (-log["tau_app"][:, 0])[mask]; tau2s = (-log["tau_app"][:, 1])[mask]
    grfs = log["grf_z"][mask]
    bzs = log["q"][:, 0]; tsim = log["t"]; vsim = np.gradient(bzs, tsim)
    tfk, bzfk, vfk = measured_fk_base(td, m, d, fg)
    h_real = float(td["h_real"]); h_sim = float(bzs.max())

    fig, ax = plt.subplots(3, 3, figsize=(15, 11))
    fig.suptitle(f"{ds}/{sub}   Mode A digital twin   |   h_sim={h_sim:.2f}m  h_camera={h_real:.2f}m",
                 fontsize=13, fontweight="bold")
    # row0
    ax[0,0].plot(ts, q1s, label="sim"); ax[0,0].plot(t_real, td["q1"], "--", label="real")
    ax[0,0].set_title("q1 hip [rad]")
    ax[0,1].plot(ts, q2s, label="sim"); ax[0,1].plot(t_real, td["q2"], "--", label="real")
    ax[0,1].set_title("q2 knee [rad]")
    ax[0,2].plot(tsim, bzs, label="base_z sim")
    ax[0,2].plot(tfk, bzfk, ":", label="base_z from measured q (FK)")
    ax[0,2].axhline(h_real, ls="--", color="k", lw=1, label=f"camera apex {h_real:.2f}")
    ax[0,2].set_title("base center height [m]")
    # row1
    ax[1,0].plot(ts, dq1s, label="sim"); ax[1,0].plot(t_real, td["dq1"], "--", label="real")
    ax[1,0].set_title("dq1 hip [rad/s]")
    ax[1,1].plot(ts, dq2s, label="sim"); ax[1,1].plot(t_real, td["dq2"], "--", label="real")
    ax[1,1].set_title("dq2 knee [rad/s]  (terminal spike = height driver)")
    ax[1,2].plot(tsim, vsim, label=f"base_vz sim (peak {np.max(vsim):.2f})")
    ax[1,2].plot(tfk, vfk, ":", label=f"base_vz from measured q (peak {np.max(vfk):.2f})")
    ax[1,2].set_title("base center velocity [m/s]")
    # row2
    ax[2,0].plot(ts, tau1s, label="sim applied"); ax[2,0].plot(t_real, td["tau1_real"], "--", label="real (input)")
    ax[2,0].set_title("tau1 hip [Nm]")
    ax[2,1].plot(ts, tau2s, label="sim applied"); ax[2,1].plot(t_real, td["tau2_real"], "--", label="real (input)")
    ax[2,1].set_title("tau2 knee [Nm]")
    ax[2,2].plot(ts, grfs, label="sim"); ax[2,2].plot(t_real, td["grf_z"], "--", label="real")
    ax[2,2].set_title("GRF_z [N]  — UNRELIABLE (load cell), NOT fitted")
    for a in ax.flat:
        a.set_xlabel("t [s]"); a.legend(fontsize=8); a.grid(alpha=0.3)
    fig.tight_layout()
    png = OUT / f"trial_{ds}_{sub}.png"
    fig.savefig(png, dpi=95); plt.close(fig)
    return dict(png=str(png), ds=ds, sub=sub, h_sim=h_sim, h_real=h_real,
                vsim=float(np.max(vsim)), vfk=float(np.max(vfk)))


def main():
    global FOURBAR
    fbj = REPO / "code/goal19/phase11/fourbar_refit_best.json"
    if fbj.exists():
        best = json.load(open(fbj, encoding="utf-8"))
        d = dict(zip(best["names"], best["x"]))
        S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = d["fc_hip"]; S.FC_KNEE = d["fc_knee"]
        S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        FOURBAR = d
        ap = dict(arm_hip=0.0, arm_knee=d["arm_knee"])
    else:
        best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
        d = R.set_params(np.array(best["x"]))
        ap = dict(arm_hip=0.0, arm_knee=d["arm_knee"])
    jumps = [(ds, sub, None) for ds, sub, isj in list_experiments()
             if isj and ds in LOADERS]
    for mds, tdir, subs in MS.MARCH:
        for sub in subs:
            jumps.append((mds, sub, MS.load_march(tdir, sub)))
    print(f"generating {len(jumps)} jump trial figures + summary (v3 model)...")
    res = []
    for ds, sub, td in jumps:
        try:
            r = one_trial(ds, sub, ap, td=td)
        except Exception as e:
            print(f"  {ds}/{sub}: ERROR {e}"); r = None
        if r:
            res.append(r)
            print(f"  {ds}/{sub}: h_sim={r['h_sim']:.2f} h_cam={r['h_real']:.2f} "
                  f"vsim={r['vsim']:.2f} vfk={r['vfk']:.2f}")
    # height summary bar
    fig, ax = plt.subplots(figsize=(max(10, len(res) * 0.5), 5))
    x = np.arange(len(res)); w = 0.4
    ax.bar(x - w/2, [r["h_sim"] for r in res], w, label="sim h")
    ax.bar(x + w/2, [r["h_real"] for r in res], w, label="camera h")
    ax.set_xticks(x); ax.set_xticklabels([f"{r['ds'].replace('jump_','')}/{r['sub']}" for r in res],
                                         rotation=90, fontsize=7)
    ax.set_ylabel("jump height [m]"); ax.set_title("Sim vs Camera jump height (base center apex)")
    ax.legend(); ax.grid(alpha=0.3, axis="y"); fig.tight_layout()
    fig.savefig(OUT / "height_summary.png", dpi=110); plt.close(fig)
    json.dump(res, open(OUT / "viz_index.json", "w"), indent=2)
    print(f"\nSAVED {len(res)} figures + height_summary.png to {OUT}")


if __name__ == "__main__":
    main()
