# -*- coding: utf-8 -*-
"""p25_d_deploy — P25 Phase D 배포 리허설 평가기 (MARATHON_p25 지표 선고정 구현).

목적: Phase A/B/C가 산출한 점프 궤적(계획)을 (q_des, dq_des)로 p24a 트윈에
폐루프 PD 배포하고 ① τ-fidelity F_τ ② 실현 높이 h_PD ③ H_fid 를 계산한다.
개념 주의(MARATHON 명문): 트윈 안 리허설에서 플랜트=트윈이므로 F_τ의 성분은
모델 오차가 아니라 **PD 추종 한계 + 궤적의 공격성** — "궤적의 배포 가능성"을 잰다.

═══ API ═══
  deploy(npz_path, gains, return_log=False) → dict
    gains: 프리셋 이름 "mid"/"high" 또는 (kp1, kd1, kp2, kd2) 튜플.
    프리셋 = 실 폴더 라벨 규약 kp1_kd1_kp2_kd2 = (hip_kp, hip_kd, knee_kp, knee_kd)
    (g22_p10_pdlaw.label_gains 파서로 확정된 순서):
      mid  = 120_2_120_2   → (120.0, 2.0, 120.0, 2.0)
      high = 150_2.2_500_4 → (150.0, 2.2, 500.0, 4.0)

═══ 계획 npz 스키마 (Phase A/B/C 산출 계약 — 이 파일이 단일 출처) ═══
  t        (N,)   [s] 0에서 시작하는 기준 시간축 (t[0]≠0이면 t−t[0]로 정규화)
  q        (N,2)  [rad] 최적화기 롤아웃 관절각 [hip, knee(크랭크측)] — 측정좌표 프레임
  dq       (N,2)  [rad/s]
  tau_cmd_nm  (N,2) [Nm] 계획 토크 τ* (â 채널 = ahat 출력 프레임). 별칭 허용:
                    tau_nm / tau_star_nm / tau_star. 없으면 tau_cmd_raw(별칭 tau_raw,
                    raw iTM)를 â(A_PAPER, raw, dq)로 변환 (dq = 계획 롤아웃 속도).
  bz       (N,)   [m] 롤아웃 베이스 높이 → h_plan = max(bz). 스칼라 h_plan 키가
                   있으면 그것이 우선 (bz 생략 가능).
  q_des/dq_des (N,2, 선택) 배포용 명령 궤적 — 없으면 q/dq를 그대로 명령으로 사용.
  (2,N) 저장도 허용 — 로더가 자동 전치.
  ★ Phase A 채널쌍 스키마(p25_a_twin.save_npz)도 동등 수용: q1/q2, dq1/dq2,
    raw1/raw2, tau1_nm/tau2_nm (+선택 qd1/qd2, dqd1/dqd2 — 있으면 명령으로 우선),
    t가 settle 포함(음수 시각)이면 t<0 구간을 크롭 후 0 시작으로 정규화.

═══ 배포 규약 (전부 cl_run23 정본 경로 — 재구현 없음) ═══
  - 트윈 = 승격 p24a 후보 (p23_veins/fourbar_p24a_candidate.json) 전 층:
    측정 지지법칙 + 부하연동 스프링 + 상승항 + 힙 부하-지지층. l_i=30 flip 모델.
  - 커맨드층: alphas=[1,1,1,1], ffk/ff_hip OFF, o1=o2=0, tm=x[14], 클립 ±35.5
    (R19.CLIP — cl_run23 내장), â 변환 = Paper 식.
  - settle: cl_run23 내장 T_SETTLE=0.4s 동안 SETTLE_KP/KD로 계획 초기자세
    (q_des[0])에 정착 후 t=0부터 추종.
  - 기준 종료 후: **end-hold** — cl_run23의 tm_=min(tc, t[-1]) 규약 그대로
    (q_des[-1], dq_des[-1])를 계속 명령하며 T_AFTER=0.6s 추가 스텝 → apex 포착.
    (zero-hold 아님 — dq_des[-1]≠0이면 그 값이 유지됨을 계획 작성자가 인지할 것.
     점프 계획은 이지 후 구간이라 실질 영향 없음. apex가 창 끝에 걸리면
     apex_censored=True 플래그.)

═══ 지표 정의 (MARATHON 선고정) ═══
  h_PD   = max bz (t>0) [m]  (a_full23의 h_sim 규약 동일)
  τ_PD   = 로그 sh1/sh2 = â(clip(PD 명령)) — 플랜트 층(supp/스프링/CVT) 합산 **전**
           채널 = 실기 로깅과 비교 가능한 채널 (cl_run23 sh 로깅 규약 그대로)
  F_τ    = RMSE(τ_PD−τ*)/RMS(τ*), 스탠스 구간(t∈[0, min(t_liftoff, t_end)]):
           pooled = √(mean e₁²+mean e₂²)/max(√(mean τ₁*²+mean τ₂*²), 0.5)
           (gap_v3 합산 규약), per-joint 분모 하한 0.3 (tau_gap 규약).
           t_liftoff = GRF < 0.5 N 연속 5스텝 최초 시점 (t>0.02s부터 탐색).
  H_fid  = |h_PD/h_plan − 1|
  dq/q 추종 RMSE = 기준 창(t∈[0, t_end])에서 sim−des, per-joint +
           pooled=√(mean₁+mean₂) (cl_metrics23 규약).

═══ 검증 (이 파일 내장, `python p25_d_deploy.py validate`) ═══
  ① golden 자기일관: 실측 0602 첫 trial의 (qd, dqd)를 계획으로, â(측정)를 τ*로 —
     deploy() 내부 로그가 동일 인자 cl_run23_log 직접 호출과 비트 동일해야 함
     (배관 항등) + F_τ 기계 가동 (알려진 CL 거동 재현; alphas=1·o=0 배포 규약이므로
     심판의 fitted-α τ-갭 수치와는 다름 — gap_v3 참고 수치 병기).
  ② fixed-point: CL 스스로 낳은 궤적(q,dq)을 계획으로, 그 τ_PD를 τ*로 재배포 →
     F_τ ≈ 0 기대 (자기 재현 새니티; 잔차 = 추종오차 e의 폐루프 재통과 성분).
검증 산출물: p25_d_golden_plan.npz / p25_d_fixedpoint_plan.npz / p25_d_validation.json.
"""
import os
import sys
import time
from pathlib import Path

