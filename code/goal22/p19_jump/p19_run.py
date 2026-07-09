# -*- coding: utf-8 -*-
"""P19 통합 CL 러너 — 커맨드 층 (α 게인스케일 + 1차 지연 + 클립) + 지표 v3."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p19_judge as P

CMD = json.load(open(HERE / "p19_cmdlayer.json"))
TM0, CLIP = CMD["TM"], CMD["CLIP"]
ALPH = CMD["alphas"]


def cl_run(model, is_cvt, l_i, d, gains, dqdes_on, ffk, A, tm, alphas, preload,
           o1=0.0, o2=0.0):
    """커맨드 층 포함 CL. 반환 로그 dict."""
    mj = P.J._P["mj"]; S = P.J._P["S"]
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes_on else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes_on else np.zeros_like(t)
    md = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    if is_cvt:
        from cvt_core import qpos_from_crank
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[0] = bz0; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "sh1", "sh2", "bz"]}
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
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)   # 토크 추종 지연
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -CLIP, CLIP)); c2 = float(np.clip(c2, -CLIP, CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -(s2 + preload)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
    L["t"] = tl
    return L


def gap_v3(L, d, A, m):
    t = d["t"]
    tp1 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
    num = np.sqrt(np.mean((s1 - tp1)[m] ** 2) + np.mean((s2 - tp2)[m] ** 2))
    den = max(np.sqrt(np.mean(tp1[m] ** 2) + np.mean(tp2[m] ** 2)), 0.5)
    q2r = float(np.sqrt(np.mean((np.interp(t, L["t"], L["q2"]) - d["q2"])[m] ** 2)))
    return float(num / den), q2r


def all_trials():
    """(ds, sub, d, gains, dqdes_on, ffk, mask, is_cvt, l_i) 목록."""
    from cvt_core import load_0429, label_gains_429, SUBS429
    out = []
    for tr in P.J._P["cl"]:
        d = tr["d"]
        tend = min(d["t"][-1], d["t"][min(tr["toff"], len(d["t"]) - 1)] + 0.1)
        out.append((tr["ds"], tr["sub"], d, tr["gains"], tr["dqdes"], tr["ffk"],
                    d["t"] <= tend, False, 0.030))
    for sub in SUBS429:
        d = load_0429(sub)
        g = d["grf_real"]; pk = int(np.argmax(g))
        below = np.where(g[pk:] < 0.02 * g[pk])[0]
        toff = d["t"][pk + below[0]] if len(below) else d["t"][-1]
        out.append(("jump_0429", sub, d, label_gains_429(sub), False, False,
                    d["t"] <= min(d["t"][-1], toff + 0.1), True, d["l_i"]))
    return out


TRIALS = None


def eval_stack(x32, ref, sp, A, preload30, tm, use_alpha=True, q_off_0429=(0.0548, -0.0524)):
    global TRIALS
    if TRIALS is None:
        TRIALS = all_trials()
    model_f, _ = P.build_flip(x32, ref, sp)
    model_c = None
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TRIALS:
        alphas = ALPH.get(ds, [1, 1, 1, 1]) if use_alpha else [1, 1, 1, 1]
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(x32, ref, sp, l_i)
            L = cl_run(model_c, True, l_i, d, gains, dqon, ffk, A, tm, alphas, 0.0,
                       o1=q_off_0429[0], o2=q_off_0429[1])
        else:
            dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = cl_run(model_f, False, l_i, d, gains, dqon, ffk, A, tm, alphas,
                       preload30, o1=o1, o2=o2)
        if L is None:
            rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9))
            continue
        g, q2r = gap_v3(L, d, A, m)
        rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
    return rows


def summarize(rows):
    out = {}
    for ds in sorted(set(r["ds"] for r in rows)):
        rs = [r for r in rows if r["ds"] == ds]
        out[ds] = (float(np.mean([r["g"] for r in rs])),
                   float(np.mean([r["q2"] for r in rs])), len(rs))
    fit = [r["g"] for r in rows if r["ds"] != "jump_0324"]
    out["FIT"] = (float(np.mean(fit)), 0, len(fit))
    return out
