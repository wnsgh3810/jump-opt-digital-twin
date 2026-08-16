# -*- coding: utf-8 -*-
"""p23_fit_nsga — P23 Phase 4 NSGA-II 재적합 (지표 v6; 측정 법칙이 pre30+assist 세대 교체).

설계 (MARATHON_p23.md + p22_nsga.py 패턴):
  변수 22 (p23_v6_runners.NAMES23/LO23/HI23):
    법칙 3축(LAW_A/LAW_B/LAW_V0)은 측정 제약 프라이어 (LAW_B HARD = 95% CI×1.5),
    LAW_C 고정, C_CVT·D_DQ 신규 공동적합, {M_c, I_ca, dz_ca} P19 동결 (평가 전 강제).
  목적 2:
    f1 = 0.75·CL̂(v5) + 0.25·ĈL_FF          (폐루프 τ-fidelity 합성)
    f2 = mean(ÔLdq 0424/0602/0429, ÔLdq_FF 0422/0319tau, ÂIR)  (재생 합성 — 6항 평균)
  제약 6 (g≤0): DQ̂≤1.00(strict 기본), JŴ02≤1.05, JŴ06≤1.05, Ŝ2S≤1.05, Ô6≤1.05, Ĥ≤1.02
    (LAW_B는 box bound가 이미 HARD 제약. ĈL_FF·ÔLdq_FF·ÂIR ≤1.02는 승격 게이트 —
     목적에 들어 있으므로 제약 중복 없이 마무리 단계에서 판정.)
  시드: P19+law, p22b+law + ±섭동(5% 상대) + LHS 잔여.
  체크포인트 p23_fit_nsga_ckpt.json (자동 재개), 전선 p23_fit_nsga_front.json.

시동: p23_fit_nsga.bat 더블클릭 (철칙 3). 인자: ngen nproc [pop].
env: P23_DQ_RELAX=1 → DQ̂ 캡 1.02 (기본은 과제 명세 strict 1.00).
     P23_SPRING_GATED=1 → Phase 4b 부하 연동 스프링 (벡터 23축, slot 22=T_SPR;
       p23_v6_runners docstring 참조). 구 22축 ckpt 재개 시 T_SPR=init(2.0) 자동 패드.
     P23_RISE_GATED=1 → Phase 4c 보완 게이트 상승항 (slot 21 의미 교체: D_DQ→K_RISE
       [0.0, 0.30] init 0.216; dof_damping 델타 경로 비활성). 구 ckpt 재개 시
       slot 21이 새 bounds 밖이면 클립.
     P23_NSGA_TAG=<suffix> → ckpt/front 파일명 접미사 (스모크가 본 ckpt를 안 덮게).
     P24_REFIT=1 → P24 재적합 (벡터 26축: +B1_HIP/V0_HIP/K1_HIP; 케이지 I_th 0.35↓·
       C_CVT 1.0↑; 힙 층 벡터 지배 — p23_v6_runners P24 블록 참조). 시드 = MARATHON
       P24 설계 7종 (seeds_p24): p23a 패드/연속성 쌍 + recon 최선셀×K1 + C_CVT 변형 +
       콤보. 구 ckpt(22/23축)와 벡터 의미가 다름 — 반드시 새 TAG로 fresh 시작.
"""
import json
import os
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
import p23_v6_runners as RU
from pymoo.core.problem import ElementwiseProblem

POP = 36                                  # argv[3]으로 재정의 가능 (스모크용)
TAG = os.environ.get("P23_NSGA_TAG", "")  # 스모크/변형 실행이 본 ckpt를 안 덮게
CKPT = HERE / f"p23_fit_nsga_ckpt{TAG}.json"
OUT = HERE / f"p23_fit_nsga_front{TAG}.json"
OLDQ_SESS = ("jump_0424", "jump_0602", "jump_0429")   # == p22_eval.OLDQ_SESS
FF_SESS = ("jump_0422", "jump_0319tau")               # == p23_runners.FF_SESS
DQ_CAP = 1.02 if os.environ.get("P23_DQ_RELAX", "0") == "1" else 1.00


def _winit():
    import p23_v6_eval as V
    V.ensure_init()


def eval_raw(v):
    """워커: 전 v6 원시 성분 (rows 제외 — ckpt/피클 경량화). 실패 시 None."""
    import p23_v6_eval as V
    try:
        c = V.evaluate(np.asarray(v, float), keep_rows=False)
        return {k: c[k] for k in ("CL", "DQ", "JW2", "J6J", "J6C", "S2S", "O6",
                                  "OLDQ", "H", "CLFF", "OLDQFF", "AIR",
                                  "J_v5", "J_v6")}
    except Exception:
        return None


