# -*- coding: utf-8 -*-
"""promo_all_trials — 전 trial CL/Mode A 비교 그래프 배치 (실측 vs OLD α vs 변형 C).

출력: promo_all_trials/<세션>/<trial>/{CL.png, ModeA.png} + INDEX.md
그림: 행 q/dq/τ × 열 hip/knee. 제목에 점프 높이 (실측 = Real Data.txt, sim = max(bz)-bz0).
스코프: 배포 5일 + 0424 + 0602(position) = CL+ModeA · 0324 = ModeA만 (FF 토크 세션 — 순수 PD 재현 불성립)
      · 0429 CVT = 제외 (러너 규약 별도 — INDEX 명기).
규약: 정렬무결 (실기 로그 qd 미끼) · 단위 자동 (구세션 각도 deg→rad, 속도는 전 세션 rad/s)
     · OLD α = fit 세션은 R19.ALPH(정본), 배포는 TH/TK 테이블 · 변형 C = hip SEA 96/323@9 + knee TK α.
"""
import os, sys, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p25_task0")); sys.path.insert(0, str(HERE.parent / "p25_deploy"))
import p25_a_twin as TW          # noqa: E402
from sea_twin2 import rollout_cl_sea2, ahat_np   # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
OUT = HERE / "promo_all_trials"
OUT.mkdir(exist_ok=True)
TH = {60: 0.70, 120: 0.50, 150: 0.40}
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
SESS = [
    ("26.07.22", ROOT/"26_07_22", True),
    ("26.07.23", ROOT/"26_07_23", True),
    ("26.07.24", ROOT/"26_07_24", True),
    ("26.07.25", ROOT/"26_07_25", True),
    ("26.07.27", ROOT/"26_07_27", True),
    ("26.04.24", ROOT/"26_04_24", True),
    ("26.06.02_position", ROOT/"26_06_02"/"position", True),
    ("26.03.24_Jump_No_Tr", ROOT/"26_03_24"/"Jump"/"Jump_No_Tr", False),  # ModeA만
]
R19A = getattr(TW.R19, "ALPH", {})
ALPH_FIT = {"26.04.24": R19A.get("jump_0424"), "26.06.02_position": R19A.get("jump_0602")}

def defl_2s(tau):
    a = np.abs(tau)
    d = np.where(a <= 9.0, a/96.0, 9.0/96.0 + (a-9.0)/323.0)
    return np.sign(tau)*d
def smooth(x, w=5): return np.convolve(x, np.ones(w)/w, mode="same")

def real_height(fold):
    f = fold/"Real Data.txt"
    if not f.exists(): return None
    try:
        line = f.open(encoding="utf-8", errors="ignore").readline()
    except Exception:
        return None
    mm = re.search(r"([\d.]+)\s*m", line)
    if not mm: return None
    v = float(mm.group(1))
    if v > 3: v /= 100.0   # '074m' 같은 표기 방어
    return v

tw0 = TW.twin()

