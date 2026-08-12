# -*- coding: utf-8 -*-
"""_GHN_passline — **합격선의 자(尺)를 데이터로 고른다** (08-12 저녁, 사용자 지적).

발단
  나는 "오차 ÷ 그 신호의 표준편차" 로 % 를 냈고 '완벽' 이라던 무릎 토크가 21% 로 나왔다.
  사용자가 그림을 보고 반박했다 — "거의 겹치는데?". 그래서 분모를 범위로 바꿨더니 4.5%.
  그러자 사용자가 다시 물었다 — **"그건 한 데이터만 보고 정한 것 아니냐"**. 맞는 지적이다.
  경계(앞 4/5)도 분모(범위)도 내가 trial 하나의 그림을 보고 손으로 정한 것이었다.

그래서 이 파일이 하는 일
  자를 손으로 정하지 않고 **사용자 육안 판정 전체와 가장 잘 맞는 자를 고른다.**
  후보를 전부 만들어 놓고, 각 자로 전 trial 을 줄 세운 뒤,
  **사용자가 '안 좋다' 고 한 것이 '좋다' 고 한 것보다 실제로 나쁘게 나오는 비율**로 채점한다.
  (이 비율은 통계에서 AUC 라 부르는 값이다. 1.0 이면 자가 판정을 완벽히 재현하고,
   0.5 면 동전 던지기와 같다 = 그 자는 사용자 눈과 아무 상관이 없다는 뜻.)

후보 (분모 4 × 구간 여러 개)
  분모 — 오차를 무엇으로 나눌 것인가
    ① 안 나눔 (그냥 N·m)      ② 실측이 오간 폭 (최대−최소)
    ③ 실측의 표준편차          ④ 실측 절대값의 최대
  구간 — 창의 어디를 볼 것인가
    전 구간 · 앞 70~95% · 창 끝에서 30~150ms 잘라내기

주의 (사용자 규약)
  발밑 힘센서는 크기를 못 믿고 세션 간 비교도 금지다. 여기서는 **이륙 시각 하나만** 쓰고,
  그것도 각 trial 이 자기 창 안에서 정한 값이다 (fs_data.segment).
"""
import os, sys, json, itertools
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
CACHE = HERE / "_GHN_passline.json"

# ── 사용자 육안 판정(VERDICT_260812.md §1) 을 trial×채널 라벨로 옮긴 것 ──────────
#    3 = 안 좋다고 명시 · 2 = 살짝 아쉽다 · 1 = 좋다(언급 없음 포함) · 0 = 아주 완벽
#    ※ 사용자 명시: "언급하지 않은 것은 전부 좋다는 뜻이다"
PERFECT = {("26.04.24", "60_0.75_60_2"), ("26.04.24", "60_1.5_60_1.5")}

def label(sess, name, g, ch):
    """ch: 'a1'=힙 토크 · 'a2'=무릎 토크. 반환 0~3 (작을수록 사용자가 좋다고 한 것)"""
    kp1, kp2 = g[0], g[2]
    if (sess, name) in PERFECT:
        return 0
    if sess == "26.04.24":
        if ch == "a2" and name in ("150_2.2_250_3", "150_2.2_350_3.5", "150_2.2_500_4"):
            return 3
        if ch == "a1" and name in ("150_2.2_250_3", "120_2_120_2", "120_2.2_150_2.5"):
            return 3
        if ch == "a1" and 90 <= kp1 <= 120:
            return 2            # "힙 토크가 살짝 아쉽지만 아직 괜찮음"
        return 1
    if sess == "26.04.29":      # 변속기 — "전반적으로 초중반이 잘 안 맞음, 150부터 다 안 맞음"
        return 3 if kp1 >= 150 else 2
    if sess == "26.06.02":
        return 2 if kp1 >= 150 else 1     # "150 에서의 힙·무릎 토크 아쉬움"
    if sess == "26.07.22":
        return 3 if name == "150_3.3_500_5" else 1
    if sess == "26.07.23":
        if ch == "a2" and name == "150_2.2_500_5":
            return 3
        if ch == "a1":
            return 3            # "힙 토크가 후반부에서 안 좋음" (전반적)
        return 1
    if sess == "26.07.24":
        return 3 if ch == "a2" else 1     # "무릎 토크가 전반적으로 안 좋음"
    if sess == "26.07.25":
        return 1                # "전반적으로 좋음"
    if sess == "26.07.27":
        return 3 if ch == "a2" else 2     # 무릎 후반부 ✗ · 힙 중반부 살짝 아쉬움
    return 1


