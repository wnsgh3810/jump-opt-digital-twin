# -*- coding: utf-8 -*-
"""fs_vidscale — **영상 px→mm 스케일의 정본**: 발 롤러 지름을 자로 쓴다 (마라톤G, 08-08 확립).

왜 발 롤러인가 (사용자 제안 08-08, 확정)
  영상에서 길이를 재려면 "화면 몇 px = 실제 몇 mm" 라는 **자**가 필요하다. 카메라가 살짝
  기울고 피사체마다 **깊이(거리)** 가 다르면, 먼 물체를 자로 쓸수록 원근 왜곡이 커진다.
  우리가 재려는 대상은 **발 롤러의 수평 이동**이다. 그러면 자도 **발 롤러 자신**이 최선이다 —
    · 깊이가 정확히 같다 (같은 물체) → 원근 배율 오차 **0**
    · 원이라 카메라가 기울어도 지름은 불변
    · 기준 길이가 실측 확정값: **바깥 40.0mm = 금속판 30.0mm + 고무 5.0mm×2** (08-08)
  비유: 사진 속 물건 크기를 잴 때 옆에 놓인 동전을 자로 쓰는 것과 같다. 단, 동전이 물건보다
  훨씬 앞/뒤에 있으면 틀린다 — 그래서 "물건 자신"을 자로 쓴다.

★★ 철칙: **스케일은 영상마다 그 영상 자체에서 잰다** (사용자 지시 08-08) ★★
  카메라 거리·줌·해상도가 세션마다 다르므로 발 px 지름도 다르다. **다른 trial 의 mm/px 를
  가져다 쓰는 것은 금지.** `scale_of()` 는 등재 없으면 그 trial 의 mp4 에서 직접 잰다.

폐기된 자 (전부 이 모듈 이전의 것)
  · 벽 눈금자 — 발보다 먼 평면 (마라톤F 이전)
  · **발판 플레이트 120mm** — `_G_videoslip.json` 이 쓰던 자, 0.7453 mm/px. 이 자로는 금속판이
    **24.1 mm** (실측 30.0 대비 −20%). 판독 범위도 144~178px(±10%) 로 넓었다. **전 결과 무효.**
  · 은색 판 25mm 구멍 격자 — 자기상관 검증 실패(lag33 피크 없음, 상관 −0.176). **폐기.**
  · 가로 띠 밝기 임계 — 롤러가 **밝고 배경이 어둡다**. 링크·그림자에 오염돼 26~56px 로 요동. **폐기.**

정본 측정법 `fit_roller()` — 방사 기울기 원 맞춤
  ★ 잡히는 경계는 **금속판(밝음)/고무(어두움)** 이다 — 고무 바깥은 검은 그립패드와
  명암차가 없어 안 잡힌다. 중심 후보와 반지름 r 을 훑으면서
  **안쪽(r−2px) 밝기 − 바깥쪽(r+2px) 밝기** 를 각도 평균해 최대가 되는 (cx,cy,r) 을 고른다.
  각도는 **95°~290°(좌·하)** 만 쓴다 — 오른쪽 위는 종아리 링크가 롤러를 가리기 때문.
  프레임마다 재고 **중앙값**을 취한다 (한 프레임의 모션블러에 흔들리지 않게).

26.07.23/150_2.2_250_3 결과:  금속판 **32.50 px** = 30.0 mm  →  **0.9231 mm/px**
  (구 0.7453 대비 **1.242배** — 기존 영상 슬립 수치는 전부 1.242 를 곱해야 한다)
  교차검증: 골격 겹침(종아리 250mm CAD) 0.92 · 벽 눈금자 1.03 — 모두 정합

CLI:  python fs_vidscale.py                      # 등재 trial 자가검증
      python fs_vidscale.py <mp4> <f> <cx> <cy>  # 새 영상 교정
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent

# ── 실측 상수 (사용자 확인 08-08) ────────────────────────────────────────────
#   발 롤러 = 안쪽 금속 원판 + 그 둘레의 고무 테두리
FOOT_DIA_MM = 40.0                  # **바깥 지름** (고무 포함) = 접지 반경의 2배
RUBBER_MM = 5.0                     # 고무 두께 (반경 방향)
METAL_DIA_MM = 30.0                 # **안쪽 금속 원판 지름** = 40 − 2×5 ✔
FOOT_R_M = FOOT_DIA_MM / 2000.0     # 0.020 m

# ★ `fit_roller` 가 잡는 것은 **금속 원판**(밝음)과 고무(어두움)의 경계다.
#   고무 바깥 가장자리는 배경(검은 그립패드)과 명암차가 없어 잡히지 않는다.
#   그러므로 **스케일 = METAL_DIA_MM / 측정 지름 px**.  (초기에 이걸 바깥 지름으로
#   착각해 42/32.4 = 1.296 을 썼다가 골격 겹침 검증에서 무릎이 한참 못 미쳐 발각됨.)

SECTOR = (95.0, 290.0)              # 가려지지 않은 좌·하 원호 [deg]
R_RANGE = (9.0, 26.0, 0.1)          # 반지름 탐색 [px]
EDGE_D = 2.0                        # 안/바깥 표본 간격 [px]

# trial 별 **그 영상에서 잰** 지름. 새 trial 은 calibrate() 로 등재.
FOOT_CAL = {
    ("26.07.23", "150_2.2_250_3"): dict(
        mp4="KakaoTalk_20260723_165554947.mp4", frames=(96, 199), seed=(421.0, 1138.0),
        dia_px=32.50, dia_px_iqr=(31.40, 33.60),
        note="금속 원판(30mm) 지름. 방사 기울기 원 맞춤 105프레임 중앙값 · "
             "골격 겹침(종아리 250mm CAD)과 벽 눈금자로 교차검증"),
}


def _gray(f):
    a = np.asarray(f, float)
    return a if a.ndim == 2 else a[..., :3].mean(axis=2)


def _samp(g, x, y):
    """쌍선형 보간 (서브픽셀). 경계 밖은 클립 (전역 탐색 시 IndexError 방지)."""
    H, W = g.shape
    x = np.clip(x, 0.0, W - 2.001); y = np.clip(y, 0.0, H - 2.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy)
            + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy)


def fit_roller(frame, cx0, cy0, *, sector=SECTOR, rrange=R_RANGE, d=EDGE_D, win=5.0, step=1.0,
               refine=0.1, win_y=None):
    """한 프레임에서 롤러 원을 맞춘다 → (score, cx, cy, r) [px].

    2단 탐색: 거친 격자(step)로 대략 잡고, 그 주변을 `refine` 간격으로 **서브픽셀 정밀화**.
    (1px 격자로 두면 변위가 1px=1.3mm 단위로 계단져서 슬립 시계열이 못 쓰게 된다.)
    """
    g = _gray(frame)
    ang = np.deg2rad(np.arange(sector[0], sector[1], 3.0))
    ca = np.cos(ang); sa = -np.sin(ang)
    rs = np.arange(*rrange)

    def scan(x0, y0, w, st, wy=None):
        best = None
        wy = w if wy is None else wy
        for cy in np.arange(y0 - wy, y0 + wy + 1e-9, st):
            for cx in np.arange(x0 - w, x0 + w + 1e-9, st):
                ri = (rs[:, None] - d) * ca[None, :]; si = (rs[:, None] - d) * sa[None, :]
                ro = (rs[:, None] + d) * ca[None, :]; so = (rs[:, None] + d) * sa[None, :]
                sc = (_samp(g, cx + ri, cy + si) - _samp(g, cx + ro, cy + so)).mean(axis=1)
                j = int(np.argmax(sc))
                if best is None or sc[j] > best[0]:
                    best = (float(sc[j]), float(cx), float(cy), float(rs[j]))
        return best

    b = scan(cx0, cy0, win, step, win_y)
    return scan(b[1], b[2], step * 0.75, refine) if refine else b


def track_roller(mp4, f0, f1, seed, *, win_min=6.0, win_max=60.0, win_y=7.0, ds=1,
                 order="fwd", **kw):
    """구간 전 프레임에서 원을 맞춘다 → {frame: dict(cx,cy,r,score,win)}.

    ★ **등속 예측 + 적응 탐색창 + 수직 구속** (마라톤G 08-08 사고 대응)
      고정 ±5px 창으로 두면 푸시 구간(프레임당 20~30px 이동)에서 발을 **놓치고**
      배경에 락온한다 — 실제로 f199 를 −12.7mm 로 잘못 읽어 사용자의 −60mm 증언을
      3회 반박했다. 다음 위치를 직전 속도로 예측하고, 창을 |속도|에 비례해 넓힌다.
      단 **세로 창은 좁게**(win_y) 묶는다 — 접지 중 발은 수평으로만 움직이는데,
      가로 창만 넓히면 흰 플랫폼의 **볼트 구멍**(밝은 원 = 강한 방사 경계)이
      더 높은 점수로 이겨버린다 (실제 발생: f199 가 −80.7mm 로 튐).

    ★ `order="rev"` — **시드에서 시간을 거슬러** 추적한다. 시드는 보통 스쿼트 바닥에서
      잡는데, 거기서 하강 시작(f0)까지 그냥 앞으로 추적하면 **첫 프레임부터 시드가
      엉뚱한 곳**이다. 24fps·짧은 하강에선 우연히 통했지만 59fps 4K(하강 267프레임)에선
      f120 에서 추적이 끊겼다 (08-08). 역방향이면 시드가 항상 인접 프레임이다.

    ds : 정수배 축소 (4K 처리용). 자도 같은 축소 프레임에서 재므로 mm 정밀도는 보존.
    """
    import imageio.v3 as iio
    F = {}
    for i, f in enumerate(iio.imiter(Path(mp4))):
        if f0 <= i <= f1:
            g = np.asarray(f)[..., :3].mean(axis=2)
            F[i] = (g[::ds, ::ds] if ds > 1 else g).astype(np.uint8)
        if i > f1:
            break
    ks = sorted(F)
    if order == "rev":
        ks = ks[::-1]
    out = {}; c = np.array(seed, float); v = np.zeros(2)
    for i in ks:
        pred = c + v
        w = float(np.clip(2.5 * np.hypot(*v) + win_min, win_min, win_max))
        sc, cx, cy, r = fit_roller(F[i], pred[0], pred[1], win=w, win_y=win_y, **kw)
        new = np.array([cx, cy])
        v = new - c if out else np.zeros(2)
        c = new
        out[i] = dict(cx=cx, cy=cy, r=r, score=sc, win=w)
    return out


def calibrate(mp4, f0, f1, seed, **kw):
    """새 영상 교정 — 이 영상 자체에서 발 지름을 재서 등재용 dict 반환."""
    tr = track_roller(mp4, f0, f1, seed, **kw)
    R = np.array([v["r"] for v in tr.values()]); S = np.array([v["score"] for v in tr.values()])
    ok = S > np.percentile(S, 25)                      # 흐릿한 프레임 제외
    dia = float(2 * np.median(R[ok]))
    return dict(mp4=Path(mp4).name, frames=(f0, f1), seed=list(map(float, seed)),
                dia_px=round(dia, 2),
                dia_px_iqr=(round(2 * np.percentile(R[ok], 25), 2),
                            round(2 * np.percentile(R[ok], 75), 2)),
                scale_mm_per_px=METAL_DIA_MM / dia, n=int(ok.sum()), track=tr)


def scale_of(sess, trial, *, mp4=None, f0=None, f1=None, seed=None):
    """이 trial 의 정본 스케일 [mm/px].

    ★ 등재값이 없으면 **그 영상에서 직접** 잰다. 다른 trial 값 대용은 절대 하지 않는다.
    """
    k = (sess, trial)
    if k in FOOT_CAL:
        c = FOOT_CAL[k]; d = c["dia_px"]
        lo, hi = c["dia_px_iqr"]
        return dict(scale_mm_per_px=METAL_DIA_MM / d, dia_px=d,
                    rel_sd=float((hi - lo) / 2 / d), source="FOOT_CAL", note=c.get("note", ""))
    if mp4 is None:
        raise KeyError(
            f"{k} 미등재 — 이 trial 의 mp4 를 주세요. **다른 영상의 mm/px 재사용 금지** "
            f"(카메라 거리·줌이 달라 발 px 지름이 다름)")
    c = calibrate(mp4, f0, f1, seed)
    return dict(scale_mm_per_px=c["scale_mm_per_px"], dia_px=c["dia_px"],
                rel_sd=float((c["dia_px_iqr"][1] - c["dia_px_iqr"][0]) / 2 / c["dia_px"]),
                source="calibrate(on-the-fly)", note=f"n={c['n']} 프레임")


def main():
    if len(sys.argv) >= 5:
        mp4, f0, cx, cy = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
        f1 = int(sys.argv[5]) if len(sys.argv) > 5 else f0 + 100
        c = calibrate(mp4, f0, f1, (cx, cy)); c.pop("track")
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    print("=" * 96)
    print(f"★ fs_vidscale 자가검증 — 발 롤러 자 (바깥 {FOOT_DIA_MM:.0f}mm = "
          f"금속판 {METAL_DIA_MM:.0f}mm + 고무 {RUBBER_MM:.0f}mm x2)")
    for (s, t), c in FOOT_CAL.items():
        r = scale_of(s, t)
        print(f"\n  {s}/{t}")
        print(f"    지름 {r['dia_px']:.2f} px (IQR {c['dia_px_iqr'][0]}~{c['dia_px_iqr'][1]})"
              f"  →  **{r['scale_mm_per_px']:.4f} mm/px**  (±{r['rel_sd']*100:.1f}%)")
        print(f"    구 플레이트 자 0.7453 은 금속판을 {0.7453*c['dia_px']:.1f} mm 로 본 셈 "
              f"→ 기존 영상 수치에 **×{r['scale_mm_per_px']/0.7453:.3f}** 필요")
    print(f"\n  ★ 접지 반경 r = {FOOT_R_M*1000:.1f} mm (바깥 {FOOT_DIA_MM:.0f}mm / 2). "
          f"MuJoCo foot geom 은 0.021 → **0.020 수정 필요** (구름 r·dθ 4.8% 영향)")
    print("  ★ 새 영상은 반드시 그 영상에서 재-교정 (calibrate) — 다른 trial 값 재사용 금지")


if __name__ == "__main__":
    main()
