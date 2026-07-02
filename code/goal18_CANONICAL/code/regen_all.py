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
