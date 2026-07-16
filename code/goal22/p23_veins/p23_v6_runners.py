# -*- coding: utf-8 -*-
"""p23_v6_runners — P23 Phase 4 재적합 러너층: 측정 유지-지지 법칙이 pre30+준정적층을 세대 교체.

═══ v23 벡터 (22축) — p21_cma 20-vec에서 3슬롯 재정의 + 2슬롯 확장 ═══
  idx name      init            bounds             비고
   0  stiff     P19 (0.6156)    [0.0, 2.5]         노출
   1  ref       P19 (1.6475)    [1.5, 2.7]         노출
   2  fv_hip    P19 (0.6943)    [0.05, 2.50]       노출 (Phase 1 '저속 fv≈0'은 dq≤2.7 한정 —
                                                   고속 대리 흡수항 가능성, 외삽 삭감 금지)
   3  fc_hip    P19 (0.0783)    [0.0, 0.30]        노출
   4  fv_knee   P19 (0.0690)    [0.0, 0.15]        노출
   5  fc_knee   P19 (0.0011)    [0.0, 0.25]        노출
   6  solref    P19 (0.0102)    [0.002, 0.030]     노출
   7  imp0      P19 (0.4906)    [0.05, 0.70]       노출
   8  arm_knee  P19 (0.0072)    [0.0005, 0.020]    노출 (Phase 3 ddq→유효관성 축)
   9  M_c       P19 (0.6661)    — 동결 —           Phase 1 calf 케이지 측정-건강
  10  I_th      P19 (0.7572)    [0.55, 1.45]       노출 (Phase 1 thigh 레버 3.3× 과대 축)
  11  I_ca      P19 (1.3937)    — 동결 —
  12  dz_th     P19 (0.0659)    [-0.12, 0.12]      노출. ★기존 하한 -0.12가 이미 -0.02보다
                                                   넓음 → 하한 변경 불필요 (측정 방향 수용됨)
  13  dz_ca     P19 (0.0496)    — 동결 —
  14  tm        P19 (0.00031)   [0.0, 0.020]       노출
  15  LAW_A     -1.22123        [-2.0, 0.0]        (구 c_qs 슬롯) 법칙 절편 — 측정 -1.221±0.198
  16  LAW_V0    5.79954         [4.3, 7.3]         (구 v0 슬롯) 게이트 속도 — 측정 5.80±1.00,
                                                   HARD = 95% CI×1.5
  17  o1_429    P19 (0.0894)    [-0.15, 0.15]      노출
  18  o2_429    P19 (-0.0474)   [-0.15, 0.15]      노출
  19  LAW_B     0.75851         [0.63, 0.89]       (구 pre30 슬롯) 부하 계수 — HARD = 측정
                                                   95% CI×1.5 (0.759±0.088×1.5)
  20  C_CVT     0.0             [0.0, 0.4]         확장: CVT 가지 전달손실 (p22_exp_cvtloss
                                                   coulomb형) — 이월 축 #33 공동적합
  21  D_DQ      0.0             [-0.25, 0.10]      확장: 무릎 점성 보정 (dof_damping 가산).
                                                   ★음수 = 고속 소산 삭감 = 에너지 주입 위험
                                                   (P21 교훈) — H/OLdq_FF/AIR 게이트가 단속.
  LAW_C = -0.0281448 (측정 고정 — 푸시 레짐 불확실, 탐색 금지. p23_law_fit.json gate.c)

═══ 지지 법칙 (Phase 2 측정 확정 — p23_law_fit.json 'hold_gate.gate') ═══
  supp(τ̂₂, dq₂) = LAW_A + min(LAW_B·x + LAW_C·x², 3.5)·g(dq₂; LAW_V0)
  x = min(|τ̂₂|, x_pk),  x_pk = LAW_B/(2|LAW_C|),  g(v;v0) = 1/(1+(v/v0)²)  (p20_run.gate 동형)
  ※ 정직 노트: 과제 문언의 min(b|τ̂|+cτ̂², 3.5)만으로는 |τ̂|>~21 외삽에서 포물선이 재하강해
    음수로 폭주 → x를 포물선 정점에서 클램프해 '캡 3.5 근방 유지'의 단조 구현으로 확정.
    (측정 적합 범위 |τ̂|≲9 안에서는 문언과 완전 동일.)

═══ 적용 배선 (기존 러너와의 대응) ═══
  CL(cl_run23)          구 s2_qs+preload 자리: ctrl=[-s1, -(s2+supp)], supp는 s2(사후 ahat
                        명령)·v2c 온라인 계산. settle 포함 상시 (pre30 golden 규약 동형).
  재생(a_full23)        구 lam_vec+pre30 자리: supp_vec(측정 traw2,dq2)를 t2에 합산 (SD 시프트
                        동일). settle=supp_vec[0], 기록 끝 이후=LAW_A만 (플랜트 상수 성분 —
                        구 pre30이 기록 끝 이후에도 잔존하던 규약의 물리적 대응).
  창(windows23/win429_06_23/score_0604_23)  lam = supp_vec (구 lam_vec(+pre30) 자리).
                        0429/0604(CVT)에도 절편 포함 — 법칙은 세션 보편 (Phase 2 적합에 포함).
  AIR(air_cycle23)      동일 — 무부하에서 부하항 자동 소멸, LAW_A 잔존 (Phase 2 공중 절편 실측
                        -1.1~-1.4; 상수 -1.2 주입 시 AIR 2.18→0.47 스캔 근거).
  C_CVT (CVT 가지 전용) qfrc[knee] = -C_CVT·|s₂|·max(1/max(|r|,0.2)-1, 0)·tanh(v_k)
                        (p22_exp_cvtloss coulomb형 — r=1 무변속에서 자동 소멸이지만 배선은
                        CVT 러너에만; 무변속 가지는 c_cvt=0 전달).
  D_DQ                  빌드 직후 model.dof_damping[knee] += D_DQ — qfrc가 닿지 않는
                        P12.eval_windows 내부 stepping까지 포함해 전 러너 균일 적용되는
                        플랜트 속성 구현. fv_knee와 합산이 음수가 될 수 있음 (주입 위험 명기).

═══ P23 Phase 4b: SPRING_GATED — 부하 연동 인루프 스프링 (opt-in 구조 수술) ═══
  env P23_SPRING_GATED=1 로만 켜짐 (import 시점 결정 — mp 워커는 env 상속; 기본 OFF는
  구 거동과 바이트 동일). ON이면:
    · XML 무릎 스프링 무장해제: 빌더에 넘기는 x32의 stiff 슬롯을 0 (_gate_x32) —
      spring_at="calf" 패치는 stiffness=0.000000으로 남아 관성 (ref 속성 무효과).
    · 전 러너 스텝마다 플랜트측 qfrc[knee] += stiff·(kref − q_knee_model)·h_load,
      h_load = x/(x+T_SPR), x = |ahat 무릎 토크| [Nm] (CL=온라인 s2, 재생/창=측정 트레이스).
      부호/프레임 = XML 패시브 스프링 −k·(q−springref) 동형 (p23_sg_frametest.py 검증).
      ★ kref = 컴파일된 qpos_spring[knee] = radians(ref) — XML springref가 MJCF 기본
      angle='degree'로 해석돼 온 사실을 frametest에서 발견 (raw v[1] 사용 금지;
      즉 기존 XML 스프링의 실효 기준각은 ~0.031rad = 모델 프레임 무릎 0° 부근이었음).
    · v23 벡터 23축 확장: slot 22 = T_SPR [Nm], bounds [0.5, 6.0], init 2.0.
      h→1 부하 / h→0 무부하. LAW_A bounds 불변 (0 수렴 기대 — 절편의 정체 가설).
  가설 (MARATHON Phase 4 절제 매트릭스): XML 상시 스프링이 무부하 자세에 ~1.2Nm 가짜
  토크 주입 (Phase 1 공중 정역학은 스프링 제외 시 완벽) ↔ 부하에선 실재(P18b) → 부하 게이트.
  창 평가: P12.eval_windows는 extra 훅이 qvel[2]만 받아 스프링(상태 q_knee + h_load(t)
  의존)을 못 실음 + 모델 속성도 아님(D_DQ와 다름) → eval_windows_g 동형 미러링.

이 모듈은 파일을 쓰지 않는다. 기존 파일 불변 — p20_run/p21_cma/p22_eval/p23_runners는
import만 (골든 규약 함수를 문자 그대로 미러링, 변경점은 ★주석으로 표시).
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C        # x32_of / _W / NAMES/LO/HI (20-vec 좌표)
import p22_eval as E       # ensure_init / x19_vec / QOFF_A429 / OLDQ_SESS / h_real_of
import p19_run as R19      # gap_v3 / CLIP / ALPH
import p23_runners as RN   # ff_trials / air_cycles / build_flip_welded / FF_SESS / 크래시 상수
import safe

# ── v23 벡터 정의 ──
NAMES23 = ["stiff", "ref", "fv_hip", "fc_hip", "fv_knee", "fc_knee", "solref",
           "imp0", "arm_knee", "M_c", "I_th", "I_ca", "dz_th", "dz_ca", "tm",
           "LAW_A", "LAW_V0", "o1_429", "o2_429", "LAW_B", "C_CVT", "D_DQ"]
LO23 = np.array([0.0, 1.5, 0.05, 0.0, 0.0, 0.0, 0.002, 0.05, 0.0005, 0.40, 0.55,
                 0.55, -0.12, -0.12, 0.0, -2.0, 4.3, -0.15, -0.15, 0.63, 0.0, -0.25])
HI23 = np.array([2.5, 2.7, 2.50, 0.30, 0.15, 0.25, 0.030, 0.70, 0.020, 1.10, 1.45,
                 1.45, 0.12, 0.12, 0.020, 0.0, 7.3, 0.15, 0.15, 0.89, 0.4, 0.10])
assert len(NAMES23) == len(LO23) == len(HI23) == 22

# ── Phase 4b: SPRING_GATED 모드 (모듈 docstring 참조) — 벡터 23축 확장 ──
SPRING_GATED = os.environ.get("P23_SPRING_GATED", "0") == "1"
T_SPR0, T_SPR_LO, T_SPR_HI = 2.0, 0.5, 6.0
if SPRING_GATED:
    NAMES23 = NAMES23 + ["T_SPR"]
    LO23 = np.append(LO23, T_SPR_LO)
    HI23 = np.append(HI23, T_SPR_HI)
NV23 = len(NAMES23)

# 측정 법칙 init (p23_law_fit.json hold_gate.gate — 전 자릿수 그대로)
LAW_A0 = -1.2212310538664326
LAW_B0 = 0.7585106669951319
LAW_V00 = 5.799535696434717
LAW_C = -0.02814484083476564    # 고정 (탐색 금지 — 푸시 레짐 불확실)
SUPP_CAP = 3.5                  # |τ̂| 외삽 안전 캡 [Nm]

FREEZE_IDX = np.array([9, 11, 13])   # M_c, I_ca, dz_ca — P22/P23 측정 검증 동결 (항시 적용)
_X19 = {"v": None}


def ensure_init():
    """p22_eval.ensure_init 재사용 — winit 1회 + fix0421 1회 (순서 불변 철칙)."""
    E.ensure_init()


def x19_20():
    """P19 앵커 20-vec (p22_eval.x19_vec) — 동결값·시드의 단일 출처."""
    if _X19["v"] is None:
        _X19["v"] = E.x19_vec()
    return _X19["v"]


def apply_freeze(v):
    """동결 3축을 P19 값으로 강제 (탐색기가 무슨 값을 내든 평가 전 덮어씀)."""
    v = np.asarray(v, float).copy()
    v[FREEZE_IDX] = x19_20()[FREEZE_IDX]
    return v


def _ext23():
    """확장 슬롯 init: [C_CVT, D_DQ] (+ [T_SPR0], gated 모드)."""
    return [0.0, 0.0] + ([T_SPR0] if SPRING_GATED else [])


def v23_p19_law():
    """시드 1: P19 플랜트 + 측정 법칙 init + C_CVT=D_DQ=0 (구조 변경 베이스라인)."""
    v = np.concatenate([x19_20(), _ext23()])
    v[15], v[16], v[19] = LAW_A0, LAW_V00, LAW_B0
    return np.clip(v, LO23 + 1e-9, HI23 - 1e-9)


def v23_p22b_law():
    """시드 2: p22b 플랜트(p22_gate_check rows[16]) + 측정 법칙 init + 0/0."""
    v = np.concatenate([RN.x22b_vec(), _ext23()])
    v[15], v[16], v[19] = LAW_A0, LAW_V00, LAW_B0
    return np.clip(v, LO23 + 1e-9, HI23 - 1e-9)


def law_of(v):
    """v23 → (LAW_A, LAW_B, LAW_V0)."""
    return float(v[15]), float(v[19]), float(v[16])


def pad23(v):
    """구 22축 벡터 → 현재 모드 길이 (gated면 T_SPR=init 패드) — 구 ckpt/진단 벡터 호환."""
    v = np.asarray(v, float)
    if SPRING_GATED and v.size == 22:
        v = np.append(v, T_SPR0)
    assert v.size == NV23, f"v23 길이 {v.size} (기대 {NV23}, SPRING_GATED={SPRING_GATED})"
    return v


def spr_of(v):
    """v23 → 게이트 스프링 (stiff_eff, ref, t_spr) | None(모드 OFF).
    stiff/ref는 XML 스프링과 같은 슬롯 (v[0], v[1]) — 구현 위치만 이동, 의미 동일."""
    if not SPRING_GATED:
        return None
    return float(v[0]), float(v[1]), float(v[22])


def h_load(x_abs, t_spr):
    """부하 게이트 h = x/(x+T_SPR) ∈ [0,1) — x = |ahat 무릎 토크| [Nm]."""
    return x_abs / (x_abs + t_spr)


def spr_resolve(model, spr):
    """spr → 모델 좌표 확정판 (stiff, kref_eff, T_SPR) | None.
    ★ kref_eff = 컴파일된 model.qpos_spring[knee] — XML springref는 MJCF 기본
    angle='degree'로 해석되어 radians(ref)≈0.031rad로 컴파일됨 (p23_sg_frametest 발견:
    raw v[1]=1.78rad를 쓰면 원 XML 스프링과 전혀 다른 힘). 원 스프링의 정확 복제를 위해
    반드시 컴파일 결과를 읽는다 (gated 빌드에서도 springref 속성은 남아 있음)."""
    if spr is None:
        return None
    mj = C._W["mj"]
    iq_k = safe.qadr(model, "knee", mj)
    # stiff는 XML 텍스트가 :.6f로 쓰던 값 → 동일 양자화 (frametest 잔차 1.1e-7의 원인 제거;
    # 게이트 빌드에선 jnt_stiffness=0이라 모델에서 못 읽음)
    return float(f"{spr[0]:.6f}"), float(model.qpos_spring[iq_k]), float(spr[2])


def spr_tau(qk_model, x_abs, sprm):
    """인루프 게이트 스프링 토크 [모델 프레임 knee dof]: MuJoCo 패시브 스프링
    qfrc_passive[knee] = stiff·(qpos_spring − q_knee)의 동형 × h_load
    (implicitfast에서 위치항은 명시적 → qfrc_applied 대체가 스텝 경계까지 동일 —
    p23_sg_frametest.py에서 h=1 강제 롤아웃 일치 검증). sprm = spr_resolve 확정판."""
    ks, kref, tspr = sprm
    return ks * (kref - qk_model) * h_load(x_abs, tspr)


def hl_vec(traw2, dq2, spr):
    """재생/창용 h_load 시계열 — supp_vec과 동일한 측정 ahat 트레이스 기반.
    SD 무시프트: 스프링은 플랜트측 물리량이라 명령 시프트 규약 비대상 (SD=1.5ms ≪ 게이트
    변화 시간스케일; supp는 명령 합산이라 시프트되는 것과 구별)."""
    P = C._W["P"]
    ah = P.J.ahat(P.A_PAPER, traw2, dq2)
    return h_load(np.abs(ah), spr[2])


# ══════════════════ 법칙/게이트 ══════════════════
def gate_v(v, v0):
    """== p20_run.gate (1/(1+(v/v0)^2)) — 동형 복제 (import 시점 의존 제거)."""
    return 1.0 / (1.0 + (np.abs(v) / v0) ** 2)


def supp_term(x_abs, law_b):
    """부하항 min(b·x + c·x², 3.5), x는 포물선 정점 x_pk=b/(2|c|)에서 클램프 (단조 보장)."""
    xpk = law_b / (2.0 * abs(LAW_C))
    x = np.minimum(x_abs, xpk)
    return np.minimum(law_b * x + LAW_C * x * x, SUPP_CAP)


def supp_scalar(s2, v2, law_a, law_b, law_v0):
    """CL 온라인용: s2 = 사후 ahat 명령 토크(부하 대리), v2 = 측정좌표 무릎(크랭크)속도."""
    return law_a + float(supp_term(abs(s2), law_b)) * float(gate_v(v2, law_v0))


def supp_vec(traw2, dq2, law):
    """재생/창용: 측정 트레이스 → supp 벡터 (구 lam_vec 자리; ahat = Paper 변환)."""
    law_a, law_b, law_v0 = law
    P = C._W["P"]
    ah = P.J.ahat(P.A_PAPER, traw2, dq2)
    return law_a + supp_term(np.abs(ah), law_b) * gate_v(dq2, law_v0)


# ══════════════════ 빌더 (D_DQ 배선 + Phase 4b XML 스프링 무장해제) ══════════════════
def _patch_ddq(model, d_dq):
    """빌드 직후 무릎 dof 점성 가산 — 모든 러너(창 평가 포함)에 균일한 플랜트 속성."""
    if abs(float(d_dq)) > 1e-12:
        mj = C._W["mj"]
        model.dof_damping[safe.dofadr(model, "knee", mj)] += float(d_dq)
    return model


def _gate_x32(x32):
    """SPRING_GATED: 빌더에 넘기는 x32의 stiff 슬롯을 0으로 — XML 스프링 무장해제
    (spring_at='calf' 패치는 stiffness=0.000000으로 남아 관성; springref는 무효과).
    러너의 인루프 스프링(spr_tau)이 그 자리를 대체. 원본 x32는 불변 (copy)."""
    if SPRING_GATED:
        x32 = np.asarray(x32, float).copy()
        x32[C.IDX["stiff"]] = 0.0
    return x32


def build_flip23(x32, ref, sp, d_dq):
    model, _ = C._W["P"].build_flip(_gate_x32(x32), ref, sp)
    return _patch_ddq(model, d_dq)


def build_cvt23(x32, ref, sp, l_i, d_dq):
    model, _ = C._W["P"].build_cvt(_gate_x32(x32), ref, sp, l_i)
    return _patch_ddq(model, d_dq)


def build_weld23(x32, ref, sp, d_dq):
    model, _ = RN.build_flip_welded(_gate_x32(x32), ref, sp)
    return _patch_ddq(model, d_dq)


# ══════════════════ CVT 전달비 테이블 (p22_exp_cvtloss.r_table 복제, l_i 캐시) ══════════════════
_RT = {}


def rtab(l_i):
    key = round(float(l_i), 6)
    if key not in _RT:
        from cvt_core import closure
        qs = np.linspace(-3.0, 3.0, 601)
        rs = np.ones(601)
        qk_prev = None
        for i, x in enumerate(qs):
            try:
                qk, _, _ = closure(float(x), key, qk_prev)
                qk2, _, _ = closure(float(x) + 1e-4, key, qk)
                rs[i] = (qk2 - qk) / 1e-4
                qk_prev = qk
            except Exception:
                rs[i] = rs[i - 1] if i else 1.0
        _RT[key] = (qs, rs)
    return _RT[key]


# ══════════════════ 1) cl_run23 — 폐루프 러너 (cl_run20_ff 세대 교체) ══════════════════
def cl_run23(model, is_cvt, l_i, d, gains, dqdes_on, ffk, A, tm, alphas, law,
             c_cvt=0.0, o1=0.0, o2=0.0, ff_hip=False, spr=None):
    """p23_runners.cl_run20_ff의 세대 교체 — 변경점 3 (그 외 문자 동일):
    ① 구 s2_qs(c_qs·s2·gate)+preload → supp(측정 법칙; s2·v2c 온라인)
    ② Cd 동적층 제거 (기존 심판도 Cd=0으로 불렀음 — 죽은 가지 정리)
    ③ CVT 가지 한정 C_CVT 전달손실 qfrc (무변속 호출은 c_cvt=0).
    + Phase 4b: spr=(stiff,ref,T_SPR)면 게이트 스프링 qfrc (x=|s2| 온라인, settle 포함)."""
    P = C._W["P"]
    mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = law
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqdes_on else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqdes_on else np.zeros_like(t)
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    sprm = spr_resolve(model, spr)
    qg = rg = None
    if is_cvt and c_cvt > 0:
        qg, rg = rtab(l_i)
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
            if ff_hip:
                c1 += np.interp(tm_, t, d["tdes1"])
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP)); c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = supp_scalar(s2, v2c, law_a, law_b, law_v0)      # ★ 변경점 ①
        tql = 0.0
        if qg is not None:                                      # ★ 변경점 ③ (CVT 한정)
            rr = float(np.interp(md.qpos[2], qg, rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(md.qvel[dof_knee])
            tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if sprm is not None:                                    # ★ Phase 4b 게이트 스프링
            tql += spr_tau(float(md.qpos[iq_k]), abs(s2), sprm)
        md.ctrl[:] = [-s1, -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
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


def cl_metrics23(v, x32, sp, law, c_cvt, d_dq, spr=None, model_f=None):
    """p21_cma.cl_metrics 세대 교체 — CL 스택 1회 → (τ-갭 v3, dq-갭). held-out(0324) 제외."""
    P = C._W["P"]
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    if model_f is None:
        model_f = build_flip23(x32, v[1], sp, d_dq)
    model_c = None
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    gs, dqs = [], []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds == "jump_0324":
            continue
        alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            if model_c is None:
                model_c = build_cvt23(x32, v[1], sp, l_i, d_dq)
            L = cl_run23(model_c, True, l_i, d, gains, dqon, ffk, P.A_PAPER,
                         float(v[14]), alphas, law, c_cvt=c_cvt,
                         o1=float(v[17]), o2=float(v[18]), spr=spr)
        else:
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            L = cl_run23(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER,
                         float(v[14]), alphas, law, c_cvt=0.0, o1=o1, o2=o2, spr=spr)
        if L is None:
            gs.append(2.0); dqs.append(2.0)
            continue
        g, q2r = R19.gap_v3(L, d, P.A_PAPER, m)
        gs.append(min(g, 2.0))
        t = d["t"]
        f = lambda k: np.interp(t, L["t"], L[k])
        num = np.sqrt(np.mean((f("dq1") - d["dq1"])[m] ** 2)
                      + np.mean((f("dq2") - d["dq2"])[m] ** 2))
        den = max(np.sqrt(np.mean(d["dq1"][m] ** 2) + np.mean(d["dq2"][m] ** 2)), 0.5)
        dqs.append(min(float(num / den), 2.0))
    return float(np.mean(gs)), float(np.mean(dqs))


# ══════════════════ 2) 창 평가 (windows/win429/0604 — lam→supp_vec) ══════════════════
def eval_windows_g(model, pp, hl, spr):
    """P12(g21_p12_polish).eval_windows(extra=None) 동형 미러 + 게이트 스프링 qfrc.
    D_DQ는 dof_damping(모델 속성)으로 eval_windows 내부까지 닿았지만, 스프링은 상태
    (q_knee)·부하(h_load(t)) 의존이라 extra 훅(qvel[2]만 수신)에도 모델 속성에도 못 실림 →
    win429_06_23이 p21_cma.win429_06을 미러링한 관례로 스텝 루프 복제. 변경점은 ★ 1곳."""
    mj = C._W["mj"]; MS = C._W["P12"]._G["MS"]
    ks, kref, _ = spr_resolve(model, spr)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    d = mj.MjData(model)
    t = pp["t"]; dt = model.opt.timestep
    sc = 0.0
    for i0 in pp["starts"]:
        t1 = min(t[i0] + pp["W"], t[-1])
        q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
        d.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
        d.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
        mj.mj_forward(model, d)
        nst = int(round((t1 - t[i0]) / dt))
        ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
        dq1a = np.empty(nst); dq2a = np.empty(nst)
        ok = True
        for k in range(nst):
            tc = t[i0] + k * dt
            d.ctrl[:] = [np.interp(tc, t, pp["tau_h"]), np.interp(tc, t, pp["tau_k"])]
            d.qfrc_applied[dof_knee] = (ks * (kref - float(d.qpos[iq_k]))
                                        * float(np.interp(tc, t, hl)))  # ★ 게이트 스프링
            try:
                mj.mj_step(model, d)
            except Exception:
                ok = False
                break
            ts[k] = tc + dt
            q1a[k] = d.qpos[1]; q2a[k] = d.qpos[2]
            dq1a[k] = d.qvel[1]; dq2a[k] = d.qvel[2]
        if not ok:
            sc += MS.W_Q * 2.0 + MS.W_DQ * 20.0
            continue
        mask = (t >= ts[0]) & (t <= ts[-1])
        if mask.sum() < 3:
            continue
        r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mask], ts, sim) - real[mask]) ** 2)))
        sc += (MS.W_Q * (r(q1a, pp["q1m"]) + r(q2a, pp["q2m"]))
               + MS.W_DQ * (r(dq1a, pp["dq1m"]) + r(dq2a, pp["dq2m"])))
    return sc


def windows23(model, x32, dss, law, W_override=None, spr=None):
    """p21_cma.windows_score 세대 교체 — lam = supp_vec (구 lam_vec+pre30 자리).
    D_DQ는 model 빌드 시 dof_damping으로 이미 배선됨 (eval_windows 내부까지 적용).
    spr(게이트 스프링)은 eval_windows_g 미러로 (측정 트레이스 h_load 시계열)."""
    P, P12 = C._W["P"], C._W["P12"]
    A = P.A_PAPER
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    per = []
    for tr in P12._G["trials"]:
        if tr["ds"] not in dss:
            continue
        k1, k2 = P12.OFFKEY.get(tr["ds"], (None, None))
        o1 = dd.get(k1, 0.0) if k1 else 0.0
        o2 = dd.get(k2, 0.0) if k2 else 0.0
        t = tr["pp"]["t"]
        lam = supp_vec(tr["raw2"], tr["v2"], law)               # ★ 변경점
        th = -(P.J.ahat(A, tr["raw1"], tr["v1"]))
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        if W_override:
            ppv["W"] = W_override
        ppo = P12._G["sv"](ppv, o1, o2)
        if spr is None:
            per.append(P12.eval_windows(model, ppo, None))
        else:                                                   # ★ Phase 4b
            per.append(eval_windows_g(model, ppo,
                                      hl_vec(tr["raw2"], tr["v2"], spr), spr))
    return float(np.mean(per)) if per else 9e9


def win429_06_23(x32, sp, ref, law, c_cvt, d_dq, spr=None):
    """p21_cma.win429_06 세대 교체 — lam→supp_vec + D_DQ(damping) + C_CVT(qfrc)
    + Phase 4b 게이트 스프링 (측정 트레이스 h_load)."""
    P, mj = C._W["P"], C._W["mj"]
    MS = C._W["P12"]._G["MS"]
    model = build_cvt23(x32, ref, sp, 0.02508, d_dq)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    if spr is not None:
        ks, kref, _ = spr_resolve(model, spr)
    qg, rg = rtab(0.02508) if c_cvt > 0 else (None, None)
    per = []
    for pre in C._W["pre429"]:
        d = pre["d"]; t = pre["t"]
        hl = hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
        sv = supp_vec(d["traw2"], d["dq2"], law)                # ★ 변경점
        th = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tk = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
        data = mj.MjData(model)
        dt = model.opt.timestep
        for i0, r_, gp in pre["starts"]:
            t0 = t[i0]; t1 = min(t0 + 0.6, t[-1])
            dqc = -d["dq2"][i0]
            data.qpos[:] = [pre["bz"][i0], pre["q1mj"][i0], pre["qcmj"][i0],
                            pre["qps"][i0], pre["qks"][i0]]
            data.qvel[:] = [pre["vbz"][i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
            mj.mj_forward(model, data)
            nst = int(round((t1 - t0) / dt))
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                s2m = float(np.interp(tc, t, tk))
                data.ctrl[:] = [-float(np.interp(tc, t, th)), -s2m]
                tql = 0.0
                if qg is not None:                              # ★ C_CVT
                    rr = float(np.interp(data.qpos[2], qg, rg))
                    amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
                    vk = float(data.qvel[dof_knee])
                    tql = -c_cvt * abs(s2m) * amp * float(np.tanh(vk / 1.0))
                if hl is not None:                              # ★ Phase 4b 게이트 스프링
                    tql += (ks * (kref - float(data.qpos[iq_k]))
                            * float(np.interp(tc, t, hl)))
                data.qfrc_applied[dof_knee] = tql
                try:
                    mj.mj_step(model, data)
                except Exception:
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
                dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
            if not ok:
                per.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                continue
            r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            per.append(MS.W_Q * (r(q1a, pre["q1mj"]) + r(q2a, pre["qcmj"]))
                       + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
    return float(np.mean(per)) if per else 9e9


def score_0604_23(x32, sp, ref, law, c_cvt, d_dq, spr=None):
    """p20_cma2.score_0604 세대 교체 — lam→supp_vec + D_DQ + C_CVT (+ Phase 4b 스프링).
    pre604 = winit 사전계산."""
    P, mj = C._W["P"], C._W["mj"]
    MS = C._W["P12"]._G["MS"]
    per = []
    for pre in C._W["pre604"]:
        d = pre["d"]; t = pre["t"]
        model = build_cvt23(x32, ref, sp, pre["li"], d_dq)
        dof_knee = safe.dofadr(model, "knee", mj)
        iq_k = safe.qadr(model, "knee", mj)
        if spr is not None:
            ks, kref, _ = spr_resolve(model, spr)
        qg, rg = rtab(pre["li"]) if c_cvt > 0 else (None, None)
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += pre["load"]
        data = mj.MjData(model)
        dt = model.opt.timestep
        hl = hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
        sv = supp_vec(d["traw2"], d["dq2"], law)                # ★ 변경점
        th = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
        tk = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
        for i0, r_, gp in pre["starts"]:
            t0 = t[i0]; t1 = min(t0 + 0.2, t[-1])
            dqc = -d["dq2"][i0]
            data.qpos[:] = [pre["bz"][i0], pre["q1mj"][i0], pre["qcmj"][i0],
                            pre["qps"][i0], pre["qks"][i0]]
            data.qvel[:] = [pre["vbz"][i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
            mj.mj_forward(model, data)
            nst = int(round((t1 - t0) / dt))
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                s2m = float(np.interp(tc, t, tk))
                data.ctrl[:] = [-float(np.interp(tc, t, th)), -s2m]
                tql = 0.0
                if qg is not None:                              # ★ C_CVT
                    rr = float(np.interp(data.qpos[2], qg, rg))
                    amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
                    vk = float(data.qvel[dof_knee])
                    tql = -c_cvt * abs(s2m) * amp * float(np.tanh(vk / 1.0))
                if hl is not None:                              # ★ Phase 4b 게이트 스프링
                    tql += (ks * (kref - float(data.qpos[iq_k]))
                            * float(np.interp(tc, t, hl)))
                data.qfrc_applied[dof_knee] = tql
                try:
                    mj.mj_step(model, data)
                except Exception:
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
                dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
            if not ok:
                per.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                continue
            r = lambda sim, real: float(np.sqrt(np.mean((np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            per.append(MS.W_Q * (r(q1a, pre["q1mj"]) + r(q2a, pre["qcmj"]))
                       + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
    return float(np.mean(per)) if per else 9e9


# ══════════════════ 3) a_full23 — Mode A 통짜 재생 (a_full 세대 교체) ══════════════════
def a_full23(model, is_cvt, l_i, d, law, o1, o2, c_cvt=0.0, spr=None):
    """p22_eval.a_full 세대 교체 — 변경점: lam_vec+pre30 → supp_vec (t2 합산, SD 시프트 동일).
    settle엔 supp_vec[0] 가산, 기록 끝 이후엔 LAW_A만 (구 pre30 잔존 규약의 물리 대응).
    CVT 가지엔 C_CVT qfrc. 반환 (dq2 RMSE, h_sim) 또는 None(발산).
    + Phase 4b 스프링 h_load: settle=hl[0](초기 유지 부하), 기록 중=측정 트레이스 보간,
      기록 끝 이후=0 (무명령=무부하 → 게이트 닫힘; XML 상시 스프링과의 의도된 차이)."""
    P = C._W["P"]; mj = C._W["mj"]; S = P.J._P["S"]
    t = d["t"]
    law_a = law[0]
    hl = hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
    if spr is not None:
        ks, kref, _ = spr_resolve(model, spr)
    sv = supp_vec(d["traw2"], d["dq2"], law)
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
    supp0 = float(sv[0])
    q1_0 = float(d["q1"][0]) + o1
    q2_0 = float(d["q2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
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
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    qg = rg = None
    if is_cvt and c_cvt > 0:
        qg, rg = rtab(l_i)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    dq2s = np.zeros(N); bzs = np.zeros(N)
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
            v1c = -md.qvel[1]; v2c = -md.qvel[2]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
            extra = supp0                                       # ★ settle: 초기상태 법칙값
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            extra = 0.0                                         # supp는 t2 안에 (lam 규약)
            if tc > t[-1]:
                s1 = s2 = 0.0
                extra = law_a                                   # ★ 기록 끝 이후: 상수 성분만
        md.ctrl[:] = [-s1, -(s2 + extra)]
        tql = 0.0
        if qg is not None:                                      # ★ C_CVT (CVT 한정)
            rr = float(np.interp(md.qpos[2], qg, rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(md.qvel[dof_knee])
            tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if hl is not None:                                      # ★ Phase 4b 게이트 스프링
            if tc < 0:
                h = float(hl[0])
            elif tc > t[-1]:
                h = 0.0
            else:
                h = float(np.interp(tc, t, hl))
            tql += ks * (kref - float(md.qpos[iq_k])) * h
        md.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        dq2s[k] = -md.qvel[2]; bzs[k] = md.qpos[0]
    m = t <= t[-1]
    rmse = float(np.sqrt(np.mean((np.interp(t, tl, dq2s)[m] - d["dq2"][m]) ** 2)))
    h_sim = float(bzs[tl > 0].max()) if (tl > 0).any() else float("nan")
    return rmse, h_sim


def oldq_h23(v, x32, sp, law, c_cvt, d_dq, spr=None, model_f=None):
    """p22_eval.oldq_h 세대 교체 — a_full23 사용. (OLDQ 세션별 dq2 RMSE, H, rows)."""
    P = C._W["P"]
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    if model_f is None:
        model_f = build_flip23(x32, v[1], sp, d_dq)
    model_c = build_cvt23(x32, v[1], sp, 0.02508, d_dq)
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    rows, herr = [], []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds not in E.OLDQ_SESS:
            continue
        if is_cvt:
            o1, o2 = E.QOFF_A429
            res = a_full23(model_c, True, d["l_i"], d, law, o1, o2, c_cvt=c_cvt,
                           spr=spr)
            hr = float(d.get("h_real", float("nan")))
        else:
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            res = a_full23(model_f, False, l_i, d, law, o1, o2, c_cvt=0.0, spr=spr)
            hr = E.h_real_of(ds, sub)
        if res is None:
            rows.append(dict(ds=ds, sub=str(sub), rmse=9.9,
                             h_sim=float("nan"), h_real=hr))
            herr.append(1.0)
            continue
        rmse, h_sim = res
        rows.append(dict(ds=ds, sub=str(sub), rmse=rmse, h_sim=h_sim, h_real=hr))
        if np.isfinite(hr) and np.isfinite(h_sim):
            herr.append(abs(h_sim / hr - 1.0))
    sess = {ds: float(np.mean([r["rmse"] for r in rows if r["ds"] == ds]))
            for ds in E.OLDQ_SESS}
    H = float(np.mean(herr)) if herr else float("nan")
    return sess, H, rows


# ══════════════════ 4) v6 신규 성분 — CL_FF / OLDQ_FF / AIR ══════════════════
def cl_ff23(x32, sp, ref, tm, law, d_dq, ff_hip, spr=None, model_f=None):
    """p23_runners.cl_ff 세대 교체 — cl_run23, alphas=[1,1,1,1]·o=0 동결 (앵커 프로토콜)."""
    P = C._W["P"]
    if model_f is None:
        model_f = build_flip23(x32, ref, sp, d_dq)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in RN.ff_trials():
        Lg = cl_run23(model_f, False, l_i, d, gains, dqon, ffk, P.A_PAPER, tm,
                      [1, 1, 1, 1], law, c_cvt=0.0, o1=0.0, o2=0.0, ff_hip=ff_hip,
                      spr=spr)
        if Lg is None:
            rows.append(dict(ds=ds, sub=sub, g=2.5, q2=9.9, crash=True))
            continue
        g, q2r = R19.gap_v3(Lg, d, P.A_PAPER, m)
        rows.append(dict(ds=ds, sub=sub, g=float(min(g, 2.0)), q2=float(q2r),
                         crash=False))
    sess = {ds: float(np.mean([r["g"] for r in rows if r["ds"] == ds]))
            for ds in RN.FF_SESS}
    return sess, rows


def oldq_ff23(x32, sp, ref, law, d_dq, spr=None, model_f=None):
    """p23_runners.oldq_ff 세대 교체 — a_full23 (o1=o2=0)."""
    if model_f is None:
        model_f = build_flip23(x32, ref, sp, d_dq)
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in RN.ff_trials():
        res = a_full23(model_f, False, l_i, d, law, 0.0, 0.0, c_cvt=0.0, spr=spr)
        hr = float(d.get("h_real", float("nan")))
        if res is None:
            rows.append(dict(ds=ds, sub=sub, rmse=9.9, h_sim=float("nan"),
                             h_real=hr, crash=True))
            continue
        rmse_, h_sim = res
        rows.append(dict(ds=ds, sub=sub, rmse=float(rmse_), h_sim=float(h_sim),
                         h_real=hr, crash=False))
    sess = {ds: float(np.mean([r["rmse"] for r in rows if r["ds"] == ds]))
            for ds in RN.FF_SESS}
    return sess, rows


def air_cycle23(model, d, law, spr=None):
    """p23_runners.air_replay_cycle 세대 교체 — lam/pre30 → supp_vec.
    무부하에서 부하항 자동 소멸 → 실질 LAW_A 절편 주입 (Phase 2 air_replay_scan 실증).
    + Phase 4b 스프링: 공중 |ahat|≈0.25Nm → h≈0.1 자연 소멸 (가설의 핵심 검증 지점)."""
    P = C._W["P"]; mj = C._W["mj"]; S = P.J._P["S"]
    t = d["t"]
    law_a = law[0]
    hl = hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
    if spr is not None:
        ks, kref, _ = spr_resolve(model, spr)
    sv = supp_vec(d["traw2"], d["dq2"], law)
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
    supp0 = float(sv[0])
    q1_0 = float(d["q1"][0]); q2_0 = float(d["q2"][0])
    md = mj.MjData(model)
    iq_h = safe.qadr(model, "hip", mj); iq_c = safe.qadr(model, "knee_motor", mj)
    iq_p = safe.qadr(model, "cpin", mj); iq_k = safe.qadr(model, "knee", mj)
    id_h = safe.dofadr(model, "hip", mj); id_c = safe.dofadr(model, "knee_motor", mj)
    id_k = safe.dofadr(model, "knee", mj)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    md.qpos[:] = 0
    md.qpos[iq_h] = sq1; md.qpos[iq_c] = sq2
    md.qpos[iq_p] = -sq2; md.qpos[iq_k] = sq2
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1]) / dt) + 1
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
            extra = supp0
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            extra = 0.0
            if tc > t[-1]:
                s1 = s2 = 0.0
                extra = law_a
        md.ctrl[:] = [-s1, -(s2 + extra)]
        if hl is not None:                                      # ★ Phase 4b 게이트 스프링
            if tc < 0:
                h = float(hl[0])
            elif tc > t[-1]:
                h = 0.0
            else:
                h = float(np.interp(tc, t, hl))
            md.qfrc_applied[id_k] = ks * (kref - float(md.qpos[iq_k])) * h
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


def air23(x32, sp, ref, law, d_dq, spr=None):
    """AIR = mean_cycles[ rmse(q2) + 0.1·rmse(dq2) ] (v6 동결 공식) — 용접 베이스 14사이클."""
    model_w = build_weld23(x32, ref, sp, d_dq)
    cycles, _ = RN.air_cycles()
    rows = []
    for i, d in enumerate(cycles):
        res = air_cycle23(model_w, d, law, spr=spr)
        if res is None:
            rows.append(dict(cyc=i + 1, rq=RN.CRASH_RQ, rdq=RN.CRASH_RDQ,
                             score=RN.CRASH_RQ + RN.AIR_W_DQ * RN.CRASH_RDQ, crash=True))
            continue
        rq, rdq = res
        rows.append(dict(cyc=i + 1, rq=rq, rdq=rdq,
                         score=rq + RN.AIR_W_DQ * rdq, crash=False))
    return float(np.mean([r["score"] for r in rows])), rows