def load_trial(fold):
    hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx")
    n = min(len(hip), len(knee)); hip, knee = hip.iloc[:n], knee.iloc[:n]
    t = hip["Time"].to_numpy(float) - hip["Time"].iloc[0]
    q1m = hip["currentAngle"].to_numpy(float); q2m = knee["currentAngle"].to_numpy(float)
    qd1 = hip["desiredAngle"].to_numpy(float); qd2 = knee["desiredAngle"].to_numpy(float)
    deg = np.nanmax(np.abs(q2m)) > 7
    if deg:
        q1m, q2m, qd1, qd2 = map(np.radians, (q1m, q2m, qd1, qd2))
    v1 = hip["currentAngleVelocity"].to_numpy(float); v2 = knee["currentAngleVelocity"].to_numpy(float)
    dqd1 = hip["desiredAngleVelocity"].to_numpy(float); dqd2 = knee["desiredAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float); raw2 = knee["currentTorque"].to_numpy(float)
    a1 = ahat_np(raw1, v1); a2 = ahat_np(raw2, v2)
    on = np.where(np.abs(qd2-qd2[0]) > np.radians(0.5))[0] if np.nanstd(qd2) > 1e-6 else []
    if len(on): i0 = int(on[0])
    else:
        mv = np.where(np.abs(q2m-q2m[0]) > np.radians(1.0))[0]
        i0 = max(0, int(mv[0])-5) if len(mv) else 0
    gf = fold/"GRF.xlsx"
    t_lo = None
    if gf.exists():
        g = pd.read_excel(gf)["Current_GRF"].to_numpy(float)[:n]
        g0 = np.median(g[-5:]); thr = g0 + 0.06*(np.nanmax(g)-g0)
        ab = np.where(g >= thr)[0]
        if len(ab): t_lo = float(t[min(int(ab[-1])+1, n-1)] - t[i0])
    if t_lo is None:
        t_lo = float(t[int(np.argmax(smooth(np.abs(v2), 5)))] - t[i0] + 0.02)
    t_lo = float(min(t_lo, t[-1]-t[i0]-0.004))
    s = slice(i0, None)
    return dict(t=t[s]-t[i0], q1=q1m[s], q2=q2m[s], qd1=qd1[s], qd2=qd2[s],
                dqd1=dqd1[s], dqd2=dqd2[s], dq1=v1[s], dq2=v2[s],
                raw1=raw1[s], raw2=raw2[s], a1=a1[s], a2=a2[s], t_lo=t_lo)

def gains_of(name):
    try:
        g = [float(x) for x in name.split("_")]
        return g if len(g) == 4 else None
    except ValueError:
        return None

def h_of(Lg, t_lo):
    """정본 규약 (p25 apex_of / a_full23 h_sim): t>0 최대 절대 base-z [m]."""
    bz = np.asarray(Lg["bz"]); tt = np.asarray(Lg["t"])
    return float(bz[tt > 0].max())

def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))

def panel(ax, tms, series, ylab, title):
    for lab, y, kw in series:
        ax.plot(tms, y, label=lab, **kw)
    ax.set_ylabel(ylab); ax.set_title(title, fontsize=9); ax.grid(alpha=.3)

INDEX = ["# promo_all_trials — 전 trial CL/ModeA 비교 (실측 vs OLD α vs 변형 C)",
         "", "정렬무결 규약. 0429 CVT 제외 (러너 규약 별도). 0324 = ModeA만 (FF 토크 세션).",
         "", "| 세션 | trial | h실측[m] | CL q1 O→C | CL dq1 O→C | CL τ1 O→C | MA q1 O→C |", "|---|---|---|---|---|---|---|"]

