# -*- coding: utf-8 -*-
"""_G2_air_diag — 26_08_02 데이터 무결성 진단 (회귀 전 필수 관문).

① 시간 결손(dt 튐) 전수 — 수치미분·필터가 균일 dt를 가정하므로 치명적
② 명령 구간 분해 (dqd==0 = hold 마커) → 설계된 8개 가진 구간과 대조
③ 이상 trial 판별 (명령 대비 실제 범위 폭주)
④ 각 가진 구간의 실제 진폭·주파수·토크 진폭 = 무엇이 실제로 여기됐나
원본 읽기 전용.
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
FS = 500.0
# 설계 (make_sysid_air.py) — 순서대로
DESIGN = [("힙 1Hz 12°", 1.0, 12.0, "hip"), ("힙 1Hz 6°", 1.0, 6.0, "hip"),
          ("힙 2Hz 12°", 2.0, 12.0, "hip"), ("힙 3Hz 8°", 3.0, 8.0, "hip"),
          ("무릎 2Hz 8°", 2.0, 8.0, "knee"), ("무릎 3Hz 5°", 3.0, 5.0, "knee")]


def trials():
    out = []
    for g in sorted(p for p in SESS.iterdir() if p.is_dir()):
        for t in sorted(p for p in g.iterdir() if p.is_dir()):
            if (t / "hip.xlsx").exists():
                out.append(t)
    return out


def load(fold):
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    d = dict(t=np.array(h["Time"].to_numpy(float)[:n], dtype=float, copy=True))
    d["t"] -= d["t"][0]
    for tag, s in (("1", h), ("2", k)):
        d["q" + tag] = s["currentAngle"].to_numpy(float)[:n]
        d["qd" + tag] = s["desiredAngle"].to_numpy(float)[:n]
        d["dq" + tag] = s["currentAngleVelocity"].to_numpy(float)[:n]
        d["dqd" + tag] = s["desiredAngleVelocity"].to_numpy(float)[:n]
        d["raw" + tag] = s["currentTorque"].to_numpy(float)[:n]
    d["n"] = n
    return d


def segments(d):
    """명령 속도가 0이 아닌 연속 덩어리 = 가진 구간. 0.5s 미만은 ramp 잡음으로 버림."""
    act = (np.abs(d["dqd1"]) > 1e-9) | (np.abs(d["dqd2"]) > 1e-9)
    idx = np.flatnonzero(np.diff(act.astype(int)))
    edges = np.concatenate([[0], idx + 1, [len(act)]])
    segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        if act[a] and (b - a) >= int(0.5 * FS):
            segs.append((a, b))
    return segs


def main():
    T = trials()

    print("=" * 112)
    print("① 시간 결손 (dt ≠ 2ms 인 샘플) — 균일 dt 가정의 유효성")
    print(f"{'게인폴더':<16}{'trial':<20}{'N':>6}{'결손수':>7}{'최대 dt[ms]':>12}{'누락 표본':>10}{'위치(초)':>28}")
    for t in T:
        d = load(t)
        dt = np.diff(d["t"])
        bad = np.flatnonzero(np.abs(dt - 0.002) > 1e-6)
        miss = int(round(np.sum(dt[bad]) / 0.002 - len(bad))) if len(bad) else 0
        loc = ", ".join(f"{d['t'][i]:.1f}" for i in bad[:5]) + ("..." if len(bad) > 5 else "")
        print(f"{t.parent.name:<16}{t.name:<20}{d['n']:6d}{len(bad):7d}"
              f"{(dt.max()*1000):12.1f}{miss:10d}{loc:>28}")

    print("\n" + "=" * 112)
    print("② 명령 구간 분해 — 설계는 가진 6구간 (힙4 + 무릎2) + 앞뒤 ramp 2")
    for t in T:
        d = load(t)
        segs = segments(d)
        print(f"\n{t.parent.name} / {t.name}  → 구간 {len(segs)}개")
        print(f"   {'#':<3}{'구간[s]':>14}{'길이':>7} | {'qd1 진폭°':>10}{'q1 진폭°':>10}"
              f"{'qd2 진폭°':>10}{'q2 진폭°':>10} | {'주파수Hz':>9} | {'|τ1|max':>8}{'|τ2|max':>8}")
        for i, (a, b) in enumerate(segs):
            sl = slice(a, b)
            A1 = np.ptp(np.degrees(d["qd1"][sl])) / 2
            B1 = np.ptp(np.degrees(d["q1"][sl])) / 2
            A2 = np.ptp(np.degrees(d["qd2"][sl])) / 2
            B2 = np.ptp(np.degrees(d["q2"][sl])) / 2
            # 주파수 = 지배 채널의 영교차 수
            ch = d["dqd1"][sl] if A1 > A2 else d["dqd2"][sl]
            zc = np.sum(np.diff(np.sign(ch - ch.mean())) != 0)
            dur = (b - a) / FS
            f = zc / 2.0 / dur
            a1 = ahat_np(d["raw1"][sl], d["dq1"][sl])
            a2 = ahat_np(d["raw2"][sl], d["dq2"][sl])
            print(f"   {i:<3}{f'{a/FS:.1f}~{b/FS:.1f}':>14}{dur:7.1f} | {A1:10.2f}{B1:10.2f}"
                  f"{A2:10.2f}{B2:10.2f} | {f:9.2f} | {np.abs(a1).max():8.2f}{np.abs(a2).max():8.2f}")


if __name__ == "__main__":
    main()