# ★ 구조 플래그는 p23 모듈 import 전에 env로 강제 (p24a_all_results.py 규약 동일)
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"
os.environ["P24_REFIT"] = "1"

import numpy as np

HERE = Path(__file__).parent
PV = HERE.parent / "p23_veins"
sys.path.insert(0, str(PV))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p23_v6_runners as RU
import p22_eval as E
import p19_run as R19
import p19_adapter as AD
import safe

assert RU.SPRING_GATED and RU.RISE_GATED and RU.P24_REFIT and RU.HIP_LAW, \
    "p24a 구조 플래그 불일치 (env 강제 실패 — import 순서 확인)"

CAND_PATH = PV / "fourbar_p24a_candidate.json"
MODEL_TAG = "p24a"

# 게인 프리셋 — 실 폴더 라벨 규약 kp1_kd1_kp2_kd2 (1=hip, 2=knee)
# P25_GAINS_FULL=1 → 실 세션(0429/0602) 게인 8종 전체 그리드 (사용자 지시 07-17: "게인 다양하게")
if os.environ.get("P25_GAINS_FULL"):
    GAINS = {"60_1.5_60_1.5": (60.0, 1.5, 60.0, 1.5),
             "90_1.5_90_2.5": (90.0, 1.5, 90.0, 2.5),
             "120_2_120_2": (120.0, 2.0, 120.0, 2.0),
             "120_2.2_150_2.5": (120.0, 2.2, 150.0, 2.5),
             "120_2.2_200_2.8": (120.0, 2.2, 200.0, 2.8),
             "150_2.2_250_3": (150.0, 2.2, 250.0, 3.0),
             "150_2.2_350_3.5": (150.0, 2.2, 350.0, 3.5),
             "150_2.2_500_4": (150.0, 2.2, 500.0, 4.0)}
else:
    GAINS = {"mid": (120.0, 2.0, 120.0, 2.0),
             "high": (150.0, 2.2, 500.0, 4.0)}

# P25_CLIP_RAW → 공급 클립 재정의 (raw 도메인). 18Nm 캠페인: 31.1771
# (a_hat 운동방향 가지 = 정확히 18.00Nm — 35.5→20.23Nm 보고 규약과 동일 가지)
if os.environ.get("P25_CLIP_RAW"):
    R19.CLIP = float(os.environ["P25_CLIP_RAW"])

