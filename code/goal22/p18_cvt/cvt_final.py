# -*- coding: utf-8 -*-
"""P18b 최종 검증 — iter11 승자 스택의 전면 평가 + 후보 저장.
1) 평행사변형: Mode A G7 (vs P16 기준) + CL 심판 (o_t 반영 기준토크)
2) 0429: Mode A + CL, 10 trials 전체
3) 정적 감사 재실행 (잔차 표)
4) fourbar_p18b_candidate.json 저장"""
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
from cvt_iter10 import evalG7, G7

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
SD = -0.0015
BASE_G7 = {"w_0421": 2514.1, "w_0424": 3558.4, "w_0602": 2539.3, "w_0324": 2010.2,
           "w_s2s": 5371.9, "fs_0424": 1069.9, "fs_0602": 589.9, "habs": 0.2686}
W = json.load(open(HERE / "p18b_iter11.json"))["x"]
STIFF, REF = W[0], W[1]
OT2 = {"jump_0602": W[2], "jump_position_0421": W[3], "s2s": W[4],
       "jump_0424": W[5], "jump_0324": W[6]}
OT1 = {"s2s": W[7], "jump_position_0421": W[8]}
SP = "calf" if STIFF > 1e-3 else "none"
O1Q, O2Q = 3.14 * np.pi / 180, -3.0 * np.pi / 180


def ofor(ds, table):
    for k, v in table.items():
        if ds.startswith(k):
            return v
    return 0.0


def eval_cl_adj(x32, ref, sp):
    """p14_judge.eval_cl 복제 + 기준토크 오프셋 + 배치."""
    A = np.array(X37[32:36])
    model, _ = build_flip_variant(x32, ref, sp)
    dd = dict(zip(J._P["FR"].NAMES, np.asarray(x32)[:26]))
    fit_s, ho_s = [], []
    for tr in J._P["cl"]:
        L = J.run_cl(model, dd, tr, A)
        if L is None:
            return 99.0, 99.0
        # cl_trial_score에 오프셋 반영 (tp1/tp2 가산) — 복제 채점
        d = tr["d"]; t = d["t"]; on, toff = tr["on"], tr["toff"]
        g = lambda k: np.interp(t, L["t"], L[k])
        o1, o2 = L["o"]
        tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"])) + ofor(tr["ds"], OT1)
        tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"])) + ofor(tr["ds"], OT2)
        sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                    tau1=g("sh1"), tau2=g("sh2"))
        reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"],
                     tau1=tp1, tau2=tp2)
        segs = dict(early=slice(0, on), push=slice(on, min(toff, len(t))),
                    flight=slice(min(toff, len(t)), len(t)))
        tot = wsum = 0.0
        for sn, sl in segs.items():
            if sl.stop - sl.start < 5 or sn not in tr["base"]:
                continue
            rs = []
            for ch in J.CHANNELS:
                b = tr["base"][sn].get(ch, np.nan)
                if not np.isfinite(b) or b < 1e-9:
                    continue
                r = float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2))) / b
                rs.append(min(r, J.RATIO_CLIP))
            if rs:
                tot += J.PW[sn] * np.mean(rs); wsum += J.PW[sn]
        s = tot / max(wsum, 1e-9)
        (ho_s if tr["heldout"] else fit_s).append(s)
    return float(np.mean(fit_s)), float(np.mean(ho_s))


