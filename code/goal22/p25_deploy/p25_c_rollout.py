# -*- coding: utf-8 -*-
"""p25_c_rollout — Phase C 최종 결정론 정책 롤아웃 → Phase A 호환 npz + 결과 json.

npz 스키마 = Phase A(p25_a_*.npz)와 동일 키: t/q1/q2/dq1/dq2/raw1/raw2/tau1_nm/tau2_nm/
bz/grf (t: 0→1.1995s, dt=0.5ms, active 0.6s + 수동 연장 0.6s; raw = tm 필터+클립 후
적용 커맨드, 연장 구간 0) + Phase D 소비용 qd1/qd2/dqd1/dqd2 := q/dq (q_des:=q 규약)
+ RL 전용 cmd_raw1/cmd_raw2 (정책 ZOH 원커맨드, 필터 전).
롤아웃 규약: 학습 env와 동일 (범위 이탈 시 그 시점에서 능동 중단 → 수동 연장; 발생 여부
results.caveats에 기록). h_plan = max bz (t>0, 연장 포함) — det_eval의 탄도 추정이 아닌 실측.
"""
import os
import sys
import json
import time

import numpy as np

import p25_c_env as EV
from p25_c_env import JumpEnv, G
import p25_c_train as TR
import safe

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
T_AFTER = 0.6


def det_rollout(env, ac, record=True):
    """결정론 에피소드 (평균 액션) — 서브스텝 해상도 기록 + 수동 연장."""
    obs = env.reset()
    dt = env.dt
    n_act = env.n_ep * env.nsub
    n_tot = n_act + int(round(T_AFTER / dt))
    Lg = {k: np.zeros(n_tot) for k in
          ["q1", "q2", "dq1", "dq2", "raw1", "raw2", "tau1_nm", "tau2_nm",
           "bz", "grf", "cmd_raw1", "cmd_raw2"]}
    tl = np.arange(n_tot) * dt
    k_sub = 0
    range_viol = None
    contact = []
    # ── 능동 0.6s ──
    for kc in range(env.n_ep):
        with torch.no_grad():
            mu = ac.mean(torch.as_tensor(obs, dtype=torch.float32))
        a = np.clip(mu.numpy(), -1.0, 1.0)
        c1_cmd = float(a[0]) * EV.R19.CLIP
        c2_cmd = float(a[1]) * EV.R19.CLIP
        for _ in range(env.nsub):
            q1c, q2c, v1c, v2c = env._read()
            r = env._layer_step(c1_cmd, c2_cmd, v1c, v2c, settle=False)
            assert r is not None, "결정론 롤아웃 발산"
            s1, s2, c1, c2 = r
            q1c, q2c, v1c, v2c = env._read()
            Lg["q1"][k_sub] = q1c; Lg["q2"][k_sub] = q2c
            Lg["dq1"][k_sub] = v1c; Lg["dq2"][k_sub] = v2c
            Lg["raw1"][k_sub] = c1; Lg["raw2"][k_sub] = c2
            Lg["tau1_nm"][k_sub] = s1; Lg["tau2_nm"][k_sub] = s2
            Lg["cmd_raw1"][k_sub] = c1_cmd; Lg["cmd_raw2"][k_sub] = c2_cmd
            Lg["bz"][k_sub] = env.md.qpos[0]
            Lg["grf"][k_sub] = EV.RU._grf_z(env.model, env.md)
            contact.append(env.md.ncon > 0)
            k_sub += 1
        env.k += 1
        obs = env._obs()
        q1c, q2c, _, _ = env._read()
        if not (G["Q1R"][0] <= q1c <= G["Q1R"][1]) or \
           not (G["Q2R"][0] <= q2c <= G["Q2R"][1]):
            range_viol = dict(k_ctrl=kc, t=float((kc + 1) * EV.CTRL_DT),
                              q1=float(q1c), q2=float(q2c))
            break
    # ── 수동 연장 (a_full23 기록 끝 이후 규약: s=0, 무릎 extra=LAW_A, 힙 e1=a1) ──
    law_a = G["LAW"][0]
    e1 = EV.RU.HIP["a1"] if EV.RU.HIP_LAW else 0.0
    md, mj, model = env.md, env.mj, env.model
    while k_sub < n_tot:
        md.ctrl[:] = [-e1, -law_a]
        md.qfrc_applied[env.dof_knee] = 0.0
        try:
            mj.mj_step(model, md)
        except Exception:
            break
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            break
        q1c, q2c, v1c, v2c = env._read()
        Lg["q1"][k_sub] = q1c; Lg["q2"][k_sub] = q2c
        Lg["dq1"][k_sub] = v1c; Lg["dq2"][k_sub] = v2c
        Lg["bz"][k_sub] = md.qpos[0]
        Lg["grf"][k_sub] = EV.RU._grf_z(model, md)
        contact.append(md.ncon > 0)
        k_sub += 1
    Lg["t"] = tl
    return Lg, k_sub, range_viol, np.array(contact, bool)