GRF_EPS = 0.5     # [N] 이지 판정 문턱
LIFT_HOLD = 5     # 연속 스텝 수
DEN_POOL = 0.5    # pooled RMS(τ*) 분모 하한 [Nm] (gap_v3 규약)
DEN_JOINT = 0.3   # per-joint 분모 하한 [Nm] (tau_gap 규약)

G = {}            # setup()이 채우는 전역 (winit 후 유효)


def setup():
    """winit+fix0421 1회 → 후보 벡터/모델 전역 확정 (p24a_all_results.setup 동형)."""
    if G.get("ready"):
        return
    t0 = time.time()
    cand = AD.load_candidate(CAND_PATH)
    RU.ensure_init()
    AD._INIT = True
    P = RU.C._W["P"]
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    x32, sp = RU.C.x32_of(v[:20])
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    G.update(ready=True, P=P, A=P.A_PAPER, V=v, X32=x32, SP=sp, CAND=cand,
             REF=float(v[1]), TM=float(v[14]),
             LAW=RU.law_of(v), SPR=RU.spr_of(v),
             C_CVT=float(v[20]), D_DQ=float(v[21]), KR=RU.rise_of(float(v[21])))
    print(f"[p25_d] setup done [{time.time() - t0:.0f}s] — {MODEL_TAG} "
          f"law={tuple(round(x, 4) for x in G['LAW'])} "
          f"spr={tuple(round(x, 4) for x in G['SPR'])} "
          f"k_rise={G['KR']:.4f} tm={G['TM'] * 1000:.2f}ms", flush=True)


def model_flip():
    if "model_f" not in G:
        G["model_f"] = RU.build_flip23(G["X32"], G["REF"], G["SP"], G["D_DQ"])
    return G["model_f"]


# ══════════════════ 계획 npz 로더 ══════════════════
def _as_n2(a, name):
    a = np.asarray(a, float)
    if a.ndim == 2 and a.shape[1] == 2:
        return a
    if a.ndim == 2 and a.shape[0] == 2:
        return a.T
    raise ValueError(f"계획 npz '{name}': (N,2)/(2,N) 필요 — got {a.shape}")


def _pick(z, *names):
    for n in names:
        if n in z.files:
            return z[n]
    return None


def _pair(z, n1, n2):
    """1-D 채널쌍 (Phase A p25_a_twin.save_npz 스키마) → (N,2) | None."""
    a, b = _pick(z, n1), _pick(z, n2)
    if a is None or b is None:
        return None
    return np.column_stack([np.asarray(a, float).ravel(),
                            np.asarray(b, float).ravel()])


def _mat_or_pair(z, mats, pair, req=False, tag=""):
    """행렬 키(mats) 우선, 없으면 채널쌍(pair) — 두 저장 스키마 모두 수용."""
    for n in mats:
        if n in z.files:
            return _as_n2(z[n], n)
    v = _pair(z, *pair)
    if v is None and req:
        raise ValueError(f"계획 npz에 {tag} 없음 (키 {mats} 또는 {pair})")
    return v


