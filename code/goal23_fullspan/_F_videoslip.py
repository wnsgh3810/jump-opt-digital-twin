# -*- coding: utf-8 -*-
"""_F_videoslip — 발 슬립 영상 재판독 (독립 재구축, 2026-08-02).

배경: 구 판독(_fs_descslip_all.json의 drift_deep_px)을 만든 스크립트(fs_footdrift.py 추정)가
유실되어 정의를 알 수 없음. px→mm 스케일도 구 코드(exp5_video_slip.py/video_slip_alldays.py)에서
"0.7~1.2mm/px 범위"라는 추정치였을 뿐 실측 눈금 기반이 아니었음. 본 스크립트는:
  ① 27일 프레임에 실제로 찍힌 벽면 줄자(10~140cm 눈금, 1cm 간격 tick + 10cm 라벨)를 이용해
     날짜별(카메라가 날마다 다름) mm/px 스케일을 라벨 간격 회귀로 직접 확립.
  ② 발볼트를 하강 창(GRF/자세 세그먼트: t_desc~바닥) 동안 매 프레임 서브픽셀(NCC+포물선보간)로
     절대 x 추적. 카메라 흔들림은 줄자 위 고정 라벨 패치(=배경 기준점) 추적으로 차감.
  ③ 이전 판독(drift_deep_px)·트윈 예측과 비교.

정렬: 영상 프레임과 인코더 시간축은 "이륙 앵커"로 연결 — 프레임차분 최댓값 클러스터(=푸시~비행,
블러 급증) 시작 인덱스 j ↔ fs_data.segment()의 t_lo. shift = t_lo − j/fps.
데이터 원본(mp4/xlsx)은 절대 미수정 — 읽기 전용.

CLI: python _F_videoslip.py [day ...]   (인자 없으면 5일 전부)
출력: _F_videoslip.json (스키마는 하단 main() 참조), 콘솔에 날짜별 스케일·trial별 표.
"""
import os, sys, json, glob
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
from scipy import ndimage
import imageio.v3 as iio

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe                      # noqa: E402
import fs_data as FD              # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
DAYS = ["26.07.22", "26.07.23", "26.07.24", "26.07.25", "26.07.27"]

# 27일 발볼트 기준 템플릿 좌표 (fs_video_gauge.py 검증 좌표 재사용 — 광역 코스탐색의 시드)
FOOT_REF_2707 = (1183, 368)
REF_DAY = "26.07.27"


# ───────────────────────── 유틸 ─────────────────────────

def gray(a):
    return a.mean(axis=2).astype(np.float32)


def load_frames(mp4, max_frames=None):
    fr = []
    for i, f in enumerate(iio.imiter(str(mp4), plugin="FFMPEG")):
        fr.append(gray(f))
        if max_frames and i >= max_frames:
            break
    try:
        fps = float(iio.immeta(str(mp4), plugin="FFMPEG").get("fps", 24.0))
    except Exception:
        fps = 24.0
    return fr, fps


def jump_frame_index(frames):
    """프레임차분 최댓값 클러스터(푸시~비행) 시작 인덱스 j (이륙 앵커 시드)."""
    d = [float(np.abs(frames[i + 1] - frames[i]).mean()) for i in range(len(frames) - 1)]
    top = np.argsort(d)[-12:]
    return int(min(top))


# ───────────────────────── NCC + 서브픽셀 ─────────────────────────

def _ncc(patch, T):
    p = patch - patch.mean()
    t = T - T.mean()
    denom = np.sqrt((p * p).sum() * (t * t).sum())
    if denom < 1e-6:
        return -1.0
    return float((p * t).sum() / denom)


