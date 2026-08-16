# -*- coding: utf-8 -*-
"""P18b iter10 — 결정 실험: 두 경쟁 스택 전체 맞대결.
B: spring@calf (stiff 1.158, ref 1.910) + o_t2{0602:0.69} + 0424/0324 스캔
C: spring 제거 + o_t2{0602:3.04, 0421:1.5, s2s:재스캔, 0424:3, 0324:3}
   + o_t1{s2s:1.77, 0421:0.59}   ← hip 오프셋 최초 적용
평가: G7 전체 (vs crank 기준) + 0429 Mode A (양 구성)."""
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
SD = -0.0015
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
STIFF_B, REF_B = 1.1578, 1.9104


def ofor(ds, table):
    for k, v in table.items():
        if ds.startswith(k):
            return v
    return 0.0


def evalG7(x32, ref, spring_at, ot2, ot1):
    P12 = J._P["P12"]
    A = np.array(X37[32:36])
    dd = dict(zip(J._P["FR"].NAMES, np.asarray(x32)[:26]))
    model, _ = build_flip_variant(x32, ref, spring_at)
    res = {"habs": 0.0}
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        t = tr["pp"]["t"]
        th = -(J.ahat(A, tr["raw1"], tr["v1"]) + ofor(ds, ot1))
        tk = -(J.ahat(A, tr["raw2"], tr["v2"]) + ofor(ds, ot2))
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


def run_0429(spring_at, stiff, ref, ot2_0429):
    """0429 Mode A 10 trials (q 오프셋 iter3, 토크 오프셋 ot2_0429)."""
    from cvt_run2 import build_cvt2, metrics2, score, sim_run
    import cvt_run2 as R
    from cvt_core import load_0429, SUBS429
    x32 = np.array(X37[:32]); x32[11] = stiff
    scs = []
    for sub in SUBS429:
        d = load_0429(sub)
        if abs(ot2_0429) > 1e-9:
            d = dict(d)
            # a_hat 출력에 오프셋: raw를 역변환 않고 ahat 후 가산이 정확 —
            # sim_run은 J.ahat(traw)를 쓰므로 traw 보정 대신 결과 가산 필요.
            # 간편: ahat 근사 선형이므로 traw에 ot2/(A1*CF*GR*KT/…)? → 정확히 하려면
            # sim_run 수정 필요. 여기서는 J.ahat 몽키패치로 처리.
        model, _ = build_cvt2(d["l_i"], spring_at, "crank", x32=x32, ref=ref)
        ah0 = J.ahat
        if abs(ot2_0429) > 1e-9:
            calls = {"n": 0}
            def ah2(A_, tr_, v_, _o=ot2_0429, _f=ah0):
                out = _f(A_, tr_, v_)
                return out + _o
            # tau2 채널만 보정해야 하므로 sim_run 내부 순서(tau1, tau2) 활용 불가 —
            # 대신 d["traw2"]에 역보정: ahat(traw2)+o ≈ ahat(traw2 + o/(k)) (k=유효게인)
            k_eff = float(J.ahat(np.array(X37[32:36]), np.array([10.0]), np.array([0.0]))
                          - J.ahat(np.array(X37[32:36]), np.array([9.0]), np.array([0.0])))
            d["traw2"] = d["traw2"] + ot2_0429 / k_eff
        L, _ = sim_run(model, d, d["l_i"], "A", o1=3.14 * np.pi / 180, o2=-3.0 * np.pi / 180)
        if L is None:
            scs.append(dict(score=1e9)); continue
        m = metrics2(d, L, 3.14 * np.pi / 180, -3.0 * np.pi / 180)
        scs.append(dict(score=score(m), **m))
    ok = [s for s in scs if s["score"] < 1e8]
    g = lambda k: float(np.mean([s[k] for s in ok]))
    return dict(score=g("score"), q2=g("q2"), dq2=g("dq2"),
                h_gap=g("h") - g("h_real"), n=len(ok))


def main():
    J.winit()
    base = evalG7(np.array(X37[:32]), float(X37[36]), "crank", {}, {})
    print("[A crank]", " ".join(f"{g}={base[g]:.0f}" for g in G7), flush=True)

    x32b = np.array(X37[:32]); x32b[11] = STIFF_B
    tB = {"jump_0602": 0.69}
    for o424 in (0.0, 1.0, 2.0):
        r = evalG7(x32b, REF_B, "calf", {**tB, "jump_0424": o424, "jump_0324": o424}, {})
        print(f"  B scan o424/o324={o424}: w_0424={r['w_0424']:.0f} w_0324={r['w_0324']:.0f} "
              f"fs_0424={r['fs_0424']:.0f}", flush=True)
        if o424 == 0.0 or r["w_0424"] < rB_best["w_0424"]:
            rB_best, oB = r, o424
    print("[B calf-weak]", " ".join(f"{g}={rB_best[g]:.0f}({rB_best[g]/base[g]:.2f})"
                                    for g in G7), f"o424={oB}", flush=True)

    tC1 = {"s2s": 1.77, "jump_position_0421": 0.59}
    rC_best, sC = None, None
    for os2s in (1.2, 2.0, 3.0):
        tC2 = {"jump_0602": 3.04, "jump_position_0421": 1.5, "s2s": os2s,
               "jump_0424": 3.0, "jump_0324": 3.0}
        r = evalG7(np.array(X37[:32]), float(X37[36]), "none", tC2, tC1)
        print(f"  C scan os2s={os2s}: w_s2s={r['w_s2s']:.0f} w_0421={r['w_0421']:.0f}",
              flush=True)
        if rC_best is None or r["w_s2s"] < rC_best["w_s2s"]:
            rC_best, sC = r, os2s
    print("[C none+o12]", " ".join(f"{g}={rC_best[g]:.0f}({rC_best[g]/base[g]:.2f})"
                                   for g in G7), f"os2s={sC}", flush=True)

    print("\n=== 0429 Mode A ===", flush=True)
    for nm, (sp, st, rf, ot) in dict(
            B=("calf", STIFF_B, REF_B, 0.0),
            B_ot=("calf", STIFF_B, REF_B, 0.69),
            C=("none", 0.0, 2.0, 0.0),
            C_ot1=("none", 0.0, 2.0, 1.0)).items():
        r = run_0429(sp, st, rf, ot)
        print(f"[0429 {nm:5s}] score={r['score']:.1f} q2={r['q2']:.3f} "
              f"dq2={r['dq2']:.2f} h_gap={r['h_gap']:+.3f} (n={r['n']})", flush=True)
    json.dump(dict(base=base, B=rB_best, C=rC_best),
              open(HERE / "p18b_iter10.json", "w"), indent=1)
    print("saved p18b_iter10.json", flush=True)


if __name__ == "__main__":
    main()
