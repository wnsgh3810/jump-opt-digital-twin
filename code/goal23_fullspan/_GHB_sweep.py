# -*- coding: utf-8 -*-
"""_GHB_sweep — 질량·탄성·마찰·변환식을 **한꺼번에** 맞춘다 (마라톤H, 2026-08-11).

왜 한꺼번에인가 (사용자 지시)
  08-11 에 확인된 것: 매달림 실측이 준 관절 마찰값을 **하나씩** 넣으면 전부 나빠진다.
  특히 속도비례 항을 실측대로(≈0) 줄이면 점프 높이가 +144% 무너진다.
  ⇒ 그 항은 관절 마찰이 아니라 **다른 손실을 대신 떠맡는 층**이고, 그 손실을 물리로
    바꾸려면 변환식·마찰·질량·탄성을 **같이** 움직여야 한다. 한 축씩으로는 못 넘는다.

두 판을 따로 돌려 맞대결시킨다
  ① 지금 구조 (`canon_cap`) — 분동 저울 곡선을 쓰되 보정폭을 상한으로 막는다.
  ② 새 구조 (`canon_fric`) — 곡선 전액을 쓰되 **하중에 비례하는 마찰**을 뺀다.
     기어·벨트는 전달하는 힘이 클수록 마찰이 커진다. 이러면 토크가 작은 매달림 시험에서
     안 보이고 도약에서 커지므로, 위 모순이 설명된다.
     ※ 일정한 마찰(건마찰)은 이 식에 안 넣는다 — 물리엔진의 관절 마찰 기능이
       떨림 없이 처리하므로 그쪽(FS_KNEEM_FL/FS_HIPM_FL)에 맡기고 여기선 하중비례분만 본다.

점수 (전부 낮을수록 좋음, 현행 스택 = 1.000)
  · 측정 토크 주입 재생 : 측정된 토크를 그대로 넣고 돌린 뒤 관절각·각속도 4채널 오차.
    PD 가 없어 오차를 못 감춘다 — 물리의 1급 심판.
  · 폐루프           : 실제 게인으로 PD 제어한 뒤 관절각·각속도·토크 6채널 오차.
  · 점프 높이        : 지면 기준 몸통 최고 높이, 영상 실측 대비 오차.
  점수 = 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이, **채널별로 기준선에 나눠 정규화**
  (큰 채널이 점수를 독식하는 것을 막는다 — 08-11 에 이 함정을 한 번 밟았다).

  적합 세션 = 0424·**0429(변속기)**·0602·0722·0723·0724·0725·0727
  게이트 전용 = **0324(별도 보관본)·0421(위치제어)** — 목적함수에 절대 안 들어간다.
  게이트 = 위 둘의 주입재생 + 0421 폐루프. 기준선보다 2% 넘게 나빠지면 벌점.
  ★ 변속기 세션(0429): 08-12 낮에는 이 판에서 빼야 했다 (모델에 변속기 기하가 없어서).
    저녁에 `_cvt_twin()` 으로 **trial 마다 그 trial 의 링크 길이로 모델을 다시 지어**
    태우도록 고쳐 **적합에 되살렸다.** FS_SWEEP_CVT=0 이면 옛 판(제외)이 그대로 재현된다.

CLI 보조: python _GHB_sweep.py board   → 한 후보를 이 판으로 재고 **세션별로 펼쳐** 보여준다
          (스윕을 돌리지 않는다. 통합이 맞는지 눈으로 확인하는 용도.)

★ 안 건드리는 축: 발 미끄럼 관련(FS_PRESLIDE·FS_IMPRATIO). 이 점수에는 미끄러짐이 안 들어가
  있어서, 같이 풀면 점수는 좋아지고 미끄러짐만 조용히 망가진다. 별도 심판이 있는 축이다.

CLI: python _GHB_sweep.py [시간예산_시간]     ※ 실행은 .bat 더블클릭으로 (헌법 3)
"""
import os, sys, io, json, time, math, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
# 실행 회차별로 산출 파일을 분리한다 (FS_SWEEP_TAG="2" → _GHB_sweep2.json).
# 1회차 결과가 현행 스택 H3 의 출처이므로 **절대 덮어쓰면 안 된다.**
_TAG = os.environ.get("FS_SWEEP_TAG", "")
OUT = HERE / f"_GHB_sweep{_TAG}.json"
LOG = HERE / f"_GHB_sweep{_TAG}_trials.jsonl"

# ── 현행 배포 스택 (CURRENT_STACK.md H2_260811 의 env 레시피 그대로) ────────────────
#    ★ 08-11 사고: 채점할 때 이 중 2개만 설정해 **배포 스택이 아닌 지점**에서 쟀다.
#      기준선은 반드시 배포 스택이어야 하므로 여기에 박아둔다.
BASE_ENV = {
    "FS_TMAP": "canon_cap", "FS_TDCAP": "3.8,2.6",
    "FS_MASS": "3.28", "FS_FOOTR": "0.020",
    "FS_NOSUPP": "1", "FS_NOSPR": "1", "FS_NOBIAS": "1", "FS_NODEEP": "1",
    "FS_PRESLIDE": "0.86,0.85,0.02,1.0",
    "FS_CMD_LPF": "0.002,0.0025",
    "FS_IMPRATIO": "20",
}
# ★ 08-12 저녁: 변속기 세션(26.04.29)을 **적합에 되살렸다.** 그날 낮에 뺀 이유는 "이 판의
#   모델에 변속기 기하가 없다"는 것이었는데, 이제 trial 마다 그 trial 의 링크 길이로 모델을
#   다시 지어 태운다 (`_cvt_twin`). FS_SWEEP_CVT=0 이면 옛 판(제외)을 그대로 재현한다.
_CVT_ON = os.environ.get("FS_SWEEP_CVT", "1") != "0"
FIT = ("26.04.24", "26.06.02", "26.07.22",
       "26.07.23", "26.07.24", "26.07.25", "26.07.27") + (("26.04.29",) if _CVT_ON else ())
GATE_MA = ("26.03.24", "26.04.21")
GATE_CL = ("26.04.21",)
CH6 = ("q1", "q2", "dq1", "dq2", "a1", "a2")
CH4 = ("q1", "q2", "dq1", "dq2")
# 훑을 변환식 구조. FS_SWEEP_MODES="canon_cap,canon_fric" 로 늘릴 수 있다.
#   1회차는 둘을 3시간씩 맞붙였고 하중비례형이 크게 졌다 → 2회차는 현행 구조만 6시간.
MODES = tuple(m.strip() for m in
              os.environ.get("FS_SWEEP_MODES", "canon_cap").split(",") if m.strip())

