# -*- coding: utf-8 -*-
"""마스터 클래스 Part 1 — 부모 + ①폐루프 ②접촉 ③궤적최적화 ④샘플링/MPPI."""
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
CONCEPT = "115ab81d255080fdaae6f28f55e3e205"
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")


def rt(text):
    out = []
    for i, seg in enumerate(text.split("**")):
        if seg:
            out.append({"type": "text", "text": {"content": seg},
                        "annotations": {"bold": i % 2 == 1}})
    return out


def h1(t): return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rt(t)}}
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
        r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                           headers={**H, "Content-Type": "application/json"},
                           json={"children": blocks[i:i + 80]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:500])
        time.sleep(0.4)


# ════════════════ 부모 ════════════════
parent = new_page(CONCEPT, "마스터 클래스 — MuJoCo 폐루프·접촉·최적화·샘플링 (질문 6개에서 출발한 완전 정리, 2026-07-07)")
print("MASTER_PARENT", parent, flush=True)
append(parent, [
    quote("이 문서의 목적 | 오늘 하루의 질문 6개(폐루프 외력설, 튜닝 파라미터, 시각화, 트리 루프, MuJoCo vs 해석식, "
          "MuJoCo 최적화/MPC/gradient)를 출발점으로, **이 분야를 '마스터' 수준으로 이해하는 데 필요한 배경 전체**를 "
          "8개 child 페이지에 담았다. 각 페이지는 독립적으로 읽을 수 있게 용어 정의부터 시작하고, "
          "비유 → 물리/수식 → 우리 프로젝트의 실증 데이터 → 외부 문헌 순으로 전개한다."),
    h2("읽기 지도"),
    table([
        ["페이지", "다루는 질문", "핵심 결론 한 줄"],
        ["① 폐루프의 진실", "'외력 우회라 부정확+튜닝 지옥' 커뮤니티 설의 진위",
         "그 설은 '명시적 스프링 핵'과 구식 엔진(ODE/Bullet) 이야기 — MuJoCo 등식구속은 암시적이라 무조건 안정, 우리 실측으로 파라미터 무감 확인"],
        ["② 접촉 동역학 마스터", "MuJoCo 접촉의 수학과 튜닝, 엔진 간 차이",
         "MuJoCo = 볼록 완화(soft): 해 유일·가역·빠름, 대가는 침투 — solref/solimp 두 개가 전부"],
        ["③ 궤적 최적화 지도", "해석식 경로의 전체 지형",
         "shooting/collocation × 접촉 3처리(phase/implicit/smooth) — 우리는 phase 고정 + IPOPT"],
        ["④ 샘플링과 MPPI", "MPPI가 정말 더 좋은가",
         "접촉·불연속에선 0차가 구조적으로 유리(기대값 스무딩), 그러나 우리 오프라인 정밀 점프엔 NLP 본선 + 트윈 폴리시 하이브리드가 정답"],
        ["⑤ Gradient의 물리학", "gradient를 어떻게 만들고 언제 무너지나",
         "세 추정기(해석/FD/0차) × 두 괴물(접촉 kink, 카오스 폭발) — 우리 창-평가와 CMA 선택의 이론적 근거"],
        ["⑥ 4족 MPC 해부", "GitHub 4족 MPC 코드는 어떻게 되어 있나",
         "MPC 안에는 시뮬레이터가 없다 — 축소 해석모델(SRB)+QP, 시뮬은 플랜트. 우리 구조와 동형"],
        ["⑦ RL로 policy 만들기", "MuJoCo에서 정책은 어떻게 학습되나",
         "정책기울기는 동역학을 미분하지 않는다 — 그래서 접촉에 강함. 우리 문제엔 지금은 trajopt가 적합"],
        ["⑧ 우리 연구 처방전", "이 지식이 우리 목적에 어떻게 연결되나",
         "4층 차이 정리 + 다음 실행 카드 + 4주 독서 로드맵"],
    ]),
    callout("권장 순서: ①→② (물리 기초) → ⑤ (gradient 본질) → ③→④ (최적화 두 경로) → ⑥→⑦ (분야 지형) → ⑧ (우리에게 적용). "
            "급하면 ①⑤⑧만 읽어도 오늘 질문의 답은 완결된다.", "🧭"),
    para("문헌 표기: 본문 인용은 저자·연도·제목으로 적었다 (arXiv 번호 포함 — 제목 그대로 검색하면 나옴). "
         "모두 이 분야의 검증된 표준 문헌이다."),
])

