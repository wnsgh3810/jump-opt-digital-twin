# -*- coding: utf-8 -*-
"""fs_compare_plot — 전 데이터 3자 비교 그래프: 실측 vs 배포모델(OLD) vs 현행(fs15).

채널: q1·q2 [°], dq1·dq2 [rad/s], τ1·τ2 [Nm] — 6패널 1장/trial.
모드:
  CL    = 폴더 게인 PD 폐루프. **점프(push) 구간만** (push 시작−0.05s ~ 이륙, 사용자 지시).
          OLD = TW.rollout_cl(alphas=TH/TK 또는 세션 R19.ALPH) · fs15 = FR.rollout_cl_fs(스큐+실게인+TC2ms)
  ModeA = mshoot 0.4s 창/0.3s stride, 측정 raw 주입·측정상태 리셋 (창별 조각 오버레이).
          OLD = TW.rollout_ol(구 플랜트) · fs = FR.rollout_ol_fs_b(내장 스프링 플랜트)
출력: _compare/CL/<세션>/<trial>.png · _compare/ModeA/<세션>/<trial>.png
      + 세션별 _summary.png (채널 RMSE 막대) + _compare/README.md (색인)
CLI: python fs_compare_plot.py [CL|MA]   (인자 없으면 둘 다)
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.002"),
             ("FS_KNEE_REL", "0.1"), ("FS_KNEE_LOAD", "1"), ("FS_TAULIM", "20.5")):
    os.environ.setdefault(k, v)
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import fs_data as FD
import fs_metric as FMET
import fs_runner as FR
import p25_a_twin as TW

OUT = HERE / "_compare"
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
TH = {60: 0.70, 120: 0.50, 150: 0.40}
QS = 2                      # qd 스큐 보정 [샘플] (4ms@500Hz)
CH = [("q1", "q1 [°]"), ("q2", "q2 [°]"), ("dq1", "dq1 [rad/s]"),
      ("dq2", "dq2 [rad/s]"), ("a1", "τ1 [Nm]"), ("a2", "τ2 [Nm]")]


def sh(x, n=QS):
    y = np.empty_like(x); y[n:] = x[:-n]; y[:n] = x[0]
    return y


def panels(title, subtitle=""):
    fig, ax = plt.subplots(2, 3, figsize=(15.5, 7.2), sharex=True)
    fig.suptitle(title + (f"\n{subtitle}" if subtitle else ""), fontsize=11)
    for a, (_, lab) in zip(ax.T.flat, CH):
        a.set_ylabel(lab)
        a.grid(alpha=0.3)
    for a in ax[1]:
        a.set_xlabel("t [s]")
    return fig, ax.T.flat        # 열 우선: (q1,q2),(dq1,dq2),(τ1,τ2)


def rmse_line(d, m, sims):
    """범례용 RMSE 문자열 (6채널)."""
    out = []
    for (k, _), s in zip(CH, sims):
        v = d[k][m] - s[m]
        r = np.degrees(np.sqrt(np.mean(v ** 2))) if k in ("q1", "q2") else np.sqrt(np.mean(v ** 2))
        out.append(f"{r:.2f}")
    return " / ".join(out)


def cl_pair(d, seg, g, sess):
    """(t, 실측dict, OLD 6채널, fs15 6채널, push마스크) — 실패 시 None."""
    i0 = max(0, seg["i_desc"] - 5)
    sl = slice(i0, None)
    t = d["t"][sl] - d["t"][i0]
    t_end = seg["t_lo"] - d["t"][i0]
    # --- OLD (배포 모델) ---
    sess_al = FMET.ALPH_SESS.get(sess)
    alphas = tuple(sess_al) if sess_al else (TH.get(g[0], 0.40), 0.20, TK.get(g[2], 0.656), 0.20)
    Lo = TW.rollout_cl(FMET.tw0, t, d["qd1"][sl], d["qd2"][sl], d["dqd1"][sl], d["dqd2"][sl],
                       tuple(g), alphas=alphas, t_end=t_end, t_after=0.05)
    # --- fs15 ---
    ft = FR.fs_twin()
    SP = FR._sess_params()
    sp = SP.get(sess, dict(bias1=0.0, knee_deep=None))
    Lf = FR.rollout_cl_fs(ft, t, sh(d["qd1"][sl]), sh(d["qd2"][sl]), sh(d["dqd1"][sl]), sh(d["dqd2"][sl]),
                          tuple(g), t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                          fade=True, taulim=None, vdes_ff=(sess != "26.04.21"))
    if Lo is None or Lf is None:
        return None
    gi = lambda L, k: np.interp(t, L["t"], L[k])
    old = [gi(Lo, "q1"), gi(Lo, "q2"), gi(Lo, "dq1"), gi(Lo, "dq2"), gi(Lo, "sh1"), gi(Lo, "sh2")]
    t1f = np.clip(gi(Lf, "s1f"), -20.5, 20.5)
    fs = [gi(Lf, "thm1"), gi(Lf, "q2"), gi(Lf, "dq1"), gi(Lf, "dq2"), t1f, gi(Lf, "s2")]
    meas = {k: d[k][sl][: len(t)] for k, _ in CH}
    m = seg["push"][sl][: len(t)]
    return t, meas, old, fs, m, t_end


def plot_cl(sess, name, d, seg, g):
    r = cl_pair(d, seg, g, sess)
    if r is None:
        print(f"  CL {sess}/{name}: 롤아웃 실패", flush=True)
        return
    t, meas, old, fs, m, t_end = r
    t_p0 = float(t[m][0]) if m.sum() else max(t_end - 0.3, 0.0)
    w = (t >= t_p0 - 0.05) & (t <= t_end)
    fig, ax = panels(f"{sess} / {name} — CL 점프(push) 구간 · 실측 vs 배포모델(OLD) vs 현행(fs15)",
                     f"push RMSE (q1/q2/dq1/dq2/τ1/τ2)  OLD: {rmse_line(meas, m, old)}   fs15: {rmse_line(meas, m, fs)}")
    for j, (a, (k, _)) in enumerate(zip(ax, CH)):
        y = meas[k][w]
        yo, yf = old[j][w], fs[j][w]
        if k in ("q1", "q2"):
            y, yo, yf = np.degrees(y), np.degrees(yo), np.degrees(yf)
        a.plot(t[w], y, lw=1.2, label="실측")
        a.plot(t[w], yo, "--", lw=1.0, label="배포모델 (OLD)")
        a.plot(t[w], yf, ":", lw=1.5, label="현행 (fs15)")
        a.axvline(t_p0, lw=0.6, alpha=0.4)
    ax[0].legend(fontsize=8, loc="best")
    fig.tight_layout()
    fp = OUT / "CL" / sess
    fp.mkdir(parents=True, exist_ok=True)
    fig.savefig(fp / f"{name}.png", dpi=105)
    plt.close(fig)
    return [np.sqrt(np.mean((meas[k][m] - s[m]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
            for (k, _), s in zip(CH, old)], \
           [np.sqrt(np.mean((meas[k][m] - s[m]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
            for (k, _), s in zip(CH, fs)]


def plot_ma(sess, name, d, seg):
    """ModeA mshoot: 창별 조각 오버레이 (측정 raw 주입)."""
    ft = FR.fs_twin()
    SP = FR._sess_params()
    sp = SP.get(sess, dict(bias1=0.0, knee_deep=None))
    t = d["t"]
    t0, t1 = seg["t_desc"], seg["t_lo"]
    segs_o, segs_f = [], []
    err_o, err_f = [], []
    w0 = t0
    while w0 + 0.05 < t1:
        wl = min(FMET.MSHOOT_W, t1 - w0)
        m = (t >= w0) & (t <= w0 + wl)
        if m.sum() < 20:
            w0 += FMET.MSHOOT_S
            continue
        i0 = int(np.argmax(m))
        tg = t[m] - w0
        st = FMET.st_from_meas(FMET.tw0, float(d["q1"][i0]), float(d["q2"][i0]),
                               float(d["dq1"][i0]), float(d["dq2"][i0]),
                               float(d["raw1"][i0]), float(d["raw2"][i0]))
        Lo = TW.rollout_ol(FMET.tw0, tg, d["raw1"][m], d["raw2"][m], st,
                           t_end=float(tg[-1] - 0.004), t_after=0.004)
        Lf = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=sp["bias1"],
                                knee_deep=sp["knee_deep"], fade=True)
        if Lo is not None:
            gi = lambda k: np.interp(tg, Lo["t"], Lo[k])
            v = [gi(k) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2")]
            segs_o.append((t[m], v))
            mm = tg >= 0.02
            err_o.append([np.sqrt(np.mean((d[k][m][mm] - s[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
                          for (k, _), s in zip(CH, v)])
        if Lf is not None:
            gi = lambda k: np.interp(tg, Lf["t"], Lf[k])
            v = [gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2")]
            segs_f.append((t[m], v))
            mm = tg >= 0.02
            err_f.append([np.sqrt(np.mean((d[k][m][mm] - s[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
                          for (k, _), s in zip(CH, v)])
        w0 += FMET.MSHOOT_S
    if not segs_o and not segs_f:
        print(f"  MA {sess}/{name}: 창 없음", flush=True)
        return
    eo = np.mean(err_o, axis=0) if err_o else np.full(6, np.nan)
    ef = np.mean(err_f, axis=0) if err_f else np.full(6, np.nan)
    fig, ax = panels(f"{sess} / {name} — ModeA (측정 토크 주입, 0.4s 창 재생) · 실측 vs 배포모델 vs 현행",
                     f"창평균 RMSE  OLD: {' / '.join('%.2f' % x for x in eo)}   fs: {' / '.join('%.2f' % x for x in ef)}")
    mall = (t >= t0) & (t <= t1)
    for j, (a, (k, _)) in enumerate(zip(ax, CH)):
        y = d[k][mall]
        a.plot(t[mall], np.degrees(y) if k in ("q1", "q2") else y, lw=1.2, label="실측", color="C0")
        for i, (tt, v) in enumerate(segs_o):
            yy = np.degrees(v[j]) if k in ("q1", "q2") else v[j]
            a.plot(tt, yy, "--", lw=0.9, color="C1", alpha=0.85, label="배포모델 (OLD)" if i == 0 else None)
        for i, (tt, v) in enumerate(segs_f):
            yy = np.degrees(v[j]) if k in ("q1", "q2") else v[j]
            a.plot(tt, yy, ":", lw=1.3, color="C2", alpha=0.9, label="현행 (fs)" if i == 0 else None)
    ax[0].legend(fontsize=8, loc="best")
    fig.tight_layout()
    fp = OUT / "ModeA" / sess
    fp.mkdir(parents=True, exist_ok=True)
    fig.savefig(fp / f"{name}.png", dpi=105)
    plt.close(fig)
    return list(eo), list(ef)


def summary_fig(folder, sess, rows, mode):
    """세션 요약: 채널별 OLD vs 현행 평균 RMSE 막대."""
    if not rows:
        return
    O = np.nanmean([r[0] for r in rows], axis=0)
    F = np.nanmean([r[1] for r in rows], axis=0)
    fig, a = plt.subplots(figsize=(7.5, 4))
    x = np.arange(6)
    a.bar(x - 0.19, O, 0.38, label="배포모델 (OLD)")
    a.bar(x + 0.19, F, 0.38, label="현행 (fs)")
    a.set_xticks(x); a.set_xticklabels([c[1].split(" ")[0] for c in CH])
    a.set_ylabel("RMSE (창 평균)")
    a.set_title(f"{sess} — {mode} 채널별 (trial {len(rows)}개 평균)")
    a.legend(); a.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(folder / "_summary.png", dpi=105)
    plt.close(fig)
    return O, F


def main():
    want = sys.argv[1].upper() if len(sys.argv) > 1 else "BOTH"
    OUT.mkdir(exist_ok=True)
    agg = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue                       # CVT는 fs_cvt_plot (모델 경로 상이)
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s
        except Exception as ex:
            print(f"{s}/{p.name}: LOAD {type(ex).__name__}", flush=True)
            continue
        if want in ("BOTH", "CL") and not ho and g:
            r = plot_cl(s, p.name, d, seg, g)
            if r:
                agg.setdefault(("CL", s), []).append(r)
        if want in ("BOTH", "MA"):
            r = plot_ma(s, p.name, d, seg)
            if r:
                agg.setdefault(("ModeA", s), []).append(r)
        print(f"{s}/{p.name}: OK", flush=True)
    lines = ["# 3자 비교 그래프 색인 (실측 / 배포모델 OLD / 현행 fs15)", "",
             "- `CL/<세션>/<trial>.png` — 폐루프, 점프(push) 구간",
             "- `ModeA/<세션>/<trial>.png` — 측정 토크 주입 재생 (0.4s 창)",
             "- 각 세션 폴더의 `_summary.png` = 채널별 평균 RMSE 막대", "",
             "| 모드 | 세션 | trial | q1 | q2 | dq1 | dq2 | τ1 | τ2 |", "|---|---|---|---|---|---|---|---|---|"]
    for (mode, s), rows in sorted(agg.items()):
        folder = OUT / mode / s
        res = summary_fig(folder, s, rows, mode)
        if res is None:
            continue
        O, F = res
        lines.append(f"| {mode} | {s} | {len(rows)} | " +
                     " | ".join(f"{O[i]:.2f}→{F[i]:.2f}" for i in range(6)) + " |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\ndone → {OUT} ({len(agg)} 세션·모드 조합)", flush=True)


if __name__ == "__main__":
    main()
