# -*- coding: utf-8 -*-
"""p25_c_env — P25 Phase C: PPO 파일럿용 점프 환경 (p24a 트윈 전 층 미러).

플랜트 = 승격 p24a 후보 (fourbar_p24a_candidate.json) + p23_v6_runners 전 층:
  ahat(Paper) 변환 · 측정 지지법칙 supp · Phase 4c 상승항 K_RISE · Phase 4b 게이트 스프링 ·
  P24 힙 부하-지지층 (HIP_LAW) · 커맨드층 (tm 1차 지연 + 클립 ±R19.CLIP).
env 플래그 4종은 import 전에 강제 (p24a_all_results.py 규약 그대로).
공급 클립은 env 변수 P25_CLIP_RAW로 재정의 (기본 = R19.CLIP = 35.5, 무설정 시 기존 동작
완전 보존). 18Nm 캠페인: 31.1771 (a_hat 운동방향 가지 정확히 18.00Nm — p25_d_deploy 규약).
env·cl_run23 모두 R19.CLIP을 호출 시점에 읽으므로 monkeypatch 한 곳으로 전 경로 일관.

미러 원칙: JumpEnv._layer_step()은 cl_run23의 스텝 본체를 문자 그대로 복제
(PD 명령 계산부만 정책 액션으로 대체). golden_cl()이 이를 비트 수준으로 검증:
동일 0602 trial을 cl_run23와 env 경로로 각각 폐루프 구동 → 궤적 max|Δ| ≈ 0.

태스크 (MARATHON_p25 공통 고정): 수직 최대 점프, 시작 = 0602 웅크림(qd(0), settle 0.4s),
l_i=30 flip 모델, horizon 0.6s, 제어 dt 2ms (트윈 dt 서브스텝), 공급 천장 raw ±R19.CLIP,
관절 범위 = 0602 실측 방문 범위 +10% 마진, 발 미끄럼 감시 (관측/페널티).

보상 (문서화 — p25_c_results.json에도 기록; v2 2026-07-17):
  r_t = APEX_W·Δ(running max bz)   (러닝맥스 증분 — 합계가 정확히 APEX_W·(apex − bz0).
        v1의 Δbz shaping은 에피소드 내 착지 시 상승분이 상쇄되어 신호가 종단 보너스로만
        남는 문제 → 러닝맥스 증분으로 교체. 단조 증가라 바운스가 보상받을 여지도 없음)
        − TAU_PEN·(|a1|+|a2|)  (정규화 액션, 토크 절약 소항)
        − SLIP_PEN·|Δfoot_x|   (접촉 중 발 미끄럼 — 이지 전 미끄럼 금지 제약의 연속 완화)
  종단(정상 종료): + APEX_W·max(0, 탄도외삽 apex − running max)
        탄도외삽 = bz_T + max(vbz_T,0)²/(2g)  (apex가 horizon 밖일 때의 학습용 저가 추정.
        최종 보고 h_plan은 rollout 스크립트가 수동 연장 0.6s로 실측)
  관절범위 이탈: 종료 + RANGE_PEN / 발산: 종료 + CRASH_PEN.
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

# P25_CLIP_RAW → 공급 클립 재정의 (raw 도메인; 무설정 시 R19.CLIP=35.5 그대로 = 기존 동작).
# cl_run23(p23_v6_runners)과 본 env의 _layer_step/액션 스케일/sat 감시 전부 R19.CLIP을
# 호출 시점에 읽음 → 이 한 곳이 유일한 진입점. 18Nm 캠페인: 31.1771 (p25_d_deploy 동일 규약).
if os.environ.get("P25_CLIP_RAW"):
    R19.CLIP = float(os.environ["P25_CLIP_RAW"])

assert RU.SPRING_GATED and RU.RISE_GATED and RU.HIP_LAW and RU.P24_REFIT, \
    "p24a 구조 플래그 불일치 (env 강제 실패)"

CAND = json.load(open(PV / "fourbar_p24a_candidate.json", encoding="utf-8"))

# ── 태스크/보상 상수 (Phase C 파일럿 — 선고정, 결과 json에 기록) ──
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

G = {}


def setup():
    """winit+fix0421 1회 → 후보 벡터/모델/0602 웅크림/관절범위 전역 확정
    (p24a_all_results.setup과 동일 순서)."""
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
    assert trs602, "jump_0602 trials 없음"
    d0 = trs602[0][2]
    # 관절 범위: 0602 실측 방문 범위 +10% 마진 (MARATHON 태스크 정의)
    q1s = np.concatenate([tr[2]["q1"] for tr in trs602])
    q2s = np.concatenate([tr[2]["q2"] for tr in trs602])
    s1r, s2r = q1s.max() - q1s.min(), q2s.max() - q2s.min()
    G.update(ready=True, P=P, mj=RU.C._W["mj"], S=P.J._P["S"], A=P.A_PAPER,
             V=v, X32=x32, SP=sp, REF=float(v[1]), TM=float(v[14]),
             LAW=RU.law_of(v), SPR=RU.spr_of(v), D_DQ=float(v[21]),
             KR=RU.rise_of(float(v[21])), model=model,
             TR602=trs602, CROUCH=(float(d0["qd1"][0]), float(d0["qd2"][0])),
             CROUCH_SUB=str(trs602[0][1]),
             Q1R=(q1s.min() - 0.1 * s1r, q1s.max() + 0.1 * s1r),
             Q2R=(q2s.min() - 0.1 * s2r, q2s.max() + 0.1 * s2r))
    print(f"setup done [{time.time() - t0:.0f}s] — dt={model.opt.timestep} "
          f"law={tuple(round(x, 4) for x in G['LAW'])} spr={tuple(round(x, 4) for x in G['SPR'])} "
          f"k_rise={G['KR']:.4f} tm={G['TM'] * 1000:.2f}ms "
          f"crouch(sub={G['CROUCH_SUB']})=({G['CROUCH'][0]:.4f},{G['CROUCH'][1]:.4f}) "
          f"Q1R=({G['Q1R'][0]:.3f},{G['Q1R'][1]:.3f}) Q2R=({G['Q2R'][0]:.3f},{G['Q2R'][1]:.3f})",
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
        return self._obs()

    def step(self, a):
        """a: (2,) 정규화 [−1,1] — ZOH로 nsub 서브스텝 유지 (필터/ahat/층은 매 서브스텝)."""
        a = np.clip(np.asarray(a, dtype=np.float64), -1.0, 1.0)
        c1_cmd, c2_cmd = float(a[0]) * R19.CLIP, float(a[1]) * R19.CLIP
        crash = False
        for _ in range(self.nsub):
            q1c, q2c, v1c, v2c = self._read()
            if self._layer_step(c1_cmd, c2_cmd, v1c, v2c, settle=False) is None:
                crash = True
                break
        self.k += 1
        self.ep_steps += 1
        md = self.md
        bz = float(md.qpos[0])
        old_apex = self.apex
        self.apex = max(self.apex, bz)
        rew = APEX_W * (self.apex - old_apex)          # 러닝맥스 증분 (v2)
        self.prev_bz = bz
        rew -= TAU_PEN * (abs(float(a[0])) + abs(float(a[1])))
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
        return self._obs(), float(rew), done, info


# ══════════════════ 골든 체크 ══════════════════
def golden_replay():
    """A: 0602 3 trials를 canonical a_full23(측정 토크 개루프 재생)로 — 세션평균 dq2 RMSE
    ≈ 1.2851 (p24a_crosscheck_ref) 재현 → 모델/후보/층 배선 검증."""
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
    각각 폐루프 구동 → 궤적 비트 일치 (max|Δ| < 1e-9) → env 스텝 코드 검증."""
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
    print(f"  golden B — 0602/{sub} env vs cl_run23 max|Δ|={dmax:.3e} "
          f"{'PASS' if ok else 'FAIL'}")
    return ok, dmax


def run_golden():
    okA, meanA, _ = golden_replay()
    okB, dmaxB = golden_cl(0)
    if not (okA and okB):
        raise SystemExit("GOLDEN FAIL — 학습 진입 금지")
    print("GOLDEN PASS (A: 0602 재생 세션평균 / B: env 스텝 비트 일치)")
    return dict(golden_A_mean=meanA, golden_A_canonical=GOLDEN_OLDQ_0602,
                golden_B_maxdiff=dmaxB)


if __name__ == "__main__":
    run_golden()
