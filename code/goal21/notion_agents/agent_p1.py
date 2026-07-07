# -*- coding: utf-8 -*-
"""① 폐루프의 진실 — 증축부: 6.용어사전 7.equality카탈로그 8.구세대비교 9.FAQ 10.수치총정리."""
import requests, time
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")


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


def img(p):
    r = requests.post("https://api.notion.com/v1/file_uploads",
                      headers={**H, "Content-Type": "application/json"}, json={})
    r.raise_for_status()
    uid, url = r.json()["id"], r.json()["upload_url"]
    with open(p, "rb") as f:
        requests.post(url, headers=H, files={"file": (Path(p).name, f, "image/png")}).raise_for_status()
    return {"object": "block", "type": "image", "image": {"type": "file_upload", "file_upload": {"id": uid}}}


def new_page(parent, title):
    r = requests.post("https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                      json={"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status(); time.sleep(0.4)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 80):
        chunk = blocks[i:i + 80]
        while True:
            r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                               headers={**H, "Content-Type": "application/json"},
                               json={"children": chunk})
            if r.status_code == 429:
                time.sleep(2)
                continue
            if r.status_code != 200:
                raise RuntimeError(r.text[:500])
            break
        time.sleep(0.6)


PAGE = "396ab81d255081fb8890d8990ace923c"

