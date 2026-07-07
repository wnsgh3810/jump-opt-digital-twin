# -*- coding: utf-8 -*-
"""GOAL21 Notion 증축 — ③ 궤적 최적화 지도 본문 5~9절 추가 + child ③-a IPOPT."""
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}

TARGET = "396ab81d255081b2bce8fa8248589df9"  # ③ 궤적 최적화 지도


def rt(text):
    out = []
    for i, seg in enumerate(text.split("**")):
        if seg:
            out.append({"type": "text", "text": {"content": seg},
                        "annotations": {"bold": i % 2 == 1}})
    return out


def h2(t): return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt(t)}}
def h3(t): return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
def para(t): return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(t)}}
def quote(t): return {"object": "block", "type": "quote", "quote": {"rich_text": rt(t)}}
def bullet(t): return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(t)}}
def callout(t, emoji="💡"):
    return {"object": "block", "type": "callout", "callout": {"icon": {"emoji": emoji}, "rich_text": rt(t)}}
def code(t, lang="plain text"):
    return {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": lang}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def new_page(parent, title):
    r = requests.post("https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                      json={"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status()
    time.sleep(0.6)
    return r.json()["id"]


def append(page, blocks, batch=80):
    total = 0
    for i in range(0, len(blocks), batch):
        chunk = blocks[i:i + batch]
        for attempt in range(8):
            r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                               headers={**H, "Content-Type": "application/json"},
                               json={"children": chunk})
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2))
                print(f"429 rate limited, sleep {wait}s (attempt {attempt+1})", flush=True)
                time.sleep(wait + 0.5)
                continue
            if r.status_code != 200:
                raise RuntimeError(r.text[:800])
            total += len(chunk)
            break
        else:
            raise RuntimeError("429 retry exceeded")
        time.sleep(0.6)
    return total


# ════════════════════════════════════════════════════════════════
# 본문 5~9절 — TARGET("③ 궤적 최적화 지도") 끝에 APPEND
# ════════════════════════════════════════════════════════════════
body = []

