# -*- coding: utf-8 -*-
"""fs_compare_plot — 전 데이터 3자 비교 그래프: 실측 vs 배포모델(OLD) vs 현행 스택.

채널: q1·q2 [°], dq1·dq2 [rad/s], τ1·τ2 [Nm] — 6패널 1장/trial.
모드:
  CL    = 폴더 게인 PD 폐루프. **점프(push) 구간만** (push 시작−0.05s ~ 이륙, 사용자 지시).
          OLD = TW.rollout_cl(alphas=TH/TK 또는 세션 R19.ALPH) · 현행 = FR.rollout_cl_fs (라벨은 FS_STACK_TAG)
  ModeA = mshoot 0.4s 창/0.3s stride, 측정 raw 주입·측정상태 리셋 (창별 조각 오버레이).
          OLD = TW.rollout_ol(구 플랜트) · fs = FR.rollout_ol_fs_b(내장 스프링 플랜트)
출력: _compare/CL/<세션>/<trial>.png · _compare/ModeA/<세션>/<trial>.png
      + 세션별 _summary.png (채널 RMSE 막대) + _compare/README.md (색인)
CLI: python fs_compare_plot.py [CL|MA]   (인자 없으면 둘 다)
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
for k, v in (("FS_FIXED", "1"), ("FS_FADE", "1"), ("FS_TAUOBS", "lpf"), ("FS_TC", "0.002"),
             ("FS_KNEE_REL", "0.1"), ("FS_KNEE_LOAD", "1"), ("FS_TAULIM", "20.5")):
    os.environ.setdefault(k, v)
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
import safe
import fs_data as FD
import fs_metric as FMET
import fs_runner as FR
import p25_a_twin as TW
from _G10_energy import real_h            # 점프높이 실측 (Real Data.txt, 영상 A급)

OUT = HERE / os.environ.get("FS_CMP_OUT", "_compare")   # 스택별 산출 분리 (기본 = 기존 경로)
TAG = os.environ.get("FS_STACK_TAG", "fs")              # 그림 라벨 = 실제 스택명 (하드코딩 금지)
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}
TH = {60: 0.70, 120: 0.50, 150: 0.40}


def sess_params(sess):
    """세션 상수(bias1 · knee_deep) 조회 — **FS_NOBIAS / FS_NODEEP 존중** (마라톤G G53 추가).

    ★ 왜 필요한가 (침묵실패 사례): 이 두 스위치는 그동안 `_G13_board.py` / `_G51_allboard.py`
      **안에서만** 처리됐고 `fs_runner.py` 에도 이 파일에도 없었다. 그래서 마라톤G 스택
      (인공층 전멸 = 세션 상수 0)을 env 로 넘겨도 **이 스크립트는 세션 상수를 그대로 켠 채** 돌았고,
      같은 구성인데 0421 q2 가 심판 3.99 vs 그림 7.13 으로 갈렸다 (사용자 지적으로 발각).
      두 경로가 같은 자를 쓰도록 정본 한 곳에 모은다.
    """
    sp = FR._sess_params().get(sess) or dict(bias1=0.0, knee_deep=None)
    if os.environ.get("FS_NOBIAS") == "1":
        sp = dict(sp, bias1=0.0)
    if os.environ.get("FS_NODEEP") == "1":
        sp = dict(sp, knee_deep=None)
    return sp


def alpha_of(tab, kp):
    """OLD α 조회 — 표 밖 게인은 **log-kp 선형 보간**(표 범위 밖은 단부값 고정).
    사용자 지적 (P17): 구 fallback 0.40/0.656 고정은 표 밖 게인에서 OLD를 부당하게 약화시켰다
    (예: 27일 kp1=100 → 0.40, 보간값 0.58). 비교 공정성 수정."""
    ks = sorted(tab)
    if kp in tab:
        return tab[kp]
    if kp <= ks[0]:
        return tab[ks[0]]
    if kp >= ks[-1]:
        return tab[ks[-1]]
    return float(np.interp(np.log(kp), np.log(ks), [tab[k] for k in ks]))
QS = 2                      # qd 스큐 보정 [샘플] (4ms@500Hz)
MA_W, MA_S = 0.10, 0.05     # 점프 창(~0.2~0.3s) 내 mshoot 창/stride
CH = [("q1", "q1 [°]"), ("q2", "q2 [°]"), ("dq1", "dq1 [rad/s]"),
      ("dq2", "dq2 [rad/s]"), ("a1", "τ1 [Nm]"), ("a2", "τ2 [Nm]")]


def sh(x, n=QS):
    y = np.empty_like(x); y[n:] = x[:-n]; y[:n] = x[0]
    return y


def panels(title, subtitle=""):
    fig, ax = plt.subplots(2, 3, figsize=(15.5, 7.2), sharex=True)
    fig.suptitle(title + (f"\n{subtitle}" if subtitle else ""), fontsize=11)
    for a, (_, lab) in zip(ax.T.flat, CH):
        a.set_ylabel(lab)
        a.grid(alpha=0.3)
    for a in ax[1]:
        a.set_xlabel("t [s]")
    return fig, ax.T.flat        # 열 우선: (q1,q2),(dq1,dq2),(τ1,τ2)


def rmse_line(d, m, sims):
    """범례용 RMSE 문자열 (6채널)."""
    out = []
    for (k, _), s in zip(CH, sims):
        v = d[k][m] - s[m]
        r = np.degrees(np.sqrt(np.mean(v ** 2))) if k in ("q1", "q2") else np.sqrt(np.mean(v ** 2))
        out.append(f"{r:.2f}")
    return " / ".join(out)


def cl_pair(d, seg, g, sess):
    """CL을 **ModeA와 동일 규칙**으로: 점프 창 시작에서 실측 상태 1회 앵커 → 통짜 폐루프 (P16).
    반환 (t, 실측, OLD, 현행, 창마스크) — 실패 시 None."""
    pw = FD.plot_window(d["_fold"], d)
    if pw is None:
        return None
    tt = d["t"]
    m = (tt >= pw[0]) & (tt <= pw[1])
    if m.sum() < 30:
        return None
    i0 = int(np.argmax(m))
    t = tt[m] - tt[i0]
    t_end = float(t[-1])
    init = (float(d["q1"][i0]), float(d["q2"][i0]), float(d["dq1"][i0]), float(d["dq2"][i0]),
            float(d["raw1"][i0]), float(d["raw2"][i0]))
    qd = (d["qd1"][m], d["qd2"][m], d["dqd1"][m], d["dqd2"][m])
    alphas = alphas_for(sess, g)
    Lo = cl_old_meas(FMET.tw0, t, *qd, tuple(g), alphas, t_end, init)
    ft = FR.fs_twin()
    sp = sess_params(sess)          # ★ G53: FS_NOBIAS/FS_NODEEP 존중 (정본 단일 출처)
    Lf = FR.rollout_cl_fs(ft, t, sh(qd[0]), sh(qd[1]), sh(qd[2]), sh(qd[3]),
                          tuple(g), t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                          fade=True, taulim=None, vdes_ff=(sess != "26.04.21"), init_meas=init)
    if Lo is None or Lf is None:
        return None
    gi = lambda L, k: np.interp(t, L["t"], L[k])
    old = [gi(Lo, "q1"), gi(Lo, "q2"), gi(Lo, "dq1"), gi(Lo, "dq2"), gi(Lo, "sh1"), gi(Lo, "sh2")]
    fs = [gi(Lf, "thm1"), gi(Lf, "q2"), gi(Lf, "dq1"), gi(Lf, "dq2"),
          np.clip(gi(Lf, "s1f"), -20.5, 20.5), gi(Lf, "s2")]
    meas = {k: d[k][m] for k, _ in CH}
    cmd = [d["qd1"][m], d["qd2"][m], d["dqd1"][m], d["dqd2"][m], None, None]   # exp5 형식: 명령 병기
    pl = plan_of(sess, t, d["qd2"][m])                                        # 배포 계획 (있는 세션만)
    return tt[m], meas, old, fs, np.ones(m.sum(), bool), cmd, pl



_KPREF = {}


def _kp_ref(sess):
    """세션 적합 α의 '실효 기준 게인' = 그 세션 trial 게인의 기하평균 (hip, knee)."""
    if sess not in _KPREF:
        k1 = [g[0] for s_, p_, g, c_, h_ in FD.registry() if s_ == sess and g]
        k2 = [g[2] for s_, p_, g, c_, h_ in FD.registry() if s_ == sess and g]
        _KPREF[sess] = (float(np.exp(np.mean(np.log(k1)))) if k1 else None,
                        float(np.exp(np.mean(np.log(k2)))) if k2 else None)
    return _KPREF[sess]


def alphas_for(sess, g):
    """OLD α 결정 (P18, 사용자 지시 '다른 날도 제대로 보간').
    ①세션 적합 α가 있는 날(0424/0602/0421): 세션 수준은 보존하되 **게인 의존을 복원** —
      α(kp) = α_sess × alpha_of(표, kp) / alpha_of(표, kp_ref), kp_ref = 세션 게인 기하평균.
      (구: 세션 α 하나를 kp 60~500 전 trial에 동일 적용 → 저게인 과소·고게인 과대)
    ②없는 날(7월 등): 표 log-kp 보간 (P17).
    kd 계수는 원 규약(0.20 또는 세션 적합) 유지."""
    sess_al = FMET.ALPH_SESS.get(sess)
    if not sess_al:
        return (alpha_of(TH, g[0]), 0.20, alpha_of(TK, g[2]), 0.20)
    r1, r2 = _kp_ref(sess)
    f1 = alpha_of(TH, g[0]) / alpha_of(TH, r1) if r1 else 1.0
    f2 = alpha_of(TK, g[2]) / alpha_of(TK, r2) if r2 else 1.0
    # α ≤ 1 (전달 스케일의 물리 상한 — 복원 스케일링이 1을 넘으면 클립)
    return (float(min(sess_al[0] * f1, 1.0)), float(sess_al[1]),
            float(min(sess_al[2] * f2, 1.0)), float(sess_al[3]))



_PLAN = {"26.07.27": "t0nc_cl_v9.npz"}          # 배포 계획 (exp5 규약: 27일 = v9). 다른 날은 계획 파일 미확정.
_PLANC = {}


def plan_of(sess, tm, qd2_meas):
    """배포 계획 궤적 로드 + **exp5 정렬 규약**(측정 qd2 ↔ 계획 qd2 미분 교차상관)으로 시각 정렬.
    반환 (계획 6채널 보간값, lag[s]) | None. 계획이 없는 세션은 None (OLD 재생만 표시)."""
    f = _PLAN.get(sess)
    if not f:
        return None
    if sess not in _PLANC:
        _PLANC[sess] = np.load(HERE.parent / "goal22" / "p25_task0" / f)
    Z = _PLANC[sess]
    PT = Z["t"]
    # 정렬 = **RMSE 최소 지연** (P20 정정: exp5의 미분 교차상관은 위상만 맞춰 RMSE를 12ms 어긋나게 함).
    # 명령 정지(이륙 후 홀드) 구간은 제외하고 맞춘다.
    qm = np.asarray(qd2_meas, float)
    mv = np.ones_like(qm, bool)
    if len(qm) > 6:
        mv[1:] = np.abs(np.diff(qm)) > 1e-7
    best, blag = 9e9, 0.0
    for lag_ms in range(-40, 41):
        lg = lag_ms / 1000.0
        r = float(np.sqrt(np.mean((qm[mv] - np.interp(tm[mv] + lg, PT, Z["qd2"])) ** 2)))
        if r < best:
            best, blag = r, lg
    g = lambda k: np.interp(tm + blag, PT, Z[k])
    return [g("q1"), g("q2"), g("dq1"), g("dq2"), g("tau1_nm"), g("tau2_nm")], blag


def cl_old_meas(tw, tg, qd1g, qd2g, dqd1g, dqd2g, gains, alphas, t_end, init_meas):
    """TW.rollout_cl 문자 미러 + **창 시작 실측 앵커** (settle 생략) — ModeA와 동일 규칙.
    골든: init_meas=None으로 호출하면 정본과 동일 경로(settle)로 되돌아간다 (검증 함수 golden_mirror)."""
    P = FMET.tw0["P"]; mj = P.J._P["mj"]; S = P.J._P["S"]
    law_a, law_b, law_v0 = FMET.tw0["law"]
    tm = FMET.tw0["tm"]; kr = FMET.tw0["kr"]; sprm = FMET.tw0["sprm"]
    A = P.A_PAPER
    model = FMET.tw0["model"]
    RU = TW.RU
    ap1, ad1, ap2, ad2 = alphas
    kp1, kd1, kp2, kd2 = gains
    kp1 *= ap1; kd1 *= ad1; kp2 *= ap2; kd2 *= ad2
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    settle = init_meas is None
    if settle:
        sq1, sq2 = -qd1g[0] - np.pi / 2, -qd2g[0]
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
        mj.mj_forward(model, md)
        fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
        md.qvel[:] = 0
    else:
        q1m, q2m, dq1m, dq2m = init_meas[:4]
        sq1, sq2 = -q1m - np.pi / 2, -q2m
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
        mj.mj_forward(model, md)
        fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
        md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
        c1_, c12_ = np.cos(q1m), np.cos(q1m + q2m)
        md.qvel[:] = [-0.25 * (c1_ * dq1m + c12_ * (dq1m + dq2m)), -dq1m, -dq2m, dq2m, -dq2m]
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    T_S = P.J.T_SETTLE if settle else 0.0
    N = int((T_S + t_end + 0.05) / dt)
    tl = np.arange(N) * dt - T_S
    Lg = {k: np.zeros(N) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2", "bz")}
    c1f = c2f = 0.0
    al = dt / max(tm, dt)
    for k in range(N):
        tc = tl[k]
        q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc < 0:
            c1 = S.SETTLE_KP * (qd1g[0] - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (qd2g[0] - q2c) - S.SETTLE_KD * v2c
            c1f, c2f = c1, c2
        else:
            tm_ = min(tc, t_end)
            c1 = kp1 * (np.interp(tm_, tg, qd1g) - q1c) + kd1 * (np.interp(tm_, tg, dqd1g) - v1c)
            c2 = kp2 * (np.interp(tm_, tg, qd2g) - q2c) + kd2 * (np.interp(tm_, tg, dqd2g) - v2c)
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1, c2 = c1f, c2f
        c1 = float(np.clip(c1, -TW.R19.CLIP, TW.R19.CLIP)); c2 = float(np.clip(c2, -TW.R19.CLIP, TW.R19.CLIP))
        s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
        s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
        supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
        if kr:
            supp += float(RU.rise_term(v2c, kr, law_v0))
        tql = RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm) if sprm is not None else 0.0
        md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
        md.qfrc_applied[dof_knee] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
    Lg["t"] = tl
    return Lg


def ol_old_meas(tw, tg, raw1g, raw2g, st, t_end, t_after=0.004):
    """★ G55: OLD ModeA 미러 — `TW.rollout_ol` 과 **동일 로직**에 `tq1/tq2`(모터 출력 총 토크) 추가.

    왜 필요한가 (사용자 지적): 정본이 그리던 `sh1/sh2` 는 **a_hat 출력만**이다. 그러나 OLD 는
    그 위에 `hip_supp_scalar` · `supp_scalar` · `rise_term` 을 얹어 액추에이터에 넣는다.
    ⇒ 지금까지 OLD 의 τ 는 **실제 인가량보다 작게** 그려지고 있었다.
    `tq1/tq2` = 액추에이터에 실제로 들어간 값 (gear=1 이라 ctrl 크기 = 관절 일반화력).
    ※ 무릎 `spr_tau(tql)` 는 `knee` 관절(모터 관절과 다른 DOF)에 걸리는 **부하연동 스프링**이라
      모터 출력이 아니다 — 별도 키 `spr` 로 남겨 필요 시 참고.
    검증은 `golden_mirror_ma()` 가 `TW.rollout_ol` 과 비트 대조한다 (침묵실패 방역).
    """
    P = tw["P"]
    mj = P.J._P["mj"]
    RU = TW.RU                  # cl_old_meas 와 동일 관례 (모듈 전역 아님 — 지역 바인딩)
    law_a, law_b, law_v0 = tw["law"]
    tm = tw["tm"]; kr = tw["kr"]; sprm = tw["sprm"]
    A = P.A_PAPER
    model = tw["model"]
    md = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    md.qpos[:] = st["qpos"]; md.qvel[:] = st["qvel"]
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((t_end + t_after) / dt)
    tl = np.arange(N) * dt
    Lg = {k: np.zeros(N) for k in ("q1", "q2", "dq1", "dq2", "sh1", "sh2", "tq1", "tq2", "spr", "bz")}
    c1f, c2f = st["c1f"], st["c2f"]
    al = dt / max(tm, dt)
    for k in range(N):
        tc = tl[k]
        v1c = -md.qvel[1]; v2c = -md.qvel[2]
        if tc <= t_end:
            c1 = float(np.interp(tc, tg, raw1g))
            c2 = float(np.interp(tc, tg, raw2g))
            c1f += al * (c1 - c1f); c2f += al * (c2 - c2f)
            c1 = float(np.clip(c1f, -TW.R19.CLIP, TW.R19.CLIP))
            c2 = float(np.clip(c2f, -TW.R19.CLIP, TW.R19.CLIP))
            s1 = float(P.J.ahat(A, np.array([c1]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(A, np.array([c2]), np.array([v2c]))[0])
            supp = RU.supp_scalar(s2, v2c, law_a, law_b, law_v0)
            if kr:
                supp += float(RU.rise_term(v2c, kr, law_v0))
            tql = RU.spr_tau(float(md.qpos[iq_k]), abs(s2), sprm) if sprm is not None else 0.0
            md.ctrl[:] = [-(s1 + RU.hip_supp_scalar(s1, s2, v1c)), -(s2 + supp)]
            md.qfrc_applied[dof_knee] = tql
        else:                                                   # a_full23 비행 규약
            s1 = s2 = 0.0; tql = 0.0
            md.ctrl[:] = [-(0.0 + RU.HIP["a1"]), -(0.0 + law_a)]
            md.qfrc_applied[dof_knee] = 0.0
        Lg["tq1"][k] = -float(md.ctrl[0]); Lg["tq2"][k] = -float(md.ctrl[1])
        Lg["spr"][k] = tql
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        Lg["q1"][k] = -md.qpos[1] - np.pi / 2; Lg["q2"][k] = -md.qpos[2]
        Lg["dq1"][k] = -md.qvel[1]; Lg["dq2"][k] = -md.qvel[2]
        Lg["sh1"][k] = s1; Lg["sh2"][k] = s2; Lg["bz"][k] = md.qpos[0]
    Lg["t"] = tl
    return Lg


def golden_mirror_ma(d, seg):
    """미러 신뢰 검증: ol_old_meas == 정본 TW.rollout_ol (침묵실패 방역, cl 판과 동일 규약)."""
    pw = FD.plot_window(d["_fold"], d)
    if pw is None:
        return None
    tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
    if m.sum() < 30:
        return None
    i0 = int(np.argmax(m)); tg = tt[m] - tt[i0]; t_end = float(tg[-1] - 0.004)
    st = FMET.st_from_meas(FMET.tw0, float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(d["raw1"][i0]), float(d["raw2"][i0]))
    A_ = TW.rollout_ol(FMET.tw0, tg, d["raw1"][m], d["raw2"][m], st, t_end=t_end, t_after=0.004)
    B_ = ol_old_meas(FMET.tw0, tg, d["raw1"][m], d["raw2"][m], st, t_end, 0.004)
    if A_ is None or B_ is None:
        return None
    n = min(len(A_["q1"]), len(B_["q1"]))
    return (float(np.max(np.abs(A_["q1"][:n] - B_["q1"][:n]))),
            float(np.max(np.abs(A_["sh2"][:n] - B_["sh2"][:n]))))


def golden_mirror(d, seg, g, sess):
    """미러 신뢰 검증: init_meas=None 미러 == 정본 TW.rollout_cl (침묵실패 방역)."""
    i0 = max(0, seg["i_desc"] - 5)
    sl = slice(i0, None)
    t = d["t"][sl] - d["t"][i0]
    t_end = seg["t_lo"] - d["t"][i0]
    alphas = alphas_for(sess, g)
    args = (t, d["qd1"][sl], d["qd2"][sl], d["dqd1"][sl], d["dqd2"][sl])
    A_ = TW.rollout_cl(FMET.tw0, *args, tuple(g), alphas=alphas, t_end=t_end, t_after=0.05)
    B_ = cl_old_meas(FMET.tw0, *args, tuple(g), alphas, t_end, None)
    if A_ is None or B_ is None:
        return None
    n = min(len(A_["q1"]), len(B_["q1"]))
    return float(np.max(np.abs(A_["q1"][:n] - B_["q1"][:n]))), float(np.max(np.abs(A_["sh1"][:n] - B_["sh1"][:n])))


def plot_cl(sess, name, d, seg, g):
    r = cl_pair(d, seg, g, sess)
    if r is None:
        print(f"  CL {sess}/{name}: 롤아웃 실패", flush=True)
        return
    t, meas, old, fs, m, cmd, pl = r
    fig, ax = panels(f"{sess} / {name} — CL 점프 구간 (창 시작 실측 앵커 · 통짜) · 실측 vs 배포계획(τ*) vs 배포모델 재생(OLD) vs 현행({TAG})" + (f" | 계획 정렬 {pl[1]*1000:+.0f}ms" if pl else ""),
                     f"창 RMSE (q1/q2/dq1/dq2/τ1/τ2)  OLD: {rmse_line(meas, m, old)}   {TAG}: {rmse_line(meas, m, fs)}")
    for j, (a, (k, _)) in enumerate(zip(ax, CH)):
        y, yo, yf = meas[k], old[j], fs[j]
        if k in ("q1", "q2"):
            y, yo, yf = np.degrees(y), np.degrees(yo), np.degrees(yf)
        a.plot(t, y, lw=1.2, label="실측")
        a.plot(t, yo, "--", lw=1.0, label="배포모델 (OLD)")
        a.plot(t, yf, ":", lw=1.5, label=f"현행 ({TAG})")
        if pl is not None and os.environ.get("FS_PLAN") == "1":
            # 기본 미표시 (사용자 결정 P22): OLD 재생이 계획을 RMSE≤0.2로 포함 + 계획은 27일만 존재.
            yp = np.degrees(pl[0][j]) if k in ("q1", "q2") else pl[0][j]
            a.plot(t, yp, "-.", lw=1.2, label="배포계획 (v9 τ*)")
        if cmd[j] is not None:
            yc = np.degrees(cmd[j]) if k in ("q1", "q2") else cmd[j]
            a.plot(t, yc, "--", lw=0.8, alpha=0.5, label="명령 (qd)")
    ax[0].legend(fontsize=8, loc="best")
    fig.tight_layout()
    fp = OUT / "CL" / sess
    fp.mkdir(parents=True, exist_ok=True)
    fig.savefig(fp / f"{name}.png", dpi=105)
    plt.close(fig)
    conv = lambda k, v: np.sqrt(np.mean((meas[k][m] - v[m]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
    return [conv(k, v) for (k, _), v in zip(CH, old)], [conv(k, v) for (k, _), v in zip(CH, fs)]


def plot_ma(sess, name, d, seg):
    """ModeA = **점프 창 통짜 개루프 재생** (측정 raw 주입, 초기상태만 실측 — 중간 리셋 없음).

    사용자 지적 (08-01): 창 분할 재생은 에러가 매 창 초기화돼 모델 발전의 자가 될 수 없다.
    점프 창(~0.2~0.3s)은 통짜 재생이 가능하므로 R19 정본 재생 방식(단일 샷)을 따른다.

    ★ G55 (사용자 지시): τ 패널을 **양쪽 모두 "실제 조인트에 들어간 총 토크"** 로 바꾼다.
      · OLD  = a_hat + hip_supp_scalar / a_hat + supp_scalar + rise_term  (`ol_old_meas.tq*`)
      · 현행 = 토크맵(canon_cap 등) 출력 + 커맨드층 보정 전부           (`rollout_ol_fs_b.tq*`)
      구 방식(`sh1/sh2` vs `s1/s2`)은 **a_hat 출력만**이라 OLD 를 과소 표시했다.
      제목에 **점프높이**(영상 실측 vs 두 모델, 부호 있는 오차)를 병기한다.
    """
    ft = FR.fs_twin()
    sp = sess_params(sess)
    t = d["t"]
    pw = FD.plot_window(d["_fold"], d)          # 그래프·재생 창 = 원본 xlsx (점프) — 훅 규약
    if pw is None:
        return
    m = (t >= pw[0]) & (t <= pw[1])
    if m.sum() < 30:
        print(f"  MA {sess}/{name}: 표본 부족", flush=True)
        return
    i0 = int(np.argmax(m))
    tg = t[m] - t[i0]
    t_end = float(tg[-1] - 0.004)
    # h 판독용 연장 (심판 _G13_board 와 동일한 자: 이지 후 +0.6s)
    t_ext = min(t[m][-1] + 0.6, t[-1])
    m2 = (t >= t[i0]) & (t <= t_ext)
    tg2 = t[m2] - t[i0]
    st = FMET.st_from_meas(FMET.tw0, float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(d["raw1"][i0]), float(d["raw2"][i0]))
    Lo = ol_old_meas(FMET.tw0, tg, d["raw1"][m], d["raw2"][m], st, t_end, 0.004)
    Lf = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                            float(d["q1"][i0]), float(d["q2"][i0]),
                            float(d["dq1"][i0]), float(d["dq2"][i0]),
                            t_end, bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
    if Lo is None or Lf is None:
        print(f"  MA {sess}/{name}: 재생 실패 (old {Lo is None} / fs {Lf is None})", flush=True)
        return
    # 점프높이 (연장 재생으로 최고점 직접 판독)
    hv = real_h(d["_fold"])
    te2 = float(tg2[-1] - 0.004)
    Ho = ol_old_meas(FMET.tw0, tg2, d["raw1"][m2], d["raw2"][m2], st, te2, 0.004)
    Hf = FR.rollout_ol_fs_b(ft, tg2, d["raw1"][m2], d["raw2"][m2],
                            float(d["q1"][i0]), float(d["q2"][i0]),
                            float(d["dq1"][i0]), float(d["dq2"][i0]),
                            te2, bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
    ho_ = float(np.asarray(Ho["bz"]).max()) if Ho else np.nan
    hf_ = float(np.asarray(Hf["bz"]).max()) if Hf else np.nan
    if hv:
        HT = (f"점프높이  영상 {hv:.3f} m  ·  OLD {ho_:.3f} m ({100*(ho_/hv-1):+.1f}%)"
              f"  →  {TAG} {hf_:.3f} m ({100*(hf_/hv-1):+.1f}%)")
    else:
        HT = f"점프높이  영상 실측 없음  ·  OLD {ho_:.3f} m → {TAG} {hf_:.3f} m"
    go = lambda k: np.interp(tg, Lo["t"], Lo[k])
    gf = lambda k: np.interp(tg, Lf["t"], Lf[k])
    # ★ τ = 총 인가 토크 (tq1/tq2). 구 sh1/sh2·s1/s2 는 토크맵 출력만이라 쓰지 않는다.
    old = [go("q1"), go("q2"), go("dq1"), go("dq2"), go("tq1"), go("tq2")]
    fs = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2"), gf("tq1"), gf("tq2")]
    meas = {k: d[k][m] for k, _ in CH}
    mm = tg >= 0.0
    eo = [np.sqrt(np.mean((meas[k][mm] - v[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
          for (k, _), v in zip(CH, old)]
    ef = [np.sqrt(np.mean((meas[k][mm] - v[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
          for (k, _), v in zip(CH, fs)]
    fig, ax = panels(f"{sess} / {name} — ModeA 통짜 재생 (측정 raw 주입 · 점프 창 · 중간 리셋 없음)\n{HT}",
                     f"창 RMSE (q1/q2/dq1/dq2/τ1/τ2)  OLD: {' / '.join('%.2f' % x for x in eo)}   "
                     f"{TAG}: {' / '.join('%.2f' % x for x in ef)}"
                     f"      ※ τ 는 **총 인가 토크**(보정 전부 포함) · 실측 τ 는 a_hat 변환값이라 참고용")
    for j_, (a, (k, _)) in enumerate(zip(ax, CH)):
        y, yo, yf = meas[k], old[j_], fs[j_]
        if k in ("q1", "q2"):
            y, yo, yf = np.degrees(y), np.degrees(yo), np.degrees(yf)
        a.plot(t[m], y, lw=1.2, label="실측" + (" (a_hat 변환)" if k in ("a1", "a2") else ""))
        a.plot(t[m], yo, "--", lw=1.0, label="배포모델 (OLD) 총 인가")
        a.plot(t[m], yf, ":", lw=1.5, label=f"현행 ({TAG}) 총 인가")
    ax[0].legend(fontsize=8, loc="best")
    ax[4].legend(fontsize=7, loc="best")
    fig.tight_layout()
    fp = OUT / "ModeA" / sess
    fp.mkdir(parents=True, exist_ok=True)
    fig.savefig(fp / f"{name}.png", dpi=105)
    plt.close(fig)
    return eo, ef


def summary_fig(folder, sess, rows, mode):
    """세션 요약: 채널별 OLD vs 현행 평균 RMSE 막대."""
    if not rows:
        return
    O = np.nanmean([r[0] for r in rows], axis=0)
    F = np.nanmean([r[1] for r in rows], axis=0)
    fig, a = plt.subplots(figsize=(7.5, 4))
    x = np.arange(6)
    a.bar(x - 0.19, O, 0.38, label="배포모델 (OLD)")
    a.bar(x + 0.19, F, 0.38, label="현행 (fs)")
    a.set_xticks(x); a.set_xticklabels([c[1].split(" ")[0] for c in CH])
    a.set_ylabel("RMSE (창 평균)")
    a.set_title(f"{sess} — {mode} 채널별 (trial {len(rows)}개 평균)")
    a.legend(); a.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(folder / "_summary.png", dpi=105)
    plt.close(fig)
    return O, F


def main():
    want = sys.argv[1].upper() if len(sys.argv) > 1 else "BOTH"
    OUT.mkdir(exist_ok=True)
    agg = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue                       # CVT는 fs_cvt_plot (모델 경로 상이)
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
        except Exception as ex:
            print(f"{s}/{p.name}: LOAD {type(ex).__name__}", flush=True)
            continue
        if want in ("BOTH", "CL") and not ho and g:
            r = plot_cl(s, p.name, d, seg, g)
            if r:
                agg.setdefault(("CL", s), []).append(r)
        if want in ("BOTH", "MA"):
            r = plot_ma(s, p.name, d, seg)
            if r:
                agg.setdefault(("ModeA", s), []).append(r)
        print(f"{s}/{p.name}: OK", flush=True)
    lines = [f"# 3자 비교 그래프 색인 (실측 / 배포모델 OLD α / 현행 {os.environ.get('FS_STACK_TAG', 'fs')})", "",
             "- `CL/<세션>/<trial>.png` — 폐루프, 점프(push) 구간",
             "- `ModeA/<세션>/<trial>.png` — 측정 토크 주입 재생 (0.4s 창)",
             "- 각 세션 폴더의 `_summary.png` = 채널별 평균 RMSE 막대", "",
             "| 모드 | 세션 | trial | q1 | q2 | dq1 | dq2 | τ1 | τ2 |", "|---|---|---|---|---|---|---|---|---|"]
    for (mode, s), rows in sorted(agg.items()):
        folder = OUT / mode / s
        res = summary_fig(folder, s, rows, mode)
        if res is None:
            continue
        O, F = res
        lines.append(f"| {mode} | {s} | {len(rows)} | " +
                     " | ".join(f"{O[i]:.2f}→{F[i]:.2f}" for i in range(6)) + " |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\ndone → {OUT} ({len(agg)} 세션·모드 조합)", flush=True)


if __name__ == "__main__":
    main()
