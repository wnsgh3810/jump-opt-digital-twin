# -*- coding: utf-8 -*-
"""_G75_fitchk — 눈으로 찍은 대략 좌표를 **정밀화하고 즉시 검증 그림을 그린다** (마라톤G, 08-09).

왜 필요한가
  시드 판독은 trial 21건이다. 판독마다 ①격자 그림 ②확대 그림 ③fit 실행 ④검증 그림 =
  4왕복이면 84왕복이 된다. ③④를 합치고 ②를 생략해 2왕복으로 줄인다.

무엇을 하나
  대략 좌표 주변에서 `fs_vidscale.fit_roller` 를 여러 sector 로 돌려 **점수 최고**를 고르고,
  그 원(초록=금속판 30mm)과 40/30 배 원(빨강=고무 바깥)을 확대해서 그린다.
  ★ 초록이 금속판 가장자리에 물려야 정답이다. 빨강은 참고 (검은 매트와 대비가 없어 흐릿하다).

  sector 를 고정하지 않는 이유: 발이 프레임 아래 가장자리에 붙은 trial 은 원의 아래 호가
  화면 밖이라 표준 (95,290) 이 무너진다. trial 마다 다르므로 **점수로 고르게** 한다.

CLI: python _G75_fitchk.py <세션> <trial> <cx> <cy> [r_lo r_hi]
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                        # noqa: E402
import _G75_seedzoom as Z                                       # noqa: E402

SECTORS = [(95.0, 290.0), (120.0, 240.0), (140.0, 220.0), (0.0, 360.0)]


def fitchk(sess, trial, cx0, cy0, rlo=9.0, rhi=40.0, save=True):
    G, vm, f_sit, mp4 = Z.sit_frame(sess, trial)
    g = G.mean(axis=2) if G.ndim == 3 else G.astype(float)
    best = None
    for sec in SECTORS:
        sc, cx, cy, r = VS.fit_roller(g, cx0, cy0, sector=sec, rrange=(rlo, rhi, 0.1),
                                      d=2.0, win=8.0, step=0.5, refine=0.1)
        print(f"  sector{sec}  점수{sc:7.2f}  중심({cx:7.2f},{cy:8.2f})  r{r:5.2f}")
        if best is None or sc > best[0]:
            best = (sc, cx, cy, r, sec)
    sc, cx, cy, r, sec = best
    if not save:
        return best
    Wd, Zf = 120, 8
    H, W = g.shape
    x0 = int(np.clip(cx - Wd // 2, 0, max(0, W - Wd)))
    y0 = int(np.clip(cy - Wd // 2, 0, max(0, H - Wd)))
    crop = G[y0:y0 + Wd, x0:x0 + Wd]
    im = Image.fromarray(crop.astype("uint8")).convert("RGB")
    im = im.resize((im.width * Zf, im.height * Zf), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    for rr, col in ((r, (0, 255, 0)), (r * 40.0 / 30.0, (255, 80, 80))):
        dr.ellipse([(cx - rr - x0) * Zf, (cy - rr - y0) * Zf,
                    (cx + rr - x0) * Zf, (cy + rr - y0) * Zf], outline=col, width=3)
    dr.line([((cx - x0) * Zf, 0), ((cx - x0) * Zf, im.height)], fill=(0, 255, 0), width=1)
    dr.line([(0, (cy - y0) * Zf), (im.width, (cy - y0) * Zf)], fill=(0, 255, 0), width=1)
    try:
        ft = ImageFont.truetype("malgun.ttf", 26)
    except Exception:
        ft = ImageFont.load_default()
    dr.text((8, im.height - 38),
            f"{sess}/{trial} f{f_sit}  ({cx:.1f},{cy:.1f},r{r:.2f}) 점수{sc:.0f} sec{sec}"
            f"  자 {30.0 / (2 * r):.4f}mm/px",
            fill=(255, 255, 0), font=ft, stroke_width=3, stroke_fill=(0, 0, 0))
    out = HERE / "graphs" / "G72_seed" / f"_chk_{sess.replace('.', '_')}__{trial}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(f"채택 ({cx:.2f}, {cy:.2f}, {r:.2f})  점수{sc:.1f}  sector{sec}  "
          f"자 {30.0 / (2 * r):.4f}mm/px\n저장 {out}")
    return best


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit("사용: python _G75_fitchk.py <세션> <trial> <cx> <cy> [r_lo r_hi]")
    a = sys.argv
    fitchk(a[1], a[2], float(a[3]), float(a[4]),
           float(a[5]) if len(a) > 5 else 9.0, float(a[6]) if len(a) > 6 else 40.0)
