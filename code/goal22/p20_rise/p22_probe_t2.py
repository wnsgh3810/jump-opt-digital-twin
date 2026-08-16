# -*- coding: utf-8 -*-
"""P22 프로브 T2 — 세션 기준선 드리프트 = 열/배터리 지문 검사.

가설: 준정적 기준선 λ*(유지 창 최적 무릎 보정토크)가 세션 내 트라이얼 순서(시간)와
함께 상승하면 열/배터리 상태 기제 지지. 무드리프트면 기각.

방법 (기존 기계 재사용):
  λ* 창 스캐너 = p20_exp4.win_scan (exp3/exp6 검증 프로토콜, closure 리셋 + FK-bz,
  λ그리드 [-2,4] step0.5 + 포물선 보간, λ무감(<2%) 창 제외). W=0.12s (exp3/exp6과 동일).
  유지(holding) 창 = 시작점 |dq2_s(t0)| < 0.5 rad/s (dq2_s = savgol 11,3) AND
  창 전체가 푸시 시작 전에 끝남 (t0+W ≤ onset+0.01; onset = T1과 동일한 30% 피크
  연속구간의 왼쪽 끝). ※ 원정의 "|dq2|<0.5 구간 전체"는 실데이터에서 0.012~0.08s로
  너무 짧아 (트라이얼 전장 0.3s), '저속 시작 + 푸시 전 종료' 창으로 완화 — 명시 캐비앳.
  플랜트 = P19 canonical 후보 (pre30_probe와 동일), 오프셋 = 파이프라인 관례
  (0421/0424 후보 적합값, 0602 없음=0; 세션 내 상수라 순위상관에 무영향).

시간 순서 출처:
  0602: GRF.xlsx mtime (세션 당일 저녁 19:51~21:01 트라이얼 사이 간격으로 저장됨
        — 취득 직후 저장으로 판단, hip/knee는 21:33~ 일괄 수출) → 사용 (중간 신뢰).
  0421: 전 파일 다음날(4/22~23) 수출 — 취득 순서 복원 불가 → 게인 라벨 순 폴백 [FLAG].
  0424: 전 파일 이틀 뒤(4/26) 탐색기 이름순 수출 — 복원 불가 → 게인 라벨 순 폴백 [FLAG].
  (xlsx 내부 Time은 컨트롤러 상대시각 수십 초 — 세션 내 절대순서 정보 없음, 확인함)

held-out 0324 제외 (철칙 9). fit no-CVT 세션만: 0421/0424/0602.
"""
# --- 실험 데이터 경로: 단일 출처 (code/bench/datapaths.py) ---
import os as _o, sys as _s
_d = _o.path.dirname(_o.path.abspath(__file__))
while _d != _o.path.dirname(_d) and not _o.path.isdir(_o.path.join(_d, 'code', 'bench')):
    _d = _o.path.dirname(_d)
if _o.path.join(_d, 'code', 'bench') not in _s.path:
    _s.path.append(_o.path.join(_d, 'code', 'bench'))
from datapaths import DATA_ROOT, CVT_ROOT  # noqa: E402
# ---------------------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import spearmanr

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import p20_exp1 as E                      # noqa: E402  (AD.ensure_init 포함)
import p19_judge as P                     # noqa: E402
from p20_exp4 import win_scan             # noqa: E402
from p14_judge import KT, GR, CF          # noqa: E402

DATA = Path(DATA_ROOT)
DST = Path("C:/Users/junho/Desktop/jump_opt/g22_p20_results")
DST.mkdir(parents=True, exist_ok=True)
W = 0.12
STRIDE = 0.01

SESS = {
    "jump_position_0421": DATA / "26_04_21/Position Control",
    "jump_0424": DATA / "26_04_24",
    "jump_0602": DATA / "26_06_02/position",
}
# 시간 순서 (헤더 주석의 mtime 감사 근거)
CHRON = {
    "jump_position_0421": dict(source="게인 라벨 순 폴백 [FLAG: mtime=익일 수출, 복원 불가]",
                               order=None),          # None → SETS 라벨 순
    "jump_0424": dict(source="게인 라벨 순 폴백 [FLAG: mtime=이틀 뒤 이름순 수출, 복원 불가]",
                      order=None),
    "jump_0602": dict(source="GRF.xlsx mtime (세션 당일 저녁, 트라이얼 직후 저장으로 판단)",
                      order="grf_mtime"),
}


def push_onset(t, dq2, grf):
    """T1과 동일: 30% 피크 연속구간의 왼쪽 끝 시각."""
    dqs = savgol_filter(dq2, 11, 3)
    if grf is not None and len(grf) >= 5:
        n = min(len(grf), len(t))
        pk = int(np.argmax(grf[:n]))
        below = np.where(grf[pk:n] < 0.02 * grf[pk])[0]
        toff = t[pk + below[0]] if len(below) else t[n - 1]
        m = t <= toff + 0.1
    else:
        m = np.ones_like(t, bool)
    ip = int(np.argmax(np.abs(dqs) * m))
    thr = 0.30 * abs(dqs[ip])
    ia = ip
    while ia > 0 and abs(dqs[ia - 1]) > thr:
        ia -= 1
    return float(t[ia]), dqs


def grf_mtime_order(root, subs):
    mt = {}
    for sub in subs:
        f = root / sub / "GRF.xlsx"
        mt[sub] = f.stat().st_mtime if f.exists() else float("inf")
    return sorted(subs, key=lambda s: mt[s]), {s: mt[s] for s in subs}


