# -*- coding: utf-8 -*-
"""G20 — headroom + T-N envelope check for the NLP optimal trajectory.

Q1 (headroom): how much higher can the robot jump with the NLP-optimal torque
profile vs the best trajectory it has actually executed? Apples-to-apples in the
SAME twin: twin(replay real tau, best 0602 trial) vs twin(replay NLP tau*).

Q2 (feasibility): does the NLP optimum demand operating points (|omega|, |tau|)
beyond anything the real robot has DEMONSTRATED across all 24 jump trials?
Data-driven envelope — no spec guessing: bin |omega|, take max |tau| demonstrated
per bin; count NLP points exceeding the demonstrated envelope (+18 Nm hard line).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
from load_31exp import list_experiments

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
NLP = np.load(REPO / "code/goal19/nlp_demo/traj_a1.0_k130000.npz")
OUTJ = REPO / "code/goal19/nlp_demo/headroom_results.json"
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")


def build_twin():
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    return mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))


def main():
    model = build_twin()
    # -- Q1: twin heights, all 0602 trials vs NLP --------------------------------
    rows = []
    for ds, sub, isj in list_experiments():
        if ds != "jump_0602":
            continue
        td = MS.LOADERS[ds](sub)
        log = FB.run_jump_sim_fourbar(model, td)
        if log is None:
            continue
        rows.append(dict(sub=sub, h_twin=float(log["base_z"].max()), h_real=float(td["h_real"])))
    rows.sort(key=lambda r: -r["h_twin"])
    best = rows[0]
    h_nlp_twin = 1.063
    print("0602 trials (twin replay):")
    for r in rows:
        print(f"  {r['sub']:<12} h_twin={r['h_twin']:.3f}  h_cam={r['h_real']:.3f}")
    print(f"\nBEST executed: {best['sub']}  twin {best['h_twin']:.3f} (cam {best['h_real']:.3f})")
    print(f"NLP optimal  : twin {h_nlp_twin:.3f}")
    dh = h_nlp_twin - best["h_twin"]
    print(f"HEADROOM (same twin, same limits): {dh*100:+.1f} cm "
          f"({100*(h_nlp_twin/best['h_twin']-1):+.1f}%)")
    # camera-scale estimate: twin under-predicts 0602 by ratio 0.941
    scale = best["h_real"] / best["h_twin"]
    print(f"camera-scale estimate: {best['h_real']:.3f} -> ~{h_nlp_twin*scale:.3f} m "
          f"({(h_nlp_twin*scale-best['h_real'])*100:+.1f} cm)")

    # -- Q2: demonstrated (|w|,|tau|) envelope over ALL jump trials ---------------
    W = {1: [], 2: []}; T = {1: [], 2: []}
    groups = [(ds, [s for d2, s, isj in list_experiments() if d2 == ds], MS.LOADERS[ds])
              for ds in MS.LOADERS]
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    for ds, subs, loader in groups:
        for sub in subs:
            td = loader(sub)
            W[1].append(np.abs(td["dq1"])); T[1].append(np.abs(td["tau1_real"]))
            W[2].append(np.abs(td["dq2"])); T[2].append(np.abs(td["tau2_real"]))
    for j in (1, 2):
        W[j] = np.concatenate(W[j]); T[j] = np.concatenate(T[j])

    nlp_w = {1: np.abs(NLP["dq1"]), 2: np.abs(NLP["dq2"])}
    nlp_t = {1: np.abs(NLP["tau1"]), 2: np.abs(NLP["tau2"])}
    stats = {}
    BINW = 2.0
    for j, nm in ((1, "hip"), (2, "knee")):
        edges = np.arange(0, max(W[j].max(), nlp_w[j].max()) + BINW, BINW)
        env = np.zeros(len(edges) - 1)
        for i in range(len(edges) - 1):
            m = (W[j] >= edges[i]) & (W[j] < edges[i + 1])
            env[i] = T[j][m].max() if m.any() else 0.0
        idx = np.clip(np.digitize(nlp_w[j], edges) - 1, 0, len(env) - 1)
        margin = nlp_t[j] - env[idx]
        n_out = int((margin > 0).sum())
        stats[nm] = dict(nlp_tau_max=float(nlp_t[j].max()), nlp_w_max=float(nlp_w[j].max()),
                         real_tau_max=float(T[j].max()), real_w_max=float(W[j].max()),
                         pts_beyond_demonstrated=n_out, n_pts=len(nlp_t[j]),
                         worst_exceed_Nm=float(max(0.0, margin.max())))
        print(f"\n[{nm}] NLP max|tau|={nlp_t[j].max():.1f} Nm @ max|w|={nlp_w[j].max():.1f} rad/s"
              f" | demonstrated max|tau|={T[j].max():.1f}, max|w|={W[j].max():.1f}"
              f" | beyond-envelope pts: {n_out}/{len(nlp_t[j])} (worst +{max(0.0,margin.max()):.1f} Nm)")

    # -- figure (default color cycle: real cloud C1 dots, NLP path C0) -----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, j, nm in ((axes[0], 1, "Hip"), (axes[1], 2, "Knee")):
        ax.plot(W[j][::17], T[j][::17], ".", ms=2, alpha=0.25, color="C1",
                label="real, all 24 trials")
        ax.plot(nlp_w[j], nlp_t[j], "-", lw=1.8, color="C0", label="NLP optimal")
        ax.axhline(18.0, ls="--", lw=1, color="C3", label="AK80-9 V2 peak 18 Nm")
        ax.set_xlabel("|joint speed| [rad/s]"); ax.set_ylabel("|torque| [Nm]")
        ax.set_title(f"{nm}: operating points vs demonstrated envelope")
        ax.legend(fontsize=8)
    fig.tight_layout()
    out_png = SCR / "viz_final" / "nlp_envelope_check.png"
    fig.savefig(out_png, dpi=110)
    print("\nfigure ->", out_png)
    json.dump(dict(trials_0602=rows, best_executed=best, h_nlp_twin=h_nlp_twin,
                   headroom_m=dh, camera_scale_est=h_nlp_twin * scale, envelope=stats),
              open(OUTJ, "w"), indent=1)
    print("saved", OUTJ)


if __name__ == "__main__":
    main()
