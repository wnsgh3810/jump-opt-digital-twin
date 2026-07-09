# -*- coding: utf-8 -*-
"""P18 애니메이션 — CVT(l_i=25.08mm) 기하 그대로 canonical 규격 렌더 (비평행사변형 링키지 가시화)."""
import sys, json
import numpy as np
from pathlib import Path
import mujoco
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code")
import make_anim as MA
from cvt_core import build_cvt
import p14_judge as J

C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X = np.array(C16["x"]); REF = float(C16["x"][36])
TRAJD = HERE / "traj"
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_cvt_0429_results")
(DST / "gif").mkdir(parents=True, exist_ok=True)
RES = json.load(open(HERE / "cvt_results.json"))

LINK_RGBA = dict(MA.REF_RGBA)
LINK_RGBA["crank"] = (0.85, 0.45, 0.10, 1.0)
LINK_RGBA["coupler"] = (0.75, 0.20, 0.20, 1.0)

VIS = ('<asset>'
       '<texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>'
       '<texture type="2d" name="groundplane" builtin="checker" mark="edge" '
       'rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>'
       '<material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>'
       '</asset>'
       '<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>')


def build_anim_model(l_i):
    # 물리 모델 xml을 재사용하되 시각 요소 이식 (cvt_core.build_cvt는 model을 반환하므로 xml 경로 별도 구성)
    import cvt_core as CC
    import g21_p13_linkage as P13
    import g21_p13e_honest as PH
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]
    dd = dict(zip(FR.NAMES, X[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = REF
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, X[26:32])))
    xml = xml.replace('fromto="0 0 0 0 0 0.03"', f'fromto="0 0 0 0 0 {l_i:.5f}"')
    xml = xml.replace('<body name="coupler" pos="0 0 0.03">', f'<body name="coupler" pos="0 0 {l_i:.5f}">')
    import re
    xml = re.sub(r'<connect body1="coupler" body2="calf"[^/]*/>', '', xml)
    xml = xml.replace('type="capsule" size="0.008"', 'type="capsule" size="0.010"')
    xml = xml.replace('type="capsule" size="0.006"', 'type="capsule" size="0.009"')
    xml = xml.replace('<geom type="capsule" size="0.015" fromto="0 0 0 0 0 -0.25"',
                      '<geom name="rocker_vis" type="capsule" size="0.010" '
                      'fromto="0 0 0 0 0 0.03" contype="0" conaffinity="0"/>'
                      '<geom type="capsule" size="0.015" fromto="0 0 0 0 0 -0.25"', 1)
    xml = xml.replace('<worldbody>', VIS + '\n<worldbody>\n  '
                      '<light pos="0 0 1.5" dir="0 0 -1" directional="true"/>', 1)
    xml = xml.replace('<geom name="floor" size="0 0 0.05" type="plane"',
                      '<geom name="floor" size="0 0 0.05" type="plane" material="groundplane"', 1)
    model = mujoco.MjModel.from_xml_string(xml)
    for gid in range(model.ngeom):
        bid = int(model.geom_bodyid[gid])
        bn = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid)
        gn = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        if gn == "floor":
            continue
        if gn == "foot":
            model.geom_rgba[gid] = LINK_RGBA["foot"]; model.geom_matid[gid] = -1
            continue
        if gn == "rocker_vis":
            model.geom_rgba[gid] = LINK_RGBA["crank"]; model.geom_matid[gid] = -1
            continue
        if bn in LINK_RGBA:
            model.geom_rgba[gid] = LINK_RGBA[bn]; model.geom_matid[gid] = -1
    return model


def render(model, z, out, label, h_real):
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
    h_apex = float(bz.max())
    frames = []
    with mujoco.Renderer(model, width=640, height=480) as ren:
        for i in idxs:
            data.qpos[:] = [float(bz[i]), float(mj1[i]), float(mjc[i]), float(qp[i]), float(qk[i])]
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            ren.update_scene(data, camera=cam)
            img = Image.fromarray(ren.render())
            dr = ImageDraw.Draw(img)
            MA._draw_text_outlined(dr, (10, 10), f"trial = {label}", MA.FONT, fill="white")
            MA._draw_text_outlined(dr, (10, 40), f"t = {t[i]*1000:>6.0f} ms", MA.FONT)
            MA._draw_text_outlined(dr, (10, 70), f"base_z = {bz[i]*100:>5.1f} cm", MA.FONT, fill="#00ffff")
            MA._draw_text_outlined(dr, (10, 100), f"l_i = {float(z['l_i'])*1000:.1f} mm (CVT)", MA.FONT, fill="#ffaa00")
            MA._draw_text_outlined(dr, (10, 130), f"h_sim  = {h_apex:.3f} m", MA.FONT, fill="#ffff00")
            if h_real == h_real:
                MA._draw_text_outlined(dr, (10, 160), f"h_real = {h_real:.3f} m", MA.FONT, fill="#ff66ff")
            frames.append(img)
    frames[0].save(str(out), save_all=True, append_images=frames[1:],
                   duration=MA.DURATION_MS, loop=0, optimize=False)


def main():
    J.winit()
    model = None
    for f in sorted(TRAJD.glob("*.npz")):
        z = np.load(f)
        if model is None:
            model = build_anim_model(float(z["l_i"]))
        name = f.stem
        sub, mode = name.rsplit("__", 1)
        hr = RES.get(f"{sub}/{mode}", {}).get("h_real", float("nan"))
        render(model, z, DST / "gif" / (name + ".gif"), f"0429 {sub} [{mode}]", hr)
        print("gif", name, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
