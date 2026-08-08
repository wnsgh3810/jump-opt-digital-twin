# -*- coding: utf-8 -*-
"""_G81_zoomproof — 세션 전체의 추적을 **한 장으로** 눈검사 (마라톤G, 08-09).

왜
  `_G72_proof.py` 는 trial 당 한 장(4컷 풀프레임)이라 55 trial 이면 55장을 봐야 한다.
  실제로 봐야 하는 건 **초록 원이 롤러에 물렸는가** 하나뿐이므로, 원 주변만 잘라
  세션 단위로 붙이면 한 장에서 전부 판정된다.

무엇을 그리나
  trial 한 줄 = 4컷 (하강시작 · 스쿼트바닥 · 푸시 · 마지막접지).
  각 컷은 **파이프라인이 실제로 쓴 중심·반지름**으로 잘라 그린다 (독립 재맞춤 금지 —
  재맞춤을 그렸다가 정상 trial 을 불량으로 보이게 만든 전례가 있다).
  컷마다 누적 Δx [mm] 를 적어 둔다 — 원이 맞아도 값이 튀면 거기서 보인다.

CLI: python _G81_zoomproof.py <세션>            # 없으면 전 세션
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))

OUT = HERE / "graphs" / "G81_zoomproof"
JSON = HERE / "_G72_slipall.json"
HALF = 60          # 크롭 반폭 (기준 720p px — 해상도에 비례 확대)
Z = 3


def _f(sz):
    try:
        return ImageFont.truetype("malgun.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def trial_row(rec):
    """한 trial → 4컷 가로 이미지."""
    import imageio.v3 as iio
    import fs_data as FD
    hit = [q for s, q, g, c, h in FD.registry()
           if s == rec["sess"] and q.name == rec["trial"]]
    if not hit:
        return None
    mp4 = [v for v in sorted(Path(hit[0]).glob("*.mp4"))
           if "online-video-cutter" not in v.name][0]
    s = rec["series"]
    fs = [int(x) for x in s["f"]]
    n = len(fs)
    pick = sorted({0, n // 2, max(0, int(n * 0.93)), n - 1})     # 하강·바닥·푸시·마지막
    want = {fs[i]: i for i in pick}
    ds = int(rec.get("px_ds", 1)); k = float(rec.get("px_k", 1.0))
    hw = int(HALF * k)
    got = {}
    for i, fr in enumerate(iio.imiter(mp4)):
        if i in want:
            a = np.asarray(fr)
            got[i] = (a[::ds, ::ds] if ds > 1 else a).astype("uint8")
        if i > max(want):
            break
    cells = []
    for fnum in sorted(want):
        j = want[fnum]
        G = got.get(fnum)
        if G is None:
            continue
        cx, cy, r = s["cx"][j], s["cy"][j], s["r"][j]
        H, W = G.shape[0], G.shape[1]
        x0 = int(np.clip(cx - hw, 0, max(0, W - 2 * hw)))
        y0 = int(np.clip(cy - hw, 0, max(0, H - 2 * hw)))
        sub = G[y0:y0 + 2 * hw, x0:x0 + 2 * hw]
        im = Image.fromarray(sub).convert("RGB")
        im = im.resize((im.width * Z, im.height * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        dr.ellipse([(cx - r - x0) * Z, (cy - r - y0) * Z,
                    (cx + r - x0) * Z, (cy + r - y0) * Z], outline=(0, 255, 0), width=3)
        dr.line([((cx - x0) * Z, (cy - y0 - 6) * Z), ((cx - x0) * Z, (cy - y0 + 6) * Z)],
                fill=(0, 255, 255), width=2)
        dr.line([((cx - x0 - 6) * Z, (cy - y0) * Z), ((cx - x0 + 6) * Z, (cy - y0) * Z)],
                fill=(0, 255, 255), width=2)
        dr.rectangle([0, im.height - 24, im.width, im.height], fill=(0, 0, 0))
        dr.text((4, im.height - 22), f"f{fnum}  Δx {s['x'][j]:+.1f}mm  점{s['sc'][j]:.0f}",
                fill=(255, 255, 0), font=_f(16))
        cells.append(im)
    if not cells:
        return None
    w, h = cells[0].width, cells[0].height
    row = Image.new("RGB", (len(cells) * w + 300, h), (16, 16, 16))
    for i, c in enumerate(cells):
        row.paste(c, (300 + i * w, 0))
    dr = ImageDraw.Draw(row)
    g = rec["seg"]
    qc = rec.get("qc", [])
    dr.text((6, 6), rec["trial"], fill=(255, 255, 0), font=_f(22))
    dr.text((6, 34), f"자 {rec['scale']:.4f} mm/px", fill=(190, 190, 190), font=_f(17))
    dr.text((6, 58), f"하강 {g['하강전반']['slip']+g['하강후반']['slip']:+.1f}",
            fill=(210, 210, 210), font=_f(17))
    dr.text((6, 80), f"바닥 {g['바닥유지']['slip']:+.1f}", fill=(210, 210, 210), font=_f(17))
    dr.text((6, 102), f"푸시 {g['푸시~이륙']['slip']:+.1f}", fill=(255, 255, 255), font=_f(20))
    dr.text((6, 128), f"전체 {g['전체']['slip']:+.1f}", fill=(210, 210, 210), font=_f(17))
    if qc:
        dr.text((6, 154), f"QC {len(qc)}", fill=(255, 170, 0), font=_f(17))
        for i, q in enumerate(qc[:3]):
            dr.text((6, 176 + i * 18), q[:34], fill=(255, 170, 0), font=_f(13))
    return row


def main():
    import fs_data as FD                                        # noqa: F401
    OUT.mkdir(parents=True, exist_ok=True)
    d = json.load(io.open(JSON, encoding="utf-8"))
    sess = sys.argv[1] if len(sys.argv) > 1 else None
    by = {}
    for k, v in sorted(d.items()):
        if not (v.get("ok") and "cy" in (v.get("series") or {})):
            continue
        if sess and v["sess"] != sess:
            continue
        by.setdefault(v["sess"], []).append(v)
    for s, recs in by.items():
        rows = []
        for r in recs:
            try:
                row = trial_row(r)
            except Exception as ex:
                print(f"  ✗ {s}/{r['trial']}: {type(ex).__name__} {str(ex)[:50]}"); continue
            if row is not None:
                rows.append(row)
                print(f"  ✔ {s}/{r['trial']}")
        if not rows:
            continue
        w = max(x.width for x in rows); h = sum(x.height for x in rows)
        sheet = Image.new("RGB", (w, h + 40), (16, 16, 16))
        y = 40
        for x in rows:
            sheet.paste(x, (0, y)); y += x.height
        dr = ImageDraw.Draw(sheet)
        dr.text((8, 6), f"{s}  추적 검증 (초록=맞춘 원 · 4컷: 하강시작/바닥/푸시/마지막접지)",
                fill=(255, 255, 0), font=_f(26))
        fn = OUT / f"{s.replace('.', '_')}.png"
        sheet.save(fn)
        print(f"저장 {fn}  ({len(rows)} trial)")


if __name__ == "__main__":
    main()
