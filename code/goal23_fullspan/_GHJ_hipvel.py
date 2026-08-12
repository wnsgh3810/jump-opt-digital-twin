# -*- coding: utf-8 -*-
"""_GHJ_hipvel — **힙 속도를 왜 못 맞히는가**를 해부한다 (마라톤H, 08-12).

왜 이게 1순위인가 (08-12 냉정 진단)
  측정 토크를 그대로 넣고 돌렸을 때(PD 제어 없음) 오차를 **그 채널이 실제로 움직인 폭**
  으로 나눠 보면:  힙 각도 14.6% · 무릎 각도 10.5% · **힙 속도 46.7%** · 무릎 속도 23.9%.
  기록 잡음이 만드는 바닥은 7~10% 이므로 **힙 속도 오차는 잡음의 5배 = 진짜 모델 오차**다.
  게다가 26.07.22 / 26.07.25 는 86~89% — 사실상 그 채널을 예측하지 못한다.
  토크는 속도보다 한 단계 더 민감하므로(가속도에 비례), 이 연구의 합격 기준
  "계획 토크 = 실제 토크" 에 가장 직결된 양을 지금 못 맞히고 있다는 뜻이다.

무엇으로 가르나 — 오차를 세 몫으로 쪼갠다
  ① **시간이 밀린 몫**: 시뮬 속도 파형을 앞뒤로 밀어 실측과 가장 잘 겹치는 지점을 찾는다.
     밀어서 좋아지면 원인은 **타이밍**(명령 지연·접촉 시점)이다.
  ② **크기가 다른 몫**: 가장 잘 겹친 상태에서 시뮬을 몇 배 해야 실측이 되는가.
     1.0 이면 크기는 맞다. 1 보다 작으면 시뮬이 **약하게** 움직인다.
  ③ **모양이 다른 몫**: ①②를 다 맞춘 뒤에도 남는 것. 이게 크면 **파형 자체가 다르다**
     = 힘의 시간 프로파일이 틀렸다는 뜻이고, 값 맞추기로는 안 줄어든다.

  구간도 나눈다: 웅크리며 내려갈 때 / 바닥에서 방향 바꿀 때 / 밀어낼 때 / 발이 떨어진 뒤.
  어느 구간에서 생기는지 알면 무엇이 빠졌는지가 좁혀진다.

CLI: python _GHJ_hipvel.py
"""
import os, sys, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHJ_hipvel.json"

# 현행 런타임 스택 (CURRENT_STACK.md H3_260812)
STACK = dict(FS_TMAP="canon_cap", FS_TDCAP="3.733,2.309", FS_MASS="3.2988",
             FS_FOOTR="0.020", FS_NOSUPP="1", FS_NOSPR="1", FS_NOBIAS="1",
             FS_NODEEP="1", FS_PRESLIDE="0.86,0.85,0.02,1.0",
             FS_CMD_LPF="0.00317,0.00292", FS_IMPRATIO="20",
             FS_KNEEM_FL="0.2880", FS_KNEEM_DAMP="0.1617", FS_HIPM_FL="0.3026",
             FS_HIPM_DAMP="0.0964", FS_KS_HIP="138.53", FS_COMZ="thigh=-0.00189")
for _k, _v in STACK.items():
    os.environ.setdefault(_k, _v)

LAGS = np.arange(-40, 41)        # 밀어 볼 범위 [샘플] · 2ms 간격이므로 ±80ms


def decompose(real, sim, dt):
    """오차를 (시간 밀림, 크기 배율, 남는 모양) 으로 쪼갠다.

    반환 dict:
      raw   = 그대로 비교한 오차 RMS
      lag   = 가장 잘 겹치는 밀림 [ms] (양수 = 시뮬이 늦다)
      after_lag = 밀린 것만 맞춘 뒤의 오차 RMS
      gain  = **실측 ÷ 시뮬** 크기 배율 (최소제곱). 1.0 이면 크기 일치.
              1 보다 **작으면 시뮬이 실측보다 크게** 움직인다는 뜻이다 (실측이 더 작으므로).
              ☠ 08-12 첫 판에 이 방향을 반대로 적었다 — 진단이 뒤집히는 실수였다.
      resid = 밀림·크기 다 맞춘 뒤 남는 오차 RMS  ← **이게 진짜 모양 차이**
      band  = 실측 변동 폭 (평균 제거 RMS) — 위 값들을 나눌 분모
    """
    r = np.asarray(real, float); s = np.asarray(sim, float)
    n = len(r)
    band = float(np.std(r))
    raw = float(np.sqrt(np.mean((r - s) ** 2)))
    rc = r - r.mean(); sc = s - s.mean()
    best = (1e9, 0)
    for L in LAGS:
        if L >= 0:
            a, b = rc[L:], sc[:n - L] if L else sc
        else:
            a, b = rc[:n + L], sc[-L:]
        if len(a) < n // 2:
            continue
        e = float(np.sqrt(np.mean((a - b) ** 2)))
        if e < best[0]:
            best = (e, int(L))
    after, L = best
    if L >= 0:
        a, b = rc[L:], (sc[:n - L] if L else sc)
    else:
        a, b = rc[:n + L], sc[-L:]
    g = float(np.dot(a, b) / max(np.dot(b, b), 1e-12))     # 최소제곱 배율
    resid = float(np.sqrt(np.mean((a - g * b) ** 2)))
    return dict(raw=raw, lag_ms=L * dt * 1000, after_lag=after,
                gain=g, resid=resid, band=band)


