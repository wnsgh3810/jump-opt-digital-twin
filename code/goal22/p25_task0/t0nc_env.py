# -*- coding: utf-8 -*-
"""t0nc_env — P25-task0 캠페인: task0(no_cvt) 제약판 점프 환경 (p25_c_env.py 사본 수정).

원본: ../p25_deploy/p25_c_env.py (P25 Phase C — 트윈 전 층 미러, 골든 A/B 체크 동일).
변경점 (P25-task0, 사용자 지시 07-18 — 제약은 AVT LEG task0 스크립트 = t0_spec 기준):
  1. 공급 클립 기본값 = t0_spec.RAW15 = 25.5810 (a_hat 운동방향 가지 정확히 15.00 Nm
     — 토크 제약 |â|≤15의 raw 도메인 등가 박스; env 변수 P25_CLIP_RAW로 재정의 가능).
  2. 관절범위 종료조건 = task0 바운드 (q1∈[-1.2566,-0.2967], q2∈[-2.5482,-0.6283])
     — 기존 "0602 방문 +10%" 범위 대체 (setup에서 G["Q1R"]/G["Q2R"] 자체를 교체).
  3. 모터 T-N 포락선(|dq| ≤ -0.731·|â|+48.48)·|dq|≤50 위반 = 보상 페널티
     (t0_spec.penalty와 동일 정의: 스텝(서브스텝 표본)당 위반량² × w=50,
      에피소드 합계가 t0_spec.penalty의 창 평균 규모와 일치하도록 표본수로 정규화).
     가중은 T0_W_TN/T0_W_DQ env 변수로 상향 가능 (감사 실패 시 재학습 경로).
  3b. |â|>15 위반도 같은 형식의 페널티 (W_TAU). 근거 (07-18 측정): 클립 25.5810은
     운동방향(모터링) 가지에서만 â=15.00 — dq≈0에서 16.17, 제동 가지에서 17.34 Nm까지
     나옴 → 클립만으로는 감사 항목 tau_hip/tau_knee(≤15) 보장 불가. 페널티가 정지/제동
     영역에서 천장 명령을 스스로 낮추도록 유도 (모터링 중 15Nm 풀 사용은 그대로 허용).
  3c. T0_TN_MARGIN/T0_TAU_MARGIN: 페널티 기준선을 한계보다 안쪽으로 당기는 여유
     (기본 0 = t0_spec 문자 그대로). 이차 페널티는 최적점이 한계 살짝 밖에 앉는 성질이
     있어, 감사(허용오차 1e-6) 실패 시 가중 상향과 함께 쓰는 재학습 노브.
  4. 시작 자세 = task0 웅크림 (q1=-0.32, q2=-2.50) settle — 0602 웅크림 대체
     (G["CROUCH"] 교체; settle/reset 로직은 원본 그대로).
그 외 (플랜트 층 _layer_step 미러 · v2 러닝맥스 보상 · 골든 A/B)는 원본과 동일.
골든 B는 clip=25.5810 하에서 env 경로 vs cl_run23(R19.CLIP 동일 monkeypatch)
비트일치를 재검증한다 (양쪽 모두 R19.CLIP을 호출 시점에 읽으므로 한 곳 재정의로 일관).
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
# ★ 구조 플래그는 p23 모듈 import 전에 env로 강제 (import 시점에 벡터 축수 결정)
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_HIP_LAW"] = "1"
os.environ["P24_REFIT"] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
PV = HERE.parent / "p23_veins"
sys.path.insert(0, str(PV))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import p23_v6_runners as RU
import p19_run as R19
import t0_spec as T0

# P25-task0 기본 클립 = RAW15 (25.5810). P25_CLIP_RAW로 재정의 가능하나 본 캠페인은
# 기본값 사용. env·cl_run23 모두 R19.CLIP을 호출 시점에 읽음 → 이 한 곳이 유일한 진입점.
os.environ.setdefault("P25_CLIP_RAW", repr(T0.RAW15))
if os.environ.get("P25_CLIP_RAW"):
    R19.CLIP = float(os.environ["P25_CLIP_RAW"])

assert RU.SPRING_GATED and RU.RISE_GATED and RU.HIP_LAW and RU.P24_REFIT, \
    "p24a 구조 플래그 불일치 (env 강제 실패)"

CAND = json.load(open(PV / "fourbar_p24a_candidate.json", encoding="utf-8"))

# ── 태스크/보상 상수 (Phase C 선고정값 유지 + task0 페널티 가중) ──
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
GOLDEN_OLDQ_0602 = 1.2851   # p24a_crosscheck_ref.json oldq.jump_0602 (canonical)

# task0 제약 페널티 가중 (t0_spec.penalty 기본값; 감사 실패 시 env 변수로 상향 재학습)
W_TN = float(os.environ.get("T0_W_TN", 50.0))
W_DQ = float(os.environ.get("T0_W_DQ", 50.0))
W_TAU = float(os.environ.get("T0_W_TAU", 50.0))     # |â|>15 페널티 (docstring 3b)
M_TN = float(os.environ.get("T0_TN_MARGIN", 0.0))   # 페널티 기준선 여유 [rad/s]
M_TAU = float(os.environ.get("T0_TAU_MARGIN", 0.0))  # 페널티 기준선 여유 [Nm]
CROUCH_T0 = (-0.32, -2.50)   # task0 초기추정 웅크림 (task0 set_initial 시작점)

G = {}


def setup():
    """winit+fix0421 1회 → 후보 벡터/모델/task0 웅크림·관절범위 전역 확정
    (p24a_all_results.setup과 동일 순서; CROUCH/Q1R/Q2R만 task0으로 교체)."""
    if G.get("ready"):
        return
    t0 = time.time()
    RU.ensure_init()
    P = RU.C._W["P"]
    v = RU.apply_freeze(RU.pad23(np.asarray(CAND["x"], float)))
    x32, sp = RU.C.x32_of(v[:20])
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()      # ★ 반드시 fix0421 이후 (ensure_init가 보장)
    model = RU.build_flip23(x32, float(v[1]), sp, float(v[21]))
    trs602 = [tr for tr in R19.TRIALS if tr[0] == "jump_0602"]
    assert trs602, "jump_0602 trials 없음"   # 골든 A/B 전용 (시작자세로는 미사용)
    G.update(ready=True, P=P, mj=RU.C._W["mj"], S=P.J._P["S"], A=P.A_PAPER,
             V=v, X32=x32, SP=sp, REF=float(v[1]), TM=float(v[14]),
             LAW=RU.law_of(v), SPR=RU.spr_of(v), D_DQ=float(v[21]),
             KR=RU.rise_of(float(v[21])), model=model,
             TR602=trs602, CROUCH=CROUCH_T0, CROUCH_SUB="task0",
             Q1R=(T0.Q1_LB, T0.Q1_UB), Q2R=(T0.Q2_LB, T0.Q2_UB))
    print(f"setup done [{time.time() - t0:.0f}s] — dt={model.opt.timestep} "
          f"law={tuple(round(x, 4) for x in G['LAW'])} spr={tuple(round(x, 4) for x in G['SPR'])} "
          f"k_rise={G['KR']:.4f} tm={G['TM'] * 1000:.2f}ms clip={R19.CLIP} "
          f"crouch(task0)=({G['CROUCH'][0]:.4f},{G['CROUCH'][1]:.4f}) "
          f"Q1R=({G['Q1R'][0]:.4f},{G['Q1R'][1]:.4f}) Q2R=({G['Q2R'][0]:.4f},{G['Q2R'][1]:.4f}) "
          f"w_tn={W_TN} w_dq={W_DQ} w_tau={W_TAU} m_tn={M_TN} m_tau={M_TAU}",
          flush=True)


class JumpEnv:
    """gymnasium-스타일 (reset/step) 점프 환경 — 플랜트 스텝은 cl_run23 본체 미러.

    obs (7,): [(bz−0.6)/0.4, q1/1.5, q2/1.5, dq1/10, dq2/10, vbz/3, t/EP_T]
    action (2,): 정규화 raw 토크 명령 [−1,1] → ×R19.CLIP (tm 필터+클립+ahat 체인 통과)
    """

    OBS_DIM = 7
    ACT_DIM = 2

    def __init__(self, seed=0, reset_noise=True):
        setup()
        self.mj = G["mj"]
        self.model = G["model"]           # 공유 (읽기 전용) — MjData만 개별
        self.md = self.mj.MjData(self.model)
        self.dt = float(self.model.opt.timestep)
        self.nsub = int(round(CTRL_DT / self.dt))
        assert abs(self.nsub * self.dt - CTRL_DT) < 1e-12, "CTRL_DT가 트윈 dt 배수 아님"
        self.n_ep = int(round(EP_T / CTRL_DT))
        self.dof_knee = safe.dofadr(self.model, "knee", self.mj)
        self.iq_k = safe.qadr(self.model, "knee", self.mj)
        self.fg = self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_GEOM, "foot")
        self.sprm = RU.spr_resolve(self.model, G["SPR"])
        self.law = G["LAW"]
        self.kr = G["KR"]
        self.A = G["A"]
        self.al = self.dt / max(G["TM"], self.dt)     # == cl_run23 al
        self.rng = np.random.default_rng(seed)
        self.reset_noise = reset_noise
        self.c1f = self.c2f = 0.0
        self._settle_cache = None

    # ── 상태 읽기 (측정 좌표 — cl_run23 루프 상단과 동일) ──
    def _read(self):
        md = self.md
        return (-md.qpos[1] - np.pi / 2, -md.qpos[2], -md.qvel[1], -md.qvel[2])

    # ── cl_run23 스텝 본체 미러 (명령 계산부 이후 전부) ──
    def _layer_step(self, c1, c2, v1c, v2c, settle):
        P = G["P"]
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
        tql = 0.0                                     # flip(l_i=30): C_CVT 가지 없음
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

    # ── 초기 자세 + settle (cl_run23 초기화 규약 그대로) ──
    def _init_pose(self, q1_0, q2_0):
        md, mj = self.md, self.mj
        sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
        md.qvel[:] = 0
        mj.mj_forward(self.model, md)
        md.qpos[0] = 1.0 - float(md.geom_xpos[self.fg][2]) + G["S"].FOOT_RADIUS
        md.qvel[:] = 0
        mj.mj_forward(self.model, md)
        self.c1f = self.c2f = 0.0

    def _settle(self, q1_0, q2_0):
        S = G["S"]
        self._init_pose(q1_0, q2_0)
        n_set = int(round(G["P"].J.T_SETTLE / self.dt))
        for _ in range(n_set):
            q1c, q2c, v1c, v2c = self._read()
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            if self._layer_step(c1, c2, v1c, v2c, settle=True) is None:
                raise RuntimeError("settle 발산 — 모델/후보 배선 확인")

    def _obs(self):
        q1c, q2c, v1c, v2c = self._read()
        md = self.md
        return np.array([(md.qpos[0] - 0.6) / 0.4, q1c / 1.5, q2c / 1.5,
                         v1c / 10.0, v2c / 10.0, md.qvel[0] / 3.0,
                         self.k / self.n_ep], dtype=np.float32)

    def reset(self):
        if self._settle_cache is None:
            q1_0, q2_0 = G["CROUCH"]
            self._settle(q1_0, q2_0)
            self._settle_cache = (self.md.qpos.copy(), self.md.qvel.copy(),
                                  self.md.qacc_warmstart.copy(), self.c1f, self.c2f)
        qp, qv, warm, c1f, c2f = self._settle_cache
        md = self.md
        md.qpos[:] = qp
        md.qvel[:] = qv
        md.qacc_warmstart[:] = warm
        self.c1f, self.c2f = c1f, c2f
        if self.reset_noise:
            n1, n2 = self.rng.normal(0.0, NOISE_Q, 2)
            m1, m2 = self.rng.normal(0.0, NOISE_DQ, 2)
            md.qpos[1] += n1
            md.qpos[2] += n2; md.qpos[3] -= n2; md.qpos[4] += n2   # 폐쇄 패턴 유지
            md.qvel[1] += m1
            md.qvel[2] += m2; md.qvel[3] -= m2; md.qvel[4] += m2
        self.mj.mj_forward(self.model, md)
        self.k = 0
        self.bz0 = float(md.qpos[0])
        self.prev_bz = self.bz0
        self.apex = self.bz0
        self.prev_fx = float(md.geom_xpos[self.fg][0])
        self.slip_total = 0.0
        self.contact_prev = True
        self.n_bounce = 0        # 공중 → 재접촉 횟수 (바운스 착취 감시)
        self.sat_steps = 0       # |명령| ≥ 0.95·CLIP 이었던 제어스텝 수 (천장 탑승 감시)
        self.ep_steps = 0
        self.pen_total = 0.0     # task0 T-N/dq50/|â|>15 페널티 누계 (t0_spec.penalty 규모)
        self.tn_viol_sub = 0     # T-N 포락선 위반 서브스텝 수 (마진 기준)
        self.dq_viol_sub = 0     # |dq|>50 위반 서브스텝 수
        self.tau_viol_sub = 0    # |â|>15-마진 위반 서브스텝 수
        self.n_sub_done = 0
        return self._obs()

    def step(self, a):
        """a: (2,) 정규화 [−1,1] — ZOH로 nsub 서브스텝 유지 (필터/ahat/층은 매 서브스텝).
        task0 페널티: 서브스텝(포스트스텝 표본 — 감사 로그와 동일)마다 T-N/dq50 위반량²
        누적 → 총 표본수(n_ep·nsub)로 나눠 에피소드 합계가 t0_spec.penalty(창 평균)와
        같은 규모가 되도록."""
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
        rew -= pen                                     # task0 T-N/dq50 소프트 제약
        if max(abs(c1_cmd), abs(c2_cmd)) >= 0.95 * R19.CLIP:
            self.sat_steps += 1
        # 접촉/미끄럼/바운스 감시
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
            if not (G["Q1R"][0] <= q1c <= G["Q1R"][1]) or \
               not (G["Q2R"][0] <= q2c <= G["Q2R"][1]):
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
        return self._obs(), float(rew), done, info


# ══════════════════ 골든 체크 ══════════════════
def golden_replay():
    """A: 0602 3 trials를 canonical a_full23(측정 토크 개루프 재생)로 — 세션평균 dq2 RMSE
    ≈ 1.2851 (p24a_crosscheck_ref) 재현 → 모델/후보/층 배선 검증 (클립 무관 경로)."""
    setup()
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in G["TR602"]:
        res = RU.a_full23(G["model"], False, l_i, d, G["LAW"], 0.0, 0.0,
                          c_cvt=0.0, spr=G["SPR"], k_rise=G["KR"])
        assert res is not None, f"a_full23 발산: {sub}"
        rows.append((str(sub), res[0], res[1]))
        print(f"  golden A — 0602/{sub}: dq2 RMSE={res[0]:.4f} h_sim={res[1]:.4f}")
    mean = float(np.mean([r[1] for r in rows]))
    ok = abs(mean - GOLDEN_OLDQ_0602) < 0.02
    print(f"  golden A — session mean {mean:.4f} (canonical {GOLDEN_OLDQ_0602}) "
          f"{'PASS' if ok else 'FAIL'}")
    return ok, mean, rows


def golden_cl(tr_idx=0):
    """B: 동일 0602 trial을 ① canonical cl_run23 ② env._layer_step 경로(PD 드라이버)로
    각각 폐루프 구동 → 궤적 비트 일치 (max|Δ| < 1e-9) → env 스텝 코드 검증.
    양쪽 모두 R19.CLIP(=25.5810)을 호출 시점에 읽으므로 task0 클립 하 재검증이 됨."""
    setup()
    P = G["P"]
    ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i = G["TR602"][tr_idx]
    alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
    ref = RU.cl_run23(G["model"], False, l_i, d, gains, dqon, ffk, G["A"], G["TM"],
                      alphas, G["LAW"], c_cvt=0.0, o1=0.0, o2=0.0,
                      spr=G["SPR"], k_rise=G["KR"])
    assert ref is not None, "cl_run23 발산"
    # env 경로 — cl_run23의 명령 계산부를 그대로 재현하며 _layer_step 사용
    env = JumpEnv(reset_noise=False)
    t = d["t"]
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    qd1 = d["qd1"]; qd2 = d["qd2"]
    dqd1 = d["dqd1"] if dqon else np.zeros_like(t)
    dqd2 = d["dqd2"] if dqon else np.zeros_like(t)
    env._init_pose(float(qd1[0]), float(qd2[0]))
    dt = env.dt
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    S = G["S"]
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
    ok = dmax < 1e-9
    print(f"  golden B — 0602/{sub} env vs cl_run23 (clip={R19.CLIP}) max|Δ|={dmax:.3e} "
          f"{'PASS' if ok else 'FAIL'}")
    return ok, dmax


def run_golden():
    okA, meanA, _ = golden_replay()
    okB, dmaxB = golden_cl(0)
    if not (okA and okB):
        raise SystemExit("GOLDEN FAIL — 학습 진입 금지")
    print(f"GOLDEN PASS (A: 0602 재생 세션평균 / B: env 스텝 비트 일치, clip={R19.CLIP})")
    return dict(golden_A_mean=meanA, golden_A_canonical=GOLDEN_OLDQ_0602,
                golden_B_maxdiff=dmaxB, clip_raw=float(R19.CLIP))


if __name__ == "__main__":
    run_golden()
