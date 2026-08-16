# -*- coding: utf-8 -*-
"""_GHQ_inspect5 — 일어서기 전 구간 기록에서 '떠 있는 구간'(z>0.10)이 어디인지·몇 번인지."""
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench")); os.chdir(HERE)
import numpy as np
import fs_data as FD
from _GHC_s2s_updown import load_full, pick_tau

for sub, pay, cvt in FD.S2S_CASES:
    dw = FD.load_s2s(sub)
    raw = load_full(sub)
    d, pick = pick_tau(sub, raw, dw)
    t = d["t"]
    z = -0.25 * (np.sin(d["q1"]) + np.sin(d["q1"] + d["q2"]))
    ok = z > FD.S2S_ZMIN
    # 연속 구간
    e = np.diff(ok.astype(np.int8)); st = list(np.nonzero(e == 1)[0] + 1)
    if ok[0]:
        st = [0] + st
    segs = []
    for a in st:
        b = a + int(np.argmax(~ok[a:])) if (~ok[a:]).any() else len(ok)
        if (b - a) * 0.002 > 0.2:
            segs.append((float(t[a]), float(t[b - 1])))
    print(f"{sub:15s} z범위 {z.min():.3f}~{z.max():.3f} m · z>0.10 비율 {100*ok.mean():.1f}% · "
          f"구간 {len(segs)}개")
    print(f"    구간: " + " ".join(f"[{a:.1f}~{b:.1f}]" for a, b in segs[:12]))
    print(f"    정본 창(절대시간) {dw['t_abs'][0]:.2f}~{dw['t_abs'][-1]:.2f}")
    # 움직임 구간 (크랭크 |v|>0.2) 이 z>0.10 안에 얼마나 들어오나
    dq = FD._smooth(np.nan_to_num(d["dq2"]), 11)
    mv = np.abs(dq) > 0.2
    print(f"    크랭크 |v|>0.2 인 시간 {0.002*mv.sum():.1f}s 중 z>0.10 인 것 {0.002*(mv&ok).sum():.1f}s "
          f"(올라감 {0.002*((dq>0.2)&ok).sum():.1f}s · 내려감 {0.002*((dq<-0.2)&ok).sum():.1f}s)")
    # z 문턱을 낮추면?
    for zz in (0.05, 0.0, -1.0):
        o2 = z > zz
        print(f"      z>{zz:+.2f}: 움직임과 겹침 {0.002*(mv&o2).sum():5.1f}s "
              f"(올라감 {0.002*((dq>0.2)&o2).sum():5.1f} · 내려감 {0.002*((dq<-0.2)&o2).sum():5.1f})")
    print()
