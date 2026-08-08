# -*- coding: utf-8 -*-
"""_G77_sheet — 세션의 발 시드를 **한 장으로 읽고 동시에 검증한다** (마라톤G, 08-09).

자동 탐색이 왜 계속 지는가 (6번째 실패로 확정)
  ① 반지름을 세션 확정값 ±25% 로 묶어도 진다. 진짜 경쟁자는 볼트가 아니라
     **종아리 링크(밝은 곡선 바)** 다 — 폭이 발과 비슷하고 대비는 훨씬 세다.
     위치창 45px 를 주자 6/6 전부 링크 가장자리로 끌려갔고 반지름은 하한에 포화했다.
  ② 그래서 **위치창은 좁게(±12px)** 유지한다. 좁은 창은 사람이 준 중심을 신뢰한다는 뜻이고,
     그게 지금까지 성공한 유일한 방식이다 (수동 3/3).

그럼 사람 손이 55번 필요한가 → 아니다. 이 시트가 그 왕복을 세션당 1~2회로 줄인다.
  - 각 칸은 **시드 주변 넓은 크롭 + 좌표격자**를 그린다 → 빗나갔으면 **그 자리에서 참값을 읽는다**.
  - 동시에 **좁은 창으로 맞춘 원**(초록=금속판30mm, 빨강=고무바깥40mm)을 겹쳐 그린다
    → 맞았으면 그냥 통과. 즉 "읽기"와 "검증"이 한 장에서 끝난다.
  - 읽은 참값은 `_G77_manual.json` 에 넣고 다시 돌리면 그 trial 만 갱신된다.

반지름은 세션 안에서 거의 상수다 (카메라 고정 · trial 간엔 **위치만** 변한다).
  그래서 rtol 을 좁게(0.10~0.12) 잡는 게 맞다. 넓으면 붉은 케이블에 가려진 위쪽 호 때문에
  **작은 반지름으로 주저앉는다** (0602 에서 22.3 이 정답인데 16.6·18.2 로 물린 사례).

CLI
  python _G77_sheet.py <세션> <cx> <cy> <r> [hw hh win rtol]
  # 개별 보정: _G77_manual.json 에 {"<세션>/<trial>": [cx, cy]} 또는 [cx, cy, r] 추가 후 재실행
결과: graphs/G72_seed/_sheet_<세션>.png · _G77_seeds.json (확정 시드 후보)
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                                     # noqa: E402
import _G77_footfit as FF                                       # noqa: E402
import _G75_seedzoom as Z                                       # noqa: E402

OUT = HERE / "graphs" / "G72_seed"
SEEDJSON = HERE / "_G77_seeds.json"
MANUAL = HERE / "_G77_manual.json"
SECTORS = [(95.0, 290.0), (120.0, 240.0), (140.0, 220.0), (60.0, 200.0), (0.0, 360.0)]


def _load(p):
    if Path(p).exists():
        try:
            return json.load(io.open(p, encoding="utf-8"))
        except Exception:
            pass
    return {}


def trials_of(sess):
    import fs_data as FD
    out = []
    for s, p, g, c, h in FD.registry():
        if s != sess:
            continue
        v = [q for q in sorted(Path(p).glob("*.mp4")) if "online-video-cutter" not in q.name]
        if v:
            out.append(Path(p).name)
    return out


def fit_one(g, cx0, cy0, r0, win=12.0, rtol=0.18):
    """`_G77_footfit` — 각도 중앙값 + 내부 게이트. 링크 가장자리·부분 가림을 배제한다."""
    sc, cx, cy, r, sec, inn, ok = FF.fit_foot(g, cx0, cy0, r0, win=win, rtol=rtol)
    return (sc, cx, cy, r, sec, inn, ok)


def cell(G, sx, sy, fit, label, hw, hh, zoom, grid=20):
    """시드 주변 크롭 + 좌표격자 + 맞춘 원."""
    H, W = G.shape[0], G.shape[1]
    x0 = int(np.clip(sx - hw, 0, max(0, W - 2 * hw))); x1 = min(W, x0 + 2 * hw)
    y0 = int(np.clip(sy - hh, 0, max(0, H - 2 * hh))); y1 = min(H, y0 + 2 * hh)
    sub = G[y0:y1, x0:x1]
    im = Image.fromarray(sub.astype("uint8")).convert("RGB")
    im = im.resize((sub.shape[1] * zoom, sub.shape[0] * zoom), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    try:
        fg = ImageFont.truetype("malgun.ttf", 15); fl = ImageFont.truetype("malgun.ttf", 22)
    except Exception:
        fg = fl = ImageFont.load_default()
    for x in range(x0 - x0 % grid + grid, x1, grid):
        dr.line([((x - x0) * zoom, 0), ((x - x0) * zoom, im.height)], fill=(0, 165, 165), width=1)
        dr.text(((x - x0) * zoom + 2, im.height - 20), str(x), fill=(0, 255, 255), font=fg,
                stroke_width=2, stroke_fill=(0, 0, 0))
    for y in range(y0 - y0 % grid + grid, y1, grid):
        dr.line([(0, (y - y0) * zoom), (im.width, (y - y0) * zoom)], fill=(0, 165, 165), width=1)
        dr.text((2, (y - y0) * zoom + 2), str(y), fill=(0, 255, 255), font=fg,
                stroke_width=2, stroke_fill=(0, 0, 0))
    sc, cx, cy, r, sec = fit[:5]
    for rr_, col in ((r, (0, 255, 0)), (r * 40.0 / 30.0, (255, 80, 80))):
        dr.ellipse([(cx - rr_ - x0) * zoom, (cy - rr_ - y0) * zoom,
                    (cx + rr_ - x0) * zoom, (cy + rr_ - y0) * zoom], outline=col, width=3)
    dr.rectangle([0, 0, im.width, 28], fill=(0, 0, 0))
    dr.text((5, 3), label, fill=(255, 255, 0), font=fl)
    return im


def main():
    if len(sys.argv) < 5:
        raise SystemExit("사용: python _G77_sheet.py <세션> <cx> <cy> <r> [hw hh win]")
    sess = sys.argv[1]
    ax, ay, ar = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    hw = int(sys.argv[5]) if len(sys.argv) > 5 else 70
    hh = int(sys.argv[6]) if len(sys.argv) > 6 else 60
    win = float(sys.argv[7]) if len(sys.argv) > 7 else 12.0
    rtol = float(sys.argv[8]) if len(sys.argv) > 8 else 0.12
    man = _load(MANUAL)
    ts = trials_of(sess)
    print(f"{sess}: trial {len(ts)}개 · 앵커({ax},{ay},r{ar}) hw{hw} hh{hh} win{win} rtol{rtol}")
    cells, rec = [], {}
    for t in ts:
        key = f"{sess}/{t}"
        mv = man.get(key)
        sx, sy = (mv[0], mv[1]) if mv else (ax, ay)
        sr = mv[2] if mv and len(mv) > 2 else ar        # 수동으로 반지름까지 준 경우
        G, vm, f_sit, mp4 = Z.sit_frame(sess, t)
        g = G.mean(axis=2) if G.ndim == 3 else G.astype(float)
        fit = fit_one(g, sx, sy, sr, win=win, rtol=rtol)
        sc, cx, cy, r, sec, inn, ok = fit
        mmpx = 30.0 / (2 * r)
        rec[key] = dict(cx=round(cx, 2), cy=round(cy, 2), r=round(r, 2), score=round(sc, 1),
                        sector=list(sec), mm_per_px=round(mmpx, 4), f_sit=int(f_sit),
                        ds=int(vm["ds"]), fps=round(vm["fps"], 2), manual=key in man,
                        inner=round(inn, 1), gate=bool(ok))
        m = "M" if key in man else " "
        print(f" {m}{t:22s} 시드({sx:6.0f},{sy:7.0f}) → ({cx:7.2f},{cy:8.2f}) r{r:5.2f} "
              f"점수{sc:6.1f} 내부{inn:6.1f} {'통과' if ok else '★탈락'} 자{mmpx:.4f}")
        z = max(2, int(round(760 / (2 * hw))))
        cells.append(cell(G, sx, sy, fit,
                          f"{t}  r{r:.1f} 점{sc:.0f} 내{inn:.0f}"
                          f"{'' if ok else ' ★탈락'}{'  [수동]' if m == 'M' else ''}",
                          hw, hh, z))
    if not cells:
        raise SystemExit("대상 없음")
    ncol = 3 if len(cells) > 4 else 2
    nrow = (len(cells) + ncol - 1) // ncol
    cw, ch = max(c.width for c in cells), max(c.height for c in cells)
    sheet = Image.new("RGB", (ncol * cw, nrow * ch + 42), (18, 18, 18))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % ncol) * cw, (i // ncol) * ch + 42))
    dr = ImageDraw.Draw(sheet)
    try:
        ft = ImageFont.truetype("malgun.ttf", 30)
    except Exception:
        ft = ImageFont.load_default()
    dr.text((8, 6), f"{sess}  발 시드 (초록=금속판30 · 빨강=고무바깥40 · 숫자=원본좌표)",
            fill=(255, 255, 0), font=ft)
    OUT.mkdir(parents=True, exist_ok=True)
    fn = OUT / f"_sheet_{sess.replace('.', '_')}.png"
    sheet.save(fn)
    allrec = _load(SEEDJSON); allrec.update(rec); safe.atomic_json_write(SEEDJSON, allrec)
    rs = [v["r"] for v in rec.values()]
    print(f"\n저장 {fn}\n반지름 {min(rs):.2f}~{max(rs):.2f} (중앙 {np.median(rs):.2f}) "
          f"· 퍼짐 {(max(rs) - min(rs)) / np.median(rs) * 100:.1f}%")


if __name__ == "__main__":
    main()
