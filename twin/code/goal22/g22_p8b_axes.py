"""GOAL22 P8b — 역대 축 1-D 재검증 on P13f (dq-가중 후보).
P12.AXES (connect_solref/arm_hip/motor_tm/sens_delay/strib_knee/foot_dz/mu_floor)를
P13f 위에서 재스윕. KEEP 규칙: obj <= 0.98 AND ho <= 1.02."""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

OUT = Path(__file__).parent / "p8b_axes.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    return P12


def eval_ax(args):
    x32, mods = args
    if not P13._M:
        winit()
    P12 = P13._M["P12"]
    x32 = np.asarray(x32, float)
    m = dict(zip(P13.N6, x32[26:32])); m.update(mods)
    return P12.eval_p12((x32[:26], m))


def main():
    import multiprocessing as mp
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    x_f = np.array(json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))["x"])
    pool = mp.Pool(10, initializer=winit)
    base = eval_ax((x_f, {}))
    print("BASE(P13f):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)
    rows = {}
    for ax, vals in P12.AXES.items():
        rs = pool.map(eval_ax, [(x_f, {ax: v}) for v in vals])
        for v, r in zip(vals, rs):
            if r is None:
                print(f"  {ax}={v}: CRASH", flush=True)
                continue
            o = sum(r[g] / base[g] for g in G7)
            ho = r["fs_0324"] / base["fs_0324"]
            keep = "<<KEEP?" if (o <= 7.84 and ho <= 1.02) else ""
            rows.setdefault(ax, []).append(dict(v=v, obj=float(o), ho=float(ho),
                                                habs=float(r["habs"] / base["habs"])))
            print(f"  {ax}={v}: obj={o:.4f} ho={ho:.3f} habs={r['habs']/base['habs']:.3f} {keep}",
                  flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