for sess, base, do_cl in SESS:
    if not base.is_dir(): continue
    for fold in sorted([p for p in base.iterdir() if p.is_dir() and (p/"hip.xlsx").exists() and (p/"knee.xlsx").exists()]):
        try:
            d = load_trial(fold)
        except Exception as ex:
            print(f"{sess}/{fold.name}: 로드 실패 {type(ex).__name__}", flush=True); continue
        if d["t_lo"] < 0.06: continue
        hreal = real_height(fold)
        odir = OUT/sess/fold.name; odir.mkdir(parents=True, exist_ok=True)
        m = (d["t"] >= 0) & (d["t"] <= d["t_lo"]+0.02)
        msk = (d["t"] >= 0.005) & (d["t"] <= d["t_lo"]-0.005)
        tms = d["t"][m]*1000
        hs = f"{hreal:.2f}m" if hreal else "?"
        row_cl = ["—", "—", "—"]

        # ══ Mode A (플랜트 공통 + hip 관측층 차이) ══
        try:
            st = TW.settle_state(tw0, float(d["q1"][0]), float(d["q2"][0]))
            La = TW.rollout_ol(tw0, d["t"], d["raw1"], d["raw2"], st, t_end=d["t_lo"], t_after=0.6)
        except Exception:
            La = None
        if La is not None:
            q1s = np.interp(d["t"], La["t"], La["q1"]); q1c = q1s + defl_2s(d["a1"])
            dq1s = np.interp(d["t"], La["t"], La["dq1"])
            dq1c = dq1s + np.gradient(defl_2s(smooth(d["a1"], 5)), d["t"])
            q2s = np.interp(d["t"], La["t"], La["q2"]); dq2s = np.interp(d["t"], La["t"], La["dq2"])
            sh1 = np.interp(d["t"], La["t"], La["sh1"]); sh2 = np.interp(d["t"], La["t"], La["sh2"])
            hA = h_of(La, d["t_lo"])
            rq_o, rq_c = np.degrees(rmse(d["q1"][msk], q1s[msk])), np.degrees(rmse(d["q1"][msk], q1c[msk]))
            fig, axes = plt.subplots(3, 2, figsize=(13, 10), sharex=True)
            R = lambda x: np.degrees(x)
            panel(axes[0][0], tms, [("실측", R(d["q1"][m]), dict(lw=2.0)),
                                    ("OLD(무보정)", R(q1s[m]), dict(lw=1.2, ls="--")),
                                    ("변형C(2단보정)", R(q1c[m]), dict(lw=1.4))],
                  "q1 [°]", f"hip 각도 | RMSE {rq_o:.2f}→{rq_c:.2f}°")
            panel(axes[0][1], tms, [("실측", R(d["q2"][m]), dict(lw=2.0)),
                                    ("트윈(공통)", R(q2s[m]), dict(lw=1.4))],
                  "q2 [°]", f"knee 각도 | RMSE {np.degrees(rmse(d['q2'][msk], q2s[msk])):.2f}°")
            panel(axes[1][0], tms, [("실측", d["dq1"][m], dict(lw=1.8)),
                                    ("OLD", dq1s[m], dict(lw=1.2, ls="--")),
                                    ("변형C", dq1c[m], dict(lw=1.3))],
                  "dq1 [rad/s]", f"hip 속도 | RMSE {rmse(d['dq1'][msk], dq1s[msk]):.2f}→{rmse(d['dq1'][msk], dq1c[msk]):.2f}")
            panel(axes[1][1], tms, [("실측", d["dq2"][m], dict(lw=1.8)),
                                    ("트윈(공통)", dq2s[m], dict(lw=1.4))],
                  "dq2 [rad/s]", f"knee 속도 | RMSE {rmse(d['dq2'][msk], dq2s[msk]):.2f}")
            panel(axes[2][0], tms, [("실측 â1", d["a1"][m], dict(lw=1.8)),
                                    ("sim 적용(주입+법칙층)", sh1[m], dict(lw=1.3))],
                  "τ1 [Nm]", "hip 토크 (Mode A는 τ 주입 — 검증용 대조)")
            panel(axes[2][1], tms, [("실측 â2", d["a2"][m], dict(lw=1.8)),
                                    ("sim 적용", sh2[m], dict(lw=1.3))],
                  "τ2 [Nm]", "knee 토크")
            for ax in axes[2]: ax.set_xlabel("t [ms]")
            for ax in axes.flat: ax.axvline(d["t_lo"]*1000, ls=":", lw=0.8)
            axes[0][0].legend(fontsize=8); axes[0][1].legend(fontsize=8)
            fig.suptitle(f"Mode A — {sess} / {fold.name} | 점프높이: 실측 {hs} · sim {hA:.2f}m (플랜트 공통)", fontsize=13)
            fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(odir/"ModeA.png", dpi=100); plt.close(fig)
            ma_str = f"{rq_o:.1f}→{rq_c:.1f}"
        else:
            ma_str = "발산"

        # ══ CL ══
        if do_cl and (g := gains_of(fold.name)):
            al_fit = ALPH_FIT.get(sess)
            alphas = tuple(al_fit) if al_fit else (TH.get(g[0], 0.40), 0.20, TK.get(g[2], 0.656), 0.20)
            try:
                Lo = TW.rollout_cl(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"],
                                   tuple(g), alphas=alphas, t_end=d["t_lo"], t_after=0.6)
            except Exception:
                Lo = None
            gm = (g[0], g[1], g[2]*TK.get(g[2], 0.656), g[3]*0.20)
            try:
                Lc = rollout_cl_sea2(tw0, d["t"], d["qd1"], d["qd2"], d["dqd1"], d["dqd2"], gm,
                                     t_end=d["t_lo"], t_after=0.6,
                                     ks1=96.0, ks1_hi=323.0, tau0_1=9.0, bs1=1.5, jm1=0.01, ks2=None)
            except Exception:
                Lc = None
            if Lo is not None and Lc is not None:
                def gi(L, k): return np.interp(d["t"], L["t"], L[k])
                q1o, q2o, dq1o, dq2o, t1o, t2o = (gi(Lo, k) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2"))
                q1c_, q2c_ = gi(Lc, "thm1"), gi(Lc, "q2")
                dq1c_ = np.interp(d["t"], Lc["t"], np.gradient(Lc["thm1"], Lc["t"]))
                dq2c_ = np.interp(d["t"], Lc["t"], np.gradient(Lc["q2"], Lc["t"]))
                t1c, t2c = gi(Lc, "tsp1"), gi(Lc, "tsp2")
                ho, hc = h_of(Lo, d["t_lo"]), h_of(Lc, d["t_lo"])
                fig, axes = plt.subplots(3, 2, figsize=(13, 10), sharex=True)
                R = lambda x: np.degrees(x)
                trip = lambda re_, o_, c_: [("실측", re_, dict(lw=2.0)), ("OLD α", o_, dict(lw=1.2, ls="--")), ("변형 C", c_, dict(lw=1.4))]
                rr = lambda re_, o_, c_: (rmse(re_[msk], o_[msk]), rmse(re_[msk], c_[msk]))
                a_, b_ = rr(d["q1"], q1o, q1c_)
                panel(axes[0][0], tms, trip(R(d["q1"][m]), R(q1o[m]), R(q1c_[m])), "q1 [°]",
                      f"hip 각도 | RMSE {np.degrees(a_):.2f}→{np.degrees(b_):.2f}°")
                row_q1 = f"{np.degrees(a_):.1f}→{np.degrees(b_):.1f}"
                a_, b_ = rr(d["q2"], q2o, q2c_)
                panel(axes[0][1], tms, trip(R(d["q2"][m]), R(q2o[m]), R(q2c_[m])), "q2 [°]",
                      f"knee 각도 | RMSE {np.degrees(a_):.2f}→{np.degrees(b_):.2f}°")
                a_, b_ = rr(d["dq1"], dq1o, dq1c_)
                panel(axes[1][0], tms, trip(d["dq1"][m], dq1o[m], dq1c_[m]), "dq1 [rad/s]",
                      f"hip 속도 | RMSE {a_:.2f}→{b_:.2f}")
                row_dq1 = f"{a_:.1f}→{b_:.1f}"
                a_, b_ = rr(d["dq2"], dq2o, dq2c_)
                panel(axes[1][1], tms, trip(d["dq2"][m], dq2o[m], dq2c_[m]), "dq2 [rad/s]",
                      f"knee 속도 | RMSE {a_:.2f}→{b_:.2f}")
                a_, b_ = rr(d["a1"], t1o, t1c)
                panel(axes[2][0], tms, trip(d["a1"][m], t1o[m], t1c[m]), "τ1 [Nm]",
                      f"hip 토크 | RMSE {a_:.2f}→{b_:.2f}")
                row_t1 = f"{a_:.1f}→{b_:.1f}"
                a_, b_ = rr(d["a2"], t2o, t2c)
                panel(axes[2][1], tms, trip(d["a2"][m], t2o[m], t2c[m]), "τ2 [Nm]",
                      f"knee 토크 | RMSE {a_:.2f}→{b_:.2f}")
                for ax in axes[2]: ax.set_xlabel("t [ms]")
                for ax in axes.flat: ax.axvline(d["t_lo"]*1000, ls=":", lw=0.8)
                axes[0][0].legend(fontsize=8)
                fig.suptitle(f"CL — {sess} / {fold.name} | 점프높이: 실측 {hs} · OLD {ho:.2f}m · 변형C {hc:.2f}m", fontsize=13)
                fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(odir/"CL.png", dpi=100); plt.close(fig)
                row_cl = [row_q1, row_dq1, row_t1]
        INDEX.append(f"| {sess} | {fold.name} | {hs} | {row_cl[0]} | {row_cl[1]} | {row_cl[2]} | {ma_str} |")
        print(f"{sess}/{fold.name}: 완료 (h {hs})", flush=True)

(OUT/"INDEX.md").write_text("\n".join(INDEX), encoding="utf-8")
print(f"\ndone → {OUT}", flush=True)