# ── 스윕의 **출발점** 13 개 값 ─────────────────────────────────────────────────────
#   순서 = COMMON 11 개 + EXTRA["canon_cap"] 2 개.
#   ★ 08-12 밤 갱신: 앞 9 개와 뒤 2 개는 **2 회차 결과**(`_GHB_sweep2.json`)에서 왔고,
#     가운데 2 개(레일 마찰·빠를 때 커지는 저항)는 08-12 낮에 따로 찾은 값이다.
#   ⚠ 2 회차는 **토크 겹침 오류를 고치기 전 데이터**로 돌았다 (탐색 15:15 시작, 코드 수정 18:47).
#     그래서 이 값들은 "이겨야 할 상대"가 아니라 **출발점으로만** 쓴다. 이번 회차는 고친
#     데이터로 처음부터 다시 채점하므로, 여기 적힌 점수와 직접 비교하면 안 된다.
H3 = [0.15282936, 0.33847828, 0.15507681, 0.08251126,
      3.2987234, 0.00648279, 135.7284577,
      0.0023962, 0.00318871,
      0.012, 0.0005,                       # ← 신규 2 축 (08-12 낮 탐색값)
      3.68099698, 2.20596413]
# 그 전 스택 H2 = **점수의 기준선**(아래 BASE_ENV 와 같은 지점). 이걸 넣으면 1.0000 근처가
# 나와야 한다 — 판이 제대로 서 있는지 매 실행 첫머리에 확인하는 용도다.
#   신규 2 축은 기준선에 **없던 것**이므로 0 이다 (환경변수 미설정 = 0 과 같다).
H2 = [0.2469, 0.2383, 0.150, 0.312, 3.28, 0.0, 150.0, 0.002, 0.0025,
      0.0, 0.0,
      3.8, 2.6]

# ── 축 정의 (이름, 하한, 상한, 시작값) — 경계는 실측·설계공차에서만 온다 ─────────────
# ★ 08-12 저녁: **시작값을 현행 스택 H3 로 갱신했다** (1회차 산물). 1회차는 그 전 스택(H2)
#   에서 출발했는데, 지금은 H3 가 이미 3.5% 더 정확하므로 거기서 출발하는 편이 낫다.
#   경계(하한·상한)는 실측·설계공차에서 오는 값이므로 **건드리지 않는다.**
#   기준선(점수의 1.0000)은 여전히 H2 다 — 1회차와 같은 자로 재야 비교가 된다 (BASE_ENV).
COMMON = [
    # ★ 08-12 밤: 무릎 건마찰 범위를 **무게추 실측 근처로 좁혔다** (구 0.15~0.60).
    #   2 회차가 0.153 을 찾았는데 그건 당시 하한 0.15 에 거의 붙은 값이라, 하한이 더 낮았으면
    #   더 내려갔을 수 있다는 뜻이다. 무게추 실측(짐 0 일 때) 0.135 를 감싸도록 0.10 부터 연다.
    #   상한 0.20 은 실측의 1.5 배 — 여기 붙으면 "실측보다 큰 무언가가 있다"는 신호이므로
    #   범위를 늘릴 게 아니라 그 축이 무엇을 대신 떠맡는지부터 봐야 한다.
    ("무릎 건마찰",      0.10, 0.20, 0.1528),   # 무게추 실측 0.135 (2 회차 결과 0.1528)
    ("힙 건마찰",        0.10, 0.40, 0.3026),   # 매달림 실측 0.28 (H2 0.2383) — 실측과 독립 일치
    ("무릎 속도비례",    0.00, 0.25, 0.1617),   # (H2 0.150)
    ("힙 속도비례",      0.00, 0.45, 0.0964),   # (H2 0.312) — 실측 ≈0 과 독립 일치
    ("총질량",           3.26, 3.30, 3.2988),   # 케이블 제거 실측 3.26~3.30 (H2 3.28) ★ 상한 포화 중
    ("허벅지 무게중심z", -0.010, 0.025, -0.00189),  # [m] 기존 위치에 가산 (H2 0.0)
    ("힙 스프링",        100.0, 260.0, 138.53),  # (H2 150.0)
    ("힙 명령 지연",     0.000, 0.006, 0.00317), # [s] (H2 0.002)
    ("무릎 명령 지연",   0.000, 0.006, 0.00292), # (H2 0.0025)
    # ★★ 08-12 밤 신규 2 축 — 낮에 따로 찾아 둔 두 손실을 이 판에 정식 편입한다.
    #   그때 둘을 같이 넣으니 종합 점수가 1.40% 내려갔고, 세 판(주입 재생·폐루프·점프 높이)이
    #   **동시에** 좋아졌으며 검증용 데이터도 통과했다. 최적 근처가 평평했다
    #   (0.008~0.014 × 0.0004~0.0006 이 전부 −1.31~−1.40%) — 값 하나에 매달린 결과가 아니다.
    #   ⇒ 손으로 고정하지 않고 다른 축과 **함께** 풀게 한다. 둘 다 0 이면 지금 스택과 같아진다.
    ("레일 마찰",        0.000, 0.030, 0.012),   # 몸통이 수직 레일을 오르내릴 때 걸리는 마찰
                                                 # (발이 미는 힘에 비례). 0 이면 레일이 매끄럽다.
    ("빠를 때 커지는 저항", 0.0000, 0.0020, 0.0005),  # 무릎 속도의 제곱에 비례하는 손실
                                                 # [N·m/(rad/s)²]. 역기전력·감속기 효율 저하처럼
                                                 # 빠를수록 커지는 몫. 0 이면 그런 손실이 없다.
]
# ★★ 08-11 무게추 왕복 데이터(`26_08_07/{0,2,4}kg/probe_sweep_v1`)로 하중비례 마찰을 **직접 쟀다.**
#   마라톤G 는 상행·하행을 **평균내서 마찰을 지우고** 중력만 봤다. 지운 그 절반차가 곧 마찰이다.
#     마찰[명령단위] = 0.135 + 0.1197·|하중|  (무릎, 상관 +0.75)  → 전달 효율 88%
#     마찰[명령단위] = 0.278 + 0.0029·|하중|  (힙,  사실상 0)     → 전달 효율 ≈100%
#   무릎 기울기는 2kg 에서 +0.1169, 4kg 에서 +0.1177 — **다른 두 하중이 0.7% 안에 일치**.
#   물리적으로 타당: 무릎은 4절 링크+벨트를 거치고 힙은 모터가 거의 직접 돌린다.
#   식이 요구하는 단위는 N·m 이므로 명령→토크 환산(힙 1.241 · 무릎 1.306)을 곱한다:
#     무릎 기울기 0.1197×1.306 = **0.156** · 힙 0.0029×1.241 = **0.004**
#   ⇒ 이 값을 **하한 앵커**로 쓴다. 고정하지는 않는다 — 마라톤G G6-D 가 "빠를 때 더 깎이는
#     손실(역기전력·KT 처짐·감속기 효율 저하)은 토크 채널로 원리상 측정 불가" 라고 확정했고,
#     이 측정은 초당 0.4~0.9 라디안의 **준정적** 값이다. 도약은 그보다 훨씬 빠르다.
#     즉 준정적 손실은 **반드시 있고**(하한), 동적 손실이 그 위에 더해질 수 있다(상한 여유).
#   ★ 직전 판(하한 0.05)은 힙의 실측 0.004 를 **탐색 범위 밖으로 밀어냈다** — 사용자 실행 40분 후 발각.
EXTRA = {
    # 보정 상한: 무게추는 명령 11.5 까지 **선형**임을 확인했으나 그건 준정적 값이다.
    #   상한이 낮다 = "빠를 때 깎인다"를 대신 떠맡는 것이라 물리적으로 배제할 수 없다.
    #   ⇒ 강제로 올리지 않고 범위를 넓혀 탐색이 정하게 한다 (검증 구간 7.2/6.4 도 포함).
    # ★ 08-12 저녁: 시작값을 H3 로 갱신 (H2 는 3.8 / 2.6 이었다).
    #   ☠ 2 회차 첫 시동 때 **여기 두 축만 빠뜨렸다** — COMMON 9 개는 옮기고 EXTRA 2 개를
    #     안 옮겨서, 힙 보정상한이 2.6(H2) 으로 출발했다 (현행 2.309 대비 12.6% 어긋남).
    #     3 분 만에 로그에서 발견해 재시동. **축 목록은 두 군데(COMMON·EXTRA)에 나뉘어 있다.**
    "canon_cap":  [("무릎 보정상한", 2.0, 12.0, 3.733), ("힙 보정상한", 1.2, 10.0, 2.309)],
    # ★ 범위 산정 (08-11 두 번 틀린 뒤 확정)
    #   하한 = **준정적 실측** (느릴 때의 손실은 반드시 있다): 무릎 0.156 · 힙 0.004
    #   상한 = "지금 상한이 하던 일을 전부 하중비례가 떠맡는" 극단까지 여유를 둔다.
    #     (지금 구조는 명령이 커지면 보정이 상한에 걸려 기울기가 a_hat 0.682 로 수렴한다.
    #      같은 곳에 닿는 하중기울기는 환산−0.682 = 무릎 0.624 · 힙 0.559.)
    #   ★ 그런데 그 등가점을 실제로 재보니 **더 나빠졌다** (0.40 에서 34.4 → 0.624 에서 164.7).
    #     마찰은 속도 반대로 작용하므로 **내려앉는 구간에서는 토크를 더한다** — 고속 구간만 보고
    #     세운 등가 논리가 저속·역방향 구간에서 깨진 것이다. 등가점은 상한 근처일 뿐 정답이 아니다.
    #     실측 6점 중 최선은 0.40/0.35 → 시작점은 그쪽으로 둔다 (범위는 양쪽을 다 감싼다).
    #   1차 시도의 상한 0.45 는 등가점을, 그 전 판의 하한 0.05 는 힙 실측을 범위 밖으로 밀어냈다.
    "canon_fric": [("무릎 하중기울기", 0.156, 0.80, 0.40), ("힙 하중기울기", 0.004, 0.70, 0.35),
                   ("무릎 속도문턱", 0.03, 3.00, 0.30), ("힙 속도문턱", 0.03, 3.00, 0.30)],
}


