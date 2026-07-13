# -*- coding: utf-8 -*-
"""P20 실험 11 — 동적층의 물리 후보: 발-바닥 마찰계수 μ (스펀지 Cd 대체 시험).

논리: 레일 고정 구조라 푸시 중 발이 수평으로 움직임. 시뮬 μ=1.0은 포화율 0.81로
꽉 잡지만, 실물 μ가 낮으면 실물은 미끄러져 수평 구속력이 사라짐 → 실물 무릎이
덜 들고 시뮬이 더 듦 = 동적층의 부호·강도의존·출력측(r-축소)·저속무관 전부 충족.
시험: 준정적층(c=0.25, v0=6)만 켜고 Cd=0, μ ∈ {1.0, 0.7, 0.5, 0.4, 0.3} 스캔.
성공 = 어떤 μ가 [점프 창 → 79 근접] + [CL FIT/HO ≥ 두손(36.5/32.2)] + [0429 무악화]
      + [s2s/저속 무영향(슬립 없음)] 동시 달성 → 스펀지가 물리 파라미터로 대체됨.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
import p19_run as R
import p20_run as P20
import p20_exp7 as X7
from cvt_core import load_0429

mj = P.J._P["mj"]
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20_results")


def set_mu(model, mu):
    for gn in ("foot", "floor"):
        gid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, gn)
        model.geom_friction[gid][0] = mu


def f429_hi(mu):
    """0429 고속 잔여 λ* (준정적층 base, 4 subs)."""
    lams = []
    model = None
    for sub in ("60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"):
        d = load_0429(sub)
        if model is None:
            model, _ = P.build_cvt(E.X32, E.V[1], E.SP, d["l_i"])
            set_mu(model, mu)
        base = np.interp(d["t"] - P.SD, d["t"],
                         0.25 * P.J.ahat(E.A, d["traw2"], d["dq2"]) * P20.gate(d["dq2"], 6.0))
        percfg = {}
        for lam in np.arange(-2.0, 3.01, 0.5):
            for t0, sc in X7.win_lam_429(model, d, d["l_i"], lam, lam_base=base):
                percfg.setdefault(round(t0, 4), []).append(sc)
        for t0, scs in percfg.items():
            scs = np.array(scs)
            if (scs.max() - scs.min()) / max(scs.min(), 1e-9) < 0.02:
                continue
            i0 = int(np.searchsorted(d["t"], t0))
            if abs(d["dq2"][i0]) > 10:
                lg = np.arange(-2.0, 3.01, 0.5)
                i = int(np.argmin(scs))
                lams.append(float(lg[i]))
    return float(np.mean(lams)) if lams else float("nan")


def main():
    out = {}
    for mu in (1.0, 0.7, 0.5, 0.4, 0.3):
        # F1: 점프 창 (준정적층 벡터만, μ 반영 flip 모델)
        model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
        set_mu(model_f, mu)
        fn = lambda tr: 0.25 * P.J.ahat(E.A, tr["raw2"], tr["v2"]) * P20.gate(tr["v2"], 6.0)
        r1 = E.eval_set(model_f, E.JDS, fn)
        F1 = float(np.mean(list(r1.values())))
        s2s = float(list(E.eval_set(model_f, ("s2s_gnd_0319",), fn).values())[0])
        # CL 본지표: eval_stack20에 μ 주입 — 빌더 이후 모델 패치 필요 → 로컬 루프
        R.TRIALS = R.TRIALS or R.all_trials()
        model_c = None
        rows = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
            alphas = R.ALPH.get(ds, [1, 1, 1, 1])
            if is_cvt:
                if model_c is None:
                    model_c, _ = P.build_cvt(E.X32, E.V[1], E.SP, l_i)
                    set_mu(model_c, mu)
                L = P20.cl_run20(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                                 E.V[15], alphas, c_qs=0.25, v0=6.0, Cd=0.0,
                                 o1=E.QOFF[0], o2=E.QOFF[1])
            else:
                dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(E.X32)[:26]))
                k1, k2 = P.J.OFFK.get(ds, (None, None))
                o1 = dd.get(k1, 0.0) if k1 else 0.0
                o2 = dd.get(k2, 0.0) if k2 else 0.0
                L = P20.cl_run20(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                                 E.V[15], alphas, c_qs=0.25, v0=6.0, Cd=0.0, o1=o1, o2=o2)
            if L is None:
                rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9))
                continue
            g, q2r = R.gap_v3(L, d, P.A_PAPER, m)
            rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
        s = R.summarize(rows)
        hi429 = f429_hi(mu)
        out[mu] = dict(F1=F1, s2s=s2s, fit=100 * s["FIT"][0], ho=100 * s["jump_0324"][0],
                       hi429=hi429,
                       per={k: round(100 * v[0], 1) for k, v in s.items() if k.startswith("jump")})
        print(f"μ={mu:.1f} | 점프창 {F1:6.1f} (참조79.2) | s2s {s2s:5.1f} | "
              f"CL FIT {out[mu]['fit']:5.1f}% HO {out[mu]['ho']:5.1f}% "
              f"(두손 36.5/32.2) | 0429고속잔여 {hi429:+5.2f} | " +
              " ".join(f"{k.split('_')[-1]} {v}" for k, v in out[mu]["per"].items()), flush=True)
    json.dump(out, open(DST / "exp11_results.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
