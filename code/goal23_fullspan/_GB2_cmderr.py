# -*- coding: utf-8 -*-
"""_GB2_cmderr — 폐루프 무릎 토크 악화가 **진짜인지 눈금 탓인지** 가른다 (마라톤G, 08-11).

문제
  폐루프 토크를 모델별 변환식으로 공정하게 비교했더니, 무릎이 9세션 중 6세션에서
  나빠졌다. 원인 후보가 둘이다.
    ① 진짜 나빠짐 — 무릎 궤적 예측이 덜 좋아졌다 (인공 보조층을 끈 자리)
    ② 눈금 탓   — 현행 변환식이 더 가파르다(무릎 한계 3.8 vs 힙 2.6). 같은 명령
                  오차라도 토크 오차가 크게 찍힌다.

가르는 법 — **변환식을 안 거치고** 명령 단위(N·m)에서 비교한다
  실로봇 PD 가 실제로 계산한 값이 `raw` 로 기록돼 있다. 모델에 대해 같은 양은
      c_model = clip( kp·(qd − q_model) + kd·(dqd − dq_model) )
  즉 "**로봇이 이 모델이 말한 자리에 있었다면 무엇을 명령했을까**". 실제 컨트롤러의
  **폴더 게인 그대로** 쓰므로 α·변환식이 끼어들지 않는다. 이걸 raw 와 비교한다.
    · 명령 오차도 나빠졌다        → ① 진짜
    · 명령 오차는 좋아졌는데 토크만 → ② 눈금

침묵실패 방역 (반드시 통과해야 결과를 믿는다)
  **실측 q·dq 로 같은 식을 계산하면 raw 가 재현돼야 한다.** 안 되면 게인·스큐·클립
  규약 중 하나가 틀린 것이고, 그러면 이 판별 전체가 무의미하다. 먼저 이걸 찍는다.
  ★ qd 는 q/raw 보다 2샘플 선행 기록 → `fs_compare_plot.sh` 로 뒤로 밀어야 한다
    (미보정 시 push 에서 kp·e 가 25~30% 과대 — 데이터 사전 등재).
  ★ 26.04.21 은 위치제어라 dq_des 가 인가되지 않는다 (dqd=0 으로 둔다).

CLI: python _GB2_cmderr.py
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_compare_plot as CP                                     # noqa: E402
import fs_data as FD                                             # noqa: E402
import p25_a_twin as TW                                          # noqa: E402
import safe                                                      # noqa: E402

CLIP = float(TW.R19.CLIP)
OUT = HERE / "_compare_G50" / "_cmderr.json"
NO_VDES = ("26.04.21",)          # 위치제어 세션 — dq_des 미인가


def cmd_of(g, qd1, qd2, dqd1, dqd2, q1, q2, dq1, dq2):
    """실로봇 PD 가 이 상태에서 계산했을 명령 [N·m] (변환식 개입 없음)."""
    c1 = g[0] * (qd1 - q1) + g[1] * (dqd1 - dq1)
    c2 = g[2] * (qd2 - q2) + g[3] * (dqd2 - dq2)
    return np.clip(c1, -CLIP, CLIP), np.clip(c2, -CLIP, CLIP)


def one(sess, name, d, seg, g):
    r = CP.cl_pair(d, seg, g, sess)
    if r is None:
        return None
    t, (meas_o, _), old, fs, m, cmd, _pl = r
    qd1, qd2, dqd1, dqd2 = [CP.sh(x) for x in cmd[:4]]        # ★ 2샘플 스큐 보정
    if sess in NO_VDES:
        dqd1 = np.zeros_like(dqd1); dqd2 = np.zeros_like(dqd2)
    # 창 마스크로 실측 raw 를 뽑는다 (cl_pair 과 같은 창)
    pw = FD.plot_window(d["_fold"], d)
    mw = (d["t"] >= pw[0]) & (d["t"] <= pw[1])
    r1, r2 = d["raw1"][mw], d["raw2"][mw]
    # ① 자기검증: 실측 상태로 재구성한 명령이 raw 를 재현하는가
    v1, v2 = cmd_of(g, qd1, qd2, dqd1, dqd2,
                    meas_o["q1"], meas_o["q2"], meas_o["dq1"], meas_o["dq2"])
    # ② 두 모델
    o1, o2 = cmd_of(g, qd1, qd2, dqd1, dqd2, old[0], old[1], old[2], old[3])
    f1, f2 = cmd_of(g, qd1, qd2, dqd1, dqd2, fs[0], fs[1], fs[2], fs[3])
    e = lambda a, b: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))
    return dict(sess=sess, trial=name, n=int(mw.sum()),
                self1=e(v1, r1), self2=e(v2, r2),          # 재현 오차 (작아야 신뢰)
                rms1=float(np.sqrt(np.mean(r1 ** 2))), rms2=float(np.sqrt(np.mean(r2 ** 2))),
                old1=e(o1, r1), old2=e(o2, r2),
                new1=e(f1, r1), new2=e(f2, r2))


def main():
    rows = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g:
            continue
        if ho and os.environ.get("FS_CMP_HO") != "1":
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            a = one(s, p.name, d, seg, g)
        except Exception as ex:
            print(f"  ✗ {s}/{p.name}: {type(ex).__name__} {str(ex)[:60]}", flush=True); continue
        if a:
            rows.append(a)
            print(f"  {s}/{p.name}: OK", flush=True)
    if not rows:
        raise SystemExit("결과 없음")
    safe.atomic_json_write(OUT, rows)

    # ── ① 자기검증 먼저 (이게 나쁘면 아래 결과는 무의미) ──
    s1 = np.array([r["self1"] for r in rows]); s2 = np.array([r["self2"] for r in rows])
    m1 = np.array([r["rms1"] for r in rows]); m2 = np.array([r["rms2"] for r in rows])
    print("\n" + "=" * 72)
    print("① 자기검증 — 실측 각도로 재구성한 명령이 기록된 명령(raw)을 재현하는가")
    print(f"   힙  : 재현 오차 중앙 {np.median(s1):.2f} N·m  (명령 크기 {np.median(m1):.1f} → "
          f"{100*np.median(s1/m1):.1f}%)")
    print(f"   무릎: 재현 오차 중앙 {np.median(s2):.2f} N·m  (명령 크기 {np.median(m2):.1f} → "
          f"{100*np.median(s2/m2):.1f}%)")
    print("   → 이 값이 작아야 아래 비교를 믿을 수 있다.")

    # ── ② 판별 ──
    print("\n② 명령 오차 (변환식 개입 없음) — 세션별 trial 평균")
    print(f"\n{'세션':10s} {'n':>2s}   {'힙 OLD→새':>20s}   {'무릎 OLD→새':>20s}")
    agg = {}
    for r in rows:
        agg.setdefault(r["sess"], []).append(r)
    W = [0, 0]
    for s in sorted(agg):
        A = agg[s]
        o1 = np.mean([x["old1"] for x in A]); n1 = np.mean([x["new1"] for x in A])
        o2 = np.mean([x["old2"] for x in A]); n2 = np.mean([x["new2"] for x in A])
        W[0] += n1 < o1; W[1] += n2 < o2
        print(f"{s:10s} {len(A):2d}   {o1:6.2f}→{n1:6.2f} ({100*(n1/o1-1):+5.0f}%)   "
              f"{o2:6.2f}→{n2:6.2f} ({100*(n2/o2-1):+5.0f}%)")
    print(f"\n   명령 기준 개선: 힙 {W[0]}/{len(agg)} 세션 · 무릎 {W[1]}/{len(agg)} 세션")
    print(f"   저장 → {OUT}")


if __name__ == "__main__":
    main()
