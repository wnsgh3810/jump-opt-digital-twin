# -*- coding: utf-8 -*-
"""t0nc_train — P25-task0: task0 제약판 PPO 학습 (p25_c_train.py 사본 수정).

원본: ../p25_deploy/p25_c_train.py (커스텀 torch PPO, CPU 전용) — 구조/하이퍼 동일.
변경점: env = t0nc_env (task0 클립 25.5810·관절바운드 종료·T-N/dq50 페널티·task0 웅크림),
예산 3M cap (플래토 조기종료 동일: 600k 이후 20회 det-eval 5mm 미개선), 출력 파일명
t0nc_* 고정. det-eval/학습 로그에 task0 페널티 지표 (pen_total/tn_viol/dq_viol) 추가.
시동 전 골든 체크 (run_golden, clip=25.5810 하 비트일치) 통과 필수.
"""
import os
import sys
import time

import numpy as np

import t0nc_env as EV
from t0nc_env import JumpEnv, G
import safe

# torch: MS-Store python site-packages는 MAX_PATH 초과로 wheel 설치 불가(WinError 206)
# → 짧은 경로 전용 설치 (pip --target, 2026-07-17)
sys.path.insert(0, "C:/Users/junho/AppData/Local/torchcpu311")
import torch
import torch.nn as nn

torch.set_num_threads(2)
torch.manual_seed(0)

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("T0_TAG", "")   # 출력 파일명 접미 (병행/재학습 실험용, 기본 "")

# ── 하이퍼파라미터 (선고정 — Phase C와 동일, 예산만 3M) ──
N_ENVS = 4
T_ROLL = 512
TOTAL_STEPS = 3_000_000
GAMMA = 0.999
LAM = 0.95
CLIP_EPS = 0.2
EPOCHS = 10
MB = 256
LR0, LR1 = 3e-4, 1e-4
ENT_COEF = 3e-3
VF_COEF = 0.5
GRAD_CLIP = 0.5
LOG_STD0 = np.log(0.6)
EVAL_EVERY = 10          # 업데이트 단위
PLATEAU_AFTER = 600_000
PLATEAU_PATIENCE = 20    # det-eval 횟수
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

    def mean(self, obs):
        """결정론 액션 — 선형 평균 (v2: tanh 스쿼시 제거 — 천장 ±1 도달성 확보,
        env가 [−1,1] 클립). 초기 가중치가 작아 시작 평균 ≈ 0."""
        return self.pi(obs)

    def dist(self, obs):
        return torch.distributions.Normal(self.mean(obs), self.log_std.exp())

    def value(self, obs):
        return self.v(obs).squeeze(-1)


