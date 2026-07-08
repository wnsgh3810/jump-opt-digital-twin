"""GOAL22 P13 — 구간별(초반홀드/푸시/비행) × 채널별 × 게인변형별 오차 분해.

사용자 가설 (07-09): fit은 dq 고점을 얻는 대신 초반 q1 추종을 잃고, 그 결과가
토크 재분배로 나타난다. + "검증 기준" 논쟁: label(명목 게인) vs fit(상태적합) vs
★ reg(데이터 회귀 실효 게인 — 토크 법칙 공간에서 적합, 널-오염 없음).

reg 게인: 0324/0421 = V2 (dq_des=0), 0424/0602 = V1 (dq_des 인가), 0324 knee = V3 (ff).
구간: 초반 = [0, 모션온셋(|dq2_real|>1.0)], 푸시 = [온셋, 이륙(grf_real<5)], 비행 = 이후.
"""
import sys, json
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).parent))
import g22_p10_cl as CL
from g22_p10_pdlaw import SETS

TRAJ = Path(__file__).parent / "p10_cl_traj"
OUT = Path(__file__).parent / "p13_phases.json"
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/g22_cl_gallery")
PDLAW = json.load(open(Path(__file__).parent / "p10_pdlaw.json"))


def reg_gains(ds, sub):
    v_h = "V2" if ds in ("jump_0324", "jump_position_0421") else "V1"
    v_k = "V3" if ds == "jump_0324" else v_h
    g1 = PDLAW[f"{ds}/{sub}/j1"][v_h]
    g2 = PDLAW[f"{ds}/{sub}/j2"][v_k]
    return (max(g1["kp"], 1.0), max(g1["kd"], 0.02), max(g2["kp"], 1.0), max(g2["kd"], 0.02))


def phases(d):
    t = d["t"]
    dq2 = np.asarray(d["dq2"])
    on = np.argmax(np.abs(dq2) > 1.0)
    if on == 0 and abs(dq2[0]) <= 1.0:
        on = len(t) // 4
    gr = d.get("grf_real")
    if gr is not None:
        idx = np.where(gr[on:] < 5.0)[0]
        toff = on + (idx[0] if len(idx) else len(t) - 1 - on)
    else:
        toff = int(len(t) * 0.8)
    return on, toff


def seg_metrics(t, L, d, on, toff):
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - CL.SD, t, d["tau1_paper"])
    tp2 = np.interp(t - CL.SD, t, d["tau2_paper"])
    sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                tau1=g("sh1"), tau2=g("sh2"))
    reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"], tau1=tp1, tau2=tp2)
    segs = dict(early=slice(0, on), push=slice(on, toff), flight=slice(toff, len(t)))
    out = {}
    for sn, sl in segs.items():
        if sl.stop - sl.start < 5:
            continue
        out[sn] = {ch: float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2)))
                   for ch in sims}
    # dq 고점 오차 (푸시+비행 전체)
    for ch in ("dq1", "dq2"):
        i_r = np.argmax(np.abs(reals[ch]))
        i_s = np.argmax(np.abs(sims[ch]))
        out[f"pk_{ch}"] = float(abs(abs(sims[ch][i_s]) - abs(reals[ch][i_r])))
    return out


def L_from_npz(f):
    z = np.load(f)
    L = {k: z[k] for k in ["t", "q1", "q2", "dq1", "dq2", "sh1", "sh2", "grf", "bz"]}
    L["o"] = tuple(z["o"])
    return L


