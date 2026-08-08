# -*- coding: utf-8 -*-
"""_G75_seedzoom — 세션 발 시드를 **확대해서 직접 읽기** (마라톤G, 08-09).

왜 수동인가
  자동 전역 탐색은 광학테이블 볼트머리·트러스구멍·브래킷 나사에 진다 (REJECTED #78 계열).
  반지름 사전으로 구속해도, 같은 720px 규격 안에서 발 지름이 26~32px 로 달라
  (카메라 거리 차이) 사전 범위가 하한 포화값 14.7 을 포함해 버린다.
  등재한 세션(0723·0424)은 **둘 다 성공**했다 → 세션당 한 번 읽는 게 확실하고 빠르다.

사용
  python _G75_seedzoom.py <세션> [cx cy]     # cx,cy 없으면 하단 전체를 격자로 뽑는다
  → 발 롤러 중심과 **금속판 반지름**을 읽어 fs_slipmeas.SEED_CAL 에 등재.
  ★ 반지름까지 정확해야 한다 — 중심만 맞고 반지름이 틀리면 추적이 조용히 무너진다
    (0424 에서 r 20 vs 실제 33 으로 세 번 실패).
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_slipmeas as SM                                       # noqa: E402

OUT = HERE / "graphs" / "G72_seed"


def _f(sz):
    try:
        return ImageFont.truetype("malgun.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def main():
    import fs_data as FD
    import imageio.v3 as iio
    sess = sys.argv[1]
    ctr = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) >= 4 else None
    p = [q for s, q, g, c, h in FD.registry() if s == sess][0]
    mp4 = [v for v in sorted(Path(p).glob("*.mp4")) if "online-video-cutter" not in v.name][0]
    vm = SM.video_meta(mp4); ds = vm["ds"]
    prof = SM.motion_profile(mp4, k=vm["k"], ds=ds)
    f_lo, a, b = SM.liftoff_frame(prof)
    f_sit = max(4, f_lo - max(6, int(round(0.6 * vm["fps"]))))
    G = None
    for i, fr in enumerate(iio.imiter(mp4)):
        if i == f_sit:
            G = np.asarray(fr)[::ds, ::ds] if ds > 1 else np.asarray(fr)
            break
    H, W = G.shape[0], G.shape[1]
    if ctr is None:                       # 1단계: 하단 전체 격자
        y0 = int(H * 0.72); crop = G[y0:H]; Z = max(1, int(1500 / W))
        im = Image.fromarray(crop.astype("uint8")).convert("RGB")
        im = im.resize((W * Z, (H - y0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(im); ft = _f(16 + 4 * Z)
        for x in range(0, W, 25):
            dr.line([(x * Z, 0), (x * Z, im.height)], fill=(0, 190, 190), width=1)
            if x % 50 == 0:
                dr.text((x * Z + 2, 2), str(x), fill=(0, 255, 255), font=ft,
                        stroke_width=2, stroke_fill=(0, 0, 0))
        for y in range(y0, H, 25):
            dr.line([(0, (y - y0) * Z), (im.width, (y - y0) * Z)], fill=(0, 190, 190), width=1)
            if y % 50 == 0:
                dr.text((3, (y - y0) * Z + 2), str(y), fill=(0, 255, 255), font=ft,
                        stroke_width=2, stroke_fill=(0, 0, 0))
        dr.text((8, im.height - 40), f"{sess}  f{f_sit}  ds={ds}  처리 {W}x{H}",
                fill=(255, 255, 0), font=_f(26), stroke_width=3, stroke_fill=(0, 0, 0))
        fn = OUT / f"_zoom1_{sess.replace('.', '_')}.png"
    else:                                  # 2단계: 지목 지점 확대 (반지름 눈금 포함)
        cx, cy = ctr; Wd = 150; Z = 6
        x0 = int(np.clip(cx - Wd // 2, 0, W - Wd)); y0 = int(np.clip(cy - Wd // 2, 0, H - Wd))
        im = Image.fromarray(G[y0:y0 + Wd, x0:x0 + Wd].astype("uint8")).convert("RGB")
        im = im.resize((Wd * Z, Wd * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(im); ft = _f(20)
        for k in range(0, Wd + 1, 10):
            dr.line([(k * Z, 0), (k * Z, Wd * Z)], fill=(0, 170, 170), width=1)
            dr.line([(0, k * Z), (Wd * Z, k * Z)], fill=(0, 170, 170), width=1)
            dr.text((k * Z + 2, 2), str(x0 + k), fill=(0, 255, 255), font=ft,
                    stroke_width=2, stroke_fill=(0, 0, 0))
            dr.text((3, k * Z + 2), str(y0 + k), fill=(0, 255, 255), font=ft,
                    stroke_width=2, stroke_fill=(0, 0, 0))
        for r in (12, 16, 20, 24, 28, 33):     # 반지름 눈금 — 어디에 맞는지 고른다
            dr.ellipse([(cx - r - x0) * Z, (cy - r - y0) * Z,
                        (cx + r - x0) * Z, (cy + r - y0) * Z], outline=(255, 70, 70), width=3)
            dr.text(((cx + r - x0) * Z + 3, (cy - y0) * Z - 12), f"r{r}", fill=(255, 120, 120),
                    font=ft, stroke_width=3, stroke_fill=(0, 0, 0))
        dr.text((8, Wd * Z - 34), f"{sess} f{f_sit}  중심({cx:.0f},{cy:.0f})",
                fill=(255, 255, 0), font=_f(24), stroke_width=3, stroke_fill=(0, 0, 0))
        fn = OUT / f"_zoom2_{sess.replace('.', '_')}.png"
    im.save(fn)
    print(f"저장 {fn}  · f_sit={f_sit} ds={ds} 처리 {W}x{H}")


if __name__ == "__main__":
    main()
