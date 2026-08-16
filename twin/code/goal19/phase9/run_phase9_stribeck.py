"""Phase 9 - Stribeck friction (break the jump-vs-sit2stand trade-off?).

Hypothesis: sit2stand stability needs friction at LOW speed; jumps are hurt by the
VISCOUS term (fv*v) at HIGH speed. If we supply low-speed friction via a Stribeck
STATIC excess and REDUCE the viscous coefficient, sit2stand stays stable while jumps
recover -> potentially beats the uniform-friction frontier.

Stribeck: F(v) = [Fc + (Fs-Fc)exp(-(|v|/vs)^2)]sign(v) + Fv*v
Base (XML) already has Fc (frictionloss) + Fv (damping). We ADD the excess
  (Fs-Fc)*exp(-(|v|/vs)^2)*sign(v) = ds*exp(-(|v|/vs)^2)*sign(v)
via mjcb_passive, and jointly RE-FIT a lower fv_hip.

Fit: fv_hip_new, ds_hip, ds_knee, vs  (4D). Keep fv_knee, fc_hip, fc_knee, contact, mass.
FINAL baseline (uniform friction) = 15,182.
"""
import sys, json, time
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
for p in ["templates","data_loaders","phase1","phase2","phase3","phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))

import sub_sim_iter6v2 as S
import plot_4panel as P4
import mujoco
from load_31exp import list_experiments

FM = json.load(open(REPO/"code/goal19/goal19_final_model.json"))
P1_X = np.array(FM["mass_15d"]); P1_X[5]=FM["m_foot_ex"]; FR=FM["friction"]; CT=FM["contact"]
BASE = 15182.0

# Globals the passive callback reads (set per-eval)
_DS_HIP = 0.0
_DS_KNEE = 0.0
_VS = 0.1


def _passive_cb(model, data):
    """Add Stribeck static-excess friction on hip/knee joints via qfrc_passive."""
    nv = model.nv
    # dof layout: air s2s (nv=2): hip=0,knee=1 ; gnd/jump (nv=3): base=0,hip=1,knee=2
    if nv >= 3:
        hi, ki = 1, 2
    else:
        hi, ki = 0, 1
    vh = data.qvel[hi]; vk = data.qvel[ki]
    if _DS_HIP > 0:
        data.qfrc_passive[hi] += -_DS_HIP * np.exp(-(vh/_VS)**2) * np.sign(vh)
    if _DS_KNEE > 0:
        data.qfrc_passive[ki] += -_DS_KNEE * np.exp(-(vk/_VS)**2) * np.sign(vk)


def apply_final(fv_hip):
    ap = P4.apply_phase1_params(P1_X)
    S.FV_HIP=float(fv_hip); S.FV_KNEE=FR["fv_knee"]; S.FC_HIP=FR["fc_hip"]; S.FC_KNEE=FR["fc_knee"]
    S.SOLREF_TC_LOCK=CT["solref_tc"]; S.IMP0_LOCK=CT["imp0"]
    return ap


BOUNDS = np.array([
    [0.0, 0.95],   # fv_hip_new (base 0.787; allow lower)
    [0.0, 3.0],    # ds_hip  (static excess)
    [0.0, 3.0],    # ds_knee
    [0.02, 0.6],   # vs (Stribeck velocity, rad/s)
])
X0 = np.array([FR["fv_hip"], 0.0, 0.0, 0.1])  # = current model (no Stribeck) => should == BASE


# Patch the sim loops to set the passive callback AFTER model creation (model is arg).
# Setting it before from_xml_string breaks compilation, so we scope it to stepping only.
_ORIG_JUMP = S.run_jump_sim
_ORIG_S2S = S.run_sit2stand_cycle

def _wrap(orig):
    def wrapped(model, *a, **k):
        mujoco.set_mjcb_passive(_passive_cb)
        try:
            return orig(model, *a, **k)
        finally:
            mujoco.set_mjcb_passive(None)
    return wrapped

S.run_jump_sim = _wrap(_ORIG_JUMP)
S.run_sit2stand_cycle = _wrap(_ORIG_S2S)


def eval_vec(x):
    global _DS_HIP, _DS_KNEE, _VS
    x = np.clip(x, BOUNDS[:,0], BOUNDS[:,1])
    fv_hip, ds_hip, ds_knee, vs = x
    _DS_HIP, _DS_KNEE, _VS = float(ds_hip), float(ds_knee), float(vs)
    ap = apply_final(fv_hip)
    total=0.0
    for ds, sub, isj in list_experiments():
        try:
            s,_ = S.run_one_sub(ds, sub, 0.0, 0.0, 0.0, ap["arm_knee"], motor_tm=0.0)
        except Exception:
            s=None
        total += 5e5 if (s is None or not np.isfinite(s) or s>5e5) else float(s)
    return total


def main():
    out = Path(__file__).resolve().parent
    print(f"[Phase 9] Stribeck friction (break trade-off?) — base={BASE}")
    t0=time.time()
    s0=eval_vec(X0)
    print(f"X0 (no Stribeck, fv_hip={FR['fv_hip']:.3f}) = {s0:.2f}  [should ~= {BASE}]  ({time.time()-t0:.0f}s)")

    import cma
    lo,hi=BOUNDS[:,0],BOUNDS[:,1]; span=hi-lo
    to_n=lambda x:(x-lo)/span; from_n=lambda u:np.clip(u,0,1)*span+lo
    es=cma.CMAEvolutionStrategy(to_n(np.clip(X0,lo,hi)),0.25,{
        'bounds':[[0.0]*4,[1.0]*4],'maxfevals':150,'popsize':10,'verbose':-9,'seed':13})
    best_s=s0; best_x=X0.copy(); hist=[]
    while not es.stop():
        U=es.ask(); Sc=[]
        for u in U:
            xx=from_n(u); s=eval_vec(xx); Sc.append(s)
            if s<best_s: best_s=s; best_x=xx.copy()
        es.tell(U,Sc)
        hist.append(dict(gen=int(es.countiter),best=float(best_s),nfev=int(es.countevals),elapsed=time.time()-t0))
        print(f"gen {es.countiter:2d} best={best_s:9.2f} fv_h={best_x[0]:.3f} ds_h={best_x[1]:.3f} ds_k={best_x[2]:.3f} vs={best_x[3]:.3f} ({time.time()-t0:.0f}s)")
        (out/"phase9_progress.json").write_text(json.dumps(dict(best_score=float(best_s),best_x=best_x.tolist(),
            var_names=["fv_hip","ds_hip","ds_knee","vs"],baseline=BASE,history=hist),indent=2))
    imp=100*(BASE-best_s)/BASE
    print(f"\n[Phase 9 done] best={best_s:.2f}  Δ vs uniform-friction final = {imp:+.2f}%  → {'KEEP (breaks trade-off!)' if imp>3 else 'DROP (no gain)'}")
    (out/"phase9_best.json").write_text(json.dumps(dict(best_score=float(best_s),best_x=best_x.tolist(),
        var_names=["fv_hip","ds_hip","ds_knee","vs"],baseline=BASE,improve_pct=imp,keep=imp>3,history=hist),indent=2))
    print(f"Written: {out/'phase9_best.json'}")


if __name__ == "__main__":
    main()
