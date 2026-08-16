# -*- coding: utf-8 -*-
"""P18b iter7 — H* 검증: 스프링 제거 + 세션별 무릎 토크 영점 오프셋(o_t2).
정적 감사값 주입: 0602 +3.04, 0421 +0.10, s2s(0319) +0.56. 0424/0324는 1-D 스캔.
Mode A 심판 그룹 점수로 spring@crank 기준과 비교."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
from cvt_iter5 import build_flip_variant

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
REF = float(X37[36])
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
SD = -0.0015


def ot2_for(ds, table):
    for k, v in table.items():
        if ds.startswith(k):
            return v
    return 0.0


def eval_modeA_adj(x36, ot2_table, spring_at):
    """p14_judge.eval_modeA 복제 + 무릎 토크 세션 오프셋 + 스프링 배치."""
    P12 = J._P["P12"]
    x32 = np.asarray(x36[:32]); A = np.asarray(x36[32:36])
    dd = dict(zip(J._P["FR"].NAMES, x32[:26]))
    model, _ = build_flip_variant(x32, REF, spring_at)
    res = {"habs": 0.0}
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        t = tr["pp"]["t"]
        ot2 = ot2_for(ds, ot2_table)
        th = -J.ahat(A, tr["raw1"], tr["v1"])
        tk = -(J.ahat(A, tr["raw2"], tr["v2"]) + ot2)
        ppv = dict(tr["pp"], tau_h=np.interp(t - SD, t, th), tau_k=np.interp(t - SD, t, tk))
        ppo = P12._G["sv"](ppv, o1, o2)
        res[P12.GKEY[ds]] = res.get(P12.GKEY[ds], 0.0) + P12.eval_windows(model, ppo, None)
        if ds in ("jump_0424", "jump_0602", "jump_0324"):
            fsk = "fs_" + ds.split("_")[-1]
            sc, h_pred = P12.fs_metric(model, ppo, tr["td"], None)
            res[fsk] = res.get(fsk, 0.0) + sc
            if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr["h_real"]):
                res["habs"] += abs(h_pred - tr["h_real"])
    return res


def main():
    J.winit()
    P12 = J._P["P12"]
    dss = sorted(set(tr["ds"] for tr in P12._G["trials"]))
    print("datasets:", dss, flush=True)
    x36 = list(X37[:36])

    base = eval_modeA_adj(x36, {}, "crank")
    print("[base spring@crank]", " ".join(f"{g}={base[g]:.0f}" for g in G7), flush=True)

    T0 = {"jump_0602": 3.04, "jump_position_0421": 0.10, "s2s": 0.56}
    r1 = eval_modeA_adj(x36, T0, "none")
    print("[none + o_t2(static)]", " ".join(f"{g}={r1[g]:.0f}" for g in G7), flush=True)

    # 0424 / 0324 1-D 스캔
    best = dict(T0)
    for ds_key, grp in [("jump_0424", "w_0424"), ("jump_0324", "w_0324")]:
        vals = []
        for o in (0.0, 1.0, 2.0, 3.0):
            r = eval_modeA_adj(x36, {**best, ds_key: o}, "none")
            vals.append((r[grp], o, r))
            print(f"  scan {ds_key} o={o:+.1f} -> {grp}={r[grp]:.0f} "
                  f"fs={r.get('fs_' + ds_key.split('_')[-1], 0):.0f}", flush=True)
        vals.sort()
        best[ds_key] = vals[0][1]
    r2 = eval_modeA_adj(x36, best, "none")
    print("[none + o_t2(best)]", " ".join(f"{g}={r2[g]:.0f}" for g in G7), flush=True)
    print("o_t2 table:", best, flush=True)

    # 비교표
    print(f"\n{'group':10s} {'crank':>9} {'none+ot2':>9} {'ratio':>6}")
    for g in G7:
        print(f"{g:10s} {base[g]:9.1f} {r2[g]:9.1f} {r2[g]/max(base[g],1e-9):6.2f}",
              flush=True)
    json.dump(dict(base=base, static=r1, best=r2, table=best),
              open(HERE / "p18b_iter7.json", "w"), indent=1)
    print("saved p18b_iter7.json", flush=True)


if __name__ == "__main__":
    main()
