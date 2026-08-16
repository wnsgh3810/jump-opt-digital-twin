# -*- coding: utf-8 -*-
"""t0wc_env — P25-task0: task0(with_cvt) l_i-조건부 PPO 점프 환경 (t0nc_env 사본 확장).

원본: t0nc_env.py (no_cvt판 — 골든 A/B 검증 구조, task0 제약 페널티 |â|>15 포함).
변경점 (P25-task0 with_cvt 확장, 사용자 지시 07-18 "모든 방법론에서 l_i 상수 최적화"):
  1. 플랜트 = CVT 체인 (t0wc_cma.rollout_cl이 미러하는 cl_run23 is_cvt=True 본체):
     모델 = build_cvt23(l_i) · 초기자세 = qpos_from_crank(폐쇄 솔버) ·
     C_CVT 전달손실 qfrc(rtab 전달비) · 게이트 스프링/힙 지지/상승항은 no_cvt판 그대로.
     l_i는 0.05mm 양자화 키로 모델/rtab/settle 캐시 (t0wc_liopt 정정 노트와 동일 근거 —
     크랭크 지오메트리는 빌드 시 굳으므로 l_i 연속축은 격자 모델로 실현).
  2. l_i-조건부 정책: 에피소드마다 l_i ~ U[15,30]mm 샘플(reset) → obs 8축째 =
     (l_i−22.5)/7.5 ∈ [−1,1]. li_fixed 인자로 고정 모드 (평가/골든/롤아웃용).
  3. 관절 종료조건 q2측 = 크랭크 qm ∈ [QM_LB, QM_UB] (t0_spec cvt=True 규약;
     q1은 no_cvt판과 동일). knee 채널 = 크랭크(모터측) — 측정 규약과 동일.
  4. 시작 자세 = task0 웅크림 (q1=-0.32, qm=-2.50) settle — no_cvt판 규약의 좌표를
     크랭크로 해석 (QM 바운드 [−2.95,−0.05] 내부). settle은 CVT 체인 전 층 활성.
  5. reset 노이즈 = (q1, qm) 2축 섭동 → 폐쇄 정합 재투영 (qpos_from_crank) + 전달비
     기반 종속 속도 (dqk=r·dqm, dqpin=∂qpin/∂qm·dqm) — no_cvt판 폐쇄 패턴의 CVT 일반화.
그 외 (v2 러닝맥스 보상 · task0 T-N/dq50/|â|>15 페널티 · 클립 RAW15=25.5810)는
no_cvt판과 동일. env 플래그 4종 + 클립 배선은 t0wc_cma import가 담당 (단일 진입점).

골든 (run_golden — 학습/롤아웃 진입 전 필수):
  A: 0429 10 trials canonical a_full23 재생 — 세션평균 dq2 RMSE ≈ 2.6057
     (p24a_crosscheck_ref.oldq.jump_0429, CURRENT_STACK '재생 0429 2.61') — 클립 무관 경로.
  B: 동일 0429 trial을 ① canonical RU.cl_run23(is_cvt=True, l_i=25.08) ② env._layer_step
     경로(PD 드라이버)로 폐루프 구동 → 궤적 비트일치 (목표 max|Δ|=0).
"""
import os
import time

import numpy as np

import t0wc_cma as W          # ★ env 플래그 4종 + 클립(RAW15) + sys.path + setup 재사용
import p23_v6_runners as RU
import p19_run as R19
import t0_spec as T0
import safe
from cvt_core import closure, qpos_from_crank

safe.utf8_console()

# ── 태스크/보상 상수 (t0nc_env와 동일) ──
CTRL_DT = 0.002          # 제어 주기 [s]
EP_T = 0.6               # 에피소드 (horizon) [s]
APEX_W = 5.0
TAU_PEN = 1e-4
SLIP_PEN = 1.0
RANGE_PEN = 0.5
CRASH_PEN = 1.0
GRAV = 9.81
NOISE_Q = 0.005          # reset 관절각 노이즈 std [rad]
NOISE_DQ = 0.05          # reset 관절속도 노이즈 std [rad/s]
GOLDEN_0429 = W.GOLDEN_0429   # 2.6057 — p24a_crosscheck_ref.oldq.jump_0429 (canonical)

