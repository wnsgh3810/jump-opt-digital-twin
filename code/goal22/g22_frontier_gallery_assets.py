"""GOAL22 프런티어 갤러리 자산 — 24 trial full-replay: P13e vs P13f(W150) vs P13g(W300) vs 실측.
패널 q1/q2/GRF/dq1/dq2/base_z, 실측 구간만, Malgun Gothic (P13e 갤러리 규격 유지).
실측 표시 오프셋은 P13e 기준 (모델별 오프셋 차이는 ≤1° 수준)."""
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

REPO = Path(__file__).resolve().parents[2]
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
OUT = SCR / "g22_frontier_gallery"; (OUT / "png").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

PH.winit()
P12 = P13._M["P12"]
if P12._G["trials"] is None:
    P12.build_trials()
S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
import mshoot_fourbar as FB


def build_model(x32):
    x32 = np.asarray(x32)
    dd = dict(zip(FR.NAMES, x32[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, x32[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


x_e = np.array(json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))["x"])
x_f = np.array(json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))["x"])
x_g = np.array(json.load(open(Path(__file__).parent / "p3_dqw300.json"))["selected"]["x"])
x_h = np.array(json.load(open(Path(__file__).parent / "fourbar_p13h_candidate.json"))["x"])
# P13h는 계측 보정(sens_delay=-1.5ms) 전제 — replay 시 τ(t+1.5ms)
MODELS = [("P13e (현 canonical)", build_model(x_e), 0.0),
          ("P13f (dq-가중 150)", build_model(x_f), 0.0),
          ("P13g (dq-가중 300)", build_model(x_g), 0.0),
          ("P13h (계측보정 ★추천)", build_model(x_h), -0.0015)]
dd_e = MODELS[0][1][1]

index = []
for tr_ in P12._G["trials"]:
    ds, sub, td, isj = tr_["ds"], tr_["sub"], tr_["td"], tr_["isj"]
    if not isj:
        continue
    k1, k2 = P12.OFFKEY.get(ds, (None, None))
    o1 = dd_e.get(k1, 0.0) if k1 else 0.0; o2 = dd_e.get(k2, 0.0) if k2 else 0.0
    trt = np.asarray(td["t"])
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7.4))
    hs = []
    for nm, (m, _), sd in MODELS:
        td_in = td
        if sd != 0.0:
            tt = np.asarray(td["t"])
            td_in = dict(td)
            td_in["tau1_real"] = np.interp(tt - sd, tt, np.asarray(td["tau1_real"]))
            td_in["tau2_real"] = np.interp(tt - sd, tt, np.asarray(td["tau2_real"]))
        lg = FB.run_jump_sim_fourbar(m, td_in)
        if lg is None:
            print("crash", ds, sub, nm, flush=True)
            continue
        mk = (lg["t"] >= -0.05) & (lg["t"] <= trt[-1] + 0.01)
        ax[0, 0].plot(lg["t"][mk], np.degrees(-lg["q1"][mk] - np.pi / 2), lw=1.2, label=nm)
        ax[0, 1].plot(lg["t"][mk], np.degrees(-lg["q2"][mk]), lw=1.2, label=nm)
        ax[0, 2].plot(lg["t"][mk], lg["grf_z"][mk], lw=1.2, label=nm)
        ax[1, 0].plot(lg["t"][mk], -lg["dq1"][mk], lw=1.2, label=nm)
        ax[1, 1].plot(lg["t"][mk], -lg["dq2"][mk], lw=1.2, label=nm)
        ax[1, 2].plot(lg["t"][mk], lg["base_z"][mk], lw=1.2, label=nm)
        hs.append(float(lg["base_z"].max()))
    ax[0, 0].plot(trt, np.degrees(np.asarray(td["q1"]) + o1), ls="--", lw=1.7, label="실측 (+off)")
    ax[0, 1].plot(trt, np.degrees(np.asarray(td["q2"]) + o2), ls="--", lw=1.7, label="실측 (+off)")
    grf_r = np.asarray(td.get("grf_z", []))
    if len(grf_r) == len(trt):
        ax[0, 2].plot(trt, grf_r, ls="--", lw=1.7, label="실측")
    ax[1, 0].plot(trt, np.asarray(td["dq1"]), ls="--", lw=1.7, label="실측")
    ax[1, 1].plot(trt, np.asarray(td["dq2"]), ls="--", lw=1.7, label="실측")
    hr = float(td.get("h_real", np.nan))
    if np.isfinite(hr):
        ax[1, 2].axhline(hr, ls=":", lw=1.1)
        ax[1, 2].text(0.02, hr, f" h_real {hr:.2f}", va="bottom", fontsize=8)
    ax[0, 0].set_ylabel("q1 hip [deg]"); ax[0, 1].set_ylabel("q2 knee [deg]")
    ax[0, 2].set_ylabel("GRF z [N]")
    ax[1, 0].set_ylabel("dq1 hip [rad/s]"); ax[1, 1].set_ylabel("dq2 knee [rad/s]")
    ax[1, 2].set_ylabel("base z [m]")
    for a in ax.flat:
        a.grid(alpha=0.3); a.set_xlabel("t [s]"); a.set_xlim(-0.05, trt[-1] + 0.01)
    ax[0, 0].legend(fontsize=7)
    fig.suptitle(f"{ds} / {sub} — 프런티어 full-replay (실측 구간)")
    fig.tight_layout()
    png = OUT / "png" / f"{ds}__{sub}.png"
    fig.savefig(png, dpi=105); plt.close(fig)
    index.append(dict(ds=ds, sub=str(sub), png=png.name,
                      h=[round(h, 3) for h in hs],
                      h_real=hr if np.isfinite(hr) else None))
    print("done", ds, sub, flush=True)
json.dump(index, open(OUT / "index.json", "w"), indent=1)
print(f"ASSETS DONE: {len(index)} trials", flush=True)
