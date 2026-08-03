# -*- coding: utf-8 -*-
"""_E_railshake_video — 점프 영상에서 레일(수직 가이드) 횡 흔들림 정량화.

목적: 측정토크→반력 분석의 수직이탈각 φ 큰 날(26.07.23/24) vs 작은 날(22/25/27)이
      영상의 레일 횡 진동 진폭 순서와 일치하는지 독립 확증.

방법 (방법 A 변형, 1D 서브픽셀 상관):
- ROI(레일 상단 밴드): y∈[2%,16%]·x∈[35%,97%] — 전 날짜에서 레일 기둥/apex 플레이트/
  스트럿만 포함. 왼쪽 눈금자(걸이형 차트, 독립 흔들림 가능)와 로봇 가동범위
  (흰색 리미트 스톱 ~50cm 위로 캐리지 못 올라감) 배제. 근거 이미지: 스크래치 roi_*.png.
- 각 프레임 ROI의 열평균 휘도 프로파일 → gradient(에지 강조) → 기준(점프 직전 중앙값)
  프로파일과 ±20px NCC + 포물선 보간 → 수평 시프트 u_rail(t) [px].
- 카메라 흔들림 보정: 우하단 정적 클러터 ROI(y 86~99%, x 65~99%)의 동일 시프트
  u_cam(t)를 차감. rel(t) = u_rail − u_cam.
- 점프 온셋 j: 다운샘플 프레임 차분 에너지 top-10 클러스터의 최소 인덱스
  (fs_video_desc 패턴). 창 = [j, j+2.5s] (푸시~착지 링잉).
- 지표 shake_px = p95(|highpass(rel)|) (highpass = 0.5s 이동평균 차감), 720px 폭 기준
  정규화(×720/W; 22일만 1080p). baseline(점프 전 동일 지표)과 cam p95도 기록.
- 이륙 충격 분리: shake_push_px = 동일 지표를 [j, j+0.45s] 창(푸시+초기 비행, 착지 전)만.
- 줌 보정: 상단 밴드 전폭 열평균의 최암부 2개 = 레일 기둥 → 간격 px 측정(물리 고정)
  → shake_norm = shake_px × (260 / spacing_720): 날짜 간 카메라 거리 차 보정.

산출: _E_railshake.json (이 폴더). 원본 데이터 무수정.
CLI: python _E_railshake_video.py
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import json
from pathlib import Path
import numpy as np
import imageio.v3 as iio

HERE = Path(__file__).parent
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/"
           r"C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/"
           r"fcd547c7-41bc-4112-9159-2d1f317a3cc9/scratchpad")
DAYS = ["26.07.22", "26.07.23", "26.07.24", "26.07.25", "26.07.27"]

ROI_RAIL = (0.02, 0.16, 0.35, 0.97)   # y0,y1,x0,x1 (비율)
ROI_CAM = (0.86, 0.99, 0.65, 0.99)
MAXLAG = 20
WIN_POST_S = 2.5      # 점프 온셋 후 분석 창
HP_S = 0.5            # 하이패스(이동평균 차감) 창


def gray(a):
    return a.mean(axis=2).astype(np.float32)


def prof(g, roi):
    H, W = g.shape
    y0, y1, x0, x1 = (int(roi[0] * H), int(roi[1] * H), int(roi[2] * W), int(roi[3] * W))
    p = g[y0:y1, x0:x1].mean(axis=0)
    return np.gradient(p)                     # 에지 강조 + 저주파 조명 제거


def xshift(p, R, m=MAXLAG):
    """p가 R 대비 몇 px 수평 이동했는지 (서브픽셀). return (shift, peak_ncc)."""
    a = p[m:-m] - p[m:-m].mean()
    na = np.sqrt((a * a).sum()) + 1e-9
    sc = np.empty(2 * m + 1)
    for k in range(-m, m + 1):
        b = R[m + k:len(R) - m + k]
        b = b - b.mean()
        sc[k + m] = float((a * b).sum() / (na * (np.sqrt((b * b).sum()) + 1e-9)))
    i = int(np.argmax(sc))
    d = 0.0
    if 0 < i < 2 * m:
        den = sc[i - 1] - 2 * sc[i] + sc[i + 1]
        if abs(den) > 1e-12:
            d = 0.5 * (sc[i - 1] - sc[i + 1]) / den
            d = float(np.clip(d, -1, 1))
    return -(i - m + d), float(sc[i])         # p(x)=R(x-s) → 최적 k=-s


def rail_spacing_px(g):
    """상단 밴드 전폭 열평균에서 최암부(검은 레일 기둥) 2개 간격 [px]."""
    H, W = g.shape
    band = g[int(0.02 * H):int(0.16 * H), :].mean(axis=0)
    band = np.convolve(band, np.ones(7) / 7, mode="same")
    v = band.max() - band
    i1 = int(np.argmax(v))
    v2 = v.copy()
    v2[max(0, i1 - int(0.08 * W)):i1 + int(0.08 * W)] = 0
    i2 = int(np.argmax(v2))
    return abs(i2 - i1)


def highpass(u, w):
    w = max(3, int(w) | 1)
    pad = np.pad(u, w // 2, mode="reflect")
    ma = np.convolve(pad, np.ones(w) / w, mode="valid")
    return u - ma


def save_roi_png(rgb, path):
    im = rgb.copy()
    H, W = im.shape[:2]
    for roi, val in ((ROI_RAIL, (255, 60, 60)), (ROI_CAM, (60, 255, 60))):
        y0, y1, x0, x1 = int(roi[0] * H), int(roi[1] * H), int(roi[2] * W), int(roi[3] * W)
        t = 4
        im[y0:y0 + t, x0:x1] = val; im[y1 - t:y1, x0:x1] = val
        im[y0:y1, x0:x0 + t] = val; im[y0:y1, x1 - t:x1] = val
    iio.imwrite(str(path), im)


OUT = {}
for day in DAYS:
    saved_roi = False
    for fold in sorted((ROOT / day).iterdir()):
        if not fold.is_dir():
            continue
        mp4s = sorted(fold.glob("*.mp4"))
        if not mp4s:
            continue
        try:
            fps = float(iio.immeta(str(mp4s[0]), plugin="FFMPEG").get("fps", 24.0))
            pr_rail, pr_cam, dd = [], [], []
            prev_small = None
            W = H = 0
            first_rgb = None
            spacing = 0
            for i, f in enumerate(iio.imiter(str(mp4s[0]), plugin="FFMPEG")):
                if i == 0:
                    first_rgb = f.copy()
                g = gray(f)
                H, W = g.shape
                if i == 0:
                    spacing = rail_spacing_px(g)
                small = g[::6, ::6]
                if prev_small is not None:
                    dd.append(float(np.abs(small - prev_small).mean()))
                prev_small = small
                pr_rail.append(prof(g, ROI_RAIL))
                pr_cam.append(prof(g, ROI_CAM))
        except Exception as ex:
            print(f"{day}/{fold.name}: 영상 실패 {type(ex).__name__} {ex}", flush=True)
            continue
        n = len(pr_rail)
        if n < 30:
            print(f"{day}/{fold.name}: 프레임 부족 ({n})", flush=True)
            continue
        if not saved_roi:
            save_roi_png(first_rgb, SCR / f"roi_{day.replace('.', '')}.png")
            saved_roi = True
        dd = np.asarray(dd)
        j = int(min(np.argsort(dd)[-10:]))                       # 점프 온셋 프레임
        i0, i1 = j, min(n, j + int(WIN_POST_S * fps) + 1)        # 분석 창
        b0, b1 = max(0, j - int(1.5 * fps)), max(1, j - int(0.4 * fps))  # 베이스라인 창
        if b1 - b0 < 3:
            b0, b1 = 0, min(6, n)
        R_rail = np.median(np.stack(pr_rail[b0:b1]), axis=0)
        R_cam = np.median(np.stack(pr_cam[b0:b1]), axis=0)
        u_rail = np.empty(n); u_cam = np.empty(n); q = np.empty(n)
        for i in range(n):
            u_rail[i], q[i] = xshift(pr_rail[i], R_rail)
            u_cam[i], _ = xshift(pr_cam[i], R_cam)
        rel = highpass(u_rail - u_cam, HP_S * fps)
        raw = highpass(u_rail, HP_S * fps)
        cam = highpass(u_cam, HP_S * fps)
        sc = 720.0 / W                                           # 해상도 정규화
        sp720 = spacing * sc                                     # 레일 간격 (px@720w)
        zn = 260.0 / sp720 if sp720 > 50 else 1.0                # 줌(거리) 정규화 계수
        ip = min(n, j + int(0.45 * fps) + 1)                     # 푸시+초기비행 창 (착지 전)
        seg = rel[i0:i1]; segb = rel[b0:b1]
        shake = float(np.percentile(np.abs(seg), 95)) * sc
        push = float(np.percentile(np.abs(rel[i0:ip]), 95)) * sc
        res = dict(
            shake_px=round(shake, 3),
            shake_norm=round(shake * zn, 3),
            shake_push_px=round(push, 3),
            shake_push_norm=round(push * zn, 3),
            shake_std_px=round(float(seg.std()) * sc, 3),
            shake_raw_px=round(float(np.percentile(np.abs(raw[i0:i1]), 95)) * sc, 3),
            baseline_px=round(float(np.percentile(np.abs(segb), 95)) * sc, 3),
            cam_px=round(float(np.percentile(np.abs(cam[i0:i1]), 95)) * sc, 3),
            rail_spacing_px720=round(sp720, 1),
            ncc_min=round(float(q[i0:i1].min()), 3),
            jump_frame=j, fps=fps, width=W, n_frames=n,
            method="railband-x-NCC-subpx(cam-comp, p95 |hp 0.5s|, norm720w, zoom=260/spacing)",
        )
        OUT[f"{day}/{fold.name}"] = res
        print(f"{day}/{fold.name}: shake {res['shake_px']:.2f}px norm {res['shake_norm']:.2f} "
              f"push {res['shake_push_norm']:.2f} (raw {res['shake_raw_px']:.2f}, "
              f"base {res['baseline_px']:.2f}, cam {res['cam_px']:.2f}) sp {sp720:.0f}px "
              f"j={j} n={n} ncc_min {res['ncc_min']:.2f}", flush=True)

jp = HERE / "_E_railshake.json"
json.dump(OUT, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved →", jp, flush=True)

# 날짜별 요약
for key in ("shake_px", "shake_norm", "shake_push_norm"):
    print(f"\n== 날짜별 {key} 중앙값 ==", flush=True)
    for day in DAYS:
        v = [r[key] for k, r in OUT.items() if k.startswith(day)]
        if v:
            print(f"{day}: median {np.median(v):.2f} (n={len(v)}, "
                  f"range {min(v):.2f}~{max(v):.2f})", flush=True)

print("\n== 게인 매칭 (150_2.2_250_3, 전 날짜 공통) ==", flush=True)
for day in DAYS:
    k = f"{day}/150_2.2_250_3"
    if k in OUT:
        r = OUT[k]
        print(f"{day}: shake_norm {r['shake_norm']:.2f} push_norm {r['shake_push_norm']:.2f}",
              flush=True)