def stats_of(Lg, contact, n_act, dt):
    ma = slice(0, n_act)   # 능동 구간
    st = dict(
        peak_raw1=float(np.abs(Lg["raw1"][ma]).max()),
        peak_raw2=float(np.abs(Lg["raw2"][ma]).max()),
        peak_tau1_nm=float(np.abs(Lg["tau1_nm"][ma]).max()),
        peak_tau2_nm=float(np.abs(Lg["tau2_nm"][ma]).max()),
        peak_dq1=float(np.abs(Lg["dq1"]).max()),
        peak_dq2=float(np.abs(Lg["dq2"]).max()),
        ceil_frac_raw1=float(np.mean(np.abs(Lg["raw1"][ma]) >= EV.R19.CLIP - 0.1)),
        ceil_frac_raw2=float(np.mean(np.abs(Lg["raw2"][ma]) >= EV.R19.CLIP - 0.1)),
        ceil_frac_cmd1=float(np.mean(np.abs(Lg["cmd_raw1"][ma]) >= 0.95 * EV.R19.CLIP)),
        ceil_frac_cmd2=float(np.mean(np.abs(Lg["cmd_raw2"][ma]) >= 0.95 * EV.R19.CLIP)))
    # 접촉 전이 분석 (바운스 착취 감시)
    c = contact
    trans_up = np.where(c[:-1] & ~c[1:])[0]          # 접촉→공중 (이지)
    trans_dn = np.where(~c[:-1] & c[1:])[0]          # 공중→접촉 (착지/재접촉)
    i_apex = int(np.argmax(Lg["bz"][:len(c)]))
    st["n_liftoffs"] = int(len(trans_up))
    st["n_touchdowns"] = int(len(trans_dn))
    st["n_hops_before_apex"] = int(np.sum(trans_dn < i_apex))   # apex 전 재접촉 = 바운스
    st["t_liftoff"] = float(trans_up[0] * dt) if len(trans_up) else float("nan")
    st["t_liftoff_last_before_apex"] = float(
        trans_up[trans_up < i_apex][-1] * dt) if np.any(trans_up < i_apex) else float("nan")
    st["t_apex"] = float(i_apex * dt)
    return st


