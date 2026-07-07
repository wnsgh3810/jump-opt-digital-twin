"""GOAL22 최종 비교표 — P13e / P13f(W150) / P13g(W300) / P13h(W150+sd-1.5ms 재적합).
표준 심판(W_DQ=50) obj·ho + 갤러리 full-replay (P13h는 τ 타임라인 −1.5ms 보정 적용)."""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13
from g22_p8b_axes import winit, eval_ax

OUT = Path(__file__).parent / "g22_final_table.json"


def build_model(P12, x32):
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    xml = P13.apply_linkage_mods(xml, dict(zip(P13.N6, np.asarray(x32)[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


def gallery(P12, x32, sd=0.0):
    sys.path.insert(0, str(REPO / "code/goal19/phase11"))
    import mshoot_fourbar as FB
    model, dd = build_model(P12, x32)
    from collections import defaultdict
    G = defaultdict(lambda: np.zeros(7))
    for tr_ in P12._G["trials"]:
        ds, sub, td, isj = tr_["ds"], tr_["sub"], tr_["td"], tr_["isj"]
        if not isj:
            continue
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
        td2 = td
        if sd != 0.0:
            t = np.asarray(td["t"])
            td2 = dict(td)
            td2["tau1_real"] = np.interp(t - sd, t, np.asarray(td["tau1_real"]))
            td2["tau2_real"] = np.interp(t - sd, t, np.asarray(td["tau2_real"]))
        log = FB.run_jump_sim_fourbar(model, td2)
        if log is None:
            G[ds] += [1, 1, 10, 10, 0, 1, 1]
            continue
        tr = np.asarray(td["t"])
        mk = (log["t"] >= 0) & (log["t"] <= tr[-1])
        f = lambda a: np.interp(tr, log["t"][mk], a[mk])
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        hr = float(td.get("h_real", np.nan))
        G[ds] += [r(f(-log["q1"] - np.pi / 2), td["q1"] + o1), r(f(-log["q2"]), td["q2"] + o2),
                  r(f(-log["dq1"]), td["dq1"]), r(f(-log["dq2"]), td["dq2"]),
                  float(log["base_z"].max()), hr if np.isfinite(hr) else 0.0, 1]
    return {ds: dict(q1=g[0] / g[6], q2=g[1] / g[6], dq1=g[2] / g[6], dq2=g[3] / g[6],
                     h_ratio=g[4] / max(g[5], 1e-9)) for ds, g in G.items() if g[6]}


def main():
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    x_e = np.array(json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))["x"])
    x_f = np.array(json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))["x"])
    x_g = np.array(json.load(open(Path(__file__).parent / "p3_dqw300.json"))["selected"]["x"])
    x_h = np.array(json.load(open(Path(__file__).parent / "p8d_refit_sd.json"))["selected"]["x"])
    base = eval_ax((x_e, {}))
    tab = {}
    for tag, x, mods in [("P13e", x_e, {}), ("P13f", x_f, {}), ("P13g", x_g, {}),
                         ("P13h", x_h, {"sens_delay": -0.0015})]:
        r = eval_ax((x, mods))
        o = sum(r[g] / base[g] for g in G7)
        gal = gallery(P12, x, sd=mods.get("sens_delay", 0.0))
        tab[tag] = dict(obj=float(o), ho=float(r["fs_0324"] / base["fs_0324"]),
                        habs=float(r["habs"] / base["habs"]), gallery=gal)
        print(f"\n{tag}: 표준obj={o:.4f} ho={tab[tag]['ho']:.3f} habs={tab[tag]['habs']:.3f}", flush=True)
        for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
            b = gal[ds]
            print(f"  {ds:20s} q1 {b['q1']:.4f} q2 {b['q2']:.4f} dq1 {b['dq1']:.2f} "
                  f"dq2 {b['dq2']:.2f} h {b['h_ratio']:.3f}", flush=True)
    json.dump(tab, open(OUT, "w"), indent=1)
    print("\nsaved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
