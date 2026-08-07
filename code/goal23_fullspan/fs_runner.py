# -*- coding: utf-8 -*-
"""fs_runner — 내장 스프링 모델(fs_model)용 CL/ModeA 러너 (이름 기반 어드레싱).

CL: 폴더 게인 PD가 인코더(θ_m=hip_m)에 작용 — hip α 없음 (스프링 창발), knee는 OLD α.
    커맨드층 미러: raw PD → 클립(CLIP=35.5) → a_hat(Paper) → 축토크 + 지지법칙/무릎 스프링층.
ModeA: 측정 raw 주입 (hip_m/knee_motor), 동일 플랜트.
τ1 채점 대응물 = s1(모터 축토크, 전류센서 아날로그 — 내장 스프링에선 과도역 포함해 이것이 정답).
v1 스프링 = XML 선형 k150 (H10: 140~200 평탄대역). 2단 보정은 후속 축.
골든: G5 등가성 — 온건역(27일)에서 변형 C CL과 비교.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
for _p in ("p25_task0", "p25_deploy", "p23_veins", "p19_jump", "p18_cvt"):
    sys.path.insert(0, str(HERE.parent / "goal22" / _p))
import p25_a_twin as TW          # noqa: E402
import safe                      # noqa: E402
import mujoco as mjm             # noqa: E402
import fs_model as FM            # noqa: E402

RU = TW.RU
_CACHE = {}


def fs_twin(ks=FM.KS_HIP, bs=FM.BS_HIP, arm=FM.ARM_HIP):
    """fs 모델 + 정본 층 파라미터 캐시. FS_HIPM_DAMP/FL/ARM으로 hip_m 감쇠/마찰/관성 재검 (F30)."""
    ks = float(os.environ.get("FS_KS_HIP", str(ks)))   # 마라톤G C: G8-B 는 k_s ≳ 400~500 요구 (현행 150)
    arm = float(os.environ.get("FS_HIPM_ARM", str(arm)))
    bs = float(os.environ.get("FS_BS", str(bs)))
    dm = float(os.environ.get("FS_HIPM_DAMP", "0.312066"))
    fl = float(os.environ.get("FS_HIPM_FL", "0.238254"))
    _mu = os.environ.get("FS_MU")            # 마라톤D P3: 발-바닥 마찰 (슬립 축)
    _rx = os.environ.get("FS_RAILX")         # 마라톤E P2: 레일 횡 컴플라이언스 "k,b" [N/m, N·s/m]
    _mt = os.environ.get("FS_MASS")          # 사용자 실측 08-02: 총질량 [kg] (케이블 제거 3.26, 허용 ~3.3)
    # 마라톤G Phase1: 바디별 질량분포 축 (사용자 확정 08-02 — 메모리 mass-ledger-truth)
    #   FS_MBODY="thigh=1.05,crank=0.44"  바디 질량 [kg] (thigh = 허벅지+knee모터 한 묶음)
    #   FS_COMZ ="thigh=-0.004"           CoM z 오프셋 [m] (기존 ipos에 가산)
    #   FS_IBODY="thigh=1.10"             관성 배율 (미지정 시 질량비로 자동 스케일)
    _mb = os.environ.get("FS_MBODY")
    _cz = os.environ.get("FS_COMZ")
    _ib = os.environ.get("FS_IBODY")
    # 마라톤G G1-E3: 공중 동정 실측 마찰 반영용 (무릎측). 힙측은 기존 FS_HIPM_DAMP/FL.
    _kd = os.environ.get("FS_KNEEM_DAMP")
    _kf = os.environ.get("FS_KNEEM_FL")
    key = (ks, bs, arm, dm, fl, _mu, _rx, _mt, _mb, _cz, _ib, _kd, _kf)
    if key not in _CACHE:
        if "base" not in _CACHE:
            base_xml, tw = FM.capture_base_xml()
            _CACHE["base"] = (base_xml, tw)
        base_xml, tw = _CACHE["base"]
        model, xml = FM.build_fs(ks=ks, bs=bs, arm=arm, base_xml=base_xml, dm=dm, fl=fl)
        if _rx:
            _k, _b = (float(v) for v in _rx.split(","))
            _bz = '<joint name="base_z" type="slide" axis="0 0 1"/>'
            xml = safe.xml_patch(
                xml, _bz,
                _bz + "\n      "
                + f'<joint name="base_x" type="slide" axis="1 0 0" stiffness="{_k}" damping="{_b}" springref="0"/>',
                count=1)
            model = mjm.MjModel.from_xml_string(xml)
        if _mu:
            for _gn in ("foot", "floor"):
                _gi = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, _gn)
                model.geom_friction[_gi][0] = float(_mu)
        def _kv(sp):
            return {k.strip(): float(v) for k, v in
                    (it.split("=") for it in sp.split(",") if it.strip())}

        def _bid(nm):
            i = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_BODY, nm)
            if i < 0:
                raise ValueError(f"바디 이름 없음: {nm} (오타 시 침묵 실패 방지)")
            return i
        if _mb:
            # 바디 질량 지정. 관성은 기본 **질량비로 스케일** (형상 불변 가정) — FS_IBODY가 있으면 그쪽 우선.
            _ibs = _kv(_ib) if _ib else {}
            for _n, _v in _kv(_mb).items():
                _i = _bid(_n)
                _r = float(_v) / float(model.body_mass[_i])
                model.body_mass[_i] = float(_v)
                if _n not in _ibs:
                    model.body_inertia[_i] *= _r
        if _ib:
            for _n, _v in _kv(_ib).items():
                model.body_inertia[_bid(_n)] *= float(_v)
        if _kd or _kf:
            _kj = safe.dofadr(model, "knee_motor", mjm)
            if _kd:
                model.dof_damping[_kj] = float(_kd)
            if _kf:
                model.dof_frictionloss[_kj] = float(_kf)
        if _cz:
            # CoM z 이동 → 관성은 평행축 정리로 보정하지 않는다 (여기 I는 **CoM 기준** 관성이므로
            # 형상이 그대로면 불변). 이동량은 물리적 합당 범위에서만 쓸 것.
            for _n, _v in _kv(_cz).items():
                model.body_ipos[_bid(_n)][2] += float(_v)
        if _mt:
            # 사용자 실측 (08-02): 케이블 제거 총질량 3.26kg (정합 허용대 3.26~3.3).
            # 링크 질량 확정 후 **잔여를 base**(전장·레일 캐리지 몫)에 몰아준다 — base는 어차피 적합축.
            _bi = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_BODY, "base")
            model.body_mass[_bi] += float(_mt) - float(model.body_mass.sum())
            if model.body_mass[_bi] <= 0:
                raise ValueError(f"base 질량이 음수 — 링크 질량 합이 총질량 초과 ({_mt})")
        _names = ["base_z", "hip_m", "hip", "knee_motor", "cpin", "knee"] + (["base_x"] if _rx else [])
        iq = {n: safe.qadr(model, n, mjm) for n in _names}
        dof = {n: safe.dofadr(model, n, mjm) for n in iq}
        _CACHE[key] = dict(model=model, xml=xml, tw=tw, iq=iq, dof=dof,
                           P=tw["P"], law=tw["law"], kr=tw["kr"], sprm=tw["sprm"])
    return _CACHE[key]


def _settle(ft, q1_0, q2_0, t_settle=None):
    """settle (cl_run23 settle 블록 미러 — PD는 hip_m 인코더에)."""
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    _nospr = os.environ.get("FS_NOSPR") == "1"   # 마라톤G: 부하연동 무릎 스프링(|s2| 비례) 절제
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    _ci = ft.get("cvt_init")            # 마라톤C #266: CVT 폐쇄 정합 초기화 (qpos_from_crank)
    if _ci is not None:
        b5 = _ci(q1_0, q2_0)
        md.qpos[iq["base_z"]] = b5[0]
        md.qpos[iq["hip_m"]] = b5[1]
        md.qpos[iq["hip"]] = 0.0
        md.qpos[iq["knee_motor"]] = b5[2]
        md.qpos[iq["cpin"]] = b5[3]
        md.qpos[iq["knee"]] = b5[4]
    else:
        md.qpos[iq["base_z"]] = 1.0
        md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2
        md.qpos[iq["hip"]] = 0.0
        md.qpos[iq["knee_motor"]] = -q2_0
        md.qpos[iq["cpin"]] = q2_0
        md.qpos[iq["knee"]] = -q2_0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    Ns = int(round((t_settle or P.J.T_SETTLE) / dt))
    c1f = c2f = 0.0
    for k in range(Ns):
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        c1 = S.SETTLE_KP * (q1_0 - thm) - S.SETTLE_KD * v1c
        c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
        c1f, c2f = c1, c2
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += _rise(v2c, kr, law_v0)
        tql = 0.0 if _nospr else (RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm)
                                  if sprm is not None else 0.0)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        mjm.mj_step(model, md)
    return md, c1f, c2f



def _tau2s(d, k_lo=96.0, k_hi=323.0, tau0=9.0):
    """2단 스프링 토크 (처짐 d[rad] → Nm). d0=tau0/k_lo에서 연속."""
    d0 = tau0 / k_lo
    a = abs(d)
    t = k_lo * a if a <= d0 else tau0 + k_hi * (a - d0)
    return np.sign(d) * t


def _bias_ramp():
    """마라톤C: FS_BIAS_RAMP="기울기@임계°" — 접지 깊이 결합 hip 정역학 항 (무슬립 합의 갭).
    bias1(q2) = bias1 + k·max(0, th − q2°) [Nm]. 상수 bias(공중 앵커)와 별층 — 전 세션 고정."""
    v = os.environ.get("FS_BIAS_RAMP")
    if not v:
        return None
    k_, th_ = v.split("@")
    return (float(k_), float(th_))


def _rise(v2c, kr, law_v0):
    """마라톤F F4: 상승항 형태 교정 — `k·dq2·(1−gate_v)`는 고속에서 무한 선형 증가(=음의 감쇠,
    에너지원). 물리적으로는 포화해야 한다. FS_RISE_CAP=<Nm>이면 tanh 포화형으로 교체:
        k·C·tanh(dq2·(1−gate_v)/C)   — 저속 구간은 원식과 1차 일치, 고속에서 |·|≤k·C로 상한.
    FS_RISE_SCALE=<배>는 크기만 스케일 (형태 대조군). 둘 다 미지정이면 원식 그대로."""
    r = float(RU.rise_term(v2c, kr, law_v0))
    _c = os.environ.get("FS_RISE_CAP")
    if _c:
        C = float(_c)
        if C > 0 and kr:
            x = r / kr                      # = dq2·(1−gate_v)
            r = kr * C * float(np.tanh(x / C))
    _sc = os.environ.get("FS_RISE_SCALE")
    if _sc:
        r *= float(_sc)
    return r


def _svg_gate(v, spec):
    """F-H8 supp 속도 게이트: spec="v1"(0부터 선형 소멸) 또는 "v0,v1"(v0까지 온전, v1에서 0)."""
    if not spec:
        return 1.0
    p = [float(x) for x in str(spec).split(",")]
    av = abs(v)
    if len(p) == 1:
        return max(0.0, 1.0 - av / p[0])
    v0, v1 = p
    if av <= v0:
        return 1.0
    return max(0.0, (v1 - av) / (v1 - v0))


def _vceil_init():
    """마라톤F F-H7: 전압 포락선 토크 천장 — FS_VCEIL="w0,w1[,tau_max]" [rad/s, rad/s, Nm].

    |ω|≤w0 천장 tau_max(기본 20.5=raw35.5 환산) 평평 · w0~w1 선형 강하 · ≥w1 에서 0.
    REJECTED #61 재심 (22일 판독은 3~22rad/s 평평 = w0≥22 하한; push 말기 ω 25~30rad/s는 미판독 영역).
    모터링 사분면(τ·ω>0)만 적용 (제동은 back-EMF가 돕는 방향). 관측은 커맨드 수준 유지."""
    v = os.environ.get("FS_VCEIL")
    if not v:
        return None
    p = [float(x) for x in v.split(",")]
    return (p[0], p[1], p[2] if len(p) > 2 else 20.5)


def _vceil_cap(s, w, vc):
    w0, w1, tm = vc
    if s * w <= 0.0:
        return s
    aw = abs(w)
    if aw <= w0:
        return s
    cap = tm * max(0.0, (w1 - aw) / (w1 - w0))
    return float(np.clip(s, -cap, cap))


def _escrow_gate(bank, tau, vel, dt):
    """마라톤F F1: 저장-방출 에너지 회계 게이트 (층별 은행).

    p = τ·v ≤ 0 (흡수) → 은행 적립 · p > 0 (방출) → 잔고 한도 내만 (초과분 τ 스케일 컷).
    형태(적합 법칙)는 유지하고 순주입만 구조적으로 0으로. (은행, 게이트 후 τ) 반환."""
    p = tau * vel
    if p <= 0.0:
        return bank - p * dt, tau              # 흡수: −p·dt 적립
    e = p * dt
    if e <= bank:
        return bank - e, tau
    if bank <= 0.0:
        return 0.0, 0.0
    return 0.0, tau * (bank / e)


def _tmap_init(P=None, A=None):
    """마라톤G A: raw → 축토크 변환기 교체 (None = 기존 a_hat 유지).

    `FS_TMAP=canon`  → **G5 정본곡선**(분동으로 크기 고정 + 로드셀로 raw 36 까지 실측 연결)
      raw = d1·τ + d2·τ|τ| + d3·τ³ 의 역함수 (단조 — 판별식<0 확인). `_G5_curve_final.json`.
    `FS_TRANS=c[,gmin]` → **상태(속도) 의존 전달률** g(ω) = clip(1 − c·|ω|, gmin, 1) 를 곱한다.
      근거(G10): 정적 분동/로드셀 교정은 ω≈0 조건 → g(0)=1 이어야 하고,
      푸시(ω 13~20 rad/s)의 에너지 감사가 요구하는 실효 배율은 0.66~0.75.
      c=0 이면 전달률 비활성(정본곡선 그대로).
    `FS_TSCALE=k`  → 지금 맵을 **k배** (형태 유지·크기만). supp 대체 실험용:
      G11-D 가 인공 지지층 몫 = 주입 에너지의 18.8% 로 계량했으므로 k≈1.19 가 에너지 등가.
    ※ A_c* 스캔(08-08) 결론: canon 단독 교체는 전 구성 게이트 탈락 — **필요한 보정은
      속도 의존이 아니라 토크 의존**(a_hat/canon 비가 0.32→0.66 으로 raw 와 함께 변함)이었다.
    """
    md_ = os.environ.get("FS_TMAP")                 # None | "canon" | "canon_cap" | "ahat" | "model"
    k = float(os.environ.get("FS_TSCALE", "1") or 1)
    sp = (os.environ.get("FS_TRANS") or "0").split(",")
    c = float(sp[0] or 0); gmin = float(sp[1]) if len(sp) > 1 else 0.35
    if md_ is None and k == 1.0 and c == 0.0:
        return None                                 # 완전 레거시 경로 (비트 동일)
    if md_ in ("canon", "canon_cap", "model"):
        pass
    if md_ in ("canon", "canon_cap"):
        import json as _j
        cf = _j.load(open(HERE / "_G5_curve_final.json", encoding="utf-8"))
        d1, d2, d3 = cf["d1"], cf["d2"], cf["d3"]
        _dc = [float(x) for x in (os.environ.get("FS_TDCAP", "0") or "0").split(",")]
        dcap_k = _dc[0]; dcap_h = _dc[1] if len(_dc) > 1 else _dc[0]   # 무릎, 힙 (부호가 반대인 supp 대응)

        def _canon(raw):
            t = raw / d1
            for _ in range(40):
                f = d1 * t + d2 * t * abs(t) + d3 * t ** 3 - raw
                df = d1 + 2 * d2 * abs(t) + 3 * d3 * t * t
                t = t - f / (df if abs(df) > 1e-9 else 1e-9)
            return t

        if md_ == "canon":
            def base(raw, v, ch=1):
                return _canon(raw)
        else:
            # canon_cap: **분동 검증분만 채택**. τ = a_hat + clip(canon − a_hat, ±Δmax).
            #   canon−a_hat 은 raw 5 에서 3.4Nm → raw 35.5 에서 10.4Nm 로 계속 커지는데
            #   raw>11.5 구간은 **절대값 불신 로드셀의 모양** 외삽분 (데이터 사전 등재).
            #   반면 인공 지지층 supp 는 2~5Nm 로 **포화** → 실제 결손은 포화형이다 (G14-B).
            def base(raw, v, ch=1):
                a = float(P.J.ahat(A, np.array([raw]), np.array([v]))[0])
                dd = _canon(raw) - a
                dc = dcap_k if ch else dcap_h
                return a + (dd if dc <= 0 else max(-dc, min(dc, dd)))
    elif md_ == "model":
        # ─────────────── 마라톤G G24: **a_hat 폐기** 모터 모델군 (사용자 지시 08-08) ───────────────
        # a_hat 은 논문식 하나일 뿐이고, ①분동으로 틀린 게 증명됐고 ②마찰항이 섞여 있어
        # 트윈 관절마찰과 **이중 차감**되며 ③속도항이 캡 지점에서 불연속 전환을 만든다.
        # 여기서는 raw→축토크 를 **순수 변환**으로 두고, 마찰은 트윈 플랜트에 맡긴다.
        #   FS_TMODEL="form:p1,p2,..."   (ch=0 힙, ch=1 무릎 — 공통 파라미터)
        #     lin:k            τ = k·raw                              (1) 기준선
        #     sat:k,c          τ = k·raw − c·raw|raw|                 (2) 자기포화/기어 부하손
        #     cub:k,c,d        τ = k·raw − c·raw|raw| − d·raw³        (3) 포화 3차
        #     pw:k,rc,k2       raw≤rc 는 k·raw, 위는 기울기 k2        (2+) **측정구간/외삽구간 분리**
        #     vis:k,b          τ = k·raw − b·ω                        (2) 점성 (사용자 지시)
        #     cou:k,fc         τ = k·raw − fc·tanh(ω/0.05)            (2) 쿨롱
        #     visc:k,c,b       포화 + 점성                             (3)
        #     env:k,a,b        τ = sign·min(|k·raw|, a − b|ω|)        (3) 전압 포락선 (REJECTED #61 재심)
        #   ※ k 의 기준값 = **1.24 Nm/raw** (분동 실측, raw≤11.5 선형성 ±1.7% 확인 — G3/G4)
        spec = (os.environ.get("FS_TMODEL") or "lin:1.24").split(":")
        form = spec[0]
        pr = [float(x) for x in spec[1].split(",")] if len(spec) > 1 and spec[1] else []
        g = lambda i, d: pr[i] if len(pr) > i else d

        def base(raw, v, ch=1):
            r = float(raw); a = abs(r); s = 1.0 if r >= 0 else -1.0
            k = g(0, 1.24)
            if form == "lin":
                return k * r
            if form == "sat":
                return k * r - g(1, 0.0) * r * a
            if form == "cub":
                return k * r - g(1, 0.0) * r * a - g(2, 0.0) * r ** 3
            if form == "pw":
                rc, k2 = g(1, 11.5), g(2, 0.40)
                return s * (k * a if a <= rc else k * rc + k2 * (a - rc))
            if form == "vis":
                return k * r - g(1, 0.0) * float(v)
            if form == "cou":
                return k * r - g(1, 0.0) * np.tanh(float(v) / 0.05)
            if form == "visc":
                return k * r - g(1, 0.0) * r * a - g(2, 0.0) * float(v)
            if form == "env":
                cap = max(g(1, 48.5) - g(2, 0.73) * abs(float(v)), 0.0)
                return s * min(k * a, cap)
            raise ValueError(f"FS_TMODEL form 미지원: {form}")
    else:                                           # a_hat 원형 (형태 유지, 크기만 k배)
        def base(raw, v, ch=1):
            return float(P.J.ahat(A, np.array([raw]), np.array([v]))[0])

    def tmap(raw, v, ch=1):
        g = 1.0 if c <= 0 else min(1.0, max(gmin, 1.0 - c * abs(v)))
        return base(float(raw), float(v), ch) * k * g
    return tmap


def _nosupp_init():
    """FS_NOSUPP=1 → 인공 지지층(supp·rise·hip_supp) 전면 비활성 (마라톤G A 절제)."""
    return os.environ.get("FS_NOSUPP") == "1"


def _escrow_init():
    """FS_ESCROW="supp2,hsupp1,spr" → 층별 은행 dict (초기잔고 FS_ESCROW_SEED [J], 기본 0)."""
    v = os.environ.get("FS_ESCROW")
    if not v:
        return None
    seed = float(os.environ.get("FS_ESCROW_SEED", "0") or 0)
    return {k.strip(): seed for k in v.split(",") if k.strip()}


_PSL_PRISTINE = {}     # id(model) → 원본 (foot, floor) 마찰 — _PreSlide 누수 자가 치유용


class _PreSlide:
    """마라톤E P4: stick-slip 이력 마찰 (Karnopp형 presliding) — FS_PRESLIDE="mu_s[,mu_k[,v_stop[,mu_hold]]]".

    점착(stick) 중엔 접촉쌍 마찰을 mu_hold(기본 2.0)로 올려 규제화 쿨롱의 파단 이하 크리프를 억제
    (0602 깊은 앉기 유지 창의 MA q2 악화 원인 = 유지 구간 위상 활주). 파단은 |Ft|/N ≥ mu_s에서만
    → slide 상태(마찰 mu_k, 기본 =mu_s=0.85 데이터 하한) → 발 접선속도 |v_t|<v_stop 재점착.
    발+바닥 geom 동시 설정. 모델이 _CACHE 공유이므로 rollout 양 종단에서 restore() 의무."""

    def __init__(self, model, fg):
        p = [float(v) for v in os.environ["FS_PRESLIDE"].split(",")]
        self.mu_s = p[0]
        self.mu_k = p[1] if len(p) > 1 else p[0]
        self.v_stop = p[2] if len(p) > 2 else 0.02
        self.mu_hold = p[3] if len(p) > 3 else 2.0
        self.model = model; self.fg = fg
        self.gf = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "floor")
        # 침묵실패 방역: 롤아웃이 예외로 이탈하면 restore()가 건너뛰어져 캐시 모델에 stick 마찰이 남는다
        # → 원본값을 모델별로 1회 기록해 두고, 이후 생성 시 그 값으로 되돌린 뒤 시작 (누수 자가 치유)
        _key = id(model)
        if _key in _PSL_PRISTINE:
            self.orig = _PSL_PRISTINE[_key]
            model.geom_friction[fg][0], model.geom_friction[self.gf][0] = self.orig
        else:
            self.orig = (float(model.geom_friction[fg][0]), float(model.geom_friction[self.gf][0]))
            _PSL_PRISTINE[_key] = self.orig
        self.slide = False; self.fx_prev = None
        self._cf = np.zeros(6)
        self._set(self.mu_hold)

    def _set(self, mu):
        self.model.geom_friction[self.fg][0] = mu
        self.model.geom_friction[self.gf][0] = mu

    def step(self, md, dt):
        """mj_step 직후 호출: 상태 갱신 + 다음 스텝 마찰 설정. (법선합, 접선합) 반환 (cfz/cfx 로깅 겸용)."""
        fz = ft_ = 0.0
        for ci in range(md.ncon):
            c = md.contact[ci]
            if c.geom1 == self.fg or c.geom2 == self.fg:
                mjm.mj_contactForce(self.model, md, ci, self._cf)
                fz += abs(float(self._cf[0]))
                ft_ += float(np.hypot(self._cf[1], self._cf[2]))
        fx = float(md.geom_xpos[self.fg][0])
        vt = 0.0 if self.fx_prev is None else (fx - self.fx_prev) / dt
        self.fx_prev = fx
        if not self.slide:
            if fz > 1.0 and ft_ >= self.mu_s * fz:
                self.slide = True
        elif abs(vt) < self.v_stop or fz <= 1.0:
            self.slide = False
        self._set(self.mu_k if self.slide else self.mu_hold)
        return fz, ft_

    def restore(self):
        self.model.geom_friction[self.fg][0] = self.orig[0]
        self.model.geom_friction[self.gf][0] = self.orig[1]


def rollout_cl_fs(ft, tg, qd1g, qd2g, dqd1g, dqd2g, gains, t_end, t_after=0.05, two_stage=False, bias1=0.0, knee_deep=None, fade=False, taulim=None, lim_raw=None, lim2_nm=None, vdes_ff=True, init_meas=None):
    """CL 통짜 — settle 후 폴더 게인 PD(θ_m 기준, hip α 없음·knee α는 gains에 이미 반영).
    init_meas=(q1,q2,dq1,dq2,raw1,raw2): settle 대신 **창 시작 실측 상태 1회 앵커** (ModeA와 동일 규칙,
    마라톤D P16 사용자 지시). thm1을 실측 q1에 앵커·처짐은 측정 토크에서 (F15/P12 규약).
    lim_raw/lim2_nm: 마라톤C P5~6 잔재 (P7 철회 — 사용자 확인: 제한은 전류 포화 35.5 단일뿐). 미사용 유지.
    vdes_ff=False: dq_des 미인가 세션 (0421 위치제어 등 — 데이터 사전 메타) — 실효 PD = kp·e − kd·dq
    (MIT 모드 v_des=0). P8 형태 동정: 0421 M2 RMSE 3.61 vs M1 10.88 raw."""
    _ramp = _bias_ramp()
    model = ft["model"]; P = ft["P"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    _nospr = os.environ.get("FS_NOSPR") == "1"   # 마라톤G: 부하연동 무릎 스프링(|s2| 비례) 절제
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    kp1, kd1, kp2, kd2 = gains
    if init_meas is not None:
        _q1m, _q2m, _dq1m, _dq2m, _r1m, _r2m = init_meas
        md = mjm.MjData(model)
        _s10 = float(P.J.ahat(A, np.array([float(np.clip(_r1m, -TW.R19.CLIP, TW.R19.CLIP))]),
                              np.array([float(_dq1m)]))[0])
        _d0 = float(np.clip(np.sign(_s10) * (abs(_s10) / 96.0 if abs(_s10) <= 9
                                             else 9 / 96.0 + (abs(_s10) - 9) / 323.0), -0.3, 0.3))
        _ci0 = ft.get("cvt_init")
        if _ci0 is not None:
            # 마라톤F F3: CVT(l_i≠30)는 평행사변형 관례가 폐쇄 모순 → qpos_from_crank로 정합 초기화
            # 반환 = 5q [bz, hip_m, crank, cpin, knee] — 6q(fs, hip 처짐 조인트 포함)에 이름 매핑
            _qc5 = np.asarray(_ci0(_q1m, _q2m), float)
            md.qpos[iq["base_z"]] = _qc5[0]
            md.qpos[iq["hip_m"]] = _qc5[1]
            md.qpos[iq["hip"]] = _d0                   # 처짐 분할 (앵커 규약 유지)
            md.qpos[iq["knee_motor"]] = _qc5[2]
            md.qpos[iq["cpin"]] = _qc5[3]
            md.qpos[iq["knee"]] = _qc5[4]
        else:
            md.qpos[iq["base_z"]] = 1.0
            md.qpos[iq["hip_m"]] = -_q1m - np.pi / 2   # thm1(모터측) = 실측 앵커
            md.qpos[iq["hip"]] = _d0
            md.qpos[iq["knee_motor"]] = -_q2m
            md.qpos[iq["cpin"]] = _q2m
            md.qpos[iq["knee"]] = -_q2m
        mjm.mj_forward(model, md)
        _fg0 = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
        md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[_fg0][2]) + P.J._P["S"].FOOT_RADIUS
        _c1, _c12 = np.cos(_q1m), np.cos(_q1m + _q2m)
        md.qvel[:] = 0
        md.qvel[dof["base_z"]] = -0.25 * (_c1 * _dq1m + _c12 * (_dq1m + _dq2m))
        md.qvel[dof["hip_m"]] = -_dq1m
        if _ci0 is not None:
            # 폐쇄 정합 속도: d(qpos)/d(q2) 수치 미분 × dq2 (전달비 r(q)이 자동 반영) — 5q 인덱스 2/3/4
            _eps = 1e-5
            _dr5 = (np.asarray(_ci0(_q1m, _q2m + _eps), float) - _qc5) / _eps
            for _j, _n in ((2, "knee_motor"), (3, "cpin"), (4, "knee")):
                md.qvel[dof[_n]] = _dr5[_j] * _dq2m
        else:
            md.qvel[dof["knee_motor"]] = -_dq2m
            md.qvel[dof["cpin"]] = _dq2m
            md.qvel[dof["knee"]] = -_dq2m
        mjm.mj_forward(model, md)
    else:
        md, _, _ = _settle(ft, float(qd1g[0]), float(qd2g[0]))
    dt = model.opt.timestep
    # 마라톤C P12: 커맨드 지연 (전송+펌웨어+전류루프) — dq2 잔차의 가속도 기저 서명 (~7-9ms) 반영
    _dly_n = int(round(float(os.environ.get("FS_CMD_DELAY", "0") or 0) / dt))
    _dbuf = [] if _dly_n > 0 else None
    # P13: kd 속도 신호 지연 (펌웨어 속도 추정 필터 — kd 비례 발현, 일괄 지연과 구별)
    _vtc = float(os.environ.get("FS_KD_VLAG", "0") or 0)
    _vaf = dt / (_vtc + dt) if _vtc > 0 else None
    _v1f = _v2f = 0.0
    # P17: 커맨드 출력 1차 지연 LPF (지연군 판독 tc — 기록 raw=전달 전류이므로 관측·플랜트 동일값)
    _ctc = float(os.environ.get("FS_CMD_LPF", "0") or 0)
    _caf = dt / (_ctc + dt) if _ctc > 0 else None
    _c1f = _c2f = 0.0
    tc_f = float(os.environ.get("FS_TC", "0.010"))
    s1f = 0.0
    af = dt / max(tc_f, dt)
    N = int(round((t_end + t_after) / dt))
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "defl", "bz", "tsp1", "s1f", "fx",
            "cfx", "cfz", "bx", "slipv")
    Lg = {k: np.zeros(N) for k in keys}
    _fgx = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")   # 마라톤D P3: 발 x (슬립 지표)
    # 마라톤E P12: 접촉 물질점의 접선속도 = **진짜 미끄럼**(구름이면 0) — 발이동을 구름/슬립으로 분해
    _slog = os.environ.get("FS_SLIPLOG") == "1"
    if _slog:
        _fbody = int(model.geom_bodyid[_fgx])
        _jacp = np.zeros((3, model.nv))
    _cf6 = np.zeros(6)                                            # P14: 발 접촉 법선/접선력 (슬립 방아쇠 진단)
    # F28b 하중 인식 간섭: N(t)=sim 발 접촉 수직력 / mg 스케일 (하강≈1 → 세션 적합 보존)
    load_on = os.environ.get("FS_KNEE_LOAD") == "1" and knee_deep
    if load_on:
        _fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
        _Nmg = float(model.body_mass.sum() * 9.81)
        _cf = np.zeros(6)
    # 마라톤D P6 (사용자 가설): 레일 캐리지 마찰 — 발 수평 반력 비례 쿨롱 (base_z 저항)
    _rail = float(os.environ.get("FS_RAIL", "0") or 0)
    if _rail > 0:
        _fgR = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
        _cfR = np.zeros(6)
    _rxv = os.environ.get("FS_RAILX")        # 마라톤E P2: 레일 횡 컴플라이언스 → 횡하중=스프링력
    _rxkb = tuple(float(v) for v in _rxv.split(",")) if (_rxv and "base_x" in dof) else None
    _w2 = float(os.environ.get("FS_W2", "0") or 0)
    _eta = float(os.environ.get("FS_ETA", "1") or 1)   # P7 고속 제곱 소산 (버스트 전용)
    _psl = _PreSlide(model, _fgx) if os.environ.get("FS_PRESLIDE") else None
    _eled = ({k_: np.zeros(N) for k_ in ("motor1", "motor2", "supp2", "hsupp1", "spr_tql", "kdeep2", "bias_h")}
             if os.environ.get("FS_ELEDGER") == "1" else None)   # 층별 순간 파워 [W] (오프라인 창 적분)
    _esc = _escrow_init()                  # 마라톤F F1: 층별 에너지 회계 (None = 비활성)
    _est = float(os.environ.get("FS_ESC_STORE", "1") or 1)   # F1b: 하강 흡수 증폭 (supp2)
    _svg = os.environ.get("FS_SUPP_VG") or None              # F-H8: supp 속도 게이트 spec (None=비활성)
    _vcl = _vceil_init()                   # 마라톤F F-H7: 전압 포락선 천장 (None = 비활성)
    _tmap = _tmap_init(P, A); _nosupp = _nosupp_init()   # 마라톤G A: 정본곡선 전달률 · 지지층 절제
    for k in range(N):
        tc = k * dt
        tm_ = min(tc, t_end)
        qd1 = float(np.interp(tm_, tg, qd1g)); qd2 = float(np.interp(tm_, tg, qd2g))
        dqd1 = float(np.interp(tm_, tg, dqd1g)); dqd2 = float(np.interp(tm_, tg, dqd2g))
        thm = -md.qpos[iq["hip_m"]] - np.pi / 2
        q2c = -md.qpos[iq["knee_motor"]]
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        b_eff = 0.0
        if _vaf is not None:
            _v1f += _vaf * (v1c - _v1f)
            _v2f += _vaf * (v2c - _v2f)
        if tc <= t_end:
            _f1 = dqd1 if vdes_ff else 0.0
            _f2 = dqd2 if vdes_ff else 0.0
            _vk1 = _v1f if _vaf is not None else v1c
            _vk2 = _v2f if _vaf is not None else v2c
            c1 = kp1 * (qd1 - thm) + kd1 * (_f1 - _vk1)
            c2 = kp2 * (qd2 - q2c) + kd2 * (_f2 - _vk2)
        else:
            c1 = c2 = 0.0
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP))
        c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        if _caf is not None:
            _c1f += _caf * (c1 - _c1f)
            _c2f += _caf * (c2 - _c2f)
            c1, c2 = _c1f, _c2f
        if lim_raw is not None:
            if lim_raw[0]:
                c1 = float(np.clip(c1, -lim_raw[0], lim_raw[0]))
            if lim_raw[1]:
                c2 = float(np.clip(c2, -lim_raw[1], lim_raw[1]))
        # 관측 = 계산 시점 커맨드 (실기 로그 타이밍), 플랜트 = 지연 커맨드 (모터 실행 타이밍)
        _cv = (lambda r, v: _tmap(r, v)) if _tmap is not None else \
              (lambda r, v: float(P.J.ahat(A, np.array([r]), np.array([v]))[0]))
        s1o = _cv(c1, v1c)
        s2o = _cv(c2, v2c)
        if _dbuf is not None:
            _dbuf.append((c1, c2))
            c1, c2 = _dbuf[max(0, len(_dbuf) - 1 - _dly_n)]
            s1 = _cv(c1, v1c, 0)
            s2 = _cv(c2, v2c, 1)
        else:
            s1, s2 = s1o, s2o
        if lim2_nm is not None:
            s2 = float(np.clip(s2, -lim2_nm, lim2_nm))
            s2o = float(np.clip(s2o, -lim2_nm, lim2_nm))
        if taulim is not None:
            s1 = float(np.clip(s1, -taulim, taulim))   # F26 진단: 세션 토크 상한 (실측 플래토 판독)
            s1o = float(np.clip(s1o, -taulim, taulim))
        if _vcl is not None:               # F-H7: 전압 포락선 천장 (플랜트 전달만 — 관측 s1o/s2o 무변)
            s1 = _vceil_cap(s1, v1c, _vcl)
            s2 = _vceil_cap(s2, v2c, _vcl)
        supp = 0.0 if _nosupp else RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr and not _nosupp:
            supp += _rise(v2c, kr, law_v0)
        if _svg is not None:
            supp *= _svg_gate(v2c, _svg)   # F-H8: 유지 전용 게이트 (고속 소멸 = 마찰성 — 주입 불가 형태)
        if _esc is not None and "supp2" in _esc:
            if _est > 1.0 and supp * v2c < 0.0:
                supp *= _est               # F1b: 하강 흡수 증폭 (탄성 저장 경로) — 증폭분 그대로 은행 적립
            _esc["supp2"], supp = _escrow_gate(_esc["supp2"], supp, v2c, dt)
        tql = 0.0 if _nospr else (RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm)
                                  if sprm is not None else 0.0)
        if _esc is not None and "spr" in _esc:
            # CVT 소산항(아래 tql +=)은 열소산이라 은행 적립 대상이 아님 — 스프링분만 게이트
            _esc["spr"], tql = _escrow_gate(_esc["spr"], tql, float(md.qvel[dof["knee"]]), dt)
        if _eta < 1.0:                   # P8 기어박스 η^sign 재심 (모터링 사분면만) — 관측은 커맨드 수준 유지
            s1 = s1 * (_eta if s1 * v1c > 0 else 1.0)
            s2 = s2 * (_eta if s2 * v2c > 0 else 1.0)
        _cd = ft.get("cvt_diss")        # 마라톤C #266: CVT 전달비 소산 (a_cvt_mirror 문자 미러)
        if _cd is not None:
            _cc, _qg, _rg = _cd
            _rr = float(np.interp(float(md.qpos[iq["knee_motor"]]), _qg, _rg))
            _amp = max(1.0 / max(abs(_rr), 0.2) - 1.0, 0.0)
            tql += -_cc * abs(s2) * _amp * float(np.tanh(float(md.qvel[dof["knee"]]) / 1.0))
        _hsupp = 0.0 if _nosupp else RU.hip_supp_scalar(s1, s2, v1c)
        if _esc is not None and "hsupp1" in _esc:
            _esc["hsupp1"], _hsupp = _escrow_gate(_esc["hsupp1"], _hsupp, v1c, dt)
        md.ctrl[:] = [-(s1 + _hsupp), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        if _eled is not None:              # 마라톤E P9: 층별 순간 파워 원장 (진단 전용 — 동역학 무변경)
            _vkn = float(md.qvel[dof["knee"]])
            _eled["motor1"][k] = s1 * v1c             # 모터 명령 파워 (로봇 좌표)
            _eled["motor2"][k] = s2 * v2c
            _eled["supp2"][k] = supp * v2c            # 무릎 지지 적층 (ctrl 경유)
            _eled["hsupp1"][k] = _hsupp * v1c         # 힙 지지 적층
            _eled["spr_tql"][k] = tql * _vkn          # 스프링/CVT 소산 항 (knee link)
        if two_stage or bias1:
            dq_s = float(md.qpos[iq["hip"]])
            corr = (FM.KS_HIP * dq_s - _tau2s(dq_s)) if two_stage else 0.0
            b_base = bias1
            if _ramp is not None:
                b_base = bias1 + _ramp[0] * max(0.0, _ramp[1] - np.degrees(q2c))
            b_eff = b_base
            if fade and abs(v1c) > 1.0:
                b_eff = b_base * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)
            if os.environ.get("FS_BIAS_SIDE") == "motor":
                # F56/F57: 자세무관 오프셋의 물리 후보 = 모터측 → ctrl에 얹고 s1 로그에도 포함 (회계 일치)
                md.qfrc_applied[dof["hip"]] = corr
                md.ctrl[0] = md.ctrl[0] - b_eff          # hip ctrl 부호 규약: -(s1+...)
                s1 = s1 + b_eff
            else:
                md.qfrc_applied[dof["hip"]] = corr + b_eff
            if _eled is not None:
                _eled["bias_h"][k] = (corr + b_eff) * float(md.qvel[dof["hip"]])
        _dc = os.environ.get("FS_DEEP_DMPCUT")
        _fcut = os.environ.get("FS_DEEP_FLCUT")
        if _dc is not None or _fcut is not None:
            # F49 정찰: 운영영역(깊이) 게이트 hip 감쇠 절감 — 깊은 굴곡(q2<-120°)에서만 XML 감쇠 일부 상쇄
            q2r_ = -float(md.qpos[iq["knee_motor"]])
            _th = float(os.environ.get("FS_DEEP_TH", "-120.0"))
            gg = 1.0 / (1.0 + np.exp((q2r_ - np.radians(_th)) / np.radians(4.0)))
            v_hm = float(md.qvel[dof["hip_m"]])
            _q = (float(_dc) * gg * v_hm) if _dc is not None else 0.0
            if _fcut is not None:
                _q += float(_fcut) * gg * float(np.tanh(v_hm / 0.05))
            md.qfrc_applied[dof["hip_m"]] = _q
        if knee_deep:
            kd_, q20_ = knee_deep
            q2r = -float(md.qpos[iq["knee_motor"]])
            tau_ext = kd_ * max(0.0, q20_ - q2r)
            _rel = os.environ.get("FS_KNEE_REL")
            if _rel is not None and v2c > 0.2:
                tau_ext *= float(_rel)
            elif fade and v2c > 1.0:
                tau_ext *= max(0.0, 1.0 - (v2c - 1.0) / 2.0)
            if load_on:
                Nf = 0.0
                for ci in range(md.ncon):
                    _c = md.contact[ci]
                    if _c.geom1 == _fg or _c.geom2 == _fg:
                        mjm.mj_contactForce(model, md, ci, _cf)
                        Nf += abs(float(_cf[0]))
                tau_ext *= min(Nf / _Nmg, 3.0)
            md.qfrc_applied[dof["knee_motor"]] = -tau_ext
            if _eled is not None:
                _eled["kdeep2"][k] = tau_ext * v2c      # qfrc −tau_ext × qvel(−v2c) = +tau_ext·v2c
        if _rail > 0:
            if _rxkb is not None:
                _Fx = _rxkb[0] * float(md.qpos[dof["base_x"]]) + _rxkb[1] * float(md.qvel[dof["base_x"]])
                _skip_contact = True
            else:
                _skip_contact = False
            _Fx = _Fx if _rxkb is not None else 0.0
            for ci in range(0 if _rxkb is not None else md.ncon):
                _c = md.contact[ci]
                if _c.geom1 == _fgR or _c.geom2 == _fgR:
                    mjm.mj_contactForce(model, md, ci, _cfR)
                    _Fx += float((np.array(_c.frame).reshape(3, 3).T @ _cfR[:3])[0])
            _vbz = float(md.qvel[dof["base_z"]])
            _g = np.tanh(max(_vbz, 0.0) / 0.05) if os.environ.get("FS_RAIL_UP") == "1" else np.tanh(_vbz / 0.05)
            md.qfrc_applied[dof["base_z"]] = -_rail * abs(_Fx) * float(_g)
        if _w2 > 0:
            _v2m = float(md.qvel[dof["knee_motor"]])
            md.qfrc_applied[dof["knee_motor"]] = md.qfrc_applied[dof["knee_motor"]] - _w2 * _v2m * abs(_v2m)
            _v1m = float(md.qvel[dof["hip_m"]])
            md.qfrc_applied[dof["hip_m"]] = -_w2 * _v1m * abs(_v1m)   # 순할당 (hip_m 유일 기록자)
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            if _psl is not None:
                _psl.restore()
            return None
        Lg["t"][k] = tc
        Lg["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
        Lg["q1"][k] = -(md.qpos[iq["hip_m"]] + md.qpos[iq["hip"]]) - np.pi / 2
        Lg["q2"][k] = -md.qpos[iq["knee_motor"]]
        Lg["dq1"][k] = -md.qvel[dof["hip_m"]]
        Lg["dq2"][k] = -md.qvel[dof["knee_motor"]]
        Lg["s1"][k] = s1o
        Lg["s2"][k] = s2o
        Lg["defl"][k] = md.qpos[iq["hip"]]
        Lg["bz"][k] = md.qpos[iq["base_z"]]
        Lg["fx"][k] = float(md.geom_xpos[_fgx][0])
        Lg["bx"][k] = float(md.qpos[dof["base_x"]]) if "base_x" in dof else 0.0
        if _psl is not None:
            _fz, _fxt = _psl.step(md, dt)                         # 상태 갱신 + 접촉력 (이중 루프 회피)
        else:
            _fz = _fxt = 0.0
            for _ci in range(md.ncon):
                _c = md.contact[_ci]
                if _c.geom1 == _fgx or _c.geom2 == _fgx:
                    mjm.mj_contactForce(model, md, _ci, _cf6)
                    _fz += abs(float(_cf6[0]))                    # 접촉 법선 (contact frame)
                    _fxt += float(np.hypot(_cf6[1], _cf6[2]))     # 접선 크기
        Lg["cfz"][k] = _fz
        Lg["cfx"][k] = _fxt
        if _slog and _fz > 1.0:
            for _ci in range(md.ncon):
                _c = md.contact[_ci]
                if _c.geom1 == _fgx or _c.geom2 == _fgx:
                    mjm.mj_jac(model, md, _jacp, None, np.asarray(_c.pos, float), _fbody)
                    Lg["slipv"][k] = float(_jacp[0] @ md.qvel)   # 접촉점 물질속도 x = 미끄럼 속도
                    break
        Lg["tsp1"][k] = _tau2s(float(md.qpos[iq["hip"]])) + (b_eff if (two_stage or bias1) else 0.0)
        s1f += af * (s1o - s1f)
        Lg["s1f"][k] = s1f
    if _psl is not None:
        _psl.restore()
    if _eled is not None:
        Lg["eledger"] = _eled
    return Lg


def rollout_ol_fs(ft, tg, raw1g, raw2g, q1_0, q2_0, dq1_0, dq2_0, t_end, t_after=0.05):
    """ModeA — 측정 raw 주입 (mshoot 창용: 측정상태 초기화, 스프링 처짐은 정적 τ/k로 시드)."""
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    _nospr = os.environ.get("FS_NOSPR") == "1"   # 마라톤G: 부하연동 무릎 스프링(|s2| 비례) 절제
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    r1_0 = float(np.interp(0.0, tg, raw1g))
    v1_0 = float(dq1_0)
    s1_0 = float(P.J.ahat(A, np.array([np.clip(r1_0, -TW.R19.CLIP, TW.R19.CLIP)]), np.array([v1_0]))[0])
    defl0 = np.clip(s1_0 / FM.KS_HIP, -0.3, 0.3)
    md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2 - defl0
    md.qpos[iq["hip"]] = defl0
    md.qpos[iq["knee_motor"]] = -q2_0
    md.qpos[iq["cpin"]] = q2_0
    md.qpos[iq["knee"]] = -q2_0
    md.qpos[iq["base_z"]] = 1.0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    L = 0.25
    c1, c12 = np.cos(q1_0), np.cos(q1_0 + q2_0)
    dbz = -L * (c1 * dq1_0 + c12 * (dq1_0 + dq2_0))
    md.qvel[:] = 0
    md.qvel[dof["base_z"]] = dbz
    md.qvel[dof["hip_m"]] = -dq1_0
    md.qvel[dof["knee_motor"]] = -dq2_0
    md.qvel[dof["cpin"]] = dq2_0
    md.qvel[dof["knee"]] = -dq2_0
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    N = int(round((t_end + t_after) / dt))
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "bz")
    Lg = {k: np.zeros(N) for k in keys}
    for k in range(N):
        tc = k * dt
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        if tc <= t_end:
            r1 = float(np.interp(tc, tg, raw1g)); r2 = float(np.interp(tc, tg, raw2g))
        else:
            r1 = r2 = 0.0
        r1 = float(np.clip(r1, -TW.R19.CLIP, TW.R19.CLIP))
        r2 = float(np.clip(r2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([r1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([r2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += _rise(v2c, kr, law_v0)
        tql = 0.0 if _nospr else (RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm)
                                  if sprm is not None else 0.0)
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        mjm.mj_step(model, md)
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
        Lg["bz"][k] = md.qpos[iq["base_z"]]     # ModeA 점프높이 판정 (사용자 요청 08-02)
    return Lg


def golden_g5():
    """G5 등가성: 온건역(27일 150 trial) CL — fs(k150) vs 변형 C 기록치 vs 실측."""
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    d = FD.load2(FD.SESS_FIT["26.07.27"] / "150_2.2_250_3")
    seg = FD.segment(d)
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    g = (150.0, 2.2, 250.0 * TK[250], 3.0 * 0.20)
    i0 = max(0, seg["i_desc"] - 5)
    t = d["t"][i0:] - d["t"][i0]
    t_end = seg["t_lo"] - d["t"][i0]
    L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:], g, t_end)
    if L is None:
        print("G5: 발산!")
        return False
    m = seg["score"][i0:][: len(t)]
    gi = lambda k: np.interp(t, L["t"], L[k])
    r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                    gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
    print(f"G5 fs(k150) 전구간: q1 {r[0]:.2f}° q2 {r[1]:.2f}° dq1 {r[2]:.2f} dq2 {r[3]:.2f} τ1 {r[4]:.2f} τ2 {r[5]:.2f}")
    print("   변형 C 기록치     : q1 0.87° q2 0.81° dq1 0.22 dq2 0.25 τ1 1.19 τ2 0.63 (베이스라인 JSON)")
    ok = r[0] < 1.5 and r[4] < 2.5
    print("G5", "근접" if ok else "괴리 — 진단 필요")
    return ok





def baseline_fs():
    """fs(k150) CL 전 trial 채점 — 비CVT fit 세션 (베이스라인 대조용)."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            _tko = os.environ.get("FS_TKOVR"); _kds = os.environ.get("FS_KDSC")
            gm = (g[0], g[1], g[2] * (float(_tko) if _tko else TK.get(g[2], 0.656)),
                  g[3] * (float(_kds) if _kds else 0.20))
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0])
            if L is None:
                print(f"{s}/{p.name}: 발산", flush=True)
                continue
            m = seg["score"][i0:][: len(t)]
            gi = lambda k: np.interp(t, L["t"], L[k])
            r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                            gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
            OUT.setdefault(s, []).append(list(r))
            print(f"{s}/{p.name}: q1 {r[0]:.2f} q2 {r[1]:.2f} dq1 {r[2]:.2f} dq2 {r[3]:.2f} τ1 {r[4]:.2f} τ2 {r[5]:.2f}", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    json.dump(OUT, open(HERE / "_fs_baseline_fsmodel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs(k150) 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")





def baseline_fs2():
    """fs 2단+세션 바이어스 (캘리브: 하강·복귀 정적 감사 → (r1d+r1u)/2, 채점 창 밖 = 무누수)."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    BIAS = {}
    for s in down:
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        if s in up and up[s]:
            r1u = np.mean([v["r1_up"] for v in up[s].values()])
            BIAS[s] = float((r1d + r1u) / 2)
        else:
            BIAS[s] = float(r1d)
    print("세션 바이어스:", {k: round(v, 2) for k, v in BIAS.items()})
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            _tko = os.environ.get("FS_TKOVR"); _kds = os.environ.get("FS_KDSC")
            gm = (g[0], g[1], g[2] * (float(_tko) if _tko else TK.get(g[2], 0.656)),
                  g[3] * (float(_kds) if _kds else 0.20))
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True, bias1=BIAS.get(s, 0.0))
            if L is None:
                print(f"{s}/{p.name}: 발산", flush=True)
                continue
            m = seg["score"][i0:][: len(t)]
            gi = lambda k: np.interp(t, L["t"], L[k])
            r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                            gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
            OUT.setdefault(s, []).append(list(r))
            print(f"{s}/{p.name}: q1 {r[0]:.2f} q2 {r[1]:.2f} dq1 {r[2]:.2f} dq2 {r[3]:.2f} τ1 {r[4]:.2f} τ2 {r[5]:.2f}", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    json.dump(OUT, open(HERE / "_fs_baseline_fs2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs2(2단+세션바이어스) 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")





def modea_fs():
    """ModeA mshoot fs판 (0.4s 창·측정상태 리셋) — 양방향 심판의 나머지 절반. 세션 바이어스 동일 주입."""
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    BIAS = {}
    for s in down:
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        BIAS[s] = float((r1d + r1u) / 2)
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]
        rows = []
        w0 = seg["t_desc"]
        while w0 + 0.05 < seg["t_lo"]:
            wl = min(0.4, seg["t_lo"] - w0)
            m = (t >= w0) & (t <= w0 + wl)
            if m.sum() < 20:
                w0 += 0.3
                continue
            i0 = int(np.argmax(m))
            tg = t[m] - w0
            L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=BIAS.get(s, 0.0))
            if L is None:
                w0 += 0.3
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            mm = tg >= 0.02
            r = FMET._rmse6({k: d[k][m] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, mm,
                            gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2"))
            rows.append(r)
            w0 += 0.3
        if rows:
            a = np.mean(rows, axis=0)
            OUT.setdefault(s, []).append(list(a))
            print(f"{s}/{p.name}: MA q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f}", flush=True)
    json.dump(OUT, open(HERE / "_fs_modea_fs2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs2 ModeA 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")


def rollout_ol_fs_b(ft, tg, raw1g, raw2g, q1_0, q2_0, dq1_0, dq2_0, t_end, t_after=0.004, bias1=0.0, knee_deep=None, fade=False, bz_floor=None, knee_rel=None):
    """rollout_ol_fs + 2단·바이어스 qfrc (mshoot용 래퍼 — 별도 구현 유지로 원본 무변경)."""
    _ramp = _bias_ramp()
    model = ft["model"]; P = ft["P"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = ft["law"]; kr = ft["kr"]; sprm = ft["sprm"]
    _nospr = os.environ.get("FS_NOSPR") == "1"   # 마라톤G: 부하연동 무릎 스프링(|s2| 비례) 절제
    iq, dof = ft["iq"], ft["dof"]
    A = P.A_PAPER
    md = mjm.MjData(model)
    r1_0 = float(np.interp(0.0, tg, raw1g))
    s1_0 = float(P.J.ahat(A, np.array([np.clip(r1_0, -TW.R19.CLIP, TW.R19.CLIP)]), np.array([float(dq1_0)]))[0])
    defl0 = np.clip(np.sign(s1_0) * (abs(s1_0) / 96.0 if abs(s1_0) <= 9 else 9 / 96.0 + (abs(s1_0) - 9) / 323.0), -0.3, 0.3)
    # 마라톤D P12 (사용자 적발 08-01): 실측 q1 = **모터측 인코더** → sim 모터각(thm1)을 실측에 앵커해야 한다.
    # 구현 오류였던 구식: hip_m에서 defl0을 빼 링크각을 실측에 맞춤 → thm1이 처짐만큼 어긋난 채 출발
    # (0602 −1.02° 등, F15 계보 '실측=모터측' 규약 위반). FS_MA_INIT=link 로 구식 재현 가능.
    _lnk = os.environ.get("FS_MA_INIT") == "link"
    # 마라톤G 08-02: F3(F-H10) 폐쇄 초기화 픽스가 **CL에만** 들어가 있었다 — 개루프(ModeA)는
    # CVT(l_i≠30)에서도 평행사변형 관례로 출발해 4-bar 루프 모순 → 솔버 스냅 → 발산
    # (U-보드 MA 0429: q2 494°·dq2 136). rollout_cl_fs(init_meas) 경로와 동일하게 미러한다.
    _ci0 = ft.get("cvt_init")
    if _ci0 is not None:
        _qc5 = np.asarray(_ci0(q1_0, q2_0), float)     # 5q [bz, hip_m, crank, cpin, knee]
        md.qpos[iq["base_z"]] = _qc5[0]
        md.qpos[iq["hip_m"]] = _qc5[1]
        md.qpos[iq["hip"]] = defl0
        md.qpos[iq["knee_motor"]] = _qc5[2]
        md.qpos[iq["cpin"]] = _qc5[3]
        md.qpos[iq["knee"]] = _qc5[4]
    else:
        md.qpos[iq["hip_m"]] = -q1_0 - np.pi / 2 - (defl0 if _lnk else 0.0)
        md.qpos[iq["hip"]] = defl0
        md.qpos[iq["knee_motor"]] = -q2_0
        md.qpos[iq["cpin"]] = q2_0
        md.qpos[iq["knee"]] = -q2_0
        md.qpos[iq["base_z"]] = 1.0
    mjm.mj_forward(model, md)
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[iq["base_z"]] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    if bz_floor is not None:
        md.qpos[iq["base_z"]] = max(float(md.qpos[iq["base_z"]]), bz_floor)   # 엔드스톱 위 초기화 (착좌)
    Lseg = 0.25
    c1_, c12 = np.cos(q1_0), np.cos(q1_0 + q2_0)
    dbz = -Lseg * (c1_ * dq1_0 + c12 * (dq1_0 + dq2_0))
    md.qvel[:] = 0
    md.qvel[dof["base_z"]] = dbz
    md.qvel[dof["hip_m"]] = -dq1_0
    if _ci0 is not None:
        # 폐쇄 정합 속도: d(qpos)/d(q2) 수치미분 × dq2 (전달비 r(q) 자동 반영) — CL 경로와 동일
        _eps = 1e-5
        _dr5 = (np.asarray(_ci0(q1_0, q2_0 + _eps), float) - _qc5) / _eps
        for _j, _n in ((2, "knee_motor"), (3, "cpin"), (4, "knee")):
            md.qvel[dof[_n]] = _dr5[_j] * dq2_0
    else:
        md.qvel[dof["knee_motor"]] = -dq2_0
        md.qvel[dof["cpin"]] = dq2_0
        md.qvel[dof["knee"]] = -dq2_0
    mjm.mj_forward(model, md)
    dt = model.opt.timestep
    N = int(round((t_end + t_after) / dt))
    # 마라톤G G13: 발 접촉 진단용 로깅 (xf=발 geom x, thf=발 바디 각) — **동역학 무변경**.
    # 슬립 = Δxf − r·Δthf (구름 성분 차감). 기하 요구량(_G12_slipgeo)과 같은 정의로 맞춘다.
    keys = ("t", "thm1", "q1", "q2", "dq1", "dq2", "s1", "s2", "bz", "xf", "thf")
    Lg = {k: np.zeros(N) for k in keys}
    _gfoot = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    _bfoot = int(model.geom_bodyid[_gfoot]) if _gfoot >= 0 else 0
    load_on = os.environ.get("FS_KNEE_LOAD") == "1" and knee_deep
    if load_on:
        _Nmg = float(model.body_mass.sum() * 9.81)
        _cf = np.zeros(6)
    _rail = float(os.environ.get("FS_RAIL", "0") or 0)      # P6 레일 마찰 (CL과 동일 플랜트)
    if _rail > 0:
        _cfR = np.zeros(6)
    _rxv = os.environ.get("FS_RAILX")
    _rxkb = tuple(float(v) for v in _rxv.split(",")) if (_rxv and "base_x" in dof) else None
    _w2 = float(os.environ.get("FS_W2", "0") or 0)
    _eta = float(os.environ.get("FS_ETA", "1") or 1)   # P7 고속 제곱 소산 (버스트 전용)
    _psl = _PreSlide(model, fg) if os.environ.get("FS_PRESLIDE") else None
    _esc = _escrow_init()                  # 마라톤F F1: CL과 동일 플랜트 (에너지 회계)
    _est = float(os.environ.get("FS_ESC_STORE", "1") or 1)   # F1b 동일
    _svg = os.environ.get("FS_SUPP_VG") or None              # F-H8 동일
    _vcl = _vceil_init()                   # F-H7 동일 플랜트
    _tmap = _tmap_init(P, A); _nosupp = _nosupp_init()   # 마라톤G A 동일 플랜트
    for k in range(N):
        tc = k * dt
        v1c = -md.qvel[dof["hip_m"]]
        v2c = -md.qvel[dof["knee_motor"]]
        r1 = float(np.interp(tc, tg, raw1g)) if tc <= t_end else 0.0
        r2 = float(np.interp(tc, tg, raw2g)) if tc <= t_end else 0.0
        r1 = float(np.clip(r1, -TW.R19.CLIP, TW.R19.CLIP))
        r2 = float(np.clip(r2, -TW.R19.CLIP, TW.R19.CLIP))
        if _tmap is None:
            s1 = float(P.J.ahat(A, np.array([r1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([r2]), np.array([v2c]))[0])
        else:                              # 마라톤G A: G5 정본곡선 + 상태의존 전달률
            s1 = _tmap(r1, v1c, 0)
            s2 = _tmap(r2, v2c, 1)
        if _vcl is not None:               # F-H7: 실측 τ는 이미 실기 천장 반영 — 정확하면 무작동
            s1 = _vceil_cap(s1, v1c, _vcl)
            s2 = _vceil_cap(s2, v2c, _vcl)
        supp = 0.0 if _nosupp else RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr and not _nosupp:
            supp += _rise(v2c, kr, law_v0)
        if _svg is not None:
            supp *= _svg_gate(v2c, _svg)   # F-H8 동일 플랜트
        if _esc is not None and "supp2" in _esc:
            if _est > 1.0 and supp * v2c < 0.0:
                supp *= _est               # F1b 동일 플랜트
            _esc["supp2"], supp = _escrow_gate(_esc["supp2"], supp, v2c, dt)
        tql = 0.0 if _nospr else (RU.spr_tau(float(md.qpos[iq["knee"]]), abs(s2), sprm)
                                  if sprm is not None else 0.0)
        if _esc is not None and "spr" in _esc:
            _esc["spr"], tql = _escrow_gate(_esc["spr"], tql, float(md.qvel[dof["knee"]]), dt)
        if _eta < 1.0:
            s1 = s1 * (_eta if s1 * v1c > 0 else 1.0)
            s2 = s2 * (_eta if s2 * v2c > 0 else 1.0)
        _hsupp = 0.0 if _nosupp else RU.hip_supp_scalar(s1, s2, v1c)
        if _esc is not None and "hsupp1" in _esc:
            _esc["hsupp1"], _hsupp = _escrow_gate(_esc["hsupp1"], _hsupp, v1c, dt)
        md.ctrl[:] = [-(s1 + _hsupp), -(s2 + supp)]
        md.qfrc_applied[dof["knee"]] = tql
        dq_s = float(md.qpos[iq["hip"]])
        b_base = bias1
        if _ramp is not None:
            b_base = bias1 + _ramp[0] * max(0.0, _ramp[1] - np.degrees(-float(md.qpos[iq["knee_motor"]])))
        b_eff = b_base
        if fade and abs(v1c) > 1.0:
            b_eff = b_base * max(0.0, 1.0 - (abs(v1c) - 1.0) / 2.0)   # 저속 전용 (마찰성 가설)
        md.qfrc_applied[dof["hip"]] = (FM.KS_HIP * dq_s - _tau2s(dq_s)) + b_eff
        if knee_deep:
            kd_, q20_ = knee_deep
            q2r = -float(md.qpos[iq["knee_motor"]])
            tau_ext = kd_ * max(0.0, q20_ - q2r)     # 로봇 좌표 신전(+) 방향 받침
            _rel = knee_rel if knee_rel is not None else (float(os.environ["FS_KNEE_REL"]) if "FS_KNEE_REL" in os.environ else None)
            if _rel is not None:
                if v2c > 0.2:
                    tau_ext *= _rel                                   # 방출 분율 (부분 소산 모델)
            elif fade and v2c > 1.0:
                tau_ext *= max(0.0, 1.0 - (v2c - 1.0) / 2.0)         # 고속 신전 시 소산 (방출 무반환)
            if load_on:
                Nf = 0.0
                for ci in range(md.ncon):
                    _c = md.contact[ci]
                    if _c.geom1 == fg or _c.geom2 == fg:
                        mjm.mj_contactForce(model, md, ci, _cf)
                        Nf += abs(float(_cf[0]))
                tau_ext *= min(Nf / _Nmg, 3.0)
            md.qfrc_applied[dof["knee_motor"]] = -tau_ext
        if _rail > 0:
            if _rxkb is not None:
                _Fx = _rxkb[0] * float(md.qpos[dof["base_x"]]) + _rxkb[1] * float(md.qvel[dof["base_x"]])
                _skip_contact = True
            else:
                _skip_contact = False
            _Fx = _Fx if _rxkb is not None else 0.0
            for ci in range(0 if _rxkb is not None else md.ncon):
                _c = md.contact[ci]
                if _c.geom1 == fg or _c.geom2 == fg:
                    mjm.mj_contactForce(model, md, ci, _cfR)
                    _Fx += float((np.array(_c.frame).reshape(3, 3).T @ _cfR[:3])[0])
            _vbz = float(md.qvel[dof["base_z"]])
            _g = np.tanh(max(_vbz, 0.0) / 0.05) if os.environ.get("FS_RAIL_UP") == "1" else np.tanh(_vbz / 0.05)
            md.qfrc_applied[dof["base_z"]] = -_rail * abs(_Fx) * float(_g)
        if _w2 > 0:
            _v2m = float(md.qvel[dof["knee_motor"]])
            md.qfrc_applied[dof["knee_motor"]] = md.qfrc_applied[dof["knee_motor"]] - _w2 * _v2m * abs(_v2m)
            _v1m = float(md.qvel[dof["hip_m"]])
            md.qfrc_applied[dof["hip_m"]] = -_w2 * _v1m * abs(_v1m)   # 순할당 (hip_m 유일 기록자)
        _dc = os.environ.get("FS_DEEP_DMPCUT")
        _fcut = os.environ.get("FS_DEEP_FLCUT")
        if _dc is not None or _fcut is not None:
            q2r_ = -float(md.qpos[iq["knee_motor"]])
            _th = float(os.environ.get("FS_DEEP_TH", "-120.0"))
            gg = 1.0 / (1.0 + np.exp((q2r_ - np.radians(_th)) / np.radians(4.0)))
            v_hm = float(md.qvel[dof["hip_m"]])
            _q = (float(_dc) * gg * v_hm) if _dc is not None else 0.0
            if _fcut is not None:
                _q += float(_fcut) * gg * float(np.tanh(v_hm / 0.05))
            md.qfrc_applied[dof["hip_m"]] = _q
        mjm.mj_step(model, md)
        if not np.isfinite(md.qpos).all():
            if _psl is not None:
                _psl.restore()
            return None
        if _psl is not None:
            _psl.step(md, dt)
        Lg["t"][k] = tc
        Lg["thm1"][k] = -md.qpos[iq["hip_m"]] - np.pi / 2
        Lg["q1"][k] = -(md.qpos[iq["hip_m"]] + md.qpos[iq["hip"]]) - np.pi / 2
        Lg["q2"][k] = -md.qpos[iq["knee_motor"]]
        Lg["dq1"][k] = -md.qvel[dof["hip_m"]]
        Lg["dq2"][k] = -md.qvel[dof["knee_motor"]]
        Lg["s1"][k] = s1
        Lg["s2"][k] = s2
        Lg["bz"][k] = md.qpos[iq["base_z"]]     # ModeA 점프높이 판정 (사용자 요청 08-02)
        Lg["xf"][k] = md.geom_xpos[_gfoot][0]   # G13 발 접촉 진단 (동역학 무관)
        Lg["thf"][k] = np.arctan2(md.xmat[_bfoot][2], md.xmat[_bfoot][0])
    if _psl is not None:
        _psl.restore()
    return Lg

def fit_knee_deep():
    """세션별 (q2_0, k_d) 적합 — 하강 창(깊은 부분)만 사용 (규칙 4). HO 0324 포함(자체 캘리브 관찰용)."""
    import json
    import fs_data as FD
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    def bias_of(s):
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]])
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        return float((r1d + r1u) / 2)
    ft = fs_twin()
    FIT = {}
    for s, base in FD.SESS_FIT.items():
        if s in FD.CVT_SESS:
            continue
        trials = FD.trials_of(base)[:2]     # 세션당 2 trial로 적합 (속도)
        b = bias_of(s) if s in down else 0.0
        def deep_err(knee_deep):
            errs = []
            for p in trials:
                d = FD.load2(p); seg = FD.segment(d); t = d["t"]
                w0 = seg["t_desc"]
                while w0 + 0.05 < seg["t_lo"]:
                    wl = min(0.4, seg["t_lo"] - w0)
                    m = (t >= w0) & (t <= w0 + wl)
                    if m.sum() < 20:
                        w0 += 0.3
                        continue
                    if np.degrees(np.mean(d["q2"][m])) > -125:
                        w0 += 0.3
                        continue
                    i0 = int(np.argmax(m)); tg = t[m] - w0
                    L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                        float(d["q1"][i0]), float(d["q2"][i0]),
                                        float(d["dq1"][i0]), float(d["dq2"][i0]),
                                        float(tg[-1] - 0.004), bias1=b, knee_deep=knee_deep)
                    if L is not None:
                        mm = tg >= 0.02
                        q2s = np.interp(tg, L["t"], L[k]) if (k := "q2") else None
                        errs.append(np.degrees(np.sqrt(np.mean((d["q2"][m][mm] - q2s[mm]) ** 2))))
                    w0 += 0.3
            return float(np.mean(errs)) if errs else None
        e0 = deep_err(None)
        if e0 is None:
            print(f"{s}: 깊은 창 없음 — 요소 불필요", flush=True)
            FIT[s] = None
            continue
        best = (e0, None)
        for q20 in (-2.20, -2.27, -2.36, -2.44):
            for kd in (2.5, 5.0, 10.0, 20.0):
                e = deep_err((kd, q20))
                if e is not None and e < best[0]:
                    best = (e, (kd, q20))
        FIT[s] = dict(err0=round(e0, 2), err=round(best[0], 2),
                      kd=best[1][0] if best[1] else 0.0,
                      q20_deg=round(float(np.degrees(best[1][1])), 1) if best[1] else None)
        print(f"{s}: {e0:.2f}° → {best[0]:.2f}° (k_d {FIT[s]['kd']}, 결합 {FIT[s]['q20_deg']}°)", flush=True)
    import json as _j
    safe.atomic_json_write(HERE / "_fs_knee_deep.json", FIT)
    print("done")
def _sess_params():
    import fs_data as FD
    if os.environ.get("FS_FIXED") == "1":
        # F52 고정 파라미터 노선 (bias 0.85 · k_d 5@-128 전 세션 — 26.04.29 포함)
        class _P:
            def get(self, s, d=None):
                return dict(bias1=0.85, knee_deep=(5.0, float(np.radians(-128.0))))
            def __contains__(self, s):
                return True
            def __getitem__(self, s):
                return self.get(s)
        return _P()
    down = safe.read_json(HERE / "_fs_static_audit.json")
    up = safe.read_json(HERE / "_fs_updown.json")
    kd = safe.read_json(HERE / "_fs_knee_deep.json")
    P = {}
    for s in list(down.keys()) + ["26.07.25"]:
        if s in P:
            continue
        r1d = np.mean([r["a1"] - r["s1"] for tr in down[s].values() for r in tr["rows"] if r["ok"]]) if s in down else 0.0
        r1u = np.mean([v["r1_up"] for v in up[s].values()]) if s in up and up[s] else r1d
        b = float((r1d + r1u) / 2)
        k = kd.get(s)
        knee = (float(k["kd"]), float(np.radians(k["q20_deg"]))) if (k and k.get("kd")) else None
        P[s] = dict(bias1=b, knee_deep=knee)
    # 0429 CVT: fs_calib_cvt 감사 (복귀 표본 없음 → 하강 단독; 크랭크 잔차 +0.08≈0라 knee_deep 없음)
    cvt_p = HERE / "_fs_cvt_audit.json"
    if cvt_p.exists():
        cv = safe.read_json(cvt_p)
        rr = [r["a1"] - r["s1"] for tr in cv.values() for r in tr["down"] if r["ok"]]
        if rr:
            P["26.04.29"] = dict(bias1=float(np.mean(rr)), knee_deep=None)
    return P


def baseline_fs3():
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        tl_ = None
        _tlm = os.environ.get("FS_TAULIM")
        try:
            _obs_fixed = float(_tlm) if _tlm not in (None, "1", "2", "3") else None
        except ValueError:
            _obs_fixed = None
        if _tlm == "1":
            _tj = HERE / "_fs_taulim.json"
            if _tj.exists():
                _te = safe.read_json(_tj).get(s)
                tl_ = float(_te["lim"]) if (_te and _te.get("active")) else None
        elif _tlm in ("2", "3"):              # F26 재공략: trial 입자도 (진단 — 판독원=푸시 창)
            _tj = HERE / "_fs_taulim_trial.json"
            if _tj.exists():
                _te = safe.read_json(_tj).get(f"{s}/{p.name}")
                tl_ = float(_te["lim"]) if (_te and _te.get("active")) else None
        obs_lim = tl_ if _tlm == "3" else None
        if _tlm == "3":
            tl_ = None                        # 3 = 관측 전용 클립 (동역학 무손 — F30 트레이드오프 해소 시도)
        if _obs_fixed is not None:
            obs_lim = _obs_fixed              # 수치형 = 단일 축토크 관측 클립 (F54: raw 35.5 환산 ~20.5)
            tl_ = None
        try:
            d = FD.load2(p); seg = FD.segment(d)
            _tko = os.environ.get("FS_TKOVR"); _kds = os.environ.get("FS_KDSC")
            gm = (g[0], g[1], g[2] * (float(_tko) if _tko else TK.get(g[2], 0.656)),
                  g[3] * (float(_kds) if _kds else 0.20))
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            _lr = None
            if os.environ.get("FS_LIMRAW") == "1":
                _lj = HERE / "_fs_lim.json"
                if _lj.exists():
                    _le = safe.read_json(_lj).get(s)
                    if _le:
                        # 판독 천장이 모터 최대(35.5) 미만일 때만 유효 설정으로 간주
                        _l1 = _le.get("r1"); _l2 = _le.get("r2")
                        _lr = (_l1 if (_l1 and _l1 < 34.0) else None,
                               _l2 if (_l2 and _l2 < 34.0) else None)
                        if _lr == (None, None):
                            _lr = None
            _l2n = None
            if os.environ.get("FS_LIM2NM") == "1":
                _nj = HERE / "_fs_lim_nm.json"
                if _nj.exists():
                    _ne = safe.read_json(_nj).get(s)
                    if _ne and _ne.get("lim2_nm") and _ne["lim2_nm"] < 19.0:
                        _l2n = float(_ne["lim2_nm"])
            _vff = s not in os.environ.get("FS_VDES0", "").split(",")
            _qsn = int(os.environ.get("FS_QDSHIFT", "0") or 0)
            def _sh(x, _n=_qsn):
                # P18: qd 채널 로깅 스큐 보정 (qd가 q/raw보다 _n샘플 선행 기록 — δ4ms=2샘플 판독)
                if _n <= 0:
                    return x
                y = np.empty_like(x); y[_n:] = x[:-_n]; y[:_n] = x[0]
                return y
            L = rollout_cl_fs(ft, t, _sh(d["qd1"][i0:]), _sh(d["qd2"][i0:]), _sh(d["dqd1"][i0:]), _sh(d["dqd2"][i0:]),
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                              fade=os.environ.get("FS_FADE") == "1", taulim=tl_, lim_raw=_lr, lim2_nm=_l2n,
                              vdes_ff=_vff)
            if L is None:
                continue
            gi = lambda k: np.interp(t, L["t"], L[k])
            for wn in ("score", "push"):
                m = seg[wn][i0:][: len(t)]
                _to = os.environ.get("FS_TAUOBS")
                if _to == "sess":
                    _wj = HERE / "_fs_tauobs_w.json"
                    _w = float(safe.read_json(_wj).get(s, 0.5)) if _wj.exists() else 0.5
                    t1obs = _w * gi("s1f") + (1 - _w) * gi("tsp1")
                else:
                    t1obs = (gi("tsp1") if _to == "spr" else
                             gi("s1f") if _to == "lpf" else
                             0.5 * gi("s1f") + 0.5 * gi("tsp1") if _to == "blend" else gi("s1"))
                if obs_lim is not None:
                    t1obs = np.clip(t1obs, -obs_lim, obs_lim)
                r = FMET._rmse6({k: d[k][i0:] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, m,
                                gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), t1obs, gi("s2"))
                OUT.setdefault(s, {}).setdefault(wn, []).append(list(r))
            print(f"{s}/{p.name}: OK", flush=True)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    json.dump(OUT, open(HERE / "_fs3_cl.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for wn in ("score", "push"):
        print(f"\n=== fs3 CL {wn} 창 세션 요약 ===")
        for s, d_ in OUT.items():
            a = np.mean(d_[wn], axis=0)
            print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")


def modea_fs3():
    import json
    import fs_data as FD
    import fs_metric as FMET
    ft = fs_twin()
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]
        rows = []
        w0 = seg["t_desc"]
        while w0 + 0.05 < seg["t_lo"]:
            wl = min(0.4, seg["t_lo"] - w0)
            m = (t >= w0) & (t <= w0 + wl)
            if m.sum() < 20:
                w0 += 0.3
                continue
            i0 = int(np.argmax(m)); tg = t[m] - w0
            L = rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                float(d["q1"][i0]), float(d["q2"][i0]),
                                float(d["dq1"][i0]), float(d["dq2"][i0]),
                                float(tg[-1] - 0.004), bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                                fade=os.environ.get("FS_FADE") == "1")
            if L is None:
                w0 += 0.3
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            mm = tg >= 0.02
            rows.append(FMET._rmse6({k: d[k][m] for k in ("q1", "q2", "dq1", "dq2", "a1", "a2")}, mm,
                                    gi("thm1"), gi("q2"), gi("dq1"), gi("dq2"), gi("s1"), gi("s2")))
            w0 += 0.3
        if rows:
            OUT.setdefault(s, []).append(list(np.mean(rows, axis=0)))
            print(f"{s}/{p.name}: OK", flush=True)
    json.dump(OUT, open(HERE / "_fs3_ma.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n=== fs3 ModeA 세션 요약 ===")
    for s, rows in OUT.items():
        a = np.mean(rows, axis=0)
        print(f"{s}: q1 {a[0]:.2f} q2 {a[1]:.2f} dq1 {a[2]:.2f} dq2 {a[3]:.2f} τ1 {a[4]:.2f} τ2 {a[5]:.2f}")
    print("done")

def tauobs_compare():
    """τ1 관측 4안 동시 채점 (푸시 창) — 한 패스: s1 / lpf10(s1f) / 스프링측(tsp1) / 블렌드 0.5."""
    import fs_data as FD
    ft = fs_twin()
    TKK = np.array([60, 120, 250, 500]); TKV = np.array([0.85, 0.789, 0.656, 0.40])
    SP = _sess_params()
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g or s == "26.04.21":
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * float(np.interp(g[2], TKK, TKV)) if False else g[2] * {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}.get(g[2], 0.656), g[3] * 0.20)
            gm = (g[0], g[1], gm[2], gm[3])
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            m = seg["push"][i0:][: len(t)]
            a1 = d["a1"][i0:][: len(t)]
            res = {}
            for nm, key in (("s1", "s1"), ("lpf", "s1f"), ("spr", "tsp1")):
                o = np.interp(t, L["t"], L[key])
                res[nm] = float(np.sqrt(np.mean((a1[m] - o[m]) ** 2)))
            ob = 0.5 * np.interp(t, L["t"], L["s1f"]) + 0.5 * np.interp(t, L["t"], L["tsp1"])
            res["blend"] = float(np.sqrt(np.mean((a1[m] - ob[m]) ** 2)))
            # 게인 인식 (trial 입자도): 전류루프 지연 관점 — 저게인(60)=스프링측, 고게인(120+)=lpf10
            w = float(np.clip((g[0] - 60.0) / 60.0, 0.0, 1.0))
            og = w * np.interp(t, L["t"], L["s1f"]) + (1 - w) * np.interp(t, L["t"], L["tsp1"])
            res["gain"] = float(np.sqrt(np.mean((a1[m] - og[m]) ** 2)))
            OUT.setdefault(s, []).append(res)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print("\n=== 푸시 τ1 관측 5안 (세션 평균) ===")
    tot = {k: [] for k in ("s1", "lpf", "spr", "blend", "gain")}
    for s, rows in OUT.items():
        a = {k: float(np.mean([r[k] for r in rows])) for k in tot}
        for k in tot:
            tot[k].append(a[k])
        print(f"{s}: s1 {a['s1']:.2f} | lpf10 {a['lpf']:.2f} | spr {a['spr']:.2f} | blend {a['blend']:.2f} | gain {a['gain']:.2f}")
    print("전체 평균: " + " | ".join(f"{k} {np.mean(v):.2f}" for k, v in tot.items()))
    print("done")


def tauobs_desc():
    """관측 블렌드 w의 세션 상수화 판별: 하강 창에서 w* 캘리브 → 푸시 제로샷 평가.
    w=0(스프링측)~1(lpf10) 11단계. 누수 없음 (w 선정에 푸시 창 미사용). 오라클 병기."""
    import fs_data as FD
    ft = fs_twin()
    SP = _sess_params()
    W = np.linspace(0, 1, 11)
    ACC = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt or ho or not g or s == "26.04.21":
            continue
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        try:
            d = FD.load2(p); seg = FD.segment(d)
            gm = (g[0], g[1], g[2] * {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}.get(g[2], 0.656), g[3] * 0.20)
            i0 = max(0, seg["i_desc"] - 5)
            t = d["t"][i0:] - d["t"][i0]
            L = rollout_cl_fs(ft, t, d["qd1"][i0:], d["qd2"][i0:], d["dqd1"][i0:], d["dqd2"][i0:],
                              gm, seg["t_lo"] - d["t"][i0], two_stage=True,
                              bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            a1 = d["a1"][i0:][: len(t)]
            lp = np.interp(t, L["t"], L["s1f"]); tp = np.interp(t, L["t"], L["tsp1"])
            row = {}
            for wn in ("desc", "push"):
                m = seg[wn][i0:][: len(t)]
                row[wn] = [float(np.sqrt(np.mean((a1[m] - (w * lp + (1 - w) * tp)[m]) ** 2))) for w in W]
            ACC.setdefault(s, []).append(row)
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__}", flush=True)
    print("\n=== 관측 w 세션 상수화: 하강 캘리브 → 푸시 제로샷 (τ1 RMSE) ===")
    zs, bl, orc, WS = [], [], [], {}
    for s, rows in ACC.items():
        dmean = np.mean([r["desc"] for r in rows], axis=0)
        pmean = np.mean([r["push"] for r in rows], axis=0)
        iw = int(np.argmin(dmean)); io = int(np.argmin(pmean))
        zs.append(pmean[iw]); bl.append(pmean[5]); orc.append(pmean[io])
        WS[s] = float(W[iw])
        print(f"{s}: w*_desc={W[iw]:.1f} → 푸시 {pmean[iw]:.2f} | blend0.5 {pmean[5]:.2f} | "
              f"오라클 w={W[io]:.1f} {pmean[io]:.2f}", flush=True)
    print(f"전체: 제로샷 {np.mean(zs):.2f} | blend0.5 {np.mean(bl):.2f} | 오라클 {np.mean(orc):.2f}")
    safe.atomic_json_write(HERE / "_fs_tauobs_w.json", WS)
    print("done → _fs_tauobs_w.json")

if __name__ == "__main__":
    import sys as _s
    a = _s.argv[1] if len(_s.argv) > 1 else ""
    if a == "baseline":
        golden_g5(); baseline_fs()
    elif a == "baseline2":
        baseline_fs2()
    elif a == "modea":
        modea_fs()
    elif a == "kneedeep":
        fit_knee_deep()
    elif a == "tauobs":
        tauobs_compare()
    elif a == "tauobs2":
        tauobs_desc()
    elif a == "fs3":
        baseline_fs3(); modea_fs3()
    else:
        golden_g5()
