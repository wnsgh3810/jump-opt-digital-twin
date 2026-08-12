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
    """G63: 단일 출처 `fs_runner.sess_params` 로 위임 (구현 중복 제거)."""
    return FR.sess_params(sess)


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
# 짐 지고 일어서기(26.06.04) 게인 — 폴더에 없어 기록에서 되돌려 푼 추정값 (08-12)
S2S_GAIN = (147.0, 2.2, 205.0, 2.5)   # (힙 비례, 힙 미분, 무릎 비례, 무릎 미분)
MA_W, MA_S = 0.10, 0.05     # 점프 창(~0.2~0.3s) 내 mshoot 창/stride
CH = [("q1", "q1 [°]"), ("q2", "q2 [°]"), ("dq1", "dq1 [rad/s]"),
      ("dq2", "dq2 [rad/s]"), ("a1", "τ1 [N·m]"), ("a2", "τ2 [N·m]")]


def sh(x, n=QS):
    y = np.empty_like(x); y[n:] = x[:-n]; y[:n] = x[0]
    return y


def tau_ref(raw, v, ch, *, old):
    """모터 명령(raw) → 관절 토크. **비교의 기준선을 만드는 함수** (사용자 지시 08-11).

    왜 이게 필요한가
      모터가 남기는 기록은 "이만큼 힘을 내라"는 **명령**뿐이다. 관절에 실제로 걸린
      토크는 이 데이터에 없다. 명령을 토크로 바꾸려면 변환식이 필요한데, 그 변환식은
      **모델의 일부**다 (기존 배포판 = a_hat / 현행 = 정본곡선 canon_cap).

      구판은 기준선을 **항상 a_hat 으로만** 그렸다. 그래서 현행 스택은 자기 변환식으로
      계산한 토크를 **남의 변환식으로 만든 선**과 비교당했다 — 비교가 성립하지 않는다
      (변환식 차이만으로 힙 2.16 · 무릎 3.66 Nm 가 오차로 잡힌다. 동역학 성분 0).

      사용자 지시: 폐루프에서 알고 싶은 것은 "내 궤적·게인을 실제 로봇에 넣으면
      계획대로 움직이고 계획한 토크가 나오는가"다. 그러려면 **실측 명령과 시뮬레이션을
      같은 변환식으로 바꿔** 비교해야 한다. 그래서 기준선을 모델마다 따로 만든다.

    한계 (그림 제목에도 적는다)
      양쪽에 같은 변환식이 들어가므로 **변환식 자체가 맞는지는 이 비교로 알 수 없다.**
      변환식이 틀려도 두 선이 함께 움직인다. 그건 분동/로드셀 교정으로 따로 결판낼 일.

    old=True  → 배포판 변환식 (a_hat)
    old=False → 현행 스택 변환식 (FS_TMAP 등 환경변수 그대로 존중)

    ★ ch 규약: **0 = 힙, 1 = 무릎** (fs_runner 롤아웃 호출부와 동일 —
      `_tmap(r1, v1c, 0)` / `_tmap(r2, v2c, 1)`). canon_cap 의 캡이 채널마다
      다르므로(FS_TDCAP="무릎,힙") 뒤집으면 힙 기준선이 조용히 틀어진다.
      실제로 08-11 첫 구현에서 뒤집었다가 힙이 1.20Nm 어긋나 잡았다.
    """
    raw = np.asarray(raw, float); v = np.asarray(v, float)
    P = FMET.tw0["P"]; A = P.A_PAPER
    if old:
        return P.J.ahat(A, raw, v)
    tm = FR._tmap_init(P, A)
    if tm is None:                       # 현행도 a_hat 인 구성 (레거시 경로)
        return P.J.ahat(A, raw, v)
    return np.array([tm(float(r), float(w), ch) for r, w in zip(raw, v)])


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


