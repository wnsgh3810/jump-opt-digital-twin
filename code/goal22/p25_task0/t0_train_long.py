# -*- coding: utf-8 -*-
"""t0_train_long — P25-task0 스케일업 PPO (코디네이터 지시 07-18: exploration 부족 해소).

사용: python t0_train_long.py nc|wc|wc2 [total_steps]   (출력 접미 _long/_long2 — 기존 불침)

wc2 = CVT 조건부 재시도 (코디 07-18: wc long 퇴행 best 0.663 진단 반영, 1회):
  ① BC 시범 4앵커 (li15/li20/li2508 + liopt 26.25 h=1.1233) — l_i 관측 태워 복제
  ② 엔트로피 플로어: std ≥ 0.25 를 10M 스텝까지 강제 (조기 붕괴 std 0.16 방지)
  ③ 넷 128×128 (l_i별 전략 가족 용량) + GPU 재벤치
  예산/patience 동일. 산출 접미 _long2 (기존 t0wc_ppo.npz 불침).

두 캠페인 공용 (task0 제약·클립 25.5810·골든 규약 전부 유지):
  nc = no_cvt task0 (t0nc_env, obs 7) — 목표선 CMA CL 0.977
  wc = CVT l_i-조건부 (t0wc_env, obs 8, l_i~U[15,30]) — 목표선 CMA CL 1.1045@25.08

스케일업 4종 (지시 스펙):
  1. 예산 3M → 24M cap, 플래토 patience 20 → 60 evals, LR 선형 스케줄은 새 예산에
     자동 재스트레치 (frac = up/n_updates).
  2. 병렬 env 4 → min(코어−4, 24) = 16 (20코어 감지) — multiprocessing spawn 워커
     8×2 env, 물리 스텝 병렬화. 처리율(steps/s) 로그에 기록 (전: nc 4.5k / wc 4.1k).
  3. GPU (RTX 5080 sm_120, torch cu128 별도 경로): 시작 시 넷 업데이트 GPU/CPU 벤치
     → 빠른 쪽 사용 (플래그 DEV). 미설치/미지원이면 CPU + 사유 로그.
  4. 탐색 구조 개선:
     (ii) BC 워밍스타트 (주 수단): CMA 최적해 npz (nc: t0nc_cl / wc: t0wc_cl_li{15,20,2508}
        3점)의 raw 시퀀스를 env에 재생하며 (obs, a) 수집 → 정책 평균 행동복제 →
        PPO 파인튜닝. 시작 crouch = 티처 q0 (t0_spec: 시작 자세는 바운드 내 자유 =
        최적화 대상이므로 합법; wc는 l_i별 티처 q0 선형보간 CROUCH_FN).
     (iii-lite) 초기상태 랜덤화 확대: NOISE_DQ 0.05→0.1 (nc/wc), NOISE_Q 0.005→0.015(wc;
        nc는 티처 q1이 바운드에 근접해 0.005 유지 — 시작 즉시 범위이탈 방지).
     보조: BC 보존 위해 LOG_STD0 0.6→0.4, 초기 25 업데이트 value-only 워밍업
        (신선한 V가 BC 정책을 초반에 파괴하는 것 방지). 엔트로피 3e-3 유지.
"""
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
TAG = "_long"

# ── 하이퍼 (스케일업분 외 기존과 동일) ──
N_ENVS = min((os.cpu_count() or 8) - 4, 24, 16)   # 16 (8워커×2env)
ENV_PER_W = 2
T_ROLL = 512
TOTAL_STEPS = 24_000_000
GAMMA = 0.999
LAM = 0.95
CLIP_EPS = 0.2
EPOCHS = 10
MB = 256
LR0, LR1 = 3e-4, 1e-4
ENT_COEF = 3e-3
VF_COEF = 0.5
GRAD_CLIP = 0.5
LOG_STD0 = float(np.log(0.4))     # BC 보존 (기존 0.6)
EVAL_EVERY = 10
PLATEAU_AFTER = 6_000_000
PLATEAU_PATIENCE = 60
PLATEAU_DELTA = 0.005
VF_WARM = 25                      # value-only 워밍업 업데이트 수
BC_ITERS = 4000
BC_LR = 1e-3
QD_MARGIN = 0.006      # 티처 q_des 인워드 클램프 [rad] (collect_teacher 주석 참조)
BAR_MARGIN = 0.02      # 티처 재생 바운드 배리어 [rad] — 이탈 직전 PD 브레이크
                       # (0.01은 li15 비행 오버슈트를 못 잡음 — 0.02 확정)

NOISE_DQ_LONG = 0.10
NOISE_Q_LONG = {"nc": 0.005, "nc05": 0.005, "wc": 0.015, "wc2": 0.015}

# ── wc2 재시도 처방 (코디 07-18) ──
STD_FLOOR = 0.25                 # 엔트로피 플로어 (std 하한)
STD_FLOOR_UNTIL = 10_000_000     # [env steps] wc2: 고정값. fix: 예산 40% (main에서)
HID = {"nc": 64, "wc": 64, "wc2": 128}   # wc2/fix: 용량 확대
TAGS = {"nc": "_long", "wc": "_long", "wc2": "_long2"}
EVAL_LIS_WC = {"wc": [15.0, 25.08, 30.0], "wc2": [15.0, 25.08, 26.25, 30.0]}

