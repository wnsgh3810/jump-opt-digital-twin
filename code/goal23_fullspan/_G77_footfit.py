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


def _prof(g, cx, cy, rs, sector, d=2.0):
    """각도 **중앙값** 방사 기울기 (부분 가림에 강함)."""
    ang = np.deg2rad(np.arange(sector[0], sector[1], 3.0))
    ca = np.cos(ang); sa = -np.sin(ang)
    ri = (rs[:, None] - d) * ca[None, :]; si = (rs[:, None] - d) * sa[None, :]
    ro = (rs[:, None] + d) * ca[None, :]; so = (rs[:, None] + d) * sa[None, :]
    return np.median(VS._samp(g, cx + ri, cy + si) - VS._samp(g, cx + ro, cy + so), axis=1)


def fit_foot(g, cx0, cy0, r0, *, win=20.0, rtol=0.18, step=1.0, refine=0.25,
             sectors=SECTORS, inner_max=INNER_MAX):
    """(score, cx, cy, r, sector, inner) — 내부 게이트를 통과한 최고점.

    통과 후보가 하나도 없으면 게이트를 무시한 최고점을 돌려주되 inner 를 함께 반환하니
    호출부가 판정할 수 있다 (inner 가 양수면 의심 — 사람이 봐야 한다).
    """
    rs = np.arange(max(6.0, r0 * (1 - rtol)), r0 * (1 + rtol) + 1e-9, 0.25)

    def eval_at(cx, cy):
        out = None
        for sec in sectors:
            s = _prof(g, cx, cy, rs, sec)
            j = int(np.argmax(s))
            rj = rs[j]
            rin = np.arange(rj * INNER[0], rj * INNER[1] + 1e-9, 0.5)
            si = float(_prof(g, cx, cy, rin, sec).max())
            ok = si <= inner_max * max(s[j], 1e-6)
            cand = (float(s[j]), float(cx), float(cy), float(rj), sec, si, ok)
            if out is None or (cand[6], cand[0]) > (out[6], out[0]):
                out = cand
        return out

    best = None
    for cy in np.arange(cy0 - win, cy0 + win + 1e-9, step):
        for cx in np.arange(cx0 - win, cx0 + win + 1e-9, step):
            c = eval_at(cx, cy)
            if best is None or (c[6], c[0]) > (best[6], best[0]):
                best = c
    if refine:                                  # 서브픽셀 정밀화 (1px 격자 = 슬립 계단화)
        bx, by = best[1], best[2]
        for cy in np.arange(by - step, by + step + 1e-9, refine):
            for cx in np.arange(bx - step, bx + step + 1e-9, refine):
                c = eval_at(cx, cy)
                if (c[6], c[0]) > (best[6], best[0]):
                    best = c
    return best
