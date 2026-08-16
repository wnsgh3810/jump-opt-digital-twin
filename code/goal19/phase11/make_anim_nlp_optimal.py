"""G20 — render the NLP-optimal jump with the CANONICAL renderer (no custom rendering).

Same pattern as make_anim_v3_canonical.py: produce a sim log npz (t, q=[bz,hip,crank],
grf_z) from the four-bar twin replaying the NLP tau*, then call
goal18_v9/_make_anim_universal_colored.py :: make_anim_universal_colored.
h_real overlay = NLP predicted apex (labelled as prediction via trial label).
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
import sys, json, importlib.util, tempfile
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot_fourbar as FB

CANON = Path((LEGACY_ROOT + "/goal18_v9/_make_anim_universal_colored.py"))
spec = importlib.util.spec_from_file_location("_mauc", str(CANON))
_mauc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mauc)

BEST = json.load(open(REPO / "code/goal19/phase11/fourbar_refit_best.json", encoding="utf-8"))
BD = dict(zip(BEST["names"], BEST["x"]))
NLP = np.load(REPO / "code/goal19/nlp_demo/traj_a1.0_k130000.npz")
OUT_DIR = REPO / "code/goal19/phase11/anim_final"
TMP = Path(tempfile.mkdtemp(prefix="anim_nlp_"))


def main():
    S.FV_HIP = BD["fv_hip"]; S.FV_KNEE = BD["fv_knee"]; S.FC_HIP = BD["fc_hip"]; S.FC_KNEE = BD["fc_knee"]
    S.SOLREF_TC_LOCK = BD["solref_tc"]; S.IMP0_LOCK = BD["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = BD["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    mfb = mujoco.MjModel.from_xml_string(FB.build_xml_fourbar_jump(BD["arm_knee"], BD))
    xml = S.build_xml_jump_6d(0.0, BD["arm_knee"])
    xml_path = TMP / "leg_v3.xml"
    xml_path.write_text(xml, encoding="utf-8")

    t = NLP["t"]; q1c = NLP["q1"]; q2c = NLP["q2"]
    tau1 = NLP["tau1"]; tau2 = NLP["tau2"]; z = NLP["z"]; dz = NLP["dz"]
    h_pred = float(z[-1] + max(dz[-1], 0) ** 2 / (2 * 9.81))
    d = mujoco.MjData(mfb)
    q1m0 = -q1c[0] - np.pi / 2; q2m0 = -q2c[0]
    d.qpos[:] = [float(z[0]), q1m0, q2m0, -q2m0, q2m0]
    d.qvel[:] = 0.0
    mujoco.mj_forward(mfb, d)
    dt = mfb.opt.timestep; T_SET = 0.4
    N = int((T_SET + t[-1] + 0.9) / dt) + 1
    tl = np.zeros(N); q = np.zeros((N, 3)); grf = np.zeros(N)
    for k in range(N):
        tc = k * dt
        if tc < T_SET:
            th = S.SETTLE_KP * (q1m0 - d.qpos[1]) + S.SETTLE_KD * (-d.qvel[1])
            tk = S.SETTLE_KP * (q2m0 - d.qpos[2]) + S.SETTLE_KD * (-d.qvel[2])
        elif tc < T_SET + t[-1]:
            tm = tc - T_SET
            th = float(np.interp(tm, t, -tau1)); tk = float(np.interp(tm, t, -tau2))
        else:
            th = tk = 0.0
        d.ctrl[:] = [th, tk]
        mujoco.mj_step(mfb, d)
        tl[k] = tc - T_SET
        q[k] = [d.qpos[0], d.qpos[1], d.qpos[2]]
        gz = 0.0
        for c in range(d.ncon):
            cf = np.zeros(6)
            mujoco.mj_contactForce(mfb, d, c, cf)
            gz += (d.contact[c].frame.reshape(3, 3).T @ cf[:3])[2]
        grf[k] = gz
    print(f"twin replay apex: {q[:,0].max():.3f} m (NLP pred {h_pred:.3f})")
    npz_path = TMP / "nlp_optimal.npz"
    np.savez(npz_path, t=tl, q=q, grf_z=grf)
    gif = OUT_DIR / "nlp_optimal_jump.gif"
    _mauc.make_anim_universal_colored(str(npz_path), str(xml_path), str(gif),
                                      trial_label="NLP optimal (pred)",
                                      h_real_m=h_pred)
    print("DONE ->", gif)


if __name__ == "__main__":
    main()
