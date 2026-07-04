"""GOAL19 — render all v3 jump simulations as GIFs (canonical visual conventions).

Follows goal18_CANONICAL make_anim conventions: 40ms of physical time per frame
(25fps = real-time playback), same camera (azimuth 135, elev -15), same body colors,
coord handling native (sim logs are already in mj frame). Jumps need base flight, so
base_z comes from the v3 sim itself (the canonical s2s renderer pins the foot — wrong
for jumps; this adapter keeps every visual convention but frees the base).
Overlay: trial name + h_sim / h_cam.
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import mujoco
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "code/goal19/phase11"))
for p in ["templates", "data_loaders", "phase1", "phase2", "phase3", "phase4"]:
    sys.path.insert(0, str(REPO / "code/goal19" / p))
import sub_sim_iter6v2 as S
import mshoot as MS
import mshoot_refit as R
from load_31exp import list_experiments

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else (REPO / "code/goal19/phase11/anim_v3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHYS_DT_PER_FRAME = 0.040   # canonical: 40ms physical per frame -> real-time at 25fps
DUR_MS = 40
REF_RGBA = {'base': (0.5, 0.5, 0.5, 1.0), 'thigh': (0.6, 0.6, 0.7, 1.0),
            'calf': (0.5, 0.6, 0.6, 1.0), 'foot': (0.5, 0.5, 0.5, 1.0)}
try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 22)
except Exception:
    FONT = ImageFont.load_default()


def _override_rgba(model):
    for gid in range(model.ngeom):
        bid = int(model.geom_bodyid[gid])
        bname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid)
        gname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        if gname == 'floor':
            continue
        if gname == 'foot':
            model.geom_rgba[gid] = REF_RGBA['foot']; model.geom_matid[gid] = -1
        elif bname in REF_RGBA:
            model.geom_rgba[gid] = REF_RGBA[bname]; model.geom_matid[gid] = -1


def _text(draw, pos, s):
    x, y = pos
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            if dx or dy:
                draw.text((x + dx, y + dy), s, font=FONT, fill='black')
    draw.text((x, y), s, font=FONT, fill='white')


def render_jump(ds, sub, td, arm_knee):
    xml = S.build_xml_jump_6d(0.0, arm_knee)
    model = mujoco.MjModel.from_xml_string(xml)
    log = S.run_jump_sim(model, td, 0, 0, motor_tm=0.0)
    if log is None:
        print(f"  {ds}/{sub}: sim FAIL"); return None
    # motion start (t=0) to apex + 0.3s
    t = log["t"]; q = log["q"]
    i_apex = int(np.argmax(q[:, 0]))
    m0 = np.searchsorted(t, 0.0)
    m1 = min(len(t) - 1, np.searchsorted(t, t[i_apex] + 0.3))
    seg_t = t[m0:m1]; seg_q = q[m0:m1]
    n_frames = min(200, max(30, int(round((seg_t[-1] - seg_t[0]) / PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(seg_t) - 1, n_frames).astype(int)
    rmodel = mujoco.MjModel.from_xml_string(xml)
    _override_rgba(rmodel)
    rdata = mujoco.MjData(rmodel)
    cam = mujoco.MjvCamera()
    cam.azimuth, cam.elevation, cam.distance = 135.0, -15.0, 1.9
    cam.lookat[:] = [0.0, 0.0, 0.55]
    h_sim = float(q[:, 0].max()); h_cam = float(td["h_real"])
    frames = []
    with mujoco.Renderer(rmodel, height=480, width=480) as ren:
        for i in idxs:
            rdata.qpos[:] = seg_q[i]
            mujoco.mj_forward(rmodel, rdata)
            ren.update_scene(rdata, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            _text(dr, (10, 8), f"{ds.replace('jump_','')}/{sub}")
            _text(dr, (10, 38), f"h_sim {h_sim:.2f} m   h_cam {h_cam:.2f} m")
            _text(dr, (10, 445), f"t = {seg_t[i]:.2f} s  (real-time)")
            frames.append(img)
    gif = OUT_DIR / f"{ds}_{sub}.gif".replace("/", "_")
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=DUR_MS, loop=0)
    print(f"  {ds}/{sub}: {gif.name} ({len(frames)} frames, h_sim={h_sim:.2f})")
    return gif


def main():
    best = json.load(open(REPO / "code/goal19/phase11/mshoot_refit_best.json", encoding="utf-8"))
    d = R.set_params(np.array(best["x"]))
    jobs = [(ds, sub, MS.LOADERS[ds](sub)) for ds, sub, isj in list_experiments()
            if isj and ds in MS.LOADERS]
    for mds, tdir, subs in MS.MARCH:
        for sub in subs:
            jobs.append((mds, sub, MS.load_march(tdir, sub)))
    print(f"rendering {len(jobs)} jump animations (v3, canonical conventions)...")
    for ds, sub, td in jobs:
        try:
            render_jump(ds, sub, td, d["arm_knee"])
        except Exception as e:
            print(f"  {ds}/{sub}: ERROR {e}")
    print("DONE ->", OUT_DIR)


if __name__ == "__main__":
    main()
