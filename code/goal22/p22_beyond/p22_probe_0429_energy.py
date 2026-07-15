# -*- coding: utf-8 -*-
"""P22 Phase 0c — 0429 에너지 잉여(rho~1.4) 3-가설 판별 프로브.

T3(p20_rise/p22_probe_t3) 원장 재사용. 0429(CVT l_i=25.08mm)만 푸시 입력일
W_in = ∫a_hat·dq dt 가 E_req = M·g·Δh 보다 +20~71% 크고, 무변속(0424/0602)은
leg-KE 보정 시 거의 정확히 균형. 이 잉여의 귀속을 정량 판별:

  H1: a_hat 포화항(A1·GR·|Iq|·Iq)이 고전류대(|traw|>30)에서 과소차감
      -> 축토크 과대추정 = 유령 일 (측정 문제, 0429만 그 대역에서 동작)
  H2: CVT(비평행사변형 l_i=25.08) 강도비례 실전달손실 (물리 손실)
  H3: 0429 전용 규약 오류 (bz0 폐쇄 FK / h_real 메타 / crank-vs-knee / leg-KE 과대)

unwrap 분기는 재감사하지 않음 — REJECTED.md #27 (push 구간 unwrap 정상 확정) 인용만.

산출:
  T1: |traw| 전류-bin [0,20)/[20,30)/[30,~35.5] 별 채널 W_in 분해 + 누적 W_in-E_req
  T2: H1 정량화 — A1 -> s·A1 스칼라 (per-trial s_i, 전역 s*) + 무변속 교차검증 이동량
      + 임계형 변형(H1b: raw>R0 초과분 제곱 droop) 동일 검증
  T3: H3 감사 — bz0/h_real 재확인, 무릎측(정직) leg-KE (폐쇄 전달비 r(t)=dqk/dqc)
  T4: verdict 표 (트라이얼별 잉여 귀속)
"""
import sys
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "code" / "bench"))
import p19_adapter as AD    # noqa: E402  (sys.path 셋업: p19_jump/p18_cvt/p20_rise 등)
import safe                  # noqa: E402

safe.utf8_console()
AD.ensure_init()
import p22_probe_t3 as T3    # noqa: E402  (T3 규약 함수/모델 재사용 — 재구현 금지)
from cvt_core import qpos_from_crank  # noqa: E402

P, R = T3.P, T3.R
MJ, S = T3.MJ, T3.S
M_TOT, G = T3.M_TOT, T3.G
A = P.A_PAPER
KT, GR, CF = P.J.KT, P.J.GR, P.J.CF          # 0.091 / 9.0 / 0.59
C_IQ = CF / (GR * KT)                        # raw(iTM) -> Iq [A]
BEDGE = [0.0, 20.0, 30.0, np.inf]
BLBL = ["0-20", "20-30", "30+"]
CROSS_DS = ("jump_position_0421", "jump_0424", "jump_0602")


def iq(traw):
    return C_IQ * np.asarray(traw, float)


def droop_pw(traw, dq):
    """A1 항의 일률 기여 [W] / A1 스케일 1 기준: A1·GR·|Iq|·Iq·dq."""
    I = iq(traw)
    return A[1] * GR * np.abs(I) * I * np.asarray(dq, float)


def thresh_pw(traw, dq, r0_raw):
    """임계형(H1b) droop 일률 커널: GR·(|Iq|-Iq0)+²·sign(Iq)·dq (계수 c는 별도)."""
    I = iq(traw)
    ex = np.maximum(np.abs(I) - C_IQ * r0_raw, 0.0)
    return GR * ex ** 2 * np.sign(I) * np.asarray(dq, float)


