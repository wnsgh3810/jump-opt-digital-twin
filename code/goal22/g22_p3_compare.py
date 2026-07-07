"""P3 후속 — P13e vs P13f(dq-가중 선택해) 표준 심판 + 갤러리 full-replay 정면 비교.
표준 가중(W_DQ=50) obj + 데이터셋별 full-replay q/dq RMSE + h_ratio → (dq, h) 프런티어."""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

OUT = Path(__file__).parent / "p3_compare.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    return P12


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


def gallery_judge(P12, x32):
    """full-replay per-ds q1/q2/dq1/dq2 RMSE + h_ratio (P13e 갤러리 관례)."""
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
        log = FB.run_jump_sim_fourbar(model, td)
        if log is None:
            G[ds] += [1, 1, 10, 10, 0, 1, 1]
            continue
        tr = np.asarray(td["t"])
        mk = (log["t"] >= 0) & (log["t"] <= tr[-1])
        f = lambda a: np.interp(tr, log["t"][mk], a[mk])
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        hr = float(td.get("h_real", np.nan))
        G[ds] += [r(f(-log["q1"] - np.pi / 2), td["q1"] + o1),
                  r(f(-log["q2"]), td["q2"] + o2),
                  r(f(-log["dq1"]), td["dq1"]),
                  r(f(-log["dq2"]), td["dq2"]),
                  float(log["base_z"].max()), hr if np.isfinite(hr) else 0.0, 1]
    out = {}
    for ds, g in G.items():
        n = g[6]
        out[ds] = dict(q1=g[0] / n, q2=g[1] / n, dq1=g[2] / n, dq2=g[3] / n,
                       h_ratio=g[4] / max(g[5], 1e-9))
    return out


def main():
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x_e = np.array(can["x"])
    p3 = json.load(open(Path(__file__).parent / "p3_dqw150.json"))
    x_f = np.array(p3["selected"]["x"])

    base = PH.eval32(x_e)                       # 표준 W_DQ=50
    r_f = PH.eval32(x_f)
    o_f = sum(r_f[g] / base[g] for g in G7)
    print(f"표준 심판(W_DQ=50): P13e obj=8.0000  P13f obj={o_f:.4f} "
          f"ho={r_f['fs_0324']/base['fs_0324']:.3f} habs={r_f['habs']/base['habs']:.3f}", flush=True)

    ge = gallery_judge(P12, x_e)
    gf = gallery_judge(P12, x_f)
    print("\n=== 갤러리 full-replay (P13e -> P13f) ===")
    for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
        a, b = ge[ds], gf[ds]
        print(f"{ds:20s} q1 {a['q1']:.4f}->{b['q1']:.4f}  q2 {a['q2']:.4f}->{b['q2']:.4f}  "
              f"dq1 {a['dq1']:.2f}->{b['dq1']:.2f}  dq2 {a['dq2']:.2f}->{b['dq2']:.2f}  "
              f"h {a['h_ratio']:.3f}->{b['h_ratio']:.3f}", flush=True)
    json.dump(dict(obj_std_f=float(o_f), ho_f=float(r_f["fs_0324"] / base["fs_0324"]),
                   gallery_e=ge, gallery_f=gf, x_f=[float(v) for v in x_f]),
              open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