def main():
    t0 = time.time()
    EV.setup()
    ck = torch.load(os.path.join(HERE, "p25_c_policy.pt"), weights_only=False)
    tlog = json.load(open(os.path.join(HERE, "p25_c_train_log.json"), encoding="utf-8"))
    env = JumpEnv(seed=12345, reset_noise=False)
    n_act = env.n_ep * env.nsub
    out = {}
    for tag in ("final", "best"):
        ac = TR.ActorCritic()
        ac.load_state_dict(ck[tag] if ck[tag] is not None else ck["final"])
        ac.eval()
        Lg, k_rec, rv, contact = det_rollout(env, ac)
        h_plan = float(Lg["bz"][1:k_rec].max()) if k_rec > 1 else float("nan")
        st = stats_of(Lg, contact, n_act, env.dt)
        out[tag] = dict(h_plan=h_plan, range_viol=rv, stats=st, Lg=Lg, k_rec=k_rec)
        print(f"[{tag}] h_plan={h_plan:.4f} liftoff={st['t_liftoff']:.3f}s "
              f"apex@{st['t_apex']:.3f}s hops_before_apex={st['n_hops_before_apex']} "
              f"ceil(raw1/raw2)={st['ceil_frac_raw1']:.2f}/{st['ceil_frac_raw2']:.2f} "
              f"range_viol={rv}", flush=True)
    # ── npz (최종 정책 = 정본; best가 5mm 이상 높으면 별도 저장) ──
    def save_npz(path, R):
        Lg = R["Lg"]
        np.savez(path, t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"],
                 dq2=Lg["dq2"], raw1=Lg["raw1"], raw2=Lg["raw2"],
                 tau1_nm=Lg["tau1_nm"], tau2_nm=Lg["tau2_nm"], bz=Lg["bz"],
                 grf=Lg["grf"], cmd_raw1=Lg["cmd_raw1"], cmd_raw2=Lg["cmd_raw2"],
                 qd1=Lg["q1"], qd2=Lg["q2"], dqd1=Lg["dq1"], dqd2=Lg["dq2"])
    save_npz(os.path.join(HERE, "p25_c_ppo.npz"), out["final"])
    files = dict(npz="p25_c_ppo.npz", curve="p25_c_curve.png",
                 policy="p25_c_policy.pt", train_log="p25_c_train_log.json")
    if out["best"]["h_plan"] > out["final"]["h_plan"] + 0.005:
        save_npz(os.path.join(HERE, "p25_c_ppo_best.npz"), out["best"])
        files["npz_best"] = "p25_c_ppo_best.npz"
    # ── Phase A 대비 (표본 효율 — 존재하는 결과만) ──
    comp = {}
    for meth, f in (("ol_cma", "p25_a_res_ol.json"), ("mppi", "p25_a_res_mppi.json"),
                    ("cl_cma", "p25_a_res_cl.json")):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            r = json.load(open(p, encoding="utf-8"))
            comp[meth] = dict(h_plan=r.get("h_plan"),
                              evals=r.get("evals", r.get("stats", {}).get("evals")))
    fin = tlog.get("final", {})
    steps = fin.get("steps")
    n_ep_rl = int(steps / env.n_ep) if steps else None
    # ── 정직 노트 ──
    caveats = [
        "RL 파일럿 — 보상 shaping(Δbz+apex 보너스)·범위 종료 페널티가 목적을 근사할 뿐, "
        "제약 엄수(관절범위/미끄럼)는 소프트 페널티임",
        "학습 중 apex 보상은 탄도 외삽 추정(bz+vz²/2g), 본 h_plan은 수동 연장 0.6s 실측",
        f"시작 웅크림 = 0602 첫 trial의 qd(0) settle (Phase A twin은 측정 q(0) — "
        f"양쪽 settle 수렴 자세 차이는 mm 수준)",
        "에피소드 0.6s 고정 — 이지 후 잔여 시간의 Δbz shaping이 자세 정리와 무관한 "
        "관성 활용을 이미 포함",
    ]
    if out["final"]["range_viol"]:
        caveats.append(f"최종 정책 롤아웃 중 관절범위 이탈 발생: {out['final']['range_viol']}")
    hops = out["final"]["stats"]["n_hops_before_apex"]
    if hops > 0:
        caveats.append(f"apex 전 재접촉(바운스) {hops}회 — 접촉모델 착취 가능성, bz 트레이스 확인 필요")
    res = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        method="ppo",
        note="PPO 파일럿 (Phase C) — 커스텀 torch PPO, MLP 2x64, p24a 트윈 전 층 미러 env",
        h_plan=out["final"]["h_plan"],
        h_plan_best_ckpt=out["best"]["h_plan"],
        stats=out["final"]["stats"],
        training=dict(steps=steps, episodes=n_ep_rl, wall_s=fin.get("wall_s"),
                      stop=fin.get("stop"), best_h_during_train=fin.get("best_h"),
                      best_step=fin.get("best_step"),
                      n_updates=len(tlog.get("updates", [])),
                      n_evals=len(tlog.get("evals", []))),
        hyper=tlog.get("hyper"),
        golden=tlog.get("golden"),
        env=dict(ctrl_dt=EV.CTRL_DT, ep_t=EV.EP_T, sim_dt=env.dt,
                 crouch=G["CROUCH"], crouch_sub=G["CROUCH_SUB"],
                 q1_range=[float(x) for x in G["Q1R"]],
                 q2_range=[float(x) for x in G["Q2R"]],
                 obs="[(bz-0.6)/0.4, q1/1.5, q2/1.5, dq1/10, dq2/10, vbz/3, t/0.6]",
                 action="raw torque (2,) [-35.5,35.5] → tm필터→클립→ahat→supp/rise/스프링/힙층",
                 reset_noise=dict(q_std=EV.NOISE_Q, dq_std=EV.NOISE_DQ)),
        phase_a_comparison=comp,
        caveats=caveats,
        files=files,
        wall_s_rollout=time.time() - t0)
    safe.atomic_json_write(os.path.join(HERE, "p25_c_results.json"), res)
    make_traj_fig(out["final"]["Lg"], out["final"]["h_plan"], n_act)
    print(f"saved: p25_c_ppo.npz / p25_c_results.json / p25_c_traj.png "
          f"[{time.time() - t0:.0f}s]", flush=True)


def make_traj_fig(Lg, h_plan, n_act):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    t = Lg["t"]
    fig, ax = plt.subplots(2, 2, figsize=(11, 7))
    ax[0, 0].plot(t, Lg["bz"], label="bz")
    ax[0, 0].axhline(h_plan, linestyle=":", alpha=0.6, label=f"apex {h_plan:.3f} m")
    ax[0, 0].axvline(t[n_act - 1], linestyle="--", alpha=0.4)
    ax[0, 0].set_title("베이스 높이"); ax[0, 0].legend(fontsize=8)
    ax[0, 1].plot(t, Lg["q1"], label="q1")
    ax[0, 1].plot(t, Lg["q2"], label="q2")
    ax[0, 1].set_title("관절각 [rad]"); ax[0, 1].legend(fontsize=8)
    ax[1, 0].plot(t, Lg["raw1"], label="raw1 (적용)")
    ax[1, 0].plot(t, Lg["raw2"], label="raw2 (적용)")
    ax[1, 0].axhline(35.5, linestyle=":", alpha=0.5)
    ax[1, 0].axhline(-35.5, linestyle=":", alpha=0.5)
    ax[1, 0].set_title("raw 토크 명령 (필터+클립 후)"); ax[1, 0].legend(fontsize=8)
    ax[1, 1].plot(t, Lg["grf"], label="GRF z")
    ax[1, 1].set_title("접촉력 z 합 [N]"); ax[1, 1].legend(fontsize=8)
    for a in ax.flat:
        a.set_xlabel("t [s]")
    fig.suptitle("P25 Phase C — PPO 최종 결정론 롤아웃 (p24a 트윈)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "p25_c_traj.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