def load_plan(npz_path):
    """계획 npz → dict(t, qd(N,2), dqd(N,2), tau(N,2)|None, tau_src, h_plan).

    두 스키마 수용: ① 행렬형 (모듈 docstring 계약: q_des/dq_des/q/dq/tau_cmd_nm …)
    ② Phase A 채널쌍형 (p25_a_twin.save_npz: q1 q2/dq1 dq2/raw1 raw2/tau1_nm
    tau2_nm + 선택 qd1 qd2/dqd1 dqd2 — t가 settle 포함이면 t<0 구간 크롭)."""
    z = np.load(npz_path, allow_pickle=True)
    t = np.asarray(z["t"], float).ravel()
    q = _mat_or_pair(z, ("q",), ("q1", "q2"))
    dq = _mat_or_pair(z, ("dq",), ("dq1", "dq2"))
    qd = _mat_or_pair(z, ("q_des", "qdes"), ("qd1", "qd2"))
    dqd = _mat_or_pair(z, ("dq_des", "dqdes"), ("dqd1", "dqd2"))
    if qd is None:
        qd = q
    if dqd is None:
        dqd = dq
    if qd is None or dqd is None:
        raise ValueError(f"계획 npz에 명령 궤적 없음 (q_des|qd1,qd2|q|q1,q2): "
                         f"{npz_path}")
    # τ* — Nm 우선, 없으면 raw→â 변환 (변환 속도 = 계획 롤아웃 dq, 없으면 dq_des)
    tau = _mat_or_pair(z, ("tau_cmd_nm", "tau_nm", "tau_star_nm", "tau_star"),
                       ("tau1_nm", "tau2_nm"))
    tau_src = "nm" if tau is not None else None
    if tau is None:
        raw = _mat_or_pair(z, ("tau_cmd_raw", "tau_raw"), ("raw1", "raw2"))
        if raw is not None:
            dqv = dq if dq is not None else dqd
            P = G["P"]
            tau = np.column_stack([P.J.ahat(G["A"], raw[:, 0], dqv[:, 0]),
                                   P.J.ahat(G["A"], raw[:, 1], dqv[:, 1])])
            tau_src = "raw->ahat"
    bz = _pick(z, "bz")
    if "h_plan" in z.files:
        h_plan = float(np.asarray(z["h_plan"]).ravel()[0])
    elif bz is not None:
        bzv = np.asarray(bz, float).ravel()
        h_plan = float(bzv[t > 0].max() if (t > 0).any() else bzv.max())
    else:
        h_plan = float("nan")
    # settle 포함 t (Phase A 스키마: 0=커맨드 시작) → t<0 크롭 후 0 시작 정규화
    for name, a in (("q_des", qd), ("dq_des", dqd), ("tau", tau)):
        if a is not None and len(a) != len(t):
            raise ValueError(f"계획 npz 길이 불일치: t {len(t)} vs {name} {len(a)}")
    mk = t >= -1e-12
    t2 = t[mk] - t[mk][0]
    return dict(t=t2, qd=qd[mk], dqd=dqd[mk],
                tau=tau[mk] if tau is not None else None,
                tau_src=tau_src, h_plan=h_plan)


# ══════════════════ 지표 계산 ══════════════════
def _liftoff(tl, grf, t_end):
    """이지 시각 — GRF < GRF_EPS 연속 LIFT_HOLD 스텝 최초 (t>0.02s 탐색)."""
    cnt = 0
    for k in range(len(tl)):
        if tl[k] <= 0.02:
            continue
        if grf[k] < GRF_EPS:
            cnt += 1
            if cnt >= LIFT_HOLD:
                return float(tl[k - LIFT_HOLD + 1]), True
        else:
            cnt = 0
    return float(t_end), False


def metrics_of(L, plan):
    """cl_run23_log 로그 + 계획 → 지표 dict (deploy/검증 공용)."""
    t = plan["t"]
    t_end = float(t[-1])
    tl = L["t"]
    pos = tl > 0
    bz_pos = L["bz"][pos]
    k_apex = int(np.argmax(bz_pos))
    h_pd = float(bz_pos[k_apex])
    apex_censored = bool(k_apex == len(bz_pos) - 1)
    t_lo, lo_found = _liftoff(tl, L["grf"], t_end)
    sm = (tl >= 0.0) & (tl <= min(t_lo, t_end))     # 스탠스 (τ* 정의역 내)
    rm = (tl >= 0.0) & (tl <= t_end)                # 기준 창 (추종 지표)
    out = dict(h_PD=h_pd, apex_censored=apex_censored,
               t_end=t_end, t_liftoff=t_lo, liftoff_found=lo_found,
               stance_n=int(sm.sum()),
               h_plan=float(plan["h_plan"]), tau_src=plan["tau_src"])
    hp = plan["h_plan"]
    out["H_fid"] = (float(abs(h_pd / hp - 1.0))
                    if np.isfinite(hp) and hp > 1e-6 else float("nan"))
    # F_τ — τ_PD = sh 채널 (â 출력, 플랜트 층 합산 전)
    if plan["tau"] is not None and sm.any():
        ts1 = np.interp(tl, t, plan["tau"][:, 0])
        ts2 = np.interp(tl, t, plan["tau"][:, 1])
        e1 = (L["sh1"] - ts1)[sm]
        e2 = (L["sh2"] - ts2)[sm]
        m1 = float(np.mean(ts1[sm] ** 2))
        m2 = float(np.mean(ts2[sm] ** 2))
        out["rms_tau_star"] = float(np.sqrt(m1 + m2))
        out["F_tau"] = float(np.sqrt(np.mean(e1 ** 2) + np.mean(e2 ** 2))
                             / max(np.sqrt(m1 + m2), DEN_POOL))
        out["F_tau_hip"] = float(np.sqrt(np.mean(e1 ** 2))
                                 / max(np.sqrt(m1), DEN_JOINT))
        out["F_tau_knee"] = float(np.sqrt(np.mean(e2 ** 2))
                                  / max(np.sqrt(m2), DEN_JOINT))
    else:
        out.update(F_tau=float("nan"), F_tau_hip=float("nan"),
                   F_tau_knee=float("nan"), rms_tau_star=float("nan"),
                   tau_missing=plan["tau"] is None)
    # 추종 RMSE (기준 창)
    for nm, sim1, sim2, ref in (("dq", L["dq1"], L["dq2"], plan["dqd"]),
                                ("q", L["q1"], L["q2"], plan["qd"])):
        r1 = np.interp(tl, t, ref[:, 0])
        r2 = np.interp(tl, t, ref[:, 1])
        m1 = float(np.mean((sim1 - r1)[rm] ** 2))
        m2 = float(np.mean((sim2 - r2)[rm] ** 2))
        out[f"{nm}_rmse_hip"] = float(np.sqrt(m1))
        out[f"{nm}_rmse_knee"] = float(np.sqrt(m2))
        out[f"{nm}_rmse"] = float(np.sqrt(m1 + m2))
    return out