# ════════════════ ① 폐루프의 진실 ════════════════
p1 = new_page(parent, "① 폐루프의 진실 — '외력 우회' 소문의 기원과 MuJoCo equality의 실체")
print("c1", p1, flush=True)
append(p1, [
    quote("용어 | **명시적(explicit) 적분**: 지금 상태의 힘으로 다음 상태를 계산 (미래를 안 봄). "
          "**암시적(implicit) 적분**: 다음 상태에서 성립해야 할 조건을 방정식으로 풀어 계산 (무조건 안정). "
          "**ERP/CFM**: ODE/Bullet 엔진의 구속 튜닝 계수 (오차수정비율/구속힘혼합). "
          "**equality constraint**: 'A점과 B점은 항상 같다' 같은 등식을 솔버가 강제하는 것."),
    h2("1. 당신이 들은 소문은 '틀린 말'이 아니다 — 다른 대상에 대한 말이다"),
    para("커뮤니티에서 읽으신 \"폐루프는 외력을 추가해 우회 구현하는 거라 정확도 낮고 파라미터 튜닝도 많이 필요하다\"는 "
         "이야기에는 **세 개의 실제 기원**이 있고, 셋 다 사실에 뿌리가 있습니다. 다만 그 어느 것도 현재 MuJoCo의 "
         "equality constraint에 대한 정확한 묘사가 아닙니다:"),
    bullet("**기원 1 — 명시적 스프링 핵(hack)**: 루프를 지원 안 하는(또는 못 믿는) 환경에서 쓰는 고전 수법 — 두 점 사이에 "
           "아주 뻣뻣한 스프링-댐퍼 힘을 '사용자가 외력으로' 추가. 이건 진짜로 문제가 많습니다: 강성 k를 크게 하면 "
           "명시적 적분이 폭발하고(아래 그림), 작게 하면 링크가 벌어지고, k·c 두 개를 손튜닝해야 하고, dt까지 줄여야 합니다. "
           "소문의 '정확도↓·튜닝 지옥'은 정확히 이 방식의 증상입니다."),
    bullet("**기원 2 — 구식 엔진의 구속 품질**: ODE(Gazebo 기본)와 초기 Bullet의 조인트 구속은 ERP/CFM 두 계수를 "
           "문제마다 손봐야 했고, 뻣뻣하게 만들면 지터(떨림)가 생겼습니다. 그 세대의 경험담이 '폐루프 = 골칫거리'라는 "
           "통념으로 남았습니다."),
    bullet("**기원 3 — URDF의 한계**: 로봇 기술 표준 포맷인 URDF는 **루프를 아예 표현 못 합니다** (트리만 허용). "
           "그래서 4-bar가 있는 로봇을 URDF로 옮기면 링키지가 사라지고, 사람들이 위의 스프링 핵으로 때우곤 했습니다. "
           "'루프는 우회해야 한다'는 인상의 큰 출처."),
    h2("2. MuJoCo가 실제로 하는 것 — 외력이 아니라 '암시적 구속'"),
    para("MuJoCo도 트리는 트리로 둡니다(우리도 coupler에서 루프를 한 번 '자름'). 하지만 잘린 자리를 스프링 외력으로 "
         "때우는 게 아니라, **equality constraint를 접촉과 같은 볼록 최적화 솔버 안에서 암시적으로 풉니다** "
         "(Todorov 2014, \"Convex and analytically-invertible dynamics with contacts and constraints\", ICRA). "
         "차이를 비유로: 명시적 스프링은 '지금 벌어진 만큼 세게 당기기' — 세게 당길수록 다음 스텝에 과하게 튕겨서 발산합니다. "
         "암시적 구속은 '다음 스텝에 벌어짐이 줄어들도록 필요한 힘을 방정식으로 역산' — 아무리 뻣뻣해도 원리적으로 발산하지 않습니다."),
    img(FIG / "m1_implicit.png"),
    para("왼쪽: 같은 강성(k=1e7), 같은 dt(0.5ms)에서 명시적 방식은 수 ms 만에 폭발하고 암시적은 조용히 수렴합니다. "
         "오른쪽: 명시적 방식의 안정 조건 dt < 2√(m/k) — 폐루프에 필요한 강성 영역에서는 dt를 µs 급으로 줄여야 한다는 뜻이고, "
         "이것이 '튜닝 지옥'의 수학적 정체입니다. **암시적 구속에는 이 제한 자체가 없습니다.**"),
    h2("3. 그럼 파라미터는? — 있지만, '민감한 튜닝 대상'이 아님을 실측으로 확인"),
    para("MuJoCo equality의 부드러움은 solref(시정수 tc, 감쇠비 ζ)와 solimp(임피던스 곡선)로 정해집니다. "
         "우리 connect는 solref=(0.0008, 1) — 0.8ms 시정수로 하드코딩돼 있었죠. 어제(P12) 이걸 처음으로 스윕했습니다:"),
    table([
        ["connect solref tc", "종합 점수 (기준=8.0)", "판정"],
        ["0.3 ms", "8.0000 — 소수점 4자리까지 동일", "강성 포화 구간: 더 조여도 아무 변화 없음"],
        ["0.8 ms (현재)", "8.0 (기준)", "충분히 뻣뻣 — 검증 완료"],
        ["2 ms", "9.18 (+15%)", "느슨해지기 시작"],
        ["5 / 12 ms", "15.8 / 39.4", "링키지가 출렁 — 명확히 나쁨"],
    ]),
    callout("결론: 파라미터는 **존재하지만 '충분히 작게'라는 한 방향 조건**일 뿐, 문제마다 정밀 튜닝할 대상이 아닙니다. "
            "기본값 수준(≤1ms)이면 결과가 완전히 포화됩니다. '튜닝 지옥' 소문은 우리 상황에 적용되지 않음을 데이터로 확인.", "✅"),
    h2("4. 정확도는? — 해석식과 기계 정밀도 일치"),
    para("'우회라 부정확하다'에 대한 가장 강한 반증: 우리 4-bar의 MuJoCo 모델(트리+connect)과 폐루프를 손으로 소거한 "
         "해석적 축소좌표 동역학(사용자 유도)을 무작위 300개 상태에서 직접 비교한 결과 — **질량행렬 오차 4.4×10⁻¹⁶, "
         "bias(코리올리+중력) 오차 3.6×10⁻¹⁴**. 부동소수점 한계 그 자체입니다. 폐루프 잔차(coupler 끝과 rocker 끝의 벌어짐)도 "
         "1.1×10⁻¹⁶ m. '우회 구현'이라는 말이 무색한 수준으로, 두 표현은 같은 물리입니다."),
    h2("5. 다른 엔진들은 어떻게 하나 (전부 '자르고 닫는다')"),
    table([
        ["엔진", "폐루프 처리", "튜닝 성격"],
        ["MuJoCo", "equality (connect/weld/joint), 암시적 볼록 솔버", "solref/solimp — 기본값으로 대부분 OK (우리 실측)"],
        ["ODE (Gazebo)", "조인트 구속 + ERP/CFM", "문제별 손튜닝 필요했던 세대 — 소문의 고향"],
        ["Bullet/PyBullet", "btConstraint (point2point 등)", "ERP/CFM 유사; 뻣뻣하면 지터"],
        ["DART / RaiSim", "hard 구속 (LCP류)", "정확하지만 해 비유일/미분 곤란 이슈"],
        ["Drake", "hard/compliant 선택 가능", "연구용으로 가장 유연"],
        ["Simscape(MATLAB)", "cut joint 자동 + 닫힘 조건", "내부적으로 같은 원리 — '네이티브 지원'도 실은 자르고 닫음"],
    ]),
    para("핵심 통찰: **루프를 '네이티브'로 푼다는 도구들도 내부적으로는 전부 루프를 한 군데 자르고 닫힘 조건을 구속으로 "
         "강제합니다** (라그랑주 승수 = hard, 정규화 = soft의 차이일 뿐). 세 번째 길은 우리 해석식처럼 닫힘식이 손으로 풀리는 "
         "경우 축소 좌표로 아예 소거하는 것 — 평행사변형이라 가능했고, NLP에 쓰는 게 바로 그 표현입니다."),
    quote("한 장 요약 | 소문은 '명시적 스프링 핵 + 구식 엔진'의 실화다. MuJoCo equality는 암시적이라 안정성 문제와 "
          "dt 제약이 원천적으로 없고, 파라미터는 '충분히 작게' 한 방향 조건뿐이며(실측 포화 확인), 정확도는 해석식과 "
          "기계 정밀도로 일치한다(실측). 시각화도 무영향 — 렌더러는 몸체를 qpos 위치에 그릴 뿐이다."),
])