# ── 자(尺) 후보 ────────────────────────────────────────────────────────────────
DENOMS = {
    "안나눔[N·m]":  lambda r: 1.0,
    "오간폭":       lambda r: float(r.max() - r.min()),
    "표준편차":     lambda r: float(np.std(r)),
    "최대절대값":   lambda r: float(np.max(np.abs(r))),
}
# 구간: ("이름", 종류, 값)   frac = 앞쪽 몇 % 까지 · tail_ms = 창 끝에서 몇 ms 잘라낼지
SEGS = ([("전구간", "frac", 1.00)]
        + [(f"앞{int(f*100)}%", "frac", f) for f in (0.95, 0.90, 0.85, 0.80, 0.75, 0.70)]
        + [(f"끝{m}ms제외", "tail_ms", m) for m in (30, 50, 80, 120, 150)])


def auc(bad, good):
    """'안 좋다'로 지목된 값들이 '좋다'는 값들보다 큰(=더 나쁜) 비율. 1.0 완벽 · 0.5 무의미."""
    if not len(bad) or not len(good):
        return np.nan
    b = np.asarray(bad)[:, None]; g = np.asarray(good)[None, :]
    return float(((b > g).sum() + 0.5 * (b == g).sum()) / (b.size * g.size))


def collect():
    """전 trial 을 한 번 돌려 (오차파형, 실측파형, 이륙시각) 을 모은다. 무겁다 → 캐시."""
    import _GHJ_hipvel as GJ
    for k, v in GJ.STACK.items():
        os.environ.setdefault(k, v)
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR, fs_cvt as FC
    ft0 = FR.fs_twin()
    out = []
    for s, p, g, cvt, ho in FD.registry():
        if not g:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            ft = FC.cvt_ft(d["l_i"], ft_base=ft0) if cvt else None
            r = CP.cl_pair(d, seg, g, s, ft=ft)
            if r is None:
                continue
            t, (mo, mf), old, fs, m, cmd, pl = r
            # 이륙 시각을 이 창의 시간축으로 옮긴다 (창 시작 = 0)
            t_lo = float(d["t"][seg["i_lo"]] - d["t"][int(np.argmax(m))]) \
                if "i_lo" in seg else float("nan")
            row = dict(s=s, n=p.name, g=list(g), t=t.tolist(), t_lo=t_lo, cvt=bool(cvt))
            for i, k in ((4, "a1"), (5, "a2")):
                row[k] = dict(real=np.asarray(mf[k]).tolist(), sim=np.asarray(fs[i]).tolist())
            out.append(row)
            print(f"  모음 {s}/{p.name}", flush=True)
        except Exception as ex:
            print(f"  건너뜀 {s}/{p.name}: {type(ex).__name__} {ex}", flush=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def slice_of(t, kind, val, t_lo):
    """구간 마스크. frac=앞쪽 비율 · tail_ms=창 끝에서 잘라낼 시간"""
    if kind == "frac":
        return np.arange(int(len(t) * val))
    return np.flatnonzero(np.asarray(t) <= t[-1] - val * 1e-3)


def main():
    if CACHE.exists() and "recollect" not in sys.argv:
        R = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"캐시 사용 ({len(R)} trial) — 다시 모으려면 인자 recollect")
    else:
        print("전 trial 폐루프 재생 중 (한 번만)…")
        R = collect()
    print()

    # ── 0. 이륙이 창의 어디인가 (내가 '마지막 1/5' 이라 부른 것의 정체) ──────────
    fr = [r["t_lo"] / r["t"][-1] for r in R if np.isfinite(r.get("t_lo", np.nan))]
    if fr:
        print("■ 창 안에서 이륙이 일어나는 위치 (창 시작 0 · 창 끝 1)")
        print(f"   중앙값 {np.median(fr):.3f} · 범위 {min(fr):.3f}~{max(fr):.3f} "
              f"({len(fr)} trial)")
        print(f"   ⇒ 내가 손으로 잡은 경계 0.80 은 이륙보다 "
              f"{'앞' if 0.80 < np.median(fr) else '뒤'}에 있다.")
        print()

    # ── 1. 자 후보 전수 채점 ────────────────────────────────────────────────────
    rows = []
    for (dn, dfun), (sn, kind, val) in itertools.product(DENOMS.items(), SEGS):
        rec = {}
        for ch in ("a1", "a2"):
            vals, labs = [], []
            for r in R:
                real = np.asarray(r[ch]["real"]); sim = np.asarray(r[ch]["sim"])
                ix = slice_of(r["t"], kind, val, r["t_lo"])
                if len(ix) < 20:
                    continue
                e = real[ix] - sim[ix]
                den = dfun(real)                      # 분모는 창 전체 실측으로 (구간 무관)
                if den <= 1e-9:
                    continue
                vals.append(float(np.sqrt(np.mean(e ** 2))) / den)
                labs.append(label(r["s"], r["n"], r["g"], ch))
            vals = np.asarray(vals); labs = np.asarray(labs)
            rec[ch] = auc(vals[labs == 3], vals[labs <= 1])
        rows.append((dn, sn, rec["a1"], rec["a2"], np.nanmean([rec["a1"], rec["a2"]])))

    rows.sort(key=lambda x: -x[4])
    print("■ 자 후보 채점 — '안 좋다'고 한 것이 '좋다'고 한 것보다 나쁘게 나오는 비율")
    print("   (1.00 = 사용자 눈을 완벽히 재현 · 0.50 = 동전 던지기 = 무의미)")
    print()
    print(f"   {'분모':12s} {'구간':12s} {'힙토크':>7s} {'무릎토크':>8s} {'평균':>7s}")
    print("   " + "-" * 52)
    for dn, sn, a1, a2, av in rows[:14]:
        print(f"   {dn:12s} {sn:12s} {a1:7.3f} {a2:8.3f} {av:7.3f}")
    print("   ...")
    for dn, sn, a1, a2, av in rows[-4:]:
        print(f"   {dn:12s} {sn:12s} {a1:7.3f} {a2:8.3f} {av:7.3f}")
    print()

    # ── 2. 분모별 최선 (구간을 최선으로 뽑았을 때) ─────────────────────────────
    print("■ 분모만 놓고 보면 (각 분모의 최선 구간 성적)")
    for dn in DENOMS:
        sub = [r for r in rows if r[0] == dn]
        b = max(sub, key=lambda x: x[4])
        w = min(sub, key=lambda x: x[4])
        print(f"   {dn:12s} 최선 {b[4]:.3f} ({b[1]}) · 최악 {w[4]:.3f} ({w[1]}) "
              f"· 구간 바꿔도 폭 {b[4]-w[4]:.3f}")
    print()
    print("■ 구간만 놓고 보면 (각 구간의 최선 분모 성적)")
    for sn in [s[0] for s in SEGS]:
        sub = [r for r in rows if r[1] == sn]
        b = max(sub, key=lambda x: x[4])
        print(f"   {sn:12s} 최선 {b[4]:.3f} ({b[0]})")


if __name__ == "__main__":
    main()