# ---------------- 5. 용어 완전 사전 ----------------
body += [
    h2("5. 용어 완전 사전 (표)"),
    para("③ 전체와 child ③-a에서 반복적으로 등장하는 용어를 한 곳에 모았습니다. 아래 절(6~9)이나 child 페이지를 읽다가 "
         "막히면 이 표로 돌아오시면 됩니다."),
    table([
        ["용어", "정의"],
        ["NLP (비선형계획, Nonlinear Program)", "목적함수나 제약 중 하나 이상이 비선형인 최적화 문제: min f(x) s.t. g(x)=0, "
         "h(x)≤0. 우리 궤적최적화의 최종 형태."],
        ["결정변수 (decision variable)", "NLP가 값을 정하는 미지수 x — 우리 문제에서는 각 시간점의 관절각·각속도, 토크, "
         "그리고 phase 길이(자유 시간)까지 포함."],
        ["등식 제약 (equality constraint) g(x)=0", "반드시 정확히 0이어야 하는 조건 — 동역학 결함(defect), 스탠스 중 "
         "발끝-지면 위치 일치."],
        ["부등식 제약 (inequality constraint) h(x)≤0", "한계를 넘지 않아야 하는 조건 — 토크 한계, GRF≥0, 마찰원뿔, "
         "관절 가동범위."],
        ["KKT 조건 (Karush–Kuhn–Tucker)", "NLP의 국소 최적점이 반드시 만족하는 4개 연립조건(정지성·원시가능·쌍대가능·"
         "상보성) — IPOPT가 '다 풀렸다'고 판단하는 기준 그 자체 (child ③-a 3절)."],
        ["라그랑주 승수 (Lagrange multiplier) λ, ν", "제약의 '그림자 가격(shadow price)' — 그 제약을 살짝 풀어주면 목적함수가 "
         "얼마나 좋아지는지. 동역학 제약의 승수는 물리적으로 힘 그 자체가 됨 (child ③-a 4절)."],
        ["내점법 (interior-point method)", "부등식을 로그 장벽(barrier)으로 녹여 '제약 안쪽 영역'만 탐색하며 점진적으로 "
         "경계에 접근하는 방법 — IPOPT의 이름(Interior Point OPTimizer) 그대로."],
        ["SQP (순차 이차계획법, Sequential Quadratic Programming)", "매 반복마다 원래 NLP를 국소 이차근사(QP)로 바꿔 "
         "푸는 solver 계열 — 내점법과 나란한 대안 (예: SNOPT)."],
        ["sparsity (희소성)", "변수·제약 개수는 많아도, 각 제약이 실제로 의존하는 변수는 소수뿐이라 야코비안·헤시안 대부분이 "
         "0인 구조. collocation은 각 구간 제약이 그 구간의 변수만 건드려 sparsity가 극단적으로 좋음."],
        ["warm start", "이전에 푼 비슷한 문제의 해를 다음 문제의 초기값으로 재사용 — 수렴 반복 수를 크게 줄임."],
        ["transcription", "연속시간 최적제어 문제를 유한 개의 결정변수를 가진 NLP로 '번역'하는 절차 전체(shooting/"
         "collocation의 선택 포함)."],
        ["defect (결함 제약)", "이산화된 두 시점 사이에서 동역학이 실제로 성립하는지를 재는 등식 제약 — 0이면 그 구간의 "
         "궤적이 물리법칙(운동방정식)을 만족한다는 뜻. 6절 참조."],
        ["mesh / knot", "궤적을 이산화하는 시간 격자. mesh는 격자 전체, knot은 각 다항식 조각의 경계점(구간 시작·끝)."],
        ["complementarity 제약", "'A=0 이거나 B=0(또는 둘 다 0)'이라는 either-or 논리를 A≥0, B≥0, A·B≤ε 형태의 연속 "
         "부등식으로 표현한 것 — 접촉의 '닿거나 안 닿거나' 논리를 NLP 제약으로 바꾸는 핵심 도구 (8절)."],
    ]),
    h3("표기 규칙"),
    table([
        ["기호", "의미"],
        ["x", "상태 벡터 (q, dq) — 관절각과 각속도"],
        ["u", "입력 벡터 — 관절 토크 τ"],
        ["f(x,u)", "동역학 우변 — 상태의 시간미분 ẋ = f(x,u)"],
        ["g(x)=0 / h(x)≤0", "각각 등식·부등식 제약 함수"],
        ["λ, ν", "각각 등식·부등식 제약의 라그랑주 승수"],
        ["Δt", "격자 구간의 스텝 크기 (h는 제약함수 기호와 겹쳐 이 페이지에서는 Δt로 표기)"],
        ["N", "phase 내 격자 구간 개수"],
    ]),
    h3("자주 헷갈리는 짝 4가지"),
    bullet("**등식 vs 부등식** — 등식은 '정확히 이 값'(예: 발끝이 정확히 지면 위), 부등식은 '이 범위 안'(예: 토크가 한계 "
           "이하). 등식은 언제나 '작동 중'이고, 부등식은 작동할 수도(active) 안 할 수도(inactive) 있음 — 이 차이가 KKT의 "
           "상보성 조건을 만듭니다."),
    bullet("**라그랑주 승수 vs 벌점(penalty) 가중치** — 벌점은 사람이 미리 정하는 임의의 숫자(어긋나면 비용을 더함)이고, "
           "라그랑주 승수는 solver가 '정확한 등호를 만들기 위해 필요한 만큼' 스스로 계산해내는 값 — 승수는 결과이지 "
           "설정이 아닙니다."),
    bullet("**warm start vs cold start** — cold start는 임의·균일 초기값에서 출발(수렴 느림, 로컬해 위험), warm start는 "
           "물리적 초기 추정이나 이전 해에서 출발(수렴 빠름, 좋은 해로 수렴할 확률↑)."),
    bullet("**shooting의 '상태' vs collocation의 '상태'** — shooting에서 상태는 변수가 아니라 적분의 결과(부산물)이고, "
           "collocation에서는 상태 자체가 결정변수 — 이 차이가 6절의 defect 제약이 필요한 이유입니다."),
]