# ════════════════ ② 접촉 동역학 ════════════════
p2 = new_page(parent, "② 접촉 동역학 마스터 — 왜 어렵고, MuJoCo는 무엇을 포기하고 무엇을 얻었나")
print("c2", p2, flush=True)
append(p2, [
    quote("용어 | **상보성(complementarity)**: '침투 없음(r≥0)과 접촉력 없음(F≥0) 중 적어도 하나는 0' — 접촉의 본질적 "
          "either-or 논리. **LCP**: 그 논리를 그대로 푸는 선형 상보성 문제. **볼록 완화(convex relaxation)**: either-or를 "
          "부드러운 최적화로 근사해 항상 풀리게 만드는 것. **restitution**: 반발계수(튀어오름)."),
    h2("1. 접촉이 물리 시뮬레이션의 최종 보스인 이유"),
    para("자유 비행 동역학은 매끄러운 미분방정식이라 쉽습니다. 접촉이 들어오는 순간 세 가지가 동시에 깨집니다:"),
    bullet("**논리가 들어옴**: '닿았으면 힘이 있고, 안 닿았으면 0' — if문이 물리에 들어오면서 방정식이 매끄러움을 잃습니다 "
           "(Signorini 조건: 0 ≤ r ⊥ F ≥ 0)."),
    bullet("**마찰의 방향 결정**: 정지 마찰은 '움직이려는 방향의 반대'인데 그 방향은 힘을 알아야 정해지고 힘은 방향을 "
           "알아야 정해지는 순환 — 최대소산 원리로 최적화 문제가 됩니다."),
    bullet("**강체 가정의 자기모순**: 완전 강체 + 쿨롱 마찰 조합은 해가 없거나 여러 개인 상황이 실제로 존재합니다 "
           "(Painlevé 역설, 1895 — 분필이 칠판에서 끼익 하며 튀는 현상). 즉 '정확하게' 풀 대상 자체가 불완전한 모델."),
    h2("2. 두 학파 — hard(LCP)와 soft(볼록 완화)"),
    table([
        ["", "hard / LCP 계열", "soft / 볼록 완화 (MuJoCo)"],
        ["대표", "Stewart–Trinkle, Anitescu-Potra; DART, RaiSim, Dojo", "Todorov 2014; MuJoCo, (Drake compliant 모드)"],
        ["철학", "상보성 논리를 그대로 푼다", "논리를 부드러운 벌점으로 근사해 항상 풀리게"],
        ["장점", "침투 없음, 반발 정확", "해가 **항상 존재하고 유일** + **가역**(힘→운동뿐 아니라 운동→힘 역산 가능!) + 빠름 + 미분 잘됨"],
        ["단점", "해 비유일 가능, 느림, 미분 곤란", "침투 허용(µm~mm), 반발계수 직접 지정 불가"],
    ]),
    para("MuJoCo가 '가역'이라는 점은 우리에게 특별히 중요합니다 — inverse dynamics가 접촉 중에도 잘 정의되기 때문에 "
         "모델 기반 제어·식별과 궁합이 좋고, 이것이 MuJoCo가 'Model-based control을 위한 물리엔진'으로 설계된 이유입니다 "
         "(Todorov, Erez, Tassa 2012, IROS)."),
    h2("3. MuJoCo 접촉의 수학 — 딱 두 손잡이"),
    para("접촉(그리고 ①의 equality)은 위반량 r에 대해 다음 '참조 감쇠 거동'을 부과합니다 (개념식):"),
    code("목표 가속도  a* = −(2/tc)·ṙ − (1/(tc²·ζ²))·r     ← solref = (tc, ζ)\n"
         "실제 부과 강도 = 임피던스 d(r) ∈ [d0, dmax]        ← solimp = (d0, dmax, width, mid, power)\n"
         "즉: 침투가 깊어질수록(솔이 width를 지나며) 구속이 d0에서 dmax로 단단해짐"),
    img(FIG / "m2_contact.png"),
    bullet("**solref tc** = 접촉 스프링의 시정수. k ∝ 1/tc². 경험칙 tc ≥ 2·dt — 우리는 dt 0.5ms에 tc 6.0ms(fit). "
           "너무 작으면 GRF 채터링(우리 G16에서 실제로 겪음), 너무 크면 발이 파묻히고 이륙이 늦어집니다."),
    bullet("**solimp imp0(d0)** = 첫 접촉의 반발 강도. 우리 fit 0.371 — 부드러운 안착 쪽."),
    bullet("**condim**: 1(수직만)/3(+미끄럼)/4(+비틀림)/6(+구름). 우리는 6 — 발 실린더의 비틀림·구름까지."),
    bullet("**마찰 원뿔**: pyramidal(각뿔, LP 친화적이나 모서리 방향 마찰 √2배 왜곡) vs elliptic(물리 정확) — 우리는 elliptic."),
    img(FIG / "m3_cones.png"),
    bullet("**impratio**: 수직 대비 마찰 방향 구속 강성비 (우리 100 — 미끄럼을 단단히)."),
    h2("4. 실전 튜닝 노트 (우리 프로젝트에서 배운 것 포함)"),
    bullet("접촉 파라미터는 GRF로 fit하지 말 것 — GRF 계측이 불신될 때 q/dq 재현을 통해 간접 식별 (우리 원칙; "
           "solref/imp0는 q/dq 창 점수로 식별했고 G20에서 NLP 접촉 강성을 트윈 유효강성 k_eq≈1.3e5로 환산해 맞춤)."),
    bullet("반발(튀어오름)이 필요한 문제(공 튀기기 등)에서 MuJoCo는 solref 음수 표기(직접 강성/감쇠 지정)나 별도 근사가 필요 — "
           "다행히 점프 로봇의 착지는 반발이 거의 없어 무관."),
    bullet("이륙/착지 이벤트를 '스케줄'하지 않아도 되는 것이 soft contact의 최대 실무 이점 — 힘이 0이 되며 자동 이륙 "
           "(우리 ste 지표가 모델 검증에 쓰일 수 있는 이유)."),
    bullet("μ(마찰계수)는 미끄러짐이 실제로 일어난 데이터가 있어야 식별 가능 — 우리 점프에선 약식별이라 문헌값 1.0 고정, "
           "미끄러짐 의심 구간은 잔차 스파이크 감지로만 취급."),
    h2("5. 엔진 선택 가이드"),
    table([
        ["쓰임", "권장", "이유"],
        ["모델 기반 제어·식별·MPC", "MuJoCo", "가역·유일해·빠름·미분(FD/MJX)"],
        ["대규모 병렬 RL", "Isaac(PhysX), MJX/Brax", "GPU 수천 환경"],
        ["접촉 정밀 검증(침투 0 요구)", "RaiSim/DART/Drake(hard)", "hard 구속"],
        ["미분가능 접촉 연구", "Dojo, MJX", "구속의 암시적 미분/스무딩"],
    ]),
    quote("한 장 요약 | 접촉은 '논리+순환+역설'로 어려운데, MuJoCo는 볼록 완화로 '항상 풀리고 유일하고 가역'을 얻는 대신 "
          "약간의 침투를 허용했다. 손잡이는 사실상 solref(tc,ζ)와 solimp 두 개 — 우리 fit(6ms/0.371)은 그 위에서 "
          "q/dq 재현으로 식별된 값이다."),
])

