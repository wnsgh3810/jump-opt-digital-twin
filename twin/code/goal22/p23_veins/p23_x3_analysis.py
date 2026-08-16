# -*- coding: utf-8 -*-
"""p23_x3_analysis — P23 Phase 3 판결부: 동적 푸시 부족분 3택 판별.

입력: p23_x3_rows.json (p23_x3_winlam — 6세션 창별 λ2*/λ1*, 단일 프로토콜)
판별 논리 (프롬프트 명세):
  λ*(상태)가 명령 구조(family)와 무관하게 상태만의 함수 → 플랜트 성질 (H-B/H-C 쪽)
  같은 상태에서 family별로 갈라짐 → 체인/명령 구조 성질 (H-A 쪽)
분석:
  [1] 세션별 λ2* 표 (저속/고속 분리 — exp7 표와 연속성)
  [2] ★ 핵심 대조 (같은 날): 0319pd(NO_TR_JUMP, PD) vs 0319tau(no_tr_tau, FF)
      상태 근접 매칭 (q2m, dq2m, a2m z-정규화 유클리드, greedy 1:1) → Δλ2* 통계
      (부트스트랩 CI + Wilcoxon). 매칭 품질(거리) 보고, 거리 ≤1.0 제한 변형 포함.
  [3] 통합 회귀: λ2* ~ 1 + a2m + dq2m + q2m + famFF + day 더미 + famFF·a2m (HC3 CI)
      + 0319 단독 day-통제 회귀 + 물리형 회귀 (ddq2m 관성항 vs a2m 부하항 — H-B/H-C 힌트)
  [4] 보조 대조 (day 교란): 0422(FF) vs 0424+0602(PD) 매칭 — 방증 전용
  [5] 힙 채널: λ1* ~ a1m(부하) + q1m(자세) — '부하비례 지지' vs '질량 과대(중력 시그니처)'
출력: p23_x3_result.json + p23_x3_lambda.png (Malgun Gothic, 자동 색)
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
ROWS = HERE / "p23_x3_rows.json"
OUT_JSON = HERE / "p23_x3_result.json"
OUT_FIG = HERE / "p23_x3_lambda.png"
SESS_ORDER = ["jump_position_0421", "jump_0424", "jump_0602", "jump_0319pd",
              "jump_0422", "jump_0319tau"]
RNG = np.random.default_rng(23)


def arr(rows, k):
    return np.array([r[k] for r in rows], float)


# ══════════════════ 통계 헬퍼 ══════════════════
def ols_hc3(X, y, names):
    """OLS + HC3 샌드위치 SE → 표 (coef, se, ci95, p)."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    w = (e / np.clip(1 - h, 1e-6, None)) ** 2
    cov = XtX_inv @ (X.T * w) @ X @ XtX_inv
    se = np.sqrt(np.diag(cov))
    z = b / np.clip(se, 1e-12, None)
    p = 2 * stats.norm.sf(np.abs(z))
    r2 = 1 - np.sum(e ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
    cond = float(np.linalg.cond(X))
    tab = [dict(name=n, coef=float(bi), se=float(si),
                ci95=[float(bi - 1.96 * si), float(bi + 1.96 * si)], p=float(pi))
           for n, bi, si, pi in zip(names, b, se, p)]
    return dict(table=tab, r2=float(r2), n=int(len(y)), cond=cond)


def greedy_match(rows_a, rows_b, feats=("q2m", "dq2m", "a2m")):
    """z-정규화(합동 std) 유클리드 greedy 1:1 매칭 → [(ia, ib, dist)]."""
    FA = np.column_stack([arr(rows_a, f) for f in feats])
    FB = np.column_stack([arr(rows_b, f) for f in feats])
    pool = np.vstack([FA, FB])
    sd = pool.std(axis=0)
    sd[sd < 1e-9] = 1.0
    ZA, ZB = FA / sd, FB / sd
    D = np.sqrt(((ZA[:, None, :] - ZB[None, :, :]) ** 2).sum(-1))
    pairs = []
    used_a, used_b = set(), set()
    for idx in np.argsort(D, axis=None):
        ia, ib = int(idx // D.shape[1]), int(idx % D.shape[1])
        if ia in used_a or ib in used_b:
            continue
        pairs.append((ia, ib, float(D[ia, ib])))
        used_a.add(ia); used_b.add(ib)
        if len(pairs) == min(D.shape):
            break
    return pairs


def paired_stats(dl, n_boot=10000):
    """Δλ 통계: 평균, SD, 부트스트랩 95% CI, Wilcoxon p."""
    dl = np.asarray(dl, float)
    dl = dl[np.isfinite(dl)]
    if len(dl) < 3:
        return dict(n=int(len(dl)), mean=float("nan"))
    bs = np.array([RNG.choice(dl, len(dl)).mean() for _ in range(n_boot)])
    try:
        wp = float(stats.wilcoxon(dl).pvalue)
    except ValueError:
        wp = float("nan")
    return dict(n=int(len(dl)), mean=float(dl.mean()), sd=float(dl.std()),
                sem=float(dl.std() / np.sqrt(len(dl))),
                ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                wilcoxon_p=wp)


def nn_match(rows_a, rows_b, feats=("q2m", "dq2m", "a2m")):
    """복원 최근접 매칭 (각 A창 → 최근접 B창) — greedy 1:1의 강건성 대조용."""
    FA = np.column_stack([arr(rows_a, f) for f in feats])
    FB = np.column_stack([arr(rows_b, f) for f in feats])
    pool = np.vstack([FA, FB])
    sd = pool.std(axis=0)
    sd[sd < 1e-9] = 1.0
    D = np.sqrt((((FA / sd)[:, None, :] - (FB / sd)[None, :, :]) ** 2).sum(-1))
    jb = np.argmin(D, axis=1)
    return [(ia, int(jb[ia]), float(D[ia, jb[ia]])) for ia in range(len(rows_a))]


def match_block(rows_a, rows_b, la="A", lb="B", key="lam2"):
    """매칭 대조 블록: greedy 1:1 (전체 + 거리≤1.0) + NN 복원 변형. Δ = A − B."""
    pairs = greedy_match(rows_a, rows_b)
    ds_ = [p[2] for p in pairs]
    dl_all = [rows_a[ia][key] - rows_b[ib][key] for ia, ib, _ in pairs]
    tight = [(ia, ib, dd) for ia, ib, dd in pairs if dd <= 1.0]
    dl_t = [rows_a[ia][key] - rows_b[ib][key] for ia, ib, _ in tight]
    nn = nn_match(rows_a, rows_b)
    dl_nn = [rows_a[ia][key] - rows_b[ib][key] for ia, ib, _ in nn]
    out = dict(
        delta_nn=paired_stats(dl_nn),
        nn_dist_mean=float(np.mean([p[2] for p in nn])),
        n_a=len(rows_a), n_b=len(rows_b), n_pairs=len(pairs),
        dist=dict(mean=float(np.mean(ds_)), med=float(np.median(ds_)),
                  max=float(np.max(ds_))),
        delta_all=paired_stats(dl_all),
        n_tight=len(tight), delta_tight=paired_stats(dl_t),
        pairs=[dict(a=dict(t0=rows_a[ia]["t0"], lam2=rows_a[ia]["lam2"],
                           lam1=rows_a[ia]["lam1"], q2m=rows_a[ia]["q2m"],
                           dq2m=rows_a[ia]["dq2m"], a2m=rows_a[ia]["a2m"]),
                    b=dict(t0=rows_b[ib]["t0"], lam2=rows_b[ib]["lam2"],
                           lam1=rows_b[ib]["lam1"], q2m=rows_b[ib]["q2m"],
                           dq2m=rows_b[ib]["dq2m"], a2m=rows_b[ib]["a2m"]),
                    dist=dd) for ia, ib, dd in pairs],
        label=f"{la} - {lb}")
    return out


def std_coefs(X, y, names):
    """표준화 회귀계수 (비교용) — 절편 제외 열 z-score."""
    Xs = X.copy().astype(float)
    ys = (y - y.mean()) / max(y.std(), 1e-12)
    out = {}
    cols = []
    nm = []
    for j, n in enumerate(names):
        if n == "const":
            continue
        c = X[:, j]
        s = c.std()
        if s < 1e-12:
            continue
        cols.append((c - c.mean()) / s)
        nm.append(n)
    Z = np.column_stack([np.ones(len(y))] + cols)
    b = np.linalg.pinv(Z.T @ Z) @ Z.T @ ys
    for n, bi in zip(nm, b[1:]):
        out[n] = float(bi)
    return out


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    dat = json.load(open(ROWS, encoding="utf-8"))
    rows = dat["rows"]
    meta = dat["meta"]
    print("=" * 100)
    print("p23_x3_analysis — 동적 푸시 부족분 3택 판별 (H-A 체인 / H-B 관성 / H-C 기구)")
    print("=" * 100)
    print(f"입력: {len(rows)} 창, 프로토콜 skip(민감도<2%) {dat['meta']['n_skipped_insensitive']}")

    # ── 데이터 위생: edge 검열 ──
    n_edge2 = sum(1 for r in rows if r["lam2_edge"])
    n_edge1 = sum(1 for r in rows if r.get("lam1_edge"))
    ok = [r for r in rows if not r["lam2_edge"]]
    print(f"λ2 그리드 경계(검열) 창 {n_edge2}/{len(rows)} 제외 → 분석 {len(ok)}창 "
          f"(λ1 경계 {n_edge1} — 힙 분석에서 별도 제외)")

    res = {"meta_protocol": meta["protocol"], "hygiene": dict(
        n_rows=len(rows), n_lam2_edge=n_edge2, n_lam1_edge=n_edge1, n_used=len(ok))}

    # ══ [1] 세션 표 ══
    print("\n[1] 세션별 λ2* (저속 |dq2m|<5 / 고속 >10 rad/s) — 오프셋 0 통일, P19 플랜트")
    tab = {}
    for ds in SESS_ORDER:
        rs = [r for r in ok if r["ds"] == ds]
        if not rs:
            continue
        lo = [r["lam2"] for r in rs if abs(r["dq2m"]) < 5]
        hi = [r["lam2"] for r in rs if abs(r["dq2m"]) > 10]
        al = [r["lam2"] for r in rs]
        f = lambda v: (float(np.mean(v)), float(np.std(v)), len(v)) if v else (np.nan, 0, 0)
        tab[ds] = dict(all=f(al), lo=f(lo), hi=f(hi), family=rs[0]["family"], day=rs[0]["day"])
        print(f"  {ds:22s} [{rs[0]['family']} {rs[0]['day']}] 전체 {f(al)[0]:+.2f}±{f(al)[1]:.2f}"
              f" (n={f(al)[2]:3d}) | 저속 {f(lo)[0]:+.2f}±{f(lo)[1]:.2f} (n={f(lo)[2]})"
              f" | 고속 {f(hi)[0]:+.2f}±{f(hi)[1]:.2f} (n={f(hi)[2]})")
    res["session_table"] = tab

    # ══ [2] ★ 핵심 대조: 0319 같은 날 PD vs FF ══
    print("\n[2] ★ 핵심 대조 (day-통제): 0319pd(PD) vs 0319tau(FF) — 상태 매칭 Δλ2*")
    pd_r = [r for r in ok if r["ds"] == "jump_0319pd"]
    ff_r = [r for r in ok if r["ds"] == "jump_0319tau"]
    key = match_block(pd_r, ff_r, "0319pd", "0319tau")
    res["key_contrast_0319"] = key
    da, dt_ = key["delta_all"], key["delta_tight"]
    print(f"  창 수: PD {key['n_a']} / FF {key['n_b']} → 매칭 {key['n_pairs']}쌍, "
          f"거리(z) 평균 {key['dist']['mean']:.2f} / 중앙 {key['dist']['med']:.2f} / "
          f"최대 {key['dist']['max']:.2f}")
    print(f"  Δλ2*(PD−FF) 전체쌍  : {da['mean']:+.2f} ± {da['sem']:.2f} (SEM), "
          f"CI95 [{da['ci95'][0]:+.2f}, {da['ci95'][1]:+.2f}], Wilcoxon p={da['wilcoxon_p']:.3f} "
          f"(n={da['n']})")
    if dt_.get("n", 0) >= 3:
        print(f"  Δλ2*(PD−FF) 거리≤1.0: {dt_['mean']:+.2f} ± {dt_['sem']:.2f}, "
              f"CI95 [{dt_['ci95'][0]:+.2f}, {dt_['ci95'][1]:+.2f}], p={dt_['wilcoxon_p']:.3f} "
              f"(n={dt_['n']})")
    else:
        print(f"  거리≤1.0 쌍 {dt_.get('n', 0)}개 — 통계 불가 (매칭 품질 명기)")
    dn = key["delta_nn"]
    print(f"  Δλ2*(PD−FF) NN복원  : {dn['mean']:+.2f} ± {dn['sem']:.2f}, "
          f"CI95 [{dn['ci95'][0]:+.2f}, {dn['ci95'][1]:+.2f}] "
          f"(n={dn['n']}, NN거리 평균 {key['nn_dist_mean']:.2f})")
    # 강건성: 첫 창(t0=0.02) 제외 — FF 세션들 첫 창이 리셋 과도 인공물 (0422 3건·0319tau
    # 1건 모두 λ2 큰 음수, 기록이 이미 운동 중 시작하는 세션에서만 발생)
    pd_r2 = [r for r in pd_r if r["t0"] > 0.021]
    ff_r2 = [r for r in ff_r if r["t0"] > 0.021]
    key2 = match_block(pd_r2, ff_r2, "0319pd", "0319tau")
    key2.pop("pairs")
    res["key_contrast_0319_no_first_window"] = key2
    k2 = key2["delta_all"]
    print(f"  [강건성: 첫 창 제외] Δλ2*(PD−FF) = {k2['mean']:+.2f} ± {k2['sem']:.2f}, "
          f"CI95 [{k2['ci95'][0]:+.2f}, {k2['ci95'][1]:+.2f}], p={k2['wilcoxon_p']:.3f} "
          f"(n={k2['n']})")
    print("  매칭쌍 상세 (PD쪽 | FF쪽 | λ2 차):")
    for p in sorted(key["pairs"], key=lambda x: x["dist"]):
        a, b = p["a"], p["b"]
        print(f"    d={p['dist']:.2f}  PD(t0={a['t0']:.3f} q2={a['q2m']:+.2f} "
              f"dq2={a['dq2m']:5.2f} â2={a['a2m']:5.1f} λ2={a['lam2']:+.2f}) | "
              f"FF(t0={b['t0']:.3f} q2={b['q2m']:+.2f} dq2={b['dq2m']:5.2f} "
              f"â2={b['a2m']:5.1f} λ2={b['lam2']:+.2f}) | Δ={a['lam2'] - b['lam2']:+.2f}")
    # 힙도 같은 매칭으로
    dl1 = [key["pairs"][i]["a"]["lam1"] - key["pairs"][i]["b"]["lam1"]
           for i in range(len(key["pairs"]))]
    key["delta_lam1"] = paired_stats(dl1)
    d1 = key["delta_lam1"]
    if d1.get("n", 0) >= 3:
        print(f"  (힙) Δλ1*(PD−FF)   : {d1['mean']:+.2f} ± {d1['sem']:.2f}, "
              f"CI95 [{d1['ci95'][0]:+.2f}, {d1['ci95'][1]:+.2f}] (n={d1['n']})")

    # ══ [3] 통합 회귀 ══
    print("\n[3] 통합 회귀 λ2* ~ 상태 + family + day (HC3 CI95)")
    days = sorted(set(r["day"] for r in ok) - {"03-19"})     # 기준일 = 03-19
    names = (["const", "a2m", "dq2m", "q2m", "famFF"]
             + [f"day_{d}" for d in days] + ["famFF_x_a2m"])
    y = arr(ok, "lam2")
    fam = np.array([1.0 if r["family"] == "FF" else 0.0 for r in ok])
    X = np.column_stack(
        [np.ones(len(ok)), arr(ok, "a2m"), arr(ok, "dq2m"), arr(ok, "q2m"), fam]
        + [np.array([1.0 if r["day"] == d else 0.0 for r in ok]) for d in days]
        + [fam * arr(ok, "a2m")])
    reg = ols_hc3(X, y, names)
    res["pooled_regression"] = reg
    n_tests = len([n for n in names if n.startswith(("fam", "day"))])
    print(f"  n={reg['n']}, R2={reg['r2']:.3f}, cond={reg['cond']:.0f} "
          f"(Bonferroni 기준 α=0.05/{n_tests}={0.05 / n_tests:.4f} — fam/day 더미 {n_tests}개)")
    for t in reg["table"]:
        sig = "*" if (t["p"] < 0.05 / n_tests and t["name"].startswith(("fam", "day"))) else \
              ("+" if t["p"] < 0.05 else " ")
        print(f"    {t['name']:14s} {t['coef']:+8.3f}  CI[{t['ci95'][0]:+7.3f},"
              f"{t['ci95'][1]:+7.3f}]  p={t['p']:.4f} {sig}")

    # 0319 단독 (완전 day-통제)
    r19 = [r for r in ok if r["day"] == "03-19"]
    y19 = arr(r19, "lam2")
    f19 = np.array([1.0 if r["family"] == "FF" else 0.0 for r in r19])
    X19 = np.column_stack([np.ones(len(r19)), arr(r19, "a2m"), arr(r19, "dq2m"),
                           arr(r19, "q2m"), f19])
    reg19 = ols_hc3(X19, y19, ["const", "a2m", "dq2m", "q2m", "famFF"])
    res["regression_0319_only"] = reg19
    print(f"  [0319 단독 day-통제] n={reg19['n']}, R2={reg19['r2']:.3f}")
    for t in reg19["table"]:
        print(f"    {t['name']:14s} {t['coef']:+8.3f}  CI[{t['ci95'][0]:+7.3f},"
              f"{t['ci95'][1]:+7.3f}]  p={t['p']:.4f}")

    # 물리형: 부하항 vs 관성항 (H-B vs 부하법칙) — 공선성 명기
    Xp = np.column_stack([np.ones(len(ok)), arr(ok, "a2m"), arr(ok, "ddq2m"),
                          arr(ok, "dq2m")])
    np_ = ["const", "a2m", "ddq2m", "dq2m"]
    regp = ols_hc3(Xp, y, np_)
    cc = np.corrcoef(np.column_stack([arr(ok, "a2m"), arr(ok, "ddq2m"),
                                      arr(ok, "dq2m")]).T)
    regp["collinearity"] = dict(a2_ddq2=float(cc[0, 1]), a2_dq2=float(cc[0, 2]),
                                ddq2_dq2=float(cc[1, 2]))
    regp["std_coefs"] = std_coefs(Xp, y, np_)
    res["physics_form_regression"] = regp
    print(f"  [물리형 λ2*~a2m+ddq2m+dq2m] R2={regp['r2']:.3f} | 상관 "
          f"a2·ddq2={cc[0, 1]:.2f} a2·dq2={cc[0, 2]:.2f} ddq2·dq2={cc[1, 2]:.2f}")
    for t in regp["table"]:
        sc = regp["std_coefs"].get(t["name"])
        print(f"    {t['name']:8s} {t['coef']:+8.4f}  CI[{t['ci95'][0]:+7.4f},"
              f"{t['ci95'][1]:+7.4f}]  p={t['p']:.4f}"
              + (f"  (표준화 {sc:+.2f})" if sc is not None else ""))

    # 세션 고정효과 (within-session) 물리형 — 세션 간 수준차를 흡수하고 창 내부 형태만
    sess_ids = sorted(set(r["ds"] for r in ok))
    yf = y.copy().astype(float)
    Xf = np.column_stack([arr(ok, "a2m"), arr(ok, "ddq2m"), arr(ok, "dq2m")]).astype(float)
    for s in sess_ids:
        m = np.array([r["ds"] == s for r in ok])
        yf[m] -= yf[m].mean()
        Xf[m] -= Xf[m].mean(axis=0)
    regf = ols_hc3(np.column_stack([np.ones(len(ok)), Xf]), yf,
                   ["const", "a2m", "ddq2m", "dq2m"])
    regf["std_coefs"] = std_coefs(np.column_stack([np.ones(len(ok)), Xf]), yf,
                                  ["const", "a2m", "ddq2m", "dq2m"])
    res["physics_form_within_session"] = regf
    print(f"  [세션 고정효과(within) 물리형] R2={regf['r2']:.3f} — 세션 수준차 제거 후 형태")
    for t in regf["table"]:
        if t["name"] == "const":
            continue
        sc = regf["std_coefs"].get(t["name"])
        print(f"    {t['name']:8s} {t['coef']:+8.4f}  CI[{t['ci95'][0]:+7.4f},"
              f"{t['ci95'][1]:+7.4f}]  p={t['p']:.4f}"
              + (f"  (표준화 {sc:+.2f})" if sc is not None else ""))

    # ══ [4] 보조 대조 (day 교란) ══
    print("\n[4] 보조 대조 (day 교란 — 방증 전용): 0422(FF) vs 0424+0602(PD)")
    ff22 = [r for r in ok if r["ds"] == "jump_0422"]
    pd46 = [r for r in ok if r["ds"] in ("jump_0424", "jump_0602")]
    sec = match_block(ff22, pd46, "0422FF", "0424/0602PD")
    sec.pop("pairs")
    res["secondary_contrast"] = sec
    sa = sec["delta_all"]
    print(f"  매칭 {sec['n_pairs']}쌍 (거리 평균 {sec['dist']['mean']:.2f}) "
          f"Δλ2*(FF−PD) = {sa['mean']:+.2f} ± {sa['sem']:.2f}, "
          f"CI95 [{sa['ci95'][0]:+.2f}, {sa['ci95'][1]:+.2f}], p={sa['wilcoxon_p']:.3f}")

    # ══ [5] 힙 채널 ══
    print("\n[5] 힙 채널 λ1* — 부하비례 지지 vs 질량 과대(자세 시그니처)")
    hok = [r for r in ok if np.isfinite(r["lam1"]) and not r.get("lam1_edge")]
    print(f"  유효 힙 창 {len(hok)} (λ1 NaN/경계 제외)")
    htab = {}
    for ds in SESS_ORDER:
        rs = [r for r in hok if r["ds"] == ds]
        if not rs:
            continue
        v = [r["lam1"] for r in rs]
        htab[ds] = dict(mean=float(np.mean(v)), sd=float(np.std(v)), n=len(v))
        print(f"    {ds:22s} λ1* {np.mean(v):+.2f}±{np.std(v):.2f} (n={len(v)})")
    res["hip_session_table"] = htab
    yh = arr(hok, "lam1")
    Xh = np.column_stack([np.ones(len(hok)), arr(hok, "a1m"), arr(hok, "q1m")])
    nh = ["const", "a1m(부하)", "q1m(자세)"]
    regh = ols_hc3(Xh, yh, nh)
    regh["std_coefs"] = std_coefs(Xh, yh, nh)
    res["hip_regression"] = regh
    print(f"  회귀 λ1* ~ 부하 + 자세: R2={regh['r2']:.3f}")
    for t in regh["table"]:
        sc = regh["std_coefs"].get(t["name"])
        print(f"    {t['name']:12s} {t['coef']:+8.4f}  CI[{t['ci95'][0]:+7.4f},"
              f"{t['ci95'][1]:+7.4f}]  p={t['p']:.4f}"
              + (f"  (표준화 {sc:+.2f})" if sc is not None else ""))
    b_load = [t for t in regh["table"] if t["name"] == "a1m(부하)"][0]
    b_post = [t for t in regh["table"] if t["name"] == "q1m(자세)"][0]
    sig_load = b_load["p"] < 0.025
    sig_post = b_post["p"] < 0.025
    # '지지' 기제 예측 = 부하와 함께 λ1*가 (+)로 증가 (무릎 λ2>0과 동일 부호 구조).
    # (−) 기울기는 지지가 아니라 과대 모델(마찰/질량) 신호로 해석.
    if sig_load and b_load["coef"] > 0 and \
            abs(regh["std_coefs"]["a1m(부하)"]) >= abs(regh["std_coefs"]["q1m(자세)"]):
        hip_lean = "부하비례 지지 쪽 (λ1*가 힙 부하와 함께 (+) 증가 — 무릎과 동일 기제 의심)"
    elif sig_load and b_load["coef"] < 0:
        hip_lean = ("지지 반증: 부하 기울기 (−) — 고부하일수록 힙은 오히려 과잉 모델 "
                    "(질량/마찰 과대 쪽 신호). 자세항 " +
                    ("유의" if sig_post else "비유의"))
    elif sig_post and not sig_load:
        hip_lean = "질량/중력 시그니처 쪽 (자세 의존 우세 — thigh 질량 과대 의심)"
    elif sig_load and sig_post:
        hip_lean = "혼합 (부하·자세 둘 다 유의 — 단독 판정 불가)"
    else:
        hip_lean = "판별력 부족 (둘 다 비유의 — 지상 힙 λ1*는 P20의 '≈0' 주장과 비교로만)"
    res["hip_verdict_lean"] = hip_lean
    print(f"  → 힙 판정 lean: {hip_lean}")

    # ══ 그림 ══
    fig = plt.figure(figsize=(13.5, 5.4))
    ax = fig.add_subplot(1, 2, 1)
    fam_col = {}
    for famn, mk in (("PD", "o"), ("FF", "^")):
        rs = [r for r in ok if r["family"] == famn]
        sc = ax.scatter(arr(rs, "a2m"), arr(rs, "lam2"), s=20, alpha=0.65,
                        marker=mk, label=f"{famn} (n={len(rs)})")
        fam_col[famn] = sc.get_facecolor()[0]
    ax.set_xlabel("창 평균 |â₂| [Nm] (무릎 부하)")
    ax.set_ylabel("창별 무릎 보충 λ2* [Nm]")
    ax.set_title("λ2* vs 무릎 부하 — 명령 구조(family)별 (6세션, 단일 프로토콜)")
    ax.grid(alpha=0.3); ax.legend(loc="upper left", fontsize=9)
    # 매칭쌍 인셋: 0319 same-day
    axi = ax.inset_axes([0.60, 0.06, 0.38, 0.42])
    pl = [(p["b"]["lam2"], p["a"]["lam2"], p["dist"]) for p in key["pairs"]]
    if pl:
        xs, ys_, ds_ = zip(*pl)
        axi.scatter(xs, ys_, s=22, c=ds_, alpha=0.9)
        lim = [min(min(xs), min(ys_)) - 0.5, max(max(xs), max(ys_)) + 0.5]
        axi.plot(lim, lim, ls=":", lw=1)
        axi.set_xlim(lim); axi.set_ylim(lim)
    axi.set_xlabel("λ2* FF(0319tau)", fontsize=7)
    axi.set_ylabel("λ2* PD(0319pd)", fontsize=7)
    axi.set_title("같은 날 매칭쌍 (색=매칭거리)", fontsize=8)
    axi.tick_params(labelsize=7); axi.grid(alpha=0.3)

    ax2 = fig.add_subplot(1, 2, 2)
    q1_all = arr(hok, "q1m")
    vmin, vmax = float(q1_all.min()), float(q1_all.max())
    for famn, mk in (("PD", "o"), ("FF", "^")):
        rs = [r for r in hok if r["family"] == famn]
        sc2 = ax2.scatter(arr(rs, "a1m"), arr(rs, "lam1"), c=arr(rs, "q1m"),
                          s=22, alpha=0.8, marker=mk, vmin=vmin, vmax=vmax,
                          label=famn)
    cb = fig.colorbar(sc2, ax=ax2)
    cb.set_label("창 평균 q1 [rad] (힙 자세)")
    ax2.axhline(0.0, ls=":", lw=1)
    ax2.set_xlabel("창 평균 |â₁| [Nm] (힙 부하)")
    ax2.set_ylabel("창별 힙 보충 λ1* [Nm]")
    ax2.set_title("힙 채널: λ1* vs 부하 (색=자세) — 지지 vs 질량 판별")
    ax2.grid(alpha=0.3); ax2.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=120)
    print(f"\nsaved {OUT_FIG}")

    # ══ 3택 판결 ══
    print("\n" + "=" * 100)
    print("3택 판결 (H-A 측정/체인 | H-B 관성/질량 | H-C 기구)")
    fam_pool = [t for t in reg["table"] if t["name"] == "famFF"][0]
    fam_int = [t for t in reg["table"] if t["name"] == "famFF_x_a2m"][0]
    fam_19 = [t for t in reg19["table"] if t["name"] == "famFF"][0]
    alpha_b = 0.05 / n_tests
    key_ci = key["delta_all"]["ci95"]
    key_zero = key_ci[0] <= 0 <= key_ci[1]
    fam_sig = (fam_pool["p"] < alpha_b) or (fam_int["p"] < alpha_b) or (fam_19["p"] < 0.025)
    # family 효과의 부호 일관성: 0319단독 회귀 vs 매칭 Δ vs 보조 대조 (모두 FF−PD 방향으로)
    fam_signs = dict(
        matched_0319=float(-key["delta_all"]["mean"]),          # Δ는 PD−FF → 부호 반전
        reg_0319=float(fam_19["coef"]),
        pooled=float(fam_pool["coef"]),
        secondary_0422=float(sec["delta_all"]["mean"]))
    signs = np.sign([v for v in fam_signs.values() if abs(v) > 1e-9])
    sign_consistent = bool(len(set(signs.tolist())) <= 1)
    verdict = dict(
        key_contrast_zero=bool(key_zero),
        family_significant_pooled=bool(fam_sig),
        family_effect_signs_FFminusPD=fam_signs,
        family_sign_consistent=sign_consistent,
        delta_matched=key["delta_all"],
        dynamic_rise_universal="전 세션(양 family·전 day) 저속→고속 λ2* 상승 — 세션표 [1] 참조",
        note_confounds=["0319/0422 l_i=30.00 가정 (Clutch 미기록)",
                        "0319pd 힙 영점 −π/4 규약 보정 적용 (이산 규약 수정 — 로더 문서화)",
                        "0319pd knee cff≈0.35 — 순수 PD 아닐 가능성 (FF 부분 인가 의심, "
                        "로더 self-test 근거)",
                        "day 더미와 famFF 부분 공선 (0422가 유일한 04-22 세션)",
                        "오프셋 0 통일 — 적합 오프셋 미사용으로 λ* 산포 증가",
                        "0319 핵심 대조 n=17쌍 (단일 trial 쌍) — 검정력 제한"])
    res["verdict_inputs"] = verdict
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    print(f"  핵심 Δλ2*(매칭, day-통제) CI95 [{key_ci[0]:+.2f}, {key_ci[1]:+.2f}] → "
          f"{'0 포함' if key_zero else '0 배제'}")
    print(f"  family 항 유의성 (Bonferroni α={alpha_b:.4f}): pooled famFF p={fam_pool['p']:.4f}, "
          f"상호작용 p={fam_int['p']:.4f}, 0319단독 famFF p={fam_19['p']:.4f} → "
          f"{'유의(일부)' if fam_sig else '비유의'}")
    print(f"  family 효과 부호 (FF−PD 방향 통일): {fam_signs} → "
          f"{'일관' if sign_consistent else '불일관 (잔여 교란 신호 — 실효과 아님 쪽)'}")
    print(f"saved {OUT_JSON}")


if __name__ == "__main__":
    main()
