# -*- coding: utf-8 -*-
"""p20_run — P20 2층 보정 러너 (pre30 상수의 세대 교체).

구조 (p20_exp1~9 판별 체인의 산물, HYPOTHESES.md 참조):
  준정적 층: λ_qs = c·τ̂₂·g(|v₂|), g(v)=1/(1+(v/v₀)²) — 정지/저속에서 무릎 부하의
             c(≈0.25)를 지지, 운동 시 소멸. 비례형이라 모터/무릎측 구분 불가(r 소거)
             → 크랭크 좌표 적용. 플랜트측 (명령 로그 제외 — pre30과 동일 규약).
  동적 층 : 무릎 관절(dof 'knee')에 qfrc = −C_d·(1−g(|v_knee|))·tanh(τ̂₂/2)
             — 운동 중 상수형, CVT에선 변속비 축소가 기구학에서 자동 발생.
커맨드층(α·클립 ±35.5·지연 tm)은 P19 그대로. Mode A/창 평가용 입력 벡터 헬퍼 포함.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import p19_judge as P
import p19_run as R
import safe
from cvt_core import closure, qpos_from_crank

C_QS, V0, C_DYN = 0.25, 6.0, 2.5          # exp9a 승자 + exp10 적합 대상


def gate(v, v0=V0):
    return 1.0 / (1.0 + (np.abs(v) / v0) ** 2)


def r_of_crank(qc_meas, l_i, flip=False):
    """측정 크랭크각(측정좌표) 궤적 → 전달비 r(t)=dqk/dqc (flip이면 1)."""
    if flip:
        return np.ones_like(qc_meas)
    mjc = ((-np.asarray(qc_meas) + np.pi) % (2 * np.pi)) - np.pi
    out = np.ones_like(mjc)
    qk_prev = None
    for i, x in enumerate(mjc):
        try:
            qk, _, _ = closure(float(x), l_i, qk_prev)
            qk2, _, _ = closure(float(x) + 1e-4, l_i, qk)
            out[i] = (qk2 - qk) / 1e-4
            qk_prev = qk
        except Exception:
            out[i] = out[i - 1] if i else 1.0
    return out


def lam_input_vec(d, is_cvt, l_i, c=C_QS, v0=V0, Cd=C_DYN):
    """Mode A/창 평가용 무릎(크랭크) 입력 보정 벡터 (측정 신호 기반)."""
    ah = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
    g = gate(d["dq2"], v0)
    qs = c * ah * g
    r = r_of_crank(d["q2"], l_i, flip=not is_cvt)
    vk = np.abs(r * d["dq2"])
    dyn = r * Cd * (1.0 - gate(vk, v0)) * np.tanh(ah / 2.0)
    return qs + dyn


def cl_run20(model, is_cvt, l_i, d, gains, dqdes_on, ffk, A, tm, alphas,
             c_qs=C_QS, v0=V0, Cd=C_DYN, o1=0.0, o2=0.0, preload=0.0):
    """커맨드층 포함 CL + P20 2층 플랜트 보정. (p19_run.cl_run 세대 교체본)"""
    mj = P.J._P["mj"]; S = P.J._P["S"]
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes_on else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes_on else np.zeros_like(t)
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee")
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    if is_cvt:
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
            c1f, c2f = c1, c2
        else:
            tm_ = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm_, t, qd1) - q1c) + kd1 * (np.interp(tm_, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm_, t, qd2) - q2c) + kd2 * (np.interp(tm_, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm_, t, d["tdes2"])
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R.CLIP, R.CLIP)); c2 = float(np.clip(c2, -R.CLIP, R.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        # ── P20 2층 (플랜트측, 로그 제외) ──
        s2_qs = c_qs * s2 * float(gate(v2c, v0))
        vk = float(md.qvel[dof_knee])
        dyn = Cd * (1.0 - gate(vk, v0)) * float(np.tanh(s2 / 2.0))
        md.ctrl[:] = [-s1, -(s2 + s2_qs + preload)]
        md.qfrc_applied[dof_knee] = -dyn
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
    L["t"] = tl
    return L


def eval_stack20(x32, ref, sp, A, tm, c=C_QS, v0=V0, Cd=C_DYN,
                 use_alpha=True, q_off_0429=(0.0548, -0.0524)):
    """p19_run.eval_stack 세대 교체본 — cl_run20 + 지표 v3(gap_v3) 그대로."""
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f, _ = P.build_flip(x32, ref, sp)
    model_c = None
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        alphas = R.ALPH.get(ds, [1, 1, 1, 1]) if use_alpha else [1, 1, 1, 1]
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(x32, ref, sp, l_i)
            L = cl_run20(model_c, True, l_i, d, gains, dqon, ffk, A, tm, alphas,
                         c_qs=c, v0=v0, Cd=Cd, o1=q_off_0429[0], o2=q_off_0429[1])
        else:
            dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = cl_run20(model_f, False, l_i, d, gains, dqon, ffk, A, tm, alphas,
                         c_qs=c, v0=v0, Cd=Cd, o1=o1, o2=o2)
        if L is None:
            rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9))
            continue
        g, q2r = R.gap_v3(L, d, A, m)
        rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
    return rows
