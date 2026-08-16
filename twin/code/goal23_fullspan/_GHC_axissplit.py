"""신규 두 축 중 누가 판을 무너뜨렸나 — 가르는 시험 (2026-08-13)

■ 왜 이 시험을 하나
  3 회차 탐색(_GHB_sweep3)이 첫머리에 "이겨야 할 상대"로 찍은 숫자가 **39.15** 였다.
  정상이면 0.96 근처여야 한다. 뜯어보면 벌점(36.28)만 문제가 아니라 측정 토크를 그대로
  넣고 돌린 판이 2.70 배, 점프 높이 오차가 5.80 배로 **모델이 통째로 무너졌다.**

  그 지점은 "현행 스택 11 개 값 + 신규 2 축(레일 마찰 0.012 · 속도 제곱 손실 0.0005)" 이다.
  즉 무너뜨린 건 신규 2 축 중 하나(또는 둘의 조합)다. 그런데 탐색의 답은 갈렸다:
      레일 마찰      → 범위 끝(0.030)까지 밀어 올림 = 더 넣고 싶어 한다
      속도 제곱 손실 → 정확히 0 으로 끔          = 기각
  ⇒ 정황은 "속도 제곱 손실이 범인" 이지만, 로그만으로는 확정할 수 없다. 하나씩 켜서 가른다.

■ 무엇을 재나
  점수 = 0.40×(측정 토크 주입 재생) + 0.40×(폐루프) + 0.20×(점프 높이).
  그 전 스택(H2)이 1.0000 이고 **낮을수록 정확**하다. 벌점은 적합에 안 쓰는 두 세션
  (26.03.24 · 26.04.21)이 2% 넘게 나빠질 때 붙는다 — 0 이 정상.

■ 아무것도 쓰지 않는다
  evaluate() 는 파일을 건드리지 않는다 (진행 기록 append 는 최적화 콜백 안에만 있다).
  1·2·3 회차 산출물은 전부 그대로다.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench"))

try:
    import safe
    safe.utf8_console()
except Exception:
    pass

import _GHB_sweep as S

H3 = list(S.H3)          # 3 회차의 출발점 = 현행 스택 11 개 + 신규 2 축(0.012, 0.0005)
I_RAIL, I_W2 = 9, 10     # 신규 2 축의 자리

# 4 시간 탐색(3 회차)이 내놓은 승자 13 개 값 (_GHB_sweep3.json)
WIN = [0.11324997406833642, 0.2796119101476333, 0.19666095664563962, 0.02914296313988121,
       3.2996928308045868, 0.023096910938684462, 138.00508823549094,
       0.0018713477569056234, 0.0031499989526842516,
       0.02974060602736533, 2.605549317903806e-07,
       4.021067356100458, 2.382944347251327]


def _mk(base, rail, w2):
    x = list(base); x[I_RAIL], x[I_W2] = rail, w2
    return x


CASES = [
    ("A. 순수 현행 스택 (신규 2 축 둘 다 끔)", _mk(H3, 0.0,     0.0)),
    ("B. 현행 + 레일 마찰만 (0.012)",          _mk(H3, 0.012,   0.0)),
    ("C. 현행 + 속도 제곱 손실만 (0.0005)",     _mk(H3, 0.0,     0.0005)),
    ("D. 현행 + 둘 다 — 39.15 재현 확인",       _mk(H3, 0.012,   0.0005)),
    ("E. 현행 + 레일 마찰 0.02974 만",          _mk(H3, 0.02974, 0.0)),
    ("F. ★ 4 시간 탐색 승자 그대로",            list(WIN)),
    ("G. 승자에서 레일 마찰만 끔",              _mk(WIN, 0.0,    0.0)),
]


def main():
    print("=" * 78, flush=True)
    print("■ 신규 두 축 가르기 — 현행 스택 위에서 하나씩만 켠다", flush=True)
    print("   점수: 낮을수록 정확 · 그 전 스택 = 1.0000 · 벌점 0 이 정상", flush=True)
    print("=" * 78, flush=True)
    print("  준비 중 (엑셀 읽기) …", flush=True)
    t0 = time.time()
    S._ensure()
    print(f"  준비 끝 {time.time()-t0:.0f}초 · trial {len(S._C)} 개\n", flush=True)

    print(f"{'경우':38s} {'점수':>9s} {'주입재생':>9s} {'폐루프':>8s} {'점프높이':>9s} {'벌점':>8s}",
          flush=True)
    print("-" * 88, flush=True)

    rows = []
    for name, x in CASES:
        t1 = time.time()
        v, det = S.evaluate(("canon_cap", x))
        if det is None:
            print(f"{name:38s} {v:>9.2f}   ← 계산 실패 또는 발산", flush=True)
            rows.append((name, v, None))
            continue
        print(f"{name:38s} {v:>9.4f} {det['ma']:>9.4f} {det['cl']:>8.4f} "
              f"{det['h']:>9.4f} {det['pen']:>8.3f}   ({time.time()-t1:.0f}초)", flush=True)
        rows.append((name, v, det))

    # 게이트(적합에 안 쓰는 두 세션) 개별 성적 — 1.0 이 그대로, 1.02 넘으면 벌점
    print("\n" + "-" * 88, flush=True)
    print("■ 적합에 안 쓰는 세션의 성적 (1.000 = 그대로 · 1.02 넘으면 벌점)", flush=True)
    print(f"{'경우':38s} {'26.03.24 주입':>14s} {'26.04.21 주입':>14s} {'26.04.21 폐루프':>16s}",
          flush=True)
    for name, v, det in rows:
        if det is None:
            continue
        g = det["gate"]
        print(f"{name:38s} {g.get('26.03.24MA', float('nan')):>14.4f} "
              f"{g.get('26.04.21MA', float('nan')):>14.4f} "
              f"{g.get('26.04.21CL', float('nan')):>16.4f}", flush=True)

    print("\n" + "=" * 78, flush=True)
    print("■ 읽는 법", flush=True)
    print("   A 가 0.96 근처면 판이 정상이다 (기준점 확인).", flush=True)
    print("   B 가 A 보다 좋으면  → 레일 마찰은 살아 있다.", flush=True)
    print("   C 가 크게 나빠지면  → **속도 제곱 손실이 범인 확정.**", flush=True)
    print("   D 가 39.15 근처면   → 3 회차 첫머리 숫자가 재현된 것이다.", flush=True)
    print("   E 는 탐색이 고른 레일 마찰 값이 현행 스택 위에서도 좋은지 본다.", flush=True)
    print("=" * 78, flush=True)


if __name__ == "__main__":
    main()