def main():
    model, _ = P.build_flip(E.X32, E.V[1], E.SP)
    trials_by = {}
    for tr in P.J._P["cl"]:
        if tr["ds"] in SESS:
            trials_by.setdefault(tr["ds"], {})[str(tr["sub"])] = tr

    out = {}
    for ds, root in SESS.items():
        subs = list(trials_by[ds].keys())          # SETS 라벨 순 (로더 순서 보존)
        ch = CHRON[ds]
        if ch["order"] == "grf_mtime":
            chron_subs, mts = grf_mtime_order(root, subs)
        else:
            chron_subs, mts = subs, {}
        k1, k2 = E.P12.OFFKEY.get(ds, (None, None))
        o1 = E.DD[k1] if k1 else 0.0
        o2 = E.DD[k2] if k2 else 0.0
        rows = []
        for sub in subs:
            d = trials_by[ds][sub]["d"]
            t = d["t"]
            onset, dqs = push_onset(t, d["dq2"], d.get("grf_real"))
            starts = [t0 for t0 in np.arange(0.0, max(onset - W + 0.0101, 0.0), STRIDE)
                      if abs(dqs[int(np.searchsorted(t, t0))]) < 0.5 and t0 + W <= onset + 0.01]
            note = ""
            if not starts:                          # 폴백: 푸시 전 최저속 시작점 1개
                pre = t < onset - W
                if pre.sum() > 3:
                    i0 = int(np.argmin(np.abs(dqs[pre])))
                    starts = [float(t[i0])]
                    note = "fallback_minspeed"
            rs = win_scan(model, d, 0.030, starts, W, o1=o1, o2=o2)
            lam = [r["lam"] for r in rs]
            iqm = [r["iq"] for r in rs]
            nb = sum(1 for v in lam if v in (-2.0, 4.0))
            rows.append(dict(sub=sub, onset=float(onset), n_start=len(starts),
                             n_win=len(rs), n_bound=nb, note=note,
                             lam_mean=float(np.mean(lam)) if lam else float("nan"),
                             lam_std=float(np.std(lam)) if lam else float("nan"),
                             iq_mean=float(np.mean(iqm)) if iqm else float("nan"),
                             traw_mean=float(np.mean(iqm) * GR * KT / CF) if iqm else float("nan"),
                             wins=[dict(t0=r["t0"], lam=r["lam"], iq=r["iq"], dq=r["dq"])
                                   for r in rs]))
            print(f"{ds}/{sub}: onset={onset:.3f} wins={len(rs)}/{len(starts)} "
                  f"λ*={rows[-1]['lam_mean']:+.2f}±{rows[-1]['lam_std']:.2f} "
                  f"⟨|Iq|⟩={rows[-1]['iq_mean']:.1f}A {note}", flush=True)

        bysub = {r["sub"]: r for r in rows}
        lam_ch = [bysub[s]["lam_mean"] for s in chron_subs]
        iq_ch = [bysub[s]["iq_mean"] for s in chron_subs]
        ok = np.isfinite(lam_ch)
        idx = np.arange(len(chron_subs))[ok]
        lam_v = np.asarray(lam_ch)[ok]
        rho_o, p_o = spearmanr(idx, lam_v) if ok.sum() > 2 else (float("nan"), float("nan"))
        iq_v = np.asarray(iq_ch)[ok]
        rho_i, p_i = spearmanr(iq_v, lam_v) if ok.sum() > 2 else (float("nan"), float("nan"))
        # 창 단위 pooled λ* vs |Iq|
        wl = [(w["iq"], w["lam"]) for r in rows for w in r["wins"]]
        if len(wl) > 3:
            rho_w, p_w = spearmanr([x for x, _ in wl], [y for _, y in wl])
        else:
            rho_w, p_w = float("nan"), float("nan")
        out[ds] = dict(chron_source=CHRON[ds]["source"], chron_order=chron_subs,
                       grf_mtimes=mts, trials=rows,
                       spearman_order=dict(rho=float(rho_o), p=float(p_o), n=int(ok.sum())),
                       spearman_iq_trial=dict(rho=float(rho_i), p=float(p_i)),
                       spearman_iq_window=dict(rho=float(rho_w), p=float(p_w), n=len(wl)))

    print("\n=== T2 요약: 유지 창 λ* vs 트라이얼 시간 순서 ===")
    for ds, r in out.items():
        print(f"\n[{ds}]  순서 출처: {r['chron_source']}")
        print(f"  {'#':>2} {'sub':20s} {'λ*':>7} {'±':>5} {'⟨|Iq|⟩A':>8} {'창수':>4}")
        for i, s in enumerate(r["chron_order"]):
            tr = next(x for x in r["trials"] if x["sub"] == s)
            print(f"  {i:2d} {s:20s} {tr['lam_mean']:+7.2f} {tr['lam_std']:5.2f} "
                  f"{tr['iq_mean']:8.1f} {tr['n_win']:4d}{' ' + tr['note'] if tr['note'] else ''}")
        so = r["spearman_order"]
        si = r["spearman_iq_trial"]
        sw = r["spearman_iq_window"]
        print(f"  Spearman λ* vs 순서: ρ={so['rho']:+.2f} (p={so['p']:.3f}, n={so['n']}) | "
              f"λ* vs ⟨|Iq|⟩(트라이얼): ρ={si['rho']:+.2f} (p={si['p']:.3f}) | "
              f"(창 pooled): ρ={sw['rho']:+.2f} (p={sw['p']:.3f}, n={sw['n']})")
    json.dump(out, open(DST / "p22_probe_t2.json", "w"), indent=1)
    print("\nsaved", DST / "p22_probe_t2.json")


if __name__ == "__main__":
    main()
