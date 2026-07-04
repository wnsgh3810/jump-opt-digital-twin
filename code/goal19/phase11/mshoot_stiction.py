"""G20 — TRUE static friction (stiction) identified from held-out s2s_air.

Air held-out exposed a regime the fit never sampled: the real leg HOLDS position in
air with tau ~0.04 Nm while gravity demands ~0.3-1.0 Nm — gearbox stiction and/or the
CVT lead-screw in the crank is (partially) non-backdrivable. The old Stribeck test
(G20-C) injected smooth tanh friction which produces ZERO torque at v=0 — it could
never hold a static load, so it was blind to this.

Correct mechanism (hybrid):
  - XML frictionloss = fs  (MuJoCo solves it as a constraint -> true stiction)
  - eval-loop ASSIST torque  +(fs - fc_r1)*tanh(v/VS)  added to the commanded tau,
    cancelling the excess when moving  ->  net kinetic friction returns to the
    round-1 Coulomb (fc_hip 0.169 / fc_knee 0.057) that the jump/gnd fit demands.
  Net model: static fs at v=0, smooth decay to round-1 fc at |v| >~ VS (Stribeck).

Part 1: grid (fs_h, fs_k) on air cycles (this is now a FIT on air).
Part 2: GUARD — full jump+s2s_gnd window metric with the same hybrid vs round-1
        baseline. Keep only if guard degradation < 1%.
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
import mshoot_fourbar as FB
import mshoot_fourbar_refit as FR
from mshoot_dateoff import prep_with_grad, shifted_view
from mshoot_s2s_air_holdout import load_air_cycles, prep_air, air_xml_fourbar

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
VS = 0.1   # [rad/s] assist smoothing — well below motion speeds (1-20 rad/s)


def set_globals(fs_h, fs_k):
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]
    S.FC_HIP = fs_h; S.FC_KNEE = fs_k          # frictionloss = static level
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0


def assists(fs_h, fs_k, v1, v2):
    a_h = (fs_h - BD["fc_hip"]) * np.tanh(v1 / VS)
    a_k = (fs_k - BD["fc_knee"]) * np.tanh(v2 / VS)
    return a_h, a_k


def eval_windows_hyb(model, pp, fs_h, fs_k, fourbar=True, has_bz=True):
    d = mujoco.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    out = []
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        if has_bz:
            d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
            d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
            j1, j2 = 1, 2
        else:
            d.qpos[:] = [pp["q1m"][i0], q2, -q2, q2]
            d.qvel[:] = [pp["dq1m"][i0], dq2, -dq2, dq2]
            j1, j2 = 0, 1
        mujoco.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            a_h, a_k = assists(fs_h, fs_k, d.qvel[j1], d.qvel[j2])
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]) + a_h,
                         np.interp(tc, t, pp["tau_k"]) + a_k]
            try:
                mujoco.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[j1]; q2a[k] = d.qpos[j2]
            dq1a[k] = d.qvel[j1]; dq2a[k] = d.qvel[j2]
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


def air_score(fs_h, fs_k, cycles):
    set_globals(fs_h, fs_k)
    m = mujoco.MjModel.from_xml_string(air_xml_fourbar(BD["arm_knee"], BD))
    tot = 0.0; acc = np.zeros(4); nw = 0
    for td in cycles:
        pp = prep_air(td, BD["o1_0319"], BD["o2_0319"])
        wins = eval_windows_hyb(m, pp, fs_h, fs_k, has_bz=False)
        tot += MS.window_score(wins); nw += len(wins)
        for w in wins:
            acc += [w["rq1"], w["rq2"], w["rdq1"], w["rdq2"]]
    return tot, acc / max(nw, 1)


def guard_score(fs_h, fs_k):
    """Full fit metric (jump + s2s_gnd windows) with the hybrid."""
    set_globals(fs_h, fs_k)
    model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))
    mj, mg = FR.get_serial_models()
    total = 0.0
    for ds, subs, loader, isj in FR.all_groups():
        k1, k2 = FR.OFFKEY.get(ds, (None, None))
        o1 = BD[k1] if k1 else 0.0; o2 = BD[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            pp = prep_with_grad((ds, sub), td, mj if isj else mg)
            total += MS.window_score(
                eval_windows_hyb(model, shifted_view(pp, o1, o2), fs_h, fs_k))
    return total


def main():
    cycles = load_air_cycles()
    grid_cyc = cycles[:5]
    base_air, mb = air_score(BD["fc_hip"], BD["fc_knee"], grid_cyc)   # fs=fc -> assist=0
    print(f"AIR baseline (fs=fc r1): {base_air:.0f}  q2={mb[1]:.3f} dq2={mb[3]:.2f}", flush=True)
    best = (BD["fc_hip"], BD["fc_knee"], base_air)
    for fs_h in [0.5, 1.0, 1.5, 2.5]:
        for fs_k in [0.5, 1.0, 2.0, 3.0]:
            sc, m = air_score(fs_h, fs_k, grid_cyc)
            tag = " <-- best" if sc < best[2] else ""
            print(f"fs=({fs_h:.1f},{fs_k:.1f}): air={sc:7.0f}  q2={m[1]:.3f} dq2={m[3]:.2f}{tag}", flush=True)
            if sc < best[2]:
                best = (fs_h, fs_k, sc)
    fs_h, fs_k, _ = best
    print(f"\nBEST fs=({fs_h},{fs_k}) -> full-15-cycle air + guard...", flush=True)
    a_full, ma = air_score(fs_h, fs_k, cycles)
    a_base, mb2 = air_score(BD["fc_hip"], BD["fc_knee"], cycles)
    g_new = guard_score(fs_h, fs_k)
    g_base = guard_score(BD["fc_hip"], BD["fc_knee"])
    print(f"AIR  15cyc: {a_base:.0f} -> {a_full:.0f} ({100*(a_full/a_base-1):+.1f}%)  "
          f"q2 {mb2[1]:.3f}->{ma[1]:.3f}  dq2 {mb2[3]:.2f}->{ma[3]:.2f}")
    print(f"GUARD (jump+gnd fit metric): {g_base:.0f} -> {g_new:.0f} ({100*(g_new/g_base-1):+.1f}%)")
    verdict = "KEEP (regime extension)" if g_new < g_base * 1.01 else "DROP (hurts primary regime)"
    print("VERDICT:", verdict)
    json.dump(dict(fs_h=fs_h, fs_k=fs_k, VS=VS, air_base=a_base, air_new=a_full,
                   guard_base=g_base, guard_new=g_new, verdict=verdict),
              open(REPO / "code/goal19/phase11/stiction_best.json", "w"), indent=1)


if __name__ == "__main__":
    main()