def run_0429_full(mode):
    from cvt_run2 import build_cvt2, metrics2, score, sim_run
    from cvt_core import load_0429, label_gains_429, SUBS429
    x32 = np.array(X37[:32]); x32[11] = max(STIFF, 1e-6)
    out = []
    for sub in SUBS429:
        d = load_0429(sub)
        model, _ = build_cvt2(d["l_i"], SP, "crank", x32=x32, ref=REF)
        gains = label_gains_429(sub) if mode == "CL" else None
        L, _ = sim_run(model, d, d["l_i"], mode, gains=gains, o1=O1Q, o2=O2Q)
        if L is None:
            out.append(dict(sub=sub, score=1e9)); continue
        m = metrics2(d, L, O1Q, O2Q)
        out.append(dict(sub=sub, score=score(m), **m))
    ok = [r for r in out if r["score"] < 1e8]
    g = lambda k: float(np.mean([r[k] for r in ok]))
    print(f"[0429 {mode}] score={g('score'):.1f} q1={g('q1'):.3f} q2={g('q2'):.3f} "
          f"dq1={g('dq1'):.2f} dq2={g('dq2'):.2f} dtoff={g('dtoff')*1000:.1f}ms "
          f"h={g('h'):.3f}/{g('h_real'):.3f} (n={len(ok)})", flush=True)
    return out


def main():
    J.winit()
    print(f"WINNER: stiff={STIFF:.3f} ref={REF:.2f} sp={SP} OT2={OT2} OT1={OT1}",
          flush=True)
    x32 = np.array(X37[:32]); x32[11] = max(STIFF, 1e-6)
    r = evalG7(x32, REF, SP, OT2, OT1)
    print("[G7]", " ".join(f"{g}={r[g]:.0f}({r[g]/BASE_G7[g]:.2f})" for g in G7),
          flush=True)
    c, cg = eval_cl_adj(x32, REF, SP)
    c0, cg0 = 0.8943, 1.0271   # P16 crank 기준 (iter5 judge)
    print(f"[CL] C={c:.4f}({c/c0:.2f}) Cg={cg:.4f}({cg/cg0:.2f})", flush=True)
    a = run_0429_full("A")
    cl = run_0429_full("CL")
    # 정적 감사
    from cvt_iter6 import settle_hold
    A4 = np.array(X37[32:36])
    P12 = J._P["P12"]
    model_s, _ = build_flip_variant(x32, REF, SP)
    res_st = []
    for tr in P12._G["trials"]:
        td = tr["td"]
        dq0 = max(float(np.mean(np.abs(np.asarray(td["dq1"])[:25]))),
                  float(np.mean(np.abs(np.asarray(td["dq2"])[:25]))))
        if dq0 > 0.15:
            continue
        q1_0 = float(np.mean(np.asarray(td["q1"])[:25]))
        q2_0 = float(np.mean(np.asarray(td["q2"])[:25]))
        m1 = float(np.mean(J.ahat(A4, tr["raw1"][:25], tr["v1"][:25]))) + ofor(tr["ds"], OT1)
        m2 = float(np.mean(J.ahat(A4, tr["raw2"][:25], tr["v2"][:25]))) + ofor(tr["ds"], OT2)
        h1, h2 = settle_hold(model_s, q1_0, q2_0)
        res_st.append((tr["ds"], m1 - h1, m2 - h2))
    for ds in sorted(set(x[0] for x in res_st)):
        e1 = [x[1] for x in res_st if x[0] == ds]
        e2 = [x[2] for x in res_st if x[0] == ds]
        print(f"[static {ds:20s}] hip 잔차 {np.mean(e1):+.2f} knee 잔차 {np.mean(e2):+.2f}",
              flush=True)
    json.dump(dict(
        CANDIDATE="P18b — spring resolve + dual-channel session torque offsets (2026-07-09)",
        stiff_knee=STIFF, springref=REF, spring_at=SP, fric_at="crank",
        ot2=OT2, ot1=OT1, o1_0429=O1Q, o2_0429=O2Q,
        base_x37=[float(v) for v in X37],
        G7={g: float(r[g]) for g in G7}, CL=dict(C=c, Cg=cg),
        r0429_A=a, r0429_CL=cl),
        open(HERE / "fourbar_p18b_candidate.json", "w"), indent=1)
    print("saved fourbar_p18b_candidate.json", flush=True)


if __name__ == "__main__":
    main()