# ---------------- 6. collocation 결함 제약 손 전개 ----------------
body += [
    h2("6. collocation 결함 제약 손 전개"),
    para("5절의 'defect'가 실제로 무엇을 계산하는지, 가장 단순한 형태부터 우리가 쓰는 형태까지 손으로 전개합니다. 구간을 "
         "k=0,...,N-1로 나누고 스텝 크기 Δt(=T/N — T는 phase 길이, 자유 시간이면 그 자체도 결정변수)를 씁니다."),
    code("오일러(Euler) 결함 — 가장 단순한 형태, N개 등식 제약:\n\n"
         "δ_k = x_{k+1} − x_k − Δt·f(x_k, u_k) = 0      (k = 0, ..., N-1)\n\n"
         "x_k: k번째 격자점의 상태(q, dq), u_k: 그 구간의 입력(τ), f: 동역학 우변(가속도)."),
    para("해석: x_{k+1}이 'x_k에서 출발해 Δt만큼 오일러 적분한 값'과 정확히 같아야 한다는 등식입니다. 1차 정확도라 오차가 "
         "O(Δt²)/스텝 — 우리처럼 정밀한 토크·GRF가 필요한 문제엔 성기지만, 개념을 보기엔 가장 직관적입니다."),
    code("Hermite–Simpson 결함 — 우리가 쓰는 3차 정확도 형태:\n\n"
         "x_m = (x_k + x_{k+1})/2 + (Δt/8)·(f_k − f_{k+1})        ← 구간 중점 상태(암시적으로 정의)\n"
         "δ_k = x_{k+1} − x_k − (Δt/6)·(f_k + 4·f_m + f_{k+1}) = 0  ← 심슨 적분 규칙의 등식화\n\n"
         "f_k = f(x_k, u_k),  f_m = f(x_m, u_m),  f_{k+1} = f(x_{k+1}, u_{k+1})"),
    para("직관: 구간 양끝과 중점 세 곳에서 가속도를 평가해 심슨 적분(포물선 근사)으로 다음 상태를 예측하고, 그 예측이 실제 "
         "x_{k+1}과 같아야 한다고 강제합니다. 4차 정확도(O(Δt⁴)/스텝)로 오일러보다 훨씬 적은 격자점으로 같은 정밀도를 냅니다 "
         "— 우리 task들이 이 방식을 쓰는 이유."),
    table([
        ["방식", "정확도(스텝당)", "구간당 동역학 평가", "구간당 등식 제약"],
        ["오일러", "O(Δt²)", "1회 (f_k만)", "1개"],
        ["Hermite–Simpson", "O(Δt⁴)", "3회 (f_k, f_m, f_{k+1})", "1개"],
    ]),
    code("야코비안의 블록-띠(block-banded) 구조 (N=4 예시, ×=0이 아닌 블록):\n\n"
         "      x0 u0 x1 u1 x2 u2 x3 u3 x4\n"
         "δ0 [  ×  ×  ×  ×  .  .  .  .  . ]\n"
         "δ1 [  .  .  ×  ×  ×  ×  .  .  . ]\n"
         "δ2 [  .  .  .  .  ×  ×  ×  ×  . ]\n"
         "δ3 [  .  .  .  .  .  .  ×  ×  × ]\n\n"
         "각 defect δ_k는 그 구간의 (x_k,u_k,x_{k+1},u_{k+1})만 건드림 → 대각선 근방만 채워짐 (희소)"),
    bullet("격자점 수 N: 스탠스 구간은 접촉력이 빠르게 변하는 이륙 직전(whip)까지 담아야 해서 조밀하게, 비행 구간은 탄도라 "
           "성기게 — 우리 task들의 불균등 mesh 배치가 이 이유입니다."),
    bullet("u_m(중점 입력)은 보통 (u_k+u_{k+1})/2로 두거나 별도 결정변수로 둠 — 후자가 자유도는 늘지만 토크 프로파일이 "
           "더 매끄러워집니다."),
    bullet("Hermite-Simpson은 3차 다항식 collocation의 특수 케이스 — 더 고차인 Legendre-Gauss-Radau(LGR) collocation은 "
           "구간당 정확도가 더 높아 격자점을 줄일 수 있지만 야코비안이 조밀해지는 트레이드오프가 있습니다 (우리는 "
           "Hermite-Simpson으로 정확도/속도 균형을 맞춤)."),
    bullet("defect가 N개, 상태변수가 (N+1)개 격자점 × 상태차원이면 — 등식 제약 개수가 상태변수 개수와 딱 맞아떨어지도록 "
           "설계된 것이 collocation의 구조입니다."),
    quote("해설 | 동역학을 '적분해서 확인'하는 게 아니라 '제약으로 강제'합니다 — 그래서 상태·입력이 모두 결정변수이고, "
          "야코비안이 블록-띠(block-banded) 희소 구조를 가집니다. IPOPT가 이 sparsity를 그대로 활용해 변수 수천 개도 "
          "빠르게 풉니다."),
]

