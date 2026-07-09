# -*- coding: utf-8 -*-
"""P18b iter8 — H*+stiction: spring 제거 + o_t2 + fc_knee(쿨롱) 스캔.
가설: 스프링의 s2s/0421 역할 = 정지 마찰(스프링 있는 상태에서 기각됐던 축 재심)."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from cvt_iter7 import eval_modeA_adj, G7

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
T_BEST = {"jump_0602": 3.04, "jump_position_0421": 0.1, "s2s": 0.56,
          "jump_0424": 3.0, "jump_0324": 3.0}


def main():
    J.winit()
    FR = J._P["FR"]
    i_fck = FR.NAMES.index("fc_knee")
    i_fvk = FR.NAMES.index("fv_knee")
    x36 = list(X37[:36])
    base = eval_modeA_adj(x36, {}, "crank")
    print("[crank base]", " ".join(f"{g}={base[g]:.0f}" for g in G7), flush=True)

    rows = []
    for fc in (0.1, 0.3, 0.6, 1.0, 1.5):
        x = list(x36); x[i_fck] = fc
        r = eval_modeA_adj(x, T_BEST, "none")
        rows.append((fc, r))
        print(f"[none+ot2 fc_knee={fc:.1f}] " +
              " ".join(f"{g}={r[g]:.0f}" for g in G7), flush=True)

    # 최적 fc에서 o_t2 0421/0602 재스캔
    def gsum(r):
        return sum(r[g] / base[g] for g in G7) / len(G7)
    fc_best = min(rows, key=lambda t: gsum(t[1]))[0]
    x = list(x36); x[i_fck] = fc_best
    print(f"fc_best={fc_best}", flush=True)
    tbl = dict(T_BEST)
    for ds_key, grp, vals in [("jump_position_0421", "w_0421", (0.0, 0.5, 1.0, 1.5)),
                              ("jump_0602", "w_0602", (2.0, 3.04, 4.0)),
                              ("s2s", "w_s2s", (0.0, 0.56, 1.2))]:
        sc = []
        for o in vals:
            r = eval_modeA_adj(x, {**tbl, ds_key: o}, "none")
            sc.append((r[grp], o))
            print(f"  scan {ds_key} o={o:+.2f} -> {grp}={r[grp]:.0f}", flush=True)
        sc.sort(); tbl[ds_key] = sc[0][1]
    rf = eval_modeA_adj(x, tbl, "none")
    print("[final none+ot2+fc]", " ".join(f"{g}={rf[g]:.0f}" for g in G7), flush=True)
    print("table:", tbl, flush=True)
    print(f"\n{'group':10s} {'crank':>9} {'final':>9} {'ratio':>6}")
    for g in G7:
        print(f"{g:10s} {base[g]:9.1f} {rf[g]:9.1f} {rf[g]/max(base[g],1e-9):6.2f}",
              flush=True)
    json.dump(dict(base=base, rows=[(f, r) for f, r in rows], final=rf,
                   fc_best=fc_best, table=tbl),
              open(HERE / "p18b_iter8.json", "w"), indent=1)
    print("saved p18b_iter8.json", flush=True)


if __name__ == "__main__":
    main()
