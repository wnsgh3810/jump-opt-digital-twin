# -*- coding: utf-8 -*-
"""p25_c_train — P25 Phase C: PPO 파일럿 학습 (커스텀 torch PPO, CPU 전용).

정책/가치: MLP 2×64 tanh (소형 넷 — 과제 규약). 액션 = 대각 가우시안 (state-independent
log_std), 평균은 tanh로 [−1,1] 스쿼시 → env가 ×35.5.
PPO: n_envs=4 lockstep(단일 프로세스, BLAS 2스레드 캡) · T=512/env → batch 2048 ·
γ=0.999 λ=0.95 clip=0.2 epochs=10 mb=256 · lr 3e-4→1e-4 선형 · ent 1e-3 · vf 0.5 ·
grad clip 0.5. 예산 1.5M 제어스텝 (조기 종료: 600k 이후 det-eval h가 15회(≈307k 스텝)
연속 5mm 미개선이면 플래토 판정).
det-eval (10 업데이트마다): 노이즈 없는 결정론 에피소드 + 수동 연장 0.6s → 실측 apex.
출력: p25_c_policy.pt (final+best) · p25_c_train_log.json · p25_c_curve.png.
시동 전 골든 체크 (run_golden) 통과 필수 — 실패 시 학습 진입 금지.
"""
import os
import sys
import time

import numpy as np

import p25_c_env as EV
from p25_c_env import JumpEnv, G
import safe

# torch: MS-Store python site-packages는 MAX_PATH 초과로 wheel 설치 불가(WinError 206)
# → 짧은 경로 전용 설치 (pip --target, 2026-07-17)
sys.path.insert(0, "C:/Users/junho/AppData/Local/torchcpu311")
import torch
import torch.nn as nn

torch.set_num_threads(2)
torch.manual_seed(0)

HERE = os.path.dirname(os.path.abspath(__file__))

# ── 하이퍼파라미터 (선고정) ──
N_ENVS = 4
T_ROLL = 512
TOTAL_STEPS = 1_500_000
GAMMA = 0.999
LAM = 0.95
CLIP_EPS = 0.2
EPOCHS = 10
MB = 256
LR0, LR1 = 3e-4, 1e-4
ENT_COEF = 1e-3
VF_COEF = 0.5
GRAD_CLIP = 0.5
LOG_STD0 = np.log(0.5)
EVAL_EVERY = 10          # 업데이트 단위
PLATEAU_AFTER = 600_000
PLATEAU_PATIENCE = 15    # det-eval 횟수
PLATEAU_DELTA = 0.005    # [m]


class ActorCritic(nn.Module):
    def __init__(self, obs_dim=7, act_dim=2, hid=64):
        super().__init__()
        self.pi = nn.Sequential(nn.Linear(obs_dim, hid), nn.Tanh(),
                                nn.Linear(hid, hid), nn.Tanh(),
                                nn.Linear(hid, act_dim))
        self.v = nn.Sequential(nn.Linear(obs_dim, hid), nn.Tanh(),
                               nn.Linear(hid, hid), nn.Tanh(),
                               nn.Linear(hid, 1))
        self.log_std = nn.Parameter(torch.full((act_dim,), float(LOG_STD0)))

    def dist(self, obs):
        mu = torch.tanh(self.pi(obs))
        return torch.distributions.Normal(mu, self.log_std.exp())

    def value(self, obs):
        return self.v(obs).squeeze(-1)


def det_eval(env, ac):
    """결정론 에피소드 (노이즈 없는 reset, 평균 액션) + 수동 연장 → 실측 apex."""
    obs = env.reset()
    ep_ret = 0.0
    info = {}
    while True:
        with torch.no_grad():
            mu = torch.tanh(ac.pi(torch.as_tensor(obs, dtype=torch.float32)))
        obs, r, done, info = env.step(mu.numpy())
        ep_ret += r
        if done:
            break
    apex_act = passive_apex(env)
    return dict(ep_ret=float(ep_ret), apex_obs=float(info.get("apex_obs", np.nan)),
                apex_est=float(info.get("apex_est", np.nan)),
                h_eval=float(max(info.get("apex_obs", 0.0), apex_act)),
                sat_frac=float(info.get("sat_frac", np.nan)),
                n_bounce=int(info.get("n_bounce", -1)),
                slip_total=float(info.get("slip_total", np.nan)),
                crash=bool(info.get("crash", False)),
                range_term=bool(info.get("range", False)))


def passive_apex(env, t_after=0.6):
    """에피소드 종료 상태에서 수동 연장 (a_full23 기록 끝 이후 규약:
    s1=s2=0, 무릎 extra=LAW_A, 힙 e1=HIP.a1, 스프링 h=0) → max bz."""
    law_a = G["LAW"][0]
    e1 = EV.RU.HIP["a1"] if EV.RU.HIP_LAW else 0.0
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


