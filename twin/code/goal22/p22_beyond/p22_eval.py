# -*- coding: utf-8 -*-
"""p22_eval — 마라톤 P22 단일 후보 평가기 (지표 v5, MARATHON_p22.md 준거).

성분:
  1) p21_cma.eval_parts 7성분 (CL, DQ, JW2, J6J, J6C, S2S, O6) — winit 후 fix0421 1회 적용
  2) OLDQ: Mode A 통짜 재생 dq2 RMSE — jump_0424/jump_0602 (l_i=30 flip) + jump_0429 (CVT)
  3) H:    같은 점프 trial의 재생 점프높이 |h_sim/h_real − 1| 평균 (h_sim = t>0 base z 최대,
           절대 bz apex vs h_real 직접 비교 — repo 규약)
  J_v5 = 0.30·CLτ̂ + 0.15·CLdq̂ + 0.10·JŴ02 + 0.10·JŴ06 + 0.075·Ŝ2S + 0.025·Ô6
         + 0.15·ÔLdq + 0.10·Ĥ   (성분̂ = 성분/P19_rebased 앵커, JŴ06 = 0.5·J6Ĵ + 0.5·J6Ĉ,
         ÔLdq = 세션별 정규화 후 평균)

통짜 재생 규약 (golden = CVT/jump_opt/g22_p19_all_results 를 만든
p19_all_results.run_any mode-A 그대로 — 앵커 검증으로 강제):
  - settle: t<0 동안 S.SETTLE_KP/KD PD (목표 = 측정 q(0)+offset), 커맨드는 ahat 경유
  - 주입: tau = ahat(A_PAPER, traw, dq) 를 t−P.SD 로 interp (무릎은 +lam_vec(c_qs, v0)),
          기록 끝(tc > t[-1]) 이후 0 (a429_full 규약)
  - pre30(무변속 전용, v[19])은 ctrl 단에서 상시 가산 (settle 포함 — golden run_any 규약)
  - q-오프셋: 무변속 = OFFK per-session (x32 dict, eval_stack20 규약; 0602는 항목 없음=0),
              0429 = QOFF_A429 (3.14°, −3.0°) 고정 (Mode A 프로토콜 = P18b 값)
  - 초기자세: 무변속 [1, −q1(0)−π/2, −q2(0), −sq2, sq2] / 0429 qpos_from_crank + 발높이 보정
  - RMSE: t ≤ t[-1] 전 구간, 측정 dq2 대비 (측정좌표 dq2_sim = −qvel[2])

main(): P19 앵커 벡터(x19) 평가 → p22_eval_anchors.json 저장.
골든 검증: 7성분 vs p22_rebase.json(after) ±1% + OLDQ 세션 앵커 vs
{0424:1.89, 0602:1.26, 0429:3.31} ±0.15 — 불일치 시 저장 없이 FAIL 종료.
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
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import p21_cma as C
import p22_fix0421 as FX
import safe

ANCHOR_PATH = HERE / "p22_eval_anchors.json"
REBASE_PATH = HERE / "p22_rebase.json"
QOFF_A429 = (3.14 * np.pi / 180, -3.0 * np.pi / 180)   # == p19_all_results.QOFF_A429
OLDQ_SESS = ("jump_0424", "jump_0602", "jump_0429")
GOLDEN_OLDQ = {"jump_0424": 1.89, "jump_0602": 1.26, "jump_0429": 3.31}
GOLDEN_TOL = 0.15
W_V5 = dict(CL=0.30, DQ=0.15, JW2=0.10, JW6=0.10, S2S=0.075, O6=0.025,
            OLDQ=0.15, H=0.10)

_INIT = {"winit": False, "fix": False}
_ANCH = {"d": None}


def ensure_init():
    """judge winit 1회 + fix0421 1회 (반드시 winit 이후) — 철칙: 순서 불변."""
    if not _INIT["winit"]:
        C.winit_worker(dict(CL=1, DQ=1, JW2=1, J6J=1, J6C=1, S2S=1, O6=1, raw=True))
        _INIT["winit"] = True
    if not _INIT["fix"]:
        FX.apply(C._W["P"], verbose=False)
        _INIT["fix"] = True


def x19_vec():
    """P19 앵커 벡터 — p22_rebase.py의 x19 구성 그대로 (v4/v5 정규화 기준점)."""
    import p19_adapter as AD
    C19 = AD.load_candidate(HERE.parent / "p19_jump/fourbar_p19_candidate.json")
    v19 = np.array(C19["x"], float)
    x19 = np.array([v19[0], v19[1], v19[3], v19[4], v19[5], v19[6], v19[7], v19[8],
                    v19[9], v19[10], v19[11], v19[12], v19[13], v19[14], v19[15],
                    0.0, 6.0, v19[16], v19[17], v19[2]])
    return np.clip(x19, C.LO + 1e-9, C.HI - 1e-9)


def h_real_of(ds, sub):
    """무변속 trial의 h_real — P12 trials에서 (ds, sub) 매칭 (p19_all_results 규약)."""
    for tr in C._W["P12"]._G["trials"]:
        if tr["ds"] == ds and str(tr.get("sub", "")) == str(sub):
            hr = tr.get("h_real", float("nan"))
            return float(hr) if hr == hr else float("nan")
    return float("nan")


def a_full(model, is_cvt, l_i, d, v, o1, o2, pre30):
    """통짜 Mode A 재생 1 trial → (dq2 RMSE, h_sim) 또는 None(발산).

    골든 규약(run_any mode-A) + a429_full의 t1/t2 구성(lam 포함, 기록 끝 이후 0).
    """
    P = C._W["P"]; mj = C._W["mj"]; S = P.J._P["S"]
    t = d["t"]
    lam = C.lam_vec(d["traw2"], d["dq2"], v[15], v[16])
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + lam)
    q1_0 = float(d["q1"][0]) + o1
    q2_0 = float(d["q2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    if is_cvt:
        from cvt_core import qpos_from_crank
        md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    else:
        md.qpos[:] = [1.0, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    dq2s = np.zeros(N); bzs = np.zeros(N)
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
            v1c = -md.qvel[1]; v2c = -md.qvel[2]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            if tc > t[-1]:
                s1 = s2 = 0.0
        md.ctrl[:] = [-s1, -(s2 + pre30)]
        try:
            mj.mj_step(model, md)
        except Exception:
            return None
        if abs(md.qpos[0]) > 5 or not np.isfinite(md.qpos).all():
            return None
        dq2s[k] = -md.qvel[2]; bzs[k] = md.qpos[0]
    m = t <= t[-1]
    rmse = float(np.sqrt(np.mean((np.interp(t, tl, dq2s)[m] - d["dq2"][m]) ** 2)))
    h_sim = float(bzs[tl > 0].max()) if (tl > 0).any() else float("nan")
    return rmse, h_sim


def oldq_h(v, verbose=False):
    """OLDQ(세션별 통짜 재생 dq2 RMSE 평균) + H(|h_sim/h_real−1| 점프 trial 평균)."""
    P, R = C._W["P"], C._W["R"]
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model_f, _ = P.build_flip(x32, v[1], sp)
    model_c, _ = P.build_cvt(x32, v[1], sp, 0.02508)
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    rows, herr = [], []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        if ds not in OLDQ_SESS:
            continue
        if is_cvt:
            o1, o2 = QOFF_A429
            res = a_full(model_c, True, d["l_i"], d, v, o1, o2, pre30=0.0)
            hr = float(d.get("h_real", float("nan")))
        else:
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            res = a_full(model_f, False, l_i, d, v, o1, o2, pre30=float(v[19]))
            hr = h_real_of(ds, sub)
        if res is None:
            rows.append(dict(ds=ds, sub=str(sub), rmse=9.9,
                             h_sim=float("nan"), h_real=hr))
            herr.append(1.0)          # 발산 처벌 (a429_full의 crash 반환 h=2.0 상당)
            if verbose:
                print(f"  OLDQ {ds}/{sub}: CRASH", flush=True)
            continue
        rmse, h_sim = res
        rows.append(dict(ds=ds, sub=str(sub), rmse=rmse, h_sim=h_sim, h_real=hr))
        if np.isfinite(hr) and np.isfinite(h_sim):
            herr.append(abs(h_sim / hr - 1.0))
        if verbose:
            print(f"  OLDQ {ds}/{sub}: dq2 RMSE {rmse:.3f}  h_sim {h_sim:.3f} "
                  f"h_real {hr:.3f}", flush=True)
    sess = {ds: float(np.mean([r["rmse"] for r in rows if r["ds"] == ds]))
            for ds in OLDQ_SESS}
    H = float(np.mean(herr)) if herr else float("nan")
    return sess, H, rows


def load_anchors():
    if _ANCH["d"] is None and ANCHOR_PATH.exists():
        _ANCH["d"] = safe.read_json(ANCHOR_PATH)
    return _ANCH["d"]


def j_v5(comp, anch):
    """지표 v5 가중합 — MARATHON_p22.md 정의 (JŴ06 = 0.5·J6Ĵ + 0.5·J6Ĉ)."""
    jw6 = 0.5 * comp["J6J"] / anch["J6J"] + 0.5 * comp["J6C"] / anch["J6C"]
    oldq = float(np.mean([comp["OLDQ"][s] / anch["OLDQ"][s] for s in OLDQ_SESS]))
    return float(W_V5["CL"] * comp["CL"] / anch["CL"]
                 + W_V5["DQ"] * comp["DQ"] / anch["DQ"]
                 + W_V5["JW2"] * comp["JW2"] / anch["JW2"]
                 + W_V5["JW6"] * jw6
                 + W_V5["S2S"] * comp["S2S"] / anch["S2S"]
                 + W_V5["O6"] * comp["O6"] / anch["O6"]
                 + W_V5["OLDQ"] * oldq
                 + W_V5["H"] * comp["H"] / anch["H"])


def evaluate(v20, anchors=None, verbose=False):
    """단일 후보 평가 → dict(7성분 + OLDQ 세션별/trial별 + H + J_v5).

    J_v5는 anchors(또는 p22_eval_anchors.json)가 있을 때만 채움 (없으면 None).
    """
    ensure_init()
    v = np.asarray(v20, float)
    if verbose:
        print("eval_parts (CL/DQ/JW2/JW6/S2S/O6) ...", flush=True)
    jcl, jdq, jw02, (j6j, j6c), s2s, o6 = C.eval_parts(v)
    comp = dict(CL=float(jcl), DQ=float(jdq), JW2=float(jw02), J6J=float(j6j),
                J6C=float(j6c), S2S=float(s2s), O6=float(o6))
    if verbose:
        print("OLDQ/H 통짜 재생 (25 trials) ...", flush=True)
    sess, H, rows = oldq_h(v, verbose=verbose)
    comp["OLDQ"] = sess
    comp["OLDQ_trials"] = rows
    comp["H"] = H
    anch = anchors if anchors is not None else load_anchors()
    comp["J_v5"] = j_v5(comp, anch) if anch else None
    return comp


# ══════════ main: P19 앵커 산출 + 골든 검증 ══════════
def _chk(name, got, want, tol_rel=None, tol_abs=None):
    if tol_rel is not None:
        ok = abs(got / want - 1.0) <= tol_rel
        detail = f"got {got:.4f} vs ref {want:.4f} (Δ {100 * (got / want - 1):+.2f}%)"
    else:
        ok = abs(got - want) <= tol_abs
        detail = f"got {got:.3f} vs ref {want:.3f} (Δ {got - want:+.3f}, tol ±{tol_abs})"
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    return ok


def main():
    safe.utf8_console() if hasattr(safe, "utf8_console") else None
    t0 = time.time()
    print("=== p22_eval — P19 앵커 산출 (P19_rebased, fix0421 적용) ===", flush=True)
    ensure_init()
    print(f"winit+fix0421 done [{time.time() - t0:.0f}s]", flush=True)
    x19 = x19_vec()
    comp = evaluate(x19, anchors=False, verbose=True)   # anchors=False → J_v5 스킵
    comp["J_v5"] = None

    print("\n=== 앵커 성분표 (P19_rebased) ===", flush=True)
    for k in ("CL", "DQ", "JW2", "J6J", "J6C", "S2S", "O6"):
        print(f"  {k:5s} = {comp[k]:.4f}", flush=True)
    for s in OLDQ_SESS:
        print(f"  OLDQ[{s}] = {comp['OLDQ'][s]:.3f}", flush=True)
    print(f"  H     = {comp['H']:.4f}", flush=True)

    print("\n=== 골든 검증 ===", flush=True)
    rb = safe.read_json(REBASE_PATH)["after"]
    ok = True
    # ① 7성분 vs p22_rebase.json(after) — 결정론이므로 ±1%는 사실상 동일성 체크
    for k in ("CL", "DQ", "JW2", "J6J", "J6C", "S2S", "O6"):
        ok &= _chk(f"rebase {k}", comp[k], float(rb[k]), tol_rel=0.01)
    # ② OLDQ 세션 앵커 vs 아카이브 npz 전수값 (±0.15)
    for s in OLDQ_SESS:
        ok &= _chk(f"OLDQ {s}", comp["OLDQ"][s], GOLDEN_OLDQ[s], tol_abs=GOLDEN_TOL)
    if not ok:
        print("\nVALIDATION FAILED — 앵커 저장하지 않음 (규약 차이를 찾아 고칠 것; "
              "앵커를 러너에 맞춰 재정의 금지)", flush=True)
        sys.exit(1)

    anch = dict(CL=comp["CL"], DQ=comp["DQ"], JW2=comp["JW2"], J6J=comp["J6J"],
                J6C=comp["J6C"], S2S=comp["S2S"], O6=comp["O6"],
                OLDQ=comp["OLDQ"], H=comp["H"],
                OLDQ_trials=comp["OLDQ_trials"],
                weights=W_V5, golden_oldq=GOLDEN_OLDQ,
                note="P19_rebased anchors (fix0421 적용, x19=p22_rebase 구성). "
                     "J_v5(P19)=1.0 by definition.")
    jv5_self = j_v5(comp, anch)
    assert abs(jv5_self - 1.0) < 1e-9, f"J_v5(P19) != 1.0: {jv5_self}"
    print(f"\nJ_v5(P19) self-check = {jv5_self:.6f} (= 1.0 by definition)", flush=True)
    safe.atomic_json_write(ANCHOR_PATH, anch)
    print(f"saved {ANCHOR_PATH.name} [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
