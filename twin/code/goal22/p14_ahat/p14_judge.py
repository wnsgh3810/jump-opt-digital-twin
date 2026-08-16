"""P14 — 이중 심판 (Mode A + 폐루프 τ-채널) with a_hat 해방.

x = [32 모델 파라미터, A1, A2, A3, A4]  (A0=0 고정)
a_hat(τ_rep, v) = A1·GR·KT·Iq − A2·GR·|Iq|·Iq − A3·sgn(v) − A4·|Iq|·sgn(v),  Iq = CF/(GR·KT)·τ_rep

Mode A 측: canonical tau_real을 paper 역변환(뉴턴)으로 raw 복원(캐시) → 후보 a_hat으로 재변환해
창(w_*)+full-stance(fs_*)+habs 하이브리드 (P12 인프라 재사용, sens_delay=-1.5ms 고정).
CL 측: p13i 심판과 동일 골격 — 단 sim 액추에이터와 실측 τ 참조 모두 후보 a_hat 사용.
게이트: Mode A fs_0324 및 CL 0324 (둘 다 x0 기준 ≤1.05).
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
G22 = HERE.parent
REPO = G22.parents[1]
sys.path.insert(0, str(G22))
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13
from g22_p10_pdlaw import SETS, label_gains
from g22_p10_cl import load_trial_xlsx
from g22_p13_phases import phases

KT, GR, CF = 0.091, 9.0, 0.59
A_PAPER = np.array([1.15605006, 4.17389589e-4, 0.26855607, 0.04904241])
SD = -0.0015
CHANNELS = ("q1", "q2", "dq1", "dq2", "tau1", "tau2")
PW = {"early": 0.5, "push": 2.0, "flight": 1.0}
RATIO_CLIP = 10.0
T_SETTLE, T_AFTER = 0.4, 0.6
OFFK = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
        "jump_0424": ("o1_0424", "o2_0424"), "s2s_gnd_0319": ("o1_0319", "o2_0319")}
_P = {}


def ahat(A, tau_rep, v):
    Iq = (CF / (GR * KT)) * np.asarray(tau_rep, float)
    s = np.sign(v)
    return A[0] * GR * KT * Iq - A[1] * GR * np.abs(Iq) * Iq - A[2] * s - A[3] * np.abs(Iq) * s


def invert_paper(tau_shaft, v, iters=25):
    """paper(A_PAPER) 역변환: shaft -> raw (뉴턴, 단조 구간)."""
    x = np.asarray(tau_shaft, float) / (A_PAPER[0] * CF)     # 초기값: 선형 역
    for _ in range(iters):
        f = ahat(A_PAPER, x, v) - tau_shaft
        Iq = (CF / (GR * KT)) * x
        df = A_PAPER[0] * CF - 2 * A_PAPER[1] * GR * (CF / (GR * KT)) ** 2 * np.abs(x) \
             - A_PAPER[3] * (CF / (GR * KT)) * np.sign(v) * np.sign(x)
        x = x - f / np.maximum(np.abs(df), 0.05) * np.sign(df)
    return x


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    if P12._G["trials"] is None:
        P12.build_trials()
    _P["P12"] = P12
    _P["mj"] = P12._G["mujoco"]; _P["S"] = P12._G["S"]
    _P["FR"] = P12._G["FR"]; _P["FL"] = P12._G["FL"]
    # ── Mode A: raw 복원 캐시 (P12 trials의 tau_real -> raw, canonical) ──
    for tr in P12._G["trials"]:
        td = tr["td"]
        for j in (1, 2):
            v = np.asarray(td[f"dq{j}"], float)
            ts = np.asarray(td[f"tau{j}_real"], float)
            tr[f"raw{j}"] = invert_paper(ts, v)
            tr[f"v{j}"] = v
    # ── CL: xlsx 트라이얼 캐시 ──
    base = json.load(open(G22 / "p13_phases.json"))
    cl = []
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            d = load_trial_xlsx(ds, root, sub)
            on, toff = phases(d)
            b = base.get(f"{ds}/{sub}", {}).get("label")
            if b is None:
                continue
            cl.append(dict(ds=ds, sub=sub, d=d, on=on, toff=toff, base=b,
                           gains=label_gains(ds, sub), ffk=(ds == "jump_0324"),
                           dqdes=(ds in ("jump_0424", "jump_0602")),
                           heldout=(ds == "jump_0324")))
    _P["cl"] = cl


def build_model(x32):
    S = _P["S"]; FR = _P["FR"]; FL = _P["FL"]; mj = _P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


# ══════════ Mode A 심판 (P12 인프라 + a_hat 주입) ══════════
def eval_modeA(x36):
    P12 = _P["P12"]
    x32 = x36[:32]; A = x36[32:36]
    dd = dict(zip(_P["FR"].NAMES, x32[:26]))
    model, _ = build_model(x32)
    res = {"habs": 0.0}
    for tr in P12._G["trials"]:
        ds = tr["ds"]
        k1, k2 = P12.OFFKEY.get(ds, (None, None))
        o1 = dd[k1] if k1 else 0.0; o2 = dd[k2] if k2 else 0.0
        # a_hat 재변환 + mj frame + sens_delay
        t = tr["pp"]["t"]
        th = -ahat(A, tr["raw1"], tr["v1"])
        tk = -ahat(A, tr["raw2"], tr["v2"])
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


# ══════════ CL 심판 (p13i 골격 + a_hat 주입) ══════════
def run_cl(model, dd, tr, A):
    mj = _P["mj"]; S = _P["S"]
    d = tr["d"]; t = d["t"]
    kp1, kd1, kp2, kd2 = tr["gains"]
    k1, k2 = OFFK.get(tr["ds"], (None, None))
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
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2"]}
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
        s1 = float(ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -s2]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
        L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2
    L["t"] = tl; L["o"] = (o1, o2)
    return L


def cl_trial_score(L, tr, A):
    d = tr["d"]; t = d["t"]; on, toff = tr["on"], tr["toff"]
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, ahat(A, d["traw2"], d["dq2"]))
    sims = dict(q1=g("q1") - o1, q2=g("q2") - o2, dq1=g("dq1"), dq2=g("dq2"),
                tau1=g("sh1"), tau2=g("sh2"))
    reals = dict(q1=d["q1"], q2=d["q2"], dq1=d["dq1"], dq2=d["dq2"], tau1=tp1, tau2=tp2)
    segs = dict(early=slice(0, on), push=slice(on, min(toff, len(t))),
                flight=slice(min(toff, len(t)), len(t)))
    tot = wsum = 0.0
    for sn, sl in segs.items():
        if sl.stop - sl.start < 5 or sn not in tr["base"]:
            continue
        rs = []
        for ch in CHANNELS:
            b = tr["base"][sn].get(ch, np.nan)
            if not np.isfinite(b) or b < 1e-9:
                continue
            r = float(np.sqrt(np.mean((sims[ch][sl] - reals[ch][sl]) ** 2))) / b
            rs.append(min(r, RATIO_CLIP))
        if rs:
            tot += PW[sn] * np.mean(rs); wsum += PW[sn]
    return tot / max(wsum, 1e-9)


def eval_cl(x36):
    x32 = x36[:32]; A = x36[32:36]
    model, dd = build_model(x32)
    fit_s, ho_s = [], []
    for tr in _P["cl"]:
        L = run_cl(model, dd, tr, A)
        if L is None:
            return 99.0, 99.0
        s = cl_trial_score(L, tr, A)
        (ho_s if tr["heldout"] else fit_s).append(s)
    return float(np.mean(fit_s)), float(np.mean(ho_s))


def eval36(x36):
    """반환 dict(JA_groups, JC, JC_gate)."""
    try:
        if not _P:
            winit()
        x36 = np.asarray(x36, float)
        ra = eval_modeA(x36)
        jc, jcg = eval_cl(x36)
        return dict(A=ra, C=jc, Cg=jcg)
    except Exception:
        return None
