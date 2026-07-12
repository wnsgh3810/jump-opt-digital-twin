# -*- coding: utf-8 -*-
"""P20 실험 1 — 상승 성분의 함수형 판별 (a_hat 구조 내 재보정, Paper 형태 유지).

프로브(pre30_probe) 발견: 부족 무릎토크 = 세션별 저속 기준선 + 강도 비례 상승(+2~3Nm).
a_hat 구조: â = A0·GR·KT·Iq − A1·GR·|Iq|Iq − A2·sgn(v) − A3·|Iq|·sgn(v) — 점성(∝v) 항 없음.
→ 구조 내 상승 후보 = δA1(전류 제곱·포화형) / δA3(부하 비례형) / (구조 외 참조) c_v·v.

설계: 세션별 pre(기준선)는 프로브 실측값으로 고정(뉴이선스), 전역 δ 하나를 형태별 스캔.
  성공 = 어떤 형태가 [기준선+상승] 없이 const 2.25보다 창 replay 점수 우수 + s2s 무해
        + 0429 Mode A 개선(모터측이므로 0429에도 반드시 적용돼야 함 — 교차 검증).
0324(held-out) 미사용. 스텝핑 = P12.eval_windows 프로토콜.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_adapter as AD

AD.ensure_init()
import p19_judge as P
from p14_judge import KT, GR, CF, invert_paper

CAND = AD.load_candidate(HERE.parent / "p19_jump/fourbar_p19_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)
A = P.A_PAPER
P12 = P.J._P["P12"]
mj = P.J._P["mj"]
MS = P12._G["MS"]
DD = dict(zip(P.J._P["FR"].NAMES, np.asarray(X32)[:26]))
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20_results")
DST.mkdir(parents=True, exist_ok=True)
# 세션별 저속 기준선 (pre30_probe 초반 창 실측)
BASE = {"jump_position_0421": 0.14, "jump_0424": 1.78, "jump_0602": 2.20,
        "s2s_gnd_0319": 0.99}
JDS = ("jump_position_0421", "jump_0424", "jump_0602")


def iq_of(raw):
    return (CF / (GR * KT)) * np.asarray(raw, float)


def forms(raw2, dq2):
    Iq = iq_of(raw2)
    return {"A1(제곱·포화형)": GR * np.abs(Iq) * Iq,
            "A3(부하비례형)": np.abs(Iq) * np.sign(dq2),
            "visc(점성 참조형)": np.asarray(dq2, float)}


def win_scores(model, tr, tk_extra, th_extra=0.0):
    """창 replay 점수 — tau_k에 시간영역 보정 벡터(tk_extra) 가산."""
    k1, k2 = P12.OFFKEY.get(tr["ds"], (None, None))
    o1 = DD[k1] if k1 else 0.0
    o2 = DD[k2] if k2 else 0.0
    pp0 = tr["pp"]; t = pp0["t"]
    th = -(P.J.ahat(A, tr["raw1"], tr["v1"]) + th_extra)
    tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + tk_extra)
    ppv = dict(pp0, tau_h=np.interp(t - P.SD, t, th), tau_k=np.interp(t - P.SD, t, tk))
    pp = P12._G["sv"](ppv, o1, o2)
    d_ = mj.MjData(model); dt = model.opt.timestep
    out = []
    for i0 in [int(i) for i in pp["starts"]]:
        t1 = min(t[i0] + pp["W"], t[-1])
        qc = float(pp["q2m"][i0]); dqc = float(pp["dq2m"][i0])
        d_.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], qc, -qc, qc]
        d_.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dqc, -dqc, dqc]
        mj.mj_forward(model, d_)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d_.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mj.mj_step(model, d_)
            except Exception:
                ok = False; break
            ts[k] = tc + dt
            q1a[k] = d_.qpos[1]; q2a[k] = d_.qpos[2]
            dq1a[k] = d_.qvel[1]; dq2a[k] = d_.qvel[2]
        if not ok:
            out.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
        mk = (t >= ts[0]) & (t <= ts[-1])
        if mk.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
        out.append(MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
                   + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"])))
    return out


def eval_set(model, dss, tk_fn, th_fn=None):
    """dss 세션들의 전 trial 평균 점수. tk_fn(tr)->보정벡터."""
    per = {}
    for tr in P12._G["trials"]:
        if tr["ds"] not in dss:
            continue
        sc = win_scores(model, tr, tk_fn(tr), th_fn(tr) if th_fn else 0.0)
        per.setdefault(tr["ds"], []).extend(sc)
    return {ds: float(np.mean(v)) for ds, v in per.items()}


def sc429(delta_form=None):
    """0429 Mode A (cma2 프로토콜) — 무릎 raw를 invert_paper로 보정 주입 (hip 불변)."""
    from cvt_run2 import sim_run, metrics2, score
    from cvt_core import load_0429
    import cvt_run2 as C
    SUB4 = ["60_0.75_60_2", "90_1.5_90_2.5", "120_2.2_200_2.8", "150_2.2_500_4"]
    o1, o2 = 3.14 * np.pi / 180, -3.0 * np.pi / 180
    A_save = C.A.copy(); C.A = np.asarray(A, float)
    try:
        scs = []
        model = None
        for sub in SUB4:
            d = load_0429(sub)
            if delta_form is not None:
                lam_t = delta_form(d["traw2"], d["dq2"])
                tgt = P.J.ahat(A, d["traw2"], d["dq2"]) + lam_t
                d = dict(d, traw2=invert_paper(tgt, d["dq2"]))
            if model is None:
                model, _ = P.build_cvt(X32, V[1], SP, d["l_i"])
            L, _ = sim_run(model, d, d["l_i"], "A", o1=o1, o2=o2)
            if L is None:
                return float("nan")
            scs.append(score(metrics2(d, L, o1, o2)))
        return float(np.mean(scs))
    finally:
        C.A = A_save


def main():
    model, _ = P.build_flip(X32, V[1], SP)
    out = {"refs": {}, "hip": {}, "grid": {}, "s2s": {}, "m0429": {}}
    # ── 기준점 2종 ──
    const_fn = lambda tr: 2.25
    base_fn = lambda tr: BASE[tr["ds"]]
    out["refs"]["const2.25"] = eval_set(model, JDS, const_fn)
    out["refs"]["base_only"] = eval_set(model, JDS, base_fn)
    print("ref const2.25:", out["refs"]["const2.25"], flush=True)
    print("ref base_only:", out["refs"]["base_only"], flush=True)
    # ── hip 채널 스캔 (무릎 const 2.25 고정) ──
    for lam_h in (-1.5, -0.75, 0.0, 0.75, 1.5):
        r = eval_set(model, JDS, const_fn, th_fn=lambda tr: lam_h)
        out["hip"][lam_h] = r
        print(f"hip λ={lam_h:+.2f}: " + " ".join(f"{k.split('_')[-1]} {v:.1f}" for k, v in r.items()), flush=True)
    # ── 형태별 δ 그리드 (기준선 + δ·form) ──
    GRIDS = {"A1(제곱·포화형)": [2e-4, 4.17e-4, 8e-4, 1.3e-3, 2e-3],
             "A3(부하비례형)": [0.05, 0.10, 0.15, 0.22],
             "visc(점성 참조형)": [0.05, 0.10, 0.15, 0.20]}
    best = (None, None, 9e9)
    for fname, grid in GRIDS.items():
        for dl in grid:
            fn = lambda tr, _f=fname, _d=dl: BASE[tr["ds"]] + _d * forms(tr["raw2"], tr["v2"])[_f]
            r = eval_set(model, JDS, fn)
            tot = float(np.mean(list(r.values())))
            out["grid"][f"{fname}|{dl}"] = r
            print(f"{fname} δ={dl:g}: 평균 {tot:.1f} | " +
                  " ".join(f"{k.split('_')[-1]} {v:.1f}" for k, v in r.items()), flush=True)
            if tot < best[2]:
                best = (fname, dl, tot)
    print(f"\nBEST: {best[0]} δ={best[1]:g} (평균 {best[2]:.1f})", flush=True)
    # ── 승자: s2s 무해성 + 0429 교차 검증 ──
    fname, dl, _ = best
    fn = lambda tr: BASE[tr["ds"]] + dl * forms(tr["raw2"], tr["v2"])[fname]
    out["s2s"]["winner"] = eval_set(model, ("s2s_gnd_0319",), fn)
    out["s2s"]["base_only"] = eval_set(model, ("s2s_gnd_0319",), base_fn)
    out["s2s"]["const"] = eval_set(model, ("s2s_gnd_0319",), const_fn)
    print("s2s: const", out["s2s"]["const"], "| base", out["s2s"]["base_only"],
          "| winner", out["s2s"]["winner"], flush=True)
    out["m0429"]["ref"] = sc429(None)
    dform = lambda raw, dq, _f=fname, _d=dl: _d * forms(raw, dq)[_f]
    out["m0429"]["winner"] = sc429(dform)
    print(f"0429 Mode A: ref {out['m0429']['ref']:.2f} → winner(+{fname}) {out['m0429']['winner']:.2f}",
          flush=True)
    out["best"] = {"form": fname, "delta": dl}
    json.dump(out, open(DST / "exp1_results.json", "w"), indent=1, default=float)
    # ── 그림 ──
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.5))
    for fname_, grid in GRIDS.items():
        ys = [np.mean(list(out["grid"][f"{fname_}|{d}"].values())) for d in grid]
        xs = list(range(1, len(grid) + 1))
        ax[0].plot(xs, ys, "o-", label=fname_)
    for lab, key in (("const 2.25 (P19)", "const2.25"), ("기준선만", "base_only")):
        ax[0].axhline(np.mean(list(out["refs"][key].values())), ls=":", lw=1)
        ax[0].text(1, np.mean(list(out["refs"][key].values())), lab, fontsize=7, va="bottom")
    ax[0].set_xlabel("δ 그리드 인덱스"); ax[0].set_ylabel("창 replay 점수 (낮을수록 좋음)")
    ax[0].set_title("형태별 δ 스캔 (기준선+상승 분해)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    hs = sorted(out["hip"].keys())
    ax[1].plot(hs, [np.mean(list(out["hip"][h].values())) for h in hs], "o-")
    ax[1].set_xlabel("hip λ [Nm]"); ax[1].set_ylabel("창 점수")
    ax[1].set_title("hip 채널 상수 스캔 (0 근처 최소 = hip은 무보정)"); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(DST / "exp1_forms.png", dpi=110)
    print("saved", DST / "exp1_forms.png", flush=True)


if __name__ == "__main__":
    main()
