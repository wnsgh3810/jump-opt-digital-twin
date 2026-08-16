# -*- coding: utf-8 -*-
"""p24_hip_fit — P24 preflight 카드 1: 힙 지지 법칙 적합 + 공중 반증 예측 검사.

입력: p24_hip_rows.json (p24_hip_extract — light/stock 두 플랜트 변형의 창별 λ₁*).
적합 (light 변형, 지상 세션만: 0421/0424/0602 + s2s0319 + 0604):
  H0 : λ₁ = c                          (상수 — 부하 무관 대조)
  H2a: λ₁ = a₁ + b₁·|τ̂₁|              (게이트 없음)
  H2 : λ₁ = a₁ + b₁·|τ̂₁|·g(v₁; v0₁)   (과제 법칙 + 절편; g = 1/(1+(v/v0)²))
  H2f: λ₁ =      b₁·|τ̂₁|·g(v₁; v0₁)   (과제 문언 그대로 — a₁=0 강제)
  H2s: λ₁ = a₁ + b₁·τ̂₁·g(v₁; v0₁)     (부호 진단 — 지지가 부하 방향인가)
  K2 : λ₁ = a₁ + b₁·|τ̂₂|·g(v₁; v0₁)   (부하 대리 = 무릎(지상부하) — |τ̂₁|은 공중/지상을
  K2f: λ₁ =      b₁·|τ̂₂|·g(v₁; v0₁)    구별 못함(0604 0.40 vs air 0.42Nm)의 대안)
가중 = 그룹 균형 (그룹 = 세션, 0604은 렁별) — p23_law_calib.fit_hold_gate 규약.
CI = 선형화 공분산 95% (동일 규약). 공중(s2s_air + s2s0324) = 홀드아웃 예측 검사
(가설의 반증 지점: λ₁_air ≈ 0 & 법칙 예측도 ≈ 0이어야 함).

출력: p24_hip_fit.json (+ p24_hip_fit.png). 색 명시 없음 (auto cycle).
실행: PYTHONIOENCODING=utf-8 python p24_hip_fit.py
"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROWS_PATH = HERE / "p24_hip_rows.json"
FIT_PATH = HERE / "p24_hip_fit.json"
FIG_PATH = HERE / "p24_hip_fit.png"
GND = ("0421", "0424", "0602", "s2s0319", "0604")
AIRS = ("s2s_air", "s2s0324")
BINS = [(0.0, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 8.0), (8.0, 25.0)]
BIN_LAB = ["|dq1|<0.3", "0.3-1", "1-3", "3-8", "8+"]
KNEE_V0 = 5.7995        # 무릎 법칙 v0 (p23_law_fit hold_gate) — 대조용


def g_of(v, v0):
    return 1.0 / (1.0 + (np.asarray(v, float) / v0) ** 2)


def grp_of(r):
    return f"0604_{r['branch']}_{r['sub']}" if r["sess"] == "0604" else r["sess"]


def weights(rs):
    cnt = {}
    for r in rs:
        cnt[grp_of(r)] = cnt.get(grp_of(r), 0) + 1
    w = np.array([1.0 / cnt[grp_of(r)] for r in rs])
    return w / w.sum() * len(w)


def _ci(res, n):
    """least_squares 결과 → 95% CI (선형화 공분산) — p23_law_calib._ci 동형."""
    p = len(res.x)
    dof_ = max(n - p, 1)
    s2 = 2 * res.cost / dof_
    JTJ = res.jac.T @ res.jac
    try:
        cov = s2 * np.linalg.inv(JTJ)
        se = np.sqrt(np.maximum(np.diag(cov), 0))
    except np.linalg.LinAlgError:
        se = np.full(p, np.nan)
    return 1.96 * se


def fit_all(F):
    """지상 창 F → 모델 5종 적합 dict."""
    from scipy.optimize import least_squares
    lam = np.array([r["lam1"] for r in F])
    tau = np.array([r["t1m"] for r in F])          # |τ̂₁| 창 평균
    taus = np.array([r["t1sgn"] for r in F])       # 부호 있는 τ̂₁ 창 평균
    v1 = np.array([r["v1"] for r in F])            # |dq₁| 창 평균
    w = weights(F)
    sw = np.sqrt(w)
    n = len(F)
    out = {"n_fit": int(n)}

    # H0 (가중 상수)
    c0 = float(np.sum(w * lam) / np.sum(w))
    rss0 = float(np.sum(w * (lam - c0) ** 2))
    out["H0"] = dict(params=dict(c=c0),
                     ci=dict(c=float(1.96 * np.sqrt(rss0 / (n - 1) / np.sum(w)))),
                     rss_w=rss0, k=1)

    # H2a (가중 선형, 게이트 없음)
    X = np.column_stack([np.ones(n), tau])
    coef, *_ = np.linalg.lstsq(X * sw[:, None], lam * sw, rcond=None)
    res = X @ coef - lam
    rss = float(np.sum(w * res ** 2))
    cov = rss / (n - 2) * np.linalg.inv((X * sw[:, None]).T @ (X * sw[:, None]))
    out["H2a"] = dict(params=dict(a=float(coef[0]), b=float(coef[1])),
                      ci=dict(a=float(1.96 * np.sqrt(cov[0, 0])),
                              b=float(1.96 * np.sqrt(cov[1, 1]))), rss_w=rss, k=2)

    def nls(fun, p0, bounds, v0grid, v0slot):
        best = None
        for v0g in v0grid:
            p0_ = list(p0)
            p0_[v0slot] = v0g
            r_ = least_squares(fun, p0_, bounds=bounds)
            if best is None or r_.cost < best.cost:
                best = r_
        return best

    # H2 (절편 + 게이트)
    def res2(p):
        a, b, v0 = p
        return sw * ((a + b * tau * g_of(v1, v0)) - lam)
    b2 = nls(res2, [0.0, 0.3, 6.0], ([-4, -1.5, 0.3], [4, 1.5, 60]),
             (1.0, 2.0, 4.0, 6.0, 10.0, 20.0), 2)
    ci2 = _ci(b2, n)
    out["H2"] = dict(params=dict(a=float(b2.x[0]), b=float(b2.x[1]), v0=float(b2.x[2])),
                     ci=dict(a=float(ci2[0]), b=float(ci2[1]), v0=float(ci2[2])),
                     rss_w=float(2 * b2.cost), k=3, v0_at_bound=bool(b2.x[2] > 59.0))

    # H2f (a=0 강제 — 과제 문언)
    def res2f(p):
        b, v0 = p
        return sw * (b * tau * g_of(v1, v0) - lam)
    b2f = nls(res2f, [0.3, 6.0], ([-1.5, 0.3], [1.5, 60]),
              (1.0, 2.0, 4.0, 6.0, 10.0, 20.0), 1)
    ci2f = _ci(b2f, n)
    out["H2f"] = dict(params=dict(b=float(b2f.x[0]), v0=float(b2f.x[1])),
                      ci=dict(b=float(ci2f[0]), v0=float(ci2f[1])),
                      rss_w=float(2 * b2f.cost), k=2, v0_at_bound=bool(b2f.x[1] > 59.0))

    # H2s (부호 진단)
    def res2s(p):
        a, b, v0 = p
        return sw * ((a + b * taus * g_of(v1, v0)) - lam)
    b2s = nls(res2s, [0.0, 0.3, 6.0], ([-4, -1.5, 0.3], [4, 1.5, 60]),
              (1.0, 2.0, 4.0, 6.0, 10.0, 20.0), 2)
    ci2s = _ci(b2s, n)
    out["H2s"] = dict(params=dict(a=float(b2s.x[0]), b=float(b2s.x[1]), v0=float(b2s.x[2])),
                      ci=dict(a=float(ci2s[0]), b=float(ci2s[1]), v0=float(ci2s[2])),
                      rss_w=float(2 * b2s.cost), k=3, v0_at_bound=bool(b2s.x[2] > 59.0))

    # K2 / K2f (부하 대리 = 무릎 |τ̂₂| — 지상부하를 실제로 구별하는 유일한 창 통계)
    tk = np.array([r["tk"] for r in F])
    def resk(p):
        a, b, v0 = p
        return sw * ((a + b * tk * g_of(v1, v0)) - lam)
    bk = nls(resk, [0.0, -0.2, 4.0], ([-4, -1.5, 0.3], [4, 1.5, 60]),
             (1.0, 2.0, 4.0, 6.0, 10.0, 20.0), 2)
    cik = _ci(bk, n)
    out["K2"] = dict(params=dict(a=float(bk.x[0]), b=float(bk.x[1]), v0=float(bk.x[2])),
                     ci=dict(a=float(cik[0]), b=float(cik[1]), v0=float(cik[2])),
                     rss_w=float(2 * bk.cost), k=3, v0_at_bound=bool(bk.x[2] > 59.0))

    def reskf(p):
        b, v0 = p
        return sw * (b * tk * g_of(v1, v0) - lam)
    bkf = nls(reskf, [-0.2, 4.0], ([-1.5, 0.3], [1.5, 60]),
              (1.0, 2.0, 4.0, 6.0, 10.0, 20.0), 1)
    cikf = _ci(bkf, n)
    out["K2f"] = dict(params=dict(b=float(bkf.x[0]), v0=float(bkf.x[1])),
                      ci=dict(b=float(cikf[0]), v0=float(cikf[1])),
                      rss_w=float(2 * bkf.cost), k=2, v0_at_bound=bool(bkf.x[1] > 59.0))

    for m in ("H0", "H2a", "H2", "H2f", "H2s", "K2", "K2f"):
        d_ = out[m]
        d_["rmse_w"] = float(np.sqrt(d_["rss_w"] / n))
        d_["aic"] = float(n * np.log(max(d_["rss_w"] / n, 1e-12)) + 2 * d_["k"])
        d_["bic"] = float(n * np.log(max(d_["rss_w"] / n, 1e-12)) + d_["k"] * np.log(n))
    return out


def predict(model, p, rows):
    tau = np.array([r["t1m"] for r in rows])
    taus = np.array([r["t1sgn"] for r in rows])
    tk = np.array([r["tk"] for r in rows])
    v1 = np.array([r["v1"] for r in rows])
    if model == "H0":
        return np.full(len(rows), p["c"])
    if model == "H2a":
        return p["a"] + p["b"] * tau
    if model == "H2":
        return p["a"] + p["b"] * tau * g_of(v1, p["v0"])
    if model == "H2f":
        return p["b"] * tau * g_of(v1, p["v0"])
    if model == "H2s":
        return p["a"] + p["b"] * taus * g_of(v1, p["v0"])
    if model == "K2":
        return p["a"] + p["b"] * tk * g_of(v1, p["v0"])
    if model == "K2f":
        return p["b"] * tk * g_of(v1, p["v0"])
    raise KeyError(model)


def sess_table(rows, label, fits=None):
    """세션별 λ₁* 요약 (+옵션: H2 잔차)."""
    out = {}
    print(f"\n[{label}] 세션별 λ₁* (창 평균±std | 저속 v₁<1 | ⟨|τ̂₁|⟩)")
    for s in GND + AIRS:
        rs = [r for r in rows if r["sess"] == s]
        if not rs:
            continue
        lo = [r["lam1"] for r in rs if r["v1"] < 1.0]
        la = [r["lam1"] for r in rs]
        tm = [r["t1m"] for r in rs]
        e = {}
        if fits:
            pr = predict("H2", fits["H2"]["params"], rs)
            e = dict(resid_mean=float(np.mean([r["lam1"] for r in rs] - pr)),
                     resid_rmse=float(np.sqrt(np.mean(([r["lam1"] for r in rs] - pr) ** 2))))
        out[s] = dict(n=len(rs), lam_mean=float(np.mean(la)), lam_std=float(np.std(la)),
                      lam_lo=float(np.mean(lo)) if lo else float("nan"),
                      n_lo=len(lo), t1m_mean=float(np.mean(tm)), **e)
        print(f"  {s:9s} n={len(rs):4d} λ₁ {np.mean(la):+.2f}±{np.std(la):.2f}"
              f" | v<1: {np.mean(lo) if lo else float('nan'):+.2f} (n={len(lo)})"
              f" | ⟨|τ̂₁|⟩={np.mean(tm):.2f}Nm"
              + (f" | H2 잔차 {e['resid_mean']:+.2f} (rmse {e['resid_rmse']:.2f})" if e else ""))
    return out


def main():
    t0 = time.time()
    blob = safe.read_json(ROWS_PATH)
    rows_all = [r for r in blob["rows"] if not r["edge"]]
    n_edge = len(blob["rows"]) - len(rows_all)
    light = [r for r in rows_all if r["variant"] == "light"]
    stock = [r for r in rows_all if r["variant"] == "stock"]
    print(f"=== p24_hip_fit — rows {len(blob['rows'])} (edge 제외 {n_edge}) | "
          f"light {len(light)} / stock {len(stock)} ===")

    F = [r for r in light if r["sess"] in GND]
    HO = [r for r in light if r["sess"] in AIRS]
    fits = fit_all(F)

    print(f"\n[모델 비교 — light 플랜트, 지상 {len(F)}창 적합 / 공중 {len(HO)}창 홀드아웃]")
    print(f"{'모델':4s} {'k':>2} {'wRMSE':>7} {'AIC':>9} {'BIC':>9}  params (±95%CI)")
    for m in ("H0", "H2a", "H2", "H2f", "H2s", "K2", "K2f"):
        d_ = fits[m]
        ps = " ".join(f"{k}={v:+.4f}±{d_['ci'].get(k, float('nan')):.4f}"
                      for k, v in d_["params"].items())
        print(f"{m:4s} {d_['k']:2d} {d_['rmse_w']:7.3f} {d_['aic']:9.1f} {d_['bic']:9.1f}  {ps}"
              + ("  ※v0 상한" if d_.get("v0_at_bound") else ""))

    st_l = sess_table(light, "light — 세션별", fits)
    st_s = sess_table(stock, "stock(대조군, p23a 그대로) — 세션별")

    # 공중 반증 예측 검사
    print("\n[공중 반증 예측 — 가설: light 플랜트에서 λ₁_air ≈ 0, 법칙 예측도 ≈ 0]")
    air_chk = {}
    for s in AIRS:
        rs = [r for r in HO if r["sess"] == s]
        if not rs:
            continue
        la = np.array([r["lam1"] for r in rs])
        pr = predict("H2", fits["H2"]["params"], rs)
        prk = predict("K2f", fits["K2f"]["params"], rs)
        sem = la.std() / np.sqrt(len(la))
        air_chk[s] = dict(n=len(rs), obs_mean=float(la.mean()), obs_ci95=float(1.96 * sem),
                          pred_mean=float(pr.mean()), pred_mean_K2f=float(prk.mean()),
                          pred_rmse=float(np.sqrt(np.mean((pr - la) ** 2))),
                          pred_rmse_K2f=float(np.sqrt(np.mean((prk - la) ** 2))))
        print(f"  {s:9s} 관측 {la.mean():+.3f}±{1.96 * sem:.3f} (n={len(rs)}) | "
              f"H2 예측 {pr.mean():+.3f} (RMSE {air_chk[s]['pred_rmse']:.3f}) | "
              f"K2f 예측 {prk.mean():+.3f} (RMSE {air_chk[s]['pred_rmse_K2f']:.3f})")

    # 0604 부하축
    print("\n[0604 부하축 (light, v₁<1) — 지지 ∝ 힙 부하?]")
    load_axis = []
    for br, sub, load in [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5),
                          ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0.0)]:
        rs = [r for r in light if r["sess"] == "0604" and r["sub"] == sub
              and r["branch"] == br and r["v1"] < 1.0]
        if not rs:
            continue
        la = [r["lam1"] for r in rs]
        pr = predict("H2", fits["H2"]["params"], rs)
        load_axis.append(dict(branch=br, sub=sub, load=load, n=len(rs),
                              t1m=float(np.mean([r["t1m"] for r in rs])),
                              obs=float(np.mean(la)), obs_std=float(np.std(la)),
                              pred=float(np.mean(pr))))
        print(f"  {br:6s}/{sub:9s} {load:.1f}kg ⟨|τ̂₁|⟩={load_axis[-1]['t1m']:.2f}Nm "
              f"λ₁ {np.mean(la):+.2f}±{np.std(la):.2f} (n={len(rs)}) | 예측 {np.mean(pr):+.2f}")

    # 게이트 빈 추적 (H2 절편 기준 정규화, 지지항 >0.8Nm 창)
    hp = fits["H2"]["params"]
    gate_bins = []
    for j, (lo, hi) in enumerate(BINS):
        rs = [r for r in F if lo <= r["v1"] < hi and abs(hp["b"]) * r["t1m"] > 0.8]
        if len(rs) < 3:
            continue
        gh = [(r["lam1"] - hp["a"]) / (hp["b"] * r["t1m"]) for r in rs]
        gate_bins.append(dict(lab=BIN_LAB[j], v=float(np.mean([r["v1"] for r in rs])),
                              g=float(np.mean(gh)),
                              sem=float(np.std(gh) / np.sqrt(len(gh))), n=len(rs)))
    print("\n[게이트 빈 추적 (light, (λ₁−a)/(b·|τ̂₁|), 지지항>0.8Nm)]")
    for g_ in gate_bins:
        print(f"  {g_['lab']:10s} n={g_['n']:4d} v̄={g_['v']:5.2f}  ĝ={g_['g']:+.3f}±"
              f"{g_['sem']:.3f}  vs g(v̄;{hp['v0']:.1f})={float(g_of(g_['v'], hp['v0'])):.3f}")

    # 지지 비율 (저속): supp/|τ̂₁| ≈ b₁ (g→1) — 가설의 '~40-50% at air load scale' 대조
    print(f"\n[지지 비율] 저속 g→1에서 supp₁/|τ̂₁| ≈ b₁ = {hp['b']:+.3f} "
          f"(±{fits['H2']['ci']['b']:.3f}) — 가설 예상 0.4~0.5")
    print(f"[게이트 v0₁] = {hp['v0']:.2f}±{fits['H2']['ci']['v0']:.2f} rad/s "
          f"(무릎 법칙 v0 = {KNEE_V0:.2f})")

    # 배선 권고 (p23_v6_runners HIP 기본값의 단일 출처)
    kf = fits["K2f"]
    tk_max = float(max(r["tk"] for r in F))
    wire = dict(form="supp1 = b1*min(|tau2_hat|, cap)*g(|dq1|; v01)  (a1=0)",
                src="knee", a1=0.0, b1=kf["params"]["b"], b1_ci=kf["ci"]["b"],
                v01=kf["params"]["v0"], v01_ci=kf["ci"]["v0"], cap=round(tk_max, 2),
                why=("과제 문언 |τ̂₁| 대리는 공중/지상 비구별 (0604 지상 0.40Nm vs air "
                     "0.42Nm) → H2 절편 -1.7 퇴화·공중 예측 실패. K2f(무릎=지상부하 대리, "
                     "절편 0 강제)만 b₁ CI가 0 제외 + 공중 자동 소멸."))
    print(f"\n[배선 권고 K2f] b1={wire['b1']:+.4f}±{wire['b1_ci']:.4f} "
          f"v01={wire['v01']:.3f}±{wire['v01_ci']:.3f} cap={wire['cap']} (a1=0, src=knee)")

    # 저장
    out = dict(gen=time.strftime("%Y-%m-%d %H:%M"),
               n_rows=len(blob["rows"]), n_edge=n_edge,
               n_fit=len(F), n_holdout_air=len(HO),
               fits=fits, sess_light=st_l, sess_stock=st_s,
               air_check=air_chk, load_axis=load_axis, gate_bins=gate_bins,
               knee_v0_ref=KNEE_V0, wire=wire,
               note=("light 플랜트 (I_th=0.40, dz_th=-0.03 — 케이지 밖, 측정 전용) 창별 "
                     "λ₁* 적합. λ₂=p23a 법칙 고정 (좌표하강 결합 caveat: λ₁*가 무릎 법칙 "
                     "잔차를 일부 흡수할 수 있음). 적합=지상, 공중=홀드아웃 반증 검사."))
    safe.atomic_json_write(FIT_PATH, out)

    # ── 그림 ──
    fig, ax = plt.subplots(2, 2, figsize=(14.5, 10))
    mks = ["o", "s", "^", "D", "x", "P", "*"]
    axa = ax[0, 0]
    tg = np.linspace(0, max(r["t1m"] for r in F) * 1.05, 60)
    for j, (lo, hi) in enumerate(BINS):
        rs = [r for r in F if lo <= r["v1"] < hi]
        if not rs:
            continue
        axa.scatter([r["t1m"] for r in rs], [r["lam1"] for r in rs], s=14, alpha=0.5,
                    marker=mks[j % len(mks)], label=BIN_LAB[j])
    for j, s in enumerate(AIRS):
        rs = [r for r in HO if r["sess"] == s]
        if rs:
            axa.scatter([r["t1m"] for r in rs], [r["lam1"] for r in rs], s=20, alpha=0.7,
                        marker=mks[(5 + j) % len(mks)], label=f"{s} (공중 홀드아웃)")
    axa.plot(tg, hp["a"] + hp["b"] * tg, lw=1.8,
             label=f"H2 @g=1: {hp['a']:+.2f}{hp['b']:+.3f}·|τ̂₁|")
    axa.plot(tg, hp["a"] + hp["b"] * tg * float(g_of(5.0, hp["v0"])), lw=1.6, ls="--",
             label=f"H2 @v=5 (v0={hp['v0']:.1f})")
    axa.axhline(0, lw=0.8, alpha=0.5)
    axa.set_xlabel("창 평균 |τ̂₁| [Nm] (힙 부하)"); axa.set_ylabel("창별 λ₁* [Nm]")
    axa.set_title("힙 λ₁* vs 부하 — light 플랜트 (지상 속도빈 + 공중 앵커)")
    axa.legend(fontsize=7); axa.grid(alpha=0.3)

    axb = ax[0, 1]
    if gate_bins:
        axb.errorbar([g_["v"] for g_ in gate_bins], [g_["g"] for g_ in gate_bins],
                     yerr=[1.96 * g_["sem"] for g_ in gate_bins], fmt="o", capsize=3,
                     label="측정 ĝ 빈 평균")
    vg = np.logspace(-1.3, 1.4, 100)
    axb.plot(vg, g_of(vg, hp["v0"]), lw=1.5, label=f"적합 g(v; v0₁={hp['v0']:.1f})")
    axb.plot(vg, g_of(vg, KNEE_V0), lw=1.2, ls="--", label=f"무릎 법칙 g(v; {KNEE_V0:.1f})")
    axb.axhline(1.0, lw=0.8, alpha=0.5)
    axb.set_xscale("log")
    axb.set_xlabel("창 평균 |dq₁| [rad/s]"); axb.set_ylabel("(λ₁−a)/(b·|τ̂₁|)")
    axb.set_title("힙 속도 게이트 — 무릎 게이트와 대조")
    axb.legend(fontsize=8); axb.grid(alpha=0.3)

    axc = ax[1, 0]
    ss = [s for s in GND + AIRS if s in st_l]
    xs = np.arange(len(ss))
    axc.plot(xs, [st_l[s]["lam_mean"] for s in ss], "o-", label="light 관측 ⟨λ₁*⟩")
    axc.plot(xs, [float(np.mean(predict("H2", hp, [r for r in light if r["sess"] == s])))
                  for s in ss], "s--", label="H2 법칙 예측")
    axc.plot(xs, [st_s[s]["lam_mean"] if s in st_s else float("nan") for s in ss],
             "^:", label="stock(p23a) 관측 ⟨λ₁*⟩ (대조)")
    axc.axhline(0, lw=0.8, alpha=0.5)
    axc.set_xticks(xs); axc.set_xticklabels(ss, rotation=30, fontsize=8)
    axc.set_ylabel("λ₁ [Nm]")
    axc.set_title("세션별 힙 잔차 — light(법칙 필요) vs stock(무거운 thigh가 대리)")
    axc.legend(fontsize=8); axc.grid(alpha=0.3)

    axd = ax[1, 1]
    if load_axis:
        la_ = [r_ for r_ in load_axis if r_["branch"] == "cvt"]
        axd.errorbar([r_["load"] for r_ in la_], [r_["obs"] for r_ in la_],
                     yerr=[r_["obs_std"] for r_ in la_], fmt="o-", capsize=3,
                     label="0604 cvt 관측 (v₁<1)")
        axd.plot([r_["load"] for r_ in la_], [r_["pred"] for r_ in la_], "s--",
                 label="H2 예측")
        nc = [r_ for r_ in load_axis if r_["branch"] == "no_cvt"]
        if nc:
            axd.errorbar([r_["load"] for r_ in nc], [r_["obs"] for r_ in nc],
                         yerr=[r_["obs_std"] for r_ in nc], fmt="^", capsize=3,
                         label="0604 no_cvt 관측")
    axd.set_xlabel("페이로드 [kg]"); axd.set_ylabel("λ₁ [Nm]")
    axd.set_title("부하축 — 페이로드에 따른 힙 지지 스케일링")
    axd.legend(fontsize=8); axd.grid(alpha=0.3)

    fig.suptitle("P24 preflight — 힙 부하비례 지지 법칙 λ₁ = a₁ + b₁·|τ̂₁|·g(|dq₁|; v0₁) "
                 "(light-thigh p23a 플랜트, 지상 적합 / 공중 홀드아웃)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=110)
    print(f"\nsaved {FIT_PATH.name} + {FIG_PATH.name} [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
