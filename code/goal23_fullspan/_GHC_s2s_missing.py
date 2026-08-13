# -*- coding: utf-8 -*-
"""일어서기에서 **모자란 토크가 얼마인지** 자세별로 직접 잰다 (08-14 신설).

■ 무엇을 하나
  짧은 창(0.15초)을 매번 실측 상태로 새로 시작해 재생하되, 무릎(크랭크) 쪽에 **일정한
  여분 명령 토크 Δ 를 더해** 본다. 그 창의 실측을 가장 잘 따라가게 만드는 Δ 를 찾는다.
  Δ 가 0 이면 모델에 모자란 것이 없다는 뜻이고, Δ 가 +2 N·m 면 "이 자세에서 모델이
  실제보다 2 N·m 만큼 덜 밀고 있다"는 뜻이다. **0 이 완벽**이고 부호도 뜻이 있다.

■ 왜 이렇게 재나
  무릎은 4절 링크를 거쳐 구동되어 운동방정식을 직접 분해하는 방법이 성립하지 않는다
  (08-13 에 시도했다가 무의미한 값이 나왔다). 그래서 "역학을 풀어 모자란 힘을 계산"하는
  대신 **"얼마를 더 넣어야 실측과 같아지나"를 시뮬레이션으로 되찾는다.** 모델의 나머지
  부분은 그대로 두므로, 나온 값은 그 자세에서 모델에 빠진 것의 크기다.

■ 무엇을 가르나
  · Δ 가 자세(크랭크각)에 따라 어떻게 변하나 → 변속기 비선형 구간에 몰리나?
  · Δ 가 짐 무게에 따라 커지나 → **하중에 비례하는 손실**인가? (그렇다면 그 축을 열어야 한다)
  · 무변속에서도 같은 Δ 가 필요한가 → 변속기 탓인지 공통 탓인지

사용법: python _GHC_s2s_missing.py
"""
from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
HERE = str(Path(__file__).parent)
sys.path.insert(0, HERE)
os.chdir(HERE)

import numpy as np                       # noqa: E402
import fs_data as FD                     # noqa: E402
import fs_runner as FR                   # noqa: E402
import fs_cvt as FC                      # noqa: E402
import _GHB_sweep as S                   # noqa: E402

WIN, STEP = 0.15, 0.05
BINS = [(-180, -160), (-160, -140), (-140, -120), (-120, -90), (-90, -60), (-60, 0)]


def err_of(ft, d, mm, dlt):
    """무릎 명령에 일정한 여분 Δ 를 더해 재생했을 때, 창 끝의 크랭크각 어긋남 [도]."""
    t = d["t"]
    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm] + dlt,
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(tg[-1] - 0.004), fade=True)
    if L is None:
        return None
    sim = np.interp(tg, L["t"], L["q2"])
    return float(np.degrees(sim - d["q2"][mm])[-1])      # 부호 있는 값 (되찾기용)


def solve_delta(ft, d, mm, lo=-8.0, hi=8.0, it=12):
    """창 끝 어긋남을 0 으로 만드는 Δ 를 이분법으로 되찾는다 (없으면 None)."""
    a, b = err_of(ft, d, mm, lo), err_of(ft, d, mm, hi)
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or a * b > 0:
        return None                                     # 범위 안에서 부호가 안 바뀌면 포기
    for _ in range(it):
        m = 0.5 * (lo + hi)
        v = err_of(ft, d, mm, m)
        if v is None or not np.isfinite(v):
            return None
        if v * a > 0:
            lo, a = m, v
        else:
            hi = m
    return 0.5 * (lo + hi)


def main():
    S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
    m0 = float(os.environ.get("FS_MASS", "3.30"))
    print("자세별로 **모자란 무릎 명령 토크** Δ [N·m] — 0 이 완벽, +면 모델이 덜 밀고 있다는 뜻")
    print(f"{'경우':16s} " + " ".join(f"{a}~{b}".rjust(12) for a, b in BINS))
    print("-" * 96)
    for sub, pay, cvt in FD.S2S_CASES:
        d = FD.load_s2s(sub)
        if d is None:
            continue
        W = FD.air_windows(d, nwin=4, wmax=2.0)
        os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
        ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
        t = d["t"]
        acc = collections.defaultdict(list)
        for w0, w1 in W:
            a = w0
            while a + WIN <= w1:
                mm = (t >= a) & (t <= a + WIN)
                if mm.sum() >= 20:
                    dl = solve_delta(ft, d, mm)
                    if dl is not None:
                        cr = float(np.degrees(np.mean(d["q2"][mm])))
                        for b in BINS:
                            if b[0] <= cr < b[1]:
                                acc[b].append(dl); break
                a += STEP
        row = []
        for b in BINS:
            row.append(f"{np.mean(acc[b]):+8.2f}({len(acc[b]):2d})" if acc[b] else " " * 12)
        print(f"{sub:16s} " + " ".join(row))
    print("-" * 96)
    print("괄호 = 창 개수. 변속기 지렛대 비율: −176° 0.014(사점) · −170° 0.19 · −90° 0.84 · 0° 0.09")
    print("무변속은 전 각도 1.000 이라 같은 자세에서 증폭이 없다 — 두 줄을 비교하는 것이 요점이다.")


if __name__ == "__main__":
    main()
