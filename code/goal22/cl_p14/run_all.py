"""cl_p14 — P14 (이중 심판 식별 모델 + a_hat)로 g22 폐루프 PD 재현 전체 재실행.

구성 = P10 v5 프로토콜 그대로 (라벨 게인, 무클립, dq_des 규칙, 0324 knee ff),
단 모델 x32 = P14, 액추에이터·실측 τ 참조 변환 = P14 a_hat (4계수).
산출: trial별 6-패널 그림(표준 규격) + traj npz + canonical 4-bar GIF + P13h+paper 대비 표.
"""
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
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
import p14_judge as J
from g22_p10_pdlaw import SETS, label_gains
from g22_p10_cl import load_trial_xlsx, SD
import g22_p10_anim as AN

CAND = json.load(open(HERE.parent / "p14_ahat/fourbar_p14_candidate.json"))
X = np.array(CAND["x"])
A = np.array(CAND["A_HAT"])
OLD = json.load(open(HERE.parent / "p10_cl.json"))
DST = Path((LEGACY_ROOT + "/g22_cl_p14_results"))
(DST / "png").mkdir(parents=True, exist_ok=True)
(DST / "gif").mkdir(parents=True, exist_ok=True)
TRAJD = HERE / "traj"; TRAJD.mkdir(exist_ok=True)
T_SETTLE, T_AFTER = 0.4, 0.6


