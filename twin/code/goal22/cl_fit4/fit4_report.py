"""cl_fit4 리포트 — label/fit1/fit2/fit4/fit4 5-변형 push 지표, 널-비율, 그림+GIF."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import g22_p10_cl as CL
from g22_p10_pdlaw import SETS
from g22_p12_tradeoff import make_jac
import g22_p10_anim as AN

RES = json.load(open(HERE / "fit4_result.json"))
F2 = json.load(open(HERE.parent / "cl_fit2/fit2_result.json"))
F3 = json.load(open(HERE.parent / "cl_fit3/fit3_result.json"))
PHS = json.load(open(HERE.parent / "p13_phases.json"))
TRAJD = HERE / "traj"
OLDTRAJ = HERE.parent / "p10_cl_traj"
DST = Path((LEGACY_ROOT + "/g22_cl_fit4_results"))
(DST / "png").mkdir(parents=True, exist_ok=True)
(DST / "gif").mkdir(parents=True, exist_ok=True)


def push_rmse(key, ch):
    """fit4 traj npz에서 push 구간 RMSE 직접 계산 (tau 포함)."""
    from g22_p13_phases import phases
    ds, sub = key.split("/")
    d = CL.load_trial_xlsx(ds, SETS[ds][0], sub)
    t = d["t"]
    on, toff = phases(d)
    z = np.load(TRAJD / f"{ds}__{sub}__fit4.npz")
    g = lambda k: np.interp(t, z["t"], z[k])
    o1, o2 = tuple(z["o"])
    tp1 = np.interp(t - CL.SD, t, d["tau1_paper"]); tp2 = np.interp(t - CL.SD, t, d["tau2_paper"])
    sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                tau1=g("sh1"), tau2=g("sh2"))
    reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"], tau1=tp1, tau2=tp2)
    sl = slice(on, min(toff, len(t)))
    return float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2)))


def main():
    CL.winit()
    model = AN.build_fourbar_model()
    a_vec = make_jac(model)
    cl_json = json.load(open(HERE.parent / "p10_cl.json"))
    nulls = {}
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            key = f"{ds}/{sub}"
            if key not in RES:
                continue
            d = CL.load_trial_xlsx(ds, root, sub)
            t = d["t"]
            zL = np.load(OLDTRAJ / f"{ds}__{sub}__label.npz")
            zF = np.load(TRAJD / f"{ds}__{sub}__fit4.npz")
            g = lambda z, k: np.interp(t, z["t"], z[k])
            st = g(zL, "grf") > 5.0
            d1 = (g(zF, "sh1") - g(zL, "sh1"))[st]
            d2 = (g(zF, "sh2") - g(zL, "sh2"))[st]
            q1r, q2r = np.asarray(d["q1"])[st], np.asarray(d["q2"])[st]
            num = den = 0.0; a = None
            for i in range(len(q1r)):
                if i % max(1, len(q1r) // 50) == 0:
                    a = a_vec(q1r[i], q2r[i])
                if a is None:
                    continue
                ah = a / np.linalg.norm(a)
                nh = np.array([-ah[1], ah[0]])
                v = np.array([d1[i], d2[i]])
                num += (v @ nh) ** 2; den += v @ v
            nulls[key] = 100.0 * num / max(den, 1e-12)
            L = {k: zF[k] for k in ["t", "q1", "q2", "dq1", "dq2", "sh1", "sh2", "grf", "bz"]}
            L["o"] = tuple(zF["o"])
            m = dict(RES[key]["metrics"])
            m["h_real"] = CL._L["hmap"].get((ds, sub), float("nan"))
            m["tau1_pk"] = tuple(m["tau1_pk"]); m["tau2_pk"] = tuple(m["tau2_pk"])
            CL.PNGD = DST / "png"
            CL.fig_trial(ds, sub, d, L, m, "fit4")
            print("fig", key, flush=True)

    print("\n=== push 지표 중앙값: label / fit1 / fit2 / fit3 / fit4 ===", flush=True)
    for ds in SETS:
        ks = [f"{ds}/{s}" for s in SETS[ds][1] if f"{ds}/{s}" in RES]
        if not ks:
            continue
        line = f"[{ds}] "
        for ch in ("q1", "dq2", "tau1", "tau2"):
            lab = np.median([PHS[k]["label"]["push"][ch] for k in ks if "push" in PHS[k]["label"]])
            f1 = np.median([PHS[k]["fit"]["push"][ch] for k in ks if "push" in PHS[k].get("fit", {})])
            f2 = np.median([F2[k]["detail"]["push"][ch] for k in ks if "push" in F2[k]["detail"]])
            f3 = np.median([F3[k]["detail"]["push"][ch] for k in ks if "push" in F3[k]["detail"]])
            f4 = np.median([push_rmse(k, ch) for k in ks])
            line += f"{ch} {lab:.3f}/{f1:.3f}/{f2:.3f}/{f3:.3f}/{f4:.3f}  "
        print(line, flush=True)
    print("\n=== 널-비율 (fit4−label) 중앙값 ===", flush=True)
    for ds in SETS:
        ks = [k for k in nulls if k.startswith(ds + "/")]
        if ks:
            print(f"{ds:22s} {np.median([nulls[k] for k in ks]):5.1f}%", flush=True)

    print("\nGIF 렌더링...", flush=True)
    for f in sorted(TRAJD.glob("*__fit4.npz")):
        name = f.stem
        ds, sub, _ = name.split("__")
        hr = (cl_json.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real")
        AN.render_jump_cl(model, f, DST / "gif" / (name + ".gif"),
                          name.replace("__", " / "), h_real=hr)
    json.dump(nulls, open(HERE / "fit4_nullfrac.json", "w"), indent=1)
    print("DONE — 결과:", DST, flush=True)


if __name__ == "__main__":
    main()
