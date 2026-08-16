# -*- coding: utf-8 -*-
"""26.06.04 페이로드 s2s — P19 스택 재실행 (g22_p19_all_results/s2s_0604_payload).

P18c(s2s_0604.py) 대비: 플랜트=P19 x32, A=Paper, tm=P19, CL에 dq_des 인가(실기 동일).
게인 = P18c 회귀 실효게인 재사용 (s2s_0604_gains.json — 회귀값이라 α 불필요).
프리로드 = l_i=30(no_cvt)만 V[2]. 페이로드 = base 질량 가산 (레일 병진).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_all_results as B
import p19_judge as P

sys.path.insert(0, str(HERE.parent / "p18_cvt"))
import s2s_0604 as S0
from cvt_run2 import build_cvt2

SD = B.ROOT / "s2s_0604_payload"
for c in ("png", "gif", "traj"):
    (SD / c).mkdir(parents=True, exist_ok=True)


def main():
    gains = json.load(open(HERE.parent / "p18_cvt/s2s_0604_gains.json"))
    mj = P.J._P["mj"]
    for grp, sub, load in S0.TRIALS:
        d = S0.load_0604(grp, sub)
        model, _ = build_cvt2(d["l_i"], B.SP, "crank", x32=B.X32, ref=B.V[1])
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load
        pre = B.PRE30 if grp == "no_cvt" else 0.0
        g = gains[f"{grp}/{sub}"]
        name = f"{grp}_{sub}"
        for mode in ("CL", "A"):
            L = B.run_any(model, True, d["l_i"], d, mode, g, True, False,
                          [1, 1, 1, 1], pre, 0.0, 0.0)
            if L is None:
                print(f"CRASH {name} [{mode}]", flush=True)
                continue
            B.make_fig(f"s2s_0604/{grp}", sub, d, L, mode, d["l_i"], 0.0, 0.0,
                       float("nan"), SD / "png" / f"{name}__{mode}.png",
                       cl_note=" · 회귀 실효게인 (P18c)")
            B.save_npz(SD / "traj" / f"{name}__{mode}.npz", L, l_i=d["l_i"],
                       ds=f"s2s_0604_{grp}", sub=sub, mode=mode,
                       h_real=float("nan"))
            print(f"png {name} [{mode}] load={load}kg", flush=True)
    for f in sorted((SD / "traj").glob("*.npz")):
        out = SD / "gif" / (f.stem + ".gif")
        if out.exists():
            continue
        z = np.load(f, allow_pickle=True)
        L = {k: z[k] for k in ("t", "q1", "q2", "bz")}
        try:
            B.render_gif(L, float(z["l_i"]),
                         f"P19 {z['ds']}/{z['sub']} [{z['mode']}]",
                         float("nan"), out, float(z["t"][-1]) - P.J.T_AFTER)
            print(f"gif {f.stem}", flush=True)
        except Exception as e:
            print(f"GIF FAIL {f.stem}: {e}", flush=True)
    print("S2S0604 DONE", flush=True)


if __name__ == "__main__":
    main()
