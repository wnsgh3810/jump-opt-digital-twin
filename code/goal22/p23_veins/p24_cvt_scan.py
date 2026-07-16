# -*- coding: utf-8 -*-
"""p24_cvt_scan — P24 preflight card 2: C_CVT 캡 너머 스캔 + 에너지 감사 + K_RISE 상호작용.

평가 전용 (기존 파일 무수정·후보 무갱신·커밋 없음). evaluate()는 경계 클립을 하지
않으므로 (apply_freeze는 동결 3축만 강제) 탐색 케이지 밖 C_CVT를 그대로 평가한다 —
out-of-cage 정직 명기: 여기 수치는 '캡을 풀면 어디까지 가는가'의 관측이지 재적합이 아니다.

Task 1: C_CVT ∈ {0.3955(=p23a 재현), 0.4, 0.6, 0.8, 1.0, 1.3} × K_RISE=0.1881 → 전 v6 성분표
        + per-session CL (p19_adapter.eval_p23 — held-out 포함).
Task 2: best C_CVT에서 0429 trial별 소산 에너지 (a_full23 미러 + P22 exp_cvtloss 축적 규약)
        vs P22 원장 surplus_res (2.38→9.74 J, mean 5.60).
Task 3: {0.3955, best C_CVT} × K_RISE {0.1881, 0.10, 0.0} (K=0.1881 케이스는 Task 1 재사용).
결과: p24_cvt_scan_result.json + stdout 표.
"""
import os
os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "p22_beyond"))
sys.path.insert(0, str(HERE.parent / "p20_rise"))
sys.path.insert(0, str(HERE.parent / "p19_jump"))
sys.path.insert(0, str(HERE.parent.parent / "bench"))

import safe
safe.utf8_console()

import p23_v6_eval as V6            # noqa: E402
import p23_v6_runners as RU         # noqa: E402
import p22_eval as E                # noqa: E402
import p21_cma as C                 # noqa: E402
import p19_run as R19               # noqa: E402
import p19_adapter as AD            # noqa: E402

assert RU.SPRING_GATED and RU.RISE_GATED, "구조 플래그 미적용 — env 순서 확인"

CAND = safe.read_json(HERE / "fourbar_p23a_candidate.json")
X0 = np.asarray(CAND["x"], float)
IC, IK = 20, 21                      # C_CVT / K_RISE 슬롯
C0, K0 = float(X0[IC]), float(X0[IK])
LEDGER = safe.read_json(HERE.parent / "p22_beyond" / "p22_probe_0429_energy_result.json")
LED429 = {r["sub"]: r for r in LEDGER["rows"] if r["ds"] == "jump_0429"}
OUT = HERE / "p24_cvt_scan_result.json"


def v_of(c_cvt, k_rise):
    v = X0.copy()
    v[IC] = float(c_cvt)
    v[IK] = float(k_rise)
    return v


def cl_sessions(v):
    """p19_adapter.eval_p23 — per-session CL τ-갭 (held-out 0324 포함)."""
    cand = dict(names=list(CAND["names"]), x=[float(a) for a in v],
                structure=dict(CAND.get("structure", {})))
    r = AD.eval_p23(cand)
    return dict(fit=float(r["fit"]), heldout=float(r["heldout"]),
                sess={k: float(val[0]) for k, val in r["summary"].items()})


def eval_config(c_cvt, k_rise):
    t0 = time.time()
    v = v_of(c_cvt, k_rise)
    comp = V6.evaluate(v, verbose=False, keep_rows=True)
    cl = cl_sessions(v)
    rows429 = [r for r in comp.get("OLDQ_trials", []) if r["ds"] == "jump_0429"]
    out = dict(
        c_cvt=float(c_cvt), k_rise=float(k_rise),
        J_v5=comp["J_v5"], J_v6=comp["J_v6"],
        OLDQ=comp["OLDQ"], H=comp["H"], O6=comp["O6"], J6C=comp["J6C"],
        S2S=comp["S2S"], JW2=comp["JW2"], J6J=comp["J6J"], DQ=comp["DQ"],
        CLFF=comp["CLFF"], OLDQFF=comp["OLDQFF"], AIR=comp["AIR"],
        CL_fit=cl["fit"], CL_heldout=cl["heldout"], CL_sess=cl["sess"],
        norm=comp["norm"], gates=comp["gates"],
        rows429=[dict(sub=r["sub"], rmse=float(r["rmse"]),
                      h_sim=float(r["h_sim"]) if np.isfinite(r["h_sim"]) else None,
                      h_real=float(r["h_real"])) for r in rows429],
        t_s=float(time.time() - t0))
    return out


