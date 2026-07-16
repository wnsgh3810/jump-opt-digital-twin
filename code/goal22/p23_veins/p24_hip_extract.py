# -*- coding: utf-8 -*-
"""p24_hip_extract — P24 preflight 카드 1: 힙 채널 창별 잔차 λ₁* 측정 (LIGHT-THIGH 플랜트).

가설 (P24): 측정된 무릎 유지-지지 법칙(기어 물림이 부하를 받쳐 모터 전류가 과소보고)은
기어 달린 모든 관절에 존재해야 한다 — 지금까지 무릎만 모델링했다. 힙 판
λ₁ = b₁·|τ̂₁|·g(|dq₁|; v0₁) (지상 부하 시 ON)이 오늘의 모순을 화해시킨다:
  · 공중 정역학: thigh 중력 레버 실측이 모델의 ~1/3.3 (Phase 1: 힙 준정적 −0.55~−0.71
    vs 모델 −1.2~−1.7 Nm) → 가벼운 thigh가 옳다
  · 지상 적합: thigh를 가볍게 하면 재생/H 붕괴 (0424 1.88→3.50, H 0.96→2.56)
    → 무거운 레버를 요구
  → 실물 = 가벼운 thigh + 지상 부하비례 힙 지지. 트윈의 무거운 thigh는 그 지지의 대리.

측정 설계 (p23_law_calib(Phase 2) 추출 프로토콜 미러 + p23 러너층):
  - 플랜트: p23a 후보 (SPRING_GATED+RISE_GATED)에 I_th=0.40, dz_th=−0.03 오버라이드
    (오늘 probe 값 — 탐색 케이지 밖이지만 측정 전용, 명기). 대조군 = stock p23a.
  - 무릎 채널: λ₂ = 측정 법칙(supp_vec+rise_term) 상시 활성 + 게이트 스프링 qfrc(h_load
    트레이스) + 0604 cvt 가지는 C_CVT qfrc — 즉 p23 창 심판과 동일 배선. λ₂ 스캔 없음.
  - 힙 채널: th + λ₁ 그리드 [−8, +8] step 0.5 스캔 → argmin 포물선 보정 (win_scan 정본
    점수: MS.W_Q·(q1+q2 RMSE) + MS.W_DQ·(dq1+dq2 RMSE), 민감도 <2% 창 제외).
  - 세션: 점프 유지+푸시 0421/0424/0602 (R19.TRIALS, held-out 0324·CVT 0429 제외) /
    s2s_gnd_0319 / 0604 페이로드 4렁 (부하축!) / 공중 s2s_air 0319 + s2s_0324
    (반증 예측: 공중 λ₁ ≈ 0).
  - 창 그리드/캡/오프셋 = p23_law_calib과 동일 (직접 비교 가능성).

출력: p24_hip_rows.json (변형별 rows + meta). 원본 데이터 읽기 전용, 기존 파일 불변.
실행: PYTHONIOENCODING=utf-8 python p24_hip_extract.py [--variant light|stock|both]
"""
import os
import sys
import time
from pathlib import Path

import numpy as np

# ★ 구조 플래그는 p23 모듈 import 전에 env로 강제 (import 시점에 벡터 축수 결정)
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe

safe.utf8_console()

import p23_v6_runners as RU
import p22_eval as E
import p21_cma as C
import p19_run as R19
import p23_loaders as L
import p19_adapter as AD
import s2s_0604 as S0
from cvt_core import closure

assert RU.SPRING_GATED and RU.RISE_GATED, "p23a 구조 플래그 불일치 (env 강제 실패)"