# ════════════════ ③ 궤적 최적화 지도 ════════════════
p3 = new_page(parent, "③ 궤적 최적화 지도 — 해석식 경로의 전체 지형 (우리 NLP가 서 있는 곳)")
print("c3", p3, flush=True)
append(p3, [
    quote("용어 | **transcription**: 연속 시간 최적제어를 유한 개 변수의 NLP로 바꾸는 번역. **shooting**: 제어입력만 변수로 "
          "두고 상태는 적분으로 얻음. **collocation**: 상태와 입력을 모두 변수로 두고 동역학을 등식 제약으로 부과. "
          "**DDP/iLQR**: horizon을 뒤에서 앞으로 쓸며 국소 LQR 근사로 개선하는 2차 방법."),
    h2("1. 세 가지 transcription — 각각의 성격"),
    table([
        ["방식", "변수", "장점", "약점", "우리와의 관계"],
        ["single shooting", "u(t)만", "변수 적음, 구현 단순", "카오스에 취약 — 뒤쪽 u의 gradient가 폭발 (⑤ 참조)", "full-replay 평가가 이 구조 (그래서 발산 증폭 시험)"],
        ["multiple shooting", "u(t) + 구간별 시작상태", "구간 절단으로 카오스 차단, 병렬화", "이음매 등식 제약 추가", "**우리 '창 평가'가 정확히 이 아이디어** (0.1s 창 리셋)"],
        ["direct collocation", "x(t), u(t) 전부", "gradient 최고 품질, sparsity, 제약 자연스러움", "변수 많음", "**우리 CasADi NLP (task 0~28)** — Hermite-Simpson류"],
        ["DDP/iLQR (간접류)", "u(t) (피드백 게인 부산물)", "빠름, 피드백 공짜", "상태 제약 어려움", "Crocoddyl/OCS2/MJPC-iLQG 계열"],
    ]),
    para("비유: single shooting은 '출발 각도만 정해 대포 쏘기'(멀리 갈수록 민감), collocation은 '전체 궤적을 점토로 빚어놓고 "
         "물리 법칙에 맞게 다듬기'(다루기 쉬움), DDP는 '뒤에서부터 최적 반응을 계산해 내려오기'."),
    h2("2. 접촉 처리 3형 — 궤적 최적화의 진짜 갈림길"),
    bullet("**A. phase 고정 (우리 + 4족 MPC 관행)**: 접촉 스케줄(스탠스→비행)을 미리 정하고 각 phase 안에서는 매끄러운 "
           "동역학 + 제약(발끝 위치 고정, GRF≥0, 마찰원뿔, |τ|≤한계)으로 풂. 장점: 매끄러워서 IPOPT가 잘 수렴. "
           "단점: 스케줄 자체는 사람이 설계. 단일 점프처럼 스케줄이 자명한 문제에 최적."),
        bullet("**B. contact-implicit**: 상보성 조건(r≥0 ⊥ F≥0)을 NLP 제약으로 그대로 넣어 **스케줄까지 최적화가 발견** "
           "(Posa, Cantu, Tedrake 2014, IJRR). 새 보행 패턴 발견 같은 탐색 문제에 강력하지만 수렴이 매우 까다로움 — "
           "상보성 제약은 제약자격(LICQ)이 깨져서 solver가 자주 길을 잃음."),
    bullet("**C. 접촉 스무딩**: 동역학에 soft contact를 넣고 전체를 매끄럽게 — MJX류 미분가능 시뮬 최적화가 이 노선. "
           "간단하지만 스무딩 바이어스(⑤)와 stiff ODE 비용을 치름."),
    h2("3. Solver와 도구 생태계"),
    table([
        ["도구", "계열", "특징"],
        ["CasADi + IPOPT (우리)", "collocation+내점법", "자동미분·sparsity 자동, 연구 표준 조합"],
        ["TOWR (Winkler 2018)", "phase 최적화 포함", "4족 게이트·발위치·CoM 동시 최적화의 고전"],
        ["Crocoddyl (Mastalli 2020)", "DDP(FDDP)", "전신 모델 고속 — Pinocchio 해석 동역학 위"],
        ["OCS2 (ETH)", "SLQ/DDP MPC", "ANYmal 계열 실기 MPC"],
        ["MJPC (DeepMind 2022)", "시뮬=모델", "iLQG(유한차분)+Predictive Sampling — 예외적으로 시뮬을 직접 모델로"],
    ]),
    h2("4. 우리 파이프라인 리캡 — 배포 궤적이 만들어지는 길"),
    bullet("① CasADi로 4-bar 축소좌표 동역학(당신의 유도) + a_hat 역모델 + phase 제약 구성 → IPOPT로 τ(t), q(t) 동시 최적화"),
    bullet("② 얻은 τ(t)를 MuJoCo 트윈에서 open-loop 리허설 — 접촉 차이(k_eq 매칭)와 마찰로 생기는 갭 확인 (G20: −14%→−4.4%)"),
    bullet("③ 트윈 통과분만 배포 CSV로 (70/85/100%) — 다음 실험실 세션의 체크리스트(해설 ⑪) 대상"),
    callout("수렴 실전 팁 (우리 경험): 변수 스케일링(각도 rad·토크 10Nm급을 O(1)로), 좋은 초기 궤적(정적 자세→탄도 보간), "
            "warm start(이전 해), 제약 완화 후 조이기 순서. IPOPT가 안 풀리면 대개 모델이 아니라 스케일링 문제.", "🛠️"),
    quote("한 장 요약 | 궤적 최적화 = transcription 선택 × 접촉 처리 선택. 우리는 collocation×phase-고정 — 단일 점프라는 "
          "문제 성격에 정확히 맞는 조합이고, 접촉 스케줄 탐색이 필요해지면 contact-implicit(Posa 2014)이 다음 도구다."),
])

