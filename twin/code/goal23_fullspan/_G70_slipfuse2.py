# -*- coding: utf-8 -*-
"""_G70_slipfuse2 — **정본 자(발 롤러)로 재계산한 영상+엔코더 융합 슬립** (마라톤G, 08-08).

_G68 대비 바뀐 세 가지 (전부 사용자 발견/제보에서 출발)
  ① **자 교체**: 발판 플레이트 120mm(0.7453 mm/px) → **발 롤러**(그 영상에서 직접 측정).
     원 맞춤이 잡는 경계는 **안쪽 금속 원판 30.0mm** (고무 바깥은 검은 패드와 명암차 없음).
     32.40 px = 30.0 mm → **0.9259 mm/px**. 구 자는 금속판을 24.1mm 로 본 셈 = **1.242배** 과소.
  ② **추적점 교체**: 링크 연결부(롤러 중심에서 10.3mm 오른쪽, 종아리 회전에 따라 궤도운동)
     → **원 맞춤으로 얻은 롤러 기하 중심** (`fs_vidscale.fit_roller`).
  ③ **접지 반경 교체**: r = 21.0 → **20.0 mm** (바깥 지름 40mm/2, 사용자 실측 08-08).
     MuJoCo `foot` geom 은 아직 0.021 — 수정 필요.

원리 (왜 영상만으로도, 엔코더만으로도 안 되는가)
  | 측정 | 얻는 것 | 못 얻는 것 |
  |---|---|---|
  | 엔코더 q1,q2 | **Δθ_발** (4절 폐쇄로 결정, **베이스 위치와 무관**) | Δx_발 |
  | 영상(롤러 중심) | **Δx_발** (세계 좌표 실측) | Δθ_발 (롤러 표면 마커 없음) |
        **슬립(t) = Δx_발(영상) − r·Δθ_발(엔코더)**,  r = 20.0 mm
  비유: 바퀴가 굴러간 거리는 "바퀴가 몇 바퀴 돌았나"(엔코더)로 알고, 실제로 몇 cm 갔나는
  자로 재야(영상) 안다. 둘이 안 맞는 차이가 곧 **미끄러짐**이다.

부호: **+ = 화면 오른쪽 = 모델 +x** (사용자 확정 08-08)

CLI: python _G70_slipfuse2.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
import fs_vidscale as VS                                      # noqa: E402
from _G10_energy import Reduced                               # noqa: E402
from _G13_board import lpf                                    # noqa: E402

SESS, TRIAL = "26.07.23", "150_2.2_250_3"
OLD_SCALE = 0.7453                     # 폐기된 플레이트 자 (대조용)


def main():
    V = json.load(io.open(HERE / "_G_videoslip.json", encoding="utf-8"))
    fps = V["_meta"]["fps"]; shift = V["sync"]["shift_SH_s"]; fb = V["frame_bounds"]

    sc = VS.scale_of(SESS, TRIAL)
    s_mm = sc["scale_mm_per_px"]

    FIT = json.load(io.open(HERE / "_G70_diskfit.json", encoding="utf-8"))
    fi = np.array(sorted(int(k) for k in FIT), float)
    xpx = np.array([FIT[str(int(k))]["cx"] for k in fi], float)
    # * 평활 금지. 3프레임 이동중앙값을 넣었더니 **푸시의 급변을 뭉개** f199 를
    #   -56.5 -> -38.5mm 로 깎아먹었다 (마지막 프레임은 이웃이 한쪽뿐이라 더 심함).
    #   서브픽셀 정밀화(0.1px)로 이미 격자 잡음은 없다 - 원자료 그대로 쓴다.
    xs = xpx
    t_vid = fi / fps + shift

    R = Reduced(FR.fs_twin())
    r = VS.FOOT_R_M            # ★ 0.020 m (바깥 40mm/2) — 모델 geom 0.021 은 오류
    p = [q for s, q, g, c, h in FD.registry() if s == SESS and q.name == TRIAL][0]
    d = FD.load2(p); t = d["t"]
    q1f = lpf(d["q1"], 30.0); q2f = lpf(d["q2"], 30.0)
    th = np.array([R.state(q1f[i], q2f[i])[2] for i in range(0, len(t), 2)])
    th_v = np.interp(t_vid, t[::2], th)

    i0 = int(np.argmin(np.abs(fi - fb["f_desc0"])))
    x_mm = (xs - xs[i0]) * s_mm
    roll = r * (th_v - th_v[i0]) * 1000.0
    slip = x_mm - roll

    print("=" * 100)
    print(f"★ 융합 슬립 (정본 자) — {SESS}/{TRIAL}")
    print(f"   발 지름 {sc['dia_px']:.2f} px = {VS.FOOT_DIA_MM:.0f} mm → **{s_mm:.4f} mm/px** "
          f"(±{sc['rel_sd']*100:.1f}%) · 구 자 {OLD_SCALE} 대비 ×{s_mm/OLD_SCALE:.3f}")
    print(f"   r = {r*1000:.1f} mm · fps {fps} · 부호 + = 화면 오른쪽 = 모델 +x")

    B = [("하강 전반", fb["f_desc0"], (fb["f_desc0"] + fb["f_bot"]) // 2),
         ("하강 후반(깊게)", (fb["f_desc0"] + fb["f_bot"]) // 2, fb["f_bot"]),
         ("바닥유지", fb["f_bot"], fb["f_push"]),
         ("푸시~이륙", fb["f_push"], fb["f_lo"]),
         ("전체(하강~이륙)", fb["f_desc0"], fb["f_lo"])]
    print(f"\n{'구간':<20}{'t [s]':>14}{'영상 Δx':>11}{'구름 rΔθ':>11}{'**슬립**':>11}{'(구 자)':>10}")
    for lab, a, b in B:
        ia = int(np.argmin(np.abs(fi - a))); ib = int(np.argmin(np.abs(fi - b)))
        dx = x_mm[ib] - x_mm[ia]; rr = roll[ib] - roll[ia]
        old = (xs[ib] - xs[ia]) * OLD_SCALE - rr
        print(f"{lab:<20}{f'{t_vid[ia]:.2f}~{t_vid[ib]:.2f}':>14}"
              f"{dx:11.2f}{rr:11.2f}{dx-rr:11.2f}{old:10.2f}")

    # 사용자 지목 구간 — ★ 시각은 **영상 시계**(frame/fps) 기준 (데이터 시계 아님)
    print(f"\n★ 사용자 지목 구간 (영상 시계 기준)")
    t_v0 = fi / fps
    for a, b, say in ((6.67, 7.42, "깊게 앉는 순간 (육안 −10~15mm)"),
                      (6.67, 8.17, "사용자 재확인 (육안 8.xx mm)"),
                      (8.00, 8.29, "푸시~이륙 (육안 −60mm = 플레이트 절반)"),
                      (8.21, 8.29, "마지막 2프레임 (폭발 구간)")):
        ia = int(np.argmin(np.abs(t_v0 - a))); ib = int(np.argmin(np.abs(t_v0 - b)))
        dx = x_mm[ib] - x_mm[ia]; rr = roll[ib] - roll[ia]
        print(f"   {a:.2f}~{b:.2f}s (f{int(fi[ia])}~f{int(fi[ib])})  영상 Δx {dx:+7.2f} · "
              f"구름 {rr:+7.2f} · **슬립 {dx-rr:+7.2f}** mm   ← {say}")

    print(f"\n{'프레임':>7}{'t[s]':>8}{'영상Δx':>10}{'구름':>9}{'슬립':>9}   국면")
    for k in range(0, len(fi), 4):
        f_ = int(fi[k])
        ph = ("하강" if f_ < fb["f_bot"] else "유지" if f_ < fb["f_push"]
              else "푸시" if f_ <= fb["f_lo"] else "비행")
        print(f"{f_:7d}{t_vid[k]:8.2f}{x_mm[k]:10.2f}{roll[k]:9.2f}{slip[k]:9.2f}   {ph}")

    json.dump(dict(scale=sc, frame=fi.tolist(), t=t_vid.tolist(), x_mm=x_mm.tolist(),
                   roll_mm=roll.tolist(), slip_mm=slip.tolist()),
              io.open(HERE / "_G70_slipfuse2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G70_slipfuse2.json")


if __name__ == "__main__":
    main()
