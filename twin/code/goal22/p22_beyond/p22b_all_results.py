# -*- coding: utf-8 -*-
"""p22b 후보 전 데이터 결과 생성 — p22a_all_results와 동일 (태그만 교체)."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p19_all_results as B
import p19_adapter as AD

TAG = "p22b"
CAND = AD.load_candidate(HERE / f"fourbar_{TAG}_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)

B.CAND = CAND
B.X32, B.V, B.SP = X32, V, SP
B.QOFF = QOFF                      # CL 전용 — Mode A 0429 오프셋은 프로토콜 기본값 유지
B.TM = float(V[15])
B.PRE30 = float(V[2])
B.C_QSG = float(CAND["p20"]["c_qs"])
B.V0G = float(CAND["p20"]["v0"])
B.MODEL_TAG = TAG
B.ROOT = Path(LEGACY_ROOT + f"/g22_{TAG}_all_results")


def main():
    B.ROOT.mkdir(parents=True, exist_ok=True)
    print(f"{TAG} stack: sp={B.SP} tm={B.TM*1000:.2f}ms pre30={B.PRE30:.3f} "
          f"c_qs={B.C_QSG:.4f} v0={B.V0G:.1f}", flush=True)
    res = B.do_jumps()
    B.do_s2s()
    crashes = [r for r in res if r[3] != "OK"]
    print(f"SIM DONE — {len(res)} runs, crash {len(crashes)}: {crashes}", flush=True)
    import importlib
    import s2s_0604_p19 as S6
    importlib.reload(S6)
    S6.main()
    B.do_gifs()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()

# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------