"""GOAL22 P8 — 레일 Coulomb 마찰 축 (P5 정적 발견 후속).

P5: 크라우치 정적 τ 불일치 ~3-4Nm → 레일 스틱션이 하중 일부를 부담한다는 증거.
MuJoCo base_z slide joint에 frictionloss[N]을 넣어 축 스윕 (P13e·P13f 각각):
창/held-out/habs 반응 확인. 유망하면 rail_fc 자유화한 미니 재적합(P13h).
"""
import sys, json
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

OUT = Path(__file__).parent / "p8_railfc.json"


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    orig = P12.apply_xml_mods

    def patched(xml, mods):
        xml = orig(xml, mods)
        rf = mods.get("rail_fc", 0.0)
        if rf > 0:
            xml = xml.replace('<joint name="base_z" type="slide" axis="0 0 1"/>',
                              f'<joint name="base_z" type="slide" axis="0 0 1" frictionloss="{rf:.4f}"/>')
        return xml

    P12.apply_xml_mods = patched
    if P12._G["trials"] is None:
        P12.build_trials()
    return P12


def eval_rail(args):
    x32, rf = args
    if not P13._M:
        winit()
    P12 = P13._M["P12"]
    x32 = np.asarray(x32, float)
    mods = dict(zip(P13.N6, x32[26:32]))
    if rf > 0:
        mods["rail_fc"] = rf
    return P12.eval_p12((x32[:26], mods))


def main():
    import multiprocessing as mp
    P12 = winit()
    G7 = P12.OBJ_GROUPS
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x_e = np.array(can["x"])
    p13f = json.load(open(Path(__file__).parent / "fourbar_p13f_candidate.json"))
    x_f = np.array(p13f["x"])
    pool = mp.Pool(10, initializer=winit)
    FS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    rows = {}
    for tag, x in [("P13e", x_e), ("P13f", x_f)]:
        rs = pool.map(eval_rail, [(x, f) for f in FS])
        base = rs[0]
        print(f"\n=== {tag} + rail_fc 스윕 (기준 rf=0) ===", flush=True)
        print(f"{'rf[N]':>6} {'obj':>8} {'ho':>6} {'habs':>6} {'w_sum':>7} {'fs_sum':>7}", flush=True)
        rows[tag] = []
        for f, r in zip(FS, rs):
            if r is None:
                print(f"{f:6.2f}  CRASH", flush=True)
                continue
            o = sum(r[g] / base[g] for g in G7)
            ho = r["fs_0324"] / base["fs_0324"]
            wsum = sum(r[g] for g in G7 if g.startswith("w_"))
            fssum = r["fs_0424"] + r["fs_0602"]
            rows[tag].append(dict(rf=f, obj=float(o), ho=float(ho),
                                  habs=float(r["habs"] / base["habs"]),
                                  w=float(wsum), fs=float(fssum)))
            print(f"{f:6.2f} {o:8.4f} {ho:6.3f} {r['habs']/base['habs']:6.3f} {wsum:7.0f} {fssum:7.0f}",
                  flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
