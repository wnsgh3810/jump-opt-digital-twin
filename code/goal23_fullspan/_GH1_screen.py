# -*- coding: utf-8 -*-
"""_GH1_screen — 마라톤H 1축 스크리닝 (2026-08-11).

무엇
  fs_runner 의 **미탐색 축 51개**를 하나씩 켜 보며 폐루프 보드를 잰다.
  목적은 우승자 결정이 아니라 **후보 선별** — 살아남은 축만 전 보드+게이트로 넘긴다.

왜 부분집합인가
  전 보드 1회가 수 분이라 51축×3값을 다 돌리면 몇 시간이다. 스크리닝은 **세션 다양성만
  유지한 부분집합**으로 빠르게 훑고, 유망한 것만 정밀 재판정한다.
  ★ 부분집합 성적으로 채택하지 말 것 — 게이트(0421)와 변속(0429)이 빠져 있다.

지표
  폐루프 6채널 RMSE 의 trial 평균 (기준선 대비 %). 낮을수록 좋음.

CLI
  python _GH1_screen.py            # 전 축
  python _GH1_screen.py FS_MU,FS_TSCALE
환경
  GH1_SESS  부분집합 세션 (기본: 0424,0602,0722,0727 — 게인·날짜 다양)
"""
import os, sys, io, json, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                                      # noqa: E402

SESS = os.environ.get("GH1_SESS", "26.04.24,26.06.02,26.07.22,26.07.27").split(",")
OUT = HERE / "_GH1_screen.json"
CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")

# 축 → 시험값. 기본값(=현행)은 자동으로 기준선이 되므로 여기 안 적는다.
AXES = {
    # ── 토크 변환식 ──
    "FS_TSCALE":    ["0.92", "1.08"],
    "FS_TRANS":     ["0.01,0.6", "0.02,0.5"],
    "FS_TDCAP":     ["3.0,2.0", "4.6,3.2", "3.8,3.8"],
    "FS_KDSC":      ["0.5", "0.75", "1.5"],
    "FS_TKOVR":     ["0.8", "1.2"],
    # ── 질량·관성·무게중심 ──
    "FS_MASS":      ["3.22", "3.34"],
    # ★ 이 셋은 "바디이름=값" 형식이다 (fs_runner._kv). 숫자만 주면 파싱 실패 → 전 trial 실패.
    #   질량은 절대값[kg], 관성은 배율, CoM 은 z 오프셋[m].
    "FS_MBODY":     ["thigh=0.87", "thigh=0.96", "crank=0.40", "crank=0.50"],
    "FS_IBODY":     ["thigh=0.85", "thigh=1.15", "calf=0.85", "calf=1.15"],
    "FS_COMZ":      ["thigh=-0.008", "thigh=0.008", "calf=-0.008", "calf=0.008"],
    # ── 탄성·감쇠 ──
    "FS_HSPR_S":    ["0.8", "1.25"],
    "FS_HIPM_DAMP": ["0.20", "0.45"],
    "FS_HIPM_ARM":  ["0.95", "1.05"],
    "FS_W2":        ["0.02", "0.05"],
    "FS_BS":        ["0.5", "2.0"],
    # ── 접촉 ──
    "FS_MU":        ["0.75", "1.0"],
    "FS_FOOTR":     ["0.018", "0.022"],
    "FS_PRESLIDE":  ["0.80,0.80,0.02,1.0", "0.92,0.90,0.02,1.0", "0.86,0.85,0.04,1.0"],
    # ── 관측·커맨드 ──
    "FS_TC":        ["0.001", "0.005"],
    "FS_CMD_LPF":   ["0.002", "0.005"],
    "FS_QDSHIFT":   ["1", "3"],
    "FS_TAULIM":    ["18.0", "25.0"],
    # ── 인공층 잔재 (되살리면 좋아지나) ──
    "FS_KNEE_REL":  ["0.05", "0.2"],
    "FS_RISE_CAP":  ["1.0", "3.0"],
}


def board():
    import fs_data as FD, fs_compare_plot as CP
    F = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g or s not in SESS:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            r = CP.cl_pair(d, seg, g, s)
        except Exception:
            continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        e = lambda a, b, k: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if k in ("q1", "q2") else 1)
        F.append([e(fs[i], mf[k], k) for i, k in enumerate(CH)])
    F = np.array(F)
    return F if len(F) and np.all(np.isfinite(F)) else None


def main():
    want = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    import fs_runner as FR
    base = board()
    if base is None:
        raise SystemExit("기준선 산출 실패")
    b = base.mean()
    print(f"부분집합 {SESS} · {len(base)} trial")
    print(f"기준선 (현행 G26_0811): 전채널 {b:.4f} "
          f"| 무릎각 {base[:,1].mean():.2f}° 무릎토크 {base[:,5].mean():.2f}\n", flush=True)
    res = {}
    t0 = time.time()
    for ax, vals in AXES.items():
        if want and ax not in want:
            continue
        prev = os.environ.get(ax)
        for v in vals:
            os.environ[ax] = v
            FR._S2S = None                      # 힙 스프링 캐시 무효화
            f = board()
            if f is None:
                print(f"  {ax:14s} = {v:22s} → 발산/실패", flush=True); continue
            d = 100 * (f.mean() / b - 1)
            res[f"{ax}={v}"] = dict(tot=float(f.mean()), d=float(d),
                                    ch=[float(x) for x in f.mean(0)])
            mark = " ★" if d < -1.0 else ("  ." if d < 0 else "")
            print(f"  {ax:14s} = {v:22s} → {f.mean():.4f} ({d:+6.2f}%){mark}", flush=True)
        if prev is None:
            os.environ.pop(ax, None)
        else:
            os.environ[ax] = prev
        FR._S2S = None
    safe.atomic_json_write(OUT, {"base": float(b), "sess": SESS, "res": res})
    print(f"\n{time.time()-t0:.0f}초 · 저장 → {OUT}")
    good = sorted([(v["d"], k) for k, v in res.items()])[:12]
    print("\n개선 상위 12 (부분집합 기준 — 전 보드·게이트 재판정 필요)")
    for d, k in good:
        print(f"  {d:+6.2f}%  {k}")


if __name__ == "__main__":
    main()
