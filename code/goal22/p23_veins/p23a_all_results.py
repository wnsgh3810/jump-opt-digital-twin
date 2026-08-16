# -*- coding: utf-8 -*-
"""p23a 후보 전 데이터 결과 생성 — g22_p19_all_results / g22_p22b_all_results와 1:1 파일 호환.

출력: CVT/jump_opt/g22_p23a_all_results/<세션>/{png,gif,traj}/ + INDEX.md
  - 점프 5세션 (0324 held-out / 0421 / 0424 / 0602 / 0429 CVT) × CL + A
  - s2s_gnd_0319 (사이클 리셋 Mode A replay) · s2s_0604_payload (CL + A)
  - 보너스: jump_0422 / jump_0319tau (CL(FF)+A) · s2s_air_0319 (A, 용접 베이스)

프로토콜 (침묵실패 방역 — 전부 심판 코드와 동일 배선):
  CL  = p23_v6_runners.cl_run23_log — p19_adapter.eval_p23 배선 그대로
        (0324: alphas=1, o=0, ff_hip=True / 0429: o=x[17],x[18], C_CVT / 그 외 OFFK+ALPH)
  A   = p23_v6_runners.a_full23_log — p23_v6_runners.oldq_h23 배선 그대로
        (0429: QOFF_A429 + 0.02508 빌드 / 무변속 OFFK / 0324·신규세션 o=0 = oldq_ff23 규약)
  s2s_gnd = p19_all_results.do_s2s 미러 + p23 층 (lam→supp_vec+rise, 게이트 스프링 qfrc)
  s2s_0604 = s2s_0604_p19 미러 + p23 러너 (페이로드 base 질량 가산, C_CVT 전 그룹 배선)
  그림 = bench/render_kit.fig_trial_std (변경 금지, import 사용) · GIF = goal18_CANONICAL.

MANDATORY 교차검증 (스테이지 check — 통과 전 png/gif 생성 금지):
  ① A-재생 npz 재계산 세션 dq2 RMSE (0424/0602/0429) == p23_v6_eval.evaluate() OLDQ ±0.02
  ② CL npz 재계산 τ-갭 세션 평균 == p19_adapter.eval_p23 summary ±0.2%p

스테이지: ref → sim → check → figs → gifs → bonus → index (기본 all = 순차 + 게이트).
"""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os
import sys
import json
import time
from pathlib import Path

# ★ 구조 플래그는 p23 모듈 import 전에 env로 강제 (import 시점에 벡터 축수 결정)
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent / "p18_cvt"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p23_v6_runners as RU
import p23_v6_eval as EV
import p23_runners as RN
import p22_eval as E
import p19_run as R19
import p19_adapter as AD
import render_kit as RK
import safe

assert RU.SPRING_GATED and RU.RISE_GATED, "p23a 구조 플래그 불일치 (env 강제 실패)"

import mujoco
from PIL import Image, ImageDraw
from cvt_core import closure, qpos_from_crank  # noqa: F401 (qpos_from_crank: 러너 내부 사용)

sys.path.insert(0, (LEGACY_ROOT + "/goal18_CANONICAL/code"))
import make_anim as MA
from cvt_anim import build_anim_model

MODEL_TAG = "p23a"
CAND = AD.load_candidate(HERE / "fourbar_p23a_candidate.json")
ROOT = Path((LEGACY_ROOT + "/g22_p23a_all_results"))
REF_JSON = ROOT / "p23a_crosscheck_ref.json"
RESULT_JSON = ROOT / "p23a_crosscheck_result.json"
DSDIR = {"jump_0324": "jump_0324_heldout", "jump_position_0421": "jump_position_0421",
         "jump_0424": "jump_0424", "jump_0602": "jump_0602",
         "jump_0429": "jump_0429_cvt",
         "jump_0422": "jump_0422", "jump_0319tau": "jump_0319tau"}
CL_TOL = 0.002      # ±0.2%p (τ-갭은 비율)
OLDQ_TOL = 0.02

# setup()이 채우는 전역 (winit 후에만 유효)
G = {}


def setup():
    """winit+fix0421 1회 → 후보 벡터/모델 파라미터 전역 확정 (eval_p23와 동일 순서)."""
    if G.get("ready"):
        return
    t0 = time.time()
    RU.ensure_init()
    AD._INIT = True
    P = RU.C._W["P"]
    v = RU.apply_freeze(RU.pad23(np.asarray(CAND["x"], float)))
    x32, sp = RU.C.x32_of(v[:20])
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()      # ★ 반드시 fix0421 이후 (ensure_init가 보장)
    G.update(ready=True, P=P, A=P.A_PAPER, V=v, X32=x32, SP=sp,
             REF=float(v[1]), TM=float(v[14]),
             LAW=RU.law_of(v), SPR=RU.spr_of(v),
             C_CVT=float(v[20]), D_DQ=float(v[21]), KR=RU.rise_of(float(v[21])),
             QOFF_CL429=(float(v[17]), float(v[18])),
             DD=dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26])))
    print(f"setup done [{time.time() - t0:.0f}s] — law={tuple(round(x, 4) for x in G['LAW'])} "
          f"spr={tuple(round(x, 4) for x in G['SPR'])} c_cvt={G['C_CVT']:.4f} "
          f"k_rise={G['KR']:.4f} tm={G['TM'] * 1000:.2f}ms", flush=True)


def model_flip():
    if "model_f" not in G:
        G["model_f"] = RU.build_flip23(G["X32"], G["REF"], G["SP"], G["D_DQ"])
    return G["model_f"]