def ncc_search(f, T, cy, cx, ry, rx):
    """정수화소 격자 NCC 탐색. 반환: (best_score, dy*, dx*, score_grid, y0, x0)
    score_grid: (2ry+1, 2rx+1) — 이후 포물선 보간에 재사용.
    T의 세로/가로가 홀수여도(리사이즈 템플릿 대비) 정확히 동작하도록 비대칭 반폭 사용
    (h0=th//2, h1=th-h0 — 대칭 ±h 가정 시 홀수 크기에서 patch.shape가 항상 어긋나
    전 격자가 무효화되는 버그 확인됨, day22 리사이즈 코스탐색에서 재현)."""
    th, tw = T.shape
    h0, h1 = th // 2, th - th // 2
    w0, w1 = tw // 2, tw - tw // 2
    ny, nx = 2 * ry + 1, 2 * rx + 1
    grid = np.full((ny, nx), -1.0, dtype=np.float64)
    for iy, dy in enumerate(range(-ry, ry + 1)):
        yy0, yy1 = cy + dy - h0, cy + dy + h1
        if yy0 < 0 or yy1 > f.shape[0]:
            continue
        for ix, dx in enumerate(range(-rx, rx + 1)):
            xx0, xx1 = cx + dx - w0, cx + dx + w1
            if xx0 < 0 or xx1 > f.shape[1]:
                continue
            patch = f[yy0:yy1, xx0:xx1]
            if patch.shape != T.shape:
                continue
            grid[iy, ix] = _ncc(patch, T)
    iy, ix = np.unravel_index(np.argmax(grid), grid.shape)
    return float(grid[iy, ix]), iy - ry, ix - rx, grid, cy - ry, cx - rx


def parabolic_refine(grid, iy, ix):
    """격자 peak(iy,ix) 주변 3점 포물선 보간 (분리형: y·x 각각) → 서브픽셀 오프셛(dsy,dsx)."""
    ny, nx = grid.shape
    dsy = dsx = 0.0
    if 0 < iy < ny - 1:
        y0, y1, y2 = grid[iy - 1, ix], grid[iy, ix], grid[iy + 1, ix]
        den = (y0 - 2 * y1 + y2)
        if abs(den) > 1e-9:
            dsy = 0.5 * (y0 - y2) / den
            dsy = float(np.clip(dsy, -1.0, 1.0))
    if 0 < ix < nx - 1:
        x0, x1, x2 = grid[iy, ix - 1], grid[iy, ix], grid[iy, ix + 1]
        den = (x0 - 2 * x1 + x2)
        if abs(den) > 1e-9:
            dsx = 0.5 * (x0 - x2) / den
            dsx = float(np.clip(dsx, -1.0, 1.0))
    return dsy, dsx


def track_point(frames, idx_list, T0, cy0, cx0, ry=20, rx=25, propagate=True, min_score_propagate=0.55):
    """프레임열 idx_list(임의 순서, 보통 시간순)를 따라 템플릿 T0(1개, 고정)를 추적.
    propagate=True: 이전 위치를 다음 탐색 중심으로 전파 (발볼트 — 실제 이동 추적 필요).
    propagate=False: 탐색 중심을 시드(cy0,cx0)에 고정 (배경기준점 — 정적 물체이므로 전파 시
    프레임별 미세오차가 누적되어 줄자의 인접 유사 눈금으로 "걸어가는" 드리프트 위험 확인됨).
    저신뢰 프레임(score<min_score_propagate)에서는 전파를 건너뛴다 — 그렇지 않으면 한 번의
    오정합이 다음 탐색 중심을 오염시켜 눈덩이처럼 드리프트가 누적된다(day22 실측으로 확인:
    전파 무조건 허용 시 -27~-34px의 물리적으로 불가능한 "표류"가 발생).
    반환: dict(t_idx -> (y,x,score))."""
    out = {}
    cy, cx = cy0, cx0
    for i in idx_list:
        sc, iy, ix, grid, y0, x0 = ncc_search(frames[i], T0, int(round(cy)), int(round(cx)), ry, rx)
        dsy, dsx = parabolic_refine(grid, iy + ry, ix + rx)
        y_abs = y0 + (iy + ry) + dsy
        x_abs = x0 + (ix + rx) + dsx
        out[i] = (float(y_abs), float(x_abs), sc)
        if propagate and sc >= min_score_propagate:
            cy, cx = y_abs, x_abs       # 다음 탐색 중심 갱신 (전파, 신뢰도 충분할 때만)
    return out