def cl_pair(d, seg, g, sess, ft=None, show_old=True):
    """CL을 **ModeA와 동일 규칙**으로: 점프 창 시작에서 실측 상태 1회 앵커 → 통짜 폐루프 (P16).
    반환 (t, 실측, OLD, 현행, 창마스크) — 실패 시 None.

    ★ 08-12: `ft` 를 주면 그 트윈으로 돌린다. 변속기 실험은 링크 길이가 곧 모델 치수라
      trial 마다 다른 모델을 써야 하기 때문이다 (`fs_cvt.cvt_ft`). 안 주면 지금까지처럼
      무변속 트윈을 새로 받아 쓰므로 **무변속 세션의 결과는 한 자리도 안 바뀐다.**"""
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
    # ★ 08-12: show_old=False 면 배포 모델을 안 돌린다 (짐 지고 일어서기 — 배포 모델에는
    #   짐을 넣을 방법이 없어 비교가 성립하지 않는다).
    Lo = cl_old_meas(FMET.tw0, t, *qd, tuple(g), alphas, t_end, init) if show_old else None
    if ft is None:
        ft = FR.fs_twin()
    sp = sess_params(sess)          # ★ G53: FS_NOBIAS/FS_NODEEP 존중 (정본 단일 출처)
    # ★ 08-11 판별용 노브 (사용자 제기 "알파 문제 아냐?"): 무릎 kp 를 줄여서 넣는다.
    #   FS_KNEE_A="table" → α(kp) 표 보간 (게인 의존) · FS_KNEE_A="0.656" → 상수배 (게인 무관)
    #   미설정 = 현행(=1.0, α 없음). 배포모델은 원래 α 를 쓴다(alphas_for) — 그래서 이 노브가
    #   **게인 의존이 실체인지 단순 과대인지**를 가른다. 상수배로도 고쳐지면 α 가설은 기각.
    _ka = os.environ.get("FS_KNEE_A")
    gg = tuple(g)
    if _ka:
        _s = alpha_of(TK, g[2]) if _ka == "table" else float(_ka)
        gg = (g[0], g[1], g[2] * _s, g[3])
    Lf = FR.rollout_cl_fs(ft, t, sh(qd[0]), sh(qd[1]), sh(qd[2]), sh(qd[3]),
                          gg, t_end, two_stage=True, bias1=sp["bias1"], knee_deep=sp["knee_deep"],
                          fade=True, taulim=None, vdes_ff=(sess != "26.04.21"), init_meas=init)
    if (show_old and Lo is None) or Lf is None:
        return None
    gi = lambda L, k: np.interp(t, L["t"], L[k])
    old = ([gi(Lo, "q1"), gi(Lo, "q2"), gi(Lo, "dq1"), gi(Lo, "dq2"), gi(Lo, "sh1"), gi(Lo, "sh2")]
           if show_old else [np.full(len(t), np.nan)] * 6)
    fs = [gi(Lf, "thm1"), gi(Lf, "q2"), gi(Lf, "dq1"), gi(Lf, "dq2"),
          np.clip(gi(Lf, "s1f"), -20.5, 20.5), gi(Lf, "s2")]
    # ★ 08-11: τ 기준선을 **모델마다** 만든다 (tau_ref 참조).
    #   각도·각속도는 센서 실측이라 하나뿐이고, τ 만 변환식에 따라 달라진다.
    meas_o = {k: d[k][m] for k, _ in CH}
    meas_f = dict(meas_o)
    meas_o["a1"] = tau_ref(d["raw1"][m], d["dq1"][m], 0, old=True)
    meas_o["a2"] = tau_ref(d["raw2"][m], d["dq2"][m], 1, old=True)
    meas_f["a1"] = tau_ref(d["raw1"][m], d["dq1"][m], 0, old=False)
    meas_f["a2"] = tau_ref(d["raw2"][m], d["dq2"][m], 1, old=False)
    cmd = [d["qd1"][m], d["qd2"][m], d["dqd1"][m], d["dqd2"][m], None, None]   # exp5 형식: 명령 병기
    pl = plan_of(sess, t, d["qd2"][m])                                        # 배포 계획 (있는 세션만)
    return tt[m], (meas_o, meas_f), old, fs, np.ones(m.sum(), bool), cmd, pl



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


