# -*- coding: utf-8 -*-
"""_F_majump — ModeA(제어기 없는 측정토크 재생) 점프높이 판정 (사용자 요청 08-02).

CL 점프높이는 PD+지지층이 개입해 '모델이 맞나'를 못 가린다. ModeA는 측정 토크만 주입하므로
**플랜트 물리만으로 결정되는 높이** — 에너지 회계의 가장 직접적인 심판.
h = max(smoothed d(bz)/dt)² / 2g. 창 = 점프창(plot_window), 실측 앵커 1회.
CLI: FS_MASS=... python _F_majump.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
import fs_runner as FR

JH = safe.read_json(HERE / "_D_jumph.json")


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    rows = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m)); t = tt[m] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            dt = float(np.median(np.diff(L["t"])))
            v = np.convolve(np.gradient(L["bz"], dt), np.ones(5) / 5, mode="same")
            h = max(float(v.max()), 0.0) ** 2 / (2 * 9.81) * 100
            jh = JH.get(f"{s}/{p.name}", {}).get("h_cm")
            if jh:
                rows.setdefault(s, []).append((h, jh))
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print(f"\n{'세션':<10} {'n':>3} {'ModeA h[cm]':>12} {'실측 h[cm]':>11} {'Δ':>8} {'비율':>7}")
    ds, hs, ms = [], [], []
    for s in sorted(rows):
        a = np.array(rows[s])
        hm, hr = float(np.median(a[:, 0])), float(np.median(a[:, 1]))
        ds.append(abs(hm - hr)); hs.append(hm); ms.append(hr)
        print(f"{s:<10} {len(a):3d} {hm:12.1f} {hr:11.1f} {hm-hr:+8.1f} {hm/hr:7.2f}")
    print(f"{'평균':<10} {'':>3} {np.mean(hs):12.1f} {np.mean(ms):11.1f} {np.mean(hs)-np.mean(ms):+8.1f} "
          f"{np.mean(hs)/np.mean(ms):7.2f}   |Δh| 평균 {np.mean(ds):.2f}cm")


if __name__ == "__main__":
    main()