# ───────────────────────── ① 줄자 px→mm 스케일 ─────────────────────────

def _label_groups(f, x0, x1, thr=130, min_sz=60, max_sz=300, ygap=30):
    sub = f[:, x0:x1]
    dark = sub < thr
    lbl, n = ndimage.label(dark)
    if n == 0:
        return []
    coms = ndimage.center_of_mass(dark, lbl, range(1, n + 1))
    sizes = ndimage.sum(dark, lbl, range(1, n + 1))
    comps = [(c[0], c[1], s) for c, s in zip(coms, sizes) if min_sz < s < max_sz]
    if len(comps) < 4:
        return []
    comps.sort(key=lambda c: c[0])
    groups = []
    cur = [comps[0]]
    for c in comps[1:]:
        if c[0] - cur[-1][0] < ygap:
            cur.append(c)
        else:
            groups.append(cur)
            cur = [c]
    groups.append(cur)
    return [(float(np.mean([g[0] for g in grp])), float(np.mean([g[1] for g in grp]))) for grp in groups]


def _clean_diffs(diffs):
    """인접 라벨간 간격 중 절반 크기로 쪼개진 오검출(한 라벨의 상하 stacked 숫자가 별개
    그룹으로 분리)을 인접 항끼리 합쳐 복구. day24/day27 각기 다른 trial의 f_cal 프레임에서
    반복 확인된 실패모드 — tail(바닥쪽) 그룹에서 특히 잦음(전역 med<65 필터는 창 전체 중앙값이라
    일부 tail만 쪼개진 경우 못 거름). 정상 간격의 기준은 '65px 이상인 항들의 중앙값'."""
    diffs = list(diffs)
    normal = [d for d in diffs if d > 65]
    ref = float(np.median(normal)) if normal else (float(np.median(diffs)) if diffs else 0.0)
    out = []
    i = 0
    while i < len(diffs):
        d = diffs[i]
        if d < 0.65 * ref and i + 1 < len(diffs):
            out.append(d + diffs[i + 1])
            i += 2
        else:
            out.append(d)
            i += 1
    return np.array(out)


