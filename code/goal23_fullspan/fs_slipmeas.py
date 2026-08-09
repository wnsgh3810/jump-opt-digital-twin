# -*- coding: utf-8 -*-
"""fs_slipmeas — **슬립·구름 판정의 정본 절차** (마라톤G G72, 08-08 확립).

한 줄: 슬립 = (영상으로 잰 발의 실제 이동) − (엔코더로 계산한 굴러간 거리).

왜 둘이 다 필요한가
  | 측정 | 얻는 것 | 못 얻는 것 |
  |---|---|---|
  | 엔코더 q1,q2 | **Δθ_발** — 4절 폐쇄로 결정, **베이스 위치와 무관** | Δx_발 |
  | 영상(롤러 중심) | **Δx_발** — 세계 좌표 실측 | Δθ_발 (롤러에 마커 없음) |
  비유: 바퀴가 "몇 바퀴 돌았나"는 엔코더가, "실제로 몇 cm 갔나"는 자가 안다.
  둘의 차이가 **미끄러짐**이다. 하나만으로는 절대 분해되지 않는다.

━━ 절차 5단계 (전부 자동, 각 단계에 QC 플래그) ━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ① **자 교정**   그 영상에서 발 금속판(30.0mm) 지름을 재서 mm/px 확정 (`fs_vidscale`).
                 ★ 다른 영상 값 재사용 금지 — 카메라 거리·줌이 세션마다 다르다.
  ② **동기**     영상 이륙 프레임(프레임차분 급증 시작) ↔ 데이터 `segment().t_lo`.
  ③ **발 탐색**  스쿼트 바닥에서 전역 원 탐색 → 각 후보를 이륙까지 추적 →
                 **이륙 때 가장 크게 움직인 원 = 발** (볼트 구멍·나사는 0px 움직인다).
  ④ **추적**     등속 예측 + 적응창 + 수직 구속 (`fs_vidscale.track_roller`).
  ⑤ **융합**     slip(t) = Δx_영상 − r·Δθ_엔코더,  r = 20.0 mm.

━━ 하지 말 것 (전부 실제 사고, REJECTED #73~#77) ━━━━━━━━━━━━━━━━━━━━━━━━━
  ✗ 발판 플레이트 120mm 자 (0.7453) — 금속판을 24.1mm 로 봄, ×1.239 오차
  ✗ 링크 연결부 추적 — 종아리 회전에 따라 궤도운동, 병진 변위가 아님
  ✗ 고정 ±5px 탐색창 — 푸시(프레임당 20~30px)에서 발을 놓치고 배경에 락온
  ✗ 세로 창까지 넓히기 — 흰 플랫폼 **볼트 구멍**이 더 높은 점수로 이김
  ✗ 이동중앙값 평활 — 푸시 급변을 뭉갬 (−56.5 → −38.5mm)
  ✗ 모델 Δx 로 만든 '기하 슬립' — |모델Δx|/|구름| 중앙 3.23, 증언과 부호 반대

정본 검증 trial: 26.07.23/150_2.2_250_3 →
  하강전반 −0.6 · 하강후반 −6.8 · 바닥유지 −0.6 · **푸시~이륙 −42.0** · 전체 −49.9 mm
  (사용자 육안 3건 전부 재현: 깊게앉기 −10~15 · 6.67~8.17s 이동 8.xx · 푸시 −60=플레이트 절반)

CLI:  python fs_slipmeas.py <세션> <trial>      # 한 trial
      python fs_slipmeas.py --all               # 전수 (오래 걸림 → .bat 로)
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                       # noqa: E402

OUT_JSON = HERE / "_G72_slipall.json"
REF_W = 720.0            # 기준 가로 해상도 — 픽셀 단위 파라미터는 전부 이 비율로 스케일


def video_meta(mp4):
    """★ fps·해상도는 **영상마다 읽는다** (하드코딩 절대 금지).

    실측 분포: 0723/0602/0725/0727 = 24fps 720x1280 · 0324/0722 = 30fps ·
    **0424/0429/0421 = 59.3fps 2160x3840(4K)**.
    24 로 고정했다가 전수 배치를 통째로 버린 전례가 있다 (08-08).
    4K 는 발이 3배 커서 반지름 탐색 범위도 비례 확대해야 한다.
    """
    import imageio
    rd = imageio.get_reader(str(Path(mp4)))
    m = rd.get_meta_data(); n = int(rd.count_frames()); rd.close()
    w, h = int(m["size"][0]), int(m["size"][1])   # imageio meta size = (W, H) 순서
    ds = max(1, int(w // 1080))             # ★ 4K 만 절반 축소 (발이 너무 작아지면 안 됨)
    return dict(fps=float(m["fps"]), n=n, h=h, w=w, ds=ds, k=(w / ds) / REF_W)


# ── ② 동기 ────────────────────────────────────────────────────────────────────
def motion_profile(mp4, step=4, k=1.0, ds=1):
    """프레임차분(움직임) 시계열. 이륙은 여기서 폭발적으로 튄다. (step 은 해상도 비례)"""
    import imageio.v3 as iio
    step = max(2, int(round(step * k * ds)))
    prof = []; prev = None
    for f in iio.imiter(Path(mp4)):
        g = np.asarray(f, float)[..., :3].mean(axis=2)[::step, ::step]
        prof.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
    return np.asarray(prof)


PROFCACHE = HERE / "graphs" / "G72_seed" / "_profcache"


def motion_profile_cached(mp4, k=1.0, ds=1):
    """`motion_profile` 을 mp4 별로 캐시한다.

    왜 — 2패스(세션 자 확정 → 재측정)면 trial 당 **영상 전체를 두 번** 훑는다.
    4K 59fps 는 한 번이 수십 초라 전수에서 이것만으로 몇 시간이 간다.
    프레임차분은 영상만의 함수(결정적)이므로 캐시해도 값이 달라지지 않는다.
    """
    PROFCACHE.mkdir(parents=True, exist_ok=True)
    fp = PROFCACHE / f"{Path(mp4).stem}_k{k:.3f}_ds{ds}.npy"
    if fp.exists():
        try:
            return np.load(fp)
        except Exception:
            pass
    prof = motion_profile(mp4, k=k, ds=ds)
    np.save(fp, prof)
    return prof


def liftoff_frame(prof, *, lo=0.25, hi=0.50, min_run=3):
    """이륙 프레임 검출.

    ★ 단발 스파이크를 버려야 한다 — 카카오톡 mp4 는 **1초(24프레임) 간격 키프레임**에서
      프레임차분이 혼자 튄다 (실측: f24·f48·f72·f120·f144·f168·f192 에 3~5 크기 스파이크).
      "임계 첫 교차" 로 잡으면 f24 를 이륙으로 오인한다.
    절차: prof > lo·max 인 **연속 런** 중 길이 ≥ min_run 인 **최장 런** = 점프 구간.
          그 안에서 prof > hi·max 를 처음 넘는 프레임 = 이륙.
    반환: (f_lo, run_start, run_end)  — 불확도 ±1~2프레임(±42~83ms).
    """
    m = float(prof.max())
    idx = np.where(prof > lo * m)[0]
    if not len(idx):
        return None, None, None
    runs = [r for r in np.split(idx, np.where(np.diff(idx) > 3)[0] + 1) if len(r) >= min_run]
    if not runs:
        return None, None, None
    run = max(runs, key=len)
    inside = run[prof[run] > hi * m]
    f = int(inside[0]) if len(inside) else int(run[0])
    return f, int(run[0]), int(run[-1])


# ── ③ 발 시드 ────────────────────────────────────────────────────────────────
#
# ★★ 결론 (08-09): **자동 전역 탐색은 이 데이터에 대해 작동하지 않는다.** ★★
#   다섯 가지 판별을 시도했고 전부 다르게 실패했다:
#     (1) 최고 점수 원          → 광학테이블 볼트머리·브래킷 나사
#     (2) 이륙 때 움직인 원      → 허벅지 트러스 구멍 (이륙엔 로봇 전체가 움직인다)
#     (3) 가장 아래 원          → 광학테이블 볼트 구멍 (테이블이 발보다 아래)
#     (4) (2) AND (3) 결합       → 여전히 실패 (발이 상위 후보에 못 듦)
#     (5) 후보 45개로 확대 + (4) → 여전히 실패 (0602/150_2.2_250_3)
#   근본 원인: 롤러는 지름 20~60px 의 **저대비** 원인데, 화면에는 작고 고대비인 원
#   (볼트머리·나사·구멍)이 수십 개 있다. 방사 기울기 점수는 후자를 항상 선호한다.
#
#   ⇒ **수동 시드가 정답이다.** 등재한 두 세션(0723·0424)은 **둘 다 한 번에 성공**했다.
#     그리고 **세션 단위로는 부족하다** — 같은 세션 안에서도 로봇 설치 위치가
#     trial 마다 달라(카메라는 고정) 0602 의 세션 시드가 다른 trial 에서 볼트에 락온했다.
#     ⇒ **trial 단위 시드**를 `_G75_seedzoom.py` 로 읽어 SEED_CAL 에 등재한다.
#        키는 "<세션>/<trial>" 형식을 우선 조회하고, 없으면 세션 키로 폴백.
#
# 왜 완전 자동을 포기했나 (08-08)
#   전역 원 탐색은 **광학 테이블 볼트 머리·브래킷 나사·트러스 구멍**이 점수에서 이긴다.
#   0424(원거리 4K)에서 상위 12후보에 발이 아예 없었다. 판별로 시도한 두 규칙도 실패:
#     "이륙 때 움직인 원" → 트러스 구멍 (이륙엔 로봇 전체가 움직임)
#     "가장 아래 원"     → 광학 테이블 구멍 (테이블이 발보다 아래)
#   카메라 배치는 **세션 단위로 일정**하므로, 세션마다 한 번만 눈으로 읽어 등재한다.
#   그 뒤 trial 별 미세 차이는 넉넉한 창(±60px) + **반지름 구속**(±30%)으로 흡수한다.
#   반지름 구속이 결정적이다 — 볼트 머리(r≈4)·트러스 구멍(r≈24)을 형상만으로 배제한다.
#
# 값은 **처리 해상도**(ds 적용 후) 기준. `_G72_seedsheet.py` 로 그림 보고 채운다.
SEED_CAL = {
    "26.07.23": (421.0, 1138.0, 16.2),      # ds=1 (720x1280)
    "26.04.24": (510.0, 1681.0, 33.5),      # ds=2 (1080x1920) — 금속판 지름 ~67px
    # ★ 0602 는 발이 **프레임 바닥에 붙어** 있다 (중심 y=1262, 프레임 1280).
    #   원의 아래쪽(r+2=19 → y 1281)이 화면 밖 → 방사 기울기의 바깥 표본이 클립된다.
    #   섹터를 좌·상으로 돌려야 한다 (아래를 못 쓴다). SECTOR_CAL 참조.
    # ⚠ 0602 는 등재해도 실패했다. 시드를 120_2_120_2 에서 읽었는데
    #   **같은 세션 안에서도 로봇 설치 위치가 trial 마다 다르다** (카메라는 고정이어도
    #   로봇을 다시 놓으면 발이 옮겨간다). 150_2.2_250_3 에서 흰 브래킷 볼트에 락온.
    #   ⇒ SEED_CAL 은 세션 단위로 부족하다 — **trial 단위 시드**가 필요하다.
    #   "26.06.02": (417.0, 1262.0, 17.0),   # 120_2_120_2 기준. 세션 공용 불가.
}

# ★ trial 단위 시드의 **단일 출처** = `_G77_seeds.json` (판독 산출물, _G77_sheet.py 가 씀).
#   여기 딕셔너리에 손으로 55줄을 옮겨 적지 않는다 — 옮겨 적는 순간 두 곳이 갈라진다.
#   내부 게이트를 통과한 것만 싣는다 (gate=False 는 사람이 다시 봐야 하는 것이다).
_SEEDJSON = HERE / "_G77_seeds.json"
if _SEEDJSON.exists():
    try:
        _SEEDGATE = {}
        for _k, _v in json.load(io.open(_SEEDJSON, encoding="utf-8")).items():
            SEED_CAL[_k] = (float(_v["cx"]), float(_v["cy"]), float(_v["r"]))
            _SEEDGATE[_k] = bool(_v.get("gate", True))
    except Exception as _ex:                       # 판독 파일이 깨져도 측정은 돌게
        print(f"[경고] _G77_seeds.json 읽기 실패 — 세션 시드만 사용: {_ex}")


# 처리 해상도(가로 px)별 발 금속판 **반지름 사전**. 등재 세션에서 실측한 값.
#   같은 촬영 규격이면 발 크기도 같다 — 미등재 세션의 자동 탐색을 이걸로 구속한다.
#   구속이 없으면 광학테이블 볼트머리(r≈4)·트러스구멍(r≈24)이 점수로 이긴다.
R_PRIOR = {720: 16.2, 1080: 29.4}


# 발이 프레임 가장자리에 붙은 세션은 **원호 섹터**를 돌려야 한다 (잘린 쪽을 뺀다).
SECTOR_CAL = {"26.06.02": (120.0, 240.0)}      # 좌측 위주 (아래가 화면 밖)


def seed_of(sess, trial=None, k=1.0):
    """시드 (cx, cy, r_expect). **trial 키 우선**, 없으면 세션 키, 그것도 없으면 None."""
    if trial and f"{sess}/{trial}" in SEED_CAL:
        return SEED_CAL[f"{sess}/{trial}"]
    return SEED_CAL.get(sess)


def r_prior(proc_w):
    """처리 가로폭에 가장 가까운 규격의 반지름 사전."""
    key = min(R_PRIOR, key=lambda w: abs(w - proc_w))
    return R_PRIOR[key] * (proc_w / key)


# ── ③ 발 탐색 ────────────────────────────────────────────────────────────────
def _scan_circles(g, ys, xs, *, rrange=(6.0, 30.0, 0.5), topn=40, k=1.0):
    """거친 격자 전역 탐색 → 상위 후보 [(score,cx,cy,r)]."""
    ang = np.deg2rad(np.arange(*VS.SECTOR, 6.0)); ca = np.cos(ang); sa = -np.sin(ang)
    rs = np.arange(rrange[0] * k, rrange[1] * k, max(0.5, rrange[2] * k))
    ed = VS.EDGE_D * k
    out = []
    for cy in ys:
        for cx in xs:
            ri = (rs[:, None] - ed) * ca[None, :]; si = (rs[:, None] - ed) * sa[None, :]
            ro = (rs[:, None] + ed) * ca[None, :]; so = (rs[:, None] + ed) * sa[None, :]
            sc = (VS._samp(g, cx + ri, cy + si) - VS._samp(g, cx + ro, cy + so)).mean(axis=1)
            j = int(np.argmax(sc)); out.append((float(sc[j]), float(cx), float(cy), float(rs[j])))
    out.sort(key=lambda t: -t[0])
    # 근접 후보 병합
    keep = []
    for c in out:
        if all(np.hypot(c[1] - q[1], c[2] - q[2]) > 14 * k for q in keep):
            keep.append(c)
        if len(keep) >= topn:
            break
    return keep


def find_foot(mp4, f_lo, *, band=(0.60, 0.99), back=14, topn=45, k=1.0, ds=1, rprior=None):
    """⚠ 폴백 전용 — 신뢰하지 말 것. 위 주석의 5회 실패 기록 참조."""
    """**이륙 순간 크게 움직이는 원 = 발**.

    판별 원리 (이게 결정적이다):
      바닥유지 구간에는 발도 배경 볼트 구멍도 거의 안 움직인다 → 구별 불가.
      그런데 **이륙 순간(2~3프레임)엔 발만 20~40px 튄다.** 배경은 0이다.
      그래서 스쿼트 바닥 프레임에서 후보를 뽑고, 각 후보를 이륙까지 따라가
      **변위가 가장 큰 것**을 발로 판정한다. (반지름이 무너지는 후보는 탈락.)
    반환: (score, cx, cy, r, moved_px) — cx,cy 는 **스쿼트 바닥 프레임** 기준 시드.
    """
    import imageio.v3 as iio
    f_sit = max(4, f_lo - back)
    want = set(range(f_sit, f_lo + 2)); F = {}
    for i, f in enumerate(iio.imiter(Path(mp4))):
        if i in want:
            g = np.asarray(f, float)[..., :3].mean(axis=2)
            F[i] = g[::ds, ::ds] if ds > 1 else g
        if i > max(want):
            break
    if f_sit not in F or f_lo not in F:
        return None
    H, W = F[f_sit].shape
    ys = np.arange(int(H * band[0]), int(H * band[1]), 6.0 * k)
    xs = np.arange(int(W * 0.10), int(W * 0.94), 6.0 * k)
    rr_scan = ((rprior * 0.65, rprior * 1.35, 0.5) if rprior else (6.0 * k, 30.0 * k, 0.5 * k))
    cands = _scan_circles(F[f_sit], ys, xs, topn=topn, k=1.0, rrange=rr_scan)
    # ★ **발 = 로봇에서 가장 아래**  (2차 판별)
    #   "이륙 때 움직인 원" 만으로는 부족하다 — 이륙 순간엔 허벅지 트러스도 링크도 다 움직인다.
    #   실제로 0424(카메라 먼 세션)에서 **트러스 구멍**을 발로 오인했다 (08-08).
    #   발은 지면에 닿아 있으므로 로봇 부품 중 화면상 **가장 아래**다 — 이건 애매하지 않다.
    ok_list = []
    for s0, cx, cy, r0 in cands:
        c = np.array([cx, cy], float); v = np.zeros(2); rr = [r0]; okk = True
        for i in range(f_sit + 1, f_lo + 1):
            if i not in F:
                okk = False; break
            pred = c + v
            w = float(np.clip(2.5 * np.hypot(*v) + 6.0 * k, 6.0 * k, 60.0 * k))
            sc, nx, ny, nr = VS.fit_roller(F[i], pred[0], pred[1], win=w, win_y=7.0 * k,
                                           rrange=(rr_scan[0], rr_scan[1], 0.1 * k),
                                           d=VS.EDGE_D * k, refine=0.1 * k)
            v = np.array([nx, ny]) - c; c = np.array([nx, ny]); rr.append(nr)
        if not okk:
            continue
        rr = np.array(rr)
        if rr.std() / max(rr.mean(), 1e-9) > 0.20:          # 반지름 붕괴 → 발이 아님
            continue
        moved = float(abs(c[0] - cx))
        if moved < 3.0 * k:                                  # 이륙에 안 움직임 → 배경
            continue
        ok_list.append((s0, float(cx), float(cy), float(np.median(rr)), moved))
    if not ok_list:
        return None
    # ★ **움직인 것 중 가장 아래** = 발.  두 조건을 반드시 **함께** 써야 한다:
    #   "움직인 원"만 → 허벅지 트러스 구멍(이륙엔 로봇 전체가 움직임)
    #   "가장 아래"만 → 광학테이블 볼트 구멍(테이블이 발보다 아래)
    #   그리고 후보 수(topn)가 적으면 발이 목록에 아예 못 든다 — 볼트머리·나사가
    #   대비 점수로 이기기 때문. 45개까지 받아서 위 두 조건으로 거른다.
    ymax = max(c[2] for c in ok_list)
    low = [c for c in ok_list if c[2] > ymax - 4.0 * max(c2[3] for c2 in ok_list)]
    return max(low, key=lambda c: c[4])


def r0max(lst):
    return max(c[3] for c in lst) if lst else 1.0


# ── ⑤ 융합 ───────────────────────────────────────────────────────────────────
# CVT 입력 링크 길이는 **trial 마다** `fs_data.cvt_li` 로 읽는다 (세션 상수 금지, 사용자 지시 08-09).
# 무변속 세션은 0.030 이 돌아오므로 별도 분기가 필요 없다.


class ReducedCVT:
    """CVT(l_i≠30) 세션용 축약 상태 — 크랭크→무릎 사상을 **폐쇄 솔버**로 푼다.

    `_G10_energy.Reduced` 를 감싸고 `_fw` 만 갈아 끼운다. 기본형은 knee = crank 인데
    그건 평행사변형(l_i=30) 관례라 CVT 에서 성립하지 않는다.
    """

    def __init__(self, ft, l_i):
        from _G10_energy import Reduced as _R
        import mujoco as _mj
        from cvt_core import closure as _cl
        self._R = _R(ft); self.l_i = float(l_i); self._mj = _mj; self._cl = _cl
        self.r = self._R.r
        self._c = {}

    def _fw(self, q1, q2, zb):
        R = self._R; md = R.md
        qc = -q2
        qk, qpin, _ = self._cl(qc, self.l_i, qc)      # 초기추정 = 평행사변형 (가지 고정)
        md.qpos[R.iq["base_z"]] = zb
        md.qpos[R.iq["hip_m"]] = -q1 - np.pi / 2
        md.qpos[R.iq["hip"]] = 0.0
        md.qpos[R.iq["knee_motor"]] = qc
        md.qpos[R.iq["cpin"]] = qpin
        md.qpos[R.iq["knee"]] = qk
        self._mj.mj_forward(R.m, md)
        return md

    def state(self, q1, q2):
        k = (round(q1, 9), round(q2, 9))
        if k in self._c:
            return self._c[k]
        R = self._R
        md = self._fw(q1, q2, 0.0)
        zb = -(float(md.geom_xpos[R.gf][2]) - R.r)
        md = self._fw(q1, q2, zb)
        out = (zb, float(md.geom_xpos[R.gf][0]),
               float(np.arctan2(md.xmat[R.bf][2], md.xmat[R.bf][0])), None)
        self._c[k] = out
        return out


def measure(sess, trial, *, verbose=True, force_dia=None):
    """한 trial 의 슬립·구름 분해. 실패 시 reason 을 담은 dict 반환."""
    import fs_data as FD, fs_runner as FR
    from _G10_energy import Reduced
    from _G13_board import lpf

    hit = [q for s, q, g, c, h in FD.registry() if s == sess and q.name == trial]
    if not hit:
        return dict(sess=sess, trial=trial, ok=False, reason="registry 없음")
    p = hit[0]
    vids = sorted(Path(p).glob("*.mp4"))
    vids = [v for v in vids if "online-video-cutter" not in v.name]
    if not vids:
        return dict(sess=sess, trial=trial, ok=False, reason="mp4 없음")
    mp4 = vids[0]

    d = FD.load2(p); t = d["t"]; seg = FD.segment(d)
    if seg is None or seg.get("t_lo") is None:
        return dict(sess=sess, trial=trial, ok=False, reason="segment/t_lo 없음")
    t_lo = float(seg["t_lo"])

    vm = video_meta(mp4); fps = vm["fps"]; k = vm["k"]; ds = vm["ds"]
    prof = motion_profile_cached(mp4, k=k, ds=ds)
    f_lo, r0f, r1f = liftoff_frame(prof)
    if f_lo is None or f_lo < 40:
        return dict(sess=sess, trial=trial, ok=False, reason=f"이륙 프레임 검출 실패 (f_lo={f_lo})",
                    mp4=mp4.name)
    shift = t_lo - f_lo / fps                      # 데이터시각 = 영상시각 + shift (뒤에서 재확정)

    f0 = max(2, f_lo - int(round(4.5 * fps)))      # 하강 시작 부근 (~4.5초 전)
    sec = SECTOR_CAL.get(sess, VS.SECTOR)      # 가장자리에 붙은 세션은 원호를 돌린다
    sd = seed_of(sess, trial, k); _seed_warn = None
    if sd is not None:
        # 세션 시드 → 스쿼트 바닥 프레임에서 **반지름 구속**하며 국소 정밀화
        import imageio.v3 as iio
        f_sit0 = max(4, f_lo - max(6, int(round(0.6 * fps))))
        G = None
        for i, fr in enumerate(iio.imiter(mp4)):
            if i == f_sit0:
                g = np.asarray(fr, float)[..., :3].mean(axis=2)
                G = g[::ds, ::ds] if ds > 1 else g
                break
        if G is None:
            return dict(sess=sess, trial=trial, ok=False, reason="시드 프레임 읽기 실패")
        rc = sd[2]
        # ★ 시드 정밀화는 **발 전용 맞춤**(_G77_footfit: 각도 중앙값 + 내부 게이트)으로.
        #   구 코드는 win=60px 로 넓게 찾았는데, 그 창이면 **종아리 링크의 밝은 가장자리**가
        #   점수로 이긴다 (0602 에서 6/6 전부 링크로 끌려갔다). 시드가 trial 단위로
        #   정확해진 지금은 좁은 창(±10px)이 맞고, 내부 게이트가 링크를 배제한다.
        import _G77_footfit as FF
        sc0, cx0, cy0, r0, _sec, _inn, _ok, _br = FF.fit_foot(
            G, sd[0], sd[1], rc, win=10.0 * k, rtol=0.18, step=1.0, refine=0.25)
        # 게이트 탈락은 **경고**지 실패가 아니다. 0324 처럼 발이 "두꺼운 검은 고무 타이어 +
        # 밝은 금속 중앙" 이면 '안이 깨끗하다' 가정이 애초에 성립하지 않는다 (중앙에 큰 허브 구멍).
        # 시드는 이미 사람이 시트로 확인한 값이므로, 여기서 막지 말고 QC 로 넘긴다.
        _seed_warn = (f"시드 게이트 탈락 (내부 {_inn:.1f} · 밝기차 {_br:.1f} "
                      f"vs 테두리 {sc0:.1f}) — 검증 시트 확인 필수") if not _ok else None
        moved = float("nan")
    else:
        rp = r_prior(vm["w"] / ds)
        fd = find_foot(mp4, f_lo, back=max(6, int(round(0.6 * fps))), k=k, ds=ds, rprior=rp)
        if fd is None:
            return dict(sess=sess, trial=trial, ok=False,
                        reason="발 시드 없음 (SEED_CAL 미등재 + 자동 탐색 실패)", mp4=mp4.name)
        sc0, cx0, cy0, r0, moved = fd

    # 시드는 **스쿼트 바닥(f_lo-14)** 기준 → 거기서 앞뒤로 나눠 추적
    f_sit = max(4, f_lo - max(6, int(round(0.6 * fps))))
    _rc = r0 if r0 and np.isfinite(r0) else 16.0 * k
    TK = dict(win_min=6.0 * k, win_max=60.0 * k, win_y=7.0 * k, ds=ds, sector=sec,
              rrange=(_rc * 0.70, _rc * 1.30, 0.1 * k), d=VS.EDGE_D * k, refine=0.1 * k)
    # 추적기 A/B: FS_FOOTTRK=1 이면 발 전용(_G77_footfit.track_foot), 아니면 정본 track_roller.
    #   기본을 정본으로 둔 이유 = 0723/150_2.2_250_3 푸시 −43.1mm 회귀 기준을 지키기 위해.
    #   전환은 그 기준을 재현한 뒤에만 (아래 _G78 A/B 참조).
    _ft = bool(os.environ.get("FS_FOOTTRK"))
    if _ft:
        import _G77_footfit as FF
        TKF = dict(win_min=6.0 * k, win_max=60.0 * k, win_y=7.0 * k, ds=ds, rtol=0.18,
                   step=1.0, refine=0.25)
        tb = FF.track_foot(mp4, f0, f_sit, (cx0, cy0), r0, order="rev", **TKF)
    else:
        tb = VS.track_roller(mp4, f0, f_sit, (cx0, cy0), order="rev", **TK)   # ★ 역방향
    # ★ 이륙 추정치 **너머까지** 추적하고, 접지 종료는 아래 유효성 절단이 정한다.
    #   프레임차분 기반 이륙 검출은 fps 에 편향된다 — 24fps 는 푸시가 2~3프레임이라
    #   "최대의 50% 첫 교차" 가 맞았지만, 59fps 는 푸시가 15프레임에 걸쳐 올라가
    #   같은 규칙이 **푸시 중간**에서 발동한다 (0424: 검출 f294, 실제 이륙 ~f301).
    #   물리(발이 지면을 떠남)가 정하게 두면 fps 와 무관해진다.
    f_hi = int(min(len(prof) - 1, np.argmax(prof) + 0.15 * fps))
    if _ft:
        tf = FF.track_foot(mp4, f_sit, max(f_sit, f_hi),
                           (tb[f_sit]["cx"], tb[f_sit]["cy"]), r0, **TKF)
    else:
        tf = VS.track_roller(mp4, f_sit, max(f_sit, f_hi),
                             (tb[f_sit]["cx"], tb[f_sit]["cy"]), **TK)
    tr = {**tb, **tf}
    # 자(지름)·QC 는 **접지 절단 뒤 남은 프레임**으로만 계산한다 (아래에서 확정).
    #   전체 추적으로 계산했더니 이미 버린 이륙 후 프레임 때문에 "최저 점수 21" 이
    #   허위로 뜨고 지름 산포도 부풀었다 (08-08).

    # ★ 접지 유효 구간 절단 — 이륙 다음 프레임부터 발이 화면에서 사라져 추적이 튄다.
    #   (실측: f200 에서 −148mm 로 폭주). 지면 높이에서 벗어나거나 점수가 무너지면 자른다.
    ks = sorted(tr)
    cys = np.array([tr[k]["cy"] for k in ks]); scs = np.array([tr[k]["score"] for k in ks])
    y0 = float(np.median(cys[: max(3, len(ks) // 2)])); s0 = float(np.median(scs))
    cxs = np.array([tr[k]["cx"] for k in ks])
    last = len(ks) - 1
    for j in range(3, len(ks)):
        if (abs(cys[j] - y0) > 8.0 * k or scs[j] < 0.5 * s0
                or abs(cxs[j] - cxs[j - 1]) > 60.0 * k * 24.0 / fps):   # 1프레임 물리 한계
            last = j - 1; break
    ks = ks[: last + 1]
    f_end = ks[-1]
    fi = np.array(ks, float)
    xpx = np.array([tr[int(k)]["cx"] for k in fi])          # ★ 평활 금지

    Rk = np.array([tr[int(q)]["r"] for q in fi]); Sk = np.array([tr[int(q)]["score"] for q in fi])
    okk = Sk > np.percentile(Sk, 25)
    dia_meas = float(2 * np.median(Rk[okk]))
    # ★ **세션 자 강제** — 카메라가 세션 중 안 움직였으므로 자는 세션 내 상수다.
    #   trial 마다 독립으로 재게 뒀더니 한 세션 안에서 자가 최대 111% 흔들렸다
    #   (지름이 탐색 하한 14.7px 에 포화 → +83~107mm 같은 물리 불가 슬립). G74 참조.
    dia = float(force_dia) if force_dia else dia_meas
    s_mm = VS.METAL_DIA_MM / dia
    rel = float((2 * np.percentile(Rk[okk], 75) - 2 * np.percentile(Rk[okk], 25)) / 2 / dia)

    # ★★ 동기 재확정: **마지막 접지 프레임 ↔ 데이터 t_lo** ★★
    #   24fps 에서 푸시는 5프레임뿐인데 구름이 마지막 프레임에 15mm 급변한다 —
    #   동기 1프레임(42ms) 오차가 **푸시 슬립을 11mm** 흔든다.
    #   프레임차분으로 잡은 f_lo 는 ±1프레임 불확도가 있으므로, 물리적으로 확실한
    #   "발이 지면에 있던 마지막 프레임 = 이륙 직전" 을 t_lo 에 맞춘다.
    shift = t_lo - f_end / fps
    t_vid = fi / fps
    t_dat = t_vid + shift

    # ★ CVT 세션(l_i≠30)은 **구름 항이 달라진다**.
    #   기본 Reduced 는 knee = crank (평행사변형)를 가정하는데 그건 l_i=30 에서만 참이다
    #   (검증: closure(qc, 0.030) = qc, 오차 0.00°). l_i=25.08 에서는 최대 18° 어긋나고
    #   전달비가 0.83 → 0.09 까지 변한다. 미보정으로 재면 0429 의 구름이 −19 대신 −37 로 나와
    #   "CVT 가 3배 미끄러진다"는 **인공 결론**이 나온다 (실제로 영상 Δx 는 거의 같다).
    #   발이 종아리와 한 덩어리이므로 θ_foot 은 (q1, 무릎각)의 함수 —
    #   크랭크→무릎 사상만 폐쇄 솔버로 바로잡으면 된다.
    _li = float(d.get("l_i", FD.L_I_NOM))
    Rd = (Reduced(FR.fs_twin()) if abs(_li - FD.L_I_NOM) < 1e-6
          else ReducedCVT(FR.fs_twin(), _li))
    rfoot = VS.FOOT_R_M
    q1f = lpf(d["q1"], 30.0); q2f = lpf(d["q2"], 30.0)
    th = np.array([Rd.state(q1f[i], q2f[i])[2] for i in range(0, len(t), 2)])
    th_v = np.interp(t_dat, t[::2], th)

    x_mm = (xpx - xpx[0]) * s_mm
    roll = rfoot * (th_v - th_v[0]) * 1000.0
    slip = x_mm - roll

    # 구간 경계는 **데이터 세그먼트**에서 (프레임 비율 추정 금지)
    t_bot = float(t[seg["i_bot"]]); t_push = float(seg["t_push"]); t_desc = float(seg["t_desc"])
    jf = lambda td: int(np.argmin(np.abs(t_dat[: len(fi)] - td)))
    n = len(fi)
    i_d, i_b, i_p = jf(t_desc), jf(t_bot), jf(t_push)
    i_m = (i_d + i_b) // 2
    B = {"하강전반": (i_d, i_m), "하강후반": (i_m, i_b),
         "바닥유지": (i_b, i_p), "푸시~이륙": (i_p, n - 1), "전체": (i_d, n - 1)}
    segs = {k: dict(dx=float(x_mm[b] - x_mm[a]), roll=float(roll[b] - roll[a]),
                    slip=float(slip[b] - slip[a]), t=(float(t_vid[a]), float(t_vid[b])))
            for k, (a, b) in B.items()}

    # 동기 민감도: shift 를 ±1프레임 흔들었을 때 푸시 슬립이 얼마나 변하나
    def push_slip(sh):
        tv = fi / fps + sh
        th2 = np.interp(tv, t[::2], th)
        rl = rfoot * (th2 - th2[0]) * 1000.0
        a, b = B["푸시~이륙"]
        return float((x_mm[b] - x_mm[a]) - (rl[b] - rl[a]))
    sens = float(max(abs(push_slip(shift + 1 / fps) - segs["푸시~이륙"]["slip"]),
                     abs(push_slip(shift - 1 / fps) - segs["푸시~이륙"]["slip"])))

    qc = []
    if sens > 8.0:
        qc.append(f"동기 ±1프레임 → 푸시슬립 ±{sens:.0f}mm")
    if rel > 0.10:
        qc.append(f"지름 산포 {rel*100:.0f}% (>10%)")
    if force_dia and abs(dia_meas - dia) / dia > 0.12:
        qc.append(f"측정지름 {dia_meas:.1f} vs 세션자 {dia:.1f} ({(dia_meas/dia-1)*100:+.0f}%) — 추적 의심")
    if float(np.min(Sk)) < 40:
        qc.append(f"최저 추적점수 {np.min(Sk):.0f} (<40)")
    if np.isfinite(moved) and moved < 15 * k * 24.0 / fps:
        qc.append(f"이륙 변위 {moved:.0f}px (<{15*k*24.0/fps:.0f} — 발 오탐 가능)")
    if sd is None:
        qc.append("SEED_CAL 미등재 — 반지름구속 자동 시드 (검증 시트 확인 필수)")
    if sd is not None and _seed_warn:
        qc.append(_seed_warn)
    if abs(shift) > 20:
        qc.append(f"동기 shift {shift:+.1f}s (비정상)")
    if f_end >= f_hi:
        qc.append(f"접지 절단 미발생 (f{f_end} = 추적 끝) — 이륙 이후까지 추적됐을 수 있음")
    if abs(f_end - f_lo) > 0.30 * fps:
        qc.append(f"접지끝 f{f_end} vs 차분이륙 f{f_lo} 차이 {abs(f_end-f_lo)}프레임")
    if B["푸시~이륙"][1] - B["푸시~이륙"][0] < 2:
        qc.append("푸시 구간 프레임 <2 (분해능 부족)")

    res = dict(sess=sess, trial=trial, ok=True, mp4=mp4.name, fps=fps,
               vid_w=vm["w"], vid_h=vm["h"], vid_n=vm["n"], px_k=k, px_ds=ds,
               f_lo=f_lo, f_end=f_end, f_hi=f_hi, jump_run=[r0f, r1f], t_lo=t_lo,
               shift=shift, f0=f0,
               seed=[cx0, cy0], seed_r=r0, seed_moved=moved,
               dia_px=dia, dia_meas=dia_meas, scale=s_mm, rel_sd=rel,
               dia_forced=bool(force_dia),
               score_min=float(np.min(Sk)), score_med=float(np.median(Sk)),
               r_foot_mm=rfoot * 1000, seg=segs, sync_sens_mm=sens, qc=qc,
               series=dict(f=fi.tolist(), x=x_mm.tolist(), roll=roll.tolist(), slip=slip.tolist(),
                           cx=[tr[int(q)]["cx"] for q in fi], cy=[tr[int(q)]["cy"] for q in fi],
                           r=[tr[int(q)]["r"] for q in fi], sc=[tr[int(q)]["score"] for q in fi]))
    if verbose:
        _pr(res)
    return res


def _pr(r):
    if not r["ok"]:
        print(f"  ✗ {r['sess']}/{r['trial']}: {r['reason']}")
        return
    print(f"  {r['sess']}/{r['trial']:<20s} {r['fps']:.0f}fps {r['vid_w']}x{r['vid_h']} · 자 {r['scale']:.4f} mm/px (지름 {r['dia_px']:.1f}px "
          f"±{r['rel_sd']*100:.0f}%) · 이륙 f{r['f_lo']} · shift {r['shift']:+.2f}s"
          + ("   ⚠ " + " / ".join(r["qc"]) if r["qc"] else ""))
    g = r["seg"]
    print(f"      {'구간':<10}{'Δx':>9}{'구름':>9}{'슬립':>9}")
    for k in ("하강전반", "하강후반", "바닥유지", "푸시~이륙", "전체"):
        v = g[k]
        print(f"      {k:<10}{v['dx']:9.2f}{v['roll']:9.2f}{v['slip']:9.2f}")


def session_dia(sess, trials, *, verbose=True):
    """세션 자 확정 — 여러 trial 에서 지름을 재 **중앙값**을 세션 자로 삼는다.

    카메라는 세션 중 고정이므로 지름은 상수여야 한다. trial 별 측정이 흩어지면
    그 세션은 추적이 불안한 것이고, 중앙값이 가장 많은 trial 이 동의한 값이다.
    산포가 크면 (>12%) 수동 시드 등재 대상으로 표시한다.
    """
    ds = []
    for q in trials:
        try:
            r = measure(sess, q, verbose=False)
            if r.get("ok"):
                ds.append((q, r["dia_meas"], r["score_med"], len(r["qc"])))
        except Exception:
            pass
    if not ds:
        return None, []
    v = np.array([d[1] for d in ds])
    med = float(np.median(v))
    spread = float((v.max() - v.min()) / med)
    if verbose:
        print(f"  [세션 자] {sess}: n={len(ds)} 지름 {v.min():.1f}~{v.max():.1f} "
              f"→ 중앙 **{med:.1f}px** (산포 {spread*100:.0f}%)"
              + ("  ⚠ 수동 시드 권장" if spread > 0.12 else ""))
    return med, ds


def main():
    import fs_data as FD
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reg = {}
    if "--all" in sys.argv:
        for s, q, g, c, h in FD.registry():
            reg.setdefault(s, []).append(q.name)
    elif len(args) >= 2 and args[1] == "*":
        for s, q, g, c, h in FD.registry():
            if s == args[0]:
                reg.setdefault(s, []).append(q.name)
    elif len(args) >= 2:
        reg = {args[0]: [args[1]]}
    else:
        reg = {"26.07.23": ["150_2.2_250_3"]}

    print("=" * 104)
    print(f"★ 슬립·구름 판정 — 자=발 금속판 {VS.METAL_DIA_MM:.0f}mm · r={VS.FOOT_R_M*1000:.0f}mm "
          f"· + = 화면 오른쪽 = 모델 +x")
    # ★ 자 정책 (08-09 변경)
    #   구: 세션 자 고정(2패스). 근거는 "카메라는 세션 중 고정" 이었다.
    #   신: **trial 별 자**가 기본. 시드 판독에서 그 전제가 깨진 걸 확인했다 —
    #       0324 는 P40_D0.7 발 지름이 23px, P100_D3 는 39px 다(같은 세션, 카메라 이동).
    #       0727 은 60_2/80_2 만 촬영일이 다르다. 세션 자를 강제하면 이런 trial 이 통째로 틀린다.
    #   세션 중앙값은 버리지 않고 **QC 기준**으로 쓴다 (12% 이상 벗어나면 경고).
    #   구 방식으로 되돌리려면 FS_SESSDIA=1.
    sess_force = bool(os.environ.get("FS_SESSDIA"))
    print("  자 정책: " + ("세션 자 고정(2패스, FS_SESSDIA)" if sess_force
                          else "**trial 별 자** + 세션 중앙값 대비 QC"))
    OUT = {}
    if OUT_JSON.exists():
        try:
            OUT = json.load(io.open(OUT_JSON, encoding="utf-8"))
        except Exception:
            OUT = {}
    import safe
    MINE = {}                       # 이 프로세스가 이번에 계산한 것만 (병합 방향 고정)
    for sess, trials in reg.items():
        med, _ = (session_dia(sess, trials) if (sess_force and len(trials) > 1)
                  else (None, []))
        for q in trials:
            try:
                r = measure(sess, q, force_dia=med)
                if r.get("ok") and not sess_force:
                    r["sess_dia_ref"] = None      # 세션 대비 QC 는 전수 끝난 뒤 일괄 (아래)
            except Exception as ex:
                r = dict(sess=sess, trial=q, ok=False,
                         reason=f"{type(ex).__name__}: {str(ex)[:70]}")
                print(f"  ✗ {sess}/{q}: {r['reason']}")
            OUT[f"{sess}/{q}"] = r
            MINE[f"{sess}/{q}"] = r
            # ★ 쓰기 직전에 다시 읽어 **내가 이번에 계산한 것만** 얹는다.
            #   ① 시작 시점 dict 를 통째로 쓰면 남의 결과를 지운다
            #      (0424 작업과 7세션 작업이 서로를 덮어써 0602 가 낡은 값으로 되돌아갔다)
            #   ② 그렇다고 `cur.update(OUT)` 로 고치면 **방향이 반대**다 —
            #      내 프로세스의 낡은 사본이 남의 최신 결과를 덮는다
            #      (0324/P40_D0.7 이 고쳐 놓은 값에서 되돌아갔다. 08-09 2차 사고)
            #   ⇒ 반드시 **MINE 만** 얹는다.
            try:
                cur = json.load(io.open(OUT_JSON, encoding="utf-8")) if OUT_JSON.exists() else {}
            except Exception:
                cur = {}
            cur.update(MINE)
            OUT = cur
            safe.atomic_json_write(OUT_JSON, OUT)
    # 세션 중앙값 대비 QC (자를 강제하지 않는 대신 **사후 감사**로 잡는다)
    if not sess_force:
        by = {}
        for k, v in OUT.items():
            if v.get("ok"):
                by.setdefault(v["sess"], []).append(v)
        for s, vs in by.items():
            if len(vs) < 3:
                continue
            # ★ 해상도로 정규화하고 비교한다. 한 세션 안에서도 촬영 규격이 섞일 수 있다
            #   (0421 은 P60 만 24fps 720p, 나머지는 59fps 4K) — 생 px 로 비교하면
            #   정상 trial 에 "−34% 카메라 이동" 이라는 **허위 경고**가 붙는다.
            m = float(np.median([v["dia_px"] / v["px_k"] for v in vs]))
            for v in vs:
                d = (v["dia_px"] / v["px_k"]) / m - 1
                tag = f"세션 중앙 지름(해상도 정규화) {m:.1f} 대비 {d*100:+.0f}%"
                v["sess_dia_ref"] = round(m, 2)   # 해상도 정규화 값 (dia_px / px_k)
                v["qc"] = [q for q in v.get("qc", []) if "세션 중앙 지름" not in q]
                if abs(d) > 0.12:
                    v["qc"].append(tag + " — 카메라 이동/추적 확인")
        safe.atomic_json_write(OUT_JSON, OUT)
    good = [v for v in OUT.values() if v.get("ok")]
    clean = [v for v in good if not v.get("qc")]
    print("")
    print(f"성공 {len(good)}/{len(OUT)} · QC 무경고 {len(clean)} · 저장: {OUT_JSON.name}")


if __name__ == "__main__":
    main()