def _sync_x0():
    """축 목록의 **시작값을 현행 스택의 정밀값으로 강제 일치**시킨다.

    ☠ 왜 필요한가 (08-12 사고, 6 시간을 날릴 뻔했다)
      위 표에 적힌 시작값은 **사람이 읽으려고 반올림한 숫자**다(0.2880). 실제 현행 값은
      소수점이 길다(0.28800339…). 게다가 축 목록이 COMMON(9 개)과 EXTRA(2 개) **두 군데로
      나뉘어 있어서**, 손으로 갱신하다 뒤쪽 2 개를 빠뜨렸다. 힙 보정상한이 현행 2.309 가
      아니라 그 전 스택 값 2.6 (12.6% 어긋남)으로 출발했고, 로그를 보고서야 발견했다.
      ⇒ 손으로 옮겨 적는 일 자체를 없앤다. 표의 숫자는 **눈으로 보기 위한 것**일 뿐이고,
        실제 출발점은 언제나 위 H3 하나에서 온다 (단일 출처).
    """
    n = len(COMMON)
    for i in range(n):
        COMMON[i] = COMMON[i][:3] + (H3[i],)
    for i in range(len(EXTRA["canon_cap"])):
        EXTRA["canon_cap"][i] = EXTRA["canon_cap"][i][:3] + (H3[n + i],)


_sync_x0()


def env_of(mode, x):
    """축 벡터 → 환경변수 dict (현행 스택 위에 덮어쓴다)."""
    e = dict(BASE_ENV)
    e["FS_KNEEM_FL"] = f"{x[0]:.4f}"
    e["FS_HIPM_FL"] = f"{x[1]:.4f}"
    e["FS_KNEEM_DAMP"] = f"{x[2]:.4f}"
    e["FS_HIPM_DAMP"] = f"{x[3]:.4f}"
    e["FS_MASS"] = f"{x[4]:.4f}"
    e["FS_COMZ"] = f"thigh={x[5]:.5f}"
    e["FS_KS_HIP"] = f"{x[6]:.2f}"
    e["FS_CMD_LPF"] = f"{x[7]:.5f},{x[8]:.5f}"
    # ★ 08-12 밤 신규 2 축. 0 이면 환경변수를 아예 안 넣어 **기준선과 완전히 같은 지점**이 된다
    #   (문자열 "0.00000" 을 넣어도 같지만, 안 넣는 쪽이 옛 판 재현을 문자 그대로 보장한다).
    if x[9] > 0:
        e["FS_RAIL"] = f"{x[9]:.5f}"        # 몸통이 레일을 오르내릴 때의 마찰
    if x[10] > 0:
        e["FS_W2"] = f"{x[10]:.6f}"         # 무릎 속도의 제곱에 비례하는 손실
    e["FS_TMAP"] = mode
    n = len(COMMON)                          # ← 축을 늘려도 아래 인덱스가 저절로 따라온다
    if mode == "canon_cap":
        e["FS_TDCAP"] = f"{x[n]:.3f},{x[n+1]:.3f}"
    else:
        e.pop("FS_TDCAP", None)
        # 일정몫(건마찰)은 0 — 물리엔진 관절 마찰이 담당한다. 점성도 0 (관절 감쇠가 담당).
        e["FS_TFRIC"] = (f"0,{x[n]:.4f},0,{x[n+2]:.4f},"
                         f"0,{x[n+1]:.4f},0,{x[n+3]:.4f}")
    return e


