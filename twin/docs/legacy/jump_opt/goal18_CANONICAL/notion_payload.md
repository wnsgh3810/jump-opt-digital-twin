> 🔒 **STATUS: LOCKED CANONICAL — 2026-07-01.** 앞으로 모든 시뮬레이션 렌더링은 이 코드 기준. 모델이 수정되어도 시각화 파이프라인은 그대로 사용.

> **File location**: `C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/`
> **Final output**: `goal18_v13/Iter6/` — 30/30 sub-folders, 217 gifs, 224 plots
> **Git tag**: `v14-canonical` (annotated) + `LOCKED-2026-07-01`
> **Commit**: `e2fc5ed9` (canonical folder), `f14ca44b` (dependency freeze)

## 🔑 핵심 원칙 (LOCK — 절대 변경 금지)

1. **좌표 변환** (CRITICAL): `mj_q1 = -q1_canonical - π/2`, `mj_q2 = -q2_canonical`
2. **Angle wrap** `(-π, +π]`
3. **카메라**: azim=135°, elev=-15°, dist=1.2, lookat=(0, 0, 0.3)
4. **색상**: base(0.5,0.5,0.5) / thigh(0.6,0.6,0.7) / calf(0.5,0.6,0.6) / foot(0.5,0.5,0.5)
5. **Real-time pace**: `n_frames = clamp(30, 200, round(cyc_dur / 0.04))`, 40ms/frame
6. **GND foot-on-floor**: `mj_step` × **1500회** (500 부족 → 29.3cm 정지 버그), PD kp=1000 kd=50
7. **AIR base**: `base_z = 0.55` 고정, overlay `"base = 0 (air, fixed)"`

## 📊 최종 결과

| Dataset | Subs | mode_A | mode_B | Total |
|---|---|---|---|---|
| sit2stand_0324 | 4 | 54 | 54 | 108 |
| sit2stand_air_0319 | 1 | 15 | 15 | 30 |
| sit2stand_gnd_0319 | 1 | 15 | 15 | 30 |
| jump_0424 | 9 | 10 | 9 | 19 |
| jump_0602 | 6 | 6 | 6 | 12 |
| jump_position_0421 | 6 | 6 | 6 | 12 |
| jump_torque_0422 | 3 | 3 | 3 | 6 |
| **TOTAL** | **30** | **109** | **108** | **217** gifs, 224 plots |

## 📝 Iteration History

| Version | 시도 | 결과 |
|---|---|---|
| v10 | Original jump XML | sit2stand 안 보임 |
| v11 | Camera 조정 | 여전히 문제 |
| v12 | v3 오렌지+그린 | 사용자 거부 |
| v13 rev1 | 좌표 변환 미적용 | leg 반대 방향 |
| v13 rev2 | 좌표 변환 + real-time | gnd 29.3cm 정지 |
| v13 rev3 | Wrap 추가 | 여전히 정지 |
| v13 rev4 | mj_step 500→1500 | ✓ 정상 안착 |
| **v14** | **mode_B 30/30 완비** | ✅ **최종 LOCKED** |

---

# 📜 CODE TOGGLES — 전체 파일 실제 내용 (절대 잊지 말 것)

이 토글들은 `goal18_CANONICAL/code/` 내부의 실제 파일 100% 복사. 파일이 사라져도 이거 보면 복구 가능.

+++ 🎬 `make_anim.py` — 핵심 렌더러 (좌표 변환 + wrap + real-time pace + mj_step 1500 gnd)
```python
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

```
+++