# task0 제약 페널티 가중 (t0nc_env와 동일 — t0_spec.penalty 기본값)
W_TN = float(os.environ.get("T0_W_TN", 50.0))
W_DQ = float(os.environ.get("T0_W_DQ", 50.0))
W_TAU = float(os.environ.get("T0_W_TAU", 50.0))
M_TN = float(os.environ.get("T0_TN_MARGIN", 0.0))
M_TAU = float(os.environ.get("T0_TAU_MARGIN", 0.0))
CROUCH_T0 = (-0.32, -2.50)   # task0 웅크림 (q1, 크랭크 qm) — no_cvt판 규약 좌표

# ── l_i-조건부 상수 ──
LI_LB_MM, LI_UB_MM = 15.0, 30.0   # 학습 샘플링 범위 (사용자 지시: U[15,30]mm)
LI_Q_MM = 0.05                    # 모델/rtab/settle 캐시 양자화 [mm] (t0wc_liopt 규약)
LI_FIT_MM = 25.08                 # CVT 층 fit 검증점 (0429) — l_i<25.08 = 외삽
LI_MID, LI_HALF = 22.5, 7.5       # obs 정규화: (l_i−22.5)/7.5 ∈ [−1,1]


def quant_mm(li_mm):
    """0.05mm 격자 양자화 + fit 앵커(25.08) 스냅 (t0wc_liopt.quant_mm 규약, 범위 [15,30])."""
    li_mm = float(np.clip(li_mm, LI_LB_MM, LI_UB_MM))
    if abs(li_mm - LI_FIT_MM) <= LI_Q_MM / 2:
        return LI_FIT_MM
    return float(np.clip(round(round(li_mm / LI_Q_MM) * LI_Q_MM, 5),
                         LI_LB_MM, LI_UB_MM))


def li_m(li_mm):
    """양자화 l_i [mm] → 모델 키 [m] (t0wc_cma.model_cvt 키 규약 round 6)."""
    return round(quant_mm(li_mm) / 1000.0, 6)


def setup():
    W.setup()


_SETTLE = {}   # (l_i키[mm], q1_0, q2_0) → (qpos, qvel, warmstart, c1f, c2f) — 전 env 공유

# 장기 캠페인(BC 워밍스타트) 티처 crouch 주입 훅: li_mm → (q1_0, qm_0). None이면 CROUCH_T0.
# (t0_spec 규약상 시작 자세는 바운드 내 자유 = 최적화 대상 — CMA 최적 crouch 사용은 합법)
CROUCH_FN = None


def _crouch_of(li_mm):
    return CROUCH_FN(li_mm) if CROUCH_FN is not None else CROUCH_T0