def model_cvt_cl(l_i):
    """CL용 CVT 모델 — eval_p23 규약 (첫 CVT trial의 l_i로 1회 빌드)."""
    if "model_c_cl" not in G:
        G["model_c_cl"] = RU.build_cvt23(G["X32"], G["REF"], G["SP"], l_i, G["D_DQ"])
    return G["model_c_cl"]


def model_cvt_a():
    """A(재생)용 CVT 모델 — oldq_h23 규약 (l_i=0.02508 고정 빌드)."""
    if "model_c_a" not in G:
        G["model_c_a"] = RU.build_cvt23(G["X32"], G["REF"], G["SP"], 0.02508, G["D_DQ"])
    return G["model_c_a"]


def offsets_nocvt(ds):
    """무변속 세션 OFFK per-session 오프셋 (x32 dict) — eval_p23/oldq_h23 공용."""
    P = G["P"]
    k1, k2 = P.J.OFFK.get(ds, (None, None))
    return (G["DD"].get(k1, 0.0) if k1 else 0.0,
            G["DD"].get(k2, 0.0) if k2 else 0.0)


# ══════════════════ 그림/GIF/NPZ (p19_all_results 정본 미러 — 규격 불변) ══════════════════
def make_fig(ds, sub, d, L, mode, l_i, o1, o2, hr, out, cl_note=" · 실효게인 α+클립 반영"):
    """표준 그림 — 지표=cvt_run2.metrics2, 그림=render_kit.fig_trial_std (변경 금지)."""
    import cvt_run2 as CR
    A = G["A"]; P = G["P"]
    d2 = dict(d)
    d2.setdefault("h_real", hr)
    if not np.isfinite(d2.get("h_real", float("nan"))):
        d2["h_real"] = float(hr)
    A_save = CR.A.copy(); CR.A = np.asarray(A, float)   # 주입 후 복원 (repo 규약)
    try:
        m = CR.metrics2(d2, L, o1, o2)
    finally:
        CR.A = A_save
    t = d["t"]
    tp1 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw1"], d["dq1"]))
    tp2 = np.interp(t - P.SD, t, P.J.ahat(A, d["traw2"], d["dq2"]))
    RK.fig_trial_std(out, f"{ds}/{sub}", d2, L, m, mode, l_i, tp1, tp2,
                     o1q=o1, o2q=o2, model_tag=MODEL_TAG, cl_note=cl_note)


ANIM = {}


def render_gif(L, l_i, label, hr, out, t_end, lookat_z=0.3):
    li_r = round(float(l_i), 4)
    if li_r not in ANIM:
        ANIM[li_r] = build_anim_model(li_r)
    am = ANIM[li_r]
    mk = (L["t"] >= -0.05) & (L["t"] <= t_end + 0.35)
    tt = L["t"][mk]; q1 = L["q1"][mk]; qc = L["q2"][mk]; bz = L["bz"][mk]
    wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
    mj1 = wrap(-q1 - np.pi / 2); mjc = wrap(-qc)
    h_sim = float(bz[tt > 0].max()) if (tt > 0).any() else float("nan")
    dur = float(tt[-1] - tt[0])
    n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(tt) - 1, n).astype(int)
    data = mujoco.MjData(am)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, lookat_z])
    frames = []
    qk_prev = None
    with mujoco.Renderer(am, width=640, height=480) as ren:
        for i in idxs:
            qk, qp, _ = closure(float(mjc[i]), li_r, qk_prev)
            qk_prev = qk
            data.qpos[:] = [float(bz[i]), float(mj1[i]), float(mjc[i]), qp, qk]
            data.qvel[:] = 0.0
            mujoco.mj_forward(am, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            RK.draw_overlay(dr, MA, label, tt[i] * 1000, bz_cm=bz[i] * 100,
                            hip_deg=float(np.degrees(q1[i])),
                            knee_deg=float(np.degrees(qc[i])),
                            h_sim=h_sim, h_real=hr, l_i_mm=li_r * 1000)
            frames.append(img)
    frames[0].save(str(out), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)


def save_npz(out, L, **meta):
    np.savez(out, **{k: v for k, v in L.items()},
             **{k: v for k, v in meta.items()})


def mkdirs(sd):
    for c in ("png", "gif", "traj"):
        (sd / c).mkdir(parents=True, exist_ok=True)


# ══════════════════ 스테이지 ref — 심판 신선값 (교차검증 기준) ══════════════════
def stage_ref(force=False):
    if REF_JSON.exists() and not force:
        print(f"ref 존재 — 재사용: {REF_JSON}", flush=True)
        return safe.read_json(REF_JSON)
    setup()
    print("=== ref ① p23_v6_eval.evaluate (OLDQ 등 전 성분, 신선) ===", flush=True)
    comp = EV.evaluate(np.asarray(CAND["x"], float), verbose=True, keep_rows=True)
    print("=== ref ② p19_adapter.eval_p23 (CL 세션 요약, 신선) ===", flush=True)
    r23 = AD.eval_p23(CAND)
    ref = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), cand=str(CAND["_path"]),
        oldq={k: float(v) for k, v in comp["OLDQ"].items()},
        oldq_trials=comp["OLDQ_trials"],
        clff={k: float(v) for k, v in comp["CLFF"].items()},
        clff_rows=comp["CLFF_rows"],
        oldqff={k: float(v) for k, v in comp["OLDQFF"].items()},
        oldqff_rows=comp["OLDQFF_rows"],
        air=float(comp["AIR"]), air_rows=comp["AIR_rows"],
        J_v6=float(comp["J_v6"]), J_v5=float(comp["J_v5"]),
        norm={k: float(v) for k, v in comp["norm"].items()},
        H=float(comp["H"]),
        cl_summary=r23["summary"], fit=float(r23["fit"]),
        heldout=float(r23["heldout"]), cl_rows=r23["rows"])
    safe.atomic_json_write(REF_JSON, ref)
    print(f"ref 저장: OLDQ={ {k: round(v, 3) for k, v in ref['oldq'].items()} } "
          f"CL(FIT/HO)={ref['fit']:.4f}/{ref['heldout']:.4f}", flush=True)
    return ref