# ════════════════ ④ 샘플링과 MPPI ════════════════
p4 = new_page(parent, "④ 샘플링 기반 최적화와 MPPI — '그게 더 좋은가'에 대한 정직한 답")
print("c4", p4, flush=True)
append(p4, [
    quote("용어 | **0차(zeroth-order)**: 미분 없이 함수값만으로 최적화. **rollout**: 후보 제어를 시뮬에 굴려 궤적·비용을 "
          "얻는 것. **CEM**: 상위 엘리트 샘플로 분포를 다시 fit하는 교차엔트로피법. **MPPI**: 비용의 소프트맥스 가중 평균으로 "
          "제어를 갱신하는 경로적분 MPC. **λ(temperature)**: 가중치의 뾰족함 조절."),
    h2("1. 0차 방법 가계도 — 전부 '뿌리고, 점수 매기고, 몰아가기'"),
    table([
        ["방법", "갱신 규칙", "성격"],
        ["Random Search", "제일 좋은 샘플 채택", "기준선"],
        ["CEM", "상위 K% 엘리트의 평균/분산으로 분포 재적합", "단순·강건, MPC에도 흔함"],
        ["CMA-ES (우리 식별)", "순위 기반 + **공분산 적응**(파라미터 상관 학습)", "저~중차원 오프라인 최적화의 왕"],
        ["MPPI (Williams et al. 2017)", "u ← u + Σᵢ wᵢ·δᵢ,  wᵢ ∝ exp(−Jᵢ/λ)", "모든 샘플을 부드럽게 활용, 실시간 MPC 특화"],
        ["Predictive Sampling (Howell et al. 2022, MJPC)", "스플라인 노트 주변 샘플 → best 채택", "'가장 단순한 방법'이 iLQG에 필적한 사건"],
    ]),
    img(FIG / "m6_mppi.png"),
    para("MPPI의 이론적 뿌리는 경로적분 제어/자유에너지 쌍대성입니다 — 최적 제어분포가 비용의 지수 가중으로 표현된다는 "
         "결과에서 저 소프트맥스 갱신식이 유도됩니다 (Williams et al. 2017, \"Information Theoretic MPC for Model-Based "
         "Reinforcement Learning\", ICRA — arXiv에서 원문 공개). 실전에서 중요한 세부: 노이즈를 시간 상관(콜로드 노이즈)으로 "
         "주거나 스플라인 노트에 주지 않으면 τ가 지글지글해집니다."),
    h2("2. 왜 접촉·불연속에서 0차가 '구조적으로' 유리한가"),
    para("⑤에서 자세히 다루지만 핵심만: 접촉이 만드는 kink 위에서 미분은 '한쪽 벼랑의 기울기'만 봅니다. 반면 샘플링은 "
         "노이즈 폭만큼의 이웃을 **평균**하므로, 실제로 최적화하는 함수가 E[J(θ+ε)] — **저절로 매끄러워진 비용**입니다 "
         "(randomized smoothing). 이것이 Suh et al. 2022 (ICML, \"Do Differentiable Simulators Give Better Policy "
         "Gradients?\")의 핵심 논지이고, '미분가능 시뮬레이터가 항상 이기지는 못한다'는 실험적 결론의 이유입니다."),
    h2("3. 정직한 손익계산서"),
    table([
        ["", "MPPI/샘플링", "NLP(collocation+IPOPT)"],
        ["접촉/불연속", "◎ 기대값 스무딩으로 강건", "△ phase 설계로 회피 필요"],
        ["제약 처리(토크한계·마찰원뿔)", "△ 벌점으로만 — 위반 보장 없음", "◎ 등식/부등식 제약 정확"],
        ["해의 매끄러움/정밀도", "△ 노이즈 잔재, λ·σ 튜닝", "◎ 국소 최적성 KKT 보장"],
        ["계산", "rollout 수천 개 — 병렬(GPU/멀티코어) 필수", "한 번의 희소 NLP — CPU면 충분"],
        ["온라인 재계획", "◎ anytime — 실시간 MPC의 강자", "× (풀 NLP는 느림; DDP 계열이 대안)"],
        ["필요물", "빠르고 정확한 시뮬(=트윈!)", "매끄러운 해석 모델"],
    ]),
    h2("4. \"그래서 MPPI가 더 좋아?\" — 문제 유형별 답"),
    bullet("**실시간 피드백이 있는 문제(주행·보행 MPC)**: MPPI/샘플링이 강력 — 매 스텝 재계획이 모델 오차를 흡수하고, "
           "불연속에 강하며, GPU로 수천 rollout이 싸다."),
    bullet("**오프라인 정밀 궤적 + 제약 많음 (= 우리 점프)**: NLP가 본선 — 토크 한계·마찰원뿔·이륙조건을 제약으로 정확히 "
           "지키는 해가 필요하고, 배포가 open-loop τ라 '재계획이 흡수해 줄 오차'가 없다. 정밀도가 전부."),
    bullet("**우리에게 최적 하이브리드**: NLP 해를 초기값으로 → **트윈 위 직접 폴리시(CMA/MPPI, τ 스플라인 노트 ~20개)**. "
           "장점: NLP↔트윈 번역 갭(접촉 차이)이 원천 소멸 — 트윈이 곧 평가 함수이므로. 예상 비용: 스탠스 rollout ~0.05s × "
           "샘플 1만 개 ÷ 10코어 ≈ 15분/사이클 — 오프라인로는 충분히 쌈."),
    callout("MJPC 일화가 주는 교훈: DeepMind가 '교육용 기준선'으로 넣은 Predictive Sampling(그냥 노트 흔들어 best 채택)이 "
            "정교한 iLQG와 여러 태스크에서 대등했다 (Howell et al. 2022, arXiv:2212.00541; github.com/google-deepmind/mujoco_mpc). "
            "**빠른 시뮬 + 단순한 탐색이 '똑똑한 미분'을 이기는 일이 흔하다** — 우리가 CMA로 식별을 밀어온 것과 같은 결.", "🎯"),
    quote("한 장 요약 | 샘플링의 힘 = 병렬성 + 기대값 스무딩. MPPI는 '실시간 재계획' 문제의 도구이고, 우리 오프라인 정밀 "
          "점프에서는 NLP가 본선 — 단 최종 폴리시를 트윈 위 샘플링으로 하면 모델 번역 갭이 0이 되는 하이브리드가 이상적."),
])

json.dump(dict(parent=parent, p1=p1, p2=p2, p3=p3, p4=p4),
          open(Path(__file__).parent / "master_pages_part1.json", "w"))
print("PART1 DONE")