def normalize(r, a5, aff):
    """원시 성분 → (목적 2, 제약 6). 실패(None)는 대형 페널티."""
    if r is None:
        return [9.0, 9.0], [9.0] * 6
    clff = float(np.mean([r["CLFF"][s] / aff["CL_FF"][s] for s in FF_SESS]))
    f1 = 0.75 * r["CL"] / a5["CL"] + 0.25 * clff
    reps = ([r["OLDQ"][s] / a5["OLDQ"][s] for s in OLDQ_SESS]
            + [r["OLDQFF"][s] / aff["OLDQ_FF"][s] for s in FF_SESS]
            + [r["AIR"] / aff["AIR"]])
    f2 = float(np.mean(reps))
    jw6 = 0.5 * r["J6J"] / a5["J6J"] + 0.5 * r["J6C"] / a5["J6C"]
    g = [r["DQ"] / a5["DQ"] - DQ_CAP,
         r["JW2"] / a5["JW2"] - 1.05,
         jw6 - 1.05,
         r["S2S"] / a5["S2S"] - 1.05,
         r["O6"] / a5["O6"] - 1.05,
         r["H"] / a5["H"] - 1.02]
    return [float(f1), float(f2)], [float(x) for x in g]


class Prob(ElementwiseProblem):
    """모듈 레벨 (Windows spawn 피클링). 워커 전송 시 runner 제외 (p22_nsga 패턴)."""

    def __init__(self, a5=None, aff=None, runner=None):
        super().__init__(n_var=RU.NV23, n_obj=2, n_constr=6,
                         xl=RU.LO23, xu=RU.HI23, elementwise_runner=runner)
        self._a5 = a5
        self._aff = aff

    def __getstate__(self):
        d = self.__dict__.copy()
        d["elementwise_runner"] = None
        return d

    def _evaluate(self, x, out, *a, **k):
        r = eval_raw(x)      # freeze는 evaluate 내부(apply_freeze)에서 강제
        f, g = normalize(r, self._a5, self._aff)
        out["F"] = f
        out["G"] = g


def seeds():
    """P19+law, p22b+law (법칙 3축 = 측정 init, C_CVT=D_DQ=0). P24_REFIT: 설계 시드 7종."""
    if RU.P24_REFIT:
        return seeds_p24()
    return [RU.v23_p19_law(), RU.v23_p22b_law()]


