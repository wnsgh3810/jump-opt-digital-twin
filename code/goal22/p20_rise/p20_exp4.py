# -*- coding: utf-8 -*-
"""P20 실험 4 — 마찰 이력 가설의 반증 검사 2종 (기존 데이터만으로).

검사 A (부호 반전): s2s_0319 창별 λ*를 운동 방향(sign dq2)별로 분리.
  · 운동마찰(무기억)이라면: 내려갈 때/올라갈 때 λ* 부호 반전
  · 하중-지지(정지마찰 흡수)라면: 방향 무관 λ* ≈ +1.0 유지
검사 B (부하 스케일링 + 동일세션 l_i 대조): 26.06.04 페이로드 s2s.
  · A3형 부하비례 마찰이면: 기준선 ∝ 평균|Iq| (payload 0→5kg 증가)
  · 같은 날 no_cvt(30mm) vs cvt(25.2mm) 기준선 비교 → l_i 무관성 세션내 확정
프로토콜: exp3의 closure 리셋 + FK-bz (검증됨), λ 그리드 [-2,4].
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E
import p19_judge as P
from cvt_core import closure

sys.path.insert(0, str(HERE.parent / "p18_cvt"))
import s2s_0604 as S0

mj = P.J._P["mj"]
S = P.J._P["S"]
MS = E.P12._G["MS"]
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_p20_results")
LGRID = np.arange(-2.0, 4.01, 0.5)


def fk_bz(model, data, q1mj, qcmj, l_i, qk_prev):
    qk, qp, _ = closure(float(qcmj), l_i, qk_prev)
    data.qpos[:] = [1.0, q1mj, qcmj, qp, qk]
    data.qvel[:] = 0
    mj.mj_forward(model, data)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(data.geom_xpos[fg][2]) + S.FOOT_RADIUS, qk, qp


def win_scan(model, d, l_i, starts, W, o1=0.0, o2=0.0):
    """각 창 t0에서 λ 그리드 스캔 → (t0, dq_signed, |Iq|평균, λ*) 목록."""
    t = d["t"]
    th = np.interp(t - P.SD, t, P.J.ahat(E.A, d["traw1"], d["dq1"]))
    tk0 = np.interp(t - P.SD, t, P.J.ahat(E.A, d["traw2"], d["dq2"]))
    q1mj = -(d["q1"] + o1) - np.pi / 2
    qcmj = -(d["q2"] + o2)
    data = mj.MjData(model)
    bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
    qk_prev = None
    for i in range(len(t)):
        bz[i], qk_prev, qp_ = fk_bz(model, data, q1mj[i], qcmj[i], l_i, qk_prev)
        qks[i] = qk_prev; qps[i] = qp_
    vbz = np.gradient(bz, t)
    dt = model.opt.timestep
    out = []
    from p14_judge import KT, GR, CF
    for t0 in starts:
        i0 = int(np.searchsorted(t, t0))
        if i0 >= len(t) - 5:
            continue
        t1 = min(t0 + W, t[-1])
        qk2, qp2, _ = closure(float(qcmj[i0]) + 1e-4, l_i, qks[i0])
        r_ = (qk2 - qks[i0]) / 1e-4; gp = (qp2 - qps[i0]) / 1e-4
        dqc = -d["dq2"][i0]
        scores = []
        for lam in LGRID:
            data.qpos[:] = [bz[i0], q1mj[i0], qcmj[i0], qps[i0], qks[i0]]
            data.qvel[:] = [vbz[i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
            mj.mj_forward(model, data)
            nst = int(round((t1 - t0) / dt))
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                data.ctrl[:] = [-float(np.interp(tc, t, th)),
                                -float(np.interp(tc, t, tk0) + lam)]
                try:
                    mj.mj_step(model, data)
                except Exception:
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
                dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
            if not ok:
                scores.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                scores.append(np.nan); continue
            r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            scores.append(MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
                          + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
        scores = np.array(scores)
        if np.isnan(scores).any() or (scores.max() - scores.min()) / max(scores.min(), 1e-9) < 0.02:
            continue
        i = int(np.argmin(scores))
        if i in (0, len(LGRID) - 1):
            ls = float(LGRID[i])
        else:
            a, b, c = scores[i - 1], scores[i], scores[i + 1]
            den = a - 2 * b + c
            ls = float(LGRID[i] + np.clip(0.5 * (a - c) / den if abs(den) > 1e-12 else 0, -1, 1) * 0.5)
        wm = (t >= t0) & (t <= t1)
        iq = float(np.mean(np.abs((CF / (GR * KT)) * d["traw2"][wm])))
        out.append(dict(t0=float(t0), dq=float(d["dq2"][i0]), iq=iq, lam=ls))
    return out


def main():
    rows = []
    # ── 검사 A: s2s_0319 방향별 (P12 캐시 → d형 변환) ──
    model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
    for tr in E.P12._G["trials"]:
        if tr["ds"] != "s2s_gnd_0319":
            continue
        pp = tr["pp"]; t = pp["t"]
        d = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                 dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                 traw1=tr["raw1"], traw2=tr["raw2"])
        starts = np.arange(0.4, t[-1] - 0.4, 0.45)
        for r_ in win_scan(model_f, d, 0.030, starts, 0.2):
            rows.append(dict(grp="A_s2s0319", sub=str(tr["sub"]), **r_))
        print(f"A s2s/{tr['sub']} done", flush=True)
    # ── 검사 B: 0604 페이로드 (cvt 0/2.5/5kg + no_cvt 0kg, 같은 세션) ──
    for grp, sub, load in [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5),
                           ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0.0)]:
        d = S0.load_0604(grp, sub)
        li = d["l_i"]
        model, _ = (P.build_cvt(E.X32, E.V[1], E.SP, li) if grp == "cvt"
                    else P.build_flip(E.X32, E.V[1], E.SP))
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load          # 페이로드 = base 질량 (P18c 규약)
        starts = np.arange(0.3, d["t"][-1] - 0.3, 0.35)
        for r_ in win_scan(model, d, li, starts, 0.2):
            rows.append(dict(grp=f"B_0604_{grp}_{sub}", sub=sub, load=load, **r_))
        print(f"B 0604 {grp}/{sub} done", flush=True)
    json.dump(rows, open(DST / "exp4_rows.json", "w"), indent=1)
    # ── 판정 A ──
    a = [r for r in rows if r["grp"] == "A_s2s0319"]
    dn = [r["lam"] for r in a if r["dq"] < -0.15]
    up = [r["lam"] for r in a if r["dq"] > 0.15]
    print(f"\n[검사 A] s2s 내려갈 때(v<0) λ* {np.mean(dn):+.2f}±{np.std(dn):.2f} (n={len(dn)}) | "
          f"올라갈 때(v>0) λ* {np.mean(up):+.2f}±{np.std(up):.2f} (n={len(up)})", flush=True)
    print("  → 부호 반전이면 운동마찰형 / 동일 부호면 하중-지지형(정지마찰 흡수)", flush=True)
    # ── 판정 B ──
    print("\n[검사 B] 0604 같은 세션 — 저속 기준선 vs 부하/l_i")
    for g in sorted(set(r["grp"] for r in rows if r["grp"].startswith("B"))):
        rs = [r for r in rows if r["grp"] == g and abs(r["dq"]) < 1.5]
        lam = [r["lam"] for r in rs]; iq = [r["iq"] for r in rs]
        print(f"  {g:26s} λ* {np.mean(lam):+.2f}±{np.std(lam):.2f} (n={len(rs)}, ⟨|Iq|⟩ {np.mean(iq):.1f}A)",
              flush=True)


if __name__ == "__main__":
    main()
