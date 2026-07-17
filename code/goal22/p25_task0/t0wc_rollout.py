# -*- coding: utf-8 -*-
"""t0wc_rollout — P25-task0: l_i-조건부 PPO 정책 → h(l_i) 평가 곡선 + 최적 l_i* 롤아웃.

원본: t0nc_rollout.py (결정론 롤아웃 + t0_spec 감사 규약 동일). 변경점:
  1. 평가 곡선: l_i ∈ [15,30]mm 1mm 그리드 + 검증앵커 25.08 → 각 점 결정론 롤아웃
     (final·best 체크포인트 각각) → h(l_i) → RL 자체의 l_i* = argmax
     (campaign-pass 점 우선: t0_spec.audit(cvt=True) + 스탠스≤0.3s + 범위이탈 없음).
  2. 각 점 t0_spec.audit(cvt=True) 통과 여부 + l_i<25.08 외삽 플래그 표기.
  3. 산출: t0wc_ppo.npz (l_i* 롤아웃, t0wc 스키마 + qm/l_i/h_plan) ·
     t0wc_ppo_audit.json (audit + l_i* + h(l_i) 곡선 데이터 + CMA 비교) ·
     t0wc_ppo_licurve.png (h vs l_i — 검증앵커 25.08/30 + AVT 25.161 참조선 +
     외삽 음영 + CMA 앵커점).
"""
import os
import sys
import json
import time

import numpy as np

import t0wc_env as EV
from t0wc_env import JumpEnv
import t0wc_train as TR
import t0_spec as T0
import safe

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
# 고정-l_i 폴백 모드 (t0wc_train과 동일 규약): 평가 = 그 1점만, 파일 접미 자동
LI_FIX = os.environ.get("T0_LI_FIXED")
LI_FIX = EV.quant_mm(float(LI_FIX)) if LI_FIX else None
TAG = os.environ.get("T0_TAG", "")
if LI_FIX is not None and not TAG:
    TAG = "_lifix" + f"{LI_FIX:g}".replace(".", "p")
T_AFTER = 0.6
LIS_EVAL = [LI_FIX] if LI_FIX is not None else \
    sorted(set([float(x) for x in range(15, 31)] + [EV.LI_FIT_MM]))
AVT_OPT_MM = 25.161            # AVT 해석모델 최적 (참조선)


def det_rollout(env, ac):
    """결정론 에피소드 (평균 액션) — 서브스텝 해상도 기록 + 수동 연장 (t0nc 규약,
    관절범위 q2측 = 크랭크 QM 바운드)."""
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
        if not (T0.Q1_LB <= q1c <= T0.Q1_UB) or \
           not (T0.QM_LB <= q2c <= T0.QM_UB):
            range_viol = dict(k_ctrl=kc, t=float((kc + 1) * EV.CTRL_DT),
                              q1=float(q1c), qm=float(q2c))
            break
    # ── 수동 연장 (기록 끝 이후 규약: s=0, 무릎 extra=LAW_A, 힙 e1=a1, qfrc=0) ──
    law_a = EV.W.G["LAW"][0]
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
    for j, (dqk, shk) in enumerate((("dq1", "tau1_nm"), ("dq2", "tau2_nm")), 1):
        gap = T0.tn_gap(Lg[dqk][ma], Lg[shk][ma])
        st[f"tn_gap_max_{j}"] = float(gap.max())
        for th in (0.5, 1.0, 2.0, 5.0):
            st[f"tn_active{th}_frac_{j}"] = float(np.mean(gap >= -th))
    c = contact
    trans_up = np.where(c[:-1] & ~c[1:])[0]
    trans_dn = np.where(~c[:-1] & c[1:])[0]
    i_apex = int(np.argmax(Lg["bz"][:len(c)]))
    st["n_liftoffs"] = int(len(trans_up))
    st["n_touchdowns"] = int(len(trans_dn))
    st["n_hops_before_apex"] = int(np.sum(trans_dn < i_apex))
    st["t_liftoff"] = float(trans_up[0] * dt) if len(trans_up) else float("nan")
    st["t_apex"] = float(i_apex * dt)
    st["t_stance"] = st["t_liftoff"]
    st["stance_ok"] = bool(st["t_stance"] <= T0.T_ST_MAX) if np.isfinite(st["t_stance"]) else False
    return st