# ══════════════════ 메인 API ══════════════════
def deploy(npz_path, gains, return_log=False):
    """계획 npz를 트윈 폐루프 PD로 배포 → 지표 dict (모듈 docstring 참조)."""
    setup()
    if isinstance(gains, str):
        glabel, g4 = gains, GAINS[gains]
    else:
        g4 = tuple(float(x) for x in gains)
        assert len(g4) == 4, f"gains 튜플은 (kp1,kd1,kp2,kd2) 4원 — got {gains}"
        glabel = "_".join(f"{x:g}" for x in g4)
    plan = load_plan(npz_path)
    d = dict(t=plan["t"], qd1=plan["qd"][:, 0], qd2=plan["qd"][:, 1],
             dqd1=plan["dqd"][:, 0], dqd2=plan["dqd"][:, 1])
    L = RU.cl_run23_log(model_flip(), False, 0.030, d, g4, True, False,
                        G["A"], G["TM"], [1, 1, 1, 1], G["LAW"], c_cvt=0.0,
                        o1=0.0, o2=0.0, ff_hip=False, spr=G["SPR"],
                        k_rise=G["KR"])
    base = dict(plan=str(npz_path), gains_label=glabel, gains=list(g4),
                model=MODEL_TAG)
    if L is None:
        return dict(base, crash=True, h_PD=float("nan"), h_plan=plan["h_plan"],
                    H_fid=float("nan"), F_tau=float("nan"),
                    F_tau_hip=float("nan"), F_tau_knee=float("nan"),
                    dq_rmse=float("nan"))
    out = dict(base, crash=False, dt=float(model_flip().opt.timestep),
               **metrics_of(L, plan))
    if return_log:
        out["log"] = L
        out["_plan"] = plan
    return out


# ══════════════════ 검증 ① golden 자기일관 (실측 0602) ══════════════════
def _trial_0602():
    setup()
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds == "jump_0602":
            return ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i
    raise RuntimeError("jump_0602 trial 없음")


def make_golden_plan(out_path):
    """0602 첫 trial: 계획 = 기록 (qd,dqd) / τ* = â(측정) / h_plan = h_real."""
    ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i = _trial_0602()
    P = G["P"]
    tau = np.column_stack([P.J.ahat(G["A"], d["traw1"], d["dq1"]),
                           P.J.ahat(G["A"], d["traw2"], d["dq2"])])
    hr = E.h_real_of(ds, sub)
    np.savez(out_path, t=d["t"],
             q_des=np.column_stack([d["qd1"], d["qd2"]]),
             dq_des=np.column_stack([d["dqd1"], d["dqd2"]]),
             q=np.column_stack([d["q1"], d["q2"]]),
             dq=np.column_stack([d["dq1"], d["dq2"]]),
             tau_cmd_nm=tau, h_plan=float(hr),
             method=f"golden {ds}/{sub}")
    return out_path, (ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i)


