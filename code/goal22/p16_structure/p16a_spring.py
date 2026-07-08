# -*- coding: utf-8 -*-
"""P16a — stiff_knee 재심: springref 자유화 (역대 미검증 1-D) + drop-test.

배경: stiff_knee(GOAL19, 동적 −23.5% 기여)는 springref=0 LOCK 상태로 채택됨.
P5에서 crouch 정적 −3.3Nm 편향의 원인으로 지목됨 (spring τ = −k·(q_crank − ref)).
질문: ref를 풀면 동적 이득을 유지하며 정적 편향을 제거할 수 있는가? k=0(drop)은?

방법: 모델 = P14 (x32 + a_hat 고정), (k, ref) 그리드 → 이중 심판 (Mode A + CL).
ref는 mj 크랭크각 기준 (crouch ≈ +2.6 rad). 정적 편향 지표 = k·(2.6 − ref).
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

OUT = HERE / "p16a_result.json"
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
CAND = json.load(open(HERE.parent / "p14_ahat/fourbar_p14_candidate.json"))
X36 = np.array(CAND["x"])
IDX_K = CAND["names"].index("stiff_knee")


def build_with_ref(x32, ref):
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


_REF = [0.0]


def winit():
    J.winit()
    J.build_model = lambda x32: build_with_ref(x32, _REF[0])   # springref-aware 패치


def eval_cell(args):
    k, ref = args
    try:
        if not J._P:
            winit()
        _REF[0] = ref
        x = X36.copy()
        x[IDX_K] = k
        ra = J.eval_modeA(x)
        jc, jcg = J.eval_cl(x)
        return dict(k=k, ref=ref, A={g: float(ra[g]) for g in G7},
                    fs0324=float(ra["fs_0324"]), C=float(jc), Cg=float(jcg))
    except Exception as e:
        return dict(k=k, ref=ref, err=str(e))


def main():
    import multiprocessing as mp
    winit()
    k14 = float(X36[IDX_K])
    grid = [(k14, 0.0)]                                    # 기준 (P14 그대로)
    grid += [(0.0, 0.0)]                                   # drop-test
    for k in [0.5, k14, 2.0]:
        for ref in [0.6, 1.2, 1.8, 2.4]:
            grid.append((round(k, 3), ref))
    pool = mp.Pool(10, initializer=winit)
    rs = pool.map(eval_cell, grid)
    base = rs[0]
    print(f"기준 P14 (k={k14:.3f}, ref=0): JC={base['C']:.4f}", flush=True)
    print(f"{'k':>6} {'ref':>5} {'JA':>7} {'JC':>7} {'hoA':>6} {'hoC':>6} {'정적편향[Nm]':>10}", flush=True)
    rows = []
    for r in rs:
        if "err" in r:
            print(r["k"], r["ref"], "ERR", r["err"][:60], flush=True)
            continue
        ja = sum(r["A"][g] / base["A"][g] for g in G7) / len(G7)
        jc = r["C"] / base["C"]
        hoA = r["fs0324"] / base["fs0324"]
        hoC = r["Cg"] / base["Cg"]
        bias = r["k"] * (2.6 - r["ref"])
        rows.append(dict(r, ja=float(ja), jc=float(jc), hoA=float(hoA), hoC=float(hoC),
                         bias=float(bias)))
        tag = " <-- drop" if r["k"] == 0 else (" <-- 기준" if (r["k"] == k14 and r["ref"] == 0) else "")
        print(f"{r['k']:6.2f} {r['ref']:5.1f} {ja:7.4f} {jc:7.4f} {hoA:6.3f} {hoC:6.3f} "
              f"{bias:10.2f}{tag}", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
