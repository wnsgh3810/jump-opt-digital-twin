# -*- coding: utf-8 -*-
"""p23_runners — P23 Phase 0c: 지표 v6 신규 성분 러너 3종 + 바닥 (MARATHON_p23.md 준거).

성분 (전부 p23_loaders의 청정 xlsx 로더 소비, csv 오염 경로 없음):
  1. CL_FF   — 폐루프 τ-갭 gap_v3, jump_0422(3) + jump_0319tau(1).
               러너 = cl_run20_ff (p20_run.cl_run20의 최소 변형: hip FF 주입 옵션 추가 —
               p20_run.py는 불변). alphas=[1,1,1,1] (이 세션들엔 적합된 커맨드층 없음 —
               held-out 0324와 동일 규약), tm=v[14], c_qs=v[15], v0=v[16], Cd=0
               (p21_cma.cl_metrics CL 규약), preload(pre30)=v[19] (무변속 플랜트측),
               o1=o2=0 (적합 오프셋 없음). 마스크 = GRF 이륙+0.1s (p19 규약; 이 세션들은
               기록이 짧아 사실상 전체 창).
  2. OLDQ_FF — Mode A 통짜 재생 dq2 RMSE (세션별), p22_eval.a_full 규약 그대로
               (settle→ahat(traw)+lam 주입(SD 시프트)→기록 끝 이후 0; o1=o2=0; pre30=v[19]).
  3. AIR     — s2s_air 0319 14사이클 재생, 용접 베이스 (실세션 = 로봇 매달림; 레거시
               GOAL18도 base weld). 모델 = build_flip_welded (P.build_flip과 동일 조성
               (cvt_iter5.build_flip_variant 복제) + safe.xml_patch 2건: bz slide joint
               제거 + base를 z=1m — 컴파일 검증 nq 5→4).
               사이클마다: 측정 q(0)로 초기화 → T_SETTLE 위치 PD settle → ahat+lam 주입.
               지표 AIR = mean_cycles[ rmse(q2) + 0.1·rmse(dq2) ]  ← v6 동결 공식.
               ★ 프로토콜 결정 (Phase 0c): AIR의 동결 정의는 pre30=0.
                 근거: pre30=v[19](≈2Nm 상수)를 공중에 그대로 가산하면 크랭크가 수 회전
                 폭주 (P19 rq 32rad, 지표 포화·카오스) — 실 로봇은 매달림에서 안 돌았음 =
                 '무변속 상시 플랜트측 pre30' 가설이 공중 데이터로 반증됨 (P20 pre30 해체
                 마라톤의 '기준선=세션별'과 정합). a_full 블랭킷 규약에서의 유일한 이탈이며
                 pre30 ON 값은 진단용으로 병기 (air_score(pre30_on=True)).
               crash 사이클 = (rmse_q2, rmse_dq2) = (2.0, 20.0) → 점수 4.0 (win429 관례).
  바닥      — ① CL_FF 재구성 바닥: 측정 (q,dq)→명령모델(PD+FF[+clip ±35.5]+ahat) vs 측정
               τ(SD 시프트), gap_v3 동형 비율 (p19 재구성 바닥 방법, 시뮬 없음).
               knee-only vs knee+hip 양쪽 산출 → 낮은 쪽으로 FF 주입 프로토콜 동결.
             ② dq2 측정 노이즈: |dq2|<0.5 구간 std (p22_rebase.dq_noise_floor 규약).
             ③ AIR 노이즈 바닥: 사이클 내 |dq2|<0.5 구간에서 q2 잔차(savgol 21,3) std +
               0.1·dq2 std → AIR 공식에 대입.

주의: 원본 데이터 읽기 전용. 이 모듈은 파일을 쓰지 않는다 (쓰기는 p23_anchors.py 전담).
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p22_eval as E      # ensure_init / x19_vec / a_full (골든 규약 재사용)
import p21_cma as C       # x32_of / lam_vec / _W
import p19_run as R       # gap_v3 / CLIP
import p23_loaders as L
import safe

GATE_PATH = HERE.parent / "p22_beyond/p22_gate_check.json"
FF_SESS = ("jump_0422", "jump_0319tau")
AIR_W_DQ = 0.1                     # AIR = rmse(q2) + 0.1*rmse(dq2)  (v6 동결)
CRASH_RQ, CRASH_RDQ = 2.0, 20.0    # crash 사이클 페널티 (win429 W_Q*2+W_DQ*20 관례)
DQ_LOW = 0.5                       # 노이즈 바닥 저속 마스크 (p22_rebase 규약)

BASE_Z_LINE = '<joint name="base_z" type="slide" axis="0 0 1"/>'
BASE_BODY_OLD = '<body name="base" pos="0 0 0" childclass="leg">'
BASE_BODY_NEW = '<body name="base" pos="0 0 1" childclass="leg">'

_T = {"rows": None, "air": None}


def ensure_init():
    """p22_eval.ensure_init 재사용 — winit 1회 + fix0421 1회 (순서 불변 철칙)."""
    E.ensure_init()


def x22b_vec():
    """p22b 벡터 = p22_gate_check.json rows[16]['x'] (20-vec, p21_cma 좌표) — 그 외 아무
    변환도 적용하지 않음 (과제 동결). rows[16]은 NSGA 프런트 i=29 (J_v5=0.9489, PASS)."""
    row = safe.read_json(GATE_PATH)["rows"][16]
    v = np.asarray(row["x"], float)
    assert v.shape == (20,), f"p22b 벡터 길이 {v.shape} (기대 20)"
    return v


def ff_trials():
    """p23_loaders.all_new_trials() 캐시 — (ds, sub, d, gains, dqon, ffk, mask, cvt, l_i)."""
    if _T["rows"] is None:
        _T["rows"] = L.all_new_trials()
    return _T["rows"]


def air_cycles():
    """load_s2s_air() 캐시 — (cycles 14개, meta)."""
    if _T["air"] is None:
        _T["air"] = L.load_s2s_air()
    return _T["air"]


# ══════════════════ 1) CL_FF — 폐루프 τ-갭 ══════════════════
def cl_run20_ff(model, is_cvt, l_i, d, gains, dqdes_on, ffk, A, tm, alphas,
                c_qs=0.0, v0=6.0, Cd=0.0, o1=0.0, o2=0.0, preload=0.0,
                ff_hip=False):
    """p20_run.cl_run20의 최소 변형 — ff_hip=True면 hip에도 FF(tdes1) 주입.

    본체는 cl_run20과 문자 그대로 동일 (p20_run.py 불변 원칙; 변경분은 ff_hip 분기
    한 줄). 반환 로그 dict (q1/q2/dq1/dq2/sh1/sh2/bz/t)."""
    P = C._W["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    P20 = C._W["P20"]
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes_on else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes_on else np.zeros_like(t)
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    sq1, sq2 = -qd1[0] - np.pi / 2, -qd2[0]
    if is_cvt:
        from cvt_core import qpos_from_crank
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
    Lg = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz"]}
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
            if ff_hip:                                # ★ 유일한 변경점
                c1 += np.interp(tm_, t, d["tdes1"])
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R.CLIP, R.CLIP)); c2 = float(np.clip(c2, -R.CLIP, R.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        s2_qs = c_qs * s2 * float(P20.gate(v2c, v0))
        vk = float(md.qvel[dof_knee])
        dyn = Cd * (1.0 - P20.gate(vk, v0)) * float(np.tanh(s2 / 2.0))
        md.ctrl[:] = [-s1, -(s2 + s2_qs + preload)]
        md.qfrc_applied[dof_knee] = -dyn
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
    Lg["t"] = tl
    return Lg


def cl_ff(v, ff_hip):
    """CL_FF: 세션별 gap_v3 평균 → ({ds: g_mean}, rows). alphas=[1,1,1,1] 동결."""
    ensure_init()
    P = C._W["P"]
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model_f, _ = P.build_flip(x32, v[1], sp)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in ff_trials():
        Lg = cl_run20_ff(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                         float(v[14]), [1, 1, 1, 1], c_qs=float(v[15]),
                         v0=float(v[16]), Cd=0.0, o1=0.0, o2=0.0,
                         preload=float(v[19]), ff_hip=ff_hip)
        if Lg is None:
            rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9, crash=True))
            continue
        g, q2r = R.gap_v3(Lg, d, P.A_PAPER, m)
        rows.append(dict(ds=ds, sub=sub, g=float(min(g, 2.0)), q2=float(q2r),
                         crash=False))
    sess = {ds: float(np.mean([r["g"] for r in rows if r["ds"] == ds]))
            for ds in FF_SESS}
    return sess, rows


# ══════════════════ 2) OLDQ_FF — Mode A 통짜 재생 dq2 RMSE ══════════════════
def oldq_ff(v):
    """p22_eval.a_full 그대로 (o1=o2=0, pre30=v[19]) → ({ds: rmse_mean}, rows)."""
    ensure_init()
    P = C._W["P"]
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model_f, _ = P.build_flip(x32, v[1], sp)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in ff_trials():
        res = E.a_full(model_f, False, l_i, d, v, 0.0, 0.0, pre30=float(v[19]))
        hr = float(d.get("h_real", float("nan")))
        if res is None:
            rows.append(dict(ds=ds, sub=sub, rmse=9.9, h_sim=float("nan"),
                             h_real=hr, crash=True))
            continue
        rmse_, h_sim = res
        rows.append(dict(ds=ds, sub=sub, rmse=float(rmse_), h_sim=float(h_sim),
                         h_real=hr, crash=False))
    sess = {ds: float(np.mean([r["rmse"] for r in rows if r["ds"] == ds]))
            for ds in FF_SESS}
    return sess, rows


# ══════════════════ 3) AIR — 용접 베이스 s2s_air 재생 ══════════════════
def build_flip_welded(x32, ref, spring_at):
    """cvt_iter5.build_flip_variant 조성 복제 + 베이스 용접.

    P.build_flip(=cvt_iter5)과 완전히 같은 XML 경로 (S 글로벌 세팅 →
    FL.build_xml_fourbar_flip → P13.apply_linkage_mods → calf 스프링/SEA_TC 패치) 뒤
    컴파일 직전 safe.xml_patch 2건:
      ① bz slide joint 라인 제거 (nq 5→4, 컴파일 후 검증)
      ② base body를 z=1m로 (다리 최대 신장 ~0.53m → 발이 바닥 plane(z=0)에 절대 닿지
         않음 = 무접촉; 실세션 매달림 재현)"""
    import re
    import cvt_iter5 as I5
    import g21_p13_linkage as P13
    import g21_p13e_honest as PH
    J = C._W["P"].J
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]
    S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0
    S.STIFF_KNEE = dd["stiff_knee"] if spring_at == "crank" else 0.0
    S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    if spring_at == "calf":
        mkn = re.search(r'<joint name="knee" type="hinge" damping="([0-9.eE+-]+)"/>', xml)
        assert mkn, "knee joint line not found"
        xml = xml.replace(mkn.group(0),
                          f'<joint name="knee" type="hinge" damping="{mkn.group(1)}" '
                          f'stiffness="{dd["stiff_knee"]:.6f}" springref="{ref:.5f}"/>')
    xml = xml.replace('body2="calf" anchor="0 0 -0.25" solref="0.0008 1"',
                      f'body2="calf" anchor="0 0 -0.25" solref="{I5.SEA_TC[0]:.5f} 1"')
    # ── 용접 (검증된 치환만) ──
    xml = safe.xml_patch(xml, BASE_Z_LINE, "", count=1)
    xml = safe.xml_patch(xml, BASE_BODY_OLD, BASE_BODY_NEW, count=1)
    model = mj.MjModel.from_xml_string(xml)
    assert mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "base_z") < 0, "weld 실패: base_z 잔존"
    assert model.nq == 4, f"weld 후 nq={model.nq} (기대 4 = bz 제거 확인)"
    return model, dd


def verify_weld(model):
    """settle 테스트: 제어 0 + 중력 0.5s → base 월드 z가 1.0에서 불변 + 발이 바닥
    위(>0.2m) 유지 + 상태 유한. (body_sameframe류 함정 무관하나 컴파일 결과 직접 검증.)"""
    mj = C._W["mj"]
    md = mj.MjData(model)
    mj.mj_forward(model, md)
    bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    z0 = float(md.xpos[bid][2])
    fmin = 9.9
    for _ in range(int(0.5 / model.opt.timestep)):
        md.ctrl[:] = 0
        mj.mj_step(model, md)
        fmin = min(fmin, float(md.geom_xpos[fg][2]))
    z1 = float(md.xpos[bid][2])
    ok = (abs(z0 - 1.0) < 1e-9 and abs(z1 - 1.0) < 1e-9
          and bool(np.isfinite(md.qpos).all()) and fmin > 0.2)
    return dict(ok=bool(ok), base_z0=z0, base_z1=z1, foot_min_z=float(fmin),
                nq=int(model.nq))


def air_replay_cycle(model, d, v, pre30):
    """1사이클 통짜 재생 (a_full 규약: settle→ahat+lam 주입(SD)→기록 끝 이후 0;
    pre30은 ctrl 상시 가산). 반환 (rmse_q2, rmse_dq2) 또는 None(crash)."""
    P = C._W["P"]; mj = C._W["mj"]; S = P.J._P["S"]
    t = d["t"]
    lam = C.lam_vec(d["traw2"], d["dq2"], v[15], v[16])
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
    q1_0 = float(d["q1"][0]); q2_0 = float(d["q2"][0])          # o1=o2=0 (적합 오프셋 없음)
    md = mj.MjData(model)
    iq_h = safe.qadr(model, "hip", mj); iq_c = safe.qadr(model, "knee_motor", mj)
    iq_p = safe.qadr(model, "cpin", mj); iq_k = safe.qadr(model, "knee", mj)
    id_h = safe.dofadr(model, "hip", mj); id_c = safe.dofadr(model, "knee_motor", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = 0
    md.qpos[iq_h] = sq1; md.qpos[iq_c] = sq2
    md.qpos[iq_p] = -sq2; md.qpos[iq_k] = sq2
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1]) / dt) + 1     # T_AFTER 불필요 (지표 창 = t<=t[-1])
    tl = np.arange(N) * dt - P.J.T_SETTLE
    q2s = np.zeros(N); dq2s = np.zeros(N)
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[iq_h] - np.pi / 2; q2c = -md.qpos[iq_c]
            v1c = -md.qvel[id_h]; v2c = -md.qvel[id_c]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            if tc > t[-1]:
                s1 = s2 = 0.0
        md.ctrl[:] = [-s1, -(s2 + pre30)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if not np.isfinite(md.qpos).all() or np.abs(md.qpos).max() > 50:
            return None
        q2s[k] = -md.qpos[iq_c]; dq2s[k] = -md.qvel[id_c]
    rq = float(np.sqrt(np.mean((np.interp(t, tl, q2s) - d["q2"]) ** 2)))
    rdq = float(np.sqrt(np.mean((np.interp(t, tl, dq2s) - d["dq2"]) ** 2)))
    return rq, rdq


def air_score(v, pre30_on=False):
    """AIR = mean_cycles[ rmse(q2) + 0.1*rmse(dq2) ] (동결 공식).

    ★ pre30_on=False가 v6 동결 정의 (Phase 0c 프로토콜 결정 — 모듈 docstring 근거:
    공중에서 pre30 상수 가산은 크랭크 폭주 = 지표 포화, 실데이터로 반증).
    pre30_on=True는 진단용 변형 (블랭킷 pre30 가설의 공중 반증 수치 기록용)."""
    ensure_init()
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model_w, _ = build_flip_welded(x32, v[1], sp)
    pre30 = float(v[19]) if pre30_on else 0.0
    cycles, meta = air_cycles()
    rows = []
    for i, d in enumerate(cycles):
        res = air_replay_cycle(model_w, d, v, pre30)
        if res is None:
            rows.append(dict(cyc=i + 1, rq=CRASH_RQ, rdq=CRASH_RDQ,
                             score=CRASH_RQ + AIR_W_DQ * CRASH_RDQ, crash=True))
            continue
        rq, rdq = res
        rows.append(dict(cyc=i + 1, rq=rq, rdq=rdq,
                         score=rq + AIR_W_DQ * rdq, crash=False))
    air = float(np.mean([r["score"] for r in rows]))
    return air, rows


# ══════════════════ 4) 바닥 ══════════════════
def recon_floor(ff_hip):
    """CL_FF 재구성 바닥 (p19 방법, 시뮬 없음): 측정 (q,dq)→명령모델(PD+FF+clip+ahat)
    vs 측정 τ(SD 시프트) — gap_v3 동형 비율. dqd=0 (dqdes_on=False 세션),
    커맨드층 지연(tm)·alphas 없음 (순수 명령모델; 과제 정의 'PD+FF+ahat')."""
    ensure_init()
    P = C._W["P"]
    per = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in ff_trials():
        t = d["t"]
        kp1, kd1, kp2, kd2 = gains
        c1 = kp1 * (d["qd1"] - d["q1"]) - kd1 * d["dq1"]
        c2 = kp2 * (d["qd2"] - d["q2"]) - kd2 * d["dq2"]
        if ffk:
            c2 = c2 + d["tdes2"]
        if ff_hip:
            c1 = c1 + d["tdes1"]
        c1 = np.clip(c1, -R.CLIP, R.CLIP); c2 = np.clip(c2, -R.CLIP, R.CLIP)
        s1 = P.J.ahat(P.A_PAPER, c1, d["dq1"])
        s2 = P.J.ahat(P.A_PAPER, c2, d["dq2"])
        tp1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tp2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]))
        num = np.sqrt(np.mean((s1 - tp1)[m] ** 2) + np.mean((s2 - tp2)[m] ** 2))
        den = max(np.sqrt(np.mean(tp1[m] ** 2) + np.mean(tp2[m] ** 2)), 0.5)
        per.append(dict(
            ds=ds, sub=sub, floor=float(num / den),
            rmse1=float(np.sqrt(np.mean((s1 - tp1)[m] ** 2))),
            rmse2=float(np.sqrt(np.mean((s2 - tp2)[m] ** 2))),
            rms_meas=float(den)))
    sess = {ds: float(np.mean([r["floor"] for r in per if r["ds"] == ds]))
            for ds in FF_SESS}
    sess["MEAN"] = float(np.mean([sess[ds] for ds in FF_SESS]))
    return sess, per


def dq2_noise_floor():
    """OLDQ_FF 바닥: |dq2|<0.5 구간 dq2 std (p22_rebase.dq_noise_floor 규약, ≥10 샘플)."""
    out = {}
    for ds, sub, d, *_ in ff_trials():
        v2 = np.asarray(d["dq2"], float)
        mm = np.abs(v2) < DQ_LOW
        if mm.sum() >= 10:
            out.setdefault(ds, []).append(
                dict(sub=str(sub), std=float(v2[mm].std()), n=int(mm.sum())))
        else:
            out.setdefault(ds, []).append(
                dict(sub=str(sub), std=float("nan"), n=int(mm.sum())))
    res = {}
    for ds, rows in out.items():
        vals = [r["std"] for r in rows if np.isfinite(r["std"])]
        res[ds] = dict(mean=float(np.mean(vals)) if vals else float("nan"),
                       per_trial=rows)
    return res


def air_noise_floor():
    """AIR 바닥: 사이클 내 저속(|dq2|<0.5) 구간에서
    q2 노이즈 = std(q2 − savgol(q2,21,3)), dq2 노이즈 = std(dq2) →
    floor = mean_cycles[ sig_q2 + 0.1·sig_dq2 ] (AIR 공식 대입)."""
    from scipy.signal import savgol_filter
    cycles, _ = air_cycles()
    per = []
    for i, d in enumerate(cycles):
        q2 = np.asarray(d["q2"], float); dq2 = np.asarray(d["dq2"], float)
        if len(q2) < 25:
            continue
        low = np.abs(dq2) < DQ_LOW
        if low.sum() < 10:
            continue
        resid = q2 - savgol_filter(q2, 21, 3)
        sq = float(resid[low].std()); sdq = float(dq2[low].std())
        per.append(dict(cyc=i + 1, sig_q2=sq, sig_dq2=sdq,
                        floor=sq + AIR_W_DQ * sdq, n_low=int(low.sum())))
    fl = float(np.mean([r["floor"] for r in per])) if per else float("nan")
    return dict(floor=fl,
                sig_q2_mean=float(np.mean([r["sig_q2"] for r in per])) if per else float("nan"),
                sig_dq2_mean=float(np.mean([r["sig_dq2"] for r in per])) if per else float("nan"),
                per_cycle=per)
