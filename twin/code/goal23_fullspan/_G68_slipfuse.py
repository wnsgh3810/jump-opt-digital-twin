# -*- coding: utf-8 -*-
"""_G68_slipfuse — **영상 + 엔코더 융합**으로 구름/슬립을 실제로 분해 (마라톤G, 08-08).

왜 이게 가능한가 (사용자 질문 "영상과 hip,knee 각도로 제대로 측정 못하려나?" 의 답)
  각각으로는 못 하지만 **합치면 된다**:
  | 측정 | 얻는 것 | 못 얻는 것 |
  |---|---|---|
  | 엔코더 q1,q2 | **Δθ_발** — 발은 종아리와 한 몸이라 4절 폐쇄로 결정. **베이스 위치와 무관** | Δx_발 |
  | 영상(발 볼트 추적) | **Δx_발** — 세계 좌표 실측 | Δθ_발 (롤러 표면 마커 부재) |
        **슬립(t) = Δx_발(영상) − r·Δθ_발(엔코더)**
  `_G_videoslip.json` 의 "분해 불가"는 **영상만** 봤을 때의 결론이다.

부호 규약 (사용자 확정 08-08)
  "앉는 동안 구름으로 발끝 중심이 **오른쪽**으로 갔다" + 엔코더 하강 r·Δθ = **+9.86mm (모델 +x)**
  ⇒ **모델 +x = 화면 오른쪽**. 이 매핑으로 영상 px 증가(+screen-right) = +x.

기존 지표와의 차이 (왜 갈아타야 하나)
  구 `기하 슬립` 은 Δx 를 **모델**(베이스 x 고정 가정)에서 뽑았다. 전수 검정 결과
  |모델Δx|/|구름| 중앙 **3.23** (25일은 13~17배) — 베이스 수평 이동·기하 오차가 전부
  '슬립' 으로 잘못 계상된다. 여기서는 Δx 를 **영상 실측**으로 바꾼다.

CLI: python _G68_slipfuse.py
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
from _G10_energy import Reduced                               # noqa: E402
from _G13_board import lpf                                    # noqa: E402

TRIAL = ("26.07.23", "150_2.2_250_3")


def main():
    V = json.load(io.open(HERE / "_G_videoslip.json", encoding="utf-8"))
    R = Reduced(FR.fs_twin()); r = R.r
    tr = V["track"]; sc = V["scale"]["scale_mm_per_px"]
    fps = V["_meta"]["fps"]; shift = V["sync"]["shift_SH_s"]
    fb = V["frame_bounds"]
    fi = np.asarray(tr["frame_idx"], float)
    xpx = np.asarray(tr["x_px"], float)
    ok = np.isfinite(xpx)
    fi, xpx = fi[ok], xpx[ok]
    t_vid = fi / fps + shift                     # 데이터 시간축으로
    x_mm = (xpx - xpx[0]) * sc                   # 첫 프레임 기준 변위 [mm], + = 화면 오른쪽

    p = [q for s, q, g, c, h in FD.registry() if s == TRIAL[0] and q.name == TRIAL[1]][0]
    d = FD.load2(p); seg = FD.segment(d); t = d["t"]
    q1f = lpf(d["q1"], 30.0); q2f = lpf(d["q2"], 30.0)
    # 엔코더 → 발 각도 (4절 폐쇄). 베이스 위치와 무관한 **내부 형상 변수**
    th = np.array([R.state(q1f[i], q2f[i])[2] for i in range(0, len(t), 2)])
    tt = t[::2]
    th_v = np.interp(t_vid, tt, th)
    roll_mm = r * (th_v - th_v[0]) * 1000        # 구름분 [mm], + = 모델 +x = 화면 오른쪽
    slip = x_mm - roll_mm                        # ★ 융합 슬립

    print("=" * 104)
    print(f"★ 영상+엔코더 융합 슬립 — {TRIAL[0]}/{TRIAL[1]}")
    print(f"   r = {r*1000:.1f} mm · 스케일 {sc:.4f} mm/px · fps {fps} · 부호 + = 화면 오른쪽 = 모델 +x")
    B = [("하강 전반", fb["f_desc0"], (fb["f_desc0"] + fb["f_bot"]) // 2),
         ("하강 후반(깊게)", (fb["f_desc0"] + fb["f_bot"]) // 2, fb["f_bot"]),
         ("바닥유지", fb["f_bot"], fb["f_push"]),
         ("푸시~이륙", fb["f_push"], fb["f_lo"])]
    print(f"\n{'구간':<18}{'프레임':>12}{'영상 Δx':>10}{'구름 rΔθ':>11}{'**슬립**':>11}")
    for lab, a, b in B:
        ia = int(np.argmin(np.abs(fi - a))); ib = int(np.argmin(np.abs(fi - b)))
        dx = x_mm[ib] - x_mm[ia]; rr = roll_mm[ib] - roll_mm[ia]
        print(f"{lab:<18}{f'{a}~{b}':>12}{dx:10.2f}{rr:11.2f}{dx-rr:11.2f}")
    ia = int(np.argmin(np.abs(fi - fb["f_desc0"]))); ib = int(np.argmin(np.abs(fi - fb["f_lo"])))
    print(f"{'전체(하강~이륙)':<18}{f'{fb[chr(102)+chr(95)+chr(100)+chr(101)+chr(115)+chr(99)+chr(48)]}~{fb[chr(102)+chr(95)+chr(108)+chr(111)]}':>12}"
          f"{x_mm[ib]-x_mm[ia]:10.2f}{roll_mm[ib]-roll_mm[ia]:11.2f}{(x_mm[ib]-x_mm[ia])-(roll_mm[ib]-roll_mm[ia]):11.2f}")

    print("\n" + "=" * 104)
    print("★ 프레임별 추이 (하강 개시 기준 누적)")
    print(f"{'프레임':>7}{'t[s]':>8}{'영상 Δx':>10}{'구름':>9}{'슬립':>9}   국면")
    for k in range(0, len(fi), 4):
        f_ = int(fi[k])
        ph = ("하강" if f_ < fb["f_bot"] else "유지" if f_ < fb["f_push"]
              else "푸시" if f_ <= fb["f_lo"] else "비행")
        print(f"{f_:7d}{t_vid[k]:8.3f}{x_mm[k]:10.2f}{roll_mm[k]:9.2f}{slip[k]:9.2f}   {ph}")
    json.dump(dict(frame=fi.tolist(), t=t_vid.tolist(), x_mm=x_mm.tolist(),
                   roll_mm=roll_mm.tolist(), slip_mm=slip.tolist()),
              io.open(HERE / "_G68_slipfuse.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G68_slipfuse.json")


if __name__ == "__main__":
    main()
