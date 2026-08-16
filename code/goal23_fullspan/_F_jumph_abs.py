# -*- coding: utf-8 -*-
"""_F_jumph_abs — 점프높이 정본 측정: **지면 기준 베이스 중심의 최고 높이** (사용자 정의 확인 08-02).

정의: 점프높이 = 지면(z=0)에서 베이스 중심까지의 높이의 최댓값. 실측 출처 = 각 trial의
`Real Data.txt`의 "실제 점프 높이 : X m". sim은 base_z(= 지면 기준 베이스 중심) 최댓값.
※ 폐기: GRF 체공시간 g·T²/8은 **상승분**이지 점프높이가 아니다 (혼동 전례 2회).
ModeA(측정 토크 주입, 제어기 없음) 재생을 이륙 후 +0.6s까지 연장해 최고점을 직접 읽는다.
CLI: FS_MASS=... python _F_jumph_abs.py
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD
import fs_runner as FR

ROOT = Path(DATA_ROOT)
PAT = re.compile(r"실제 점프 높이\s*:\s*([\d.]+)")


def real_h(fold):
    f = fold / "Real Data.txt"
    if not f.exists():
        return None
    m = PAT.search(f.read_text(encoding="utf-8", errors="ignore"))
    if not m:
        return None
    v = float(m.group(1))
    return v / 100.0 if v > 5.0 else v      # 단위 혼재 방어: 26.03.24/P100_D3만 cm 표기(74.000)


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    rows = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hr = real_h(p)
        if hr is None:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            t_end_abs = min(tt[m][-1] + 0.6, tt[-1])
            m2 = (tt >= tt[i0]) & (tt <= t_end_abs)
            t = tt[m2] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            hs = float(L["bz"].max())
            rows.setdefault(s, []).append((hs, hr, p.name))
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print(f"\n{'세션':<10} {'n':>3} {'sim 최고[m]':>11} {'실측[m]':>9} {'Δ[cm]':>8} {'배율':>6}")
    A, B, D = [], [], []
    for s in sorted(rows):
        a = np.array([(x, y) for x, y, _ in rows[s]], float)
        hs, hr = float(np.median(a[:, 0])), float(np.median(a[:, 1]))
        A.append(hs); B.append(hr); D += list(np.abs(a[:, 0] - a[:, 1]) * 100)
        print(f"{s:<10} {len(a):3d} {hs:11.3f} {hr:9.3f} {(hs-hr)*100:+8.1f} {hs/hr:6.3f}")
    print(f"{'평균':<10} {'':>3} {np.mean(A):11.3f} {np.mean(B):9.3f} {(np.mean(A)-np.mean(B))*100:+8.1f} "
          f"{np.mean(A)/np.mean(B):6.3f}")
    print(f"\n**|Δh| (trial별 절대오차 평균) = {np.mean(D):.2f} cm**")


if __name__ == "__main__":
    main()
