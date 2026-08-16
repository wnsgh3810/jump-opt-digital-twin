"""P6 visual report — full-replay traces: real vs canonical vs a_hat variants.
One figure per date (representative trial), panels: q1, q2, dq2, base height.
Colors: matplotlib auto cycle (no explicit colors); real = dashed.
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
sys.path.insert(0, str(REPO / "code/goal21"))
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_fourbar as FB
from g21_ahat_refit import invert_ahat, ahat_fwd, AH0

CAN = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
NAMES = CAN["names"]
SA = json.load(open(REPO / "code/goal21/ahat_stageA.json"))
bestB = None
for ln in open(REPO / "code/goal21/ahat_cands.jsonl"):
    c = json.loads(ln)
    if c["heldout"] <= 1.0 and (bestB is None or c["obj"] < bestB["obj"]):
        bestB = c

CONFIGS = [
    ("canonical (paper a_hat)", CAN["x"], AH0),
    ("Stage-A a_hat-only", CAN["x"], SA["ah"]),
    ("Stage-B selected", bestB["x"][:26], bestB["x"][26:]),
]
OFFDS = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
         "jump_0424": ("o1_0424", "o2_0424")}
TRIALS = [
    ("jump_0424", "120_2_120_2"),
    ("jump_0602", "120_2_120_2"),
    ("jump_0324", "P60_D1.5"),
    ("jump_position_0421", "P60_D0.75_P60_D2"),
]


def load_td(ds, sub):
    if ds in MS.LOADERS:
        return MS.LOADERS[ds](sub)
    for d2, tdir, subs in MS.MARCH:
        if d2 == ds:
            return MS.load_march(tdir, sub)


def replay(x26, ah, td):
    dd = dict(zip(NAMES, x26))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    model = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(dd["arm_knee"], dd))
    a0, a1, a2, a3h, a4h, a3k, a4k = ah
    v1 = np.asarray(td["dq1"], float); v2 = np.asarray(td["dq2"], float)
    Iq1 = invert_ahat(np.asarray(td["tau1_real"], float), v1)
    Iq2 = invert_ahat(np.asarray(td["tau2_real"], float), v2)
    tdv = dict(td)
    tdv["tau1_real"] = ahat_fwd(Iq1, v1, a0, a1, a2, a3h, a4h)
    tdv["tau2_real"] = ahat_fwd(Iq2, v2, a0, a1, a2, a3k, a4k)
    return FB.run_jump_sim_fourbar(model, tdv), dd


for ds, sub in TRIALS:
    td = load_td(ds, sub)
    tr = np.asarray(td["t"])
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    logs = []
    for name, x26, ah in CONFIGS:
        log, dd = replay(x26, ah, td)
        k1, k2 = OFFDS.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        logs.append((name, log, o1, o2))
    # panels: sims first (solid), real last (dashed)
    for name, log, o1, o2 in logs:
        mk = log["t"] >= -0.05
        ax[0, 0].plot(log["t"][mk], np.degrees(-log["q1"][mk] - np.pi / 2), lw=1.4, label=name)
        ax[0, 1].plot(log["t"][mk], np.degrees(-log["q2"][mk]), lw=1.4, label=name)
        ax[1, 0].plot(log["t"][mk], -log["dq2"][mk], lw=1.4, label=name)
        ax[1, 1].plot(log["t"][mk], log["base_z"][mk], lw=1.4, label=name)
    o1c, o2c = logs[0][2], logs[0][3]   # canonical offsets for real display
    ax[0, 0].plot(tr, np.degrees(np.asarray(td["q1"]) + o1c), ls="--", lw=1.8, label="real (+off)")
    ax[0, 1].plot(tr, np.degrees(np.asarray(td["q2"]) + o2c), ls="--", lw=1.8, label="real (+off)")
    ax[1, 0].plot(tr, np.asarray(td["dq2"]), ls="--", lw=1.8, label="real")
    hr = float(td.get("h_real", np.nan))
    if np.isfinite(hr):
        ax[1, 1].axhline(hr, ls=":", lw=1.2)
        ax[1, 1].text(0.02, hr, f" h_real {hr:.2f} m", va="bottom", fontsize=8)
    ax[0, 0].set_ylabel("q1 hip [deg]"); ax[0, 1].set_ylabel("q2 knee [deg]")
    ax[1, 0].set_ylabel("dq2 knee [rad/s]"); ax[1, 1].set_ylabel("base height [m]")
    for a in ax.flat:
        a.set_xlabel("t [s]"); a.grid(alpha=0.3)
    ax[0, 0].legend(fontsize=8, loc="best")
    fig.suptitle(f"P6 full-replay — {ds} / {sub}  (open-loop tau replay incl. settle)")
    fig.tight_layout()
    out = REPO / f"code/goal21/p6_replay_{ds}_{sub}.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("saved", out.name, flush=True)
