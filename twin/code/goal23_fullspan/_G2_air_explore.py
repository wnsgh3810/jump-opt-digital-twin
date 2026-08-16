# -*- coding: utf-8 -*-
"""_G2_air_explore — 26_08_02 공중 동정 실험 **원본 재판독** (마라톤G 재시작).

목적: 회귀·모형을 걸기 **전에** 원본이 실제로 무엇을 담고 있는지만 본다.
  ① 채널/샘플링/구간  ② 가진 진폭·주파수 (힙/무릎 각각)  ③ raw 토크 범위·랩 흔적
  ④ 명령(qd) vs 실제(q) 관계 = 실효 게인·스큐  ⑤ 정지 구간 유무(오프셋 앵커 후보)
원본 읽기 전용. 출력은 표로만.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
from sea_twin2 import ahat_np          # noqa: E402
import fs_data as FD                   # noqa: E402

SESS = FD.ROOT / "26_08_02"


def trials():
    out = []
    for g in sorted(p for p in SESS.iterdir() if p.is_dir()):
        for t in sorted(p for p in g.iterdir() if p.is_dir()):
            if (t / "hip.xlsx").exists():
                out.append(t)
    return out


def raw(fold):
    h = pd.read_excel(fold / "hip.xlsx")
    k = pd.read_excel(fold / "knee.xlsx")
    return h, k


def dom_freq(x, fs):
    """DC 제거 후 지배 주파수 [Hz] 와 그 성분의 진폭 비중."""
    y = np.asarray(x, float) - np.mean(x)
    w = np.hanning(len(y))
    F = np.abs(np.fft.rfft(y * w))
    f = np.fft.rfftfreq(len(y), 1.0 / fs)
    F[0] = 0.0
    i = int(np.argmax(F))
    return f[i], float(F[i] / max(F.sum(), 1e-12))


def main():
    T = trials()
    print(f"세션: {SESS}   trial {len(T)}개\n")

    h0, k0 = raw(T[0])
    print("[열 목록] hip.xlsx :", list(h0.columns))
    print("          knee.xlsx:", list(k0.columns))
    dt = np.diff(h0["Time"].to_numpy(float))
    print(f"[샘플링] dt 중앙값 {np.median(dt)*1000:.3f} ms  (min {dt.min()*1000:.3f} / "
          f"max {dt.max()*1000:.3f})  → {1/np.median(dt):.1f} Hz\n")

    print("=" * 118)
    print("① 구간·가진 (원본 그대로, 필터 없음)")
    print(f"{'게인폴더':<16}{'trial':<20}{'N':>6}{'dur[s]':>8} | "
          f"{'q1범위[°]':>16}{'p-p':>7}{'f[Hz]':>7} | {'q2범위[°]':>16}{'p-p':>7}{'f[Hz]':>7}")
    for t in T:
        h, k = raw(t)
        n = min(len(h), len(k))
        tt = h["Time"].to_numpy(float)[:n]
        fs = 1.0 / np.median(np.diff(tt))
        q1 = np.degrees(h["currentAngle"].to_numpy(float)[:n])
        q2 = np.degrees(k["currentAngle"].to_numpy(float)[:n])
        f1, _ = dom_freq(q1, fs)
        f2, _ = dom_freq(q2, fs)
        print(f"{t.parent.name:<16}{t.name:<20}{n:6d}{tt[-1]-tt[0]:8.2f} | "
              f"[{q1.min():+7.1f},{q1.max():+7.1f}]{np.ptp(q1):7.1f}{f1:7.2f} | "
              f"[{q2.min():+7.1f},{q2.max():+7.1f}]{np.ptp(q2):7.1f}{f2:7.2f}")

    print("\n" + "=" * 118)
    print("② 명령(desired) vs 실제(current) — 가진이 어디에 걸렸나")
    print(f"{'게인폴더':<16}{'trial':<20} | {'qd1 p-p':>9}{'q1 p-p':>9}{'추종비':>7} | "
          f"{'qd2 p-p':>9}{'q2 p-p':>9}{'추종비':>7} | {'dqd1 p-p':>9}{'dqd2 p-p':>9}")
    for t in T:
        h, k = raw(t)
        n = min(len(h), len(k))
        a = np.ptp(np.degrees(h["desiredAngle"].to_numpy(float)[:n]))
        b = np.ptp(np.degrees(h["currentAngle"].to_numpy(float)[:n]))
        c = np.ptp(np.degrees(k["desiredAngle"].to_numpy(float)[:n]))
        d = np.ptp(np.degrees(k["currentAngle"].to_numpy(float)[:n]))
        e = np.ptp(h["desiredAngleVelocity"].to_numpy(float)[:n])
        f = np.ptp(k["desiredAngleVelocity"].to_numpy(float)[:n])
        print(f"{t.parent.name:<16}{t.name:<20} | {a:9.2f}{b:9.2f}{b/max(a,1e-9):7.3f} | "
              f"{c:9.2f}{d:9.2f}{d/max(c,1e-9):7.3f} | {e:9.2f}{f:9.2f}")

    print("\n" + "=" * 118)
    print("③ 토크 채널 (raw iTM 원본 · a_hat 변환 축토크 Nm · 기록된 명령토크)")
    print(f"{'게인폴더':<16}{'trial':<20} | {'raw1 범위':>17}{'τ1[Nm]범위':>17} | "
          f"{'raw2 범위':>17}{'τ2[Nm]범위':>17} | {'tdes1 p-p':>10}{'tdes2 p-p':>10}")
    for t in T:
        h, k = raw(t)
        n = min(len(h), len(k))
        r1 = h["currentTorque"].to_numpy(float)[:n]
        r2 = k["currentTorque"].to_numpy(float)[:n]
        v1 = h["currentAngleVelocity"].to_numpy(float)[:n]
        v2 = k["currentAngleVelocity"].to_numpy(float)[:n]
        a1 = ahat_np(r1, v1)
        a2 = ahat_np(r2, v2)
        d1 = h["desiredTorque"].to_numpy(float)[:n]
        d2 = k["desiredTorque"].to_numpy(float)[:n]
        print(f"{t.parent.name:<16}{t.name:<20} | "
              f"[{r1.min():+7.2f},{r1.max():+7.2f}][{a1.min():+7.2f},{a1.max():+7.2f}] | "
              f"[{r2.min():+7.2f},{r2.max():+7.2f}][{a2.min():+7.2f},{a2.max():+7.2f}] | "
              f"{np.ptp(d1):10.3f}{np.ptp(d2):10.3f}")

    print("\n" + "=" * 118)
    print("④ 속도 채널 무결성 — 차분(q)과 기록 dq의 일치 (스케일 검증)")
    print(f"{'게인폴더':<16}{'trial':<20} | {'힙 비율':>8}{'상관':>7} | {'무릎 비율':>9}{'상관':>7}")
    for t in T:
        h, k = raw(t)
        n = min(len(h), len(k))
        tt = h["Time"].to_numpy(float)[:n]
        d = np.median(np.diff(tt))
        for lab, src in (("", h), ("", k)):
            pass
        row = []
        for src in (h, k):
            q = src["currentAngle"].to_numpy(float)[:n]
            v = src["currentAngleVelocity"].to_numpy(float)[:n]
            fd = np.gradient(q, d)
            ok = np.isfinite(fd) & np.isfinite(v)
            sc = float(np.dot(fd[ok], v[ok]) / max(np.dot(v[ok], v[ok]), 1e-12))
            cc = float(np.corrcoef(fd[ok], v[ok])[0, 1])
            row += [sc, cc]
        print(f"{t.parent.name:<16}{t.name:<20} | {row[0]:8.3f}{row[1]:7.3f} | {row[2]:9.3f}{row[3]:7.3f}")

    print("\n" + "=" * 118)
    print("⑤ 정지(무가진) 구간 탐색 — |dq1|,|dq2| < 0.05 rad/s 가 연속 0.2s 이상")
    print(f"{'게인폴더':<16}{'trial':<20} | {'정지표본':>8}{'비율%':>7} | "
          f"{'정지구간 q1[°]':>14}{'q2[°]':>9} | {'raw1 평균':>9}{'raw2 평균':>9}")
    for t in T:
        h, k = raw(t)
        n = min(len(h), len(k))
        v1 = h["currentAngleVelocity"].to_numpy(float)[:n]
        v2 = k["currentAngleVelocity"].to_numpy(float)[:n]
        still = (np.abs(v1) < 0.05) & (np.abs(v2) < 0.05)
        q1 = np.degrees(h["currentAngle"].to_numpy(float)[:n])
        q2 = np.degrees(k["currentAngle"].to_numpy(float)[:n])
        r1 = h["currentTorque"].to_numpy(float)[:n]
        r2 = k["currentTorque"].to_numpy(float)[:n]
        ns = int(still.sum())
        if ns:
            print(f"{t.parent.name:<16}{t.name:<20} | {ns:8d}{100*ns/n:7.1f} | "
                  f"{q1[still].mean():14.1f}{q2[still].mean():9.1f} | "
                  f"{r1[still].mean():9.3f}{r2[still].mean():9.3f}")
        else:
            print(f"{t.parent.name:<16}{t.name:<20} | {0:8d}{0.0:7.1f} | {'-':>14}{'-':>9} | {'-':>9}{'-':>9}")


if __name__ == "__main__":
    main()
