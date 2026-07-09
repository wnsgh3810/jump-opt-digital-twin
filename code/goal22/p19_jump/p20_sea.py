# -*- coding: utf-8 -*-
"""P20 — 기어박스 직렬탄성 (SEA): 무릎 모터 로터 DOF 추가 + 텐던 커플링.

물리: AK80-9 엔코더/PD는 로터 측, 링키지는 크랭크 측. 기어박스 유연성 k_sea가
그 사이에 있으면 부하 시 와인드업 δ=τ/k_sea 만큼 두 각이 어긋남 — P19 잔여 갭의
시그니처(중반 푸시 실측 τ 후퇴)와 일치하는 후보.
구현: rotor2 body(armature/마찰=모터측)를 base 마지막 자식으로 추가 (기존 dof 0~4 불변,
rotor=5), knee actuator를 rotor로 재타깃, fixed tendon(coef +1/-1, stiffness=k_sea,
damping=b_sea)으로 rotor↔crank 결합. 엔코더 읽기/PD/로그 = rotor.
"""
import sys, json, re
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
import p19_judge as P
import p19_run as R

K_SEA = [500.0]
B_SEA = [1.0]


def _sea_xml(xml, dd, crank_pos_body="crank"):
    """knee actuator를 rotor로 옮기고 SEA 텐던 삽입."""
    # 1) knee_motor 관절: 모터측 속성 제거 (armature/damping/frictionloss -> 링키지 잔여만)
    mkm = re.search(r'<joint name="knee_motor"[^/]*/>', xml)
    assert mkm, "knee_motor joint not found"
    line = mkm.group(0)
    line2 = re.sub(r'armature="[^"]*"', 'armature="1e-6"', line)
    line2 = re.sub(r'damping="[^"]*"', 'damping="0.001"', line2)
    line2 = re.sub(r'frictionloss="[^"]*"', 'frictionloss="0"', line2)
    xml = xml.replace(line, line2)
    # 2) rotor body를 base의 마지막 자식으로 (crank pivot과 동축 — crank body pos 추출)
    mcr = re.search(r'<body name="crank" pos="([^"]+)"', xml)
    crank_pos = mcr.group(1) if mcr else "0 0 0"
    rotor = (f'<body name="rotor2" pos="{crank_pos}">'
             f'<inertial pos="0 0 0" mass="0.001" diaginertia="1e-7 1e-7 1e-7"/>'
             f'<joint name="rotor2_j" type="hinge" armature="{dd["arm_knee"]:.8f}" '
             f'damping="{dd["fv_knee"]:.6f}" frictionloss="{dd["fc_knee"]:.6f}"/>'
             f'</body>')
    # base body의 닫는 태그 직전 삽입: worldbody 구조상 base 서브트리의 마지막 </body> 찾기
    # (안전: crank body의 종료 뒤가 아니라, actuator 직전의 마지막 </body></worldbody> 사용)
    xml = xml.replace('</worldbody>', rotor + '</worldbody>')
    # ↑ worldbody 직속이면 rotor가 world에 붙음 — base가 슬라이드만 하므로 모터 스테이터는
    #   world 고정과 등가가 아님! base z를 따라가야 함 → base 마지막 자식으로 넣어야 정확.
    return xml


def _sea_xml_in_base(xml, dd):
    """rotor를 base 서브트리 마지막에 삽입 (crank와 동일 부모/좌표)."""
    mcr = re.search(r'(<body name="crank" pos="([^"]+)">)', xml)
    assert mcr, "crank body not found"
    crank_open, crank_pos = mcr.group(1), mcr.group(2)
    rotor = (f'<body name="rotor2" pos="{crank_pos}">'
             f'<inertial pos="0 0 0" mass="0.001" diaginertia="1e-7 1e-7 1e-7"/>'
             f'<joint name="rotor2_j" type="hinge" armature="{dd["arm_knee"]:.8f}" '
             f'damping="{dd["fv_knee"]:.6f}" frictionloss="{dd["fc_knee"]:.6f}"/>'
             f'</body>')
    # crank body 여는 태그 직전에 rotor 삽입 → 같은 부모(base), dof 순서는 rotor가 crank보다
    # 앞서게 됨 — 기존 인덱스 붕괴! 대신 crank의 "부모 종료" 위치에 넣기 어려우므로:
    # crank 서브트리 전체를 찾아 그 뒤에 삽입.
    depth = 0; i = mcr.start(1); n = len(xml)
    j = i
    while j < n:
        mo = re.compile(r'<body\b|</body>').search(xml, j)
        if mo is None:
            break
        if mo.group(0) == '</body>':
            depth -= 1
            j = mo.end()
            if depth == 0:
                break
        else:
            depth += 1
            j = mo.end()
    xml = xml[:j] + rotor + xml[j:]
    return xml


