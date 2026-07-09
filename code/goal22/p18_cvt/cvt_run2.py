# -*- coding: utf-8 -*-
"""P18b 마라톤 러너 v2 — 0429 CVT 오차 해결.

v1 대비:
  - hold→replay 20ms 블렌딩 (t=0 계단 킥 제거)
  - 정적 평형 갭 로그 (settle 끝 hold 토크 vs 측정 초기 토크)
  - stance 전용 지표 + 이륙시각 차 + 에너지 원장
  - 배치 축: 스프링/마찰을 crank(모터) vs calf(무릎) 관절에 — 평행사변형에선 두 배치가
    수학적으로 동일(qk≡qc)하므로 기존 세션 성능 불변이 보장됨. 0429만이 분리 가능.
  - l_i 오버라이드 + 세션 오프셋(o1,o2) 훅
"""
import sys, json
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from cvt_core import qpos_from_crank, closure, load_0429, label_gains_429, SUBS429
import cvt_core as CC
import p14_judge as J

SD = -0.0015
T_SETTLE, T_AFTER, T_BLEND = 0.4, 0.6, 0.02
C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X = np.array(C16["x"])
A = np.array(C16["x"][32:36])
REF = float(C16["x"][36])


def build_cvt2(l_i, spring_at="crank", fric_at="crank", x32=None, ref=None):
    """cvt_core.build_cvt와 동일하되 스프링/점성+쿨롱 마찰 배치 선택."""
    x32 = X[:32] if x32 is None else x32
    ref = REF if ref is None else ref
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FC_HIP = dd["fc_hip"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0
    if spring_at == "crank":
        S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = ref
    else:
        S.STIFF_KNEE = 0.0; S.SPRINGREF_KNEE = ref
    if fric_at == "crank":
        S.FV_KNEE = dd["fv_knee"]; S.FC_KNEE = dd["fc_knee"]
    else:
        S.FV_KNEE = 0.0; S.FC_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = __import__("g21_p13e_honest").TOTAL
    import g21_p13_linkage as P13
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    xml = xml.replace('fromto="0 0 0 0 0 0.03"', f'fromto="0 0 0 0 0 {l_i:.5f}"')
    xml = xml.replace('<body name="coupler" pos="0 0 0.03">',
                      f'<body name="coupler" pos="0 0 {l_i:.5f}">')
    import re
    xml = re.sub(r'<connect body1="coupler" body2="calf"[^/]*/>', '', xml)
    xml = xml.replace('<joint name="cpin" type="hinge"/>',
                      '<joint name="cpin" type="hinge"/><site name="ctip" pos="0 0 -0.25" size="0.003"/>')
    xml = xml.replace('<joint name="cpin" type="hinge" damping=',
                      '<site name="ctip" pos="0 0 -0.25" size="0.003"/><joint name="cpin" type="hinge" damping=')
    # calf 무릎 힌지: 배치 옵션 반영 — 기존 damping(fitted d_kneep)은 보존, 속성 추가
    mkn = re.search(r'<joint name="knee" type="hinge" damping="([0-9.eE+-]+)"/>', xml)
    assert mkn, "knee joint line not found"
    extra = ""
    if fric_at == "calf":
        extra += f' frictionloss="{dd["fc_knee"]:.6f}"'
        dmp = float(mkn.group(1)) + dd["fv_knee"]
    else:
        dmp = float(mkn.group(1))
    if spring_at == "calf":
        extra += f' stiffness="{dd["stiff_knee"]:.6f}" springref="{ref:.5f}"'
    xml = xml.replace(mkn.group(0),
                      f'<joint name="knee" type="hinge" damping="{dmp:.6f}"{extra}/>')
    if spring_at == "calf":
        assert f'stiffness="{dd["stiff_knee"]:.6f}"' in xml
    xml = xml.replace('<joint name="knee" type="hinge" damping=',
                      '<site name="rocker" pos="0 0 0.03" size="0.003"/><joint name="knee" type="hinge" damping=')
    xml = xml.replace('<equality>',
                      '<equality>\n  <connect site1="ctip" site2="rocker" solref="0.0008 1"/>')
    return mj.MjModel.from_xml_string(xml), dd


def fk_bz(model, dta, q1m, qc, l_i):
    mj = J._P["mj"]; S = J._P["S"]
    qp5, qk, r = qpos_from_crank(1.0, q1m, qc, l_i)
    dta.qpos[:] = qp5; dta.qvel[:] = 0
    mj.mj_forward(model, dta)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    return 1.0 - float(dta.geom_xpos[fg][2]) + S.FOOT_RADIUS


def sim_run(model, d, l_i, mode, gains=None, o1=0.0, o2=0.0, preload=0.0, cap=None):
    """preload: 플랜트측 무릎 보조 토크(canonical, 명령 로그 제외). cap: 공급 천장(shaft Nm)."""
    mj = J._P["mj"]; S = J._P["S"]
    t = d["t"]
    q1r = d["q1"] + o1; q2r = d["q2"] + o2      # 오프셋: 모델각 = 측정각 + o
    dta = mj.MjData(model)
    q1_0 = (d["qd1"][0] + o1) if mode == "CL" else q1r[0]
    q2_0 = (d["qd2"][0] + o2) if mode == "CL" else q2r[0]
    mj_q1_0 = -q1_0 - np.pi / 2
    mj_qc_0 = -q2_0
    bz0 = fk_bz(model, dta, mj_q1_0, mj_qc_0, l_i)
    qp5, _, _ = qpos_from_crank(bz0, mj_q1_0, mj_qc_0, l_i)
    dta.qpos[:] = qp5; dta.qvel[:] = 0
    mj.mj_forward(model, dta)
    tau1_in = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tau2_in = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    dt = model.opt.timestep
    N = int((T_SETTLE + t[-1] + T_AFTER) / dt)
    tl = np.arange(N) * dt - T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz", "grf",
                                  "qk", "qpin"]}
    kp1 = kd1 = kp2 = kd2 = 0.0
    if gains:
        kp1, kd1, kp2, kd2 = gains
    hold1 = hold2 = 0.0
    for k in range(N):
        tc = tl[k]
        q1c = -dta.qpos[1] - np.pi / 2
        q2c = -dta.qpos[2]
        v1c = -dta.qvel[1]; v2c = -dta.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            h1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
            h2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
            hold1, hold2 = h1, h2
            s1, s2 = h1, h2
        elif mode == "A":
            tm = min(tc, t[-1])
            s1 = float(np.interp(tm, t, tau1_in))
            s2 = float(np.interp(tm, t, tau2_in))
            if tc < T_BLEND:                     # hold→replay 블렌딩
                w = tc / T_BLEND
                s1 = (1 - w) * hold1 + w * s1
                s2 = (1 - w) * hold2 + w * s2
        else:
            tm = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm, t, d["qd1"]) + o1 - q1c) + kd1 * (0.0 - v1c)
            c2 = kp2 * (np.interp(tm, t, d["qd2"]) + o2 - q2c) + kd2 * (0.0 - v2c)
            s1 = float(J.ahat(A, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(J.ahat(A, np.array([float(c2)]), np.array([v2c]))[0])
        if tc > t[-1]:
            s1 = s2 = 0.0
        a1, a2 = s1, s2
        if cap is not None:
            a1 = float(np.clip(a1, -cap, cap)); a2 = float(np.clip(a2, -cap, cap))
        dta.ctrl[:] = [-a1, -(a2 + preload)]
        try:
            mj.mj_step(model, dta)
        except Exception:
            return None, None
        if abs(dta.qpos[0]) > 5 or not np.isfinite(dta.qpos).all():
            return None, None
        L["q1"][k] = -dta.qpos[1] - np.pi / 2; L["q2"][k] = -dta.qpos[2]
        L["dq1"][k] = -dta.qvel[1]; L["dq2"][k] = -dta.qvel[2]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = dta.qpos[0]
        L["qk"][k] = dta.qpos[4]; L["qpin"][k] = dta.qpos[3]
        gz = 0.0
        for ci in range(dta.ncon):
            cf = np.zeros(6)
            mj.mj_contactForce(model, dta, ci, cf)
            gz += (dta.contact[ci].frame.reshape(3, 3).T @ cf[:3])[2]
        L["grf"][k] = gz
    L["t"] = tl
    diag = dict(hold1=hold1, hold2=hold2,
                meas0_1=float(tau1_in[0]), meas0_2=float(tau2_in[0]))
    return L, diag


def takeoff_time(tt, g, thresh_frac=0.02):
    pk = int(np.argmax(g))
    below = np.where(g[pk:] < thresh_frac * g[pk])[0]
    return float(tt[pk + below[0]]) if len(below) else float("nan")


def metrics2(d, L, o1=0.0, o2=0.0):
    """stance 전용 RMSE + 이륙시각 + h + 에너지 원장."""
    t = d["t"]
    q1r = d["q1"] + o1; q2r = d["q2"] + o2
    toff_r = takeoff_time(t, d["grf_real"]) if d["grf_real"] is not None else t[-1]
    mk = (L["t"] >= 0) & (L["t"] <= t[-1])
    f = lambda a: np.interp(t, L["t"][mk], a[mk])
    st = t <= toff_r
    r = lambda a, b: float(np.sqrt(np.mean((a[st] - b[st]) ** 2)))
    # sim 이륙시각
    mk2 = L["t"] >= 0.02
    gs = L["grf"][mk2]
    zero = np.where(gs < 1.0)[0]
    toff_s = float(L["t"][mk2][zero[0]]) if len(zero) else float("nan")
    # 에너지 원장 (입력 일 = a_hat 토크 × 각속도 적분, 이륙까지)
    dtt = np.gradient(t)
    tp1 = np.interp(t - SD, t, J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - SD, t, J.ahat(A, d["traw2"], d["dq2"]))
    W_real = float(np.sum((tp1 * d["dq1"] + tp2 * d["dq2"])[st] * dtt[st]))
    sts = (L["t"] >= 0) & (L["t"] <= (toff_s if np.isfinite(toff_s) else t[-1]))
    dts = L["t"][1] - L["t"][0]
    W_sim = float(np.sum((L["sh1"] * L["dq1"] + L["sh2"] * L["dq2"])[sts] * dts))
    return dict(q1=r(f(L["q1"]), q1r), q2=r(f(L["q2"]), q2r),
                dq1=r(f(L["dq1"]), d["dq1"]), dq2=r(f(L["dq2"]), d["dq2"]),
                toff_r=toff_r, toff_s=toff_s,
                dtoff=float(toff_s - toff_r) if np.isfinite(toff_s) else 9.9,
                h=float(L["bz"][L["t"] > 0].max()), h_real=float(d["h_real"]),
                W_real=W_real, W_sim=W_sim)


def score(m):
    """마라톤 고정 점수 (작을수록 좋음)."""
    return (100 * (m["q1"] + m["q2"]) + 10 * (m["dq1"] + m["dq2"])
            + 300 * abs(m["h"] - m["h_real"]) + 200 * abs(m["dtoff"]))


def run_variant(args):
    tag, sub, spring_at, fric_at, l_i_override, o1, o2 = args
    if not J._P:
        J.winit()
    d = load_0429(sub)
    l_i = l_i_override if l_i_override else d["l_i"]
    model, dd = build_cvt2(l_i, spring_at, fric_at)
    L, diag = sim_run(model, d, l_i, "A", o1=o1, o2=o2)
    if L is None:
        return dict(tag=tag, sub=sub, err="CRASH")
    m = metrics2(d, L, o1, o2)
    return dict(tag=tag, sub=sub, score=score(m), **m, **diag)


def main():
    import multiprocessing as mp
    variants = [
        ("v2base_sprC_frcC", "crank", "crank", None),
        ("sprCALF_frcC", "calf", "crank", None),
        ("sprC_frcCALF", "crank", "calf", None),
        ("sprCALF_frcCALF", "calf", "calf", None),
        ("both_li23.5", "calf", "calf", 0.0235),
        ("both_li26.5", "calf", "calf", 0.0265),
        ("both_li28", "calf", "calf", 0.0280),
        ("base_li26.5", "crank", "crank", 0.0265),
    ]
    jobs = [(tag, s, sp, fr, li, 0.0, 0.0)
            for (tag, sp, fr, li) in variants for s in SUBS429]
    pool = mp.Pool(10, initializer=J.winit)
    res = []
    for r in pool.imap_unordered(run_variant, jobs):
        res.append(r)
        if "err" in r:
            print(f"{r['tag']:18s} {r['sub']:18s} CRASH", flush=True)
    pool.close(); pool.join()
    json.dump(res, open(HERE / "p18b_iter1.json", "w"), indent=1)
    print(f"\n{'variant':18s} {'score':>7} {'q2':>6} {'dq2':>6} {'dtoff':>7} "
          f"{'h_gap':>7} {'W_sim/W_real':>13} {'hold2 vs meas0':>15}")
    for tag, *_ in variants:
        rs = [r for r in res if r.get("tag") == tag and "err" not in r]
        if not rs:
            print(f"{tag:18s} ALL CRASH"); continue
        g = lambda k: np.mean([r[k] for r in rs])
        print(f"{tag:18s} {g('score'):7.1f} {g('q2'):6.3f} {g('dq2'):6.2f} "
              f"{g('dtoff')*1000:6.1f}ms {g('h')-g('h_real'):+7.3f} "
              f"{g('W_sim'):6.2f}/{g('W_real'):5.2f}J "
              f"{g('hold2'):+6.2f}/{g('meas0_2'):+5.2f}Nm  (n={len(rs)})", flush=True)
    print("saved p18b_iter1.json", flush=True)


if __name__ == "__main__":
    main()
