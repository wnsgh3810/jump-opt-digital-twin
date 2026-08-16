# -*- coding: utf-8 -*-
"""_G3_scale — 26_08_07 토크 척도 k 의 **투명 판정 + 대안 가설 배제**.

_G3_weight 의 동시적합이 k≈0.55 를 냈으나, 그 적합은 마찰항(fv·fc)이 저속에서 공선이라
값이 폭주했다(fv1=4.95). 여기서는 **마찰을 적합하지 않고 소거**한다.

방법 — 방향평균(direction averaging)
  스윕은 0.04Hz 왕복이라 같은 각도를 **올라가며 한 번, 내려가며 한 번** 지난다.
  쿨롱 마찰은 방향에 따라 부호만 바뀌므로  τ↑(q) + τ↓(q) 의 **평균에서 정확히 소거**된다.
  점성도 |dq| 가 같고 부호만 반대라 함께 소거. 관성은 0.014Nm 이하로 무시.
  ⇒ 남는 것은 **순수 중력 + 추** 뿐이다.
  k(q1) = [τ̄_2kg(q1) − τ̄_0kg(q1)] / [M·g·지레팔(q1)]  ← 각도마다 하나씩, 곡선으로 나온다.

배제해야 할 대안 (k≈0.55 가 a_hat 게인 오류가 아닐 가능성)
  A. 추가 완전히 매달리지 않음(바닥/구조물 접촉) → k 가 **발끝 높이에 의존**할 것
  B. 지레팔 L2 가 250mm 가 아님 → 힙/무릎 두 채널의 k 가 **서로 달라야** 함 (의존형태가 다름)
  C. 베이스 기울어짐/엔드스톱 → k 가 **자세에 의존**할 것
  D. a_hat 비선형 → k 가 **토크 크기에 의존**할 것
  전부 k 의 **의존성 검사**로 판별한다. 전 구간 k 가 일정하면 **공통 척도 오차**만 남는다.
CLI: python _G3_scale.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                       # noqa: E402
from _G2_air_fit import ahat               # noqa: E402

SESS = FD.ROOT / "26_08_07"
FS, DT = 500.0, 1.0 / 500.0
M_W, G = 2.0, 9.81
L1, L2 = 0.25, 0.250


def lpf(x, fc=3.0, order=4):
    b, a = butter(order, fc / (FS / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


def load(path):
    h = pd.read_excel(path / "hip.xlsx"); k = pd.read_excel(path / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    tu = np.arange(0.0, t[-1] + 1e-9, DT)
    gv = lambda s, c: np.interp(tu, t, s[c].to_numpy(float)[:n])
    q1 = lpf(gv(h, "currentAngle")); q2 = lpf(gv(k, "currentAngle"))
    v1 = np.gradient(q1, DT); v2 = np.gradient(q2, DT)
    r1 = gv(h, "currentTorque"); r2 = gv(k, "currentTorque")
    t1 = lpf(ahat(r1, lpf(gv(h, "currentAngleVelocity")), "smooth"))
    t2 = lpf(ahat(r2, lpf(gv(k, "currentAngleVelocity")), "smooth"))
    s = slice(400, len(tu) - 400)
    return dict(t=tu[s], q1=q1[s], q2=q2[s], dq1=v1[s], dq2=v2[s],
                t1=t1[s], t2=t2[s], raw1=lpf(r1)[s], raw2=lpf(r2)[s])


def hip_segments(d):
    """힙만 움직이는 스윕 구간을 무릎 자세별로 묶는다."""
    mov = (np.abs(d["dq1"]) > 0.02) & (np.abs(d["dq2"]) < 0.01)
    ix = np.flatnonzero(np.diff(mov.astype(int)))
    ed = np.concatenate([[0], ix + 1, [len(mov)]])
    segs = []
    for a, b in zip(ed[:-1], ed[1:]):
        if mov[a] and (b - a) > int(3.0 * FS):
            segs.append((a, b, float(np.mean(d["q2"][a:b]))))
    # 무릎 자세로 그룹화
    out = {}
    for a, b, q2m in segs:
        key = round(np.degrees(q2m) / 10) * 10
        out.setdefault(key, []).append((a, b))
    return out


def dir_avg(d, seg_list, grid, ch):
    """구간들을 방향별로 나눠 q1 격자에 보간 후 **상행/하행 평균** = 마찰 소거."""
    up, dn = [], []
    key = "t1" if ch == 1 else "t2"
    for a, b in seg_list:
        q = d["q1"][a:b]; y = d[key][a:b]; v = d["dq1"][a:b]
        for mask, box in ((v > 0.02, up), (v < -0.02, dn)):
            if mask.sum() < 200:
                continue
            qq, yy = q[mask], y[mask]
            o = np.argsort(qq)
            qq, yy = qq[o], yy[o]
            uq, inv = np.unique(np.round(qq, 5), return_inverse=True)
            uy = np.bincount(inv, yy) / np.bincount(inv)
            box.append(np.interp(grid, uq, uy, left=np.nan, right=np.nan))
    if not up or not dn:
        return None
    U = np.nanmean(np.array(up), 0); D = np.nanmean(np.array(dn), 0)
    return 0.5 * (U + D)


def q2_on(d, seg_list, grid):
    qs, ys = [], []
    for a, b in seg_list:
        qs.append(d["q1"][a:b]); ys.append(d["q2"][a:b])
    q = np.concatenate(qs); y = np.concatenate(ys)
    o = np.argsort(q)
    uq, inv = np.unique(np.round(q[o], 5), return_inverse=True)
    uy = np.bincount(inv, y[o]) / np.bincount(inv)
    return np.interp(grid, uq, uy, left=np.nan, right=np.nan)


def main():
    D0 = [load(SESS / "0kg" / n) for n in ("probe_sweep_v1", "probe_sweep_v1 - 2")]
    D2 = load(SESS / "2kg" / "probe_sweep_v1")
    S0 = [hip_segments(d) for d in D0]
    S2 = hip_segments(D2)
    keys = sorted(set(S2) & set(S0[0]) & set(S0[1]))
    print("=" * 112)
    print("① 힙 스윕 구간 (무릎 자세별) — 상행/하행 각각 존재해야 마찰이 소거된다")
    for k_ in keys:
        print(f"   q2≈{k_:+4d}° : 0kg {len(S0[0][k_])}+{len(S0[1][k_])} 구간 · 2kg {len(S2[k_])} 구간")

    rows = []
    print("\n" + "=" * 112)
    print("② k(q1) 곡선 — 마찰 소거 후 (추 토크 실측 ÷ 계산)")
    for k_ in keys:
        lo = max(np.degrees(D2["q1"][a:b]).min() for a, b in S2[k_])
        hi = min(np.degrees(D2["q1"][a:b]).max() for a, b in S2[k_])
        grid = np.radians(np.linspace(lo + 1.5, hi - 1.5, 60))
        y2 = dir_avg(D2, S2[k_], grid, 1)
        y0 = np.nanmean([dir_avg(d, s[k_], grid, 1) for d, s in zip(D0, S0)], 0)
        r2 = dir_avg(D2, S2[k_], grid, 2)
        r0 = np.nanmean([dir_avg(d, s[k_], grid, 2) for d, s in zip(D0, S0)], 0)
        q2g = q2_on(D2, S2[k_], grid)
        lev1 = L1 * np.cos(grid) + L2 * np.cos(grid + q2g)
        lev2 = L2 * np.cos(grid + q2g)
        fz = L1 * np.sin(grid) + L2 * np.sin(grid + q2g)
        print(f"\n  ── 무릎 q2 ≈ {k_:+d}° ──")
        print(f"{'q1[°]':>8}{'발끝높이mm':>11}{'힙지레mm':>10}{'계산Δτ1':>9}{'실측Δτ1':>9}{'k1':>7}"
              f" | {'무릎지레mm':>11}{'계산Δτ2':>9}{'실측Δτ2':>9}{'k2':>7}")
        for i in range(0, len(grid), 6):
            p1 = M_W * G * lev1[i]; m1 = y2[i] - y0[i]
            p2 = M_W * G * lev2[i]; m2 = r2[i] - r0[i]
            k1 = m1 / p1 if abs(p1) > 0.5 else np.nan
            k2 = m2 / p2 if abs(p2) > 0.5 else np.nan
            print(f"{np.degrees(grid[i]):8.1f}{1000*fz[i]:11.1f}{1000*lev1[i]:10.1f}{p1:9.3f}"
                  f"{m1:9.3f}{k1:7.3f} | {1000*lev2[i]:11.1f}{p2:9.3f}{m2:9.3f}{k2:7.3f}")
        for i in range(len(grid)):
            rows.append(dict(q2key=k_, q1=grid[i], fz=fz[i], lev1=lev1[i], lev2=lev2[i],
                             m1=y2[i] - y0[i], m2=r2[i] - r0[i]))

    # ── 전역 기울기 (원점 통과 회귀) ──
    R = [r for r in rows if np.isfinite(r["m1"]) and np.isfinite(r["m2"])]
    p1 = np.array([M_W * G * r["lev1"] for r in R]); m1 = np.array([r["m1"] for r in R])
    p2 = np.array([M_W * G * r["lev2"] for r in R]); m2 = np.array([r["m2"] for r in R])
    k1 = float(p1 @ m1 / (p1 @ p1)); k2 = float(p2 @ m2 / (p2 @ p2))
    r1 = m1 - k1 * p1; r2v = m2 - k2 * p2
    print("\n" + "=" * 112)
    print("③ 전역 기울기 (원점 통과 최소제곱)")
    print(f"   힙  k1 = {k1:.4f}   잔차 RMS {np.sqrt(np.mean(r1**2)):.4f} Nm / 신호폭 {np.ptp(p1):.2f} Nm")
    print(f"   무릎 k2 = {k2:.4f}   잔차 RMS {np.sqrt(np.mean(r2v**2)):.4f} Nm / 신호폭 {np.ptp(p2):.2f} Nm")
    print(f"   → H2(척도 정상)=1.000 · H1(a_hat 1.711배 과소)=0.584")
    print(f"   → 함의: 참 토크 = a_hat × {1/k1:.3f} (힙) / × {1/k2:.3f} (무릎)")

    # ── ④ 대안 배제: k 의 의존성 검사 ──
    print("\n" + "=" * 112)
    print("④ 대안 가설 배제 — k 가 무엇에 의존하는가 (일정하면 '공통 척도 오차'만 남는다)")
    def bins(vals, lab, unit, nb=5):
        v = np.array(vals)
        qs = np.percentile(v, np.linspace(0, 100, nb + 1))
        print(f"\n   [{lab}]")
        print(f"{'구간':>22}{'표본':>7}{'k1':>9}{'k2':>9}")
        for a, b in zip(qs[:-1], qs[1:]):
            m = (v >= a) & (v <= b) & (np.abs(p1) > 0.5)
            if m.sum() < 5:
                continue
            kk1 = float(p1[m] @ m1[m] / (p1[m] @ p1[m]))
            mm = (v >= a) & (v <= b) & (np.abs(p2) > 0.5)
            kk2 = float(p2[mm] @ m2[mm] / (p2[mm] @ p2[mm])) if mm.sum() > 5 else np.nan
            print(f"{f'{a:8.1f} ~ {b:8.1f}':>22}{int(m.sum()):7d}{kk1:9.3f}{kk2:9.3f}")
        print(f"      ({unit})")
    bins([1000 * r["fz"] for r in R], "A. 발끝 높이 (추 접촉 여부)", "mm, 힙축 기준")
    bins([abs(M_W * G * r["lev1"]) for r in R], "D. 추 토크 크기 (비선형)", "Nm")
    bins([np.degrees(r["q1"]) for r in R], "C. 힙 자세 (엔드스톱·기울어짐)", "deg")

    # ── ⑤ 대안 B: 지레팔 L2 가 틀렸다면? ──
    print("\n" + "=" * 112)
    print("⑤ 대안 B 배제 — 'L2(무릎~발끝)가 250mm가 아니다'로 설명되는가")
    best = None
    for L2t in np.arange(0.05, 0.40, 0.002):
        lv1 = np.array([L1 * np.cos(r["q1"]) + L2t * np.cos(r["q1"] + (np.arctan2(
            np.sin(r["q1"] + 0), np.cos(r["q1"] + 0)) * 0 + 1) * 0) for r in R])  # placeholder
        break
    q1a = np.array([r["q1"] for r in R])
    q12 = np.array([np.arccos(np.clip((r["lev2"]) / L2, -1, 1)) * np.sign(1) for r in R])
    # lev2 = L2 cos(q1+q2) → cos(q1+q2) = lev2/L2 (기존 L2로 복원)
    c12 = np.array([r["lev2"] / L2 for r in R])
    c1 = np.cos(q1a)
    print(f"{'가정 L2[mm]':>12}{'힙 k1':>9}{'무릎 k2':>9}{'두 채널 불일치':>14}")
    for L2t in (0.10, 0.1375, 0.15, 0.20, 0.250, 0.30):
        pa = M_W * G * (L1 * c1 + L2t * c12)
        pb = M_W * G * (L2t * c12)
        ka = float(pa @ m1 / (pa @ pa)); kb = float(pb @ m2 / (pb @ pb))
        print(f"{1000*L2t:12.1f}{ka:9.3f}{kb:9.3f}{abs(ka-kb):14.3f}")
    print("   → 어떤 L2 를 넣어도 두 채널의 k 를 동시에 1.0 으로 만들 수 없으면 대안 B 기각")

    # ── ⑥ raw 단위 직결 (a_hat 을 아예 쓰지 않는 판정) ──
    print("\n" + "=" * 112)
    print("⑥ a_hat 을 **전혀 쓰지 않는** 판정 — raw 단위로 직접 회귀")
    rw = []
    for k_ in keys:
        lo = max(np.degrees(D2["q1"][a:b]).min() for a, b in S2[k_])
        hi = min(np.degrees(D2["q1"][a:b]).max() for a, b in S2[k_])
        grid = np.radians(np.linspace(lo + 1.5, hi - 1.5, 60))
        for ch, key in ((1, "raw1"), (2, "raw2")):
            pass
        def davg(d, segs, key):
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
            return 0.5 * (np.nanmean(np.array(up), 0) + np.nanmean(np.array(dn), 0)) if up and dn else None
        q2g = q2_on(D2, S2[k_], grid)
        lev1 = L1 * np.cos(grid) + L2 * np.cos(grid + q2g)
        lev2 = L2 * np.cos(grid + q2g)
        d1 = davg(D2, S2[k_], "raw1") - np.nanmean([davg(d, s[k_], "raw1") for d, s in zip(D0, S0)], 0)
        d2 = davg(D2, S2[k_], "raw2") - np.nanmean([davg(d, s[k_], "raw2") for d, s in zip(D0, S0)], 0)
        for i in range(len(grid)):
            rw.append((M_W * G * lev1[i], d1[i], M_W * G * lev2[i], d2[i]))
    A = np.array([r for r in rw if np.all(np.isfinite(r))])
    s1 = float(A[:, 0] @ A[:, 1] / (A[:, 0] @ A[:, 0]))
    s2 = float(A[:, 2] @ A[:, 3] / (A[:, 2] @ A[:, 2]))
    print(f"   힙  : Δraw / Δτ_참 = {s1:.4f} raw/Nm  →  **1 raw = {1/s1:.4f} Nm**")
    print(f"   무릎 : Δraw / Δτ_참 = {s2:.4f} raw/Nm  →  **1 raw = {1/s2:.4f} Nm**")
    print(f"   a_hat 의 선형 게인 = A0·CF = 1.15605×0.59 = {1.15605*0.59:.4f} Nm/raw")
    print(f"   → 실측/a_hat = {(1/s1)/(1.15605*0.59):.3f} (힙) · {(1/s2)/(1.15605*0.59):.3f} (무릎)")

    json.dump(dict(k1=k1, k2=k2, nm_per_raw_hip=1 / s1, nm_per_raw_knee=1 / s2,
                   ahat_linear_gain=1.15605 * 0.59),
              io.open(HERE / "_G3_scale.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G3_scale.json")


if __name__ == "__main__":
    main()