class JumpEnv:
    """gymnasium-스타일 (reset/step) CVT 점프 환경 — 플랜트 스텝은 cl_run23(is_cvt) 미러.

    obs (8,): [(bz−0.6)/0.4, q1/1.5, qm/1.5, dq1/10, dqm/10, vbz/3, t/EP_T, (l_i−22.5)/7.5]
    action (2,): 정규화 raw 토크 명령 [−1,1] → ×R19.CLIP (tm 필터+클립+ahat 체인 통과)
    q2 채널 = 크랭크(모터측) qm — t0_spec cvt=True 규약 (바운드 QM_LB/QM_UB).
    """

    OBS_DIM = 8
    ACT_DIM = 2

    def __init__(self, seed=0, reset_noise=True, li_fixed=None, ctrl_dt=None):
        """ctrl_dt: 액션 주기 [s] (기본 CTRL_DT=2ms). 이산화 프로브(1ms/0.5ms)용 —
        물리 dt(0.5ms)는 불변, 액션-물리 substep 비율만 변경. 스텝 페널티 정규화는
        n_ep·nsub = EP_T/dt 로 ctrl_dt 불변."""
        setup()
        self.mj = W.G["mj"]
        self.A = W.G["A"]
        self.law = W.G["LAW"]
        self.kr = W.G["KR"]
        self.c_cvt = W.G["C_CVT"]
        self.rng = np.random.default_rng(seed)
        self.reset_noise = reset_noise
        self.li_fixed = li_fixed
        self._cache = {}          # l_i키 → (l_i, model, md, sprm, qg, rg, dof, iq, fg)
        self._key = None
        self.dt = None
        self._bind(quant_mm(li_fixed if li_fixed is not None else LI_FIT_MM))
        self.dt = float(self.model.opt.timestep)
        self.ctrl_dt = float(ctrl_dt) if ctrl_dt else CTRL_DT
        self.nsub = int(round(self.ctrl_dt / self.dt))
        assert abs(self.nsub * self.dt - self.ctrl_dt) < 1e-12, "ctrl_dt가 트윈 dt 배수 아님"
        self.n_ep = int(round(EP_T / self.ctrl_dt))
        self.al = self.dt / max(W.G["TM"], self.dt)     # == cl_run23 al
        self.c1f = self.c2f = 0.0

    # ── l_i 바인드 (키별 1회: 모델/rtab은 W.model_cvt 전역 캐시, MjData는 env별) ──
    def _bind(self, li_mm):
        key = li_mm
        if key == self._key:
            return
        if key not in self._cache:
            l_i = li_m(key)
            model, sprm, (qg, rg) = W.model_cvt(l_i)
            if self.c_cvt <= 0:
                qg = rg = None
            if self.dt is not None:
                assert abs(float(model.opt.timestep) - self.dt) < 1e-15, "l_i별 dt 불일치"
            self._cache[key] = (
                l_i, model, self.mj.MjData(model), sprm, qg, rg,
                safe.dofadr(model, "knee", self.mj), safe.qadr(model, "knee", self.mj),
                self.mj.mj_name2id(model, self.mj.mjtObj.mjOBJ_GEOM, "foot"))
        (self.l_i, self.model, self.md, self.sprm, self.qg, self.rg,
         self.dof_knee, self.iq_k, self.fg) = self._cache[key]
        self.li_mm = key
        self._key = key

    # ── 상태 읽기 (측정 좌표 — cl_run23 루프 상단과 동일; q2 = 크랭크) ──
    def _read(self):
        md = self.md
        return (-md.qpos[1] - np.pi / 2, -md.qpos[2], -md.qvel[1], -md.qvel[2])

    # ── cl_run23(is_cvt=True) 스텝 본체 미러 (명령 계산부 이후 전부) ──
    def _layer_step(self, c1, c2, v1c, v2c, settle):
        P = W.G["P"]
        if settle:
            self.c1f, self.c2f = c1, c2
        else:
            self.c1f += self.al * (c1 - self.c1f)
            self.c2f += self.al * (c2 - self.c2f)
            c1, c2 = self.c1f, self.c2f
        c1 = float(np.clip(c1, -R19.CLIP, R19.CLIP))
        c2 = float(np.clip(c2, -R19.CLIP, R19.CLIP))
        s1 = float(P.J.ahat(self.A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(self.A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, *self.law)
        if self.kr:
            supp += float(RU.rise_term(v2c, self.kr, self.law[2]))
        tql = 0.0
        if self.qg is not None:                       # ★ C_CVT 전달손실 (CVT 한정 가지)
            rr = float(np.interp(self.md.qpos[2], self.qg, self.rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(self.md.qvel[self.dof_knee])
            tql = -self.c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
        if self.sprm is not None:
            tql += RU.spr_tau(float(self.md.qpos[self.iq_k]), abs(s2), self.sprm)
        if RU.HIP_LAW:
            self.md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        else:
            self.md.ctrl[:] = [-s1, -(s2 + supp)]
        self.md.qfrc_applied[self.dof_knee] = tql
        try:
            self.mj.mj_step(self.model, self.md)
        except Exception:
            return None
        if abs(self.md.qpos[0]) > 5 or not np.isfinite(self.md.qpos).all():
            return None
        return s1, s2, c1, c2

    # ── 초기 자세 + settle (cl_run23 is_cvt=True 초기화 규약 그대로) ──
    def _init_pose(self, q1_0, q2_0):
        md, mj = self.md, self.mj
        sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, self.l_i)[0]
        md.qvel[:] = 0
        mj.mj_forward(self.model, md)
        md.qpos[0] = 1.0 - float(md.geom_xpos[self.fg][2]) + W.G["S"].FOOT_RADIUS
        md.qvel[:] = 0
        mj.mj_forward(self.model, md)
        self.c1f = self.c2f = 0.0

    def _settle(self, q1_0, q2_0):
        S = W.G["S"]
        self._init_pose(q1_0, q2_0)
        n_set = int(round(W.G["P"].J.T_SETTLE / self.dt))
        for _ in range(n_set):
            q1c, q2c, v1c, v2c = self._read()
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            if self._layer_step(c1, c2, v1c, v2c, settle=True) is None:
                raise RuntimeError(f"settle 발산 (l_i={self.li_mm}mm) — 모델/후보 배선 확인")

    def _settled(self):
        """현 (l_i키, crouch)의 settle 상태 (전역 캐시 — 결정론이라 env 간 공유 가능)."""
        q0 = _crouch_of(self.li_mm)
        key = (self.li_mm, round(q0[0], 6), round(q0[1], 6))
        if key not in _SETTLE:
            self._settle(*q0)
            _SETTLE[key] = (self.md.qpos.copy(), self.md.qvel.copy(),
                            self.md.qacc_warmstart.copy(), self.c1f, self.c2f)
        return _SETTLE[key]

    def _obs(self):
        q1c, q2c, v1c, v2c = self._read()
        md = self.md
        return np.array([(md.qpos[0] - 0.6) / 0.4, q1c / 1.5, q2c / 1.5,
                         v1c / 10.0, v2c / 10.0, md.qvel[0] / 3.0,
                         self.k / self.n_ep, (self.li_mm - LI_MID) / LI_HALF],
                        dtype=np.float32)

    def reset(self):
        li = quant_mm(self.li_fixed) if self.li_fixed is not None else \
            quant_mm(self.rng.uniform(LI_LB_MM, LI_UB_MM))
        self._bind(li)
        qp, qv, warm, c1f, c2f = self._settled()
        md = self.md
        md.qpos[:] = qp
        md.qvel[:] = qv
        md.qacc_warmstart[:] = warm
        self.c1f, self.c2f = c1f, c2f
        if self.reset_noise:
            n1, n2 = self.rng.normal(0.0, NOISE_Q, 2)
            m1, m2 = self.rng.normal(0.0, NOISE_DQ, 2)
            # 폐쇄 정합 노이즈: (q1, qm) 섭동 → qpos_from_crank 재투영 + 전달비 종속 속도
            qc = float(md.qpos[2]) + n2
            md.qpos[:] = qpos_from_crank(float(md.qpos[0]), float(md.qpos[1]) + n1,
                                         qc, self.l_i, float(md.qpos[4]))[0]
            qk1, pin1, _ = closure(qc, self.l_i, float(md.qpos[4]))
            qk2, pin2, _ = closure(qc + 1e-4, self.l_i, qk1)
            dpin = ((pin2 - pin1 + np.pi) % (2 * np.pi) - np.pi) / 1e-4
            dqk = (qk2 - qk1) / 1e-4
            md.qvel[1] += m1
            md.qvel[2] += m2; md.qvel[3] += dpin * m2; md.qvel[4] += dqk * m2
        self.mj.mj_forward(self.model, md)
        self.k = 0
        self.bz0 = float(md.qpos[0])
        self.prev_bz = self.bz0
        self.apex = self.bz0
        self.prev_fx = float(md.geom_xpos[self.fg][0])
        self.slip_total = 0.0
        self.contact_prev = True
        self.n_bounce = 0        # 공중 → 재접촉 횟수 (바운스 착취 감시)
        self.sat_steps = 0       # |명령| ≥ 0.95·CLIP 이었던 제어스텝 수
        self.ep_steps = 0
        self.pen_total = 0.0     # task0 T-N/dq50/|â|>15 페널티 누계
        self.tn_viol_sub = 0
        self.dq_viol_sub = 0
        self.tau_viol_sub = 0
        self.n_sub_done = 0
        return self._obs()

    def step(self, a):
        """a: (2,) 정규화 [−1,1] — ZOH로 nsub 서브스텝 유지 (필터/ahat/층은 매 서브스텝).
        task0 페널티/보상/종료 = t0nc_env와 동일, q2 바운드만 크랭크 QM (cvt=True 규약)."""
        a = np.clip(np.asarray(a, dtype=np.float64), -1.0, 1.0)
        c1_cmd, c2_cmd = float(a[0]) * R19.CLIP, float(a[1]) * R19.CLIP
        crash = False
        pen = 0.0
        for _ in range(self.nsub):
            q1c, q2c, v1c, v2c = self._read()
            r = self._layer_step(c1_cmd, c2_cmd, v1c, v2c, settle=False)
            if r is None:
                crash = True
                break
            s1, s2 = r[0], r[1]
            _, _, w1, w2 = self._read()          # 포스트스텝 dq (감사와 동일 표본)
            g1 = abs(w1) - (T0.TN_COEF * abs(s1) + T0.TN_OFF - M_TN)
            g2 = abs(w2) - (T0.TN_COEF * abs(s2) + T0.TN_OFF - M_TN)
            d1 = abs(w1) - T0.DQ_LIM
            d2 = abs(w2) - T0.DQ_LIM
            e1 = abs(s1) - (15.0 - M_TAU)
            e2 = abs(s2) - (15.0 - M_TAU)
            if g1 > 0 or g2 > 0:
                self.tn_viol_sub += 1
            if d1 > 0 or d2 > 0:
                self.dq_viol_sub += 1
            if e1 > 0 or e2 > 0:
                self.tau_viol_sub += 1
            pen += W_TN * (max(g1, 0.0) ** 2 + max(g2, 0.0) ** 2) \
                + W_DQ * (max(d1, 0.0) ** 2 + max(d2, 0.0) ** 2) \
                + W_TAU * (max(e1, 0.0) ** 2 + max(e2, 0.0) ** 2)
            self.n_sub_done += 1
        pen /= (self.n_ep * self.nsub)
        self.pen_total += pen
        self.k += 1
        self.ep_steps += 1
        md = self.md
        bz = float(md.qpos[0])
        old_apex = self.apex
        self.apex = max(self.apex, bz)
        rew = APEX_W * (self.apex - old_apex)          # 러닝맥스 증분 (v2)
        self.prev_bz = bz
        rew -= TAU_PEN * (abs(float(a[0])) + abs(float(a[1])))
        rew -= pen                                     # task0 소프트 제약
        if max(abs(c1_cmd), abs(c2_cmd)) >= 0.95 * R19.CLIP:
            self.sat_steps += 1
        in_contact = md.ncon > 0
        fx = float(md.geom_xpos[self.fg][0])
        if in_contact and self.contact_prev:
            slip = abs(fx - self.prev_fx)
            rew -= SLIP_PEN * slip
            self.slip_total += slip
        if in_contact and not self.contact_prev:
            self.n_bounce += 1
        self.contact_prev = in_contact
        self.prev_fx = fx
        done = False
        info = {}
        if crash:
            rew -= CRASH_PEN
            done = True
            info["crash"] = True
        else:
            q1c, q2c, _, _ = self._read()
            if not (T0.Q1_LB <= q1c <= T0.Q1_UB) or \
               not (T0.QM_LB <= q2c <= T0.QM_UB):
                rew -= RANGE_PEN
                done = True
                info["range"] = True
        if not done and self.k >= self.n_ep:
            done = True
            vbz = float(md.qvel[0])
            apex_est = max(self.apex, bz + max(vbz, 0.0) ** 2 / (2 * GRAV))
            rew += APEX_W * max(0.0, apex_est - self.apex)   # 탄도 외삽분만 가산
            info["apex_est"] = apex_est
        if done:
            info["apex_obs"] = self.apex
            info["slip_total"] = self.slip_total
            info["n_bounce"] = self.n_bounce
            info["sat_frac"] = self.sat_steps / max(self.ep_steps, 1)
            info["pen_total"] = self.pen_total
            info["tn_viol_frac"] = self.tn_viol_sub / max(self.n_sub_done, 1)
            info["dq_viol_frac"] = self.dq_viol_sub / max(self.n_sub_done, 1)
            info["tau_viol_frac"] = self.tau_viol_sub / max(self.n_sub_done, 1)
            info["li_mm"] = self.li_mm
        return self._obs(), float(rew), done, info


# ══════════════════ 골든 체크 ══════════════════
def golden_replay():
    """A: 0429 10 trials를 canonical a_full23(측정 토크 개루프 재생, QOFF_A429)로 —
    세션평균 dq2 RMSE ≈ 2.6057 재현 → CVT 모델/후보/층 배선 검증 (클립 무관 경로).
    t0wc_cma.golden ①과 동일 경로/기준."""
    setup()
    model_a, _, _ = W.model_cvt(li_m(LI_FIT_MM))
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in W.G["TR429"]:
        o1, o2 = W.E.QOFF_A429
        res = RU.a_full23(model_a, True, d["l_i"], d, W.G["LAW"], o1, o2,
                          c_cvt=W.G["C_CVT"], spr=W.G["SPR"], k_rise=W.G["KR"])
        rows.append((str(sub), float(res[0]) if res else 9.9))
        print(f"  golden A — 0429/{str(sub):16s}: dq2 RMSE={rows[-1][1]:.4f}", flush=True)
    mean = float(np.mean([r[1] for r in rows]))
    ok = abs(mean - GOLDEN_0429) < 0.05
    print(f"  golden A — session mean {mean:.4f} (canonical {GOLDEN_0429}) "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    return ok, mean, rows


def golden_cl(tr_idx=0):
    """B: 동일 0429 trial을 ① canonical RU.cl_run23(is_cvt=True, l_i=25.08)
    ② env._layer_step 경로(PD 드라이버)로 각각 폐루프 구동 → 궤적 비트일치
    (목표 max|Δ|=0) → env CVT 스텝 코드 검증. 양쪽 모두 R19.CLIP(=25.5810)을
    호출 시점에 읽으므로 task0 클립 하 재검증이 됨 (t0nc_env.golden_cl의 CVT판)."""
    setup()
    P = W.G["P"]
    ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i = W.G["TR429"][tr_idx]
    alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
    o1, o2 = W.G["QOFF_CL429"]
    model_c, _, _ = W.model_cvt(li_m(LI_FIT_MM))
    ref = RU.cl_run23(model_c, True, li_m(LI_FIT_MM), d, gains, dqon, ffk, W.G["A"],
                      W.G["TM"], alphas, W.G["LAW"], c_cvt=W.G["C_CVT"],
                      o1=o1, o2=o2, spr=W.G["SPR"], k_rise=W.G["KR"])
    assert ref is not None, "cl_run23 발산"
    # env 경로 — cl_run23의 명령 계산부를 그대로 재현하며 _layer_step 사용
    env = JumpEnv(reset_noise=False, li_fixed=LI_FIT_MM)
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"] + o1; qd2 = d["qd2"] + o2
    dqd1 = d["dqd1"] if dqon else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqon else np.zeros_like(t)
    env._init_pose(float(qd1[0]), float(qd2[0]))
    dt = env.dt
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    S = W.G["S"]
    q2a = np.zeros(N); dq2a = np.zeros(N); bza = np.zeros(N)
    sh1 = np.zeros(N); sh2 = np.zeros(N)
    for k in range(N):
        tc = tl[k]
        q1c, q2c, v1c, v2c = env._read()
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2[0] - q2c) - S.SETTLE_KD * v2c
            r = env._layer_step(c1, c2, v1c, v2c, settle=True)
        else:
            tm_ = min(tc, t[-1])
            c1 = kp1 * (np.interp(tm_, t, qd1) - q1c) + kd1 * (np.interp(tm_, t, dqd1) - v1c)
            c2 = kp2 * (np.interp(tm_, t, qd2) - q2c) + kd2 * (np.interp(tm_, t, dqd2) - v2c)
            if ffk:
                c2 += np.interp(tm_, t, d["tdes2"])
            r = env._layer_step(c1, c2, v1c, v2c, settle=False)
        assert r is not None, f"env 경로 발산 k={k}"
        s1, s2, _, _ = r
        q1c, q2c, v1c, v2c = env._read()
        q2a[k] = q2c; dq2a[k] = v2c; bza[k] = env.md.qpos[0]
        sh1[k] = s1; sh2[k] = s2
    dmax = max(float(np.abs(q2a - ref["q2"]).max()),
               float(np.abs(dq2a - ref["dq2"]).max()),
               float(np.abs(bza - ref["bz"]).max()),
               float(np.abs(sh1 - ref["sh1"]).max()),
               float(np.abs(sh2 - ref["sh2"]).max()))
    ok = dmax < 1e-12
    print(f"  golden B — 0429/{sub} env vs cl_run23(is_cvt, l_i=25.08, clip={R19.CLIP}) "
          f"max|Δ|={dmax:.3e} {'PASS' if ok else 'FAIL'}", flush=True)
    return ok, dmax


def run_golden():
    okA, meanA, _ = golden_replay()
    okB, dmaxB = golden_cl(0)
    if not (okA and okB):
        raise SystemExit("GOLDEN FAIL — 학습 진입 금지")
    print(f"GOLDEN PASS (A: 0429 재생 세션평균 / B: env CVT 스텝 비트일치, "
          f"clip={R19.CLIP})", flush=True)
    return dict(golden_A_mean=meanA, golden_A_canonical=GOLDEN_0429,
                golden_B_maxdiff=dmaxB, clip_raw=float(R19.CLIP),
                golden_li_mm=LI_FIT_MM)


if __name__ == "__main__":
    t0 = time.time()
    run_golden()
    # 부가 스모크: l_i 격자 끝단 settle/에피소드 + 모델 빌드 시간 계측
    for li in (15.0, 20.0, 30.0):
        t1 = time.time()
        e = JumpEnv(seed=1, reset_noise=True, li_fixed=li)
        o = e.reset()
        n = 0
        done = False
        while not done:
            o, r, done, info = e.step(np.array([0.3, -0.5]))
            n += 1
        print(f"  smoke l_i={li}mm: build+settle+ep({n} steps) {time.time() - t1:.2f}s "
              f"apex={info.get('apex_obs', float('nan')):.3f} "
              f"end={'crash' if info.get('crash') else ('range' if info.get('range') else 'T')}",
              flush=True)
    print(f"total {time.time() - t0:.0f}s", flush=True)