# ── 작업자별 1회 준비 (엑셀 읽기 ~80초 + 기준선) ───────────────────────────────────
_C = None
_BASE = None

# ── 변속기(26.04.29) 실험을 같은 판에 태우기 ────────────────────────────────────────
#   이 로봇의 핵심 장치가 변속기인데, 그 데이터 10회분이 채점에서 빠져 있었다.
#   빠진 이유는 "쓸 수 없어서"가 아니라 **잘못 채점되고 있어서**였다 (위 _ensure 주석).
#
#   무엇이 trial 마다 다른가: 4절 링크의 입력 변 길이. 그건 **모델 치수 자체**라
#   trial 마다 모델을 다시 지어야 한다. 짓는 건 비싸므로(XML 빌드) 길이별로 캐시한다.
#
#   ★ 대신 조심할 것: 스윕은 질량·마찰·탄성 같은 **물리값을 매 평가마다 바꾼다.**
#     모델을 캐시해 두고 가만두면 **옛 물리로 채점**하게 된다 — 그게 08-12 에 잡은
#     결함 #3 과 똑같은 사고다. 그래서 물리는 평가할 때마다 다시 심는다(`restamp`).
_CVT_STAMPED = set()      # 이번 env 로 물리를 이미 심은 링크 길이들


def _cvt_twin(li, ft0):
    """이 trial 의 링크 길이로 지은 변속기 트윈 (기하는 캐시, 물리는 env 바뀔 때마다 재이식)."""
    import fs_cvt as FC
    key = round(float(li), 7)
    fresh = key not in _CVT_STAMPED
    ft = FC.cvt_ft(li, ft_base=ft0, restamp=fresh)
    _CVT_STAMPED.add(key)
    return ft


def _apply(e):
    import fs_runner as FR
    for k in ("FS_KNEEM_FL", "FS_HIPM_FL", "FS_KNEEM_DAMP", "FS_HIPM_DAMP", "FS_MASS",
              "FS_COMZ", "FS_KS_HIP", "FS_CMD_LPF", "FS_TMAP", "FS_TDCAP", "FS_TFRIC",
              "FS_FOOTR", "FS_NOSUPP", "FS_NOSPR", "FS_NOBIAS", "FS_NODEEP",
              "FS_PRESLIDE", "FS_IMPRATIO",
              # ★ 08-13 버그픽스: 신규 2 축을 env_of 에는 추가했는데 **여기 지우는 목록에는
              #   안 넣었다.** env_of 는 값이 0 이면 변수를 아예 안 넣으므로(옛 판 재현 보장),
              #   지우지 않으면 **직전 평가의 값이 그대로 남아** 다음 평가를 오염시킨다.
              #   실제로 08-13 가르기 시험에서 "레일 마찰만 0.0005 없이" 를 쟀는데 직전 값이
              #   살아남아 두 경우가 소수점 4 자리까지 똑같이 나왔다 (C 와 D 가 39.1540 동일).
              #   4 시간 탐색 자체는 무사할 가능성이 높다 — 탐색이 내놓는 실수값이 정확히 0.0
              #   이 되는 일은 사실상 없어서 매번 두 변수를 명시로 덮어썼기 때문이다
              #   (승자도 2.6e-07 로 0 이 아니었다). 그래도 침묵 실패이므로 막는다.
              "FS_RAIL", "FS_W2"):
        os.environ.pop(k, None)
    os.environ.update(e)
    FR._S2S = None
    _CVT_STAMPED.clear()      # 물리가 바뀌었다 → 변속기 모델에도 다시 심어야 한다
    # 모델 캐시가 무한히 자라는 것을 막는다 (축 조합마다 새 모델 = 수만 개)
    if len(FR._CACHE) > 40:
        b = FR._CACHE.get("base")
        FR._CACHE.clear()
        if b is not None:
            FR._CACHE["base"] = b