+++ 🚀 `regen_all.py` — 30 sub-folder 일괄 orchestrator
```python
"""v13 rev2 regen — jump XML + coord conversion + real-time pace + plot cp."""
from __future__ import annotations
from pathlib import Path
import sys, json, shutil
import numpy as np

V13 = Path("C:/Users/junho/Desktop/jump_opt/goal18_v13/Iter6")
V10 = Path("C:/Users/junho/Desktop/jump_opt/goal18_v10/Iter6")

sys.path.insert(0, str(V13))
sys.path.insert(0, "C:/Users/junho/Desktop/jump_opt/goal12/iter38")

from _make_anim_sit2stand import render_sit2stand
from run_i38 import build_xml_i38


def load_pm():
    with open("C:/Users/junho/Desktop/jump_opt/goal12/iter38/iter38_metrics.json") as f:
        p = json.load(f)['per_trial']['0424_60_0.75_60_2']
    return dict(fv_hip=float(p['fv_hip']), fv_knee=float(p['fv_knee']),
                fc_hip=float(p['fc_hip']),
                m_base=float(p['m_base']) * 1.0358,
                solref_tc=0.007085, imp0=0.2526,
                m_thigh_scale=float(p['m_thigh_scale']) * 0.9315,
                m_calf_scale=float(p['m_calf_scale']) * 1.0148,
                fc_knee=float(p['fc_knee']), arm_knee=0.01983)


def cp_plots(src_root: Path, dst_root: Path) -> int:
    """Copy plots from src/mode_X/plots to dst/mode_X/plots."""
    n = 0
    for mode in ('mode_A', 'mode_B'):
        src_plots = src_root / mode / 'plots'
        if not src_plots.exists():
            continue
        dst_plots = dst_root / mode / 'plots'
        dst_plots.mkdir(parents=True, exist_ok=True)
        for pf in sorted(src_plots.glob('*.png')):
            shutil.copy2(pf, dst_plots / pf.name)
            n += 1
    return n


def render_dataset(src_root: Path, dst_root: Path, ds_label: str,
                   xml_path: Path, kind: str) -> dict:
    n_anim = 0
    playbacks = []
    for mode in ('mode_A', 'mode_B'):
        src_sim = src_root / mode / 'sim_data'
        if not src_sim.exists():
            continue
        dst_anim = dst_root / mode / 'anims'
        # Clear existing anims (v13 rev1 gifs) to ensure re-render
        if dst_anim.exists():
            for old in dst_anim.glob('*.gif'):
                old.unlink()
        dst_anim.mkdir(parents=True, exist_ok=True)
        for npz in sorted(src_sim.glob('*.npz')):
            stem = npz.stem
            cyc = stem.split('cycle')[-1] if 'cycle' in stem else stem
            out_gif = dst_anim / f"cycle{cyc}.gif"
            try:
                info = render_sit2stand(str(npz), str(xml_path), str(out_gif),
                                        f"{ds_label} {mode} cyc{cyc}", kind)
                n_anim += 1
                playbacks.append(info['playback_s'])
            except Exception as e:
                print(f"  [ERR] {npz.name}: {e}")
    n_plots = cp_plots(src_root, dst_root)
    return dict(gifs=n_anim, plots=n_plots,
                playback_min=float(np.min(playbacks)) if playbacks else 0,
                playback_max=float(np.max(playbacks)) if playbacks else 0)


def cp_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return sum(1 for _ in dst.rglob('*.gif'))


def main():
    V13.mkdir(parents=True, exist_ok=True)
    xml_path = V13 / 'leg.xml'
    xml_path.write_text(build_xml_i38(**load_pm()), encoding='utf-8')

    reports = []

    # sit2stand_0324 subfolders (canonical from goal16)
    s2s_src = Path("C:/Users/junho/Desktop/jump_opt/goal16/cross_validation_clean/sit2stand_0324")
    for sub in sorted(s2s_src.iterdir()):
        if not sub.is_dir() or 'OLD' in sub.name:
            continue
        if not (sub / 'mode_A' / 'sim_data').exists():
            continue
        r = render_dataset(sub, V13 / 'sit2stand_0324' / sub.name,
                           f"sit2stand_0324 {sub.name}", xml_path, 'air')
        r['folder'] = f"sit2stand_0324/{sub.name}"
        r['kind'] = 'air'
        reports.append(r)

    # sit2stand_air_0319 (canonical from v4)
    r = render_dataset(
        Path("C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/sit2stand_air_0319/ROOT"),
        V13 / 'sit2stand_air_0319' / 'ROOT',
        "sit2stand_air_0319 ROOT", xml_path, 'air')
    r['folder'] = "sit2stand_air_0319/ROOT"; r['kind'] = 'air'
    reports.append(r)

    # sit2stand_gnd_0319
    r = render_dataset(
        Path("C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/sit2stand_gnd_0319/ROOT"),
        V13 / 'sit2stand_gnd_0319' / 'ROOT',
        "sit2stand_gnd_0319 ROOT", xml_path, 'gnd')
    r['folder'] = "sit2stand_gnd_0319/ROOT"; r['kind'] = 'gnd'
    reports.append(r)

    # jump: cp from v10 (both anims + plots)
    for jd in ('jump_0424', 'jump_0602', 'jump_position_0421', 'jump_torque_0422'):
        n = cp_tree(V10 / jd, V13 / jd)
        reports.append({'folder': jd, 'action': 'cp_v10', 'gifs': n})

    summary = {'version': 'v13_rev2', 'reports': reports}
    (V13 / '_v13_rev2_summary.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()

```
+++

