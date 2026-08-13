# -*- coding: utf-8 -*-
"""5 회차 공동 재적합 **판정 도구** (08-14 신설) — 탐색이 끝난 뒤 한 번 돌린다.

■ 무엇을 판정하나
  탐색이 찾은 값 묶음(승자)을 지금 쓰는 모델(배포 스택)과 나란히 놓고,
  **① 점수가 어디서 좋아졌나 ② 실측과 얼마나 가까워졌나 ③ 승격해도 되나** 를 답한다.

■ 왜 '점수가 내려갔다' 만으로는 승격할 수 없나
  점수는 여러 판의 가중 합이라, 한 판을 크게 얻고 다른 판을 조금씩 내주면 총점이
  내려간다. 그런데 우리가 원하는 것은 **물리적으로 옳은 값**이다. 그래서 세 가지를 따로 본다.
    · 갈림 신호 1 — 탐색이 **실측을 모른 채** 실측 근처에 앉았는가 (독립 확인)
    · 갈림 신호 2 — 매달림(무릎 고정)은 좋아졌는데 **변속기 일어서기만** 안 좋아졌는가
                    (그렇다면 값이 아니라 구조 문제로 확정 — 다음 단계가 갈린다)
    · 갈림 신호 3 — 4 판 연속 범위 끝에 붙어 있던 **총질량이 떨어졌는가**
                    (마찰·환산이 제 몫을 찾으면 질량이 대신 떠맡던 것을 놓아야 정상)

■ 이 도구는 아무것도 승격하지 않는다. 표만 낸다. 승격은 사용자가 결정한다.

사용법: python _GHC_judge5.py [태그]      (기본 태그 5)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("FS_SWEEP_AIR", "1")
os.environ.setdefault("FS_SWEEP_S2S", "1")
os.environ.setdefault("FS_SWEEP_CVT", "1")

import _GHB_sweep as S           # noqa: E402
import fs_data as FD             # noqa: E402

TAG = sys.argv[1] if len(sys.argv) > 1 else "5"

# 실측으로 알고 있는 값 (탐색은 이걸 모른 채 돌았다 — 가까이 오면 독립 확인이다)
#   각 항목: (축 이름, 실측값, 실측 출처, 얼마나 가까우면 '일치'로 볼지 [비율])
MEASURED = {
    "무릎 건마찰": (0.423, "공중 일어서기 6기록 11만 표본, 같은 자세 상행-하행 차이의 절반", 0.30),
    "힙 건마찰": (0.280, "매달림 방향분해 08-11", 0.30),
    "무릎 속도비례": (0.034, "위와 같은 실측의 속도 기울기", 1.00),
    "힙 속도비례": (0.000, "속도 37배에도 마찰 0.28→0.22 (거의 평평)", None),
    "총질량": (3.280, "케이블 제거 저울 실측 3.26~3.30", 0.01),
    "힙 모터축 관성": (0.0164, "모터 끈 자유 흔들림 (범위 0.0145~0.0193)", 0.25),
    # ☠ 08-14 철회 — 이 두 축은 **실측을 그대로 넣으면 안 된다**는 것이 시험으로 확인됐다.
    #   1.85/13 을 넣으면 점프 주입 +43% · 폐루프 토크 +46% · 점프 높이 +140% 로 무너지고,
    #   다른 실측값을 같이 넣어도 회수가 안 된다. 이유(유력): ①분동이 잰 비율에는 전동계
    #   마찰이 이미 섞여 있는데 모델은 그 마찰을 따로 갖고 있어 **두 번 세는 것** ②분동 검증
    #   범위는 명령 0~11.5 뿐인데 점프는 37 까지 쓴다(**범위 밖 외삽**).
    #   ⇒ 실측값은 참고로만 적어 두고, **일치 여부를 판정 근거로 쓰지 않는다** (tol=None).
    "환산 비율 (작은 토크)": (1.85, "분동 곡선 재현값 — 그대로 넣으면 안 됨 (08-14 시험)", None),
    "환산 비율 깎임 (큰 토크)": (13.0, "분동 곡선 재현값 — 그대로 넣으면 안 됨 (08-14 시험)", None),
}


def _axes():
    return [a[0] for a in S.COMMON] + ["무릎 보정상한", "힙 보정상한"]


def _bounds():
    lo = [a[1] for a in S.COMMON] + [2.0, 1.2]
    hi = [a[2] for a in S.COMMON] + [12.0, 10.0]
    return lo, hi


def load_winner(tag):
    p = HERE / f"_GHB_sweep{tag}.json"
    if not p.exists():
        print(f"[중단] {p.name} 이 없다 — 탐색이 아직 안 끝났거나 태그가 다르다.")
        sys.exit(2)
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    r = d["res"]["canon_cap"]
    return np.asarray(r["x"], float), r


def per_record_air():
    """매달림 기록별 성적 — 어느 기록이 좋아졌는지 봐야 '무엇이 고쳐졌나' 를 안다."""
    import collections
    g = collections.defaultdict(list)
    for nm, v in S.air_board():
        g[nm].append(float(np.mean(v)))
    return {nm: float(np.mean(x)) for nm, x in g.items()}


def per_case_s2s():
    """일어서기 경우별 성적 — 변속기 유무로 갈리는지가 핵심이다."""
    import fs_runner as FR, fs_cvt as FC
    m0 = float(os.environ.get("FS_MASS", "3.30"))
    keep = os.environ.get("FS_MASS")
    out = {}
    try:
        for sub, pay, cvt, d, W in (S._S or []):
            per = []
            try:
                os.environ["FS_MASS"] = f"{m0 + pay:.4f}"
                FR._CACHE.clear(); S._CVT_STAMPED.clear()
                ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
                t = d["t"]
                for w0, w1 in W:
                    mm = (t >= w0) & (t <= w1)
                    if mm.sum() < 20:
                        continue
                    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
                    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                                           float(d["q1"][i0]), float(d["q2"][i0]),
                                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                                           float(tg[-1] - 0.004), fade=True)
                    if L is None:
                        continue
                    gf = lambda k: np.interp(tg, L["t"], L[k])   # noqa: E731
                    sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                    v = [S._r80(tg, d[k][mm], sm, floor=fl)
                         for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
                    if all(np.isfinite(v)):
                        per.append(float(np.mean([min(x, 10.0) for x in v])))
            except Exception:
                per = []
            out[sub] = float(np.mean(per)) if per else 3.0
    finally:
        if keep is None:
            os.environ.pop("FS_MASS", None)
        else:
            os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return out


def snap(x):
    """이 값 묶음으로 모든 판을 한 번씩 재서 돌려준다."""
    S._apply(S.env_of("canon_cap", np.asarray(x, float)))
    v, det = S.evaluate(("canon_cap", np.asarray(x, float)))
    S._apply(S.env_of("canon_cap", np.asarray(x, float)))
    air = per_record_air()
    s2s = per_case_s2s()
    return v, det, air, s2s


def main():
    print(f"\n{'#'*78}\n# 5 회차 판정 — 탐색 승자 vs 지금 쓰는 모델\n{'#'*78}")
    xw, r = load_winner(TAG)
    S._ensure()
    xd = np.asarray(S.DEPLOY, float)
    ax = _axes(); lo, hi = _bounds()

    print(f"\n■ 탐색 요약: 평가 {r.get('nfev','?')} 회 · {r.get('minutes',0)/60:.1f} 시간 "
          f"· 승자 점수 {r.get('score', float('nan')):.5f}")

    print("\n■ 1. 값이 어디로 갔나 (0 이 완벽인 점수와 달리, 여기는 물리값 그 자체다)")
    print(f"{'축':22s} {'지금':>12s} {'승자':>12s} {'변화':>9s} {'범위 안 위치':>12s}  실측 대조")
    print("-" * 118)
    sat = []
    for i, nm in enumerate(ax):
        a, b = float(xd[i]), float(xw[i])
        pos = (b - lo[i]) / (hi[i] - lo[i]) if hi[i] > lo[i] else 0.5
        tag = ""
        if pos > 0.97 or pos < 0.03:
            tag = "  ← 범위 끝에 붙음"
            sat.append(nm)
        m = MEASURED.get(nm)
        mtxt = ""
        if m:
            mv, _src, tol = m
            if tol is None:
                mtxt = f"실측 ≈{mv:g} (평평)"
            else:
                near = abs(b - mv) <= tol * max(abs(mv), 1e-9)
                was = abs(a - mv) <= tol * max(abs(mv), 1e-9)
                mtxt = (f"실측 {mv:g} → {'★일치' if near else '불일치'}"
                        f"{' (전에도 일치)' if was and near else ''}")
        print(f"{nm:22s} {a:12.5f} {b:12.5f} {100*(b-a)/max(abs(a),1e-9):8.1f}% "
              f"{100*pos:11.1f}%{tag}  {mtxt}")
    print("-" * 118)

    print("\n■ 2. 점수 (전부 **0 이 완벽**, 클수록 부정확)")
    vd, dd, aird, s2sd = snap(xd)
    vw, dw, airw, s2sw = snap(xw)
    rows = [("측정 토크 주입 재생 (점프)", "ma"), ("PD 흉내 각도·속도 (점프)", "clq"),
            ("PD 흉내 토크 (점프, 명령끼리)", "clt"), ("점프 높이", "h"),
            ("매달림 15 기록", "air"), ("짐 지고 일어서기 4 경우", "s2s"),
            ("총점(벌점 포함)", None)]
    print(f"{'판':32s} {'지금':>10s} {'승자':>10s} {'변화':>9s}")
    print("-" * 66)
    for lab, k in rows:
        a = vd if k is None else dd.get(k, float("nan"))
        b = vw if k is None else dw.get(k, float("nan"))
        print(f"{lab:32s} {a:10.5f} {b:10.5f} {100*(b-a)/max(abs(a),1e-9):8.1f}%")
    print("-" * 66)
    print(f"{'벌점 (0 이어야 승격 가능)':32s} {dd.get('pen',0):10.3f} {dw.get('pen',0):10.3f}")

    print("\n■ 3. 검증 전용 세션 (적합에 안 쓴 것 — 1.00 이 같음, 넘으면 나빠진 것)")
    for k in dw.get("gate", {}):
        print(f"  {k:22s} {dd['gate'].get(k, float('nan')):8.4f} → {dw['gate'][k]:8.4f}")

    print("\n■ 4. 매달림 기록별 (0 이 완벽)")
    print(f"{'기록':26s} {'지금':>8s} {'승자':>8s} {'변화':>8s}")
    print("-" * 56)
    for nm in sorted(set(aird) | set(airw), key=lambda z: -airw.get(z, 9)):
        a, b = aird.get(nm, float("nan")), airw.get(nm, float("nan"))
        print(f"{nm:26s} {a:8.3f} {b:8.3f} {100*(b-a)/max(abs(a),1e-9):7.1f}%")

    print("\n■ 5. 짐 지고 일어서기 경우별 (0 이 완벽) — **갈림 신호 2**")
    print(f"{'경우':22s} {'지금':>8s} {'승자':>8s} {'변화':>8s}")
    print("-" * 52)
    for nm in sorted(set(s2sd) | set(s2sw)):
        a, b = s2sd.get(nm, float("nan")), s2sw.get(nm, float("nan"))
        print(f"{nm:22s} {a:8.3f} {b:8.3f} {100*(b-a)/max(abs(a),1e-9):7.1f}%")

    print("\n■ 6. 갈림 신호 판정")
    hits = [nm for nm in MEASURED
            if MEASURED[nm][2] is not None and nm in ax
            and abs(xw[ax.index(nm)] - MEASURED[nm][0]) <= MEASURED[nm][2] * abs(MEASURED[nm][0])]
    print(f"  1) 실측과 독립 일치: {len(hits)} 개 — {', '.join(hits) if hits else '없음'}")
    cvt_c = [k for k in s2sw if k.startswith("cvt")]
    ncvt_c = [k for k in s2sw if k.startswith("no_cvt")]
    if cvt_c and ncvt_c:
        dc = np.mean([s2sw[k] - s2sd[k] for k in cvt_c])
        dn = np.mean([s2sw[k] - s2sd[k] for k in ncvt_c])
        print(f"  2) 변속기 일어서기 변화 {dc:+.3f} · 무변속 {dn:+.3f}  → "
              + ("무변속만 좋아짐 = **구조 문제 확정, 다음은 변속기 기하·마찰**"
                 if (dn < -0.05 and dc > -0.05) else "둘 다 같은 방향 (값 문제 쪽)"))
    im = ax.index("총질량")
    print(f"  3) 총질량 {xd[im]:.4f} → {xw[im]:.4f} (상한 {hi[im]}) — "
          + ("**상한에서 떨어졌다 = 대리 흡수 해소 신호**" if xw[im] < hi[im] - 0.005
             else "여전히 상한에 붙어 있다 = 아직 무언가를 대신 떠맡는 중"))
    print(f"\n  범위 끝에 붙은 축 {len(sat)} 개: {', '.join(sat) if sat else '없음'}"
          + ("   (승격 조건은 1 개 이하)" if sat else ""))

    out = HERE / f"_GHC_judge{TAG}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(x_win=list(map(float, xw)), x_dep=list(map(float, xd)), axes=ax,
                       det_win=dw, det_dep=dd, air_win=airw, air_dep=aird,
                       s2s_win=s2sw, s2s_dep=s2sd, saturated=sat, measured_hits=hits),
                  f, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장 → {out.name}")


if __name__ == "__main__":
    main()