# ══════════════════ 스테이지 sim — 코어 79 npz ══════════════════
def do_jumps(skip_existing=True):
    setup()
    A = G["A"]
    results = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        sd = ROOT / DSDIR[ds]
        mkdirs(sd)
        alphas = R19.ALPH.get(ds, [1, 1, 1, 1])
        if is_cvt:
            hr = float(d.get("h_real", float("nan")))
        else:
            hr = E.h_real_of(ds, sub)
        for mode in ("CL", "A"):
            out = sd / "traj" / f"{sub}__{mode}.npz"
            if skip_existing and out.exists():
                results.append((ds, sub, mode, "SKIP"))
                continue
            if mode == "CL":
                if is_cvt:
                    L = RU.cl_run23_log(model_cvt_cl(l_i), True, l_i, d, gains, dqon,
                                        ffk, A, G["TM"], alphas, G["LAW"],
                                        c_cvt=G["C_CVT"], o1=G["QOFF_CL429"][0],
                                        o2=G["QOFF_CL429"][1], spr=G["SPR"],
                                        k_rise=G["KR"])
                else:
                    # held-out 0324(ffk): o=0 + ff_hip (eval_p23 규약)
                    o1, o2 = (0.0, 0.0) if ffk else offsets_nocvt(ds)
                    L = RU.cl_run23_log(model_flip(), False, l_i, d, gains, dqon,
                                        ffk, A, G["TM"], alphas, G["LAW"],
                                        c_cvt=0.0, o1=o1, o2=o2, ff_hip=bool(ffk),
                                        spr=G["SPR"], k_rise=G["KR"])
            else:
                if is_cvt:
                    o1, o2 = E.QOFF_A429      # oldq_h23 규약 (Mode A 프로토콜 = P18b)
                    L = RU.a_full23_log(model_cvt_a(), True, d["l_i"], d, G["LAW"],
                                        o1, o2, c_cvt=G["C_CVT"], spr=G["SPR"],
                                        k_rise=G["KR"])
                else:
                    # 0324(ffk): o=0 (oldq_ff23 규약 — 적합 오프셋 없음)
                    o1, o2 = (0.0, 0.0) if ffk else offsets_nocvt(ds)
                    L = RU.a_full23_log(model_flip(), False, l_i, d, G["LAW"],
                                        o1, o2, c_cvt=0.0, spr=G["SPR"],
                                        k_rise=G["KR"])
            if L is None:
                print(f"CRASH {ds}/{sub} [{mode}]", flush=True)
                results.append((ds, sub, mode, "CRASH"))
                continue
            save_npz(out, L, l_i=l_i, ds=ds, sub=sub, mode=mode, h_real=hr)
            results.append((ds, sub, mode, "OK"))
            print(f"npz {ds}/{sub} [{mode}]", flush=True)
    return results


def s2s_gnd_trials():
    """P12 s2s_gnd_0319 트라이얼 → (sub, tr, pp, rs_i, rs_t, d_ps) 목록.
    p19_all_results.do_s2s의 전처리 미러 + p23 층 (lam=supp_vec+rise)."""
    setup()
    P = G["P"]; A = G["A"]
    P12 = P.J._P["P12"]
    k1, k2 = P12.OFFKEY.get("s2s_gnd_0319", (None, None))
    o1 = G["DD"].get(k1, 0.0) if k1 else 0.0
    o2 = G["DD"].get(k2, 0.0) if k2 else 0.0
    items = []
    for tr in P12._G["trials"]:
        if tr["ds"] != "s2s_gnd_0319":
            continue
        sub = str(tr["sub"])
        t = tr["pp"]["t"]
        lam = RU.supp_vec(tr["raw2"], tr["v2"], G["LAW"])       # ★ p23 층
        if G["KR"]:
            lam = lam + RU.rise_term(tr["v2"], G["KR"], G["LAW"][2])
        th = -P.J.ahat(A, tr["raw1"], tr["v1"])
        tk = -(P.J.ahat(A, tr["raw2"], tr["v2"]) + lam)
        ppv = dict(tr["pp"], tau_h=np.interp(t - P.SD, t, th),
                   tau_k=np.interp(t - P.SD, t, tk))
        pp = P12._G["sv"](ppv, o1, o2)
        rs_i = sorted({0} | {int(i) for i in pp["starts"]})
        rs_t = [float(t[i]) for i in rs_i]
        d_ps = dict(t=t, q1=-pp["q1m"] - np.pi / 2, q2=-pp["q2m"],
                    dq1=-pp["dq1m"], dq2=-pp["dq2m"],
                    traw1=tr["raw1"], traw2=tr["raw2"],
                    grf_real=None, h_real=float("nan"))
        items.append((sub, tr, pp, rs_i, rs_t, d_ps))
    return items


