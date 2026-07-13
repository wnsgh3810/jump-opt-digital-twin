# -*- coding: utf-8 -*-
"""p20c 모델 전 데이터 결과 생성 — p19_all_results 정본 파이프라인 재사용 (모델만 교체).

출력: Desktop/jump_opt/g22_p20c_all_results/<세션>/{png,gif,traj}/
구성 차이 (vs P19): pre30=0 (담요 제거), 보정층 c_qs≈0.005는 <0.1Nm이라 생략(INDEX에 명기),
0429 각도 영점 = 재적합값 (7.0°, −5.0°) — A/CL 동일 적용. 플랜트 x = p20c.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p19_all_results as B          # 정본 파이프라인
import p19_adapter as AD

CAND = AD.load_candidate(HERE / "fourbar_p20c_candidate.json")
X32, V, SP, QOFF = AD._p19_args(CAND)

# ── 모듈 전역 오버라이드 (함수들은 호출 시점 전역을 참조) ──
B.CAND = CAND
B.X32, B.V, B.SP = X32, V, SP
B.QOFF = QOFF                        # CL용 0429 오프셋 = 재적합값
B.QOFF_A429 = QOFF                   # Mode A도 동일 (엔코더 영점은 모드 무관)
B.TM = float(V[15])
B.PRE30 = 0.0                        # 담요 제거 (p20c 핵심)
B.ROOT = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20c_all_results")


def main():
    B.ROOT.mkdir(parents=True, exist_ok=True)
    print(f"p20c stack: sp={B.SP} tm={B.TM*1000:.2f}ms pre30=0 qoff429="
          f"({QOFF[0]:.4f},{QOFF[1]:.4f})", flush=True)
    res = B.do_jumps()
    B.do_s2s()
    crashes = [r for r in res if r[3] != "OK"]
    print(f"SIM DONE — {len(res)} runs, crash {len(crashes)}: {crashes}", flush=True)
    # 0604 페이로드 (동일 파이프라인, B 전역이 이미 p20c)
    import s2s_0604_p19 as S6
    S6.main()
    B.do_gifs()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