CAND_PATH = HERE / "fourbar_p23a_candidate.json"
OUT_PATH = HERE / "p24_hip_rows.json"
LGRID1 = np.arange(-8.0, 8.01, 0.5)     # 힙 λ₁ 그리드 (winlam ±6 → 푸시 지지 여유 확장)
WIN = 0.2                               # p23_law_calib 동일
SENS_MIN = 0.02
CAP = {"s2s0319": 90, "s2s0324": 90, "0604": 110, "air": 15}   # p23_law_calib 동일
JDS = ("jump_position_0421", "jump_0424", "jump_0602")
SESS_OF = {"jump_position_0421": "0421", "jump_0424": "0424", "jump_0602": "0602"}
VARIANTS = {"light": {"I_th": 0.40, "dz_th": -0.03},   # 오늘 probe 값 (케이지 밖 — 측정 전용)
            "stock": {}}                                # 대조군: p23a 그대로

_G = {}


def init():
    RU.ensure_init()
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()          # ensure_init가 fix0421 이후 보장
    P = C._W["P"]
    _G.update(P=P, mj=C._W["mj"], S=P.J._P["S"], MS=C._W["P12"]._G["MS"],
              P12=C._W["P12"], FR=P.J._P["FR"], A=P.A_PAPER, SD=P.SD)


def variant_vec(name):
    """p23a 후보 벡터 → I_th/dz_th 오버라이드 (동결 3축 강제 포함)."""
    cand = safe.read_json(CAND_PATH)
    v = RU.apply_freeze(RU.pad23(np.asarray(cand["x"], float)))
    ov = VARIANTS[name]
    if "I_th" in ov:
        v[RU.NAMES23.index("I_th")] = ov["I_th"]
    if "dz_th" in ov:
        v[RU.NAMES23.index("dz_th")] = ov["dz_th"]
    return v


def plant_of(v):
    """v23 → (x32, sp, 파생 상수 dict) — p23a_all_results.setup()과 동일 파생."""
    x32, sp = C.x32_of(v[:20])
    return x32, sp, dict(
        REF=float(v[1]), TM=float(v[14]), LAW=RU.law_of(v), SPR=RU.spr_of(v),
        C_CVT=float(v[20]), KR=RU.rise_of(float(v[21])),
        DD=dict(zip(_G["FR"].NAMES, np.asarray(x32)[:26])))


def traces_of(d, g):
    """측정 트레이스 → (th, tk, hl, a1, a2). 무릎 = ahat+법칙(supp+rise) SD 시프트 폴드
    (windows23/win429_06_23 규약 문자 동일), 힙 = ahat SD 시프트 (λ₁는 창에서 가산).
    hl = 게이트 스프링 h_load 시계열 (SD 무시프트 — hl_vec 규약)."""
    P, SD, A = _G["P"], _G["SD"], _G["A"]
    t = d["t"]
    sv = RU.supp_vec(d["traw2"], d["dq2"], g["LAW"])
    if g["KR"]:
        sv = sv + RU.rise_term(d["dq2"], g["KR"], g["LAW"][2])
    a1 = P.J.ahat(A, d["traw1"], d["dq1"])
    a2 = P.J.ahat(A, d["traw2"], d["dq2"])
    th = np.interp(t - SD, t, a1)
    tk = np.interp(t - SD, t, a2 + sv)
    hl = RU.hl_vec(d["traw2"], d["dq2"], g["SPR"])
    return th, tk, hl, a1, a2


def lam_star(lg, scores):
    """argmin + 포물선 보정 → (λ*, edge?, 민감도) — winlam 동형."""
    scores = np.asarray(scores, float)
    sens = float((scores.max() - scores.min()) / max(scores.min(), 1e-9))
    i = int(np.argmin(scores))
    if i in (0, len(lg) - 1):
        return float(lg[i]), True, sens
    a, b, c = scores[i - 1], scores[i], scores[i + 1]
    den = a - 2 * b + c
    step = float(lg[1] - lg[0])
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return float(lg[i] + np.clip(off, -1, 1) * step), False, sens