def do_s2s(skip_existing=True):
    """s2s_gnd_0319 — 사이클 리셋 Mode A replay (p19 do_s2s 미러 + p23 층 + 게이트 스프링)."""
    setup()
    sd = ROOT / "s2s_gnd_0319"
    mkdirs(sd)
    P = G["P"]; mj = RU.C._W["mj"]
    model = model_flip()
    ks, kref, _ = RU.spr_resolve(model, G["SPR"])
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    dt = model.opt.timestep
    for sub, tr, pp, rs_i, rs_t, d_ps in s2s_gnd_trials():
        out = sd / "traj" / f"{sub}__A.npz"
        if skip_existing and out.exists():
            continue
        t = tr["pp"]["t"]
        hl = RU.hl_vec(tr["raw2"], tr["v2"], G["SPR"])          # ★ 게이트 스프링 h_load
        md = mj.MjData(model)
        N = int(t[-1] / dt)
        tl = np.arange(N) * dt
        L = {k: np.zeros(N) for k in ["q1", "q2", "dq1", "dq2", "sh1", "sh2",
                                      "bz", "grf"]}
        ridx = 0
        for k in range(N):
            tc = tl[k]
            if ridx < len(rs_i) and tc >= rs_t[ridx]:
                i0 = rs_i[ridx]; ridx += 1
                q2 = pp["q2m"][i0]; dq2 = pp["dq2m"][i0]
                md.qpos[:] = [pp["bz"][i0], pp["q1m"][i0], q2, -q2, q2]
                md.qvel[:] = [pp["vbz"][i0], pp["dq1m"][i0], dq2, -dq2, dq2]
                mj.mj_forward(model, md)
            c1 = float(np.interp(tc, t, pp["tau_h"]))
            c2 = float(np.interp(tc, t, pp["tau_k"]))
            md.ctrl[:] = [c1, c2]
            md.qfrc_applied[dof_knee] = (ks * (kref - float(md.qpos[iq_k]))
                                         * float(np.interp(tc, t, hl)))  # ★ 스프링
            try:
                mj.mj_step(model, md)
            except Exception:
                break
            if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
                break
            L["q1"][k] = -md.qpos[1] - np.pi / 2; L["q2"][k] = -md.qpos[2]
            L["dq1"][k] = -md.qvel[1]; L["dq2"][k] = -md.qvel[2]
            L["sh1"][k] = -c1; L["sh2"][k] = -c2     # 측정좌표 축토크 (ctrl 부호 반전)
            L["bz"][k] = md.qpos[0]
            L["grf"][k] = RU._grf_z(model, md)
        L["t"] = tl
        save_npz(out, L, l_i=0.030, ds="s2s_gnd_0319", sub=sub, mode="A",
                 h_real=float("nan"))
        print(f"npz s2s/{sub} [A]", flush=True)


def do_s2s0604(skip_existing=True):
    """26.06.04 페이로드 s2s — s2s_0604_p19 미러 + p23 러너 (base 질량 가산)."""
    setup()
    import s2s_0604 as S0
    sd = ROOT / "s2s_0604_payload"
    mkdirs(sd)
    mj = RU.C._W["mj"]
    gains = json.load(open(HERE.parent / "p18_cvt/s2s_0604_gains.json"))
    for grp, sub, load in S0.TRIALS:
        d = S0.load_0604(grp, sub)
        name = f"{grp}_{sub}"
        need = [m for m in ("CL", "A")
                if not (skip_existing and (sd / "traj" / f"{name}__{m}.npz").exists())]
        if not need:
            continue
        model = RU.build_cvt23(G["X32"], G["REF"], G["SP"], d["l_i"], G["D_DQ"])
        bid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
        model.body_mass[bid] += load                            # 페이로드 (score_0604_23 규약)
        g = gains[f"{grp}/{sub}"]
        for mode in need:
            if mode == "CL":
                L = RU.cl_run23_log(model, True, d["l_i"], d, g, True, False,
                                    G["A"], G["TM"], [1, 1, 1, 1], G["LAW"],
                                    c_cvt=G["C_CVT"], o1=0.0, o2=0.0,
                                    spr=G["SPR"], k_rise=G["KR"])
            else:
                L = RU.a_full23_log(model, True, d["l_i"], d, G["LAW"], 0.0, 0.0,
                                    c_cvt=G["C_CVT"], spr=G["SPR"], k_rise=G["KR"])
            if L is None:
                print(f"CRASH {name} [{mode}]", flush=True)
                continue
            save_npz(sd / "traj" / f"{name}__{mode}.npz", L, l_i=d["l_i"],
                     ds=f"s2s_0604_{grp}", sub=sub, mode=mode, h_real=float("nan"))
            print(f"npz {name} [{mode}] load={load}kg", flush=True)


def stage_sim():
    res = do_jumps()
    do_s2s()
    do_s2s0604()
    crashes = [r for r in res if r[3] == "CRASH"]
    print(f"SIM DONE — jumps {len(res)} runs, crash {len(crashes)}: {crashes}", flush=True)
    return not crashes