# ---------------- 7. 우리 점프 NLP의 실제 뼈대 ----------------
body += [
    h2("7. 우리 점프 NLP의 실제 뼈대"),
    bullet("**phase 2개**(스탠스 → 비행) — 각 phase 길이도 결정변수(자유 시간, free final time): 점프 높이나 타이밍을 "
           "사람이 미리 정하지 않고 NLP가 스스로 찾습니다."),
    bullet("**스탠스 제약**: 발끝 위치를 지면의 한 점에 고정(등식) + GRF_z ≥ 0(부등식, 지면은 당길 수 없음) + "
           "|GRF_x| ≤ μ·GRF_z(마찰원뿔) + |τ| ≤ 토크 한계(액추에이터 물리) + 관절 가동범위."),
    bullet("**이륙 경계**(phase 1→2 접합): GRF가 정확히 0으로 연속 전환, 상태(q, dq)는 두 phase 사이에 연속(등식 제약) — "
           "'갑자기 순간이동' 방지."),
    bullet("**비행**: 접촉힘 항 자체가 존재하지 않음(제약이 아니라 아예 모델에서 제거) — 순수 탄도(포물선) 동역학만."),
    bullet("**목적**: 점프 높이 최대화(대표 task) 또는 에너지·부드러움 최소화 등 — 지금까지 task 0~28종이 서로 다른 "
           "목적·제약 조합을 씁니다."),
    bullet("**동역학**: 4-bar 축소좌표 해석식(사용자 유도, 계수 A, B, K, IΣ) + a_hat 역모델(전류→축토크)을 CasADi 표현식 "
           "그래프로 작성 → 자동미분 → IPOPT 호출."),
    bullet("**산출물**: τ(t), q(t) 전체 궤적 → MuJoCo 트윈에서 open-loop 리허설('진짜로 되는지' 검증) → 검증 통과분만 "
           "배포 CSV로."),
    bullet("**G20 실증 사례**: NLP 접촉 강성을 트윈 fit 유효강성 k_eq≈1.3×10⁵로 맞춘 뒤 sim-real 갭이 −14%에서 −4.4%로 "
           "줄고, 실제 점프 높이가 +6.5cm 개선 — 트윈↔NLP 파라미터 일치가 실질 성능으로 이어진 실증입니다."),
    code("결정변수 벡터 (개념적 레이아웃):\n\n"
         "X = [ x_0, u_0, x_1, u_1, ..., x_N, T1,       ← phase 1 (스탠스)\n"
         "      x_0', u_0', ..., x_M', T2 ]              ← phase 2 (비행)\n\n"
         "등식/부등식 제약 개수 ≈ 상태차원×(N+M) [defect] + 부등식 개수×격자점 수\n"
         "→ 변수 수백~수천 개, 그러나 sparsity(6절) 덕분에 IPOPT는 초 단위로 처리"),
    table([
        ["", "스탠스 (phase 1)", "비행 (phase 2)"],
        ["결정변수", "q(t), dq(t), τ(t)", "q(t), dq(t)"],
        ["등식 제약", "발끝-지면 위치 고정, defect", "defect만 (접촉 없음)"],
        ["부등식 제약", "GRF_z≥0, 마찰원뿔, |τ|≤한계, 관절범위", "관절범위만"],
        ["접촉힘", "라그랑주 승수로 계산됨 (= GRF, child ③-a 4절)", "존재하지 않음"],
        ["길이", "자유 시간 변수 T1 (하한 있음, 9절)", "자유 시간 변수 T2"],
    ]),
    table([
        ["목적 계열", "예시", "제약 특이사항"],
        ["점프 높이 최대화", "task0 (vertical jump, no CVT / with CVT)", "표준 뼈대 그대로"],
        ["에너지 최소화", "저부하 sit-to-stand 계열", "목표 높이를 등식으로 고정, τ² 적분 최소화"],
        ["payload 조건부", "task28 (payload sit2stand)", "질량 파라미터를 추가 등식으로 고정, 나머지 뼈대 동일"],
        ["CVT 비율 자유화", "with_cvt 계열", "크랭크 길이 l_i를 추가 결정변수로"],
    ]),
    quote("한 줄 | phase를 사람이 나누고(=스케줄 고정, 8절과 대비), 그 안의 물리는 전부 등식·부등식 제약으로 정확히 강제 — "
          "이게 collocation×phase-고정의 실체입니다."),
]

# ---------------- 8. contact-implicit 한 걸음 더 ----------------
body += [
    h2("8. contact-implicit 한 걸음 더"),
    para("7절은 '언제 스탠스이고 언제 비행인지'를 사람이 미리 정합니다. contact-implicit 궤적최적화는 그 스케줄 자체를 "
         "사람이 안 정합니다 — 발이 닿았는지 안 닿았는지조차 NLP가 풀어야 할 미지수로 둡니다."),
    code("상보성 제약으로 접촉을 직접 표현:\n\n"
         "0 ≤ φ(q) ⊥ λ ≥ 0\n\n"
         "φ(q): 발끝과 지면 사이의 거리(간극, gap function) — 발이 지면에 닿으면 0, 떠 있으면 양수\n"
         "λ: 그 순간의 접촉력(수직 GRF)\n"
         "⊥ (상보성): φ와 λ 둘 다 0 이상이면서, 적어도 하나는 반드시 0 — '떠 있으면 힘이 0, 힘이 있으면 붙어 있음'을 "
         "동시에 강제"),
    para("문제는 이 상보성 제약이 **제약자격(LICQ, 선형독립 제약자격)을 구조적으로 위반**한다는 점입니다 — φ=0인 지점에서 "
         "φ와 λ의 제약 기울기가 서로 얽혀 KKT 조건이 잘 정의되지 않고, IPOPT 같은 내점법 solver가 그 근방에서 헤매기 "
         "쉽습니다(수렴 실패, 과도한 반복). 완화 기법: 등식 φ·λ=0 대신 φ·λ ≤ ε(작은 양수)로 느슨하게 풀고, ε을 점점 0으로 "
         "줄여가며 해를 이어갑니다(homotopy) — Posa, Cantu, Tedrake 2014 (\"A Direct Method for Trajectory Optimization "
         "of Rigid Bodies Through Contact\", IJRR)가 이 완화 기법을 정리한 대표 문헌입니다."),
    para("**언제 필요한가**: 어떤 동작을 언제 접촉하고 언제 떼야 하는지 자체가 미지수인 문제 — 새로운 보행 패턴 발견, "
         "다중 접촉(손+발) 동작, 재도약(더블 점프) 타이밍 탐색 같은 '스케줄 탐색' 문제에서 강력합니다. **우리 단일 점프"
         "(스탠스 1번 → 비행 1번, 스케줄이 자명)에는 불필요** — 7절의 phase 고정이 정확히 같은 답을 훨씬 쉽게 줍니다. "
         "contact-implicit을 도입할 시점은 오직 '접촉 스케줄 자체가 궁금해질 때'입니다(예: 착지 후 재도약 최적 타이밍)."),
    bullet("완화 파라미터 ε의 스케줄(annealing)이 실무 관행 — 처음엔 크게 풀어 대략적 스케줄을 찾고, ε을 줄이며 물리적으로 "
           "정밀한 해로 수렴시킵니다."),
    bullet("이 상보성은 ②절(접촉 동역학 마스터)에서 본 Signorini 조건(0≤r⊥F≥0)과 정확히 같은 형태 — MuJoCo의 soft "
           "contact가 매 스텝 수치적으로 근사해 푸는 바로 그 조건을, 여기서는 NLP 제약으로 명시적으로 풀겠다는 뜻입니다. "
           "MuJoCo의 soft contact와 이 완화된 상보성은 철학적으로 친척 — 둘 다 '논리를 부드러운 부등식으로 근사'한다는 "
           "같은 아이디어의 다른 구현입니다."),
    table([
        ["기준", "phase 고정 (우리, 7절)", "contact-implicit (본 절)"],
        ["스케줄", "사람이 설계", "NLP가 발견"],
        ["제약자격(LICQ)", "충족 — 매끄러운 표준 NLP", "구조적 위반 — 완화·homotopy 필요"],
        ["수렴성", "IPOPT가 잘 수렴", "까다로움, 초기화·ε 스케줄에 민감"],
        ["표현력", "정해진 스케줄 안에서만 최적", "새로운 접촉 패턴 발견 가능"],
        ["우리 문제 적합도", "◎ 스케줄 자명(단일 점프)", "△ 지금은 과한 도구"],
    ]),
    quote("한 줄 | contact-implicit은 '스케줄까지 찾아주는' 대신 수렴이 까다로운 상보성 제약을 대가로 치릅니다 — 우리처럼 "
          "스케줄이 이미 자명한 문제에는 쓸모보다 비용이 큽니다."),
]