# ── 고정-l_i 전용 정책 스윕 (코디 07-18 밤): campaign = "fix:<li>[:<ctrl_ms>]" ──
# 교사 검증 (07-18): 24/25.08/26.25(=li26 knots 전이)/30 = 2ms 완주 재생
# (1.074/1.084/1.090/0.974), 28 = 152페어 절단이나 탄도 1.126 (스탠스 완비 — 채택),
# liopt(26.25)는 2ms 불가·1ms 1.106·0.5ms 1.105 완주 → 프로브 교사.
FIX_TEACHER = {24.0: "t0wc_cl_li24.npz", 25.08: "t0wc_cl_li2508.npz",
               26.25: "t0wc_cl_li26.npz", 28.0: "t0wc_cl_li28.npz",
               30.0: "t0nc_cl.npz"}
FIX_TEACHER_PROBE = "t0wc_cl_liopt.npz"   # ctrl_dt < 2ms 프로브 (26.25)


def parse_fix(campaign):
    """'fix:26.25[:1|:0.5]' -> (li_mm, ctrl_dt[s], tag). 예산/플래토는 main에서
    sim-time 등가 보정 (x 0.002/ctrl_dt)."""
    parts = campaign.split(":")
    li = float(parts[1])
    ctrl_ms = float(parts[2]) if len(parts) > 2 else 2.0
    li_s = f"{li:g}".replace(".", "p")
    tag = f"_lifix{li_s}_long"
    if ctrl_ms != 2.0:
        tag += "_" + f"{ctrl_ms:g}".replace(".", "") + "ms"
    return li, ctrl_ms / 1000.0, tag


def fix_teacher_of(campaign):
    li, ctrl_dt, _ = parse_fix(campaign)
    # ★ 07-19 픽스: 프로브 교사(liopt)는 26.25 전용 — 24/25.08/28@0.5ms는 자기 점
    # CMA 교사를 해당 주기로 재샘플 (0.5ms = CMA 네이티브 주기라 재생 충실도 최상)
    if ctrl_dt < 0.002 - 1e-12 and abs(li - 26.25) < 1e-9:
        return FIX_TEACHER_PROBE
    return FIX_TEACHER[li]


# ── 티처 (CMA 최적해) 로드 ──
def teacher_nc():
    aj = json.load(open(HERE / "t0nc_cl_audit.json", encoding="utf-8"))
    p = aj["params"]
    return (float(p["knots_qd1"][0]), float(p["knots_qd2"][0])), aj["h_plan"]


def teacher_wc_knots(with_liopt=False):
    keys = [("li15", 15.0), ("li20", 20.0), ("li2508", 25.08)]
    if with_liopt:
        keys.append(("liopt", 26.25))    # CMA 자유-l_i 최적해 (h=1.1233)
    rows = []
    for k, li in keys:
        a = json.load(open(HERE / f"t0wc_cl_{k}_audit.json", encoding="utf-8"))
        p = a["params"]
        rows.append((li, float(p["knots_qd1"][0]), float(p["knots_qd2"][0]),
                     float(a["h_plan"])))
    return rows


def crouch_fn_of(knots):
    lis = np.array([r[0] for r in knots])
    q1s = np.array([r[1] for r in knots])
    qms = np.array([r[2] for r in knots])

    def f(li_mm):
        return (float(np.interp(li_mm, lis, q1s)), float(np.interp(li_mm, lis, qms)))
    return f


def load_env_module(campaign):
    """env 모듈 import + crouch/노이즈 패치 (main·worker 공용)."""
    if campaign in ("nc", "nc05"):
        import t0nc_env as EVm
        EVm.setup()
        q0, _ = teacher_nc()
        EVm.G["CROUCH"] = q0
    elif campaign.startswith("fix:"):
        import t0wc_env as EVm
        EVm.setup()
        z = np.load(HERE / fix_teacher_of(campaign))
        q0 = (float(z["knots_qd1"][0]), float(z["knots_qd2"][0]))
        EVm.CROUCH_FN = lambda li_mm, q0=q0: q0     # 교사 crouch 상수
    else:
        import t0wc_env as EVm
        EVm.setup()
        EVm.CROUCH_FN = crouch_fn_of(teacher_wc_knots(campaign == "wc2"))
    EVm.NOISE_Q = NOISE_Q_LONG.get(campaign, 0.015)
    EVm.NOISE_DQ = NOISE_DQ_LONG
    return EVm


