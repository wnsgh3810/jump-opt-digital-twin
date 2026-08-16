# -*- coding: utf-8 -*-
"""P20 실험 3 — 0429(CVT)에 창별 λ* 정밀 측정 (빠져 있던 결정적 측정).

동기: "0429는 보정 불필요" 판정은 총점(sc429) 비교였고, 각도 오프셋 o1/o2가
자유 적합된 상태라 상승 성분이 흡수돼 숨었을 수 있다. l_i=30 세션들과 동일한
창(window) 프로토콜로 0429의 λ*(t)를 직접 잰다.
  - 0429에도 상승(+수 Nm, 푸시 후반)이 보이면: 모터측(a_hat) 가설 부활 + 그림 통일
  - 정말 평탄 ~0이면: l_i=30 특이성 확정 (기계 구성 쪽)
방법: stance 한정 창 (W=0.12s, 시작 0.02~toff-0.06 step 0.03) — bz는 접촉 FK로
재구성 (fk_bz 패턴), 리셋은 closure 기반 (li_offset_probe 검증 패턴).
비교군: 0602/0424도 같은 W=0.12 프로토콜로 재측정 (사과-사과 비교).
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
from cvt_core import closure, qpos_from_crank, load_0429, SUBS429
from cvt_run2 import takeoff_time

mj = P.J._P["mj"]
S = P.J._P["S"]
MS = E.P12._G["MS"]
DST = Path((LEGACY_ROOT + "/g22_p20_results"))
LGRID = np.arange(-2.0, 5.01, 0.5)
W = 0.12
O1, O2 = 3.14 * np.pi / 180, -3.0 * np.pi / 180   # P18b/cma2 0429 프로토콜 오프셋


def fk_bz_cvt(model, data, q1mj, qcmj, l_i, qk_prev):
    qk, qp, _ = closure(float(qcmj), l_i, qk_prev)
    data.qpos[:] = [1.0, q1mj, qcmj, qp, qk]
    data.qvel[:] = 0
    mj.mj_forward(model, data)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS, qk, qp


def win_lam_429(model, d, l_i, lam, lam_base=0.0):
    """0429 stance 창 점수 (λ 보정) — closure 리셋 + FK-bz."""
    t = d["t"]
    toff = takeoff_time(t, d["grf_real"])
    th = np.interp(t - P.SD, t, P.J.ahat(E.A, d["traw1"], d["dq1"]))
    tk = np.interp(t - P.SD, t, P.J.ahat(E.A, d["traw2"], d["dq2"]))
    q1mj = -(d["q1"] + O1) - np.pi / 2
    qcmj = -(d["q2"] + O2)
    data = mj.MjData(model)
    # stance FK: bz(t), qk(t), qp(t)
    bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
    qk_prev = None
    for i in range(len(t)):
        bz[i], qk_prev, qp_ = fk_bz_cvt(model, data, q1mj[i], qcmj[i], l_i, qk_prev)
        qks[i] = qk_prev; qps[i] = qp_
    vbz = np.gradient(bz, t)
    dt = model.opt.timestep
    out = []
    tk_l = tk + lam_base + lam
    tk_l0 = th
    starts = np.arange(0.02, max(toff - 0.05, 0.03), 0.015)
    for t0 in starts:
        i0 = int(np.searchsorted(t, t0))
        t1 = min(t0 + W, t[-1])
        # closure 관절 속도 (수치미분)
        qk2, _, _ = closure(float(qcmj[i0]) + 1e-4, l_i, qks[i0])
        r_ = (qk2 - qks[i0]) / 1e-4
        qp2 = closure(float(qcmj[i0]) + 1e-4, l_i, qks[i0])[1]
        gp = (qp2 - qps[i0]) / 1e-4
        dqc = -d["dq2"][i0]
        data.qpos[:] = [bz[i0], q1mj[i0], qcmj[i0], qps[i0], qks[i0]]
        data.qvel[:] = [vbz[i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
        mj.mj_forward(model, data)
        nst = int(round((t1 - t0) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t0 + k * dt
            data.ctrl[:] = [-float(np.interp(tc, t, tk_l0)) if False else -float(np.interp(tc, t, th)),
                            -float(np.interp(tc, t, tk_l))]
            try:
                mj.mj_step(model, data)
            except Exception:
                ok = False; break
            ts[k] = tc + dt
            q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
            dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
        if not ok:
            out.append((t0, MS.W_Q * 2 + MS.W_DQ * 20)); continue
        mk = (t >= ts[0]) & (t <= ts[-1])
        if mk.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
        sc = (MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
              + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
        out.append((t0, sc))
    return out


def lam_star(scores):
    i = int(np.argmin(scores))
    if i in (0, len(LGRID) - 1):
        return float(LGRID[i])
    a, b, c = scores[i - 1], scores[i], scores[i + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return float(LGRID[i] + np.clip(off, -1, 1) * 0.5)


def flip_windows_W(tr, lam):
    """l_i=30 비교군 — 같은 W=0.12 프로토콜 (E.win_scores는 pp W 사용이라 별도)."""
    pp0 = tr["pp"]; t = pp0["t"]
    k1, k2 = E.P12.OFFKEY.get(tr["ds"], (None, None))
    o1 = E.DD[k1] if k1 else 0.0
    o2 = E.DD[k2] if k2 else 0.0
    th = -(P.J.ahat(E.A, tr["raw1"], tr["v1"]))
    tk = -(P.J.ahat(E.A, tr["raw2"], tr["v2"]) + lam)
    ppv = dict(pp0, tau_h=np.interp(t - P.SD, t, th), tau_k=np.interp(t - P.SD, t, tk))
    pp = E.P12._G["sv"](ppv, o1, o2)
    model = FLIP
    d_ = mj.MjData(model); dt = model.opt.timestep
    out = []
    for i0 in [int(i) for i in pp["starts"]]:
        t0 = t[i0]; t1 = min(t0 + W, t[-1])
        qc = float(pp["q2m"][i0]); dqc = float(pp["dq2m"][i0])
        d_.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], qc, -qc, qc]
        d_.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dqc, -dqc, dqc]
        mj.mj_forward(model, d_)
        nst = int(round((t1 - t0) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t0 + k * dt
            d_.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            try:
                mj.mj_step(model, d_)
            except Exception:
                ok = False; break
            ts[k] = tc + dt
            q1a[k] = d_.qpos[1]; q2a[k] = d_.qpos[2]
            dq1a[k] = d_.qvel[1]; dq2a[k] = d_.qvel[2]
        if not ok:
            out.append((t0, MS.W_Q * 2 + MS.W_DQ * 20)); continue
        mk = (t >= ts[0]) & (t <= ts[-1])
        if mk.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
        out.append((t0, MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
                    + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"]))))
    return out


def main():
    global FLIP
    rows = []
    # ── 0429: 6 subs ──
    from cvt_core import SUBS429 as subs
    model_c = None
    for sub in subs:
        d = load_0429(sub)
        if model_c is None:
            model_c, _ = P.build_cvt(E.X32, E.V[1], E.SP, d["l_i"])
        percfg = {}
        for lam in LGRID:
            for t0, sc in win_lam_429(model_c, d, d["l_i"], lam):
                percfg.setdefault(round(t0, 4), []).append(sc)
        for t0, scs in percfg.items():
            scs = np.array(scs)
            if (scs.max() - scs.min()) / max(scs.min(), 1e-9) < 0.02:
                continue
            ls = lam_star(scs)
            i0 = int(np.searchsorted(d["t"], t0))
            rows.append(dict(ds="jump_0429", sub=sub, t0=t0, lam=ls,
                             dq=float(abs(d["dq2"][i0]))))
        print(f"0429/{sub} done", flush=True)
    # ── l_i=30 비교군 (같은 W) ──
    FLIP, _ = P.build_flip(E.X32, E.V[1], E.SP)
    for ds_w, sub_w in [("jump_0602", "150_2.2_500_5"), ("jump_0602", "120_2_120_2"),
                        ("jump_0424", "150_2.2_350_3.5"), ("jump_0424", "120_2_120_2")]:
        tr = next(t_ for t_ in E.P12._G["trials"]
                  if t_["ds"] == ds_w and str(t_["sub"]) == sub_w)
        percfg = {}
        for lam in LGRID:
            for t0, sc in flip_windows_W(tr, lam):
                percfg.setdefault(round(float(t0), 4), []).append(sc)
        pp = tr["pp"]
        for t0, scs in percfg.items():
            scs = np.array(scs)
            if (scs.max() - scs.min()) / max(scs.min(), 1e-9) < 0.02:
                continue
            i0 = int(np.searchsorted(pp["t"], t0))
            rows.append(dict(ds=ds_w, sub=sub_w, t0=t0, lam=lam_star(scs),
                             dq=float(abs(pp["dq2m"][i0]))))
        print(f"{ds_w}/{sub_w} done", flush=True)
    json.dump(rows, open(DST / "exp7_rows.json", "w"), indent=1)
    # ── 집계 ──
    print(f"\n{'세션':12s} {'저속(|dq|<5) λ*':>16} {'고속(|dq|>10) λ*':>17}  n")
    for ds in ("jump_0429", "jump_0602", "jump_0424"):
        rs = [r for r in rows if r["ds"] == ds]
        lo = [r["lam"] for r in rs if r["dq"] < 5]
        hi = [r["lam"] for r in rs if r["dq"] > 10]
        print(f"{ds:12s} {np.mean(lo) if lo else float('nan'):+13.2f}±{np.std(lo) if lo else 0:.2f}"
              f" {np.mean(hi) if hi else float('nan'):+14.2f}±{np.std(hi) if hi else 0:.2f}"
              f"  ({len(lo)}/{len(hi)})", flush=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    for ds in ("jump_0429", "jump_0602", "jump_0424"):
        rs = [r for r in rows if r["ds"] == ds]
        ax.scatter([r["dq"] for r in rs], [r["lam"] for r in rs], s=20, alpha=0.8, label=ds)
    ax.set_xlabel("창 시작 |dq_crank| [rad/s]"); ax.set_ylabel("창별 λ* [Nm]")
    ax.grid(alpha=0.3); ax.legend()
    ax.set_title("0429 vs l_i=30 — 같은 프로토콜(W=0.12) 창별 λ*")
    fig.tight_layout(); fig.savefig(DST / "exp7_429_lambda.png", dpi=110)
    print("saved", DST / "exp7_429_lambda.png", flush=True)


if __name__ == "__main__":
    main()
