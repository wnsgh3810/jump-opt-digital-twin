# -*- coding: utf-8 -*-
"""P18b 최종 스택으로 0429 결과 재생성 (png_v2 + traj_v2 + json)."""
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
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from cvt_run2 import build_cvt2, sim_run, metrics2, score, SD
from cvt_core import load_0429, label_gains_429, SUBS429

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
A = np.array(C16["x"][32:36])
W = json.load(open(HERE / "p18b_iter11.json"))["x"]
STIFF, REF = W[0], W[1]
O1Q, O2Q = 3.14 * np.pi / 180, -3.0 * np.pi / 180
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_cvt_0429_results")
(DST / "png_v2").mkdir(parents=True, exist_ok=True)
TRAJD = HERE / "traj_v2"; TRAJD.mkdir(exist_ok=True)


def fig_trial(sub, d, L, m, tag, l_i):
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk] - O1Q), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk] - O2Q), "C0", lw=1.3, label="q2(crank) sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    if tag == "CL":
        ax[0, 0].plot(t, np.degrees(d["qd1"]), "C2--", lw=1.1, label="q_des")
        ax[0, 0].plot(t, np.degrees(d["qd2"]), "C2--", lw=1.1, label="_nolegend_")
    ax[0, 0].set_ylabel("q [deg]")
    ax[0, 1].plot(L["t"][mk], L["dq1"][mk], lw=1.3, label="sim")
    ax[0, 1].plot(t, d["dq1"], lw=1.3, label="real")
    ax[0, 1].set_ylabel("dq1 hip [rad/s]")
    ax[0, 2].plot(L["t"][mk], L["dq2"][mk], lw=1.3, label="sim")
    ax[0, 2].plot(t, d["dq2"], lw=1.3, label="real")
    ax[0, 2].set_ylabel("dq2 crank [rad/s]")
    ax[1, 0].plot(L["t"][mk], L["sh1"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 0].plot(t, tp1, lw=1.3, label="real tau (a_hat)")
    ax[1, 0].set_ylabel("hip tau [Nm]")
    ax[1, 1].plot(L["t"][mk], L["sh2"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 1].plot(t, tp2, lw=1.3, label="real tau (a_hat)")
    ax[1, 1].set_ylabel("knee(crank) tau [Nm]")
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a_ in ax.flat:
        a_.grid(alpha=0.3); a_.legend(fontsize=7); a_.set_xlabel("t [s]")
    extra = " · 실효게인 α+클립 반영" if tag == "CL" else ""
    fig.suptitle(f"26.04.29/{sub} [{tag} FINAL P18b, l_i={l_i*1000:.1f}mm{extra}] — "
                 f"q2 RMSE {m['q2']:.3f} rad · dq2 {m['dq2']:.2f} · "
                 f"h_sim {m['h']:.2f} / h_real {m['h_real']:.2f} m")
    fig.tight_layout()
    fig.savefig(DST / "png_v2" / f"{sub}__{tag}.png", dpi=100)
    plt.close(fig)


def run_one(args):
    sub, mode = args
    if not J._P:
        J.winit()
    d = load_0429(sub)
    x32 = np.array(X37[:32]); x32[11] = max(STIFF, 1e-6)
    model, _ = build_cvt2(d["l_i"], "calf", "crank", x32=x32, ref=REF)
    gains = label_gains_429(sub) if mode == "CL" else None
    # CL은 P19 커맨드층 반영: 실효 게인 α (데이터 전용 적합, p19_cmdlayer) + raw 클립 ±35.5
    ALPHA_0429 = [1.18, 0.37, 1.58, 0.93]
    kw = dict(alphas=ALPHA_0429, clip_raw=35.5) if mode == "CL" else {}
    L, _ = sim_run(model, d, d["l_i"], mode, gains=gains, o1=O1Q, o2=O2Q, **kw)
    if L is None:
        return dict(sub=sub, mode=mode, err="CRASH")
    m = metrics2(d, L, O1Q, O2Q)
    fig_trial(sub, d, L, m, mode, d["l_i"])
    np.savez(TRAJD / f"{sub}__{mode}.npz",
             t=L["t"], q1=L["q1"], q2=L["q2"], qk=L["qk"], qpin=L["qpin"], bz=L["bz"],
             dq1=L["dq1"], dq2=L["dq2"], sh1=L["sh1"], sh2=L["sh2"], grf=L["grf"],
             l_i=d["l_i"])
    return dict(sub=sub, mode=mode, score=score(m), **m)


def main():
    import multiprocessing as mp
    jobs = [(s, m) for s in SUBS429 for m in ("A", "CL")]
    pool = mp.Pool(10, initializer=J.winit)
    res = {}
    for r in pool.imap_unordered(run_one, jobs):
        res[f"{r['sub']}/{r['mode']}"] = r
        if "err" not in r:
            print(f"{r['sub']:20s}/{r['mode']:2s} q2 {r['q2']:.3f} dq2 {r['dq2']:.2f} "
                  f"h {r['h']:.3f}/{r['h_real']:.3f}", flush=True)
    pool.close(); pool.join()
    json.dump(res, open(HERE / "cvt_results_v2.json", "w"), indent=1)
    for mode in ("A", "CL"):
        ks = [k for k in res if k.endswith("/" + mode) and "err" not in res[k]]
        g = lambda f: np.mean([res[k][f] for k in ks])
        print(f"[{mode} 평균] score {g('score'):.1f} q2 {g('q2'):.3f} dq2 {g('dq2'):.2f} "
              f"h {g('h'):.3f}/{g('h_real'):.3f}", flush=True)
    print("saved cvt_results_v2.json", flush=True)


if __name__ == "__main__":
    main()
