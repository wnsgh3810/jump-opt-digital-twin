# -*- coding: utf-8 -*-
"""_G4_linearity — 26_08_07 **4kg 추가 실행**: 토크 척도의 선형성 판정 (G3 의 최대 미결).

G3 결론: 저토크(|raw| ≲ 7)에서 1 raw ≈ 1.14~1.31 Nm — a_hat(0.682)의 1.7~1.9배.
G3 미결: 점프는 raw 37.8 까지 간다. 그 척도를 외삽하면 46.8 Nm(57A)로 비현실적
         → raw↔토크가 **포화 비선형**일 가능성. 저토크 교정만으론 못 가른다.

4kg 실행이 결정적인 이유 — **교정이 전혀 필요 없는 순수 비율 시험**
  추 하중이 정확히 2배면, 추가 만드는 raw 증가분도 **정확히 2배**여야 한다 (선형이면).
      R(q) ≡ [raw_4kg(q) − raw_0kg(q)] / [raw_2kg(q) − raw_0kg(q)]
  R = 2.000 → 선형 (G3 척도가 고토크까지 유효)
  R < 2     → 포화 (고토크에서 Nm/raw 가 커진다 = a_hat 쪽으로 수렴)
  R > 2     → 팽창
  이 비율은 **Nm/raw 값을 몰라도** 계산된다. 분동 두 개의 질량비만 알면 된다.

마찰은 G3 과 동일하게 **방향평균**(0.04Hz 왕복의 상행·하행)으로 소거한다.
CLI: python _G4_linearity.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
from _G3_scale import load, hip_segments, q2_on, SESS, G, L1, L2   # noqa: E402

LOADS = [("0kg", 0.0, ["probe_sweep_v1", "probe_sweep_v1 - 2"]),
         ("2kg", 2.0, ["probe_sweep_v1"]),
         ("4kg", 4.0, ["probe_sweep_v1"])]


def ksegs(d):
    """무릎 전용 스윕 (힙 완전 고정) — gB·척도 교차검증에 최적."""
    mov = (np.abs(d["dq2"]) > 0.03) & (np.abs(d["dq1"]) < 0.02)
    ix = np.flatnonzero(np.diff(mov.astype(int)))
    ed = np.concatenate([[0], ix + 1, [len(mov)]])
    return [(a, b) for a, b in zip(ed[:-1], ed[1:]) if mov[a] and (b - a) > int(8.0 * 500)]


def davg(d, segs, grid, key, on="q1"):
    up, dn = [], []
    v_key = "dq1" if on == "q1" else "dq2"
    for a, b in segs:
        q = d[on][a:b]; y = d[key][a:b]; v = d[v_key][a:b]
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


def main():
    D = {}
    for tag, m, names in LOADS:
        D[tag] = [load(SESS / tag / n) for n in names]
    print("=" * 112)
    print("① 무결성 — 4kg 실행이 다른 실행과 같은 궤적인가")
    print(f"{'하중':<6}{'실행':<22}{'표본':>8}{'길이s':>7}{'q1 범위[°]':>17}{'q2 범위[°]':>17}"
          f"{'raw1 범위':>16}{'raw2 범위':>16}")
    for tag, m, names in LOADS:
        for n, d in zip(names, D[tag]):
            print(f"{tag:<6}{n:<22}{len(d['q1']):8d}{d['t'][-1]-d['t'][0]:7.1f}"
                  f"[{np.degrees(d['q1']).min():+6.1f},{np.degrees(d['q1']).max():+6.1f}]"
                  f"[{np.degrees(d['q2']).min():+7.1f},{np.degrees(d['q2']).max():+6.1f}]"
                  f"[{d['raw1'].min():+6.2f},{d['raw1'].max():+6.2f}]"
                  f"[{d['raw2'].min():+6.2f},{d['raw2'].max():+6.2f}]")

    # ── ② 순수 비율 시험 (교정 불필요) ──
    S = {tag: [hip_segments(d) for d in D[tag]] for tag, _, _ in LOADS}
    keys = sorted(set(S["4kg"][0]) & set(S["2kg"][0]) & set(S["0kg"][0]) & set(S["0kg"][1]))
    print("\n" + "=" * 112)
    print("② ★ 순수 비율 시험 — R = Δraw(4kg) / Δraw(2kg).  선형이면 정확히 2.000")
    print("   (Nm/raw 값을 전혀 쓰지 않는다. 분동 질량비 2:1 만 쓴다.)")
    rows = []
    for k_ in keys:
        lo = max(np.degrees(D["4kg"][0]["q1"][a:b]).min() for a, b in S["4kg"][0][k_])
        hi = min(np.degrees(D["4kg"][0]["q1"][a:b]).max() for a, b in S["4kg"][0][k_])
        grid = np.radians(np.linspace(lo + 1.5, hi - 1.5, 60))
        q2g = q2_on(D["4kg"][0], S["4kg"][0][k_], grid)
        lev1 = L1 * np.cos(grid) + L2 * np.cos(grid + q2g)
        lev2 = L2 * np.cos(grid + q2g)
        print(f"\n  ── 무릎 q2 ≈ {k_:+d}° ──")
        print(f"{'q1[°]':>7}{'힙지레mm':>10} | {'Δraw1(2kg)':>11}{'Δraw1(4kg)':>11}{'R1':>7}"
              f" | {'Δraw2(2kg)':>11}{'Δraw2(4kg)':>11}{'R2':>7}")
        for ch, key in ((1, "raw1"), (2, "raw2")):
            y0 = np.nanmean([davg(d, s[k_], grid, key) for d, s in zip(D["0kg"], S["0kg"])], 0)
            y2 = davg(D["2kg"][0], S["2kg"][0][k_], grid, key)
            y4 = davg(D["4kg"][0], S["4kg"][0][k_], grid, key)
            for i in range(len(grid)):
                rows.append(dict(ch=ch, q2key=k_, q1=grid[i], lev=(lev1 if ch == 1 else lev2)[i],
                                 d2=y2[i] - y0[i], d4=y4[i] - y0[i]))
        for i in range(0, len(grid), 7):
            r1 = [r for r in rows if r["ch"] == 1 and r["q2key"] == k_][i]
            r2 = [r for r in rows if r["ch"] == 2 and r["q2key"] == k_][i]
            R1 = r1["d4"] / r1["d2"] if abs(r1["d2"]) > 0.4 else np.nan
            R2 = r2["d4"] / r2["d2"] if abs(r2["d2"]) > 0.4 else np.nan
            print(f"{np.degrees(grid[i]):7.1f}{1000*lev1[i]:10.1f} | {r1['d2']:11.3f}{r1['d4']:11.3f}"
                  f"{R1:7.3f} | {r2['d2']:11.3f}{r2['d4']:11.3f}{R2:7.3f}")

    print("\n" + "=" * 112)
    print("③ 전역 비율 (원점 통과 회귀: Δraw4 = R · Δraw2)")
    for ch, lab in ((1, "힙"), (2, "무릎")):
        A = np.array([[r["d2"], r["d4"]] for r in rows
                      if r["ch"] == ch and np.isfinite(r["d2"]) and np.isfinite(r["d4"])])
        R = float(A[:, 0] @ A[:, 1] / (A[:, 0] @ A[:, 0]))
        res = A[:, 1] - R * A[:, 0]
        print(f"   {lab}: R = {R:.4f}   잔차 RMS {np.sqrt(np.mean(res**2)):.4f} raw / "
              f"Δraw4 폭 {np.ptp(A[:,1]):.2f} raw   → 선형이면 2.000")
        # 구간별
        q = np.percentile(np.abs(A[:, 0]), [0, 25, 50, 75, 100])
        print(f"      {'|Δraw2| 구간':>18}{'표본':>7}{'R':>9}")
        for a, b in zip(q[:-1], q[1:]):
            m = (np.abs(A[:, 0]) >= a) & (np.abs(A[:, 0]) <= b)
            if m.sum() < 5:
                continue
            print(f"      {f'{a:6.2f} ~ {b:6.2f}':>18}{int(m.sum()):7d}"
                  f"{float(A[m,0] @ A[m,1] / (A[m,0] @ A[m,0])):9.3f}")

    # ── ④ 하중별 척도 ──
    print("\n" + "=" * 112)
    print("④ 하중별 척도 [Nm/raw] — 선형이면 두 하중에서 같아야 한다")
    print(f"{'채널':<6}{'하중':<6}{'Δraw / Δτ_참 [raw/Nm]':>24}{'1 raw = ? Nm':>15}{'a_hat 대비':>11}")
    OUT = {}
    for ch in (1, 2):
        A = np.array([[r["lev"], r["d2"], r["d4"]] for r in rows
                      if r["ch"] == ch and np.isfinite(r["d2"]) and np.isfinite(r["d4"])])
        for mi, (mass, col) in enumerate(((2.0, 1), (4.0, 2))):
            p = mass * G * A[:, 0]
            s = float(p @ A[:, col] / (p @ p))
            OUT[f"ch{ch}_{mass:.0f}kg"] = 1 / s
            print(f"{'힙' if ch==1 else '무릎':<6}{mass:.0f}kg{'':2}{s:24.4f}{1/s:15.4f}"
                  f"{(1/s)/0.68207:11.3f}")

    # ── ⑤ 무릎 전용 스윕에서도 동일 검사 ──
    print("\n" + "=" * 112)
    print("⑤ 무릎 전용 스윕(힙 완전 고정)에서의 교차 검증")
    KS = {tag: [ksegs(d) for d in D[tag]] for tag, _, _ in LOADS}
    grid = np.radians(np.linspace(-113, -59, 80))
    q1f = float(np.mean([np.mean(D["4kg"][0]["q1"][a:b]) for a, b in KS["4kg"][0]]))
    c12 = np.cos(q1f + grid)
    print(f"   힙 고정각 (4kg) = {np.degrees(q1f):.2f}°   cos(q1+q2) 변화폭 {np.ptp(c12):.3f}")
    print(f"{'채널':<6}{'하중':<6}{'추항 계수[raw]':>16}{'물리 M·g·L2[Nm]':>17}{'1 raw = ? Nm':>15}{'a_hat 대비':>11}")
    for ch, key in ((1, "raw1"), (2, "raw2")):
        y0 = np.nanmean([davg(d, s, grid, key, "q2") for d, s in zip(D["0kg"], KS["0kg"])], 0)
        b0 = np.linalg.lstsq(np.column_stack([c12, np.ones(len(grid))])[np.isfinite(y0)],
                             y0[np.isfinite(y0)], rcond=None)[0]
        for tag, mass in (("2kg", 2.0), ("4kg", 4.0)):
            yy = davg(D[tag][0], KS[tag][0], grid, key, "q2")
            m = np.isfinite(yy)
            bb = np.linalg.lstsq(np.column_stack([c12[m], np.ones(m.sum())]), yy[m], rcond=None)[0]
            phys = mass * G * L2
            s = (bb[0] - b0[0]) / phys
            print(f"{'힙' if ch==1 else '무릎':<6}{tag:<6}{bb[0]-b0[0]:16.4f}{phys:17.4f}"
                  f"{1/s:15.4f}{(1/s)/0.68207:11.3f}")

    json.dump(OUT, io.open(HERE / "_G4_linearity.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G4_linearity.json")


if __name__ == "__main__":
    main()
