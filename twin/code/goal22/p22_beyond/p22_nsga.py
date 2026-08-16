# -*- coding: utf-8 -*-
"""P22 Phase 2 — NSGA-II 파레토 전선 매핑: (CLτ, 통짜 재생 dq) 동시 최소화.

설계 (MARATHON_p22.md 지표 v5 준거):
  목적 2: f1 = CL̂ (지표 v3 CL τ-갭, P19_rebased 정규화)
          f2 = ÔLdq_sub (세션별 3-trial 부분집합 통짜 재생 dq2 RMSE, 부분집합 앵커 정규화)
  제약 6 (g≤0): DQ̂≤1.02, JŴ02≤1.05, JŴ06≤1.05, Ŝ2S≤1.05, Ô6≤1.05, Ĥ_sub≤1.05
  변수 20: p21_cma NAMES/LO/HI 그대로. 시드: P19, p20c, p21, p21h + 섭동 + LHS.
  마무리: 비지배 전선을 full evaluate(25 replay)로 재검증 → p22_nsga_front.json.

사용: run_p22_nsga.bat 더블클릭 (철칙 3). 인자: ngen nproc [pop]. 체크포인트 자동 재개.
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

import safe
import p21_cma as C
from pymoo.core.problem import ElementwiseProblem

POP = 36                                  # argv[3]으로 재정의 가능 (스모크용)
CKPT = HERE / "p22_nsga_ckpt.json"
OUT = HERE / "p22_nsga_front.json"

# 세션별 부분집합 (강도 최저/중간/최고 — 강도 스펙트럼 커버, 결정론)
SUBSET = {
    "jump_0424": ["60_0.75_60_2", "120_2_120_2", "150_2.2_500_4"],
    "jump_0602": ["60_0.75_60_2", "120_2_120_2", "150_2.2_500_5"],
    "jump_0429": ["60_0.75_60_2", "120_2.2_150_2.5", "150_2.2_500_4"],
}


def _winit():
    import p22_eval as E
    E.ensure_init()


def _sub_oldq_h(v):
    """부분집합 통짜 재생 → (세션별 dq2 RMSE 평균 dict, H_sub)."""
    import p22_eval as E
    P, R = C._W["P"], C._W["R"]
    if R.TRIALS is None:
        R.TRIALS = R.all_trials()
    v = np.asarray(v, float)
    x32, sp = C.x32_of(v)
    model_f, _ = P.build_flip(x32, v[1], sp)
    model_c, _ = P.build_cvt(x32, v[1], sp, 0.02508)
    dd = dict(zip(P.J._P["FR"].NAMES, np.asarray(x32)[:26]))
    per, herr = {}, []
    for ds, sub, d, gains, dqon, ffk, m, is_cvt, l_i in R.TRIALS:
        if ds not in SUBSET or str(sub) not in SUBSET[ds]:
            continue
        if is_cvt:
            o1, o2 = E.QOFF_A429
            res = E.a_full(model_c, True, d["l_i"], d, v, o1, o2, pre30=0.0)
            hr = float(d.get("h_real", float("nan")))
        else:
            k1, k2 = P.J.OFFK.get(ds, (None, None))
            o1 = dd.get(k1, 0.0) if k1 else 0.0
            o2 = dd.get(k2, 0.0) if k2 else 0.0
            res = E.a_full(model_f, False, l_i, d, v, o1, o2, pre30=float(v[19]))
            hr = E.h_real_of(ds, sub)
        if res is None:
            per.setdefault(ds, []).append(9.9)
            herr.append(1.0)
            continue
        rmse, h_sim = res
        per.setdefault(ds, []).append(rmse)
        if np.isfinite(hr) and np.isfinite(h_sim):
            herr.append(abs(h_sim / hr - 1.0))
    sess = {ds: float(np.mean(lst)) for ds, lst in per.items()}
    return sess, (float(np.mean(herr)) if herr else 1.0)


FULL_OLDQ = True   # 세그먼트 2+: 부분집합 근사 폐기 (3-trial이 0429 세션 내 일반화를 못 잡음)

# 세그먼트 4+: 널스페이스 나사 동결 (Phase 1 판정 + p22a held-out 재생 악화 신호).
# env P22_FREEZE=1 이면 {M_c, I_th, I_ca, dz_ca}를 P19 값에 고정 — 동결로도 게이트
# 통과점이 남는지의 반증 시험. (지표 v5 불변 — 탐색 공간 조작일 뿐)
import os
FREEZE_ON = os.environ.get("P22_FREEZE", "0") == "1"
FREEZE_IDX = [9, 10, 11, 13]          # NAMES: M_c, I_th, I_ca, dz_ca
X19_REF = None                         # 지연 초기화 (워커 각자)


def _apply_freeze(v):
    global X19_REF
    v = np.asarray(v, float).copy()
    if FREEZE_ON:
        if X19_REF is None:
            import p22_rebase as RB
            X19_REF = RB.x19_vec()
        v[FREEZE_IDX] = X19_REF[FREEZE_IDX]
    return v


def eval_raw(v):
    """워커: 원시 성분 (정규화는 Prob이). 실패 시 None."""
    import p22_eval as E
    E.ensure_init()
    v = _apply_freeze(v)
    try:
        jcl, jdq, jw02, (j6j, j6c), s2s, o6 = C.eval_parts(np.asarray(v, float))
        if FULL_OLDQ:
            sess, hsub, _ = E.oldq_h(v)
        else:
            sess, hsub = _sub_oldq_h(v)
        return dict(CL=float(jcl), DQ=float(jdq), JW2=float(jw02), J6J=float(j6j),
                    J6C=float(j6c), S2S=float(s2s), O6=float(o6),
                    OLDQ=sess, H=float(hsub))
    except Exception:
        return None


DQ_CAP = 1.00 if os.environ.get("P22_DQ_STRICT", "0") == "1" else 1.02


def normalize(r, anch, suba, hs0):
    """원시 성분 → (목적 2, 제약 6). 실패(None)는 대형 페널티."""
    if r is None:
        return [9.0, 9.0], [9.0] * 6
    f1 = r["CL"] / anch["CL"]
    f2 = float(np.mean([r["OLDQ"].get(ds, 9.9) / suba[ds] for ds in SUBSET]))
    jw6 = 0.5 * r["J6J"] / anch["J6J"] + 0.5 * r["J6C"] / anch["J6C"]
    g = [r["DQ"] / anch["DQ"] - DQ_CAP,
         r["JW2"] / anch["JW2"] - 1.05,
         jw6 - 1.05,
         r["S2S"] / anch["S2S"] - 1.05,
         r["O6"] / anch["O6"] - 1.05,
         r["H"] / max(hs0, 1e-9) - 1.05]
    return [float(f1), float(f2)], [float(x) for x in g]


class Prob(ElementwiseProblem):
    """모듈 레벨 (Windows spawn 피클링). 워커 전송 시 runner 제외."""

    def __init__(self, anch=None, suba=None, hs0=1.0, runner=None):
        super().__init__(n_var=20, n_obj=2, n_constr=6,
                         xl=C.LO, xu=C.HI, elementwise_runner=runner)
        self._anch = anch
        self._suba = suba
        self._hs0 = float(hs0)

    def __getstate__(self):
        d = self.__dict__.copy()
        d["elementwise_runner"] = None
        return d

    def _evaluate(self, x, out, *a, **k):
        r = eval_raw(x)
        f, g = normalize(r, self._anch, self._suba, self._hs0)
        out["F"] = f
        out["G"] = g


def seeds():
    import p19_adapter as AD
    import p22_rebase as RB
    out = [RB.x19_vec()]
    for tag in ("p20c", "p21", "p21h"):
        try:
            cd = AD.load_candidate(HERE.parent / "p20_rise" / f"fourbar_{tag}_candidate.json")
            x = np.array(cd["x"], float)
            cq = float(cd.get("p20", {}).get("c_qs", 0.0))
            v0 = min(float(cd.get("p20", {}).get("v0", 6.0)), 39.9)
            vec = np.array([x[0], x[1], *x[3:16], cq, v0, x[16], x[17], x[2]])
            out.append(np.clip(vec, C.LO + 1e-9, C.HI - 1e-9))
        except Exception as ex:
            print(f"seed {tag} skip: {ex}", flush=True)
    return out


def main():
    import multiprocessing as mp
    from pymoo.parallelization.starmap import StarmapParallelization
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.operators.sampling.lhs import LHS
    from pymoo.optimize import minimize
    from pymoo.core.population import Population
    from pymoo.core.evaluator import Evaluator
    from pymoo.termination import get_termination
    from pymoo.core.callback import Callback

    global POP
    ngen = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    if len(sys.argv) > 3:
        POP = int(sys.argv[3])
    anch = safe.read_json(HERE / "p22_eval_anchors.json")

    pool = mp.Pool(nproc, initializer=_winit)

    import p22_rebase as RB
    if FULL_OLDQ:
        # 전체 25-trial 재생 = 정본 앵커 그대로
        suba = dict(anch["OLDQ"])
        hs0 = float(anch["H"])
        print(f"full-anchor OLdq: {suba}  H: {hs0:.4f}", flush=True)
    else:
        x19 = RB.x19_vec()
        a0 = pool.apply(eval_raw, (x19,))
        assert a0 is not None, "anchor eval failed"
        suba = {ds: a0["OLDQ"][ds] for ds in SUBSET}
        hs0 = a0["H"]
        print(f"sub-anchor OLdq: {suba}  H_sub: {hs0:.4f}", flush=True)
        safe.atomic_json_write(HERE / "p22_nsga_subanchor.json",
                               dict(OLDQ=suba, H=hs0, full=a0))

    runner = StarmapParallelization(pool.starmap)
    prob = Prob(anch=anch, suba=suba, hs0=hs0, runner=runner)

    # 초기 개체군: 시드 + 시드 주변 섭동 + LHS
    sd = seeds()
    X0 = list(sd)
    rng = np.random.default_rng(83)
    while len(X0) < max(POP // 2, len(sd)):
        b = sd[rng.integers(len(sd))]
        X0.append(np.clip(b * (1 + 0.05 * rng.standard_normal(20)),
                          C.LO + 1e-9, C.HI - 1e-9))
    X0 = X0[:POP]
    if len(X0) < POP:
        lhs = LHS().do(prob, POP - len(X0)).get("X")
        X0 = list(X0) + list(lhs)
    X0 = np.array(X0)
    if CKPT.exists():
        try:
            ck = safe.read_json(CKPT)
            X0 = np.array(ck["X"], float)
            print(f"resume from ckpt gen={ck['gen']} ({len(X0)} inds)", flush=True)
        except Exception:
            pass
    pop0 = Population.new("X", X0)
    Evaluator().eval(prob, pop0)

    alg = NSGA2(pop_size=POP, sampling=pop0)
    t0 = time.time()

    class CB(Callback):
        def notify(self, algorithm):
            gen = algorithm.n_gen
            X = algorithm.pop.get("X"); F = algorithm.pop.get("F")
            G = algorithm.pop.get("G")
            safe.atomic_json_write(CKPT, dict(gen=int(gen), X=X.tolist(),
                                              F=F.tolist(), G=G.tolist()))
            feas = (G <= 0).all(axis=1)
            if feas.any():
                Ff = F[feas]
                nd = ((Ff[:, 0] <= 1.0) & (Ff[:, 1] <= 1.0)).sum()
                print(f"gen {gen:3d} feas {feas.sum():2d}/{len(F)} "
                      f"bestCL^ {Ff[:, 0].min():.4f} bestOLdq^ {Ff[:, 1].min():.4f} "
                      f"P19지배 {nd} [{(time.time() - t0) / 60:.1f}m]", flush=True)
            else:
                print(f"gen {gen:3d} feas 0/{len(F)}", flush=True)

    res = minimize(prob, alg, get_termination("n_gen", ngen),
                   callback=CB(), seed=83, verbose=False)

    # 마무리: 비지배 전선 full 재검증
    _winit()
    import p22_eval as E
    F = np.atleast_2d(res.F); X = np.atleast_2d(res.X)
    order = np.argsort(F[:, 0])
    nfr = 12 if POP >= 24 else 2          # 스모크에선 2개만 full 재검증
    front = []
    for i in order[:nfr]:
        full = E.evaluate(X[i])
        full.pop("OLDQ_trials", None)
        front.append(dict(x=[float(a) for a in X[i]], F=[float(a) for a in F[i]],
                          full=full))
        print(f"front[{len(front)}] F={F[i]} J_v5={full['J_v5']:.4f} "
              f"OLDQ={full['OLDQ']}", flush=True)
    safe.atomic_json_write(OUT, dict(front=front, ngen=ngen))
    print(f"DONE [{(time.time() - t0) / 60:.1f}m] -> {OUT.name}", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
