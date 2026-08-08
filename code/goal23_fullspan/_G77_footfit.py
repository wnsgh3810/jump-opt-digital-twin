# -*- coding: utf-8 -*-
"""_G77_footfit — 발 롤러 전용 원 맞춤 (마라톤G, 08-09). **내부 게이트 + 각도 중앙값**.

발견 (0602 판독 중)
  방사 기울기 점수만 쓰면 "밝다→어둡다" 경계는 무엇이든 이긴다. 실제로 진 상대는
  볼트가 아니라 **종아리 링크의 밝은 가장자리**였고, 붉은 케이블이 원호를 가리면
  **반지름이 작은 쪽으로 주저앉았다** (22.25 가 정답인데 16.6/18.2/20.2 로).

  두 가지를 추가하면 갈린다.
  ① **각도 중앙값** — 평균은 원호 일부만 가려도 통째로 끌려간다. 중앙값은 버틴다.
  ② **내부 게이트** — 발은 균일하게 밝은 원판이라 안쪽(0.62~0.78R)에는 경계가 없다.
     실측: 정상 trial 의 내부 점수는 −7 ~ −21, 어긋난 trial 은 +11 이상.
     즉 "안이 깨끗한가"를 물으면 링크 가장자리·부분 가림이 전부 탈락한다.

  이 두 개가 자동 탐색 6전 6패를 끝냈다. 다만 **위치 앵커는 여전히 사람이 준다** —
  전역 탐색은 시도하지 않는다 (프레임 전체엔 균일하게 밝은 원이 여럿 있다).

정본(fs_vidscale.fit_roller)은 건드리지 않는다 — 0723 자 측정의 재현성을 지켜야 한다.
여기서는 **시드 판독 전용**으로만 쓴다.
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                        # noqa: E402

SECTORS = [(95.0, 290.0), (120.0, 240.0), (60.0, 200.0), (140.0, 260.0)]
INNER = (0.62, 0.78)        # 내부 게이트 반경 비율
INNER_MAX = 0.30            # 내부 점수 ≤ 이 비율 × 테두리 점수 여야 발
BRIGHT_IN = (0.25, 0.45, 0.60)      # 밝기 대비 — 안쪽 표본 반경 비율
BRIGHT_OUT = (1.20, 1.35)           #              바깥 표본 반경 비율
BRIGHT_MIN = 25.0           # (안 − 바깥) 평균 밝기차 [0~255]. 이보다 작으면 발이 아니다.


def _key(c, gate):
    """후보 비교 키.

    hard = (게이트 전체 통과, 점수)  — 시드 판독용
    soft = (**밝기 게이트만** 통과, 점수 − max(0, 내부))  — 추적용
      밝기는 두 모드 모두에서 **하드**다. "어두운 바닥 위 밝은 원판"은 발의 물리적 정의라
      블러로 흔들리지 않는다. 무르게 푸는 건 내부 게이트뿐이다.
    """
    if gate == "hard":
        return (c[6], c[0])
    return (c[7] >= BRIGHT_MIN, c[0] - max(0.0, c[5]))


def _ring(g, cx, cy, r, fracs, ca, sa):
    """반경 비율 목록에서 링 샘플의 평균 밝기."""
    rr = np.array([r * f for f in fracs])
    return float(VS._samp(g, cx + rr[:, None] * ca[None, :],
                          cy + rr[:, None] * sa[None, :]).mean())


def _prof(g, cx, cy, rs, sector, d=2.0):
    """각도 **중앙값** 방사 기울기 (부분 가림에 강함)."""
    ang = np.deg2rad(np.arange(sector[0], sector[1], 3.0))
    ca = np.cos(ang); sa = -np.sin(ang)
    ri = (rs[:, None] - d) * ca[None, :]; si = (rs[:, None] - d) * sa[None, :]
    ro = (rs[:, None] + d) * ca[None, :]; so = (rs[:, None] + d) * sa[None, :]
    return np.median(VS._samp(g, cx + ri, cy + si) - VS._samp(g, cx + ro, cy + so), axis=1)


def fit_foot(g, cx0, cy0, r0, *, win=20.0, win_y=None, rtol=0.18, step=1.0, refine=0.25,
             sectors=SECTORS, inner_max=INNER_MAX, gate="hard"):
    """(score, cx, cy, r, sector, inner, ok, bright) — 게이트를 통과한 최고점.

    gate="hard"  : 통과 여부를 점수보다 **우선**한다. 시드 판독용 (정지 프레임, 블러 없음).
    gate="soft"  : 점수에서 max(0, 내부)만 감점한다. **추적용**.
      왜 나누나 — 푸시 구간은 모션블러로 진짜 발도 내부 게이트를 놓친다. 거기서 hard 를
      쓰면 "게이트 통과한 엉뚱한 원"이 "게이트 놓친 진짜 발"을 이겨서 추적이 무너진다
      (실측: 0723 푸시 슬립 −42.9 → −7.7). 정지 프레임에선 hard 가 옳고 추적에선 아니다.
    """
    rs = np.arange(max(6.0, r0 * (1 - rtol)), r0 * (1 + rtol) + 1e-9, 0.25)

    def eval_at(cx, cy):
        out = None
        for sec in sectors:
            ang = np.deg2rad(np.arange(sec[0], sec[1], 6.0))
            ca, sa = np.cos(ang), -np.sin(ang)
            s = _prof(g, cx, cy, rs, sec)
            j = int(np.argmax(s))
            rj = rs[j]
            rin = np.arange(rj * INNER[0], rj * INNER[1] + 1e-9, 0.5)
            si = float(_prof(g, cx, cy, rin, sec).max())
            # ★ 밝기 대비 게이트 — 발은 **어두운 바닥 위의 밝은 금속 원판**이다.
            #   내부 게이트만으론 부족했다: 흰 플랫폼과 검은 매트의 경계도 원호를 이루고,
            #   그 원 **안쪽도 균일한 검은 매트**라 내부 게이트를 그냥 통과한다
            #   (0727 에서 7/7 이 이 함정에 빠졌다 — 점수 104~181 로 발보다 훨씬 셌다).
            #   "안이 바깥보다 밝은가"는 상대 비율이 아니라 **절대 밝기차**로 물어야 한다.
            br = (_ring(g, cx, cy, rj, BRIGHT_IN, ca, sa)
                  - _ring(g, cx, cy, rj, BRIGHT_OUT, ca, sa))
            ok = (si <= inner_max * max(s[j], 1e-6)) and (br >= BRIGHT_MIN)
            cand = (float(s[j]), float(cx), float(cy), float(rj), sec, si, ok, float(br))
            if out is None or _key(cand, gate) > _key(out, gate):
                out = cand
        return out

    wy = win if win_y is None else win_y     # ★ 세로는 **탐색창 자체를** 좁힌다.
    #   맞춘 뒤 cy 만 클램프하면 cx 는 이미 엉뚱한 데서 확정된 뒤다 —
    #   실제로 그 버그로 0723 푸시 슬립이 −42.9 → −4.9 로 무너졌다 (08-09).
    best = None
    for cy in np.arange(cy0 - wy, cy0 + wy + 1e-9, step):
        for cx in np.arange(cx0 - win, cx0 + win + 1e-9, step):
            c = eval_at(cx, cy)
            if best is None or _key(c, gate) > _key(best, gate):
                best = c
    if refine:                                  # 서브픽셀 정밀화 (1px 격자 = 슬립 계단화)
        bx, by = best[1], best[2]
        for cy in np.arange(by - step, by + step + 1e-9, refine):
            for cx in np.arange(bx - step, bx + step + 1e-9, refine):
                c = eval_at(cx, cy)
                if _key(c, gate) > _key(best, gate):
                    best = c
    return best


def track_foot(mp4, f0, f1, seed, r0, *, win_min=6.0, win_max=60.0, win_y=7.0, ds=1,
               order="fwd", rtol=0.18, step=1.0, refine=0.25, sectors=SECTORS,
               gate="soft"):
    """`fs_vidscale.track_roller` 와 같은 골격(등속예측·적응창·수직구속·역방향)에
    **맞춤만 `fit_foot` 으로 교체**한 추적기.

    골격을 그대로 둔 이유: 그 세 가지는 실제 사고로 얻은 것이고 여기서 바꿀 이유가 없다.
    바뀐 건 "무엇을 원으로 인정하는가" 하나다 — 푸시에서 창이 넓어질 때
    링크 가장자리에 지지 않게 된다.
    """
    import imageio.v3 as iio
    F = {}
    for i, f in enumerate(iio.imiter(Path(mp4))):
        if f0 <= i <= f1:
            a = np.asarray(f)
            g = a[..., :3].mean(axis=2) if a.ndim == 3 else a.astype(float)
            F[i] = (g[::ds, ::ds] if ds > 1 else g).astype(np.uint8)
        if i > f1:
            break
    ks = sorted(F)
    if order == "rev":
        ks = ks[::-1]
    # 섹터는 **첫 프레임에서 한 번 고르고 고정**한다. 가림 기하는 한 trial 안에서 거의 안 변하고,
    # 매 프레임 4섹터를 다 도는 건 4배 느리다 (푸시에서 창이 60px 로 넓어지면 치명적).
    _g0 = F[ks[0]].astype(float)
    sectors = [fit_foot(_g0, seed[0], seed[1], r0, win=win_min, rtol=rtol,
                        step=step, refine=0.0, sectors=sectors, gate="hard")[4]]
    out = {}; c = np.array(seed, float); v = np.zeros(2); r = float(r0)
    for i in ks:
        pred = c + v
        w = float(np.clip(2.5 * np.hypot(*v) + win_min, win_min, win_max))
        g = F[i].astype(float)
        sc, cx, cy, rr, sec, inn, ok, br = fit_foot(
            g, pred[0], pred[1], r, win=w, win_y=win_y, rtol=rtol, step=step,
            refine=refine, sectors=sectors, gate=gate)
        new = np.array([cx, cy])
        v = new - c if out else np.zeros(2)
        c = new
        out[i] = dict(cx=float(cx), cy=float(cy), r=float(rr), score=float(sc),
                      win=w, inner=float(inn), gate=bool(ok), bright=float(br))
    return out