def run_cl_p14(model, dd, ds, d, gains, ffk, dqdes):
    mj = J._P["mj"]; S = J._P["S"]
    kp1, kd1, kp2, kd2 = gains
    k1, k2 = J.OFFK.get(ds, (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
    t = d["t"]
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes else np.zeros_like(t)
    md = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "grf"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, qd1) - q1c) + kd1 * (np.interp(tm, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm, t, qd2) - q2c) + kd2 * (np.interp(tm, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm, t, d["tdes2"])
        s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
        gz = 0.0
        for ci in range(md.ncon):
            cf = np.zeros(6)
            mj.mj_contactForce(model, md, ci, cf)
            gz += (md.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
        L["grf"][k] = gz
    L["t"] = tl; L["o"] = (o1, o2)
    return L


def metrics(ds, d, L, h_real):
    t = d["t"]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    tp1 = np.interp(t - SD, t, d["tau1_p14"]); tp2 = np.interp(t - SD, t, d["tau2_p14"])
    o1, o2 = L["o"]
    return dict(tau1=r(f(L["sh1"]), tp1), tau2=r(f(L["sh2"]), tp2),
                q1=r(f(L["q1"]) - o1, d["q1"]), q2=r(f(L["q2"]) - o2, d["q2"]),
                dq1=r(f(L["dq1"]), d["dq1"]), dq2=r(f(L["dq2"]), d["dq2"]),
                h=float(L["bz"].max()), h_real=h_real)


def fig_trial(ds, sub, d, L, m):
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, d["tau1_p14"]); tp2 = np.interp(t - SD, t, d["tau2_p14"])
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk] - o1), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk] - o2), "C0", lw=1.3, label="q2 sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    ax[0, 0].plot(t, np.degrees(d["qd1"]), "C2--", lw=1.1, label="q_des")
    ax[0, 0].plot(t, np.degrees(d["qd2"]), "C2--", lw=1.1, label="_nolegend_")
    ax[0, 0].set_ylabel("q [deg]")
    ax[0, 1].plot(L["t"][mk], L["dq1"][mk], lw=1.3, label="sim")
    ax[0, 1].plot(t, d["dq1"], lw=1.3, label="real")
    ax[0, 1].set_ylabel("dq1 hip [rad/s]")
    ax[0, 2].plot(L["t"][mk], L["dq2"][mk], lw=1.3, label="sim")
    ax[0, 2].plot(t, d["dq2"], lw=1.3, label="real")
    ax[0, 2].set_ylabel("dq2 knee [rad/s]")
    ax[1, 0].plot(L["t"][mk], L["sh1"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 0].plot(t, tp1, lw=1.3, label="real tau (P14 a_hat, -1.5ms)")
    ax[1, 0].set_ylabel("hip tau [Nm]")
    ax[1, 1].plot(L["t"][mk], L["sh2"][mk], lw=1.3, label="sim shaft tau")
    ax[1, 1].plot(t, tp2, lw=1.3, label="real tau (P14 a_hat, -1.5ms)")
    ax[1, 1].set_ylabel("knee tau [Nm]")
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a in ax.flat:
        a.grid(alpha=0.3); a.legend(fontsize=7); a.set_xlabel("t [s]")
    fig.suptitle(f"{ds}/{sub} [P14] — 폐루프 PD 재현  tau RMSE hip {m['tau1']:.2f} / "
                 f"knee {m['tau2']:.2f} Nm · h_sim {m['h']:.2f} m / h_real {m['h_real']:.2f} m")
    fig.tight_layout()
    fig.savefig(DST / "png" / f"{ds}__{sub}__p14.png", dpi=100)
    plt.close(fig)


def main():
    J.winit()
    model, dd = J.build_model(X[:32])
    res = {}
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            d = load_trial_xlsx(ds, root, sub)
            d["tau1_p14"] = J.ahat(A, d["traw1"], d["dq1"])
            d["tau2_p14"] = J.ahat(A, d["traw2"], d["dq2"])
            hr = (OLD.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real", float("nan"))
            L = run_cl_p14(model, dd, ds, d, label_gains(ds, sub),
                           ds == "jump_0324", ds in ("jump_0424", "jump_0602"))
            if L is None:
                print(ds, sub, "CRASH", flush=True)
                continue
            m = metrics(ds, d, L, hr)
            res[f"{ds}/{sub}"] = m
            fig_trial(ds, sub, d, L, m)
            np.savez(TRAJD / f"{ds}__{sub}__p14.npz",
                     t=L["t"], q1=L["q1"], q2=L["q2"], bz=L["bz"],
                     dq1=L["dq1"], dq2=L["dq2"], sh1=L["sh1"], sh2=L["sh2"],
                     grf=L["grf"], o=np.array(L["o"]))
            print("done", ds, sub, flush=True)
    json.dump(res, open(HERE / "cl_p14_result.json", "w"), indent=1)

    print("\n=== P13h+paper(v5) -> P14 (폐루프 label 재현, 데이터셋 평균) ===", flush=True)
    for ds in SETS:
        ks = [k for k in res if k.startswith(ds + "/")]
        if not ks:
            continue
        avg = lambda src, f: np.mean([src[k][f] for k in ks])
        oldv = lambda f: np.mean([OLD[k]["label"][f] for k in ks])
        print(f"{ds:22s} q2 {oldv('q2'):.3f}->{avg(res,'q2'):.3f}  "
              f"dq1 {oldv('dq1'):.2f}->{avg(res,'dq1'):.2f}  "
              f"dq2 {oldv('dq2'):.2f}->{avg(res,'dq2'):.2f}  "
              f"tau1 {oldv('tau1'):.2f}->{avg(res,'tau1'):.2f}  "
              f"tau2 {oldv('tau2'):.2f}->{avg(res,'tau2'):.2f}  "
              f"h {oldv('h'):.3f}->{avg(res,'h'):.3f}", flush=True)

    print("\nGIF 렌더링 (canonical 4-bar)...", flush=True)
    anim_model = AN.build_fourbar_model()
    for f in sorted(TRAJD.glob("*__p14.npz")):
        name = f.stem
        ds, sub, _ = name.split("__")
        hr = (OLD.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real")
        AN.render_jump_cl(anim_model, f, DST / "gif" / (name + ".gif"),
                          name.replace("__", " / "), h_real=hr)
    (DST / "MODEL.txt").write_text(
        "cl_p14 — P14 이중 심판 식별 모델 + a_hat\n"
        f"A_HAT = {A.tolist()}  (paper [1.156, 4.17e-4, 0.269, 0.049])\n"
        "x32 = p14_ahat/fourbar_p14_candidate.json\n"
        "프로토콜 = P10 v5 (라벨 게인, 무클립, a_hat 액추에이터, sens_delay -1.5ms)\n",
        encoding="utf-8")
    print("DONE —", DST, flush=True)


if __name__ == "__main__":
    main()
