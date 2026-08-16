"""P15 — a_hat에 속도 텀 A5·v만 추가, Mode A 단독 적합 (사용자 07-09 제안).

τ_shaft = A1·GR·KT·Iq − A2·GR·|Iq|·Iq − A3·sgn(v) − A4·|Iq|·sgn(v) − A5·v
검증 구조: Mode A로만 학습 → 폐루프 PD 재현(미학습)을 시험지로 (p15_test.py).
x = [32 모델 파라미터, A1..A5]. 게이트: fs_0324 ≤ 1.05.
"""
import sys, json, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
import g21_p13_linkage as P13
import g21_p13e_honest as PH

MAXFEV = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
OUT = HERE / "p15_result.json"
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]


def ahat5(A, tau_rep, v):
    """paper 4계수 + A5·v 점성."""
    base = J.ahat(A[:4], tau_rep, v)
    return base - A[4] * np.asarray(v, float)


def eval_modeA5(x37):
    try:
        if not J._P:
            J.winit()
        x37 = np.asarray(x37, float)
        x32 = x37[:32]; A = x37[32:37]
        P12 = J._P["P12"]
        dd = dict(zip(J._P["FR"].NAMES, x32[:26]))
        model, _ = J.build_model(x32)
        res = {"habs": 0.0}
        for tr in P12._G["trials"]:
            ds = tr["ds"]
            k1, k2 = P12.OFFKEY.get(ds, (None, None))
            o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
            t = tr["pp"]["t"]
            th = -ahat5(A, tr["raw1"], tr["v1"])
            tk = -ahat5(A, tr["raw2"], tr["v2"])
            ppv = dict(tr["pp"], tau_h=np.interp(t - J.SD, t, th),
                       tau_k=np.interp(t - J.SD, t, tk))
            ppo = P12._G["sv"](ppv, o1, o2)
            res[P12.GKEY[ds]] = res.get(P12.GKEY[ds], 0.0) + P12.eval_windows(model, ppo, None)
            if ds in ("jump_0424", "jump_0602", "jump_0324"):
                fsk = "fs_" + ds.split("_")[-1]
                sc, h_pred = P12.fs_metric(model, ppo, tr["td"], None)
                res[fsk] = res.get(fsk, 0.0) + sc
                if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr["h_real"]):
                    res["habs"] += abs(h_pred - tr["h_real"])
        return res
    except Exception:
        return None


def winit():
    J.winit()


def main():
    import multiprocessing as mp
    import cma
    winit()
    FR = J._P["FR"]
    h = json.load(open(HERE.parent / "fourbar_p13h_candidate.json"))
    NAMES = h["names"] + ["A1", "A2", "A3", "A4", "A5"]
    x0 = np.concatenate([np.array(h["x"]), J.A_PAPER, [0.0]])
    LOb = np.concatenate([FR.LOb.copy(), P13.LO6.copy(), [1.00, 0.0, 0.0, 0.0, 0.0]])
    HIb = np.concatenate([FR.HIb.copy(), P13.HI6.copy(), [1.35, 1.3e-3, 0.45, 0.10, 0.08]])
    def idx(n): return NAMES.index(n)
    LOb[idx("M_p")] = PH.MP_PHYS - 5e-4; HIb[idx("M_p")] = PH.MP_PHYS + 5e-4
    LOb[idx("M_calf")] = 0.97; HIb[idx("M_calf")] = 1.03
    LOb[idx("M_thigh")] = 0.92; HIb[idx("M_thigh")] = 1.08
    LOb[idx("M_c")] = 0.45; HIb[idx("M_c")] = 1.00
    LOb[idx("M_base")] = 0.999; HIb[idx("M_base")] = 1.001
    for n in NAMES:
        if n.startswith("o1_") or n.startswith("o2_"):
            LOb[idx(n)] = -0.0524; HIb[idx(n)] = 0.0524
    LOb[idx("arm_knee")] = 0.0005; LOb[idx("fc_knee")] = 0.0
    LOb[idx("m_foot")] = 0.0;  HIb[idx("m_foot")] = 0.010
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
    r0 = eval_modeA5(x0)
    base = {g: r0[g] for g in G7}
    ho0 = r0["fs_0324"]
    print(f"BASE(P13h+paper+A5=0): 그룹 기준 확보 fs0324={ho0:.1f}", flush=True)

    def score(r):
        if r is None:
            return 99.0, 99.0
        return (sum(r[g] / base[g] for g in G7) / len(G7),
                r["fs_0324"] / ho0)

    es = cma.CMAEvolutionStrategy(((x0 - LOb) / (HIb - LOb)).tolist(), 0.05,
                                  {"bounds": [0, 1], "maxfevals": MAXFEV, "popsize": 20,
                                   "seed": 111, "verbose": -9})
    cands = []; best = dict(obj=1.0, x=x0.tolist()); nev = 0; t0 = time.time()
    while not es.stop():
        sols = es.ask()
        xs = [LOb + np.array(s) * (HIb - LOb) for s in sols]
        rs = pool.map(eval_modeA5, xs)
        oo = []
        for x, r in zip(xs, rs):
            o, ho = score(r); oo.append(o); nev += 1
            if o < 90 and ho <= 1.10:
                cands.append(dict(obj=float(o), ho=float(ho), x=[float(v) for v in x]))
            if o < best["obj"]:
                best = dict(obj=float(o), ho=float(ho), x=[float(v) for v in x])
                A = x[32:37]
                print(f"BEST nev={nev} obj={o:.4f} ho={ho:.3f} "
                      f"A5={A[4]:.4f} A3={A[2]:.3f} A1cf={A[0]*J.CF:.3f} "
                      f"[{(time.time()-t0)/60:.1f}min]", flush=True)
        es.tell(sols, oo)
    sel = None
    for c in cands:
        if c["ho"] <= 1.05 and (sel is None or c["obj"] < sel["obj"]):
            sel = c
    print(f"P15 DONE nev={nev} [{(time.time()-t0)/60:.1f}min] " +
          (f"selected obj={sel['obj']:.4f} ho={sel['ho']:.3f}" if sel else "none passed"),
          flush=True)
    if sel:
        xs_ = np.array(sel["x"])
        A = xs_[32:37]
        r = eval_modeA5(xs_)
        print(f"a_hat5: A=[{A[0]:.4f},{A[1]:.2e},{A[2]:.4f},{A[3]:.4f},A5={A[4]:.4f}]", flush=True)
        print(f"  A1*CF {J.A_PAPER[0]*J.CF:.3f}->{A[0]*J.CF:.3f}  A3 {J.A_PAPER[2]:.3f}->{A[2]:.3f}", flush=True)
        print("  그룹 비:", " ".join(f"{g}:{r[g]/base[g]:.3f}" for g in G7), flush=True)
        json.dump(dict(CANDIDATE="P15 — ModeA-only fit, a_hat + A5*v (2026-07-09)",
                       sens_delay=-0.0015, obj=sel["obj"], ho=sel["ho"],
                       A_HAT5=[float(v) for v in A], names=NAMES, x=sel["x"]),
                  open(HERE / "fourbar_p15_candidate.json", "w"), indent=1)
    json.dump(dict(selected=sel, n_cands=len(cands)), open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