def board():
    """반환 {세션: dict(ma=[4], cl=[6], h=오차)}"""
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
    ft0 = FR.fs_twin()
    G = collections.defaultdict(lambda: dict(ma=[], cl=[], h=[]))
    for s, p, g, cvt, d, seg, pw in _C:
        try:
            # 변속기 실험은 **그 trial 의 링크 길이로 지은 모델**에 태운다 (아래 _cvt 주석).
            ft = _cvt_twin(d["l_i"], ft0) if cvt else ft0
            t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
            i0 = int(np.argmax(m)); tg = t[m] - t[i0]
            sp = CP.sess_params(s)
            L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(tg[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is not None:
                gf = lambda k: np.interp(tg, L["t"], L[k])
                sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                v = [float(np.sqrt(np.mean((d[k][m] - w) ** 2))) *
                     (180 / np.pi if k in ("q1", "q2") else 1) for k, w in zip(CH4, sim)]
                if all(np.isfinite(v)) and max(v) < 1e4:
                    G[s]["ma"].append(v)
                t_ext = min(t[m][-1] + 0.6, t[-1])
                m2 = (t >= t[i0]) & (t <= t_ext); tg2 = t[m2] - t[i0]
                H = FR.rollout_ol_fs_b(ft, tg2, d["raw1"][m2], d["raw2"][m2],
                                       float(d["q1"][i0]), float(d["q2"][i0]),
                                       float(d["dq1"][i0]), float(d["dq2"][i0]),
                                       float(tg2[-1] - 0.004), bias1=sp["bias1"],
                                       knee_deep=sp["knee_deep"], fade=True)
                hv = CP.real_h(p)
                if H is not None and hv is not None and np.isfinite(hv):
                    hh = abs(float(np.asarray(H["bz"]).max()) - float(hv))
                    if np.isfinite(hh):
                        G[s]["h"].append(hh)
            if g:
                d["_sess"] = s; d["_fold"] = p
                r = CP.cl_pair(d, seg, g, s, ft=(ft if cvt else None))
                if r is not None:
                    _t, (mo, mf), old, fs, _m, _c, _ = r
                    v = [float(np.sqrt(np.mean((np.asarray(mf[k]) - np.asarray(fs[i])) ** 2))) *
                         (180 / np.pi if k in ("q1", "q2") else 1) for i, k in enumerate(CH6)]
                    if all(np.isfinite(v)) and max(v) < 1e4:
                        G[s]["cl"].append(v)
        except Exception:
            continue
    return {s: dict(ma=np.mean(v["ma"], axis=0).tolist() if v["ma"] else None,
                    cl=np.mean(v["cl"], axis=0).tolist() if v["cl"] else None,
                    h=float(np.mean(v["h"])) if v["h"] else None)
            for s, v in G.items() if v["ma"] or v["cl"]}


def _ensure():
    global _C, _BASE
    if _C is not None:
        return
    import fs_data as FD
    os.environ["FS_CVT_XML"] = "0"     # 작업자 16개가 같은 파일에 동시에 쓰는 것을 막는다 (사본은 눈요기용)
    C = []
    for s, p, g, cvt, ho in FD.registry():
        # ★★ 08-12 사고: 변속기 trial(26.04.29)을 **무변속 모델로 채점**하고 있었다.
        #   l_i 는 4절의 입력 링크 길이라 **모델 치수 자체**다 (fs_cvt: l_i 2mm 차 → 바디 2mm 차).
        #   기본 트윈에는 그 기하도, 폐쇄 초기화(cvt_init)도, 전달비 소산도 없다.
        #   증상: 무릎각 오차 26.8° (다른 세션 1.1° 의 24배) · 측정토크를 넣어도 크랭크가
        #   실측 160° 중 52° 만 돌았다. 정본 경로(`python fs_cvt.py cl`)로는 0.97° 로 정상.
        #   ⇒ 그날은 **변속기 trial 을 통째로 제외**했다 (임시 조치).
        #   ★ 마무리 (08-12 저녁): 이제 `_cvt_twin()` 이 trial 마다 **그 trial 의 링크 길이로
        #     모델을 다시 지어** 주므로 **같은 판에서 채점한다.** 제외는 필요 없다.
        #     FS_SWEEP_CVT=0 을 주면 옛 판(제외)을 그대로 재현한다 — 회귀 확인용.
        if cvt and not _CVT_ON:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            t = d["t"]
            if ((t >= pw[0]) & (t <= pw[1])).sum() < 30:
                continue
            C.append((s, p, g, cvt, d, seg, pw))
        except Exception:
            continue
    _C = C
    # ★ 08-12 밤 안전장치 — **토크 겹침 교정이 실제로 걸렸는지 첫머리에 찍는다.**
    #   2 회차는 이 교정이 파일에 들어가기 3 시간 전에 시작해서, 어긋난 토크로 6 시간을
    #   돌고 나서야 발각됐다 (파이썬은 시작할 때 코드를 한 번 읽고 그 뒤엔 안 다시 읽는다).
    #   확장판 토크가 원본과 정확히 36 N·m 씩 어긋나 있던 자리를 원본 값으로 되돌리는 교정이고,
    #   변속기 세션 4 개 trial 에서 46 곳이 걸려야 정상이다. 0 이 나오면 교정이 안 걸린 것이다.
    _nfix = sum(int(d.get("n_unwrap_fix", 0) or 0) for _s, _p, _g, _cvt, d, _sg, _pw in C)
    _ncvt = sum(1 for _s, _p, _g, _cvt, _d, _sg, _pw in C if _cvt)
    print(f"  데이터 {len(C)} trial (변속기 {_ncvt}) · "
          f"토크 겹침 교정 {_nfix} 곳" + ("" if _nfix else "  ⚠ 0 이면 교정 미적용 — 중단할 것"),
          flush=True)
    _apply(dict(BASE_ENV))
    _BASE = board()


def ratio(B, key, sess):
    v = []
    for s in sess:
        if s not in B or B[s].get(key) is None or _BASE.get(s, {}).get(key) is None:
            continue
        a = np.asarray(B[s][key], float); b = np.asarray(_BASE[s][key], float)
        if np.all(b > 0) and np.all(np.isfinite(a)):
            v.append(float(np.mean(a / b)))
    return float(np.mean(v)) if v else np.nan


def evaluate(args):
    """반환 (벌점 포함 점수, 세부). 실패·발산은 큰 값."""
    mode, x = args
    try:
        _ensure()
        _apply(env_of(mode, np.asarray(x, float)))
        B = board()
        if not B:
            return 9e2, None
        ma = ratio(B, "ma", FIT); cl = ratio(B, "cl", FIT)
        hs = [B[s]["h"] / _BASE[s]["h"] for s in FIT
              if s in B and B[s].get("h") and _BASE.get(s, {}).get("h")]
        h = float(np.mean(hs)) if hs else np.nan
        if not (np.isfinite(ma) and np.isfinite(cl)):
            return 9e2, None
        if not np.isfinite(h):
            h = 3.0
        J = 0.40 * ma + 0.40 * cl + 0.20 * h
        pen = 0.0; gl = {}
        for s in GATE_MA:
            r = ratio(B, "ma", (s,)); gl[f"{s}MA"] = r
            if np.isfinite(r):
                pen += 10.0 * max(0.0, r - 1.02)
        for s in GATE_CL:
            r = ratio(B, "cl", (s,)); gl[f"{s}CL"] = r
            if np.isfinite(r):
                pen += 10.0 * max(0.0, r - 1.02)
        return J + pen, dict(J=J, ma=ma, cl=cl, h=h, pen=pen, gate=gl)
    except Exception:
        return 9e2, None


def obj(x, mode):
    return evaluate((mode, x))[0]


# ── 통합 검증용 (스윕 아님) ──────────────────────────────────────────────────────────
#   현행 스택(H3)·기준선(H2)의 값은 **파일 위쪽 축 정의 앞에 한 번만** 적어 둔다.
#   여기 또 적으면 두 벌이 생겨 한쪽만 고치는 사고가 난다 (오늘 그 계열로 한 번 당했다).


def show(x=None, mode="canon_cap"):
    """후보 하나를 이 판으로 재고 **세션별로 펼쳐** 보여준다.

    왜 필요한가: 종합 점수 하나만 보면 "변속기가 제대로 태워졌는지"를 못 본다.
    08-12 사고 때 변속기 무릎각 오차가 26.8° 였는데도 종합 점수는 멀쩡해 보였다.
    그래서 **채널 원값(도·rad/s)** 을 세션별로 찍는다.
    """
    import fs_data as FD
    _ensure()
    x = H3 if x is None else x
    print(f"■ 판에 오른 trial {len(_C)} 개 "
          f"(변속기 {sum(1 for c in _C if c[3])} 개 · 무변속 {sum(1 for c in _C if not c[3])} 개)")
    print(f"  변속기 포함 여부: {'포함' if _CVT_ON else '제외 (FS_SWEEP_CVT=0)'}\n")
    v, det = evaluate((mode, x))
    _apply(env_of(mode, np.asarray(x, float)))
    B = board()
    # 오차의 절대 크기만 보면 판정이 안 된다 — 변속기는 크랭크가 더 빨리 돌아 신호 자체가 크다.
    # 그래서 **그 세션 실측 신호의 크기(RMS)** 로 나눈 몫도 같이 찍는다 (작을수록 정확).
    MAG = collections.defaultdict(lambda: collections.defaultdict(list))
    for s, p, g, cvt, d, seg, pw in _C:
        t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
        for k in CH4:
            w = np.asarray(d[k])[m]
            w = np.degrees(w) if k in ("q1", "q2") else w
            MAG[s][k].append(float(np.sqrt(np.mean(w ** 2))))
    print(f"{'세션':11s} {'구분':8s} {'n':>3s} | "
          f"{'힙각°':>13s} {'무릎각°':>14s} {'힙속도':>13s} {'무릎속도':>14s} | "
          f"{'주입비':>7s} {'폐루프비':>8s} {'높이cm':>7s}")
    print("-" * 128)
    for s in sorted(B):
        n = sum(1 for c in _C if c[0] == s)
        kind = FD.kind_of(s) if hasattr(FD, "kind_of") else ""
        kind = {"fit": "적합", "gate": "게이트", "heldout": "보관"}.get(kind, kind)
        if any(c[3] for c in _C if c[0] == s):
            kind += "·변속"
        ma = B[s].get("ma"); rm = ratio(B, "ma", (s,)); rc = ratio(B, "cl", (s,))
        h = B[s].get("h")
        cols = []
        for k, q in zip(CH4, ma or [None] * 4):
            if q is None:
                cols.append(" " * 13); continue
            mg = float(np.mean(MAG[s][k]))
            cols.append(f"{q:7.2f}({100*q/mg:4.1f}%)")
        print(f"{s:11s} {kind:8s} {n:3d} | {' '.join(cols)} | {rm:7.4f} {rc:7.4f} "
              f"{(h*100 if h else float('nan')):7.2f}")
    print("-" * 128)
    print(f"종합 {v:.5f}  (주입재생 {det['ma']:.5f} · 폐루프 {det['cl']:.5f} · "
          f"점프높이 {det['h']:.5f} · 벌점 {det['pen']:.3f})")
    print("  게이트: " + " · ".join(f"{k} {r:.4f}" for k, r in det["gate"].items()))
    print("\n  · 힙각/무릎각 [도], 힙속도/무릎속도 [rad/s] = 측정 토크를 그대로 넣고 돌렸을 때의")
    print("    오차 RMS (0 이면 완벽). 괄호 = 그 세션 실측 신호 크기 대비 몇 % 인가.")
    print("    **변속기는 크랭크가 더 빨리 돌아 신호가 1.7배 크므로 절대값만 보면 오판한다.**")
    print("  · 주입비/폐루프비 = 기준선(H2 배포 스택) 대비 배율. 1.0 이 기준선, 낮을수록 정확하다.")
    print("  · 높이 = 점프 높이 예측이 영상 실측과 어긋난 크기 [cm]. 0 이면 완벽하다.")


def compass(mode, x0, v0, lo, hi, nproc, t0, deadline_s, rounds=40):
    """마무리 다듬기 — 축마다 +한 걸음/−한 걸음을 **동시에** 재보고 좋아지면 옮긴다.

    좋아지는 데가 없으면 걸음을 절반으로 줄인다. 전역 탐색이 대충 찾아준 자리를
    조여 들어가는 단계다 (한 바퀴 = 축 수 ×2 회 평가 = 16개 동시면 20초 남짓).
    """
    import multiprocessing as mp
    n = len(x0)
    step = (hi - lo) * 0.06
    x, v = np.array(x0, float), float(v0)
    with mp.Pool(nproc) as pool:
        for it in range(rounds):
            if time.time() - t0 > deadline_s:
                print("    (시간 예산 도달 — 다듬기 중단)", flush=True); break
            cand = []
            for i in range(n):
                for sgn in (+1, -1):
                    y = x.copy(); y[i] = min(hi[i], max(lo[i], y[i] + sgn * step[i]))
                    if abs(y[i] - x[i]) > 1e-12:
                        cand.append(y)
            if not cand:
                break
            vals = pool.map(evaluate, [(mode, c) for c in cand])
            j = int(np.argmin([q[0] for q in vals]))
            if vals[j][0] < v - 1e-6:
                x, v = cand[j], float(vals[j][0])
                print(f"    다듬기 {it+1:2d}: {v:.5f}", flush=True)
            else:
                step *= 0.5
                if np.all(step < (hi - lo) * 0.002):
                    print(f"    다듬기 수렴 ({it+1} 바퀴)", flush=True); break
    return x, v


def run_mode(mode, budget_s, nproc):
    from scipy.optimize import differential_evolution
    axes = COMMON + EXTRA[mode]
    lo = np.array([a[1] for a in axes]); hi = np.array([a[2] for a in axes])
    cur = np.array([a[3] for a in axes])
    # ☠ 08-12 사고 방역: 축 목록이 COMMON(9개)+EXTRA(2개) 두 군데로 나뉘어 있어서,
    #   시작값을 현행 스택으로 옮길 때 **뒤쪽 2개를 빠뜨렸다** (힙 보정상한 2.6 vs 2.309).
    #   6시간을 잘못된 출발점에서 쓸 뻔했다. 이제 코드가 스스로 대조한다.
    if mode == "canon_cap":
        bad = [(a[0], c, h) for a, c, h in zip(axes, cur, H3) if abs(c - h) > 1e-6 * max(1, abs(h))]
        if bad:
            print("\n  ★★ 경고: 시작값이 현행 스택(H3)과 다르다 — 의도한 것인지 확인하라", flush=True)
            for nm, c, h in bad:
                print(f"      {nm:16s} 시작 {c:g}  vs  현행 {h:g}", flush=True)
            if os.environ.get("FS_ALLOW_X0_DRIFT") != "1":
                raise SystemExit("  중단. 일부러 다른 곳에서 출발하려면 FS_ALLOW_X0_DRIFT=1 로 켤 것.")
        else:
            print("  시작값 대조: 11 개 축 모두 현행 스택과 일치 ✔", flush=True)
    print(f"\n{'='*78}\n■ {mode} — 축 {len(axes)} 개", flush=True)
    for a in axes:
        print(f"    {a[0]:16s} {a[1]:>8.4g} ~ {a[2]:<8.4g}  (현행 {a[3]:g})", flush=True)
    t0 = time.time(); hist = []

    def cb(*a, **kw):
        # scipy 버전마다 콜백 인자가 다르다 (xk,convergence 또는 intermediate_result)
        xk = a[0] if a and not hasattr(a[0], "x") else (a[0].x if a else cur)
        v, det = evaluate((mode, xk))
        hist.append((float(v), list(map(float, xk))))
        el = time.time() - t0
        print(f"    [{el/60:6.1f}분] 최고 {v:.4f}  "
              f"(주입 {det['ma']:.4f} 폐루프 {det['cl']:.4f} 높이 {det['h']:.4f} 벌점 {det['pen']:.3f})"
              if det else f"    [{el/60:6.1f}분] {v:.1f}", flush=True)
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(mode=mode, t=el, v=float(v),
                                    x=list(map(float, xk)), det=det), ensure_ascii=False) + "\n")
        return el > budget_s
    res = differential_evolution(
        obj, list(zip(lo, hi)), args=(mode,), strategy="best1bin",
        maxiter=400, popsize=12, tol=1e-5, mutation=(0.4, 1.0), recombination=0.85,
        seed=20260811, polish=False, init="sobol", updating="deferred",
        workers=nproc, callback=cb, x0=cur, disp=False)
    xb, vb = np.asarray(res.x, float), float(res.fun)
    print(f"    전역 탐색 끝 {(time.time()-t0)/60:.0f}분 · 평가 {res.nfev} 회 · {vb:.5f}", flush=True)
    xb, vb = compass(mode, xb, vb, lo, hi, nproc, t0, budget_s * 1.25)
    v, det = evaluate((mode, xb))
    res.x, res.nfev = xb, res.nfev
    print(f"  → {mode} 완료 {(time.time()-t0)/60:.0f}분 · 평가 {res.nfev} 회 · 점수 {v:.4f}", flush=True)
    return dict(mode=mode, x=list(map(float, res.x)), score=float(v), det=det,
                axes=[a[0] for a in axes], cur=list(map(float, cur)),
                nfev=int(res.nfev), minutes=(time.time() - t0) / 60)


