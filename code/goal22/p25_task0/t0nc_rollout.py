# -*- coding: utf-8 -*-
"""t0nc_rollout — P25-task0: 최종 결정론 정책 롤아웃 → npz + t0_spec 감사 json.

원본: ../p25_deploy/p25_c_rollout.py — 롤아웃 규약 동일 (학습 env와 동일 경로,
범위 이탈 시 능동 중단 → 수동 연장 0.6s, h_plan = 실측 max bz).
변경점: 출력 t0nc_ppo.npz(final) / t0nc_ppo_best.npz(best, 무조건 저장) /
t0nc_ppo_audit.json (t0_spec.audit 전 항목 + 스탠스 시간 + T-N 활성/천장 라이딩 통계
+ 학습 통계) / t0nc_ppo_traj.png. 감사는 final·best 각각 수행,
t0_spec.audit()["pass"]=True + 스탠스 ≤0.3s가 캠페인 통과 조건.
npz 스키마 = Phase A 호환: t/q1/q2/dq1/dq2/raw1/raw2/tau1_nm/tau2_nm/bz/grf
+ qd1/qd2/dqd1/dqd2 := q/dq + cmd_raw1/cmd_raw2 + h_plan.
"""
import os
import sys
import json
import time

import numpy as np

import t0nc_env as EV
from t0nc_env import JumpEnv, G
import t0nc_train as TR
import t0_spec as T0
import safe

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get("T0_TAG", "")
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
            range_viol = dict(k_ctrl=kc, t=float((kc + 1) * env.ctrl_dt),
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
    # T-N 포락선 활성/위반 통계 (능동 구간, 감사와 동일 표본)
    for j, (dqk, shk) in enumerate((("dq1", "tau1_nm"), ("dq2", "tau2_nm")), 1):
        gap = T0.tn_gap(Lg[dqk][ma], Lg[shk][ma])
        st[f"tn_gap_max_{j}"] = float(gap.max())
        for th in (0.5, 1.0, 2.0, 5.0):
            st[f"tn_active{th}_frac_{j}"] = float(np.mean(gap >= -th))
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
    # 스탠스 시간 (t=0 접지 시작 → 첫 이지) — t0_spec 감사 항목 (≤ 0.3s)
    st["t_stance"] = st["t_liftoff"]
    st["stance_ok"] = bool(st["t_stance"] <= T0.T_ST_MAX) if np.isfinite(st["t_stance"]) else False
    return st


def main():
    t0 = time.time()
    EV.setup()
    golden = EV.run_golden()   # 롤아웃 시점 재검증 (clip=25.5810 비트일치 포함)
    ck = torch.load(os.path.join(HERE, f"t0nc_ppo_policy{TAG}.pt"), weights_only=False)
    tlog = json.load(open(os.path.join(HERE, f"t0nc_train_log{TAG}.json"), encoding="utf-8"))
    ck_clip = ck.get("hyper", {}).get("clip_raw", None)
    assert ck_clip is not None and abs(ck_clip - float(EV.R19.CLIP)) < 1e-9, \
        f"클립 불일치: 체크포인트 {ck_clip} vs 현재 env {EV.R19.CLIP} (P25_CLIP_RAW 확인)"
    cdt = float(os.environ.get("T0_CTRL_DT_MS", "2")) / 1000.0   # 0.5ms 수확용
    env = JumpEnv(seed=12345, reset_noise=False, ctrl_dt=cdt)
    n_act = env.n_ep * env.nsub
    out = {}
    hid = int(ck.get("hyper", {}).get("hid", 64))   # nc05(128) 등 넷 크기 호환
    for tag in ("final", "best"):
        ac = TR.ActorCritic(hid=hid)
        ac.load_state_dict(ck[tag] if ck[tag] is not None else ck["final"])
        ac.eval()
        Lg, k_rec, rv, contact = det_rollout(env, ac)
        h_plan = float(Lg["bz"][1:k_rec].max()) if k_rec > 1 else float("nan")
        st = stats_of(Lg, contact, n_act, env.dt)
        # ── t0_spec 감사 (커맨드 창 t≤0.6, cvt=False) ──
        L = dict(t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
                 sh1=Lg["tau1_nm"], sh2=Lg["tau2_nm"])
        aud = T0.audit(L, t_end=EV.EP_T, cvt=False)
        pass_all = bool(aud["pass"] and st["stance_ok"] and rv is None)
        out[tag] = dict(h_plan=h_plan, range_viol=rv, stats=st, audit=aud,
                        pass_all=pass_all, Lg=Lg, k_rec=k_rec)
        print(f"[{tag}] h_plan={h_plan:.4f} liftoff={st['t_liftoff']:.3f}s "
              f"apex@{st['t_apex']:.3f}s hops={st['n_hops_before_apex']} "
              f"ceil(raw1/raw2)={st['ceil_frac_raw1']:.2f}/{st['ceil_frac_raw2']:.2f} "
              f"audit_pass={aud['pass']} stance_ok={st['stance_ok']} "
              f"range_viol={rv}", flush=True)
        for k in ("tau_hip", "tau_knee", "tn_hip", "tn_knee", "dq_hip", "dq_knee",
                  "q1_lo", "q1_hi", "q2_lo", "q2_hi"):
            print(f"    audit {k:8s} = {aud[k]:+.4f}  "
                  f"({'OK' if aud[k] <= 1e-6 else 'VIOL'})", flush=True)

    # ── npz (final = 정본, best = 무조건 별도 저장) ──
    def save_npz(path, R):
        Lg = R["Lg"]
        np.savez(path, t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"],
                 dq2=Lg["dq2"], raw1=Lg["raw1"], raw2=Lg["raw2"],
                 tau1_nm=Lg["tau1_nm"], tau2_nm=Lg["tau2_nm"], bz=Lg["bz"],
                 grf=Lg["grf"], cmd_raw1=Lg["cmd_raw1"], cmd_raw2=Lg["cmd_raw2"],
                 qd1=Lg["q1"], qd2=Lg["q2"], dqd1=Lg["dq1"], dqd2=Lg["dq2"],
                 h_plan=float(R["h_plan"]))
    save_npz(os.path.join(HERE, f"t0nc_ppo{TAG}.npz"), out["final"])
    save_npz(os.path.join(HERE, f"t0nc_ppo_best{TAG}.npz"), out["best"])
    files = dict(npz=f"t0nc_ppo{TAG}.npz", npz_best=f"t0nc_ppo_best{TAG}.npz",
                 curve="t0nc_ppo_curve.png", policy=f"t0nc_ppo_policy{TAG}.pt",
                 train_log=f"t0nc_train_log{TAG}.json", traj=f"t0nc_ppo_traj{TAG}.png")
    fin = tlog.get("final", {})
    steps = fin.get("steps")
    n_ep_rl = int(steps / env.n_ep) if steps else None
    caveats = [
        "P25-task0 캠페인 — 제약은 AVT LEG task0_vertjump_no_cvt 기준 (t0_spec): "
        "|â|≤15Nm(raw 박스 25.5810) · T-N |dq|≤-0.731|â|+48.48 · |dq|≤50 · "
        "q1∈[-1.2566,-0.2967] q2∈[-2.5482,-0.6283] · 스탠스≤0.3s(감사)",
        "관절바운드 = 학습 종료조건(hard-ish), T-N/dq50 = 스텝당 위반량² 소프트 페널티 "
        "(w=50, t0_spec.penalty 규모) — task0(NLP)의 hard 제약과 처리 방식이 달라 "
        "h_plan 직접 비교에 유의",
        "토크 박스는 공급 클립 25.5810이 구조적으로 강제 (a_hat 운동방향 가지 15.00Nm "
        "— 제동 가지에서 |â|가 15를 넘을 수 있는지는 감사(tau_hip/tau_knee)로 확인)",
        "시작 웅크림 = task0 초기추정 (q1=-0.32, q2=-2.50) settle — task0은 시작 자세도 "
        "최적화 대상(바운드 내 자유)이므로 본 캠페인은 그 부분공간의 한 점에서 출발",
        "학습 중 apex 보상은 탄도 외삽 추정, 본 h_plan은 수동 연장 0.6s 실측",
        "감사 창(t≤0.6s)은 이륙 후 공중 자세까지 포함 — task0 NLP는 스탠스 구간만 "
        "제약하므로 본 감사가 더 엄격한 쪽",
    ]
    for tag in ("final", "best"):
        if out[tag]["range_viol"]:
            caveats.append(f"{tag} 정책 롤아웃 중 관절범위 이탈: {out[tag]['range_viol']}")
        hops = out[tag]["stats"]["n_hops_before_apex"]
        if hops > 0:
            caveats.append(f"{tag}: apex 전 재접촉(바운스) {hops}회 — bz 트레이스 확인 필요")
    res = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        campaign="P25-task0 no_cvt (PPO 재학습, task0 제약)",
        method="ppo",
        clip_raw=float(EV.R19.CLIP),
        h_plan=out["final"]["h_plan"],
        h_plan_best_ckpt=out["best"]["h_plan"],
        audit_final={k: v for k, v in out["final"]["audit"].items()},
        audit_best={k: v for k, v in out["best"]["audit"].items()},
        pass_final=out["final"]["pass_all"],
        pass_best=out["best"]["pass_all"],
        stance_final=dict(t_stance=out["final"]["stats"]["t_stance"],
                          ok=out["final"]["stats"]["stance_ok"], max=T0.T_ST_MAX),
        stance_best=dict(t_stance=out["best"]["stats"]["t_stance"],
                         ok=out["best"]["stats"]["stance_ok"], max=T0.T_ST_MAX),
        stats_final=out["final"]["stats"],
        stats_best=out["best"]["stats"],
        range_viol_final=out["final"]["range_viol"],
        range_viol_best=out["best"]["range_viol"],
        training=dict(steps=steps, episodes=n_ep_rl, wall_s=fin.get("wall_s"),
                      stop=fin.get("stop"), best_h_during_train=fin.get("best_h"),
                      best_step=fin.get("best_step"),
                      n_updates=len(tlog.get("updates", [])),
                      n_evals=len(tlog.get("evals", []))),
        hyper=tlog.get("hyper"),
        golden=golden,
        env=dict(ctrl_dt=env.ctrl_dt, ep_t=EV.EP_T, sim_dt=env.dt,
                 crouch=list(G["CROUCH"]), crouch_sub=G["CROUCH_SUB"],
                 q1_range=[float(x) for x in G["Q1R"]],
                 q2_range=[float(x) for x in G["Q2R"]],
                 obs="[(bz-0.6)/0.4, q1/1.5, q2/1.5, dq1/10, dq2/10, vbz/3, t/0.6]",
                 action=f"raw torque (2,) [-{EV.R19.CLIP},{EV.R19.CLIP}] → "
                        "tm필터→클립→ahat→supp/rise/스프링/힙층",
                 w_tn=EV.W_TN, w_dq=EV.W_DQ, w_tau=EV.W_TAU, m_tn=EV.M_TN, m_tau=EV.M_TAU,
                 reset_noise=dict(q_std=EV.NOISE_Q, dq_std=EV.NOISE_DQ)),
        caveats=caveats,
        files=files,
        wall_s_rollout=time.time() - t0)
    safe.atomic_json_write(os.path.join(HERE, f"t0nc_ppo_audit{TAG}.json"), res)
    make_traj_fig(out["final"]["Lg"], out["final"]["h_plan"], n_act)
    print(f"saved: t0nc_ppo{TAG}.npz / t0nc_ppo_best{TAG}.npz / t0nc_ppo_audit{TAG}.json / "
          f"t0nc_ppo_traj{TAG}.png [{time.time() - t0:.0f}s]", flush=True)
    print(f"PASS(final)={out['final']['pass_all']} PASS(best)={out['best']['pass_all']}",
          flush=True)


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
    for b in (T0.Q1_LB, T0.Q1_UB, T0.Q2_LB, T0.Q2_UB):
        ax[0, 1].axhline(b, linestyle=":", alpha=0.35)
    ax[0, 1].set_title("관절각 [rad] (점선 = task0 바운드)"); ax[0, 1].legend(fontsize=8)
    ax[1, 0].plot(t, Lg["tau1_nm"], label="â1 (hip)")
    ax[1, 0].plot(t, Lg["tau2_nm"], label="â2 (knee)")
    ax[1, 0].axhline(15.0, linestyle=":", alpha=0.5)
    ax[1, 0].axhline(-15.0, linestyle=":", alpha=0.5)
    ax[1, 0].set_title("축토크 â [Nm] (점선 = ±15)"); ax[1, 0].legend(fontsize=8)
    # T-N 평면 (능동 구간)
    ma = slice(0, n_act)
    tr = np.linspace(0, 16, 50)
    ax[1, 1].plot(tr, T0.TN_COEF * tr + T0.TN_OFF, linestyle="--", alpha=0.5,
                  label="T-N 한계")
    ax[1, 1].plot(np.abs(Lg["tau1_nm"][ma]), np.abs(Lg["dq1"][ma]), ".", ms=2,
                  label="hip")
    ax[1, 1].plot(np.abs(Lg["tau2_nm"][ma]), np.abs(Lg["dq2"][ma]), ".", ms=2,
                  label="knee")
    ax[1, 1].axhline(T0.DQ_LIM, linestyle=":", alpha=0.5)
    ax[1, 1].set_xlabel("|â| [Nm]"); ax[1, 1].set_ylabel("|dq| [rad/s]")
    ax[1, 1].set_title("T-N 포락선 체크"); ax[1, 1].legend(fontsize=8)
    for a in ax.flat[:3]:
        a.set_xlabel("t [s]")
    fig.suptitle("P25-task0 — PPO 최종 결정론 롤아웃 (task0 제약, no_cvt)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, f"t0nc_ppo_traj{TAG}.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
