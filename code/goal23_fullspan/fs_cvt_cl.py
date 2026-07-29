# -*- coding: utf-8 -*-
"""fs_cvt_cl — 0429 CVT 세션 CL 6채널 편입 (Day2: 사상 첫 CVT 폐루프 채점).

구성: fs 6q CVT 모델(build_cvt_pair) + 폴더 게인 PD (crank측 — CVT 커맨드는 크랭크 좌표) +
CVT 층의 CL화 (데이터 벡터 → 순간값 스칼라 미러):
  supp = supp_scalar(s2,v2)+rise · hip_supp_scalar · hl = h_load(|s2|, spr[2]) ·
  C_CVT qfrc(rtab 전달비) · 2단 스프링 qfrc + bias1(F21 하강 감사) + fade.
τ1 관측: w 세션 상수(_fs_tauobs_w, F35: 0429=0.0 스프링측) + tau_lim=15 클립 (What.txt 문서 출처).
knee_deep 미적용 (크랭크↔무릎 매핑 미정). 게이트: 동일 모델의 재생 골든(golden3 2.389) 기재현으로 갈음.
CLI: python fs_cvt_cl.py [tk0]  (tk0 = crank 게인 TK 스케일 미적용 변형 — 판별)
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD                     # noqa: E402
import fs_cvt as FC                      # noqa: E402
import fs_model as FM                    # noqa: E402
import fs_runner as FR                   # noqa: E402
import safe                              # noqa: E402

TW = FC.TW
RU = FC.RU
from cvt_core import qpos_from_crank     # noqa: E402
import p23_v6_runners as V6              # noqa: E402

L_I = 0.02508
TAU_LIM_DOC = 15.0                       # What.txt 0429 기록 (문서 출처)
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}


def rollout_cl_cvt(model, tw, nm, d, gains, t_end, use_tk=True, bias1=0.53):
    P = tw["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = tw["law"]; kr = tw["kr"]
    ks = kref = None
    if tw["spr"] is not None:
        ks, kref, _ = RU.spr_resolve(model, tw["spr"])
    o1, o2, cc = float(nm["o1_429"]), float(nm["o2_429"]), float(nm["C_CVT"])
    qg, rg = RU.rtab(L_I)
    iq = {n: safe.qadr(model, n, mj) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    dof = {n: safe.dofadr(model, n, mj) for n in iq}
    kp1, kd1, kp2, kd2 = gains
    if use_tk:
        kp2 = kp2 * TK.get(gains[2], 0.656)
        kd2 = kd2 * 0.20
    q1_0 = float(d["qd1"][0]) + o1
    q2_0 = float(d["qd2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    base5 = qpos_from_crank(1.0, sq1, sq2, L_I)[0]
    s1_0 = float(P.J.ahat(P.A_PAPER, np.array([d["raw1"][0]]), np.array([d["dq1"][0]]))[0])
    defl0 = float(np.clip(np.sign(s1_0) * (abs(s1_0) / 96.0 if abs(s1_0) <= 9 else 9 / 96.0 + (abs(s1_0) - 9) / 323.0), -0.3, 0.3))
    md.qpos[iq["base_z"]] = base5[0]
    md.qpos[iq["hip_m"]] = base5[1] - defl0
    md.qpos[iq["hip"]] = defl0
    md.qpos[iq["knee_motor"]] = base5[2]
    md.qpos[iq["cpin"]] = base5[3]
    md.qpos[iq["knee"]] = base5[4]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    tc_f = float(os.environ.get("FS_TC", "0.010"))
    af = dt / max(tc_f, dt)
    s1f = 0.0
    t = d["t"]
    NT = int(round((P.J.T_SETTLE + t_end + 0.05) / dt))
    tl = np.arange(NT) * dt - P.J.T_SETTLE
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "tsp1", "s1f", "s2sup")
    Lg = {k: np.zeros(NT) for k in keys}
    for k in range(NT):
        tc = tl[k]
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        if tc < 0:
            c1 = S.SETTLE_KP * (q1_0 - thm) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        elif tc <= t_end:
            tm_ = min(tc, t[-1])
            qd1 = float(np.interp(tm_, t, d["qd1"])) + o1
            qd2 = float(np.interp(tm_, t, d["qd2"])) + o2
            dqd1 = float(np.interp(tm_, t, d["dqd1"]))
            dqd2 = float(np.interp(tm_, t, d["dqd2"]))
            c1 = kp1 * (qd1 - thm) + kd1 * (dqd1 - v1c)
            c2 = kp2 * (qd2 - q2c) + kd2 * (dqd2 - v2c)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(P.A_PAPER, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(P.A_PAPER, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        rr = float(np.interp(md.qpos[iq["knee_motor"]], qg, rg))
        amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
        vk = float(md.qvel[dof["knee"]])
        tql = -cc * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if ks is not None:
            hl = float(V6.h_load(np.array([abs(s2)]), tw["spr"][2])[0])
            tql += ks * (kref - float(md.qpos[iq["knee"]])) * hl
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        dq_s = float(md.qpos[iq["hip"]])
        corr = FM.KS_HIP * dq_s - FR._tau2s(dq_s)
        b_eff = bias1
        if abs(v1c) > 1.0:
            b_eff = bias1 * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)
        md.qfrc_applied[dof["hip"]] = corr + b_eff
        mj.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        Lg["t"][k] = tc
        Lg["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
        Lg["q1"][k] = -(md.qpos[iq["hip_m"]] + md.qpos[iq["hip"]]) - np.pi / 2
        Lg["q2"][k] = -md.qpos[iq["knee_motor"]]
        Lg["dq1"][k] = -md.qvel[dof["hip_m"]]
        Lg["dq2"][k] = -md.qvel[dof["knee_motor"]]
        Lg["s1"][k] = s1
        Lg["s2"][k] = s2
        Lg["s2sup"][k] = s2 + supp
        Lg["tsp1"][k] = FR._tau2s(dq_s) + b_eff
        s1f += af * (s1 - s1f)
        Lg["s1f"][k] = s1f
    return Lg


def main():
    use_tk = not (len(sys.argv) > 1 and sys.argv[1] == "tk0")
    model_c, model_cf, ctx = FC.build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    SP = FR._sess_params()
    b = SP.get("26.04.29", {}).get("bias1", 0.53)
    wj = HERE / "_fs_tauobs_w.json"
    w29 = float(safe.read_json(wj).get("26.04.29", 0.5)) if wj.exists() else 0.5
    o1 = float(nm["o1_429"]); o2 = float(nm["o2_429"])
    OUT = {"score": [], "push": []}
    for s, p, g, cvt, ho in FD.registry():
        if not cvt or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception as ex:
            print(f"{p.name}: 로드 FAIL {type(ex).__name__}", flush=True)
            continue
        i0 = max(0, seg["i_desc"] - 5)
        dd = {k: d[k][i0:] for k in ("qd1", "qd2", "dqd1", "dqd2", "raw1", "dq1",
                                     "q1", "q2", "dq2", "a1", "a2")}
        dd["t"] = d["t"][i0:] - d["t"][i0]
        L = rollout_cl_cvt(model_cf, tw, nm, dd, g, float(seg["t_lo"] - d["t"][i0]),
                           use_tk=use_tk, bias1=b)
        if L is None:
            print(f"{p.name}: 발산", flush=True)
            continue
        t = dd["t"]
        gi = lambda k: np.interp(t, L["t"], L[k])
        obs = np.clip(w29 * gi("s1f") + (1 - w29) * gi("tsp1"), -TAU_LIM_DOC, TAU_LIM_DOC)
        res = {}
        for wn in ("score", "push"):
            m = seg[wn][i0:][: len(t)]
            # q1 채널 = 인코더(thm1) 기준 — 실측 q1은 모터측 (F15 교훈: 사지각 비교는 처짐 유령)
            r = [float(np.degrees(np.sqrt(np.mean((dd["q1"][m] + o1 - gi("thm1")[m]) ** 2)))),
                 float(np.degrees(np.sqrt(np.mean((dd["q2"][m] + o2 - gi("q2")[m]) ** 2)))),
                 float(np.sqrt(np.mean((dd["dq1"][m] - gi("dq1")[m]) ** 2))),
                 float(np.sqrt(np.mean((dd["dq2"][m] - gi("dq2")[m]) ** 2))),
                 float(np.sqrt(np.mean((dd["a1"][m] - obs[m]) ** 2))),
                 float(np.sqrt(np.mean((dd["a2"][m] - gi("s2")[m]) ** 2)))]
            OUT[wn].append(r)
            res[wn] = r
        print(f"{p.name}: push q1 {res['push'][0]:.2f} q2 {res['push'][1]:.2f} dq1 {res['push'][2]:.2f} "
              f"dq2 {res['push'][3]:.2f} t1 {res['push'][4]:.2f} t2 {res['push'][5]:.2f}", flush=True)
    for wn in ("score", "push"):
        if OUT[wn]:
            a = np.mean(OUT[wn], axis=0)
            print(f"\n0429 CL {wn} 평균 (TK {'on' if use_tk else 'off'}): "
                  f"q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} t1 {a[4]:.2f} t2 {a[5]:.2f}", flush=True)
    safe.atomic_json_write(HERE / ("_fs_cvt_cl_" + ("tk" if use_tk else "tk0") + ".json"), OUT)
    print("done", flush=True)


if __name__ == "__main__":
    main()