class Tee:
    """화면과 로그 파일에 동시에 쓴다 (6시간 실행이라 로그가 남아야 한다)."""

    def __init__(self, path):
        self.f = io.open(path, "a", encoding="utf-8")
        self.o = sys.stdout

    def write(self, s):
        self.o.write(s); self.f.write(s); self.f.flush()

    def flush(self):
        self.o.flush(); self.f.flush()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "board":
        show()
        return
    budget_h = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    sys.stdout = Tee(HERE / f"_GHB_sweep{_TAG}.log")
    print(f"\n{'#'*78}\n# 시작 {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'#'*78}")
    print("""
  마라톤H 공동 재적합 — 질량·탄성·마찰·변환식을 한꺼번에 맞춘다

  왜: 매달림 실측이 준 관절 마찰값을 하나씩 넣으면 전부 나빠진다. 특히 속도에
      비례하는 항을 실측대로(거의 0) 줄이면 점프 높이가 크게 무너진다. 그 항은
      관절 마찰이 아니라 다른 곳의 손실을 대신 떠맡고 있다는 뜻이고, 그걸 진짜
      물리로 바꾸려면 여러 값을 같이 움직여야 한다. 한 축씩으로는 못 넘는다.

  ★ 2 회차 (08-12 저녁) — 1 회차와 무엇이 다른가
      ① **변속기 실험 10 회분이 판에 들어왔다.** 1 회차 때는 채점 코드가 그걸 잘못
         태우고 있어서(무변속 모델에 태움 + 링크 손실 누락) 빼고 돌렸다. 이제
         trial 마다 그 trial 의 링크 길이로 모델을 다시 지어 태운다. 적합 8 세션.
      ② **출발점을 현행 스택(1 회차 승자)으로 옮겼다.** 이미 3.5% 더 정확한 자리다.
      ③ **하중에 비례하는 마찰 구조는 안 돌린다.** 1 회차에서 크게 지고 기각됐다.
         그 시간을 지금 구조에 얹어 더 촘촘히 훑는다 (6 시간 전부).

  점수: 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이. **그 전 스택(H2)이 1.0000** 이고
        낮을수록 좋다. 별도 보관본(0324)과 위치제어(0421)는 목적함수에서 빠지고
        게이트로만 쓴다. 게이트가 2% 넘게 나빠지면 벌점.
        이번에 이겨야 할 상대는 1.0000 이 아니라 **현행 스택 점수**다 (첫머리에 찍는다).

  안 건드림: 발 미끄럼 관련 두 값. 이 점수에 미끄러짐이 안 들어가 있어서 같이
             풀면 점수만 좋아지고 미끄러짐이 조용히 망가진다.

  창을 닫지 마세요. 중간에 꺼도 진행 기록(_GHB_sweep2_trials.jsonl)은 남습니다.
  1 회차 산출물(_GHB_sweep.json/.log/_trials.jsonl)은 **건드리지 않습니다.**
""", flush=True)
    nproc = max(1, min(16, (os.cpu_count() or 4) - 4))
    print(f"■ 마라톤H 공동 재적합 — 시간예산 {budget_h}시간 · 작업자 {nproc} 개", flush=True)
    print("  준비 중 (엑셀 읽기 + 기준선) …", flush=True)
    _ensure()
    print(f"  trial {len(_C)} 개 · 기준선 세션 {len(_BASE)} 개", flush=True)
    # 0.9998 근처가 나온다 — 정확히 1.0000 이 아닌 이유는 위 H2 목록이 **반올림된 값**이라서다
    # (예: 힙 건마찰 코드 기본값 0.238254 vs 목록 0.2383). 1 회차도 0.99949 였다. 정상 범위.
    b0, d0 = evaluate(("canon_cap", H2))
    print(f"  기준선 재확인 (그 전 스택 H2): 점수 {b0:.4f} — 1.0000 근처여야 정상", flush=True)
    b1, d1 = evaluate(("canon_cap", H3))
    print(f"  현행 스택 재확인 (H3): 점수 {b1:.5f} — 이 값을 이겨야 승격 후보다\n", flush=True)
    R = {}
    # ★ 08-12 저녁: **하중비례 마찰 구조(canon_fric)는 안 돌린다.** 1회차에서 종합 1.3617 로
    #   크게 지고 기각됐고(REJECTED #82), 무릎에만 적용한 재심도 15조합 전부 탈락했다(#83).
    #   그 3시간을 현행 구조에 얹어 **더 촘촘히** 훑는 편이 낫다.
    for mode in MODES:
        R[mode] = run_mode(mode, budget_h * 3600 / len(MODES), nproc)
        import safe
        safe.atomic_json_write(OUT, dict(base_check=b0, res=R))
    print(f"\n{'='*78}\n■ 맞대결 (전부 낮을수록 정확 · 기준선 = 그 전 스택 H2)")
    print(f"{'구조':14s} {'점수':>8s} {'주입재생':>9s} {'폐루프':>8s} {'점프높이':>9s} {'벌점':>7s}")
    print(f"{'기준선 H2':14s} {1.0:8.4f} {1.0:9.4f} {1.0:8.4f} {1.0:9.4f} {0.0:7.3f}")
    _dh = d1 or {}
    print(f"{'현행 H3':14s} {b1:8.5f} {_dh.get('ma',float('nan')):9.4f} "
          f"{_dh.get('cl',float('nan')):8.4f} {_dh.get('h',float('nan')):9.4f} {_dh.get('pen',0):7.3f}"
          f"   ← 이걸 이겨야 한다")
    for m, r in R.items():
        d = r["det"] or {}
        print(f"{m:12s} {r['score']:8.4f} {d.get('ma',float('nan')):9.4f} "
              f"{d.get('cl',float('nan')):8.4f} {d.get('h',float('nan')):9.4f} {d.get('pen',0):7.3f}")
    for m, r in R.items():
        print(f"\n── {m} 최적값")
        for nm, v, c in zip(r["axes"], r["x"], r["cur"]):
            tag = ""
            axes = COMMON + EXTRA[m]
            a = [z for z in axes if z[0] == nm][0]
            if abs(v - a[1]) < 1e-6 * max(1, abs(a[1])) or abs(v - a[2]) < 1e-6 * max(1, abs(a[2])):
                tag = "  ★경계 포화 — 물리 재검 필요"
            print(f"    {nm:16s} {v:10.5f}  (현행 {c:g}){tag}")
        print(f"    게이트: " + " · ".join(f"{k} {100*(x-1):+.1f}%"
                                          for k, x in (r["det"] or {}).get("gate", {}).items()))
    _s2s_report(R)
    print(f"\n저장 → {OUT}")