def main():
    import safe
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
    import fs_cvt as FC
    ft0 = FR.fs_twin()
    R = collections.defaultdict(list)
    SEGN = ("하강", "전환", "밀기", "이륙후")
    for s, p, g, cvt, ho in FD.registry():
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m)); tg = t[m] - t[i0]
            dt = float(np.median(np.diff(t)))
            ft = FC.cvt_ft(d["l_i"], ft_base=ft0) if cvt else ft0
            sp = CP.sess_params(s)
            L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(tg[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is None:
                continue
            gi = lambda k: np.interp(tg, L["t"], L[k])
            sim = dict(dq1=gi("dq1"), dq2=gi("dq2"), q1=gi("thm1"), q2=gi("q2"))
            idx = np.where(m)[0]
            cut = {}
            for nm, a, b in (("하강", seg["i_desc"], seg["i_bot"]),
                             ("전환", seg["i_bot"], seg["i_push"]),
                             ("밀기", seg["i_push"], seg["i_lo"]),
                             ("이륙후", seg["i_lo"], idx[-1] + 1)):
                sel = (idx >= a) & (idx < b)
                cut[nm] = sel
            for ch in ("dq1", "dq2"):
                real = np.asarray(d[ch])[m]
                dec = decompose(real, sim[ch], dt)
                dec.update(sess=s, trial=p.name, ch=ch)
                for nm in SEGN:
                    sel = cut[nm]
                    if sel.sum() > 10:
                        rr, ss = real[sel], sim[ch][sel]
                        dec[f"seg_{nm}"] = float(np.sqrt(np.mean((rr - ss) ** 2)))
                        dec[f"band_{nm}"] = float(np.std(rr))
                R[s].append(dec)
        except Exception as ex:
            print(f"  {s}/{p.name}: {type(ex).__name__} {ex}", flush=True)
    # ── 표 1: 오차를 세 몫으로 쪼개기 ────────────────────────────────────────────
    print("측정 토크를 그대로 넣고 돌렸을 때의 **속도 오차**를 세 몫으로 쪼갠다")
    print("  (전부 그 채널이 실제로 움직인 폭으로 나눈 % · 0% 면 완벽)\n")
    for ch, lab in (("dq1", "힙 속도"), ("dq2", "무릎 속도")):
        print(f"■ {lab}")
        print(f"  {'세션':11s} {'n':>3s} | {'그대로':>7s} {'밀림후':>7s} {'남는모양':>8s} | "
              f"{'밀림[ms]':>9s} {'크기배율':>8s}")
        tot = collections.defaultdict(list)
        for s in sorted(R):
            rows = [x for x in R[s] if x["ch"] == ch]
            if not rows:
                continue
            f = lambda k: np.mean([x[k] / x["band"] * 100 for x in rows])
            lag = np.mean([x["lag_ms"] for x in rows])
            gn = np.mean([x["gain"] for x in rows])
            print(f"  {s:11s} {len(rows):3d} | {f('raw'):6.1f}% {f('after_lag'):6.1f}% "
                  f"{f('resid'):7.1f}% | {lag:+8.1f} {gn:8.3f}")
            tot["raw"].append(f("raw")); tot["after"].append(f("after_lag"))
            tot["resid"].append(f("resid")); tot["lag"].append(lag); tot["gain"].append(gn)
        print(f"  {'평균':11s} {'':3s} | {np.mean(tot['raw']):6.1f}% "
              f"{np.mean(tot['after']):6.1f}% {np.mean(tot['resid']):7.1f}% | "
              f"{np.mean(tot['lag']):+8.1f} {np.mean(tot['gain']):8.3f}\n")
    # ── 표 2: 구간별 ────────────────────────────────────────────────────────────
    print("구간별로 어디서 생기나 (오차 ÷ 그 구간 변동 폭, %)\n")
    for ch, lab in (("dq1", "힙 속도"), ("dq2", "무릎 속도")):
        print(f"■ {lab}")
        print(f"  {'세션':11s} | " + " ".join(f"{n:>8s}" for n in SEGN))
        for s in sorted(R):
            rows = [x for x in R[s] if x["ch"] == ch]
            if not rows:
                continue
            cells = []
            for nm in SEGN:
                v = [x[f"seg_{nm}"] / max(x[f"band_{nm}"], 1e-9) * 100
                     for x in rows if f"seg_{nm}" in x and x[f"band_{nm}"] > 1e-6]
                cells.append(f"{np.mean(v):7.1f}%" if v else f"{'-':>8s}")
            print(f"  {s:11s} | " + " ".join(cells))
        print()
    safe.atomic_json_write(OUT, {s: R[s] for s in R})
    print(f"저장 → {OUT}")
    print("\n※ '그대로' = 아무 보정 없이 잰 오차 · '밀림후' = 시뮬 파형을 시간축으로 밀어")
    print("   가장 잘 겹치게 한 뒤의 오차 · '남는모양' = 밀림과 크기를 둘 다 맞춘 뒤에도")
    print("   남는 오차. **남는모양이 크면 파형 자체가 다르다 = 값 맞추기로는 못 고친다.**")
    print("   '밀림' 양수 = 시뮬이 실측보다 **늦다**")
    print("   '크기배율' = **실측 ÷ 시뮬**. 1.0 이면 크기 일치. 1 보다 **작으면**")
    print("   시뮬이 실측보다 **크게(과하게)** 움직인다 — 예: 0.60 이면 시뮬이 1.7배 과하다.")


if __name__ == "__main__":
    main()
