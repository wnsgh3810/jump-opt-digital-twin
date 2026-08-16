# -*- coding: utf-8 -*-
"""_GHQ_s2sveldir — **모자란 토크가 속도·방향에 어떻게 의존하나** (일어서기 4경우).

방법은 `_GHC_s2s_missing` / `_GHC_s2s_updown` 과 같다:
  0.15초 창을 매번 실측 상태로 새로 앵커해 재생하되, 무릎(크랭크) 명령에 일정한 여분 Δ 를
  더해 창 끝의 어긋남을 0 으로 만드는 Δ 를 이분법으로 되찾는다 [명령 N·m].
바뀐 점: 자세뿐 아니라 **속도**와 **부호(올라감/내려감)** 를 창마다 같이 기록해서
  Δ 를 속도의 함수로 본다. 앉는 구간(내려감)은 전 구간(raw_unwrap) 기록에만 있다.

창 채택 조건
  · 몸통 높이 z = −0.25(sin q1 + sin(q1+q2)) > 0.10 m — 받침에 얹혀 있는 구간을 뺀다
    (fs_data.plot_window 의 s2s 규약과 같은 식). 창 전체가 조건을 만족해야 한다.
  · 창 안 크랭크 속도의 부호가 일정하고 |평균속도| ≥ VMIN.

출력: `_GHQ_s2sveldir.json` (창별 원자료) + 표.
CLI: python _GHQ_s2sveldir.py [step]
"""
from __future__ import annotations
import os, sys, json, time

os.environ.setdefault("FS_SWEEP_AIR", "0")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
os.chdir(HERE)

import numpy as np                        # noqa: E402
import fs_data as FD                      # noqa: E402
import fs_runner as FR                    # noqa: E402
import fs_cvt as FC                       # noqa: E402
import _GHB_sweep as S                    # noqa: E402
from _GHC_s2s_missing import solve_delta   # noqa: E402
from _GHC_s2s_updown import load_full, pick_tau  # noqa: E402

WIN = float(os.environ.get("GHQ_WIN", "0.15"))
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
VMIN = 0.05
ZMIN = FD.S2S_ZMIN
ONLY = os.environ.get("GHQ_ONLY", "")
OUT = HERE / os.environ.get("GHQ_OUT", "_GHQ_s2sveldir.json")


def main():
    S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
    m0 = float(os.environ.get("FS_MASS", "3.30"))
    rows = []
    for sub, pay, cvt in FD.S2S_CASES:
        if ONLY and ONLY not in sub:
            continue
        t0w = time.time()
        dw = FD.load_s2s(sub)
        raw = load_full(sub)
        if raw is None:
            print(f"{sub}: 전 구간 기록 없음 — 건너뜀"); continue
        d, pick = pick_tau(sub, raw, dw)
        if d is None or pick[1] > 0.5:
            print(f"{sub}: ⚠ 전 구간 기록이 정본 창과 불일치 — 건너뜀"); continue
        print(f"{sub}: 전 구간 토크 = {pick[0]} ✔")
        d["l_i"] = dw["l_i"]
        os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
        ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
        t = d["t"]
        dt = float(np.median(np.diff(t)))
        dq = FD._smooth(np.nan_to_num(d["dq2"]), max(3, int(round(0.02 / dt))))
        z = -0.25 * (np.sin(d["q1"]) + np.sin(d["q1"] + d["q2"]))
        a, n_ok, n_try = float(t[0]), 0, 0
        while a + WIN <= float(t[-1]):
            mm = (t >= a) & (t <= a + WIN)
            a += STEP
            if mm.sum() < 20 or not np.all(z[mm] > ZMIN):
                continue
            v = float(np.mean(dq[mm]))
            if abs(v) < VMIN:
                continue
            sg = np.sign(dq[mm])
            if not np.all(sg == np.sign(v)):        # 창 안에서 방향이 바뀌면 버린다
                continue
            n_try += 1
            dl = solve_delta(ft, d, mm)
            if dl is None:
                continue
            n_ok += 1
            rows.append(dict(case=sub, pay=pay, cvt=bool(cvt), t=float(t[mm][0]),
                             dlt=float(dl), v=v, absv=abs(v),
                             q2=float(np.degrees(np.mean(d["q2"][mm]))),
                             q1=float(np.degrees(np.mean(d["q1"][mm]))),
                             v1=float(np.mean(d["dq1"][mm])),
                             raw2=float(np.mean(d["raw2"][mm])),
                             absraw2=float(np.mean(np.abs(d["raw2"][mm]))),
                             z=float(np.mean(z[mm]))))
        print(f"   창 {n_ok}/{n_try} 성공 ({time.time()-t0w:.0f}s)")
    json.dump(rows, open(OUT, "w", encoding="utf-8"))
    print(f"저장 → {OUT}  ({len(rows)} 창)")


if __name__ == "__main__":
    main()
