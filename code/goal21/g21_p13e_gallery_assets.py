"""P13e 갤러리 자산 — 24 trial full-replay: P10(flip, 유령질량) vs P13e(정직물리) vs 실측.
패널: q2 / dq2 / dq1 / base height. 실측 오프셋은 P13e(물리 ≤3°) 기준."""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import mujoco

REPO = Path(__file__).resolve().parents[2]
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
OUT = SCR / "p13e_gallery"; (OUT / "png").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13_linkage as P13
P13.winit()
P12 = P13._M["P12"]; FB = P12._G["FB"]; S = P12._G["S"]
import g21_fourbar_flip as FL
import mshoot as MS
from load_31exp import list_experiments

P10 = json.load(open(REPO / "code/goal21/fourbar_flip_canonical.json"))
P13E = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
OFF = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
       "jump_0424": ("o1_0424", "o2_0424")}


def build_model(cfg, honest):
    dd = dict(zip(cfg["names"], cfg["x"]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd)
    if honest:
        sc["TOTAL_MASS"] = 3.2
        xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                     {n: dd[n] for n in P13.N6})
    else:
        xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    return mujoco.MjModel.from_xml_string(xml), dd


m10, dd10 = build_model(P10, honest=False)
m13, dd13 = build_model(P13E, honest=True)

groups = []
for ds in MS.LOADERS:
    subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
    groups.append((ds, subs, MS.LOADERS[ds]))
for ds, tdir, subs in MS.MARCH:
    groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))

index = []
for ds, subs, loader in groups:
    k1, k2 = OFF.get(ds, (None, None))
    o1 = dd13[k1] if k1 else 0.0; o2 = dd13[k2] if k2 else 0.0
    for sub in subs:
        td = loader(sub)
        tr = np.asarray(td["t"])
        logs = []
        for nm, m in [("P13e (정직물리)", m13)]:
            lg = FB.run_jump_sim_fourbar(m, td)
            if lg is None:
                print("crash", ds, sub, nm); break
            logs.append((nm, lg))
        if len(logs) < 1:
            continue
        fig, ax = plt.subplots(2, 3, figsize=(14.5, 7.4))
        for nm, lg in logs:
            mk = (lg["t"] >= -0.05) & (lg["t"] <= tr[-1] + 0.01)
            ax[0, 0].plot(lg["t"][mk], np.degrees(-lg["q1"][mk] - np.pi / 2), lw=1.3, label=nm)
            ax[0, 1].plot(lg["t"][mk], np.degrees(-lg["q2"][mk]), lw=1.3, label=nm)
            ax[0, 2].plot(lg["t"][mk], lg["grf_z"][mk], lw=1.3, label=nm)
            ax[1, 0].plot(lg["t"][mk], -lg["dq1"][mk], lw=1.3, label=nm)
            ax[1, 1].plot(lg["t"][mk], -lg["dq2"][mk], lw=1.3, label=nm)
            ax[1, 2].plot(lg["t"][mk], lg["base_z"][mk], lw=1.3, label=nm)
        ax[0, 0].plot(tr, np.degrees(np.asarray(td["q1"]) + o1), ls="--", lw=1.7, label="실측 (+off)")
        ax[0, 1].plot(tr, np.degrees(np.asarray(td["q2"]) + o2), ls="--", lw=1.7, label="실측 (+off)")
        grf_r = np.asarray(td.get("grf_z", []))
        if len(grf_r) == len(tr):
            ax[0, 2].plot(tr, grf_r, ls="--", lw=1.7, label="실측")
        ax[1, 0].plot(tr, np.asarray(td["dq1"]), ls="--", lw=1.7, label="실측")
        ax[1, 1].plot(tr, np.asarray(td["dq2"]), ls="--", lw=1.7, label="실측")
        hr = float(td.get("h_real", np.nan))
        if np.isfinite(hr):
            ax[1, 2].axhline(hr, ls=":", lw=1.1)
            ax[1, 2].text(0.02, hr, f" h_real {hr:.2f}", va="bottom", fontsize=8)
        ax[0, 0].set_ylabel("q1 hip [deg]"); ax[0, 1].set_ylabel("q2 knee [deg]")
        ax[0, 2].set_ylabel("GRF z [N]")
        ax[1, 0].set_ylabel("dq1 hip [rad/s]"); ax[1, 1].set_ylabel("dq2 knee [rad/s]")
        ax[1, 2].set_ylabel("base z [m]")
        for a in ax.flat:
            a.grid(alpha=0.3); a.set_xlabel("t [s]"); a.set_xlim(-0.05, tr[-1] + 0.01)
        ax[0, 0].legend(fontsize=7.5)
        fig.suptitle(f"{ds} / {sub} — P13e 정직물리 full-replay (실측 구간)")
        fig.tight_layout()
        png = OUT / "png" / f"{ds}__{sub}.png"
        fig.savefig(png, dpi=110); plt.close(fig)
        index.append(dict(ds=ds, sub=str(sub), png=png.name,
                          h13=float(logs[0][1]["base_z"].max()),
                          h_real=hr if np.isfinite(hr) else None))
        print("done", ds, sub, flush=True)
json.dump(index, open(OUT / "index.json", "w"), indent=1)
print(f"ASSETS DONE: {len(index)} trials")
