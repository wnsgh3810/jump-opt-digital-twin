# -*- coding: utf-8 -*-
"""p22a 후보 전 데이터 결과 생성 — 정본 파이프라인(p19_all_results) 재사용.

p21_all_results 패턴. 차이: 후보 경로가 p22_beyond, Mode A의 0429 각도 영점은
v5 프로토콜 고정값(B.QOFF_A429 기본 = 3.14°,−3.0°)을 유지 (p22_eval/OLdq 앵커와 동일 규약).
CL 오프셋(B.QOFF)만 후보 적합값 사용.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p19_all_results as B
import p19_adapter as AD

TAG = "p22a"
CAND = AD.load_candidate(HERE / f"fourbar_{TAG}_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)

B.CAND = CAND
B.X32, B.V, B.SP = X32, V, SP
B.QOFF = QOFF                      # CL 전용 (후보 적합 오프셋)
# B.QOFF_A429는 기본값 유지 — Mode A 프로토콜 고정 (p22_eval 규약)
B.TM = float(V[15])
B.PRE30 = float(V[2])
B.C_QSG = float(CAND["p20"]["c_qs"])
B.V0G = float(CAND["p20"]["v0"])
B.MODEL_TAG = TAG
B.ROOT = Path(rf"C:/Users/junho/Desktop/jump_opt/g22_{TAG}_all_results")


def main():
    B.ROOT.mkdir(parents=True, exist_ok=True)
    print(f"{TAG} stack: sp={B.SP} tm={B.TM*1000:.2f}ms pre30={B.PRE30:.3f} "
          f"c_qs={B.C_QSG:.3f} v0={B.V0G:.1f}", flush=True)
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
