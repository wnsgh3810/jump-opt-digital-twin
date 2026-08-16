"""sit2stand animator — v13 rev2 fix (real-time pace + foot-on-floor + plot cp).

Fixes vs v13 rev1:
  1) Speed unification: n_frames = clamp(30, 200, round(cyc_dur / 0.04))
     → 40ms of physical time per gif frame (real-time playback at 25fps).
     Every cycle in every dataset appears at the same natural pace.
  2) GND foot-on-floor: ignore canonical base_z_sim (which goes negative in
     places, causing floor penetration). Compute base_z per frame such that
     foot bottom sits at z=0.001 via mj_forward + foot geom position.
  3) AIR unchanged: base_z=0.55 shim (fixed, air mode display).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import mujoco
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
try:
    FONT = ImageFont.truetype(str(FONT_PATH), 24)
except Exception:
    FONT = ImageFont.load_default()

# ── Uniform pace ────────────────────────────────────────────────────────────
DT_FRAME_S = 0.040        # 40ms per gif frame → 25fps display
PHYS_DT_PER_FRAME = 0.040  # 40ms of physical time per frame → real-time playback
N_MIN = 30
N_MAX = 200               # cap at 8s playback (200 × 40ms)
DURATION_MS = int(DT_FRAME_S * 1000)

REF_RGBA = {
    'base':  (0.5, 0.5, 0.5, 1.0),
    'thigh': (0.6, 0.6, 0.7, 1.0),
    'calf':  (0.5, 0.6, 0.6, 1.0),
    'foot':  (0.5, 0.5, 0.5, 1.0),
}


def _override_rgba(model: mujoco.MjModel):
    for gid in range(model.ngeom):
        body_id = int(model.geom_bodyid[gid])
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        if geom_name == 'floor':
            continue
        if geom_name == 'foot':
            model.geom_rgba[gid] = REF_RGBA['foot']
            model.geom_matid[gid] = -1
            continue
        if body_name in REF_RGBA:
            model.geom_rgba[gid] = REF_RGBA[body_name]
            model.geom_matid[gid] = -1


def _draw_text_outlined(draw, pos, text, font, fill='white', stroke=2):
    x, y = pos
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, fill='black', font=font)
    draw.text(pos, text, fill=fill, font=font)


def render_sit2stand(
    canon_npz_path: str,
    model_xml_path: str,
    out_gif_path: str,
    trial_label: str,
    kind: str,   # 'air' or 'gnd'
):
    """Render sit2stand cycle with jump-style visuals + real-time pace.

    - Apply coord conversion: mj_q1 = -q1_canonical - π/2, mj_q2 = -q2_canonical.
    - Real-time pace: physical_dt=40ms per frame → 25fps display = real-time playback.
    - AIR: base_z=0.55 fixed shim, overlay "base = 0 (air, fixed)".
    - GND: compute base_z per frame so foot bottom sits at z≈0 (no penetration).
    """
    d = np.load(canon_npz_path)
    t_full = d['t_sim']
    q1c = d['q1_sim']
    q2c = d['q2_sim']
    N_full = len(t_full)
    cyc_dur = float(t_full[-1] - t_full[0])

    # Coord conversion + wrap to (-π, +π] to avoid sim-divergence unwrap
    # artifacts (canonical GND has q ranges >2π in later frames when the
    # underlying PD sim lost tracking — wrapping restores physically-valid
    # visual pose).
    def _wrap_pi(x):
        return ((x + np.pi) % (2 * np.pi)) - np.pi
    mj_q1_all = _wrap_pi(-q1c - np.pi / 2)
    mj_q2_all = _wrap_pi(-q2c)

    # ── Uniform real-time pace ─────────────────────────────────────────────
    n_frames = min(N_MAX, max(N_MIN, int(round(cyc_dur / PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, N_full - 1, n_frames).astype(int)

    # ── Load model, override colors ────────────────────────────────────────
    xml_raw = Path(model_xml_path).read_text(encoding='utf-8')
    model = mujoco.MjModel.from_xml_string(xml_raw)
    _override_rgba(model)
    data = mujoco.MjData(model)

    foot_gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, 'foot')
    foot_radius = float(model.geom_size[foot_gid, 0])  # cylinder radius

    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0
    cam.elevation = -15.0
    cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])

    frames = []
    with mujoco.Renderer(model, width=640, height=480) as renderer:
        for idx in idxs:
            mj_q1 = float(mj_q1_all[idx])
            mj_q2 = float(mj_q2_all[idx])

            if kind == 'gnd':
                # Let MuJoCo settle base via gravity + floor contact.
                # PD holds hip/knee at target while base slides down onto floor.
                data.qpos[0] = 0.6   # closer to expected landing → faster settle
                data.qpos[1] = mj_q1
                data.qpos[2] = mj_q2
                data.qvel[:] = 0.0
                for _ in range(1500):
                    data.ctrl[0] = 1000.0 * (mj_q1 - data.qpos[1]) \
                                   - 50.0 * data.qvel[1]
                    data.ctrl[1] = 1000.0 * (mj_q2 - data.qpos[2]) \
                                   - 50.0 * data.qvel[2]
                    mujoco.mj_step(model, data)
                base_z_shown = float(data.qpos[0])
            else:  # 'air'
                data.qpos[0] = 0.55
                data.qpos[1] = mj_q1
                data.qpos[2] = mj_q2
                data.qvel[:] = 0.0
                mujoco.mj_forward(model, data)
                base_z_shown = 0.55

            renderer.update_scene(data, camera=cam)
            rgb = renderer.render()
            img = Image.fromarray(rgb)
            draw = ImageDraw.Draw(img)

            t_ms = (t_full[idx] - t_full[0]) * 1000.0
            hip_deg = np.rad2deg(mj_q1)
            knee_deg = np.rad2deg(mj_q2)

            _draw_text_outlined(draw, (10, 10),
                                f'trial = {trial_label}', FONT, fill='white')
            _draw_text_outlined(draw, (10, 40),
                                f't = {t_ms:>6.0f} ms', FONT)
            if kind == 'air':
                _draw_text_outlined(draw, (10, 70),
                                    f'base = 0 (air, fixed)',
                                    FONT, fill='#00ffff')
            else:
                _draw_text_outlined(draw, (10, 70),
                                    f'base_z = {base_z_shown*100:>5.1f} cm',
                                    FONT, fill='#00ffff')
            _draw_text_outlined(draw, (10, 100),
                                f'hip  = {hip_deg:+6.1f}°', FONT, fill='#00ff00')
            _draw_text_outlined(draw, (10, 130),
                                f'knee = {knee_deg:+6.1f}°', FONT, fill='#ff8800')
            frames.append(img)

    frames[0].save(
        str(out_gif_path),
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=False,
    )
    return dict(n_frames=len(frames), cyc_dur=cyc_dur,
                playback_s=len(frames) * DT_FRAME_S)