def eval_point(env, ac, li_mm):
    """한 l_i 점 결정론 롤아웃 → (row dict, Lg)."""
    env.li_fixed = li_mm
    Lg, k_rec, rv, contact = det_rollout(env, ac)
    n_act = env.n_ep * env.nsub
    h_plan = float(Lg["bz"][1:k_rec].max()) if k_rec > 1 else float("nan")
    st = stats_of(Lg, contact, n_act, env.dt)
    L = dict(t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             sh1=Lg["tau1_nm"], sh2=Lg["tau2_nm"])
    aud = T0.audit(L, t_end=EV.EP_T, cvt=True)
    li_q = EV.quant_mm(li_mm)
    rmin, rmax = EV.W.r_range_of(Lg, EV.li_m(li_mm))
    row = dict(l_i_mm=li_q,
               h_plan=h_plan,
               bz_settle=float(Lg["bz"][0]),
               audit={k: (bool(v) if k == "pass" else float(v)) for k, v in aud.items()},
               audit_pass=bool(aud["pass"]),
               stance_s=st["t_stance"], stance_ok=st["stance_ok"],
               range_viol=rv,
               pass_all=bool(aud["pass"] and st["stance_ok"] and rv is None),
               extrapolated=bool(li_q < EV.LI_FIT_MM - 1e-9),
               r_range=[rmin, rmax],
               stats=st)
    return row, Lg