def wstats(d, a1, a2, t0, W):
    """창 [t0, t0+W] 평균 부하/속도/자세 (실좌표, 무시프트 — 부하 측정용)."""
    t = d["t"]
    wm = (t >= t0) & (t <= t0 + W)
    return dict(t1m=float(np.mean(np.abs(a1[wm]))), t1sgn=float(np.mean(a1[wm])),
                v1=float(np.mean(np.abs(d["dq1"][wm]))),
                tk=float(np.mean(np.abs(a2[wm]))), v2=float(np.mean(np.abs(d["dq2"][wm]))),
                q1deg=float(np.degrees(np.mean(d["q1"][wm]))),
                q2deg=float(np.degrees(np.mean(d["q2"][wm]))))


def win_scan_hip(model, d, l_i, starts, W, g, o1=0.0, o2=0.0, is_cvt=False):
    """접촉 세션 힙 λ₁ 스캔 — p20_exp4.win_scan 미러 + p23 층(스프링/C_CVT qfrc) +
    스캔 축을 무릎→힙으로 교체 (무릎 = 법칙 폴드 고정)."""
    mj, S, MS = _G["mj"], _G["S"], _G["MS"]
    t = d["t"]
    th0, tk, hl, a1, a2 = traces_of(d, g)
    sprm = RU.spr_resolve(model, g["SPR"])
    c_cvt = g["C_CVT"] if is_cvt else 0.0
    qg = rg = None
    if is_cvt and c_cvt > 0:
        qg, rg = RU.rtab(l_i)
    q1mj = -(d["q1"] + o1) - np.pi / 2
    qcmj = -(d["q2"] + o2)
    data = mj.MjData(model)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    fg_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    # 접촉 FK-bz (exp4 정본)
    bz = np.zeros_like(t); qks = np.zeros_like(t); qps = np.zeros_like(t)
    qk_prev = None
    for i in range(len(t)):
        qk, qp, _ = closure(float(qcmj[i]), l_i, qk_prev)
        data.qpos[:] = [1.0, q1mj[i], qcmj[i], qp, qk]
        data.qvel[:] = 0
        mj.mj_forward(model, data)
        bz[i] = 1.0 - float(data.geom_xpos[fg_id][2]) + S.FOOT_RADIUS
        qks[i], qps[i], qk_prev = qk, qp, qk
    vbz = np.gradient(bz, t)
    dt = model.opt.timestep
    ks, kref, _ = sprm
    out = []
    for t0 in starts:
        i0 = int(np.searchsorted(t, t0))
        if i0 >= len(t) - 5:
            continue
        t1 = min(t0 + W, t[-1])
        nst = int(round((t1 - t0) / dt))
        if nst < 20:
            continue
        qk2, qp2, _ = closure(float(qcmj[i0]) + 1e-4, l_i, qks[i0])
        r_ = (qk2 - qks[i0]) / 1e-4; gp = (qp2 - qps[i0]) / 1e-4
        dqc = -d["dq2"][i0]
        scores = []
        for lam in LGRID1:
            data.qpos[:] = [bz[i0], q1mj[i0], qcmj[i0], qps[i0], qks[i0]]
            data.qvel[:] = [vbz[i0], -d["dq1"][i0], dqc, gp * dqc, r_ * dqc]
            mj.mj_forward(model, data)
            ts = np.empty(nst); q1a = np.empty(nst); q2a = np.empty(nst)
            dq1a = np.empty(nst); dq2a = np.empty(nst)
            ok = True
            for k in range(nst):
                tc = t0 + k * dt
                s2m = float(np.interp(tc, t, tk))
                data.ctrl[:] = [-(float(np.interp(tc, t, th0)) + lam), -s2m]
                tql = 0.0
                if qg is not None:                      # C_CVT (CVT 한정, win429 동형)
                    rr = float(np.interp(data.qpos[2], qg, rg))
                    amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
                    vk = float(data.qvel[dof_knee])
                    tql = -c_cvt * abs(s2m) * amp * float(np.tanh(vk / 1.0))
                tql += ks * (kref - float(data.qpos[iq_k])) * float(np.interp(tc, t, hl))
                data.qfrc_applied[dof_knee] = tql
                try:
                    mj.mj_step(model, data)
                except Exception:
                    ok = False; break
                ts[k] = tc + dt
                q1a[k] = data.qpos[1]; q2a[k] = data.qpos[2]
                dq1a[k] = data.qvel[1]; dq2a[k] = data.qvel[2]
            if not ok:
                scores.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                scores.append(np.nan); continue
            r = lambda sim, real: float(np.sqrt(np.mean(
                (np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            scores.append(MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
                          + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
        scores = np.asarray(scores, float)
        if np.isnan(scores).any():
            continue
        lam1, edge, sens = lam_star(LGRID1, scores)
        if sens < SENS_MIN:
            continue
        out.append(dict(t0=float(t0), lam1=lam1, edge=bool(edge), sens=float(sens),
                        dq1_0=float(d["dq1"][i0]),
                        **wstats(d, a1, a2, t0, W)))
    return out


def win_scan_hip_air(model, d, starts, W, g):
    """공중(용접 베이스) 힙 λ₁ 스캔 — p23_law_calib.win_scan_air 미러 + 스프링 qfrc +
    스캔 축 힙 (무릎 = 법칙 폴드 고정). 반증 예측 검증부 (λ₁ ≈ 0 기대)."""
    mj, MS = _G["mj"], _G["MS"]
    t = d["t"]
    th0, tk, hl, a1, a2 = traces_of(d, g)
    sprm = RU.spr_resolve(model, g["SPR"])
    ks, kref, _ = sprm
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
        dqc = -d["dq2"][i0]; dqh = -d["dq1"][i0]
        scores = []
        for lam in LGRID1:
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
                md.ctrl[:] = [-(float(np.interp(tc, t, th0)) + lam),
                              -float(np.interp(tc, t, tk))]
                md.qfrc_applied[dof["knee"]] = (ks * (kref - float(md.qpos[iq["knee"]]))
                                                * float(np.interp(tc, t, hl)))
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
                scores.append(MS.W_Q * 2 + MS.W_DQ * 20); continue
            mk = (t >= ts[0]) & (t <= ts[-1])
            if mk.sum() < 3:
                scores.append(np.nan); continue
            r = lambda sim, real: float(np.sqrt(np.mean(
                (np.interp(t[mk], ts, sim) - real[mk]) ** 2)))
            scores.append(MS.W_Q * (r(q1a, q1mj) + r(q2a, qcmj))
                          + MS.W_DQ * (r(dq1a, -d["dq1"]) + r(dq2a, -d["dq2"])))
        scores = np.asarray(scores, float)
        if np.isnan(scores).any():
            continue
        lam1, edge, sens = lam_star(LGRID1, scores)
        if sens < SENS_MIN:
            continue
        out.append(dict(t0=float(t0), lam1=lam1, edge=bool(edge), sens=float(sens),
                        dq1_0=float(d["dq1"][i0]),
                        **wstats(d, a1, a2, t0, W)))
    return out


def subsample(starts, cap):
    starts = np.asarray(starts, float)
    if len(starts) > cap:
        starts = starts[np.linspace(0, len(starts) - 1, cap).astype(int)]
    return starts


def pack(rw, variant, sess, ds, sub, load, W, branch=""):
    return dict(variant=variant, sess=sess, ds=ds, sub=str(sub), load=float(load),
                branch=branch, W=float(W), **rw)


def extract_variant(name, rows):
    """1개 플랜트 변형(light/stock)의 전 세션 추출."""
    P = _G["P"]
    v = variant_vec(name)
    x32, sp, g = plant_of(v)
    print(f"\n=== variant [{name}] I_th={v[RU.NAMES23.index('I_th')]:.3f} "
          f"dz_th={v[RU.NAMES23.index('dz_th')]:+.3f} | law={tuple(round(x, 3) for x in g['LAW'])} "
          f"spr={tuple(round(x, 3) for x in g['SPR'])} c_cvt={g['C_CVT']:.3f} "
          f"k_rise={g['KR']:.3f} ===", flush=True)
    model_f = RU.build_flip23(x32, g["REF"], sp, 0.0)   # RISE 모드: d_dq 경로 no-op

    # ── 점프 유지+푸시 (0421/0424/0602) — law_calib extract_jumps 프로토콜 ──
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds not in JDS:
            continue                        # held-out 0324 + CVT 0429 제외
        t = d["t"]
        toff = float(t[m][-1]) - 0.1
        W = WIN
        starts = np.arange(0.02, toff - 0.14, 0.03)
        if len(starts) < 3:
            W = 0.12
            starts = np.arange(0.02, max(toff - 0.06, 0.03), 0.03)
        k1, k2 = _G["P12"].OFFKEY.get(ds, (None, None))
        o1 = g["DD"].get(k1, 0.0) if k1 else 0.0
        o2 = g["DD"].get(k2, 0.0) if k2 else 0.0
        got = win_scan_hip(model_f, d, 0.030, starts, W, g, o1=o1, o2=o2)
        rows.extend(pack(rw, name, SESS_OF[ds], ds, sub, 0.0, W) for rw in got)
        lam = [r["lam1"] for r in got]
        print(f"  [jump] {ds}/{sub}: {len(got)}창 λ₁* "
              f"{np.mean(lam) if lam else float('nan'):+.2f}±{np.std(lam) if lam else 0:.2f}",
              flush=True)

    # ── s2s_gnd_0319 — law_calib extract_s2s_gnd 프로토콜 (o=0) ──
    for tr in _G["P12"]._G["trials"]:
        if tr["ds"] != "s2s_gnd_0319":
            continue
        pp = tr["pp"]; t = pp["t"]
        d = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                 dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                 traw1=np.asarray(tr["raw1"], float), traw2=np.asarray(tr["raw2"], float))
        starts = subsample(np.arange(0.4, t[-1] - 0.4, 0.45), CAP["s2s0319"])
        got = win_scan_hip(model_f, d, 0.030, starts, WIN, g)
        rows.extend(pack(rw, name, "s2s0319", tr["ds"], tr["sub"], 0.0, WIN) for rw in got)
        lam = [r["lam1"] for r in got]
        print(f"  [s2s0319] {tr['sub']}: {len(got)}창 λ₁* "
              f"{np.mean(lam) if lam else float('nan'):+.2f}±{np.std(lam) if lam else 0:.2f}",
              flush=True)

    # ── 0604 페이로드 (부하축!) — law_calib extract_0604 프로토콜 ──
    for grp, sub, load in [("cvt", "no_load", 0.0), ("cvt", "load_2.5", 2.5),
                           ("cvt", "load_5", 5.0), ("no_cvt", "no_load", 0.0)]:
        d = S0.load_0604(grp, sub)
        li = d["l_i"]
        model = (RU.build_cvt23(x32, g["REF"], sp, li, 0.0) if grp == "cvt"
                 else RU.build_flip23(x32, g["REF"], sp, 0.0))
        bid = _G["mj"].mj_name2id(model, _G["mj"].mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load
        starts = subsample(np.arange(0.3, d["t"][-1] - 0.3, 0.35), CAP["0604"])
        got = win_scan_hip(model, d, li, starts, WIN, g, is_cvt=(grp == "cvt"))
        rows.extend(pack(rw, name, "0604", f"0604_{grp}", sub, load, WIN, branch=grp)
                    for rw in got)
        lam = [r["lam1"] for r in got]
        print(f"  [0604] {grp}/{sub} ({load}kg, l_i={li * 1000:.2f}mm): {len(got)}창 λ₁* "
              f"{np.mean(lam) if lam else float('nan'):+.2f}±{np.std(lam) if lam else 0:.2f}",
              flush=True)

    # ── 공중 (용접 베이스): s2s_air 14사이클 + s2s_0324 5 trial — 반증 예측 ──
    model_w = RU.build_weld23(x32, g["REF"], sp, 0.0)
    for i, d in enumerate(L.load_s2s_air()[0]):
        starts = subsample(np.arange(0.2, d["t"][-1] - 0.25, 0.3), CAP["air"])
        got = win_scan_hip_air(model_w, d, starts, WIN, g)
        rows.extend(pack(rw, name, "s2s_air", "s2s_air_0319", f"cyc{i + 1:02d}", 0.0, WIN)
                    for rw in got)
    n_air = len([r for r in rows if r["variant"] == name and r["sess"] == "s2s_air"])
    lam = [r["lam1"] for r in rows if r["variant"] == name and r["sess"] == "s2s_air"]
    print(f"  [air] 14사이클 계 {n_air}창 λ₁* {np.mean(lam) if lam else float('nan'):+.2f}"
          f"±{np.std(lam) if lam else 0:.2f}", flush=True)
    for sub in L.SUBS_S2S_0324:
        d, meta = L.load_s2s_0324(sub)
        starts = subsample(np.arange(0.4, d["t"][-1] - 0.4, 0.45), CAP["s2s0324"])
        got = win_scan_hip_air(model_w, d, starts, WIN, g)
        rows.extend(pack(rw, name, "s2s0324", "s2s_0324_air", sub, 0.0, WIN) for rw in got)
        lam = [r["lam1"] for r in got]
        print(f"  [s2s0324-air] {sub}: {len(got)}창 λ₁* "
              f"{np.mean(lam) if lam else float('nan'):+.2f}±{np.std(lam) if lam else 0:.2f}",
              flush=True)


def main():
    t0 = time.time()
    want = "both"
    if "--variant" in sys.argv:
        want = sys.argv[sys.argv.index("--variant") + 1]
    names = ["light", "stock"] if want == "both" else [want]
    print(f"=== p24_hip_extract — 힙 λ₁* 창별 측정 (변형: {names}) ===", flush=True)
    init()
    print(f"init done [{time.time() - t0:.0f}s]", flush=True)
    rows = []
    for name in names:
        extract_variant(name, rows)
    meta = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        protocol=dict(
            W=WIN, lgrid1=[float(LGRID1[0]), float(LGRID1[-1]), 0.5], sens_min=SENS_MIN,
            caps=CAP, plant="fourbar_p23a_candidate (SPRING_GATED+RISE_GATED)",
            variants=VARIANTS,
            knee="λ₂ = p23a 법칙 고정 (supp_vec+rise_term SD 폴드) + 게이트 스프링 qfrc "
                 "+ 0604 cvt C_CVT qfrc — 스캔 없음 (λ₁-λ₂ 좌표하강 결합 caveat 명기)",
            hip="th + λ₁ 그리드 스캔, 점수 = MS.W_Q·(q1+q2) + MS.W_DQ·(dq1+dq2) RMSE",
            offsets="jumps=P12.OFFKEY(p23a dd), s2s/0604/air=0 (law_calib 동일)",
            excluded="jump_0324 (held-out 철칙), jump_0429 (과제 범위 외 CVT 점프)",
            note_cage="light 변형 I_th=0.40은 케이지 [0.55,1.45] 밖 — 측정 전용 (probing only)"),
        n_rows=len(rows), elapsed_s=round(time.time() - t0, 1))
    safe.atomic_json_write(OUT_PATH, dict(meta=meta, rows=rows))
    print(f"\nsaved {OUT_PATH.name} — {len(rows)} rows [{(time.time() - t0) / 60:.1f}m]",
          flush=True)


if __name__ == "__main__":
    main()