def det_eval(env, ac):
    """결정론 에피소드 (노이즈 없는 reset, 평균 액션) + 수동 연장 → 실측 apex."""
    obs = env.reset()
    ep_ret = 0.0
    info = {}
    while True:
        with torch.no_grad():
            mu = ac.mean(torch.as_tensor(obs, dtype=torch.float32))
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
                pen_total=float(info.get("pen_total", np.nan)),
                tn_viol_frac=float(info.get("tn_viol_frac", np.nan)),
                dq_viol_frac=float(info.get("dq_viol_frac", np.nan)),
                tau_viol_frac=float(info.get("tau_viol_frac", np.nan)),
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
        ent=ENT_COEF, vf=VF_COEF, log_std0=float(LOG_STD0),
        clip_raw=float(EV.R19.CLIP),
        net="MLP 2x64 tanh (mean linear out, v2)", n_params=int(n_par),
        task0=dict(w_tn=EV.W_TN, w_dq=EV.W_DQ, w_tau=EV.W_TAU,
                   m_tn=EV.M_TN, m_tau=EV.M_TAU,
                   q1_bounds=[EV.T0.Q1_LB, EV.T0.Q1_UB],
                   q2_bounds=[EV.T0.Q2_LB, EV.T0.Q2_UB],
                   crouch=list(EV.CROUCH_T0),
                   tn=[EV.T0.TN_COEF, EV.T0.TN_OFF], dq_lim=EV.T0.DQ_LIM),
        reward=dict(shaping="APEX_W*d(running_max_bz) v2", apex_w=EV.APEX_W,
                    terminal="APEX_W*max(0, ballistic_apex - running_max)",
                    tau_pen=EV.TAU_PEN, slip_pen=EV.SLIP_PEN,
                    range_pen=EV.RANGE_PEN, crash_pen=EV.CRASH_PEN,
                    t0_pen="w_tn/w_dq * viol^2 per substep, / (n_ep*nsub) "
                           "(= t0_spec.penalty 창 평균 규모)")))
    best_h, best_state, best_step = -1.0, None, 0
    ep_rets = [0.0] * N_ENVS
    fin_ret, fin_apex, fin_sat, fin_pen = [], [], [], []
    steps_done = 0
    stop_reason = "budget"
    print(f"PPO start — {n_updates} updates × batch {N_ENVS * T_ROLL} "
          f"(net {n_par} params, clip={EV.R19.CLIP})", flush=True)

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
                    fin_pen.append(info.get("pen_total", 0.0))
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
        mpen = float(np.mean(fin_pen[-40:])) if fin_pen else float("nan")
        log["updates"].append(dict(up=up, steps=steps_done, ret40=mret,
                                   apex40=mapex, sat40=msat, pen40=mpen,
                                   std=[float(x) for x in ac.log_std.exp().detach()]))
        if up % EVAL_EVERY == 0 or up == n_updates:
            ev = det_eval(eval_env, ac)
            ev.update(up=up, steps=steps_done)
            log["evals"].append(ev)
            if ev["h_eval"] > best_h:
                best_h = ev["h_eval"]
                best_state = {k: v.clone() for k, v in ac.state_dict().items()}
                best_step = steps_done
            # 매 eval 체크포인트 (외부 kill 대비 — final 슬롯에 현 상태)
            torch.save(dict(final=ac.state_dict(), best=best_state, best_h=best_h,
                            best_step=best_step, steps=steps_done,
                            hyper=log["hyper"]),
                       os.path.join(HERE, f"t0nc_ppo_policy{TAG}.pt"))
            print(f"up {up:4d} steps {steps_done / 1e3:6.0f}k  ret40 {mret:6.3f}  "
                  f"apex40 {mapex:.3f}  pen40 {mpen:.4f}  det h {ev['h_eval']:.4f} "
                  f"(best {best_h:.4f})  pen {ev['pen_total']:.4f}  "
                  f"tnv {ev['tn_viol_frac']:.3f}  sat {ev['sat_frac']:.2f}  "
                  f"bounce {ev['n_bounce']}  std {ac.log_std.exp().detach().numpy().round(3)}",
                  flush=True)
            safe.atomic_json_write(os.path.join(HERE, f"t0nc_train_log{TAG}.json"), log)
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
               os.path.join(HERE, f"t0nc_ppo_policy{TAG}.pt"))
    safe.atomic_json_write(os.path.join(HERE, f"t0nc_train_log{TAG}.json"), log)
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
    ax1b = ax[1].twinx()
    lp, = ax1b.plot(es, [e["pen_total"] for e in log["evals"]], linestyle="--",
                    color=ax[1]._get_lines.get_next_color(),
                    label="task0 페널티 (det)")
    ax1b.set_ylabel("pen_total")
    if "final" in log:
        ax[1].axhline(log["final"]["best_h"], linestyle=":", alpha=0.6,
                      color=ax[1]._get_lines.get_next_color(),
                      label=f"best {log['final']['best_h']:.3f} m")
    ax[1].set_xlabel("env steps [k]"); ax[1].set_ylabel("h [m]")
    h1, lb1 = ax[1].get_legend_handles_labels()
    ax[1].legend(h1 + [lp], lb1 + [lp.get_label()], fontsize=8)
    ax[1].set_title("결정론 평가 점프 높이")
    fig.suptitle("P25-task0 — PPO (task0 제약: |â|≤15Nm·T-N·dq50·관절바운드, no_cvt)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, f"t0nc_ppo_curve{TAG}.png"), dpi=130)
    plt.close(fig)
    print(f"curve saved: t0nc_ppo_curve{TAG}.png", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        TOTAL_STEPS = int(sys.argv[1])          # smoke: python t0nc_train.py 40960
    main()