def main():
    t0 = time.time()
    EV.setup()
    golden = EV.run_golden()   # 롤아웃 시점 재검증 (0429 재생 + CVT 스텝 비트일치)
    ck = torch.load(os.path.join(HERE, f"t0wc_ppo_policy{TAG}.pt"), weights_only=False)
    tlog = json.load(open(os.path.join(HERE, f"t0wc_train_log{TAG}.json"), encoding="utf-8"))
    ck_clip = ck.get("hyper", {}).get("clip_raw", None)
    assert ck_clip is not None and abs(ck_clip - float(EV.R19.CLIP)) < 1e-9, \
        f"클립 불일치: 체크포인트 {ck_clip} vs 현재 env {EV.R19.CLIP} (P25_CLIP_RAW 확인)"
    env = JumpEnv(seed=12345, reset_noise=False, li_fixed=EV.LI_FIT_MM)
    n_act = env.n_ep * env.nsub
    curves = {}
    logs = {}
    for tag in ("final", "best"):
        ac = TR.ActorCritic()
        ac.load_state_dict(ck[tag] if ck[tag] is not None else ck["final"])
        ac.eval()
        rows = []
        for li in LIS_EVAL:
            row, Lg = eval_point(env, ac, li)
            rows.append(row)
            logs[(tag, row["l_i_mm"])] = Lg
            print(f"[{tag}] l_i={row['l_i_mm']:6.2f}mm  h={row['h_plan']:.4f}  "
                  f"audit={'PASS' if row['audit_pass'] else 'FAIL'}  "
                  f"stance={row['stance_s']:.3f}s  "
                  f"{'외삽' if row['extrapolated'] else '내삽'}"
                  f"{'  range_viol' if row['range_viol'] else ''}", flush=True)
        curves[tag] = rows

    # ── l_i* 선택: campaign-pass 점 우선 argmax h (없으면 raw argmax + 플래그) ──
    def li_star_of(rows):
        ok = [r for r in rows if r["pass_all"]]
        pool = ok if ok else rows
        r = max(pool, key=lambda r: r["h_plan"])
        return r, bool(ok)

    star = {}
    for tag in ("final", "best"):
        r, from_pass = li_star_of(curves[tag])
        star[tag] = dict(l_i_mm=r["l_i_mm"], h_plan=r["h_plan"],
                         pass_all=r["pass_all"], from_pass_pool=from_pass,
                         extrapolated=r["extrapolated"])
    # primary = pass-pool h가 더 높은 체크포인트 (동률/둘다 실패 시 final)
    primary = "best" if (star["best"]["pass_all"] and
                         (not star["final"]["pass_all"]
                          or star["best"]["h_plan"] > star["final"]["h_plan"])) else "final"
    ps = star[primary]
    li_star = ps["l_i_mm"]
    row_star = next(r for r in curves[primary] if r["l_i_mm"] == li_star)
    Lg = logs[(primary, li_star)]
    print(f"\nl_i* = {li_star:.2f} mm ({primary} ckpt)  h={ps['h_plan']:.4f} m  "
          f"pass_all={ps['pass_all']}  extrapolated={ps['extrapolated']}", flush=True)

    # ── npz (t0wc 스키마 + qm/l_i/h_plan + Phase A 호환 qd:=q) ──
    np.savez(os.path.join(HERE, f"t0wc_ppo{TAG}.npz"),
             t=Lg["t"], q1=Lg["q1"], q2=Lg["q2"], dq1=Lg["dq1"], dq2=Lg["dq2"],
             raw1=Lg["raw1"], raw2=Lg["raw2"],
             tau1_nm=Lg["tau1_nm"], tau2_nm=Lg["tau2_nm"],
             bz=Lg["bz"], grf=Lg["grf"],
             cmd_raw1=Lg["cmd_raw1"], cmd_raw2=Lg["cmd_raw2"],
             qd1=Lg["q1"], qd2=Lg["q2"], dqd1=Lg["dq1"], dqd2=Lg["dq2"],
             h_plan=float(ps["h_plan"]), qm=Lg["q2"], l_i=float(li_star),
             extrapolated=float(ps["extrapolated"]))

    # ── CMA 비교 (기존 t0wc 고정-l_i CMA 산출물) ──
    cma_ref = {}
    for m in ("cl", "ol"):
        for k in ("li15", "li20", "li2508"):
            try:
                d = safe.read_json(os.path.join(HERE, f"t0wc_{m}_{k}_audit.json"))
                cma_ref[f"{m}_{k}"] = dict(l_i_mm=d["l_i_mm"], h_plan=d["h_plan"],
                                           audit_pass=bool(d["audit"]["pass"]))
            except Exception:
                pass

    fin = tlog.get("final", {})
    caveats = [
        "P25-task0 with_cvt 캠페인 — 제약은 AVT LEG task0_vertjump_with_cvt 기준 "
        "(t0_spec cvt=True): |â|≤15Nm(raw 박스 25.5810) · T-N · |dq|≤50 · "
        "q1∈[-1.2566,-0.2967] · 크랭크 qm∈[-2.95,-0.05] · 스탠스≤0.3s(감사)",
        "l_i-조건부 단일 정책: 학습 시 에피소드마다 l_i~U[15,30]mm (0.05mm 양자화, "
        "obs 8축째 = (l_i-22.5)/7.5) — h(l_i) 곡선은 같은 정책의 결정론 롤아웃",
        "CVT 층(C_CVT 전달손실·게이트 스프링)은 l_i=25.08mm(0429)에서만 실측 검증 — "
        "l_i<25.08 결과는 모델 외삽(extrapolated 플래그), [25.08,30]은 양끝 검증 내삽",
        "관절바운드(qm 포함) = 학습 종료조건(hard-ish), T-N/dq50/|â|>15 = 스텝당 "
        "위반량² 소프트 페널티 (w=50) — CMA(t0wc_cma)의 소프트 페널티+에스컬레이션과 "
        "처리 방식이 달라 h 직접 비교에 유의",
        "시작 웅크림 = task0 초기추정 (q1=-0.32, qm=-2.50) settle 고정 — CMA판은 "
        "시작 자세도 최적화 대상(바운드 내 자유)이므로 RL이 그 부분공간의 한 점에서 출발",
        "h_plan = 능동 0.6s + 수동 연장 0.6s 실측 max bz (학습 중 apex 보상은 탄도 외삽)",
    ]
    if not ps["pass_all"]:
        caveats.append(f"주의: primary l_i* 점이 campaign-pass 실패 상태 — audit 참조")
    res = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        campaign="P25-task0 with_cvt (PPO l_i-조건부, task0 제약)",
        method="ppo_licond",
        clip_raw=float(EV.R19.CLIP),
        primary_ckpt=primary,
        li_star_mm=float(li_star),
        h_plan=float(ps["h_plan"]),
        pass_all=bool(ps["pass_all"]),
        extrapolated=bool(ps["extrapolated"]),
        audit_star=row_star["audit"],
        stance_star=dict(t_stance=row_star["stance_s"], ok=row_star["stance_ok"],
                         max=T0.T_ST_MAX),
        stats_star=row_star["stats"],
        range_viol_star=row_star["range_viol"],
        li_star_by_ckpt=star,
        h_curve={tag: [{k: v for k, v in r.items() if k != "stats"}
                       for r in curves[tag]] for tag in curves},
        h_anchor_2508={tag: next((r["h_plan"] for r in curves[tag]
                                  if abs(r["l_i_mm"] - EV.LI_FIT_MM) < 1e-6), None)
                       for tag in curves},
        h_anchor_30={tag: next((r["h_plan"] for r in curves[tag]
                                if abs(r["l_i_mm"] - 30.0) < 1e-6), None)
                     for tag in curves},
        cma_ref=cma_ref,
        avt_opt_mm=AVT_OPT_MM,
        li_eval_grid=[float(x) for x in LIS_EVAL],
        training=dict(steps=fin.get("steps"), wall_s=fin.get("wall_s"),
                      stop=fin.get("stop"),
                      best_h_mean3_during_train=fin.get("best_h"),
                      best_step=fin.get("best_step"),
                      n_updates=len(tlog.get("updates", [])),
                      n_evals=len(tlog.get("evals", []))),
        hyper=tlog.get("hyper"),
        golden=golden,
        env=dict(ctrl_dt=EV.CTRL_DT, ep_t=EV.EP_T, sim_dt=env.dt,
                 crouch=list(EV.CROUCH_T0), li_sample="U[15,30]mm (train)",
                 li_quant_mm=EV.LI_Q_MM,
                 q1_range=[T0.Q1_LB, T0.Q1_UB], qm_range=[T0.QM_LB, T0.QM_UB],
                 obs="[(bz-0.6)/0.4, q1/1.5, qm/1.5, dq1/10, dqm/10, vbz/3, "
                     "t/0.6, (l_i-22.5)/7.5]",
                 action=f"raw torque (2,) [-{EV.R19.CLIP},{EV.R19.CLIP}] → "
                        "tm필터→클립→ahat→supp/rise/C_CVT/스프링/힙층",
                 w_tn=EV.W_TN, w_dq=EV.W_DQ, w_tau=EV.W_TAU,
                 m_tn=EV.M_TN, m_tau=EV.M_TAU,
                 reset_noise=dict(q_std=EV.NOISE_Q, dq_std=EV.NOISE_DQ)),
        caveats=caveats,
        files=dict(npz=f"t0wc_ppo{TAG}.npz", curve=f"t0wc_ppo_curve{TAG}.png",
                   licurve=f"t0wc_ppo_licurve{TAG}.png",
                   policy=f"t0wc_ppo_policy{TAG}.pt",
                   train_log=f"t0wc_train_log{TAG}.json"),
        wall_s_rollout=time.time() - t0)
    if LI_FIX is not None:
        res["mode"] = f"fixed-l_i 폴백 ({LI_FIX} mm) — 조건부 저성과 시 개별 학습 (코디 07-18)"
    safe.atomic_json_write(os.path.join(HERE, f"t0wc_ppo_audit{TAG}.json"), res)
    if LI_FIX is None:
        make_licurve(curves, star, primary, cma_ref)
        print(f"saved: t0wc_ppo{TAG}.npz / t0wc_ppo_audit{TAG}.json / "
              f"t0wc_ppo_licurve{TAG}.png [{time.time() - t0:.0f}s]", flush=True)
    else:
        print(f"saved: t0wc_ppo{TAG}.npz / t0wc_ppo_audit{TAG}.json "
              f"[{time.time() - t0:.0f}s]", flush=True)