# ══════════════ 워커 (물리 스텝 병렬화 — spawn, torch 미로드) ══════════════
def worker_main(conn, campaign, seeds):
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    EVm = load_env_module(campaign)
    kw = {}
    if campaign.startswith("fix:"):
        li, cdt, _ = parse_fix(campaign)
        kw = dict(li_fixed=li, ctrl_dt=cdt)
    elif campaign == "nc05":
        kw = dict(ctrl_dt=0.0005)
    envs = [EVm.JumpEnv(seed=s, reset_noise=True, **kw) for s in seeds]
    conn.send(np.stack([e.reset() for e in envs]))
    while True:
        msg = conn.recv()
        if msg[0] == "step":
            outs = []
            for e, a in zip(envs, msg[1]):
                o, r, d, info = e.step(a)
                inf = None
                if d:
                    inf = {k: info.get(k) for k in
                           ("apex_est", "apex_obs", "sat_frac", "pen_total",
                            "crash", "range", "li_mm")}
                    o = e.reset()
                outs.append((o, float(r), bool(d), inf))
            conn.send(outs)
        elif msg[0] == "close":
            conn.close()
            return


# ══════════════ 메인 전용 (torch 지연 import) ══════════════
def gpu_bench_decide(torch, hid=64, obs_dim=8):
    """넷 업데이트 GPU/CPU 벤치 → 빠른 쪽 디바이스 반환 (지시 3; 실제 넷 크기로)."""
    if not torch.cuda.is_available():
        return "cpu", "cuda unavailable (cu128 휠 미설치/미지원) — CPU 진행"
    import torch.nn as nn

    def bench(dev):
        net = nn.Sequential(nn.Linear(obs_dim, hid), nn.Tanh(), nn.Linear(hid, hid),
                            nn.Tanh(), nn.Linear(hid, 2)).to(dev)
        opt = torch.optim.Adam(net.parameters(), lr=3e-4)
        x = torch.randn(MB, obs_dim, device=dev)
        y = torch.randn(MB, 2, device=dev)
        for _ in range(20):
            loss = (net(x) - y).pow(2).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        if dev == "cuda":
            torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(400):
            loss = (net(x) - y).pow(2).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        if dev == "cuda":
            torch.cuda.synchronize()
        return time.time() - t0
    tc, tg = bench("cpu"), bench("cuda")
    name = torch.cuda.get_device_name(0)
    note = f"{name} (hid {hid}): 400 mb-updates cpu {tc:.3f}s / gpu {tg:.3f}s"
    if tg < 0.8 * tc:
        return "cuda", note + " → GPU 사용"
    return "cpu", note + f" → 2x{hid} 넷이 작아 CPU가 빠름 (물리 스텝이 병목) — CPU 사용"


def collect_teacher(EVm, campaign, npz_name, li, ctrl_dt=None):
    """티처를 폐루프 PD로 재생 → (obs, a) 페어 수집.
    raw 개루프 재생(ZOH 2ms)은 rail-to-rail CL 명령의 스위칭 타이밍을 뭉개 발산
    (wc에서 apex 0.57 vs 티처 1.10 확인) → 티처의 q_des 스플라인+게인으로 현재
    상태에서 PD 명령을 온라인 재계산 (상태 피드백 페어 — BC 데이터로도 더 우월)."""
    import t0_spec as T0
    z = np.load(HERE / npz_name)
    t_z = z["t"]
    clip = float(EVm.R19.CLIP)
    kp1, kd1, kp2, kd2 = [float(g) for g in z["gains"]]
    # 티처 q_des 인워드 클램프: CMA 해는 관절바운드를 0.5~3 mrad로 스치는데 (감사 마진
    # q1_lo −0.0005 등), 2ms PD 재이산화의 추종오차가 바운드를 넘겨 env가 조기 종료
    # (li15/li2508에서 t≈0.15s 이탈 확인) → q_des를 δ만큼 안쪽으로 (h 손실 ~mm 규모)
    d_m = QD_MARGIN
    q2lb, q2ub = (T0.Q2_LB, T0.Q2_UB) if campaign in ("nc", "nc05") \
        else (T0.QM_LB, T0.QM_UB)
    qd1_c = np.clip(z["qd1"], T0.Q1_LB + d_m, T0.Q1_UB - d_m)
    qd2_c = np.clip(z["qd2"], q2lb + d_m, q2ub - d_m)
    kw = dict(li_fixed=li) if li is not None else {}
    if ctrl_dt is not None:
        kw["ctrl_dt"] = ctrl_dt          # 이산화 프로브 (t0wc_env만 지원)
    env = EVm.JumpEnv(seed=7, reset_noise=False, **kw)
    obs = env.reset()
    X, A = [], []
    done_info = {}
    def _barrier(q, v, lb, ub, kp, kd):
        """바운드 배리어 (재생 전용): CMA 해는 바운드를 0.1~3 mrad로 스치고, 이탈 직전
        탄도 오버슈트(비행 중 q1 상향 스윙)는 qd 클램프로 못 막음 (liopt/li15에서
        t≈0.15s 조기 종료 확인) → 바운드 안쪽 margin에서 PD 브레이크. 시범 자체가
        'task0 바운드 준수 비행'을 가르치는 상태 피드백 규칙이 됨."""
        if q > ub - BAR_MARGIN:
            return kp * ((ub - BAR_MARGIN) - q) - kd * max(v, 0.0)
        if q < lb + BAR_MARGIN:
            return kp * ((lb + BAR_MARGIN) - q) - kd * min(v, 0.0)
        return 0.0

    cdt = getattr(env, "ctrl_dt", EVm.CTRL_DT)
    for k in range(env.n_ep):
        tk = k * cdt
        q1c, q2c, v1c, v2c = env._read()
        c1 = kp1 * (float(np.interp(tk, t_z, qd1_c)) - q1c) \
            + kd1 * (float(np.interp(tk, t_z, z["dqd1"])) - v1c)
        c2 = kp2 * (float(np.interp(tk, t_z, qd2_c)) - q2c) \
            + kd2 * (float(np.interp(tk, t_z, z["dqd2"])) - v2c)
        c1 += _barrier(q1c, v1c, T0.Q1_LB, T0.Q1_UB, kp1, kd1)
        c2 += _barrier(q2c, v2c, q2lb, q2ub, kp2, kd2)
        a = np.clip([c1 / clip, c2 / clip], -1.0, 1.0)
        X.append(obs.copy())
        A.append(np.asarray(a, np.float32))
        obs, r, done, done_info = env.step(a)
        if done:
            break
    return (np.asarray(X, np.float32), np.asarray(A, np.float32),
            dict(npz=npz_name, li=li, n=len(X),
                 mode="closed-loop PD (qd 스플라인+게인 온라인)",
                 apex_replay=float(done_info.get("apex_obs", np.nan)),
                 range_term=bool(done_info.get("range", False)),
                 teacher_h=float(z["h_plan"])))


