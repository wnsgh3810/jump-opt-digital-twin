"""GOAL22 P6 — 샘플링-베이스 궤적 최적화 3종 vs NLP (트윈 위 정면 비교).

트윈 = P13e 정직물리 canonical. 변수 = hip/knee 토크 스플라인 노트 각 10개
(push T=0.184s, linear interp), 초기값 = G20 NLP deploy 100% CSV 리샘플.
rollout = settle(PD 0.4s, CSV 초기자세) → push(τ replay) → flight → apex h.
비용 = -h_apex + τ한계(18Nm) 벌점 + 스무스니스 벌점. 예산 = 방법당 ~2400 rollouts.
  (a) CMA-ES  (b) MPPI (softmax 가중, λ=0.3)  (c) Predictive Sampling (best-of-N, σ 수축)
산출: 방법별 h/위반/rollout 수/벽시계 + NLP 해 replay 기준 + 강건성(IC/질량 노이즈 h 분포).
"""
import sys, json, time
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

NK = 10                    # 노트/관절
T_PUSH = 0.184238
TAU_LIM = 18.0
T_SETTLE = 0.4
T_FLIGHT = 0.9
CSV = REPO / "code/goal19/nlp_demo/deploy/jump_optimal_s1.00_taulim18.0Nm.csv"
OUT = Path(__file__).parent / "p6_sampling.json"
_L = {}