def plot_cl(sess, name, d, seg, g, ft=None, show_old=True, note=""):
    r = cl_pair(d, seg, g, sess, ft=ft, show_old=show_old)
    if r is None:
        print(f"  CL {sess}/{name}: 롤아웃 실패", flush=True)
        return
    t, (meas_o, meas_f), old, fs, m, cmd, pl = r
    _ht = h_title(sess, name)
    fig, ax = panels(f"{sess} / {name} — CL 점프 구간 (창 시작 실측 앵커 · 통짜) · 실측 vs 배포계획(τ*) vs 배포모델 재생(OLD) vs 현행({TAG})" + (f" | 계획 정렬 {pl[1]*1000:+.0f}ms" if pl else "")
                     + ("\n" + _ht if _ht else ""),
                     f"창 RMSE (q1/q2/dq1/dq2/τ1/τ2)  OLD: {rmse_line(meas_o, m, old)}   {TAG}: {rmse_line(meas_f, m, fs)}"
                     + "\n※ τ 는 **각 모델의 변환식으로 실측 명령을 바꾼 값**과 비교한다 "
                       "(모터는 명령만 기록 — 축토크 실측은 없음). 변환식이 맞는지는 이 그림으로 알 수 없다.")
    for j, (a, (k, _)) in enumerate(zip(ax, CH)):
        y, yf2, yo, yf = meas_o[k], meas_f[k], old[j], fs[j]
        if k in ("q1", "q2"):
            y, yf2, yo, yf = np.degrees(y), np.degrees(yf2), np.degrees(yo), np.degrees(yf)
        _tau = k in ("a1", "a2")
        a.plot(t, y, lw=1.2, label="실측 명령 → 배포판 변환" if _tau else "실측")
        if _tau:
            # ★ 현행 변환식 기준선 — 현행 sim 은 **이 선**과 비교해야 한다 (사용자 지시 08-11)
            a.plot(t, yf2, lw=1.2, alpha=0.9, label=f"실측 명령 → {TAG} 변환")
        if show_old:
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
    for _i in (4, 5):                    # τ 패널은 선이 4개라 범례를 따로 단다
        ax[_i].legend(fontsize=6.5, loc="best")
    fig.tight_layout()
    fp = OUT / "CL" / sess
    fp.mkdir(parents=True, exist_ok=True)
    fig.savefig(fp / f"{name}.png", dpi=105)
    plt.close(fig)
    conv = lambda M, k, v: np.sqrt(np.mean((M[k][m] - v[m]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
    return ([conv(meas_o, k, v) for (k, _), v in zip(CH, old)],
            [conv(meas_f, k, v) for (k, _), v in zip(CH, fs)])


H_LOG = {}          # (세션,trial) → (영상 h, OLD h, 현행 h) — 점프높이는 1급 게이트라 함께 남긴다


def h_title(sess, name):
    """제목용 점프높이 한 줄 (사용자 지시: 그래프 제목에 점프높이).

    ★ 정의는 **하나뿐**이다 — 지면 기준 베이스 중심 최고높이, ModeA 연장재생으로 판독
      (`_F_jumph_abs` 정본). CL 은 이륙에서 롤아웃이 끝나 최고점이 없으므로 **같은 trial 의
      ModeA 값을 그대로 쓰고 그렇게 표기**한다. 체공 상승분 등 다른 정의와 섞지 않는다.
    """
    v = H_LOG.get(f"{sess}|{name}")
    if not v:
        return ""
    hv, ho_, hf_ = v
    if hv:
        return (f"점프높이(ModeA 연장재생)  영상 {hv:.3f} m  ·  OLD {ho_:.3f} m "
                f"({100*(ho_/hv-1):+.1f}%)  →  {TAG} {hf_:.3f} m ({100*(hf_/hv-1):+.1f}%)")
    return f"점프높이(ModeA 연장재생)  영상 실측 없음  ·  OLD {ho_:.3f} m → {TAG} {hf_:.3f} m"


def plot_ma(sess, name, d, seg, ft=None, show_old=True):
    """ModeA = **점프 창 통짜 개루프 재생** (측정 raw 주입, 초기상태만 실측 — 중간 리셋 없음).

    사용자 지적 (08-01): 창 분할 재생은 에러가 매 창 초기화돼 모델 발전의 자가 될 수 없다.
    점프 창(~0.2~0.3s)은 통짜 재생이 가능하므로 R19 정본 재생 방식(단일 샷)을 따른다.

    ★ G55 (사용자 지시): τ 패널을 **양쪽 모두 "실제 조인트에 들어간 총 토크"** 로 바꾼다.
      · OLD  = a_hat + hip_supp_scalar / a_hat + supp_scalar + rise_term  (`ol_old_meas.tq*`)
      · 현행 = 토크맵(canon_cap 등) 출력 + 커맨드층 보정 전부           (`rollout_ol_fs_b.tq*`)
      구 방식(`sh1/sh2` vs `s1/s2`)은 **a_hat 출력만**이라 OLD 를 과소 표시했다.
      제목에 **점프높이**(영상 실측 vs 두 모델, 부호 있는 오차)를 병기한다.

    ★ 08-12: `ft` 를 주면 그 트윈으로 돌린다 — 변속기는 trial 마다 모델이 다르고,
      짐 지고 일어서기는 짐 무게가 모델에 들어간다. 안 주면 지금까지와 완전히 동일하다.

    ★ 08-12 (사용자 지시): `show_old=False` 면 **배포 모델 선을 그리지 않는다.**
      짐 지고 일어서기에서 쓴다 — 배포 모델에는 **짐을 넣을 방법이 없어서**, 5kg 을 지고
      있는데 그걸 모르는 모델과 비교하면 성립하지 않는다 (실제로 무릎 각도 3532도가 나왔다).
      비교 대상이 없는 그림은 실측 vs 현행 둘만 그린다.
    """
    ft = ft if ft is not None else FR.fs_twin()
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
    Lo = ol_old_meas(FMET.tw0, tg, d["raw1"][m], d["raw2"][m], st, t_end, 0.004) if show_old else None
    Lf = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                            float(d["q1"][i0]), float(d["q2"][i0]),
                            float(d["dq1"][i0]), float(d["dq2"][i0]),
                            t_end, bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
    if (show_old and Lo is None) or Lf is None:
        print(f"  MA {sess}/{name}: 재생 실패 (old {Lo is None} / fs {Lf is None})", flush=True)
        return
    # 점프높이 (연장 재생으로 최고점 직접 판독)
    hv = real_h(d["_fold"])
    te2 = float(tg2[-1] - 0.004)
    Ho = ol_old_meas(FMET.tw0, tg2, d["raw1"][m2], d["raw2"][m2], st, te2, 0.004) if show_old else None
    Hf = FR.rollout_ol_fs_b(ft, tg2, d["raw1"][m2], d["raw2"][m2],
                            float(d["q1"][i0]), float(d["q2"][i0]),
                            float(d["dq1"][i0]), float(d["dq2"][i0]),
                            te2, bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True)
    ho_ = float(np.asarray(Ho["bz"]).max()) if Ho else np.nan
    hf_ = float(np.asarray(Hf["bz"]).max()) if Hf else np.nan
    H_LOG[f"{sess}|{name}"] = (hv, ho_, hf_)
    HT = h_title(sess, name)
    go = (lambda k: np.interp(tg, Lo["t"], Lo[k])) if show_old else None
    gf = lambda k: np.interp(tg, Lf["t"], Lf[k])
    # ★ τ = 총 인가 토크 (tq1/tq2). 구 sh1/sh2·s1/s2 는 토크맵 출력만이라 쓰지 않는다.
    old = ([go("q1"), go("q2"), go("dq1"), go("dq2"), go("tq1"), go("tq2")]
           if show_old else [np.full(len(tg), np.nan)] * 6)
    fs = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2"), gf("tq1"), gf("tq2")]
    # ★ 08-11: CL 과 동일하게 τ 기준선을 **모델마다** 만든다 (tau_ref 참조).
    meas = {k: d[k][m] for k, _ in CH}
    meas_f = dict(meas)
    meas["a1"] = tau_ref(d["raw1"][m], d["dq1"][m], 0, old=True)
    meas["a2"] = tau_ref(d["raw2"][m], d["dq2"][m], 1, old=True)
    meas_f["a1"] = tau_ref(d["raw1"][m], d["dq1"][m], 0, old=False)
    meas_f["a2"] = tau_ref(d["raw2"][m], d["dq2"][m], 1, old=False)
    mm = tg >= 0.0
    eo = ([np.sqrt(np.mean((meas[k][mm] - v[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
           for (k, _), v in zip(CH, old)] if show_old else [np.nan] * 6)
    ef = [np.sqrt(np.mean((meas_f[k][mm] - v[mm]) ** 2)) * (180 / np.pi if k in ("q1", "q2") else 1)
          for (k, _), v in zip(CH, fs)]
    fig, ax = panels(f"{sess} / {name} — ModeA 통짜 재생 (측정 raw 주입 · 점프 창 · 중간 리셋 없음)\n{HT}",
                     f"창 RMSE (q1/q2/dq1/dq2/τ1/τ2)  OLD: {' / '.join('%.2f' % x for x in eo)}   "
                     f"{TAG}: {' / '.join('%.2f' % x for x in ef)}"
                     f"\n※ τ 는 **각 모델의 변환식으로 실측 명령을 바꾼 값**과 비교 "
                     f"(모터는 명령만 기록 — 축토크 실측은 없음). 변환식이 맞는지는 이 그림으로 알 수 없다.")
    for j_, (a, (k, _)) in enumerate(zip(ax, CH)):
        y, yf2, yo, yf = meas[k], meas_f[k], old[j_], fs[j_]
        if k in ("q1", "q2"):
            y, yf2, yo, yf = np.degrees(y), np.degrees(yf2), np.degrees(yo), np.degrees(yf)
        # ★ G58: τ 패널은 **각 선의 고점을 범례에 숫자로** 박는다 (축 오독 방지 — 사용자 지적).
        _tau = k in ("a1", "a2")
        pk = (lambda v: f"  [고점 {np.max(v):.2f}]") if _tau else (lambda v: "")
        if not (_tau and not show_old):
            a.plot(t[m], y, lw=1.2,
                   label=("실측 명령 → 배포판 변환" if _tau else "실측") + pk(y))
        if _tau:
            a.plot(t[m], yf2, lw=1.2, alpha=0.9,
                   label=("실측 명령 → 변환" if not show_old else f"실측 명령 → {TAG} 변환") + pk(yf2))
        if show_old:
            a.plot(t[m], yo, "--", lw=1.0, label="배포모델 (OLD) 총 인가" + pk(yo))
        a.plot(t[m], yf, ":", lw=1.5, label=f"현행 ({TAG}) 총 인가" + pk(yf))
        if k in ("a1", "a2"):
            # ★ G57 (사용자 정정): `currentTorque` 는 **단위가 이미 N·m** 이다.
            #   AK80-9 매뉴얼: `float T_MIN=-18; T_MAX=18; t_int=float_to_uint(t_ff,T_MIN,T_MAX,12)`
            #   즉 ±18 N·m 를 12bit 로 인코딩한 값 (사양표 N.M 행도 -18~18).
            #   ⇒ 별도 축(twinx)이 아니라 **같은 Nm 축**에 그려야 직접 비교가 된다.
            #   이 선이 곧 "모터가 내겠다고 명령받은 토크"이고, τ 곡선들은 각 모델이
            #   그 명령을 자기 환율(a_hat / canon_cap)로 해석해 **실제 관절에 넣은 토크**다.
            #   규약 ⑤(색 리터럴 금지): 기본 사이클의 4번째 색 (실측·OLD·현행과 비충돌).
            rk = "raw1" if k == "a1" else "raw2"
            a.plot(t[m], d[rk][m], lw=1.0, alpha=0.85,
                   label=f"모터 명령 (엑셀 원본, 무변환) [고점 {np.max(d[rk][m]):.2f}]")
    ax[0].legend(fontsize=8, loc="best")
    for _i in (4, 5):                      # ★ G58: τ1·τ2 **양쪽 다** 범례(=고점 숫자) 표시
        ax[_i].legend(fontsize=6.5, loc="best")
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
        # ★ held-out 은 **fit 금지**이지 평가 금지가 아니다 (철칙 9).
        #   승격 판단엔 게이트 세션의 CL 비악화도 봐야 하므로 FS_CMP_HO=1 로 포함시킨다.
        _ho_ok = (not ho) or os.environ.get("FS_CMP_HO") == "1"
        # ★ ModeA 를 **먼저** 돌린다 — 점프높이는 ModeA 연장재생에서만 나오고(정본 정의),
        #   CL 제목도 그 값을 쓰기 때문이다 (사용자 지시: 제목에 점프높이).
        if want in ("BOTH", "MA", "CL"):
            r = plot_ma(s, p.name, d, seg)
            if r and want in ("BOTH", "MA"):
                agg.setdefault(("ModeA", s), []).append(r)
        if want in ("BOTH", "CL") and _ho_ok and g:
            r = plot_cl(s, p.name, d, seg, g)
            if r:
                agg.setdefault(("CL", s), []).append(r)
        print(f"{s}/{p.name}: OK", flush=True)
    # ── 짐 지고 일어서기 (26.06.04) — **검증 전용** (FS_CMP_S2S=0 으로 끌 수 있다) ──
    #   최종 목표가 "짐 지고 일어서기 같은 해본 적 없는 동작 예측"인데 채점 세션이 전부
    #   점프라 외삽을 한 번도 그려 본 적이 없었다 (08-12 발견). 창은 `plot_window` 가
    #   '몸통이 떠 있는 구간'으로 준다 (규약 §7 off-stop — 앉은 구간은 물리가 없다).
    #   ★ 재생 자체는 여기서도 **통짜**다. 조각으로 자르면 오차가 초기화된다 (규약 §11-2).
    if want in ("BOTH", "MA", "S2S") and os.environ.get("FS_CMP_S2S", "1") != "0":
        import fs_cvt as FC
        _m0 = os.environ.get("FS_MASS", "3.2988")
        for nm, fold, pay, cvt in FD.s2s_registry():
            try:
                d = FD.load_s2s(nm)
                d["_sess"] = "26.06.04"; d["_fold"] = fold
                os.environ["FS_MASS"] = f"{float(_m0) + pay:.4f}"   # 짐은 몸통에 통째로 (사용자 확인)
                FR._S2S = None
                if cvt:
                    FC._MC.clear(); FC._RT.clear()
                ft_s = FC.cvt_ft(d["l_i"], ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
                _nm = f"{nm.replace('/', '_')}_짐{pay:g}kg"
                r = plot_ma("26.06.04", _nm, d, None, ft=ft_s, show_old=False)
                if r:
                    agg.setdefault(("ModeA", "26.06.04"), []).append(r)
                # ── 폐루프 ────────────────────────────────────────────────────────
                # ★ 이 세션은 폴더 이름에 게인이 없다 (점프 세션은 폴더명이 곧 게인).
                #   그래서 **기록에서 되돌려 풀었다**: 토크 = 비례x각도오차 + 미분x속도오차
                #   를 최소제곱으로 푼다 (목표 채널을 2샘플 뒤로 밀어 시각을 맞춘 뒤).
                #   · 무릎 비례 = 네 경우 모두 200~211 로 일관 (맞춘 정도 0.86~0.99)
                #   · 힙 비례 = 99~149 로 흔들려, 가장 잘 맞은 경우(무변속 0kg, 0.94)의 147 채택
                #   · 미분 게인은 되돌려 풀면 음수까지 나온다(속도 신호 잡음) -> 점프 세션의
                #     비례:미분 비율(약 1.5%)을 적용. **여기만 추정이 섞였다.**
                _note = ("* 게인은 폴더에 없어 **기록에서 되돌려 푼 추정값**이다 "
                         f"(비례 힙 {S2S_GAIN[0]:g} / 무릎 {S2S_GAIN[2]:g}; "
                         "미분은 점프 세션 비율 적용). 실제 게인이 확인되면 다시 그릴 것.")
                r2 = plot_cl("26.06.04", _nm, d, None, S2S_GAIN, ft=ft_s,
                             show_old=False, note=_note)
                if r2:
                    agg.setdefault(("CL", "26.06.04"), []).append(r2)
                print(f"26.06.04/{nm} (짐 {pay:g}kg): OK", flush=True)
            except Exception as ex:
                print(f"26.06.04/{nm}: {type(ex).__name__} {ex}", flush=True)
        os.environ["FS_MASS"] = _m0
        FR._S2S = None
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
    # ★ 표를 다시 파싱하지 않도록 원수치를 함께 남긴다 (표만 낡는 사고 08-09 재발 방지)
    import safe
    safe.atomic_json_write(OUT / "_rmse.json", {
        f"{mode}|{s}": dict(n=len(rows), ch=[c[0] for c in CH],
                            old=np.nanmean([r[0] for r in rows], axis=0).tolist(),
                            new=np.nanmean([r[1] for r in rows], axis=0).tolist())
        for (mode, s), rows in agg.items()})
    safe.atomic_json_write(OUT / "_jumph.json", H_LOG)
    print(f"\ndone → {OUT} ({len(agg)} 세션·모드 조합)", flush=True)


if __name__ == "__main__":
    main()