+++ 🔧 `gen_mode_B_pd.py` — PD sim 으로 pseudo mode_B 생성 (jump_0424, jump_0602)
```python
"""Generate mode_B via PD sim for jump subs (pseudo mode_B).

For each entry:
  - Load mode_A source npz (has t, q, dq in MuJoCo coords)
  - Use q as pseudo-q_des reference
  - Run PD sim with entry.pd_gains tracking that reference
  - Save cycle00.npz in canonical form (t_sim, q1_sim, q2_sim, base_z_sim,
    q1_des_sim, q2_des_sim, tau1_cmd_sim, tau2_cmd_sim)
  - Render animation via render_sit2stand kind='gnd' (label prefixed "[pseudo]")
  - Copy mode_A plots to mode_B/plots/

Task per user:
  1. Apply coord conversion: mj_q_des already in MuJoCo (mode_A saves MuJoCo state)
  2. Settle 500 steps to initial pose using strong PD.
  3. Then run: ctrl = kp * (q_des - q) + kd * (dq_des - dq).
  4. If PD sim diverges (base falls too fast, or NaN), mark 'failed'.
"""
from __future__ import annotations
import sys, json, shutil, traceback
from pathlib import Path
import numpy as np
import mujoco

V13_ITER6 = Path("C:/Users/junho/Desktop/jump_opt/goal18_v13/Iter6")
XML_PATH = V13_ITER6 / "leg.xml"

sys.path.insert(0, str(V13_ITER6))
from _make_anim_sit2stand import render_sit2stand  # noqa: E402

DT_SIM = 5e-4       # matches xml opt.timestep and mode_A dt
N_SETTLE = 500
SETTLE_KP = 500.0
SETTLE_KD = 10.0
DIVERGE_BASE_M = 5.0


ENTRIES = [
    {"dataset": "jump_0424", "sub": "120_2.2_150_2.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2.2_150_2.5/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2.2, "kp_knee": 150, "kd_knee": 2.5}},
    {"dataset": "jump_0424", "sub": "120_2.2_200_2.8",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2.2_200_2.8/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2.2, "kp_knee": 200, "kd_knee": 2.8}},
    {"dataset": "jump_0424", "sub": "120_2_120_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/120_2_120_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2, "kp_knee": 120, "kd_knee": 2}},
    {"dataset": "jump_0424", "sub": "150_2.2_250_3",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_250_3/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 250, "kd_knee": 3}},
    {"dataset": "jump_0424", "sub": "150_2.2_350_3.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_350_3.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 350, "kd_knee": 3.5}},
    {"dataset": "jump_0424", "sub": "150_2.2_500_4",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/150_2.2_500_4/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 500, "kd_knee": 4}},
    {"dataset": "jump_0424", "sub": "60_0.75_60_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/60_0.75_60_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 0.75, "kp_knee": 60, "kd_knee": 2}},
    {"dataset": "jump_0424", "sub": "60_1.5_60_1.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/60_1.5_60_1.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 1.5, "kp_knee": 60, "kd_knee": 1.5}},
    {"dataset": "jump_0424", "sub": "90_0.75_90_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0424/90_0.75_90_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 90, "kd_hip": 0.75, "kp_knee": 90, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "120_2_120_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/120_2_120_2/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 120, "kd_hip": 2, "kp_knee": 120, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "150_2.2_250_3",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/150_2.2_250_3/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 250, "kd_knee": 3}},
    {"dataset": "jump_0602", "sub": "150_2.2_500_5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/150_2.2_500_5/sim_data/iter6_sim.npz",
     "pd_gains": {"kp_hip": 150, "kd_hip": 2.2, "kp_knee": 500, "kd_knee": 5}},
    {"dataset": "jump_0602", "sub": "60_0.75_60_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18/iter1/jump_0602/60_0.75_60_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 0.75, "kp_knee": 60, "kd_knee": 2}},
    {"dataset": "jump_0602", "sub": "60_1.5_60_1.5",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18/iter1/jump_0602/60_1.5_60_1.5/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 60, "kd_hip": 1.5, "kp_knee": 60, "kd_knee": 1.5}},
    {"dataset": "jump_0602", "sub": "90_0.75_90_2",
     "mode_A_source": r"C:/Users/junho/Desktop/jump_opt/goal18_v4/Iter6/jump_0602/90_0.75_90_2/sim_data/run_log.npz",
     "pd_gains": {"kp_hip": 90, "kd_hip": 0.75, "kp_knee": 90, "kd_knee": 2}},
]


def _to_canonical(mj_q1, mj_q2):
    """MuJoCo hip/knee -> canonical q1_sim/q2_sim."""
    q1c = -(mj_q1 + np.pi / 2.0)
    q2c = -mj_q2
    return q1c, q2c


def run_pd_sim(model, t_A, q_A, dq_A, pd_gains):
    """Run PD sim tracking mode_A trajectory.

    t_A: (N,) mode_A time (canonical, may start negative)
    q_A: (N, 3) mode_A MuJoCo qpos [base_z, mj_q1, mj_q2]
    dq_A: (N, 3) mode_A MuJoCo qvel
    pd_gains: dict with kp_hip, kd_hip, kp_knee, kd_knee

    Returns dict with logs, or None on divergence.
    """
    kp_h = float(pd_gains["kp_hip"])
    kd_h = float(pd_gains["kd_hip"])
    kp_k = float(pd_gains["kp_knee"])
    kd_k = float(pd_gains["kd_knee"])

    dt = float(model.opt.timestep)
    N_track = len(t_A)
    N_total = N_SETTLE + N_track

    # Reference q_des trajectories (MuJoCo hip/knee) and dq_des
    mj_q1_des = q_A[:, 1].astype(float)
    mj_q2_des = q_A[:, 2].astype(float)
    # dq_des: use provided dq_A if available (both from mode_A), else numerical gradient
    mj_dq1_des = dq_A[:, 1].astype(float) if dq_A is not None else np.gradient(mj_q1_des, t_A)
    mj_dq2_des = dq_A[:, 2].astype(float) if dq_A is not None else np.gradient(mj_q2_des, t_A)

    # Initial pose: use mode_A t=0 (or first sample)
    data = mujoco.MjData(model)
    data.qpos[0] = float(q_A[0, 0])
    data.qpos[1] = float(mj_q1_des[0])
    data.qpos[2] = float(mj_q2_des[0])
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)

    log_t = np.empty(N_total, dtype=float)
    log_q = np.empty((N_total, 3), dtype=float)
    log_dq = np.empty((N_total, 3), dtype=float)
    log_tau_cmd = np.empty((N_total, 2), dtype=float)
    log_tau_applied = np.empty((N_total, 2), dtype=float)
    log_qdes_hip = np.empty(N_total, dtype=float)
    log_qdes_knee = np.empty(N_total, dtype=float)

    # Time base: pre-settle then t_A. Use dt-spaced settle time before t_A[0].
    t_settle = t_A[0] - dt * (N_SETTLE - np.arange(N_SETTLE))
    log_t[:N_SETTLE] = t_settle
    log_t[N_SETTLE:] = t_A

    q_init_hip = float(mj_q1_des[0])
    q_init_knee = float(mj_q2_des[0])

    for k in range(N_total):
        if k < N_SETTLE:
            q_des_h = q_init_hip
            q_des_k = q_init_knee
            dq_des_h = 0.0
            dq_des_k = 0.0
            kp_h_now, kd_h_now = SETTLE_KP, SETTLE_KD
            kp_k_now, kd_k_now = SETTLE_KP, SETTLE_KD
        else:
            j = k - N_SETTLE
            q_des_h = float(mj_q1_des[j])
            q_des_k = float(mj_q2_des[j])
            dq_des_h = float(mj_dq1_des[j])
            dq_des_k = float(mj_dq2_des[j])
            kp_h_now, kd_h_now = kp_h, kd_h
            kp_k_now, kd_k_now = kp_k, kd_k

        tau_h = kp_h_now * (q_des_h - data.qpos[1]) + kd_h_now * (dq_des_h - data.qvel[1])
        tau_k = kp_k_now * (q_des_k - data.qpos[2]) + kd_k_now * (dq_des_k - data.qvel[2])
        data.ctrl[0] = float(tau_h)
        data.ctrl[1] = float(tau_k)

        try:
            mujoco.mj_step(model, data)
        except Exception:
            return None

        log_q[k] = data.qpos
        log_dq[k] = data.qvel
        log_tau_cmd[k] = [tau_h, tau_k]
        log_tau_applied[k] = data.qfrc_actuator[1:3]
        log_qdes_hip[k] = q_des_h
        log_qdes_knee[k] = q_des_k

        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
            return None
        if abs(data.qpos[0]) > DIVERGE_BASE_M:
            return None

    return dict(
        t=log_t, q=log_q, dq=log_dq,
        tau_cmd=log_tau_cmd, tau_applied=log_tau_applied,
        qdes_hip=log_qdes_hip, qdes_knee=log_qdes_knee,
    )


def save_cycle_npz(out_path, log):
    """Save mode_B cycle npz in canonical form for render_sit2stand."""
    q_all = log['q']
    dq_all = log['dq']
    q1_sim, q2_sim = _to_canonical(q_all[:, 1], q_all[:, 2])
    q1_des_sim, q2_des_sim = _to_canonical(log['qdes_hip'], log['qdes_knee'])
    base_z_sim = q_all[:, 0]

    # tau in canonical frame (sign flip)
    tau1_cmd_sim = -log['tau_cmd'][:, 0]
    tau2_cmd_sim = -log['tau_cmd'][:, 1]

    np.savez_compressed(
        str(out_path),
        t_sim=log['t'].astype(float),
        q1_sim=q1_sim.astype(float),
        q2_sim=q2_sim.astype(float),
        base_z_sim=base_z_sim.astype(float),
        q1_des_sim=q1_des_sim.astype(float),
        q2_des_sim=q2_des_sim.astype(float),
        tau1_cmd_sim=tau1_cmd_sim.astype(float),
        tau2_cmd_sim=tau2_cmd_sim.astype(float),
    )


def copy_mode_A_plots(dataset, sub, dst_plots_dir):
    """Best-effort copy of any existing mode_A plots for symmetry."""
    src_dir = V13_ITER6 / dataset / sub / "mode_A" / "plots"
    n_copied = 0
    if src_dir.exists():
        dst_plots_dir.mkdir(parents=True, exist_ok=True)
        for p in src_dir.glob("*.png"):
            shutil.copy2(str(p), str(dst_plots_dir / p.name))
            n_copied += 1
    return n_copied


def process_entry(entry, model):
    dataset = entry["dataset"]
    sub = entry["sub"]
    src_path = Path(entry["mode_A_source"])
    pd_gains = entry["pd_gains"]

    out_root = V13_ITER6 / dataset / sub / "mode_B"
    out_sim = out_root / "sim_data"
    out_anim = out_root / "anims"
    out_plots = out_root / "plots"

    if not src_path.exists():
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"mode_A source missing: {src_path}")

    try:
        d = np.load(str(src_path), allow_pickle=True)
    except Exception as e:
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"load fail: {e!r}")

    keys = set(d.files)
    if not {'t', 'q'}.issubset(keys):
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"missing keys (need t,q); got={sorted(keys)}")

    t_A = np.asarray(d['t'], dtype=float)
    q_A = np.asarray(d['q'], dtype=float)
    dq_A = np.asarray(d['dq'], dtype=float) if 'dq' in keys else None

    if q_A.shape[1] != 3:
        return dict(sub=sub, status="skipped", n_cycles=0,
                    notes=f"q.shape={q_A.shape}, expected (N,3)")

    out_sim.mkdir(parents=True, exist_ok=True)
    out_anim.mkdir(parents=True, exist_ok=True)

    log = run_pd_sim(model, t_A, q_A, dq_A, pd_gains)
    if log is None:
        return dict(sub=sub, status="failed", n_cycles=0,
                    notes="PD sim diverged (NaN or |base|>5m)")

    # Final sanity: peak |base_z| within reasonable jump range
    base_peak = float(np.abs(log['q'][:, 0]).max())
    if not np.isfinite(base_peak) or base_peak > 3.0:
        return dict(sub=sub, status="failed", n_cycles=0,
                    notes=f"base_z out of range: peak={base_peak:.2f} m")

    # Save cycle_00.npz (single "cycle" for jump)
    cycle_npz = out_sim / "cycle_00.npz"
    save_cycle_npz(cycle_npz, log)

    # Render animation with render_sit2stand kind='gnd'
    trial_label = f"[pseudo] {dataset} {sub} mode_B kp_h={pd_gains['kp_hip']} kd_h={pd_gains['kd_hip']} kp_k={pd_gains['kp_knee']} kd_k={pd_gains['kd_knee']}"
    gif_out = out_anim / "cycle_00.gif"
    try:
        render_sit2stand(
            canon_npz_path=str(cycle_npz),
            model_xml_path=str(XML_PATH),
            out_gif_path=str(gif_out),
            trial_label=trial_label,
            kind='gnd',
        )
    except Exception as e:
        return dict(sub=sub, status="failed", n_cycles=1,
                    notes=f"render failed: {e!r}")

    n_plots = copy_mode_A_plots(dataset, sub, out_plots)

    # Summary metrics
    q_end = log['q'][-1]
    peak_h = float(log['q'][:, 0].max())

    return dict(
        sub=sub,
        status="ok",
        n_cycles=1,
        notes=(
            f"peak base_z={peak_h*100:.1f}cm, q_end=[{q_end[0]:.3f},{q_end[1]:.3f},{q_end[2]:.3f}], "
            f"n_plots_copied={n_plots}, gif={gif_out.name}"
        ),
    )


def main():
    model = mujoco.MjModel.from_xml_path(str(XML_PATH))
    if abs(model.opt.timestep - DT_SIM) > 1e-9:
        print(f"[WARN] xml dt={model.opt.timestep} differs from DT_SIM={DT_SIM}")

    per_sub = []
    ok = skip = 0
    total_gifs = 0
    for i, entry in enumerate(ENTRIES):
        try:
            r = process_entry(entry, model)
        except Exception as e:
            tb = traceback.format_exc().splitlines()[-3:]
            r = dict(sub=entry["sub"], status="failed", n_cycles=0,
                     notes=f"exception: {e!r} | {' | '.join(tb)}")
        # attach dataset for disambiguation (jump_0424 vs jump_0602 subs overlap)
        r_full = {"dataset": entry["dataset"], **r}
        per_sub.append(r_full)
        if r["status"] == "ok":
            ok += 1
            total_gifs += r["n_cycles"]
        else:
            skip += 1
        print(f"[{i+1:2d}/{len(ENTRIES)}] {entry['dataset']}/{entry['sub']}: "
              f"{r['status']} - {r['notes']}")

    summary = {
        "subs_processed": ok,
        "subs_skipped": skip,
        "total_gifs": total_gifs,
        "per_sub": per_sub,
    }
    out_json = V13_ITER6 / "_mode_B_pd_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                        encoding='utf-8')
    print("\nSummary written to", out_json)
    print(json.dumps({"subs_processed": ok, "subs_skipped": skip,
                      "total_gifs": total_gifs}, indent=2))
    return summary


if __name__ == "__main__":
    main()

```
+++

