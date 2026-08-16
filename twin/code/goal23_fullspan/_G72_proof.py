# -*- coding: utf-8 -*-
"""_G72_proof — 슬립 판정의 **육안 검증 시트** (마라톤G, 08-08).

왜 필요한가
  이번 마라톤에서 자동 측정이 **다섯 번** 틀렸고, 다섯 번 다 **그림으로 봤을 때** 잡혔다:
  링크를 발로 착각 · 안쪽 금속판을 바깥 지름으로 착각 · 푸시에서 발 놓침 ·
  볼트 구멍 락온 · 역방향 미적용으로 하강 추적 붕괴.
  숫자만 보면 전부 그럴듯했다. **QC 플래그가 없어도 눈으로 한 번은 본다.**

무엇을 그리나 (trial 당 한 줄, 4컷)
  하강 시작 · 스쿼트 바닥 · 푸시 중간 · 마지막 접지 — 각 컷에 맞춘 원과 중심,
  그리고 그 시점의 누적 Δx [mm]. 원이 롤러에 안 물려 있으면 그 trial 은 버린다.

CLI: python _G72_proof.py [세션 trial]      # 없으면 _G72_slipall.json 전부
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                       # noqa: E402
import fs_slipmeas as SM                                       # noqa: E402

OUTDIR = HERE / "graphs" / "G72_proof"
DATA = Path(DATA_ROOT)


def _font(sz):
    try:
        return ImageFont.truetype("malgun.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def sheet(rec, mp4, *, tile=300):
    """한 trial 의 4컷 검증 이미지."""
    import imageio.v3 as iio
    ds = rec.get("px_ds", 1)
    f = np.array(rec["series"]["f"], int); x = np.array(rec["series"]["x"])
    n = len(f)
    picks = [0, int(n * 0.60), max(0, n - 4), n - 1]
    want = {int(f[i]) for i in picks}
    # 그 프레임들의 추적 결과가 필요 — series 에 cx,cy 가 없으면 재맞춤
    F = {}
    for i, fr in enumerate(iio.imiter(Path(mp4))):
        if i in want:
            g = np.asarray(fr)[..., :3].mean(axis=2)
            F[i] = (g[::ds, ::ds] if ds > 1 else g)
        if i > max(want):
            break
    k = rec.get("px_k", 1.0)
    tiles = []
    f1, f2 = _font(int(15)), _font(int(19))
    for j in picks:
        fr = int(f[j])
        if fr not in F:
            continue
        g = F[fr]
        # ★ **파이프라인이 실제로 쓴 값**을 그린다 (독립 재맞춤 금지).
        #   처음엔 여기서 다시 맞췄더니 넓은 창이 종아리 끝(r=9px)에 락온해,
        #   정상 추적된 trial 을 불량으로 보이게 만들었다 (08-08).
        cx, cy = rec["series"]["cx"][j], rec["series"]["cy"][j]
        r, sc = rec["series"]["r"][j], rec["series"]["sc"][j]
        half = int(tile / 2)
        x0 = int(np.clip(cx - half, 0, g.shape[1] - tile))
        y0 = int(np.clip(cy - half, 0, g.shape[0] - tile))
        crop = np.clip(g[y0:y0 + tile, x0:x0 + tile], 0, 255).astype(np.uint8)
        im = Image.fromarray(crop).convert("RGB").resize((tile * 2, tile * 2), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        X = lambda p: (p - x0) * 2; Y = lambda p: (p - y0) * 2
        dr.ellipse([X(cx - r), Y(cy - r), X(cx + r), Y(cy + r)], outline=(80, 255, 80), width=4)
        dr.line([(X(cx) - 12, Y(cy)), (X(cx) + 12, Y(cy))], fill=(0, 255, 255), width=3)
        dr.line([(X(cx), Y(cy) - 12), (X(cx), Y(cy) + 12)], fill=(0, 255, 255), width=3)
        dr.text((6, 4), f"f{fr}  t={fr/rec['fps']:.2f}s", fill=(255, 255, 0), font=f2,
                stroke_width=3, stroke_fill=(0, 0, 0))
        dr.text((6, tile * 2 - 46), f"dx {x[j]:+.1f} mm", fill=(120, 255, 120), font=f2,
                stroke_width=3, stroke_fill=(0, 0, 0))
        dr.text((6, tile * 2 - 24), f"r {r:.1f}px  score {sc:.0f}", fill=(200, 200, 200), font=f1,
                stroke_width=2, stroke_fill=(0, 0, 0))
        tiles.append(im)
    if not tiles:
        return None
    W, H = tiles[0].size
    hdr = 42
    img = Image.new("RGB", (W * len(tiles) + 6 * len(tiles), H + hdr), (18, 18, 18))
    for i, t in enumerate(tiles):
        img.paste(t, (i * (W + 6), hdr))
    dr = ImageDraw.Draw(img)
    g = rec["seg"]
    head = (f"{rec['sess']}/{rec['trial']}   {rec['fps']:.0f}fps {rec['vid_w']}x{rec['vid_h']}"
            f"  ·  자 {rec['scale']:.4f} mm/px (지름 {rec['dia_px']:.1f}px)"
            f"  ·  슬립: 하강 {g['하강전반']['slip']+g['하강후반']['slip']:+.1f} / "
            f"푸시 {g['푸시~이륙']['slip']:+.1f} / 전체 {g['전체']['slip']:+.1f} mm")
    dr.text((8, 10), head, fill=(255, 255, 0), font=_font(23), stroke_width=2, stroke_fill=(0, 0, 0))
    if rec.get("qc"):
        dr.text((8, H + hdr - 26), "⚠ " + " / ".join(rec["qc"]), fill=(255, 150, 80),
                font=_font(19), stroke_width=3, stroke_fill=(0, 0, 0))
    return img


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ALL = json.load(io.open(SM.OUT_JSON, encoding="utf-8"))
    keys = ([f"{sys.argv[1]}/{sys.argv[2]}"] if len(sys.argv) >= 3
            else [k for k, v in ALL.items() if v.get("ok")])
    made = []
    for kk in keys:
        rec = ALL.get(kk)
        if not rec or not rec.get("ok"):
            print(f"  건너뜀 {kk}"); continue
        d = DATA / rec["sess"].replace(".", "_")
        cand = list(d.rglob(rec["mp4"]))
        if not cand:
            print(f"  mp4 못찾음 {kk}"); continue
        img = sheet(rec, cand[0])
        if img is None:
            print(f"  시트 실패 {kk}"); continue
        fn = OUTDIR / (kk.replace("/", "__").replace(".", "_") + ".png")
        img.save(fn); made.append(fn)
        print(f"  ✔ {fn.name}")
    print(f"\n{len(made)}장 저장 → {OUTDIR}")


if __name__ == "__main__":
    main()