def print_config(r):
    n = r["norm"]
    print(f"\n──── C_CVT={r['c_cvt']:.4f}  K_RISE={r['k_rise']:.4f} "
          f"[{r['t_s']:.0f}s] ────", flush=True)
    print(f"  J_v5={r['J_v5']:.4f}  J_v6={r['J_v6']:.4f}", flush=True)
    o = r["OLDQ"]
    print(f"  OLDQ replay: 0424={o['jump_0424']:.3f}  0602={o['jump_0602']:.3f}  "
          f"0429={o['jump_0429']:.3f}", flush=True)
    cs = r["CL_sess"]
    print(f"  CL: FIT={r['CL_fit'] * 100:.1f}%  HO(0324)={r['CL_heldout'] * 100:.1f}%  "
          f"0421={cs['jump_position_0421'] * 100:.1f}%  0424={cs['jump_0424'] * 100:.1f}%  "
          f"0602={cs['jump_0602'] * 100:.1f}%  0429={cs['jump_0429'] * 100:.1f}%",
          flush=True)
    print(f"  JW6-C(0429창)={r['J6C']:.1f}  O6(0604)={r['O6']:.1f}  H={r['H']:.4f}  "
          f"S2S={r['S2S']:.3f}  AIR={r['AIR']:.3f}", flush=True)
    print("  norm: " + "  ".join(f"{k}={n[k]:.3f}" for k in
          ("CL", "DQ", "JW2", "JW6", "S2S", "O6", "OLDQ", "H", "CLFF", "OLDQFF",
           "AIR")), flush=True)
    print("  gates: " + "  ".join(f"{k}={'P' if ok else 'F'}"
                                  for k, ok in r["gates"].items()), flush=True)
    print("  0429 trial rmse: " + "  ".join(f"{t['sub']}={t['rmse']:.2f}"
                                            for t in r["rows429"]), flush=True)