def bc_fit(torch, ac, X, A, dev):
    """정책 평균 행동복제 (풀배치 Adam MSE) — value/log_std는 건드리지 않음."""
    x = torch.as_tensor(X, device=dev)
    a = torch.as_tensor(A, device=dev)
    opt = torch.optim.Adam(ac.pi.parameters(), lr=BC_LR)
    mse0 = float((ac.mean(x) - a).pow(2).mean())
    for it in range(BC_ITERS):
        if it == int(BC_ITERS * 0.7):
            for g in opt.param_groups:      # 후반 감쇠 (128넷 미세수렴 — 07-18 벤치)
                g["lr"] = BC_LR * 0.2
        loss = (ac.mean(x) - a).pow(2).mean()
        opt.zero_grad(); loss.backward(); opt.step()
    return mse0, float((ac.mean(x) - a).pow(2).mean())


def det_eval(torch, env, ac, EVm, campaign, dev):
    obs = env.reset()
    ep_ret = 0.0
    info = {}
    while True:
        with torch.no_grad():
            mu = ac.mean(torch.as_tensor(obs, dtype=torch.float32, device=dev))
        obs, r, done, info = env.step(mu.cpu().numpy())
        ep_ret += r
        if done:
            break
    apex_act = passive_apex(EVm, campaign, env)
    return dict(ep_ret=float(ep_ret), apex_obs=float(info.get("apex_obs", np.nan)),
                h_eval=float(max(info.get("apex_obs", 0.0), apex_act)),
                pen_total=float(info.get("pen_total", np.nan)),
                sat_frac=float(info.get("sat_frac", np.nan)),
                tn_viol_frac=float(info.get("tn_viol_frac", np.nan)),
                crash=bool(info.get("crash", False)),
                range_term=bool(info.get("range", False)))


def passive_apex(EVm, campaign, env, t_after=0.6):
    G = EVm.G if campaign in ("nc", "nc05") else EVm.W.G
    law_a = G["LAW"][0]
    e1 = EVm.RU.HIP["a1"] if EVm.RU.HIP_LAW else 0.0
    md, mj, model = env.md, env.mj, env.model
    apex = float(md.qpos[0])
    for _ in range(int(round(t_after / env.dt))):
        md.ctrl[:] = [-e1, -law_a]
        md.qfrc_applied[env.dof_knee] = 0.0
        try:
            mj.mj_step(model, md)
        except Exception:
            break
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            break
        apex = max(apex, float(md.qpos[0]))
    return apex


