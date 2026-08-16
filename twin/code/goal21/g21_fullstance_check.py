"""GOAL21 P4 validation — full-stance open-loop replay per jump trial:
does the Stribeck term change push-off outcome (takeoff velocity / apex) and
whip amplitude fidelity?  canonical vs candidate params, 0424 + 0602.

Replay from stance start (FK state) through takeoff + 0.6 s flight.
Metrics per trial:
  q2 RMSE over stance, dq2 RMSE over stance,
  whip ratio = max|dq2_sim| / max|dq2_real| in [t_to - 80 ms, t_to],
  vto (sim base vertical velocity at real takeoff time), apex bz rise.
Usage: python g21_fullstance_check.py [params.json]
  (params json: {"params": {c, vs, w, c_hip, fc_knee, fv_knee, fc_hip, fv_hip}})
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
import mshoot as MS
import sub_sim_iter6v2 as S
from apply_final_and_regen import apply_final
from load_31exp import list_experiments
from scipy.signal import savgol_filter


def stance_range(td, t):
    grf = np.asarray(td.get("grf_z", np.full(len(t), 100.0)))
    gg = savgol_filter(grf, 11, 3) if len(grf) == len(t) else np.full(len(t), 100.0)
    st = np.where(gg > 15)[0]
    brk = np.where(np.diff(st) > 3)[0]
    i1 = st[brk[0]] if len(brk) else st[-1]
    return st[0], i1


def replay(model, pp, i0, t_end, xd):
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], pp["q2m"][i0]]
    d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], pp["dq2m"][i0]]
    mujoco.mj_forward(model, d)
    nst = int(round((t_end - t[i0]) / dt))
    out = np.empty((nst, 6))
    for k in range(nst):
        tc = t[i0] + k * dt
        vk = d.qvel[2]; vh = d.qvel[1]
        ek = -xd["c"] * np.tanh(vk / xd["w"]) * np.exp(-abs(vk) / xd["vs"])
        eh = -xd["c_hip"] * np.tanh(vh / xd["w"]) * np.exp(-abs(vh) / xd["vs"])
        d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) + eh,
                     np.interp(tc, t, pp["tau_k"]) + ek]
        mujoco.mj_step(model, d)
        out[k] = [tc + dt, d.qpos[0], d.qvel[0], d.qpos[2], d.qvel[2], d.qpos[1]]
    return out


def run_config(name, xd):
    S.FC_KNEE = xd["fc_knee"]; S.FV_KNEE = xd["fv_knee"]
    S.FC_HIP = xd["fc_hip"]; S.FV_HIP = xd["fv_hip"]
    ap = _AP
    m = mujoco.MjModel.from_xml_string(S.build_xml_jump_6d(ap["arm_hip"], ap["arm_knee"]))
    rows = []
    jobs = []
    for ds in ("jump_0424", "jump_0602"):
        jobs += [(ds, sub, MS.LOADERS[ds](sub)) for d2, sub, isj in list_experiments() if d2 == ds]
    for ds, tdir, subs in MS.MARCH:      # 0324: NOT in fs objective -> out-of-sample full-traj
        jobs += [(ds, sub, MS.load_march(tdir, sub)) for sub in subs]
    if True:
        for ds, sub, td in jobs:
            pp = MS.get_prep((ds, sub), td, m, True)
            t = pp["t"]
            i0, ito = stance_range(td, t)
            t_to = t[ito]
            sim = replay(m, pp, i0, t_to + 0.6, xd)
            stm = (sim[:, 0] >= t[i0]) & (sim[:, 0] <= t_to)
            msk = (t >= t[i0]) & (t <= t_to)
            q2s = np.interp(t[msk], sim[:, 0], sim[:, 3])
            dq2s = np.interp(t[msk], sim[:, 0], sim[:, 4])
            rq2 = float(np.sqrt(np.mean((q2s - pp["q2m"][msk]) ** 2)))
            rdq2 = float(np.sqrt(np.mean((dq2s - pp["dq2m"][msk]) ** 2)))
            wm = (t >= t_to - 0.08) & (t <= t_to)
            wms = (sim[:, 0] >= t_to - 0.08) & (sim[:, 0] <= t_to)
            whip = float(np.max(np.abs(sim[wms, 4])) / max(np.max(np.abs(pp["dq2m"][wm])), 1e-9))
            vto = float(np.interp(t_to, sim[:, 0], sim[:, 2]))
            apex = float(np.max(sim[:, 1]) - pp["bz"][i0])
            rows.append(dict(ds=ds, sub=str(sub), rq2=rq2, rdq2=rdq2, whip=whip, vto=vto, apex=apex))
    return rows


if __name__ == "__main__":
    _AP = apply_final()
    FRJ = json.load(open(REPO / "code/goal19/goal19_final_model.json"))["friction"]
    can = dict(c=0.0, vs=1.0, w=0.15, c_hip=0.0, fc_knee=FRJ["fc_knee"], fv_knee=FRJ["fv_knee"],
               fc_hip=FRJ["fc_hip"], fv_hip=FRJ["fv_hip"])
    cand = dict(can, c=3.0, vs=1.0, c_hip=0.2)
    configs = [("canonical", can), ("hand c3/vs1", cand)]
    if len(sys.argv) > 1:
        pj = json.load(open(sys.argv[1]))["params"]
        configs.append(("refit-best", {k: float(pj[k]) for k in can}))
    allr = {}
    for name, xd in configs:
        rows = run_config(name, xd)
        allr[name] = rows
        for dsn in ("jump_0424", "jump_0602", "jump_0324"):
            rs = [r for r in rows if r["ds"] == dsn]
            if not rs:
                continue
            print(f"[{name:>12}] {dsn:<10} q2 {np.mean([r['rq2'] for r in rs]):.4f} | "
                  f"dq2 {np.mean([r['rdq2'] for r in rs]):.3f} | whip x{np.mean([r['whip'] for r in rs]):.3f} | "
                  f"vto {np.mean([r['vto'] for r in rs]):.3f} | apex +{np.mean([r['apex'] for r in rs]):.3f}", flush=True)
    json.dump(allr, open(REPO / "code/goal21/fullstance_check.json", "w"), indent=1)
    print("saved fullstance_check.json")
