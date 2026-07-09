# -*- coding: utf-8 -*-
"""P18b iter5 — 침묵실패 정정 재실험.
A: 0429 Mode A — 스프링 {crank | none | calf(진짜)} × 오프셋 {0, iter3} (60 sims)
B: 평행사변형 이중심판 — 같은 3 구성 (P16 x37 고정, build_model 패치)
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
O3 = (3.14 * np.pi / 180, -3.00 * np.pi / 180)


def run_cellA(args):
    spring_at, o1, o2, sub = args
    from cvt_run2 import build_cvt2, sim_run, metrics2, score
    from cvt_core import load_0429
    if not J._P:
        J.winit()
    d = load_0429(sub)
    model, _ = build_cvt2(d["l_i"], spring_at, "crank")
    L, diag = sim_run(model, d, d["l_i"], "A", o1=o1, o2=o2)
    if L is None:
        return dict(spring=spring_at, o1=o1, sub=sub, score=1e9)
    m = metrics2(d, L, o1, o2)
    return dict(spring=spring_at, o1=o1, o2=o2, sub=sub, score=score(m),
                hold2=diag["hold2"], **m)


def build_flip_variant(x32, ref, spring_at):
    """평행사변형(flip, body-connect) 모델에 스프링 배치 적용."""
    import re
    import g21_p13_linkage as P13
    import g21_p13e_honest as PH
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0
    S.STIFF_KNEE = dd["stiff_knee"] if spring_at == "crank" else 0.0
    S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    if spring_at == "calf":
        mkn = re.search(r'<joint name="knee" type="hinge" damping="([0-9.eE+-]+)"/>', xml)
        assert mkn, "knee joint line not found"
        xml = xml.replace(mkn.group(0),
                          f'<joint name="knee" type="hinge" damping="{mkn.group(1)}" '
                          f'stiffness="{dd["stiff_knee"]:.6f}" springref="{ref:.5f}"/>')
    return mj.MjModel.from_xml_string(xml), dd


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "A"
    if mode == "A":
        import multiprocessing as mp
        jobs = [(sp, o1, o2, s)
                for sp in ("crank", "none", "calf")
                for (o1, o2) in [(0.0, 0.0), O3]
                for s in json.loads(json.dumps(__import__("cvt_core").SUBS429))]
        pool = mp.Pool(10, initializer=J.winit)
        res = list(pool.imap_unordered(run_cellA, jobs, chunksize=2))
        pool.close(); pool.join()
        json.dump(res, open(HERE / "p18b_iter5A.json", "w"))
        print(f"{'spring':7s} {'off':>5} {'score':>7} {'q2':>6} {'dq2':>6} "
              f"{'dtoff':>8} {'h_gap':>7} {'hold2':>6}")
        for sp in ("crank", "none", "calf"):
            for oi, (o1, o2) in enumerate([(0.0, 0.0), O3]):
                rs = [r for r in res if r["spring"] == sp and abs(r["o1"] - o1) < 1e-9
                      and r["score"] < 1e8]
                if not rs:
                    print(f"{sp:7s} {'o'+str(oi):>5} CRASH"); continue
                g = lambda k: float(np.mean([r[k] for r in rs]))
                print(f"{sp:7s} {'o'+str(oi):>5} {g('score'):7.1f} {g('q2'):6.3f} "
                      f"{g('dq2'):6.2f} {g('dtoff')*1000:7.1f}ms "
                      f"{g('h')-g('h_real'):+7.3f} {g('hold2'):+6.2f}", flush=True)
    else:  # judge
        J.winit()
        ref = float(X37[36])
        out = {}
        for sp in ("crank", "calf", "none"):
            J.build_model = lambda x32, _sp=sp: build_flip_variant(x32, ref, _sp)
            r = J.eval36(list(X37[:36]))
            out[sp] = {**r["A"], "C": r["C"], "Cg": r["Cg"]}
            print(f"[{sp}] done", flush=True)
        print(f"{'group':10s} {'crank':>10} {'calf':>10} {'none':>10}")
        for g in G7 + ["C", "Cg"]:
            print(f"{g:10s} {out['crank'][g]:10.4f} {out['calf'][g]:10.4f} "
                  f"{out['none'][g]:10.4f}", flush=True)
        json.dump(out, open(HERE / "p18b_iter5_judge.json", "w"), indent=1)
        print("saved p18b_iter5_judge.json", flush=True)


if __name__ == "__main__":
    main()
