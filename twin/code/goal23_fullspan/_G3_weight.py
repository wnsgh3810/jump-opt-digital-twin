# -*- coding: utf-8 -*-
"""_G3_weight — 26_08_07 **2kg 분동 토크 척도 판별** (H1 vs H2 본선).

실험: 2kg **분동**(정확) 에 실을 묶어 발끝 홀(**무릎축에서 250mm**, 사용자 확인)에 연결.
      probe_sweep_v1 / probe_hold3_v2 를 0kg(각 2회 = 앞뒤 샌드위치) · 2kg(각 1회) 실행.

핵심 아이디어: 추의 토크는 **정확히 계산된다**.
  Δτ1 = M·g·(L1·cos q1 + L2·cos(q1+q2))      ← 발끝의 힙축 기준 **수평** 거리
  Δτ2 = M·g·(L2·cos(q1+q2))                  ← 발끝의 무릎축 기준 수평 거리
실이라 힘이 정확히 수직이므로 지레팔 = 수평거리로 확정된다 (추의 형상·자세 무관).

판정: 측정 Δτ / 계산 Δτ = **k**
  k ≈ 1.00 → 토크 척도 정상 → **H2**(트윈 질량분포 오류) 확정
  k ≈ 0.585 → **H1**(a_hat 게인 1.71배 과소) 확정
  그 사이 → 혼합. (0.585 = 1/1.711, G2-G의 트윈/실측 배율)

주의: 추의 토크는 다리 자체 중력과 **함수형이 같다**(둘 다 cos q1, cos(q1+q2)).
      따라서 한 실행 안에서는 분리 불가 — **0kg/2kg 실행 대조(load 지시자)만이** 분리한다.
      드리프트 흡수를 위해 **오프셋은 실행별로 따로** 둔다 (앞뒤 0kg 샌드위치가 이를 검증).
관성 기여는 0.014 Nm 이하(0.04Hz 준정적)라 무시.
CLI: python _G3_weight.py
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
from _G2_air_fit import ahat               # noqa: E402  (평활 부호판 a_hat)

SESS = FD.ROOT / "26_08_07"
FS, DT = 500.0, 1.0 / 500.0
M_W, G = 2.0, 9.81          # 분동 질량 [kg] · 중력
L1, L2 = 0.25, 0.250        # thigh · 무릎축~발끝 홀 (사용자 실측 확인)
K_H1 = 1.0 / 1.711          # H1 이 맞을 때 나와야 할 k


def lpf(x, fc=5.0, order=4):
    b, a = butter(order, fc / (FS / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


def runs():
    out = []
    for grp, load in (("0kg", 0.0), ("2kg", 1.0)):
        for d in sorted((SESS / grp).iterdir()):
            if d.is_dir() and (d / "hip.xlsx").exists():
                out.append(dict(grp=grp, name=d.name, load=load, path=d,
                                kind="sweep" if "sweep" in d.name else "hold3"))
    return out


def load(r):
    h = pd.read_excel(r["path"] / "hip.xlsx"); k = pd.read_excel(r["path"] / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    tu = np.arange(0.0, t[-1] + 1e-9, DT)
    gv = lambda s, c: np.interp(tu, t, s[c].to_numpy(float)[:n])
    q1 = lpf(gv(h, "currentAngle")); q2 = lpf(gv(k, "currentAngle"))
    v1 = lpf(gv(h, "currentAngleVelocity")); v2 = lpf(gv(k, "currentAngleVelocity"))
    t1 = lpf(ahat(gv(h, "currentTorque"), v1, "smooth"))
    t2 = lpf(ahat(gv(k, "currentTorque"), v2, "smooth"))
    e = 400
    s = slice(e, len(tu) - e)
    d = dict(q1=q1[s], q2=q2[s], dq1=v1[s], dq2=v2[s], t1=t1[s], t2=t2[s], t=tu[s])
    d.update({kk: r[kk] for kk in ("grp", "name", "load", "kind")})
    d["lev1"] = L1 * np.cos(d["q1"]) + L2 * np.cos(d["q1"] + d["q2"])   # 힙축 기준 수평거리
    d["lev2"] = L2 * np.cos(d["q1"] + d["q2"])                          # 무릎축 기준
    return d


def joint_fit(DS, ch):
    """전 실행 동시 적합. 미지수 = [gA, gB, k, fv, fc] + 실행별 오프셋.
    ch=1: τ1 = gA c1 + gB c12 + k·M·g·lev1·load + fv·dq1 + fc·tanh(dq1/0.3) + off_run
    ch=2: τ2 =        gB c12 + k·M·g·lev2·load + fv·dq2 + fc·tanh(dq2/0.3) + off_run"""
    nr = len(DS)
    base = 5 if ch == 1 else 4
    X, y, meta = [], [], []
    for i, d in enumerate(DS):
        n = len(d["q1"])
        c1 = np.cos(d["q1"]); c12 = np.cos(d["q1"] + d["q2"])
        v = d["dq1"] if ch == 1 else d["dq2"]
        A = np.zeros((n, base + nr))
        if ch == 1:
            A[:, 0] = c1; A[:, 1] = c12
            A[:, 2] = d["load"] * M_W * G * d["lev1"]
            A[:, 3] = v; A[:, 4] = np.tanh(v / 0.3)
        else:
            A[:, 0] = c12
            A[:, 1] = d["load"] * M_W * G * d["lev2"]
            A[:, 2] = v; A[:, 3] = np.tanh(v / 0.3)
        A[:, base + i] = 1.0
        X.append(A); y.append(d["t1"] if ch == 1 else d["t2"])
        meta += [i] * n
    X = np.vstack(X); y = np.concatenate(y); meta = np.array(meta)
    th, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ th
    return th, X, y, r, meta, base


def boot_k(DS, ch, nb=400, seed=3):
    """실행 단위가 아닌 **시간 블록** 부트스트랩 (잔차 자기상관 대응)."""
    rng = np.random.default_rng(seed)
    th0, X, y, r, meta, base = joint_fit(DS, ch)
    ki = 2 if ch == 1 else 1
    n = len(y); blk = 2000
    out = []
    for _ in range(nb):
        starts = rng.integers(0, n - blk, n // blk)
        idx = np.concatenate([np.arange(s, s + blk) for s in starts])
        try:
            t, *_ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
            out.append(t[ki])
        except Exception:
            pass
    return float(th0[ki]), np.percentile(out, [2.5, 97.5]), float(np.std(out))


def main():
    R = runs()
    DS = [load(r) for r in R]
    print("=" * 112)
    print("① 실행 목록 및 추 지레팔 실현 범위 (실측 각도 기준)")
    print(f"{'그룹':<6}{'실행':<22}{'종류':<7}{'표본':>7}{'q1 범위[°]':>17}{'q2 범위[°]':>17}"
          f"{'힙 지레[mm]':>17}{'계산 Δτ1[Nm]':>15}")
    for d in DS:
        print(f"{d['grp']:<6}{d['name']:<22}{d['kind']:<7}{len(d['q1']):7d}"
              f"[{np.degrees(d['q1']).min():+6.1f},{np.degrees(d['q1']).max():+6.1f}]"
              f"[{np.degrees(d['q2']).min():+7.1f},{np.degrees(d['q2']).max():+6.1f}]"
              f"[{1000*d['lev1'].min():+7.1f},{1000*d['lev1'].max():+7.1f}]"
              f"[{M_W*G*d['lev1'].min():+6.2f},{M_W*G*d['lev1'].max():+6.2f}]")

    # ── ② 가장 투명한 판정: hold3 자세별 직접 차분 ──
    print("\n" + "=" * 112)
    print("② 직접 차분 판정 (hold3 유지구간) — 양방향 접근 평균으로 정지마찰 소거")
    h0 = [d for d in DS if d["kind"] == "hold3" and d["load"] == 0]
    h2 = [d for d in DS if d["kind"] == "hold3" and d["load"] == 1]
    # 유지 구간 = |dq1|,|dq2| < 0.02 이 0.5s 이상
    def holds(d):
        st = (np.abs(d["dq1"]) < 0.02) & (np.abs(d["dq2"]) < 0.02)
        ix = np.flatnonzero(np.diff(st.astype(int)))
        ed = np.concatenate([[0], ix + 1, [len(st)]])
        out = []
        for a, b in zip(ed[:-1], ed[1:]):
            if st[a] and (b - a) > int(0.5 * FS):
                s = slice(a + (b - a) // 3, b)
                out.append(dict(q1=float(np.mean(d["q1"][s])), q2=float(np.mean(d["q2"][s])),
                                t1=float(np.mean(d["t1"][s])), t2=float(np.mean(d["t2"][s])),
                                lev1=float(np.mean(d["lev1"][s])), lev2=float(np.mean(d["lev2"][s])),
                                n=b - a))
        return out
    print(f"{'자세':<6}{'접근':<6} | {'0kg q1[°]':>10}{'τ1':>8}{'τ2':>8} | {'2kg q1[°]':>10}{'τ1':>8}{'τ2':>8}"
          f" | {'Δτ1 실측':>9}{'Δτ1 계산':>9}{'k1':>7} | {'Δτ2 실측':>9}{'Δτ2 계산':>9}{'k2':>7}")
    A0 = holds(h0[0]); A2 = holds(h2[0])
    K1, K2 = [], []
    npair = min(len(A0), len(A2))
    for i in range(npair):
        a, b = A0[i], A2[i]
        d1 = b["t1"] - a["t1"]; p1 = M_W * G * b["lev1"]
        d2 = b["t2"] - a["t2"]; p2 = M_W * G * b["lev2"]
        K1.append(d1 / p1 if abs(p1) > 0.4 else np.nan)
        K2.append(d2 / p2 if abs(p2) > 0.4 else np.nan)
        print(f"{'P'+str(i//2+1):<6}{'+↓' if i % 2 == 0 else '−↑':<6} | "
              f"{np.degrees(a['q1']):10.2f}{a['t1']:8.3f}{a['t2']:8.3f} | "
              f"{np.degrees(b['q1']):10.2f}{b['t1']:8.3f}{b['t2']:8.3f} | "
              f"{d1:9.3f}{p1:9.3f}{K1[-1]:7.3f} | {d2:9.3f}{p2:9.3f}{K2[-1]:7.3f}")
    print(f"   → k1 (힙) 중앙값 {np.nanmedian(K1):.3f} · k2 (무릎) 중앙값 {np.nanmedian(K2):.3f}")

    # ── ③ 전 실행 동시 적합 ──
    print("\n" + "=" * 112)
    print("③ 전 실행 동시 적합 (실행별 오프셋 자유 = 드리프트 흡수)")
    for ch in (1, 2):
        th, X, y, r, meta, base = joint_fit(DS, ch)
        k, ci, sd = boot_k(DS, ch)
        nm = ["gA", "gB", "k", "fv1", "fc1"] if ch == 1 else ["gB", "k", "fv2", "fc2"]
        print(f"\n  [τ{ch}]  RMS 잔차 {np.sqrt(np.mean(r**2)):.4f} Nm · "
              f"설명력 {1-np.var(r)/np.var(y):.4f}")
        for j, n2 in enumerate(nm):
            print(f"    {n2:<5} {th[j]:+10.5f}" + (f"   95%[{ci[0]:.4f}, {ci[1]:.4f}]" if n2 == "k" else ""))
        print(f"    실행별 오프셋: " + " ".join(f"{DS[i]['grp']}/{DS[i]['kind']}{'' if DS[i]['name'][-1] not in '2' else '·2'}"
                                             f"={th[base+i]:+.3f}" for i in range(len(DS))))
        print(f"    ★ k = {k:.4f}  →  H2(척도 정상)면 1.000 · H1(a_hat 1.71배 과소)면 {K_H1:.3f}")
        print(f"       판정: {'H2 (토크 척도 정상)' if abs(k-1) < abs(k-K_H1) else 'H1 (a_hat 게인 오류)'}"
              f"  · 1.000 에서 {100*(k-1):+.1f}% · {K_H1:.3f} 에서 {100*(k/K_H1-1):+.1f}%")

    # ── ④ 선형성: 토크 크기별 k ──
    print("\n" + "=" * 112)
    print("④ 척도의 선형성 — 계산 Δτ1 크기별로 k 를 따로 본다 (sweep, 표본 수만 개)")
    s0 = [d for d in DS if d["kind"] == "sweep" and d["load"] == 0]
    s2 = [d for d in DS if d["kind"] == "sweep" and d["load"] == 1][0]
    # 0kg 기준선을 (q1,q2) 격자로 보간: 2차원이라 스윕 구간별 1차원 보간
    print(f"{'계산 Δτ1 구간[Nm]':>18}{'표본':>8}{'실측 Δτ1 평균':>14}{'k':>8}")
    th, X, y, r, meta, base = joint_fit(DS, 1)
    gA, gB, kk = th[0], th[1], th[2]
    d = s2
    pred_leg = gA * np.cos(d["q1"]) + gB * np.cos(d["q1"] + d["q2"]) + \
        th[3] * d["dq1"] + th[4] * np.tanh(d["dq1"] / 0.3) + th[base + DS.index(d)]
    meas_dt = d["t1"] - pred_leg
    calc_dt = M_W * G * d["lev1"]
    for lo, hi in ((-3, -1), (-1, 0), (0, 1), (1, 2.5), (2.5, 4), (4, 6)):
        m = (calc_dt >= lo) & (calc_dt < hi)
        if m.sum() < 200:
            continue
        print(f"{f'{lo:+.1f} ~ {hi:+.1f}':>18}{int(m.sum()):8d}{meas_dt[m].mean():14.3f}"
              f"{meas_dt[m].mean()/calc_dt[m].mean():8.3f}")

    json.dump(dict(k_hip=float(joint_fit(DS, 1)[0][2]), k_knee=float(joint_fit(DS, 2)[0][1]),
                   k1_direct=float(np.nanmedian(K1)), k2_direct=float(np.nanmedian(K2))),
              io.open(HERE / "_G3_weight.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G3_weight.json")


if __name__ == "__main__":
    main()
