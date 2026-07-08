"""P13i vs P13h 삼중 채점: (1) 폐루프 심판 데이터셋별 분해(+원시 τ RMSE),
(2) 갤러리 full-replay, (3) Mode A 표준 obj (W_DQ=50, sens_delay 고정)."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import p13i_judge as J
from g22_p10_cl import SD

OUT = HERE / "p13i_compare.json"


def cl_breakdown(x32):
    model, dd = J.build_model(x32)
    per = {}
    for tr in J._J["trials"]:
        L = J.run_cl(model, dd, tr)
        if L is None:
            continue
        s = J.trial_score(L, tr)
        d = tr["d"]; t = d["t"]
        g = lambda k: np.interp(t, L["t"], L[k])
        sl = slice(tr["on"], min(tr["toff"], len(t)))
        tp1 = np.interp(t - SD, t, d["tau1_paper"])[sl]
        tp2 = np.interp(t - SD, t, d["tau2_paper"])[sl]
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        o1, o2 = L["o"]
        p = per.setdefault(tr["ds"], [])
        p.append(dict(score=s,
                      tau1=r(g("sh1")[sl], tp1), tau2=r(g("sh2")[sl], tp2),
                      q1=r(g("q1")[sl] - o1, np.asarray(d["q1"])[sl]),
                      dq2=r(g("dq2")[sl], np.asarray(d["dq2"])[sl])))
    return {ds: {k: float(np.mean([x[k] for x in v])) for k in v[0]}
            for ds, v in per.items()}


def main():
    J.winit()
    x_h = np.array(json.load(open(HERE.parent / "fourbar_p13h_candidate.json"))["x"])
    x_i = np.array(json.load(open(HERE / "fourbar_p13i_candidate.json"))["x"])
    print("=== (1) 폐루프 심판 — 푸시 구간 원시 RMSE (P13h -> P13i) ===", flush=True)
    bh = cl_breakdown(x_h); bi = cl_breakdown(x_i)
    for ds in bh:
        a, b = bh[ds], bi[ds]
        print(f"{ds:22s} score {a['score']:.3f}->{b['score']:.3f}  "
              f"tau1 {a['tau1']:.2f}->{b['tau1']:.2f}  tau2 {a['tau2']:.2f}->{b['tau2']:.2f}  "
              f"q1 {a['q1']:.3f}->{b['q1']:.3f}  dq2 {a['dq2']:.2f}->{b['dq2']:.2f}", flush=True)

    # (2)+(3): 갤러리 + Mode A 표준 obj (기존 하네스)
    from g22_p8b_axes import eval_ax
    import g22_final_table as FT
    P12 = J._J["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    G7 = P12.OBJ_GROUPS
    REPO = HERE.parents[2]
    x_e = np.array(json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))["x"])
    base = eval_ax((x_e, {}))
    res = {}
    print("\n=== (2)(3) Mode A 표준 obj + 갤러리 full-replay ===", flush=True)
    for tag, x in [("P13h", x_h), ("P13i", x_i)]:
        r = eval_ax((x, {"sens_delay": -0.0015}))
        o = sum(r[g] / base[g] for g in G7)
        gal = FT.gallery(P12, x, sd=-0.0015)
        res[tag] = dict(obj_std=float(o), ho=float(r["fs_0324"] / base["fs_0324"]), gallery=gal)
        print(f"{tag}: ModeA obj={o:.4f} ho={r['fs_0324']/base['fs_0324']:.3f}", flush=True)
        for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
            g_ = gal[ds]
            print(f"  {ds:20s} q1 {g_['q1']:.4f} q2 {g_['q2']:.4f} dq1 {g_['dq1']:.2f} "
                  f"dq2 {g_['dq2']:.2f} h {g_['h_ratio']:.3f}", flush=True)
    res["cl_h"] = bh; res["cl_i"] = bi
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print("saved", OUT.name, flush=True)


if __name__ == "__main__":
    main()
