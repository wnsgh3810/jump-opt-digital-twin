# -*- coding: utf-8 -*-
"""P13 — 4-bar linkage explainer animation: crank/coupler/rocker visible.
Flipped (correct) phase, P10-selected params, full replay of representative
trials. Side view so the linkage plane is fully visible. Colors: crank green,
coupler red, rocker purple-ish (calf-side lever is part of calf body — mark via
site sphere), thigh/calf steel/orange.
NOTE: this is a STRUCTURE-explainer visualization, NOT a replacement of the
locked goal18 canonical result-animation pipeline (which stays serial leg.xml).
"""
import sys, json
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUT = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_fourbar_flip as FL
FL.winit()
mujoco = FL._G["mujoco"]; S = FL._G["S"]; FB = FL._G["FB"]
import mshoot as MS

CANON = json.load(open(REPO / "code/goal21/fourbar_flip_canonical.json"))
NAMES = CANON["names"]; dd = dict(zip(NAMES, CANON["x"]))
S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0

xml = FL.build_xml_fourbar_flip(dd["arm_knee"], dd)
# visual emphasis (render copy only)
xml = xml.replace('<geom type="capsule" size="0.02" ', '<geom type="capsule" size="0.02" rgba="0.55 0.6 0.68 1" ')
xml = xml.replace('<geom type="capsule" size="0.015" ', '<geom type="capsule" size="0.015" rgba="0.85 0.55 0.25 1" ')
xml = xml.replace('<geom type="capsule" size="0.008" ', '<geom type="capsule" size="0.012" rgba="0.15 0.75 0.25 1" ')
xml = xml.replace('<geom type="capsule" size="0.006" ', '<geom type="capsule" size="0.009" rgba="0.85 0.15 0.15 1" ')
xml = xml.replace('<geom type="box" size="0.06 0.03 0.025" ', '<geom type="box" size="0.06 0.03 0.025" rgba="0.5 0.52 0.58 0.28" ')
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

try:
    FONT = ImageFont.truetype("malgun.ttf", 17)
    FONT_S = ImageFont.truetype("malgun.ttf", 13)
except Exception:
    FONT = FONT_S = ImageFont.load_default()


def outline(draw, pos, text, font, fill="white"):
    x, y = pos
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            draw.text((x + dx, y + dy), text, font=font, fill="black")
    draw.text(pos, text, font=font, fill=fill)


def render_trial(ds, sub, loader, out_name):
    td = loader(sub)
    log = FB.run_jump_sim_fourbar(model, td)     # flip-patched builder inside? no — pass model states
    # run_jump_sim_fourbar builds nothing; it uses the model we pass ✓
    t = log["t"]; bz = log["base_z"]; q1 = log["q1"]; q2 = log["q2"]
    mk = t >= -0.15
    t, bz, q1, q2 = t[mk], bz[mk], q1[mk], q2[mk]
    n_frames = max(30, min(120, int(round((t[-1] - t[0]) / 0.04))))
    idxs = np.linspace(0, len(t) - 1, n_frames).astype(int)
    cam = mujoco.MjvCamera()
    cam.azimuth = 100.0; cam.elevation = -10.0; cam.distance = 1.35
    cam.lookat = np.array([0.0, 0.0, 0.35])
    frames = []
    with mujoco.Renderer(model, width=560, height=460) as ren:
        for i in idxs:
            data.qpos[:] = [bz[i], q1[i], q2[i], -q2[i], q2[i]]
            data.qvel[:] = 0
            mujoco.mj_forward(model, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            d = ImageDraw.Draw(img)
            outline(d, (10, 8), f"4-bar 구조 애니메이션 — {ds} {sub}", FONT)
            outline(d, (10, 32), f"t = {t[i]:+.2f} s   knee(q2) = {np.degrees(-q2[i]):.0f}° (canonical)", FONT_S)
            outline(d, (10, 52), "초록 crank = l_i 30mm (정강이 반대방향)", FONT_S, fill="#4ce06a")
            outline(d, (10, 70), "빨강 coupler 250mm (thigh와 평행)", FONT_S, fill="#ff6a6a")
            outline(d, (10, 88), "rocker = 무릎 위/뒤 30mm (coupler 끝 결합점)", FONT_S, fill="#dddddd")
            frames.append(img.quantize(colors=128, method=Image.MEDIANCUT))
    gif = OUT / out_name
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=40, loop=0, optimize=True)
    print("saved", gif.name, f"{gif.stat().st_size/1e6:.2f} MB", flush=True)
    return gif


g1 = render_trial("jump_0424", "120_2_120_2", MS.LOADERS["jump_0424"], "fourbar_anim_0424.gif")
g2 = render_trial("jump_0602", "120_2_120_2", MS.LOADERS["jump_0602"], "fourbar_anim_0602.gif")
print("DONE")