def main():
    t_wall0 = time.time()
    golden = EV.run_golden()
    envs = [JumpEnv(seed=i, reset_noise=True) for i in range(N_ENVS)]
    eval_env = JumpEnv(seed=999, reset_noise=False)
    ac = ActorCritic()
    n_par = sum(p.numel() for p in ac.parameters())
    opt = torch.optim.Adam(ac.parameters(), lr=LR0)
    obs = np.stack([e.reset() for e in envs])
    n_updates = TOTAL_STEPS // (N_ENVS * T_ROLL)
    log = dict(golden=golden, updates=[], evals=[], hyper=dict(
        n_envs=N_ENVS, t_roll=T_ROLL, total_steps=TOTAL_STEPS, gamma=GAMMA,
        lam=LAM, clip=CLIP_EPS, epochs=EPOCHS, mb=MB, lr=[LR0, LR1],
        ent=ENT_COEF, vf=VF_COEF, log_std0=float(LOG_STD0), net="MLP 2x64 tanh",
        n_params=int(n_par),
        reward=dict(shaping="d_bz", apex_bonus=EV.APEX_BONUS, tau_pen=EV.TAU_PEN,
                    slip_pen=EV.SLIP_PEN, range_pen=EV.RANGE_PEN,
                    crash_pen=EV.CRASH_PEN)))
    best_h, best_state, best_step = -1.0, None, 0
    ep_rets = [0.0] * N_ENVS
    fin_ret, fin_apex, fin_sat = [], [], []
    steps_done = 0
    stop_reason = "budget"
    print(f"PPO start — {n_updates} updates × batch {N_ENVS * T_ROLL} "
          f"(net {n_par} params)", flush=True)

    for up in range(1, n_updates + 1):
        frac = (up - 1) / max(n_updates - 1, 1)
        for g in opt.param_groups:
            g["lr"] = LR0 + (LR1 - LR0) * frac
        O = np.zeros((T_ROLL, N_ENVS, 7), dtype=np.float32)
        Aa = np.zeros((T_ROLL, N_ENVS, 2), dtype=np.float32)
        Lp = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Rw = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Dn = np.zeros((T_ROLL, N_ENVS), dtype=np.float32)
        Vl = np.zeros((T_ROLL + 1, N_ENVS), dtype=np.float32)
        for k in range(T_ROLL):
            ot = torch.as_tensor(obs, dtype=torch.float32)
            with torch.no_grad():
                dist = ac.dist(ot)
                a = dist.sample()
                lp = dist.log_prob(a).sum(-1)
                v = ac.value(ot)
            an = a.numpy()
            O[k] = obs; Aa[k] = an; Lp[k] = lp.numpy(); Vl[k] = v.numpy()
            for i, e in enumerate(envs):
                o2, r, done, info = e.step(an[i])
                Rw[k, i] = r; Dn[k, i] = float(done)
                ep_rets[i] += r
                if done:
                    fin_ret.append(ep_rets[i]); ep_rets[i] = 0.0
                    if "apex_est" in info:
                        fin_apex.append(info["apex_est"])
                    fin_sat.append(info.get("sat_frac", 0.0))
                    o2 = e.reset()
                obs[i] = o2
        with torch.no_grad():
            Vl[T_ROLL] = ac.value(torch.as_tensor(obs, dtype=torch.float32)).numpy()
        steps_done += T_ROLL * N_ENVS
        # GAE
        Ad = np.zeros_like(Rw)
        gae = np.zeros(N_ENVS, dtype=np.float32)
        for k in reversed(range(T_ROLL)):
            nonterm = 1.0 - Dn[k]
            delta = Rw[k] + GAMMA * Vl[k + 1] * nonterm - Vl[k]
            gae = delta + GAMMA * LAM * nonterm * gae
            Ad[k] = gae
        Ret = Ad + Vl[:T_ROLL]
        b_obs = torch.as_tensor(O.reshape(-1, 7))
        b_act = torch.as_tensor(Aa.reshape(-1, 2))
        b_lp = torch.as_tensor(Lp.reshape(-1))
        b_adv = torch.as_tensor(Ad.reshape(-1))
        b_ret = torch.as_tensor(Ret.reshape(-1))
        b_adv = (b_adv - b_adv.mean()) / (b_adv.std() + 1e-8)
        nb = b_obs.shape[0]
        idx = np.arange(nb)
        for _ in range(EPOCHS):
            np.random.shuffle(idx)
            for s in range(0, nb, MB):
                j = torch.as_tensor(idx[s:s + MB])
                dist = ac.dist(b_obs[j])
                lp = dist.log_prob(b_act[j]).sum(-1)
                ratio = (lp - b_lp[j]).exp()
                adv = b_adv[j]
                l_pi = -torch.min(ratio * adv,
                                  ratio.clamp(1 - CLIP_EPS, 1 + CLIP_EPS) * adv).mean()
                l_v = (ac.value(b_obs[j]) - b_ret[j]).pow(2).mean()
                l_ent = dist.entropy().sum(-1).mean()
                loss = l_pi + VF_COEF * l_v - ENT_COEF * l_ent
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(ac.parameters(), GRAD_CLIP)
                opt.step()
        mret = float(np.mean(fin_ret[-40:])) if fin_ret else float("nan")
        mapex = float(np.mean(fin_apex[-40:])) if fin_apex else float("nan")
        msat = float(np.mean(fin_sat[-40:])) if fin_sat else float("nan")
        log["updates"].append(dict(up=up, steps=steps_done, ret40=mret,
                                   apex40=mapex, sat40=msat,
                                   std=[float(x) for x in ac.log_std.exp().detach()]))
        if up % EVAL_EVERY == 0 or up == n_updates:
            ev = det_eval(eval_env, ac)
            ev.update(up=up, steps=steps_done)
            log["evals"].append(ev)
            if ev["h_eval"] > best_h:
                best_h = ev["h_eval"]
                best_state = {k: v.clone() for k, v in ac.state_dict().items()}
                best_step = steps_done
            print(f"up {up:4d} steps {steps_done / 1e3:6.0f}k  ret40 {mret:6.3f}  "
                  f"apex40 {mapex:.3f}  det h {ev['h_eval']:.4f} "
                  f"(best {best_h:.4f})  sat {ev['sat_frac']:.2f}  "
                  f"bounce {ev['n_bounce']}  std {ac.log_std.exp().detach().numpy().round(3)}",
                  flush=True)
            safe.atomic_json_write(os.path.join(HERE, "p25_c_train_log.json"), log)
            # 플래토 조기 종료
            if steps_done >= PLATEAU_AFTER and len(log["evals"]) > PLATEAU_PATIENCE:
                recent = [e["h_eval"] for e in log["evals"][-PLATEAU_PATIENCE:]]
                prior = max(e["h_eval"] for e in log["evals"][:-PLATEAU_PATIENCE])
                if max(recent) < prior + PLATEAU_DELTA:
                    stop_reason = f"plateau (best {prior:.4f} 이후 {PLATEAU_PATIENCE}회 미개선)"
                    print(f"early stop: {stop_reason}", flush=True)
                    break

    wall = time.time() - t_wall0
    log["final"] = dict(steps=steps_done, wall_s=wall, best_h=best_h,
                        best_step=best_step, stop=stop_reason)
    torch.save(dict(final=ac.state_dict(), best=best_state, best_h=best_h,
                    best_step=best_step, hyper=log["hyper"]),
               os.path.join(HERE, "p25_c_policy.pt"))
    safe.atomic_json_write(os.path.join(HERE, "p25_c_train_log.json"), log)
    print(f"done — steps {steps_done} wall {wall / 60:.1f}min best_h {best_h:.4f} "
          f"({stop_reason})", flush=True)
    make_curve(log)


