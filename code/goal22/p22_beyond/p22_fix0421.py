# -*- coding: utf-8 -*-
"""P22 Phase 0 — 0421 Mode A/창 토크 소스 xlsx 통일 (csv 1.35x 인공물 제거).

배경 (P22 프리플라이트, HYPOTHESES.md): 레거시 로더(goal18/iter2 sub_sim.load_jump_position)가
0421의 tau_real을 xlsx가 아닌 predicted_compare.csv(kneeCurrentTorquePaper 등)에서 읽으며,
이 값은 xlsx→Paper 변환의 1.32~1.36배 (hip/knee 양 채널, 6/6 trial 검증 2026-07-16).
CL 경로(load_trial_xlsx)는 원래 xlsx 직독이라 청정 — 오염은 Mode A 캐시(raw=invert_paper(csv값))와
그걸 쓰는 창 점수(windows_score)에만 있다.

사용: judge winit 후 apply() 1회 호출 — P12._G["trials"]의 0421 raw1/raw2를 xlsx currentTorque로
교체하고 td.tau{1,2}_real을 ahat(xlsx)로 재계산. 반환: (sub, ch, 구/신 비율) 목록.
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
from pathlib import Path

import numpy as np
import pandas as pd

ROOT0421 = Path((DATA_ROOT + "/26_04_21/Position Control"))
DS = "jump_position_0421"


def apply(P=None, verbose=True):
    if P is None:
        import p19_judge as P
    J = P.J
    A = P.A_PAPER
    P12 = J._P["P12"]
    rows = []
    for tr in P12._G["trials"]:
        if tr.get("ds") != DS:
            continue
        sub = tr["sub"]
        src = {"1": pd.read_excel(ROOT0421 / sub / "hip.xlsx"),
               "2": pd.read_excel(ROOT0421 / sub / "knee.xlsx")}
        for j in ("1", "2"):
            traw = src[j]["currentTorque"].values.astype(float)
            old = np.asarray(tr["raw" + j], float)
            v = np.asarray(tr["v" + j], float)
            m = min(len(old), len(traw))
            new = old.copy()
            new[:m] = traw[:m]
            oa = J.ahat(A, old, v)
            na = J.ahat(A, new, v)
            sig = np.abs(na) > 2.0
            ratio = float(np.abs(oa[sig]).mean() / max(np.abs(na[sig]).mean(), 1e-9)) \
                if sig.any() else float("nan")
            tr["raw" + j] = new
            tr["td"][f"tau{j}_real"] = na
            rows.append((sub, j, ratio))
            if verbose:
                print(f"fix0421 {sub} ch{j}: old/new(|ahat|,sig) = {ratio:.3f}", flush=True)
    if verbose:
        print(f"fix0421 applied: {len(rows)} channels", flush=True)
    return rows