def main():
    CL.winit()
    res = {}
    for ds, (root, subs) in SETS.items():
        use_dqdes = ds in ("jump_0424", "jump_0602")
        ffk = (ds == "jump_0324")
        for sub in subs:
            d = CL.load_trial_xlsx(ds, root, sub)
            t = d["t"]
            on, toff = phases(d)
            variants = {}
            for tag in ("label", "fit"):
                f = TRAJ / f"{ds}__{sub}__{tag}.npz"
                if f.exists():
                    variants[tag] = L_from_npz(f)
            gr_ = reg_gains(ds, sub)
            Lr = CL.run_cl(ds, d, gr_, ffk, use_dqdes)
            if Lr is not None:
                variants["reg"] = Lr
            res[f"{ds}/{sub}"] = dict(on_ms=float(t[on] * 1e3), toff_ms=float(t[min(toff, len(t)-1)] * 1e3),
                                      gains_reg=[float(v) for v in gr_])
            for tag, L in variants.items():
                res[f"{ds}/{sub}"][tag] = seg_metrics(t, L, d, on, toff)
            print("done", ds, sub, flush=True)
    json.dump(res, open(OUT, "w"), indent=1)

    # ── 요약: 데이터셋 × 구간 × 채널, 변형별 중앙값 ──
    print("\n=== 구간별 RMSE 중앙값 (label / reg / fit) ===")
    for ds in SETS:
        ks = [k for k in res if k.startswith(ds + "/")]
        print(f"\n[{ds}]")
        for seg in ("early", "push", "flight"):
            line = f"  {seg:6s}: "
            for ch in ("q1", "q2", "dq1", "dq2", "tau2"):
                vals = {}
                for tag in ("label", "reg", "fit"):
                    xs = [res[k][tag][seg][ch] for k in ks
                          if tag in res[k] and seg in res[k][tag]]
                    vals[tag] = np.median(xs) if xs else np.nan
                best = min(vals, key=lambda tg: vals[tg] if np.isfinite(vals[tg]) else 9e9)
                line += f"{ch} {vals['label']:.3f}/{vals['reg']:.3f}/{vals['fit']:.3f}({best[0]})  "
            print(line, flush=True)
        # dq 고점
        for ch in ("pk_dq1", "pk_dq2"):
            vals = {tag: np.median([res[k][tag][ch] for k in ks if tag in res[k]])
                    for tag in ("label", "reg", "fit")}
            print(f"  {ch:6s}: label {vals['label']:.2f} / reg {vals['reg']:.2f} / fit {vals['fit']:.2f}",
                  flush=True)

    # ── 0602_90 상세 그림 ──
    key = "jump_0602/90_0.75_90_2"
    ds, sub = key.split("/")
    d = CL.load_trial_xlsx(ds, SETS[ds][0], sub)
    t = d["t"]
    on, toff = phases(d)
    Ls = {"label": L_from_npz(TRAJ / f"{ds}__{sub}__label.npz"),
          "fit": L_from_npz(TRAJ / f"{ds}__{sub}__fit.npz"),
          "reg": CL.run_cl(ds, d, reg_gains(ds, sub), False, True)}
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    tp2 = np.interp(t - CL.SD, t, d["tau2_paper"])
    for tag, L in Ls.items():
        g = lambda k: np.interp(t, L["t"], L[k])
        o1, _ = L["o"]
        ax[0].plot(t * 1e3, np.degrees(g("q1") - o1 - d["q1"]), lw=1.3, label=f"{tag}")
        ax[1].plot(t * 1e3, g("dq2"), lw=1.3, label=f"{tag}")
        ax[2].plot(t * 1e3, g("sh2"), lw=1.3, label=f"{tag}")
    ax[1].plot(t * 1e3, d["dq2"], "k--", lw=1.4, label="real")
    ax[2].plot(t * 1e3, tp2, "k--", lw=1.4, label="real")
    for a, ttl, yl in zip(ax, ["q1 오차 (sim−real)", "dq2", "knee tau"],
                          ["q1 err [deg]", "dq2 [rad/s]", "tau [Nm]"]):
        for x in (t[on] * 1e3, t[min(toff, len(t)-1)] * 1e3):
            a.axvline(x, ls=":", lw=0.9, color="gray")
        a.set_title(ttl); a.set_ylabel(yl); a.set_xlabel("t [ms]")
        a.grid(alpha=0.3); a.legend(fontsize=8)
    fig.suptitle(f"{key} — 구간별 label/reg/fit (점선 세로 = 모션온셋·이륙)")
    fig.tight_layout()
    fig.savefig(SCR / "p13_phases_0602_90.png", dpi=115)
    print("\nsaved p13_phases.json + p13_phases_0602_90.png", flush=True)


if __name__ == "__main__":
    main()