# ══════════ Task 2: 에너지 감사 — a_full23 미러 + E_diss 축적 (p22_exp_cvtloss 규약) ══════════
def a_full23_energy(model, l_i, d, law, o1, o2, c_cvt, spr, k_rise):
    """RU.a_full23(is_cvt=True) 문자 미러 + 변경점 1: E_diss += -tql_cvt·vk·dt
    (C_CVT 항만 축적 — 스프링 qfrc는 별도 항이라 제외; exp_cvtloss와 동일 정의).
    반환 (rmse, h_sim, E_diss_total, E_diss_record)."""
    P = C._W["P"]; mj = C._W["mj"]; S = P.J._P["S"]
    t = d["t"]
    law_a = law[0]
    hl = RU.hl_vec(d["traw2"], d["dq2"], spr) if spr is not None else None
    if spr is not None:
        ks, kref, _ = RU.spr_resolve(model, spr)
    sv = RU.supp_vec(d["traw2"], d["dq2"], law)
    if k_rise:
        sv = sv + RU.rise_term(d["dq2"], k_rise, law[2])
    t1 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"]))
    t2 = np.interp(t - P.SD, t, P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"]) + sv)
    supp0 = float(sv[0])
    q1_0 = float(d["q1"][0]) + o1
    q2_0 = float(d["q2"][0]) + o2
    md = mj.MjData(model)
    sq1, sq2 = -q1_0 - np.pi / 2, -q2_0
    from cvt_core import qpos_from_crank
    md.qpos[:] = qpos_from_crank(1.0, sq1, sq2, l_i)[0]
    mj.mj_forward(model, md)
    fg = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "foot")
    md.qpos[0] = 1.0 - float(md.geom_xpos[fg][2]) + S.FOOT_RADIUS
    md.qvel[:] = 0
    mj.mj_forward(model, md)
    dof_knee = safe.dofadr(model, "knee", mj)
    iq_k = safe.qadr(model, "knee", mj)
    qg = rg = None
    if c_cvt > 0:
        qg, rg = RU.rtab(l_i)
    dt = model.opt.timestep
    N = int((P.J.T_SETTLE + t[-1] + P.J.T_AFTER) / dt)
    tl = np.arange(N) * dt - P.J.T_SETTLE
    dq2s = np.zeros(N); bzs = np.zeros(N)
    E_tot = 0.0; E_rec = 0.0                                    # ★ 에너지 축적
    for k in range(N):
        tc = tl[k]
        if tc < 0:
            q1c = -md.qpos[1] - np.pi / 2; q2c = -md.qpos[2]
            v1c = -md.qvel[1]; v2c = -md.qvel[2]
            c1 = S.SETTLE_KP * (q1_0 - q1c) - S.SETTLE_KD * v1c
            c2 = S.SETTLE_KP * (q2_0 - q2c) - S.SETTLE_KD * v2c
            s1 = float(P.J.ahat(P.A_PAPER, np.array([float(c1)]), np.array([v1c]))[0])
            s2 = float(P.J.ahat(P.A_PAPER, np.array([float(c2)]), np.array([v2c]))[0])
            extra = supp0
        else:
            tm_ = min(tc, t[-1])
            s1 = float(np.interp(tm_, t, t1)); s2 = float(np.interp(tm_, t, t2))
            extra = 0.0
            if tc > t[-1]:
                s1 = s2 = 0.0
                extra = law_a
        md.ctrl[:] = [-s1, -(s2 + extra)]
        tql = 0.0
        if qg is not None:
            rr = float(np.interp(md.qpos[2], qg, rg))
            amp = max(1.0 / max(abs(rr), 0.2) - 1.0, 0.0)
            vk = float(md.qvel[dof_knee])
            tql = -c_cvt * abs(s2) * amp * float(np.tanh(vk / 1.0))
            dE = -tql * vk * dt                                 # ★ 소산 (≥0)
            E_tot += dE
            if 0.0 <= tc <= t[-1]:
                E_rec += dE
        if hl is not None:
            if tc < 0:
                h = float(hl[0])
            elif tc > t[-1]:
                h = 0.0
            else:
                h = float(np.interp(tc, t, hl))
            tql += ks * (kref - float(md.qpos[iq_k])) * h
        md.qfrc_applied[dof_knee] = tql
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
    return rmse, h_sim, float(E_tot), float(E_rec)


def energy_audit(c_cvt, k_rise):
    """0429 전 trial 재생 소산 에너지 vs P22 원장 surplus_res."""
    v = RU.apply_freeze(RU.pad23(v_of(c_cvt, k_rise)))
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    kr = RU.rise_of(float(v[IK]))
    x32, sp = C.x32_of(v[:20])
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    model_c = RU.build_cvt23(x32, float(v[1]), sp, 0.02508, float(v[IK]))
    o1, o2 = E.QOFF_A429
    rows = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0429":
            continue
        res = a_full23_energy(model_c, d["l_i"], d, law, o1, o2,
                              float(v[IC]), spr, kr)
        led = LED429.get(str(sub), {})
        if res is None:
            rows.append(dict(sub=str(sub), crash=True))
            continue
        rmse, h_sim, e_tot, e_rec = res
        rows.append(dict(
            sub=str(sub), crash=False, rmse=rmse, h_sim=h_sim,
            E_diss=e_tot, E_diss_rec=e_rec,
            ledger_res=float(led.get("surplus_res", float("nan"))),
            ledger_W2=float(led.get("W2", float("nan")))))
    return rows


