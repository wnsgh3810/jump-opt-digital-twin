"""P10-A3 — 폐루프 재현 sim의 canonical 규격 애니메이션.

시각 표준 = goal18_CANONICAL/make_anim.py (LOCKED): 좌표 변환 mj_q1=-q1c-π/2,
wrap(-π,π], 40ms/frame 실시간 페이스, 640x480, REF_RGBA 색, 흰 아웃라인 오버레이.
점프이므로 base_z는 폐루프 sim의 실제 값을 그대로 사용 (locked 'gnd' 모드의
foot-on-floor 보정은 stance 전용 — 우리 sim은 접촉 정상이라 관통 없음).
"""
import sys
import numpy as np
from pathlib import Path
import mujoco
from PIL import Image, ImageDraw

sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA

CANON_XML = Path("C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/leg.xml")
TRAJ = Path(__file__).parent / "p10_cl_traj"
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
GIFD = SCR / "g22_cl_gallery" / "gif"; GIFD.mkdir(parents=True, exist_ok=True)


def render_jump_cl(npz_path, out_gif, label):
    d = np.load(npz_path)
    t = d["t"]; q1c = d["q1"]; q2c = d["q2"]; bz = d["bz"]
    m = t >= -0.05
    t = t[m]; q1c = q1c[m]; q2c = q2c[m]; bz = bz[m]
    wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
    mj1 = wrap(-q1c - np.pi / 2); mj2 = wrap(-q2c)
    dur = float(t[-1] - t[0])
    n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(t) - 1, n).astype(int)
    model = mujoco.MjModel.from_xml_string(CANON_XML.read_text(encoding="utf-8"))
    MA._override_rgba(model)
    data = mujoco.MjData(model)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])
    h_apex = float(bz.max())
    frames = []
    with mujoco.Renderer(model, width=640, height=480) as ren:
        for i in idxs:
            data.qpos[0] = float(bz[i])
            data.qpos[1] = float(mj1[i]); data.qpos[2] = float(mj2[i])
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            MA._draw_text_outlined(dr, (10, 10), f"trial = {label}", MA.FONT, fill="white")
            MA._draw_text_outlined(dr, (10, 40), f"t = {t[i]*1000:>6.0f} ms", MA.FONT)
            MA._draw_text_outlined(dr, (10, 70), f"base_z = {bz[i]*100:>5.1f} cm", MA.FONT, fill="#00ffff")
            MA._draw_text_outlined(dr, (10, 100), f"hip  = {np.degrees(mj1[i]):+6.1f}°", MA.FONT, fill="#00ff00")
            MA._draw_text_outlined(dr, (10, 130), f"knee = {np.degrees(mj2[i]):+6.1f}°", MA.FONT, fill="#ff8800")
            MA._draw_text_outlined(dr, (10, 160), f"h_apex = {h_apex:.3f} m", MA.FONT, fill="#ffff00")
            frames.append(img)
    frames[0].save(str(out_gif), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)
    return len(frames)


def main():
    files = sorted(TRAJ.glob("*.npz"))
    print(f"{len(files)} trajs", flush=True)
    for f in files:
        name = f.stem            # ds__sub__tag
        out = GIFD / (name + ".gif")
        n = render_jump_cl(f, out, name.replace("__", " / "))
        print("gif", name, n, "frames", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
