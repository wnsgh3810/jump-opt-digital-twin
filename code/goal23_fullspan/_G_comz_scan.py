# -*- coding: utf-8 -*-
"""_G_comz_scan — 마라톤G Phase1: **thigh 무게중심 팔길이 스캔** (ModeA 주 심판).

배경 (사용자 확정 08-02): hip 축과 knee 축이 **동일** → knee 모터(480g)는 힙 축 위(r≈0)에 있다.
따라서 허벅지 묶음(1.05kg)의 CoM은 **구조분만의 레버를 질량비로 희석한 위치**여야 한다.
그런데 현행 트윈은 com_z = −0.1094 m로 CAD 원본(−0.0565 m)의 약 2배 — 과거 적합에서
`com_dz_th`가 케이지 상한에 붙어 생긴 **포화 산물**로 의심된다.

데이터를 한 번만 읽고 트윈만 바꿔가며 MA를 재계산한다 (보드 반복 실행 대비 대폭 빠름).
CLI: python _G_comz_scan.py [값1,값2,...]   (값 = 기존 ipos에 더할 z 오프셋 [m], + = 힙 쪽)
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
os.environ.setdefault("FS_MBODY", "thigh=1.05")     # 실측 묶음 질량 고정
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD
import fs_runner as FR

CH = ["q1", "q2", "dq1", "dq2"]


def load_all():
    """비CVT 전 trial의 채점 창 데이터 (한 번만)."""
    out = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p)
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            out.append((s, p.name, d, m, int(np.argmax(m))))
        except Exception as ex:
            print(f"{s}/{p.name}: LOAD ERR {type(ex).__name__}", flush=True)
    return out


def ma_errors(ft, SP, data):
    """세션별 MA RMSE (q1,q2 [°] · dq1,dq2 [rad/s])."""
    acc = {}
    for s, nm, d, m, i0 in data:
        tt = d["t"]; t = tt[m] - tt[i0]
        sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
        L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                               float(d["q1"][i0]), float(d["q2"][i0]),
                               float(d["dq1"][i0]), float(d["dq2"][i0]),
                               float(t[-1] - 0.004), bias1=sp["bias1"],
                               knee_deep=sp["knee_deep"], fade=True)
        if L is None:
            continue
        g = lambda k: np.interp(t, L["t"], L[k])
        r = [float(np.degrees(np.sqrt(np.mean((d["q1"][m] - g("thm1")) ** 2)))),
             float(np.degrees(np.sqrt(np.mean((d["q2"][m] - g("q2")) ** 2)))),
             float(np.sqrt(np.mean((d["dq1"][m] - g("dq1")) ** 2))),
             float(np.sqrt(np.mean((d["dq2"][m] - g("dq2")) ** 2)))]
        acc.setdefault(s, []).append(r)
    return {s: np.mean(v, axis=0) for s, v in acc.items()}


def main():
    vals = [float(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 \
        else [0.0, 0.015, 0.03, 0.045, 0.053]
    data = load_all()
    print(f"로드 {len(data)} trial (비CVT)", flush=True)
    SP = FR._sess_params()
    print(f"\n{'Δcom_z[m]':>9} {'com_z[m]':>9} | {'fit q1':>7} {'fit q2':>7} {'fit dq1':>8} {'fit dq2':>8} "
          f"| {'HO q1':>6} {'HO q2':>6} | {'gate q1':>8} {'gate q2':>8}")
    for v in vals:
        os.environ["FS_COMZ"] = f"thigh={v}"
        ft = FR.fs_twin()
        import mujoco as mjm
        _i = mjm.mj_name2id(ft["model"], mjm.mjtObj.mjOBJ_BODY, "thigh")
        cz = float(ft["model"].body_ipos[_i][2])
        E = ma_errors(ft, SP, data)
        fit = np.mean([E[s] for s in E if FD.kind_of(s) == "fit"], axis=0)
        ho = np.mean([E[s] for s in E if FD.kind_of(s) == "heldout"], axis=0)
        gt = np.mean([E[s] for s in E if FD.kind_of(s) == "gate"], axis=0)
        print(f"{v:+9.3f} {cz:9.5f} | {fit[0]:7.2f} {fit[1]:7.2f} {fit[2]:8.2f} {fit[3]:8.2f} "
              f"| {ho[0]:6.2f} {ho[1]:6.2f} | {gt[0]:8.2f} {gt[1]:8.2f}", flush=True)
        for s in sorted(E):
            print(f"    {s} [{FD.kind_of(s):<7}] " + " ".join(f"{c} {x:.2f}" for c, x in zip(CH, E[s])),
                  flush=True)


if __name__ == "__main__":
    main()
