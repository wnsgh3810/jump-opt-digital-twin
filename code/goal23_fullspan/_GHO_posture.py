# -*- coding: utf-8 -*-
"""_GHO_posture — **변속기 오차가 자세에 따라 달라지는가** (08-12, 우선순위 1번).

무엇을 밝히려는가
  짐 지고 일어서기(26.06.04)에서 **변속기를 건 경우만** 심하게 어긋난다.
  같은 동작·같은 짐이라도 변속기가 없으면 점프만큼 잘 맞는다 (따라간 시간 0.58초 vs 0.04~0.09초).
  ⇒ 원인 후보: **4절 링크가 깊게 접힌 자세에서 모델이 틀렸다.**

  근거가 될 만한 것: 무릎 모터(크랭크)가 깊게 접히면 모터 1도가 무릎 몇 도로 바뀌는지
  (= 전달비)가 0.84 에서 **0.19 까지** 떨어진다. 일어서기는 그 영역에서 시작해 1.6초를 머문다.
  점프는 같은 영역을 순식간에 지나간다. 그래서 일어서기에서만 터졌을 수 있다.

어떻게 판별하나 (새 실험 없이)
  ① 변속기 점프 세션(26.04.29)의 폐루프 무릎 각도 오차를 **크랭크 각도 구간별**로 나눈다.
     깊게 접힌 구간에서 오차가 크면 자세 의존이 실재한다.
  ② **무변속 세션도 같은 방식으로** 나눈다 (대조군). 무변속에서도 똑같이 깊은 자세에서
     오차가 크다면 4절 링크 탓이 아니라 그냥 "깊은 자세가 어렵다" 는 뜻이다.
     ⇒ **변속기에서만 나타나야** 4절 링크 모델이 범인이다.
  ③ 짐 지고 일어서기가 무너지는 순간의 크랭크 각도를 재서, ①에서 나온 나쁜 구간과 겹치는지 본다.

용어
  · 크랭크 각도 = 무릎 모터가 돌린 각도 [도]. 데이터의 무릎 채널이 바로 이 값이다.
    깊게 접힐수록 음수로 크다 (−170도 근처가 가장 접힌 상태).
  · 전달비 = 크랭크가 1도 돌 때 무릎이 실제로 몇 도 도는가 [무차원]. 1.0 이면 그대로 전달,
    0.19 면 모터가 1도 돌아도 무릎은 0.19도밖에 안 돈다.
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))

BINS = np.array([-180., -165., -150., -135., -120., -105., -90., -60.])   # 크랭크 각도 [도]


def bin_err(crank_deg, err_deg):
    """크랭크 각도 구간별 평균 오차 [도]. 반환 (구간중심, 평균오차, 표본수)"""
    out = []
    for a, b in zip(BINS[:-1], BINS[1:]):
        m = (crank_deg >= a) & (crank_deg < b)
        out.append((0.5 * (a + b), float(np.sqrt(np.mean(err_deg[m] ** 2))) if m.sum() > 5
                    else np.nan, int(m.sum())))
    return out


def main():
    import _GHJ_hipvel as GJ
    for k, v in GJ.STACK.items():
        os.environ.setdefault(k, v)
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR, fs_cvt as FC
    ft0 = FR.fs_twin()

    print("변속기 오차의 자세 의존 검사 — 우선순위 1번")
    print()
    print("  크랭크 각도 = 무릎 모터가 돌린 각도 [도]. 음수로 클수록 깊게 접힌 상태.")
    print("  값 = 폐루프 무릎 각도 오차 [도] (시뮬레이션 − 실측, 제곱평균). 0 이 완벽.")
    print()

    ACC = {"변속기": [], "무변속": []}
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
            crank = np.degrees(np.asarray(mf["q2"]))          # 실측 크랭크(무릎 모터) 각도
            err = np.degrees(np.asarray(fs[1]) - np.asarray(mf["q2"]))
            ACC["변속기" if cvt else "무변속"].append(bin_err(crank, err))
        except Exception:
            continue

    print(f"  {'크랭크 각도[도]':>14s} | {'변속기 오차[도]':>14s} {'n':>5s} | "
          f"{'무변속 오차[도]':>14s} {'n':>5s} | {'변속기÷무변속':>12s}")
    print("  " + "-" * 78)
    for i in range(len(BINS) - 1):
        row = []
        for k in ("변속기", "무변속"):
            vs = [a[i][1] for a in ACC[k] if np.isfinite(a[i][1])]
            ns = sum(a[i][2] for a in ACC[k])
            row.append((np.mean(vs) if vs else np.nan, ns))
        rr = row[0][0] / row[1][0] if np.isfinite(row[0][0]) and np.isfinite(row[1][0]) \
            and row[1][0] > 1e-9 else np.nan
        c = 0.5 * (BINS[i] + BINS[i + 1])
        f = lambda x: f"{x:14.2f}" if np.isfinite(x) else "             -"
        g2 = lambda x: f"{x:12.2f}" if np.isfinite(x) else "           -"
        print(f"  {c:14.0f} | {f(row[0][0])} {row[0][1]:5d} | {f(row[1][0])} {row[1][1]:5d} "
              f"| {g2(rr)}")

    print()
    print("  읽는 법: 맨 오른쪽이 1.0 근처면 변속기와 무변속이 똑같이 어렵다는 뜻이고,")
    print("           깊은 자세(위쪽 줄)에서만 크게 1을 넘으면 4절 링크 모델이 범인이다.")

    # ── 짐 지고 일어서기가 무너지는 순간의 자세 ────────────────────────────────
    print()
    print("■ 짐 지고 일어서기 — 무릎 각도 오차가 10도를 넘는 순간의 크랭크 각도")
    try:
        import _GHK_payload as PK
        rows = PK.run_all() if hasattr(PK, "run_all") else None
    except Exception as ex:
        rows = None
        print(f"  (자동 연결 실패: {type(ex).__name__} — 아래는 직접 계산)")
    if rows is None:
        for sub, mass, cvt in FD.S2S_CASES:
            try:
                d = FD.load_s2s(sub)
                if d is None:
                    continue
                pw = FD.plot_window(Path(sub), d)
                mm = (d["t"] >= pw[0]) & (d["t"] <= pw[1])
                cr = np.degrees(d["q2"][mm])
                print(f"  {sub:16s} 짐 {mass:4.1f}kg 변속기 {'O' if cvt else 'X'} — "
                      f"창 시작 크랭크 {cr[0]:7.1f}도 · 창 끝 {cr[-1]:7.1f}도")
            except Exception as ex:
                print(f"  {sub}: {type(ex).__name__} {ex}")


if __name__ == "__main__":
    main()
