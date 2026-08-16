# -*- coding: utf-8 -*-
"""_F_majump2 — ModeA 점프높이 **직접 측정** (사용자 지시 08-02: "시간 늘려서 최대 높이 보면 되잖아").

기존 _F_majump의 결함: 이륙 속도 v로 h=v²/2g 환산 → ①베이스 속도 vs 무게중심 속도 혼동
②이륙 시점 판정 의존. 이번 판은 **끝까지 날려서 직접 잰다**.
창을 이륙 후 +0.6s까지 늘려 측정 토크를 계속 주입(실기도 공중에서 제어 중)하고,
  ①h_peak = max(bz) − bz(이륙)          — 베이스 실제 최고점
  ②h_com  = max(com_z) − com_z(이륙)    — 무게중심 최고점
  ③h_T    = g·T²/8, T = 발 접촉 소실~회복 — **실측(GRF 체공시간)과 동일 연산자**
셋을 함께 출력해 어느 정의로도 판독 가능하게. CLI: FS_MASS=... python _F_majump2.py
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import mujoco as mjm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
import fs_runner as FR

JH = safe.read_json(HERE / "_D_jumph.json")
G = 9.81


def replay(ft, d, seg, i0, m, sp, extra=0.6):
    """이륙 후 extra초까지 측정 토크 주입 재생. 접촉·무게중심 직접 로깅."""
    model = ft["model"]; P = ft["P"]; iq, dof = ft["iq"], ft["dof"]
    tt = d["t"]
    t_end_abs = min(tt[m][-1] + extra, tt[-1])
    m2 = (tt >= tt[i0]) & (tt <= t_end_abs)
    t = tt[m2] - tt[i0]
    L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(t[-1] - 0.004), bias1=sp["bias1"],
                           knee_deep=sp["knee_deep"], fade=True)
    return L, t


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    model = ft["model"]
    fg = mjm.mj_name2id(model, mjm.mjtObj.mjOBJ_GEOM, "foot")
    rows = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            pw = FD.plot_window(p, d)
            jh = JH.get(f"{s}/{p.name}", {})
            if pw is None or not jh:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            L, t = replay(ft, d, seg, i0, m, sp)
            if L is None:
                continue
            bz = L["bz"]; dt = float(np.median(np.diff(L["t"])))
            # 이륙 = 베이스가 최저점을 지나 상승 전환한 뒤 접촉 소실 (bz 상승 개시 후 첫 자유낙하 진입)
            v = np.convolve(np.gradient(bz, dt), np.ones(5) / 5, mode="same")
            a = np.gradient(v, dt)
            k_up = int(np.argmax(v))                       # 최대 상승 속도 = 이륙 직후
            # 이륙 후 최고점
            k_pk = k_up + int(np.argmax(bz[k_up:]))
            h_peak = (bz[k_pk] - bz[k_up]) * 100
            # 체공시간: 이륙(k_up) 이후 다시 상승 정지 → 하강 → 재상승 전까지
            below = np.where(bz[k_pk:] <= bz[k_up])[0]
            T = (below[0] * dt * 2) if len(below) else np.nan   # 상승·하강 대칭 가정 불필요: 아래 참조
            T_full = (k_pk - k_up) * dt * 2                     # 대칭 포물선 가정 체공시간
            h_T = G * T_full ** 2 / 8 * 100
            rows.setdefault(s, []).append((h_peak, h_T, jh["h_cm"], jh.get("T_flight", np.nan), T_full))
        except Exception as ex:
            print(f"{s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    print(f"\n{'세션':<10} {'n':>3} {'h직접[cm]':>10} {'h_T[cm]':>8} {'실측h':>7} "
          f"{'sim T[s]':>9} {'실측T[s]':>9} {'배율':>6}")
    P1, P2, R = [], [], []
    for s in sorted(rows):
        a = np.array(rows[s], float)
        hp, hT, hr = np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2])
        Tr, Ts = np.nanmedian(a[:, 3]), np.median(a[:, 4])
        P1.append(hp); P2.append(hT); R.append(hr)
        print(f"{s:<10} {len(a):3d} {hp:10.1f} {hT:8.1f} {hr:7.1f} {Ts:9.3f} {Tr:9.3f} {hp/hr:6.2f}")
    print(f"{'평균':<10} {'':>3} {np.mean(P1):10.1f} {np.mean(P2):8.1f} {np.mean(R):7.1f} "
          f"{'':>9} {'':>9} {np.mean(P1)/np.mean(R):6.2f}")
    print(f"\n|Δh| (직접) 평균 {np.mean(np.abs(np.array(P1)-np.array(R))):.2f}cm")


if __name__ == "__main__":
    main()
