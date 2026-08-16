# -*- coding: utf-8 -*-
"""P18b iter4 — (a) 평행사변형 이중심판 가드레일: 스프링@calf vs @crank (P16 x37 동일)
(b) 0429 CL 재실행 (최종 구성: spring@calf, fric@crank, o1/o2 iter3)."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
import p16a_spring as PS
import g21_p13_linkage as P13
import g21_p13e_honest as PH

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
IT3 = json.load(open(HERE / "p18b_iter3.json"))
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]


def build_calf(x32, ref):
    """flip(평행사변형) 모델, 스프링을 knee_motor(crank) -> knee(calf)로 이동."""
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    xml = xml.replace('<joint name="knee" type="hinge" damping="0.001"/>',
                      f'<joint name="knee" type="hinge" damping="0.001" '
                      f'stiffness="{dd["stiff_knee"]:.6f}" springref="{ref:.5f}"/>')
    assert 'springref' in xml
    return mj.MjModel.from_xml_string(xml), dd


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "judge"
    if mode == "judge":
        J.winit()
        ref = float(X37[36])
        # baseline: spring@crank (P16 원본 경로)
        J.build_model = lambda x32: PS.build_with_ref(x32, ref)
        rA = J.eval36(list(X37[:36]))
        # calf: spring@knee
        J.build_model = lambda x32: build_calf(x32, ref)
        rB = J.eval36(list(X37[:36]))
        print(f"{'group':10s} {'crank':>10} {'calf':>10} {'ratio':>7}")
        for g in G7:
            a, b = rA["A"][g], rB["A"][g]
            print(f"{g:10s} {a:10.3f} {b:10.3f} {b/max(a,1e-9):7.3f}")
        print(f"{'JC':10s} {rA['C']:10.4f} {rB['C']:10.4f} {rB['C']/rA['C']:7.3f}")
        print(f"{'CLgate':10s} {rA['Cg']:10.4f} {rB['Cg']:10.4f} {rB['Cg']/rA['Cg']:7.3f}")
        json.dump(dict(crank={**rA["A"], "C": rA["C"], "Cg": rA["Cg"]},
                       calf={**rB["A"], "C": rB["C"], "Cg": rB["Cg"]}),
                  open(HERE / "p18b_iter4_judge.json", "w"), indent=1)
        print("saved p18b_iter4_judge.json", flush=True)
    else:  # cl
        import multiprocessing as mp
        from cvt_run2 import build_cvt2, sim_run, metrics2
        from cvt_core import load_0429, label_gains_429, SUBS429
        o1, o2 = IT3["o1"], IT3["o2"]

        def run_cl(sub):
            if not J._P:
                J.winit()
            d = load_0429(sub)
            model, _ = build_cvt2(d["l_i"], "calf", "crank")
            L, _ = sim_run(model, d, d["l_i"], "CL", gains=label_gains_429(sub),
                           o1=o1, o2=o2)
            if L is None:
                return dict(sub=sub, err="CRASH")
            m = metrics2(d, L, o1, o2)
            # tau RMSE (stance)
            t = d["t"]
            st = t <= m["toff_r"]
            mk = (L["t"] >= 0) & (L["t"] <= t[-1])
            f = lambda a: np.interp(t, L["t"][mk], a[mk])
            tp1 = np.interp(t + 0.0015, t, J.ahat(np.array(C16["x"][32:36]), d["traw1"], d["dq1"]))
            tp2 = np.interp(t + 0.0015, t, J.ahat(np.array(C16["x"][32:36]), d["traw2"], d["dq2"]))
            m["tau1"] = float(np.sqrt(np.mean((f(L["sh1"]) - tp1)[st] ** 2)))
            m["tau2"] = float(np.sqrt(np.mean((f(L["sh2"]) - tp2)[st] ** 2)))
            return dict(sub=sub, **m)

        pool = mp.Pool(10, initializer=J.winit)
        res = list(pool.imap_unordered(run_cl, SUBS429))
        pool.close(); pool.join()
        ok = [r for r in res if "err" not in r]
        g = lambda k: float(np.mean([r[k] for r in ok]))
        for r in sorted(ok, key=lambda r: r["sub"]):
            print(f"{r['sub']:18s} q2 {r['q2']:.3f} dq2 {r['dq2']:.2f} "
                  f"tau1 {r['tau1']:.2f} tau2 {r['tau2']:.2f} "
                  f"h {r['h']:.3f}/{r['h_real']:.3f} dtoff {r['dtoff']*1000:+.0f}ms", flush=True)
        print(f"\n[CL v2 평균] q1 {g('q1'):.3f} q2 {g('q2'):.3f} dq1 {g('dq1'):.2f} "
              f"dq2 {g('dq2'):.2f} tau1 {g('tau1'):.2f} tau2 {g('tau2'):.2f} "
              f"h {g('h'):.3f}/{g('h_real'):.3f} dtoff {g('dtoff')*1000:.1f}ms", flush=True)
        json.dump(res, open(HERE / "p18b_iter4_cl.json", "w"), indent=1)
        print("saved p18b_iter4_cl.json", flush=True)


if __name__ == "__main__":
    main()