# ---------------- 9. 실패 모드 도감 ----------------
body += [
    h2("9. 실패 모드 도감"),
    para("IPOPT를 실제로 돌리며 마주치는 실패는 놀랍도록 소수의 패턴으로 수렴합니다. 아래 6가지는 전부 우리 프로젝트에서 "
         "실제로 겪은 사례입니다."),
    table([
        ["증상", "원인", "처방"],
        ["Infeasible 반환", "제약끼리 모순 (초기 자세가 지면을 뚫고 들어가 있는 등)", "제약 완화 → 조이기 순서로 재시도 "
         "(단계적 continuation)"],
        ["수렴 안 함 / 진동", "스케일링 불량 (각도 O(1) rad, 토크 O(10) Nm, 시간 O(0.1) s가 같은 크기로 취급됨)",
         "변수·제약을 O(1) 근방으로 정규화 — \"IPOPT가 안 풀리면 대개 모델이 아니라 스케일링\"이 우리 경험칙"],
        ["이상한 로컬 해", "초기 궤적(initial guess)이 나쁨", "물리적 보간으로 초기화(정적 자세 → 탄도), 이전 해를 "
         "warm start로 재사용"],
        ["목적은 좋은데 τ 톱니", "정규화 부족 — 순수 성능 목적은 고주파 채터링으로도 값만 좋으면 만족", "Δu(연속 스텝 "
         "간 토크 변화량) 벌점 항 — 우리 task30 사례: 스무스니스 계수 10배로 해결"],
        ["phase 길이 0으로 붕괴", "시간 변수에 하한이 없어 solver가 '순식간에 끝내는' 궤도로 도피", "T ≥ T_min 하한 "
         "제약 추가"],
        ["해는 나왔는데 트윈에서 실패", "모델 갭 (접촉·마찰·파라미터가 NLP 해석식과 트윈 사이에서 다름)", "트윈 리허설 "
         "필수 게이트 — NLP 해를 최종 답으로 신뢰하지 않고 항상 트윈으로 재확인 (우리 파이프라인)"],
    ]),
    callout("실제 사례 | task30(payload sit2stand)에서 목적함수만 최적화했더니 τ가 매 스텝 부호를 바꾸는 톱니 해가 "
            "나왔습니다 — 트윈에서 재생하면 모터가 못 따라가는 궤적이었죠. Δτ 벌점 계수를 10배로 올리자 목적값은 "
            "손해를 봤지만 실제로 배포 가능한 매끄러운 해가 나왔습니다 — '수학적으로 최적'과 '실제로 쓸 수 있음' "
            "사이의 전형적인 간극입니다.", "⚠️"),
    bullet("공통 패턴: 여섯 증상 중 넷(수렴 안 함/이상한 로컬해/톱니/phase 붕괴)은 사실 하나의 원인 계열 — '문제를 푸는 "
           "사람이 IPOPT에게 준 자유도의 대가를 어떻게 통제하는가'로 수렴합니다. 스케일링·초기화·정규화·경계조건이 "
           "그 통제 수단 4종입니다."),
    quote("한 장 요약(5~9절) | NLP는 용어(5) → 결함 제약이라는 핵심 메커니즘(6) → 우리 문제의 구체적 골격(7) → 스케줄까지 "
          "푸는 확장판과 그 대가(8) → 그리고 실전에서 이 모든 게 어떻게 깨지는지(9)로 이어집니다. IPOPT는 마법이 아니라 "
          "'결함=0'이라는 제약 덩어리를 스케일 맞춰 정직하게 푸는 도구이고, 실패는 거의 항상 스케일링·초기화·제약설계 "
          "중 하나로 환원됩니다. IPOPT가 내부에서 정확히 무엇을 하는지는 child ③-a에서 이어집니다."),
]