+++ 📐 `build_xml_i38_standalone.py` — MuJoCo XML 생성기 (self-contained, 외부 의존 없음)
```python
"""Self-contained build_xml_i38 — canonical XML generator for GOAL18 rendering.

Extracted from goal12/iter38/run_i38.py + goal12/iter3/build_xml_i3.py so
this file has NO external dependency. Regenerating leg.xml from scratch
requires only Python + numpy.

Used by regen_all.py:
    xml_str = build_xml_i38(**iter38_best_params)
    Path('leg.xml').write_text(xml_str, encoding='utf-8')

Fixed constants (CAD-verified, DO NOT CHANGE unless robot changes):
    L1 = L2 = 0.25 m (thigh, calf lengths)
    LC = 0.03 m (calf offset)
    Foot cylinder: radius 21mm × half-length 6.5mm (line contact y-axis)
    dt = 0.0005s, RK4 integrator, elliptic cone impratio 100
"""
import numpy as np

# ═══════════════════════════════════════════════════════════════════════
# MuJoCo solver options
# ═══════════════════════════════════════════════════════════════════════
DT         = 0.0005      # timestep [s]  — CRITICAL: settling steps depend on this
INTEGRATOR = 'RK4'
CONE       = 'elliptic'
IMPRATIO   = 100

# Contact defaults (Iter2 CMA-ES best; overrideable via params)
SOLREF_D_G = 1.6072
IMP1_G     = 0.72007
IMP_MID_G  = 0.005409

# ═══════════════════════════════════════════════════════════════════════
# CAD constants (link geometry + masses) — VERIFIED, DO NOT CHANGE
# ═══════════════════════════════════════════════════════════════════════
M1_CAD     = 0.91281     # thigh main body [kg]
M2_CAD     = 0.23704     # calf main body [kg]
M_C_CAD    = 0.65601     # calf motor [kg]
M_P_CAD    = 0.13657     # thigh motor [kg]
M_FOOT_EXTRA = 0.018461  # foot mass extra [kg]

R1_VAL = 0.05646; R2_VAL = 0.05884  # thigh/calf CoM radial offsets
RC_VAL = 0.02069; RP_VAL = 0.13258
L1_VAL = 0.25;    L2_VAL = 0.25;    LC_VAL = 0.03   # link lengths [m]
I1_VAL = 0.0092344; I2_VAL = 0.001805
IC_VAL = 0.0005797; IP_VAL = 0.0008858

FOOT_RADIUS   = 0.021    # 21mm cylinder radius
FOOT_HALF_LEN = 0.0065   # 6.5mm half-length (13mm total, y-axis)

# ═══════════════════════════════════════════════════════════════════════
# Iter2 joint params (defaults; overrideable)
# ═══════════════════════════════════════════════════════════════════════
STIFF_HIP_G  = 0.08012
STIFF_KNEE_G = 1.16157
FC_KNEE_G    = 0.02132
ARM_KNEE_G   = 0.00490
ARM_HIP_FIXED = 0.0


def composite_inertia_scaled(m_base, m_thigh_scale=1.0, m_calf_scale=1.0):
    """Compute composite inertias of thigh & calf assemblies with mass scales."""
    M1 = M1_CAD * m_thigh_scale; Mp = M_P_CAD * m_thigh_scale
    M2 = M2_CAD * m_calf_scale;  Mc = M_C_CAD * m_calf_scale; Mf = M_FOOT_EXTRA
    I1 = I1_VAL * m_thigh_scale; Ip = IP_VAL * m_thigh_scale
    I2 = I2_VAL * m_calf_scale;  Ic = IC_VAL * m_calf_scale
    M_thigh = M1 + Mp
    com_thigh_z = -(M1 * R1_VAL + Mp * RP_VAL) / M_thigh
    d_m1 = R1_VAL + com_thigh_z; d_mp = RP_VAL + com_thigh_z
    I_thigh = I1 + M1 * d_m1**2 + Ip + Mp * (d_mp**2 + LC_VAL**2)
    M_calf = M2 + Mc + Mf
    com_calf_z = -(M2 * R2_VAL + Mc * RC_VAL + Mf * L2_VAL) / M_calf
    d_m2 = R2_VAL + com_calf_z; d_mc = RC_VAL + com_calf_z; d_mf = L2_VAL + com_calf_z
    I_calf = I2 + M2 * d_m2**2 + Ic + Mc * d_mc**2 + Mf * d_mf**2
    return dict(M_base=m_base, M_thigh=M_thigh, com_thigh_z=com_thigh_z, I_thigh=I_thigh,
                M_calf=M_calf, com_calf_z=com_calf_z, I_calf=I_calf)


def build_xml_i38(fv_hip, fv_knee, fc_hip, m_base, solref_tc, imp0,
                  m_thigh_scale, m_calf_scale, fc_knee=FC_KNEE_G, arm_knee=ARM_KNEE_G):
    """Generate MuJoCo XML for GOAL18 canonical rendering.

    Structure:
      - 3-DoF: base_z slide + hip hinge + knee hinge (all axis y)
      - Floor at z=0 (checker texture, groundplane material)
      - Base body at z=0 with slide joint
      - Thigh capsule length L1=0.25m, radius 18mm, rgba light-purple
      - Calf capsule length L2=0.25m, radius 14mm, rgba teal-gray
      - Foot cylinder line-contact (fromto y-axis), radius 21mm × 13mm
      - Contact: floor + foot (thigh/calf/base contype=1 but only foot collides
        with floor; thigh/calf conaffinity=1 for self-collision if needed)
      - Actuators: hip_act, knee_act (motor gear=1)
    """
    ci = composite_inertia_scaled(m_base, m_thigh_scale, m_calf_scale)
    M_thigh = ci['M_thigh']; com_thigh_z = ci['com_thigh_z']; I_thigh = ci['I_thigh']
    M_calf  = ci['M_calf'];  com_calf_z  = ci['com_calf_z'];  I_calf  = ci['I_calf']
    imp0_v = min(max(imp0, 0.001), IMP1_G * 0.95)
    solref = f"{solref_tc:.6f} {SOLREF_D_G}"
    solimp = f"{imp0_v:.5f} {IMP1_G:.5f} {IMP_MID_G:.6f} 0.5 2"

    return f"""<mujoco model="g12_iter38_11d">
<option cone="{CONE}" impratio="{IMPRATIO}" gravity="0 0 -9.81" timestep="{DT}" integrator="{INTEGRATOR}"/>
<default><default class="leg">
  <geom friction="1.0 0.02 0.01" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="{FOOT_RADIUS:.4f}" priority="1"
       solref="{solref}" solimp="{solimp}" condim="6"/>
  </default>
</default></default>
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
  <texture type="2d" name="groundplane" builtin="checker" mark="edge"
           rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>
  <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
</asset>
<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"
        solref="{solref}" solimp="{solimp}"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="{m_base:.6f}" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" rgba="0.5 0.5 0.5 1" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="{ARM_HIP_FIXED:.8f}"
             damping="{fv_hip:.8f}" frictionloss="{fc_hip:.8f}"
             stiffness="{STIFF_HIP_G:.8f}" springref="0"/>
      <inertial pos="0 0 {com_thigh_z:.5f}" mass="{M_thigh:.5f}"
                diaginertia="{I_thigh:.6f} {I_thigh:.6f} 0.0002"/>
      <geom type="capsule" size="0.018" fromto="0 0 0 0 0 -{L1_VAL:.4f}"
            rgba="0.6 0.6 0.7 1" contype="1" conaffinity="1"/>
      <body name="calf" pos="0 0 -{L1_VAL:.4f}">
        <joint name="knee" type="hinge" armature="{arm_knee:.8f}"
               damping="{fv_knee:.8f}" frictionloss="{fc_knee:.8f}"
               stiffness="{STIFF_KNEE_G:.8f}" springref="0"/>
        <inertial pos="0 0 {com_calf_z:.5f}" mass="{M_calf:.5f}"
                  diaginertia="{I_calf:.6f} {I_calf:.6f} 0.0001"/>
        <geom type="capsule" size="0.014" fromto="0 0 0 0 0 -{L2_VAL:.4f}"
              rgba="0.5 0.6 0.6 1" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot"
              fromto="0 -{FOOT_HALF_LEN:.4f} -{L2_VAL:.4f}  0 {FOOT_HALF_LEN:.4f} -{L2_VAL:.4f}"
              rgba="0.5 0.5 0.5 1"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_act" joint="hip" gear="1"/>
  <motor name="knee_act" joint="knee" gear="1"/>
</actuator>
</mujoco>"""


# ═══════════════════════════════════════════════════════════════════════
# Iter38 best params (0424_60_0.75_60_2 trial × Iter6 overrides)
# ═══════════════════════════════════════════════════════════════════════
ITER38_BEST_PARAMS_ITER6 = dict(
    fv_hip=0.44242008,      # hip viscous damping
    fv_knee=0.005157814,    # knee viscous damping
    fc_hip=2.04564549,      # hip Coulomb friction
    fc_knee=0.18582999,     # knee Coulomb friction
    m_base=1.28966501,      # 1.2450909688928333 × 1.0358 (iter6 override)
    solref_tc=0.007085,     # iter6 override
    imp0=0.2526,            # iter6 override
    m_thigh_scale=0.94569,  # 1.0154887550602512 × 0.9315
    m_calf_scale=0.76172,   # 0.7505875318271736 × 1.0148
    arm_knee=0.01983,       # iter6 override
)


if __name__ == '__main__':
    # Generate canonical leg.xml
    from pathlib import Path
    xml = build_xml_i38(**ITER38_BEST_PARAMS_ITER6)
    out = Path(__file__).parent / 'leg.xml'
    out.write_text(xml, encoding='utf-8')
    print(f'Wrote canonical leg.xml ({len(xml)} bytes) to {out}')

```
+++

