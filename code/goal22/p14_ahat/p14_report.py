"""P14 리포트 — JA/JC 분해, 새 a_hat 갤러리 full-replay (h 언더점프 판정), a_hat 곡선 그림."""
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
import p14_judge as J

G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/g22_cl_gallery")


def gallery(x36):
    """새 a_hat으로 τ 입력을 재변환한 Mode A full-replay 갤러리."""
    sys.path.insert(0, str(HERE.parents[2] / "code/goal19/phase11"))
    import mshoot_fourbar as FB
    P12 = J._P["P12"]
    x36 = np.asarray(x36)
    A = x36[32:36]
    model, dd = J.build_model(x36[:32])
    from collections import defaultdict
    G = defaultdict(lambda: np.zeros(7))
    for tr in P12._G["trials"]:
        if not tr["isj"]:
            continue
        ds, sub, td = tr["ds"], tr["sub"], tr["td"]
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
        t = np.asarray(td["t"])
        td2 = dict(td)
        n1 = J.ahat(A, tr["raw1"], tr["v1"]); n2 = J.ahat(A, tr["raw2"], tr["v2"])
        td2["tau1_real"] = np.interp(t - J.SD, t, n1)
        td2["tau2_real"] = np.interp(t - J.SD, t, n2)
        log = FB.run_jump_sim_fourbar(model, td2)
        if log is None:
            G[ds] += [1, 1, 10, 10, 0, 1, 1]
            continue
        mk = (log["t"] >= 0) & (log["t"] <= t[-1])
        f = lambda a: np.interp(t, log["t"][mk], a[mk])
        r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
        hr = float(td.get("h_real", np.nan))
        G[ds] += [r(f(-log["q1"] - np.pi / 2), td["q1"] + o1), r(f(-log["q2"]), td["q2"] + o2),
                  r(f(-log["dq1"]), td["dq1"]), r(f(-log["dq2"]), td["dq2"]),
                  float(log["base_z"].max()), hr if np.isfinite(hr) else 0.0, 1]
    return {ds: dict(q1=g[0] / g[6], q2=g[1] / g[6], dq1=g[2] / g[6], dq2=g[3] / g[6],
                     h_ratio=g[4] / max(g[5], 1e-9)) for ds, g in G.items() if g[6]}


def main():
    J.winit()
    cand = json.load(open(HERE / "fourbar_p14_candidate.json"))
    x_sel = np.array(cand["x"])
    h = json.load(open(HERE.parent / "fourbar_p13h_candidate.json"))
    x_h36 = np.concatenate([np.array(h["x"]), J.A_PAPER])

    # JA/JC 분해
    r0 = J.eval36(x_h36)
    rs = J.eval36(x_sel)
    ja = sum(rs["A"][g] / r0["A"][g] for g in G7) / len(G7)
    print(f"분해: JA(ModeA)={ja:.4f}  JC(폐루프)={rs['C']/r0['C']:.4f} "
          f"(둘 다 <1 = 동시 개선)", flush=True)
    for g in G7:
        print(f"  {g:10s} {rs['A'][g]/r0['A'][g]:.3f}", flush=True)

    # 갤러리 (P13h+paper vs P14)
    print("\n=== 갤러리 full-replay (P13h+paper -> P14) ===", flush=True)
    g_h = gallery(x_h36)
    g_p = gallery(x_sel)
    for ds in ["jump_position_0421", "jump_0424", "jump_0602", "jump_0324"]:
        a, b = g_h[ds], g_p[ds]
        print(f"{ds:20s} q2 {a['q2']:.3f}->{b['q2']:.3f}  dq2 {a['dq2']:.2f}->{b['dq2']:.2f}  "
              f"h {a['h_ratio']:.3f}->{b['h_ratio']:.3f}", flush=True)
    json.dump(dict(ja=float(ja), jc=float(rs["C"] / r0["C"]),
                   gallery_h=g_h, gallery_p14=g_p),
              open(HERE / "p14_gallery.json", "w"), indent=1, default=float)

    # a_hat 곡선 그림
    A = np.array(cand["A_HAT"])
    tr_ = np.linspace(-36, 36, 400)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
    for Ax, nm in [(J.A_PAPER, "paper"), (A, "P14 fit")]:
        ax[0].plot(tr_, J.ahat(Ax, tr_, np.full_like(tr_, +5.0)), lw=1.4, label=nm)
        ax[1].plot(tr_[tr_ > 0], J.ahat(Ax, tr_[tr_ > 0], np.full_like(tr_[tr_ > 0], +5.0))
                   / tr_[tr_ > 0], lw=1.4, label=nm)
    ax[0].plot(tr_, tr_, "k:", lw=0.8, label="1:1")
    ax[0].set_xlabel("reported tau (raw) [Nm]"); ax[0].set_ylabel("shaft tau [Nm]")
    ax[0].set_title("a_hat 곡선 (motoring, v=+5rad/s)")
    ax[1].set_xlabel("reported tau [Nm]"); ax[1].set_ylabel("변환비 shaft/raw")
    ax[1].set_title("유효 변환비 — 벤치에서 검증할 예측")
    for a_ in ax:
        a_.grid(alpha=0.3); a_.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(SCR / "p14_ahat_curve.png", dpi=115)
    print("\nsaved p14_gallery.json + p14_ahat_curve.png", flush=True)


if __name__ == "__main__":
    main()