def build_sea(kind, x32, ref, sp, l_i=0.030):
    """kind: 'flip' | 'cvt'. 기존 빌더 XML 경로를 복제 + SEA 삽입."""
    import g21_p13_linkage as P13
    import g21_p13e_honest as PH
    mj = P.J._P["mj"]; S = P.J._P["S"]; FR = P.J._P["FR"]; FL = P.J._P["FL"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FC_HIP = dd["fc_hip"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0
    S.STIFF_KNEE = 0.0
    S.SPRINGREF_KNEE = ref
    S.FV_KNEE = 0.0; S.FC_KNEE = 0.0        # 모터측 마찰은 rotor로 이동
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    if kind == "cvt":
        xml = xml.replace('fromto="0 0 0 0 0 0.03"', f'fromto="0 0 0 0 0 {l_i:.5f}"')
        xml = xml.replace('<body name="coupler" pos="0 0 0.03">',
                          f'<body name="coupler" pos="0 0 {l_i:.5f}">')
        xml = re.sub(r'<connect body1="coupler" body2="calf"[^/]*/>', '', xml)
        xml = xml.replace('<joint name="cpin" type="hinge" damping=',
                          '<site name="ctip" pos="0 0 -0.25" size="0.003"/>'
                          '<joint name="cpin" type="hinge" damping=')
        xml = xml.replace('<joint name="knee" type="hinge" damping=',
                          '<site name="rocker" pos="0 0 0.03" size="0.003"/>'
                          '<joint name="knee" type="hinge" damping=')
        xml = xml.replace('<equality>',
                          '<equality>\n  <connect site1="ctip" site2="rocker" solref="0.00080 1"/>')
    # 무릎 병렬 스프링 @calf (P18b/P19)
    if sp == "calf":
        mkn = re.search(r'<joint name="knee" type="hinge" damping="([0-9.eE+-]+)"/>', xml)
        if mkn:
            xml = xml.replace(mkn.group(0),
                              f'<joint name="knee" type="hinge" damping="{mkn.group(1)}" '
                              f'stiffness="{dd["stiff_knee"]:.6f}" springref="{ref:.5f}"/>')
    # SEA 삽입 + actuator 재타깃 + 텐던
    xml = _sea_xml_in_base(xml, dd)
    xml = xml.replace('joint="knee_motor"', 'joint="rotor2_j"')
    xml = xml.replace('</mujoco>',
                      f'<tendon><fixed name="sea" stiffness="{K_SEA[0]:.2f}" '
                      f'damping="{B_SEA[0]:.3f}">'
                      f'<joint joint="rotor2_j" coef="1"/>'
                      f'<joint joint="knee_motor" coef="-1"/>'
                      f'</fixed></tendon></mujoco>')
    model = mj.MjModel.from_xml_string(xml)
    return model, dd


def cl_run_sea(model, is_cvt, l_i, d, gains, dqdes_on, ffk, A, alphas, preload,
               o1=0.0, o2=0.0):
    """SEA CL: 엔코더/PD = rotor(qpos[5]). 커맨드층 (α + 클립)."""
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
        qp5 = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    else:
        qp5 = [1.0, sq1, sq2, -sq2, sq2]
    md.qpos[:5] = qp5; md.qpos[5] = sq2
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    bz0 = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qpos[0] = bz0; md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    L = {k: np.zeros(N) for k in ["q1", "q2", "sh1", "sh2", "bz"]}
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2
        q2c = -md.qpos[5]                       # ★ 엔코더 = rotor
        v1c = -md.qvel[1]; v2c = -md.qvel[5]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
        else:
            tm_ = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm_, t, qd1) - q1c) + kd1 * (np.interp(tm_, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm_, t, qd2) - q2c) + kd2 * (np.interp(tm_, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm_, t, d["tdes2"])
        c1 = float(np.clip(c1, -R.CLIP, R.CLIP)); c2 = float(np.clip(c2, -R.CLIP, R.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        md.ctrl[:] = [-s1, -(s2 + preload)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[5]
        L["sh1"][k] = s1; L["sh2"][k] = s2; L["bz"][k] = md.qpos[0]
    L["t"] = tl
    return L


def eval_sea(x32, ref, sp, A, preload30, q_off_0429=(0.0548, -0.0524)):
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f, _ = build_sea("flip", x32, ref, sp)
    model_c = None
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        alphas = R.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c, _ = build_sea("cvt", x32, ref, sp, l_i)
            L = cl_run_sea(model_c, True, l_i, d, gains, dqon, ffk, A, alphas, 0.0,
                           o1=q_off_0429[0], o2=q_off_0429[1])
        else:
            dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = cl_run_sea(model_f, False, l_i, d, gains, dqon, ffk, A, alphas,
                           preload30, o1=o1, o2=o2)
        if L is None:
            rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9))
            continue
        g, q2r = R.gap_v3(L, d, A, m)
        rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
    return rows


def main():
    P.winit()
    W3 = json.load(open(HERE / "p19_cma3.json"))
    NAMES = W3["names"]; v = np.array(W3["x"])
    IDX = dict(stiff=11, fv_hip=14, fc_hip=16, fv_knee=15, fc_knee=17,
               solref=12, imp0=13, arm_knee=9, M_c=4, I_th=5, I_ca=6, dz_th=7, dz_ca=8)
    x32 = np.array(P.X37[:32])
    for i, n in enumerate(NAMES):
        if n in IDX:
            x32[IDX[n]] = v[i]
    sp = "calf" if v[0] > 1e-3 else "none"
    for k in (20000.0, 2000.0, 800.0, 400.0, 200.0, 100.0):
        K_SEA[0] = k; B_SEA[0] = max(0.02 * np.sqrt(k), 0.3)
        rows = eval_sea(x32, v[1], sp, P.A_PAPER, v[2], q_off_0429=(v[16], v[17]))
        s = R.summarize(rows)
        print(f"k_sea={k:7.0f} b={B_SEA[0]:.2f}  CLτ FIT {100*s['FIT'][0]:.1f}% "
              f"HO {100*s['jump_0324'][0]:.1f}%  " +
              " ".join(f"{ds.split('_')[-1]}:{100*val[0]:.0f}"
                       for ds, val in s.items() if ds.startswith("jump")), flush=True)


if __name__ == "__main__":
    main()
