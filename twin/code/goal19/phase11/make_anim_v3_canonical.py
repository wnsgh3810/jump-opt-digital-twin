"""GOAL19 — render all v3 jump sims with the CANONICAL renderer (no custom rendering).

Uses goal18_v9/_make_anim_universal_colored.py :: make_anim_universal_colored — the
locked jump animation standard (v3 P60 canonical look: 640x480, 60 frames, 40ms,
iso camera, forced reference palette, trial/t/base_z/GRF/h_sim/h_real overlay).
This script ONLY produces the inputs (v3 sim log npz + v3 XML) and calls the module.
An archived copy of the renderer lives at code/goal19/canonical_render/ for durability;
the ORIGINAL at CVT/jump_opt/goal18_v9/ remains the reference.
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
import mshoot as MS
import mshoot_refit as R
from load_31exp import list_experiments

CANON = Path((LEGACY_ROOT + "/goal18_v9/_make_anim_universal_colored.py"))
spec = importlib.util.spec_from_file_location("_mauc", str(CANON))
_mauc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mauc)

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else (REPO / "code/goal19/phase11/anim_v3")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix="anim_v3_"))


def main():
    fbj = REPO / "code/goal19/phase11/fourbar_refit_best.json"
    if fbj.exists():
        import mshoot_fourbar as FB
        best = json.load(open(fbj, encoding="utf-8"))
        d = dict(zip(best["names"], best["x"]))
        S.FV_HIP = d["fv_hip"]; S.FV_KNEE = d["fv_knee"]; S.FC_HIP = d["fc_hip"]; S.FC_KNEE = d["fc_knee"]
        S.SOLREF_TC_LOCK = d["solref_tc"]; S.IMP0_LOCK = d["imp0"]
        S.STIFF_HIP = 0.0; S.STIFF_KNEE = d["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
        globals()["_FB"] = (FB, d)
    else:
        best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
        d = R.set_params(np.array(best["x"]))
        globals()["_FB"] = None
    xml = S.build_xml_jump_6d(0.0, d["arm_knee"])
    xml_path = TMP / "leg_v3.xml"
    xml_path.write_text(xml, encoding="utf-8")

    jobs = [(ds, sub, MS.LOADERS[ds](sub)) for ds, sub, isj in list_experiments()
            if isj and ds in MS.LOADERS]
    for mds, tdir, subs in MS.MARCH:
        for sub in subs:
            jobs.append((mds, sub, MS.load_march(tdir, sub)))
    print(f"rendering {len(jobs)} jump anims with CANONICAL make_anim_universal_colored...")
    model = mujoco.MjModel.from_xml_string(xml)
    fb = globals().get("_FB")
    mfb = mujoco.MjModel.from_xml_string(fb[0].build_xml_fourbar_jump(fb[1]["arm_knee"], fb[1])) if fb else None
    for ds, sub, td in jobs:
        try:
            if fb:
                fl = fb[0].run_jump_sim_fourbar(mfb, td)
                if fl is None:
                    print(f"  {ds}/{sub}: sim FAIL"); continue
                log = dict(t=fl["t"], q=np.column_stack([fl["base_z"], fl["q1"], fl["q2"]]),
                           grf_z=fl["grf_z"])
            else:
                log = S.run_jump_sim(model, td, 0, 0, motor_tm=0.0)
                if log is None:
                    print(f"  {ds}/{sub}: sim FAIL"); continue
            npz_path = TMP / f"{ds}_{sub}.npz".replace("/", "_")
            np.savez(npz_path, t=log["t"], q=log["q"], grf_z=log["grf_z"])
            gif = OUT_DIR / f"{ds}_{sub}.gif".replace("/", "_")
            _mauc.make_anim_universal_colored(
                str(npz_path), str(xml_path), str(gif),
                trial_label=f"{ds.replace('jump_','')}/{sub}",
                h_real_m=float(td["h_real"]))
            print(f"  {ds}/{sub}: {gif.name}")
        except Exception as e:
            print(f"  {ds}/{sub}: ERROR {e}")
    print("DONE ->", OUT_DIR)


if __name__ == "__main__":
    main()
