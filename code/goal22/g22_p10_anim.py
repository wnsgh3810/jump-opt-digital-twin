"""P10-A3 v2 — 폐루프 재현 sim의 canonical 규격 애니메이션, 4-bar 링키지 렌더.

시각 표준 = goal18_CANONICAL/make_anim.py (LOCKED): 40ms/frame 실시간 페이스,
640x480, 카메라(az135/el-15/d1.2), REF_RGBA 색, 흰 아웃라인 오버레이 — 전부 유지.
변경 (사용자 07-09): 모델 = P13h 4-bar flip XML (crank/coupler 링키지 표시).
qpos = [bz, q1, q2, -q2, q2] (평행사변형), base_z는 폐루프 sim 값 그대로.
"""
import sys, json
import numpy as np
from pathlib import Path
import mujoco
from PIL import Image, ImageDraw

sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code/goal21"))
import g21_p13e_honest as PH
import g21_p13_linkage as P13

TRAJ = Path(__file__).parent / "p10_cl_traj"
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
GIFD = SCR / "g22_cl_gallery" / "gif"; GIFD.mkdir(parents=True, exist_ok=True)

LINK_RGBA = dict(MA.REF_RGBA)
LINK_RGBA["crank"] = (0.85, 0.45, 0.10, 1.0)     # 링키지 강조색
LINK_RGBA["coupler"] = (0.75, 0.20, 0.20, 1.0)


def build_fourbar_model():
    PH.winit()
    P12 = P13._M["P12"]
    S = P12._G["S"]; FR = P12._G["FR"]; FL = P12._G["FL"]
    x_h = np.array(json.load(open(Path(__file__).parent / "fourbar_p13h_candidate.json"))["x"])
    dd = dict(zip(FR.NAMES, x_h[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = 0.0
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, x_h[26:32])))
    # 링키지가 보이도록 crank/coupler 캡슐 반경 살짝 확대 (시각 전용)
    xml = xml.replace('type="capsule" size="0.008"', 'type="capsule" size="0.010"')
    xml = xml.replace('type="capsule" size="0.006"', 'type="capsule" size="0.009"')
    # ── canonical(leg.xml) 시각 요소 이식: 스카이박스/체커 바닥/헤드라이트/방향광 ──
    visual_assets = (
        '<asset>'
        '<texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>'
        '<texture type="2d" name="groundplane" builtin="checker" mark="edge" '
        'rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>'
        '<material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>'
        '</asset>'
        '<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>')
    xml = xml.replace('<worldbody>', visual_assets + '\n<worldbody>\n  '
                      '<light pos="0 0 1.5" dir="0 0 -1" directional="true"/>', 1)
    xml = xml.replace('<geom name="floor" size="0 0 0.05" type="plane"',
                      '<geom name="floor" size="0 0 0.05" type="plane" material="groundplane"', 1)
    model = mujoco.MjModel.from_xml_string(xml)
    for gid in range(model.ngeom):
        bid = int(model.geom_bodyid[gid])
        bname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid)
        gname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        if gname == "floor":
            continue
        if gname == "foot":
            model.geom_rgba[gid] = LINK_RGBA["foot"]; model.geom_matid[gid] = -1
            continue
        if bname in LINK_RGBA:
            model.geom_rgba[gid] = LINK_RGBA[bname]; model.geom_matid[gid] = -1
    return model


def render_jump_cl(model, npz_path, out_gif, label, h_real=None):
    d = np.load(npz_path)
    t = d["t"]; q1c = d["q1"]; q2c = d["q2"]; bz = d["bz"]
    m = t >= -0.05
    t = t[m]; q1c = q1c[m]; q2c = q2c[m]; bz = bz[m]
    wrap = lambda x: ((x + np.pi) % (2 * np.pi)) - np.pi
    mj1 = wrap(-q1c - np.pi / 2); mj2 = wrap(-q2c)
    dur = float(t[-1] - t[0])
    n = min(MA.N_MAX, max(MA.N_MIN, int(round(dur / MA.PHYS_DT_PER_FRAME))))
    idxs = np.linspace(0, len(t) - 1, n).astype(int)
    data = mujoco.MjData(model)
    cam = mujoco.MjvCamera()
    cam.azimuth = 135.0; cam.elevation = -15.0; cam.distance = 1.2
    cam.lookat = np.array([0.0, 0.0, 0.3])
    h_apex = float(bz.max())
    frames = []
    with mujoco.Renderer(model, width=640, height=480) as ren:
        for i in idxs:
            q1m = float(mj1[i]); q2m = float(mj2[i])
            data.qpos[:] = [float(bz[i]), q1m, q2m, -q2m, q2m]
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            MA._draw_text_outlined(dr, (10, 10), f"trial = {label}", MA.FONT, fill="white")
            MA._draw_text_outlined(dr, (10, 40), f"t = {t[i]*1000:>6.0f} ms", MA.FONT)
            MA._draw_text_outlined(dr, (10, 70), f"base_z = {bz[i]*100:>5.1f} cm", MA.FONT, fill="#00ffff")
            MA._draw_text_outlined(dr, (10, 100), f"hip  = {np.degrees(q1m):+6.1f}", MA.FONT, fill="#00ff00")
            MA._draw_text_outlined(dr, (10, 130), f"knee = {np.degrees(q2m):+6.1f}", MA.FONT, fill="#ff8800")
            MA._draw_text_outlined(dr, (10, 160), f"h_sim  = {h_apex:.3f} m", MA.FONT, fill="#ffff00")
            if h_real is not None and np.isfinite(h_real):
                MA._draw_text_outlined(dr, (10, 190), f"h_real = {h_real:.3f} m", MA.FONT, fill="#ff66ff")
            frames.append(img)
    frames[0].save(str(out_gif), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)
    return len(frames)


def main():
    import json as _json
    model = build_fourbar_model()
    cl = _json.load(open(Path(__file__).parent / "p10_cl.json"))
    files = sorted(TRAJ.glob("*.npz"))
    print(f"{len(files)} trajs (4-bar 렌더, canonical 배경/조명)", flush=True)
    for f in files:
        name = f.stem                       # ds__sub__tag
        ds, sub, tag = name.split("__")
        hr = (cl.get(f"{ds}/{sub}", {}).get("label") or {}).get("h_real")
        n = render_jump_cl(model, f, GIFD / (name + ".gif"), name.replace("__", " / "),
                           h_real=hr)
        print("gif", name, n, "frames", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
