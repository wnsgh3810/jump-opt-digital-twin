# -*- coding: utf-8 -*-
"""P19 최종 마감 — cma3 vs cma6 승자 선택 + 전 지표 + 후보 저장 + 진행 차트."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P
import p19_run as R
from p19_cma3 import G6

IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
           solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
N6IDX = {"s_rc": 26, "s_ic": 27, "s_rp": 28, "s_ip": 29, "d_cpin": 30, "d_kneep": 31}
DST = Path((LEGACY_ROOT + "/g22_p19_results"))


def x32_of(W):
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(W["names"]):
        if n in IDX:
            x32[IDX[n]] = W["x"][i]
        elif n in N6IDX:
            x32[N6IDX[n]] = W["x"][i]
    return x32


def full_eval(tag, W):
    v = np.array(W["x"])
    x32 = x32_of(W)
    sp = "calf" if v[0] > 1e-3 else "none"
    qoff = (v[16], v[17])
    rows = R.eval_stack(x32, v[1], sp, P.A_PAPER, v[2], v[15], use_alpha=True,
                        q_off_0429=qoff)
    s = R.summarize(rows)
    # 푸시 충실도
    model_f, _ = P.build_flip(x32, v[1], sp)
    model_c = None
    push = {}
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        alphas = R.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(x32, v[1], sp, l_i)
            L = R.cl_run(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER, v[15],
                         alphas, 0.0, o1=qoff[0], o2=qoff[1])
        else:
            dd = dict(zip(P.J._P["FR"].NAMES, x32[:26]))
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = R.cl_run(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER, v[15],
                         alphas, v[2], o1=o1, o2=o2)
        if L is None:
            continue
        t = d["t"]
        T = t[m][-1]
        mm = m & (t <= 0.75 * T)
        tp1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tp2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]))
        s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
        num = np.sqrt(np.mean((s1 - tp1)[mm] ** 2) + np.mean((s2 - tp2)[mm] ** 2))
        den = max(np.sqrt(np.mean(tp1[mm] ** 2) + np.mean(tp2[mm] ** 2)), 0.5)
        push.setdefault(ds, []).append(num / den)
    pf = float(np.mean([g for ds, gs in push.items() if ds != "jump_0324" for g in gs]))
    ot2 = {ds: v[2] for ds in ("jump_0424", "jump_0602", "jump_position_0421", "jump_0324")}
    ma = P.eval_modeA_jump(x32, v[1], sp, P.A_PAPER, ot2)
    print(f"[{tag}] CLτ FIT {100*s['FIT'][0]:.1f}% HO {100*s['jump_0324'][0]:.1f}% "
          f"| 푸시 {100*pf:.1f}% | ModeA(w) "
          f"{np.mean([ma[g] for g in ('w_0421','w_0424','w_0602')]):.0f} "
          f"fs602 {ma['fs_0602']:.0f} habs {ma['habs']:.3f}", flush=True)
    return dict(s=s, pf=pf, ma={g: float(ma[g]) for g in G6}, rows=rows)


def main():
    P.winit()
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    W3 = json.load(open(HERE / "p19_cma3.json"))
    r3 = full_eval("cma3", W3)
    try:
        W6 = json.load(open(HERE / "p19_cma6.json"))
        r6 = full_eval("cma6", W6)
    except Exception:
        W6, r6 = None, None
    # 승자: CL FIT 우선, HO 게이트 (cma3 대비 +3%p 이내)
    use6 = (r6 is not None and r6["s"]["FIT"][0] < r3["s"]["FIT"][0]
            and r6["s"]["jump_0324"][0] < r3["s"]["jump_0324"][0] + 0.03)
    W, r, tag = (W6, r6, "cma6") if use6 else (W3, r3, "cma3")
    print(f"FINAL = {tag}", flush=True)
    json.dump(dict(CANDIDATE=f"P19 FINAL ({tag}) — jump tau-fidelity (2026-07-10)",
                   A="paper", names=W["names"], x=W["x"], cmdlayer=R.CMD,
                   metric_full=float(r["s"]["FIT"][0]), metric_push=r["pf"],
                   heldout=float(r["s"]["jump_0324"][0]),
                   modeA=r["ma"], rows=r["rows"]),
              open(HERE / "fourbar_p19_candidate.json", "w"), indent=1)
    # 진행 차트 v2
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.6))
    stages = ["P16+A_fit", "P18b+Paper", "CMA-2", f"P19 FINAL\n({tag})"]
    full = [43.7, 46.0, 38.8, 100 * r["s"]["FIT"][0]]
    pushv = [30.0, np.nan, np.nan, 100 * r["pf"]]
    b = ax[0].bar(range(4), full); b[3].set_color("C2")
    for i, s_ in enumerate(full):
        ax[0].text(i, s_ + 0.4, f"{s_:.1f}%", ha="center")
    ax[0].axhline(26, color="r", ls=":", lw=1.5, label="재구성 바닥 ≈26%")
    ax[0].set_xticks(range(4)); ax[0].set_xticklabels(stages, fontsize=9)
    ax[0].set_ylabel("점프 CL τ-갭 전체창 (FIT, %)"); ax[0].legend(); ax[0].grid(alpha=0.3, axis="y")
    ax[1].bar([0, 1], [30.0, 100 * r["pf"]], color=["C0", "C2"])
    ax[1].text(0, 30.4, "30.0%", ha="center"); ax[1].text(1, 100 * r["pf"] + 0.4, f"{100*r['pf']:.1f}%", ha="center")
    ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["P16+A_fit", f"P19 FINAL"])
    ax[1].set_ylabel("푸시 충실도 τ-갭 (이륙 전이 제외, %)")
    ax[1].grid(alpha=0.3, axis="y")
    fig.suptitle("P19 마라톤 최종 — 폐루프 토크 예측")
    fig.tight_layout()
    fig.savefig(DST / "marathon_p19.png", dpi=130)
    print("saved candidate + chart", flush=True)


if __name__ == "__main__":
    main()
