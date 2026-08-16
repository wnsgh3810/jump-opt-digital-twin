# -*- coding: utf-8 -*-
"""_GHP_posture10 — **오차의 자세 의존 재유도** (08-15).

무엇을 하나
  ① 짐 지고 일어서기 네 경우에서 **모자란 무릎 명령 토크 Δ** 를 크랭크 각도 10도 구간
     평균으로 다시 뽑는다 (`_GHC_s2s_missing.py` 의 방법 그대로, 구간만 20도 → 10도,
     창 간격만 0.05 → 0.02초로 촘촘하게).
  ② 같은 각도축에서 4절 링크의 **힘/속도 교환비** r = dq_무릎/dq_크랭크 를 계산해 나란히 둔다
     (`cvt_core.closure` — 모델이 쓰는 `RU.rtab` 과 같은 출처, 다만 연속 이어풀기로 더 촘촘히).
  ③ Δ 가 (1/r − 1) 에 비례하는지, 아니면 다른 모양인지 회귀로 가른다.

산출: _GHP_posture10.json (창별 원자료 + 구간 평균)
"""
from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["FS_CVT_XML"] = "0"          # 16 작업자 스윕과 파일 충돌 금지
HERE = str(Path(__file__).parent)
sys.path.insert(0, HERE)
sys.path.insert(0, str(Path(HERE).parent / "goal22" / "p18_cvt"))
os.chdir(HERE)

import numpy as np                       # noqa: E402
import fs_data as FD                     # noqa: E402
import fs_runner as FR                   # noqa: E402
import fs_cvt as FC                      # noqa: E402
import _GHB_sweep as S                   # noqa: E402
from cvt_core import closure             # noqa: E402

WIN, STEP = 0.15, 0.02
EDGES = np.arange(-180, 1, 10.0)
BINS = [(EDGES[i], EDGES[i + 1]) for i in range(len(EDGES) - 1)]


# ── ① 교환비 표 (연속 이어풀기) ────────────────────────────────────────────────────
def ratio_table(l_i, n=4001, qmax=3.10):
    """크랭크각(데이터 부호, [도]) → (r, dr/dθ[1/rad]) 보간용 격자.

    데이터의 크랭크각은 음수(깊게 접힘)이고 시뮬레이터 좌표는 그 부호 반대다 (qc = −q2).
    `closure` 는 시뮬레이터 좌표를 받는다. 앞 해를 초기값으로 물려 주는 이어풀기라야
    사점 근처에서 뉴턴이 엉뚱한 가지로 안 튄다 (`RU.rtab` 과 같은 방식).
    """
    qc = np.linspace(0.0, qmax, n)          # 시뮬 좌표 [rad] (0 = 편 자세, +3.05 = 깊음)
    r = np.ones(n)
    # ☠ 가지 선택: qc=0 이나 qc=±3 에서 이어풀기를 시작하면 **반대 조립 가지**(교차형)로
    #   빠진다 (모델이 쓰는 RU.rtab 이 바로 그 사고다 — _GHP_rcheck 참조).
    #   조건이 좋은 qc=π/2 에서 시작해 양쪽으로 편다. 점별(seed=qk0=qc) 풀이와 전 구간 일치.
    i0 = int(np.argmin(np.abs(qc - np.pi / 2)))
    qk0, _, r0 = closure(float(qc[i0]), float(l_i), None)
    r[i0] = r0
    p = qk0
    for i in range(i0 + 1, n):
        p, _, rr = closure(float(qc[i]), float(l_i), p); r[i] = rr
    p = qk0
    for i in range(i0 - 1, -1, -1):
        p, _, rr = closure(float(qc[i]), float(l_i), p); r[i] = rr
    ang = -np.degrees(qc)                    # 데이터 부호 [도] (0 → −177.6)
    o = np.argsort(ang)
    ang, r = ang[o], r[o]
    dr = np.gradient(r, np.radians(ang))     # dr/dθ_crank [1/rad] (데이터 부호축)
    return ang, r, dr


def r_at(tab, deg):
    ang, r, dr = tab
    return float(np.interp(deg, ang, r)), float(np.interp(deg, ang, dr))


# ── ② Δ 되찾기 (원본 _GHC_s2s_missing 과 같은 문자) ────────────────────────────────
def err_of(ft, d, mm, dlt):
    t = d["t"]
    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm] + dlt,
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(tg[-1] - 0.004), fade=True)
    if L is None:
        return None
    sim = np.interp(tg, L["t"], L["q2"])
    return float(np.degrees(sim - d["q2"][mm])[-1])


def solve_delta(ft, d, mm, lo=-8.0, hi=8.0, it=12, why=None):
    a, b = err_of(ft, d, mm, lo), err_of(ft, d, mm, hi)
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or a * b > 0:
        if why is not None:
            why.append((a, b))
        return None
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
    ft0 = FR.fs_twin()
    P = ft0["P"]
    A = FR.tq_shape(P.A_PAPER)
    tmap = FR._tmap_init(P, A)          # 명령 → 축토크 (같은 env = 재생과 같은 변환)

    rows = []
    fails = []
    tabs = {}
    for sub, pay, cvt in FD.S2S_CASES:
        d = FD.load_s2s(sub)
        if d is None:
            continue
        li = float(d["l_i"])
        if li not in tabs:
            tabs[li] = ratio_table(li)
        tab = tabs[li]
        W = FD.air_windows(d, nwin=4, wmax=2.0)
        os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
        ft = FC.cvt_ft(li, ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
        t = d["t"]
        nfail = 0
        for w0, w1 in W:
            a = w0
            while a + WIN <= w1 + 1e-9:
                mm = (t >= a) & (t <= a + WIN)
                if mm.sum() >= 20:
                    why = []
                    dl = solve_delta(ft, d, mm, why=why)
                    cr = float(np.degrees(np.mean(d["q2"][mm])))
                    cr0 = float(np.degrees(d["q2"][mm][0]))
                    cr1 = float(np.degrees(d["q2"][mm][-1]))
                    v2 = float(np.mean(d["dq2"][mm]))
                    raw2 = float(np.mean(d["raw2"][mm]))
                    rr, drr = r_at(tab, cr)
                    if dl is None:
                        nfail += 1
                        fails.append(dict(sub=sub, t0=float(a), crank=cr, dq2=v2,
                                          err_lo=(why[0][0] if why else None),
                                          err_hi=(why[0][1] if why else None)))
                    else:
                        # 명령 Δ 를 축 토크로 환산 (그 작동점에서의 기울기)
                        ax = (tmap(raw2 + dl, v2, 1) - tmap(raw2, v2, 1)) if tmap else float("nan")
                        rows.append(dict(sub=sub, pay=pay, cvt=cvt, l_i=li, t0=float(a),
                                         crank=cr, crank0=cr0, crank1=cr1, dq2=v2,
                                         raw2=raw2, r=rr, drdq=drr, delta=float(dl),
                                         delta_axis=float(ax)))
                a += STEP
        print(f"{sub:16s} 창 {sum(1 for x in rows if x['sub']==sub):3d}개 되찾음 · 실패 {nfail}", flush=True)

    json.dump(dict(rows=rows, fails=fails), open("_GHP_posture10.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("저장 → _GHP_posture10.json")


if __name__ == "__main__":
    main()
