# -*- coding: utf-8 -*-
"""P17b — com_dz_th 케이지 초과 스윕 (관찰용, 채택 아님).

3연속 +3cm 상한 추격이 어디까지 가고 싶어하는지, 가면 무엇이 좋아지는지 확인.
+dz = thigh CoM이 무릎 쪽으로 이동. P16 스택 고정, dz만 치환, 이중 심판.
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from p16a_spring import build_with_ref

G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X16 = np.array(C16["x"])
REF = float(X16[36])
IDX = C16["names"].index("com_dz_th")
OUT = HERE / "p17_dz_sweep.json"


def winit():
    J.winit()
    J.build_model = lambda x32: build_with_ref(x32, REF)


def eval_dz(dz):
    try:
        if not J._P:
            winit()
        x = X16[:36].copy()
        x[IDX] = dz
        ra = J.eval_modeA(x)
        jc, jcg = J.eval_cl(x)
        return dict(dz=float(dz), A={g: float(ra[g]) for g in G7},
                    fs0324=float(ra["fs_0324"]), C=float(jc), Cg=float(jcg))
    except Exception as e:
        return dict(dz=float(dz), err=str(e)[:80])


def main():
    import multiprocessing as mp
    winit()
    DZ = [0.0299, 0.04, 0.05, 0.06, 0.08, 0.10]
    pool = mp.Pool(6, initializer=winit)
    rs = pool.map(eval_dz, DZ)
    base = rs[0]
    print(f"기준 P16 (dz=+0.03, 현 케이지 상한): JC={base['C']:.4f}", flush=True)
    print(f"{'dz[m]':>7} {'JA':>8} {'JC':>8} {'dual':>7} {'hoA':>6} {'hoC':>6}", flush=True)
    rows = []
    for r in rs:
        if "err" in r:
            print(r["dz"], "ERR", r["err"], flush=True)
            continue
        ja = sum(r["A"][g] / base["A"][g] for g in G7) / len(G7)
        jc = r["C"] / base["C"]
        rows.append(dict(r, ja=float(ja), jc=float(jc)))
        print(f"{r['dz']:7.3f} {ja:8.4f} {jc:8.4f} {(ja+jc)/2:7.4f} "
              f"{r['fs0324']/base['fs0324']:6.3f} {r['Cg']/base['Cg']:6.3f}", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
