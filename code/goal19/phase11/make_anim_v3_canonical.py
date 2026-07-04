"""GOAL19 — render all v3 jump sims with the CANONICAL renderer (no custom rendering).

Uses goal18_v9/_make_anim_universal_colored.py :: make_anim_universal_colored — the
locked jump animation standard (v3 P60 canonical look: 640x480, 60 frames, 40ms,
iso camera, forced reference palette, trial/t/base_z/GRF/h_sim/h_real overlay).
This script ONLY produces the inputs (v3 sim log npz + v3 XML) and calls the module.
An archived copy of the renderer lives at code/goal19/canonical_render/ for durability;
the ORIGINAL at Desktop/jump_opt/goal18_v9/ remains the reference.
"""
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

CANON = Path("C:/Users/junho/Desktop/jump_opt/goal18_v9/_make_anim_universal_colored.py")
spec = importlib.util.spec_from_file_location("_mauc", str(CANON))
_mauc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mauc)

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else (REPO / "code/goal19/phase11/anim_v3")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix="anim_v3_"))


def main():
    best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    d = R.set_params(np.array(best["x"]))
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
    for ds, sub, td in jobs:
        try:
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