def make_licurve(curves, star, primary, cma_ref):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for tag in ("final", "best"):
        rows = curves[tag]
        lis = [r["l_i_mm"] for r in rows]
        hs = [r["h_plan"] for r in rows]
        ls = "-" if tag == primary else "--"
        line, = ax.plot(lis, hs, linestyle=ls, marker="o", ms=4,
                        label=f"RL {tag} ckpt" + (" (primary)" if tag == primary else ""))
        # audit-fail 점은 x 마커 덧씌움 (같은 색)
        bad = [(r["l_i_mm"], r["h_plan"]) for r in rows if not r["pass_all"]]
        if bad:
            ax.plot([b[0] for b in bad], [b[1] for b in bad], linestyle="none",
                    marker="x", ms=9, color=line.get_color())
    for k, d in cma_ref.items():
        if k.startswith("cl"):
            ax.plot([d["l_i_mm"]], [d["h_plan"]], linestyle="none", marker="*",
                    ms=13, label=f"CMA CL {d['l_i_mm']:.2f}mm: {d['h_plan']:.3f} m")
    s = star[primary]
    ax.annotate(f"RL l_i*={s['l_i_mm']:.2f}mm\nh={s['h_plan']:.3f} m",
                xy=(s["l_i_mm"], s["h_plan"]), xytext=(s["l_i_mm"] - 4.5,
                                                       s["h_plan"] - 0.12),
                arrowprops=dict(arrowstyle="->", alpha=0.7), fontsize=9)
    ax.axvline(EV.LI_FIT_MM, linestyle="--", alpha=0.7,
               label="검증앵커 25.08 (0429 CVT)")
    ax.axvline(30.0, linestyle="--", alpha=0.4, label="검증앵커 30 (무변속 세션)")
    ax.axvline(AVT_OPT_MM, linestyle=":", label="AVT 해석모델 최적 25.161")
    ax.axvspan(EV.LI_LB_MM, EV.LI_FIT_MM, alpha=0.10,
               label="외삽 구간 (CVT 층 fit @25.08)")
    ax.set_xlabel("l_i [mm]")
    ax.set_ylabel("h_plan (base-z apex) [m]")
    ax.set_title("P25-task0 with_cvt — l_i-조건부 PPO: 점프 높이 vs CVT 링크 길이 "
                 "(x = campaign-pass 실패 점)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, f"t0wc_ppo_licurve{TAG}.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
