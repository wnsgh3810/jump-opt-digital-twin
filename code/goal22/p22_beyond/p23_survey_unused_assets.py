# -*- coding: utf-8 -*-
"""p23_survey — READ-ONLY survey of 3 unused data assets.
(A) 26.03.19 s2s_air (+ context: s2s_gnd, tau/no_tr, tau/tr, TR_JUMP clutch)
(B) 26.03.24/sit2stand (5 gain folders)
(C) 26.04.22/Torque Control (3 trials) + csv-vs-xlsx(Paper) torque ratio check
Writes NOTHING into the data root. Output = stdout only.
"""
import sys, json, io
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
REPO = Path("C:/Users/junho/Documents/jump-opt-digital-twin")

# ---- Paper a_hat conversion (canonical constants; fallback if import fails) ----
ahat_src = "inline-fallback"
try:
    sys.path.insert(0, str(REPO / "code/goal22/p19_jump"))
    sys.path.insert(0, str(REPO / "code/bench"))
    import p19_judge as P
    A_PAPER = P.A_PAPER
    def ahat(traw, dq):
        return P.J.ahat(P.A_PAPER, traw, dq)
    ahat_src = "p19_judge.J.ahat"
except Exception as e:
    print(f"[warn] p19_judge import failed ({type(e).__name__}: {e}) -> inline ahat")
    KT, GR, CF = 0.091, 9.0, 0.59
    A_PAPER = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
    def ahat(traw, dq):
        Iq = (CF / (GR * KT)) * np.asarray(traw, float)
        s = np.sign(dq)
        return (A_PAPER[0] * GR * KT * Iq - A_PAPER[1] * GR * np.abs(Iq) * Iq
                - A_PAPER[2] * s - A_PAPER[3] * np.abs(Iq) * s)
print(f"[ahat source] {ahat_src}")


def stat_joint(df):
    t = df["Time"].values
    dt = float(np.median(np.diff(t)))
    q = df["currentAngle"].values
    dq = df["currentAngleVelocity"].values
    traw = df["currentTorque"].values
    out = dict(
        N=len(t), dt_ms=round(dt * 1e3, 3), fs_hz=round(1.0 / dt, 1),
        dur_s=round(float(t[-1] - t[0]), 2),
        q_min=round(float(q.min()), 3), q_max=round(float(q.max()), 3),
        peak_absdq=round(float(np.abs(dq).max()), 2),
        traw_min=round(float(traw.min()), 2), traw_max=round(float(traw.max()), 2),
        n_wrap_gt30=int((np.abs(traw) > 30).sum()),
    )
    if "desiredTorque" in df.columns:
        dtau = df["desiredTorque"].values.astype(float)
        out["desTau_rms"] = round(float(np.sqrt(np.mean(dtau ** 2))), 3)
        out["desTau_maxabs"] = round(float(np.abs(dtau).max()), 3)
        out["desTau_frac_nonzero"] = round(float(np.mean(np.abs(dtau) > 1e-9)), 3)
    if "desiredAngle" in df.columns:
        qd = df["desiredAngle"].values.astype(float)
        out["qdes_min"] = round(float(qd.min()), 3)
        out["qdes_max"] = round(float(qd.max()), 3)
    # time-base gaps
    gaps = np.diff(t)
    out["dt_max_ms"] = round(float(gaps.max()) * 1e3, 2)
    return out


def survey_trial(folder, label):
    folder = Path(folder)
    print(f"\n===== {label}  [{folder}] =====")
    files = sorted(p.name for p in folder.iterdir()) if folder.exists() else []
    key_files = [f for f in files if f.lower() in
                 ("hip.xlsx", "knee.xlsx", "grf.xlsx", "clutch.xlsx", "what.txt",
                  "pid.txt", "real data.txt", "jump_results.xlsx")]
    has_raw_unwrap = (folder / "raw_unwrap").exists()
    has_csv = (folder / "jump_opt_compare" / "predicted_compare.csv").exists()
    print(f"files: {key_files}  raw_unwrap={has_raw_unwrap}  predicted_compare.csv={has_csv}")

    res = {}
    for j in ("hip", "knee"):
        fp = folder / f"{j}.xlsx"
        if not fp.exists():
            print(f"  {j}.xlsx MISSING"); continue
        df = pd.read_excel(fp)
        res[j] = df
        print(f"  {j} cols: {list(df.columns)}")
        print(f"  {j} root: {stat_joint(df)}")
        ru = folder / "raw_unwrap" / f"{j}.xlsx"
        if ru.exists():
            dfr = pd.read_excel(ru)
            s = stat_joint(dfr)
            print(f"  {j} raw_unwrap: N={s['N']} dur={s['dur_s']}s traw[{s['traw_min']},{s['traw_max']}] "
                  f"wraps>30:{s['n_wrap_gt30']}")
            # time-aligned comparison (root xlsx may be a trimmed window of full session)
            tr_root = df["Time"].values; tr_raw = dfr["Time"].values
            print(f"  {j} timebase: root=[{tr_root[0]:.3f},{tr_root[-1]:.3f}] "
                  f"raw_unwrap=[{tr_raw[0]:.3f},{tr_raw[-1]:.3f}]")
            key_root = np.round(tr_root * 500).astype(np.int64)
            key_raw = np.round(tr_raw * 500).astype(np.int64)
            idx = {k: i for i, k in enumerate(key_raw)}
            hits = [(i, idx[k]) for i, k in enumerate(key_root) if k in idx]
            if hits:
                ir, iw = np.array(hits).T
                d_tau = np.abs(df["currentTorque"].values[ir] - dfr["currentTorque"].values[iw])
                d_q = np.abs(df["currentAngle"].values[ir] - dfr["currentAngle"].values[iw])
                print(f"  {j} aligned overlap {len(ir)}/{len(tr_root)}: "
                      f"maxdiff tau={d_tau.max():.3f} q={d_q.max():.5f}")
            else:
                print(f"  {j} aligned overlap: NONE (different timebase)")

    fp = folder / "GRF.xlsx"
    if fp.exists():
        g = pd.read_excel(fp)
        print(f"  GRF cols: {list(g.columns)}")
        col = "Current_GRF" if "Current_GRF" in g.columns else g.columns[-1]
        v = g[col].values.astype(float)
        print(f"  GRF[{col}]: N={len(v)} mean={v.mean():.2f} p95={np.percentile(v,95):.2f} "
              f"max={v.max():.2f} min={v.min():.2f}")
    else:
        print("  GRF.xlsx: ABSENT")

    fp = folder / "Clutch.xlsx"
    if fp.exists():
        c = pd.read_excel(fp)
        print(f"  Clutch cols: {list(c.columns)}")
        licol = [x for x in c.columns if "Link Length" in str(x)]
        if licol:
            li = c[licol[0]].values.astype(float)
            print(f"  l_i [mm]: N={len(li)} mean={li.mean():.3f} std={li.std():.3f} "
                  f"min={li.min():.3f} max={li.max():.3f} first={li[0]:.3f} last={li[-1]:.3f}")
    else:
        print("  Clutch.xlsx: ABSENT (l_i not recorded; no-shift assumption l_i=30.00)")

    for tname in ("PID.txt", "What.txt", "Real Data.txt"):
        fp = folder / tname
        if fp.exists():
            for enc in ("utf-8", "utf-8-sig", "cp949"):
                try:
                    txt = fp.read_text(encoding=enc).strip()
                    break
                except UnicodeDecodeError:
                    continue
            print(f"  {tname}: {txt[:200]!r}")
    return res