# ══════════════════ 스테이지 check — MANDATORY 교차검증 ══════════════════
def stage_check():
    setup()
    ref = safe.read_json(REF_JSON)
    A = G["A"]
    lines = []
    ok_all = True
    # ① CL: npz 재계산 τ-갭 vs eval_p23 summary
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        f = ROOT / DSDIR[ds] / "traj" / f"{sub}__CL.npz"
        z = np.load(f, allow_pickle=True)
        L = {k: z[k] for k in ("t", "sh1", "sh2", "q2")}
        g, q2r = R19.gap_v3(L, d, A, m)
        rows.append(dict(ds=ds, sub=sub, g=min(g, 2.0), q2=q2r))
    s = R19.summarize(rows)
    lines.append("── ① CL τ-갭: npz 재계산 vs eval_p23 (tol ±0.2%p) ──")
    cl_out = {}
    for ds in ("jump_0324", "jump_0424", "jump_0429", "jump_0602",
               "jump_position_0421"):
        got = s[ds][0]; want = float(ref["cl_summary"][ds][0])
        ok = abs(got - want) <= CL_TOL
        ok_all &= ok
        cl_out[ds] = dict(npz=got, judge=want, ok=bool(ok))
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {ds:22s} npz {got * 100:6.2f}% "
                     f"vs judge {want * 100:6.2f}% (Δ {abs(got - want) * 100:.3f}%p)")
    got = s["FIT"][0]; want = float(ref["fit"])
    ok = abs(got - want) <= CL_TOL
    ok_all &= ok
    cl_out["FIT"] = dict(npz=got, judge=want, ok=bool(ok))
    lines.append(f"[{'PASS' if ok else 'FAIL'}] {'FIT':22s} npz {got * 100:6.2f}% "
                 f"vs judge {want * 100:6.2f}%")
    # ② A-재생: npz 재계산 세션 dq2 RMSE vs evaluate() OLDQ
    lines.append("── ② A 재생 dq2 RMSE: npz 재계산 vs evaluate() OLDQ (tol ±0.02) ──")
    oldq_out = {}
    for sess in E.OLDQ_SESS:
        vals = []
        for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
            if ds != sess:
                continue
            f = ROOT / DSDIR[ds] / "traj" / f"{sub}__A.npz"
            z = np.load(f, allow_pickle=True)
            t = d["t"]
            mm = t <= t[-1]
            rmse = float(np.sqrt(np.mean(
                (np.interp(t, z["t"], z["dq2"])[mm] - d["dq2"][mm]) ** 2)))
            vals.append(rmse)
        got = float(np.mean(vals)); want = float(ref["oldq"][sess])
        ok = abs(got - want) <= OLDQ_TOL
        ok_all &= ok
        oldq_out[sess] = dict(npz=got, judge=want, ok=bool(ok), n=len(vals))
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {sess:22s} npz {got:6.3f} "
                     f"vs judge {want:6.3f} (Δ {abs(got - want):.4f})")
    verdict = "PASS" if ok_all else "FAIL"
    lines.append(f"══ 교차검증 최종: {verdict} ══")
    print("\n".join(lines), flush=True)
    safe.atomic_json_write(RESULT_JSON, dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), verdict=verdict,
        cl=cl_out, oldq=oldq_out, lines=lines))
    return ok_all


# ══════════════════ 스테이지 figs — 교차검증 통과 후에만 ══════════════════
def bonus_d_map():
    """보너스 신규 세션 d-dict 캐시 (figs 재실행 시 lazy 로드)."""
    if "bonus_d" not in G:
        G["bonus_d"] = {}
        for ds, sub, d, *rest in RN.ff_trials():
            G["bonus_d"][(ds, str(sub))] = d
    return G["bonus_d"]


def stage_figs():
    setup()
    import s2s_0604 as S0
    # 점프 5세션 (npz에서 재생성 — regen_pngs 패턴)
    tri = {(ds, str(sub)): (d, is_cvt, ffk) for ds, sub, d, g_, dq_, ffk, m_, is_cvt, li_
           in R19.TRIALS}
    for ds, dirn in DSDIR.items():
        tj = ROOT / dirn / "traj"
        if not tj.is_dir():
            continue
        for f in sorted(tj.glob("*.npz")):
            z = np.load(f, allow_pickle=True)
            L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                                   "bz", "grf")}
            sub = str(z["sub"]); mode = str(z["mode"])
            l_i = float(z["l_i"]); hr = float(z["h_real"])
            key = (ds, sub)
            if key in tri:
                d, is_cvt, ffk = tri[key]
                if is_cvt:
                    o1, o2 = G["QOFF_CL429"] if mode == "CL" else E.QOFF_A429
                elif ffk:
                    o1, o2 = 0.0, 0.0
                else:
                    o1, o2 = offsets_nocvt(ds)
                note = (" · α=1 + FF(hip+knee) 주입 (held-out 규약)" if ffk
                        else " · 실효게인 α+클립 반영")
            else:                                # 보너스 신규 세션 (o=0, α=1 규약)
                d = bonus_d_map()[(ds, sub)]
                o1 = o2 = 0.0
                note = " · α=1 + FF 주입 (신규 세션 — 적합 커맨드층 없음)"
            make_fig(ds, sub, d, L, mode, l_i, o1, o2, hr,
                     ROOT / dirn / "png" / (f.stem + ".png"), cl_note=note)
            print("png", dirn, f.stem, flush=True)
    # s2s_gnd_0319 (의사-d)
    for sub, tr, pp, rs_i, rs_t, d_ps in s2s_gnd_trials():
        f = ROOT / "s2s_gnd_0319" / "traj" / f"{sub}__A.npz"
        z = np.load(f, allow_pickle=True)
        L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                               "bz", "grf")}
        make_fig("s2s_gnd_0319 (mshoot 창 리셋 replay)", sub, d_ps, L, "A",
                 0.030, 0.0, 0.0, float("nan"),
                 ROOT / "s2s_gnd_0319" / "png" / f"{sub}__A.png")
        print("png s2s_gnd", sub, flush=True)
    # s2s_0604
    for f in sorted((ROOT / "s2s_0604_payload" / "traj").glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                               "bz", "grf")}
        ds = str(z["ds"]); sub = str(z["sub"]); mode = str(z["mode"])
        grp = ds.replace("s2s_0604_", "")
        d = S0.load_0604(grp, sub)
        make_fig(f"s2s_0604/{grp}", sub, d, L, mode, float(z["l_i"]), 0.0, 0.0,
                 float("nan"), ROOT / "s2s_0604_payload" / "png" / (f.stem + ".png"),
                 cl_note=" · 회귀 실효게인 (P18c)")
        print("png s2s_0604", f.stem, flush=True)


