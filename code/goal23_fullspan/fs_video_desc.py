# -*- coding: utf-8 -*-
"""fs_video_desc — 준정적 하강 창 영상 비틀림 감사 (Day1 #4 정도판).

교훈(fs_video_gauge): 푸시 말기는 ±0.5프레임=±5~10° 앨리어싱 → 24fps로 판별 불가.
정도 = 하강(deep squat) 창: 속도 ~0.2rad/s → 프레임당 <0.5°, 수십 프레임 표본.
측정: defl(t) = (θ_enc+C0) − θ_vid vs pred(t) = fs 2단 스프링 τ1→처짐.
  회귀 defl = α·pred + β → α = k_fs/k_eff (세션 유효강성 비). α>1 = 실기가 모델보다 유연.
  22/25 킥 날 α 이상 여부 = 잔존 게이지 +3.6~4.4°의 '구조 유연성' 가설 판별.
C0(오프셋)은 바닥(prehold 직전 3표본)에서 캘리브 — pred도 같은 기준점 차감.
정렬: 이륙 앵커 (발 템플릿 파탄 ↔ segment t_lo). 하강은 저속이라 ±2프레임 오차 ≈ 1° 미만.
추적: 바닥 프레임에서 코스 탐색(27일 250 템플릿, ±90/±140) → 자기 템플릿 → 시간 역방향
      워크 (중심 갱신, ±25 탐색, stride 4프레임).
CLI: python fs_video_desc.py <day>
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import imageio.v3 as iio

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD                     # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
DAY = sys.argv[1] if len(sys.argv) > 1 else "26.07.27"
PTS0 = {"knee": (1065, 610), "foot": (1183, 368)}


def gray(a):
    return a.mean(axis=2).astype(np.float32)


def match(f, T, cy, cx, ry=25, rx=25):
    h = T.shape[0] // 2
    best = (1e18, 0, 0)
    for dy in range(-ry, ry + 1):
        for dx in range(-rx, rx + 1):
            p = f[cy + dy - h:cy + dy + h, cx + dx - h:cx + dx + h]
            if p.shape != T.shape:
                continue
            s = float(((p - T) ** 2).mean())
            if s < best[0]:
                best = (s, dx, dy)
    return best


def defl_pred_deg(tau):
    a = np.abs(tau)
    d = np.where(a <= 9.0, a / 96.0, 9.0 / 96.0 + (a - 9.0) / 323.0)
    return np.degrees(np.sign(tau) * d)


mp250 = next(FD._D("26.07.27", "250_3_250_3").glob("*.mp4"))
fr250 = [gray(f) for f in iio.imiter(str(mp250), plugin="FFMPEG")]
d250 = [float(np.abs(fr250[i + 1] - fr250[i]).mean()) for i in range(len(fr250) - 1)]
j250 = int(min(np.argsort(d250)[-12:]))
T_REF = {k: fr250[j250 - 5][y - 20:y + 20, x - 20:x + 20].copy() for k, (y, x) in PTS0.items()}
del fr250

OUT = {}
for fold in sorted([p for p in FD._D(DAY).iterdir() if p.is_dir() and (p / "hip2.xlsx").exists()]):
    mp4s = list(fold.glob("*.mp4"))
    if not mp4s:
        continue
    try:
        fr = [gray(f) for f in iio.imiter(str(mp4s[0]), plugin="FFMPEG")]
        fps = float(iio.immeta(str(mp4s[0]), plugin="FFMPEG").get("fps", 24.0))
    except Exception as ex:
        print(f"{fold.name}: 영상 실패 {ex}", flush=True)
        continue
    dd = [float(np.abs(fr[i + 1] - fr[i]).mean()) for i in range(len(fr) - 1)]
    j = int(min(np.argsort(dd)[-12:]))
    try:
        d = FD.load2(fold); seg = FD.segment(d)
    except Exception as ex:
        print(f"{fold.name}: 데이터 FAIL {type(ex).__name__}", flush=True)
        del fr
        continue
    # 이륙 앵커: j 클러스터 시작부터 앞으로 발 블러 파탄 탐색은 생략하고 j 자체 사용
    # (하강은 저속 — j±2프레임 오차 허용, 검증: 하강 표본의 θ_enc 속도와 θ_vid 속도 상관)
    SH = seg["t_lo"] - j / fps
    f_desc = int((seg["t_desc"] - SH) * fps)
    f_bot = int((d["t"][seg["i_bot"]] - SH) * fps)
    f_desc = max(0, f_desc); f_bot = min(len(fr) - 1, f_bot)
    if f_bot - f_desc < 12:
        print(f"{fold.name}: 하강 프레임 부족 ({f_desc}~{f_bot})", flush=True)
        del fr
        continue
    # 바닥에서 코스 → 역방향 워크
    ctr = {}
    T_OWN = {}
    bad = False
    for k, (y, x) in PTS0.items():
        e0, dx0, dy0 = match(fr[f_bot], T_REF[k], y, x, ry=90, rx=140)
        cy, cx = y + dy0, x + dx0
        if e0 > 8000:
            print(f"{fold.name}: {k} 코스 파탄 (e {e0:.0f})", flush=True)
            bad = True
        ctr[k] = (cy, cx)
        T_OWN[k] = fr[f_bot][cy - 20:cy + 20, cx - 20:cx + 20].copy()
    if bad:
        del fr
        continue
    rows = []
    for i in range(f_bot, f_desc - 1, -4):
        pt = {}
        ok = True
        for k in PTS0:
            cy, cx = ctr[k]
            e, dx, dy = match(fr[i], T_OWN[k], cy, cx)
            if e > 2000:
                ok = False
                break
            ctr[k] = (cy + dy, cx + dx)
            pt[k] = ctr[k]
        if not ok:
            continue
        ky, kx = pt["knee"]; fy, fx = pt["foot"]
        rows.append(dict(fr=i, t=i / fps + SH,
                         th_vid=float(np.degrees(np.arctan2(-(ky - fy), kx - fx)))))
    del fr
    if len(rows) < 8:
        print(f"{fold.name}: 유효 표본 부족 ({len(rows)})", flush=True)
        continue
    rows = rows[::-1]                     # 시간 순
    tv = np.array([r["t"] for r in rows]); thv = np.array([r["th_vid"] for r in rows])
    the = np.interp(tv, d["t"], np.degrees(d["q1"] + d["q2"]))
    tau1 = np.interp(tv, d["t"], d["a1"])
    C0 = float(np.mean(thv[-3:] - the[-3:]))
    defl = (the + C0) - thv
    pred = -(defl_pred_deg(tau1) - defl_pred_deg(np.mean(tau1[-3:])))
    # 검증 상관 (정렬 새너티): 영상 각속도 vs 인코더 각속도
    cc = float(np.corrcoef(np.gradient(thv), np.gradient(the))[0, 1]) if len(thv) > 4 else 0.0
    # 회귀 defl = α·pred + β (pred 스팬 충분할 때만)
    span = float(pred.max() - pred.min())
    if span > 1.0:
        A_ = np.vstack([pred, np.ones_like(pred)]).T
        alpha, beta = np.linalg.lstsq(A_, defl, rcond=None)[0]
    else:
        alpha, beta = np.nan, np.nan
    OUT[fold.name] = dict(n=len(rows), corr=cc, span=span, alpha=float(alpha), beta=float(beta),
                          defl=defl.round(2).tolist(), pred=pred.round(2).tolist(),
                          tau1=tau1.round(2).tolist(), t=tv.round(3).tolist())
    print(f"{fold.name}: n={len(rows)} 정렬상관 {cc:.2f} | pred 스팬 {span:.1f}° | α={alpha:.2f} β={beta:+.2f} | "
          f"defl 범위 {defl.min():+.1f}~{defl.max():+.1f}°", flush=True)

jp = HERE / ("_fs_video_desc_" + DAY.replace(".", "") + ".json")
json.dump(OUT, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done →", jp)
