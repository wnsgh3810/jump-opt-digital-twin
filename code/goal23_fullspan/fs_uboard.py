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


# ★ 08-09: l_i 하드코딩 폐지. **trial 마다 그 trial 의 Clutch.xlsx 중앙값**을 쓴다
#   (`fs_data.cvt_li`, 사용자 지시). 구 값 0.02499 는 "실측"으로 적혀 있었으나
#   센서 실측 범위는 25.06~25.10mm 이고 24.99 는 그 밖이다 —
#   실제 출처는 "25.08 대신 24.99 가 ModeA 전수 개선" = **점수에 맞춘 값**이었다.


def _cvt_ft(ft0, li):
    """0429(CVT l_i≠30) 전용 트윈 — **이 trial 의 l_i** 로 모델·초기화·전달비를 전부 맞춘다.

    l_i 는 4절 입력 링크의 **치수**라 모델을 다시 지어야 한다 (l_i 2mm 차 → body_pos 2mm 차 검증).
    초기화(cvt_init)만 바꾸고 모델을 두면 t=0 에 루프 구속이 어긋나 솔버가 스냅한다.
    """
    import fs_cvt as FC
    import mujoco as mjm
    from cvt_core import qpos_from_crank
    li = float(li)
    model_c, model_cf, ctx = FC.build_cvt_pair(li)
    if model_cf is None:
        raise RuntimeError(f"fs 패치 CVT 모델 없음 (l_i={li})")
    ft = dict(ft0)
    ft["model"] = model_cf
    ft["iq"] = {n: safe.qadr(model_cf, n, mjm) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(model_cf, n, mjm) for n in ft["iq"]}
    ft["cvt_init"] = lambda q1, q2, _l=li: qpos_from_crank(1.0, -q1 - np.pi / 2, -q2, _l)[0]
    qg, rg = FC.RU.rtab(li)
    ft["cvt_diss"] = (float(ctx["nm"]["C_CVT"]), qg, rg)
    return ft


def run_board():
    ft0 = FR.fs_twin(); SP = FR._sess_params()
    _cv = {}       # CVT 트윈 지연 생성 캐시 (실패 시 None → 해당 세션만 건너뜀)
    OUT = {"CL": {}, "MA": {}}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            _li = FD.cvt_li(p)                     # ★ 이 trial 의 센서 실측
            _k = round(_li, 7)
            if _k not in _cv:
                try:
                    _cv[_k] = _cvt_ft(ft0, _li)
                except Exception as ex:
                    print(f"CVT 트윈 생성 실패 (l_i={_li*1000:.3f}mm) → {s}/{p.name} 건너뜀: "
                          f"{type(ex).__name__} {ex}", flush=True)
                    _cv[_k] = None
            if _cv[_k] is None:
                continue
            ft = _cv[_k]
        else:
            ft = ft0
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
            sp = FR.sess_params(s)      # ★ G63: FS_NOBIAS/FS_NODEEP 존중 (단일 출처)
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
            # ---- CL (PD 폐루프가 성립하는 전 세션 = 게이트 0421 포함, FF 0324 제외) ----
            # 마라톤G 08-02: 0421이 게이트로 이동하며 ho=True가 됨 — 조건을 ho가 아니라
            # **제어 모드**로 판정해야 0421 CL이 조용히 누락되지 않는다.
            if s not in FD.FF_SESS and g:
                init = tuple(float(d[k][i0]) for k in ("q1", "q2", "dq1", "dq2", "raw1", "raw2"))
                # ★ G64: 커맨드층 노브 (기본 1.0/1.0 = 기존 `tuple(g)` 와 **완전 동일**).
                #   FS_TKOVR = 무릎 kp 배율(α) · FS_KDSC = 무릎 kd 배율.
                #   토크맵을 바꾸면 폐루프 실효 강성이 바뀌므로 α 를 되물어야 한다 (철칙 10).
                #   FS_TKMODE=table  → 무릎 α 를 **배포 TK 표(로그보간)** 에서 조회, kd×0.20.
                #     (사용자 지시 08-08: "α=1 로 통일할 게 아니라 TK 표대로 통일해서 비교")
                #   기본(미설정) 은 α=1·kd=1 = 기존 `tuple(g)` 와 완전 동일.
                if os.environ.get("FS_TKMODE") == "table":
                    _tko = FR.alpha_of(g[2]); _kds = 0.20
                else:
                    _tko = float(os.environ.get("FS_TKOVR", "1.0"))
                    _kds = float(os.environ.get("FS_KDSC", "1.0"))
                gcl = (g[0], g[1], g[2] * _tko, g[3] * _kds)
                Lc = FR.rollout_cl_fs(ft, t, sh(d["qd1"][m]), sh(d["qd2"][m]),
                                      sh(d["dqd1"][m]), sh(d["dqd2"][m]),
                                      gcl, float(t[-1]), two_stage=True, bias1=sp["bias1"],
                                      knee_deep=sp["knee_deep"], fade=True, taulim=None,
                                      vdes_ff=FD.vdes_applied(s), init_meas=init)
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
        tot = np.zeros(6); ftot = np.zeros(6); nf = 0
        for s in sorted(OUT[md]):
            a = np.mean(OUT[md][s], axis=0); tot += a
            k = FD.kind_of(s)
            if k == "fit":
                ftot += a; nf += 1
            print(f"{s} [{k:<7}]: " + " ".join(f"{c} {v:.2f}" for c, v in zip(CH, a)))
        print("세션합(전체): " + " ".join(f"{v:.2f}" for v in tot))
        print(f"fit 평균({nf}세션): " + " ".join(f"{v:.2f}" for v in (ftot / max(nf, 1))))
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
