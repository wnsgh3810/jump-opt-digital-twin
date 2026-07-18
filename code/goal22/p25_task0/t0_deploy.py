# -*- coding: utf-8 -*-
"""t0 배포 채점 — task0 제약 계획들을 게인 8종 × {FF+PD, 그대로 PD}로 트윈 배포.

클립 = RAW15(25.5810, |â|=15Nm 등가)를 계획·배포 플랜트 양쪽에 (t18 캠페인과 동일 규약).
입력: p25_task0/t0*.npz (CVT 계획 t0wc_*는 현 배포 하네스가 flip 전용이라 제외 — 정직 표기)
출력: t0_deploy_results.json
"""
import os
import sys
from pathlib import Path

for k in ("P23_SPRING_GATED", "P23_RISE_GATED", "P24_HIP_LAW", "P24_REFIT"):
    os.environ.setdefault(k, "1")
os.environ["P25_CLIP_RAW"] = "35.5"   # 배포 플랜트 = 하드웨어 천장 (계획 캡 15Nm는 계획 npz에 이미 반영 — 사용자 지시 07-18: PD 제어에 토크 제약 없앰)
os.environ["P25_GAINS_FULL"] = "1"

import numpy as np

HERE = Path(__file__).parent
DEP = HERE.parent / "p25_deploy"
sys.path.insert(0, str(DEP))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p25_d_deploy as D
import p25_d_ff as FF
import safe


def main():
    plans = [p for p in sorted(HERE.glob("t0nc_*.npz"))]
    rows = {}
    print(f"{'계획':22s} {'모드':8s} {'게인':16s} {'h_plan':>7s} {'h_PD':>7s} {'F_τ':>7s}")
    for src in plans:
        for gkey in D.GAINS:
            for mode, fn in (("FF+PD", lambda: FF.deploy_ff(src, gkey)),
                             ("그대로", lambda: D.deploy(src, gkey))):
                r = fn()
                if r.get("crash"):
                    print(f"{src.stem:22s} {mode:8s} {gkey:16s}  CRASH", flush=True)
                    continue
                rows[f"{src.name}|{mode}|{gkey}"] = {
                    k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                    for k, v in r.items() if not isinstance(v, (list, dict, np.ndarray))}
                print(f"{src.stem:22s} {mode:8s} {gkey:16s} "
                      f"{r.get('h_plan', float('nan')):7.3f} {r['h_PD']:7.3f} "
                      f"{100*r['F_tau']:6.1f}%", flush=True)
    safe.atomic_json_write(HERE / "t0_deploy_results.json", rows)
    print("saved t0_deploy_results.json", flush=True)


if __name__ == "__main__":
    main()
