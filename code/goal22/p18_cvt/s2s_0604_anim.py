# -*- coding: utf-8 -*-
"""P18c — 0604 s2s CL GIF (canonical 규격, l_i별 모델)."""
import sys, json
import numpy as np
from pathlib import Path
import mujoco
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA
import p14_judge as J
from cvt_anim import build_anim_model

DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_s2s_0604_results/gif")
DST.mkdir(parents=True, exist_ok=True)


def render(model, z, out, label):
    t = z["t"]
    m = t >= -0.05
    t = t[m]
    q1 = z["q1"][m]; qc = z["q2"][m]; qk = z["qk"][m]; qp = z["qpin"][m]; bz = z["bz"][m]
    wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
    mj1 = wrap(-q1 - np.pi / 2); mjc = wrap(-qc)
    dur = float(t[-1] - t[0])
    n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(t) - 1, n).astype(int)
    data = mujoco.MjData(model)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])
    frames = []
    with mujoco.Renderer(model, width=640, height=480) as ren:
        for i in idxs:
            data.qpos[:] = [float(bz[i]), float(mj1[i]), float(mjc[i]),
                            float(qp[i]), float(qk[i])]
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            MA._draw_text_outlined(dr, (10, 10), f"trial = {label}", MA.FONT, fill="white")
            MA._draw_text_outlined(dr, (10, 40), f"t = {t[i]*1000:>6.0f} ms", MA.FONT)
            MA._draw_text_outlined(dr, (10, 70), f"base_z = {bz[i]*100:>5.1f} cm", MA.FONT, fill="#00ffff")
            MA._draw_text_outlined(dr, (10, 100), f"l_i = {float(z['l_i'])*1000:.1f} mm", MA.FONT, fill="#ffaa00")
            frames.append(img)
    frames[0].save(str(out), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)


def main():
    J.winit()
    models = {}
    for f in sorted((HERE / "traj_0604").glob("*__CL.npz")):
        z = np.load(f)
        li = round(float(z["l_i"]), 4)
        if li not in models:
            models[li] = build_anim_model(li)
        name = f.stem
        render(models[li], z, DST / (name + ".gif"), f"0604 {name.replace('__CL', '')} [CL]")
        print("gif", name, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
