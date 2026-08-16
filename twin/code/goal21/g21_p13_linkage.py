"""P13 — 한 번도 자유화한 적 없는 링키지 파라미터 6종 해방 (flipped phase):
  s_rc (crank CoM 위치 스케일), s_ic (crank 관성), s_rp (coupler CoM), s_ip (coupler 관성),
  d_cpin (coupler 핀 점성마찰), d_kneep (knee 수동 힌지 점성).
가설: M_p 1.7~2.0x 이상치가 사실은 coupler CoM/관성 오배치의 보상일 수 있음.
목적: P12 하이브리드(창5+fs3+habs) + held-out fs_0324 게이트. 32-D CMA."""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
_M = {}

DEF6 = np.array([1.0, 1.0, 1.0, 1.0, 0.0, 0.001])
LO6 = np.array([0.3, 0.3, 0.5, 0.3, 0.0, 0.0002])
HI6 = np.array([2.0, 3.0, 1.5, 3.0, 0.05, 0.05])
N6 = ["s_rc", "s_ic", "s_rp", "s_ip", "d_cpin", "d_kneep"]


def apply_linkage_mods(xml, mods):
    s_rc = mods.get("s_rc", 1.0); s_ic = mods.get("s_ic", 1.0)
    s_rp = mods.get("s_rp", 1.0); s_ip = mods.get("s_ip", 1.0)
    d_cp = mods.get("d_cpin", 0.0); d_kp = mods.get("d_kneep", 0.001)
    if s_rc != 1.0:
        xml = xml.replace('pos="0 0 0.02069"', f'pos="0 0 {0.02069 * s_rc:.5f}"')
    if s_ic != 1.0:
        xml = xml.replace('0.000580 0.000580 0.000580',
                          f'{0.0005797 * s_ic:.6f} {0.0005797 * s_ic:.6f} {0.0005797 * s_ic:.6f}')
    if s_rp != 1.0:
        xml = xml.replace('pos="0 0 -0.13258"', f'pos="0 0 -{0.13258 * s_rp:.5f}"')
    if s_ip != 1.0:
        xml = xml.replace('0.000886 0.000886 0.00005',
                          f'{0.0008858 * s_ip:.6f} {0.0008858 * s_ip:.6f} 0.00005')
    if d_cp > 0:
        xml = xml.replace('<joint name="cpin" type="hinge"/>',
                          f'<joint name="cpin" type="hinge" damping="{d_cp:.5f}"/>')
    if d_kp != 0.001:
        xml = xml.replace('name="knee" type="hinge" damping="0.001"',
                          f'name="knee" type="hinge" damping="{d_kp:.5f}"')
    return xml


def winit():
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(REPO / "code/goal21"))
    import g21_p12_polish as P12
    P12.winit()
    orig = P12.apply_xml_mods

    def patched(xml, mods):
        return apply_linkage_mods(orig(xml, mods), mods)

    P12.apply_xml_mods = patched
    _M["P12"] = P12


def eval32(x):
    if not _M:
        winit()
    x = np.asarray(x, float)
    mods = dict(zip(N6, x[26:]))
    return _M["P12"].eval_p12((x[:26], mods))


def main():
    import multiprocessing as mp
    import cma
    winit()
    P12 = _M["P12"]
    FR = P12._G["FR"]
    ref = json.load(open(REPO / "code/goal21/fourbar_flip_canonical.json"))
    x26 = np.array(ref["x"]); NAMES = ref["names"] + N6
    x0 = np.concatenate([x26, DEF6])
    LOb = np.concatenate([FR.LOb, LO6]); HIb = np.concatenate([FR.HIb, HI6])
    pool = mp.Pool(10, initializer=winit)
    base = eval32(x0)
    G7 = P12.OBJ_GROUPS
    print("BASE:", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.06,
                                  {"bounds": [0, 1], "maxfevals": 1100, "popsize": 20,
                                   "seed": 41, "verbose": -9})
    cands = []
    best = dict(obj=8.0, ho=1.0, x=x0.tolist())
    nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval32, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.05:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} [{(time.time()-t0)/60:.0f}min] " +
                      " ".join(f"{n}={v:.3f}" for n, v in zip(N6, x[26:])), flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P13 DONE nev={nev}  selected: obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "P13 DONE: no candidate passed", flush=True)
    if sel:
        xs = np.array(sel["x"])
        print("linkage params:", " ".join(f"{n}={v:.4f}" for n, v in zip(N6, xs[26:])), flush=True)
        i_mp = ref["names"].index("M_p"); i_mc = ref["names"].index("M_c")
        print(f"M_p {x26[i_mp]:.3f} -> {xs[i_mp]:.3f}   M_c {x26[i_mc]:.3f} -> {xs[i_mc]:.3f}", flush=True)
    json.dump(dict(selected=sel, names=NAMES, base={k: float(v) for k, v in base.items()}),
              open(REPO / "code/goal21/p13_linkage.json", "w"), indent=1)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
