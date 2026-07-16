# -*- coding: utf-8 -*-
"""p23_law_calib — P23 Phase 2: 유지-지지 법칙 λ(τ_load, v)의 측정 직접 캘리브레이션.

목적 (MARATHON_p23.md Phase 2): 점수 적합이 아니라 **창별 λ* 실측**으로 pre30을 대체할
법칙을 세운다. λ*(window) = 그 창에서 트윈이 실측 운동을 재현하는 데 필요한 무릎(크랭크)
보조토크 (p20_exp4.win_scan 정본 기계 재사용).

데이터 (전 세션 유지/저속 + 속도축):
  - 0604 페이로드 s2s: cvt 0/2.5/5kg + no_cvt 0kg (부하축; no_cvt 로드는 xlsx 미수출)
  - s2s_gnd_0319 (지상 3 trial) + s2s_0324 (5 trial — ★추출 중 공중(매달림)으로 재분류:
    knee â rms 0.25Nm = s2s_air(0.2)와 동일 서명, 지상 0319는 3.4~3.7Nm; GOAL18 canonical
    렌더 kind='air'와도 일치 → 제2 무부하 앵커 + CV 홀드아웃)
  - 점프 유지+푸시 창: 0421(fix0421 적용된 P12와 무관 — CL 경로 d는 xlsx 청정)/0424/0602
    + 0429 (크랭크 채널, closure/O1O2 = exp3 규약)
  - s2s_air 0319 (신규 무부하 앵커): 용접 베이스 win_scan_air (p23_runners.build_flip_welded)
    + 준정적 직접법(중력항 유한차분, 부호는 유지-드리프트 시험으로 검증)

프로토콜 고정:
  - 플랜트 = P19 정본 후보 (fourbar_p19_candidate — P20 λ* 실증법칙들과 동일 기준)
  - λ 그리드 [-2, 6] step 0.5 + 포물선 보간, 민감도 <2% 창 제외 (win_scan 내장)
  - 오프셋: 점프 = P12.OFFKEY 후보 오프셋 / 0429 = (3.14°, -3.0°) / s2s·0604·air = 0
  - W = 0.2s (점프는 stance 짧으면 0.12s 폴백, 행에 기록)
  - jump_0324(held-out 점프)는 완전 미사용 (철칙 9)

적합: M0 λ=c / M1 λ=b|τ| / M2 λ=(a+b|τ|)·g(v;v0), g=1/(1+(v/v0)²) / M3 = M2+세션 오프셋.
CV: fit {0604, s2s_gnd_0319, 점프 4세션} → predict {s2s_0324, s2s_air}.

산출물 (전부 이 폴더, p23_law_*): p23_law_rows.json, p23_law_fit.json, p23_law_fit.png.
원본 데이터 읽기 전용. 실행: python p23_law_calib.py [--refit(추출 생략, rows 재사용)]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

import p20_exp4 as X4            # win_scan (정본 기계) — import 시 AD.ensure_init(winit)
import p20_exp1 as E             # X32/V/SP/A/P12/DD (P19 플랜트)
import p19_judge as P
import p19_run as R
import p20_run as P20M
import p22_fix0421 as FX
import p23_loaders as L
import p21_cma as C
import p23_runners as RN
from cvt_run2 import takeoff_time

mj = X4.mj
A = E.A
LGRID = np.arange(-2.0, 6.01, 0.5)
WIN = 0.2
O1_429, O2_429 = 3.14 * np.pi / 180, -3.0 * np.pi / 180    # exp3/P18b 0429 프로토콜
ROWS_PATH = HERE / "p23_law_rows.json"
FIT_PATH = HERE / "p23_law_fit.json"
FIG_PATH = HERE / "p23_law_fit.png"
BINS = [(0.0, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 8.0)]
BIN_LAB = ["|dq2|<0.3", "0.3-1", "1-3", "3-8"]
SESS_OF = {"jump_position_0421": "0421", "jump_0424": "0424", "jump_0602": "0602",
           "jump_0429": "0429", "s2s_gnd_0319": "s2s0319"}
FITSESS = ["0604", "s2s0319", "0421", "0424", "0602", "0429"]   # M3 δ 기준 = 0604
CAP = {"s2s0319": 90, "s2s0324": 90, "0604": 110, "air": 15}


def wstats(d, t0, W):
    """창 [t0, t0+W] 평균 부하/속도/자세 (실좌표, a_hat 무시프트 — 부하 측정용)."""
    t = d["t"]
    wm = (t >= t0) & (t <= t0 + W)
    a2 = P.J.ahat(A, d["traw2"], d["dq2"])
    return dict(tk=float(np.mean(np.abs(a2[wm]))),
                tk_sgn=float(np.mean(a2[wm])),
                v=float(np.mean(np.abs(d["dq2"][wm]))),
                q2deg=float(np.degrees(np.mean(d["q2"][wm]))))


def subsample(starts, cap):
    starts = np.asarray(starts, float)
    if len(starts) > cap:
        starts = starts[np.linspace(0, len(starts) - 1, cap).astype(int)]
    return starts


def pack(rw, sess, ds, sub, load, W):
    st = dict(sess=sess, ds=ds, sub=str(sub), load=float(load), W=float(W),
              t0=rw["t0"], lam=rw["lam"], dq0=rw["dq"],
              edge=bool(rw["lam"] <= LGRID[0] + 1e-9 or rw["lam"] >= LGRID[-1] - 1e-9))
    return st


# ══════════════ 1) 추출 — 접촉 세션 (win_scan 재사용) ══════════════
def extract_jumps(rows):
    """0421/0424/0602 (flip) + 0429 (cvt) — R.TRIALS(CL 경로, xlsx 청정) d 직접 소비."""
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
    model_c = None
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        if ds == "jump_0324":
            continue                              # held-out 점프 — 완전 미사용 (철칙 9)
        t = d["t"]
        toff = float(t[m][-1]) - 0.1              # 마스크 끝 = toff+0.1 (all_trials 규약)
        W = WIN
        starts = np.arange(0.02, toff - 0.14, 0.03)
        if len(starts) < 3:                       # stance 짧으면 exp3 폴백
            W = 0.12
            starts = np.arange(0.02, max(toff - 0.06, 0.03), 0.03)
        if is_cvt:
            if model_c is None:
                model_c, _ = P.build_cvt(E.X32, E.V[1], E.SP, l_i)
            got = X4.win_scan(model_c, d, d["l_i"], starts, W,
                              o1=O1_429, o2=O2_429, lam_grid=LGRID)
        else:
            k1, k2 = E.P12.OFFKEY.get(ds, (None, None))
            o1 = E.DD.get(k1, 0.0) if k1 else 0.0
            o2 = E.DD.get(k2, 0.0) if k2 else 0.0
            got = X4.win_scan(model_f, d, 0.030, starts, W,
                              o1=o1, o2=o2, lam_grid=LGRID)
        for rw in got:
            rows.append({**pack(rw, SESS_OF[ds], ds, sub, 0.0, W), **wstats(d, rw["t0"], W)})
        print(f"[jump] {ds}/{sub}: {len(got)} windows (toff~{toff:.2f}, W={W})", flush=True)


def extract_s2s_gnd(rows):
    """s2s_gnd_0319 — exp4 검사A 변환 그대로 (P12 trials → d, o=0)."""
    model_f, _ = P.build_flip(E.X32, E.V[1], E.SP)
    for tr in E.P12._G["trials"]:
        if tr["ds"] != "s2s_gnd_0319":
            continue
        pp = tr["pp"]
        t = pp["t"]
        d = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                 dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                 traw1=tr["raw1"], traw2=tr["raw2"])
        starts = subsample(np.arange(0.4, t[-1] - 0.4, 0.45), CAP["s2s0319"])
        got = X4.win_scan(model_f, d, 0.030, starts, WIN, lam_grid=LGRID)
        for rw in got:
            rows.append({**pack(rw, "s2s0319", tr["ds"], tr["sub"], 0.0, WIN),
                         **wstats(d, rw["t0"], WIN)})
        print(f"[s2s0319] {tr['sub']}: {len(got)} windows", flush=True)


def extract_s2s_0324(rows, model_w):
    """s2s_0324 5 trial — ★공중(매달림) 판정: knee â rms 0.25Nm = s2s_air(0.2)와 동일 서명
    (지상 s2s_gnd_0319는 3.4~3.7Nm), GOAL18 canonical 렌더도 kind='air'.
    → 용접 베이스 win_scan_air로 추출 = 제2의 무부하 앵커 (다른 날, held-out DAY)."""
    for sub in L.SUBS_S2S_0324:
        d, meta = L.load_s2s_0324(sub)
        starts = subsample(np.arange(0.4, d["t"][-1] - 0.4, 0.45), CAP["s2s0324"])
        got = win_scan_air(model_w, d, starts, WIN, LGRID)
        for rw in got:
            rows.append({**pack(rw, "s2s0324", "s2s_0324_air", sub, 0.0, WIN),
                         **wstats(d, rw["t0"], WIN)})
        print(f"[s2s0324-air] {sub}: {len(got)} windows", flush=True)


def extract_0604(rows):
    """0604 페이로드 — exp4 검사B 그대로 (payload = base 질량, P18c 규약)."""
    for grp, sub, load in [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5),
                           ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0.0)]:
        d = X4.S0.load_0604(grp, sub)
        li = d["l_i"]
        model, _ = (P.build_cvt(E.X32, E.V[1], E.SP, li) if grp == "cvt"
                    else P.build_flip(E.X32, E.V[1], E.SP))
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load
        starts = subsample(np.arange(0.3, d["t"][-1] - 0.3, 0.35), CAP["0604"])
        got = X4.win_scan(model, d, li, starts, WIN, lam_grid=LGRID)
        for rw in got:
            r_ = {**pack(rw, "0604", f"0604_{grp}", sub, load, WIN),
                  **wstats(d, rw["t0"], WIN)}
            r_["branch"] = grp
            rows.append(r_)
        print(f"[0604] {grp}/{sub} (load {load}kg): {len(got)} windows", flush=True)


# ══════════════ 2) 추출 — 공중 (용접 베이스) ══════════════
def lam_star(lg, scores):
    i = int(np.argmin(scores))
    if i in (0, len(lg) - 1):
        return float(lg[i])
    a, b, c = scores[i - 1], scores[i], scores[i + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return float(lg[i] + np.clip(off, -1, 1) * (lg[1] - lg[0]))


def win_scan_air(model, d, starts, W, lam_grid):
    """win_scan의 용접-베이스 판 (bz 없음, FK 불필요; 그 외 동일 프로토콜/점수)."""
    MS = X4.MS
    t = d["t"]
    th = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tk0 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    q1mj = -d["q1"] - np.pi / 2
    qcmj = -d["q2"]
    md = mj.MjData(model)
    iq = {n: safe.qadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    dof = {n: safe.dofadr(model, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}
    dt = model.opt.timestep
    out = []
    for t0 in starts:
        i0 = int(np.searchsorted(t, t0))
        if i0 >= len(t) - 5:
            continue
        t1 = min(t0 + W, t[-1])
        nst = int(round((t1 - t0) / dt))
        if nst < 10:
            continue
        dqc = -d["dq2"][i0]
        dqh = -d["dq1"][i0]
        scores = []
        for lam in lam_grid:
            md.qpos[:] = 0
            md.qpos[iq["hip"]] = q1mj[i0]; md.qpos[iq["knee_motor"]] = qcmj[i0]
            md.qpos[iq["cpin"]] = -qcmj[i0]; md.qpos[iq["knee"]] = qcmj[i0]
            md.qvel[:] = 0
            md.qvel[dof["hip"]] = dqh; md.qvel[dof["knee_motor"]] = dqc
            md.qvel[dof["cpin"]] = -dqc; md.qvel[dof["knee"]] = dqc
            mj.mj_forward(model, md)
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                md.ctrl[:] = [-float(np.interp(tc, t, th)),
                              -(float(np.interp(tc, t, tk0)) + lam)]
                try:
                    mj.mj_step(model, md)
                except Exception:
                    ok = False; break
                if not np.isfinite(md.qpos).all():
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = md.qpos[iq["hip"]]; q2a[k] = md.qpos[iq["knee_motor"]]
                dq1a[k] = md.qvel[dof["hip"]]; dq2a[k] = md.qvel[dof["knee_motor"]]
            if not ok:
                scores.append(MS.W_Q * 2 + MS.W_DQ * 20)
                continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                scores.append(np.nan)
                continue
            r = lambda sim, real: float(np.sqrt(np.mean(
                (np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            scores.append(MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
                          + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
        scores = np.array(scores, float)
        if np.isnan(scores).any() or (scores.max() - scores.min()) / max(scores.min(), 1e-9) < 0.02:
            continue
        out.append(dict(t0=float(t0), dq=float(d["dq2"][i0]), lam=lam_star(lam_grid, scores)))
    return out


def extract_air(rows, model_w):
    cycles, meta = L.load_s2s_air()
    for i, d in enumerate(cycles):
        starts = subsample(np.arange(0.2, d["t"][-1] - 0.25, 0.3), CAP["air"])
        got = win_scan_air(model_w, d, starts, WIN, LGRID)
        for rw in got:
            rows.append({**pack(rw, "s2s_air", "s2s_air_0319", f"cyc{i + 1:02d}", 0.0, WIN),
                         **wstats(d, rw["t0"], WIN)})
        print(f"[air] cyc{i + 1:02d}: {len(got)} windows", flush=True)
    return cycles


def air_cycle_lam_scan(model_w, cycles):
    """배포 관점 검증: 0319 공중 14사이클 **통짜** 재생(air_replay_cycle, v6 AIR 공식)에
    상수 λ를 가산 스캔 — 창별 λ*(−1.4대)가 통짜 지표로도 최적인지 확인."""
    vz = np.zeros(20)
    vz[16] = 6.0                                  # lam_vec(c_qs=0, v0) → λ_vec = 0
    grid = [0.0, -0.5, -0.7, -1.0, -1.2, -1.4, -1.7, -2.0]
    out = {}
    for lam in grid:
        scs = []
        for d in cycles:
            res = RN.air_replay_cycle(model_w, d, vz, pre30=lam)
            scs.append(RN.CRASH_RQ + RN.AIR_W_DQ * RN.CRASH_RDQ if res is None
                       else res[0] + RN.AIR_W_DQ * res[1])
        out[str(lam)] = float(np.mean(scs))
        print(f"[air-replay] λ={lam:+.1f} → AIR={out[str(lam)]:.3f}", flush=True)
    return out


# ── 공중 준정적 직접법: λ_dir = τ_req(모델 정역학) − â₂ (유지 샘플) ──
def air_direct(model_w, cycles):
    """U(포텐셜: 중력+스프링) 유한차분 → 유지에 필요한 크랭크/힙 토크.
    부호는 유지-드리프트 시험(0.4s, 양부호 비교)으로 결정 — 결과에 명기.
    주의: 폐루프 connect 등식 구속(SEA_TC)의 연성 에너지는 U에 미포함 (한계 명기)."""
    model_w.opt.enableflags |= mj.mjtEnableBit.mjENBL_ENERGY
    md = mj.MjData(model_w)
    iq = {n: safe.qadr(model_w, n, mj) for n in ("hip", "knee_motor", "cpin", "knee")}

    def U(q1mj, qcmj):
        md.qpos[:] = 0
        md.qpos[iq["hip"]] = q1mj; md.qpos[iq["knee_motor"]] = qcmj
        md.qpos[iq["cpin"]] = -qcmj; md.qpos[iq["knee"]] = qcmj
        md.qvel[:] = 0
        mj.mj_forward(model_w, md)
        return float(md.energy[0])

    dl = 1e-3

    def req(q1mj, qcmj, sgn):
        dU_dc = (U(q1mj, qcmj + dl) - U(q1mj, qcmj - dl)) / (2 * dl)
        dU_dh = (U(q1mj + dl, qcmj) - U(q1mj - dl, qcmj)) / (2 * dl)
        # mj 인가토크 τ=∂U/∂q (정역학), ctrl=[-s1,-(s2)] → s_req = -sgn·∂U/∂q (sgn 시험 결정)
        return -sgn * dU_dh, -sgn * dU_dc     # (s1_req, s2_req) 실좌표 Nm

    def drift(q1mj, qcmj, s1, s2):
        md.qpos[:] = 0
        md.qpos[iq["hip"]] = q1mj; md.qpos[iq["knee_motor"]] = qcmj
        md.qpos[iq["cpin"]] = -qcmj; md.qpos[iq["knee"]] = qcmj
        md.qvel[:] = 0
        mj.mj_forward(model_w, md)
        for _ in range(int(0.4 / model_w.opt.timestep)):
            md.ctrl[:] = [-s1, -s2]
            mj.mj_step(model_w, md)
        return abs(md.qpos[iq["knee_motor"]] - qcmj) + abs(md.qpos[iq["hip"]] - q1mj)

    # 부호 결정 (첫 유지 샘플)
    d0 = cycles[0]
    hold0 = np.where((np.abs(d0["dq1"]) < 0.15) & (np.abs(d0["dq2"]) < 0.15))[0]
    i0 = int(hold0[len(hold0) // 2])
    qh0, qc0 = -d0["q1"][i0] - np.pi / 2, -d0["q2"][i0]
    dr = {}
    for sgn in (+1, -1):
        s1r, s2r = req(qh0, qc0, sgn)
        dr[sgn] = drift(qh0, qc0, s1r, s2r)
    sgn = +1 if dr[+1] <= dr[-1] else -1
    print(f"[air-direct] 부호 시험: drift(+1)={dr[+1]:.4f} rad, drift(-1)={dr[-1]:.4f} → sgn={sgn:+d}",
          flush=True)

    out = []
    for ci, d in enumerate(cycles):
        t = d["t"]
        a1 = P.J.ahat(A, d["traw1"], d["dq1"])
        a2 = P.J.ahat(A, d["traw2"], d["dq2"])
        hold = (np.abs(d["dq1"]) < 0.15) & (np.abs(d["dq2"]) < 0.15)
        idxs = np.where(hold)[0]
        if len(idxs) < 5:
            continue
        step = max(1, int(0.5 / np.median(np.diff(t))))
        for i in idxs[::step]:
            s1r, s2r = req(-d["q1"][i] - np.pi / 2, -d["q2"][i], sgn)
            wm = (t >= t[i] - 0.1) & (t <= t[i] + 0.1)
            out.append(dict(cyc=ci + 1, t0=float(t[i]),
                            tau_grav_knee=float(s2r), tau_grav_hip=float(s1r),
                            ahat_knee=float(np.mean(a2[wm])), ahat_hip=float(np.mean(a1[wm])),
                            lam_dir=float(s2r - np.mean(a2[wm])),
                            lam_dir_hip=float(s1r - np.mean(a1[wm]))))
    return dict(sign=sgn, drift_test={str(k): float(v) for k, v in dr.items()}, rows=out)


# ══════════════ 3) 적합/통계 ══════════════
def g_of(v, v0):
    return 1.0 / (1.0 + (np.asarray(v) / v0) ** 2)


def _ci(res, n):
    """least_squares 결과 → 95% CI (선형화 공분산)."""
    p = len(res.x)
    dof_ = max(n - p, 1)
    s2 = 2 * res.cost / dof_
    JTJ = res.jac.T @ res.jac
    try:
        cov = s2 * np.linalg.inv(JTJ)
        se = np.sqrt(np.maximum(np.diag(cov), 0))
    except np.linalg.LinAlgError:
        se = np.full(p, np.nan)
    return 1.96 * se


def _aic_bic(rss, n, k):
    return (n * np.log(max(rss / n, 1e-12)) + 2 * k,
            n * np.log(max(rss / n, 1e-12)) + k * np.log(n))


def fit_models(F):
    from scipy.optimize import least_squares
    from scipy import stats as st
    lam = np.array([r["lam"] for r in F])
    tk = np.array([r["tk"] for r in F])
    v = np.array([r["v"] for r in F])
    sid = np.array([FITSESS.index(r["sess"]) for r in F])   # 0 = 0604 (δ 기준)
    n = len(F)
    out = {}

    # M0: 상수
    c0 = float(lam.mean())
    rss0 = float(np.sum((lam - c0) ** 2))
    out["M0"] = dict(params=dict(c=c0), ci=dict(c=float(1.96 * lam.std(ddof=1) / np.sqrt(n))),
                     rss=rss0, k=1)
    # M1: 순비례
    b1 = float(np.sum(lam * tk) / np.sum(tk ** 2))
    rss1 = float(np.sum((lam - b1 * tk) ** 2))
    se_b1 = float(np.sqrt((rss1 / (n - 1)) / np.sum(tk ** 2)))
    out["M1"] = dict(params=dict(b=b1), ci=dict(b=1.96 * se_b1), rss=rss1, k=1)

    # M2: (a + b·τ)·g(v; v0)  (게이트 식별 시험 — v0가 상한이면 게이트 미식별)
    def res2(p):
        a, b, v0 = p
        return (a + b * tk) * g_of(v, v0) - lam

    best2 = None
    for v0g in (1.0, 2.0, 4.0, 6.0, 10.0):
        r_ = least_squares(res2, [0.5, 0.15, v0g],
                           bounds=([-3, -0.5, 0.2], [4, 1.5, 60]))
        if best2 is None or r_.cost < best2.cost:
            best2 = r_
    ci2 = _ci(best2, n)
    rss2 = float(2 * best2.cost)
    out["M2"] = dict(params=dict(a=float(best2.x[0]), b=float(best2.x[1]), v0=float(best2.x[2])),
                     ci=dict(a=float(ci2[0]), b=float(ci2[1]), v0=float(ci2[2])),
                     rss=rss2, k=3, v0_at_bound=bool(best2.x[2] > 59.0))

    # M2a: λ = a + b·τ (무게이트 선형 — M2의 v0→∞ 퇴화형)
    X = np.column_stack([np.ones(n), tk])
    coef, rssv, *_ = np.linalg.lstsq(X, lam, rcond=None)
    rss2a = float(np.sum((X @ coef - lam) ** 2))
    covd = rss2a / (n - 2) * np.linalg.inv(X.T @ X)
    out["M2a"] = dict(params=dict(a=float(coef[0]), b=float(coef[1])),
                      ci=dict(a=float(1.96 * np.sqrt(covd[0, 0])),
                              b=float(1.96 * np.sqrt(covd[1, 1]))), rss=rss2a, k=2)

    # M4: λ = a + b·τ + c·τ² (초선형 시험)
    X4_ = np.column_stack([np.ones(n), tk, tk ** 2])
    coef4, *_ = np.linalg.lstsq(X4_, lam, rcond=None)
    rss4 = float(np.sum((X4_ @ coef4 - lam) ** 2))
    covd4 = rss4 / (n - 3) * np.linalg.inv(X4_.T @ X4_)
    out["M4"] = dict(params=dict(a=float(coef4[0]), b=float(coef4[1]), c=float(coef4[2])),
                     ci={k_: float(1.96 * np.sqrt(covd4[i, i]))
                         for i, k_ in enumerate(("a", "b", "c"))}, rss=rss4, k=3)

    # M3: M2a + 세션 오프셋 (a_s = a + δ_s, δ_0604 = 0; 게이트는 미식별이라 제외)
    nd = len(FITSESS) - 1
    D = np.zeros((n, nd))
    for j in range(nd):
        D[:, j] = (sid == j + 1).astype(float)
    X3 = np.column_stack([np.ones(n), tk, D])
    coef3, *_ = np.linalg.lstsq(X3, lam, rcond=None)
    rss3 = float(np.sum((X3 @ coef3 - lam) ** 2))
    covd3 = rss3 / (n - X3.shape[1]) * np.linalg.inv(X3.T @ X3)
    pd3 = dict(a=float(coef3[0]), b=float(coef3[1]))
    cd3 = dict(a=float(1.96 * np.sqrt(covd3[0, 0])), b=float(1.96 * np.sqrt(covd3[1, 1])))
    for j, s in enumerate(FITSESS[1:]):
        pd3[f"d_{s}"] = float(coef3[2 + j])
        cd3[f"d_{s}"] = float(1.96 * np.sqrt(covd3[2 + j, 2 + j]))
    out["M3"] = dict(params=pd3, ci=cd3, rss=rss3, k=2 + nd)

    for m in ("M0", "M1", "M2", "M2a", "M3", "M4"):
        d_ = out[m]
        d_["rmse"] = float(np.sqrt(d_["rss"] / n))
        aic, bic = _aic_bic(d_["rss"], n, d_["k"])
        d_["aic"], d_["bic"] = float(aic), float(bic)
    # F-검정 (M3 vs M2a — 부하 반영 후 세션차 잔존?)
    df1, df2 = out["M3"]["k"] - out["M2a"]["k"], n - out["M3"]["k"]
    Fst = ((rss2a - rss3) / df1) / (rss3 / df2)
    out["F_M3_vs_M2a"] = dict(F=float(Fst), df=(int(df1), int(df2)),
                              p=float(st.f.sf(Fst, df1, df2)))
    out["n_fit"] = int(n)
    return out


def fit_final(rows_all):
    """최종 법칙 (배포용): 전 세션(공중 앵커 포함), 세션 균형 가중 (w=1/n_sess).
    형태 = M2a(선형) + M4(2차) — 게이트는 직접 측정에서 미식별이라 제외."""
    lam = np.array([r["lam"] for r in rows_all])
    tk = np.array([r["tk"] for r in rows_all])
    sess = [r["sess"] for r in rows_all]
    cnt = {s: sess.count(s) for s in set(sess)}
    w = np.array([1.0 / cnt[s] for s in sess])
    w = w / w.sum() * len(w)
    sw = np.sqrt(w)
    n = len(lam)
    out = {"n": int(n), "n_sess": {s: int(c) for s, c in cnt.items()}}
    for tag, cols in (("linear", [np.ones(n), tk]),
                      ("quad", [np.ones(n), tk, tk ** 2])):
        X = np.column_stack(cols)
        Xw = X * sw[:, None]
        yw = lam * sw
        coef, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        res = X @ coef - lam
        rss_w = float(np.sum(w * res ** 2))
        cov = rss_w / (n - X.shape[1]) * np.linalg.inv(Xw.T @ Xw)
        names = ("a", "b", "c")[:X.shape[1]]
        out[tag] = dict(params={k: float(c) for k, c in zip(names, coef)},
                        ci={k: float(1.96 * np.sqrt(cov[i, i])) for i, k in enumerate(names)},
                        rmse_w=float(np.sqrt(rss_w / n)),
                        rmse_by_sess={s: float(np.sqrt(np.mean(
                            [r_ ** 2 for r_, ss in zip(res, sess) if ss == s])))
                            for s in cnt})
    return out


def fit_hold_gate(data):
    """정련 적합 (물리 형태): 유지 법칙 + 게이트 공동 적합.

    ① HOLD LAW (준정적, v<1.5, 공중 앵커 포함): λ_hold(τ̂) = a + b·τ̂ [+ c·τ̂²]
       — 그룹 균형 가중 (그룹 = 세션, 단 0604은 부하 렁별).
    ② GATE (전 속도, 전 창): λ = a + (b·τ̂ + c·τ̂²)·g(v; v0) 공동 NLS —
       푸시 창(τ̂ 9~16, v 3~10)이 유지 법칙 외삽보다 얼마나 낮은지가 v0을 식별.
       ※ 절편 a(트윈 공중 편향)는 게이트 비적용 (공중 전 속도에서 λ 평탄 실측).
    반환 dict(hold_lin, hold_quad, gate, gate_bins)."""
    from scipy.optimize import least_squares

    def grp_of(r):
        return f"0604_{r['sub']}" if r["sess"] == "0604" else r["sess"]

    def weights(rs):
        cnt = {}
        for r in rs:
            cnt[grp_of(r)] = cnt.get(grp_of(r), 0) + 1
        w = np.array([1.0 / cnt[grp_of(r)] for r in rs])
        return w / w.sum() * len(w)

    out = {}
    # ── ① 유지 법칙 ──
    hold = [r for r in data if r["v"] < 1.5
            and (r["sess"] in FITSESS or r["sess"] in ("s2s0324", "s2s_air"))]
    lam = np.array([r["lam"] for r in hold])
    tk = np.array([r["tk"] for r in hold])
    w = weights(hold)
    sw = np.sqrt(w)
    for tag, cols in (("hold_lin", [np.ones(len(hold)), tk]),
                      ("hold_quad", [np.ones(len(hold)), tk, tk ** 2])):
        X = np.column_stack(cols)
        coef, *_ = np.linalg.lstsq(X * sw[:, None], lam * sw, rcond=None)
        res = X @ coef - lam
        rss_w = float(np.sum(w * res ** 2))
        cov = rss_w / (len(hold) - X.shape[1]) * np.linalg.inv((X * sw[:, None]).T @ (X * sw[:, None]))
        names = ("a", "b", "c")[:X.shape[1]]
        out[tag] = dict(params={k: float(c) for k, c in zip(names, coef)},
                        ci={k: float(1.96 * np.sqrt(cov[i, i])) for i, k in enumerate(names)},
                        rmse_w=float(np.sqrt(rss_w / len(hold))), n=len(hold))
    # 세션별 유지 잔차 (오프셋 평결용)
    hq = out["hold_quad"]["params"]
    resid = {}
    for s in sorted(set(grp_of(r) for r in hold)):
        rs = [r for r in hold if grp_of(r) == s]
        rr = [r["lam"] - (hq["a"] + hq["b"] * r["tk"] + hq.get("c", 0) * r["tk"] ** 2)
              for r in rs]
        resid[s] = dict(mean=float(np.mean(rr)),
                        sem=float(np.std(rr) / np.sqrt(len(rr))), n=len(rr))
    out["hold_resid_by_sess"] = resid

    # ── ② 게이트 공동 적합 (전 창, v 상한 없음) ──
    allw = [r for r in data if r["sess"] in FITSESS or r["sess"] in ("s2s0324", "s2s_air")]
    lam_a = np.array([r["lam"] for r in allw])
    tk_a = np.array([r["tk"] for r in allw])
    v_a = np.array([r["v"] for r in allw])
    w_a = weights(allw)
    sw_a = np.sqrt(w_a)

    def res_g(p):
        a, b, c, v0 = p
        return sw_a * ((a + (b * tk_a + c * tk_a ** 2) * g_of(v_a, v0)) - lam_a)

    best = None
    for v0g in (2.0, 4.0, 6.0, 10.0, 20.0):
        r_ = least_squares(res_g, [hq["a"], hq["b"], hq.get("c", 0.0), v0g],
                           bounds=([-3, 0.0, -0.05, 0.5], [1, 2.0, 0.15, 60]))
        if best is None or r_.cost < best.cost:
            best = r_
    ci = _ci(best, len(allw))
    out["gate"] = dict(params=dict(a=float(best.x[0]), b=float(best.x[1]),
                                   c=float(best.x[2]), v0=float(best.x[3])),
                       ci={k: float(ci[i]) for i, k in enumerate(("a", "b", "c", "v0"))},
                       rmse_w=float(np.sqrt(2 * best.cost / len(allw))), n=len(allw),
                       v0_at_bound=bool(best.x[3] > 59.0))
    # ĝ 빈 추적 (유지 법칙 기준 정규화, 지지항 S>1Nm 창만)
    gp = out["gate"]["params"]
    bins2 = BINS + [(8.0, 20.0)]
    labs2 = BIN_LAB + ["8+"]
    gate_bins = []
    for j, (lo, hi) in enumerate(bins2):
        rs = [r for r in allw
              if lo <= r["v"] < hi
              and (hq["b"] * r["tk"] + hq.get("c", 0) * r["tk"] ** 2) > 1.0]
        if len(rs) < 3:
            continue
        gh = [(r["lam"] - hq["a"]) / (hq["b"] * r["tk"] + hq.get("c", 0) * r["tk"] ** 2)
              for r in rs]
        gate_bins.append(dict(lab=labs2[j], v=float(np.mean([r["v"] for r in rs])),
                              g=float(np.mean(gh)),
                              sem=float(np.std(gh) / np.sqrt(len(gh))), n=len(rs)))
    out["gate_bins"] = gate_bins
    return out


def predict(model, params, rows):
    tk = np.array([r["tk"] for r in rows])
    v = np.array([r["v"] for r in rows])
    if model == "M0":
        return np.full(len(rows), params["c"])
    if model == "M1":
        return params["b"] * tk
    if model == "M2":
        return (params["a"] + params["b"] * tk) * g_of(v, params["v0"])
    if model == "M4":
        return params["a"] + params["b"] * tk + params["c"] * tk ** 2
    return params["a"] + params["b"] * tk          # M2a / M3(δ=0)


def bin_of(vv):
    for j, (lo, hi) in enumerate(BINS):
        if lo <= vv < hi:
            return j
    return len(BINS)          # >8


# ══════════════ 4) 보고/그림 ══════════════
def report(rows, direct, airscan):
    data = [r for r in rows if not r["edge"]]
    n_edge = len(rows) - len(data)
    F = [r for r in data if r["sess"] in FITSESS and r["v"] <= 8.0]
    n_hi = len([r for r in data if r["sess"] in FITSESS and r["v"] > 8.0])
    HO = {"s2s0324": [r for r in data if r["sess"] == "s2s0324"],
          "s2s_air": [r for r in data if r["sess"] == "s2s_air"]}
    fits = fit_models(F)

    print("\n" + "=" * 100)
    print(f"P23 Phase 2 — λ(τ_load, v) 직접 캘리브레이션  (창 {len(rows)}, edge 제외 {n_edge}, "
          f"fit {len(F)} (+v>8 제외 {n_hi}), holdout 0324-air {len(HO['s2s0324'])} / "
          f"air {len(HO['s2s_air'])})")
    print("=" * 100)

    # 세션별 저속 기준선 (P20 참조 대조)
    print("\n[세션별 저속 λ* 기준선]  (v = 창평균 |dq2|; s2s0324는 공중 재분류)")
    print(f"{'세션':10s} {'n(<0.3)':>8} {'λ*(v<0.3)':>12} {'n(<1)':>6} {'λ*(v<1)':>12} "
          f"{'⟨|τ̂|⟩(v<1)':>12}  P20참조")
    ref = {"0421": "+2.22(fix후)", "0424": "+1.45", "0602": "+2.56",
           "s2s0319": "+1.0", "0429": "+1.0", "0604": "+1.0/2.1/3.8(0/2.5/5kg)",
           "s2s0324": "무부하앵커#2 (재분류)", "s2s_air": "≈0 기대(0c)"}
    for s in FITSESS + ["s2s0324", "s2s_air"]:
        rs = [r for r in data if r["sess"] == s]
        l03 = [r["lam"] for r in rs if r["v"] < 0.3]
        l1 = [r["lam"] for r in rs if r["v"] < 1.0]
        t1 = [r["tk"] for r in rs if r["v"] < 1.0]
        f_ = lambda a: f"{np.mean(a):+.2f}±{np.std(a):.2f}" if a else "   -    "
        print(f"{s:10s} {len(l03):8d} {f_(l03):>12} {len(l1):6d} {f_(l1):>12} "
              f"{np.mean(t1) if t1 else float('nan'):12.2f}  {ref.get(s, '')}")

    # 0604 부하축 (같은 세션)
    print("\n[0604 부하축 (v<1)]")
    for br, sub, load in [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5),
                          ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0.0)]:
        rs = [r for r in data if r["sess"] == "0604" and r["sub"] == sub
              and r.get("branch") == br and r["v"] < 1.0]
        if rs:
            print(f"  {br:6s}/{sub:9s} load={load:.1f}kg  λ* {np.mean([r['lam'] for r in rs]):+.2f}"
                  f"±{np.std([r['lam'] for r in rs]):.2f} (n={len(rs)}, "
                  f"⟨|τ̂|⟩={np.mean([r['tk'] for r in rs]):.2f}Nm)")

    # 모델 비교표
    print("\n[모델 비교 (fit set = 접촉 세션만; 공중은 홀드아웃)]")
    print(f"{'모델':4s} {'k':>2} {'RMSE':>7} {'AIC':>9} {'BIC':>9}  params (±95%CI)")
    for m in ("M0", "M1", "M2", "M2a", "M4", "M3"):
        d_ = fits[m]
        ps = " ".join(f"{k}={v:+.3f}±{d_['ci'].get(k, float('nan')):.3f}"
                      for k, v in d_["params"].items())
        print(f"{m:4s} {d_['k']:2d} {d_['rmse']:7.3f} {d_['aic']:9.1f} {d_['bic']:9.1f}  {ps}")
    if fits["M2"].get("v0_at_bound"):
        print("  ※ M2 v0가 상한(60)에 붙음 → 속도 게이트 미식별 (직접 측정에선 감쇠 없음)")
    Ft = fits["F_M3_vs_M2a"]
    print(f"\nF-검정 (M3 세션 오프셋 vs M2a): F={Ft['F']:.2f} df={Ft['df']} p={Ft['p']:.2e} "
          f"→ {'유의 (세션차 잔존)' if Ft['p'] < 0.01 else '비유의 (부하로 설명됨)'}")

    # 정련 적합: 유지 법칙 + 게이트 공동 적합 (물리 형태)
    a2, b2 = fits["M2a"]["params"]["a"], fits["M2a"]["params"]["b"]
    hg = fit_hold_gate(data)
    print("\n[정련 ① 유지 법칙 (v<1.5, 공중 앵커 포함, 그룹 균형 가중)]")
    for tag in ("hold_lin", "hold_quad"):
        d_ = hg[tag]
        ps = " ".join(f"{k}={v:+.4f}±{d_['ci'][k]:.4f}" for k, v in d_["params"].items())
        print(f"  {tag:9s}: {ps} | wRMSE {d_['rmse_w']:.3f} (n={d_['n']})")
    print("  세션별 유지 잔차 (quad 기준):")
    for s, r_ in sorted(hg["hold_resid_by_sess"].items()):
        print(f"    {s:16s} {r_['mean']:+.2f} ± {1.96*r_['sem']:.2f} (n={r_['n']})")
    print("\n[정련 ② 게이트 공동 적합: λ = a + (b·τ̂ + c·τ̂²)·g(v; v0), 전 창]")
    gg = hg["gate"]
    ps = " ".join(f"{k}={v:+.4f}±{gg['ci'][k]:.4f}" for k, v in gg["params"].items())
    print(f"  {ps} | wRMSE {gg['rmse_w']:.3f} (n={gg['n']})"
          + ("  ※v0 상한 — 게이트 미식별" if gg["v0_at_bound"] else ""))
    print(f"  → 측정 v0 = {gg['params']['v0']:.2f} ± {gg['ci']['v0']:.2f} rad/s "
          f"(P20 점수적합 v0≈6과 비교)")
    print("  ĝ 빈 추적 (유지 법칙 정규화, 지지항 >1Nm 창):")
    for g_ in hg["gate_bins"]:
        print(f"    {g_['lab']:10s} n={g_['n']:4d} v̄={g_['v']:5.2f}  ĝ={g_['g']:+.3f}±{g_['sem']:.3f}"
              f"  vs g(v̄;{gg['params']['v0']:.1f})={1/(1+(g_['v']/gg['params']['v0'])**2):.3f}")
    gate_pts = hg["gate_bins"]

    # CV — 접촉으로만 적합 → 공중 2세션 외삽 예측
    print("\n[교차검증 — fit {0604, s2s0319, 점프4(접촉)} → predict {s2s_0324(공중), s2s_air(공중)}]")
    cv = {}
    for hk, hr in HO.items():
        if not hr:
            continue
        lam_h = np.array([r["lam"] for r in hr])
        cv[hk] = {}
        for m in ("M0", "M1", "M2", "M2a", "M4", "M3"):
            pr = predict(m, fits[m]["params"], hr)
            cv[hk][m] = float(np.sqrt(np.mean((pr - lam_h) ** 2)))
        print(f"  {hk:8s} (n={len(hr)}): " +
              "  ".join(f"{m} {cv[hk][m]:.3f}" for m in ("M0", "M1", "M2", "M2a", "M4", "M3")) +
              f"   [관측 λ 평균 {lam_h.mean():+.2f}]")

    # 무부하 앵커 정합 (0319 air + 0324 air)
    print("\n[무부하(공중) 앵커 vs 절편]")
    anch = {}
    for hk in ("s2s_air", "s2s0324"):
        alo = [r["lam"] for r in HO[hk] if r["v"] < 0.3]
        atk = [r["tk"] for r in HO[hk] if r["v"] < 0.3]
        if not alo:
            continue
        sem = np.std(alo) / np.sqrt(len(alo))
        pred = a2 + b2 * np.mean(atk)
        anch[hk] = dict(lam_mean=float(np.mean(alo)), lam_ci95=float(1.96 * sem),
                        n=len(alo), tk_mean=float(np.mean(atk)), pred_M2a=float(pred))
        print(f"  {hk:8s} 유지 λ* = {np.mean(alo):+.3f} ± {1.96*sem:.3f} (95%CI, n={len(alo)}, "
              f"⟨|τ̂|⟩={np.mean(atk):.2f}Nm) | M2a 외삽 예측 {pred:+.3f}")
    print(f"  절편 a(M2a, 접촉만) = {a2:+.3f}±{fits['M2a']['ci']['a']:.3f} | 문헌 마찰 바닥 0.37Nm")
    if direct and direct["rows"]:
        ld = [r["lam_dir"] for r in direct["rows"]]
        lh = [r["lam_dir_hip"] for r in direct["rows"]]
        tg = [r["tau_grav_knee"] for r in direct["rows"]]
        print(f"  [직접법] λ_dir(knee) = {np.mean(ld):+.3f} ± {1.96*np.std(ld)/np.sqrt(len(ld)):.3f} "
              f"(n={len(ld)}, 모델 정역학 요구 ⟨τ_req⟩={np.mean(tg):+.2f}Nm, sgn={direct['sign']:+d})")
        print(f"  [직접법] hip 잔차     = {np.mean(lh):+.3f} ± {1.96*np.std(lh)/np.sqrt(len(lh)):.3f} "
              f"(0c 스티션 발견 1.27Nm 대조)")
    if airscan:
        best = min(airscan, key=lambda k: airscan[k])
        print(f"  [통짜 재생 검증] AIR(λ) = " +
              " ".join(f"{k}:{airscan[k]:.3f}" for k in airscan) + f"  → 최적 λ={best}")

    # 최종 법칙 (전 데이터, 세션 균형 가중)
    rows_all = [r for r in data if (r["sess"] in FITSESS and r["v"] <= 8.0)
                or r["sess"] in ("s2s0324", "s2s_air")]
    law = fit_final(rows_all)
    print("\n[최종 법칙 (전 세션 + 공중 앵커, 세션 균형 가중)]")
    for tag in ("linear", "quad"):
        d_ = law[tag]
        ps = " ".join(f"{k}={v:+.4f}±{d_['ci'][k]:.4f}" for k, v in d_["params"].items())
        print(f"  {tag:6s}: {ps}  | wRMSE {d_['rmse_w']:.3f}")
        print("          per-sess RMSE: " +
              " ".join(f"{s} {v:.2f}" for s, v in sorted(d_["rmse_by_sess"].items())))

    fits["cv"] = cv
    fits["gate_pts"] = [g for g in gate_pts if g]
    fits["hold_gate"] = hg
    fits["air_anchor"] = anch
    fits["direct_air"] = direct
    fits["air_replay_scan"] = airscan
    fits["law_final"] = law
    return fits, F, HO


def figure(rows, fits, F, HO):
    data = [r for r in rows if not r["edge"]]
    hq = fits["hold_gate"]["hold_quad"]["params"]
    gg = fits["hold_gate"]["gate"]["params"]
    fig, ax = plt.subplots(2, 2, figsize=(14.5, 10))
    mks = ["o", "s", "^", "D", "x", "P"]

    # (1) λ vs τ_load, 속도빈별 (고정 순서 = auto cycle) + 유지 법칙/게이트 곡선
    axa = ax[0, 0]
    tg = np.linspace(0, max(r["tk"] for r in F) * 1.05, 60)
    for j, (lo, hi) in enumerate(BINS):
        rs = [r for r in F if lo <= r["v"] < hi]
        if not rs:
            continue
        axa.scatter([r["tk"] for r in rs], [r["lam"] for r in rs],
                    s=16, alpha=0.55, marker=mks[j], label=BIN_LAB[j])
    for j, (hk, lab) in enumerate([("s2s_air", "s2s_air 0319 (공중)"),
                                   ("s2s0324", "s2s 0324 (공중 재분류)")]):
        hr = HO[hk]
        if hr:
            axa.scatter([r["tk"] for r in hr], [r["lam"] for r in hr], s=22, alpha=0.7,
                        marker=mks[4 + j], label=lab)
    axa.plot(tg, hq["a"] + hq["b"] * tg + hq["c"] * tg ** 2, lw=1.8,
             label=f"유지 법칙 {hq['a']:+.2f}{hq['b']:+.3f}τ{hq['c']:+.4f}τ²")
    axa.plot(tg, gg["a"] + (gg["b"] * tg + gg["c"] * tg ** 2) * float(g_of(5.0, gg["v0"])),
             lw=1.6, ls="--", label=f"게이트 법칙 @v=5 (v0={gg['v0']:.1f})")
    axa.axhline(0, lw=0.8, alpha=0.5)
    axa.set_xlabel("창 평균 |τ_knee(a_hat)| [Nm] (부하)"); axa.set_ylabel("창별 λ* [Nm]")
    axa.set_title("λ* vs 부하 — 접촉(속도빈) + 공중 앵커 2세션")
    axa.legend(fontsize=7); axa.grid(alpha=0.3)

    # (2) 게이트 추적 (유지 법칙 정규화) — P20 점수적합 게이트와 대조
    axb = ax[0, 1]
    gp = fits["gate_pts"]
    axb.errorbar([g["v"] for g in gp], [g["g"] for g in gp],
                 yerr=[1.96 * g["sem"] for g in gp], fmt="o", capsize=3,
                 label="측정 g = (λ*-a)/S(τ) 빈 평균")
    vg = np.logspace(-1.3, 1.1, 100)
    axb.plot(vg, g_of(vg, gg["v0"]), lw=1.5, label=f"적합 g(v; v0={gg['v0']:.1f})")
    axb.plot(vg, g_of(vg, 6.0), lw=1.2, ls="--", label="P20 점수적합 g(v; 6)")
    axb.axhline(1.0, lw=0.8, alpha=0.5)
    axb.set_xscale("log")
    axb.set_xlabel("창 평균 |dq2| [rad/s]"); axb.set_ylabel("정규화 (λ*-a)/S(τ)")
    axb.set_title(f"속도 게이트 — 직접 측정 v0={gg['v0']:.2f} rad/s (P20 점수적합 6과 일치)")
    axb.legend(fontsize=8); axb.grid(alpha=0.3)

    # (3) 세션별 저속 관측 vs 유지 법칙 예측 (부하로 세션차가 사라지는가)
    axc = ax[1, 0]
    ss = FITSESS + ["s2s0324", "s2s_air"]
    obs, pre, xs = [], [], []
    for i, s in enumerate(ss):
        rs = [r for r in data if r["sess"] == s and r["v"] < 1.5]
        if not rs:
            continue
        xs.append(i)
        obs.append(np.mean([r["lam"] for r in rs]))
        pre.append(np.mean(predict("M4", hq, rs)))
    axc.plot(xs, obs, "o-", label="관측 <λ*> (v<1.5)")
    axc.plot(xs, pre, "s--", label="유지 법칙 예측 — 부하만으로")
    axc.set_xticks(range(len(ss))); axc.set_xticklabels(ss, rotation=30, fontsize=8)
    axc.set_ylabel("λ [Nm]")
    Ft = fits["F_M3_vs_M2a"]
    axc.set_title(f"세션별 저속 기준선 — 부하 설명력 (세션 오프셋 F={Ft['F']:.1f}, p={Ft['p']:.1e})")
    axc.legend(fontsize=8); axc.grid(alpha=0.3)

    # (4) 무부하 앵커 4중 검증: 통짜 공중 재생 AIR(λ) 스캔 + 앵커/법칙 마커
    axd = ax[1, 1]
    scan = fits.get("air_replay_scan") or {}
    if scan:
        ls_ = sorted((float(k), v) for k, v in scan.items())
        axd.plot([x for x, _ in ls_], [y for _, y in ls_], "o-",
                 label="0319 공중 14사이클 통짜 재생 AIR(λ)")
        axd.set_yscale("log")
    anch = fits.get("air_anchor") or {}
    marks = []
    if "s2s_air" in anch:
        marks.append((anch["s2s_air"]["lam_mean"], "0319 공중 창별 λ*"))
    if "s2s0324" in anch:
        marks.append((anch["s2s0324"]["lam_mean"], "0324 공중 창별 λ* (held-out DAY)"))
    da = fits.get("direct_air") or {}
    if da.get("rows"):
        marks.append((float(np.mean([r["lam_dir"] for r in da["rows"]])), "정역학 직접법 λ_dir"))
    lawv = hq["a"] + hq["b"] * 0.2 + hq["c"] * 0.04
    marks.append((lawv, f"유지 법칙 예측 λ(τ=0.2) = {lawv:+.2f}"))
    for j, (x, lab) in enumerate(marks):
        axd.axvline(x, ls=("--", "-.", ":", "-")[j % 4], lw=1.3, alpha=0.85,
                    color=f"C{j + 1}", label=lab)
    axd.set_xlabel("상수 λ [Nm] (공중 무릎 보정)"); axd.set_ylabel("AIR 지표 (log)")
    axd.set_title("무부하 앵커 정합 — 재생 최적, 창별 λ*, 직접법, 법칙 예측")
    axd.legend(fontsize=7); axd.grid(alpha=0.3)

    fig.suptitle("P23 Phase 2 — 유지-지지 법칙 λ(τ_load, v) 직접 캘리브레이션 "
                 "(P19 플랜트, win_scan 정본, jump_0324 미사용)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=110)
    print(f"\nsaved {FIG_PATH}", flush=True)


def main():
    t0 = time.time()
    refit = "--refit" in sys.argv
    if refit and ROWS_PATH.exists():
        blob = safe.read_json(ROWS_PATH)
        rows, direct = blob["rows"], blob.get("direct_air")
        airscan = blob.get("air_replay_scan")
        print(f"rows 재사용: {len(rows)} windows", flush=True)
    else:
        print("=== 추출 시작 (winit는 import 시 완료) ===", flush=True)
        FX.apply(P, verbose=True)          # 0421 P12 캐시 xlsx 통일 (CL 경로는 원래 청정)
        if "P" not in C._W:                # p23_runners/air_replay 의존성 주입
            C._W.update(P=P, mj=mj, P20=P20M)
        rows = []
        extract_jumps(rows)
        extract_s2s_gnd(rows)
        extract_0604(rows)
        model_w, _ = RN.build_flip_welded(E.X32, E.V[1], E.SP)
        vw = RN.verify_weld(model_w)
        print(f"[air] weld verify: {vw}", flush=True)
        assert vw["ok"], "weld 검증 실패"
        extract_s2s_0324(rows, model_w)    # ★ 공중 재분류 (knee â≈0.25Nm = air 서명)
        cycles = extract_air(rows, model_w)
        direct = air_direct(model_w, cycles)
        airscan = air_cycle_lam_scan(model_w, cycles)
        safe.atomic_json_write(ROWS_PATH, dict(
            rows=rows, direct_air=direct, air_replay_scan=airscan,
            protocol=dict(W=WIN, lgrid=[-2, 6, 0.5], plant="P19 candidate",
                          s2s0324="AIR reclassified (knee ahat rms 0.25Nm = air signature; "
                                  "goal18 canonical kind='air')",
                          offsets="jumps=OFFKEY, 0429=(3.14,-3.0)deg, s2s/0604/air=0")))
        print(f"rows 저장: {len(rows)} windows [{(time.time()-t0)/60:.1f}m]", flush=True)

    fits, F, HO = report(rows, direct, airscan)
    figure(rows, fits, F, HO)
    safe.atomic_json_write(FIT_PATH, fits)
    print(f"\nDONE [{(time.time()-t0)/60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
