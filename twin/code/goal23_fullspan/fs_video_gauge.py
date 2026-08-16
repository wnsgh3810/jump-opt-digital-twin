# -*- coding: utf-8 -*-
"""fs_video_gauge — 22/25 킥 날 잔존 게이지(+3.6~4.4°)의 영상 판별 (Day1 #4).

질문: 그 +4°는 실기 '사슬 비틀림 과다'(구조/장착 미끄럼 — 인코더≠사지)인가,
아니면 트윈 동역학 오차(인코더 자체를 못 맞춤)인가?
방법 (SEA video_deflection 계승, *2·fs 갱신):
  θ_vid = atan2(무릎휠−발볼트) [영상 = 사지 진짜 각] vs θ_enc = q1+q2 [*2 인코더]
  → 비틀림 defl = (θ_enc+C0) − θ_vid vs fs 2단 스프링 예측 τ1→defl(96/323@9).
  초과분 excess = defl − pred가 22/25에서 +4°대면 '실기 구조' / ~0이면 '트윈 동역학'.
정렬: 영상 이륙(발 템플릿 파탄) ↔ GRF2 이륙(세그먼트 t_lo — 상대 타이밍 전용, 사전 준수).
템플릿: 27일 250 검증 좌표(무릎휠 y1065x610·발볼트 y1183x368·몸통 y665x212/y660x502)
→ 각 영상에 광역 코스 탐색(±90/±140) 후 자기 템플릿 재수립 (video_slip_alldays 방식).
CLI: python fs_video_gauge.py <day>   (예: 26.07.25 · 골든: 26.07.27 = SEA 재현 확인)
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
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import imageio.v3 as iio

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fs_data as FD                     # noqa: E402

ROOT = Path(DATA_ROOT)
DAY = sys.argv[1] if len(sys.argv) > 1 else "26.07.27"
PTS0 = {"knee": (1065, 610), "foot": (1183, 368), "bodyL": (665, 212), "bodyR": (660, 502)}


def gray(a):
    return a.mean(axis=2).astype(np.float32)


def match(f, T, cy, cx, ry=35, rx=55):
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


def load_frames(mp4):
    fr = [gray(f) for f in iio.imiter(str(mp4), plugin="FFMPEG")]
    try:
        fps = float(iio.immeta(str(mp4), plugin="FFMPEG").get("fps", 24.0))
    except Exception:
        fps = 24.0
    return fr, fps


def defl_pred_deg(tau):
    """fs 2단 스프링 (96/323@9): 토크→처짐 [deg] (부호 보존)."""
    a = np.abs(tau)
    d = np.where(a <= 9.0, a / 96.0, 9.0 / 96.0 + (a - 9.0) / 323.0)
    return np.degrees(np.sign(tau) * d)


# ── 기준 템플릿 (27일 250 — SEA 검증 좌표) ──
mp250 = next(FD._D("26.07.27", "250_3_250_3").glob("*.mp4"))
fr250, _ = load_frames(mp250)
d250 = [float(np.abs(fr250[i + 1] - fr250[i]).mean()) for i in range(len(fr250) - 1)]
j250 = int(min(np.argsort(d250)[-12:]))
T_REF = {k: fr250[j250 - 5][y - 20:y + 20, x - 20:x + 20].copy() for k, (y, x) in PTS0.items()}
del fr250

OUT = {}
for fold in sorted([p for p in FD._D(DAY).iterdir() if p.is_dir() and (p / "hip2.xlsx").exists()]):
    mp4s = list(fold.glob("*.mp4"))
    if not mp4s:
        print(f"{fold.name}: 영상 없음", flush=True)
        continue
    try:
        fr, fps = load_frames(mp4s[0])
    except Exception as ex:
        print(f"{fold.name}: 영상 읽기 실패 {ex}", flush=True)
        continue
    dd = [float(np.abs(fr[i + 1] - fr[i]).mean()) for i in range(len(fr) - 1)]
    j = int(min(np.argsort(dd)[-12:]))
    if j < 8:
        print(f"{fold.name}: 점프 탐지 이상 (j={j})", flush=True)
        del fr
        continue
    # 코스 광역 → 자기 템플릿 (프레이밍 세션차 흡수)
    PTS = {}
    T_OWN = {}
    okc = True
    for k, (y, x) in PTS0.items():
        e0, dx0, dy0 = match(fr[j - 5], T_REF[k], y, x, ry=90, rx=140)
        cy, cx = y + dy0, x + dx0
        if k in ("knee", "foot") and e0 > 6000:
            print(f"{fold.name}: {k} 코스 탐색 파탄 (e {e0:.0f})", flush=True)
            okc = False
        PTS[k] = (cy, cx)
        T_OWN[k] = fr[j - 6][cy - 20:cy + 20, cx - 20:cx + 20].copy()
    if not okc:
        del fr
        continue
    FRI = list(range(j - 6, min(j + 2, len(fr))))
    trk = {k: [] for k in PTS}
    for i in FRI:
        for k, (y, x) in PTS.items():
            e, dx, dy = match(fr[i], T_OWN[k], y, x)
            trk[k].append((i, e, x + dx, y + dy))
    del fr
    rows = []
    for idx, i in enumerate(FRI):
        ek, ef = trk["knee"][idx][1], trk["foot"][idx][1]
        if ek > 1500 or ef > 1500:
            continue
        kx, ky = trk["knee"][idx][2], trk["knee"][idx][3]
        fx, fy = trk["foot"][idx][2], trk["foot"][idx][3]
        bl, br = trk["bodyL"][idx], trk["bodyR"][idx]
        body = np.degrees(np.arctan2(-(br[3] - bl[3]), br[2] - bl[2])) if (bl[1] < 4000 and br[1] < 4000) else np.nan
        rows.append(dict(fr=i, t_vid=i / fps,
                         th_vid=float(np.degrees(np.arctan2(-(ky - fy), kx - fx))), body=float(body)))
    if len(rows) < 4:
        print(f"{fold.name}: 유효 프레임 부족 ({len(rows)})", flush=True)
        continue
    # 인코더 (*2) + 정렬 (영상 이륙 = 발 템플릿 파탄 ↔ 세그먼트 t_lo)
    try:
        d = FD.load2(fold)
        seg = FD.segment(d)
    except Exception as ex:
        print(f"{fold.name}: 데이터 FAIL {type(ex).__name__}", flush=True)
        continue
    th_enc = np.degrees(d["q1"] + d["q2"])
    f_lo = None
    for idx in range(len(FRI)):
        if trk["foot"][idx][1] > 1500:
            f_lo = FRI[idx] - 0.5
            break
    if f_lo is None:
        f_lo = FRI[-1] + 0.5
    SH = seg["t_lo"] - f_lo / fps
    tv = np.array([r["t_vid"] for r in rows])
    thv = np.array([r["th_vid"] for r in rows])
    tmap = tv + SH
    the = np.interp(tmap, d["t"], th_enc)
    C0 = float(np.mean(thv[:3] - the[:3]))
    defl = (the + C0) - thv
    tau1 = np.interp(tmap, d["t"], d["a1"])
    pred = -(defl_pred_deg(tau1) - defl_pred_deg(np.mean(tau1[:3])))
    exc = defl - pred
    OUT[fold.name] = dict(fps=fps, shift_ms=SH * 1e3,
                          rows=[dict(r, defl=float(defl[i]), pred=float(pred[i]), exc=float(exc[i]),
                                     tau1=float(tau1[i])) for i, r in enumerate(rows)])
    tail = ", ".join(f"{e:+.1f}" for e in exc[-3:])
    print(f"{fold.name}: fps {fps:.0f} shift {SH*1e3:+.0f}ms | 말기 비틀림 {defl[-1]:+.2f}° 예측 {pred[-1]:+.2f}° "
          f"→ 초과 {exc[-1]:+.2f}° (말미 3프레임: {tail}) | body 범위 {np.nanmax([r['body'] for r in rows]) - np.nanmin([r['body'] for r in rows]):.2f}°", flush=True)

jp = HERE / ("_fs_video_gauge_" + DAY.replace(".", "") + ".json")
json.dump(OUT, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done →", jp)