def winit():
    PH.winit()
    P12 = P13._M["P12"]
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]; mj = P12._G["mujoco"]
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x32 = np.asarray(can["x"])
    dd = dict(zip(FR.NAMES, x32[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    xml = P13.apply_linkage_mods(xml, dict(zip(P13.N6, x32[26:32])))
    _L["model"] = mj.MjModel.from_xml_string(xml)
    _L["mj"] = mj; _L["S"] = S
    a = np.genfromtxt(CSV, delimiter=",", names=True)
    _L["q0"] = (float(a["q1_des_rad"][0]), float(a["q2_des_rad"][0]))
    _L["csv"] = a
    _L["tk"] = np.linspace(0, T_PUSH, NK)


def x_from_csv():
    a = _L["csv"]; tk = _L["tk"]
    return np.concatenate([np.interp(tk, a["t_s"], a["tau1_ff_Nm"]),
                           np.interp(tk, a["t_s"], a["tau2_ff_Nm"])])


def rollout(args):
    """x(2NK) 또는 ('dense', t, tau1, tau2). 반환 (cost, h_apex, pen, slip)."""
    if not _L:
        winit()
    x, mass_eps, ic_eps, seed = args
    mj = _L["mj"]; S = _L["S"]; model = _L["model"]
    if mass_eps:
        model = mj.MjModel.from_xml_string(_re_mass_xml(mass_eps))
    d = mj.MjData(model)
    q1c, q2c = _L["q0"]
    sq1, sq2 = -q1c - np.pi / 2, -q2c
    d.qpos[:] = [0.45, sq1, sq2, -sq2, sq2]
    mj.mj_forward(model, d)
    dt = model.opt.timestep
    tk = _L["tk"]
    if isinstance(x, tuple):
        tsrc, h1, h2 = x[1], x[2], x[3]
    else:
        tsrc, h1, h2 = tk, x[:NK], x[NK:]
    rng = np.random.default_rng(seed) if ic_eps else None
    N = int((T_SETTLE + T_PUSH + T_FLIGHT) / dt)
    h_apex = 0.0; pen_tau = 0.0
    for k in range(N):
        tc = k * dt
        if tc < T_SETTLE:
            th = S.SETTLE_KP * (sq1 - d.qpos[1]) + S.SETTLE_KD * (0 - d.qvel[1])
            tk_ = S.SETTLE_KP * (sq2 - d.qpos[2]) + S.SETTLE_KD * (0 - d.qvel[2])
            if tc >= T_SETTLE - dt * 1.5 and ic_eps:   # IC 섭동 (강건성 평가)
                d.qvel[1] += rng.normal(0, 0.05); d.qvel[2] += rng.normal(0, 0.05)
        elif tc < T_SETTLE + T_PUSH:
            tm = tc - T_SETTLE
            t1 = float(np.interp(tm, tsrc, h1)); t2 = float(np.interp(tm, tsrc, h2))
            pen_tau += (max(0.0, abs(t1) - TAU_LIM) ** 2 + max(0.0, abs(t2) - TAU_LIM) ** 2) * dt
            th, tk_ = -t1, -t2                       # canonical -> mj
        else:
            th = tk_ = 0.0
        d.ctrl[:] = [th, tk_]
        try:
            mj.mj_step(model, d)
        except Exception:
            return 10.0, 0.0, 99.0
        if not np.isfinite(d.qpos).all() or abs(d.qpos[0]) > 5:
            return 10.0, 0.0, 99.0
        if tc >= T_SETTLE:
            h_apex = max(h_apex, float(d.qpos[0]))
    if isinstance(x, tuple):
        sm = 0.0
    else:
        sm = float(np.sum(np.diff(h1) ** 2) + np.sum(np.diff(h2) ** 2))
    cost = -h_apex + 50.0 * pen_tau + 2e-4 * sm
    return float(cost), float(h_apex), float(pen_tau)


def _re_mass_xml(eps):
    """질량 섭동 XML (강건성 평가 전용): thigh/calf ±eps 비율."""
    P12 = P13._M["P12"]
    FR = P12._G["FR"]; FL = P12._G["FL"]
    can = json.load(open(REPO / "code/goal21/fourbar_honest_canonical.json"))
    x32 = np.asarray(can["x"]).copy()
    nm = list(FR.NAMES)
    x32[nm.index("M_thigh")] *= (1 + eps)
    x32[nm.index("M_calf")] *= (1 - eps)
    dd = dict(zip(FR.NAMES, x32[:26]))
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = FL.build_xml_fourbar_flip(dd["arm_knee"], sc)
    return P13.apply_linkage_mods(xml, dict(zip(P13.N6, x32[26:32])))


def run_cma(pool, x0, budget):
    import cma
    es = cma.CMAEvolutionStrategy(x0.tolist(), 1.2,
                                  {"maxfevals": budget, "popsize": 24, "seed": 5, "verbose": -9})
    best = (1e9, None); nev = 0; hist = []
    while not es.stop():
        sols = es.ask()
        rs = pool.map(rollout, [(np.array(s), 0.0, False, 0) for s in sols])
        cc = [r[0] for r in rs]; nev += len(cc)
        es.tell(sols, cc)
        i = int(np.argmin(cc))
        if cc[i] < best[0]:
            best = (cc[i], np.array(sols[i]))
        hist.append((nev, -best[0]))
    return best[1], hist, nev


def run_mppi(pool, x0, budget, lam=0.3, sigma=1.5, pop=60):
    x = x0.copy(); hist = []; nev = 0
    rng = np.random.default_rng(7)
    iters = budget // pop
    for it in range(iters):
        eps = rng.normal(0, sigma, (pop, len(x)))
        eps[0] = 0.0                                  # 현재 해 포함
        rs = pool.map(rollout, [(x + e, 0.0, False, 0) for e in eps])
        cc = np.array([r[0] for r in rs]); nev += pop
        w = np.exp(-(cc - cc.min()) / lam); w /= w.sum()
        x = x + (w[:, None] * eps).sum(0)
        c_now = rollout((x, 0.0, False, 0))[0]
        hist.append((nev, -min(c_now, cc.min())))
        sigma = max(0.4, sigma * 0.97)
    return x, hist, nev


def run_ps(pool, x0, budget, sigma=1.5, pop=60):
    x = x0.copy(); cbest = rollout((x, 0.0, False, 0))[0]
    hist = []; nev = 0
    rng = np.random.default_rng(9)
    iters = budget // pop
    for it in range(iters):
        eps = rng.normal(0, sigma, (pop, len(x)))
        rs = pool.map(rollout, [(x + e, 0.0, False, 0) for e in eps])
        cc = np.array([r[0] for r in rs]); nev += pop
        i = int(np.argmin(cc))
        if cc[i] < cbest:
            cbest = cc[i]; x = x + eps[i]
        else:
            sigma = max(0.3, sigma * 0.93)
        hist.append((nev, -cbest))
    return x, hist, nev


def robust(pool, x, n=40):
    rs = pool.map(rollout, [(x, 0.02 * (1 if i % 2 else -1), True, 100 + i) for i in range(n)])
    hs = np.array([r[1] for r in rs])
    return dict(mean=float(hs.mean()), std=float(hs.std()), min=float(hs.min()),
                p10=float(np.percentile(hs, 10)))


def main():
    import multiprocessing as mp
    winit()
    pool = mp.Pool(10, initializer=winit)
    x0 = x_from_csv()
    a = _L["csv"]
    BUDGET = 2400

    # 기준: NLP 해 (dense CSV) + 노트 리샘플 버전
    c_nlp, h_nlp, _ = rollout((("dense", a["t_s"], a["tau1_ff_Nm"], a["tau2_ff_Nm"]), 0.0, False, 0))
    c_x0, h_x0, _ = rollout((x0, 0.0, False, 0))
    print(f"NLP dense replay: h={h_nlp:.4f}   NLP 10-knot 리샘플: h={h_x0:.4f}", flush=True)

    res = dict(nlp=dict(h=float(h_nlp)), nlp_knots=dict(h=float(h_x0)))
    for name, fn in [("CMA", run_cma), ("MPPI", run_mppi), ("PS", run_ps)]:
        t0 = time.time()
        xb, hist, nev = fn(pool, x0, BUDGET)
        c, h, pen = rollout((xb, 0.0, False, 0))
        rb = robust(pool, xb)
        wall = time.time() - t0
        res[name] = dict(h=float(h), pen=float(pen), nev=nev, wall_s=float(wall),
                         hist=[[int(n), float(v)] for n, v in hist],
                         x=[float(v) for v in xb], robust=rb)
        print(f"{name:5s} h={h:.4f} pen={pen:.4f} nev={nev} wall={wall/60:.1f}min "
              f"robust(mean/std/min)={rb['mean']:.3f}/{rb['std']:.3f}/{rb['min']:.3f}", flush=True)
    rb_nlp = robust(pool, x0)
    res["nlp_knots"]["robust"] = rb_nlp
    print(f"NLP-knots robust: {rb_nlp['mean']:.3f}/{rb_nlp['std']:.3f}/{rb_nlp['min']:.3f}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