+++ 📄 `leg.xml` — 시각화 XML (build_xml_i38 output, 실제 사용 파일)
```xml
<mujoco model="g12_iter38_11d">
<option cone="elliptic" impratio="100" gravity="0 0 -9.81" timestep="0.0005" integrator="RK4"/>
<default><default class="leg">
  <geom friction="1.0 0.02 0.01" margin="0.001" condim="6"/>
  <joint axis="0 1 0"/>
  <motor ctrlrange="-100 100" ctrllimited="false"/>
  <default class="foot">
    <geom type="cylinder" size="0.0210" priority="1"
       solref="0.007085 1.6072" solimp="0.25260 0.72007 0.005409 0.5 2" condim="6"/>
  </default>
</default></default>
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
  <texture type="2d" name="groundplane" builtin="checker" mark="edge"
           rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3" markrgb="0.8 0.8 0.8" width="300" height="300"/>
  <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
</asset>
<visual><headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/></visual>
<worldbody>
  <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
  <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"
        solref="0.007085 1.6072" solimp="0.25260 0.72007 0.005409 0.5 2"/>
  <body name="base" pos="0 0 0" childclass="leg">
    <joint name="base_z" type="slide" axis="0 0 1" armature="0" damping="0" frictionloss="0"/>
    <inertial pos="0 0 0" mass="1.289665" diaginertia="0.005 0.005 0.005"/>
    <geom type="box" size="0.06 0.03 0.025" rgba="0.5 0.5 0.5 1" contype="0" conaffinity="0"/>
    <body name="thigh" pos="0 0 -0.025">
      <joint name="hip" type="hinge" armature="0.00000000"
             damping="0.44242008" frictionloss="2.04564549"
             stiffness="0.08012000" springref="0"/>
      <inertial pos="0 0 -0.06637" mass="0.99264"
                diaginertia="0.010340 0.010340 0.0002"/>
      <geom type="capsule" size="0.018" fromto="0 0 0 0 0 -0.2500"
            rgba="0.6 0.6 0.7 1" contype="1" conaffinity="1"/>
      <body name="calf" pos="0 0 -0.2500">
        <joint name="knee" type="hinge" armature="0.01983000"
               damping="0.00515781" frictionloss="0.18582999"
               stiffness="1.16157000" springref="0"/>
        <inertial pos="0 0 -0.03661" mass="0.69869"
                  diaginertia="0.002873 0.002873 0.0001"/>
        <geom type="capsule" size="0.014" fromto="0 0 0 0 0 -0.2500"
              rgba="0.5 0.6 0.6 1" contype="1" conaffinity="1"/>
        <geom name="foot" class="foot"
              fromto="0 -0.0065 -0.2500  0 0.0065 -0.2500"
              rgba="0.5 0.5 0.5 1"/>
      </body>
    </body>
  </body>
</worldbody>
<actuator>
  <motor name="hip_act" joint="hip" gear="1"/>
  <motor name="knee_act" joint="knee" gear="1"/>
</actuator>
</mujoco>
```
+++

