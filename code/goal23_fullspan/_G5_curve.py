# -*- coding: utf-8 -*-
"""_G5_curve — **raw→토크 정본 곡선**: 26_06_01 로드셀(모양) + 26_08_07 분동(크기) 결합.

두 데이터의 성격이 정확히 상보적이다.
  · **26_06_01** (사용자 벤치, 0.5m 팔 + 로드셀): raw **1.5~36 전 구간**을 덮지만
    GRF 채널은 데이터 사전에 **"0602 이전 오프셋·기울기 캘리브 오류"**로 등재 → **절대값 불신**.
    그러나 **모양(휘어짐)** 은 유효하다.
  · **26_08_07** (2kg·4kg **분동**): 질량이 정확해 **절대 크기는 확실**하지만 raw ≤ 11.5 만 덮는다.
⇒ 로드셀을 `LC = α·τ + β` (α=미지 기울기오차, β=미지 오프셋+관절마찰) 로 두고
  **겹치는 구간(raw ≤ 11.5)에서 α·β 를 분동에 맞춰 고정**한 뒤, raw > 11.5 를 로드셀로 확장.
  → 외삽이 아니라 **실측으로 이어붙인** 곡선이 된다.

곡선 형태: raw = d1·τ + d2·τ² (+d3·τ³ 선택) — d2>0 이면 고토크에서 raw 과대판독(포화).
CLI: python _G5_curve.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                   # noqa: E402
from _G3_scale import load, hip_segments, q2_on, SESS, G, L1, L2   # noqa: E402
from _G4_linearity import ksegs, davg                  # noqa: E402

BENCH = FD.ROOT / "26_06_01"
CLIP = 35.0            # 이 위는 명령 클립(raw≈35.96)이라 raw 가 상수 → 곡선 적합서 제외
LOADS = [("0kg", 0.0, ["probe_sweep_v1", "probe_sweep_v1 - 2"]),
         ("2kg", 2.0, ["probe_sweep_v1"]), ("4kg", 4.0, ["probe_sweep_v1"])]


def ahat_lin(raw):
    Iq = 0.7204 * np.asarray(raw, float)
    return 1.15605 * 0.59 * raw - 4.17389589e-4 * 9 * np.abs(Iq) * Iq \
        - 0.26855607 - 0.04904241 * np.abs(Iq)


def bench():
    d = pd.read_csv(BENCH / "steady_state_torque_summary.csv")
    return d["motor_mean"].to_numpy(float), d["loadcell_mean"].to_numpy(float), \
        d["level"].to_numpy(float), d["loadcell_std_raw"].to_numpy(float)


def probe():
    D = {t: [load(SESS / t / n) for n in ns] for t, m, ns in LOADS}
    S = {t: [hip_segments(x) for x in D[t]] for t, m, ns in LOADS}
    K = {t: [ksegs(x) for x in D[t]] for t, m, ns in LOADS}
    R, ri = [], 0
    for t, m, ns in LOADS:
        for j, d in enumerate(D[t]):
            for k_ in S[t][j]:
                lo = max(np.degrees(d["q1"][a:b]).min() for a, b in S[t][j][k_])
                hi = min(np.degrees(d["q1"][a:b]).max() for a, b in S[t][j][k_])
                g = np.radians(np.linspace(lo + 1.5, hi - 1.5, 60))
                q2g = q2_on(d, S[t][j][k_], g)
                y = davg(d, S[t][j][k_], g, "raw1")
                for i in range(len(g)):
                    if np.isfinite(y[i]):
                        R.append(dict(run=ri, mass=m, q1=g[i], q2=q2g[i], y=y[i]))
            if K[t][j]:
                g = np.radians(np.linspace(-113, -59, 80))
                q1f = float(np.mean([np.mean(d["q1"][a:b]) for a, b in K[t][j]]))
                y = davg(d, K[t][j], g, "raw1", "q2")
                for i in range(len(g)):
                    if np.isfinite(y[i]):
                        R.append(dict(run=ri, mass=m, q1=q1f, q2=g[i], y=y[i]))
            ri += 1
    return R, ri


def main():
    rm, lc, lv, ls = bench()
    R, NR = probe()
    yv = np.array([r["y"] for r in R]); mass = np.array([r["mass"] for r in R])
    runi = np.array([r["run"] for r in R])
    c1 = np.cos([r["q1"] for r in R]); c12 = np.cos([r["q1"] + r["q2"] for r in R])
    lev = L1 * c1 + L2 * c12
    ok = rm < CLIP

    print("=" * 112)
    print("① 26_06_01 벤치 원본 (0.5m 팔 + 로드셀, 정적 스텝)")
    print(f"{'명령 P':>8}{'모터 raw':>10}{'로드셀 τ[Nm]':>14}{'로드셀/raw':>11}"
          f"{'a_hat[Nm]':>11}{'속도[rad/s]':>12}{'':>6}")
    for i in range(len(rm)):
        print(f"{lv[i]:8.3f}{rm[i]:10.3f}{lc[i]:14.3f}{lc[i]/rm[i]:11.3f}"
              f"{ahat_lin(rm[i]):11.3f}{pd.read_csv(BENCH/'steady_state_torque_summary.csv')['vel_abs_mean'][i]:12.3f}"
              f"{'  ←클립' if rm[i]>=CLIP else '':>6}")
    print(f"   ★ 로드셀/raw 가 저raw 1.02 → raw13 근처 1.16 → raw22 에서 1.00 → raw36 에서 0.80")
    print(f"     = **raw 22 부근에서 raw=Nm 교차, 그 위로 raw 과대판독** (사용자 관찰 18~20 과 정합)")

    # ── ② 결합 적합 ──
    def curve_raw(tau, p):          # raw = d1 τ + d2 τ|τ| + d3 τ³
        d1, d2, d3 = p
        return d1 * tau + d2 * tau * np.abs(tau) + d3 * tau ** 3

    def curve_tau(raw, p, lo=-60, hi=60):
        t = np.asarray(raw, float) / max(p[0], 1e-6)
        for _ in range(80):
            f = curve_raw(t, p) - raw
            df = p[0] + 2 * p[1] * np.abs(t) + 3 * p[2] * t ** 2
            t = t - f / np.where(np.abs(df) < 1e-9, 1e-9, df)
        return t

    def resid(x, wB, cubic):
        d1, d2, d3 = x[0], x[1], (x[2] if cubic else 0.0)
        gA, gB = x[3], x[4]; off = x[5:5 + NR]; al, be = x[5 + NR], x[6 + NR]
        p = (d1, d2, d3)
        tau = gA * c1 + gB * c12 + mass * G * lev + off[runi]
        rA = curve_raw(tau, p) - yv
        tb = curve_tau(rm[ok], p)
        rB = (al * tb + be - lc[ok]) * wB
        return np.concatenate([rA, rB])

    print("\n" + "=" * 112)
    print("② 결합 적합 — 로드셀은 모양만(α·τ+β 로 자유), 절대 크기는 분동이 고정")
    OUT = {}
    for cubic in (False, True):
        wB = np.sqrt(len(yv) / max(ok.sum(), 1)) * 0.7      # 두 블록 영향력 균형
        x0 = np.concatenate([[0.80, 0.01, 0.0, 1.5, 0.05], np.zeros(NR), [1.0, 0.0]])
        sol = least_squares(lambda x: resid(x, wB, cubic), x0, method="lm", max_nfev=200000)
        d1, d2, d3 = sol.x[0], sol.x[1], (sol.x[2] if cubic else 0.0)
        gA, al, be = sol.x[3], sol.x[5 + NR], sol.x[6 + NR]
        p = (d1, d2, d3)
        rA = curve_raw(gA * c1 + sol.x[4] * c12 + mass * G * lev + sol.x[5:5 + NR][runi], p) - yv
        tb = curve_tau(rm[ok], p)
        rB = al * tb + be - lc[ok]
        print(f"   [{'2차' if not cubic else '3차'}] d1={d1:.4f} d2={d2:+.6f} d3={d3:+.8f}"
              f" | gA={gA:.4f} Nm | 로드셀 보정 α={al:.4f} β={be:+.4f}")
        print(f"        분동 잔차 {np.sqrt(np.mean(rA**2)):.4f} raw · 로드셀 잔차 "
              f"{np.sqrt(np.mean(rB**2)):.4f} Nm (신호 {lc[ok].max():.1f} Nm)")
        OUT["cubic" if cubic else "quad"] = dict(d1=float(d1), d2=float(d2), d3=float(d3),
                                                 gA=float(gA), alpha=float(al), beta=float(be))
        if cubic:
            P = p

    # ── ③ 정본 곡선표 ──
    print("\n" + "=" * 112)
    print("③ ★ 정본 환산표  τ(raw)  — 분동으로 크기 고정 + 로드셀로 raw 36 까지 실측 연결")
    print(f"{'raw':>7}{'τ 정본[Nm]':>12}{'τ/raw':>8}{'a_hat[Nm]':>11}{'정본/a_hat':>11}"
          f"{'로드셀(보정)':>13}{'':>8}")
    for raw in (1, 2, 3, 5, 8, 11.5, 15, 18, 20, 22, 25, 28, 30, 32, 35.5):
        t = float(curve_tau(np.array([raw]), P)[0])
        a = float(ahat_lin(raw))
        near = np.argmin(np.abs(rm[ok] - raw))
        lcc = (lc[ok][near] - OUT["cubic"]["beta"]) / OUT["cubic"]["alpha"] if abs(rm[ok][near] - raw) < 2.5 else np.nan
        tag = "교정" if raw <= 11.5 else ("로드셀" if raw <= 32 else "클립부근")
        print(f"{raw:7.1f}{t:12.3f}{t/raw:8.3f}{a:11.3f}{t/a:11.3f}"
              f"{lcc:13.3f}{tag:>8}")
    OUT["table_note"] = "raw<=11.5 분동 교정 · 11.5~32 로드셀 실측 · >32 클립"
    json.dump(OUT, io.open(HERE / "_G5_curve.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G5_curve.json")


if __name__ == "__main__":
    main()
