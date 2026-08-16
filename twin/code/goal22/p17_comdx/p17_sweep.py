# -*- coding: utf-8 -*-
"""P17 — off-axis(축 수직, 전후 x방향) CoM 오프셋: 역대 미검증 축.

배경: com_dz(축방향)만 자유였고 dx는 항상 0. com_dz_th가 3개 모델 연속 +3cm 상한 추격
→ off-axis 성분(실물: 무릎 모터·텐셔너가 thigh 옆에 부착)을 dz로 흉내 내는 중일 가능성.
방법: P16 스택(모델+a_hat+springref) 고정, dx_th/dx_ca 1-D 스윕 → 이중 심판.
XML: thigh/calf inertial pos의 x성분 주입.
"""
import sys, json, re
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "p14_ahat"))
sys.path.insert(0, str(HERE.parent / "p16_structure"))
import p14_judge as J
import g21_p13_linkage as P13
import g21_p13e_honest as PH

OUT = HERE / "p17_sweep.json"
G7 = ["w_0421", "w_0424", "w_0602", "w_0324", "w_s2s", "fs_0424", "fs_0602", "habs"]
C16 = json.load(open(HERE.parent / "p16_structure/fourbar_p16_candidate.json"))
X16 = np.array(C16["x"])              # 32 + A4 + springref
REF = float(X16[36])
X36 = X16[:36]


def build_p17(x32, ref, dx_th, dx_ca):
    S = J._P["S"]; FR = J._P["FR"]; FL = J._P["FL"]; mj = J._P["mj"]
    dd = dict(zip(FR.NAMES, np.asarray(x32)[:26]))
    S.FV_HIP = dd["fv_hip"]; S.FV_KNEE = dd["fv_knee"]; S.FC_HIP = dd["fc_hip"]; S.FC_KNEE = dd["fc_knee"]
    S.SOLREF_TC_LOCK = dd["solref_tc"]; S.IMP0_LOCK = dd["imp0"]
    S.STIFF_HIP = 0.0; S.STIFF_KNEE = dd["stiff_knee"]; S.SPRINGREF_KNEE = ref
    sc = dict(dd); sc["TOTAL_MASS"] = PH.TOTAL
    xml = P13.apply_linkage_mods(FL.build_xml_fourbar_flip(dd["arm_knee"], sc),
                                 dict(zip(P13.N6, np.asarray(x32)[26:32])))
    if dx_th != 0.0:
        # thigh inertial: diaginertia 끝이 0.0002 로 유일
        xml = re.sub(r'<inertial pos="0 0 (-[\d.]+)" (mass="[\d.]+" diaginertia="[\d.e+-]+ [\d.e+-]+ 0\.0002"/>)',
                     f'<inertial pos="{dx_th:.5f} 0 \\1" \\2', xml, count=1)
    if dx_ca != 0.0:
        # calf body 블록 내 첫 inertial
        i = xml.find('<body name="calf"')
        j = xml.find('<inertial pos="0 0 ', i)
        xml = xml[:j] + f'<inertial pos="{dx_ca:.5f} 0 ' + xml[j + len('<inertial pos="0 0 '):]
    return mj.MjModel.from_xml_string(xml), dd


_CFG = [REF, 0.0, 0.0]


def winit():
    J.winit()
    J.build_model = lambda x32: build_p17(x32, _CFG[0], _CFG[1], _CFG[2])


def eval_cell(args):
    dx_th, dx_ca = args
    try:
        if not J._P:
            winit()
        _CFG[1] = dx_th; _CFG[2] = dx_ca
        ra = J.eval_modeA(X36)
        jc, jcg = J.eval_cl(X36)
        return dict(dx_th=dx_th, dx_ca=dx_ca, A={g: float(ra[g]) for g in G7},
                    fs0324=float(ra["fs_0324"]), C=float(jc), Cg=float(jcg))
    except Exception as e:
        return dict(dx_th=dx_th, dx_ca=dx_ca, err=str(e)[:80])


def main():
    import multiprocessing as mp
    winit()
    grid = [(0.0, 0.0)]
    for v in [-0.03, -0.02, -0.01, 0.01, 0.02, 0.03]:
        grid.append((v, 0.0))
    for v in [-0.03, -0.02, -0.01, 0.01, 0.02, 0.03]:
        grid.append((0.0, v))
    pool = mp.Pool(10, initializer=winit)
    rs = pool.map(eval_cell, grid)
    base = rs[0]
    print(f"기준 P16 (dx=0): JC={base['C']:.4f}", flush=True)
    print(f"{'dx_th':>7} {'dx_ca':>7} {'JA':>8} {'JC':>8} {'hoA':>6} {'hoC':>6}", flush=True)
    rows = []
    for r in rs:
        if "err" in r:
            print(r["dx_th"], r["dx_ca"], "ERR", r["err"], flush=True)
            continue
        ja = sum(r["A"][g] / base["A"][g] for g in G7) / len(G7)
        jc = r["C"] / base["C"]
        hoA = r["fs0324"] / base["fs0324"]; hoC = r["Cg"] / base["Cg"]
        rows.append(dict(r, ja=float(ja), jc=float(jc), hoA=float(hoA), hoC=float(hoC)))
        print(f"{r['dx_th']:7.3f} {r['dx_ca']:7.3f} {ja:8.4f} {jc:8.4f} {hoA:6.3f} {hoC:6.3f}",
              flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
