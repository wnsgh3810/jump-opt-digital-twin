"""Universal make_anim wrapper (v9) — forces v3 P60 build_xml_i38 REFERENCE visuals.

Origin
------
Same body/API as goal18_v8/_make_anim_universal.py. Only difference: right
before rendering, the loaded XML is patched so it matches the canonical
v3 P60 reference render (goal12/iter38/run_i38.py :: build_xml_i38(...)):

  <asset>  skybox gradient + groundplane checker texture + groundplane material
  <visual> headlight diffuse 0.6 / ambient 0.3 / specular 0
  <light>  directional light in worldbody
  <geom rgba>  base=(0.5 0.5 0.5), thigh=(0.6 0.6 0.7), calf=(0.5 0.6 0.6),
              foot=(0.5 0.5 0.5), floor=material=groundplane

Motivation
----------
User found P100_D0.75_P100_D2 GIFs had olive-green (74,148,97) and rust-red
(121,61,29) links because goal18_v4's leg_iter6.xml chose rgba=(0.8 0.4 0.2)
for thigh and (0.4 0.7 0.4) for calf — those diverge from the v3 P60 canonical
render. v9 clamps every rendered XML back to the reference palette regardless
of what the source XML specifies, and injects the reference asset/visual
blocks if they are missing (which is the case for sub_sim_6d.build_xml_jump_6d
based XMLs used by many goal18_v4+ trials).

Override method
---------------
Two-stage (XML sed + geom_rgba array setter):
  1. Text patch on XML string: inject <asset>, <visual>, and <light> from the
     reference if the source XML lacks them; force floor geom to reference
     material="groundplane".
  2. After MjModel.from_xml_string, set model.geom_rgba[i] per-geom by body
     name so any color specified in the source XML is overridden regardless
     of whether it was present or not.

Kind (air / gnd / jump) invariant — every geom on every source XML is unified.
"""
from pathlib import Path
import re
import numpy as np
import mujoco
from PIL import Image, ImageDraw, ImageFont

# ---- v3 P60 canonical spec (matches goal12/iter38/run_i38.py build_xml_i38) ----
FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
N_FRAMES = 60
DURATION_MS = 40  # 25 fps
try:
    FONT = ImageFont.truetype(str(FONT_PATH), 24)
except Exception:
    FONT = ImageFont.load_default()


# ============================================================================
#  Reference visual spec (verbatim from build_xml_i38)
# ============================================================================
REF_ASSET_BLOCK = (
    '<asset>'
    '<texture type="skybox" builtin="gradient" '
    'rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>'
    '<texture type="2d" name="groundplane" builtin="checker" mark="edge" '
    'rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" '
    'width="300" height="300"/>'
    '<material name="groundplane" texture="groundplane" texuniform="true" '
    'texrepeat="5 5" reflectance="0.2"/>'
    '</asset>'
)
REF_VISUAL_BLOCK = (
    '<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" '
    'specular="0 0 0"/></visual>'
)
REF_LIGHT = '<light pos="0 0 1.5" dir="0 0 -1" directional="true"/>'

REF_RGBA = {
    'base':  (0.5, 0.5, 0.5, 1.0),
    'thigh': (0.6, 0.6, 0.7, 1.0),
    'calf':  (0.5, 0.6, 0.6, 1.0),
    'foot':  (0.5, 0.5, 0.5, 1.0),
}


def _patch_xml_string(xml_str: str) -> str:
    """Inject missing asset/visual/light + force floor material.

    Idempotent: skips blocks that are already present. Safe to call on
    already-canonical XML (v3 P60 build_xml_i38 output) — passes through
    unchanged.
    """
    # (1) Ensure <asset> exists — inject before <worldbody> if absent.
    if '<asset>' not in xml_str and '<asset/>' not in xml_str:
        xml_str = xml_str.replace('<worldbody>', REF_ASSET_BLOCK + '<worldbody>', 1)
    else:
        # asset exists but might lack skybox/groundplane texture/material.
        # Only inject material="groundplane" texture pair if not already there.
        if 'name="groundplane"' not in xml_str:
            xml_str = re.sub(r'(<asset>)', r'\1' + REF_ASSET_BLOCK[len('<asset>'):-len('</asset>')], xml_str, count=1)
        if 'type="skybox"' not in xml_str:
            skybox_snippet = (
                '<texture type="skybox" builtin="gradient" '
                'rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>'
            )
            xml_str = re.sub(r'(<asset>)', r'\1' + skybox_snippet, xml_str, count=1)

    # (2) Ensure <visual> block exists — inject before <worldbody> if absent.
    if '<visual>' not in xml_str and '<visual/>' not in xml_str:
        xml_str = xml_str.replace('<worldbody>', REF_VISUAL_BLOCK + '<worldbody>', 1)

    # (3) Ensure worldbody has a directional light (skip if any <light exists).
    if '<light ' not in xml_str and '<light/>' not in xml_str:
        xml_str = xml_str.replace('<worldbody>', '<worldbody>' + REF_LIGHT, 1)

    # (4) Force floor geom to use material="groundplane".
    # Handles both <geom name="floor" .../> and <geom name="floor" ...></geom>.
    def _add_floor_material(m):
        tag = m.group(0)
        if 'material=' in tag:
            # Replace any existing material with groundplane.
            tag = re.sub(r'material="[^"]*"', 'material="groundplane"', tag)
        else:
            tag = tag[:-2] + ' material="groundplane"/>' if tag.rstrip().endswith('/>') \
                  else re.sub(r'(<geom\s+name="floor"[^>]*?)>', r'\1 material="groundplane">', tag)
        return tag
    xml_str = re.sub(r'<geom\s+name="floor"[^/]*?/>', _add_floor_material, xml_str)

    return xml_str


