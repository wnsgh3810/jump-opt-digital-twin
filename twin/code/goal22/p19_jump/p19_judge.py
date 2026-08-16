# -*- coding: utf-8 -*-
"""P19 심판 — 점프 전용 τ-fidelity (마라톤 고정 지표).

목적 (사용자 정의): 궤적(q_des, dq_des)로 PD 제어했을 때 실측 토크 ≈ sim 예측 토크.
지표: CL τ-갭 = RMSE(τ_sim − τ_meas)/RMS(τ_meas), 관절·트라이얼 평균 (점프 세션만).
  - no_cvt: jump_0324(ff, held-out) / jump_position_0421 / jump_0424 / jump_0602
  - cvt   : 0429 10 trials (l_i=25.08)
보조: Mode A 점프 창 심판 (w_0421/0424/0602/0324) + fs/h — 식별성 보조.
변환식 A는 인자 (Paper 우선)."""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
P18 = HERE.parent / "p18_cvt"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(P18))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J

A_PAPER = J.A_PAPER.copy() if hasattr(J, "A_PAPER") else np.array(
    [1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X37 = np.array(C16["x"])
A_FIT = np.array(C16["x"][32:36])
W18 = json.load(open(P18 / "p18b_iter11.json"))["x"]
SD = -0.0015


def winit():
    J.winit()


# ══════════ 모델 빌더 (평행사변형 flip + CVT) ══════════
def build_flip(x32, ref, spring_at):
    import cvt_iter5 as I5
    return I5.build_flip_variant(x32, ref, spring_at)


def build_cvt(x32, ref, spring_at, l_i):
    from cvt_run2 import build_cvt2
    return build_cvt2(l_i, spring_at, "crank", x32=x32, ref=ref)


# ══════════ CL τ-갭 (no_cvt 세션, p14 cl 캐시) ══════════
def run_cl_pre(model, dd, tr, A, preload, kp1s=1.0, kp2s=1.0):
    """p14_judge.run_cl + 플랜트 프리로드 + 게인 스케일."""
    mj = J._P["mj"]; S = J._P["S"]
    d = tr["d"]; t = d["t"]
    kp1, kd1, kp2, kd2 = tr["gains"]
    kp1 *= kp1s; kp2 *= kp2s
    k1, k2 = J.OFFK.get(tr["ds"], (None, None))
    o1 = dd.get(k1, 0.0) if k1 else 0.0; o2 = dd.get(k2, 0.0) if k2 else 0.0
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if tr["dqdes"] else np.zeros_like(t)
    dqd2 = d["dqd2"] if tr["dqdes"] else np.zeros_like(t)
    md = mj.MjData(model)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[:] = [bz0, sq1, sq2, -sq2, sq2]; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((J.T_SETTLE + t[-1] + J.T_AFTER) / dt)
    tl = np.arange(N) * dt - J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, qd1) - q1c) + kd1 * (np.interp(tm, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm, t, qd2) - q2c) + kd2 * (np.interp(tm, t, dqd2) - v2c)
            if tr["ffk"]:
                c2 += np.interp(tm, t, d["tdes2"])
        s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -(s2 + preload)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
    L["t"] = tl; L["o"] = (o1, o2)
    return L


def tau_gap(L, tr, A):
    """τ-갭 (상대 RMSE) — [0, toff+0.1] 창."""
    d = tr["d"]; t = d["t"]
    tend = min(t[-1], t[min(tr["toff"], len(t) - 1)] + 0.1)
    m = t <= tend
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
    g1 = float(np.sqrt(np.mean((s1 - tp1)[m] ** 2)) / max(np.sqrt(np.mean(tp1[m] ** 2)), 0.3))
    g2 = float(np.sqrt(np.mean((s2 - tp2)[m] ** 2)) / max(np.sqrt(np.mean(tp2[m] ** 2)), 0.3))
    q2r = float(np.sqrt(np.mean((np.interp(t, L["t"], L["q2"]) - d["q2"])[m] ** 2)))
    return g1, g2, q2r


def eval_cl_nocvt(x32, ref, spring_at, A, preload30, kp1s_0421=1.0):
    model, _ = build_flip(x32, ref, spring_at)
    dd = dict(zip(J._P["FR"].NAMES, np.asarray(x32)[:26]))
    rows = []
    for tr in J._P["cl"]:
        kp1s = kp1s_0421 if tr["ds"] == "jump_position_0421" else 1.0
        L = run_cl_pre(model, dd, tr, A, preload30, kp1s=kp1s)
        if L is None:
            rows.append(dict(ds=tr["ds"], sub=tr["sub"], g1=9.9, g2=9.9, q2=9.9))
            continue
        g1, g2, q2r = tau_gap(L, tr, A)
        rows.append(dict(ds=tr["ds"], sub=tr["sub"], g1=g1, g2=g2, q2=q2r))
    return rows