print(f"body blocks prepared: {len(body)}", flush=True)
n_body = append(TARGET, body)
print(f"APPENDED to TARGET: {n_body} blocks", flush=True)

# ════════════════════════════════════════════════════════════════
# child: ③-a IPOPT가 실제로 하는 일 — 내점법과 라그랑주 승수의 물리
# ════════════════════════════════════════════════════════════════
child = new_page(TARGET, "③-a IPOPT가 실제로 하는 일 — 내점법과 라그랑주 승수의 물리")
print("child_id", child, flush=True)

cb = []

cb += [
    quote("용어 | **barrier(장벽) 함수**: 부등식 제약 경계에 가까워질수록 무한대로 커지는 벌점 — log(s)의 음수. "
          "**slack 변수 s**: 부등식 h(x)≤0을 h(x)+s=0, s≥0으로 바꿔주는 여유변수. **μ (barrier parameter)**: 장벽의 "
          "세기 — 크면 벽이 두껍고(안전하지만 부정확), 작으면 벽이 얇아짐(경계에 접근, 정확). **restoration phase**: "
          "원래 목적을 잠시 포기하고 '제약 위반량'만 줄이는 IPOPT의 구조 모드."),
]

cb += [
    h2("1. 문제 형식 — IPOPT가 실제로 받는 입력"),
    para("IPOPT는 임의의 최적화가 아니라 정확히 이 형태의 문제만 풉니다:"),
    code("min f(x)   s.t.   g(x) = 0,   h(x) ≤ 0\n\n"
         "f: 목적함수 (우리는 −점프높이, 또는 에너지)\n"
         "g: 등식 제약 전부 (defect + 발끝고정)\n"
         "h: 부등식 제약 전부 (GRF≥0, 마찰원뿔, 토크한계 등)"),
    para("CasADi NLP 빌더가 우리가 적은 물리 조건을 전부 이 g, h 두 함수로 모아줍니다 — 5절의 defect δ_k도 g의 "
         "일부입니다."),
]

cb += [
    h2("2. 내점법 직관 — 전기 철조망에서 낮은 펜스로"),
    para("부등식 h(x)≤0을 다루는 가장 쉬운(그러나 나쁜) 방법은 '위반하면 못 가게 딱 막기'인데, 이건 미분이 불연속이라 "
         "gradient 기반 solver가 다룰 수 없습니다. 내점법의 해법: 부등식을 아예 없애고, 그 자리에 **장벽(barrier)** "
         "비용을 심습니다."),
    code("min f(x) − μ·Σᵢ log(−hᵢ(x))   s.t.   g(x) = 0\n\n"
         "−log(−hᵢ(x))는 hᵢ(x)가 0에 가까워질수록(경계에 다가갈수록) +∞로 폭발\n"
         "→ 경계가 '넘을 수 없는 벽'이 아니라 '다가갈수록 비용이 무한'해지는 것으로 바뀜"),
    bullet("비유: 처음엔 μ가 커서 장벽이 전기 철조망처럼 셈 — 경계 근처엔 얼씬도 못 하고 안쪽 넓은 영역만 봄. 반복이 "
           "진행되며 μ를 점점 줄이면 철조망이 낮은 나무 펜스로 서서히 바뀌고, 그제서야 solver가 펜스(진짜 경계)에 바짝 "
           "붙은 진짜 최적해를 찾아갑니다."),
    bullet("실무 구현은 slack 변수 s>0를 도입해 h(x)+s=0으로 바꾸고 −μΣlog(s)를 더하는 형태를 씁니다 — s가 '경계까지 "
           "남은 여유'이고 IPOPT 로그에 종종 보이는 값입니다."),
    bullet("μ의 스케줄: 매 외부 반복(outer iteration)마다 μ를 일정 비율(보통 0.1~0.2배씩)로 줄이며, 각 μ에서 g(x)=0만 "
           "남은(상대적으로 쉬운) 등식제약 NLP를 뉴턴법으로 몇 스텝 풂 — 이 전체가 '내점법'입니다."),
]