# ── 짐 지고 일어서기(26.06.04) 감시 — 고치는 대상이 아니라 **지켜보는 대상** ────────────
#   사용자 지시 08-12: "점프를 고치다가 이게 조용히 망가지는 걸 막자."
#   2 회차에서 실제로 무릎 토크 오차가 1.3% 나빠졌는데 아무도 몰랐다 — 이 데이터가
#   채점에 아예 안 들어가기 때문이다.
#   ★ 목적함수·벌점에는 **절대 넣지 않는다.** 탐색이 끝난 뒤 한 번만 재서 표로 찍는다.
#     (매 평가마다 재면 6 시간이 늘고, 목적함수에 넣으면 사용자가 금지한 "적합 대상 추가"가 된다.)
def _s2s_board(over):
    """짐 지고 일어서기 4 경우의 토크 오차 [N·m]. 낮을수록 정확, 0 이 완벽.
    창의 앞 80% 구간 (합격선의 자와 같은 기준)."""
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR, fs_cvt as FC
    _apply(over)
    out = []
    for sub, mass, cvt in FD.S2S_CASES:
        try:
            d = FD.load_s2s(sub)
            if d is None:
                continue
            d["_sess"] = "26.06.04"; d["_fold"] = sub
            ft = FC.cvt_ft(0.02525, ft_base=FR.fs_twin()) if cvt else None
            r = CP.cl_pair(d, None, CP.S2S_GAIN, "26.06.04", ft=ft, show_old=False)
            _t, (mo, mf), _o, fs, _m, _c, _p = r
            e = []
            for i, k in ((4, "a1"), (5, "a2")):
                real = np.asarray(mf[k]); sim = np.asarray(fs[i])
                ix = np.arange(int(len(real) * 0.80))
                e.append(float(np.sqrt(np.mean((real[ix] - sim[ix]) ** 2))))
            out.append((sub, mass, e[0], e[1]))
        except Exception:
            continue
    return out


