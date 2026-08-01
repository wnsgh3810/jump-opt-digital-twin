# -*- coding: utf-8 -*-
"""fs_uboard — 통일 심판 보드 (마라톤 F Phase 0: 지표 보드 = 그래프 규약).

구 보드(baseline_fs3/modea_fs3)의 이원화 해소: CL·MA 모두 **점프 창(plot_window) ·
창 시작 실측 앵커 · 통짜**로 채점 (perf_plot_guard 규약과 동일한 자 — _E_gconv 프로토타입 정식화).
- CL  : fit 세션 (게인 有·비CVT·비HO) — rollout_cl_fs(init_meas=)
- MA  : 전 비CVT 세션 (held-out 0324 포함) — rollout_ol_fs_b (통짜 재생)
- 가드: 기준표(ref JSON) 대비 세션×채널 상대 임계 **max(+5%, 절대 +0.05°/동단위)**
출력: _F_uboard_<tag>.json = {"CL": {sess: [[6ch]...]}, "MA": {...}}
CLI: python fs_uboard.py <tag> [ref_tag]   (ref 주면 가드 판정표 출력)
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
import fs_runner as FR

CH = ["q1", "q2", "dq1", "dq2", "t1", "t2"]
_qs = int(os.environ.get("FS_QDSHIFT", "0") or 0)


def sh(x):
    if _qs <= 0:
        return x
    y = np.empty_like(x); y[_qs:] = x[:-_qs]; y[:_qs] = x[0]
    return y


def rmse6(d, m, thm1, q2s, dq1s, dq2s, t1s, t2s):
    r = []
    for meas, sim, deg in ((d["q1"][m], thm1, True), (d["q2"][m], q2s, True),
                           (d["dq1"][m], dq1s, False), (d["dq2"][m], dq2s, False),
                           (d["a1"][m], t1s, False), (d["a2"][m], t2s, False)):
        v = float(np.sqrt(np.mean((meas - sim) ** 2)))
        r.append(float(np.degrees(v)) if deg else v)
    return r


def run_board():
    ft = FR.fs_twin(); SP = FR._sess_params()
    OUT = {"CL": {}, "MA": {}}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]
            m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            t = tt[m] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            # ---- MA (전 세션, held-out 포함) ----
            Lm = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                                    float(d["q1"][i0]), float(d["q2"][i0]),
                                    float(d["dq1"][i0]), float(d["dq2"][i0]),
                                    float(t[-1] - 0.004), bias1=sp["bias1"],
                                    knee_deep=sp["knee_deep"], fade=True)
            if Lm is not None:
                gm = lambda k: np.interp(t, Lm["t"], Lm[k])
                OUT["MA"].setdefault(s, []).append(
                    rmse6(d, m, gm("thm1"), gm("q2"), gm("dq1"), gm("dq2"), gm("s1"), gm("s2")))
            # ---- CL (fit 세션만) ----
            if not ho and g:
                init = tuple(float(d[k][i0]) for k in ("q1", "q2", "dq1", "dq2", "raw1", "raw2"))
                Lc = FR.rollout_cl_fs(ft, t, sh(d["qd1"][m]), sh(d["qd2"][m]),
                                      sh(d["dqd1"][m]), sh(d["dqd2"][m]),
                                      tuple(g), float(t[-1]), two_stage=True, bias1=sp["bias1"],
                                      knee_deep=sp["knee_deep"], fade=True, taulim=None,
                                      vdes_ff=(s != "26.04.21"), init_meas=init)
                if Lc is not None:
                    gc = lambda k: np.interp(t, Lc["t"], Lc[k])
                    OUT["CL"].setdefault(s, []).append(
                        rmse6(d, m, gc("thm1"), gc("q2"), gc("dq1"), gc("dq2"),
                              np.clip(gc("s1f"), -20.5, 20.5), gc("s2")))
            print(f"{s}/{p.name}: OK", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    return OUT


def guard(cur, ref):
    """MA 가드: 세션×채널(q1,q2) 악화 ≤ max(ref×5%, 0.05). CL은 세션합 표만."""
    bad = []
    for s in sorted(ref["MA"]):
        if s not in cur["MA"]:
            bad.append((s, "누락", 0, 0)); continue
        a = np.mean(ref["MA"][s], axis=0); b = np.mean(cur["MA"][s], axis=0)
        for i in (0, 1):
            tol = max(a[i] * 0.05, 0.05)
            if b[i] - a[i] > tol:
                bad.append((s, CH[i], a[i], b[i]))
    return bad


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "x"
    OUT = run_board()
    safe.atomic_json_write(HERE / f"_F_uboard_{tag}.json", OUT)
    for md in ("CL", "MA"):
        print(f"\n=== U-보드 {md} (세션 평균) ===")
        tot = np.zeros(6)
        for s in sorted(OUT[md]):
            a = np.mean(OUT[md][s], axis=0); tot += a
            print(f"{s}: " + " ".join(f"{c} {v:.2f}" for c, v in zip(CH, a)))
        print("세션합: " + " ".join(f"{v:.2f}" for v in tot))
    if len(sys.argv) > 2:
        ref = safe.read_json(HERE / f"_F_uboard_{sys.argv[2]}.json")
        bad = guard(OUT, ref)
        print("\n=== MA 가드 (상대 max(+5%, +0.05)) ===")
        if bad:
            for s, ch, a, b in bad:
                print(f"  ★위반 {s} {ch}: {a:.2f}→{b:.2f}")
        else:
            print("  전 세션 통과")
    print("done", flush=True)


if __name__ == "__main__":
    main()
