# -*- coding: utf-8 -*-
"""pre30 판별 프로브 — 창별 최적 무릎 보정토크 λ*(window) 프로파일 (2026-07-13).

배경: '클러치 프리로드' 기구 해석이 사용자 반론(볼스크류 내부 힘루프는 크랭크에
순토크 불가)으로 기각됨. 상수항 2.25Nm의 정체 재심문:
  H-const : λ*가 창/각도/단계 무관 평탄 → 진짜 상수 (원인 미규명, 벤치로)
  H-grav  : λ* ∝ 정강이 수평성분 u_x (중력 모양) → 중력 잔차 (m·d 크기 판정)
  H-stance: 이륙 후 창에서 λ*→0 → 접촉 기원
동일 프로토콜로 jump vs s2s 재측정 (2.2 vs 1.34가 실측인지 적합맥락 잡음인지).
0324(held-out)는 철칙 9(게이트 전용)로 제외. 스텝핑은 canonical P12.eval_windows.
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
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_adapter as AD

AD.ensure_init()
import p19_judge as P

CAND = AD.load_candidate(HERE / "fourbar_p19_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)
A = P.A_PAPER
P12 = P.J._P["P12"]
mj = P.J._P["mj"]
DST = Path((LEGACY_ROOT + "/g22_p19_all_results/pre30_probe"))
DST.mkdir(parents=True, exist_ok=True)
LGRID = np.arange(-2.0, 5.01, 0.5)


def shank_ux(model, data, bz, q1m, q2m):
    """정강이(calf) 링크축의 world 수평성분 — 단위 CoM 거리당 무릎 중력모멘트 인자."""
    data.qpos[:] = [bz, q1m, q2m, -q2m, q2m]
    data.qvel[:] = 0
    mj.mj_forward(model, data)
    bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "calf")
    xmat = data.xmat[bid].reshape(3, 3)
    return float(xmat[0, 2])


def lam_star(scores):
    """λ 그리드 점수 → 포물선 보간 최소점."""
    i = int(np.argmin(scores))
    if i in (0, len(LGRID) - 1):
        return float(LGRID[i]), float(scores[i])
    a, b, c = scores[i - 1], scores[i], scores[i + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return float(LGRID[i] + np.clip(off, -1, 1) * (LGRID[1] - LGRID[0])), float(b)


def main():
    model, _ = P.build_flip(X32, V[1], SP)
    data = mj.MjData(model)
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(X32)[:26]))
    from cvt_run2 import takeoff_time
    rows = []
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        if ds == "jump_0324":
            continue
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0
        o2 = dd[k2] if k2 else 0.0
        pp = tr["pp"]
        t = pp["t"]
        th_i = np.interp(t - P.SD, t, -P.J.ahat(A, tr["raw1"], tr["v1"]))
        tk_i = np.interp(t - P.SD, t, P.J.ahat(A, tr["raw2"], tr["v2"]))
        starts = [int(i) for i in pp["starts"]]
        if len(starts) > 12:
            starts = starts[::max(1, len(starts) // 12)]
        td = tr.get("td") or {}
        g = np.asarray(td.get("grf_z", []), dtype=float)
        toff = takeoff_time(t, g) if len(g) == len(t) else float("nan")
        if np.isfinite(toff):                      # 이륙 후 창 추가 (접촉 기원 검사)
            for dt_ in (0.02, 0.10):
                if toff + dt_ + 0.05 < t[-1]:
                    starts.append(int(np.searchsorted(t, toff + dt_)))
        # λ별 sv 적용 pp 준비 → 창별 점수
        svs = {}
        for lam in LGRID:
            ppv = dict(pp, tau_h=th_i, tau_k=-(tk_i + lam))
            svs[lam] = P12._G["sv"](ppv, o1, o2)
        for i0 in starts:
            scores = []
            for lam in LGRID:
                pw = dict(svs[lam], starts=[i0])
                scores.append(P12.eval_windows(model, pw, None))
            scores = np.array(scores)
            if scores.min() <= 0 or (scores.max() - scores.min()) / max(scores.min(), 1e-9) < 0.02:
                continue                     # λ 무감 창은 제외
            ls, sc = lam_star(scores)
            ppo = svs[0.0]
            ux = np.mean([shank_ux(model, data, ppo["bz"][j], ppo["q1m"][j], ppo["q2m"][j])
                          for j in (i0, min(i0 + 100, len(t) - 1))])
            phase = "flight" if (np.isfinite(toff) and t[i0] > toff) else "stance"
            wm = (t >= t[i0]) & (t <= t[i0] + pp["W"])
            tk_abs = float(np.mean(np.abs(tk_i[wm])))
            grf_m = float(np.mean(g[wm])) if len(g) == len(t) else float("nan")
            sens = float((scores.max() - scores.min()) / scores.min())
            rows.append(dict(ds=ds, sub=str(tr["sub"]), t0=float(t[i0]),
                             lam=ls, ux=ux, phase=phase, tk=tk_abs, grf=grf_m,
                             sens=sens, q2deg=float(np.degrees(-ppo["q2m"][i0]))))
        print(f"{ds}/{tr['sub']}: {len(starts)} windows, toff={toff}", flush=True)

    # ── 0429 전달비: 무릎측 상수의 크랭크 등가 ──
    from cvt_core import load_0429, closure
    d = load_0429("120_2_120_2")
    mjc = ((-d["q2"] + np.pi) % (2 * np.pi)) - np.pi
    qk_prev, qks = None, []
    for x in mjc:
        qk, _, _ = closure(float(x), d["l_i"], qk_prev)
        qk_prev = qk
        qks.append(qk)
    qks = np.array(qks)
    dm = np.gradient(mjc)
    r = np.where(np.abs(dm) > 1e-5, np.gradient(qks) / dm, np.nan)
    r_st = r[(d["t"] < 0.19) & np.isfinite(r)]

    # ── 집계/판정 ──
    out = {"rows": rows, "r0429": dict(mean=float(np.nanmean(r_st)),
                                       p10=float(np.nanpercentile(r_st, 10)),
                                       p90=float(np.nanpercentile(r_st, 90)))}
    R = rows
    for ds in sorted(set(r_["ds"] for r_ in R)):
        rs = [r_ for r_ in R if r_["ds"] == ds and r_["phase"] == "stance"]
        lam = np.array([r_["lam"] for r_ in rs])
        ux_ = np.array([r_["ux"] for r_ in rs])
        tk_ = np.array([r_["tk"] for r_ in rs])
        c_ux = np.corrcoef(lam, ux_)[0, 1] if len(rs) > 3 else float("nan")
        c_tk = np.corrcoef(lam, tk_)[0, 1] if len(rs) > 3 else float("nan")
        s_tk = float(np.sum(lam * tk_) / np.sum(tk_ ** 2)) if len(rs) > 3 else float("nan")
        print(f"{ds:22s} n={len(rs):3d}  λ* {lam.mean():+.2f} ± {lam.std():.2f}"
              f"  corr(ux) {c_ux:+.2f}  corr(|τk|) {c_tk:+.2f}"
              f"  스케일적합 λ*≈{100*s_tk:.1f}%·|τk|")
    lam = np.array([r_["lam"] for r_ in R])
    ux = np.array([r_["ux"] for r_ in R])
    tk = np.array([r_["tk"] for r_ in R])
    cc = np.corrcoef(lam, ux)[0, 1] if len(R) > 3 else float("nan")
    ct = np.corrcoef(lam, tk)[0, 1] if len(R) > 3 else float("nan")
    st = float(np.sum(lam * tk) / np.sum(tk ** 2))
    print(f"\n전체(pooled) λ* corr: u_x {cc:+.3f} · |τk| {ct:+.3f}"
          f" · 스케일적합 {100*st:.1f}%·|τk|")
    md = np.polyfit(ux, lam, 1) if len(R) > 3 else [np.nan, np.nan]
    print(f"u_x 기울기 = {md[0]:.2f} Nm → 중력 해석 시 m·d = {abs(md[0])/9.81:.3f} kg·m")
    for ph in ("stance", "flight"):
        rs = [r_["lam"] for r_ in R if r_["phase"] == ph]
        if rs:
            print(f"{ph}: n={len(rs)} λ* {np.mean(rs):+.2f} ± {np.std(rs):.2f}")
    print(f"\n0429 전달비 r: mean {out['r0429']['mean']:.3f} "
          f"[p10 {out['r0429']['p10']:.3f}, p90 {out['r0429']['p90']:.3f}]"
          f" → 무릎측 상수 2.25Nm의 크랭크 등가 ≈ {2.25*out['r0429']['mean']:.2f} Nm")
    json.dump(out, open(DST / "probe_rows.json", "w"), indent=1)

    # ── 그림 ──
    fig, ax = plt.subplots(1, 4, figsize=(19, 4.5))
    for ds in sorted(set(r_["ds"] for r_ in R)):
        rs = [r_ for r_ in R if r_["ds"] == ds]
        ax[0].scatter([r_["q2deg"] for r_ in rs], [r_["lam"] for r_ in rs],
                      s=18, label=ds, alpha=0.8)
        ax[1].scatter([r_["ux"] for r_ in rs], [r_["lam"] for r_ in rs],
                      s=18, label=ds, alpha=0.8)
        ax[2].scatter([r_["tk"] for r_ in rs], [r_["lam"] for r_ in rs],
                      s=18, label=ds, alpha=0.8)
    ax[0].set_xlabel("knee(crank) 각 [deg]"); ax[0].set_ylabel("창별 λ* [Nm]")
    ax[0].axhline(2.25, ls=":", lw=1); ax[0].set_title("λ* vs 무릎각 (평탄=상수)")
    ax[1].set_xlabel("정강이 수평성분 u_x"); ax[1].set_ylabel("λ* [Nm]")
    ax[1].set_title(f"λ* vs 중력인자 (r={cc:+.2f})")
    ax[2].set_xlabel("창 평균 |τ_knee| [Nm]"); ax[2].set_ylabel("λ* [Nm]")
    xg = np.linspace(0, max(tk), 20)
    ax[2].plot(xg, st * xg, ls=":", lw=1)
    ax[2].set_title(f"λ* vs 부하 (r={ct:+.2f}, {100*st:.0f}% 스케일)")
    fl = [r_ for r_ in R if r_["phase"] == "flight"]
    stw = [r_ for r_ in R if r_["phase"] == "stance"]
    ax[3].boxplot([[r_["lam"] for r_ in stw], [r_["lam"] for r_ in fl] or [np.nan]],
                  tick_labels=["stance", "flight"])
    ax[3].axhline(2.25, ls=":", lw=1); ax[3].set_ylabel("λ* [Nm]")
    ax[3].set_title("접촉 유무별 (같으면 접촉기원 아님)")
    for a_ in ax:
        a_.grid(alpha=0.3)
    ax[0].legend(fontsize=7)
    fig.suptitle("pre30 판별 프로브 — 창별 최적 무릎 보정토크 λ* (P19 플랜트, 0324 제외)")
    fig.tight_layout()
    fig.savefig(DST / "probe_lambda.png", dpi=110)
    print("saved", DST / "probe_lambda.png", flush=True)


if __name__ == "__main__":
    main()