def print_energy(tag, rows):
    print(f"\n──── 에너지 감사 [{tag}] — 재생 C_CVT 소산 vs P22 원장 잔차 ────",
          flush=True)
    print(f"{'sub':16s} {'E_diss[J]':>9s} {'원장res[J]':>9s} {'E/res':>6s} "
          f"{'E/W2':>6s} {'dq2RMSE':>8s}", flush=True)
    es, ls = [], []
    for r in rows:
        if r.get("crash"):
            print(f"{r['sub']:16s}  CRASH", flush=True)
            continue
        ratio = r["E_diss"] / r["ledger_res"] if r["ledger_res"] else float("nan")
        pw2 = r["E_diss"] / r["ledger_W2"] if r["ledger_W2"] else float("nan")
        es.append(r["E_diss"]); ls.append(r["ledger_res"])
        print(f"{r['sub']:16s} {r['E_diss']:9.2f} {r['ledger_res']:9.2f} "
              f"{ratio:6.2f} {pw2 * 100:5.1f}% {r['rmse']:8.3f}", flush=True)
    if es:
        print(f"{'MEAN':16s} {np.mean(es):9.2f} {np.mean(ls):9.2f} "
              f"{np.mean(es) / np.mean(ls):6.2f}   (원장 목표 2.38→9.74, mean 5.60)",
              flush=True)


def main():
    t0 = time.time()
    print("=== p24_cvt_scan — C_CVT beyond-cap (평가 전용, out-of-cage) ===", flush=True)
    print(f"p23a: C_CVT={C0:.4f}  K_RISE={K0:.4f}  T_SPR={X0[22]:.4f}", flush=True)
    V6.ensure_init()
    print(f"init done [{time.time() - t0:.0f}s]", flush=True)

    results = {}

    # ── Task 1: C_CVT 스캔 (K_RISE = p23a) ──
    print("\n════ Task 1: C_CVT 스캔 (K_RISE=0.1881) ════", flush=True)
    for cc in (C0, 0.4, 0.6, 0.8, 1.0, 1.3):
        key = f"c{cc:g}_k{K0:g}"
        r = eval_config(cc, K0)
        results[key] = r
        print_config(r)
        safe.atomic_json_write(OUT, results)

    # best C_CVT: 0429 replay 최소 (게이트 전멸 조합은 제외하되 없으면 무조건 최소)
    scan = [r for r in results.values()]
    ok = [r for r in scan if r["gates"]["ALL"]] or scan
    best = min(ok, key=lambda r: r["OLDQ"]["jump_0429"])
    cbest = best["c_cvt"]
    print(f"\n>>> best C_CVT = {cbest:g} (0429 replay {best['OLDQ']['jump_0429']:.3f}, "
          f"gates ALL={'P' if best['gates']['ALL'] else 'F'})", flush=True)

    # ── Task 2: 에너지 감사 (best + p23a 대조) ──
    print("\n════ Task 2: 에너지 감사 ════", flush=True)
    ea = {}
    for cc, tag in ((C0, f"p23a C_CVT={C0:.4f}"), (cbest, f"best C_CVT={cbest:g}")):
        if f"E_{cc:g}" in ea:
            continue
        rows = energy_audit(cc, K0)
        ea[f"E_{cc:g}"] = rows
        print_energy(tag, rows)
    results["energy_audit"] = ea
    safe.atomic_json_write(OUT, results)

    # ── Task 3: 상호작용 {C0, cbest} × K_RISE {K0, 0.10, 0.0} ──
    print("\n════ Task 3: C_CVT × K_RISE 상호작용 ════", flush=True)
    for cc in dict.fromkeys((C0, cbest)):
        for kr in (K0, 0.10, 0.0):
            key = f"c{cc:g}_k{kr:g}"
            if key in results:
                print(f"\n(재사용) {key}", flush=True)
                continue
            r = eval_config(cc, kr)
            results[key] = r
            print_config(r)
            safe.atomic_json_write(OUT, results)

    print(f"\nsaved {OUT.name}  [{(time.time() - t0) / 60:.1f}m total]", flush=True)


if __name__ == "__main__":
    main()