def _s2s_report(R):
    print(f"\n{'='*78}")
    print("■ 짐 지고 일어서기(26.06.04) — **감시만** 한다 (점수에 안 들어감)")
    print("   토크 오차 [N·m] = 실측 명령 토크를 현행 환산식으로 바꾼 값과 시뮬레이션 토크의")
    print("   차이(제곱평균). 0 이 완벽. PD 제어를 흉내 낸 판, 창 앞 80%.")
    try:
        cur = _s2s_board(env_of("canon_cap", H3))
        rows = {"현행 출발점": cur}
        for m, r in R.items():
            rows[m] = _s2s_board(env_of(m, r["x"]))
    except Exception as ex:
        print(f"   (재기 실패: {type(ex).__name__} {ex})")
        return
    names = [c[0] for c in cur]
    print(f"\n   {'경우':16s} {'짐':>6s} | " + " | ".join(f"{k[:12]:>17s}" for k in rows))
    print(f"   {'':16s} {'':>6s} | " + " | ".join("     힙     무릎" for _ in rows))
    print("   " + "-" * (26 + 20 * len(rows)))
    for i, nm in enumerate(names):
        line = f"   {nm:16s} {cur[i][1]:4.1f}kg | "
        line += " | ".join(f"{rows[k][i][2]:7.2f} {rows[k][i][3]:8.2f}"
                           if i < len(rows[k]) else "        -        " for k in rows)
        print(line)
    print("   " + "-" * (26 + 20 * len(rows)))
    f = lambda v, j: np.mean([x[j] for x in v]) if v else float("nan")
    print(f"   {'평균':16s} {'':>6s} | "
          + " | ".join(f"{f(rows[k],2):7.2f} {f(rows[k],3):8.2f}" for k in rows))
    base = f(cur, 3)
    for k in rows:
        if k == "현행 출발점":
            continue
        v = f(rows[k], 3)
        print(f"\n   ⇒ {k}: 무릎 토크 오차 {base:.2f} → {v:.2f} N·m "
              f"({100*(v/base-1):+.1f}%)  " + ("좋아짐" if v < base else "**나빠짐 — 확인 필요**"))


if __name__ == "__main__":
    main()
