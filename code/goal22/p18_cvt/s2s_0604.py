# -*- coding: utf-8 -*-
"""P18c — 26.06.04 페이로드 sit-to-stand 검증 (P18b 최종 모델).

데이터: cvt/{no_load, load_2.5, load_5} (l_i=25.2mm) + no_cvt/no_load (l_i=30mm).
no_cvt/{load_5, load_7.5}는 기립 실패로 xlsx 미수출 (영상만) — 반사실 실험 대상.
모델: P18b (spring 0.404@calf ref 2.15), 페이로드 = base 질량 가산 (레일 병진만이라 정확),
      프리로드 = l_i=30mm에만 +2.06 Nm (P18b), cvt는 0.
검증: Mode A (τ replay) + CL (회귀 게인, dq_des 인가) + 반사실 (no_cvt에 로드, 천장 유/무).
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
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import sys, json
import numpy as np
import pandas as pd
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
from cvt_run2 import build_cvt2, sim_run, SD

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
A = np.array(C16["x"][32:36])
W = json.load(open(HERE / "p18b_iter11.json"))["x"]
STIFF, REF = W[0], W[1]
PRELOAD_30 = 2.06          # l_i=30mm 전용 (P18b, 세션 평균)
CAP_SHAFT = float(J.ahat(A, np.array([35.5]), np.array([0.0]))[0]) if False else None
D04 = Path((DATA_ROOT + "/26_06_04"))
DST = Path((LEGACY_ROOT + "/g22_s2s_0604_results"))
(DST / "png").mkdir(parents=True, exist_ok=True)
(DST / "counterfactual").mkdir(exist_ok=True)
TRIALS = [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5), ("cvt", "load_5", 5.0),
          ("no_cvt", "no_load", 0.0)]


def load_0604(grp, sub):
    p = D04 / grp / sub
    def rd(fn):
        df = pd.read_excel(p / fn)
        return {c: df[c].values.astype(float) for c in df.columns}
    hip = rd("hip.xlsx"); knee = rd("knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    t = hip["Time"][:n] - hip["Time"][0]
    d = dict(t=t, h_real=float("nan"))
    for nm, src in [("1", hip), ("2", knee)]:
        d["q" + nm] = src["currentAngle"][:n]; d["qd" + nm] = src["desiredAngle"][:n]
        d["dq" + nm] = src["currentAngleVelocity"][:n]; d["dqd" + nm] = src["desiredAngleVelocity"][:n]
        d["traw" + nm] = src["currentTorque"][:n]; d["tdes" + nm] = src["desiredTorque"][:n]
    try:
        grf = pd.read_excel(p / "GRF.xlsx")
        col = [c for c in grf.columns if "Current" in c][0]
        g = grf[col].values.astype(float)
        d["grf_real"] = g[:n] if len(g) >= n else np.pad(g, (0, n - len(g)), "edge")
    except Exception:
        d["grf_real"] = None
    if grp == "cvt":
        cl = pd.read_excel(p / "clutch.xlsx")
        m = (cl["Time"].values >= hip["Time"][0]) & (cl["Time"].values <= hip["Time"][n - 1])
        d["l_i"] = float(np.median(cl["Current Link Length [mm]"].values[m])) / 1000.0
    else:
        d["l_i"] = 0.030
    return d


def regress_gains(d):
    """V1 회귀 (dq_des 인가): traw ~ kp(qd-q) + kd(dqd-dq). 포화 샘플 제외."""
    out = []
    for j in (1, 2):
        m = np.abs(d[f"traw{j}"]) < 17.5
        e = (d[f"qd{j}"] - d[f"q{j}"])[m]
        ev = (d[f"dqd{j}"] - d[f"dq{j}"])[m]
        y = d[f"traw{j}"][m]
        X_ = np.column_stack([e, ev])
        c, *_ = np.linalg.lstsq(X_, y, rcond=None)
        yh = X_ @ c
        r2 = 1 - np.sum((y - yh) ** 2) / np.sum((y - y.mean()) ** 2)
        out += [float(c[0]), float(c[1]), float(r2), float(100 * (~m).mean())]
    return out  # kp1,kd1,r2_1,sat1, kp2,kd2,r2_2,sat2


def build_0604(l_i, load_kg):
    x32 = np.array(X37[:32]); x32[11] = max(STIFF, 1e-6)
    model, dd = build_cvt2(l_i, "calf", "crank", x32=x32, ref=REF)
    mj = J._P["mj"]
    bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
    model.body_mass[bid] += load_kg      # 레일 병진 전용 body — 질량 가산이 정확
    return model


def metrics_s2s(d, L):
    t = d["t"]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    r = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    m = dict(q1=r(f(L["q1"]), d["q1"]), q2=r(f(L["q2"]), d["q2"]),
             dq1=r(f(L["dq1"]), d["dq1"]), dq2=r(f(L["dq2"]), d["dq2"]))
    if d["grf_real"] is not None:
        m["grf"] = r(f(L["grf"]), d["grf_real"])
        m["grf_mean_sim"] = float(np.mean(f(L["grf"])))
        m["grf_mean_real"] = float(np.mean(d["grf_real"]))
    m["pk_sh2_sim"] = float(np.max(np.abs(L["sh2"][mk])))
    tp2 = J.ahat(A, d["traw2"], d["dq2"])
    m["pk_sh2_real"] = float(np.max(np.abs(tp2)))
    m["stand_sim"] = float(L["bz"][mk].max() - L["bz"][mk][0])
    return m


def fig_trial(name, d, L, m, tag, l_i, load, outdir="png"):
    t = d["t"]
    mk = (L["t"] >= -0.02) & (L["t"] <= t[-1] + 0.01)
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    fig, ax = plt.subplots(2, 3, figsize=(14.5, 7))
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q1"][mk]), "C0", lw=1.3, label="q1 sim")
    ax[0, 0].plot(t, np.degrees(d["q1"]), "C1", lw=1.3, label="q1 real")
    ax[0, 0].plot(L["t"][mk], np.degrees(L["q2"][mk]), "C0", lw=1.3, label="q2(crank) sim")
    ax[0, 0].plot(t, np.degrees(d["q2"]), "C1", lw=1.3, label="q2 real")
    if tag.startswith("CL"):
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
    ax[1, 1].axhline(19.3, ls=":", color="gray", lw=1, label="supply ceiling (raw 35.5)")
    ax[1, 1].axhline(-19.3, ls=":", color="gray", lw=1)
    ax[1, 1].set_ylabel("knee(crank) tau [Nm]")
    ax[1, 2].plot(L["t"][mk], L["grf"][mk], lw=1.3, label="sim")
    if d.get("grf_real") is not None:
        ax[1, 2].plot(t, d["grf_real"], lw=1.3, label="real")
    ax[1, 2].set_ylabel("GRF z [N]")
    for a_ in ax.flat:
        a_.grid(alpha=0.3); a_.legend(fontsize=7); a_.set_xlabel("t [s]")
    gtxt = f"q2 {m['q2']:.3f} rad · dq2 {m['dq2']:.2f}" if "q2" in m else ""
    fig.suptitle(f"26.06.04/{name} [{tag}, l_i={l_i*1000:.1f}mm, load {load}kg, P18b] {gtxt}")
    fig.tight_layout()
    fig.savefig(DST / outdir / f"{name.replace('/', '_')}__{tag}.png", dpi=100)
    plt.close(fig)


def run_one(args):
    grp, sub, load, mode, gains, preload, cap = args
    if not J._P:
        J.winit()
    d = load_0604(grp, sub)
    model = build_0604(d["l_i"], load)
    L, _ = sim_run(model, d, d["l_i"], mode, gains=gains, preload=preload, cap=cap)
    if L is None:
        return dict(name=f"{grp}/{sub}", mode=mode, err="CRASH")
    m = metrics_s2s(d, L)
    tag = mode if cap is None else mode + "cap"
    fig_trial(f"{grp}/{sub}", d, L, m, tag, d["l_i"], load)
    np.savez(HERE / "traj_0604" / f"{grp}_{sub}__{tag}.npz",
             t=L["t"], q1=L["q1"], q2=L["q2"], qk=L["qk"], qpin=L["qpin"], bz=L["bz"],
             dq1=L["dq1"], dq2=L["dq2"], sh1=L["sh1"], sh2=L["sh2"], grf=L["grf"],
             l_i=d["l_i"])
    return dict(name=f"{grp}/{sub}", mode=tag, load=load, **m)


def main():
    (HERE / "traj_0604").mkdir(exist_ok=True)
    J.winit()
    # 1) 게인 회귀
    gains = {}
    print(f"{'trial':16s} {'kp1':>6} {'kd1':>5} {'R2':>5} {'sat%':>4} | "
          f"{'kp2':>6} {'kd2':>5} {'R2':>5} {'sat%':>4}")
    for grp, sub, load in TRIALS:
        d = load_0604(grp, sub)
        g = regress_gains(d)
        gains[f"{grp}/{sub}"] = (g[0], g[1], g[4], g[5])
        print(f"{grp+'/'+sub:16s} {g[0]:6.1f} {g[1]:5.2f} {g[2]:5.2f} {g[3]:4.1f} | "
              f"{g[4]:6.1f} {g[5]:5.2f} {g[6]:5.2f} {g[7]:4.1f}", flush=True)
    json.dump(gains, open(HERE / "s2s_0604_gains.json", "w"), indent=1)

    # 2) Mode A + CL (usable 4 trials)
    import multiprocessing as mp
    jobs = []
    for grp, sub, load in TRIALS:
        pre = PRELOAD_30 if grp == "no_cvt" else 0.0
        jobs.append((grp, sub, load, "A", None, pre, None))
        jobs.append((grp, sub, load, "CL", gains[f"{grp}/{sub}"], pre, None))
    pool = mp.Pool(8, initializer=J.winit)
    res = list(pool.imap_unordered(run_one, jobs))
    pool.close(); pool.join()
    for r in sorted(res, key=lambda r: (r["name"], r["mode"])):
        if "err" in r:
            print(r["name"], r["mode"], "CRASH", flush=True); continue
        print(f"{r['name']:16s} {r['mode']:4s} q1 {r['q1']:.3f} q2 {r['q2']:.3f} "
              f"dq1 {r['dq1']:.2f} dq2 {r['dq2']:.2f} "
              f"GRF {r.get('grf_mean_sim', 0):.0f}/{r.get('grf_mean_real', 0):.0f}N "
              f"pk_tau2 {r['pk_sh2_sim']:.1f}/{r['pk_sh2_real']:.1f}Nm", flush=True)
    json.dump([r for r in res], open(HERE / "s2s_0604_results.json", "w"), indent=1)
    print("PART1 DONE", flush=True)


if __name__ == "__main__":
    main()
