"""P13i 심판 — 폐루프(label 게인) 재현 기반, τ-잔차 채널 + 채널 정규화 + 구간 가중.

설계 근거 (2026-07-09 발견 3종):
  (1) 스탠스 널-공간: 상태만으로는 토크 분배 식별 불가 → τ1/τ2 잔차 채널 추가
  (2) dq2 지배: 채널별 RMSE를 P13h 기준값(p13_phases.json)으로 정규화
  (3) 구간 중요도: 초반 0.5 / 푸시 2.0 / 비행 1.0
목적 = fit 데이터셋(0421/0424/0602, 21 trials) 평균 / 게이트 = 0324 (held-out) ≤ 1.05.
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
from g22_p10_cl import load_trial_xlsx, SD
from g22_p13_phases import phases
from load_combined_15trial import paper_a_hat

CHANNELS = ("q1", "q2", "dq1", "dq2", "tau1", "tau2")
PW = {"early": 0.5, "push": 2.0, "flight": 1.0}
T_SETTLE, T_AFTER = 0.4, 0.6
RATIO_CLIP = 10.0
_J = {}


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    _J["P12"] = P12
    _J["mj"] = P12._G["mujoco"]; _J["S"] = P12._G["S"]
    _J["FR"] = P12._G["FR"]; _J["FL"] = P12._G["FL"]
    base = json.load(open(G22 / "p13_phases.json"))
    trials = []
    for ds, (root, subs) in SETS.items():
        for sub in subs:
            d = load_trial_xlsx(ds, root, sub)
            on, toff = phases(d)
            b = base.get(f"{ds}/{sub}", {}).get("label")
            if b is None:
                continue
            trials.append(dict(ds=ds, sub=sub, d=d, on=on, toff=toff, base=b,
                               gains=label_gains(ds, sub),
                               ffk=(ds == "jump_0324"),
                               dqdes=(ds in ("jump_0424", "jump_0602")),
                               heldout=(ds == "jump_0324")))
    _J["trials"] = trials


def build_model(x32):
    S = _J["S"]; FR = _J["FR"]; FL = _J["FL"]; mj = _J["mj"]
    x32 = np.asarray(x32, float)
    dd = dict(zip(FR.NAMES, x32[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, x32[26:32])))
    return mj.MjModel.from_xml_string(xml), dd


OFFK = {"jump_0324": ("o1_0324", "o2_0324"), "jump_position_0421": ("o1_0421", "o2_0421"),
        "jump_0424": ("o1_0424", "o2_0424")}


def run_cl(model, dd, tr):
    """v5 물리 폐루프 (무클립, a_hat). 반환 sim dict 또는 None."""
    mj = _J["mj"]; S = _J["S"]
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
        s1 = float(paper_a_hat(np.array([float(c1)]), np.array([v1c]))[0])
        s2 = float(paper_a_hat(np.array([float(c2)]), np.array([v2c]))[0])
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


def trial_score(L, tr):
    """구간×채널 정규화 점수. 반환 (가중합, per-detail) 또는 None."""
    d = tr["d"]; t = d["t"]; on, toff = tr["on"], tr["toff"]
    g = lambda k: np.interp(t, L["t"], L[k])
    o1, o2 = L["o"]
    tp1 = np.interp(t - SD, t, d["tau1_paper"])
    tp2 = np.interp(t - SD, t, d["tau2_paper"])
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


def eval32_cl(x32):
    """반환 (obj_fit, gate_0324) — 실패 시 (99, 99)."""
    try:
        if not _J:
            winit()
        model, dd = build_model(x32)
        fit_s, ho_s = [], []
        for tr in _J["trials"]:
            L = run_cl(model, dd, tr)
            if L is None:
                return 99.0, 99.0
            s = trial_score(L, tr)
            (ho_s if tr["heldout"] else fit_s).append(s)
        return float(np.mean(fit_s)), float(np.mean(ho_s))
    except Exception:
        return 99.0, 99.0
