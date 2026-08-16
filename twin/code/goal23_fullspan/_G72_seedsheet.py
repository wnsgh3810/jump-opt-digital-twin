# -*- coding: utf-8 -*-
"""_G72_seedsheet — **세션별 발 시드**를 눈으로 읽기 위한 시트 (마라톤G, 08-08).

왜 세션별 수동 시드인가
  전역 원 탐색은 **광학 테이블 볼트 머리·브래킷 나사·트러스 구멍**이 점수에서 이긴다.
  0424(원거리 4K)에선 상위 12후보에 발이 아예 없었다. 자동 판별 두 가지도 실패했다
  ("이륙 때 움직인 원" → 트러스 구멍 / "가장 아래 원" → 광학 테이블 구멍).
  카메라 배치는 **세션 단위로 일정**하므로, 세션마다 한 번만 읽어 `fs_slipmeas.SEED_CAL`
  에 등재한다. trial 별 차이는 넉넉한 창 + **반지름 구속**(±30%)이 흡수한다.

무엇을 그리나
  세션마다 대표 trial 의 **스쿼트 바닥 프레임**을 처리 해상도(ds 적용)로 저장하고,
  50px 격자에 좌표를 찍는다. 발 롤러 중심 (cx, cy) 와 대략 반지름을 읽어 SEED_CAL 에 넣는다.

CLI: python _G72_seedsheet.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_slipmeas as SM                                       # noqa: E402

OUTDIR = HERE / "graphs" / "G72_seed"


def main():
    import fs_data as FD
    import imageio.v3 as iio
    OUTDIR.mkdir(parents=True, exist_ok=True)
    try:
        f1 = ImageFont.truetype("malgun.ttf", 17); f2 = ImageFont.truetype("malgun.ttf", 30)
    except Exception:
        f1 = f2 = ImageFont.load_default()

    seen = {}
    for s, p, g, cvt, ho in FD.registry():
        if s in seen:
            continue
        v = [q for q in sorted(Path(p).glob("*.mp4")) if "online-video-cutter" not in q.name]
        if v:
            seen[s] = (p, v[0])

    print(f"세션 {len(seen)}개")
    for s, (p, mp4) in sorted(seen.items()):
        try:
            vm = SM.video_meta(mp4); ds = vm["ds"]
            prof = SM.motion_profile(mp4, k=vm["k"], ds=ds)
            f_lo, a, b = SM.liftoff_frame(prof)
            if f_lo is None:
                print(f"  ✗ {s}: 이륙 검출 실패"); continue
            f_sit = max(4, f_lo - max(6, int(round(0.6 * vm["fps"]))))
            G = None
            for i, fr in enumerate(iio.imiter(Path(mp4))):
                if i == f_sit:
                    G = np.asarray(fr)[::ds, ::ds] if ds > 1 else np.asarray(fr)
                    break
            if G is None:
                print(f"  ✗ {s}: 프레임 읽기 실패"); continue
            im = Image.fromarray(G.astype("uint8")).convert("RGB")
            H, W = G.shape[0], G.shape[1]
            im = im.crop((0, int(H * 0.45), W, H))            # 아래쪽 절반만 (발이 있는 영역)
            dr = ImageDraw.Draw(im)
            oy = int(H * 0.45)
            for x in range(0, W, 50):
                dr.line([(x, 0), (x, im.height)], fill=(0, 190, 190), width=1)
                dr.text((x + 2, 2), str(x), fill=(0, 255, 255), font=f1,
                        stroke_width=2, stroke_fill=(0, 0, 0))
            for y in range(oy - oy % 50, H, 50):
                dr.line([(0, y - oy), (W, y - oy)], fill=(0, 190, 190), width=1)
                dr.text((3, y - oy + 2), str(y), fill=(0, 255, 255), font=f1,
                        stroke_width=2, stroke_fill=(0, 0, 0))
            dr.text((8, im.height - 44),
                    f"{s} / {Path(p).name}  f{f_sit} (스쿼트 바닥)  ds={ds} 처리 {W}x{H}",
                    fill=(255, 255, 0), font=f2, stroke_width=3, stroke_fill=(0, 0, 0))
            z = 2 if W < 900 else 1
            if z > 1:
                im = im.resize((im.width * z, im.height * z), Image.LANCZOS)
            fn = OUTDIR / f"{s.replace('.', '_')}.png"
            im.save(fn)
            print(f"  ✔ {s}  {fn.name}  (ds={ds} {W}x{H} f_sit={f_sit})")
        except Exception as ex:
            print(f"  ✗ {s}: {type(ex).__name__} {str(ex)[:60]}")
    print(f"\n→ {OUTDIR}  ·  발 롤러 중심을 읽어 fs_slipmeas.SEED_CAL 에 등재")


if __name__ == "__main__":
    main()