+++ ⚙️ `iter38_best_params.json` — iter38 best params + iter6 overrides (JSON)
```json
{
  "_meta": {
    "source": "goal12/iter38/iter38_metrics.json per_trial 0424_60_0.75_60_2 with iter6 overrides",
    "purpose": "Reference model params for GOAL18 canonical XML generation (visual XML — actual sim params can differ)",
    "verified": "2026-07-01, GOAL18 v14 LOCKED"
  },
  "iter38_raw": {
    "fv_hip": 0.44242008097557617,
    "fv_knee": 0.005157814351430768,
    "fc_hip": 2.0456454927823104,
    "fc_knee": 0.18582999169728892,
    "m_base": 1.2450909688928333,
    "m_thigh_scale": 1.0154887550602512,
    "m_calf_scale": 0.7505875318271736
  },
  "iter6_overrides": {
    "m_base_scale": 1.0358,
    "solref_tc": 0.007085,
    "imp0": 0.2526,
    "M_thigh_scale_mult": 0.9315,
    "M_calf_scale_mult": 1.0148,
    "arm_knee": 0.01983
  },
  "final_effective": {
    "fv_hip": 0.44242008,
    "fv_knee": 0.005157814,
    "fc_hip": 2.04564549,
    "fc_knee": 0.18582999,
    "m_base": 1.28966501,
    "m_thigh_scale": 0.94569,
    "m_calf_scale": 0.76172,
    "solref_tc": 0.007085,
    "imp0": 0.2526,
    "arm_knee": 0.01983
  }
}

```
+++


