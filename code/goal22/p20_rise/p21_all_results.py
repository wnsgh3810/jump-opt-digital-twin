# -*- coding: utf-8 -*-
"""p21/p21h 후보 전 데이터 결과 생성 — 정본 파이프라인 재사용 (인자: 후보 태그).

사용: python p21_all_results.py p21   또는  python p21_all_results.py p21h
구성: pre30≈0 + 상시 부하비례 어시스트 (C_QSG·â/(1+(v/V0G)²)) — 러너 전역으로 주입.
0429 각도 영점 = 후보 적합값, A/CL 동일.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p19_all_results as B
import p19_adapter as AD

TAG = sys.argv[1] if len(sys.argv) > 1 else "p21"
CAND = AD.load_candidate(HERE / f"fourbar_{TAG}_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)

B.CAND = CAND
B.X32, B.V, B.SP = X32, V, SP
B.QOFF = QOFF
B.QOFF_A429 = QOFF
B.TM = float(V[15])
B.PRE30 = float(V[2])
B.C_QSG = float(CAND["p20"]["c_qs"])
B.V0G = float(CAND["p20"]["v0"])
B.MODEL_TAG = TAG
B.ROOT = Path(rf"C:/Users/junho/Desktop/jump_opt/g22_{TAG}_all_results")


def main():
    B.ROOT.mkdir(parents=True, exist_ok=True)
    print(f"{TAG} stack: sp={B.SP} tm={B.TM*1000:.2f}ms pre30={B.PRE30:.3f} "
          f"c_qs={B.C_QSG:.3f} v0={B.V0G:.1f} qoff429=({QOFF[0]:.4f},{QOFF[1]:.4f})", flush=True)
    res = B.do_jumps()
    B.do_s2s()
    crashes = [r for r in res if r[3] != "OK"]
    print(f"SIM DONE — {len(res)} runs, crash {len(crashes)}: {crashes}", flush=True)
    import importlib
    import s2s_0604_p19 as S6
    importlib.reload(S6)          # SD가 B.ROOT 기준으로 재계산되도록
    S6.main()
    B.do_gifs()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