def main(campaign):
    t_wall0 = time.time()
    is_fix = campaign.startswith("fix:")
    if is_fix:
        li_fix, cdt_fix, tag = parse_fix(campaign)
        hid = 128                              # wc2 레시피 고정
        ratio = 0.002 / cdt_fix               # sim-time 등가 예산 보정
    elif campaign == "nc05":                   # no_cvt @0.5ms (07-19 전면 비교)
        li_fix, cdt_fix, ratio = None, 0.0005, 4.0
        tag = "_long_05ms"
        hid = 128                              # 0.5ms 프로브 레시피 고정
    else:
        li_fix, cdt_fix, ratio = None, None, 1.0
        tag = TAGS[campaign]
        hid = HID[campaign]
    total = int(TOTAL_STEPS * ratio)
    plateau_after = int(PLATEAU_AFTER * ratio)
    patience = min(120, int(round(PLATEAU_PATIENCE * ratio))) \
        if (is_fix or campaign == "nc05") else PLATEAU_PATIENCE
    # 엔트로피 플로어 종료점: fix/nc05=예산 40% (코디 처방), wc2=10M, 그 외 없음
    floor_until = int(0.4 * total) if (is_fix or campaign == "nc05") else \
        (STD_FLOOR_UNTIL if campaign == "wc2" else -1)
    EVm = load_env_module(campaign)
    golden = EVm.run_golden()      # 골든 재확인 (지시 5)
    prefix = "t0nc" if campaign in ("nc", "nc05") else "t0wc"
    obs_dim = EVm.JumpEnv.OBS_DIM

    sys.path.insert(0, "C:/Users/junho/AppData/Local/torchcpu311")   # 폴백
    sys.path.insert(0, "C:/Users/junho/AppData/Local/torchcu128")    # 우선 (RTX 5080)
    import torch
    import torch.nn as nn
    torch.set_num_threads(4)
    torch.manual_seed(0)
    dev, gpu_note = gpu_bench_decide(torch, hid=hid, obs_dim=obs_dim)
    print(f"[dev] {gpu_note}", flush=True)

    # AC (기존 캠페인 클래스 재사용 — 아키텍처/이름 동일 → 롤아웃 스크립트 호환)
    if campaign in ("nc", "nc05"):
        import t0nc_train as TRb
        ac = TRb.ActorCritic(hid=hid)
    else:
        import t0wc_train as TRb
        ac = TRb.ActorCritic(hid=hid)
    with torch.no_grad():
        ac.log_std.fill_(LOG_STD0)
    ac.to(dev)

    # ── 재개 (T0_RESUME=1, 외부 킬 후속 — 코디 07-19): 같은 tag ckpt에서 이어서 ──
    resume_ck = None
    if os.environ.get("T0_RESUME") == "1":
        fck = HERE / f"{prefix}_ppo_policy{tag}.pt"
        if fck.exists():
            resume_ck = torch.load(fck, weights_only=False)
            print(f"[resume] {fck.name}: steps={resume_ck.get('steps')} "
                  f"best={float(resume_ck.get('best_h', -1)):.4f} — BC 스킵, "
                  f"잔여 예산으로 재개", flush=True)

    # ── (ii) BC 워밍스타트 ──
    if is_fix:
        teachers = [(fix_teacher_of(campaign), li_fix)]
    else:
        teachers = ([("t0nc_cl.npz", None)] if campaign in ("nc", "nc05") else
                    [("t0wc_cl_li15.npz", 15.0), ("t0wc_cl_li20.npz", 20.0),
                     ("t0wc_cl_li2508.npz", 25.08)])
    # wc2 4앵커 시도 결과 (07-18): liopt(26.25, h=1.1233, 스탠스 0.044s)는 2ms 액션
    # MDP에서 재생 불가 — raw/PD/배리어/시간스트레치/li2508전이/기존정책+배리어 전부
    # 붕괴 또는 바운드 이탈 (최고 탄도 ~0.91). 초임펄스 CL 해는 0.5ms PD 전용 지식
    # → 시범은 3앵커 유지, 26.25는 eval 앵커 + 깊은 crouch 노트(CROUCH_FN)로만 반영.
    # (CMA 1.1233과 RL 갭의 일부는 탐색이 아니라 2ms 액션 이산화 자체임을 시사)
    Xs, As, t_meta = [], [], []
    if resume_ck is None:
        for npz_name, li in teachers:
            X, A, meta = collect_teacher(EVm, campaign, npz_name, li, ctrl_dt=cdt_fix)
            Xs.append(X); As.append(A); t_meta.append(meta)
            print(f"[bc] teacher {npz_name} (li={li}): {meta['n']} pairs, "
                  f"replay apex={meta['apex_replay']:.3f} (teacher h={meta['teacher_h']:.3f})",
                  flush=True)
        mse0, mse1 = bc_fit(torch, ac, np.concatenate(Xs), np.concatenate(As), dev)
        print(f"[bc] fit: MSE {mse0:.4f} → {mse1:.6f} ({BC_ITERS} iters)", flush=True)
    else:
        ac.load_state_dict(resume_ck["final"])
        ac.to(dev)
        t_meta = (resume_ck.get("hyper", {}).get("explore", {})
                  .get("bc", {}).get("teachers", []))
        mse0 = mse1 = float("nan")

    # eval env (메인 프로세스, 노이즈 없음)
    if campaign in ("nc", "nc05"):
        eval_envs = [("q0", EVm.JumpEnv(
            seed=999, reset_noise=False,
            **(dict(ctrl_dt=cdt_fix) if cdt_fix else {})))]
    elif is_fix:
        eval_envs = [(f"{li_fix:g}", EVm.JumpEnv(seed=999, reset_noise=False,
                                                 li_fixed=li_fix, ctrl_dt=cdt_fix))]
    else:
        eval_envs = [(f"{li:g}", EVm.JumpEnv(seed=990 + i, reset_noise=False, li_fixed=li))
                     for i, li in enumerate(EVAL_LIS_WC[campaign])]
    bc_evals = {nm: det_eval(torch, e, ac, EVm, campaign, dev) for nm, e in eval_envs}
    bc_h = {nm: round(v["h_eval"], 4) for nm, v in bc_evals.items()}
    print(f"[bc] det-eval h: {bc_h}", flush=True)

    # ── 워커 스폰 ──
    n_w = N_ENVS // ENV_PER_W
    ctx = mp.get_context("spawn")
    conns, procs = [], []
    for w in range(n_w):
        pc, cc = ctx.Pipe()
        seeds = list(range(w * ENV_PER_W, (w + 1) * ENV_PER_W))
        p = ctx.Process(target=worker_main, args=(cc, campaign, seeds), daemon=True)
        p.start()
        conns.append(pc); procs.append(p)
    obs = np.concatenate([c.recv() for c in conns])   # (N_ENVS, obs_dim)
    print(f"[mp] {n_w} workers × {ENV_PER_W} envs = {N_ENVS} — ready "
          f"[{time.time() - t_wall0:.0f}s]", flush=True)

    opt = torch.optim.Adam(ac.parameters(), lr=LR0)
    n_updates = total // (N_ENVS * T_ROLL)
    log = dict(golden=golden, updates=[], evals=[], hyper=dict(
        campaign=campaign, n_envs=N_ENVS, n_workers=n_w, t_roll=T_ROLL,
        total_steps=total, li_fixed=li_fix, ctrl_dt=(cdt_fix or 0.002), tag=tag,
        gamma=GAMMA, lam=LAM, clip=CLIP_EPS,
        epochs=EPOCHS, mb=MB, lr=[LR0, LR1], ent=ENT_COEF, vf=VF_COEF,
        log_std0=LOG_STD0, clip_raw=float(EVm.R19.CLIP), device=dev,
        gpu_note=gpu_note, vf_warm=VF_WARM, hid=hid,
        net=f"MLP 2x{hid} tanh (obs {obs_dim}, mean linear out, v2)",
        plateau=dict(after=PLATEAU_AFTER, patience=PLATEAU_PATIENCE,
                     delta=PLATEAU_DELTA),
        std_floor=(dict(floor=STD_FLOOR, until=floor_until)
                   if floor_until > 0 else None),
        explore=dict(bc=dict(teachers=t_meta, iters=BC_ITERS, lr=BC_LR,
                             mse=[mse0, mse1], det_h_after_bc=bc_h),
                     noise_q=NOISE_Q_LONG.get(campaign, 0.015), noise_dq=NOISE_DQ_LONG,
                     log_std0=LOG_STD0,
                     crouch=("teacher q0 " + str(EVm.G["CROUCH"])
                             if campaign in ("nc", "nc05")
                             else ("teacher q0 고정 " + str(EVm.CROUCH_FN(li_fix))
                                   if is_fix else "teacher q0(l_i) 선형보간 "
                                   + str(teacher_wc_knots(campaign == "wc2"))))),
        sps_before="nc 4.5k / wc 4.1k steps/s (4 env 직렬, 기존 캠페인)"))
    best_h, best_state, best_step = -1.0, None, 0
    steps0 = 0
    if resume_ck is not None:
        best_h = float(resume_ck.get("best_h", -1.0))
        best_state = resume_ck.get("best")
        best_step = int(resume_ck.get("best_step", 0))
        steps0 = int(resume_ck.get("steps", 0))
        log["hyper"]["resume"] = dict(from_steps=steps0, best_h=best_h)
    ep_rets = np.zeros(N_ENVS)
    fin_ret, fin_apex, fin_pen = [], [], []
    steps_done = steps0
    stop_reason = "budget"
    print(f"PPO start — {n_updates} updates × batch {N_ENVS * T_ROLL} "
          f"(dev {dev}, clip={EVm.R19.CLIP})", flush=True)

    t_prev = time.time()
    for up in range(1, n_updates + 1):
        if steps_done >= total:
            break
        frac = min(1.0, steps_done / max(total, 1))
        for g in opt.param_groups:
            g["lr"] = LR0 + (LR1 - LR0) * frac
        O = np.zeros((T_ROLL, N_ENVS, obs_dim), dtype=np.float32)
        Aa = np.zeros((T_ROLL, N_ENVS, 2), dtype=np.float32)
        Lp = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Rw = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Dn = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Vl = np.zeros((T_ROLL + 1, N_ENVS), dtype=np.float32)
        t_roll0 = time.time()
        for k in range(T_ROLL):
            ot = torch.as_tensor(obs, dtype=torch.float32, device=dev)
            with torch.no_grad():
                dist = ac.dist(ot)
                a = dist.sample()
                lp = dist.log_prob(a).sum(-1)
                v = ac.value(ot)
            an = a.cpu().numpy()
            O[k] = obs; Aa[k] = an
            Lp[k] = lp.cpu().numpy(); Vl[k] = v.cpu().numpy()
            for w, c in enumerate(conns):
                c.send(("step", an[w * ENV_PER_W:(w + 1) * ENV_PER_W]))
            i = 0
            for c in conns:
                for (o2, r, d, inf) in c.recv():
                    Rw[k, i] = r; Dn[k, i] = float(d)
                    ep_rets[i] += r
                    if d:
                        fin_ret.append(ep_rets[i]); ep_rets[i] = 0.0
                        if inf and inf.get("apex_est") is not None:
                            fin_apex.append(inf["apex_est"])
                        if inf and inf.get("pen_total") is not None:
                            fin_pen.append(inf["pen_total"])
                    obs[i] = o2
                    i += 1
        t_roll = time.time() - t_roll0
        with torch.no_grad():
            Vl[T_ROLL] = ac.value(torch.as_tensor(
                obs, dtype=torch.float32, device=dev)).cpu().numpy()
        steps_done += T_ROLL * N_ENVS
        Ad = np.zeros_like(Rw)
        gae = np.zeros(N_ENVS, dtype=np.float32)
        for k in reversed(range(T_ROLL)):
            nonterm = 1.0 - Dn[k]
            delta = Rw[k] + GAMMA * Vl[k + 1] * nonterm - Vl[k]
            gae = delta + GAMMA * LAM * nonterm * gae
            Ad[k] = gae
        Ret = Ad + Vl[:T_ROLL]
        b_obs = torch.as_tensor(O.reshape(-1, obs_dim), device=dev)
        b_act = torch.as_tensor(Aa.reshape(-1, 2), device=dev)
        b_lp = torch.as_tensor(Lp.reshape(-1), device=dev)
        b_adv = torch.as_tensor(Ad.reshape(-1), device=dev)
        b_ret = torch.as_tensor(Ret.reshape(-1), device=dev)
        b_adv = (b_adv - b_adv.mean()) / (b_adv.std() + 1e-8)
        nb = b_obs.shape[0]
        idx = np.arange(nb)
        warm = resume_ck is None and up <= VF_WARM   # 워밍업 (재개 시 스킵 — V 이미 학습됨)
        for _ in range(EPOCHS):
            np.random.shuffle(idx)
            for s in range(0, nb, MB):
                j = torch.as_tensor(idx[s:s + MB], device=dev)
                l_v = (ac.value(b_obs[j]) - b_ret[j]).pow(2).mean()
                if warm:
                    loss = VF_COEF * l_v
                else:
                    dist = ac.dist(b_obs[j])
                    lp = dist.log_prob(b_act[j]).sum(-1)
                    ratio = (lp - b_lp[j]).exp()
                    adv = b_adv[j]
                    l_pi = -torch.min(
                        ratio * adv,
                        ratio.clamp(1 - CLIP_EPS, 1 + CLIP_EPS) * adv).mean()
                    l_ent = dist.entropy().sum(-1).mean()
                    loss = l_pi + VF_COEF * l_v - ENT_COEF * l_ent
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(ac.parameters(), GRAD_CLIP)
                opt.step()
                if floor_until > 0 and steps_done < floor_until:
                    with torch.no_grad():      # 엔트로피 플로어 (wc2/fix 처방)
                        ac.log_std.clamp_(min=float(np.log(STD_FLOOR)))
        mret = float(np.mean(fin_ret[-80:])) if fin_ret else float("nan")
        mapex = float(np.mean(fin_apex[-80:])) if fin_apex else float("nan")
        mpen = float(np.mean(fin_pen[-80:])) if fin_pen else float("nan")
        sps = T_ROLL * N_ENVS / max(time.time() - t_prev, 1e-9)
        sps_roll = T_ROLL * N_ENVS / max(t_roll, 1e-9)
        t_prev = time.time()
        log["updates"].append(dict(up=up, steps=steps_done, ret=mret, apex=mapex,
                                   pen=mpen, sps=round(sps), sps_roll=round(sps_roll),
                                   std=[float(x) for x in
                                        ac.log_std.exp().detach().cpu()]))
        if up % EVAL_EVERY == 0 or up == n_updates:
            evs = {nm: det_eval(torch, e, ac, EVm, campaign, dev) for nm, e in eval_envs}
            hs = [v["h_eval"] for v in evs.values()]
            ev = dict(up=up, steps=steps_done,
                      h_eval=float(np.mean(hs)),
                      h_anchor={nm: float(v["h_eval"]) for nm, v in evs.items()},
                      pen_total=float(np.mean([v["pen_total"] for v in evs.values()])),
                      warm=warm)
            log["evals"].append(ev)
            if ev["h_eval"] > best_h:
                best_h = ev["h_eval"]
                best_state = {k: v.detach().cpu().clone()
                              for k, v in ac.state_dict().items()}
                best_step = steps_done
            torch.save(dict(final={k: v.detach().cpu().clone()
                                   for k, v in ac.state_dict().items()},
                            best=best_state, best_h=best_h, best_step=best_step,
                            steps=steps_done, hyper=log["hyper"]),
                       HERE / f"{prefix}_ppo_policy{tag}.pt")
            ha_s = "/".join(f"{v:.3f}" for v in ev["h_anchor"].values())
            print(f"up {up:4d} steps {steps_done / 1e6:6.2f}M  ret {mret:6.3f}  "
                  f"apex {mapex:.3f}  det h({'/'.join(ev['h_anchor'])}) {ha_s} "
                  f"mean {ev['h_eval']:.4f} (best {best_h:.4f})  "
                  f"sps {sps:5.0f}  std {ac.log_std.exp().detach().cpu().numpy().round(3)}"
                  f"{'  [VF-warm]' if warm else ''}", flush=True)
            import safe
            safe.atomic_json_write(HERE / f"{prefix}_train_log{tag}.json", log)
            if steps_done >= plateau_after and len(log["evals"]) > patience:
                recent = [e["h_eval"] for e in log["evals"][-patience:]]
                prior = max(e["h_eval"] for e in log["evals"][:-patience])
                if max(recent) < prior + PLATEAU_DELTA:
                    stop_reason = (f"plateau (best {prior:.4f} 이후 "
                                   f"{patience}회 미개선)")
                    print(f"early stop: {stop_reason}", flush=True)
                    break

    wall = time.time() - t_wall0
    log["final"] = dict(steps=steps_done, wall_s=wall, best_h=best_h,
                        best_step=best_step, stop=stop_reason,
                        sps_mean=float(np.mean([u["sps"] for u in
                                                log["updates"][2:]])) if
                        len(log["updates"]) > 2 else None)
    torch.save(dict(final={k: v.detach().cpu().clone()
                           for k, v in ac.state_dict().items()},
                    best=best_state, best_h=best_h, best_step=best_step,
                    hyper=log["hyper"]),
               HERE / f"{prefix}_ppo_policy{tag}.pt")
    import safe
    safe.atomic_json_write(HERE / f"{prefix}_train_log{tag}.json", log)
    print(f"done — steps {steps_done} wall {wall / 60:.1f}min best_h {best_h:.4f} "
          f"({stop_reason})", flush=True)
    for c in conns:
        try:
            c.send(("close",))
        except Exception:
            pass
    make_curve(log, prefix, tag)