cb += [
    h2("3. KKT 조건 4줄과 각각의 물리적 뜻"),
    para("내점법이 μ→0으로 수렴한 극한에서, 해가 반드시 만족하는 4개 연립조건이 KKT 조건입니다."),
    table([
        ["조건", "수식", "뜻"],
        ["정지성 (stationarity)", "∇f(x) + Σλᵢ∇gᵢ(x) + Σνⱼ∇hⱼ(x) = 0", "힘의 균형 — 목적함수를 개선하려는 '힘'과 제약들이 "
         "밀어내는 '힘'이 정확히 상쇄되는 지점. 더 이상 어느 방향으로도 공짜로 좋아질 수 없다는 뜻."],
        ["원시 가능성 (primal feasibility)", "g(x)=0,  h(x)≤0", "해가 실제로 물리적으로 허용된 상태 — 모든 등식·부등식을 "
         "어기지 않음."],
        ["쌍대 가능성 (dual feasibility)", "νⱼ ≥ 0 (모든 부등식 승수)", "부등식 승수는 항상 음이 아님 — 제약은 '밀어내는 "
         "방향'으로만 힘을 가할 수 있고 '끌어당길' 수는 없다는 물리적 제한(지면이 발을 밀 수는 있어도 빨아들일 수는 "
         "없는 것과 같은 논리)."],
        ["상보성 (complementary slackness)", "νⱼ·hⱼ(x) = 0 (각 j에 대해)", "제약이 작동 중이 아니면(hⱼ<0, 여유 있음) "
         "그 승수는 반드시 0 — 실제로 경계에 닿아 있는 제약만 힘(승수)을 가짐. 발이 공중에 떠 있으면 GRF는 0이어야 "
         "한다는 것과 정확히 같은 논리 (= Signorini 조건, 8절)."],
    ]),
    para("IPOPT의 내부 종료 조건은 사실상 이 넷을 '허용오차 안에서' 동시에 만족하는지를 검사하는 것입니다 — 5절 로그의 "
         "dual infeasibility, constraint violation이 바로 이 넷 중 정지성/원시가능성의 잔차입니다."),
]

cb += [
    h2("4. 라그랑주 승수의 물리 — 동역학 제약의 승수는 '힘'이다"),
    para("이 절이 이 페이지에서 가장 중요한 통찰입니다. 등식 제약 g(x)=0에 붙는 라그랑주 승수 λ는 추상적인 숫자가 아니라, "
         "**그 제약을 유지하기 위해 시스템에 실제로 가해져야 하는 순간의 구속력**입니다."),
    bullet("본문 6절의 동역학 결함 제약 δ_k=0은 사실 '뉴턴의 운동방정식이 이 순간 성립한다'는 등식입니다. 그 제약의 승수는 "
           "'운동방정식을 정확히 만족시키기 위해 추가로 필요한 가상의 일반화力(generalized force)' — 관성력·중력·구동토크의 "
           "균형에 부족한 부분을 메우는 항입니다."),
    bullet("**스탠스 구간의 '발끝 = 지면의 한 점' 등식 제약의 승수가 바로 그 순간의 GRF입니다.** 이는 우연이 아니라 "
           "라그랑주 역학의 표준 결과 — 구속조건 φ(q)=0을 유지하기 위해 필요한 구속력은 항상 그 구속의 야코비안 방향으로 "
           "승수 배만큼 작용합니다(F_constraint = λ·∇φ(q)). 발끝 위치 구속의 야코비안은 지면 법선·접선 방향이므로, 그 "
           "승수 성분이 곧 수직·수평 GRF입니다."),
    callout("실무적 의미 | 수기 해석 동역학에서 GRF를 얻으려면 보통 별도로 접촉력 방정식을 풀거나 뉴턴-오일러를 거꾸로 "
            "계산해야 합니다. 그런데 collocation NLP를 IPOPT로 풀면, **최적해와 함께 라그랑주 승수도 부산물로 나오고, "
            "그게 곧 GRF 시계열입니다** — 별도 계산이 필요 없습니다. CasADi에서는 최적화 후 제약의 dual 값을 그대로 "
            "꺼내면 됩니다.", "⚙️"),
    bullet("같은 논리가 비행-스탠스 접합 제약(상태 연속)에도 적용되지만, 그 제약에 물리적 '힘' 의미는 없습니다 — 접합 "
           "제약은 '순간이동 금지'일 뿐 실제 구속력이 아니므로, 그 승수는 수학적 조정값으로 읽어야 합니다. **모든 등식 "
           "제약의 승수가 힘인 것은 아니고, '물리적 구속을 표현하는 제약'의 승수만 힘으로 해석됩니다.**"),
]