def validate_golden():
    setup()
    gp = HERE / "p25_d_golden_plan.npz"
    gp, (ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i) = make_golden_plan(gp)
    assert dqon and not ffk, f"golden trial 규약 확인 실패 (dqon={dqon}, ffk={ffk})"
    res = deploy(gp, gains, return_log=True)
    # 항등 기준: 동일 인자 cl_run23_log 직접 호출 (배포 규약 = alphas 1, o=0)
    L_ref = RU.cl_run23_log(model_flip(), False, l_i, d, gains, dqon, ffk,
                            G["A"], G["TM"], [1, 1, 1, 1], G["LAW"], c_cvt=0.0,
                            o1=0.0, o2=0.0, ff_hip=False, spr=G["SPR"],
                            k_rise=G["KR"])
    L = res["log"]
    dmax = {k: float(np.abs(L[k] - L_ref[k]).max())
            for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz")}
    g_v3, q2r = R19.gap_v3(L, d, G["A"], m)          # 참고: 심판 창(toff+0.1) 지표
    out = dict(trial=f"{ds}/{sub}", gains=list(gains),
               identity_max_abs_diff=dmax,
               identity_pass=bool(max(dmax.values()) < 1e-12),
               F_tau=res["F_tau"], F_tau_hip=res["F_tau_hip"],
               F_tau_knee=res["F_tau_knee"],
               gap_v3_ref=float(g_v3), q2_rmse_ref=float(q2r),
               h_PD=res["h_PD"], h_plan=res["h_plan"], H_fid=res["H_fid"],
               dq_rmse=res["dq_rmse"], t_liftoff=res["t_liftoff"],
               stance_n=res["stance_n"], apex_censored=res["apex_censored"],
               note=("항등: deploy 내부 로그 vs 동일 인자 cl_run23_log (기대 0). "
                     "F_τ(스탠스, τ*=â측정) vs gap_v3(심판 창, alphas=1·o=0 배포 "
                     "규약이라 fitted-α 심판 수치와 다름) 병기."))
    del res["log"], res["_plan"]
    out["deploy_result"] = res
    return out


# ══════════════════ 검증 ② fixed-point (CL 자기 궤적 재배포) ══════════════════
def validate_fixedpoint(gains="mid"):
    setup()
    gp = HERE / "p25_d_golden_plan.npz"
    if not gp.exists():
        make_golden_plan(gp)
    r1 = deploy(gp, gains, return_log=True)
    assert not r1["crash"], "fixed-point 1차 배포 crash"
    L1 = r1["log"]
    tl = L1["t"]
    t_end = float(r1["t_end"])
    mk = (tl >= 0.0) & (tl <= t_end)
    t2 = tl[mk] - tl[mk][0]
    fp = HERE / "p25_d_fixedpoint_plan.npz"
    np.savez(fp, t=t2,
             q=np.column_stack([L1["q1"][mk], L1["q2"][mk]]),
             dq=np.column_stack([L1["dq1"][mk], L1["dq2"][mk]]),
             tau_cmd_nm=np.column_stack([L1["sh1"][mk], L1["sh2"][mk]]),
             bz=L1["bz"][mk], h_plan=float(r1["h_PD"]),
             method=f"fixedpoint(CL self, {r1['gains_label']})")
    r2 = deploy(fp, gains)
    # 기계 바닥(floor) 검증: 계획 = 1차와 **동일 명령**(golden qd/dqd) + τ* = 1차의
    # τ_PD(sh, golden t 그리드로 재표집) → 재배포는 1차와 비트 동일 궤적이므로
    # F_τ ≈ 0 (재표집 보간 오차만 잔존) — F_τ 기계의 0-바닥 확인.
    pg = np.load(gp, allow_pickle=True)
    tg = np.asarray(pg["t"], float)
    fpc = HERE / "p25_d_fixedpoint_cmd_plan.npz"
    np.savez(fpc, t=tg, q_des=pg["q_des"], dq_des=pg["dq_des"],
             tau_cmd_nm=np.column_stack([np.interp(tg, tl, L1["sh1"]),
                                         np.interp(tg, tl, L1["sh2"])]),
             h_plan=float(r1["h_PD"]),
             method=f"fixedpoint-cmd(floor, {r1['gains_label']})")
    r3 = deploy(fpc, gains)
    out = dict(gains_label=r1["gains_label"],
               run1=dict(h_PD=r1["h_PD"], F_tau_vs_golden=r1["F_tau"],
                         t_liftoff=r1["t_liftoff"]),
               floor_cmd=dict(F_tau=r3["F_tau"], F_tau_hip=r3["F_tau_hip"],
                              F_tau_knee=r3["F_tau_knee"], h_PD=r3["h_PD"],
                              H_fid=r3["H_fid"]),
               run2=dict(h_PD=r2["h_PD"], F_tau=r2["F_tau"],
                         F_tau_hip=r2["F_tau_hip"], F_tau_knee=r2["F_tau_knee"],
                         H_fid=r2["H_fid"], dq_rmse=r2["dq_rmse"],
                         q_rmse=r2["q_rmse"], t_liftoff=r2["t_liftoff"]),
               note=("floor_cmd: 동일 명령 재배포 (진짜 고정점) → F_τ 바닥 확인. "
                     "run2: 실현 (q,dq) 재배포 — δ=q₁−q₂ 동역학이 "
                     "M δ̈+k_d δ̇+k_p δ=τ₁ 인 공진 필터 (τ₂=k_p δ+k_d δ̇, "
                     "ζ=k_d/2√(k_p M)≪1) 라 τ₁이 증폭 재생됨 → 실현 궤적은 "
                     "일반적으로 PD 고정점이 아님 (개루프≠폐루프 독트린의 정량 "
                     "재현 — MARATHON 가설 열의 예상과 정합)."))
    return out


def main():
    safe.utf8_console()
    stage = sys.argv[1] if len(sys.argv) > 1 else "validate"
    t0 = time.time()
    if stage != "validate":
        sys.exit(f"unknown stage: {stage} (validate만 지원)")
    res = dict(gen=time.strftime("%Y-%m-%d %H:%M"), model=MODEL_TAG,
               cand=str(CAND_PATH))
    print("═══ 검증 ① golden 자기일관 (0602 실측) ═══", flush=True)
    res["golden"] = validate_golden()
    gd = res["golden"]
    print(f"  trial={gd['trial']} gains={gd['gains']}", flush=True)
    print(f"  항등 max|Δ| = { {k: f'{v:.2e}' for k, v in gd['identity_max_abs_diff'].items()} }"
          f" → {'PASS' if gd['identity_pass'] else 'FAIL'}", flush=True)
    print(f"  F_τ(스탠스) = {gd['F_tau'] * 100:.1f}% (hip {gd['F_tau_hip'] * 100:.1f}% / "
          f"knee {gd['F_tau_knee'] * 100:.1f}%) · gap_v3(심판창, α=1) = "
          f"{gd['gap_v3_ref'] * 100:.1f}%", flush=True)
    print(f"  h_PD = {gd['h_PD']:.3f} m vs h_plan(real) = {gd['h_plan']:.3f} m "
          f"(H_fid {gd['H_fid'] * 100:.1f}%) · dq_rmse {gd['dq_rmse']:.2f} · "
          f"liftoff {gd['t_liftoff'] * 1000:.0f}ms", flush=True)
    print("═══ 검증 ② fixed-point (CL 자기 궤적 재배포, mid) ═══", flush=True)
    res["fixedpoint"] = validate_fixedpoint("mid")
    fx = res["fixedpoint"]
    print(f"  run1 h_PD = {fx['run1']['h_PD']:.3f} m (F_τ vs golden "
          f"{fx['run1']['F_tau_vs_golden'] * 100:.1f}%)", flush=True)
    fc = fx["floor_cmd"]
    print(f"  floor(동일 명령 재배포): F_τ = {fc['F_tau'] * 100:.3f}% "
          f"(hip {fc['F_tau_hip'] * 100:.3f}% / knee {fc['F_tau_knee'] * 100:.3f}%) "
          f"· h_PD = {fc['h_PD']:.3f} m", flush=True)
    r2 = fx["run2"]
    print(f"  실현궤적 재배포: F_τ = {r2['F_tau'] * 100:.2f}% (hip {r2['F_tau_hip'] * 100:.2f}% / "
          f"knee {r2['F_tau_knee'] * 100:.2f}%) · h_PD = {r2['h_PD']:.3f} m "
          f"(H_fid {r2['H_fid'] * 100:.2f}%) · q_rmse {r2['q_rmse']:.4f} rad · "
          f"dq_rmse {r2['dq_rmse']:.3f} rad/s", flush=True)
    safe.atomic_json_write(HERE / "p25_d_validation.json", res)
    print(f"검증 원장 저장: p25_d_validation.json [{time.time() - t0:.0f}s]",
          flush=True)


if __name__ == "__main__":
    main()