# ══════════════════ 스테이지 gifs ══════════════════
def stage_gifs():
    setup()
    P = G["P"]
    for sd in sorted(ROOT.iterdir()):
        if not (sd / "traj").is_dir():
            continue
        for f in sorted((sd / "traj").glob("*.npz")):
            out = sd / "gif" / (f.stem + ".gif")
            if out.exists():
                continue
            z = np.load(f, allow_pickle=True)
            L = {k: z[k] for k in ("t", "q1", "q2", "bz")}
            ds = str(z["ds"]); sub = str(z["sub"]); mode = str(z["mode"])
            if ds.startswith("s2s"):
                t_end = float(z["t"][-1]) - 0.35
            else:
                mask = z["t"] >= 0
                t_end = float(z["t"][mask][-1]) - P.J.T_AFTER
            lz = 0.7 if ds == "s2s_air_0319" else 0.3   # 용접(공중) 세션은 카메라 상향
            try:
                render_gif(L, float(z["l_i"]), f"{MODEL_TAG} {ds}/{sub} [{mode}]",
                           float(z["h_real"]), out, t_end, lookat_z=lz)
                print(f"gif {ds}/{sub} [{mode}]", flush=True)
            except Exception as e:
                print(f"GIF FAIL {ds}/{sub} [{mode}]: {e}", flush=True)