def make_curve(log):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    st = [u["steps"] / 1e3 for u in log["updates"]]
    ax[0].plot(st, [u["ret40"] for u in log["updates"]], label="에피소드 리턴 (이동40)")
    ax0b = ax[0].twinx()
    l2, = ax0b.plot(st, [u["apex40"] for u in log["updates"]], linestyle="--",
                    color=ax[0]._get_lines.get_next_color(), label="apex_est (이동40)")
    ax[0].set_xlabel("env steps [k]"); ax[0].set_ylabel("리턴")
    ax0b.set_ylabel("apex_est [m]")
    h1, lb1 = ax[0].get_legend_handles_labels()
    ax[0].legend(h1 + [l2], lb1 + [l2.get_label()], loc="lower right", fontsize=8)
    ax[0].set_title("PPO 학습 곡선 (탐사 롤아웃)")
    es = [e["steps"] / 1e3 for e in log["evals"]]
    ax[1].plot(es, [e["h_eval"] for e in log["evals"]], marker="o", ms=3,
               label="det-eval apex (수동연장 실측)")
    if "final" in log:
        ax[1].axhline(log["final"]["best_h"], linestyle=":", alpha=0.6,
                      color=ax[1]._get_lines.get_next_color(),
                      label=f"best {log['final']['best_h']:.3f} m")
    ax[1].set_xlabel("env steps [k]"); ax[1].set_ylabel("h [m]")
    ax[1].legend(fontsize=8); ax[1].set_title("결정론 평가 점프 높이")
    fig.suptitle("P25 Phase C — PPO 파일럿 (p24a 트윈, 점프 태스크)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "p25_c_curve.png"), dpi=130)
    plt.close(fig)
    print("curve saved: p25_c_curve.png", flush=True)


import safe  # noqa: E402  (p25_c_env가 bench 경로 주입 완료)

if __name__ == "__main__":
    main()
