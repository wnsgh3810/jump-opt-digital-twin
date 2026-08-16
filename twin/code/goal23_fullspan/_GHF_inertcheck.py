# -*- coding: utf-8 -*-
"""_GHF_inertcheck — 공중 식별이 잡은 것이 **정말 관성인가** 를 검산한다 (마라톤H, 08-12).

왜 (사용자 지적 08-12: "+77%는 너무 심한데 · 공중 식별에서 해석 못한 지점이 있을 수도")
  공중 흔들기 데이터는 힙 모터축 관성을 0.010 → 0.050 으로 올리라고 한다(오차 −11.4%).
  그런데 그 값을 도약 판에 넣으면 세션에 따라 **+78% 까지 무너진다.**
  둘 다 옳을 수는 없다. 공중 쪽 해석부터 검산한다.

검산 원리 — **관성은 속도와 무관해야 한다**
  회전 관성은 각가속도를 거스르는 성질이고, **얼마나 빨리 도는지와 무관**하다.
  반면 마찰·점성·전류 한계 같은 것들은 **속도에 따라 달라진다.**
  ⇒ 흔드는 속도로 조각을 나눠 각 무리마다 "가장 잘 맞는 관성"을 따로 찾는다.
    · 무리마다 같은 값이 나오면 → **진짜 관성이다.**
    · 속도가 빠른 무리일수록 큰 값을 요구하면 → **관성이 아니라 속도 의존 현상**이고,
      내가 그것을 관성으로 잘못 읽은 것이다.

  같은 방식으로 **자료원별**(주파수 쓸기 vs 느린 왕복)로도 나눠 본다.

CLI: python _GHF_inertcheck.py
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHF_inertcheck.json"
sys.path.insert(0, str(HERE))
import _GHE_inertia as GE          # 자료 읽기·재생 함수를 그대로 쓴다 (같은 판이어야 비교가 된다)

ARMS = [0.010, 0.015, 0.020, 0.030, 0.040, 0.060]     # 힙 모터축 관성 [kg·m²] · 현행 0.010
NBIN = 3


def segs_all(d, win=GE.WIN, stride=0.5):
    """기록 전체에 고르게 조각을 깐다 (가속 큰 것만 고르지 않는다 — 속도별로 나눌 것이므로)."""
    t = d["t"]; dt = float(np.median(np.diff(t))); nw = int(win / dt); ns = max(1, int(stride / dt))
    return [int(i) for i in range(0, len(t) - nw - 1, ns)], nw


def main():
    import fs_runner as FR, fs_metric as FMET
    P = FMET.tw0["P"]; A = P.A_PAPER
    D = {f: GE.load(GE.DATA / f) for f in GE.FOLDS if (GE.DATA / f / "hip.xlsx").exists()}
    # 조각마다 평균 힙 속도를 재서 속도 무리를 나눈다
    META = {}
    for f, d in D.items():
        s, nw = segs_all(d)
        sp = np.array([np.mean(np.abs(d["v1"][a:a + nw])) for a in s])
        META[f] = (s, nw, sp)
    # ★ 08-12 결함 발견: 기록 전체에 조각을 깔면 **대부분이 거의 안 움직이는 구간**이라
    #   무리가 안 갈리고(경계 0.05·0.05), 게다가 정지 조각에서는 관성을 키울수록 다리가
    #   덜 움직여 **무조건 오차가 준다** — 식별이 아니라 퇴화다.
    #   ⇒ 실제로 움직이는 조각(평균 힙 속도 0.15 rad/s 이상)만 남기고 나눈다.
    VMIN = 0.15
    for f in list(META):
        s0, nw0, sp0 = META[f]
        k = [i for i, v in enumerate(sp0) if v >= VMIN]
        META[f] = ([s0[i] for i in k], nw0, sp0[k])
    allsp = np.concatenate([m[2] for m in META.values() if len(m[2])])
    ed = np.percentile(allsp, np.linspace(0, 100, NBIN + 1))
    print(f"  (움직이는 조각만: 평균 힙 속도 {VMIN} rad/s 이상 · "
          f"{sum(len(m[0]) for m in META.values())} 개 남음)")
    print("공중 식별이 잡은 것이 정말 관성인가 — **속도 무리별로 따로** 찾아본다\n")
    print("  회전 관성은 속도와 무관해야 한다. 무리마다 답이 다르면 관성이 아니다.")
    print(f"  힙 속도 무리 경계 [rad/s]: " + " · ".join(f"{x:.2f}" for x in ed) + "\n")
    print(f"{'무리':22s} {'조각수':>6s} | " + " ".join(f"{a:>7.3f}" for a in ARMS) + " | 최적")
    RES = {}
    for bi in range(NBIN):
        rows = []
        for arm in ARMS:
            os.environ["FS_HIPM_ARM"] = f"{arm}"
            FR._S2S = None
            ft = FR.fs_twin(); tmap = FR._tmap_init(P, A)
            KS = float(os.environ.get("FS_KS_HIP", "150"))
            E = []
            for f, d in D.items():
                s, nw, sp = META[f]
                sel = [a for a, v in zip(s, sp) if ed[bi] <= v <= ed[bi + 1]]
                if not sel:
                    continue
                r = GE.run(ft, d, sel, nw, tmap, KS)
                if r is not None:
                    E.append(r)
            rows.append(np.median(np.vstack(E)[:, 0]) if E else np.nan)
        os.environ.pop("FS_HIPM_ARM", None); FR._S2S = None
        n = sum(len([a for a, v in zip(META[f][0], META[f][2])
                     if ed[bi] <= v <= ed[bi + 1]]) for f in D)
        best = ARMS[int(np.nanargmin(rows))] if np.any(np.isfinite(rows)) else np.nan
        RES[f"speed_bin{bi}"] = dict(lo=float(ed[bi]), hi=float(ed[bi + 1]),
                                     errs=list(map(float, rows)), best=float(best), n=n)
        print(f"{f'속도 {ed[bi]:.2f}~{ed[bi+1]:.2f}':22s} {n:6d} | "
              + " ".join(f"{x:7.3f}" for x in rows) + f" | **{best:.3f}**", flush=True)
    print("\n자료원별 (같은 속도 조건이 아니므로 참고용)")
    print(f"{'자료원':22s} {'조각수':>6s} | " + " ".join(f"{a:>7.3f}" for a in ARMS) + " | 최적")
    for f, d in D.items():
        rows = []
        for arm in ARMS:
            os.environ["FS_HIPM_ARM"] = f"{arm}"
            FR._S2S = None
            ft = FR.fs_twin(); tmap = FR._tmap_init(P, A)
            s, nw, sp = META[f]
            r = GE.run(ft, d, s, nw, tmap, float(os.environ.get("FS_KS_HIP", "150")))
            rows.append(np.median(r[:, 0]) if r is not None else np.nan)
        os.environ.pop("FS_HIPM_ARM", None); FR._S2S = None
        best = ARMS[int(np.nanargmin(rows))] if np.any(np.isfinite(rows)) else np.nan
        RES[f] = dict(errs=list(map(float, rows)), best=float(best), n=len(META[f][0]))
        print(f"{f.split('/')[-1][:20]:22s} {len(META[f][0]):6d} | "
              + " ".join(f"{x:7.3f}" for x in rows) + f" | **{best:.3f}**", flush=True)
    import safe
    safe.atomic_json_write(OUT, RES)
    print(f"\n저장 → {OUT}")
    print("※ 속도 무리마다 최적값이 같으면 진짜 관성. 빠를수록 큰 값을 요구하면 관성이 아니다.")


if __name__ == "__main__":
    main()
