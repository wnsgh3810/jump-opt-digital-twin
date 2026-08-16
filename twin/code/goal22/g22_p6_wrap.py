"""P6 마무리 — 비교 그림(토크 파형 + 수렴 곡선) + CMA 해 배포 CSV (100%/85%)."""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).parent))
import g22_p6_sampling as P6

HERE = Path(__file__).parent
DEP = HERE / "deploy_g22"
DEP.mkdir(exist_ok=True)


def full_trace(x, dense=False, scale=1.0):
    """rollout 재현 + (t, q_crank, dq_crank, tau_cmd) 기록 (push 구간, canonical)."""
    mj = P6._L["mj"]; S = P6._L["S"]; model = P6._L["model"]
    d = mj.MjData(model)
    q1c, q2c = P6._L["q0"]
    sq1, sq2 = -q1c - np.pi / 2, -q2c
    d.qpos[:] = [0.45, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, d)
    dt = model.opt.timestep
    tk = P6._L["tk"]; a = P6._L["csv"]
    if dense:
        tsrc, h1, h2 = a["t_s"], a["tau1_ff_Nm"], a["tau2_ff_Nm"]
    else:
        x = np.asarray(x); tsrc, h1, h2 = tk, x[:P6.NK], x[P6.NK:]
    N = int((P6.T_SETTLE + P6.T_PUSH + P6.T_FLIGHT) / dt)
    rec = []; h_apex = 0.0
    for k in range(N):
        tc = k * dt
        if tc < P6.T_SETTLE:
            th = S.SETTLE_KP * (sq1 - d.qpos[1]) + S.SETTLE_KD * (0 - d.qvel[1])
            tk_ = S.SETTLE_KP * (sq2 - d.qpos[2]) + S.SETTLE_KD * (0 - d.qvel[2])
        elif tc < P6.T_SETTLE + P6.T_PUSH:
            tm = tc - P6.T_SETTLE
            t1 = scale * float(np.interp(tm, tsrc, h1)); t2 = scale * float(np.interp(tm, tsrc, h2))
            av1 = P6.tau_avail(abs(float(d.qvel[1]))); av2 = P6.tau_avail(abs(float(d.qvel[2])))
            t1 = float(np.clip(t1, -av1, av1)); t2 = float(np.clip(t2, -av2, av2))
            th, tk_ = -t1, -t2
            rec.append([tm, -d.qpos[1] - np.pi / 2, -d.qpos[2], -d.qvel[1], -d.qvel[2], t1, t2])
        else:
            th = tk_ = 0.0
        d.ctrl[:] = [th, tk_]
        mj.mj_step(model, d)
        if tc >= P6.T_SETTLE:
            h_apex = max(h_apex, float(d.qpos[0]))
    return np.array(rec), h_apex


def main():
    P6.winit()
    res = json.load(open(HERE / "p6_sampling_env.json"))
    a = P6._L["csv"]

    # ── 그림: 토크 파형 + 수렴 ──
    fig, ax = plt.subplots(2, 2, figsize=(13, 8))
    tr_nlp, h_nlp = full_trace(None, dense=True)
    traces = {"NLP replay": (tr_nlp, h_nlp)}
    for name in ["CMA", "MPPI", "PS"]:
        tr, h = full_trace(res[name]["x"])
        traces[name] = (tr, h)
    for name, (tr, h) in traces.items():
        ax[0, 0].plot(tr[:, 0] * 1e3, tr[:, 5], lw=1.4, label=f"{name} (h={h:.3f}m)")
        ax[0, 1].plot(tr[:, 0] * 1e3, tr[:, 6], lw=1.4, label=name)
        ax[1, 0].plot(tr[:, 0] * 1e3, tr[:, 3], lw=1.2, label=name)
    ax[0, 0].set_title("hip 토크 (포화 후 실제 인가) [Nm]"); ax[0, 0].legend(fontsize=8)
    ax[0, 1].set_title("knee 토크 [Nm]"); ax[0, 1].legend(fontsize=8)
    ax[1, 0].set_title("hip 각속도 [rad/s]"); ax[1, 0].legend(fontsize=8)
    for name in ["CMA", "MPPI", "PS"]:
        hh = np.array(res[name]["hist"])
        ax[1, 1].plot(hh[:, 0], hh[:, 1], lw=1.4, label=name)
    ax[1, 1].axhline(res["nlp"]["h"], ls="--", lw=1.2, label="NLP replay")
    ax[1, 1].set_title("수렴 곡선 (rollouts vs best h)"); ax[1, 1].legend(fontsize=8)
    ax[1, 1].set_xlabel("rollouts")
    for A in ax.flat:
        A.grid(alpha=0.3)
    for A in ax.flat[:3]:
        A.set_xlabel("push t [ms]")
    fig.suptitle("P6 — 트윈(P13e) 위 샘플링 궤적최적화 3종 vs NLP (토크-속도 봉투·과신전 하드스톱 적용)")
    fig.tight_layout()
    fig.savefig(HERE / "p6_summary.png", dpi=115)
    print("saved p6_summary.png", flush=True)

    # ── 배포 CSV (CMA 해, 100% / 85%) ──
    for scale, tag in [(1.0, "s1.00"), (0.85, "s0.85")]:
        tr, h = full_trace(res["CMA"]["x"], scale=scale)
        # 500Hz 리샘플
        t5 = np.arange(0, P6.T_PUSH, 0.002)
        cols = [np.interp(t5, tr[:, 0], tr[:, i]) for i in range(1, 7)]
        M = np.column_stack([t5] + cols)
        fn = DEP / f"jump_g22cma_{tag}_h{h:.3f}m.csv"
        np.savetxt(fn, M, delimiter=",", fmt="%.6f",
                   header="t_s,q1_des_rad,q2_des_rad,dq1_des_rad_s,dq2_des_rad_s,tau1_ff_Nm,tau2_ff_Nm",
                   comments="")
        print(f"saved {fn.name} (h_twin={h:.3f})", flush=True)


if __name__ == "__main__":
    main()
