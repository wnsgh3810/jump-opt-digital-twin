# -*- coding: utf-8 -*-
"""P22 probe — 0421 고게인 동적 과소속 해부 (P19·p22b 공통 미해결).

관찰: 같은 â를 넣어도 sim 크랭크 피크가 실측의 ~60% (P200 trial). 에너지 원장은 균형(0.97).
질문: 푸시 구간에서 sim의 무릎/힙을 무엇이 붙잡는가 — 스프링? 감쇠? 마찰(constraint)? 관성?
방법: a_full 복제 재생에서 스텝별 qfrc_passive(스프링+감쇠)·qfrc_constraint(마찰/접촉 반영분)·
      입력 â·관성행렬 대각을 로깅, 푸시 구간 평균으로 성분표 산출. 실측 요구 가속과의 잔차 토크도.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe


def replay_probe(v, ds="jump_position_0421", sub="P200_D1.5_P200_D4"):
    import p22_eval as E
    import p21_cma as C
    E.ensure_init()
    P, R = C._W["P"], C._W["R"]
    mj = C._W["mj"]; S = P.J._P["S"]
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    d = next(dd for ds_, sub_, dd, *_ in R.TRIALS if ds_ == ds and str(sub_) == str(sub))
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model, _ = P.build_flip(x32, v[1], sp)
    dd32 = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    k1, k2 = P.J.OFFK.get(ds, (None, None))
    o1 = dd32.get(k1, 0.0) if k1 else 0.0
    o2 = dd32.get(k2, 0.0) if k2 else 0.0
    t = d["t"]
    lam = C.lam_vec(d["traw2"], d["dq2"], v[15], v[16])
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
    q1_0 = float(d["q1"][0]) + o1; q2_0 = float(d["q2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0; mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    nv = model.nv
    L = dict(t=[], dq2=[], tin2=[], pas=[], con=[], M22=[], tin1=[], pas1=[], con1=[])
    Mfull = np.zeros((nv, nv))
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * (-md.qvel[1])
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * (-md.qvel[2])
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([-md.qvel[1]]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([-md.qvel[2]]))[0])
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            if tc > t[-1]:
                s1 = s2 = 0.0
        md.ctrl[:] = [-s1, -(s2 + float(v[19]))]
        mj.mj_step(model, md)
        if 0 <= tc <= t[-1]:
            mj.mj_fullM(model, Mfull, md.qM)
            L["t"].append(tc)
            L["dq2"].append(-md.qvel[2])
            L["tin2"].append(-(s2 + float(v[19])))
            L["pas"].append(float(md.qfrc_passive[2]))
            L["con"].append(float(md.qfrc_constraint[2]))
            L["M22"].append(float(Mfull[2, 2]))
            L["tin1"].append(-s1)
            L["pas1"].append(float(md.qfrc_passive[1]))
            L["con1"].append(float(md.qfrc_constraint[1]))
    return {k: np.array(val) for k, val in L.items()}, d


def report(tag, L, d):
    # 푸시 창: 실측 dq2가 피크의 30%를 넘는 구간
    pk = np.argmax(np.abs(d["dq2"]))
    thr = 0.3 * abs(d["dq2"][pk])
    idx = np.where(np.abs(d["dq2"]) > thr)[0]
    t0, t1_ = d["t"][idx[0]], d["t"][idx[-1]]
    m = (L["t"] >= t0) & (L["t"] <= t1_)
    # sim 좌표: 무릎 dof 2 (MJ 부호는 측정과 반대) — 성분은 MJ frame 그대로 평균
    print(f"\n[{tag}] 푸시 창 {t0:.3f}~{t1_:.3f}s (실측 |dq2|>30%피크)")
    print(f"  입력 |τ_in2| 평균  : {np.mean(np.abs(L['tin2'][m])):7.2f} Nm")
    print(f"  passive(스프링+감쇠) 크랭크: 평균 {np.mean(L['pas'][m]):+7.2f} Nm "
          f"(|.|평균 {np.mean(np.abs(L['pas'][m])):.2f})")
    print(f"  constraint(마찰·폐쇄·접촉) 크랭크: 평균 {np.mean(L['con'][m]):+7.2f} Nm "
          f"(|.|평균 {np.mean(np.abs(L['con'][m])):.2f})")
    print(f"  M[crank,crank] 평균: {np.mean(L['M22'][m]):7.4f} kg·m²")
    print(f"  hip: passive {np.mean(L['pas1'][m]):+7.2f} / constraint {np.mean(L['con1'][m]):+7.2f} Nm")
    print(f"  sim dq2 피크 {np.max(np.abs(L['dq2'])):.1f} vs 실측 {abs(d['dq2'][pk]):.1f} rad/s")


def main():
    import p22_rebase as RB
    gc = safe.read_json(HERE / "p22_gate_check.json")
    xb = np.array(gc["rows"][16]["x"], float)      # p22b (i=29)
    for sub in ("P200_D1.5_P200_D4", "P100_D0.75_P100_D2"):
        for tag, v in (("P19", RB.x19_vec()), ("p22b", xb)):
            L, d = replay_probe(v, sub=sub)
            report(f"{tag} 0421/{sub}", L, d)
    # 0424 고게인 대조
    for tag, v in (("P19", RB.x19_vec()), ("p22b", xb)):
        L, d = replay_probe(v, ds="jump_0424", sub="150_2.2_500_4")
        report(f"{tag} 0424/150_2.2_500_4", L, d)


if __name__ == "__main__":
    main()
