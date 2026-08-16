"""cl_fit2 리포트 — 게인표(label/reg/fit_old/fit2), 널-비율 재측정, 구간지표, 그림+GIF."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys, json, shutil
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import g22_p10_cl as CL
from g22_p10_pdlaw import SETS
from g22_p12_tradeoff import make_jac
from g22_p13_phases import phases
import g22_p10_anim as AN

RES = json.load(open(HERE / "fit2_result.json"))
OLD = json.load(open(HERE.parent / "p10_cl.json"))
PDLAW = json.load(open(HERE.parent / "p10_pdlaw.json"))
PHS = json.load(open(HERE.parent / "p13_phases.json"))
TRAJD = HERE / "traj"
OLDTRAJ = HERE.parent / "p10_cl_traj"
DST = Path((LEGACY_ROOT + "/g22_cl_fit2_results"))
(DST / "png").mkdir(parents=True, exist_ok=True)
(DST / "gif").mkdir(parents=True, exist_ok=True)


def reg_gains(ds, sub):
    v_h = "V2" if ds in ("jump_0324", "jump_position_0421") else "V1"
    v_k = "V3" if ds == "jump_0324" else v_h
    g1 = PDLAW[f"{ds}/{sub}/j1"][v_h]; g2 = PDLAW[f"{ds}/{sub}/j2"][v_k]
    return (g1["kp"], g1["kd"], g2["kp"], g2["kd"])


def main():
    CL.winit()
    model = AN.build_fourbar_model()
    a_vec = make_jac(model)
    cl_json = json.load(open(HERE.parent / "p10_cl.json"))

    print("=== 게인 비교: label / reg(회귀) / fit_old / fit2 (hip kp 기준) ===", flush=True)
    nulls = {}
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            key = f"{ds}/{sub}"
            if key not in RES:
                continue
            r = RES[key]
            gl = r["gains_label"]; gf2 = r["gains_fit2"]
            gr = reg_gains(ds, sub)
            gfo = OLD[key]["gains_fit"]
            print(f"{key:32s} hip kp {gl[0]:5.0f} | reg {gr[0]:6.1f} | old {gfo[0]:6.1f} | fit2 {gf2[0]:6.1f}"
                  f"   knee kp {gl[2]:5.0f} | {gr[2]:6.1f} | {gfo[2]:6.1f} | {gf2[2]:6.1f}", flush=True)
            # 널-비율 (fit2 − label, 스탠스)
            d = CL.load_trial_xlsx(ds, root, sub)
            t = d["t"]
            zL = np.load(OLDTRAJ / f"{ds}__{sub}__label.npz")
            zF = np.load(TRAJD / f"{ds}__{sub}__fit2.npz")
            g = lambda z, k: np.interp(t, z["t"], z[k])
            st = g(zL, "grf") > 5.0
            d1 = (g(zF, "sh1") - g(zL, "sh1"))[st]
            d2 = (g(zF, "sh2") - g(zL, "sh2"))[st]
            q1r, q2r = np.asarray(d["q1"])[st], np.asarray(d["q2"])[st]
            num = den = 0.0
            a = None
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
            # 그림 (표준 6-패널, fit2 태그)
            L = {k: zF[k] for k in ["t", "q1", "q2", "dq1", "dq2", "sh1", "sh2", "grf", "bz"]}
            L["o"] = tuple(zF["o"])
            m = dict(r["metrics"])
            m["h_real"] = CL._L["hmap"].get((ds, sub), float("nan"))
            m["tau1_pk"] = tuple(m["tau1_pk"]); m["tau2_pk"] = tuple(m["tau2_pk"])
            CL.PNGD = DST / "png"
            CL.fig_trial(ds, sub, d, L, m, "fit2")

    print("\n=== 널-비율 (fit2−label Δτ 중 운동-불가시 성분, 스탠스) ===", flush=True)
    for ds in SETS:
        ks = [k for k in nulls if k.startswith(ds + "/")]
        if ks:
            print(f"{ds:22s} 중앙값 {np.median([nulls[k] for k in ks]):5.1f}%  "
                  f"(기존 fit: 78~99%)", flush=True)

    print("\n=== 구간 지표 중앙값: label / fit_old / fit2 ===", flush=True)
    for ds in SETS:
        ks = [f"{ds}/{s}" for s in SETS[ds][1] if f"{ds}/{s}" in RES]
        if not ks:
            continue
        line = f"[{ds}] "
        for seg, ch in [("push", "q1"), ("push", "dq2"), ("push", "tau1"), ("push", "tau2")]:
            lab = np.median([PHS[k]["label"][seg][ch] for k in ks if seg in PHS[k]["label"]])
            fo = np.median([PHS[k]["fit"][seg][ch] for k in ks if seg in PHS[k].get("fit", {})])
            f2 = np.median([RES[k]["detail"][seg][ch] for k in ks if seg in RES[k]["detail"]])
            line += f"{seg}.{ch} {lab:.3f}/{fo:.3f}/{f2:.3f}  "
        print(line, flush=True)

    # GIF 24 (canonical 4-bar 규격)
    print("\nGIF 렌더링...", flush=True)
    for f in sorted(TRAJD.glob("*__fit2.npz")):
        name = f.stem
        ds, sub, _ = name.split("__")
        hr = (cl_json.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real")
        AN.render_jump_cl(model, f, DST / "gif" / (name + ".gif"),
                          name.replace("__", " / "), h_real=hr)
    json.dump(nulls, open(HERE / "fit2_nullfrac.json", "w"), indent=1)
    print("DONE — 결과:", DST, flush=True)


if __name__ == "__main__":
    main()
