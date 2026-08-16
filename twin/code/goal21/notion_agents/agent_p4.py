# -*- coding: utf-8 -*-
"""④ 샘플링과 MPPI 페이지 증축 — 5.용어사전 6.MPPI유도 7.하이퍼파라미터 8.실무트릭 9.CMA대조 10.설계시트."""
import requests, time

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
TARGET = "396ab81d2550812fbeabca1717948df1"


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
def code(t): return {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": "plain text"}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def append(page, blocks):
    for i in range(0, len(blocks), 80):
        chunk = blocks[i:i + 80]
        for attempt in range(6):
            r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                               headers={**H, "Content-Type": "application/json"},
                               json={"children": chunk})
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2)) + 1
                print(f"  429 rate-limited, retry {attempt+1} after {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise RuntimeError(r.text[:800])
            break
        else:
            raise RuntimeError("exceeded retry attempts on 429")
        time.sleep(0.6)


blocks = []

# ════════════════ 5. 용어 완전 사전 ════════════════
blocks += [
    h2("5. 용어 완전 사전 — 샘플링·MPC 어휘 총정리"),
    para("앞선 절들(①~④)에서 정의 없이 스치듯 쓴 용어를 한 곳에 모았습니다. rollout부터 CMA의 step-size까지, "
         "이후 6~10절에서 바로 전제하고 쓰는 12개 용어입니다."),
    table([
        ["용어", "정의", "직관 한 줄"],
        ["rollout", "후보 제어열을 시뮬레이터(트윈)에 넣어 끝까지 실행해 궤적과 비용을 얻는 한 번의 시도.", "공을 한 번 굴려 보는 것."],
        ["horizon H", "최적화가 내다보는 미래 스텝(또는 시간)의 길이.", "몇 수 앞까지 볼지."],
        ["receding horizon", "매 스텝마다 H만큼 다시 계획하고 첫 입력만 실행한 뒤 한 칸 밀어 반복하는 원리.", "MPC라는 이름 자체의 정의."],
        ["temperature λ", "MPPI 가중치 exp(−J/λ)의 뾰족함을 정하는 상수.", "소프트맥스의 '온도'와 동일한 역할."],
        ["elite fraction (CEM 상위 비율)", "전체 샘플 중 비용이 낮은 상위 K%만 골라 다음 분포를 갱신하는 데 쓰는 비율.", "반 등수 안에서만 평균 내기."],
        ["importance sampling", "원하는 분포에서 직접 뽑을 수 없을 때, 뽑기 쉬운 분포에서 뽑고 가중치로 보정해 기대값을 맞추는 기법.", "다른 곳에서 뽑고 셈은 맞게 고치기."],
        ["colored noise (시간 상관 노이즈)", "매 스텝 독립인 백색잡음 대신, 이웃 스텝끼리 상관을 준 노이즈.", "액추에이터가 실제로 낼 수 있는 매끄러운 파형에 가까움."],
        ["spline knot", "제어 신호를 몇 개의 매듭점 값으로 표현하고 그 사이를 보간하는 파라미터화 방식.", "스텝 수 대신 노트 수만큼만 최적화."],
        ["anytime 알고리즘", "계산을 중간에 끊어도 그 시점까지 찾은 최선의 답을 즉시 반환할 수 있는 알고리즘.", "지금 멈춰도 답은 준다."],
        ["warm start / shift", "이전 스텝에서 구한 해를 한 칸 밀어 다음 스텝 최적화의 초기값으로 재사용.", "매번 백지에서 풀지 않기."],
        ["공분산 적응 (CMA)", "탐색 분포의 공분산 행렬을 성공한 샘플들의 방향으로 갱신해 파라미터 간 상관을 학습하는 것.", "탐색 모양을 계곡 방향으로 늘리기."],
        ["step-size σ", "탐색 분포 전체의 크기(스칼라 스케일).", "진화 경로 신호로 크게/작게 조절."],
    ]),
    callout("이 12개 용어는 뿔뿔이 흩어져 있지 않습니다 — 아래 다섯 갈래로 6~10절에 그대로 다시 등장합니다.", "🗺️"),
    bullet("① rollout · ② horizon H · ③ receding horizon · ④ temperature λ → 바로 다음 6절 MPPI 유도의 재료"),
    bullet("⑤ elite fraction · ⑥ importance sampling → CEM/MPPI 공통 골격 (6절 ②~③ 계단)"),
    bullet("⑦ colored noise · ⑧ spline knot → 8절 실무 트릭의 처음 두 항목"),
    bullet("⑨ anytime 알고리즘 · ⑩ warm start/shift → 10절 설계 시트의 재계획 구조"),
    bullet("⑪ 공분산 적응(CMA) · ⑫ step-size σ → 9절 CMA-ES 대조의 핵심 축"),
]

# ════════════════ 6. MPPI 유도를 네 계단으로 ════════════════
blocks += [
    h2("6. MPPI 유도를 네 계단으로 — '왜 하필 그 갱신식인가'"),
    para("④ 페이지의 표에 있던 갱신식 u ← u + Σᵢ wᵢ·δᵢ가 어디서 나오는지, 전체 흐름을 먼저 수식 네 줄로 보고 "
         "그다음 한 계단씩 풀어봅니다."),
    code("① q*(U) ∝ p(U)·exp(-J(U)/λ)                              최적 제어분포 (이론상의 목표)\n"
         "② p(U)에서 샘플링                                          실제로 뽑을 수 있는 것 (importance sampling)\n"
         "③ w_i = exp(-(J_i - J_min)/λ) / Σ_j exp(-(J_j - J_min)/λ)   샘플별 가중치 (수치안정화 포함)\n"
         "④ u ← u + Σ_i w_i · δ_i                                   가중 평균으로 제어 갱신"),
    h3("① 최적 제어분포의 형태"),
    para("제어열 U에 대해 '이상적인' 분포 q*(U)가 있다고 하면, 정보이론적 최적 제어 이론은 그 형태를 q*(U) ∝ "
         "p(U)·exp(−J(U)/λ)로 못박습니다. 직관은 단순합니다 — **좋은 궤적일수록(J가 작을수록) 지수적으로 더 자주 "
         "뽑히는 분포**가 이론적으로 최적이라는 것입니다. 이 결과는 자유에너지와 KL 다이버전스의 쌍대성에서 나오며, "
         "MPPI의 '경로적분(path integral)'이라는 이름도 여기서 옵니다 (Williams et al. 2017, ICRA, \"Information "
         "Theoretic MPC for Model-Based Reinforcement Learning\")."),
    h3("② 문제 — q*에서 직접 뽑을 수 없다"),
    para("q*(U)는 '정답이 무엇인지 이미 알아야 뽑을 수 있는' 분포라 직접 샘플링이 불가능합니다. 실제로 우리가 가진 "
         "것은 현재 정책 p(U) — 지금의 제어열 u에 노이즈를 얹은 분포뿐입니다. 그래서 **p에서 뽑고, 뽑힌 각 샘플에 "
         "가중치를 매겨 q*의 기대값을 흉내내는** importance sampling(용어 사전 ⑥번)을 씁니다."),
    h3("③ 가중치 — J_min을 빼는 이유"),
    para("importance sampling을 풀어내면 샘플 i의 가중치는 wᵢ = exp(−(Jᵢ−J_min)/λ) / Σⱼ exp(−(Jⱼ−J_min)/λ)로 "
         "정리됩니다. 분자·분모에 exp(−J_min/λ)가 똑같이 곱해져 약분되므로, 수학적으로는 J_min을 빼든 안 빼든 "
         "결과가 동일합니다. 그럼에도 빼는 이유는 순수한 **수치 안정화 트릭**입니다 — J가 크면 exp(−J/λ)가 언더플로로 "
         "0이 되어버릴 수 있는데, 최솟값을 기준으로 삼으면 지수의 인자가 항상 0 이하로 잡혀 이 문제가 사라집니다."),
    h3("④ 갱신 — 가중 평균으로 노이즈를 몰아준다"),
    para("최종 갱신 u ← u + Σᵢ wᵢ·δᵢ는 '비용이 낮았던 노이즈 방향으로, 가중 평균만큼 이동'한다는 뜻입니다. "
         "의사코드로 풀면 다음 여덟 줄입니다."),
    code("δ_1..δ_N ~ N(0, Σ)              # 노이즈 샘플 (colored noise 권장, 8절 참고)\n"
         "U_i = U + δ_i                   # 후보 제어열\n"
         "J_i = rollout_cost(U_i)         # 트윈에 굴려 비용 계산 (rollout)\n"
         "w_i = exp(-(J_i - min(J)) / λ)  # 지수 가중치 (J_min 차감으로 안정화)\n"
         "w_i /= sum(w_i)                 # 정규화\n"
         "U = U + Σ_i w_i * δ_i           # 가중 평균으로 갱신\n"
         "U = shift(U)                    # 한 스텝 밀어 재사용 (warm start)\n"
         "return U[0]                     # 첫 입력만 실행 (receding horizon)"),
    bullet("마지막 두 줄(shift, 첫 입력만 반환)이 바로 용어 사전의 receding horizon·warm start 정의 그 자체입니다 — "
           "이 여덟 줄 전체가 매 제어 스텝마다 반복됩니다."),
    callout("λ 직관 — **λ는 소프트맥스의 온도**입니다. λ가 작으면 exp(−(Jᵢ−J_min)/λ)의 차이가 극단적으로 벌어져 "
            "사실상 최고 샘플 하나만 반영됩니다(그리디, 결과 분산이 큼). λ가 크면 모든 샘플의 가중치가 비슷해져 "
            "그냥 평균을 내는 것과 같아집니다(둔감). 실전에서는 그 사이 어딘가 — 비용 분포의 퍼짐 정도를 보고 "
            "조절합니다.", "🌡️"),
    quote("6절 요약 | MPPI 갱신식은 '이상적 분포 q* → 못 뽑으니 importance sampling → 수치안정화한 가중치 → "
          "가중 평균'이라는 네 계단의 최종 산물이다. 신비로운 공식이 아니라 자유에너지 쌍대성의 직접적인 귀결이다."),
]

# ════════════════ 7. 하이퍼파라미터가 하는 일 ════════════════
blocks += [
    h2("7. 하이퍼파라미터가 하는 일 — 감으로 정하지 않기 위한 표"),
    para("MPPI/CEM 계열에서 실제로 만지는 손잡이는 몇 개 안 됩니다. 각각을 키우고 줄일 때 무슨 일이 일어나는지, "
         "그리고 어디서부터 시작할지의 '감각'을 정리합니다 — 아래 시작값은 경험 법칙이지 정답이 아니며, 문제마다 "
         "다시 튜닝해야 합니다."),
    table([
        ["파라미터", "키우면", "줄이면", "시작값 감각"],
        ["λ (temperature)", "가중치가 평탄해져 많은 샘플을 고르게 반영 — 둔감·보수적, 분산은 작지만 최적에서 멀어질 수 있음",
         "가중치가 뾰족해져 최고 샘플 위주로 반영 — 그리디, 수렴은 빠르나 분산·잡음이 큼", "비용의 표준편차의 약 0.5배"],
        ["노이즈 σ", "탐색 폭이 넓어져 다른 구조의 해도 발견 가능 — 대신 rollout 상당수가 낭비됨",
         "국소적으로만 다듬음 — 수렴은 빠르나 초기값 근방의 local optimum에 갇히기 쉬움", "액추에이터 범위의 5~20%"],
        ["샘플 수 N", "가중 평균의 분산이 줄고 해 품질이 좋아짐 — 계산 비용은 거의 선형으로 증가",
         "계산은 빠르지만 가중 평균이 잡음에 취약해짐", "64~1024"],
        ["horizon H", "먼 미래(착지 자세 등)까지 비용에 반영 — 대신 카오스·계산량이 커짐",
         "근시안적이지만 안정적이고 빠름", "과제 전체 시간의 1~2배"],
        ["knot 수", "표현력이 늘어 더 복잡한 τ 파형 가능 — 탐색 차원도 함께 늘어 어려워짐",
         "저차원이라 탐색이 쉽고 파형이 매끄러움 — 대신 표현력 부족 위험", "10절 설계 시트 기준 관절당 10개 안팎"],
        ["smoothing 벌점", "τ가 매끄러워져 채터링이 줄어듦 — 급격한 반응이 필요한 순간엔 억제될 위험",
         "자유도가 커져 급격한 대응 가능 — 대신 지글거림(chattering) 위험", "다른 비용 항 대비 작게 시작, 지글거리면 키움"],
    ]),
    para("이 표의 부작용 — rollout 낭비, 지글거림, local optimum 갇힘 — 을 실제로 어떻게 막는지가 다음 8절의 "
         "실무 트릭 7개입니다."),
    quote("7절 요약 | 손잡이는 여섯 개뿐이지만 서로 트레이드오프로 얽혀 있다. 시작값은 '감각'이며, 실제 튜닝은 "
          "비용 분포와 rollout 예산을 보며 반복적으로 조정해야 한다."),
]

# ════════════════ 8. 실무 트릭 7개 ════════════════
blocks += [
    h2("8. 실무 트릭 7개 — 표에서 안 보이는 것들"),
    para("하이퍼파라미터를 잘 잡아도 구현 디테일에서 성패가 갈립니다. MPPI/샘플링 구현에서 반복적으로 등장하는 "
         "일곱 가지 트릭입니다."),
    bullet("**colored noise (시간 상관 노이즈)** — 백색잡음을 그대로 τ에 얹으면 매 스텝이 독립이라 제어가 지글지글 "
           "떨립니다."),
    para("시간 상관을 준(또는 아예 스플라인 노트에만 노이즈를 주는) colored noise를 쓰면, 액추에이터가 실제로 "
         "따라갈 수 있는 매끄러운 후보 궤적이 나옵니다 — 7절의 smoothing 벌점과 목적이 같은, 샘플링 단계의 사전 예방."),
    bullet("**knot 파라미터화** — 스텝마다 독립 변수를 두는 대신 몇 개의 매듭점(knot)으로 제어를 표현합니다."),
    para("탐색 차원이 스텝 수에서 노트 수로 줄고, 보간이 매끄러움을 자동으로 보장합니다. 7절의 knot 수 트레이드오프가 "
         "바로 이 파라미터화의 대가입니다."),
    bullet("**이전 해 shift 재사용 (warm start)** — 매 재계획을 백지에서 시작하지 않고, 직전 스텝의 해를 한 칸 "
           "밀어 초기값으로 씁니다."),
    para("워밍업 없이 바로 좋은 후보 주변을 탐색할 수 있어, 매 스텝 새로 탐색해야 하는 비용을 사실상 없앱니다 "
         "(용어 사전 ⑨~⑩번, 6절 의사코드의 마지막 두 줄)."),
    bullet("**elite만 평균 (CEM 혼합)** — MPPI의 소프트맥스 가중 대신, 상위 K%(엘리트)만 골라 평균 내는 CEM 방식을 "
           "섞기도 합니다."),
    para("나쁜 샘플의 영향을 원천 차단해 더 결단력 있는 갱신이 되며, MPPI가 λ 튜닝에 민감할 때 흔히 쓰는 보완책입니다."),
    bullet("**제약은 큰 벌점 + 사후 클리핑** — 샘플링 계열은 등식/부등식 제약을 정확히 지킬 방법이 없습니다."),
    para("위반 시 큰 비용을 매겨 가중치를 사실상 0으로 만들고, 그래도 남는 위반은 최종적으로 한계값에서 잘라내는 "
         "(clip) 이중 안전장치를 씁니다 — ④ 페이지 '정직한 손익계산서'의 '제약 처리 △' 항목이 실무에서 이렇게 "
         "메워집니다."),
    bullet("**GPU/멀티코어 병렬이 사실상 전제** — 수백~수천 개의 독립 rollout을 동시에 굴려야 합니다."),
    para("병렬화 없이는 실용적인 재계획 주기가 나오지 않습니다 — MPPI/샘플링 계열이 GPU 시대에 다시 주목받는 "
         "이유이기도 합니다."),
    bullet("**비용 정규화** — 비용 J의 스케일이 태스크마다 들쭉날쭉하면 λ도 매번 다시 잡아야 합니다."),
    para("비용을 정규화해두면 λ 하나로 여러 상황에 더 잘 견뎌, 튜닝 자체가 안정됩니다."),
    quote("8절 요약 | 일곱 트릭은 결국 세 갈래다 — 매끄러움을 미리 넣기(colored noise·knot), 반복을 재사용하기"
          "(warm start·elite), 그리고 정확성을 사후에 보정하기(클리핑·정규화). 이론식 하나만으로는 실전이 안 돌아간다."),
]

# ════════════════ 9. CMA-ES는 왜 다른가 ════════════════
blocks += [
    h2("9. CMA-ES는 왜 다른가 — '한 벡터 문제' vs '한 궤적 문제'"),
    para("MPPI는 매 제어 스텝마다 '이번 한 궤적을 어떻게 이을까'라는 문제를 온라인으로 반복해서 풉니다 — 문제 "
         "자체가 매 순간 조금씩 바뀌고, 앤타임으로 언제든 끊어 답을 씁니다. CMA-ES는 반대로 '이 26개 파라미터 "
         "벡터 하나'를 오프라인으로, 수렴할 때까지 붙잡고 있는 문제입니다 — 문제가 고정되어 있고, 세대를 반복해 "
         "하나의 최종 답에 도달하는 것이 목적입니다."),
    para("CMA의 갱신은 세 요소로 이루어집니다."),
    bullet("**평균 이동** — 성적이 좋은 상위 샘플들의 가중 평균으로 탐색 중심을 옮깁니다."),
    bullet("**공분산 적응** — 성공한 방향으로 분포의 공분산 행렬을 갱신해 파라미터끼리의 상관을 학습하고, "
           "탐색 분포의 모양을 계곡의 방향으로 길쭉하게 늘립니다."),
    bullet("**step-size 조절** — 진화 경로(최근 이동들이 얼마나 한 방향으로 정렬돼 있는지)를 신호로 삼아, "
           "잘 나아가고 있으면 σ를 키우고 갈팡질팡하면 줄입니다."),
    table([
        ["요소", "무엇을 학습하나", "MPPI에서의 대응"],
        ["평균 이동", "상위 샘플의 가중 평균으로 탐색 중심 이동", "동일 — u ← u + Σwᵢδᵢ 자체가 평균 이동"],
        ["공분산 적응", "성공 방향들의 상관관계 → 탐색 분포를 계곡 모양으로 길쭉하게", "보통 없음 — 노이즈 공분산 Σ는 대개 고정(대각)"],
        ["step-size σ", "진화 경로(최근 이동의 정렬도)로 수렴 속도 가감", "λ가 유사한 역할을 하지만 분포 크기가 아니라 가중치 뾰족함을 조절"],
    ]),
    para("공분산 적응의 유무가 두 방법의 실질적인 차이입니다 — MPPI는 매 스텝 빠르게 도는 대신 분포 모양을 "
         "고정해두고, CMA는 느리게 여러 세대를 도는 대신 분포 모양 자체를 문제에 맞춰 학습합니다."),
    callout("우리 사례 연결 — 26-파라미터 식별에서 이 공분산 적응이 실제로 작동한 흔적이 있습니다. 질량을 올리면서 "
            "관성을 낮추는 식으로 서로 보상하는 방향이 존재하는데, 등고선이 이렇게 기울어진 '계곡'에서는 파라미터 "
            "축에 나란히만 탐색하는 방법보다, 공분산이 계곡 방향으로 늘어난 CMA의 탐색이 훨씬 빠르게 바닥에 "
            "도달합니다.", "🔍"),
    quote("9절 요약 | MPPI와 CMA는 같은 '0차 샘플링' 가문이지만 푸는 문제의 시간 구조가 다르다 — 온라인 반복 vs "
          "오프라인 수렴. 그 차이가 공분산 적응의 유무로 구현에 그대로 드러난다."),
]

# ════════════════ 10. 설계 시트 ════════════════
blocks += [
    h2("10. '우리 트윈 위 MPPI/CMA 폴리시' 설계 시트"),
    para("④·⑧ 페이지에서 언급한 하이브리드 카드(NLP 해 → 트윈 위 직접 폴리시)를 실제로 설계한다면 이렇게 잡습니다."),
    table([
        ["항목", "내용"],
        ["변수", "무릎·엉덩이 τ 스플라인 노트 각 10개(총 20개), 초기값 = NLP 해"],
        ["비용", "−h_apex(정점 높이) + 토크 한계 벌점 + 착지 자세 벌점 (ILC와 연결 가능)"],
        ["rollout", "트윈 스탠스+비행 구간 약 0.6초, 1회 rollout ≈ 0.05~0.1초"],
        ["세대당 예산", "N=512 샘플/세대, 10코어 병렬 → 세대당 약 5초"],
        ["총 예산", "50세대 ≈ 5~15분"],
    ]),
    bullet("**장점** — NLP와 트윈 사이의 번역 갭(접촉 모델링 차이 등)이 원천적으로 사라집니다. 트윈 자체가 곧 "
           "평가 함수이기 때문입니다."),
    bullet("**한계** — 샘플링 계열이라 제약을 정확히 보장하지 않습니다(9절의 '정직한 손익계산서', 8절 트릭 5번의 "
           "벌점+클리핑으로만 방어). 따라서 이 폴리시는 NLP 해에서 크게 벗어나지 않는 근방을 다듬는 용도로 "
           "한정합니다."),
    bullet("변수 20개(노트 10+10)는 7절의 knot 수 트레이드오프, 비용의 토크·자세 벌점은 8절 '제약은 큰 벌점+"
           "클리핑' 트릭, rollout 예산 산정은 6절 갱신식의 반복 구조를 그대로 따릅니다 — 이 시트는 5~9절의 "
           "개념을 우리 문제에 대입한 결과일 뿐, 새로운 방법이 아닙니다."),
    callout("MJPC의 교훈 — 가장 단순한 샘플링(Predictive Sampling)이 정교한 iLQG와 여러 태스크에서 필적했다는 "
            "사실(Howell et al. 2022, arXiv:2212.00541)이 이 카드의 실질적 근거입니다. 우리 트윈이 충분히 빠르면"
            "(rollout 0.05~0.1초), '똑똑하게 미분'하기보다 '단순하게 많이 굴려보기'가 실제로 통할 가능성이 높습니다.",
            "🎯"),
    quote("10절 요약 — 5~9절을 한 장에 | 용어(5) → 유도(6) → 손잡이(7) → 트릭(8) → CMA 대조(9)를 모두 거쳐 "
          "나온 결론은 하나다: 우리 트윈이 곧 평가 함수가 되는 순간, NLP와 샘플링 폴리시 사이의 번역 갭은 사라진다. "
          "남는 것은 '얼마나 빨리, 얼마나 많이 굴릴 수 있는가'뿐이고, 그 답이 바로 이 설계 시트다."),
]

print(f"total blocks to append: {len(blocks)}", flush=True)
append(TARGET, blocks)

# 검증
r = requests.get(f"https://api.notion.com/v1/blocks/{TARGET}/children?page_size=100", headers=H).json()
all_blocks = r.get("results", [])
while r.get("has_more"):
    r = requests.get(f"https://api.notion.com/v1/blocks/{TARGET}/children?page_size=100&start_cursor={r['next_cursor']}",
                     headers=H).json()
    all_blocks += r.get("results", [])
print(f"page total blocks now: {len(all_blocks)}", flush=True)
print(f"appended this run: {len(blocks)}", flush=True)
print("DONE — https://www.notion.so/" + TARGET.replace("-", ""))
