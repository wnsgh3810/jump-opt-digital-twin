# -*- coding: utf-8 -*-
"""p24_refit_check — P24 재적합 검증 드라이버 (골든 연속성 + 전선 top-K 엄격 게이트/HO).

모드 (argv[1]):
  golden      하네스 검증 — ① 연속성 시드 (p23a + B1=K1=0, 힙 층 실효 0)의 evaluate가
              p23a 수치(J_v6 0.8976, norm 전 성분)를 재현하는가 ② as-is 패드 시드
              (HIP ON)의 점수 변화 관측 (기록용) ③ 연속성 시드의 HO 진단이
              동결 심판 참조값 (CL≈0.3479, 재생≈2.92)과 정합하는가.
  front [K=3] p23_fit_nsga_front_p24.json 전선 top-K → full evaluate(keep_rows=True)
              + HO (eval_p23 CL + 0324 A-재생 진단) + 성공바 판정 표.

성공바 (P24 과제 문언 — "확" 그림):
  gates ALL 통과 + OLDQ 세션별 전부 ≤ P19 앵커 (0424 1.8934 / 0602 1.2555 / 0429 3.3109)
  + Ĥ ≤ 1.02 + HO CL ≤ 0.362 + J_v6 < 0.88.

HO 규약 (p23_ho_check / fourbar_p23a_candidate.heldout 미러):
  CL   = p19_adapter.eval_p23 (held-out 0324 포함 폐루프; ff_hip=True, o=0, 동결 적용 —
         후보 파일의 0.3469는 동결 미적용, 동결 심판 참조값은 0.3479)
  재생 = a_full23 (무변속 모델, o1=o2=0) 0324 3 trial dq2 RMSE — 평균이 replay_diag.

평가 전용 — 기존 파일 무수정, 산출 p24_refit_check.json. 커밋 없음.
실행: PYTHONIOENCODING=utf-8 python p24_refit_check.py golden|front [K]
"""
import os

os.environ["P23_SPRING_GATED"] = "1"
os.environ["P23_RISE_GATED"] = "1"
os.environ["P24_REFIT"] = "1"
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
import p23_runners as RN            # noqa: E402
import p22_eval as E                # noqa: E402
import p21_cma as C                 # noqa: E402
import p19_run as R19               # noqa: E402
import p19_adapter as AD            # noqa: E402

assert RU.P24_REFIT and RU.NV23 == 26, "P24_REFIT env 미적용"

CAND = safe.read_json(HERE / "fourbar_p23a_candidate.json")
FRONT_PATH = HERE / "p23_fit_nsga_front_p24.json"
OUT = HERE / "p24_refit_check.json"
HO_CL_REF, HO_REP_REF = 0.3479, 2.9167       # 동결 심판 참조값 (p23a)
BAR = dict(ho_cl=0.362, jv6=0.88, h_norm=1.02)
PSHOW = ("stiff", "ref", "I_th", "dz_th", "LAW_A", "LAW_V0", "LAW_B", "C_CVT",
         "K_RISE", "T_SPR", "B1_HIP", "V0_HIP", "K1_HIP")


def seed_pair():
    """(as-is 패드, 연속성 B1=K1=0) — p23_fit_nsga.seeds_p24와 동일 구성."""
    base = RU.pad23(np.asarray(CAND["x"], float))
    off = base.copy()
    off[RU.NAMES23.index("B1_HIP")] = 0.0
    off[RU.NAMES23.index("K1_HIP")] = 0.0
    return base, off


def ho_cl(v):
    """held-out 0324 포함 폐루프 CL — p19_adapter.eval_p23 (동결·힙 슬롯 자동 주입)."""
    cand = dict(names=list(RU.NAMES23), x=[float(a) for a in v],
                structure=dict(spring_gated=True, rise_gated=True))
    r = AD.eval_p23(cand)
    return dict(fit=float(r["fit"]), heldout=float(r["heldout"]),
                sess={k: float(val[0]) for k, val in r["summary"].items()})


