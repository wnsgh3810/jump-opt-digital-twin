# -*- coding: utf-8 -*-
"""fs_cvt — 0429 CVT(l_i=25.08) 세션의 fs 편입: CVT 모델 캡처+직렬 힌지 패치+골든.

정본 호출 규약 (H13 검증): RU.build_cvt23(x32, ref, sp, l_i, d_dq) → l_i 는 trial 별 실측 →
RU.a_full23_log(model_c, True, d.l_i, d, law, o1_429, o2_429, c_cvt, spr=spr_resolve(model_c), k_rise).
골든: 기본(무패치) CVT 재생 dq2 RMSE ≈ 3.31 재현 → 러너 신뢰 후 fs 패치판 측정.
CLI: golden — 기본/fs 패치 CVT 재생 비교 (R19 구창 trial).
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
for _p in ("p25_task0", "p25_deploy", "p23_veins", "p19_jump", "p18_cvt", "p20_rise"):
    sys.path.insert(0, str(HERE.parent / "goal22" / _p))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
import mujoco as mjm             # noqa: E402
import fs_model as FM            # noqa: E402

RU = TW.RU; C = TW.C


def build_cvt_pair(li=0.02508):
    """CVT 모델 쌍 빌드. `li` = 그 **trial 의** Clutch.xlsx 실측 (fs_data.cvt_li).

    ★ 세션 상수로 고정하지 말 것 (사용자 지시 08-09). 기본값은 하위호환용이며,
      결과를 내는 경로는 반드시 trial 값을 넘긴다.
    """
    """CVT XML 캡처 → (기본 model_c, fs 패치 model_cf, 파라미터)."""
    cand = safe.read_json(TW.CAND_PATH)
    nm = dict(zip(cand["names"], np.asarray(cand["x"], float)))
    tw = TW.twin()   # winit 보장
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    x32, sp = C.x32_of(v[:20])
    ref = float(v[1]); d_dq = float(v[21])
    orig = mjm.MjModel.from_xml_string
    captured = []

    def cap(xml, *a, **k):
        captured.append(xml)
        return orig(xml, *a, **k)
    mjm.MjModel.from_xml_string = staticmethod(cap)
    try:
        model_c = RU.build_cvt23(x32, ref, sp, float(li), d_dq)
    finally:
        mjm.MjModel.from_xml_string = orig
    if not captured:
        raise RuntimeError("CVT XML 캡처 실패")
    xml_c = captured[-1]
    # ★ 08-12: 이 두 파일은 **눈으로 보려고** 남기는 사본이다. 스윕은 작업자 16개가 동시에
    #   같은 이름으로 쓰므로 서로 덮어써 내용이 섞인다 (동역학과는 무관하지만 보면 헷갈린다).
    #   FS_CVT_XML=0 이면 안 쓴다 — 스윕이 그렇게 켠다.
    _wx = os.environ.get("FS_CVT_XML") != "0"
    if _wx:
        open(HERE / "_cvt_base.xml", "w", encoding="utf-8").write(xml_c)
    # fs 패치 시도 (hip 라인 구조가 flip과 같은지 검사 후)
    model_cf = None
    try:
        model_cf, xml_cf = FM.build_fs(base_xml=xml_c)
        if _wx:
            open(HERE / "_cvt_fs.xml", "w", encoding="utf-8").write(xml_cf)
    except Exception as ex:
        print(f"fs 패치 실패 (hip 라인 상이?): {type(ex).__name__} {ex}", flush=True)
    # ★ 08-12: 여기까지의 모델은 **기본 물리값**이다 (힙스프링 150 · 힙마찰 0.2383 ·
    #   힙감쇠 0.3121 · 총질량 3.2010 …). 현행 스택이 지정한 값이 하나도 안 들어가 있어서
    #   **변속기 세션은 지금까지 옛 물리로 채점돼 왔다** (통과한 게이트 포함).
    #   여기서 이름 기준으로 심는다. **부품 위치는 안 건드린다 — 그게 변속기 기하다.**
    #
    # ☠ 08-12 저녁 정정 (사용자 적발): 처음엔 `model_c` 에도 같이 심었는데 **그건 틀렸다.**
    #   `model_c` 는 **비교용 배포 모델**이다. 거기에 현행 물리(질량 3.2988·스프링 138.53·
    #   마찰 0.3026/0.0964)를 넣으면 더 이상 배포 모델이 아니고, 배포 모델이 쓰는 게인
    #   보정표와 안 맞아 **발산한다** (변속기 폐루프 그림에서 힙 각도가 −91도까지 갔다).
    #   ⇒ 현행 물리는 **현행 모델(model_cf)에만** 심는다. 배포 모델은 옛 물리 그대로 둔다.
    import fs_runner as _FR
    if model_cf is not None:
        _FR.apply_stack_physics(model_cf, mjm)
    return model_c, model_cf, dict(nm=nm, tw=tw, v=v)


# ── 변속기 트윈 묶기 (단일 출처) ────────────────────────────────────────────────────
#   이 로봇은 무릎을 4절 링크로 돌리고, 그 링크 한 변의 길이(l_i)를 바꾸면 힘과 속도의
#   교환비가 달라진다 — 자전거 기어와 같다. 그런데 **그 길이는 모델의 치수 자체**여서
#   (2mm 다르면 부품 위치가 2mm 다르다) 길이가 다른 실험은 모델부터 다시 지어야 한다.
#   그걸 안 하고 무변속 모델에 태운 것이 08-12 에 잡은 사고다 (무릎각 오차 26.8°).
#
#   여기 함수 하나로 모아 둔 이유: 예전에는 이 묶는 절차가 fs_cvt.cl() 안에만 있었고,
#   채점판은 그 존재를 모른 채 변속기 실험을 통째로 건너뛰고 있었다. 사본이 둘이면
#   한쪽만 고치는 사고가 또 난다.
_MC = {}      # round(l_i, 7) → fs 패치된 변속기 모델. **기하 전용 캐시**
_RT = {}      # round(l_i, 7) → 전달비 표 (링크 길이로만 정해진다)
_NM = None    # 후보 파라미터 (전달비 손실 계수 C_CVT 를 여기서 꺼낸다)


def cvt_ft(li, ft_base=None, restamp=True):
    """이 trial 의 링크 길이 `li`[m] 로 묶인 트윈 dict 을 만들어 준다.

    무엇을 묶나 (넷 다 있어야 한다 — 하나라도 빠지면 조용히 틀린다)
      ① 모델      : 그 길이로 지은 4절 기하
      ② 관절 주소 : 모델이 새로 지어졌으므로 관절 번호도 다시 찾는다
      ③ 폐쇄 초기화: 4절은 고리라서 시작 자세가 고리를 닫고 있어야 한다. 안 그러면
                     솔버가 벌어진 고리를 억지로 닫으며 힘이 폭발한다 (`cvt_init`)
      ④ 전달비 손실: 링크를 거치며 새는 몫 (`cvt_diss`)

    `restamp=True` 면 현행 스택의 **물리값**(질량·마찰·탄성·발 반경 …)을 다시 심는다.
    기하는 링크 길이로만 정해지므로 캐시하지만, 물리는 값을 훑는 동안 계속 바뀌므로
    평가할 때마다 다시 심어야 한다. 안 그러면 옛 물리로 채점하게 된다 (08-12 결함 #3).
    """
    global _NM
    import fs_runner as FR
    from cvt_core import qpos_from_crank
    li = float(li); key = round(li, 7)
    if key not in _MC:
        _mc, _mcf, _ctx = build_cvt_pair(li)
        if _mcf is None:
            raise RuntimeError(f"fs 패치 CVT 모델 없음 (l_i={li})")
        _MC[key] = _mcf
        _RT[key] = RU.rtab(li)
        _NM = _ctx["nm"]
    m = _MC[key]
    if restamp:
        FR.apply_stack_physics(m, mjm)
    ft = dict(ft_base if ft_base is not None else FR.fs_twin())
    ft["model"] = m
    ft["iq"] = {n: safe.qadr(m, n, mjm)
                for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
    ft["dof"] = {n: safe.dofadr(m, n, mjm) for n in ft["iq"]}
    ft["cvt_init"] = lambda q1, q2, _l=li: qpos_from_crank(1.0, -q1 - np.pi / 2, -q2, _l)[0]
    qg, rg = _RT[key]
    ft["cvt_diss"] = (float(_NM["C_CVT"]), qg, rg)
    return ft


def golden():
    model_c, model_cf, ctx = build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    spr_c = RU.spr_resolve(model_c, tw["spr"])
    o1, o2, cc = nm["o1_429"], nm["o2_429"], nm["C_CVT"]
    for tag, mm in [("기본", model_c)] + ([("fs패치", model_cf)] if model_cf is not None else []):
        spr_m = RU.spr_resolve(mm, tw["spr"])
        rms = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
            if ds != "jump_0429":
                continue
            try:
                res = RU.a_full23(mm, True, d.get("l_i", l_i), d, tw["law"], o1, o2,
                                  c_cvt=cc, spr=tw["spr"], k_rise=tw["kr"])
                rms.append(float(res[0]) if res else 9.9)
            except Exception as ex:
                rms.append(9.9)
                print(f"  {sub}: ERR {type(ex).__name__}", flush=True)
        print(f"{tag}: 0429 재생 dq2 RMSE 평균 {np.mean(rms):.3f} (n={len(rms)}, 골든 앵커 ~3.31)", flush=True)

def a_cvt_mirror(model, d, tw, o1, o2, c_cvt, fs=False, two_stage=True, fade=True, bias1=0.0, ret_traces=False):
    """a_full23 CVT 가지 문자 미러 (fs=False: 5q 검증 경로 → 정본 2.705 재현이 골든 /
    fs=True: 6q 직렬힌지 경로 — hip 분할 init + 2단 qfrc + 소산 게이트 + 세션 bias1).
    반환 (dq2 RMSE, q1 RMSE, h_sim) | None. ret_traces=True면 dict(tl,q1,q2,dq1,dq2) 추가 반환."""
    import fs_runner as FR
    P = TW.C._W["P"]; mj = TW.C._W["mj"]; S = P.J._P["S"]
    law = tw["law"]; spr = tw["spr"]; kr = tw["kr"]
    t = d["t"]; law_a = law[0]
    hl = RU.hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
    ks = kref = None
    if spr is not None:
        ks, kref, _ = RU.spr_resolve(model, spr)
    sv = RU.supp_vec(d["traw2"], d["dq2"], law)
    if kr:
        sv = sv + RU.rise_term(d["dq2"], kr, law[2])
    a1v = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
    sv1 = RU.hip_supp_vec(d["traw1"], d["dq1"], d["traw2"], d["dq2"])
    a1v = a1v + sv1
    sv1_0 = float(sv1[0])
    t1 = np.interp(t - P.SD, t, a1v)
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
    supp0 = float(sv[0])
    HIPD = RU.HIP if hasattr(RU, "HIP") else {"a1": 0.0}
    q1_0 = float(d["q1"][0]) + o1
    q2_0 = float(d["q2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    from cvt_core import qpos_from_crank
    base5 = qpos_from_crank(1.0, sq1, sq2, float(d.get("l_i", 0.02508)))[0]
    if fs:
        iq = {n: safe.qadr(model, n, mj) for n in ("base_z", "hip_m", "hip", "knee_motor", "cpin", "knee")}
        dofm = {n: safe.dofadr(model, n, mj) for n in iq}
        s1_0 = float(P.J.ahat(P.A_PAPER, np.array([d["traw1"][0]]), np.array([d["dq1"][0]]))[0])
        defl0 = float(np.clip(np.sign(s1_0) * (abs(s1_0) / 96.0 if abs(s1_0) <= 9 else 9 / 96.0 + (abs(s1_0) - 9) / 323.0), -0.3, 0.3))
        md.qpos[iq["base_z"]] = base5[0]
        md.qpos[iq["hip_m"]] = base5[1]      # P12: thm1(모터측)을 실측에 앵커 (구: -defl0 → 처짐만큼 이탈)
        md.qpos[iq["hip"]] = defl0
        md.qpos[iq["knee_motor"]] = base5[2]
        md.qpos[iq["cpin"]] = base5[3]
        md.qpos[iq["knee"]] = base5[4]
        i_hipm, i_crank = iq["hip_m"], iq["knee_motor"]
        dof_knee = dofm["knee"]; iq_k = iq["knee"]
        d_hipm, d_crank = dofm["hip_m"], dofm["knee_motor"]
    else:
        md.qpos[:] = base5
        i_hipm, i_crank = 1, 2
        dof_knee = safe.dofadr(model, "knee", mj); iq_k = safe.qadr(model, "knee", mj)
        d_hipm, d_crank = 1, 2
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    qg = rg = None
    if c_cvt > 0:
        qg, rg = RU.rtab(float(d.get("l_i", 0.02508)))
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    dq2s = np.zeros(N); bzs = np.zeros(N); q1s = np.zeros(N)
    q2s_c = np.zeros(N); dq1s = np.zeros(N)
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[i_hipm] - np.pi / 2
            q2c = -md.qpos[i_crank]
            v1c = -md.qvel[d_hipm]; v2c = -md.qvel[d_crank]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
            extra = supp0
            e1 = sv1_0
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            extra = 0.0
            e1 = 0.0
            if tc > t[-1]:
                s1 = s2 = 0.0
                extra = law_a
                e1 = float(HIPD.get("a1", 0.0))
        md.ctrl[:] = [-(s1 + e1), -(s2 + extra)]
        tql = 0.0
        if qg is not None:
            rr = float(np.interp(md.qpos[i_crank], qg, rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(md.qvel[dof_knee])
            tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if hl is not None and ks is not None:
            if tc < 0:
                h = float(hl[0])
            elif tc > t[-1]:
                h = 0.0
            else:
                h = float(np.interp(tc, t, hl))
            tql += ks * (kref - float(md.qpos[iq_k])) * h
        md.qfrc_applied[dof_knee] = tql
        if fs:
            v1c_now = -md.qvel[d_hipm]
            dq_s = float(md.qpos[iq["hip"]])
            corr = (FM.KS_HIP * dq_s - FR._tau2s(dq_s)) if two_stage else 0.0
            b_eff = bias1
            if fade and abs(v1c_now) > 1.0:
                b_eff = bias1 * max(0.0, 1.0 - (abs(v1c_now) - 1.0) / 2.0)
            md.qfrc_applied[dofm["hip"]] = corr + b_eff
        mj.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            return None
        dq2s[k] = -md.qvel[d_crank]
        q1s[k] = (-(md.qpos[i_hipm] + md.qpos[iq["hip"]]) - np.pi / 2) if fs else (-md.qpos[i_hipm] - np.pi / 2)
        bzs[k] = md.qpos[0]
        q2s_c[k] = -md.qpos[i_crank]
        dq1s[k] = -md.qvel[d_hipm]
    m = (tl >= 0) & (tl <= t[-1])
    rmse = float(np.sqrt(np.mean((np.interp(tl[m], t, d["dq2"]) - dq2s[m]) ** 2)))
    rq1 = float(np.degrees(np.sqrt(np.mean((np.interp(tl[m], t, d["q1"]) + o1 - q1s[m]) ** 2))))
    if ret_traces:
        return rmse, rq1, float(bzs[tl > 0].max()), dict(tl=tl[m], q1=q1s[m], q2=q2s_c[m], dq1=dq1s[m], dq2=dq2s[m])
    return rmse, rq1, float(bzs[tl > 0].max())


def golden2():
    """미러 검증: 5q 경로가 정본 2.705를 재현하는가 → 통과 시 6q(fs) 측정."""
    model_c, model_cf, ctx = build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = nm["o1_429"], nm["o2_429"], nm["C_CVT"]
    for tag, mm, fs in [("미러 5q", model_c, False)] + ([("미러 6q(fs)", model_cf, True)] if model_cf is not None else []):
        rms = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
            if ds != "jump_0429":
                continue
            try:
                res = a_cvt_mirror(mm, d, tw, o1, o2, cc, fs=fs)
                rms.append(res[0] if res else 9.9)
            except Exception as ex:
                rms.append(9.9)
                print(f"  {sub}: ERR {type(ex).__name__} {ex}", flush=True)
        print(f"{tag}: 0429 재생 {np.mean(rms):.3f} (정본 앵커 2.705)", flush=True)

def golden3():
    """0429 세션 bias1(정적 감사) 편입 판별: fs 6q에서 bias 유/무 dq2·q1 비교."""
    model_c, model_cf, ctx = build_cvt_pair()
    tw = ctx["tw"]; nm = ctx["nm"]
    o1, o2, cc = nm["o1_429"], nm["o2_429"], nm["C_CVT"]
    cv = safe.read_json(HERE / "_fs_cvt_audit.json")
    rr = [r["a1"] - r["s1"] for tr in cv.values() for r in tr["down"] if r["ok"]]
    b = float(np.mean(rr))
    print(f"0429 감사 bias1 = {b:+.3f} Nm (n={len(rr)})", flush=True)
    for tag, bb in [("bias=0", 0.0), (f"bias={b:+.2f}", b)]:
        rms, rq = [], []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in TW.R19.TRIALS:
            if ds != "jump_0429":
                continue
            try:
                res = a_cvt_mirror(model_cf, d, tw, o1, o2, cc, fs=True, bias1=bb)
                rms.append(res[0] if res else 9.9)
                rq.append(res[1] if res else 99.9)
            except Exception as ex:
                rms.append(9.9); rq.append(99.9)
                print(f"  {sub}: ERR {type(ex).__name__} {ex}", flush=True)
        print(f"{tag}: dq2 {np.mean(rms):.3f} | q1 {np.mean(rq):.2f}° (n={len(rms)})", flush=True)


def cl():
    """마라톤C #266: 0429 CVT CL 채점 (baseline_fs3 미러 — fullspan *2 push/score 창).
    모델 = 정본 CVT 캡처 + fs 6q 패치. settle은 qpos_from_crank 폐쇄 정합 (ft["cvt_init"] 훅),
    전달비 소산 C_CVT는 ft["cvt_diss"] 훅. dq_des 인가(M1) — 사용자 확정 08-01."""
    import fs_runner as FR
    import fs_data as FD
    import fs_metric as FMET
    # ★ 08-09 정정: 구 주석은 "0.02499 = Clutch.xlsx 실측" 이었으나 **사실이 아니다**.
    #   센서 실측 범위는 25.06~25.10mm (10 trial 중앙 25.08). 24.99 는 그 밖이다.
    #   진짜 출처는 "25.08 대신 24.99 가 ModeA 전수 개선" — 점수에 맞춘 값이었다.
    #   이제 **trial 마다 그 trial 의 센서 중앙값**을 쓴다 (fs_data.cvt_li).
    # ★ 08-12: 묶는 절차는 `cvt_ft()` 로 옮겼다 (채점판도 같은 것을 쓴다 — 사본 금지).
    ft = None
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    SP = FR._sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if s != "26.04.29" or ho or not g:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            ft = cvt_ft(d["l_i"])       # ★ trial 별 실측 l_i (fs_data.cvt_li)
            _tko = os.environ.get("FS_TKOVR"); _kds = os.environ.get("FS_KDSC")
            gm = (g[0], g[1], g[2] * (float(_tko) if _tko else TK.get(g[2], 0.656)),
                  g[3] * (float(_kds) if _kds else 0.20))
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            _qs = int(os.environ.get("FS_QDSHIFT", "0") or 0)
            def _sh(x, _n=_qs):
                if _n <= 0:
                    return x
                y = np.empty_like(x); y[_n:] = x[:-_n]; y[:_n] = x[0]
                return y
            L = FR.rollout_cl_fs(ft, t, _sh(d["qd1"][i0:]), _sh(d["qd2"][i0:]), _sh(d["dqd1"][i0:]), _sh(d["dqd2"][i0:]),
                                 gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                                 bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                 fade=os.environ.get("FS_FADE") == "1", taulim=None)
            if L is None:
                print(f"{s}/{p.name}: rollout None", flush=True)
                continue
            gi = lambda k: np.interp(t, L["t"], L[k])
            for wn in ("score", "push"):
                m = seg[wn][i0:][: len(t)]
                t1obs = gi("s1f") if os.environ.get("FS_TAUOBS") == "lpf" else gi("s1")
                _tlm = os.environ.get("FS_TAULIM")
                try:
                    _ol = float(_tlm) if _tlm else None
                except ValueError:
                    _ol = None
                if _ol is not None:
                    t1obs = np.clip(t1obs, -_ol, _ol)
                r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                                gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), t1obs, gi("s2"))
                OUT.setdefault(wn, []).append(list(r))
            print(f"{s}/{p.name}: OK", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    for wn in ("score", "push"):
        if wn in OUT:
            a = np.mean(OUT[wn], axis=0)
            print(f"[{wn}] 0429 CVT CL: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}", flush=True)
    safe.atomic_json_write(HERE / "_fs_cvt_cl2.json", OUT)
    print("done → _fs_cvt_cl2.json", flush=True)


if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) > 1 and _s.argv[1] == "golden2":
        golden2()
    elif len(_s.argv) > 1 and _s.argv[1] == "golden3":
        golden3()
    elif len(_s.argv) > 1 and _s.argv[1] == "cl":
        cl()
    else:
        golden()
