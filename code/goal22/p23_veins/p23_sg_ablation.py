# -*- coding: utf-8 -*-
"""p23_sg_ablation — Phase 4b 결정 시험: 부하 연동 스프링 하에서 두 유역이 화해하는가.

p23_diag_x.json(세그2 F2-최선)의 x에 T_SPR을 붙여 SPRING_GATED로
  {LAW_A: −1.221(측정), −0.6, 0} × {T_SPR: 1, 2, 4} 9칸 + as-is(LAW_A −0.414, T_SPR init)
을 평가 — Phase 4 절제 매트릭스와 같은 성분표 (OLDQ 3 + FF 2 + AIR + CL̂).

성공 기준 (과제 동결): 어떤 변형이 {0429≤3.6, 0319tau≤1.6, AIR≤~1.0}과
{0424≤2.3, 0602≤1.5, 0422≤2.5}를 동시 만족 = 절편 2분법(두 유역) 화해.
비교 기준 (비게이트, MARATHON 매트릭스): base 2.21/1.36/5.19 | 2.36/3.36 | 2.01 | 0.978,
LAW_A=−1.22 2.74/1.91/3.60 | 4.36/1.57 | 0.77 | 1.006.

산출: p23_sg_ablation.json + 표 출력. 단발 실행 (~10 eval ≈ 2-3분, .bat 불요).
"""
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ["P23_SPRING_GATED"] = "1"      # 이 스크립트는 게이트 모드 전용 (import 전 강제)

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p23_v6_eval as V
import p23_v6_runners as RU
import safe

# 성공 기준 (과제 문언; AIR '≤1.0-ish'는 1.05로 코드화하되 원값 보고)
CRIT_LOW = dict(o0429=3.6, f0319=1.6, AIR=1.05)     # 저토크·공중 유역
CRIT_HIGH = dict(o0424=2.3, o0602=1.5, f0422=2.5)   # 고게인 유역


def main():
    safe.utf8_console()
    assert RU.SPRING_GATED and RU.NV23 == 23
    t0 = time.time()
    V.ensure_init()
    a5, aff, _ = V.anchors()
    x = np.asarray(safe.read_json(HERE / "p23_diag_x.json")["x"], float)
    assert x.size == 22
    print(f"diag x: LAW_A={x[15]:+.4f} D_DQ={x[21]:+.4f} C_CVT={x[20]:.4f} "
          f"stiff={x[0]:.4f} ref={x[1]:.4f} | winit [{time.time() - t0:.0f}s]", flush=True)

    cells = [("asis", float(x[15]), RU.T_SPR0)]
    for la in (RU.LAW_A0, -0.6, 0.0):
        for tsp in (1.0, 2.0, 4.0):
            cells.append((f"A{la:+.2f}_T{tsp:.0f}", la, tsp))
    # 보충 3칸: T_SPR 바운드 추적 확인 + 중간 절편 (1차 9칸 판독 후 추가)
    for la, tsp in ((0.0, 6.0), (-0.3, 4.0), (-0.3, 6.0)):
        cells.append((f"A{la:+.2f}_T{tsp:.0f}", la, tsp))

    hdr = (f"{'variant':16s} {'0424':>6s} {'0602':>6s} {'0429':>6s} "
           f"{'0422':>6s} {'0319t':>6s} {'AIR':>6s} {'CL^':>6s} "
           f"{'J_v5':>7s} {'J_v6':>7s} {'lowB':>5s} {'highB':>5s}")
    print("\n" + hdr, flush=True)
    rows = []
    for name, la, tsp in cells:
        v = np.append(x.copy(), tsp)
        v[15] = la
        c = V.evaluate(v, keep_rows=False)
        r = dict(name=name, LAW_A=float(la), T_SPR=float(tsp),
                 o0424=c["OLDQ"]["jump_0424"], o0602=c["OLDQ"]["jump_0602"],
                 o0429=c["OLDQ"]["jump_0429"], f0422=c["OLDQFF"]["jump_0422"],
                 f0319=c["OLDQFF"]["jump_0319tau"], AIR=c["AIR"],
                 CLhat=c["CL"] / a5["CL"], J_v5=c["J_v5"], J_v6=c["J_v6"],
                 H=c["H"], DQhat=c["DQ"] / a5["DQ"], gates=c["gates"])
        r["low_ok"] = bool(r["o0429"] <= CRIT_LOW["o0429"]
                           and r["f0319"] <= CRIT_LOW["f0319"]
                           and r["AIR"] <= CRIT_LOW["AIR"])
        r["high_ok"] = bool(r["o0424"] <= CRIT_HIGH["o0424"]
                            and r["o0602"] <= CRIT_HIGH["o0602"]
                            and r["f0422"] <= CRIT_HIGH["f0422"])
        rows.append(r)
        print(f"{name:16s} {r['o0424']:6.2f} {r['o0602']:6.2f} {r['o0429']:6.2f} "
              f"{r['f0422']:6.2f} {r['f0319']:6.2f} {r['AIR']:6.2f} {r['CLhat']:6.3f} "
              f"{r['J_v5']:7.3f} {r['J_v6']:7.3f} "
              f"{'P' if r['low_ok'] else '.':>5s} {'P' if r['high_ok'] else '.':>5s}",
              flush=True)

    both = [r for r in rows if r["low_ok"] and r["high_ok"]]
    print(f"\n두 유역 동시 만족: {len(both)}/{len(rows)}"
          + (" -> " + ", ".join(r["name"] for r in both) if both else " (없음)"),
          flush=True)
    safe.atomic_json_write(HERE / "p23_sg_ablation.json", dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        crit=dict(low=CRIT_LOW, high=CRIT_HIGH),
        base_x="p23_diag_x.json", rows=rows))
    print(f"saved p23_sg_ablation.json [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