def csv_ratio(folder, res, label):
    """Compare jump_opt_compare/predicted_compare.csv torque vs xlsx raw->Paper ahat."""
    fp = Path(folder) / "jump_opt_compare" / "predicted_compare.csv"
    if not fp.exists():
        print(f"  [{label}] no predicted_compare.csv"); return
    pc = pd.read_csv(fp)
    print(f"  [{label}] csv cols: {list(pc.columns)}")
    pt = pc["Time"].values - pc["Time"].values[0]
    for j, ccol in (("hip", "hipCurrentTorquePaper"), ("knee", "kneeCurrentTorquePaper")):
        if ccol not in pc.columns or j not in res:
            print(f"  [{label}] {j}: column/xlsx missing"); continue
        df = res[j]
        t = df["Time"].values - df["Time"].values[0]
        tau_x = ahat(df["currentTorque"].values.astype(float),
                     df["currentAngleVelocity"].values.astype(float))
        tau_c = np.interp(t, pt, pc[ccol].values.astype(float))
        m = np.abs(tau_x) > 2.0
        if m.sum() < 50:
            m = np.abs(tau_x) > 0.5
        r_med = float(np.median(tau_c[m] / tau_x[m]))
        slope = float(np.sum(tau_c[m] * tau_x[m]) / np.sum(tau_x[m] ** 2))
        rmse = float(np.sqrt(np.mean((tau_c - tau_x) ** 2)))
        print(f"  [{label}] {j}: ratio_med={r_med:.4f} slope_LS={slope:.4f} "
              f"RMSE(csv-xlsxPaper)={rmse:.3f} Nm  n_mask={int(m.sum())} "
              f"rms_xlsxPaper={np.sqrt(np.mean(tau_x**2)):.3f} rms_csv={np.sqrt(np.mean(tau_c**2)):.3f}")


# ============================ ASSET A: 26.03.19 ============================
print("\n" + "#" * 70)
print("# ASSET A — 26.03.19 (s2s_air focus)")
print("#" * 70)
B19 = DATA / "26_03_19"
resA = {}
resA["s2s_air"] = survey_trial(B19 / "position/sit2stand_air", "0319 position/sit2stand_air")
resA["s2s_gnd"] = survey_trial(B19 / "position/sit2stand_gnd", "0319 position/sit2stand_gnd (context)")
resA["no_tr_tau"] = survey_trial(B19 / "tau/no_tr_tau", "0319 tau/no_tr_tau (bonus FF torque)")
resA["tr_tau"] = survey_trial(B19 / "tau/tr_tau", "0319 tau/tr_tau (TR - check l_i)")
resA["TR_JUMP"] = survey_trial(B19 / "position/TR_JUMP", "0319 position/TR_JUMP (known-bad l_i check)")
resA["NO_TR_JUMP"] = survey_trial(B19 / "position/NO_TR_JUMP", "0319 position/NO_TR_JUMP (context)")

# ============================ ASSET B: 26.03.24/sit2stand ============================
print("\n" + "#" * 70)
print("# ASSET B — 26.03.24/sit2stand")
print("#" * 70)
B24 = DATA / "26_03_24/sit2stand"
for sub in sorted(p.name for p in B24.iterdir() if p.is_dir()):
    survey_trial(B24 / sub, f"0324 sit2stand/{sub}")

# ============================ ASSET C: 26.04.22/Torque Control ============================
print("\n" + "#" * 70)
print("# ASSET C — 26.04.22/Torque Control")
print("#" * 70)
B22 = DATA / "26_04_22/Torque Control"
for sub in sorted(p.name for p in B22.iterdir() if p.is_dir()):
    res = survey_trial(B22 / sub, f"0422 TC/{sub}")
    csv_ratio(B22 / sub, res, f"0422 {sub}")

print("\n[DONE]")
