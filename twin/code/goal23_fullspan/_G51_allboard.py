# -*- coding: utf-8 -*-
"""_G51_allboard — **전 데이터 ModeA 전수 비교표** (q · dq · h), p24 vs 신구성 (마라톤G, 08-08).

왜 필요한가
  심판 `_G13_board` 는 **CVT 세션(0429)을 제외**하고 세션 평균만 남긴다. 사용자 요청:
  "모든 데이터에서의 ModeA q·dq·h 성능을 p24 와 비교".
  ⇒ 여기서는 **CVT 포함 전 trial**을 돌리고 **trial 단위**로 전부 남긴다.

동일성 보장 (중요)
  창·초기화·연장·채널 정의를 `_G13_board` 와 **비트 단위로 같게** 유지한다:
    · 채점 창 = `FD.plot_window`  · h 판독 = 이지 후 +0.6s 연장 후 `bz` 최댓값
    · q1 은 **thm1**(모터측) 로 채점 (보드와 동일)  · fade=True
    · FS_NOBIAS / FS_NODEEP 존중
  ⇒ 비CVT 세션 숫자는 `_G13_board` 결과와 일치해야 한다 (자체 검증 항목).

사용법
  python _G51_allboard.py p24        # 환경변수 없이 = 구 기준선
  <env 세팅> python _G51_allboard.py new
  python _G51_allboard.py --report   # 두 결과를 합쳐 비교표 출력
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
from _G13_board import real_h                                 # noqa: E402  (심판과 동일 출처)

CH = ("q1", "q2", "dq1", "dq2")


def run(tag):
    ft = FR.fs_twin(); SP = FR._sess_params()
    rows = []
    print(f"전수 보드 실행: tag={tag}  (CVT 포함)")
    for s, p, g, cvt, ho in FD.registry():
        hv = real_h(p)
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m))
            t_end = min(tt[m][-1] + 0.6, tt[-1])          # h 판독용 연장 (보드와 동일)
            m2 = (tt >= tt[i0]) & (tt <= t_end)
            t = tt[m2] - tt[i0]
            sp = SP.get(s) or dict(bias1=0.0, knee_deep=None)
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
            ts = tt[m] - tt[i0]
            gm = lambda k: np.interp(ts, L["t"], L[k])
            e = dict(q1=float(np.sqrt(np.mean(np.degrees(gm("thm1") - d["q1"][m]) ** 2))),
                     q2=float(np.sqrt(np.mean(np.degrees(gm("q2") - d["q2"][m]) ** 2))),
                     dq1=float(np.sqrt(np.mean((gm("dq1") - d["dq1"][m]) ** 2))),
                     dq2=float(np.sqrt(np.mean((gm("dq2") - d["dq2"][m]) ** 2))))
            hs = float(np.asarray(L["bz"], float).max())
            rows.append(dict(s=s, name=p.name, cvt=bool(cvt), ho=bool(ho),
                             e=e, hs=hs, hv=(float(hv) if hv else None)))
            print(f"  {'[CVT] ' if cvt else ''}{s}/{p.name}: "
                  f"q1 {e['q1']:.3f} q2 {e['q2']:.3f} dq1 {e['dq1']:.3f} dq2 {e['dq2']:.3f} "
                  f"h {hs:.3f}/{hv}", flush=True)
        except Exception as ex:
            print(f"  {s}/{p.name}: ERR {type(ex).__name__} {ex}", flush=True)
    json.dump(rows, io.open(HERE / f"_G51_all_{tag}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n저장: _G51_all_{tag}.json  ({len(rows)} trial)")


def pct(a, b):
    return 100.0 * (b / a - 1.0) if (a and np.isfinite(a) and a > 0) else np.nan


def report():
    A = {f"{r['s']}/{r['name']}": r for r in
         json.load(io.open(HERE / "_G51_all_p24.json", encoding="utf-8"))}
    B = {f"{r['s']}/{r['name']}": r for r in
         json.load(io.open(HERE / "_G51_all_new.json", encoding="utf-8"))}
    keys = [k for k in A if k in B]
    print("=" * 132)
    print("★★ 전 데이터 ModeA 성능 — p24 → 신구성  (q: ° · dq: rad/s · h: m)")
    print("   신구성 = canon_cap 3.8/2.6 · MASS 3.28 · PRESLIDE 0.86,0.85,0.02,1.0 · 인공층 전멸")
    print("   ※ 음수 = 개선.  h 는 |h_sim/h_영상 − 1| (영상 실측 A급 대비 오차율)")
    print("=" * 132)
    hdr = (f"{'세션':<11}{'trial':<21}{'역할':<9}"
           f"{'q1 p24':>8}{'→신':>8}{'%':>7}{'q2 p24':>8}{'→신':>8}{'%':>7}"
           f"{'dq1':>7}{'→':>7}{'%':>7}{'dq2':>7}{'→':>7}{'%':>7}{'h오차%':>8}{'→':>7}")
    cur = None
    ACC = {k: [] for k in CH}; AH = []
    for k in sorted(keys, key=lambda x: (B[x]["cvt"], x)):
        a, b = A[k], B[k]
        if b["s"] != cur:
            print("\n" + hdr); print("-" * 132)
            cur = b["s"]
        role = "CVT" if b["cvt"] else ("held-out" if b["ho"] else
                                       ("게이트" if b["s"] == "26.04.21" else "fit"))
        v = []
        for c in CH:
            x, y = a["e"][c], b["e"][c]
            v += [x, y, pct(x, y)]
            if not b["cvt"]:
                ACC[c].append(y / x)
        ha = abs(a["hs"] / a["hv"] - 1) * 100 if a["hv"] else np.nan
        hb = abs(b["hs"] / b["hv"] - 1) * 100 if b["hv"] else np.nan
        if np.isfinite(ha) and not b["cvt"]:
            AH.append((ha, hb))
        print(f"{b['s']:<11}{b['name'][:20]:<21}{role:<9}"
              f"{v[0]:8.3f}{v[1]:8.3f}{v[2]:+7.1f}{v[3]:8.3f}{v[4]:8.3f}{v[5]:+7.1f}"
              f"{v[6]:7.3f}{v[7]:7.3f}{v[8]:+7.1f}{v[9]:7.3f}{v[10]:7.3f}{v[11]:+7.1f}"
              f"{ha:8.2f}{hb:7.2f}")

    # ── 세션별 집계 ──
    print("\n" + "=" * 132)
    print("■ 세션별 평균 (RMSE 의 평균)")
    print(f"{'세션':<12}{'역할':<10}{'n':>4}" + "".join(
        f"{c+' p24':>10}{'→신':>9}{'%':>8}" for c in CH) + f"{'h오차% p24':>12}{'→신':>9}")
    for s in sorted({B[k]["s"] for k in keys}, key=lambda x: (any(B[k]["cvt"] for k in keys if B[k]["s"] == x), x)):
        sub = [k for k in keys if B[k]["s"] == s]
        cvt = B[sub[0]]["cvt"]
        role = "CVT" if cvt else ("held-out" if B[sub[0]]["ho"] else
                                  ("게이트" if s == "26.04.21" else "fit"))
        line = f"{s:<12}{role:<10}{len(sub):4d}"
        for c in CH:
            x = np.mean([A[k]["e"][c] for k in sub]); y = np.mean([B[k]["e"][c] for k in sub])
            line += f"{x:10.3f}{y:9.3f}{pct(x, y):+8.1f}"
        hx = np.nanmean([abs(A[k]["hs"] / A[k]["hv"] - 1) * 100 if A[k]["hv"] else np.nan for k in sub])
        hy = np.nanmean([abs(B[k]["hs"] / B[k]["hv"] - 1) * 100 if B[k]["hv"] else np.nan for k in sub])
        line += f"{hx:12.2f}{hy:9.2f}"
        print(line)

    # ── 전체 집계 ──
    print("\n" + "=" * 132)
    print("■ 전체 집계")
    for lab, sel in (("비CVT (심판 대상 9 세션)", lambda r: not r["cvt"]),
                     ("CVT (0429)", lambda r: r["cvt"]),
                     ("전 데이터", lambda r: True)):
        sub = [k for k in keys if sel(B[k])]
        if not sub:
            continue
        print(f"\n  [{lab}]  n={len(sub)} trial")
        print(f"    {'채널':<8}{'p24':>10}{'신':>10}{'변화':>9}{'trial 평균 배율':>16}"
              f"{'개선 trial':>12}{'악화 trial':>12}")
        for c in CH:
            x = np.mean([A[k]["e"][c] for k in sub]); y = np.mean([B[k]["e"][c] for k in sub])
            rat = np.array([B[k]["e"][c] / A[k]["e"][c] for k in sub])
            print(f"    {c:<8}{x:10.3f}{y:10.3f}{pct(x, y):+8.1f}%{rat.mean():16.3f}"
                  f"{int((rat < 1).sum()):12d}{int((rat >= 1).sum()):12d}")
        hh = [(abs(A[k]["hs"] / A[k]["hv"] - 1), abs(B[k]["hs"] / B[k]["hv"] - 1))
              for k in sub if A[k]["hv"] and B[k]["hv"]]
        if hh:
            hh = np.array(hh)
            print(f"    {'h':<8}{100*hh[:,0].mean():9.2f}%{100*hh[:,1].mean():9.2f}%"
                  f"{pct(hh[:,0].mean(), hh[:,1].mean()):+8.1f}%{'':16}"
                  f"{int((hh[:,1]<hh[:,0]).sum()):12d}{int((hh[:,1]>=hh[:,0]).sum()):12d}")
            # 부호 있는 편향
            sb = np.array([(A[k]["hs"] / A[k]["hv"], B[k]["hs"] / B[k]["hv"])
                           for k in sub if A[k]["hv"] and B[k]["hv"]])
            print(f"    {'h 편향':<8}{sb[:,0].mean():10.4f}{sb[:,1].mean():10.4f}"
                  f"      (h_sim/h_영상 평균 — 1.000 이 무편향)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        report()
    else:
        run(sys.argv[1] if len(sys.argv) > 1 else "x")
