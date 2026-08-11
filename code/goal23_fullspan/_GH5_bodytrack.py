# -*- coding: utf-8 -*-
"""_GH5_bodytrack — 영상에서 **몸통이 앞뒤로 흔들리는지** 잰다 (마라톤H, 2026-08-11).

왜 (사용자 지시 "몸통도 추적해서 앞뒤로 흔들리는지 재봐")
  관절각이 요구하는 발 앞뒤 이동(+10.7mm 중앙)과 영상이 본 실제 이동(+4.5mm)이
  **7mm 어긋난다.** 베이스가 세로 레일에만 붙어 있다면 발은 관절각이 정한 자리에
  있어야 하므로 이건 기하학적 모순이다. 각도 오프셋으로도(사용자 한계 ±3° 적용) 설명이
  안 된다(7.1mm 잔여). 남은 후보는 **베이스가 앞뒤로 움직인다**.

방법
  프레임마다 두 곳을 2차원 상관추적한다.
    · **몸통** = 모터 뭉치 (레일 위를 오르내리므로 세로로도 따라가야 한다)
    · **정지기준** = 벽에 붙은 눈금자 (카메라 흔들림 보정용 — 이게 움직이면 카메라가 움직인 것)
  몸통 x 변위에서 정지기준 x 변위를 빼면 **몸통의 진짜 앞뒤 이동**이다.
  자(mm/px)는 슬립 측정에서 쓴 것과 같은 값(발 금속판 30mm 기준)을 쓴다.

★ 한계: 원근. 몸통은 발보다 카메라에 가까울 수 있어 같은 자를 쓰면 크기가 어긋난다.
  그래서 **절대 크기보다 "움직이는가/언제 움직이는가"** 를 먼저 본다.

CLI: python _GH5_bodytrack.py [세션/trial ...]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GH5_bodytrack.json"


def ncc_track(ref, img, cx, cy, half, win):
    """정규화 상관으로 템플릿 위치 찾기. 반환 (x, y, 점수). 부화소는 포물선 보간."""
    h, w = img.shape
    y0, y1 = int(cy - half), int(cy + half + 1)
    x0, x1 = int(cx - half), int(cx + half + 1)
    T = ref[y0:y1, x0:x1]
    T = T - T.mean()
    tn = np.sqrt((T * T).sum()) + 1e-9
    best = (-2.0, 0, 0)
    S = {}
    for dy in range(-win, win + 1):
        for dx in range(-win, win + 1):
            a, b = y0 + dy, y1 + dy
            c, d = x0 + dx, x1 + dx
            if a < 0 or c < 0 or b > h or d > w:
                continue
            P = img[a:b, c:d]
            P = P - P.mean()
            v = float((T * P).sum() / (tn * (np.sqrt((P * P).sum()) + 1e-9)))
            S[(dy, dx)] = v
            if v > best[0]:
                best = (v, dy, dx)
    sc, dy, dx = best
    # x 부화소 (포물선)
    l = S.get((dy, dx - 1)); r = S.get((dy, dx + 1))
    if l is not None and r is not None and (l - 2 * sc + r) != 0:
        dx = dx + 0.5 * (l - r) / (l - 2 * sc + r)
    return cx + dx, cy + dy, sc


def run_one(sess, trial, body_xy=None, ref_xy=None, half=60, win=70, step=2):
    import fs_data as FD
    import imageio.v3 as iio
    M = json.load(io.open(HERE / "_G72_slipall.json", encoding="utf-8"))
    v = [x for x in M.values() if x.get("sess") == sess and x.get("trial") == trial][0]
    p = [q for s, q, g, c, h in FD.registry() if s == sess and q.name == trial][0]
    mp4 = [x for x in sorted(Path(p).glob("*.mp4")) if "online-video-cutter" not in x.name][0]
    se = v["series"]; f0 = int(se["f"][0]); f1 = int(v["f_end"])
    sc = float(v["scale"]) * float(v["px_k"])
    fx0, fy0 = float(se["cx"][0]), float(se["cy"][0])
    G = {}
    for i, fr in enumerate(iio.imiter(mp4)):
        if f0 <= i <= f1 and (i - f0) % step == 0:
            G[i] = np.asarray(fr, float)[..., :3].mean(axis=2)
        if i > f1:
            break
    ks = sorted(G)
    if len(ks) < 6:
        return None
    ref = G[ks[0]]
    H, W = ref.shape
    # 몸통 = 발에서 위로 (다리 길이 ~500mm) · 정지기준 = 왼쪽 벽 (발보다 위, 가장자리)
    bx, by = body_xy if body_xy else (fx0, max(half + 5, fy0 - 560.0 / sc))
    rx, ry = ref_xy if ref_xy else (max(half + 5, W * 0.09), H * 0.45)
    B = []; R = []
    pb = (bx, by); pr = (rx, ry)
    for k in ks:
        pb = ncc_track(ref, G[k], pb[0], pb[1], half, win)[:2] if k != ks[0] else (bx, by)
        pr = ncc_track(ref, G[k], pr[0], pr[1], half, 12)[:2] if k != ks[0] else (rx, ry)
        B.append(pb); R.append(pr)
    B = np.array(B); R = np.array(R)
    xb = (B[:, 0] - B[0, 0]) * sc          # 몸통 x [mm]
    xr = (R[:, 0] - R[0, 0]) * sc          # 카메라 흔들림 [mm]
    return dict(sess=sess, trial=trial, f=ks, scale=sc,
                body_x=xb.tolist(), ref_x=xr.tolist(),
                body_y=((B[:, 1] - B[0, 1]) * sc).tolist(),
                body_xy0=[bx, by], ref_xy0=[rx, ry])


def main():
    want = sys.argv[1:] or ["26.07.22/150_3.3_500_5", "26.07.22/60_0.75_60_2",
                            "26.07.27/150_2.2_250_3", "26.07.25/150_2.2_250_3"]
    res = {}
    for w in want:
        s, t = w.split("/")
        try:
            r = run_one(s, t)
        except Exception as ex:
            print(f"  ✗ {w}: {type(ex).__name__} {str(ex)[:60]}", flush=True); continue
        if r is None:
            print(f"  ✗ {w}: 프레임 부족", flush=True); continue
        res[w] = r
        b = np.array(r["body_x"]); c = np.array(r["ref_x"])
        net = b - c
        print(f"{w:32s} 몸통 앞뒤 {net.min():+6.1f} ~ {net.max():+6.1f} mm "
              f"(폭 {net.max()-net.min():5.1f}) · 카메라 흔들림 {c.max()-c.min():4.1f} mm", flush=True)
    if res:
        import safe
        safe.atomic_json_write(OUT, res)
        print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
