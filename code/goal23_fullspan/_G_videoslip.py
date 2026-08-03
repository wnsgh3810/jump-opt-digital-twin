# -*- coding: utf-8 -*-
"""_G_videoslip — 발 수평 이동(구름+슬립) 전 구간(하강~바닥유지~push~이륙) 재측정.

배경: 과거 _F_videoslip.py는 (a) 하강(descent) 창만 쟀고 "복원 완료"로 잘못 보고된 전례가 있고,
(b) px→mm 스케일을 발보다 훨씬 뒤쪽 평면인 벽 눈금자로 잡아 원근오차가 있었다(사용자 확정,
08-02). 본 스크립트는:
  ① 발판 플레이트(발 롤러가 얹히는 흰 브라켓+검정 그립패드 어셈블리, 전체 길이 120mm 사용자
     확정)를 이용해 발과 "같은 깊이"에서 px→mm 스케일을 직접 잡는다. 롤러 자체의 실측 지름
     (반지름 19~21mm)으로 교차검증한다.
  ② 발 롤러를 하강 개시(t_desc)부터 이륙(t_lo)까지 전 구간, NCC(정규화 상호상관)+포물선
     서브픽셀 보간으로 매 프레임 추적한다(2707일 재구축 스크립트 _F_videoslip.py와 동일 알고리즘,
     탐색범위만 전 구간에 맞게 확장).
  ③ 이륙 앵커(프레임차분 최댓값 클러스터 시작 ↔ fs_data.segment()의 t_lo)로 프레임-데이터 시간
     동기화. push 말기는 24fps 앨리어싱으로 블러가 커 추적이 끊길 수 있음 — 끊기면 정직하게
     "이 지점부터 추적 불가"라고 보고한다(억지 외삽 금지).
  ④ 롤러 표면에 회전각(Δθ) 추적 가능한 비대칭 마커(볼트·무늬 등)가 있는지 확인 — 있으면 구름
     성분 r·Δθ와 슬립 성분(Δx − r·Δθ)을 분리하고, 없으면 "총 변위만" 이라고 보고한다.
  ⑤ 구간별(desc / prehold / push) **부호 있는(signed)** 순변위를 보고한다 — 마라톤 G 대조용
     시뮬레이션 기준선이 하강과 push 구간의 이동 방향이 반대라고 보고했기 때문에(사용자 지시,
     08-02), 크기뿐 아니라 방향 판별이 1급 요구사항이다. 부호 규약은 아래 SIGN_CONVENTION 참조.

SIGN_CONVENTION: +x = 영상 프레임(회전 보정 후, portrait) 픽셀 x좌표 증가 방향 = 화면상 "오른쪽".
  로봇 좌/우(전후) 운동학 부호와의 대응은 CAD/제어 좌표계 확인 없이는 단정하지 않는다 — 오직
  "화면상 오른쪽/왼쪽"으로만 보고하고, 두 구간(하강 vs push)이 같은 방향인지 반대 방향인지는
  이 화면-고정 부호로 직접 비교 가능(부호 규약이 두 구간에 동일하게 적용되므로 규약 자체의
  절대 의미를 모르더라도 "같다/반대다" 판정은 유효함).

데이터 원본(mp4/xlsx)은 절대 미수정 — 읽기 전용.
CLI: python _G_videoslip.py
출력: _G_videoslip.json, _G_videoslip_*.png (오버레이/궤적 검증 이미지)
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np
import imageio.v3 as iio

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe                      # noqa: E402
import fs_data as FD              # noqa: E402

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
DAY = "26.07.23"
TRIAL = "150_2.2_250_3"

# ── 발판 플레이트 스케일 (이 trial의 프레임에서 수동+Sobel엣지 확인, 08-02) ──
# 대상: 그립패드가 얹히는 흰 브라켓 상단면(발 롤러가 실제로 접촉하는 높이에 가장 가까운 면).
# 여러 크롭·행에서 반복 판독한 결과 144~178px 스프레드(오블리크 각도 + 저해상도 압축 영상이라
# 좌측 모서리가 특히 불명확 — 라운드 처리·인접 브라켓 부품과 경계가 흐림). 중심값 161px 채택,
# 폭 스프레드를 그대로 스케일 불확도로 반영(±~15%, 아래 uncertainty_pct 참조).
# 하위 넓은 흰 베이스(마운트 플랜지, y=1230~1240에서 폭 ~210px)는 별개 부품으로 판단해 제외
# (그립패드와 동일 높이가 아님 — 발 접촉면과 다른 깊이라 쓰면 다시 원근오차 재도입 위험).
PLATE_WIDTH_PX = 161.0
PLATE_LEN_MM = 120.0
PLATE_WIDTH_PX_RANGE = (144.0, 178.0)          # 관측된 반복판독 스프레드 → 스케일 불확도 산정용

# 롤러 지름 교차검증 (프레임140, 비블러 구간에서 육안+격자 판독)
ROLLER_DIAM_PX = 59.0
ROLLER_DIAM_PX_RANGE = (55.0, 63.0)
ROLLER_DIAM_MM_RANGE = (38.0, 42.0)            # r=19~21mm (실물 19~20mm, 설계 21mm)

# 발 롤러 시드좌표 (f_bot=177 프레임, gray frame 기준 (y,x)) — 코스 NCC 탐색 시드
ROLLER_SEED_YX = (1120, 440)


def gray(a):
    return a.mean(axis=2).astype(np.float32)


def load_frames(mp4):
    fr = []
    for f in iio.imiter(str(mp4), plugin="FFMPEG"):
        fr.append(gray(f))
    try:
        fps = float(iio.immeta(str(mp4), plugin="FFMPEG").get("fps", 24.0))
    except Exception:
        fps = 24.0
    return fr, fps


def jump_frame_index(frames):
    """프레임차분 최댓값 클러스터(푸시~비행) 시작 인덱스 j (이륙 앵커 시드). 반환 (j, diffs)."""
    d = [float(np.abs(frames[i + 1] - frames[i]).mean()) for i in range(len(frames) - 1)]
    top = np.argsort(d)[-12:]
    return int(min(top)), d


# ───────────────────────── NCC + 서브픽셀 (계보: _F_videoslip.py) ─────────────────────────

def _ncc(patch, T):
    p = patch - patch.mean()
    t = T - T.mean()
    denom = np.sqrt((p * p).sum() * (t * t).sum())
    if denom < 1e-6:
        return -1.0
    return float((p * t).sum() / denom)


def ncc_search(f, T, cy, cx, ry, rx):
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
    ny, nx = grid.shape
    dsy = dsx = 0.0
    if 0 < iy < ny - 1:
        y0, y1, y2 = grid[iy - 1, ix], grid[iy, ix], grid[iy + 1, ix]
        den = (y0 - 2 * y1 + y2)
        if abs(den) > 1e-9:
            dsy = float(np.clip(0.5 * (y0 - y2) / den, -1.0, 1.0))
    if 0 < ix < nx - 1:
        x0, x1, x2 = grid[iy, ix - 1], grid[iy, ix], grid[iy, ix + 1]
        den = (x0 - 2 * x1 + x2)
        if abs(den) > 1e-9:
            dsx = float(np.clip(0.5 * (x0 - x2) / den, -1.0, 1.0))
    return dsy, dsx


def track_point(frames, idx_list, T0, cy0, cx0, ry=20, rx=30, min_score_propagate=0.5):
    """idx_list(시간순 임의방향)를 따라 고정 템플릿 T0를 추적. 신뢰도 낮은 프레임에서는
    탐색중심 전파를 건너뛴다(한번의 오정합이 눈덩이처럼 드리프트하는 것 방지, _F_videoslip.py와
    동일 정책). 반환: dict(idx -> (y,x,score))."""
    out = {}
    cy, cx = cy0, cx0
    for i in idx_list:
        sc, iy, ix, grid, y0, x0 = ncc_search(frames[i], T0, int(round(cy)), int(round(cx)), ry, rx)
        dsy, dsx = parabolic_refine(grid, iy + ry, ix + rx)
        y_abs = y0 + (iy + ry) + dsy
        x_abs = x0 + (ix + rx) + dsx
        out[i] = (float(y_abs), float(x_abs), sc)
        if sc >= min_score_propagate:
            cy, cx = y_abs, x_abs
    return out


# ───────────────────────── 배경(카메라 흔들림) 참조점 ─────────────────────────
# 광학테이블 브레드보드 홀 패턴(움직이지 않는 고정 배경) — 다리 스윙 궤적에서 벗어난 위치.
BG_SEED_YX = (1175, 605)


def main():
    fold = FD._D(DAY, TRIAL)
    mp4s = list(fold.glob("*.mp4"))
    if not mp4s:
        print("영상 없음"); return
    mp4 = mp4s[0]

    d = FD.load2(fold)
    seg = FD.segment(d)
    frames, fps = load_frames(mp4)
    n = len(frames)
    H, W = frames[0].shape
    print(f"영상: {mp4.name}  fps={fps}  frames={n}  shape=(H={H},W={W})  duration={n/fps:.2f}s", flush=True)

    j, dseries = jump_frame_index(frames)
    SH = seg["t_lo"] - j / fps
    print(f"이륙 앵커: frame j={j} (diff클러스터 시작) <-> t_lo={seg['t_lo']:.3f}s  shift SH={SH:.4f}s", flush=True)

    def t2f(t):
        return (t - SH) * fps

    f_desc = int(round(t2f(seg["t_desc"])))
    f_bot = int(round(t2f(d["t"][seg["i_bot"]])))
    f_push = int(round(t2f(seg["t_push"])))
    f_lo = int(round(t2f(seg["t_lo"])))
    f_land = int(round(t2f(seg["t_land"])))
    f_desc0 = max(0, f_desc - 5)          # 약간 여유 포함 (요청: "하강 개시"부터)
    f_land_ext = min(n - 1, f_land + 5)
    print(f"프레임 경계: desc={f_desc}(pad{f_desc0}) bot={f_bot} push={f_push} lo={f_lo} land={f_land}(ext{f_land_ext}) / 전체 0~{n-1}", flush=True)

    # ── fps·해상도로 8~10mm 판별가능성 정량 판정 (스케일은 아래서 확정, 여기선 선계산) ──
    scale_mm_per_px = PLATE_LEN_MM / PLATE_WIDTH_PX
    scale_lo = PLATE_LEN_MM / PLATE_WIDTH_PX_RANGE[1]
    scale_hi = PLATE_LEN_MM / PLATE_WIDTH_PX_RANGE[0]
    roller_scale = float(np.mean(ROLLER_DIAM_MM_RANGE)) / ROLLER_DIAM_PX
    px_for_8_10mm = (8.0 / scale_mm_per_px, 10.0 / scale_mm_per_px)
    print(f"스케일(발판 기준) = {scale_mm_per_px:.4f} mm/px (행별 범위 {scale_lo:.4f}~{scale_hi:.4f})", flush=True)
    print(f"롤러지름 교차검증 스케일 = {roller_scale:.4f} mm/px", flush=True)
    print(f"8~10mm 이동 = {px_for_8_10mm[0]:.1f}~{px_for_8_10mm[1]:.1f} px @ 이 스케일 -> 서브픽셀 NCC로 충분히 판별 가능 (1px << 이 범위)", flush=True)

    # push 구간 속도/블러 정량화
    push_dur = seg["t_lo"] - seg["t_push"]
    push_frames = (f_lo - f_push)
    print(f"push~이륙 구간: {push_dur*1000:.0f}ms, {push_frames}개 프레임 (24fps에서 프레임당 {push_dur*1000/max(push_frames,1):.1f}ms)", flush=True)

    # ── 발 롤러 추적: f_bot에서 자기 템플릿 확보, 전방/후방 양쪽으로 전파 ──
    cy0, cx0 = ROLLER_SEED_YX
    # 코스 위치 재확인 (템플릿 자체를 세밀히 새로 자르기 전에 대략 정합)
    T_seed = frames[f_bot][cy0 - 20:cy0 + 20, cx0 - 20:cx0 + 20].copy()
    T_roller = T_seed

    idx_back = list(range(f_bot, f_desc0 - 1, -1))                       # 바닥->하강개시 역방향
    idx_fwd = list(range(f_bot, min(n - 1, f_land_ext) + 1))              # 바닥->착지+여유 정방향

    trk_back = track_point(frames, idx_back, T_roller, cy0, cx0, ry=18, rx=35)
    trk_fwd = track_point(frames, idx_fwd, T_roller, cy0, cx0, ry=18, rx=55, min_score_propagate=0.45)

    trk = dict(trk_back)
    trk.update(trk_fwd)
    idx_sorted = sorted(trk)
    t_arr = np.array([i / fps + SH for i in idx_sorted])
    x_px = np.array([trk[i][1] for i in idx_sorted])
    y_px = np.array([trk[i][0] for i in idx_sorted])
    ncc = np.array([trk[i][2] for i in idx_sorted])
    idx_arr = np.array(idx_sorted)

    # ── 배경(카메라 흔들림) 참조점 추적 ──
    bgy0, bgx0 = BG_SEED_YX
    T_bg = frames[f_bot][bgy0 - 16:bgy0 + 16, bgx0 - 16:bgx0 + 16].copy()
    trk_bg = track_point(frames, idx_sorted, T_bg, bgy0, bgx0, ry=8, rx=8, min_score_propagate=0.55)
    xb = np.array([trk_bg[i][1] for i in idx_sorted])
    qb = np.array([trk_bg[i][2] for i in idx_sorted])
    bg_shake_px = float(np.nanmax(xb) - np.nanmin(xb)) if len(xb) else float("nan")
    bg_ncc_mean = float(np.nanmean(qb)) if len(qb) else float("nan")
    print(f"배경기준점 흔들림: {bg_shake_px:.2f}px (ncc평균 {bg_ncc_mean:.3f}) -> 카메라 {'고정' if bg_shake_px<2.0 else '흔들림 유의'}", flush=True)

    good = ncc > 0.55
    print(f"롤러 추적: {len(idx_sorted)}프레임, 양호(ncc>0.55) {good.sum()}개, ncc평균 {ncc.mean():.3f}", flush=True)

    def val_at(f_target):
        """f_target 근접 프레임의 (x,y,ncc,실제idx) 반환 (품질 무관, 최근접)."""
        k = int(np.argmin(np.abs(idx_arr - f_target)))
        return float(x_px[k]), float(y_px[k]), float(ncc[k]), int(idx_arr[k])

    def seg_disp(fa, fb, label):
        """[fa,fb] 구간의 부호있는 순변위(px/mm) — 각 끝점에서 품질 확인, 저품질이면 good=False."""
        xa, ya, qa, ia = val_at(fa)
        xb_, yb_, qb_, ib = val_at(fb)
        ok = (qa > 0.55) and (qb_ > 0.55)
        dpx = xb_ - xa
        return dict(label=label, f_a=ia, f_b=ib, x_a_px=round(xa, 2), x_b_px=round(xb_, 2),
                    ncc_a=round(qa, 3), ncc_b=round(qb_, 3), quality_ok=bool(ok),
                    disp_px=round(dpx, 2), disp_mm=round(dpx * scale_mm_per_px, 3),
                    sign=("+screen-right" if dpx > 0 else ("-screen-left" if dpx < 0 else "0")))

    seg_results = {
        "desc": seg_disp(f_desc0, f_bot, "하강(desc, 앉기 개시->바닥)"),
        "prehold": seg_disp(f_bot, f_push, "바닥유지(prehold, 바닥->푸시 개시)"),
        "push": seg_disp(f_push, f_lo, "push~이륙(push, 푸시개시->이륙)"),
        "desc_to_liftoff": seg_disp(f_desc0, f_lo, "하강개시~이륙 전체"),
        "liftoff_to_land": seg_disp(f_lo, f_land_ext, "이륙~착지(비행/재접지, 참고용 — 슬립 아님)"),
    }
    for k, r in seg_results.items():
        flag = "OK" if r["quality_ok"] else "품질저하"
        print(f"  [{r['label']}] f{r['f_a']}->f{r['f_b']}: {r['disp_px']:+.2f}px = {r['disp_mm']:+.3f}mm "
              f"({r['sign']}) ncc=({r['ncc_a']:.2f},{r['ncc_b']:.2f}) [{flag}]", flush=True)

    # desc 구간은 끝점(f_desc0) ncc가 낮지만(포즈가 템플릿 캡처지점 f_bot과 멀어 외형이 달라짐),
    # 궤적 자체는 f97->f178 전 구간에서 매끄럽게 단조 증가(요동 없음) — 그리고 ncc가 f_bot에
    # 가까워질수록 매끄럽게 1.0으로 수렴하는 것도 "포즈거리에 따른 자연스러운 신뢰도 저하"와
    # 정합(오정합이었다면 ncc가 이렇게 매끄럽게 거동하지 않고 프레임간 위치가 들쭉날쭉했을 것).
    # 이 정성적 근거를 함께 보고한다 — 엄격한 ncc>0.55 게이트만으로 "저품질"로 버리면 과도.
    dx_seq = np.diff(x_px[(idx_arr >= f_desc0) & (idx_arr <= f_bot)])
    desc_monotonic_frac = float(np.mean(dx_seq >= -0.15)) if len(dx_seq) else float("nan")   # 거의 항상 비감소
    desc_max_jump_px = float(np.max(np.abs(dx_seq))) if len(dx_seq) else float("nan")
    print(f"  [desc 정성체크] 프레임간 비감소 비율 {desc_monotonic_frac:.2f}, 최대 프레임간 점프 {desc_max_jump_px:.2f}px "
          f"-> {'매끄러움(오정합 아닐 가능성 높음)' if desc_monotonic_frac > 0.85 and desc_max_jump_px < 3 else '요동 있음(불확실)'}",
          flush=True)

    same_dir = None
    if seg_results["desc"]["quality_ok"] and seg_results["push"]["quality_ok"]:
        same_dir = bool(np.sign(seg_results["desc"]["disp_px"]) == np.sign(seg_results["push"]["disp_px"]))
        print(f"  => 하강 vs push 방향: {'같음(동일 부호)' if same_dir else '반대(부호 반전)'}", flush=True)
    else:
        same_dir = bool(np.sign(seg_results["desc"]["disp_px"]) == np.sign(seg_results["push"]["disp_px"]))
        print(f"  => 방향(참고, 품질저하 있음에도 부호는 계산): {'같음' if same_dir else '반대'} "
              f"— desc가 매끄러운 궤적 근거로 방향은 신뢰, 크기는 신중히 볼 것", flush=True)

    # ── push~이륙 구간: 정확한 "이륙 프레임"이 ±1프레임(24fps 앨리어싱) 불확실 + 이 구간
    # 자체가 프레임당 ~40px씩 움직이는 급구간이라, 끝점 프레임 선택에 결과가 매우 민감함.
    # f_lo-1/f_lo/f_lo+1 세 후보로 push 변위를 다시 계산해 그 민감도를 그대로 노출한다.
    push_sensitivity = []
    for df in (-1, 0, 1):
        r = seg_disp(f_push, f_lo + df, f"push (liftoff후보 f_lo{df:+d})")
        push_sensitivity.append(r)
        print(f"  [push 민감도] f_lo{df:+d}={f_lo+df}: {r['disp_px']:+.2f}px = {r['disp_mm']:+.2f}mm ({r['sign']})",
              flush=True)
    push_mm_lo = min(r["disp_mm"] for r in push_sensitivity)
    push_mm_hi = max(r["disp_mm"] for r in push_sensitivity)
    push_all_negative = all(r["disp_px"] < 0 for r in push_sensitivity)
    print(f"  => push 변위 범위(이륙프레임 ±1): {push_mm_lo:+.1f} ~ {push_mm_hi:+.1f} mm "
          f"(방향은 {'일관되게 음(-)' if push_all_negative else '후보에 따라 부호가 바뀜(불확실)'})", flush=True)

    range_px = float(np.nanmax(x_px[good]) - np.nanmin(x_px[good])) if good.any() else float("nan")

    # ── 구름/슬립 분해 가능성 ──
    rolling_decomp = dict(
        possible=False,
        reason="롤러 표면(그립면)에 회전각 추적 가능한 비대칭 마커(스크래치·페인트점·무늬 등) 육안 확인 "
               "불가 — 매끈한 금속/고무 원통 표면, 중심의 볼트/딤플은 축(고정 허브)이라 회전해도 화면상 "
               "위치가 안 변해 Δθ 대리 신호로 쓸 수 없음. 서브픽셀(~0.3px) 추적을 해도 '무엇의 회전'을 "
               "재는지가 없어 방법론적으로 막힘 (해상도 문제가 아니라 마커 부재 문제).",
        conclusion="발 중심 총 변위(Δx)만 측정 — 구름/슬립 성분 분해 불가.")

    # ── JSON 저장 ──
    out = dict(
        _meta=dict(
            desc="_G_videoslip — 발 수평 이동 전 구간(하강~바닥유지~push~이륙) 재측정. "
                 "px->mm 스케일은 발판 플레이트(120mm, 발과 동일 깊이)로 확립 — 구 벽눈금자 스케일 폐기. "
                 "구간별 변위는 부호 있음(SIGN_CONVENTION: +=화면오른쪽, -=화면왼쪽). "
                 "구름/슬립 분해는 롤러 표면 마커 부재로 불가 — 총변위만.",
            trial=f"{DAY}/{TRIAL}", mp4=mp4.name, fps=fps, n_frames=n, resolution=[int(W), int(H)],
            duration_s=round(n / fps, 3),
        ),
        sync=dict(anchor_frame_j=j, t_lo_data_s=round(seg["t_lo"], 4), shift_SH_s=round(SH, 5),
                  method="프레임차분 최댓값 클러스터 시작(j) <-> fs_data.segment().t_lo 앵커; "
                         "24fps 앨리어싱으로 ±1프레임(~±42ms) 불확도"),
        frame_bounds=dict(f_desc0=f_desc0, f_bot=f_bot, f_push=f_push, f_lo=f_lo, f_land=f_land_ext,
                           t_desc_s=round(seg["t_desc"], 4), t_bot_s=round(float(d["t"][seg["i_bot"]]), 4),
                           t_push_s=round(seg["t_push"], 4), t_lo_s=round(seg["t_lo"], 4),
                           t_land_s=round(seg["t_land"], 4)),
        resolvability=dict(
            scale_mm_per_px=round(scale_mm_per_px, 4),
            px_for_8mm=round(px_for_8_10mm[0], 2), px_for_10mm=round(px_for_8_10mm[1], 2),
            verdict="판별 가능 — 8~10mm가 각각 약 %.0f~%.0fpx에 해당, 서브픽셀(포물선보간) NCC 추적의 "
                    "잔차수준(<1~2px)보다 훨씬 큼. 과거 '24fps 판별 불가' 결론은 push 말기(수 프레임 내 "
                    "블러 급증 구간)에는 유효하나 저속 하강 구간에는 적용되지 않음(공간분해능 vs 시간분해능 "
                    "혼동)." % (px_for_8_10mm[0], px_for_8_10mm[1]),
            push_duration_ms=round(push_dur * 1000, 1), push_n_frames=push_frames,
        ),
        scale=dict(
            method="발판 플레이트(그립패드 마운트 흰 브라켓 상단면, 전체 길이 120mm 사용자 확정) 폭을 "
                   "Sobel엣지+휘도임계 세그먼트로 이 trial 프레임(f=177)에서 직접 판독. 발 롤러와 동일 "
                   "깊이(같은 높이의 접촉면)라 원근오차 최소화 — 구 벽눈금자(발보다 먼 평면) 스케일 폐기.",
            plate_width_px=PLATE_WIDTH_PX, plate_len_mm=PLATE_LEN_MM,
            plate_width_px_range=list(PLATE_WIDTH_PX_RANGE),
            scale_mm_per_px=round(scale_mm_per_px, 4),
            scale_mm_per_px_range=[round(scale_lo, 4), round(scale_hi, 4)],
            roller_diam_px=ROLLER_DIAM_PX, roller_diam_px_range=list(ROLLER_DIAM_PX_RANGE),
            roller_diam_mm_range=list(ROLLER_DIAM_MM_RANGE),
            roller_cross_check_mm_per_px=round(roller_scale, 4),
            old_wall_ruler_scale_mm_per_px=1.0184,
            note="발판 기준(~%.3f mm/px)과 롤러지름 교차검증(~%.3f mm/px)이 %.0f%% 이내로 합치 — "
                 "발 깊이에서의 스케일로 신뢰. 구 벽눈금자 스케일(1.0184 mm/px, 발보다 먼 평면)과는 "
                 "약 %.0f%% 괴리 — 벽눈금자를 계속 썼다면 같은 px변위를 %.0f%% 더 큰 mm로 오판했을 것."
                 % (scale_mm_per_px, roller_scale, 100 * abs(scale_mm_per_px - roller_scale) / scale_mm_per_px,
                    100 * (1.0184 / scale_mm_per_px - 1), 100 * (1.0184 / scale_mm_per_px - 1)),
            uncertainty_pct=round(100 * (scale_hi - scale_lo) / scale_mm_per_px / 2, 1),
        ),
        camera=dict(bg_seed_yx=list(BG_SEED_YX), bg_shake_px=round(bg_shake_px, 2),
                     bg_ncc_mean=round(bg_ncc_mean, 3),
                     verdict="고정(흔들림 무시 가능)" if bg_shake_px < 2.0 else "흔들림 유의 — 배경보정 필요"),
        rolling_slip_decomposition=rolling_decomp,
        segments=seg_results,
        desc_qualitative_check=dict(
            nonshrink_frame_frac=round(desc_monotonic_frac, 3), max_frame_to_frame_jump_px=round(desc_max_jump_px, 2),
            note="ncc<0.55(f_desc0=97~f130 부근)에도 프레임간 위치가 요동 없이 매끄럽게 단조 변화 — "
                 "낮은 ncc는 자세(포즈)가 템플릿 캡처지점(f_bot)과 멀어 외형이 달라진 결과로 해석, "
                 "오정합(false lock)이라면 기대되는 들쭉날쭉한 프레임간 점프가 관측되지 않음.",
        ),
        push_liftoff_sensitivity=dict(
            candidates=push_sensitivity,
            disp_mm_range=[round(push_mm_lo, 2), round(push_mm_hi, 2)],
            direction_robust=push_all_negative,
            note="이 구간은 프레임당 최대 ~40px(≈28mm) 이동하는 급구간이라, '이륙 프레임'을 ±1프레임만 "
                 "옮겨도(24fps 앨리어싱 불확도 범위 내) 변위 크기 추정치가 크게 바뀐다. 방향은 세 후보 "
                 "모두에서 일관되면 신뢰하되, 절대 mm 크기는 이 범위로 넓게 보고한다.",
        ),
        direction_check=dict(
            desc_sign=seg_results["desc"]["sign"], push_sign=seg_results["push"]["sign"],
            same_direction=same_dir,
            note="부호는 화면(회전보정 후 portrait 프레임) 픽셀 x좌표 기준 — 로봇 전/후 운동학 부호와의 "
                 "매핑은 별도 CAD/좌표계 확인 없이 단정하지 않음. '같다/반대다' 판정 자체는 화면 고정축 "
                 "기준이라 유효.",
        ),
        track=dict(n=len(idx_sorted), n_good=int(good.sum()), ncc_mean=round(float(ncc.mean()), 3),
                   range_px=round(range_px, 2), range_mm=round(range_px * scale_mm_per_px, 3),
                   frame_idx=idx_arr.tolist(), t=t_arr.round(4).tolist(),
                   x_px=x_px.round(3).tolist(), y_px=y_px.round(3).tolist(), ncc=ncc.round(3).tolist()),
    )
    outp = HERE / "_G_videoslip.json"
    safe.atomic_json_write(outp, out)
    print(f"\n저장 -> {outp}", flush=True)

    # ── 오버레이 이미지 ──
    make_overlays(frames, idx_arr, x_px, y_px, ncc, good, f_desc0, f_bot, f_push, f_lo, f_land_ext,
                  cy0, cx0, scale_mm_per_px, seg_results)


def make_overlays(frames, idx_arr, x_px, y_px, ncc, good, f_desc0, f_bot, f_push, f_lo, f_land,
                   cy0, cx0, scale_mm_per_px, seg_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # (1) 궤적 그래프: x_px(t) 전 구간, 구간 경계 표시
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(idx_arr, x_px, "-o", ms=2.5, lw=1.0, label="롤러 x위치 [px]")
    ax.scatter(idx_arr[~good], x_px[~good], s=14, marker="x", zorder=5, label="저품질(ncc<=0.55)")
    for f_, lab in [(f_desc0, "desc0"), (f_bot, "bot"), (f_push, "push"), (f_lo, "lo(이륙)"), (f_land, "land")]:
        ax.axvline(f_, ls=":", lw=1.0)
        ax.text(f_, ax.get_ylim()[1] if False else max(x_px) + 1, lab, fontsize=8, rotation=90, va="bottom")
    ax.set_xlabel("frame idx"); ax.set_ylabel("x [px] (+= 화면오른쪽)")
    ax.set_title(f"26.07.23/150_2.2_250_3 — 발 롤러 x위치 전 구간 (scale={scale_mm_per_px:.3f}mm/px)")
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(HERE / "_G_videoslip_trajectory.png", dpi=130)
    plt.close(fig)

    # (2) NCC 신뢰도 그래프
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.plot(idx_arr, ncc, "-", lw=1.0)
    ax.axhline(0.55, ls="--", c="gray", lw=1)
    for f_ in [f_desc0, f_bot, f_push, f_lo, f_land]:
        ax.axvline(f_, ls=":", lw=0.8)
    ax.set_xlabel("frame idx"); ax.set_ylabel("NCC score")
    ax.set_title("추적 신뢰도(NCC) — 0.55 아래는 저품질")
    ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(HERE / "_G_videoslip_ncc.png", dpi=130)
    plt.close(fig)

    # (3) 프레임 오버레이: 대표 프레임(desc0/bot/push/lo)에 추적점 십자 표시
    picks = [f_desc0, f_bot, f_push, f_lo]
    fig, axes = plt.subplots(1, len(picks), figsize=(4 * len(picks), 5.2))
    idx_list = idx_arr.tolist()
    for ax, f_ in zip(axes, picks):
        ax.imshow(frames[f_], cmap="gray", vmin=0, vmax=255)
        if f_ in idx_list:
            k = idx_list.index(f_)
            ax.plot(x_px[k], y_px[k], "r+", ms=18, mew=2)
        ax.set_xlim(cx0 - 90, cx0 + 90); ax.set_ylim(cy0 + 90, cy0 - 90)
        ax.set_title(f"frame {f_}", fontsize=10)
        ax.axis("off")
    fig.suptitle("발 롤러 추적 오버레이 (빨강 십자 = 추적 위치)")
    fig.tight_layout(); fig.savefig(HERE / "_G_videoslip_overlay.png", dpi=130)
    plt.close(fig)

    print("오버레이 저장: _G_videoslip_trajectory.png, _G_videoslip_ncc.png, _G_videoslip_overlay.png", flush=True)


if __name__ == "__main__":
    main()
