# -*- coding: utf-8 -*-
"""_G3_absolute — 26_08_07 **척도를 몰라도 되는 절대 측정** (마라톤G G3 결론부).

핵심 착상: 이 실험은 **다리 자체의 무게와 2kg 분동을 같은 센서로, 비슷한 크기로** 잰다.
  raw(q1) = a·cos q1 + b·cos(q1+q2) + load·w·M·g·(L1 cos q1 + L2 cos(q1+q2)) + off
  여기서 w = 센서 척도 [raw/Nm] 이므로
      **gA = a/w · gB = b/w**  ← 센서 척도가 **약분되어 사라진다**.
  즉 a_hat 이 맞든 틀리든, 2kg 분동을 자로 삼아 **다리의 중력을 Nm 절대값으로** 얻는다.
  이것이 H2(트윈 질량분포)를 판정하는 정본 측정이다.

부수 산출: w 자체 = 센서 척도. a_hat 의 선형게인(0.6821 Nm/raw)과 비교하면 H1 판정.
마찰은 **방향평균**(0.04Hz 왕복의 상행·하행 평균)으로 소거하므로 적합하지 않는다.
CLI: python _G3_absolute.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
from _G3_scale import (load, hip_segments, q2_on, SESS, M_W, G, L1, L2)   # noqa: E402


def davg(d, segs, grid, key):
    up, dn = [], []
    for a, b in segs:
        q = d["q1"][a:b]; y = d[key][a:b]; v = d["dq1"][a:b]
        for mask, box in ((v > 0.02, up), (v < -0.02, dn)):
            if mask.sum() < 200:
                continue
            qq, yy = q[mask], y[mask]
            o = np.argsort(qq); qq, yy = qq[o], yy[o]
            uq, inv = np.unique(np.round(qq, 5), return_inverse=True)
            box.append(np.interp(grid, uq, np.bincount(inv, yy) / np.bincount(inv),
                                 left=np.nan, right=np.nan))
    if not up or not dn:
        return None
    return 0.5 * (np.nanmean(np.array(up), 0) + np.nanmean(np.array(dn), 0))


def collect():
    D0 = [load(SESS / "0kg" / n) for n in ("probe_sweep_v1", "probe_sweep_v1 - 2")]
    D2 = load(SESS / "2kg" / "probe_sweep_v1")
    S0 = [hip_segments(d) for d in D0]; S2 = hip_segments(D2)
    keys = sorted(set(S2) & set(S0[0]) & set(S0[1]))
    rows = []
    for k_ in keys:
        lo = max(np.degrees(D2["q1"][a:b]).min() for a, b in S2[k_])
        hi = min(np.degrees(D2["q1"][a:b]).max() for a, b in S2[k_])
        grid = np.radians(np.linspace(lo + 1.5, hi - 1.5, 80))
        q2g = q2_on(D2, S2[k_], grid)
        for ri, (d, segs, ld) in enumerate(
                [(D0[0], S0[0][k_], 0.0), (D0[1], S0[1][k_], 0.0), (D2, S2[k_], 1.0)]):
            for key, ch in (("raw1", 1), ("raw2", 2)):
                y = davg(d, segs, grid, key)
                if y is None:
                    continue
                for i in range(len(grid)):
                    if not np.isfinite(y[i]):
                        continue
                    rows.append(dict(run=ri, load=ld, ch=ch, q1=grid[i], q2=q2g[i],
                                     y=y[i], key=k_))
    return rows


def fit(rows, ch):
    """raw = a·c1 + b·c12 + load·w·M·g·lev + off_run   (ch=2 는 c1 항 없음)"""
    R = [r for r in rows if r["ch"] == ch]
    nruns = len(set(r["run"] for r in R))
    ncol = (3 if ch == 1 else 2) + nruns
    X = np.zeros((len(R), ncol)); y = np.zeros(len(R))
    for i, r in enumerate(R):
        c1 = np.cos(r["q1"]); c12 = np.cos(r["q1"] + r["q2"])
        lev = (L1 * c1 + L2 * c12) if ch == 1 else (L2 * c12)
        if ch == 1:
            X[i, 0] = c1; X[i, 1] = c12; X[i, 2] = r["load"] * M_W * G * lev
            X[i, 3 + r["run"]] = 1.0
        else:
            X[i, 0] = c12; X[i, 1] = r["load"] * M_W * G * lev
            X[i, 2 + r["run"]] = 1.0
        y[i] = r["y"]
    th, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ th
    return th, X, y, res, R


def boot(rows, ch, nb=2000, seed=11):
    rng = np.random.default_rng(seed)
    th, X, y, res, R = fit(rows, ch)
    out = []
    n = len(y)
    for _ in range(nb):
        idx = rng.integers(0, n, n)
        try:
            t, *_ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
            out.append(t)
        except Exception:
            pass
    return th, np.array(out)


def main():
    rows = collect()
    print("=" * 108)
    print("① raw 단위 동시 적합 (0kg 2회 + 2kg 1회, 방향평균으로 마찰 소거)")
    OUT = {}
    for ch in (1, 2):
        th, B = boot(rows, ch)
        if ch == 1:
            a, b, w = th[0], th[1], th[2]
            Ba, Bb, Bw = B[:, 0], B[:, 1], B[:, 2]
        else:
            a, b, w = np.nan, th[0], th[1]
            Bb, Bw = B[:, 0], B[:, 1]
            Ba = np.full_like(Bb, np.nan)
        _, X, y, res, R = fit(rows, ch)
        print(f"\n  [채널 {'힙 τ1' if ch==1 else '무릎 τ2'}]  표본 {len(y)}  "
              f"잔차 RMS {np.sqrt(np.mean(res**2)):.4f} raw  설명력 {1-np.var(res)/np.var(y):.4f}")
        print(f"    w (센서 척도) = {w:.4f} raw/Nm  →  **1 raw = {1/w:.4f} Nm**  "
              f"95%[{np.percentile(1/Bw,2.5):.3f}, {np.percentile(1/Bw,97.5):.3f}]")
        if ch == 1:
            gA = a / w; BgA = Ba / Bw
            print(f"    gA = a/w = **{gA:.4f} Nm**  95%[{np.percentile(BgA,2.5):.3f}, "
                  f"{np.percentile(BgA,97.5):.3f}]   ← 척도가 약분됨")
            OUT["gA"] = (float(gA), float(np.percentile(BgA, 2.5)), float(np.percentile(BgA, 97.5)))
        gB = b / w; BgB = Bb / Bw
        print(f"    gB = b/w = **{gB:.4f} Nm**  95%[{np.percentile(BgB,2.5):.3f}, "
              f"{np.percentile(BgB,97.5):.3f}]")
        OUT[f"gB_ch{ch}"] = (float(gB), float(np.percentile(BgB, 2.5)), float(np.percentile(BgB, 97.5)))
        OUT[f"nm_per_raw_ch{ch}"] = float(1 / w)

    # ── ② 트윈 대조 ──
    print("\n" + "=" * 108)
    print("② 중력 절대값 대조 — 이 gA·gB 는 센서 척도와 무관하다 (2kg 분동이 자)")
    from _G2_air_twin import twin, grav
    gA_m = OUT["gA"][0]; gB_m = OUT["gB_ch2"][0]
    print(f"{'후보':<26}{'gA[Nm]':>10}{'실측대비':>10}{'gB[Nm]':>10}{'실측대비':>10}"
          f"{'ρ=gB/gA':>10}")
    print(f"{'실측 (2kg 분동 교정)':<26}{gA_m:10.4f}{'기준':>10}{gB_m:10.4f}{'기준':>10}"
          f"{gB_m/gA_m:10.4f}")
    for lab, kw in (("트윈 현행 p24", dict()), ("트윈 +thigh 1.05", dict(mthigh=1.05)),
                    ("트윈 +CoM CAD 0.053", dict(mthigh=1.05, comz=0.053)),
                    ("트윈 +CoM 0.073", dict(mthigh=1.05, comz=0.073))):
        ft = twin(**kw); gA, gB = grav(ft)
        print(f"{lab:<26}{gA:10.4f}{100*(gA/gA_m-1):+9.1f}%{gB:10.4f}"
              f"{100*(gB/gB_m-1):+9.1f}%{gB/gA:10.4f}")
    nc = json.load(io.open(HERE / "_G3_nocurrent.json", encoding="utf-8"))
    print(f"{'무동력 평형 (독립 측정)':<26}{'-':>10}{'-':>10}{'-':>10}{'-':>10}{nc['rho']:10.4f}")

    # ── ③ a_hat 재해석: 26_08_02 동정값 보정 ──
    print("\n" + "=" * 108)
    print("③ a_hat 척도 보정을 26_08_02 공중 동정에 되먹임")
    S = json.load(io.open(HERE / "_G2_air_ident.json", encoding="utf-8"))
    th2 = dict(zip(S["names"], S["theta"]))
    f_h = OUT["nm_per_raw_ch1"] / 0.68207          # a_hat 선형게인 대비 배율
    print(f"   보정계수 = (실측 {OUT['nm_per_raw_ch1']:.4f} Nm/raw) / (a_hat 0.6821) = **{f_h:.3f}배**")
    ftw = twin(); gAt, gBt = grav(ftw)
    import mujoco, numpy as _np
    from _G2_air_twin import pose, Q1_0
    m = ftw["model"]
    def m11(q2d):
        md = pose(ftw, Q1_0, _np.radians(q2d)); M = _np.zeros((m.nv, m.nv))
        mujoco.mj_fullM(m, M, md.qM); dh = ftw["dof"]["hip_m"]; return float(M[dh, dh])
    print(f"{'항목':<22}{'a_hat 기준':>12}{'×보정':>12}{'트윈 p24':>12}{'트윈/보정실측':>14}")
    for nm, val, tw in (("Is1r [kg·m²]", th2["Is1r"], None), ("Kv [kg·m²]", th2["Kv"], None),
                        ("Is2 [kg·m²]", th2["Is2"], None)):
        pass
    c = [np.cos(np.radians(q)) for q in (-110, -85, -62)]
    X = np.column_stack([np.ones(3), 2 * np.array(c)])
    kk, *_ = np.linalg.lstsq(X, np.array([m11(q) for q in (-110, -85, -62)]), rcond=None)
    for nm, val, twv in (("Is1r [kg·m²]", th2["Is1r"], kk[0]), ("Kv [kg·m²]", th2["Kv"], kk[1]),
                         ("gA [Nm]", th2["gA"], gAt), ("gB [Nm]", th2["gB"], gBt)):
        print(f"{nm:<22}{val:12.5f}{val*f_h:12.5f}{twv:12.5f}{twv/(val*f_h):14.3f}")
    print(f"   ※ 관성은 토크/가속도라 척도가 그대로 곱해진다. gA 는 본 실험이 직접 준 "
          f"{gA_m:.4f} 가 정본 (위 ×보정 {th2['gA']*f_h:.4f} 와 대조)")

    # ── ④ 고토크 외삽 경고 ──
    print("\n" + "=" * 108)
    print("④ ★ 적용 범위 경고 — 본 교정은 **저토크 구간에서만** 검증됐다")
    print(f"   교정 구간: |raw| ≲ 7 (2kg 실행 최대 6.75)")
    print(f"   점프 세션 실측 |raw| 최대: 0324 hip 13.8 / knee 18.8 · 0602 21.9 / 35.5 · "
          f"0724 37.8 / 28.0")
    print(f"   교정 척도를 그대로 외삽하면 raw 37.8 = {37.8*OUT['nm_per_raw_ch1']:.1f} Nm — "
          f"AK80-9(GR9·KT0.091)로는 {37.8*OUT['nm_per_raw_ch1']/(9*0.091):.0f} A 가 필요해 비현실적.")
    print(f"   a_hat 기준이면 raw 37.8 = {37.8*0.68207:.1f} Nm ({37.8*0.68207/(9*0.091):.0f} A) — 현실적.")
    print(f"   ⇒ **raw→토크 관계가 강한 포화 비선형**이라는 뜻. 저토크에서 {1/0.68207*OUT['nm_per_raw_ch1']:.2f}배,")
    print(f"      고토크에서 ~1배로 수렴하는 형태가 두 관측을 동시에 만족한다.")
    print(f"      → 판정: **H1은 저토크 구간에서 확정, 고토크 구간은 미검증** (차기 실험 필요)")

    json.dump(OUT, io.open(HERE / "_G3_absolute.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G3_absolute.json")


if __name__ == "__main__":
    main()
