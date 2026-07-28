# -*- coding: utf-8 -*-
"""video_slip_alldays — 전 배포일(07-22~25) 발끝 슬립 영상 전수 측정 (사용자: 날짜별로 크게 다름).

exp5에서 확립한 파이프라인 확장: 점프클러스터 탐지 → 발볼트 코스 위치(exp5-250 템플릿, 광역)
→ 자기 템플릿 정밀 추적(j−6..j+1, 오차<1300, 중위수 이상치 제거) → 패드 고정 검증
→ 구름 차감(그 trial 인코더 정강이 회전) → 진짜 슬립 범위. 감사용 마킹 스트립 저장.
사용법: python video_slip_alldays.py <day: 26.07.22|23|24|25>
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd
import imageio.v3 as iio

HERE = Path(__file__).parent
ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
DAY = sys.argv[1] if len(sys.argv) > 1 else "26.07.23"
SCALE = (0.7, 1.2); R_FOOT = (20.0, 25.0)

def gray(a): return a.mean(axis=2)
def match(f, T, cy, cx, ry, rx):
    h = T.shape[0]//2; best = (1e18, 0, 0)
    for dy in range(-ry, ry+1, 1):
        for dx in range(-rx, rx+1, 1):
            p = f[cy+dy-h:cy+dy+h, cx+dx-h:cx+dx+h]
            if p.shape != T.shape: continue
            s = float(((p-T)**2).mean())
            if s < best[0]: best = (s, dx, dy)
    return best

# 기준 템플릿 (exp5 250 — 검증 완료 좌표)
mp250 = next((ROOT/"26.07.27"/"250_3_250_3").glob("*.mp4"))
fr250 = [gray(f) for f in iio.imiter(str(mp250), plugin="FFMPEG")]
d250 = [float(np.abs(fr250[i+1]-fr250[i]).mean()) for i in range(len(fr250)-1)]
j250 = int(min(np.argsort(d250)[-12:]))
TY, TX = 1183, 368
T_REF = fr250[j250-5][TY-18:TY+18, TX-18:TX+18].copy()
del fr250

OUT = {}
for fold in sorted([p for p in (ROOT/DAY).iterdir() if p.is_dir() and (p/"hip.xlsx").exists()]):
    mp4s = list(fold.glob("*.mp4"))
    if not mp4s:
        print(f"{fold.name}: 영상 없음"); continue
    try:
        fr = [gray(f) for f in iio.imiter(str(mp4s[0]), plugin="FFMPEG")]
    except Exception as ex:
        print(f"{fold.name}: 영상 읽기 실패 {ex}"); continue
    d = [float(np.abs(fr[i+1]-fr[i]).mean()) for i in range(len(fr)-1)]
    j = int(min(np.argsort(d)[-12:]))
    if j < 8:
        print(f"{fold.name}: 점프 탐지 이상 (j={j})"); continue
    # 코스: 광역 탐색 (프레이밍이 날마다 다를 수 있음)
    e0, dx0, dy0 = match(fr[j-5], T_REF, TY, TX, ry=90, rx=140)
    cy, cx = TY+dy0, TX+dx0
    T_own = fr[j-6][cy-18:cy+18, cx-18:cx+18].copy()
    track = []
    for i in range(j-6, min(j+2, len(fr))):
        e, dx, dy = match(fr[i], T_own, cy, cx, ry=35, rx=55)
        track.append((i, e, dx, dy))
    good = [x for x in track if x[1] <= 1300]
    dxs0 = [x[2] for x in good]
    dxs = [dd for k, dd in enumerate(dxs0) if abs(dd - np.median(dxs0[max(0,k-1):k+2])) <= 25]
    if len(dxs) < 3:
        print(f"{fold.name}: 추적 실패 (good {len(good)}) — 감사 프레임 저장")
        crop = fr[j-5][max(0,cy-120):cy+120, max(0,cx-180):cx+180]
        iio.imwrite(HERE/f"audit_{DAY}_{fold.name}.png", np.stack([crop]*3, -1).astype(np.uint8))
        OUT[fold.name] = dict(fail=True, coarse_err=round(e0)); continue
    disp_px = max(abs(dxs[-1]-dxs[0]), max(abs(dd-dxs[0]) for dd in dxs))
    # 구름: 그 trial 인코더 정강이 회전 (onset→GRF 이륙)
    try:
        hip = pd.read_excel(fold/"hip.xlsx"); knee = pd.read_excel(fold/"knee.xlsx"); grf = pd.read_excel(fold/"GRF.xlsx")
        n = min(len(hip), len(knee), len(grf))
        t = hip["Time"].to_numpy(float)[:n]; t -= t[0]
        q1 = hip["currentAngle"].to_numpy(float)[:n]; q2 = knee["currentAngle"].to_numpy(float)[:n]
        if np.nanmax(np.abs(q2)) > 7: q1, q2 = np.radians(q1), np.radians(q2)
        sh = q1 + q2
        qd2 = knee["desiredAngle"].to_numpy(float)[:n]
        on = np.where(np.abs(qd2-qd2[0]) > (0.5 if np.nanmax(np.abs(qd2)) > 7 else np.radians(0.5)))[0]
        i0 = int(on[0]) if len(on) else 0
        g = grf["Current_GRF"].to_numpy(float)[:n]; g0 = np.median(g[-5:]); thr = g0+0.06*(np.nanmax(g)-g0)
        ab = np.where(g >= thr)[0]; i1 = min(int(ab[-1])+1, n-1) if len(ab) else n-1
        dth = abs(float(sh[i1]-sh[i0]))
    except Exception:
        dth = 0.5
    disp_mm = (disp_px*SCALE[0], disp_px*SCALE[1])
    roll = (R_FOOT[0]*dth*0.8, R_FOOT[1]*dth)
    true_lo = max(0.0, disp_mm[0]-roll[1]); true_hi = max(0.0, disp_mm[1]-roll[0])
    OUT[fold.name] = dict(disp_px=float(disp_px), disp_mm=[round(x,1) for x in disp_mm],
                          shank_deg=round(np.degrees(dth),1), roll_mm=[round(x,1) for x in roll],
                          true_mm=[round(true_lo,1), round(true_hi,1)],
                          dxs=dxs, coarse_err=round(e0), n_track=len(dxs))
    print(f"{fold.name}: dx={dxs} → 이동 {disp_px:.0f}px={disp_mm[0]:.0f}~{disp_mm[1]:.0f}mm | "
          f"구름 {roll[0]:.0f}~{roll[1]:.0f} | 진짜슬립 {true_lo:.0f}~{true_hi:.0f}mm (코스오차 {e0:.0f})", flush=True)
    del fr

jp = HERE/("_video_slip_" + DAY.replace(".", "").replace("/", "_") + ".json")
json.dump(OUT, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done →", jp)
