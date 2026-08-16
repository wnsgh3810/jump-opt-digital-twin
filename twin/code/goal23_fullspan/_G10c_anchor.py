# -*- coding: utf-8 -*-
"""_G10c_anchor — `실제 점프 높이`(**영상 실측**, 사용자 확정 08-07)를 A급 앵커로 재계산.

사용자 확정: "Expected 이건 믿지마. 실제 점프 높이 적힌거만 봐 — 그건 영상으로 잰거니까 정확해."
⇒ ①`Expected Maximum Jump State` 블록은 전량 무시 ②GRF 체공시간 경로도 h 지표로 쓰지 않는다
  (h_B/h_실측 0.919 = 8% 과소 — 레일 마찰·착지 자세차. 데이터 사전의 'GRF 타이밍 전용' 규칙과 정합)
③이지 CoM 속도를 **영상 h 에서 역산**해 ΔE 를 다시 잡고, 척도 판정을 재확인한다.

  rise_needed = h_영상 − [z_CoM(이지) + (z_base−z_CoM)(정점 자세)]
  ż_anchor    = √(2g·rise_needed)
  KE(이지)    = ½M·ż_anchor² + KE_내부(관절 상대운동, 운동학 그대로)
CLI: python _G10c_anchor.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                        # noqa: E402
import fs_runner as FR                                      # noqa: E402
from _G10_energy import Reduced, tau_canon, lpf, real_h, G, M_REAL, FC1, FV1, FC2, FV2  # noqa: E402
from _G10b_scale import MU, ARM                             # noqa: E402


def main():
    R = Reduced(FR.fs_twin())
    print("=" * 120)
    print("영상 실측 h 를 앵커로 이지 CoM 속도 역산 → ΔE 재산출 → 척도 판정 재확인")
    print(f"{'세션':<11}{'trial':<19}{'ż_운동학':>9}{'ż_영상앵커':>11}{'비':>6}"
          f"{'ΔE_운동학':>10}{'ΔE_앵커':>9}{'필요일':>8}{'W_a':>8}{'W_c':>8}{'s_a':>6}{'s_c':>6}")
    A = []
    for sess, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hC = real_h(p)
        if hC is None:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]; dt = float(np.median(np.diff(t)))
        q1 = lpf(d["q1"], 30.0); q2 = lpf(d["q2"], 30.0)
        v1 = np.gradient(q1, dt); v2 = np.gradient(q2, dt)
        lo, hi = seg["i_push"], min(seg["i_lo"] + int(0.06 / dt), len(t) - 3)
        S = [R.MV(q1[i], q2[i]) for i in range(lo, hi)]
        zb = np.array([s["dzb"] @ np.array([v1[i], v2[i]]) for i, s in zip(range(lo, hi), S)])
        k = int(np.argmax(zb)); ito = lo + k; s1 = S[k]
        i0 = seg["i_bot"] if ito - seg["i_bot"] >= 30 else max(0, ito - int(0.35 / dt))
        s0 = R.MV(q1[i0], q2[i0])
        Am = np.diag(ARM)
        dq0 = np.array([v1[i0], v2[i0]]); dq1 = np.array([v1[ito], v2[ito]])
        KE1 = 0.5 * dq1 @ (s1["M"] + Am) @ dq1
        KE0 = 0.5 * dq0 @ (s0["M"] + Am) @ dq0
        vk = float(s1["dzc"] @ dq1)                       # 운동학 CoM 속도
        # 정점 자세: 탄도 상승시간 후의 실제 관절각
        j = min(ito + int(max(vk, 0) / G / dt), len(q1) - 1)
        sa = R.MV(q1[j], q2[j]); off = sa["zb"] - sa["zc"]
        rise = max(hC - off - s1["zc"], 1e-4)
        va = float(np.sqrt(2 * G * rise))                 # 영상 앵커 CoM 속도
        KE_int = KE1 - 0.5 * M_REAL * vk ** 2             # 내부(관절 상대) 운동에너지
        KE1a = 0.5 * M_REAL * va ** 2 + KE_int
        dE_k = KE1 + s1["V"] - (KE0 + s0["V"])
        dE_a = KE1a + s1["V"] - (KE0 + s0["V"])
        sl = slice(i0, ito + 1)
        tc1, tc2 = tau_canon(d["raw1"]), tau_canon(d["raw2"])
        Wa = float(np.trapezoid(d["a1"][sl] * v1[sl] + d["a2"][sl] * v2[sl], dx=dt))
        Wc = float(np.trapezoid(tc1[sl] * v1[sl] + tc2[sl] * v2[sl], dx=dt))
        Wjf = float(np.trapezoid(FC1 * np.abs(v1[sl]) + FV1 * v1[sl] ** 2
                                 + FC2 * np.abs(v2[sl]) + FV2 * v2[sl] ** 2, dx=dt))
        SS = [R.MV(q1[i], q2[i]) for i in range(i0, ito + 1, 3)]
        vv = np.array([[lpf(v1, 20.0)[i], lpf(v2, 20.0)[i]] for i in range(i0, ito + 1, 3)])
        vx = np.array([s["dxf"] @ vv[m] for m, s in enumerate(SS)])
        vth = np.array([s["dth"] @ vv[m] for m, s in enumerate(SS)])
        zc = np.array([s["zc"] for s in SS])
        N = np.maximum(M_REAL * (G + np.gradient(np.gradient(zc, 3 * dt), 3 * dt)), 0.0)
        Wsl = MU * float(np.trapezoid(N * np.abs(vx - R.r * vth), dx=3 * dt))
        need = dE_a + Wjf + Wsl
        A.append((vk, va, dE_k, dE_a, need, Wa, Wc))
        print(f"{sess:<11}{p.name[:18]:<19}{vk:9.2f}{va:11.2f}{va/vk:6.3f}"
              f"{dE_k:10.2f}{dE_a:9.2f}{need:8.2f}{Wa:8.2f}{Wc:8.2f}"
              f"{need/Wa:6.3f}{need/Wc:6.3f}")
    a = np.array(A)
    f = lambda x: f"{np.median(x):.3f} [{np.percentile(x,10):.3f}, {np.percentile(x,90):.3f}]"
    print("\n" + "=" * 120)
    print(f"  ż 영상앵커 / ż 운동학        {f(a[:,1]/a[:,0])}   ← 1.0 이면 트윈 CoM 야코비안 정확")
    print(f"  ΔE 앵커 / ΔE 운동학          {f(a[:,3]/a[:,2])}")
    print(f"  ΔE [J]                       {f(a[:,3])}")
    print(f"  필요일 [J]                   {f(a[:,4])}")
    print(f"  ★ 필요 배율 s(a_hat)         {f(a[:,4]/a[:,5])}   (<1 인 건수 {int((a[:,4]<a[:,5]).sum())}/{len(a)})")
    print(f"  ★ 필요 배율 s(정본)          {f(a[:,4]/a[:,6])}   (>1 인 건수 {int((a[:,4]>a[:,6]).sum())}/{len(a)})")
    print(f"  손실 무시한 하한: η(a_hat)   {f(a[:,3]/a[:,5])}   (η>1 = 에너지창조 {int((a[:,3]>a[:,5]).sum())}/{len(a)})")
    print(f"                    η(정본)    {f(a[:,3]/a[:,6])}")
    json.dump(dict(s_a=list(map(float, a[:, 4] / a[:, 5])), s_c=list(map(float, a[:, 4] / a[:, 6])),
                   dE=list(map(float, a[:, 3])), vratio=list(map(float, a[:, 1] / a[:, 0]))),
              io.open(HERE / "_G10c_anchor.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n저장: _G10c_anchor.json")


if __name__ == "__main__":
    main()
