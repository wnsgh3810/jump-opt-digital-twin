# -*- coding: utf-8 -*-
"""P22 exp — CVT 가지 전용 부하종속 전달손실의 시뮬 반증 시험.

0c 판정: 0429 에너지 잔차 = 무릎 채널 일의 9→25% (강도 단조), 푸시 말미(r→0.38) 집중.
가설 모델 (둘 다 r=1에서 자동 소멸 → l_i=30 세션 무접촉):
  (a) 쿨롱형: τ_loss = c·|s₂|·(1/r − 1)·tanh(v_k/1.0)   [부하×구속증폭 비례 마찰]
  (b) 점성형: τ_loss = c·|s₂|·(1/r − 1)·v_k              [부하종속 점성]
지표: 0429 전 10 subs Mode A 통짜 재생 — dq2 RMSE (P19 앵커 3.31), h_sim 평균,
      소산 에너지/trial (0c 잔차 목표 2.4~9.7 J와 대조).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C
import p22_rebase as RB
import safe


def r_table(l_i, qc_lo=-3.0, qc_hi=3.0, n=601):
    """MJ 크랭크각 그리드 → 전달비 r=dqk/dqc 보간 테이블."""
    from cvt_core import closure
    qs = np.linspace(qc_lo, qc_hi, n)
    rs = np.ones(n)
    qk_prev = None
    for i, x in enumerate(qs):
        try:
            qk, _, _ = closure(float(x), l_i, qk_prev)
            qk2, _, _ = closure(float(x) + 1e-4, l_i, qk)
            rs[i] = (qk2 - qk) / 1e-4
            qk_prev = qk
        except Exception:
            rs[i] = rs[i - 1] if i else 1.0
    return qs, rs


def replay_0429(v, form, c, subs=None):
    """a429_full (p21_polish) 복제 + CVT 손실 항. 반환: per-sub dict."""
    import p19_judge as P
    from cvt_core import load_0429, SUBS429, qpos_from_crank
    mj = P.J._P["mj"]; S = P.J._P["S"]
    x32, sp = C.x32_of(v)
    model, _ = P.build_cvt(x32, v[1], sp, 0.02508)
    dof_knee = safe.dofadr(model, "knee")
    qg, rg = r_table(0.02508)
    rmse = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
    out = []
    for sub in (subs or SUBS429):
        d = load_0429(sub); t = d["t"]
        lam = C.lam_vec(d["traw2"], d["dq2"], v[15], v[16])
        t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
        md = mj.MjData(model)
        sq1, sq2 = -(d["q1"][0]) - np.pi / 2, -(d["q2"][0])
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, d["l_i"])[0]
        mj.mj_forward(model, md)
        fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
        md.qvel[:] = 0; mj.mj_forward(model, md)
        dt = model.opt.timestep
        N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
        tl = np.arange(N) * dt - P.J.T_SETTLE
        dq2s = np.zeros(N); bzs = np.zeros(N)
        E_diss = 0.0
        crash = False
        for k in range(N):
            tc = tl[k]
            if tc < 0:
                q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
                c1 = S.SETTLE_KP * (-(sq1 + np.pi / 2) - q1c) - S.SETTLE_KD * (-md.qvel[1])
                c2 = S.SETTLE_KP * (-sq2 - q2c) - S.SETTLE_KD * (-md.qvel[2])
                s1 = float(P.J.ahat(P.A_PAPER, np.array([c1]), np.array([-md.qvel[1]]))[0])
                s2 = float(P.J.ahat(P.A_PAPER, np.array([c2]), np.array([-md.qvel[2]]))[0])
            else:
                tm_ = min(tc, t[-1])
                s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
                if tc > t[-1]:
                    s1 = s2 = 0.0
            md.ctrl[:] = [-s1, -s2]
            # ── CVT 전달손실 (r=1에서 자동 소멸) ──
            if c > 0:
                r = float(np.interp(md.qpos[2], qg, rg))
                amp = max(1.0 / max(abs(r), 0.2) - 1.0, 0.0)
                vk = float(md.qvel[dof_knee])
                if form == "coulomb":
                    tl_ = -c * abs(s2) * amp * float(np.tanh(vk / 1.0))
                else:
                    tl_ = -c * abs(s2) * amp * vk
                md.qfrc_applied[dof_knee] = tl_
                E_diss += -tl_ * vk * dt
            try:
                mj.mj_step(model, md)
            except Exception:
                crash = True
                break
            dq2s[k] = -md.qvel[2]; bzs[k] = md.qpos[0]
        if crash:
            out.append(dict(sub=sub, e=9.9, h=0.0, E=0.0, crash=True))
            continue
        m = t <= t[-1]
        out.append(dict(sub=sub, e=rmse(np.interp(t, tl, dq2s)[m], d["dq2"][m]),
                        h=float(bzs[tl > 0].max()), E=float(E_diss), crash=False))
    return out


def main():
    C.winit_worker(dict(CL=1, DQ=1, JW2=1, J6J=1, J6C=1, S2S=1, O6=1, raw=True))
    v = RB.x19_vec()
    res = {}
    print("form c | dq2RMSE(mean) h(mean) E_diss(mean/min/max) crash", flush=True)
    for form, grid in [("coulomb", [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]),
                       ("viscous", [0.005, 0.01, 0.02, 0.04, 0.08])]:
        for c in grid:
            if form == "viscous" and c == 0.0:
                continue
            rows = replay_0429(v, form, c)
            es = [r["e"] for r in rows]; hs = [r["h"] for r in rows]
            Es = [r["E"] for r in rows]; nc = sum(r["crash"] for r in rows)
            key = f"{form}:{c}"
            res[key] = rows
            print(f"{form:8s} {c:5.3f} | {np.mean(es):.3f} {np.mean(hs):.3f} "
                  f"{np.mean(Es):.1f}/{np.min(Es):.1f}/{np.max(Es):.1f} J  crash={nc}",
                  flush=True)
    safe.atomic_json_write(HERE / "p22_exp_cvtloss.json", res)
    print("saved p22_exp_cvtloss.json", flush=True)


if __name__ == "__main__":
    main()