---

## 🔧 사용법

**한 cycle 렌더**:
```python
import sys
sys.path.insert(0, 'C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code')
from make_anim import render_sit2stand

render_sit2stand(
    canon_npz_path='.../cycle01.npz',
    model_xml_path='C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/leg.xml',
    out_gif_path='.../cycle01.gif',
    trial_label='sit2stand_0324 P20_D1 mode_A cyc01',
    kind='air'   # or 'gnd'
)
```

**leg.xml 재생성** (모델 params 변경 시):
```python
from build_xml_i38_standalone import build_xml_i38, ITER38_BEST_PARAMS_ITER6
xml = build_xml_i38(**ITER38_BEST_PARAMS_ITER6)
open('leg.xml', 'w').write(xml)
```

**전체 재생성**:
```
python C:/Users/junho/Desktop/jump_opt/goal18_CANONICAL/code/regen_all.py
```

## ⚠️ 알려진 이슈

- **jump_0424/0602 mode_B (15 subs)**: canonical 없음 → PD sim으로 pseudo 생성. `[pseudo]` prefix 표시.
- **canonical GND 후반부 발산** (sit2stand_gnd cycle01 t>4.4s): sim tracking 잃고 q wrap → wrap_pi로 시각적 복구
- **base_z 29.3cm 정지 버그**: mj_step 500 부족. **1500회 필수**.
- **좌표 변환 안 하면 무릎 반대**: 반드시 `mj_q = -q_canonical - offset` 적용

## 🔗 Related

- Memory: `goal18_canonical_pipeline.md`, `feedback_animation_standard.md`
- Git tag: `v14-canonical` (annotated commit `e2fc5ed9`)
- Root marker: `C:/Users/junho/Desktop/jump_opt/CANONICAL_LOCK.md`
