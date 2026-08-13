# -*- coding: utf-8 -*-
"""**연구 최종 지표** — 계획한 토크와 실제로 나간 토크가 얼마나 같은가 (08-14 신설).

■ 이 연구가 최종적으로 물어야 하는 것
  시뮬레이션(디지털 트윈)에서 최적화한 궤적을 실로봇에 PD 제어로 내렸을 때,
  **실제 모터에 나간 토크가 계획했던 토크와 같은가.** 같으면 트윈이 실기를 대신할 수 있고,
  다르면 트윈에서 아무리 좋은 궤적을 만들어도 실기에서는 다른 일이 벌어진다.

■ 왜 지금까지 못 쟀나
  계획 궤적을 실제로 실기에 내려 본 세션이 **26.07.27 하나뿐**이다. 그 계획 파일이
  어디 있는지, 어느 시행이 그 계획을 쓴 것인지가 정리돼 있지 않아 08-14 전까지
  이 비교를 정식으로 한 적이 없었다. (과거에 한 번 계산된 값이 있으나 시간 정렬이
  8ms 어긋나 무릎을 2배 낙관 평가했다 — 아래 '정렬' 참조.)

■ 무엇을 무엇과 비교하나 (두 가지 수준, 둘 다 낸다)
  ① **명령 수준** (권장): 계획이 내놓은 모터 명령 토크 vs 실기에 기록된 모터 명령 토크.
     둘 다 원값이라 **환산식(명령→축토크 비율)이 끼어들지 않는다.** 가장 공정하다.
  ② 축 수준 (참고): 계획의 관절 축토크 vs 실측 명령을 분동 곡선으로 환산한 값.
     환산 모델에 전적으로 의존하므로 해석에 주의. 환산을 양쪽에 똑같이 적용한 값도 병기한다.

■ 값의 뜻 — "계획 대비 상대 오차" [단위 없음]
  (계획과 실측의 차이를 제곱평균한 값) ÷ (계획 토크 자체의 제곱평균).
  **0 이 완벽**이고, 0.28 이면 "계획 토크 크기의 28% 만큼 어긋났다"는 뜻이다.
  상관계수도 같이 낸다 — 1.0 이면 파형 모양이 같다는 뜻이고, 크기가 달라도 1.0 이 될 수 있다.
  ⇒ 상대 오차가 크면서 상관이 높으면 **모양은 맞고 크기가 틀린 것**이고,
    상관이 낮으면 **모양 자체가 다른 것**이다. 고칠 곳이 완전히 다르다.

■ 시간 정렬 (결과를 좌우한다 — 반드시 읽을 것)
  실기 기록에는 계획을 언제 내리기 시작했는지가 안 적혀 있어 맞춰야 한다.
  여기서는 **배포된 목표각 채널로 맞춘다** (계획과 실기가 같은 숫자를 가지므로 기계
  정밀도로 맞는다). 과거의 교차상관 정렬은 위상만 맞추고 크기를 안 봐서 12ms 어긋났고,
  그 결과 무릎 값이 0.144 로 나왔다 — 정밀 정렬로는 0.272 다 (2배 낙관).
  목표각 채널은 실제값보다 2샘플(4ms) 먼저 기록되므로 되돌린 뒤 맞춘다.

■ 창
  계획 시작 ~ **계획상 이륙 시각**까지. 이륙 후 구간은 애초에 실기로 내려보낸 적이 없다
  (배포 벡터가 이륙+10ms 에서 잘려 있다) — 그 구간 비교는 원리상 성립하지 않는다.

사용법:  python fs_taufid.py            (배포 계획이 있는 세션 전부)
        python fs_taufid.py 26.07.27   (한 세션만)
출력:   화면 표 + `_FTAU_<세션>.json`
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import fs_data as FD                     # noqa: E402
import fs_compare_plot as CP             # noqa: E402

QD_SKEW = 2          # 목표각 채널이 실제값보다 앞서 기록된 샘플 수 (4ms @500Hz)
CURVE = HERE / "_G5_curve_final.json"    # 분동 실측 곡선 (명령 → 축토크)


def _curve():
    with open(CURVE, encoding="utf-8") as f:
        c = json.load(f)
    return c["d1"], c["d2"], c["d3"]


def cmd_to_axis(raw):
    """모터 명령 [N·m] → 축토크 [N·m]. 분동(무게추) 실측 곡선의 역함수를 뉴턴법으로 푼다.

    곡선 자체는 "축토크를 주면 명령이 얼마로 기록되는가"를 3차식으로 적합한 것이다.
    우리에게 필요한 것은 반대 방향이라 수치로 뒤집는다. 실측 비율은 작은 명령에서
    1.26배, 큰 명령(35.5)에서 0.86배다. **검증된 범위는 명령 0~11.5 뿐**이므로
    점프의 고토크 구간(최대 37)에서는 외삽임을 잊지 말 것.
    """
    d1, d2, d3 = _curve()
    r = np.asarray(raw, float)
    x = r / d1
    for _ in range(12):
        f = d1 * x + d2 * x * np.abs(x) + d3 * x ** 3 - r
        df = d1 + 2 * d2 * np.abs(x) + 3 * d3 * x * x
        x = x - f / np.where(np.abs(df) > 1e-9, df, 1e-9)
    return x


def _unskew(x, n=QD_SKEW):
    """목표각 채널을 n 샘플 뒤로 밀어 실제값과 같은 시간축에 놓는다."""
    y = np.empty_like(np.asarray(x, float))
    y[n:] = np.asarray(x, float)[:-n]
    y[:n] = float(np.asarray(x, float)[0])
    return y


def _rel(plan, meas):
    """(차이의 제곱평균) ÷ (계획의 제곱평균), 그리고 상관계수. 0 이 완벽."""
    p = np.asarray(plan, float); m = np.asarray(meas, float)
    rms = float(np.sqrt(np.mean((p - m) ** 2)))
    ref = float(np.sqrt(np.mean(p ** 2)))
    cc = float(np.corrcoef(p, m)[0, 1]) if p.std() > 0 and m.std() > 0 else float("nan")
    return dict(rms=rms, rel=(rms / ref if ref > 1e-9 else float("nan")), corr=cc,
                rms_plan=ref, rms_meas=float(np.sqrt(np.mean(m ** 2))),
                peak_plan=float(np.max(np.abs(p))), peak_meas=float(np.max(np.abs(m))))


def plan_file(sess):
    """이 세션에 배포된 계획 파일 경로 (없으면 None). 정본 표는 그림 코드가 갖고 있다."""
    f = CP._PLAN.get(sess)
    return (HERE.parent / "goal22" / "p25_task0" / f) if f else None


def _lift_and_cut(Z):
    """계획상 이륙 시각과 배포 절단 시각 [s].

    이륙은 계획을 만들 때 같이 저장된 검산 파일에 적혀 있고, 배포 벡터는 그 시각
    +10ms 에서 잘려 나갔다 (계획 생성 코드의 규약). 검산 파일이 없으면 계획의
    목표각이 멈추는 지점으로 되찾는다.
    """
    t = Z["t"]
    aud = HERE.parent / "goal22" / "p25_task0" / "t0nc_cl_v9_audit.json"
    if aud.exists():
        try:
            with open(aud, encoding="utf-8") as f:
                a = json.load(f)
            tl = float((a.get("stats") or a).get("t_liftoff"))
            if np.isfinite(tl):
                return tl, tl + 0.010
        except Exception:
            pass
    q = np.asarray(Z["qd2"], float)
    v = np.abs(np.gradient(q, t))
    k = np.where((t > 0.05) & (v < 0.05))[0]
    tl = float(t[k[0]]) if len(k) else 0.20
    return tl, tl + 0.010


def measure(sess, verbose=True):
    """이 세션의 모든 시행에 대해 계획 vs 측정을 잰다. 반환 {시행이름: 결과}."""
    pf = plan_file(sess)
    if pf is None or not pf.exists():
        if verbose:
            print(f"  {sess}: 배포된 계획 파일이 없다 — 이 세션은 최종 지표를 잴 수 없다.")
        return {}
    Z = np.load(pf)
    PT = np.asarray(Z["t"], float)
    t_lift, t_cut = _lift_and_cut(Z)
    base = FD.SESS_FIT.get(sess) or FD.SESS_HO.get(sess) or FD.SESS_GATE.get(sess)
    if base is None:
        if verbose:
            print(f"  {sess}: 등록부에 없는 세션이다.")
        return {}
    out = {}
    for fold in FD.trials_of(base):
        try:
            d = FD.load2(fold)
        except Exception as e:
            if verbose:
                print(f"  {fold.name}: 읽기 실패 {e!r}")
            continue
        tm = np.asarray(d["t"], float)
        qd1s, qd2s = _unskew(d["qd1"]), _unskew(d["qd2"])
        # ── 시작 시각 찾기 ──────────────────────────────────────────────────────
        #   계획은 웅크린 자세에서 출발한다. 실기 목표각이 그 자세를 떠나 빠르게 움직이기
        #   시작하는 순간을 대략 잡고, 그 주변 ±60ms 를 훑어 목표각이 가장 잘 겹치는
        #   지점을 고른다. 목표각은 계획과 실기가 같은 숫자라 정확히 겹쳐야 정상이다.
        crouch = float(np.interp(0.0, PT, Z["qd2"]))
        vq = np.abs(np.gradient(qd2s, tm))
        fast = np.where(vq > 3.0)[0]
        if not len(fast):
            continue
        near = np.where(np.abs(qd2s[:fast[0]] - crouch) < 2e-3)[0]
        t_on = float(tm[near[-1]]) if len(near) else float(tm[fast[0]] - 0.05)
        best, t0 = 9e9, t_on
        for dl in np.arange(-0.060, 0.0605, 0.0005):
            a = t_on + dl
            m = (tm >= a) & (tm <= a + t_cut)
            if m.sum() < 50:
                continue
            e = float(np.sqrt(np.mean((qd2s[m] - np.interp(tm[m] - a, PT, Z["qd2"])) ** 2)))
            if e < best:
                best, t0 = e, a
        seg = (tm >= t0 - 0.05) & (tm <= t0 + 0.30)
        ts = tm[seg] - t0
        g = lambda P: np.interp(ts, PT, np.asarray(P, float))     # noqa: E731
        W = (ts >= 0) & (ts <= t_lift)
        if W.sum() < 30:
            continue
        r1, r2 = d["raw1"][seg], d["raw2"][seg]
        o = dict(t0=t0,
                 # 배포 확인 — 이 값이 0 에 가까워야 "그 계획을 그대로 내린 시행"이다
                 deploy_qd1_deg=float(np.degrees(np.sqrt(np.mean((qd1s[seg][W] - g(Z["qd1"])[W]) ** 2)))),
                 deploy_qd2_deg=float(np.degrees(np.sqrt(np.mean((qd2s[seg][W] - g(Z["qd2"])[W]) ** 2)))),
                 gains=list(FD.gains_of(fold.name) or ()),
                 cmd_hip=_rel(g(Z["raw1"])[W], r1[W]),
                 cmd_knee=_rel(g(Z["raw2"])[W], r2[W]),
                 ax_hip=_rel(g(Z["tau1_nm"])[W], cmd_to_axis(r1)[W]),
                 ax_knee=_rel(g(Z["tau2_nm"])[W], cmd_to_axis(r2)[W]),
                 ax2_hip=_rel(cmd_to_axis(g(Z["raw1"]))[W], cmd_to_axis(r1)[W]),
                 ax2_knee=_rel(cmd_to_axis(g(Z["raw2"]))[W], cmd_to_axis(r2)[W]),
                 # 추종 오차 = 목표각과 실제각의 차이 [도]. 토크는 이것에 게인을 곱해 만들어지므로
                 # 토크가 얼마나 어긋났는지의 뿌리다. 실기와 트윈(계획)을 나란히 낸다.
                 track_hip_deg=float(np.degrees(np.sqrt(np.mean((qd1s[seg][W] - d["q1"][seg][W]) ** 2)))),
                 track_knee_deg=float(np.degrees(np.sqrt(np.mean((qd2s[seg][W] - d["q2"][seg][W]) ** 2)))),
                 plan_track_hip_deg=float(np.degrees(np.sqrt(np.mean((g(Z["qd1"])[W] - g(Z["q1"])[W]) ** 2)))),
                 plan_track_knee_deg=float(np.degrees(np.sqrt(np.mean((g(Z["qd2"])[W] - g(Z["q2"])[W]) ** 2)))),
                 t_lift=t_lift, t_cut=t_cut)
        # ☠ 08-14 — 여기서 "실기 추종 오차 ÷ 트윈 추종 오차" 를 만들려다 **철회**했다.
        #   검산해 보니 계획 파일의 각도 채널로 PD 식을 다시 세우면(게인×각도차 + 감쇠×속도차)
        #   힙 35.7 · 무릎 27.8 [N·m] 이 나오는데, 같은 파일에 적힌 계획 토크는 13.9 · 18.4 다
        #   (힙 2.6배 · 무릎 1.5배 어긋남, 상관은 0.97/0.92 로 모양은 같다).
        #   ⇒ 계획 토크는 **각도 차이에 게인만 곱한 값이 아니다.** 사이에 명령을 줄이는 층이
        #     끼어 있고(비율 힙 0.41 · 무릎 0.68), 힙은 관절각과 모터각이 구조 휨 때문에
        #     서로 다르다. 그래서 계획 파일의 관절각으로 만든 "트윈 추종 오차" 는 계획 토크와
        #     짝이 맞지 않는 숫자이고, 그것으로 만든 배수는 뜻이 없다.
        #   ★ 남는 사실 하나는 중요하다: **계획 토크에는 이미 그 축소 비율이 발라져 있다.**
        #     그 비율이 물리적으로 틀리면 계획 자체가 틀린 것이고, 실기가 아무리 잘 따라가도
        #     "측정 ≈ 계획" 은 성립하지 않는다. (다음 단계에서 이 층을 따로 검증할 것.)
        out[fold.name] = o
    return out


def report(sess, R):
    print(f"\n■ {sess} — 계획한 토크와 실제 나간 토크의 차이 (0 이 완벽)")
    print("  값 = (계획-실측 차이의 제곱평균) ÷ (계획 토크의 제곱평균). 상관 1.0 = 파형 모양 일치.")
    print(f"  창 = 계획 시작 ~ 계획상 이륙({(next(iter(R.values()))['t_lift'] if R else 0):.4f}s). "
          f"그 뒤는 실기에 내려보낸 적이 없어 비교 불가.\n")
    print(f"{'시행(게인)':22s} {'배포확인°':>9s} | {'힙 상대':>7s} {'힙 상관':>7s} {'힙 피크비':>8s}"
          f" | {'무릎 상대':>8s} {'무릎 상관':>8s} {'무릎 피크비':>9s}")
    print("-" * 104)
    for k, v in R.items():
        ch, ck = v["cmd_hip"], v["cmd_knee"]
        print(f"{k:22s} {v['deploy_qd2_deg']:9.4f} | {ch['rel']:7.3f} {ch['corr']:7.3f} "
              f"{ch['peak_meas']/max(ch['peak_plan'],1e-9):8.2f} | {ck['rel']:8.3f} {ck['corr']:8.3f} "
              f"{ck['peak_meas']/max(ck['peak_plan'],1e-9):9.2f}")
    print("-" * 104)
    print("  배포확인° = 실기 목표각과 계획 목표각의 차이 [도]. 0 에 가까우면 그 계획을 그대로 내린 시행이다.")
    print("  피크비 = 실측 최대 토크 ÷ 계획 최대 토크. 1.0 이 완벽, 1.5 면 실기가 계획보다 1.5배 세게 썼다는 뜻.")
    print("\n  ※ 계획 토크는 게인 150/250 으로 계산된 값이다. 게인이 다른 시행의 값을 그대로")
    print("    견주면 게인 차이까지 오차로 세어지므로, **같은 게인인 150_2.2_250_3 이 정본**이다.")
    print("    나머지는 '게인을 바꾸면 어느 쪽으로 움직이나' 를 보는 참고용이다.\n")
    print(f"{'시행(게인)':22s} | {'실기 추종 힙°':>13s} {'실기 추종 무릎°':>15s}")
    print("-" * 104)
    for k, v in R.items():
        print(f"{k:22s} | {v['track_hip_deg']:13.3f} {v['track_knee_deg']:15.3f}")
    print("-" * 104)
    print("  실기 추종 오차 = 실기의 목표각과 실제각의 차이 [도] (창 안 제곱평균). 0 이 완벽.")
    print("  ※ 트윈 쪽 추종 오차는 여기 안 낸다 — 계획 파일의 관절각으로 만든 값이 계획 토크와")
    print("    짝이 안 맞는 것을 08-14 에 확인했다 (파일 안 주석 참조). 내려면 재생을 돌려야 한다.")


def main():
    sess_list = sys.argv[1:] or list(CP._PLAN.keys())
    for s in sess_list:
        R = measure(s)
        if not R:
            continue
        report(s, R)
        p = HERE / f"_FTAU_{s.replace('.', '')}.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(R, f, ensure_ascii=False, indent=1, default=float)
        print(f"\n  저장 → {p.name}")


if __name__ == "__main__":
    main()