def seeds_p24():
    """MARATHON P24 설계 시드 (a~e) — 전부 p23a(23축) 기반 26축.
    (a) p23a as-is 패드 (B1=-0.2608, V0=3.3244, K1=0 — HIP 층 ON이라 점수 변화 있음)
    (b) p23a + B1=K1=0 = 힙 층 실효 0 → 진짜 연속성 시드 (p23a 수치 재현;
        B1=0은 케이지 [-0.378,-0.144] 밖 — 초기 개체는 그대로 평가되고 자손은
        연산자가 케이지로 회수하는 의도된 배치)
    (c) recon 최선셀 (I_th 0.40, dz_th -0.015, b₁ lo=-0.3386) × K1 {0.1, 0.2}
    (d) 카드 2 C_CVT {0.6, 0.8} 변형 (힙 실효 0 — 스캔 재현점: c0.6 = J_v6 0.8755)
    (e) light+hip+cvt 콤보 (I_th 0.40, dz_th -0.015, b₁ -0.26, K1 0.15, C_CVT 0.6)"""
    cand = safe.read_json(HERE / "fourbar_p23a_candidate.json")
    base = RU.pad23(np.asarray(cand["x"], float))
    iI, iZ = RU.NAMES23.index("I_th"), RU.NAMES23.index("dz_th")
    iC = RU.NAMES23.index("C_CVT")
    iB, iK1 = RU.NAMES23.index("B1_HIP"), RU.NAMES23.index("K1_HIP")
    b1_lo = -0.2608 - 0.0778                       # 측정 CI 하단 (recon 'lo' 셀)
    off = base.copy()
    off[iB] = 0.0; off[iK1] = 0.0
    S = [base, off]
    for k1 in (0.1, 0.2):                          # (c)
        s = base.copy()
        s[iI], s[iZ], s[iB], s[iK1] = 0.40, -0.015, b1_lo, k1
        S.append(s)
    for cc in (0.6, 0.8):                          # (d)
        s = off.copy()
        s[iC] = cc
        S.append(s)
    s = base.copy()                                # (e)
    s[iI], s[iZ], s[iB], s[iK1], s[iC] = 0.40, -0.015, -0.26, 0.15, 0.6
    S.append(s)
    return S


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
    safe.utf8_console()
    ngen = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    if len(sys.argv) > 3:
        POP = int(sys.argv[3])

    import p23_v6_eval as V
    a5, aff, ffhip = V.anchors()
    print(f"v6 anchors OK (ff={'knee+hip' if ffhip else 'knee-only'}) | "
          f"DQ cap {DQ_CAP} | pop {POP} ngen {ngen} nproc {nproc}", flush=True)

    pool = mp.Pool(nproc, initializer=_winit)
    runner = StarmapParallelization(pool.starmap)
    prob = Prob(a5=a5, aff=aff, runner=runner)

    # 초기 개체군: 시드 + 시드 주변 섭동 + LHS (p22_nsga 패턴)
    sd = seeds()
    X0 = list(sd)
    rng = np.random.default_rng(97)
    while len(X0) < max(POP // 2, len(sd)):
        b = sd[rng.integers(len(sd))]
        X0.append(np.clip(b * (1 + 0.05 * rng.standard_normal(RU.NV23)),
                          RU.LO23 + 1e-9, RU.HI23 - 1e-9))
    X0 = X0[:POP]
    if len(X0) < POP:
        lhs = LHS().do(prob, POP - len(X0)).get("X")
        X0 = list(X0) + list(lhs)
    X0 = np.array(X0)
    if CKPT.exists():
        try:
            ck = safe.read_json(CKPT)
            Xc = np.array(ck["X"], float)
            if RU.SPRING_GATED and Xc.shape[1] == RU.NV23 - 1:
                # 구 22축 ckpt → T_SPR init 패드 (Phase 4b 재개 경로)
                Xc = np.hstack([Xc, np.full((len(Xc), 1), RU.T_SPR0)])
                print(f"ckpt 22-slot -> T_SPR={RU.T_SPR0} 패드 (SPRING_GATED 재개)",
                      flush=True)
            assert Xc.shape[1] == RU.NV23, \
                f"ckpt 폭 {Xc.shape[1]} != NV23 {RU.NV23} (모드/파일 불일치)"
            if RU.RISE_GATED:
                # 구 D_DQ 값(음수 가능)이 K_RISE bounds 밖일 수 있음 → 클립 (Phase 4c)
                nc = int(((Xc < RU.LO23) | (Xc > RU.HI23)).any(axis=1).sum())
                if nc:
                    print(f"RISE_GATED: ckpt {nc} inds 새 bounds로 클립 (slot21 등)",
                          flush=True)
                Xc = np.clip(Xc, RU.LO23 + 1e-9, RU.HI23 - 1e-9)
            X0 = Xc
            print(f"resume from ckpt gen={ck['gen']} ({len(X0)} inds)", flush=True)
        except AssertionError:
            raise
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
                      f"bestF1 {Ff[:, 0].min():.4f} bestF2 {Ff[:, 1].min():.4f} "
                      f"P19지배 {nd} [{(time.time() - t0) / 60:.1f}m]", flush=True)
            else:
                print(f"gen {gen:3d} feas 0/{len(F)}", flush=True)

    res = minimize(prob, alg, get_termination("n_gen", ngen),
                   callback=CB(), seed=97, verbose=False)

    # 마무리: 전선 상위를 rows 포함 full 재평가 (J_v6·게이트 확정)
    _winit()
    if res.X is None:
        # 가능해 0 (초기 세그먼트 정상 — P19+law 시드 자체가 DQ/JW/H 캡 위반) →
        # 최종 개체군을 제약위반(CV) 오름차순으로 폴백 보고
        X = np.atleast_2d(res.pop.get("X"))
        F = np.atleast_2d(res.pop.get("F"))
        cv = np.asarray(res.pop.get("CV"), float).ravel()
        order = np.argsort(cv)
        print(f"no feasible front — min-CV fallback (best CV {cv.min():.3f})", flush=True)
    else:
        F = np.atleast_2d(res.F); X = np.atleast_2d(res.X)
        order = np.argsort(F[:, 0])
    nfr = 12 if POP >= 24 else 2          # 스모크에선 2개만
    front = []
    for i in order[:nfr]:
        full = V.evaluate(X[i], keep_rows=False)
        front.append(dict(x=[float(a) for a in X[i]], F=[float(a) for a in F[i]],
                          full=full))
        print(f"front[{len(front)}] F={F[i]} J_v6={full['J_v6']:.4f} "
              f"J_v5={full['J_v5']:.4f} gates_ALL={full['gates']['ALL']}", flush=True)
    safe.atomic_json_write(OUT, dict(front=front, ngen=ngen, pop=POP,
                                     dq_cap=DQ_CAP, names=RU.NAMES23,
                                     feasible=bool(res.X is not None)))
    print(f"DONE [{(time.time() - t0) / 60:.1f}m] -> {OUT.name}", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