# ══════════════════ 스테이지 bonus — 신규 세션 (0422/0319tau/공중) ══════════════════
def stage_bonus(skip_existing=True):
    setup()
    ref = safe.read_json(REF_JSON) if REF_JSON.exists() else None
    ffhip = EV.anchors()[2]
    A = G["A"]
    bonus_d_map()
    # 점프 FF 2세션 — cl_ff23/oldq_ff23 배선 (alphas=1, o=0)
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in RN.ff_trials():
        sd = ROOT / DSDIR[ds]
        mkdirs(sd)
        hr = float(d.get("h_real", float("nan")))
        for mode in ("CL", "A"):
            out = sd / "traj" / f"{sub}__{mode}.npz"
            if skip_existing and out.exists():
                continue
            if mode == "CL":
                L = RU.cl_run23_log(model_flip(), False, l_i, d, gains, dqon, ffk,
                                    A, G["TM"], [1, 1, 1, 1], G["LAW"], c_cvt=0.0,
                                    o1=0.0, o2=0.0, ff_hip=ffhip, spr=G["SPR"],
                                    k_rise=G["KR"])
            else:
                L = RU.a_full23_log(model_flip(), False, l_i, d, G["LAW"], 0.0, 0.0,
                                    c_cvt=0.0, spr=G["SPR"], k_rise=G["KR"])
            if L is None:
                print(f"CRASH {ds}/{sub} [{mode}]", flush=True)
                continue
            save_npz(out, L, l_i=l_i, ds=ds, sub=sub, mode=mode, h_real=hr)
            print(f"npz {ds}/{sub} [{mode}]", flush=True)
    # 공중 s2s 14사이클 — air23 배선 (용접 베이스, A만)
    sd = ROOT / "s2s_air_0319"
    mkdirs(sd)
    model_w = RU.build_weld23(G["X32"], G["REF"], G["SP"], G["D_DQ"])
    cycles, _ = RN.air_cycles()
    for i, dcy in enumerate(cycles):
        sub = f"cyc{i + 1:02d}"
        G["bonus_air"] = G.get("bonus_air", {})
        G["bonus_air"][sub] = dcy
        out = sd / "traj" / f"{sub}__A.npz"
        if skip_existing and out.exists():
            continue
        L = RU.air_cycle23_log(model_w, dcy, G["LAW"], spr=G["SPR"], k_rise=G["KR"])
        if L is None:
            print(f"CRASH air/{sub}", flush=True)
            continue
        save_npz(out, L, l_i=0.030, ds="s2s_air_0319", sub=sub, mode="A",
                 h_real=float("nan"))
        print(f"npz air/{sub} [A]", flush=True)
    # 소프트 교차검증 (신규 성분 — evaluate() CLFF/OLDQFF/AIR 대비)
    if ref is not None:
        print("── 보너스 소프트 검증 (npz vs evaluate 신규 성분) ──", flush=True)
        for sess in RN.FF_SESS:
            gs, rs = [], []
            for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in RN.ff_trials():
                if ds != sess:
                    continue
                zc = np.load(ROOT / DSDIR[ds] / "traj" / f"{sub}__CL.npz",
                             allow_pickle=True)
                g, _ = R19.gap_v3({k: zc[k] for k in ("t", "sh1", "sh2", "q2")},
                                  d, A, m)
                gs.append(min(g, 2.0))
                za = np.load(ROOT / DSDIR[ds] / "traj" / f"{sub}__A.npz",
                             allow_pickle=True)
                t = d["t"]; mm = t <= t[-1]
                rs.append(float(np.sqrt(np.mean(
                    (np.interp(t, za["t"], za["dq2"])[mm] - d["dq2"][mm]) ** 2))))
            print(f"  CLFF[{sess}] npz {np.mean(gs):.4f} vs judge "
                  f"{ref['clff'][sess]:.4f} | OLDQFF npz {np.mean(rs):.3f} vs "
                  f"{ref['oldqff'][sess]:.3f}", flush=True)
        scs = []
        for i in range(len(cycles)):
            sub = f"cyc{i + 1:02d}"
            z = np.load(sd / "traj" / f"{sub}__A.npz", allow_pickle=True)
            dcy = cycles[i]; t = dcy["t"]
            rq = float(np.sqrt(np.mean((np.interp(t, z["t"], z["q2"]) - dcy["q2"]) ** 2)))
            rdq = float(np.sqrt(np.mean((np.interp(t, z["t"], z["dq2"]) - dcy["dq2"]) ** 2)))
            scs.append(rq + RN.AIR_W_DQ * rdq)
        print(f"  AIR npz {np.mean(scs):.4f} vs judge {ref['air']:.4f}", flush=True)
    # 보너스 그림
    for ds in ("jump_0422", "jump_0319tau"):
        for f in sorted((ROOT / DSDIR[ds] / "traj").glob("*.npz")):
            z = np.load(f, allow_pickle=True)
            L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                                   "bz", "grf")}
            sub = str(z["sub"])
            make_fig(ds, sub, bonus_d_map()[(ds, sub)], L, str(z["mode"]),
                     float(z["l_i"]), 0.0, 0.0, float(z["h_real"]),
                     ROOT / DSDIR[ds] / "png" / (f.stem + ".png"),
                     cl_note=" · α=1 + FF 주입 (신규 세션 — 적합 커맨드층 없음)")
            print("png", ds, f.stem, flush=True)
    for f in sorted((ROOT / "s2s_air_0319" / "traj").glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        L = {k: z[k] for k in ("t", "q1", "q2", "dq1", "dq2", "sh1", "sh2",
                               "bz", "grf")}
        sub = str(z["sub"])
        make_fig("s2s_air_0319 (용접 베이스 재생)", sub, G["bonus_air"][sub], L,
                 "A", 0.030, 0.0, 0.0, float("nan"),
                 ROOT / "s2s_air_0319" / "png" / (f.stem + ".png"))
        print("png air", sub, flush=True)


# ══════════════════ 스테이지 index ══════════════════
def stage_index():
    ref = safe.read_json(REF_JSON)
    res = safe.read_json(RESULT_JSON)
    n = {}
    for sd in sorted(ROOT.iterdir()):
        if (sd / "traj").is_dir():
            n[sd.name] = (len(list((sd / "png").glob("*.png"))),
                          len(list((sd / "gif").glob("*.gif"))),
                          len(list((sd / "traj").glob("*.npz"))))
    v = CAND["x"]
    cl = res["cl"]; oq = res["oldq"]
    txt = f"""# g22_p23a_all_results — P23 최종 후보 p23a 전 데이터 결과 ({time.strftime('%Y-%m-%d')})

**모델**: p23a (`code/goal22/p23_veins/fourbar_p23a_candidate.json`, judge p23, NSGA-II v6 gen80 min-F2)
= **측정 유지-지지 법칙**이 P19의 pre30(상수 프리로드)+준정적층을 세대 교체 + 구조 2수술 (Phase 4b/4c).

## 구조 3층 (측정 법칙 수식)

1. **유지-지지 법칙 (P23-2 측정 적합)** — 구 pre30/c_qs 자리를 대체, 전 세션 보편:
   `supp(τ̂₂, dq₂) = A + min(B·x + C·x², 3.5)·g(dq₂; v0)`,  `x = min(|τ̂₂|, x_pk)`, `g(v;v0)=1/(1+(v/v0)²)`
   (A={float(v[15]):.4f}, B={float(v[19]):.4f}, C=−0.02814 고정, v0={float(v[16]):.3f})
2. **부하연동 인루프 스프링 (Phase 4b, spring_gated)** — XML 상시 스프링 무장해제 후
   `τ_spr = k·(k_ref − q_knee)·h`, `h = x/(x+T_SPR)`, x=|ahat 무릎토크|, T_SPR={float(v[22]):.3f} Nm
   (k={float(v[0]):.4f}, ref={float(v[1]):.4f} — springref 도(°)-해석 유령 규명 후 컴파일값 사용)
3. **게이트 너머 상승항 (Phase 4c, rise_gated)** — `rise = K_RISE·dq₂·(1−g(dq₂; v0))`, K_RISE={float(v[21]):.4f}
   (Phase 3 측정 λ₂≈+0.216·dq₂ CI 내). + CVT 가지 전달손실 C_CVT={float(v[20]):.4f} (coulomb형).
플랜트 동결 3축 (M_c/I_ca/dz_ca)은 P19 값으로 강제 (apply_freeze — 심판 규약).

## P19 / p22b 대비 (동일 규격 그래프는 두 아카이브와 파일명 1:1 대응)

| 지표 | P19 | p22b | **p23a** |
|---|---|---|---|
| CL τ-갭 FIT / held-out | 38.1% / 35.7% | 37.0% / 34.5% | **{ref['fit'] * 100:.1f}% / {ref['heldout'] * 100:.1f}%** |
| A 재생 dq2 (0424 / 0602) | 1.89 / 1.26 | 1.72 / 1.18 | **{oq['jump_0424']['judge']:.2f} / {oq['jump_0602']['judge']:.2f}** |
| A 재생 dq2 (0429 CVT) | 3.31 | 3.45 | **{oq['jump_0429']['judge']:.2f}** (+31% vs P19 — 정직: 법칙 구조의 비용) |
| A 재생 dq2 (0324 held-out, 진단) | 2.93 | 3.84 | **{CAND['heldout']['replay_diag']:.2f}** |
| 공중 s2s AIR (q2+0.1·dq2, P19비) | 1.0 | — | **{ref['norm']['AIR']:.2f}× (−{(1 - ref['norm']['AIR']) * 100:.0f}%)** |
| s2s_gnd 창 점수 (Ŝ2S, P19비) | 1.0 | — | **{ref['norm']['S2S']:.2f}× (−{(1 - ref['norm']['S2S']) * 100:.0f}%)** |
| J_v6 (v6 종합, P19=1) | 1.0 | — | **{ref['J_v6']:.3f}** (게이트 {'전부 PASS' if CAND['v6_gates']['pass']['ALL'] else '일부 FAIL'}) |

## 교차검증 (침묵실패 방역 — npz 재계산 vs 심판 신선값): **{res['verdict']}**

| 검증 | 세션 | npz 재계산 | 심판 | 판정 |
|---|---|---|---|---|
""" + "\n".join(
        f"| CL τ-갭 (±0.2%p) | {ds} | {cl[ds]['npz'] * 100:.2f}% | {cl[ds]['judge'] * 100:.2f}% | "
        f"{'PASS' if cl[ds]['ok'] else 'FAIL'} |"
        for ds in ("jump_0324", "jump_0424", "jump_0429", "jump_0602",
                   "jump_position_0421", "FIT")) + "\n" + "\n".join(
        f"| A dq2 RMSE (±0.02) | {ds} | {oq[ds]['npz']:.3f} | {oq[ds]['judge']:.3f} | "
        f"{'PASS' if oq[ds]['ok'] else 'FAIL'} |"
        for ds in ("jump_0424", "jump_0602", "jump_0429")) + f"""

## 1:1 비교 안내

폴더 구조·파일명·그래프 규격(png_v2 = `bench/render_kit.fig_trial_std`)·GIF(goal18_CANONICAL+표준 오버레이)
모두 g22_p19_all_results / g22_p22b_all_results와 동일 — 같은 상대경로 파일을 나란히 열면 모델만 다른 비교가 됨.
파일명 `<트라이얼>__<모드>.{{png,gif,npz}}`, 모드 **CL**=폐루프 PD(커맨드층 α·클립·tm) / **A**=실측 τ replay.

| 폴더 | 파일 수 (png/gif/npz) | 비고 |
|---|---|---|
""" + "\n".join(
        f"| `{k}/` | {a}/{b}/{c} |" + (
            " **held-out** (fit 미포함) |" if k == "jump_0324_heldout" else
            " CVT l_i=25.08mm |" if k == "jump_0429_cvt" else
            " Mode A만 (mshoot 창 리셋 replay) |" if k == "s2s_gnd_0319" else
            " 페이로드 s2s (cvt 0/2.5/5kg + no_cvt 0kg) |" if k == "s2s_0604_payload" else
            " **신규 세션** (P19/p22b 아카이브에 없음 — CL(FF)+A) |" if k.startswith("jump_03") or k == "jump_0422" else
            " **신규 세션** (공중 14사이클, 용접 베이스, A만) |" if k == "s2s_air_0319" else " |")
        for k, (a, b, c) in n.items()) + f"""

## 읽는 법 (함정 — P19 INDEX의 함정 + p23a 고유)

- **A 모드 knee τ 패널**: sim 곡선은 replay 주입 총량 = 측정 ahat + **supp(법칙)** — 실측 곡선과의
  간극이 곧 법칙 층의 크기 (P19 아카이브에서 s2s_gnd만 pre30 간극을 보이던 것과 달리, p23a는
  법칙이 전 세션 보편이라 점프 A에서도 부하 구간에 간극이 보임. CL의 sh는 종전과 동일하게
  supp 미포함 사후-ahat 명령 — τ-갭 지표 정의 불변).
- **held-out 0324 오프셋 규약 차이**: P19/p22b 아카이브는 0324에 레거시 OFFK 오프셋을 적용했지만
  p23a는 심판(eval_p23/oldq_ff23) 규약대로 **o=0** (적합 산물 미사용) — q 패널 비교 시 참고.
- 0429 CL q-오프셋 = x[17],x[18] = ({float(v[17]):+.4f}, {float(v[18]):+.4f}) rad / A = P18b 고정 (3.14°, −3.0°).
- s2s_gnd_0319의 knee τ에서 sim−real 간극 = supp(법칙) 층 (구 pre30 자리) + 게이트 스프링은 qfrc라 τ 패널 밖.
- s2s_air_0319는 용접 베이스(base z=1m 고정) — bz/GRF 패널은 상수(1.0/0). GIF 카메라만 상향.
- 신규 세션(0422/0319tau)의 CL은 α=1 + FF(hip+knee — p23_anchors 동결 프로토콜), 적합 커맨드층 없음.
- 나머지 함정 (a_hat 변환·크랭크측 knee·CL 실효게인)은 g22_p19_all_results/INDEX.md와 동일.

생성 코드: `code/goal22/p23_veins/p23a_all_results.py` (러너 = p23_v6_runners의 로그 미러 변형,
기존 함수 불변). 교차검증 원장: `p23a_crosscheck_ref.json` / `p23a_crosscheck_result.json`.
"""
    (ROOT / "INDEX.md").write_text(txt, encoding="utf-8")
    print(f"INDEX.md 저장 — 폴더 {len(n)}개, 파일 수 {n}", flush=True)


def main():
    safe.utf8_console()
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    ROOT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if stage in ("ref", "all"):
        stage_ref()
    if stage in ("sim", "all"):
        stage_sim()
    if stage in ("check", "all"):
        ok = stage_check()
        if not ok:
            print("교차검증 FAIL — png/gif 생성 중단 (침묵실패 방역)", flush=True)
            sys.exit(1)
    if stage in ("figs", "all"):
        if stage == "figs" and not RESULT_JSON.exists():
            sys.exit("check 먼저 (RESULT_JSON 없음)")
        stage_figs()
    if stage in ("bonus", "all"):
        stage_bonus()
    if stage in ("gifs", "all"):
        stage_gifs()
    if stage in ("index", "all"):
        stage_index()
    print(f"DONE [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
