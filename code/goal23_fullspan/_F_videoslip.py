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

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
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
    score_grid: (2ry+1, 2rx+1) — 이후 포물선 보간에 재사용."""
    h, w = T.shape[0] // 2, T.shape[1] // 2
    ny, nx = 2 * ry + 1, 2 * rx + 1
    grid = np.full((ny, nx), -1.0, dtype=np.float64)
    for iy, dy in enumerate(range(-ry, ry + 1)):
        yy0, yy1 = cy + dy - h, cy + dy + h
        if yy0 < 0 or yy1 > f.shape[0]:
            continue
        for ix, dx in enumerate(range(-rx, rx + 1)):
            xx0, xx1 = cx + dx - w, cx + dx + w
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


def track_point(frames, idx_list, T0, cy0, cx0, ry=20, rx=25):
    """프레임열 idx_list(임의 순서, 보통 시간순)를 따라 템플릿 T0(1개, 고정)를 프레임간
    전파(이전 위치를 다음 탐색 중심으로) 방식으로 추적. 반환: dict(t_idx -> (y,x,score))."""
    out = {}
    cy, cx = cy0, cx0
    for i in idx_list:
        sc, iy, ix, grid, y0, x0 = ncc_search(frames[i], T0, int(round(cy)), int(round(cx)), ry, rx)
        dsy, dsx = parabolic_refine(grid, iy + ry, ix + rx)
        y_abs = y0 + (iy + ry) + dsy
        x_abs = x0 + (ix + rx) + dsx
        out[i] = (float(y_abs), float(x_abs), sc)
        cy, cx = y_abs, x_abs           # 다음 탐색 중심 갱신 (전파)
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
            diffs = np.diff(ys)
            med = float(np.median(diffs))
            if med < 20:
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
    diffs = np.diff(ys)
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

def locate_foot_seed(f, T_ref, y0, x0, ry=110, rx=170):
    sc, iy, ix, grid, gy0, gx0 = ncc_search(f, T_ref, y0, x0, ry, rx)
    cy, cx = y0 + iy, x0 + ix
    return cy, cx, sc


# ───────────────────────── main ─────────────────────────

def process_trial(day, fold, T_ref_foot, quiet=False):
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
    # 프레이밍이 trial마다 미세하게 다를 수 있음 — day-level 재사용시 배경패치 오정합 확인됨)
    cal_rep = calibrate_ruler(frames[f_bot])
    if cal_rep is None:
        return None, "줄자 판독 실패"

    # 발볼트 코스 위치: 바닥(f_bot) 프레임에서 27일 템플릿으로 광역 탐색
    cy, cx, e0 = locate_foot_seed(frames[f_bot], T_ref_foot, *FOOT_REF_2707)
    if e0 < 0.35:
        return None, f"발볼트 코스탐색 파탄 (ncc={e0:.2f})"
    T_own = frames[f_bot][int(cy) - 20:int(cy) + 20, int(cx) - 20:int(cx) + 20].copy()
    if T_own.shape != (40, 40):
        return None, "발볼트 템플릿 프레임 경계 초과"

    idx_list = list(range(f_bot, f_desc - 1, -1))     # 바닥→하강개시 (자기 템플릿 원점에서 역방향 전파)
    foot_trk = track_point(frames, idx_list, T_own, cy, cx, ry=18, rx=22)

    # 배경(카메라 흔들림) 기준점: 줄자 라벨 패치 (day-level calibrate_ruler의 bg_seed 재사용 —
    # 같은 날 전 trial 카메라 고정이므로 위치 재탐색 불필요, 템플릿만 이 trial 프레임에서 추출)
    bgy0, bgx0 = int(cal_rep["bg_seed"][0]), int(cal_rep["bg_seed"][1])
    if not (20 <= bgy0 < frames[f_bot].shape[0] - 20 and 20 <= bgx0 < frames[f_bot].shape[1] - 20):
        bg_trk = None
    else:
        T_bg = frames[f_bot][bgy0 - 20:bgy0 + 20, bgx0 - 20:bgx0 + 20].copy()
        bg_trk = track_point(frames, idx_list, T_bg, bgy0, bgx0, ry=12, rx=15)

    idx_sorted = sorted(foot_trk)
    t_arr = np.array([(i / fps + SH) for i in idx_sorted])
    x_raw = np.array([foot_trk[i][1] for i in idx_sorted])
    y_raw = np.array([foot_trk[i][0] for i in idx_sorted])
    q = np.array([foot_trk[i][2] for i in idx_sorted])
    if bg_trk is not None:
        xb = np.array([bg_trk[i][1] for i in idx_sorted])
        yb = np.array([bg_trk[i][0] for i in idx_sorted])
        qb = np.array([bg_trk[i][2] for i in idx_sorted])
        x_corr = x_raw - (xb - xb[0])
        y_corr = y_raw - (yb - yb[0])
        bg_shake_px = float(np.max(xb) - np.min(xb))
    else:
        x_corr = x_raw.copy(); y_corr = y_raw.copy()
        qb = np.full_like(q, np.nan)
        bg_shake_px = float("nan")

    good = q > 0.6
    n_good = int(good.sum())
    if n_good < 10:
        return None, f"추적 품질 미달 (good {n_good}/{len(q)})"

    tg, xg = t_arr[good], x_corr[good]
    A = np.vstack([tg, np.ones_like(tg)]).T
    slope, intercept = np.linalg.lstsq(A, xg, rcond=None)[0]
    dur = tg[-1] - tg[0]
    drift_fit_px = float(slope * dur)
    drift_end_px = float(np.median(xg[-3:]) - np.median(xg[:3]))
    rng_px = float(xg.max() - xg.min())
    resid = xg - (A @ [slope, intercept])
    quality = "good" if (n_good / len(q) > 0.85 and np.std(resid) < 1.5) else \
              ("marginal" if n_good / len(q) > 0.6 else "poor")

    scale_local = cal_rep["mm_per_px_local"]
    scale_global = cal_rep["mm_per_px_global"]
    res = dict(
        n_frames=int(len(q)), n_good=n_good, fps=fps, shift_ms=float(SH * 1e3),
        f_desc=f_desc, f_bot=f_bot,
        desc_drift_px=round(drift_fit_px, 2), desc_drift_px_endpoint=round(drift_end_px, 2),
        range_px=round(rng_px, 2),
        scale_mm_per_px=round(scale_local, 4), scale_mm_per_px_global=round(scale_global, 4),
        desc_drift_mm=round(drift_fit_px * scale_local, 3),
        desc_drift_mm_endpoint=round(drift_end_px * scale_local, 3),
        range_mm=round(rng_px * scale_local, 3),
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
                              "서브픽셀(NCC+포물선보간) 발볼트 추적 + 배경ROI 카메라흔들림 차감")}

    # 27일 발볼트 기준 템플릿 확보 (fs_video_gauge.py 좌표 재사용)
    ref_fold = ROOT / REF_DAY / "250_3_250_3"
    ref_mp4 = list(ref_fold.glob("*.mp4"))[0]
    ref_frames, ref_fps = load_frames(ref_mp4)
    jr = jump_frame_index(ref_frames)
    fy, fx = FOOT_REF_2707
    T_ref_foot = ref_frames[jr - 5][fy - 20:fy + 20, fx - 20:fx + 20].copy()

    for day in days:
        base = ROOT / day
        if not base.exists():
            print(f"{day}: 폴더 없음", flush=True)
            continue
        # 날짜 스케일 (대표 trial 첫 영상으로 확립, 해당 날짜 내 전 trial 공용 — 동일 카메라 고정)
        trials = FD.trials_of(base)
        if not trials:
            print(f"{day}: trial 없음", flush=True)
            continue
        cal_rep = None
        for t0 in trials:
            m0 = list(t0.glob("*.mp4"))
            if not m0:
                continue
            fr0, _ = load_frames(m0[0], max_frames=90)
            cal_rep = calibrate_ruler(fr0[min(60, len(fr0) - 1)])
            if cal_rep is not None:
                break
        if cal_rep is None:
            print(f"{day}: 줄자 판독 실패 — 스킵", flush=True)
            continue
        print(f"\n=== {day} === 스케일: 전역 {cal_rep['mm_per_px_global']:.4f}mm/px "
              f"| 국소(바닥측) {cal_rep['mm_per_px_local']:.4f}mm/px "
              f"(n라벨 {cal_rep['n_groups']}, cv {cal_rep['cv']:.3f})", flush=True)
        OUT[day] = {"_scale": cal_rep}
        for fold in trials:
            key = fold.name
            res, err = process_trial(day, fold, T_ref_foot, cal_rep)
            if err:
                print(f"  {key}: FAIL — {err}", flush=True)
                OUT[day][key] = dict(fail=err)
                continue
            print(f"  {key}: n={res['n_frames']}(good {res['n_good']}) drift {res['desc_drift_px']:+.2f}px "
                  f"={res['desc_drift_mm']:+.2f}mm (끝점 {res['desc_drift_px_endpoint']:+.1f}px) "
                  f"범위 {res['range_px']:.1f}px | bg흔들림 {res['bg_shake_px']}px | ncc {res['ncc_mean']:.2f} "
                  f"| {res['quality']}", flush=True)
            OUT[day][key] = res

    outp = HERE / "_F_videoslip.json"
    safe.atomic_json_write(outp, OUT)
    print(f"\ndone -> {outp}")


if __name__ == "__main__":
    main()
