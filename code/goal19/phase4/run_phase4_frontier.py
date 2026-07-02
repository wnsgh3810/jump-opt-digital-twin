"""Phase 4 - Jump vs sit2stand trade-off frontier.

KEY finding (Phases 1-3): jumps progressively under-jump (h_sim/h_real 80%->54%)
because the total-sum score is sit2stand-dominated. This traces the Pareto frontier:
re-optimize the 3 params most implicated in the tension
  (M_foot_ex, fv_hip, fc_knee)
minimizing  sit2stand_sum + LAMBDA * jump_sum  for LAMBDA in {1,2,4,8}.

For each LAMBDA report: default-metric total, sit2stand mean, jump mean, jump h ratio.
Base = Phase 3 stack (mass + friction + contact); other params fixed.
User authorized weight adjustment with justification.
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
for p in ["templates","data_loaders","phase1","phase2","phase3"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))

import sub_sim_iter6v2 as S
import plot_4panel as P4
from load_31exp import list_experiments

P1_X = np.array(json.load(open(REPO/"code/goal19/phase1/phase1_best.json"))["best_x"])
P2_FRIC = json.load(open(REPO/"code/goal19/phase2/phase2_best.json"))["best_x"]
P3 = json.load(open(REPO/"code/goal19/phase3/phase3_best.json"))["best_x"]

# index of M_foot_ex in P1_X is 5; fv_hip is P2_FRIC[0]; fc_knee is P2_FRIC[3]
DEFAULT3 = np.array([P1_X[5], P2_FRIC[0], P2_FRIC[3]])  # M_foot_ex, fv_hip, fc_knee
B3 = np.array([[0.0, 0.40], [0.0, 2.0], [0.0, 2.0]])


def apply_base(m_foot_ex, fv_hip, fc_knee):
    x = P1_X.copy(); x[5] = m_foot_ex
    ap = P4.apply_phase1_params(x)
    S.FV_HIP = float(fv_hip); S.FV_KNEE = float(P2_FRIC[1])
    S.FC_HIP = float(P2_FRIC[2]); S.FC_KNEE = float(fc_knee)
    S.SOLREF_TC_LOCK = float(P3[0]); S.IMP0_LOCK = float(P3[1])
    return ap


def eval_groups(params3):
    """Return (sit2stand_sum, jump_sum, default_total, jump_h_ratio)."""
    m_foot_ex, fv_hip, fc_knee = np.clip(params3, B3[:,0], B3[:,1])
    ap = apply_base(m_foot_ex, fv_hip, fc_knee)
    s2s = 0.0; jmp = 0.0; hs=[]; hr=[]
    for ds, sub, isj in list_experiments():
        q1, q2 = P4.OFFSET_MAP.get((ds, sub), (0.0, 0.0))
        try:
            s, m = S.run_one_sub(ds, sub, q1, q2, ap["arm_hip"], ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s, m = None, None
        v = 5e5 if (s is None or not np.isfinite(s) or s > 5e5) else float(s)
        if isj:
            jmp += v
            if m: hs.append(m.get('h_sim_m',0)); hr.append(m.get('h_real_m',0))
        else:
            s2s += v
    ratio = (sum(hs)/sum(hr)) if hr else 0
    return s2s, jmp, s2s+jmp, ratio


def optimize_lambda(lam):
    """Minimize s2s + lam*jump over 3 params via small CMA-ES."""
    import cma
    lo, hi = B3[:,0], B3[:,1]; span = hi-lo
    to_n = lambda x:(x-lo)/span; from_n = lambda u: np.clip(u,0,1)*span+lo
    es = cma.CMAEvolutionStrategy(to_n(np.clip(DEFAULT3,lo,hi)), 0.3, {
        'bounds':[[0.0]*3,[1.0]*3],'maxfevals':90,'popsize':8,'verbose':-9,'seed':3})
    best_obj=1e18; best_p=DEFAULT3.copy()
    while not es.stop():
        U=es.ask(); O=[]
        for u in U:
            p=from_n(u); s2s,jmp,_,_=eval_groups(p); obj=s2s+lam*jmp; O.append(obj)
            if obj<best_obj: best_obj=obj; best_p=p.copy()
        es.tell(U,O)
    return best_p


def main():
    out = Path(__file__).resolve().parent
    print("[Phase 4] Jump vs sit2stand trade-off frontier")
    # Default point (Phase 3 stack)
    s2s0,jmp0,tot0,r0 = eval_groups(DEFAULT3)
    print(f"Phase 3 stack (default): total={tot0:.0f} s2s={s2s0:.0f} jump={jmp0:.0f} h_ratio={r0:.3f}")
    print(f"  DEFAULT3 (M_foot_ex,fv_hip,fc_knee) = {[round(v,4) for v in DEFAULT3]}")
    print("-"*80)
    frontier=[dict(lam='phase3_default', params=DEFAULT3.tolist(), s2s=s2s0, jump=jmp0, total=tot0, h_ratio=r0)]
    for lam in [1.0, 2.0, 4.0, 8.0]:
        t0=time.time()
        p = optimize_lambda(lam)
        s2s,jmp,tot,r = eval_groups(p)
        print(f"LAMBDA={lam:4.1f}: total={tot:.0f} s2s={s2s:.0f} jump={jmp:.0f} h_ratio={r:.3f}  "
              f"params={[round(v,4) for v in p]}  ({time.time()-t0:.0f}s)")
        frontier.append(dict(lam=lam, params=p.tolist(), s2s=float(s2s), jump=float(jmp),
                             total=float(tot), h_ratio=float(r)))
        (out/"phase4_frontier.json").write_text(json.dumps(frontier, indent=2))
    print("-"*80)
    print("Frontier (jump weight lam -> jump h recovers, sit2stand degrades):")
    for f in frontier:
        print(f"  lam={str(f['lam']):14s} s2s={f['s2s']:7.0f} jump={f['jump']:7.0f} h_ratio={f['h_ratio']:.3f}")
    (out/"phase4_frontier.json").write_text(json.dumps(frontier, indent=2))
    print(f"Written: {out/'phase4_frontier.json'}")


if __name__ == "__main__":
    main()