def ho_replay(v):
    """0324 A-재생 진단 — p23_ho_check 규약 미러 (a_full23, 무변속, o1=o2=0)."""
    v = RU.apply_freeze(RU.pad23(np.asarray(v, float)))
    law = RU.law_of(v)
    spr = RU.spr_of(v)
    kr = RU.rise_of(float(v[21]))
    x32, sp = C.x32_of(v[:20])
    model_f = RU.build_flip23(x32, float(v[1]), sp, float(v[21]))
    if R19.TRIALS is None:
        R19.TRIALS = R19.all_trials()
    reps = []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R19.TRIALS:
        if ds != "jump_0324":
            continue
        res = RU.a_full23(model_f, False, l_i, d, law, 0.0, 0.0, c_cvt=0.0,
                          spr=spr, k_rise=kr)
        reps.append(float(res[0]) if res is not None else 9.9)
    return reps


def bar_of(comp, ho, reps):
    a5, _, _ = V6.anchors()
    oldq = {s: bool(comp["OLDQ"][s] <= a5["OLDQ"][s] + 1e-12) for s in E.OLDQ_SESS}
    b = dict(gates_all=bool(comp["gates"]["ALL"]),
             oldq=oldq, oldq_all=all(oldq.values()),
             H=bool(comp["norm"]["H"] <= BAR["h_norm"] + 1e-12),
             ho_cl=bool(ho["heldout"] <= BAR["ho_cl"] + 1e-12),
             jv6=bool(comp["J_v6"] < BAR["jv6"]),
             ho_replay_diag=float(np.mean(reps)))
    b["SUCCESS"] = all(b[k] for k in ("gates_all", "oldq_all", "H", "ho_cl", "jv6"))
    return b


def show_one(tag, v, comp, ho=None, reps=None):
    a5, _, _ = V6.anchors()
    n = comp["norm"]
    print(f"\n──── {tag} ────", flush=True)
    print("  " + "  ".join(f"{k}={v[RU.NAMES23.index(k)]:+.4f}" for k in PSHOW),
          flush=True)
    print(f"  J_v6={comp['J_v6']:.4f}  J_v5={comp['J_v5']:.4f}  "
          f"gates_ALL={'P' if comp['gates']['ALL'] else 'F'}  "
          + " ".join(f"{k}={'P' if ok else 'F'}" for k, ok in comp["gates"].items()
                     if k != "ALL" and not ok), flush=True)
    print("  norm: " + "  ".join(f"{k}={n[k]:.3f}" for k in
          ("CL", "DQ", "JW2", "JW6", "S2S", "O6", "OLDQ", "H", "CLFF", "OLDQFF",
           "AIR")), flush=True)
    o = comp["OLDQ"]
    print("  OLDQ replay vs P19 앵커: "
          + "  ".join(f"{s[-4:]}={o[s]:.3f}/{a5['OLDQ'][s]:.3f}"
                      f"{'✓' if o[s] <= a5['OLDQ'][s] else '✗'}" for s in E.OLDQ_SESS),
          flush=True)
    print(f"  FF replay: 0422={comp['OLDQFF']['jump_0422']:.3f}  "
          f"0319tau={comp['OLDQFF']['jump_0319tau']:.3f}  AIR={comp['AIR']:.3f}  "
          f"H_raw={comp['H']:.4f}", flush=True)
    if ho is not None:
        cs = ho["sess"]
        print(f"  CL: FIT={ho['fit'] * 100:.2f}%  HO(0324)={ho['heldout'] * 100:.2f}%  "
              f"0421={cs['jump_position_0421'] * 100:.1f}  0424={cs['jump_0424'] * 100:.1f}  "
              f"0602={cs['jump_0602'] * 100:.1f}  0429={cs['jump_0429'] * 100:.1f}",
              flush=True)
    if reps is not None:
        print(f"  HO 재생 진단(0324 3tr): {['%.3f' % r for r in reps]} "
              f"mean={np.mean(reps):.3f}  (p23a 참조 2.92)", flush=True)


