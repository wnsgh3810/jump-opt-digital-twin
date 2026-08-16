"""P13e — 물리 구속 재적합 (사용자 실측 07-08 반영):
  M_p LOCK 1.0983 (150 g)  ·  M_calf [0.97, 1.03] (CAD±5g)
  M_thigh [0.92, 1.08] (CAD≈실물)  ·  M_c [0.45, 1.00] (클러치 모터 교체로 CAD보다 가벼움)
  M_base = 파라미터 아님 — 전체 3.2 kg에서 역산 (TOTAL_MASS 모드; 죽은 파라미터 버그 수정 후)
  offsets ±3° 물리 클램프 (흡수처 봉쇄 — '유령'을 정면 노출시키는 런)
관찰: 물리 우리 안에서 모델이 정직하게 도달하는 성능 + 남는 잔차의 구조."""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13_linkage as P13

MP_PHYS = 0.150 / 0.13657
TOTAL = 3.2


def eval_phys(x):
    if not P13._M:
        P13.winit()
    x = np.asarray(x, float)
    P12 = P13._M["P12"]
    mods = dict(zip(P13.N6, x[26:]))
    mods["TOTAL_MASS"] = TOTAL          # eval_p12 -> FL builder까지 dd로 전달됨?
    # eval_p12는 (x26, mods)로 XML을 FL.build_xml_fourbar_flip(arm, dd26)로 만든다 —
    # TOTAL_MASS는 dd26에 넣어야 builder가 본다. dd26은 FR.NAMES 기반 dict라 직접 추가:
    return P13._M["P12"].eval_p12((x[:26], mods))


def winit():
    P13.winit()
    P12 = P13._M["P12"]
    orig_eval = P12.eval_p12

    def patched(args):
        x26, mods = args
        import g21_fourbar_flip as FL
        ob = FL.build_xml_fourbar_flip

        def builder(arm, sc=None):
            sc = dict(sc or {})
            sc["TOTAL_MASS"] = TOTAL
            return ob(arm, sc)

        FL.build_xml_fourbar_flip = builder
        try:
            return orig_eval((x26, mods))
        finally:
            FL.build_xml_fourbar_flip = ob

    P12.eval_p12 = patched
    P13._M["P12"] = P12


def eval32(x):
    if not P13._M:
        winit()
    return P13.eval32(x)


def main():
    import multiprocessing as mp
    import cma
    winit()
    P12 = P13._M["P12"]
    FR = P12._G["FR"]
    prev = json.load(open(REPO / "code/goal21/p13c_lockMp.json"))
    NAMES = prev["names"]
    x0 = np.array(prev["selected"]["x"])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy()])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy()])
    def idx(n): return NAMES.index(n)
    # 물리 우리
    LOb[idx("M_p")] = MP_PHYS - 5e-4; HIb[idx("M_p")] = MP_PHYS + 5e-4
    LOb[idx("M_calf")] = 0.97; HIb[idx("M_calf")] = 1.03
    LOb[idx("M_thigh")] = 0.92; HIb[idx("M_thigh")] = 1.08
    LOb[idx("M_c")] = 0.45; HIb[idx("M_c")] = 1.00
    LOb[idx("M_base")] = 0.999; HIb[idx("M_base")] = 1.001   # 죽은 축 — TOTAL로 대체됨
    for n in NAMES:
        if n.startswith("o1_") or n.startswith("o2_"):
            LOb[idx(n)] = -0.0524; HIb[idx(n)] = 0.0524       # ±3°
    LOb[idx("arm_knee")] = 0.0005
    LOb[idx("fc_knee")] = 0.0
    # ---- P13e 정직-물리 케이지 (사용자: calf CAD에 발 포함, 실물≈CAD) ----
    LOb[idx("m_foot")] = 0.0;  HIb[idx("m_foot")] = 0.010       # 발은 calf CAD에 포함
    LOb[idx("I_thigh")] = 0.8; HIb[idx("I_thigh")] = 1.2
    LOb[idx("I_calf")] = 0.8;  HIb[idx("I_calf")] = 1.2
    LOb[idx("com_dz_th")] = -0.03; HIb[idx("com_dz_th")] = 0.03
    LOb[idx("com_dz_ca")] = -0.03; HIb[idx("com_dz_ca")] = 0.03
    LOb[idx("s_ic")] = 0.7; HIb[idx("s_ic")] = 1.4
    LOb[idx("s_ip")] = 0.7; HIb[idx("s_ip")] = 1.4
    LOb[idx("s_rc")] = 0.8; HIb[idx("s_rc")] = 1.2
    LOb[idx("s_rp")] = 0.8; HIb[idx("s_rp")] = 1.2
    x0 = np.clip(x0, LOb + 1e-9, HIb - 1e-9)
    pool = mp.Pool(10, initializer=winit)
    base = eval32(x0)
    G7 = P12.OBJ_GROUPS
    print("BASE(물리클램프 시작점):", " ".join(f"{k}:{v:.1f}" for k, v in base.items()), flush=True)

    def obj_of(r):
        return (99.0, 99.0) if r is None else (
            sum(r[g] / base[g] for g in G7), r["fs_0324"] / base["fs_0324"])

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.08,
                                  {"bounds": [0, 1], "maxfevals": 1400, "popsize": 20,
                                   "seed": 61, "verbose": -9})
    cands = []; best = dict(obj=8.0, ho=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval32, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = obj_of(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.08:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} Mc={x[idx('M_c')]:.3f} "
                      f"Mth={x[idx('M_thigh')]:.3f} fvh={x[idx('fv_hip')]:.3f} "
                      f"[{(time.time()-t0)/60:.0f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.0 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P13e DONE nev={nev}  selected: obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel
          else "P13e DONE: none passed ho<=1.0", flush=True)
    if sel:
        xs_ = np.array(sel["x"])
        legs = 0.91281 * xs_[idx("M_thigh")] + (0.23704 * xs_[idx("M_calf")] + xs_[idx("m_foot")]) \
               + 0.13657 * MP_PHYS + 0.65601 * xs_[idx("M_c")]
        print(f"질량 회계: 다리 {legs:.3f} kg + base {TOTAL-legs:.3f} kg = {TOTAL} kg", flush=True)
        for n in ["M_thigh", "M_calf", "M_c", "m_foot", "fv_hip", "fc_hip", "fv_knee", "fc_knee",
                  "stiff_knee", "com_dz_th", "com_dz_ca", "arm_knee"]:
            print(f"  {n:<11} {xs_[idx(n)]:.4f}", flush=True)
        offs = {n: float(np.degrees(xs_[idx(n)])) for n in NAMES if n.startswith("o")}
        print("  offsets(deg):", {k: round(v, 2) for k, v in offs.items()}, flush=True)
    json.dump(dict(selected=sel, names=NAMES, total_mass=TOTAL, mp_locked=MP_PHYS,
                   base={k: float(v) for k, v in base.items()}),
              open(REPO / "code/goal21/p13e_honest.json", "w"), indent=1)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
