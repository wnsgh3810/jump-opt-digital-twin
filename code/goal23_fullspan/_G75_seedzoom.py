# -*- coding: utf-8 -*-
"""_G75_seedzoom — 세션 발 시드를 **확대해서 직접 읽기** (마라톤G, 08-09).

왜 수동인가
  자동 전역 탐색은 광학테이블 볼트머리·트러스구멍·브래킷 나사에 진다 (REJECTED #78 계열).
  반지름 사전으로 구속해도, 같은 720px 규격 안에서 발 지름이 26~32px 로 달라
  (카메라 거리 차이) 사전 범위가 하한 포화값 14.7 을 포함해 버린다.
  수동 시드는 등재한 2건(0723·0424) **둘 다 성공** — 확실하고 빠르다.
  단 **세션당 한 번으로는 부족하다**: 같은 세션 안에서도 trial 마다 로봇을 다시 놓아서,
  0602 의 120_2_120_2 시드로 150_2.2_250_3 를 돌리자 흰 브래킷 볼트에 락온했다.

사용
  python _G75_seedzoom.py <세션> <trial> [cx cy]   # cx,cy 없으면 하단 전체를 격자로 뽑는다
  python _G75_seedzoom.py <세션> <trial> cx cy [반경눈금...]   # 눈금 직접 지정
  → 발 롤러 중심과 **금속판 반지름**을 읽어 fs_slipmeas.SEED_CAL["<세션>/<trial>"] 에 등재.
  ★ 반지름까지 정확해야 한다 — 중심만 맞고 반지름이 틀리면 추적이 조용히 무너진다
    (0424 에서 r 20 vs 실제 33 으로 세 번 실패).
  ★ **trial 인자는 필수다** (08-09). 예전엔 세션만 받아 registry 첫 trial 을 썼는데,
    같은 세션 안에서도 로봇 설치 위치가 trial 마다 달라 다른 trial 에서 볼트에 락온했다.
    trial 을 빼먹으면 "읽은 그림"과 "등재할 trial" 이 어긋난다 — 그래서 생략을 막는다.

f_lo 캐시
  시드 판독은 trial 21건 × (zoom1 + zoom2) = 42회 실행인데, 매번 영상 전체를 읽어
  프레임차분(motion_profile)을 다시 계산하면 그것만으로 대부분의 시간이 간다.
  f_lo 는 영상만의 함수(결정적)이므로 mp4 이름으로 캐시해도 값이 달라지지 않는다.
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

OUT = HERE / "graphs" / "G72_seed"
CACHE = HERE / "_G75_flo_cache.json"
FRCACHE = OUT / "_frames"          # 스쿼트 바닥 프레임 캐시 (1단계↔2단계 재디코딩 방지)


def liftoff_cached(mp4, vm):
    """f_lo 를 mp4 이름으로 캐시. 영상만의 함수라 재계산해도 같은 값이다."""
    key = Path(mp4).name
    C = {}
    if CACHE.exists():
        try:
            C = json.load(io.open(CACHE, encoding="utf-8"))
        except Exception:
            C = {}
    if key in C:
        return int(C[key])
    prof = SM.motion_profile(mp4, k=vm["k"], ds=vm["ds"])
    f_lo, a, b = SM.liftoff_frame(prof)
    C[key] = int(f_lo)
    import safe
    safe.atomic_json_write(CACHE, C)
    return int(f_lo)


def _f(sz):
    try:
        return ImageFont.truetype("malgun.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def sit_frame(sess, trial):
    """대표 프레임(스쿼트 바닥)을 얻는다 — mp4·f_sit 별로 캐시한다.

    1단계(격자)와 2단계(확대)가 같은 프레임을 쓰는데 캐시가 없으면 같은 영상을 두 번
    디코딩한다. 4K 59fps 는 그것만으로 수십 초다.
    """
    import fs_data as FD
    import imageio.v3 as iio
    hit = [q for s, q, g, c, h in FD.registry() if s == sess and Path(q).name == trial]
    if not hit:
        cand = [Path(q).name for s, q, g, c, h in FD.registry() if s == sess]
        raise SystemExit(f"[중단] {sess}/{trial} 없음. 이 세션의 trial: {cand}")
    mp4 = [v for v in sorted(Path(hit[0]).glob("*.mp4"))
           if "online-video-cutter" not in v.name][0]
    vm = SM.video_meta(mp4); ds = vm["ds"]
    f_sit = max(4, liftoff_cached(mp4, vm) - max(6, int(round(0.6 * vm["fps"]))))
    FRCACHE.mkdir(parents=True, exist_ok=True)
    fc = FRCACHE / f"{Path(mp4).stem}_f{f_sit}_ds{ds}.npy"
    if fc.exists():
        return np.load(fc), vm, f_sit, mp4
    G = None
    for i, fr in enumerate(iio.imiter(mp4)):
        if i == f_sit:
            a = np.asarray(fr)
            G = (a[::ds, ::ds] if ds > 1 else a).astype("uint8")
            break
    if G is None:
        raise SystemExit(f"[중단] 프레임 {f_sit} 읽기 실패: {mp4}")
    np.save(fc, G)
    return G, vm, f_sit, mp4


def main():
    if len(sys.argv) < 3:
        raise SystemExit("사용: python _G75_seedzoom.py <세션> <trial> [cx cy]   ★trial 필수")
    sess, trial = sys.argv[1], sys.argv[2]
    ctr = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) >= 5 else None
    G, vm, f_sit, mp4 = sit_frame(sess, trial)
    ds = vm["ds"]
    H, W = G.shape[0], G.shape[1]
    tag = f"{sess.replace('.', '_')}__{trial}"
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
        dr.text((8, im.height - 40), f"{sess}/{trial}  f{f_sit}  ds={ds}  처리 {W}x{H}",
                fill=(255, 255, 0), font=_f(26), stroke_width=3, stroke_fill=(0, 0, 0))
        fn = OUT / f"_zoom1_{tag}.png"
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
        dr.text((8, Wd * Z - 34), f"{sess}/{trial} f{f_sit}  중심({cx:.0f},{cy:.0f})",
                fill=(255, 255, 0), font=_f(24), stroke_width=3, stroke_fill=(0, 0, 0))
        fn = OUT / f"_zoom2_{tag}.png"
    im.save(fn)
    print(f"저장 {fn}  · f_sit={f_sit} ds={ds} 처리 {W}x{H}  mp4={Path(mp4).name}")


if __name__ == "__main__":
    main()
