# -*- coding: utf-8 -*-
"""_G3_probe_explore — 26_08_07 판별 실험 원본 재판독 (분석 전 무결성 확인).

구성: 0kg × {sweep, sweep-2, hold3, hold3-2} · 2kg × {sweep, hold3} · no_current(무동력 평형)
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

SESS = FD.ROOT / "26_08_07"


def runs():
    out = []
    for grp in ("0kg", "2kg"):
        for d in sorted((SESS / grp).iterdir()):
            if d.is_dir() and (d / "hip.xlsx").exists():
                out.append((grp, d.name, d))
    if (SESS / "no_current" / "hip.xlsx").exists():
        out.append(("no_current", "-", SESS / "no_current"))
    return out


def load(fold):
    h = pd.read_excel(fold / "hip.xlsx"); k = pd.read_excel(fold / "knee.xlsx")
    n = min(len(h), len(k))
    t = np.array(h["Time"].to_numpy(float)[:n], float, copy=True); t -= t[0]
    d = dict(t=t, n=n, cols=list(h.columns))
    for tag, s in (("1", h), ("2", k)):
        for src, dst in (("currentAngle", "q"), ("desiredAngle", "qd"),
                         ("currentAngleVelocity", "dq"), ("desiredAngleVelocity", "dqd"),
                         ("currentTorque", "raw"), ("desiredTorque", "tdes")):
            if src in s.columns:
                d[dst + tag] = s[src].to_numpy(float)[:n]
    d["a1"] = ahat_np(d["raw1"], d["dq1"])
    d["a2"] = ahat_np(d["raw2"], d["dq2"])
    return d


def main():
    R = runs()
    print(f"세션 {SESS}\n")
    print("=" * 122)
    print("① 기본 제원")
    print(f"{'그룹':<11}{'실행':<22}{'N':>7}{'길이s':>8}{'dt결손':>7} | "
          f"{'q1 범위[°]':>18}{'q2 범위[°]':>18} | {'raw1 범위':>16}{'raw2 범위':>16}")
    D = {}
    for grp, nm, fold in R:
        d = load(fold); D[(grp, nm)] = d
        dt = np.diff(d["t"])
        bad = int(np.sum(np.abs(dt - 0.002) > 1e-6))
        q1 = np.degrees(d["q1"]); q2 = np.degrees(d["q2"])
        print(f"{grp:<11}{nm:<22}{d['n']:7d}{d['t'][-1]:8.1f}{bad:7d} | "
              f"[{q1.min():+7.1f},{q1.max():+7.1f}][{q2.min():+7.1f},{q2.max():+7.1f}] | "
              f"[{d['raw1'].min():+6.2f},{d['raw1'].max():+6.2f}][{d['raw2'].min():+6.2f},{d['raw2'].max():+6.2f}]")

    print("\n" + "=" * 122)
    print("② 명령 채널 유무 (무동력이면 명령/토크가 0 또는 정지)")
    print(f"{'그룹':<11}{'실행':<22}{'qd1 p-p°':>10}{'qd2 p-p°':>10}{'|dq1|max':>10}"
          f"{'|dq2|max':>10}{'tdes1 p-p':>11}{'tdes2 p-p':>11}")
    for (grp, nm), d in D.items():
        print(f"{grp:<11}{nm:<22}{np.ptp(np.degrees(d['qd1'])):10.2f}"
              f"{np.ptp(np.degrees(d['qd2'])):10.2f}{np.abs(d['dq1']).max():10.2f}"
              f"{np.abs(d['dq2']).max():10.2f}"
              f"{np.ptp(d['tdes1']) if 'tdes1' in d else float('nan'):11.3f}"
              f"{np.ptp(d['tdes2']) if 'tdes2' in d else float('nan'):11.3f}")

    print("\n" + "=" * 122)
    print("③ no_current — 시간에 따른 q1·q2 (10초 간격 스냅샷, 정지 구간 탐색용)")
    d = D[("no_current", "-")]
    step = int(len(d["t"]) / 40) or 1
    print(f"{'t[s]':>7}{'q1[°]':>9}{'q2[°]':>9}{'|dq1|':>8}{'|dq2|':>8}{'raw1':>8}{'raw2':>8}")
    for i in range(0, len(d["t"]), step):
        print(f"{d['t'][i]:7.1f}{np.degrees(d['q1'][i]):9.2f}{np.degrees(d['q2'][i]):9.2f}"
              f"{abs(d['dq1'][i]):8.2f}{abs(d['dq2'][i]):8.2f}{d['raw1'][i]:8.2f}{d['raw2'][i]:8.2f}")


if __name__ == "__main__":
    main()