blocks = [
    callout("이 아래는 '① 폐루프의 진실' 기존 내용에 이어지는 심화 증축입니다 — "
            "6.용어·개념 완전 사전, 7.equality 5종 카탈로그, 8.구세대와의 정량 비교(Baumgarte·ERP/CFM), "
            "9.FAQ, 10.우리 수치 총정리, 다섯 절을 새로 추가합니다.", "📎"),

    # ════════════════ 6. 용어·개념 완전 사전 ════════════════
    h2("6. 용어·개념 완전 사전"),
    para("폐루프 구속을 제대로 이해하려면 몇 개의 고정된 어휘가 필요합니다. 이 어휘는 크게 두 층으로 나뉩니다 — "
         "'무엇을 구속하는가'를 말하는 물리 층(자유도·좌표·야코비안·승수)과, '그 구속을 수치적으로 어떻게 유지하는가'를 "
         "말하는 솔버 층(drift부터 정규화까지)입니다. 아래에서 이 둘을 순서대로 정리합니다."),

    h3("6.1 무엇을 구속하는가 — 물리 층의 언어"),
    para("이 네 용어는 '시스템이 몇 개의 진짜 자유도를 가지고, 그중 무엇이 얼마나 묶여 있으며, 그 결과 어떤 힘이 생기는가'를 "
         "기술합니다."),
    table([
        ["용어", "정의", "우리 4-bar에서의 예"],
        ["자유도(DOF)", "시스템 상태를 정하는 독립 좌표 수", "트리 5-DOF(z, hip, crank, cpin, knee) − 구속 2 = 유효 3"],
        ["일반화 좌표", "로봇 자세를 나타내는 최소 변수 집합", "q = [bz, hip, crank, cpin, knee]"],
        ["구속 야코비안 J", "구속 위반의 변화율 ṙ = J·q̇ 를 주는 행렬", "connect는 3행(공간 3방향)"],
        ["라그랑주 승수", "구속을 지키기 위해 필요한 힘의 크기", "물리적 실체는 링크 핀에 걸리는 내부 하중"],
    ]),
    code("r(q)          = p_coupler(q) - p_rocker(q)     # 구속 위반 (3D)\n"
         "ṙ             = J(q) · q̇                        # 구속 야코비안\n"
         "τ_constraint  = J(q)ᵀ · λ                        # 라그랑주 승수 → 관절 힘으로 환산"),
    para("숫자로 보면 — 트리 5-DOF(z, hip, crank, cpin, knee)에서 connect가 만드는 구속은 공간 3방향(3행)이지만, "
         "이 평면 기구에서 실질적으로 자유도를 깎는 것은 2 — 그 결과 유효 자유도는 3입니다. 승수 λ는 이 3(혹은 2)개 "
         "방향에 대응하는 실제 힘이고, 이것이 곧 coupler-rocker 핀에 걸리는 하중입니다(9절에서 다시 다룹니다)."),

    h3("6.2 그 구속을 수치적으로 어떻게 유지하는가 — 솔버 층의 언어"),
    para("이 일곱 용어는 '구속을 계속 만족시키기 위해 솔버가 무엇을 하는가'를 기술합니다. 물리 층과 달리 이쪽은 "
         "수치해석·솔버 설계의 어휘입니다."),
    table([
        ["용어", "정의", "우리 4-bar에서의 예"],
        ["drift(표류)", "수치 오차로 구속 위반이 서서히 누적되는 현상", "안정화 없는 hard 구속의 고질병"],
        ["Baumgarte 안정화", "위반 r을 r̈ + 2αṙ + β²r = 0 으로 되돌리는 고전 기법(1972)", "PD로 위반을 죽이는 것"],
        ["ERP(Error Reduction Parameter)", "ODE/Bullet에서 한 스텝에 위반의 몇 %를 지울지 (0~1)", "8절에서 정량 비교"],
        ["CFM(Constraint Force Mixing)", "구속을 부드럽게 만드는 정규화 항. 크면 물렁", "8절에서 정량 비교"],
        ["solref(tc, ζ)", "MuJoCo의 구속 목표 거동 — 시정수 tc, 감쇠비 ζ", "우리 connect (0.0008, 1)"],
        ["solimp(d0,dmax,width,mid,power)", "위반 크기에 따라 구속 강도를 d0→dmax로 올리는 곡선", "9절 FAQ '풀릴 수도 있나' 참고"],
        ["정규화(regularization) R", "솔버 행렬 JM⁻¹Jᵀ+R의 R — 해의 존재·유일성 보장 장치", "볼록 솔버가 항상 풀리게 만드는 장치"],
    ]),
    para("예를 들어 우리 connect가 안정화 없이(hard) 걸려 있었다면, 매 스텝의 부동소수점 반올림이 r을 아주 조금씩 벌리고, "
         "그게 수천 스텝 누적되면 육안으로 보이는 링크 벌어짐(drift)이 됩니다. solref(0.0008, 1)은 이 벌어짐을 임계감쇠 "
         "스프링-댐퍼처럼 매 스텝 되돌리는 목표이고, solimp는 '위반이 클 때 얼마나 세게 되돌릴지'의 곡선을 추가로 정합니다."),
    bullet("헷갈리기 쉬운 짝 1 — ERP/CFM(가상 강성/감쇠를 0~1의 무차원 비율로 말함) vs solref(tc,ζ)(초 단위 시정수와 "
           "감쇠비로 말함): 둘 다 '구속을 얼마나 세게 지킬까'를 다른 언어로 말할 뿐이며, 정확한 환산식은 8절에 있습니다."),
    bullet("헷갈리기 쉬운 짝 2 — 라그랑주 승수(구속력, 물리량 N)는 '결과'이고, solimp의 d0~dmax(구속 강도, 무차원 0~1)는 "
           "'그 결과가 나오도록 솔버가 목표하는 만족도 스케줄'입니다. 하나는 출력, 하나는 설정값입니다."),
    quote("한 줄 정리 | 자유도-좌표-야코비안-승수는 '무엇을 얼마나 구속하는가'의 물리 언어이고, "
          "drift-Baumgarte-ERP/CFM-solref/solimp-정규화는 '그 구속을 수치적으로 어떻게 유지하는가'의 솔버 언어다."),

    # ════════════════ 7. equality 5종 카탈로그 ════════════════
    h2("7. equality 5종 카탈로그"),
    para("MuJoCo에서 폐루프를 닫는 방법은 connect 하나가 아닙니다. '두 몸체 사이에 무엇을 강제로 같게 만들 것인가'에 "
         "따라 다섯 가지 equality 타입이 있고, 우리가 connect를 고른 것은 그중 '링크를 실제 몸체로 살려둔 채' 점만 "
         "붙이는 유일한 선택이기 때문입니다."),
    table([
        ["종류", "구속 내용", "자유도 제거", "전형 용도", "우리와의 관계"],
        ["connect", "두 몸체의 한 점 일치 (3D 볼조인트)", "3", "폐루프 닫기", "★우리 4-bar (coupler 끝 = rocker)"],
        ["weld", "위치 + 자세 전부 일치", "6", "단단한 결합, 잡기", "미사용"],
        ["joint", "두 관절 각도의 다항식 커플링 y=f(x)", "1", "기어비, 미러 관절",
         "평행사변형은 crank=knee 커플링으로도 근사 가능하나 링크 질량 동역학이 사라짐 — 우리가 안 쓴 이유"],
        ["tendon", "힘줄 길이 고정/커플링", "1", "케이블 구동", "미사용"],
        ["distance(gap)", "두 geom 거리 유지", "1", "막대 근사", "미사용 (구버전 스타일)"],
    ]),
    h3("왜 connect인가 — joint 커플링과의 결정적 차이"),
    para("connect를 고른 이유는 하나입니다: crank와 coupler가 질량과 관성모멘트를 가진 '실제 몸체'로 시뮬레이션 안에 "
         "살아 있어야 관성 분포가 맞기 때문입니다. joint 타입으로 y=f(x) 식 커플링을 걸면(예: crank 각도로 knee 각도를 "
         "강제) 겉보기 궤적은 똑같이 흉내 낼 수 있지만, 그 커플링을 실제로 만드는 링크 자체가 모델에 존재하지 않게 되어 "
         "그 링크의 관성력(원심력, 코리올리 힘, 관성 반작용)이 통째로 계산에서 빠집니다. connect는 실제 몸체 두 점을 "
         "3D에서 일치시킬 뿐이므로, 링크는 여전히 자기 질량대로 가속·회전하고 그 반작용을 나머지 트리에 정직하게 "
         "돌려줍니다."),
    code("joint 커플링 (y=f(x)) : coupler 링크가 모델에 없음 → 그 링크의 원심력·코리올리 항이 통째로 소실\n"
         "connect (3D 점 구속)  : coupler가 실제 몸체로 존재 → 원심력·코리올리·관성 반작용이 자동으로 포함"),
    para("구체적 예 — 우리 4-bar에서 만약 joint 커플링(crank ↔ knee 다항식)을 썼다면, coupler 링크(질량 mc, "
         "무게중심 반경 r_cg)가 만드는 원심력 성분이 knee 쪽 토크 계산에서 완전히 사라집니다. 이는 실측 토크와의 "
         "잔차를 아무리 파라미터를 조정해도 0으로 줄일 수 없는 구조적 편향이 됩니다. connect는 이 항을 자동으로 "
         "포함하므로 그런 편향이 애초에 생기지 않습니다."),
    quote("한 줄 정리 | equality는 '무엇을 강제로 같게 만들까'의 5가지 문법이며, connect가 유일하게 "
          "'링크를 실제 몸체로 남긴 채' 루프를 닫는다 — 그래서 4-bar coupler의 관성이 정직하게 동역학에 들어간다."),

    # ════════════════ 8. 구세대와의 정량 비교 ════════════════
    h2("8. 구세대와의 정량 비교 (Baumgarte·ERP/CFM)"),
    para("solref(tc, ζ)는 하늘에서 뚝 떨어진 새 발명이 아니라 1970년대부터 쓰여온 Baumgarte 안정화의 후예입니다. "
         "차이는 '같은 목표를 어떻게 부과하는가'에 있습니다."),

    h3("8.1 Baumgarte와의 관계"),
    para("Baumgarte(1972)의 원식은 구속 위반 r에 대해 r̈ + 2αṙ + β²r = 0 을 명시적인 힘으로 더해 위반을 감쇠시키는 "
         "것입니다. solref(tc, ζ=1)은 정확한 α, β 대응은 표기마다 다르지만, 개념적으로는 같은 형태의 임계감쇠(ζ=1) "
         "2차 목표 동역학을 따릅니다."),
    code("Baumgarte(1972) :  r̈ + 2αṙ + β²r = 0                    (명시적 힘으로 부과)\n"
         "solref(tc, ζ=1)  :  r̈ + (2/tc)ṙ + (1/tc²)r = 0            (암시적 솔버 목표로 부과)"),
    para("우리 connect의 (tc, ζ) = (0.0008, 1)이 바로 이 목표 동역학의 물리 단위(초) 파라미터입니다. 차이는 딱 하나 — "
         "MuJoCo는 이 목표를 매 스텝 '더하는 힘'이 아니라 볼록 최적화 솔버가 만족시켜야 할 **암시적(implicit) 목표**로 "
         "부과합니다. 그래서 tc를 아주 작게(빡빡하게) 잡아도 Baumgarte처럼 명시적 적분기가 못 따라가 발산하는 일이 "
         "없습니다."),

    h3("8.2 ERP/CFM ↔ (k,b) 환산"),
    para("ERP와 CFM은 사실 가상의 스프링 강성 k, 댐핑 b, 그리고 시뮬레이션 스텝 h만 있으면 정확한 식으로 환산됩니다."),
    code("ERP = h·k / (h·k + b)     # 한 스텝에 위반의 몇 %를 지울지 (1에 가까울수록 '즉시' 교정)\n"
         "CFM = 1 / (h·k + b)       # 구속을 얼마나 무르게 할지 (0에 가까울수록 '단단')"),
    table([
        ["원하는 것", "필요한 조작", "부작용"],
        ["구속을 더 단단하게 (ERP↑, CFM↓)", "강성 k를 키운다", "h·k가 문턱을 넘으면 explicit 스텝이 불안정"],
        ["뻣뻣하게 하려면 CFM→0, ERP→1", "k를 계속 키워야 함", "그 극한에서 ODE류는 지터(진동) 발생"],
        ["h·k가 커지면", "명시적(explicit) 성분이 불안정해짐", "결국 (k,b,h) 3개가 얽힌 안정성 경계 위의 줄타기"],
    ]),
    para("구세대(ODE/Bullet류) 튜닝은 결국 이 삼각관계 위의 줄타기입니다."),
    bullet("증상 1 — 구속을 단단하게(ERP↑, CFM↓) 하려면 강성 k를 계속 올려야 합니다."),
    bullet("증상 2 — 어느 순간 h·k가 안정성 문턱을 넘으면 explicit 적분 스텝 자체가 진동·발산합니다 (지터)."),
    bullet("증상 3 — 그래서 실무자는 '적당히 무른 CFM'과 '적당히 낮은 ERP'를 경험적으로 찾아 헤맵니다 — "
           "이것이 흔히 말하는 '피지컬 엔진 파라미터 튜닝 지옥'의 정체입니다."),

    h3("8.3 결론 — 경계 위의 줄타기 vs 경계 없음"),
    para("구세대 튜닝 지옥은 (k, b, h) 3개가 얽힌 안정성 경계 위에서 줄타기하는 것입니다. MuJoCo는 이 경계 자체를 "
         "솔버 설계로 제거했습니다: (tc, ζ)는 물리적 시간상수/감쇠비라는 직관적 단위를 가지고, 목표를 암시적으로 "
         "부과하므로 tc를 아주 작게 잡아도(=매우 뻣뻣) 지터 없이 수렴합니다 — 남은 유일한 조건은 '충분히 작은 "
         "한 방향'뿐입니다 (10절에서 수치로 확인합니다)."),
    quote("한 줄 정리 | Baumgarte/ERP·CFM은 (k,b,h) 3변수가 얽힌 안정성 경계 위의 구세대 줄타기, "
          "solref/solimp는 그 경계를 암시적 솔버로 없애고 물리 단위 파라미터(tc,ζ)만 남긴 후계자다."),

    # ════════════════ 9. FAQ ════════════════
    h2("9. FAQ"),
    para("6~8절의 개념을 실무 질문 다섯 개로 다시 점검합니다."),

    h3("Q. 폐루프가 여러 개면 어떻게 하나요?"),
    para("A. equality를 닫아야 할 루프 수만큼 추가하면 됩니다. 병렬 로봇(Stewart 플랫폼 등)은 6개의 equality를 "
         "동시에 겁니다."),

    h3("Q. 구속이 '풀릴' 수도 있나요?"),
    para("A. solimp width 밖의 큰 위반에서는 힘이 포화되어, 급격한 충격 시 구속이 순간 벌어졌다 복귀할 수 있습니다. "
         "우리 점프 replay에서는 잔차가 1e-16 수준으로 유지되어 그 영역 근처도 가지 않았습니다."),

    h3("Q. 구속력을 읽을 수 있나요?"),
    para("A. data.efc_force에서 구속별 힘을 확인할 수 있습니다 — 링크 하중 해석(설계 검증)에 사용할 수 있습니다."),

    h3("Q. 계산 비용은?"),
    para("A. 구속 3행이 추가되는 것은 솔버 행렬에 3행이 더해지는 것 — 접촉 여러 개와 같은 규모로, 무시할 수 있는 "
         "수준입니다(우리 2kHz 시뮬레이션 유지)."),

    h3("Q. connect가 회전은 왜 안 잠그나요?"),
    para("A. 점 일치만 필요하기 때문입니다 — 핀 조인트 역할(회전 자유)은 coupler의 cpin 힌지가 이미 담당하고 있으므로, "
         "connect가 weld처럼 회전까지 잠그면 과구속이 됩니다."),

    # ════════════════ 10. 우리 수치 총정리 ════════════════
    h2("10. 우리 수치 총정리"),
    para("지금까지의 개념을 우리가 실제로 검증한 숫자로 마무리합니다. 아래 두 표는 각각 '폐루프가 정말 닫혀 있는가'와 "
         "'구속 파라미터가 너무 무르지 않은가'를 정량으로 답합니다."),

    h3("10.1 폐루프가 정말 닫혀 있는가 — 잔차·해석식 대조"),
    table([
        ["항목", "값", "의미"],
        ["폐루프 잔차 (qpos = [bz, q1, q2, −q2, q2] 세팅)", "1.1e-16 m", "구속 위반이 부동소수점 잡음 수준 — 사실상 완전히 닫힘"],
        ["해석식 M 행렬 대조 |dM|", "4.4e-16", "300개 무작위 상태에서 MuJoCo와 해석식 질량행렬이 사실상 동일"],
        ["해석식 bias 항 대조 |dbias|", "3.6e-14", "코리올리·중력 항도 300개 무작위 상태에서 사실상 동일"],
    ]),

    h3("10.2 구속이 너무 무르지는 않은가 — solref 스윕"),
    table([
        ["solref tc", "obj (비용)", "기준 대비"],
        ["0.3 ms", "8.0000", "0.8ms와 동일 (이미 포화)"],
        ["0.8 ms (현재 기준)", "8.0000", "기준"],
        ["2 ms", "+15%", "느슨해지며 비용 증가 시작"],
        ["5 ms", "+97%", "약 2배"],
        ["12 ms", "+393%", "거의 5배 — 뚜렷한 열화"],
    ]),
    para("스윕이 보여주는 그림은 명확합니다: tc를 0.8ms보다 더 조여도(0.3ms) 비용이 전혀 개선되지 않고 그대로 "
         "8.0000에 머뭅니다 — 이미 '충분히 뻣뻣'해서 포화된 것입니다. 반대로 tc를 늘려 구속을 무르게 하면 "
         "(2→5→12ms) 비용이 +15%→+97%→+393%로 단조 악화됩니다. 즉 안전지대는 'tc가 충분히 작은 쪽 절반'이고, "
         "우리가 쓰는 0.8ms는 그 포화 구간 안쪽에 확실히 들어가 있습니다."),
    quote("결론 | 구속 파라미터는 '충분히 작게' 한 방향 조건. 우리 값은 포화 구간 내부로 검증 완료."),

    callout("6~10절 종합 | 이 다섯 절은 '① 폐루프의 진실'의 핵심 결론 — 우리 connect 구속이 1e-16 잔차로 "
            "사실상 완전히 닫혀 있다는 사실 — 을 어휘(6) · 분류(7) · 역사적 맥락(8) · 실무 질문(9) · "
            "수치(10) 네 방향에서 다시 확인한 것입니다.", "🔒"),
]

print(f"total blocks to append: {len(blocks)}", flush=True)
append(PAGE, blocks)
print("APPEND DONE", flush=True)

r = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100", headers=H)
r.raise_for_status()
data = r.json()
total = len(data.get("results", []))
next_cursor = data.get("next_cursor")
while data.get("has_more"):
    r = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100&start_cursor={next_cursor}",
                     headers=H)
    r.raise_for_status()
    data = r.json()
    total += len(data.get("results", []))
    next_cursor = data.get("next_cursor")

print(f"FINAL total blocks on page: {total}", flush=True)
print("PAGE — https://www.notion.so/" + PAGE.replace("-", ""))
