"""P7 gallery assets — ALL 24 jump trials:
  - 4-panel full-replay comparison PNG (canonical vs Stage-A a_hat vs real)
  - canonical-replay npz (t, q[N,3], grf_z) for the canonical GIF renderer
  - index.json (per-trial h_sim/h_real)
Outputs under scratchpad/p7_gallery/.
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

REPO = Path(__file__).resolve().parents[2]
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
OUT = SCR / "p7_gallery"; (OUT / "png").mkdir(parents=True, exist_ok=True)
(OUT / "npz").mkdir(exist_ok=True); (OUT / "gif").mkdir(exist_ok=True)

sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
from load_31exp import list_experiments
from g21_ahat_refit import invert_ahat, ahat_fwd, AH0

CAN = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
NAMES = CAN["names"]
SA = json.load(open(REPO / "code/goal21/ahat_stageA.json"))
OFFDS = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
         "jump_0424": ("o1_0424", "o2_0424")}
CONFIGS = [("canonical (paper a_hat)", AH0), ("Stage-A a_hat", SA["ah"])]


def replay(model, td, ah):
    a0, a1, a2, a3h, a4h, a3k, a4k = ah
    v1 = np.asarray(td["dq1"], float); v2 = np.asarray(td["dq2"], float)
    Iq1 = invert_ahat(np.asarray(td["tau1_real"], float), v1)
    Iq2 = invert_ahat(np.asarray(td["tau2_real"], float), v2)
    tdv = dict(td)
    tdv["tau1_real"] = ahat_fwd(Iq1, v1, a0, a1, a2, a3h, a4h)
    tdv["tau2_real"] = ahat_fwd(Iq2, v2, a0, a1, a2, a3k, a4k)
    return FB.run_jump_sim_fourbar(model, tdv)


def main():
    dd = dict(zip(NAMES, CAN["x"]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(dd["arm_knee"], dd))
    groups = []
    for ds in MS.LOADERS:
        subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
        groups.append((ds, subs, MS.LOADERS[ds]))
    for ds, tdir, subs in MS.MARCH:
        groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))
    index = []
    for ds, subs, loader in groups:
        k1, k2 = OFFDS.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        for sub in subs:
            td = loader(sub)
            tr = np.asarray(td["t"])
            logs = [(nm, replay(model, td, ah)) for nm, ah in CONFIGS]
            if any(l is None for _, l in logs):
                print("SKIP (crash)", ds, sub, flush=True)
                continue
            fig, ax = plt.subplots(2, 2, figsize=(11, 7.2))
            for nm, log in logs:
                mk = log["t"] >= -0.05
                ax[0, 0].plot(log["t"][mk], np.degrees(-log["q1"][mk] - np.pi / 2), lw=1.3, label=nm)
                ax[0, 1].plot(log["t"][mk], np.degrees(-log["q2"][mk]), lw=1.3, label=nm)
                ax[1, 0].plot(log["t"][mk], -log["dq2"][mk], lw=1.3, label=nm)
                ax[1, 1].plot(log["t"][mk], log["base_z"][mk], lw=1.3, label=nm)
            ax[0, 0].plot(tr, np.degrees(np.asarray(td["q1"]) + o1), ls="--", lw=1.7, label="real (+off)")
            ax[0, 1].plot(tr, np.degrees(np.asarray(td["q2"]) + o2), ls="--", lw=1.7, label="real (+off)")
            ax[1, 0].plot(tr, np.asarray(td["dq2"]), ls="--", lw=1.7, label="real")
            hr = float(td.get("h_real", np.nan))
            if np.isfinite(hr):
                ax[1, 1].axhline(hr, ls=":", lw=1.1)
                ax[1, 1].text(0.02, hr, f" h_real {hr:.2f} m", va="bottom", fontsize=8)
            ax[0, 0].set_ylabel("q1 hip [deg]"); ax[0, 1].set_ylabel("q2 knee [deg]")
            ax[1, 0].set_ylabel("dq2 [rad/s]"); ax[1, 1].set_ylabel("base z [m]")
            for a in ax.flat:
                a.grid(alpha=0.3); a.set_xlabel("t [s]")
            ax[0, 0].legend(fontsize=7.5)
            fig.suptitle(f"{ds} / {sub} — full-replay (open-loop tau)")
            fig.tight_layout()
            png = OUT / "png" / f"{ds}__{sub}.png"
            fig.savefig(png, dpi=110); plt.close(fig)
            # canonical npz for renderer
            log = logs[0][1]
            mk = log["t"] >= -0.10
            q = np.stack([log["base_z"][mk], log["q1"][mk], log["q2"][mk]], axis=1)
            np.savez(OUT / "npz" / f"{ds}__{sub}.npz",
                     t=log["t"][mk], q=q, grf_z=log["grf_z"][mk])
            index.append(dict(ds=ds, sub=str(sub), png=png.name,
                              h_sim=float(log["base_z"].max()),
                              h_real=hr if np.isfinite(hr) else None))
            print("done", ds, sub, flush=True)
    json.dump(index, open(OUT / "index.json", "w"), indent=1)
    print(f"ASSETS DONE: {len(index)} trials", flush=True)


if __name__ == "__main__":
    main()