def make_curve(log, prefix, tag=TAG):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    st = [u["steps"] / 1e6 for u in log["updates"]]
    ax[0].plot(st, [u["ret"] for u in log["updates"]], label="에피소드 리턴 (이동80)")
    ax0b = ax[0].twinx()
    l2, = ax0b.plot(st, [u["apex"] for u in log["updates"]], linestyle="--",
                    color=ax[0]._get_lines.get_next_color(), label="apex_est (이동80)")
    ax[0].set_xlabel("env steps [M]"); ax[0].set_ylabel("리턴")
    ax0b.set_ylabel("apex_est [m]")
    h1, lb1 = ax[0].get_legend_handles_labels()
    ax[0].legend(h1 + [l2], lb1 + [l2.get_label()], loc="lower right", fontsize=8)
    ax[0].set_title(f"{prefix} long PPO 학습 곡선 (BC 워밍스타트 + 16 env)")
    es = [e["steps"] / 1e6 for e in log["evals"]]
    anchors = list(log["evals"][0]["h_anchor"].keys()) if log["evals"] else []
    for nm in anchors:
        ax[1].plot(es, [e["h_anchor"][nm] for e in log["evals"]], marker="o", ms=2,
                   label=f"det h @ {nm}" + ("mm" if nm[0].isdigit() else ""))
    if len(anchors) > 1:
        ax[1].plot(es, [e["h_eval"] for e in log["evals"]], linestyle="--",
                   label="mean")
    if "final" in log:
        ax[1].axhline(log["final"]["best_h"], linestyle=":", alpha=0.6,
                      label=f"best {log['final']['best_h']:.3f} m")
    bc_h = log["hyper"]["explore"]["bc"]["det_h_after_bc"]
    if bc_h:
        ax[1].axhline(float(np.mean(list(bc_h.values()))), linestyle="-.", alpha=0.5,
                      label=f"BC 직후 {np.mean(list(bc_h.values())):.3f} m")
    ax[1].set_xlabel("env steps [M]"); ax[1].set_ylabel("h [m]")
    ax[1].legend(fontsize=8)
    ax[1].set_title("결정론 평가 점프 높이")
    fig.suptitle(f"P25-task0 long{tag[5:]} — {prefix} (24M cap, BC+VF워밍업, patience 60)")
    fig.tight_layout()
    fig.savefig(HERE / f"{prefix}_ppo_curve{tag}.png", dpi=130)
    plt.close(fig)
    print(f"curve saved: {prefix}_ppo_curve{tag}.png", flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    camp = sys.argv[1] if len(sys.argv) > 1 else "nc"
    assert camp in ("nc", "nc05", "wc", "wc2") or camp.startswith("fix:"), \
        "usage: python t0_train_long.py nc|nc05|wc|wc2|fix:<li>[:<ctrl_ms>] [steps]"
    if len(sys.argv) > 2:
        TOTAL_STEPS = int(sys.argv[2])
    main(camp)
