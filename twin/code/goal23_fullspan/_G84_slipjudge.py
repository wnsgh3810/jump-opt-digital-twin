# -*- coding: utf-8 -*-
"""_G84_slipjudge — **새 Ê_slip 의 그림자 채점** (마라톤G, 08-09).

이건 지표 변경이 아니다. `_G13_board.py` 의 J_G 는 손대지 않는다.
"만약 슬립 항을 영상 실측 기반으로 바꾸면 지금 트윈이 몇 점인가"를 **따로** 본다.
지표 변경은 사용자 승인 사항이다 (마라톤 규약: 지표 선고정).

무엇을 채점하나 (G83 결론)
  현행 J_G 의 슬립 항은 `slip_기하` — **모델이 만든 양**이라 모델을 모델로 채점한다
  (REJECTED #75 에 이미 기각). 대신 55 trial 전수 영상 실측을 쓴다.

  ★ 대상 구간 = **하강**(t_desc → 스쿼트 바닥). 푸시가 아니다.
    하강 슬립은 세션 안에서 0.4~1.3mm 로 재현되는데(세션 상수) 푸시는 같은 세션·같은 게인에서도
    수 mm~수십 mm 흔들린다(trial 사건). 주사위로는 지표를 만들 수 없다.

  ★ 세션당 스칼라 1개 (trial 중앙값). trial 마다 채점하면 trial 수가 많은 세션이 지배하고,
    "그 세션만 맞추는" 백도어가 열린다.

```
Ê_slip,신 = mean_세션 |하강슬립_sim,중앙 − 하강슬립_영상,중앙| / mean_세션 |하강슬립_영상,중앙|
```

CLI: python _G84_slipjudge.py [tag]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402
from _G10_energy import Reduced                               # noqa: E402

MEAS = HERE / "_G72_slipall.json"
OUT = HERE / "_G84_slipjudge.json"


def measured():
    """영상 실측 하강 슬립 — {(세션, trial): mm}. QC 3개 이상은 버린다."""
    d = json.load(io.open(MEAS, encoding="utf-8"))
    out = {}
    for k, v in d.items():
        if not (v.get("ok") and v.get("seg")):
            continue
        if len(v.get("qc", [])) >= 3:              # 신뢰 못 할 것은 채점에서 제외
            continue
        g = v["seg"]
        out[(v["sess"], v["trial"])] = g["하강전반"]["slip"] + g["하강후반"]["slip"]
    return out


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "현재"
    M = measured()
    R = Reduced(FR.fs_twin())
    ft = FR.fs_twin(); SP = FR._sess_params()
    print(f"그림자 슬립 채점: tag={tag} · 실측 {len(M)} trial · r={R.r*1000:.1f}mm")
    rows = []
    skipped_cvt = []
    for s, p, g, cvt, ho in FD.registry():
        key = (s, p.name)
        if key not in M:
            continue
        if cvt:
            # ★ CVT 세션은 여기서 채점하지 않는다.
            #   실측(fs_slipmeas)은 ReducedCVT 로 바로잡았지만, **sim 쪽 플랜트가 무변속 모델**이다
            #   (FR.fs_twin() = l_i 30mm). 기구학만 고쳐도 동역학이 다른 모델로 재생하는 셈이라
            #   비교가 성립하지 않는다. CVT 채점은 build_cvt_pair 기반으로 따로 만들어야 한다
            #   (fs_compare_cvt.py 계보). 08-09.
            skipped_cvt.append(key)
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            if seg is None:
                continue
            # ★ 창은 **하강 구간**이다 (plot_window 가 아니다).
            #   plot_window 는 점프창(푸시+체공)이라 길이가 0.16s 뿐이고 하강보다 3.8초 뒤다 —
            #   그 창으로는 하강 슬립을 원리적으로 채점할 수 없다 (실측으로 확인, 08-09).
            tt = d["t"]
            i0 = int(np.argmin(np.abs(tt - float(seg["t_desc"]))))
            i1 = int(seg["i_bot"])
            if i1 - i0 < 50:
                continue
            m2 = (tt >= tt[i0]) & (tt <= tt[min(len(tt) - 1, i1 + 20)])
            t = tt[m2] - tt[i0]
            sp = SP.get(s, dict(bias1=0.0, knee_deep=None))
            if os.environ.get("FS_NOBIAS") == "1":
                sp = dict(sp, bias1=0.0)
            if os.environ.get("FS_NODEEP") == "1":
                sp = dict(sp, knee_deep=None)
            L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m2], d["raw2"][m2],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(t[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            tb = float(tt[i1] - tt[i0])
            sel = (L["t"] >= 0.0) & (L["t"] <= tb)
            if sel.sum() < 5:
                continue
            x = np.asarray(L["xf"])[sel]; th = np.asarray(L["thf"])[sel]
            sim = ((x[-1] - x[0]) - R.r * (th[-1] - th[0])) * 1000.0
            # 개루프 재생이 하강 3초를 버티는지 함께 본다 — 못 버티면 슬립 비교도 무의미하다
            ts = tt[i0:i1 + 1] - tt[i0]
            gm = lambda k: np.interp(ts, L["t"], L[k])
            # ★ 차이를 **먼저 빼고** degrees 로 바꾼다 — 원본 q 는 rad 이다
            #   (degrees(sim) − rad(real) 로 쓰면 RMSE 가 150° 로 나온다. _G13_board 와 동일 규약)
            eq1 = float(np.sqrt(np.mean(np.degrees(gm("thm1") - d["q1"][i0:i1 + 1]) ** 2)))
            eq2 = float(np.sqrt(np.mean(np.degrees(gm("q2") - d["q2"][i0:i1 + 1]) ** 2)))
            rows.append(dict(s=s, trial=p.name, ho=ho, cvt=cvt, sim=float(sim),
                             real=float(M[key]), eq1=eq1, eq2=eq2, dur=tb))
            print(f"  {s}/{p.name:<22s} sim {sim:+7.2f}  실측 {M[key]:+7.2f}  "
                  f"차 {sim - M[key]:+7.2f} mm   (하강 {tb:.2f}s · q1 {eq1:.1f}° q2 {eq2:.1f}°)",
                  flush=True)
        except Exception as ex:
            print(f"  {s}/{p.name}: ERR {type(ex).__name__} {str(ex)[:60]}", flush=True)
    if skipped_cvt:
        print(f"\n[제외] CVT 세션 {len(skipped_cvt)} trial — sim 플랜트가 무변속 모델이라 비교 불가")
    if not rows:
        raise SystemExit("채점 대상 없음 — 측정 JSON 또는 registry 확인")

    by = {}
    for r in rows:
        by.setdefault(r["s"], []).append(r)
    print(f"\n{'세션':10s}{'n':>3}{'sim 중앙':>10}{'실측 중앙':>11}{'차':>9}")
    num = den = 0.0; ns = 0
    for s in sorted(by):
        v = by[s]
        a = float(np.median([x["sim"] for x in v]))
        b = float(np.median([x["real"] for x in v]))
        print(f"{s:10s}{len(v):3d}{a:10.2f}{b:11.2f}{a-b:9.2f}")
        num += abs(a - b); den += abs(b); ns += 1
    E = num / max(den, 1e-9)
    print(f"\n**Ê_slip,신 = {E:.4f}**  (세션 {ns}개 · 낮을수록 좋음 · 1.0 = 실측만큼 틀림)")
    print(f"  분자 mean|sim−real| = {num/ns:.2f} mm · 분모 mean|real| = {den/ns:.2f} mm")
    json.dump(dict(tag=tag, E_slip_new=E, n_sess=ns, rows=rows),
              io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"저장 {OUT.name}")


if __name__ == "__main__":
    main()
