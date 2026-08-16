"""GOAL22 P1 — dq 계측 필터 규명.

가설: 로그 dq는 펌웨어(또는 호스트) 필터를 거친 값, sim dq는 raw.
방법: 실측 q의 수치미분(central diff) vs 로그 dq를
  (a) FRF (Welch cross-spectrum, coherence 가중) → 1차 LPF (fc, delay) 적합
  (b) 이동평균 창 N (= (q[i]-q[i-N])/(N dt) 백워드차분) 시간영역 스캔
  (c) 고주파(30-100Hz) 파워비 (smoothing ratio)
  (d) 양자화 스텝 (CAN 12bit dq=±45rad/s → 0.02198, 16bit q=±12.5rad → 3.815e-4)
로 대조. central-diff 자체의 sinc 감쇠는 보정.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
from scipy.signal import welch, csd, coherence, lfilter

REPO = Path(__file__).resolve().parents[2]
for p in ["code/goal19/phase11", "code/goal19/templates", "code/goal19/data_loaders",
          "code/goal19/phase1", "code/goal19/phase2", "code/goal19/phase3", "code/goal19/phase4"]:
    sys.path.insert(0, str(REPO / p))
import mshoot as MS
from load_31exp import list_experiments

OUT = Path(__file__).parent / "p1_out"
OUT.mkdir(exist_ok=True)


def frf(x, y, fs, nseg):
    f, Pxx = welch(x, fs, nperseg=nseg)
    _, Pxy = csd(x, y, fs, nperseg=nseg)
    _, Cxy = coherence(x, y, fs, nperseg=nseg)
    H = Pxy / np.maximum(Pxx, 1e-14)
    return f, H, Cxy


def fit_lpf(f, H, C, dt):
    """coherence-가중 복소 적합: H = sinc보정 * e^{-j2πf d}/(1+jf/fc). 반환 (fc, d_ms, err)."""
    m = (f >= 2.0) & (f <= 120.0) & (C > 0.5)
    if m.sum() < 5:
        return np.nan, np.nan, np.nan
    fm, Hm, Cm = f[m], H[m], C[m]
    # central diff (np.gradient) vs true derivative: gain sin(2π f dt)/(2π f dt)
    w = 2 * np.pi * fm * dt
    g_cd = np.where(w > 1e-9, np.sin(w) / w, 1.0)
    H_fw = Hm / g_cd          # 펌웨어 필터 성분만
    best = (np.nan, np.nan, np.inf)
    for fc in np.geomspace(3, 250, 120):
        Hlp = 1.0 / (1 + 1j * fm / fc)
        # delay: 잔여 위상 기울기로 해석적 추정 대신 그리드
        for d in np.arange(0, 0.0121, 0.0005):
            Hmod = Hlp * np.exp(-1j * 2 * np.pi * fm * d)
            err = float(np.sum(Cm * np.abs(H_fw - Hmod) ** 2) / np.sum(Cm))
            if err < best[2]:
                best = (float(fc), float(d * 1e3), err)
    return best


def fit_ma(t, q, dq_log, dt, n_max=12):
    """dq_log ≈ (q[i]-q[i-N])/(N dt) 시간영역 스캔 → (N_best, rmse_best, rmse_cd)."""
    act = np.abs(dq_log) > 0.5
    if act.sum() < 50:
        act = np.ones(len(dq_log), bool)
    dq_cd = np.gradient(q, t)
    rmse_cd = float(np.sqrt(np.mean((dq_cd[act] - dq_log[act]) ** 2)))
    best = (0, rmse_cd)
    for N in range(1, n_max + 1):
        bd = np.empty_like(q)
        bd[N:] = (q[N:] - q[:-N]) / (N * dt)
        bd[:N] = bd[N]
        # 백워드차분 중심은 N/2 샘플 과거 → 로그가 지연 없이 정렬돼 있으면 시프트 보정도 스캔
        for s in range(0, N + 1):
            bs = np.roll(bd, -s)
            r = float(np.sqrt(np.mean((bs[act] - dq_log[act]) ** 2)))
            if r < best[1]:
                best = (N, r)
    return best[0], best[1], rmse_cd


def hf_ratio(x, y, fs, nseg):
    f, Px = welch(x, fs, nperseg=nseg)
    _, Py = welch(y, fs, nperseg=nseg)
    m = (f >= 30) & (f <= 100)
    return float(np.sum(Py[m]) / max(np.sum(Px[m]), 1e-14))


def qstep(v):
    u = np.unique(np.round(v, 8))
    if len(u) < 3:
        return np.nan
    d = np.diff(u)
    d = d[d > 1e-7]
    return float(np.min(d)) if len(d) else np.nan


groups = []
for ds in MS.LOADERS:
    subs = [sub for d2, sub, isj in list_experiments() if d2 == ds]
    groups.append((ds, subs, MS.LOADERS[ds]))
for ds, tdir, subs in MS.MARCH:
    groups.append((ds, subs, lambda s, _t=tdir: MS.load_march(_t, s)))

rows = []
figdone = set()
for ds, subs, loader in groups:
    for sub in subs:
        td = loader(sub)
        t = np.asarray(td["t"], float)
        dt = float(np.median(np.diff(t)))
        fs = 1.0 / dt
        nseg = min(256, 2 ** int(np.log2(len(t) // 4 + 1)))
        for j, (qk, dk) in enumerate([("q1", "dq1"), ("q2", "dq2")], 1):
            q = np.asarray(td[qk], float)
            dq = np.asarray(td[dk], float)
            dq_cd = np.gradient(q, t)
            f, H, C = frf(dq_cd, dq, fs, nseg)
            fc, dms, err = fit_lpf(f, H, C, dt)
            Nma, r_ma, r_cd = fit_ma(t, q, dq, dt)
            rows.append(dict(ds=ds, sub=str(sub), joint=j, fs=fs,
                             fc=fc, delay_ms=dms, fit_err=err,
                             N_ma=Nma, rmse_ma=r_ma, rmse_cd=r_cd,
                             hf=hf_ratio(dq_cd, dq, fs, nseg),
                             qz_q=qstep(q), qz_dq=qstep(dq)))
        if ds not in figdone:   # 대표 trial 1개 진단 그림
            figdone.add(ds)
            fig, ax = plt.subplots(2, 3, figsize=(15, 7))
            for j, (qk, dk) in enumerate([("q1", "dq1"), ("q2", "dq2")]):
                q = np.asarray(td[qk], float); dq = np.asarray(td[dk], float)
                dq_cd = np.gradient(q, t)
                i0 = int(np.argmax(np.abs(dq)))
                s0, s1 = max(0, i0 - 100), min(len(t), i0 + 100)
                ax[j, 0].plot(t[s0:s1], dq_cd[s0:s1], lw=0.9, label="d/dt(q_log) central")
                ax[j, 0].plot(t[s0:s1], dq[s0:s1], lw=1.2, label="dq_log")
                ax[j, 0].set_title(f"joint{j+1} 시간영역 (피크 부근)"); ax[j, 0].legend(fontsize=8)
                f, H, C = frf(dq_cd, dq, fs, nseg)
                w = 2 * np.pi * f * dt
                g_cd = np.where(w > 1e-9, np.sin(w) / w, 1.0)
                ax[j, 1].semilogx(f[1:], np.abs(H[1:] / g_cd[1:]), lw=1.2, label="|H| (sinc보정)")
                r = [x for x in rows if x["ds"] == ds and x["sub"] == str(sub) and x["joint"] == j + 1][0]
                if np.isfinite(r["fc"]):
                    Hm = np.abs(1 / (1 + 1j * f / r["fc"]))
                    ax[j, 1].semilogx(f[1:], Hm[1:], ls="--", lw=1.0,
                                      label=f"1차 LPF fc={r['fc']:.0f}Hz d={r['delay_ms']:.1f}ms")
                ax[j, 1].axhline(1, ls=":", lw=0.7); ax[j, 1].set_ylim(0, 1.4)
                ax[j, 1].set_title(f"joint{j+1} FRF 크기"); ax[j, 1].legend(fontsize=8)
                ax[j, 2].semilogx(f[1:], C[1:], lw=1.0)
                ax[j, 2].set_ylim(0, 1.05); ax[j, 2].set_title(f"joint{j+1} coherence")
            for a in ax.flat:
                a.grid(alpha=0.3)
            fig.suptitle(f"P1 dq 필터 진단 — {ds}/{sub} (fs={fs:.0f}Hz)")
            fig.tight_layout()
            fig.savefig(OUT / f"diag_{ds}.png", dpi=110)
            plt.close(fig)
        print("done", ds, sub, flush=True)

json.dump(rows, open(OUT / "p1_rows.json", "w"), indent=1)

# ── 요약 ──────────────────────────────────────────────────────────────────────
print("\n=== P1 요약 (dataset × joint 중앙값) ===")
print(f"{'dataset':22s} j  fc[Hz]  delay[ms]  N_ma  rmse_ma/cd  hf_ratio  qz_dq")
for ds in dict.fromkeys(r["ds"] for r in rows):
    for j in (1, 2):
        rs = [r for r in rows if r["ds"] == ds and r["joint"] == j]
        med = lambda k: float(np.nanmedian([r[k] for r in rs]))
        print(f"{ds:22s} {j}  {med('fc'):6.1f}  {med('delay_ms'):9.2f}  {med('N_ma'):4.0f}"
              f"  {med('rmse_ma'):5.3f}/{med('rmse_cd'):5.3f}  {med('hf'):8.3f}  {med('qz_dq'):7.5f}")
print("\nhf_ratio<1 = 로그 dq가 수치미분보다 평활(필터 존재 증거), ≈1 = 필터 없음")
print("qz_dq≈0.022 = CAN 12bit 양자화 확인")
