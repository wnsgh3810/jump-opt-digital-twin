# -*- coding: utf-8 -*-
"""Agent P8 — ⑧ 우리 연구 처방전 본문 증축(5~7절) + child ⑧-a 용어 총사전 생성."""
import sys, requests, time, json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
MASTER_PARENT = "396ab81d2550814995dfc2e3a712ee01"


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
def todo(t): return {"object": "block", "type": "to_do", "to_do": {"rich_text": rt(t), "checked": False}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def _request(method, url, **kwargs):
    for attempt in range(8):
        r = requests.request(method, url, headers={**H, "Content-Type": "application/json"}, **kwargs)
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", 2 * (attempt + 1)))
            print(f"429 rate limited — sleeping {wait}s (attempt {attempt + 1})", flush=True)
            time.sleep(wait)
            continue
        return r
    raise RuntimeError("exhausted retries on repeated 429")


def new_page(parent, title):
    r = _request("POST", "https://api.notion.com/v1/pages",
                 json={"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status(); time.sleep(0.6)
    return r.json()["id"]


def append(page, blocks):
    total = 0
    for i in range(0, len(blocks), 80):
        chunk = blocks[i:i + 80]
        r = _request("PATCH", f"https://api.notion.com/v1/blocks/{page}/children",
                     json={"children": chunk})
        if r.status_code != 200:
            raise RuntimeError(r.text[:800])
        total += len(chunk)
        time.sleep(0.6)
    return total


def find_child_by_prefix(parent, prefix):
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{parent}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = _request("GET", url)
        r.raise_for_status()
        data = r.json()
        for b in data.get("results", []):
            if b.get("type") == "child_page":
                title = b["child_page"].get("title", "")
                if title.startswith(prefix):
                    return b["id"], title
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return None, None


p8_id, p8_title = find_child_by_prefix(MASTER_PARENT, "⑧ 우리 연구 처방전")
if p8_id is None:
    raise RuntimeError("parent 아래에서 '⑧ 우리 연구 처방전' child_page를 찾지 못했습니다")
print("FOUND p8:", p8_id, "|", p8_title, flush=True)

# ════════════════════════════════════════════════════════════
# 브리프 A — 본문 증축 (5. 실행 카드 절차 / 6. 독서목록 해설 / 7. 로드맵 체크리스트)
# ════════════════════════════════════════════════════════════
part_A = [
    h2("5. 실행 카드별 구체 절차"),
    para("카드 1의 개요(⑧-3)에서 한 걸음 더 들어가, 실제로 손을 움직일 때의 절차를 다섯 카드 각각에 대해 구체화합니다."),

    h3("카드1 — NLP 파라미터 이식: 트윈 fitted 값 → 해석식 계수"),
    bullet("① 트윈에서 fitting된 값(질량 스케일·CoM·m_foot)을 사용자가 유도한 해석식 기호 체계로 환산합니다."),
    code("m_t=0.913·M_thigh, r_t=0.0565+com_dz_th, m_c=0.656·M_c, r_c=0.0207, m_p=0.137·M_p, "
         "r_p=0.1326, m_s=0.237·M_calf(+m_foot 처리), r_s=0.0588+com_dz_ca"),
    bullet("② 환산된 값으로 조합 계수를 재계산합니다 — A=m_t·r_t+m_p·r_p+m_s·l_t, "
           "B=m_s·r_s−m_c·r_c−m_p·l_c, K=m_s·l_t·r_s−m_p·l_c·r_p이며, 관성합 IΣ1·IΣ2도 같은 값들로 함께 갱신합니다."),
    bullet("③ 재계산된 A, B, K, IΣ1, IΣ2를 NLP 코드의 상수로 교체하고 task를 재실행한 뒤, 트윈 리허설 갭을 다시 측정하여 "
           "기존 −4.4%(G20) 대비 개선되었는지를 확인합니다."),
    bullet("주의 — m_foot 처리 규칙: 발은 독립된 강체가 아니라 calf(하퇴) 질량·CoM·관성에 합산(lumping)되는 대상입니다. "
           "r_s(=calf 복합 CoM 거리)를 계산할 때 발 질량이 포함된 복합 CoM 위치를 반드시 사용해야 하며, 발을 별도 링크로 "
           "취급하면 IΣ2가 과소평가되어 무릎 쪽 관성이 실제보다 가볍게 잡힙니다."),

    h3("카드2 — 트윈 직접 폴리시: NLP 해를 트윈 위에서 다듬기"),
    bullet("① 페이지 ④ 샘플링과 MPPI의 설계 시트를 그대로 사용합니다 — τ 스플라인 노트 약 20개, CMA/MPPI 갱신, "
           "스탠스 rollout ~0.05s × 샘플 1만 개 ÷ 10코어 규모."),
    bullet("② 선(先)조건은 'NLP warm start'입니다: CMA/MPPI 탐색분포의 초기 평균을 카드1에서 얻은 NLP 해의 τ(t)로 "
           "설정해, 트윈 위 탐색이 이미 물리적으로 그럴듯한 궤적 근방에서 시작하도록 합니다."),
    bullet("③ 제약 처리 원칙: 토크 한계·마찰원뿔 같은 제약은 NLP처럼 하드 등식/부등식으로 걸지 않고 비용함수에 "
           "벌점(penalty)으로 반영하며, rollout이 끝난 뒤 실제 위반량을 사후검증으로 별도 로깅합니다."),
    bullet("④ 트윈이 곧 평가 함수이므로, NLP와 트윈 사이의 번역 갭(접촉 처리 차이 등)이 이 단계에서 원천적으로 소멸함을 "
           "확인하는 것이 이 카드의 목적입니다."),

    h3("카드3 — 폐루프 지표 구축: 배포 시나리오와 동형인 심판"),
    bullet("정의:"),
    code("sim에 동일 kp,kd(폴더명 게인)로 q_des(t) 추종시켜 τ_sim(t)와 실측 τ 비교 "
         "(fit 사용 금지, 심판 전용 — 사용자 원칙)"),
    bullet("이 지표는 페이지 ⑤ Gradient의 물리학의 카오스 회피 논리를 그대로 따릅니다 — 짧은 창(예: 0.1~0.2s)에서 "
           "측정된 상태로 리셋하는 multiple shooting 형태로 평가하여, 긴 rollout의 발산 오염을 차단합니다."),
    bullet("사용자 원칙 재확인: 이 폐루프 지표는 파라미터를 조정(fit)하는 용도가 아니라, 트윈과 실물의 일치도를 "
           "판정하는 심판(judge) 전용입니다 — kp, kd는 폴더명이 지정하는 실측 게인 그대로 고정합니다."),
    bullet("첫 적용 대상: 0421/0422 게인 데이터셋을 이 지표로 재부활시켜 재평가하는 것으로 시작합니다."),

    h3("카드4 — 실기 체크리스트 실행"),
    bullet("전체 절차(세션 보정 → 70/85/100% 단계적 투입 → ILC)는 해설 문서 ⑪ 실 로봇 배포 체크리스트를 그대로 따릅니다."),
    bullet("최우선 항목: t_ff(피드포워드 토크) 전송이 실제로 모터에 도달하는지를 검증하는 단계를 가장 먼저 수행합니다 — "
           "이 검증이 누락되면 이후 모든 sim-실물 비교가 무의미해집니다."),
    bullet("검증 순서: t_ff 전송 확인 → 세션별 게인/오프셋 보정 → 배포 강도 70%→85%→100% 단계적 증가 → "
           "ILC(반복학습제어)로 잔차 축소."),

    h3("카드5 — 벤치 실험: knee a_hat 마찰항 재교정"),
    bullet("목표: knee 관절 a_hat의 마찰항 계수 a3(쿨롱)·a4(고속/점성)를 저속 구간부터 whip(고속 채찍질) 영역까지 "
           "새로 교정합니다."),
    bullet("절차: 벤치에서 knee를 저속~whip 속도 범위 전체로 구동하며 τ 실측치를 수집하고, 이 데이터로 a3·a4를 재fit합니다."),
    bullet("근거: 오차 지도(⑨)에서 knee whip 구간이 아직 미교정 축으로 남아 있어, 이 벤치 데이터가 확보되어야 다음 "
           "라운드 트윈의 정밀도가 개선됩니다."),

    h2("6. 독서목록 해설판 — 각 문헌을 왜, 무엇을 위해 읽는가"),
    para("⑧-4의 목록을 다시 훑되, 이번에는 '왜 읽는지'와 '읽으며 스스로 답해볼 질문'을 하나씩 붙입니다."),

    h3("교과서/강의 — 왜 읽는가"),
    bullet("**Tedrake, \"Underactuated Robotics\"** — MIT의 무료 온라인 교재로, 언더액추에이팅·궤적최적화·안정성·접촉을 "
           "하나의 일관된 표기로 관통합니다. 이 문서 ①~⑧에서 다룬 개념 대부분이 이 책의 한 장씩에 대응하므로, 우리 "
           "파이프라인을 학계 표준 언어로 재서술하는 데 가장 유용합니다. 읽으며 답할 질문: 우리 점프 NLP는 이 책 어느 "
           "장의 어떤 transcription인가?"),
    bullet("**Featherstone, \"Rigid Body Dynamics Algorithms\"** — ABA(articulated body algorithm)·RNEA 등 로봇 "
           "동역학 알고리즘의 원전으로, MuJoCo·Pinocchio 내부에서 실제로 도는 계산이 여기서 유도됩니다. 우리 4-bar "
           "축소좌표 유도가 왜 그렇게 소거되는지를 트리 알고리즘 관점에서 재확인할 때 참조합니다. 읽으며 답할 질문: "
           "우리 coupler 소거는 ABA/RNEA의 어떤 단계에 대응하는가?"),
    bullet("**Lynch & Park, \"Modern Robotics\"** — 트위스트·스크류·좌표계 표기를 통일하는 표준 교재로, 다른 문헌을 "
           "읽을 때 표기 차이로 헤매지 않게 해주는 사전 역할을 합니다. 읽으며 답할 질문: 우리가 쓰는 관절각 부호규약은 "
           "이 책의 표준과 어디서 일치하고 어디서 다른가?"),
    bullet("**MuJoCo 공식 문서 'Computation' 장** — MuJoCo의 solver·접촉·구속이 실제로 어떤 수식으로 도는지 설명하는 "
           "1차 출처이며, solref/solimp·볼록 완화의 정의가 여기 있습니다. 페이지 ①②의 근거 문헌이기도 합니다. "
           "읽으며 답할 질문: solref 음수 표기는 언제 쓰나?"),

    h3("논문 12편 — 왜 읽는가"),
    bullet("**Todorov, Erez, Tassa 2012 (IROS)** — MuJoCo가 애초에 '모델 기반 제어를 위한' 물리엔진으로 설계된 이유와 "
           "목표를 제시한 원전입니다. 왜 접촉이 가역적이어야 하는지, 왜 속도가 정밀도보다 우선인 설계인지가 여기서 "
           "나옵니다. 읽으며 답할 질문: MuJoCo가 RL 시대 이전에 어떤 문제를 겨냥해 설계되었는가?"),
    bullet("**Todorov 2014 (ICRA)** — MuJoCo 접촉·구속의 수학적 핵심(볼록 완화, 가역성)을 정식화한 논문으로, "
           "페이지 ①의 '암시적 구속'과 페이지 ②의 '볼록 완화 vs LCP' 논의가 이 논문에 뿌리를 둡니다. 읽으며 답할 "
           "질문: '가역'이 모델 기반 제어에 왜 결정적인가?"),
    bullet("**Stewart & Trinkle 1996 / Anitescu & Potra 1997** — hard 접촉(LCP) 학파의 고전으로, 상보성 조건을 "
           "그대로 선형 상보성 문제로 정식화하는 표준 절차를 제시합니다. MuJoCo의 볼록 완화가 '무엇을 완화했는가'를 "
           "이해하려면 원래의 hard 정식화를 먼저 알아야 합니다. 읽으며 답할 질문: LCP 해가 비유일해지는 구체적 기하 "
           "조건은 무엇인가?"),
    bullet("**Posa, Cantu, Tedrake 2014 (IJRR)** — 상보성 제약을 NLP 안에 직접 넣어 접촉 스케줄까지 최적화가 스스로 "
           "찾아내게 만든 방법으로, 페이지 ③의 접촉 처리 B형입니다. 우리의 phase 고정 방식이 포기한 자유도(스케줄 "
           "탐색)를 정면으로 다룹니다. 읽으며 답할 질문: 상보성 완화 ε는 왜 필요한가?"),
    bullet("**Di Carlo et al. 2018 (IROS)** — MIT Cheetah 3의 SRB 축소모델 + convex QP MPC를 정식화한 논문으로, "
           "페이지 ⑥ 전체의 근거입니다. 우리의 '축소좌표+phase 고정'과 구조적으로 동형인 4족 버전입니다. 읽으며 답할 "
           "질문: 왜 QP가 볼록인가 — 발 위치가 상수라서?"),
    bullet("**Kim et al. 2019** — convex MPC가 준 반력 명령을 전신 토크로 변환하는 WBIC 계층의 구체적 구현입니다. "
           "단일 다리인 우리에게는 불필요한 계층이지만, '왜 불필요한가'를 이해하려면 이 계층이 무엇을 하는지부터 "
           "알아야 합니다. 읽으며 답할 질문: 단일 다리·직접 토크 최적화 구조에서는 이 계층의 어떤 기능이 소멸하는가?"),
    bullet("**Williams et al. 2017 (ICRA)** — 경로적분 제어/자유에너지 쌍대성에서 소프트맥스 가중 갱신식을 유도한 "
           "MPPI 원전으로, 페이지 ④의 MPPI 표가 이 논문에 뿌리를 둡니다. 읽으며 답할 질문: λ→0과 λ→∞ 극한의 갱신은 "
           "각각 무엇이 되는가?"),
    bullet("**Howell et al. 2022, arXiv:2212.00541** — DeepMind의 실시간 MPC 플랫폼 MJPC 논문으로, 단순한 "
           "Predictive Sampling이 정교한 iLQG와 대등했다는 실증이 핵심입니다. 페이지 ④⑥ 모두의 근거이며 '단순함이 "
           "이긴다'는 이 문서 전체의 반복 모티프 출처입니다. 읽으며 답할 질문: Predictive Sampling이 iLQG를 이기는 "
           "태스크와 지는 태스크를 가르는 조건은 무엇인가?"),
    bullet("**Suh et al. 2022 (ICML), arXiv:2202.00817** — 미분가능 시뮬레이터의 gradient가 항상 유리하지는 않다는 "
           "실험적·이론적 반증이며, α-order 혼합 추정기를 제안합니다. 페이지 ⑤의 '괴물 1(접촉 kink)' 절 전체의 "
           "근거입니다. 읽으며 답할 질문: α-order에서 α를 정하는 기준은 무엇인가?"),
    bullet("**Metz et al. 2021** — 카오스 시스템에서 BPTT gradient의 분산이 폭발해 방향이 사실상 난수가 되는 현상을 "
           "실증한 \"Gradients are not all you need\"입니다. 페이지 ⑤ '괴물 2(카오스)' 절의 근거이자, 우리 "
           "multiple-shooting(창 평가) 선택을 정당화하는 문헌이기도 합니다. 읽으며 답할 질문: 이 논문이 함축하는 "
           "대안(짧은 horizon/0차로 전환)은 우리의 어떤 선택과 같은 논리인가?"),
    bullet("**Hwangbo et al. 2019 / Lee et al. 2020 / Miki et al. 2022 (Science Robotics 3부작)** — 각각 액추에이터 "
           "넷, teacher-student 증류, 지형 인지형 보행을 다루며 sim-to-real RL 파이프라인의 표준 부품 세 가지를 "
           "완성합니다. 페이지 ⑦의 근거 문헌입니다. 읽으며 답할 질문: 우리 트윈의 a_hat 모델은 이들의 '액추에이터 "
           "넷'과 무엇이 같고 무엇이 다른가?"),
    bullet("**Kumar et al. 2021 (RSS) — RMA** — 배포 중 온라인으로 환경/자기 파라미터를 잠재벡터로 추정해 적응하는 "
           "방법으로, teacher-student 계열의 확장판입니다. 언젠가 온라인 재계획을 붙일 때 참고할 적응 메커니즘입니다. "
           "읽으며 답할 질문: RMA의 온라인 적응은 우리 ILC(반복학습제어)와 원리적으로 어떻게 다른가?"),

    h2("7. 4주 학습 로드맵 — 체크리스트"),
    para("⑧-4 로드맵 문장을 실행 가능한 체크박스로 바꿉니다. 매 주말 완료 여부를 직접 표시하며 진행합니다."),

    h3("1주차 — 기초 재정렬"),
    todo("Underactuated Robotics의 궤적최적화 장을 정독한다"),
    todo("MuJoCo 공식 문서 'Computation' 장을 정독한다"),
    todo("이 문서 ①②③을 재독한다"),
    todo("우리 NLP 코드에서 결함(defect) 제약이 어디에 걸려 있는지 찾아본다"),

    h3("2주차 — Gradient 실습"),
    todo("Suh et al. 2022 (arXiv:2202.00817)을 정독한다"),
    todo("Metz et al. 2021을 정독한다"),
    todo("페이지 ⑤의 m4(kink)·m5(카오스) 그림을 직접 재현해본다"),
    todo("FD vs 0차 gradient를 간단한 토이 문제로 직접 비교 실험한다"),
    todo("⑤-a 실험(카드 근거)을 수행한다"),

    h3("3주차 — 4족 MPC 계보"),
    todo("Di Carlo et al. 2018을 정독한다"),
    todo("mit-biomimetics/Cheetah-Software의 MPC 코드를 리딩한다"),
    todo("MJPC 데모를 직접 실행해본다"),
    todo("⑥-a QP 손 유도를 따라가 본다"),

    h3("4주차 — 통합 구현"),
    todo("트윈 위에서 MPPI를 실제로 구현한다 (카드2)"),
    todo("NLP 파라미터 이식 카드1을 실행한다"),
    todo("이번 4주의 결과를 이 문서에 추가한다"),

    quote("증축 요약 | 5절은 처방전의 다섯 카드를 '무엇을 어떤 순서로' 수준까지 구체화했고, 6절은 독서목록에 "
          "'왜 읽는가'와 자가진단 질문을 붙였으며, 7절은 4주 로드맵을 실행 가능한 체크리스트로 바꾸었다 — "
          "이 페이지는 이제 읽는 문서에서 실행하는 문서로 넘어간다."),
]

n1 = append(p8_id, part_A)
print(f"appended to p8 ({p8_id}): {n1} blocks", flush=True)

# ════════════════════════════════════════════════════════════
# 브리프 C — child 페이지 "⑧-a 용어 총사전"
# ════════════════════════════════════════════════════════════
p8a = new_page(p8_id, "⑧-a 용어 총사전 — 이 문서 전체의 40개 용어 한 곳에")
print("created p8a:", p8a, flush=True)

# (용어, 한 줄 정의, 출처 페이지) — ①~⑦ 페이지에 등장하거나 그 페이지 주제와 직접 연결되는 용어
terms = [
    ("DOF", "시스템의 독립적인 운동 자유도 개수 — 트리 구조에서는 관절 수와 같지만, 폐루프는 구속식 개수만큼 자유도를 깎는다.", "①"),
    ("일반화좌표", "구속을 만족하는 최소 개수의 독립 변수로 시스템 자세를 표현한 좌표 — 우리 4-bar 축소좌표가 그 예.", "①③"),
    ("구속 야코비안", "구속식 g(q)=0을 일반화좌표로 미분한 행렬 ∂g/∂q — 구속력의 작용방향과 라그랑주 승수의 계수를 정한다.", "①"),
    ("라그랑주 승수", "구속을 정확히 만족시키기 위해 도입하는 미지의 구속력 크기 — hard 방식(LCP)이 직접 풀어내는 대상.", "①"),
    ("Baumgarte", "구속 위반량 r을 그대로 두지 않고 매 스텝 지수적으로 줄여가도록 보정항을 넣는 안정화 기법 — ODE/Bullet의 ERP가 이 계수다.", "①"),
    ("ERP/CFM", "ODE/Bullet 계열 엔진의 구속 튜닝 계수 — ERP(오차수정비율)는 Baumgarte 계수, CFM(구속력혼합)은 구속을 살짝 물렁하게 만드는 정규화항.", "①"),
    ("solref", "MuJoCo 구속/접촉의 참조 감쇠 거동을 정하는 (시정수 tc, 감쇠비 ζ) 두 값 — 가상 스프링-댐퍼의 강성·감쇠를 결정한다.", "①②"),
    ("solimp", "MuJoCo 구속/접촉의 임피던스 곡선 (d0, dmax, width, mid, power) — 위반량이 깊어질수록 구속이 얼마나 단단해지는지를 정한다.", "①②"),
    ("정규화 R", "hard 상보성 조건을 살짝 물렁하게 만들어 해가 항상 존재·유일하도록 하는 항 — MuJoCo 볼록 완화의 핵심 장치.", "①②"),
    ("drift", "적분 오차로 구속 위반량 r이 시간이 갈수록 서서히 커지는 현상 — Baumgarte/암시적 구속의 보정 대상.", "①"),
    ("Signorini", "'침투 없음(r≥0)'과 '접촉력 없음(F≥0)' 중 적어도 하나는 반드시 0이어야 한다는 접촉의 either-or 조건.", "②"),
    ("상보성", "Signorini 조건을 수학적으로 표현한 either-or 논리 0≤r⊥F≥0 — 접촉을 매끄럽지 않게 만드는 근본 원인.", "②"),
    ("KKT", "부등식 제약이 있는 최적화 문제의 국소 최적해가 만족해야 하는 1차 필요조건 — NLP 해의 최적성을 보증하는 근거.", "④"),
    ("LCP", "상보성 조건을 선형 형태로 그대로 정식화한 문제(linear complementarity problem) — hard 접촉 학파가 직접 푸는 대상.", "②"),
    ("볼록 완화", "상보성의 either-or 논리를 부드러운 볼록 최적화로 근사해 해가 항상 존재·유일하도록 만드는 것 — MuJoCo의 접근.", "②"),
    ("마찰원뿔", "접촉력이 마찰계수 안에서 미끄러지지 않으려면 놓여야 하는 원뿔 영역 — pyramidal(각뿔 근사)과 elliptic(정확한 원) 두 표현이 있다.", "②"),
    ("condim", "접촉력이 갖는 성분 수 — 1(수직만)/3(+미끄럼)/4(+비틀림)/6(+구름)까지 MuJoCo가 선택 가능.", "②"),
    ("impratio", "접촉의 수직 방향 대비 마찰(접선) 방향 구속 강성의 비율 — 크게 주면 미끄럼을 더 단단히 억제한다.", "②"),
    ("margin", "실제로 닿기 전, 이 거리 안에 들어오면 미리 접촉을 활성화하는 MuJoCo의 여유 거리 파라미터.", "②"),
    ("restitution", "충돌 후 튀어오르는 정도를 나타내는 반발계수 — soft contact(MuJoCo)는 이를 직접 지정하지 못하고 임피던스로 간접 근사한다.", "②"),
    ("efc_force", "MuJoCo가 내부적으로 계산한 모든 구속(접촉+equality)의 힘을 담는 배열 — 우리가 참조하는 접촉력/구속력의 실체.", "②"),
    ("NLP", "등식·부등식 제약이 있는 비선형 최적화 문제 — 우리 궤적최적화(CasADi+IPOPT)가 푸는 형태.", "③"),
    ("collocation", "상태 x(t)와 입력 u(t)를 모두 변수로 두고 동역학을 등식 제약(defect)으로 부과하는 transcription — 우리 NLP의 방식.", "③"),
    ("shooting", "제어입력 u(t)만 변수로 두고 상태는 적분으로 얻는 transcription — single/multiple 두 변형이 있다.", "③"),
    ("multiple shooting", "구간별로 시작 상태를 별도 변수로 두어 사슬을 끊는 shooting 변형 — 카오스 폭발을 차단하는 우리 '창 평가'의 원리.", "③"),
    ("defect", "collocation에서 인접 노드 사이 동역학이 정확히 성립하도록 강제하는 등식 제약 — 위반량이 0이 되어야 유효한 궤적이다.", "③"),
    ("내점법", "부등식 제약을 장벽함수로 내부에서 다루며 KKT 조건에 수렴해가는 NLP solver 방식 — IPOPT가 이 계열.", "③"),
    ("SQP", "매 반복 문제를 이차근사(QP)로 바꿔 순차적으로 푸는 NLP solver 방식 — 내점법의 대안 계열(sequential quadratic programming).", "③"),
    ("sparsity", "NLP 변수·제약 간 대부분이 서로 무관해 야코비안·헤시안이 대부분 0인 성질 — CasADi/IPOPT가 이를 활용해 대규모 문제를 빠르게 푼다.", "③"),
    ("warm start", "이전에 구한 해(또는 근사해)를 다음 최적화의 초기값으로 주는 것 — 수렴 속도와 안정성을 크게 높인다.", "③④"),
    ("contact-implicit", "상보성 조건을 NLP 제약으로 그대로 넣어 접촉 스케줄까지 최적화가 스스로 찾아내게 하는 방식 — Posa 2014.", "③"),
    ("rollout", "후보 제어를 시뮬레이터에 실제로 굴려 궤적과 비용을 얻는 것 — 0차 방법의 기본 연산.", "④"),
    ("horizon", "최적화·예측이 내다보는 미래 시간 길이 — 길수록 카오스 민감도가 커지고, MPC는 이를 매 스텝 다시 미는(receding) 방식으로 관리한다.", "④⑤"),
    ("temperature λ", "MPPI 가중치 exp(−J/λ)의 뾰족함을 조절하는 값 — 작을수록 최저 비용 샘플에 쏠리고, 클수록 고르게 평균한다.", "④"),
    ("importance sampling", "실제로 행동을 샘플링한 분포와 다른(갱신된) 분포 기준으로 기댓값을 보정하는 기법 — PPO 비율(ratio) 항의 근거.", "⑦"),
    ("colored noise", "샘플마다 독립인 백색잡음 대신 시간적으로 상관된 잡음을 써 제어입력이 매끄럽게 나오도록 하는 MPPI 실전 기법.", "④"),
    ("CEM", "상위 엘리트 샘플의 평균·분산으로 다음 탐색 분포를 다시 적합하는 0차 최적화(cross-entropy method) — 단순·강건해 MPC에도 흔히 쓰인다.", "④"),
    ("CMA(공분산 적응)", "샘플 순위 기반으로 탐색분포의 공분산(파라미터 간 상관)까지 학습하는 진화전략 — 우리 시스템 식별에 쓰는 방법.", "④"),
    ("MPPI", "비용의 소프트맥스 가중 평균으로 제어열을 갱신하는 경로적분 기반 실시간 MPC — Williams 2017.", "④"),
    ("Predictive Sampling", "스플라인 노트 주변을 샘플링해 최고 비용 후보를 채택하는 가장 단순한 0차 MPC — MJPC의 기준선.", "④"),
    ("pathwise", "시뮬레이션 연산 전체를 사슬법칙으로 미분해 얻는 gradient — 자동미분/미분가능 시뮬레이터의 방식(해석 gradient).", "⑤"),
    ("score function", "동역학은 미분하지 않고 '무엇을 샘플했는지'의 로그확률만 미분하는 gradient 추정 방식 — REINFORCE/PPO의 기반.", "⑤⑦"),
    ("REINFORCE", "score function 추정의 원조 정책기울기 알고리즘 — ∇E[R]=E[∇log π·R] 형태.", "⑤"),
    ("BPTT", "시간축을 거슬러 사슬법칙으로 gradient를 전파하는 방법(backpropagation through time) — 카오스 시스템에서는 분산이 폭발한다.", "⑤"),
    ("Lyapunov 지수", "초기조건의 미세한 오차가 e^{λt}로 커지는 비율 — 값이 크면 그 시스템은 카오스적이다.", "⑤"),
    ("randomized smoothing", "함수를 노이즈로 흐려 기댓값 E[J(θ+ε)]을 취하면 원래 불연속이던 비용도 매끄러워지는 성질 — 0차 방법이 접촉 kink에 강한 이유.", "④⑤"),
    ("bundled gradient", "randomized smoothing된 기대비용의 gradient — 0차 방법이 암묵적으로 따르는 방향이며 Suh 2022가 이론화했다.", "⑤"),
    ("SRB", "다리 등 부속 질량을 무시하고 로봇 전체를 질량·관성 하나로 축소한 모델(single rigid body) — 4족 convex MPC의 표준 축소모델.", "⑥"),
    ("게이트", "각 발이 언제 접촉/스윙인지 미리 정해두는 스케줄표(trot 등) — 접촉의 if문을 없애 문제를 볼록 QP로 만든다.", "⑥"),
    ("Raibert heuristic", "스윙발의 착지 위치를 몸통 속도와 원하는 속도의 차이에 비례해 정하는 고전적 경험식.", "⑥"),
    ("WBC", "MPC/QP가 정한 힘·가속도 명령을 전신 관절토크로 변환하는 고주기(0.5~1kHz) 하위 제어층(whole-body control).", "⑥"),
    ("null-space", "주요 과제(예: 접촉력 추종)를 방해하지 않으면서 남는 자유도를 부차 목표에 쓸 수 있는 영역 — WBC의 우선순위 제어 원리.", "⑥"),
    ("ZOH", "디지털 제어 명령을 다음 갱신 전까지 일정하게 유지하는 것(zero-order hold) — 정책/PD가 500Hz~1kHz로 도는 사이의 유지 방식.", "⑦"),
    ("receding horizon", "매 스텝 유한 구간을 다시 최적화하고 그중 첫 입력만 실행한 뒤 버리는 MPC의 핵심 원리.", "⑥"),
    ("PPO clip", "정책 갱신 비율(importance ratio)이 너무 커지지 않도록 [1−ε, 1+ε] 범위로 잘라내는 PPO의 안정화 장치.", "⑦"),
    ("GAE", "여러 시간축 길이의 TD 잔차를 지수가중 평균해 advantage를 저분산으로 추정하는 기법(generalized advantage estimation) — PPO 학습의 표준 부품.", "⑦"),
    ("advantage", "어떤 행동이 그 상태의 평균보다 얼마나 더 좋았는지의 척도 A(s,a) — 정책기울기 ∇E[R]=E[∇log π·A]의 가중치.", "⑦"),
    ("DR", "학습 중 물리 파라미터를 무작위로 흔들어 정책이 모델 오차에 강건해지도록 강제하는 sim-to-real 기법(domain randomization).", "⑦"),
    ("actuator net", "모터의 명령-실제토크 관계를 벤치 데이터로 지도학습한 회귀모델 — RL 시뮬 안에 들어가는 하이브리드 구동기 모델.", "⑦"),
    ("teacher-student", "특권 정보(지형 등)로 먼저 배운 교사 정책을 관측 정보만으로 모방하는 학생 정책으로 증류하는 sim-to-real 기법.", "⑦"),
    ("RMA", "배포 중 관측 이력으로 환경/자기 파라미터의 잠재벡터를 온라인 추정해 정책을 적응시키는 기법(rapid motor adaptation) — teacher-student의 확장.", "⑦"),
]

terms_sorted = sorted(terms, key=lambda x: x[0].lower())
rows = [["용어", "한 줄 정의", "출처 페이지"]] + [[t, d, p] for t, d, p in terms_sorted]

part_C = [
    quote(f"이 페이지는 ①~⑦ 페이지에 등장했거나 그 페이지 주제와 직접 연결되는 용어를 한 곳에 모은 사전입니다 — "
          f"실제 수록 용어 수는 {len(terms_sorted)}개이며, 정렬은 ABC 순을 앞세우고 그 뒤를 가나다 순으로 이었습니다."),
    h2(f"전체 용어표 (ABC → 가나다 순, 총 {len(terms_sorted)}개)"),
    table(rows),
    callout("사용법: 본문(①~⑧)을 읽다가 낯선 약어나 기호를 만나면 이 표에서 먼저 찾고, '출처 페이지' 열의 번호로 "
            "해당 페이지의 원래 문맥(비유·수식·실측치)으로 돌아가 확인하세요.", "📖"),
]

n2 = append(p8a, part_C)
print(f"appended to p8a ({p8a}): {n2} blocks (table rows incl. header = {len(rows)})", flush=True)

# ════════════════════════════════════════════════════════════
# 검증
# ════════════════════════════════════════════════════════════
for name, pid in [("p8 (⑧)", p8_id), ("p8a (⑧-a)", p8a)]:
    r = _request("GET", f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100")
    blocks = r.json().get("results", [])
    n_table = sum(1 for b in blocks if b.get("type") == "table")
    n_todo = sum(1 for b in blocks if b.get("type") == "to_do")
    print(f"{name}: {len(blocks)} top-level blocks (table={n_table}, todo={n_todo})", flush=True)

print("DONE", flush=True)
print("p8  url: https://www.notion.so/" + p8_id.replace("-", ""))
print("p8a url: https://www.notion.so/" + p8a.replace("-", ""))