cb += [
    h2("5. 실무 출력 읽기 — IPOPT 로그가 말해주는 것"),
    table([
        ["로그 항목", "뜻", "의심할 상황"],
        ["iter", "외부 반복 횟수 — μ가 한 번 줄어들 때마다 보통 여러 iter 소요", "특정 μ에서 iter가 수백을 넘도록 "
         "안 줄면 그 근방에서 헤매는 것"],
        ["objective", "현재 x에서의 f(x) 값", "값이 거의 안 바뀌는데 constraint viol.도 안 줄면 정체(stall)"],
        ["inf_pr (primal infeasibility)", "‖g(x)‖와 max(h(x),0)의 크기 — 지금 얼마나 물리법칙을 어기고 있는가", "0으로 "
         "잘 줄어야 정상. 끝까지 안 줄면 제약이 서로 모순 (9절 표 1행)"],
        ["inf_du (dual infeasibility)", "KKT 정지성 조건의 잔차 — 힘의 균형이 얼마나 안 맞는가", "primal은 좋은데 dual만 "
         "안 줄면 스케일링 문제(9절 표 2행)인 경우가 많음"],
        ["mu (barrier parameter)", "현재 장벽의 세기 — 2절의 μ가 그대로 로그에 찍힘", "정상: 매 외부반복 꾸준히 감소. "
         "한 값에 오래 멈추면 그 μ 근방이 어려운 지점"],
        ["ls (line search steps)", "그 반복에서 스텝 길이를 몇 번 줄여 받아들였는가", "매번 크면(예: >10) 초기화나 "
         "스케일링이 나쁘다는 신호"],
        ["restoration phase 진입", "원래 목적을 잠시 포기하고 오직 inf_pr만 줄이려 시도하는 특수 모드", "**뜨면 의심 1순위: "
         "스케일링 또는 제약 모순(9절 표 1·2행) — 정상적인 좋은 문제에서는 거의 안 뜸**"],
    ]),
]

cb += [
    h2("6. CasADi와의 관계 — '미분을 손으로 안 쓰는 것'이 이 조합의 전부"),
    para("CasADi는 solver가 아니라 **표현식 그래프(expression graph) 빌더 + 자동미분(AD) 엔진**입니다. 우리가 f, g, h를 "
         "심볼릭 변수(q, dq, τ, T 등)로 한 번 적으면:"),
    bullet("① CasADi가 그 수식을 연산 그래프로 저장(덧셈·곱셈·삼각함수 등 기본 연산의 트리)"),
    bullet("② 사슬법칙을 그래프 위에서 자동 적용해 ∂f/∂x, ∂g/∂x(야코비안), 필요하면 헤시안까지 정확한 수치를 계산하는 "
           "함수를 자동 생성 — 손으로 미분식을 유도하거나 유한차분으로 근사할 필요가 전혀 없음"),
    bullet("③ 어떤 원소가 항상 0인지(= 본문 6절의 블록-띠 구조)도 그래프 구조에서 자동으로 알아내 sparsity 패턴을 IPOPT에 "
           "미리 알려줌 — IPOPT는 그 패턴에 맞는 희소 선형대수로 매 반복의 뉴턴 스텝을 빠르게 풂"),
    bullet("④ IPOPT를 호출 — CasADi는 IPOPT의 wrapper일 뿐, 내점법 알고리즘 자체는 IPOPT(Wächter & Biegler)가 수행"),
    para("즉 이 조합의 본질은 '똑똑한 solver'가 아니라 **미분을 절대 손으로 쓰지 않고, 정확한 야코비안을 항상 최신 "
         "상태로 자동 공급하는 것**입니다 — 사람이 수식을 바꿔도(예: 마찰 모델 교체) 미분 코드를 다시 쓸 필요가 없다는 "
         "게 실무에서 가장 큰 가치입니다."),
]

cb += [
    h2("7. 한 장 요약"),
    quote("IPOPT는 부등식을 장벽으로 녹여(2절) 등식 제약만 남은 문제의 연속으로 풀고, 종료 시점에서 KKT 4조건(3절)이 "
          "전부 만족됩니다. 그 부산물인 라그랑주 승수는 추상적 숫자가 아니라 '그 제약을 지키는 데 필요한 실제 힘'이고, "
          "우리 문제에서는 동역학 제약의 승수가 곧 GRF입니다(4절) — 수기로 접촉력을 따로 풀 필요가 없는 이유입니다. "
          "CasADi는 이 모든 미분을 자동으로, 정확하게, 희소 구조까지 파악해 공급합니다(6절) — '미분을 손으로 안 쓴다'는 "
          "것이 이 조합의 전부입니다."),
]

print(f"child blocks prepared: {len(cb)}", flush=True)
n_child = append(child, cb)
print(f"APPENDED to CHILD: {n_child} blocks", flush=True)

# ════════════════════════════════════════════════════════════════
# 검증
# ════════════════════════════════════════════════════════════════
for name, pid in [("TARGET(p3)", TARGET), ("child(3-a)", child)]:
    all_blocks = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = requests.get(url, headers=H).json()
        all_blocks += r.get("results", [])
        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")
    print(f"{name}: {len(all_blocks)} total blocks", flush=True)

print("DONE — TARGET https://www.notion.so/" + TARGET.replace("-", ""))
print("DONE — CHILD  https://www.notion.so/" + child.replace("-", ""))