def cumtrapz(y, x):
    c = np.zeros_like(y)
    c[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return c


def bin_sums(pw, traw, t, t_end):
    """푸시 창 내 |traw| bin 별 pw 적분 (직사각형 근사, dt 균일)."""
    m = t <= t_end
    dt = float(np.median(np.diff(t)))
    a = np.abs(traw)
    out = []
    for lo, hi in zip(BEDGE[:-1], BEDGE[1:]):
        mb = m & (a >= lo) & (a < hi)
        out.append(float(np.sum(pw[mb]) * dt))
    return out


def cvt_leg_ke(model, l_i, q1, q2c, dq1, dq2c):
    """CVT 모델 정직 leg-KE: 폐쇄 일관 qvel(전달비 r, dqpin/dqc 유한차분) + 트리 질량행렬."""
    sq1, sq2 = -q1 - np.pi / 2, -q2c
    qp, qk, r = qpos_from_crank(1.0, sq1, sq2, l_i)
    eps = 1e-5
    qp2, _, _ = qpos_from_crank(1.0, sq1, sq2 + eps, l_i, qk)
    dpin = (((qp2[3] - qp[3]) + np.pi) % (2 * np.pi) - np.pi) / eps   # dqpin/dqc(mj)
    dqk = (qp2[4] - qp[4]) / eps                                       # = r (검증용)
    md = MJ.MjData(model)
    md.qpos[:] = qp
    md.qvel[:] = 0
    MJ.mj_forward(model, md)
    Mfull = np.zeros((model.nv, model.nv))
    MJ.mj_fullM(model, Mfull, md.qM)
    dsq1, dsq2 = -dq1, -dq2c
    v = np.array([0.0, dsq1, dsq2, dpin * dsq2, dqk * dsq2])
    return 0.5 * float(v @ Mfull @ v), float(r), float(dqk)


def main():
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    cl_idx = {(tr["ds"], str(tr["sub"])): (int(tr["on"]), int(tr["toff"]))
              for tr in P.J._P["cl"]}
    t3rows = {(r_["ds"], r_["sub"]): r_
              for r_ in safe.read_json(REPO / "code/goal22/p20_rise/p22_probe_t3_result.json")["rows"]}

    rows = []
    for ds, sub, d, gains, dqon, ffk, mask, is_cvt, l_i in R.TRIALS:
        if ds == "jump_0324":
            continue                      # held-out — 판정 절대 금지
        t = d["t"]
        if is_cvt:
            i_off = T3.toff_0429(d)
        else:
            _, i_off = cl_idx[(ds, str(sub))]
        i_off = min(i_off, len(t) - 1)
        t_lo = float(t[i_off])
        # ── 채널별 일률 ──
        a1 = P.J.ahat(A, d["traw1"], d["dq1"])
        a2 = P.J.ahat(A, d["traw2"], d["dq2"])
        pw1 = a1 * d["dq1"]
        pw2 = a2 * d["dq2"]
        pw = pw1 + pw2
        W_in = T3.win_upto(t, pw, t_lo)
        W1 = T3.win_upto(t, pw1, t_lo)
        W2 = T3.win_upto(t, pw2, t_lo)
        # ── T1: 전류-bin 분해 (채널별, 자기 채널 |traw| 기준) ──
        b2 = bin_sums(pw2, d["traw2"], t, t_lo)
        b1 = bin_sums(pw1, d["traw1"], t, t_lo)
        m = t <= t_lo
        med2 = float(np.median(np.abs(d["traw2"][m])))
        med1 = float(np.median(np.abs(d["traw1"][m])))
        # ── H1 커널 적분 (A1 droop 일 / 임계형 일) ──
        K = T3.win_upto(t, droop_pw(d["traw1"], d["dq1"]) + droop_pw(d["traw2"], d["dq2"]), t_lo)
        Kth30 = T3.win_upto(t, thresh_pw(d["traw1"], d["dq1"], 30.0)
                            + thresh_pw(d["traw2"], d["dq2"], 30.0), t_lo)
        Kth33 = T3.win_upto(t, thresh_pw(d["traw1"], d["dq1"], 33.0)
                            + thresh_pw(d["traw2"], d["dq2"], 33.0), t_lo)
        # 보조 커널: 점성 과대판독 (Paper a_hat엔 점성항 없음) 유령일 = b·∫dq² dt
        Kv = T3.win_upto(t, d["dq1"] ** 2 + d["dq2"] ** 2, t_lo)
        # 속도-bin 별 knee 일 점유 (>30 rad/s 는 0429 전용 대역 — H1/H2 교락 정량화)
        bv2 = []
        mwin = t <= t_lo
        dtu = float(np.median(np.diff(t)))
        for lo, hi in zip(BEDGE[:-1], BEDGE[1:]):
            mb = mwin & (np.abs(d["dq2"]) >= lo) & (np.abs(d["dq2"]) < hi)
            bv2.append(float(np.sum(pw2[mb]) * dtu))
        # ── E_req (T3 규약 재계산 + 대조) ──
        model = T3.model_of(is_cvt, l_i)
        md = MJ.MjData(model)
        bz0, _, qk0 = T3.bz_fk(md, model, is_cvt, l_i, d["q1"][0], d["q2"][0])
        z = np.load(T3.NPZ_ROOT / T3.DSDIR[ds] / "traj" / f"{sub}__A.npz", allow_pickle=True)
        h_real = float(z["h_real"])
        bz_npz0 = float(z["bz"][int(np.argmin(np.abs(z["t"] - 0.0)))])
        E_req = M_TOT * G * (h_real - bz0)
        rho = W_in / E_req
        # ── leg-KE: T3(평행사변형+crank dq) vs 무릎측 보정 vs CVT 정직 ──
        q1o, q2o = float(d["q1"][i_off]), float(d["q2"][i_off])
        v1o, v2o = float(d["dq1"][i_off]), float(d["dq2"][i_off])
        ke_t3 = T3.leg_ke(MJ.MjData(T3.MODEL_F), T3.MODEL_F, q1o, q2o, v1o, v2o)
        h3 = {}
        if is_cvt:
            ke_cvt, r_lo, dqk_fd = cvt_leg_ke(model, l_i, q1o, q2o, v1o, v2o)
            # 무릎측 각/속도를 평행사변형 모델에 넣는 간이 보정 (task 지시 변형)
            _, qk_mj, r2 = qpos_from_crank(1.0, -q1o - np.pi / 2, -q2o, l_i)
            q2k = -qk_mj
            ke_par_knee = T3.leg_ke(MJ.MjData(T3.MODEL_F), T3.MODEL_F,
                                    q1o, q2k, v1o, r2 * v2o)
            # r(t) 프로파일 (푸시 창)
            r_tr = []
            qkp = None
            for i in range(0, i_off + 1, 2):
                _, qkp, r_i = qpos_from_crank(1.0, -d["q1"][i] - np.pi / 2,
                                              -d["q2"][i], l_i, qkp)
                r_tr.append(r_i)
            r_med = float(np.median(r_tr))
            # H3 감사: h_real 원본(Real Data.txt, cvt_core 파서) vs npz 메타
            h_txt = float(d.get("h_real", np.nan))
            # crank각을 무릎각으로 오인한 잘못된 평행사변형 FK와의 bz0 차 (규약 상한)
            bz0_par, _, _ = T3.bz_fk(MJ.MjData(T3.MODEL_F), T3.MODEL_F, False, 0.03,
                                     d["q1"][0], d["q2"][0])
            h3 = dict(ke_cvt=ke_cvt, ke_par_knee=float(ke_par_knee), r_lo=r_lo,
                      r_med=r_med, dqk_fd_err=abs(dqk_fd - r_lo),
                      h_txt=h_txt, dh_meta=h_real - h_txt,
                      bz0_par=float(bz0_par), dbz_conv=float(bz0_par - bz0),
                      l_i_mm=float(l_i * 1e3))
        # ── 누적 W_in − E_req (시간 분해) ──
        cw = cumtrapz(pw, t)
        idx = np.where(m)[0]
        cross = np.where(cw[idx] >= E_req)[0]
        t_cross = float(t[idx[cross[0]]]) if len(cross) else np.nan
        cum = dict(t=[round(float(x), 4) for x in t[idx][::2]],
                   dcum=[round(float(x), 3) for x in (cw[idx] - E_req)[::2]])
        # T3 결과와 정합성 (동일 규약 재계산 검증)
        t3r = t3rows.get((ds, str(sub)), {})
        chk = dict(dW_in=float(W_in - t3r.get("W_in", np.nan)),
                   dE_req=float(E_req - t3r.get("E_req", np.nan)))
        rows.append(dict(
            ds=ds, sub=str(sub), is_cvt=bool(is_cvt), t_lo=t_lo,
            W_in=float(W_in), W1=float(W1), W2=float(W2),
            b2=[float(x) for x in b2], b1=[float(x) for x in b1],
            med_raw2=med2, med_raw1=med1,
            K=float(K), Kth30=float(Kth30), Kth33=float(Kth33),
            Kv=float(Kv), bv2=[float(x) for x in bv2],
            E_req=float(E_req), rho=float(rho), bz0=float(bz0),
            bz_npz0=float(bz_npz0), h_real=h_real,
            ke_t3=float(ke_t3), t_cross=t_cross, cum=cum, chk=chk, **h3))

    # ════ T1 표: 전류-bin 분해 ════
    print("\n=== T1. knee 채널 W_in 전류-bin 분해 (푸시 [0,t_lo], |traw2| bin) ===")
    print(f"{'ds':18s} {'sub':18s} {'W_in':>6s} {'W2':>6s} "
          f"{'W2[0-20)':>8s} {'W2[20-30)':>9s} {'W2[30+]':>8s} {'sh30+':>6s} "
          f"{'med|r2|':>7s} {'E_req':>6s} {'rho':>5s}")
    for r_ in rows:
        sh = r_["b2"][2] / max(r_["W2"], 1e-9)
        print(f"{r_['ds']:18s} {r_['sub']:18s} {r_['W_in']:6.2f} {r_['W2']:6.2f} "
              f"{r_['b2'][0]:8.2f} {r_['b2'][1]:9.2f} {r_['b2'][2]:8.2f} {sh:6.1%} "
              f"{r_['med_raw2']:7.1f} {r_['E_req']:6.2f} {r_['rho']:5.2f}")
    print("\n--- 세션 합계 bin 점유율 (knee) ---")
    binsum = {}
    for ds in sorted(set(r_["ds"] for r_ in rows)):
        rs = [r_ for r_ in rows if r_["ds"] == ds]
        tot = sum(r_["W2"] for r_ in rs)
        shares = [sum(r_["b2"][k] for r_ in rs) / tot for k in range(3)]
        binsum[ds] = dict(W2=tot, shares=shares,
                          hip=[sum(r_["b1"][k] for r_ in rs) for k in range(3)])
        print(f"{ds:20s} W2={tot:6.1f} J  " +
              "  ".join(f"{BLBL[k]}:{shares[k]:6.1%}" for k in range(3)) +
              f"   hip W1 30+bin={binsum[ds]['hip'][2]:5.2f} J")

    # ════ T2: H1 스칼라 s (A1 -> s·A1) ════
    cvt = [r_ for r_ in rows if r_["is_cvt"]]
    ncv = [r_ for r_ in rows if not r_["is_cvt"]]
    # 목표: W'(s) = E_req + ke_cvt (무변속 균형 규약과 동일: KE 보정 후 rho'_KE = 1)
    for r_ in cvt:
        T_i = r_["E_req"] + r_["ke_cvt"]
        r_["surplus"] = r_["W_in"] - r_["E_req"]
        r_["surplus_res"] = r_["W_in"] - T_i
        r_["s_i"] = 1.0 + r_["surplus_res"] / r_["K"]
        r_["s_rho10"] = 1.0 + (r_["W_in"] - r_["E_req"]) / r_["K"]
        r_["s_rho11"] = 1.0 + (r_["W_in"] - 1.1 * r_["E_req"]) / r_["K"]
        r_["c_i30"] = r_["surplus_res"] / r_["Kth30"] if r_["Kth30"] > 1e-9 else np.nan
    for r_ in ncv:
        r_["surplus"] = r_["W_in"] - r_["E_req"]
        r_["surplus_res"] = r_["surplus"] - r_["ke_t3"]     # 무변속: T3 KE가 곧 정직 KE
    Ks = np.array([r_["K"] for r_ in cvt])
    res = np.array([r_["surplus_res"] for r_ in cvt])
    s_star = 1.0 + float(np.sum(Ks * res) / np.sum(Ks ** 2))
    # 임계형 c* (R0=30/33 raw)
    c30 = float(np.sum(np.array([r_["Kth30"] for r_ in cvt]) * res)
                / np.sum(np.array([r_["Kth30"] for r_ in cvt]) ** 2))
    c33 = float(np.sum(np.array([r_["Kth33"] for r_ in cvt]) * res)
                / np.sum(np.array([r_["Kth33"] for r_ in cvt]) ** 2))
    print("\n=== T2. H1 정량화: a_hat 포화항 A1 -> s·A1 ===")
    print(f"{'sub':18s} {'surplus':>7s} {'-keCVT':>7s} {'K(A1일)':>8s} {'s_i':>6s} "
          f"{'s[rho1.0]':>9s} {'s[rho1.1]':>9s}")
    for r_ in cvt:
        print(f"{r_['sub']:18s} {r_['surplus']:7.2f} {r_['surplus_res']:7.2f} "
              f"{r_['K']:8.2f} {r_['s_i']:6.2f} {r_['s_rho10']:9.2f} {r_['s_rho11']:9.2f}")
    print(f"\n전역 s* (LS, 목표 W'=E_req+keCVT) = {s_star:.3f}")
    # s* 물리 해석: raw=35 (clip 35.5) droop
    for rw in (30.0, 33.2, 35.0, 35.5):
        I = C_IQ * rw
        ah0 = float(P.J.ahat(A, np.array([rw]), np.array([1.0]))[0])
        d0 = A[1] * GR * I * I
        print(f"  raw={rw:4.1f} (Iq={I:5.2f}A): a_hat={ah0:6.2f} Nm, Paper droop={d0:5.2f} Nm"
              f" -> s* droop={s_star * d0:5.2f} Nm (추가 {100 * (s_star - 1) * d0 / ah0:+5.1f}% of a_hat)")

    # 교차검증: 같은 s*를 무변속 원장에 적용
    print("\n--- 교차검증: s* 적용 시 무변속 세션 rho 이동 ---")
    xchk = {}
    for ds in CROSS_DS:
        rs = [r_ for r_ in rows if r_["ds"] == ds]
        rho0 = np.array([r_["rho"] for r_ in rs])
        drho = np.array([-(s_star - 1.0) * r_["K"] / r_["E_req"] for r_ in rs])
        rel = drho / rho0
        xchk[ds] = dict(rho0=float(rho0.mean()), rho1=float((rho0 + drho).mean()),
                        shift_pct=float(100 * rel.mean()),
                        K_mean=float(np.mean([r_["K"] for r_ in rs])))
        print(f"{ds:22s} rho {rho0.mean():.3f} -> {(rho0 + drho).mean():.3f} "
              f"(이동 {100 * rel.mean():+.1f}%,  K평균 {xchk[ds]['K_mean']:.2f} J)")
    # 임계형 교차검증
    print("\n--- 임계형 H1b: droop = c·GR·(|Iq|-Iq0)+²·sign, R0=30/33 raw ---")
    thr = {}
    for tag, cc, kk in (("R0=30", c30, "Kth30"), ("R0=33", c33, "Kth33")):
        line = {}
        for ds in CROSS_DS:
            rs = [r_ for r_ in rows if r_["ds"] == ds]
            rho0 = np.array([r_["rho"] for r_ in rs])
            drho = np.array([-cc * r_[kk] / r_["E_req"] for r_ in rs])
            line[ds] = float(100 * (drho / rho0).mean())
        res_after = res - cc * np.array([r_[kk] for r_ in cvt])
        thr[tag] = dict(c=cc, cross_shift_pct=line,
                        cvt_resid_after=[float(x) for x in res_after])
        I355 = C_IQ * 35.5
        dtau = cc * GR * (I355 - C_IQ * float(tag[3:])) ** 2
        print(f"{tag}: c*={cc:.4f}  droop@35.5raw={dtau:.2f} Nm  "
              f"무변속 이동% {['%s:%+.1f' % (k.split('_')[-1], v) for k, v in line.items()]}  "
              f"0429 잔차(보정후) 평균 {np.mean(res_after):+.2f} J")

    # ── 보조: 속도-지수 과대판독 (점성 b·dq 누락 가설, H1의 속도판 변형) ──
    print("\n--- 보조: 속도-지수 과대판독 b·∫dq²dt (Paper a_hat 점성항 부재) ---")
    Kv_c = np.array([r_["Kv"] for r_ in cvt])
    b_star = float(np.sum(Kv_c * res) / np.sum(Kv_c ** 2))
    print(f"b* (LS, 0429 잔차 기준) = {b_star:.4f} Nm·s/rad")
    visc = {"b_star": b_star}
    for ds in CROSS_DS:
        rs = [r_ for r_ in rows if r_["ds"] == ds]
        rho0 = np.array([r_["rho"] for r_ in rs])
        drho = np.array([-b_star * r_["Kv"] / r_["E_req"] for r_ in rs])
        visc[ds] = float(100 * (drho / rho0).mean())
        print(f"  {ds:22s} rho 이동 {visc[ds]:+.1f}%  (Kv평균 {np.mean([r_['Kv'] for r_ in rs]):.0f})")
    print("\n--- 속도-bin 별 knee 일 점유 (|dq2| rad/s bin — >30 은 0429 전용 대역) ---")
    dqshare = {}
    for ds in sorted(set(r_["ds"] for r_ in rows)):
        rs = [r_ for r_ in rows if r_["ds"] == ds]
        tot = sum(r_["W2"] for r_ in rs)
        sh = [sum(r_["bv2"][k] for r_ in rs) / tot for k in range(3)]
        dqshare[ds] = sh
        print(f"  {ds:20s} " + "  ".join(f"{BLBL[k]}:{sh[k]:6.1%}" for k in range(3)))

    # ════ T3: H3 감사 ════
    print("\n=== T3. H3 감사 (0429 규약 독립 재확인) ===")
    print(f"{'sub':18s} {'bz0':>6s} {'bz_npz':>6s} {'d[cm]':>5s} {'h_npz':>5s} {'h_txt':>5s} "
          f"{'keT3':>5s} {'keKnee':>6s} {'keCVT':>6s} {'r_lo':>5s} {'r_med':>5s} {'dbzConv':>7s}")
    for r_ in cvt:
        print(f"{r_['sub']:18s} {r_['bz0']:6.3f} {r_['bz_npz0']:6.3f} "
              f"{100 * abs(r_['bz0'] - r_['bz_npz0']):5.2f} {r_['h_real']:5.2f} "
              f"{r_['h_txt']:5.2f} {r_['ke_t3']:5.1f} {r_['ke_par_knee']:6.2f} "
              f"{r_['ke_cvt']:6.2f} {r_['r_lo']:5.3f} {r_['r_med']:5.3f} "
              f"{100 * r_['dbz_conv']:6.2f}cm")
    ke_gap = [r_["ke_t3"] - r_["ke_cvt"] for r_ in cvt]
    print(f"\nleg-KE 과대(T3 crank-dq) - 정직(CVT 폐쇄): 평균 {np.mean(ke_gap):+.2f} J "
          f"(T3 ke 평균 {np.mean([r_['ke_t3'] for r_ in cvt]):.2f} -> "
          f"정직 {np.mean([r_['ke_cvt'] for r_ in cvt]):.2f} J)")
    print(f"h_real npz-txt 차: 최대 {max(abs(r_['dh_meta']) for r_ in cvt) * 100:.1f} cm | "
          f"bz0 vs npz: 최대 {max(abs(r_['bz0'] - r_['bz_npz0']) for r_ in cvt) * 100:.2f} cm "
          f"(에너지 {M_TOT * G * max(abs(r_['bz0'] - r_['bz_npz0']) for r_ in cvt):.2f} J) | "
          f"crank-as-knee FK 오인 상한: 최대 {max(abs(r_['dbz_conv']) for r_ in cvt) * 100:.2f} cm "
          f"({M_TOT * G * max(abs(r_['dbz_conv']) for r_ in cvt):.2f} J)")

    # ════ 매칭-전류대 비교 (H1 vs H2 킬샷): med|traw2| 30~34 트라이얼 ════
    print("\n=== 매칭-전류대: med|traw2|∈[29.5,34] 트라이얼의 잉여율 비교 ===")
    print(f"{'ds':18s} {'sub':18s} {'med|r2|':>7s} {'surplus_res':>11s} {'res/W_in':>8s}")
    mb = []
    for r_ in rows:
        if 29.5 <= r_["med_raw2"] <= 34.0:
            frac = r_["surplus_res"] / r_["W_in"]
            mb.append(dict(ds=r_["ds"], sub=r_["sub"], med=r_["med_raw2"],
                           res=float(r_["surplus_res"]), frac=float(frac)))
            print(f"{r_['ds']:18s} {r_['sub']:18s} {r_['med_raw2']:7.1f} "
                  f"{r_['surplus_res']:11.2f} {frac:8.1%}")

    # ════ T4: verdict 표 ════
    print("\n=== T4. verdict — 0429 잉여 귀속 (J) ===")
    print(f"{'sub':18s} {'surplus':>7s} {'H3:keCVT':>8s} {'resid':>6s} "
          f"{'H1@s*':>6s} {'left':>6s} {'res/W2':>7s} {'t_cross/t_lo':>12s}")
    verd = []
    for r_ in cvt:
        h1 = (s_star - 1.0) * r_["K"]
        left = r_["surplus_res"] - h1
        fr = r_["surplus_res"] / r_["W2"]
        tc = r_["t_cross"] / r_["t_lo"] if np.isfinite(r_["t_cross"]) else np.nan
        verd.append(dict(sub=r_["sub"], surplus=float(r_["surplus"]),
                         ke_cvt=float(r_["ke_cvt"]), surplus_res=float(r_["surplus_res"]),
                         h1_at_sstar=float(h1), left=float(left),
                         res_over_W2=float(fr), tcross_frac=float(tc)))
        print(f"{r_['sub']:18s} {r_['surplus']:7.2f} {r_['ke_cvt']:8.2f} "
              f"{r_['surplus_res']:6.2f} {h1:6.2f} {left:6.2f} {fr:7.1%} {tc:12.2f}")
    # H2 지표: 잔차 = eta 손실이면 res/W2(무릎 채널 일) 비율의 강도 추세
    fr_arr = np.array([v["res_over_W2"] for v in verd])
    I2 = np.array([r_["med_raw2"] for r_ in cvt])
    W2a = np.array([r_["W2"] for r_ in cvt])
    cor_fr = float(np.corrcoef(fr_arr, W2a)[0, 1])
    print(f"\nH2 체크: res/W2 = {fr_arr.mean():.1%} ± {fr_arr.std():.1%} "
          f"(상수면 고정효율 손실; W2와의 상관 r={cor_fr:+.2f})")
    # per-trial 잔차 vs K 회귀 (H1 순수형이면 기울기=s*-1, 절편~0)
    A_ls = np.vstack([Ks, np.ones_like(Ks)]).T
    coef, res_ls, *_ = np.linalg.lstsq(A_ls, res, rcond=None)
    pred = A_ls @ coef
    ss = 1 - np.sum((res - pred) ** 2) / np.sum((res - res.mean()) ** 2)
    print(f"잔차 vs K 회귀: slope={coef[0]:.3f} (s*-1={s_star - 1:.3f}), "
          f"intercept={coef[1]:+.2f} J, R²={ss:.3f}")
    # 무변속 잔차 재확인 (기준선)
    for ds in CROSS_DS:
        rs = [r_ for r_ in rows if r_["ds"] == ds]
        print(f"무변속 기준선 {ds:22s}: surplus_res 평균 "
              f"{np.mean([r_['surplus_res'] for r_ in rs]):+.2f} J "
              f"(res/W_in {np.mean([r_['surplus_res'] / r_['W_in'] for r_ in rs]):+.1%})")

    # 정합성 체크 (T3 결과와의 차)
    mx = max(max(abs(r_["chk"]["dW_in"]), abs(r_["chk"]["dE_req"])) for r_ in rows)
    print(f"\nT3 결과 대비 재계산 최대 편차 (W_in/E_req): {mx:.2e} J (규약 재현 검증)")

    out = dict(
        rows=[{k: v for k, v in r_.items() if k != "cum"} for r_ in rows],
        cum_0429={r_["sub"]: r_["cum"] for r_ in rows if r_["is_cvt"]},
        bin_shares=binsum,
        s_star=s_star, s_per_trial={r_["sub"]: r_["s_i"] for r_ in cvt},
        cross_check=xchk, threshold_variant=thr,
        viscous_variant=visc, dq_bin_shares=dqshare,
        ke_correction=dict(ke_t3_mean=float(np.mean([r_["ke_t3"] for r_ in cvt])),
                           ke_cvt_mean=float(np.mean([r_["ke_cvt"] for r_ in cvt])),
                           ke_par_knee_mean=float(np.mean([r_["ke_par_knee"] for r_ in cvt]))),
        verdict=verd,
        regression=dict(slope=float(coef[0]), intercept=float(coef[1]), r2=float(ss)),
        matched_band=mb,
        note="unwrap 재감사 안 함 — REJECTED.md #27 인용. held-out 0324 제외.")
    fp = HERE / "p22_probe_0429_energy_result.json"
    safe.atomic_json_write(fp, out)
    print(f"\nsaved -> {fp}")


if __name__ == "__main__":
    main()