def calibrate_ruler(f):
    """줄자의 10cm 간격 라벨(10,20,...) y중심을 검색해 px/10cm 산출.
    x0 슬라이딩 창 탐색으로 라벨열을 자동 포착 (날짜별 프레이밍차 흡수).
    반환: dict(px_per_10cm_global, px_per_10cm_local, mm_per_px_global, mm_per_px_local,
               n_groups, cv, ys, xs, window) 또는 실패 시 None."""
    H, W = f.shape
    xmax = int(W * 0.55)
    best = None
    for x0 in range(0, max(1, xmax - 60), 6):
        for width in (60, 80, 100, 120, 150):
            x1 = x0 + width
            if x1 > xmax:
                continue
            gs = _label_groups(f, x0, x1)
            if len(gs) < 6:
                continue
            ys = np.array([g[0] for g in gs])
            diffs = _clean_diffs(np.diff(ys))
            if len(diffs) < 4:
                continue
            med = float(np.median(diffs))
            # 물리적 하한: 5개 날짜 실측 모두 10cm 라벨 간격 80~120px대 (카메라 거리차 반영).
            # <65px 는 한 라벨의 위아래 stacked 숫자가 별개 그룹으로 쪼개진 오검출(간격이
            # 정확히 절반으로 관측됨) — _clean_diffs로 병합했는데도 낮으면 이 창은 버림.
            if med < 65:
                continue
            cv = float(np.std(diffs) / med)
            key = (round(cv, 3), -len(gs))
            if best is None or key < best[0]:
                best = (key, x0, x1, gs)
    if best is None:
        return None
    _, x0, x1, gs = best
    ys = np.array([g[0] for g in gs])
    xs = np.array([g[1] for g in gs])
    diffs = _clean_diffs(np.diff(ys))
    med = float(np.median(diffs))
    cv = float(np.std(diffs) / med)
    n_local = min(3, len(diffs))
    local = float(np.median(diffs[-n_local:]))     # 하단(바닥 근접) 국소 기울기 — 원근 보정
    return dict(px_per_10cm_global=med, px_per_10cm_local=local,
                mm_per_px_global=100.0 / med, mm_per_px_local=100.0 / local,
                n_groups=int(len(gs)), cv=cv, ys=ys.round(1).tolist(), xs=xs.round(1).tolist(),
                bg_seed=(float(ys[len(ys) // 2]), float(xs[len(ys) // 2])),   # 배경(카메라흔들림) 기준점 시드
                window=[x0, x1])


# ───────────────────────── ② 발볼트 코스 위치 (27일 템플릿 → 자기 템플릿) ─────────────────────────

def locate_foot_seed(f, T_ref, y0, x0, ry=110, rx=170, resize=1.0):
    """T_ref로 광역 코스탐색. resize!=1.0이면 날짜 간 카메라 줌 차이를 보정하기 위해
    템플릿을 이 배율로 리샘플한 뒤 매칭 (스케일 불일치 시 코스탐색 자체가 엉뚱한 곳에
    안착하는 문제가 day22(1920x1080, 27일과 확연히 다른 화각)에서 확인됨)."""
    if abs(resize - 1.0) > 0.03:
        new_h = max(8, int(round(T_ref.shape[0] * resize)))
        new_w = max(8, int(round(T_ref.shape[1] * resize)))
        zy, zx = new_h / T_ref.shape[0], new_w / T_ref.shape[1]
        T_use = ndimage.zoom(T_ref, (zy, zx), order=1)
    else:
        T_use = T_ref
    sc, iy, ix, grid, gy0, gx0 = ncc_search(f, T_use, y0, x0, ry, rx)
    cy, cx = y0 + iy, x0 + ix
    return cy, cx, sc


# ───────────────────────── main ─────────────────────────

def process_trial(day, fold, T_ref_foot, ref_scale, ref_shape, quiet=False):
    mp4s = list(fold.glob("*.mp4"))
    if not mp4s:
        return None, "영상 없음"
    d = FD.load2(fold)
    seg = FD.segment(d)
    frames, fps = load_frames(mp4s[0])
    if len(frames) < 20:
        return None, f"프레임 부족 ({len(frames)})"
    j = jump_frame_index(frames)
    if j < 8:
        return None, f"점프탐지 이상 (j={j})"
    SH = seg["t_lo"] - j / fps
    f_desc = int(np.ceil((seg["t_desc"] - SH) * fps))
    f_bot = int(np.floor((d["t"][seg["i_bot"]] - SH) * fps))
    f_desc = max(0, f_desc)
    f_bot = min(len(frames) - 1, f_bot)
    if f_bot - f_desc < 15:
        return None, f"하강 프레임 부족 ({f_desc}~{f_bot})"

    # 스케일/배경기준점: trial 자신의 프레임에서 매번 재확립 (동일 날짜라도 phone 재배치로
    # 프레이밍이 trial마다 미세하게 다를 수 있음 — day-level 재사용시 배경패치 오정합 확인됨).
    # f_bot(크라우치 정지자세) 대신 이른 정지 프레임 사용 — f_bot 프레임은 trial마다 인덱스가
    # 달라 이따금 프레임 압축/블러로 숫자 라벨의 상하 stacked 획이 갈라져 절반 간격으로
    # 오검출되는 사례 확인(day24). 초반 프레임은 항상 로봇 대기자세로 안정적.
    f_cal = min(30, len(frames) - 1)
    cal_rep = calibrate_ruler(frames[f_cal])
    if cal_rep is None:
        return None, "줄자 판독 실패"

    # 발볼트 코스 위치: 바닥(f_bot) 프레임에서 27일 템플릿으로 광역 탐색.
    # ① 화면비 보정: 27일 절대좌표를 이 날짜 프레임 크기에 비례 변환한 좌표를 탐색 시드로
    #    사용 (day22는 1920x1080 — 27일과 해상도·구도가 달라 절대좌표 그대로 쓰면 탐색반경을
    #    벗어나 엉뚱한 부품(모터 쪽)에 안착함을 실측으로 확인).
    # ② 줌차 보정: 27일 대비 이 날짜의 mm/px 비율만큼 템플릿을 리샘플.
    Href, Wref = ref_shape
    Hd, Wd = frames[f_bot].shape
    seed_y = int(round(FOOT_REF_2707[0] / Href * Hd))
    seed_x = int(round(FOOT_REF_2707[1] / Wref * Wd))
    resize = ref_scale / cal_rep["mm_per_px_local"]
    cy, cx, e0 = locate_foot_seed(frames[f_bot], T_ref_foot, seed_y, seed_x,
                                   ry=150, rx=200, resize=resize)
    if e0 < 0.45:
        return None, f"발볼트 코스탐색 파탄 (ncc={e0:.2f})"
    T_own = frames[f_bot][int(cy) - 20:int(cy) + 20, int(cx) - 20:int(cx) + 20].copy()
    if T_own.shape != (40, 40):
        return None, "발볼트 템플릿 프레임 경계 초과"

    idx_list = list(range(f_bot, f_desc - 1, -1))     # 바닥→하강개시 (자기 템플릿 원점에서 역방향 전파)
    foot_trk = track_point(frames, idx_list, T_own, cy, cx, ry=18, rx=22)

    # 배경(카메라 흔들림) 기준점: 이 trial 자신의 프레임에서 확립한 줄자 라벨 패치(bg_seed)
    bgy0, bgx0 = int(cal_rep["bg_seed"][0]), int(cal_rep["bg_seed"][1])
    bgh, bgw = 32, 24   # 세로로 더 큼 (숫자 두어개+공백 포함 → 눈금 반복패턴 대비 모호성 감소)
    if not (bgh <= bgy0 < frames[f_cal].shape[0] - bgh and bgw <= bgx0 < frames[f_cal].shape[1] - bgw):
        bg_trk = None
    else:
        T_bg = frames[f_cal][bgy0 - bgh:bgy0 + bgh, bgx0 - bgw:bgx0 + bgw].copy()
        bg_trk = track_point(frames, idx_list, T_bg, bgy0, bgx0, ry=8, rx=8, propagate=False)

    idx_sorted = sorted(foot_trk)
    t_arr = np.array([(i / fps + SH) for i in idx_sorted])
    x_raw = np.array([foot_trk[i][1] for i in idx_sorted])
    y_raw = np.array([foot_trk[i][0] for i in idx_sorted])
    q = np.array([foot_trk[i][2] for i in idx_sorted])
    if bg_trk is not None:
        xb = np.array([bg_trk[i][1] for i in idx_sorted])
        yb = np.array([bg_trk[i][0] for i in idx_sorted])
        qb = np.array([bg_trk[i][2] for i in idx_sorted])
        # 배경 트랙 중앙값 필터 (창5) — 실제 카메라 흔들림은 저주파인데 반해 간헐적 오정합은
        # 1~2프레임 급跳 스파이크로 나타남 (정지 텍스트 패치의 준-주기적 패턴 오매칭 위험).
        xb_s = ndimage.median_filter(xb, size=min(5, len(xb)))
        yb_s = ndimage.median_filter(yb, size=min(5, len(yb)))
        x_corr = x_raw - (xb_s - xb_s[0])
        y_corr = y_raw - (yb_s - yb_s[0])
        bg_shake_px = float(np.max(xb_s) - np.min(xb_s))
    else:
        x_corr = x_raw.copy(); y_corr = y_raw.copy()
        qb = np.full_like(q, np.nan)
        bg_shake_px = float("nan")

    # 주지표 = x_raw(발볼트 원신호) 기반. bg_shake_px가 원신호 진폭(수~10px대)과 같은 자릿수인
    # 사례가 확인되어(day22) 배경보정을 무조건 차감하면 보정 자체의 트래킹 잡음이 신호에
    # 그대로 얹혀 오히려 더 시끄러워질 위험 — bg_corr는 참고용 2차 지표로 남기고, bg_shake는
    # "차감 안 한 채로 남는 카메라흔들림 불확도 밴드"로 별도 보고한다.
    good = q > 0.6
    n_good = int(good.sum())
    if n_good < 10:
        return None, f"추적 품질 미달 (good {n_good}/{len(q)})"

    tg, xg = t_arr[good], x_raw[good]
    A = np.vstack([tg, np.ones_like(tg)]).T
    slope, intercept = np.linalg.lstsq(A, xg, rcond=None)[0]
    dur = tg[-1] - tg[0]
    drift_fit_px = float(slope * dur)
    drift_end_px = float(np.median(xg[-3:]) - np.median(xg[:3]))
    rng_px = float(xg.max() - xg.min())
    resid = xg - (A @ [slope, intercept])
    quality = "good" if (n_good / len(q) > 0.85 and np.std(resid) < 1.5) else \
              ("marginal" if n_good / len(q) > 0.6 else "poor")

    # bg_corr 2차지표 (동일 good 마스크 — foot ncc 기준. bg 자체 품질은 섞지 않음: 그 영향은
    # 이미 bg_shake_px 불확도로 노출)
    xgc = x_corr[good]
    Ac = np.vstack([tg, np.ones_like(tg)]).T
    slope_c, intercept_c = np.linalg.lstsq(Ac, xgc, rcond=None)[0]
    drift_fit_px_corr = float(slope_c * dur)

    scale_local = cal_rep["mm_per_px_local"]
    scale_global = cal_rep["mm_per_px_global"]
    unc_mm = bg_shake_px * scale_local if bg_shake_px == bg_shake_px else None
    res = dict(
        n_frames=int(len(q)), n_good=n_good, fps=fps, shift_ms=float(SH * 1e3),
        f_desc=f_desc, f_bot=f_bot,
        desc_drift_px=round(drift_fit_px, 2), desc_drift_px_endpoint=round(drift_end_px, 2),
        range_px=round(rng_px, 2),
        scale_mm_per_px=round(scale_local, 4), scale_mm_per_px_global=round(scale_global, 4),
        desc_drift_mm=round(drift_fit_px * scale_local, 3),
        desc_drift_mm_endpoint=round(drift_end_px * scale_local, 3),
        range_mm=round(rng_px * scale_local, 3),
        desc_drift_mm_bgcorr=round(drift_fit_px_corr * scale_local, 3),
        uncertainty_mm=round(unc_mm, 3) if unc_mm is not None else None,
        bg_shake_px=round(bg_shake_px, 2) if bg_shake_px == bg_shake_px else None,
        ncc_mean=round(float(q.mean()), 3), ncc_bg_mean=round(float(np.nanmean(qb)), 3) if bg_trk else None,
        fit_resid_std_px=round(float(np.std(resid)), 3),
        quality=quality,
        t=t_arr.round(3).tolist(), x_raw_px=x_raw.round(2).tolist(), x_corr_px=x_corr.round(2).tolist(),
        ncc=q.round(3).tolist(),
    )
    return res, None


def main():
    days = sys.argv[1:] if len(sys.argv) > 1 else DAYS
    OUT = {"_meta": dict(desc="fs_video_desc/fs_video_gauge 계보 재구축 — px->mm 실측 줄자 스케일 + "
                              "서브픽셀(NCC+포물선보간) 발볼트 추적. "
                              "주지표 desc_drift_px/mm = x_raw(원신호) 선형적합. "
                              "desc_drift_mm_bgcorr = 배경ROI(줄자 라벨) 차감판(2차/참고). "
                              "uncertainty_mm = bg_shake_px*scale — 차감 안 한 채 남기는 카메라흔들림 "
                              "불확도 밴드(day22처럼 bg_shake가 원신호와 동일 자릿수면 보정판을 신뢰하지 "
                              "말고 이 밴드로 원신호를 감싸 해석할 것).")}

    # 27일 발볼트 기준 템플릿 확보 (fs_video_gauge.py 좌표 재사용) + 27일 자체 스케일
    # (다른 날짜 코스탐색 시 화각차 보정의 기준값으로 사용)
    ref_fold = FD._D(REF_DAY, "250_3_250_3")
    ref_mp4 = list(ref_fold.glob("*.mp4"))[0]
    ref_frames, ref_fps = load_frames(ref_mp4)
    jr = jump_frame_index(ref_frames)
    fy, fx = FOOT_REF_2707
    T_ref_foot = ref_frames[jr - 5][fy - 20:fy + 20, fx - 20:fx + 20].copy()
    ref_cal = calibrate_ruler(ref_frames[min(30, len(ref_frames) - 1)])
    ref_scale = ref_cal["mm_per_px_local"]
    ref_shape = ref_frames[0].shape
    print(f"기준(27일) 스케일: {ref_scale:.4f}mm/px, 프레임 {ref_shape}", flush=True)

    for day in days:
        base = FD._D(day)
        if not base.exists():
            print(f"{day}: 폴더 없음", flush=True)
            continue
        trials = FD.trials_of(base)
        if not trials:
            print(f"{day}: trial 없음", flush=True)
            continue
        print(f"\n=== {day} === ({len(trials)} trials — 스케일은 trial마다 자신의 프레임에서 재확립)", flush=True)
        OUT[day] = {}
        scales = []
        for fold in trials:
            key = fold.name
            res, err = process_trial(day, fold, T_ref_foot, ref_scale, ref_shape)
            if err:
                print(f"  {key}: FAIL — {err}", flush=True)
                OUT[day][key] = dict(fail=err)
                continue
            scales.append(res["scale_mm_per_px"])
            unc = f"±{res['uncertainty_mm']:.2f}mm" if res["uncertainty_mm"] is not None else "±?"
            print(f"  {key}: scale {res['scale_mm_per_px']:.4f}mm/px n={res['n_frames']}(good {res['n_good']}) "
                  f"drift {res['desc_drift_mm']:+.2f}mm{unc} (bg보정판 {res['desc_drift_mm_bgcorr']:+.2f}mm) "
                  f"끝점 {res['desc_drift_mm_endpoint']:+.2f}mm 범위 {res['range_mm']:.2f}mm "
                  f"| bg흔들림 {res['bg_shake_px']}px | ncc {res['ncc_mean']:.2f} | {res['quality']}", flush=True)
            OUT[day][key] = res
        if scales:
            print(f"  -> {day} 스케일 trial간 일관성: {np.mean(scales):.4f} ± {np.std(scales):.4f} mm/px "
                  f"(n={len(scales)})", flush=True)
            OUT[day]["_scale_summary"] = dict(mean=float(np.mean(scales)), std=float(np.std(scales)),
                                              n=len(scales), values=scales)

    outp = HERE / "_F_videoslip.json"
    safe.atomic_json_write(outp, OUT)
    print(f"\ndone -> {outp}")


if __name__ == "__main__":
    main()