def eval_cl_cvt(x32, ref, spring_at, A):
    """0429 CL (프리로드 0, q-오프셋 P18b)."""
    from cvt_run2 import sim_run
    from cvt_core import load_0429, label_gains_429, SUBS429
    o1, o2 = 3.14 * np.pi / 180, -3.0 * np.pi / 180
    rows = []
    import cvt_run2 as R
    A_save = R.A.copy(); R.A = np.asarray(A, float)   # cvt 러너의 변환식 주입
    try:
        for sub in SUBS429:
            d = load_0429(sub)
            model, _ = build_cvt(x32, ref, spring_at, d["l_i"])
            L, _ = sim_run(model, d, d["l_i"], "CL", gains=label_gains_429(sub),
                           o1=o1, o2=o2)
            if L is None:
                rows.append(dict(ds="jump_0429", sub=sub, g1=9.9, g2=9.9, q2=9.9))
                continue
            t = d["t"]
            g = d["grf_real"]
            pk = int(np.argmax(g)); below = np.where(g[pk:] < 0.02 * g[pk])[0]
            toff = t[pk + below[0]] if len(below) else t[-1]
            m = t <= min(t[-1], toff + 0.1)
            tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
            tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
            s1 = np.interp(t, L["t"], L["sh1"]); s2 = np.interp(t, L["t"], L["sh2"])
            g1 = float(np.sqrt(np.mean((s1 - tp1)[m] ** 2)) / max(np.sqrt(np.mean(tp1[m] ** 2)), 0.3))
            g2 = float(np.sqrt(np.mean((s2 - tp2)[m] ** 2)) / max(np.sqrt(np.mean(tp2[m] ** 2)), 0.3))
            q2r = float(np.sqrt(np.mean(((np.interp(t, L["t"], L["q2"]) - o2) - d["q2"])[m] ** 2)))
            rows.append(dict(ds="jump_0429", sub=sub, g1=g1, g2=g2, q2=q2r))
    finally:
        R.A = A_save
    return rows


def summarize(rows):
    out = {}
    for ds in sorted(set(r["ds"] for r in rows)):
        rs = [r for r in rows if r["ds"] == ds]
        out[ds] = dict(g1=float(np.mean([r["g1"] for r in rs])),
                       g2=float(np.mean([r["g2"] for r in rs])),
                       q2=float(np.mean([r["q2"] for r in rs])), n=len(rs))
    fit = [r for r in rows if r["ds"] != "jump_0324"]
    out["FIT_ALL"] = dict(g1=float(np.mean([r["g1"] for r in fit])),
                          g2=float(np.mean([r["g2"] for r in fit])),
                          gap=float(np.mean([0.5 * (r["g1"] + r["g2"]) for r in fit])))
    ho = [r for r in rows if r["ds"] == "jump_0324"]
    if ho:
        out["HELDOUT"] = dict(gap=float(np.mean([0.5 * (r["g1"] + r["g2"]) for r in ho])))
    return out


# ══════════ Mode A 점프 창 (보조 심판) ══════════
def eval_modeA_jump(x32, ref, spring_at, A, ot2_tables=None):
    """iter10 evalG7에서 s2s 제외 + A 주입."""
    P12 = J._P["P12"]
    dd = dict(zip(J._P["FR"].NAMES, np.asarray(x32)[:26]))
    model, _ = build_flip(x32, ref, spring_at)
    ot2 = ot2_tables or {}
    res = {"habs": 0.0}
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        if ds.startswith("s2s"):
            continue
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        t = tr["pp"]["t"]
        boost = ot2.get(ds, 0.0)
        th = -J.ahat(A, tr["raw1"], tr["v1"])
        tk = -(J.ahat(A, tr["raw2"], tr["v2"]) + boost)
        ppv = dict(tr["pp"], tau_h=np.interp(t - SD, t, th), tau_k=np.interp(t - SD, t, tk))
        ppo = P12._G["sv"](ppv, o1, o2)
        res[P12.GKEY[ds]] = res.get(P12.GKEY[ds], 0.0) + P12.eval_windows(model, ppo, None)
        if ds in ("jump_0424", "jump_0602", "jump_0324"):
            fsk = "fs_" + ds.split("_")[-1]
            sc, h_pred = P12.fs_metric(model, ppo, tr["td"], None)
            res[fsk] = res.get(fsk, 0.0) + sc
            if ds != "jump_0324" and np.isfinite(h_pred) and np.isfinite(tr["h_real"]):
                res["habs"] += abs(h_pred - tr["h_real"])
    return res