def main():
    t0 = time.time()
    mode = sys.argv[1] if len(sys.argv) > 1 else "golden"
    V6.ensure_init()
    print(f"init done [{time.time() - t0:.0f}s] mode={mode} NV23={RU.NV23}", flush=True)
    results = dict(gen=time.strftime("%Y-%m-%d %H:%M"), mode=mode)

    if mode == "golden":
        base, off = seed_pair()
        ref_norm = CAND["v6_gates"]["norm"]
        comp_off = V6.evaluate(off, keep_rows=False)
        show_one("연속성 시드 (p23a + B1=K1=0) — p23a 재현 기대", off, comp_off)
        dmax = max(abs(comp_off["norm"][k] / ref_norm[k] - 1) for k in ref_norm)
        print(f"  vs p23a: dJ_v6={comp_off['J_v6'] - CAND['J_v6']:+.2e}  "
              f"norm 최대 상대편차={dmax:.2e}  "
              f"{'GOLDEN OK' if abs(comp_off['J_v6'] - CAND['J_v6']) < 1e-9 and dmax < 1e-9 else 'MISMATCH!'}",
              flush=True)
        comp_base = V6.evaluate(base, keep_rows=False)
        show_one("as-is 패드 시드 (HIP ON, b1=-0.2608, K1=0) — 점수 변화 관측", base,
                 comp_base)
        ho = ho_cl(off)
        reps = ho_replay(off)
        print(f"\nHO(연속성): CL={ho['heldout']:.4f} (참조 {HO_CL_REF})  "
              f"재생={np.mean(reps):.4f} (참조 {HO_REP_REF})  reps={reps}", flush=True)
        results.update(
            continuity=dict(J_v6=comp_off["J_v6"], norm=comp_off["norm"],
                            dJ=comp_off["J_v6"] - CAND["J_v6"], dnorm_max=dmax),
            asis=dict(J_v6=comp_base["J_v6"], norm=comp_base["norm"],
                      OLDQ=comp_base["OLDQ"], H=comp_base["H"]),
            ho=dict(cl=ho, reps=reps, rep_mean=float(np.mean(reps))))

    elif mode == "front":
        K = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        fr = safe.read_json(FRONT_PATH)
        ents = fr["front"]
        ents.sort(key=lambda e: (not e["full"]["gates"]["ALL"], e["full"]["J_v6"]))
        rows = []
        for i, ent in enumerate(ents[:K]):
            v = np.asarray(ent["x"], float)
            comp = V6.evaluate(v, keep_rows=True)
            ho = ho_cl(v)
            reps = ho_replay(v)
            bar = bar_of(comp, ho, reps)
            show_one(f"front top-{i + 1} (F={ent['F']})", v, comp, ho, reps)
            print("  성공바: " + "  ".join(
                f"{k}={'P' if bar[k] else 'F'}" for k in
                ("gates_all", "oldq_all", "H", "ho_cl", "jv6"))
                + f"  → {'★ SUCCESS' if bar['SUCCESS'] else 'fail'}", flush=True)
            r429 = [r for r in comp.get("OLDQ_trials", []) if r["ds"] == "jump_0429"]
            rows.append(dict(
                rank=i + 1, x=[float(a) for a in v], F=ent["F"],
                params={k: float(v[RU.NAMES23.index(k)]) for k in PSHOW},
                J_v6=comp["J_v6"], J_v5=comp["J_v5"], OLDQ=comp["OLDQ"],
                OLDQFF=comp["OLDQFF"], CLFF=comp["CLFF"], AIR=comp["AIR"],
                H=comp["H"], norm=comp["norm"], gates=comp["gates"],
                ho_cl=ho, ho_reps=reps, bar=bar,
                rows429=[dict(sub=r["sub"], rmse=float(r["rmse"]),
                              h_sim=float(r["h_sim"]), h_real=float(r["h_real"]))
                         for r in r429]))
        results["front"] = rows
    else:
        raise SystemExit(f"unknown mode {mode}")

    safe.atomic_json_write(OUT, results)
    print(f"\nsaved {OUT.name} [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