def _override_geom_rgba(model: mujoco.MjModel) -> dict:
    """After loading model, set geom_rgba on each body-associated geom to
    the reference palette. Returns a summary of overrides for debug.
    """
    summary = {}
    for gid in range(model.ngeom):
        body_id = int(model.geom_bodyid[gid])
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        # Floor: leave to material (groundplane) — keep matid intact.
        if geom_name == 'floor':
            summary[f'geom[{gid}] (floor)'] = 'material=groundplane (unchanged)'
            continue
        # foot: dedicated palette entry
        if geom_name == 'foot':
            model.geom_rgba[gid] = REF_RGBA['foot']
            model.geom_matid[gid] = -1  # kill any material override
            summary[f'geom[{gid}] (foot)'] = REF_RGBA['foot']
            continue
        # body-based dispatch
        if body_name in REF_RGBA:
            model.geom_rgba[gid] = REF_RGBA[body_name]
            model.geom_matid[gid] = -1
            summary[f'geom[{gid}] (body={body_name})'] = REF_RGBA[body_name]
    return summary


def draw_text_outlined(draw, pos, text, font, fill='white', stroke_width=2):
    """v3 verbatim: black stroke ring + colored fill for readability on any bg."""
    x, y = pos
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, fill='black', font=font)
    draw.text(pos, text, fill=fill, font=font)


def make_anim_universal_colored(
    npz_path: str,
    model_xml_path: str,
    out_gif_path: str,
    trial_label: str,
    h_real_m: float = 0.0,
):
    """Render sim playback GIF with v3 P60 canonical visuals forced.

    Args:
        npz_path       : sim log .npz (must have 't', 'q' [N,3], 'grf_z' [N]).
        model_xml_path : MuJoCo XML path (any kind: jump / sit2stand).
        out_gif_path   : output .gif path (parent dir must exist).
        trial_label    : shown on overlay line 1.
        h_real_m       : real jump height in meters (0.0 for sit2stand).
    """
    log = np.load(npz_path)
    t_arr = log['t']
    q_arr = log['q']
    grf_arr = log['grf_z']
    N = q_arr.shape[0]

    idxs = np.linspace(0, N - 1, min(N_FRAMES, N)).astype(int)
    post_zero = t_arr >= 0.0
    h_sim = q_arr[post_zero, 0].max() if post_zero.any() else q_arr[:, 0].max()

    # -- load + patch + rgba override -----------------------------------------
    xml_raw = Path(model_xml_path).read_text(encoding='utf-8')
    xml_patched = _patch_xml_string(xml_raw)
    model = mujoco.MjModel.from_xml_string(xml_patched)
    _override_geom_rgba(model)

    data = mujoco.MjData(model)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0
    cam.elevation = -15.0
    cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])

    frames = []
    with mujoco.Renderer(model, width=640, height=480) as renderer:
        for idx in idxs:
            data.qpos[:] = q_arr[idx]
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=cam)
            rgb = renderer.render()
            img = Image.fromarray(rgb)
            draw = ImageDraw.Draw(img)

            t_ms = t_arr[idx] * 1000.0
            base_z_cm = q_arr[idx, 0] * 100.0
            grf_val = grf_arr[idx]

            draw_text_outlined(draw, (10, 10),  f'trial = {trial_label}',        FONT, fill='white')
            draw_text_outlined(draw, (10, 40),  f't = {t_ms:>6.0f} ms',           FONT)
            draw_text_outlined(draw, (10, 70),  f'base_z = {base_z_cm:>5.1f} cm', FONT, fill='#00ffff')
            draw_text_outlined(draw, (10, 100), f'GRF = {grf_val:>6.1f} N',       FONT, fill='#ffff00')
            draw_text_outlined(draw, (10, 130), f'h_sim = {h_sim*100:.1f} cm',    FONT, fill='#00ff00')
            draw_text_outlined(draw, (10, 160), f'h_real = {h_real_m*100:.1f} cm',FONT, fill='#ff8800')
            frames.append(img)

    frames[0].save(
        str(out_gif_path),
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=False,
    )
    return str(out_gif_path)


# Backwards-compat alias: callers of v8 make_anim_universal can switch by
# importing this name.
make_anim_universal = make_anim_universal_colored


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 5:
        print("Usage: python _make_anim_universal_colored.py <npz> <xml> <out_gif> <trial_label> [h_real_m]")
        sys.exit(2)
    npz, xml, out, lbl = sys.argv[1:5]
    hr = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    p = make_anim_universal_colored(npz, xml, out, lbl, hr)
    print(json.dumps({"out": p}, indent=2))
