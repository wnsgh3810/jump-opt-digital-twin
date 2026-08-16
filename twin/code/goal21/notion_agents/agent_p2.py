# -*- coding: utf-8 -*-
"""② 접촉 동역학 마스터 페이지 심화 증축 — 6.~10. 섹션 append + child '②-a solref·solimp 수학 완전 분해'."""
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")

TARGET_P2 = "396ab81d2550819c8012e25c57d26c53"  # ② 접촉 동역학 마스터


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


def _post_with_retry(method, url, **kwargs):
    for attempt in range(8):
        r = requests.request(method, url, **kwargs)
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", 1.0)) + 0.5
            print(f"429 rate limited, sleeping {wait}s (attempt {attempt+1})", flush=True)
            time.sleep(wait)
            continue
        return r
    return r


def img(p):
    r = _post_with_retry("POST", "https://api.notion.com/v1/file_uploads",
                          headers={**H, "Content-Type": "application/json"}, json={})
    r.raise_for_status()
    uid, url = r.json()["id"], r.json()["upload_url"]
    with open(p, "rb") as f:
        rr = _post_with_retry("POST", url, headers=H, files={"file": (Path(p).name, f, "image/png")})
        rr.raise_for_status()
    return {"object": "block", "type": "image", "image": {"type": "file_upload", "file_upload": {"id": uid}}}


def new_page(parent, title):
    r = _post_with_retry("POST", "https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                          json={"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status(); time.sleep(0.6)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 80):
        r = _post_with_retry("PATCH", f"https://api.notion.com/v1/blocks/{page}/children",
                              headers={**H, "Content-Type": "application/json"},
                              json={"children": blocks[i:i + 80]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:500])
        time.sleep(0.6)


# ════════════════════════════════════════════════════════════════════
# 브리프 A — 본문 증축 (② 접촉 동역학 마스터 페이지 끝에 append)
# ════════════════════════════════════════════════════════════════════
main_blocks = [
    callout("여기서부터는 1~5절에서 다진 정성적 직관을 **완전한 용어 사전 + 실제 수식 + 진단표**로 마감합니다. "
            "새 물리를 들여오지 않고, 위에서 이미 쓴 solref(tc, ζ)·solimp·condim·마찰원뿔을 손에 잡히게 재구성하는 절입니다.", "🧭"),

    # ───────────────────────── 6. 용어 완전 사전 ─────────────────────────
    h2("6. 용어 완전 사전"),
    para("접촉 동역학 문헌을 읽을 때 자주 부딪히는 용어를 세 층으로 나눠 정리합니다 — **수학적 뼈대**(왜 어려운가를 "
         "설명하는 이론), **MuJoCo 실무 파라미터**(우리가 실제로 만지는 손잡이), **부기 용어**(읽다가 마주치는 주변 개념). "
         "정의는 정확하게, 직관은 한 줄 비유로 옮겼습니다."),

    h3("6.1 수학적 뼈대 4개 — '왜 접촉이 어려운가'의 이론"),
    table([
        ["용어", "정의", "직관 한 줄"],
        ["Signorini 조건", "0 ≤ r ⊥ F ≥ 0 — 침투량 r과 접촉력 F가 둘 다 음이 아니면서 서로 직교(상보)",
         "닿지 않았으면 힘이 없고, 눌렸으면 힘이 있다 — 그 중간(살짝 닿았는데 힘도 있고 침투도 있는) 상태는 논리적으로 없다"],
        ["상보성(complementarity)", "두 비음수 변수 중 적어도 하나는 반드시 0이어야 하는 조건",
         "'둘 다 조금씩'은 허용되지 않는다 — 스위치처럼 둘 중 하나만 켜진다"],
        ["KKT 조건", "제약 있는 최적화의 1차 필요조건 — 정상성(gradient=0) + 원시실현성(제약 만족) + "
         "쌍대실현성(승수≥0) + 상보슬랙성(제약이 안 걸리면 승수=0)",
         "접촉력은 사실 물리 법칙이 아니라 '침투를 막는' 어떤 최적화 문제의 라그랑주 승수다"],
        ["마찰 원뿔(friction cone)", "접선(미끄럼) 방향 힘의 크기가 μ×법선(수직) 힘을 넘지 못하도록 정의되는 영역",
         "옆으로 미는 힘이 원뿔 밖으로 나가면 반드시 미끄러진다 — 원뿔은 '버틸 수 있는 힘'의 경계선"],
    ]),
    para("이 넷은 사실 한 이야기의 네 표현입니다: Signorini는 접촉의 **물리적 진술**이고, 상보성은 그 진술이 수학에서 "
         "취하는 **형태**이며, KKT는 '왜 상보성이 나타나는가'를 설명하는 **일반 이론**(접촉력=최적화의 결과물)이고, "
         "마찰 원뿔은 이 논리를 접선 방향까지 **확장**한 것입니다."),

    h3("6.2 MuJoCo 실무 파라미터 5개 — 우리가 실제로 만지는 손잡이"),
    table([
        ["용어", "정의", "직관 한 줄"],
        ["condim", "접촉이 만드는 구속의 차원 수 — 1(법선만) / 3(+미끄럼 2축) / 4(+비틀림) / 6(+구름 2축)",
         "발이 얼마나 '자유롭게' 미끄러지고 돌고 구를 수 있는지의 해상도 — 숫자가 클수록 더 세밀하게 막는다"],
        ["margin과 gap", "margin=충돌 검사(narrowphase)를 미리 시작하는 여유 거리, gap=접촉으로 취급은 하되 "
         "구속력은 아직 0인 완충 구간",
         "margin은 '미리 감시를 시작', gap은 '닿은 걸로 치지만 아직 안 민다' — 서로 다른 두 종류의 여유"],
        ["impratio", "마찰(접선) 방향 구속 강성 ÷ 수직(법선) 방향 구속 강성의 비",
         "옆으로 미끄러지는 것을 수직으로 파고드는 것보다 얼마나 더 단단히 막을지 — 우리는 100 (미끄럼을 거의 봉쇄)"],
        ["반발계수(restitution)", "충돌 전후 접근 속도 대비 이탈 속도의 비 e = −v'/v (0=완전비탄성, 1=완전탄성)",
         "공이 바닥에 튈 때 원래 떨어진 높이의 몇 %로 되튀어 오르는지"],
        ["broadphase / narrowphase", "broadphase=AABB 등 값싼 방법으로 충돌 '후보' 쌍을 추리는 1차 필터, "
         "narrowphase=후보 쌍에 대해서만 정확한 거리·법선을 계산하는 2차 정밀검사",
         "1차: 대충 가까운 것만 추리기(경비원의 눈대중) → 2차: 진짜 겹쳤는지 자로 재기(정밀검사)"],
    ]),
    para("이 다섯은 이미 3절(마스터 클래스 ②의 앞부분)에서 개별적으로 등장했던 것들을 다시 나열한 것인데, 여기서 "
         "강조하고 싶은 건 **margin/gap과 solimp의 width는 전혀 다른 층위의 '여유'**라는 점입니다 — margin/gap은 "
         "'접촉을 감지·생성하는 기하학적 여유'이고, width는 4절에서 다룰 '이미 생성된 접촉이 얼마나 단단해지는가'의 "
         "전이 구간입니다. 이름이 비슷해 혼동하기 쉬운 지점입니다."),

    h3("6.3 부기 용어 2개"),
    table([
        ["용어", "정의", "직관 한 줄"],
        ["efc_force", "MuJoCo가 매 스텝 계산한 모든 구속력(접촉 + equality 포함)을 담아두는 내부 배열",
         "솔버가 실제로 얼마의 힘을 썼는지를 사후에 읽을 수 있는 창구 — GRF·연결힘을 뽑아낼 때 여기를 본다"],
        ["Painlevé 역설", "완전 강체 + 쿨롱 마찰 조합에서 운동방정식의 해가 존재하지 않거나 유일하지 않은 사례 (1895)",
         "분필을 비스듬히 눌러 칠판에 그으면 끼익하며 튀는 현상 — '정확한' 강체 모델조차 가끔은 답이 없다"],
    ]),
    callout("Painlevé 역설이 주는 함의는 큽니다: soft contact(볼록 완화)는 '정확함을 포기한 타협'이 아니라, "
            "**애초에 hard 강체 모델이 항상 답을 주지 못하는 상황을 우회하는 필수 장치**이기도 합니다. "
            "7절의 볼록 QP가 '해가 항상 존재'를 보장하는 것이 바로 이 역설의 해결책입니다.", "🧩"),

    # ───────────────────────── 7. MuJoCo 솔버가 푸는 실제 문제 ─────────────────────────
    h2("7. MuJoCo 솔버가 푸는 실제 문제"),
    para("지금까지 solref·solimp·condim·마찰원뿔을 정성적으로 설명했는데, 이 절에서는 그것들이 실제로 어떤 "
         "**하나의 최적화 문제**의 계수인지를 수식으로 보여줍니다. 매 스텝, MuJoCo는 다음을 풉니다 (Todorov 2014 표기를 "
         "우리 문맥에 맞게 정리):"),
    code("min over f:  ½ fᵀ A f + fᵀ (a_unc − a*)   s.t. f ∈ 마찰원뿔들의 곱집합,  A = J M⁻¹ Jᵀ + R"),
    h3("각 기호가 의미하는 것"),
    bullet("**f** — 모든 접촉력과 equality(폐루프 구속력)를 한 벡터로 모은 것. 접촉이 여러 개, equality가 여러 개여도 "
           "전부 이 f 하나에 쌓입니다."),
    bullet("**a_unc** — '구속이 하나도 없다고 가정했을 때'의 가속도(unconstrained acceleration). 중력·관성력·이미 걸린 "
           "관절 토크만으로 계산되는, 접촉을 모르는 세계의 가속도입니다."),
    bullet("**a*** — solref가 정하는 목표 가속도. '위반량 r을 얼마나 급하게 없앨 것인가'를 지정하는 참조 신호이며, "
           "8절의 child 페이지에서 그 정확한 식 r̈_target = −(2/tc)ṙ − (1/tc²ζ²)r을 완전히 분해합니다."),
    bullet("**R** — solimp가 정하는 정규화(regularization) 행렬. 이게 커질수록 해가 '부드러워지고'(덜 뻣뻣), 0에 "
           "가까울수록 hard 구속에 가까워집니다. R>0이 바로 아래 ②의 가역성을 보장하는 항입니다."),
    para("즉 지금까지 '접촉 손잡이 두 개'라고 불러온 solref와 solimp는 실제로는 **이 한 개의 볼록 이차계획법(QP) 안에서 "
         "a*와 R을 채우는 계수**였던 것입니다. 새로운 개념이 아니라, 앞 절들의 정성적 설명을 하나의 수식으로 압축한 것뿐입니다."),

    h3("이 정식화가 주는 4가지 보장"),
    bullet("① **볼록(convex)** — 목적함수가 f에 대해 이차형식(A가 양의 준정부호)이고 제약(원뿔들의 곱)도 볼록집합이므로, "
           "해가 **항상 존재하고 유일**합니다. Painlevé 역설처럼 '답이 없는' 상황이 구조적으로 생기지 않습니다."),
    bullet("② **R>0 → 가역(invertible)** — R이 조금이라도 양수면 A가 양의 정부호가 되어 역행렬이 존재 → 운동(가속도)에서 "
           "힘을 거꾸로 풀어낼 수 있습니다(inverse dynamics). 이것이 우리 프로젝트가 q/dq만 있어도 τ를 역산해 식별할 수 있는 "
           "이유의 수학적 뿌리입니다."),
    bullet("③ **원뿔 사영(cone projection) → 미끄러짐 자동** — 최적해 f가 마찰 원뿔 경계에 부딪히면 자동으로 접선분력이 "
           "μ×법선분력으로 잘립니다. '미끄러지는 조건을 if문으로 감시'할 필요가 없고, 최적화 자체가 미끄러짐 여부를 결정합니다."),
    bullet("④ **equality도 같은 f에 포함** — 폐루프 구속(①에서 다룬 connect)과 접촉이 서로 다른 메커니즘이 아니라 "
           "**같은 볼록 문제 안의 같은 종류의 미지수**입니다. 그래서 우리 4-bar의 폐루프와 발-바닥 접촉이 한 솔버 호출로 "
           "동시에, 모순 없이 풀립니다."),
    para("이 네 보장은 각각 우리 파이프라인의 특정 지점에 꽂힙니다 — ①은 시뮬레이션이 절대 '풀리지 않아 멈추는' 일이 "
         "없다는 안정성 보장, ②는 GOAL19 이후 우리가 밀어온 역동역학 기반 식별의 근거, ③은 실기 배포 시 미끄러짐을 "
         "사람이 스케줄링하지 않아도 된다는 실무 편의, ④는 ①번 페이지에서 확인한 폐루프-접촉 통합 처리입니다."),
    para("출처: Todorov 2014, \"Convex and analytically-invertible dynamics with contacts and constraints\" (ICRA) — "
         "이 절 전체가 이 논문의 정식화를 옮긴 것입니다."),
    callout("결국 solref·solimp는 '커스텀 물리 트릭'이 아니라, **하나의 볼록 이차계획법 안에서 목표 가속도(a*)와 "
            "정규화(R)를 채우는 두 계수**일 뿐입니다. 이 관점이 서면 '왜 파라미터가 이것 둘뿐인가'라는 의문이 풀립니다 — "
            "이 QP의 자유도가 딱 그만큼이기 때문입니다.", "🔑"),

    # ───────────────────────── 8. 접촉 한 스텝의 파이프라인 ─────────────────────────
    h2("8. 접촉 한 스텝의 파이프라인"),
    para("7절의 QP는 '접촉이 이미 정해진 뒤'에 힘을 계산하는 단계입니다. 그 앞뒤로 MuJoCo가 실제로 밟는 다섯 단계를 "
         "순서대로 따라가 봅니다."),
    bullet("① **broadphase** — 모든 geom 쌍을 일일이 정밀 검사하면 너무 느리므로, AABB(축정렬 경계상자) 같은 값싼 "
           "방법으로 '겹칠 가능성이 있는' 후보 쌍만 추립니다. 멀리 떨어진 geom은 여기서 이미 걸러집니다."),
    bullet("② **narrowphase** — broadphase에서 살아남은 후보 쌍에 대해서만 정확한 거리·법선·접촉점을 계산합니다. "
           "margin 안에 들어오면 비로소 접촉이 '생성'됩니다. **우리 모델은 foot 실린더 vs floor plane 단 한 쌍뿐이라, "
           "이 broadphase+narrowphase 비용은 사실상 0에 가깝습니다** — 4족 로봇처럼 geom이 수십 개인 경우와 대비되는 "
           "우리 문제의 단순함입니다."),
    bullet("③ **접촉 프레임 구성** — 생성된 각 접촉점에 대해 법선(normal) 1축 + 접선(tangent) 2축으로 국소 좌표계를 "
         "세웁니다. 이 프레임이 이후 마찰 원뿔·condim이 정의되는 기준축입니다."),
    bullet("④ **7절의 볼록 문제 풀이** — 모든 접촉(과 equality)의 프레임이 갖춰지면, 그것들을 한데 모아 7절의 QP를 "
           "한 번에 풉니다. 여기가 계산 비용의 실질적 대부분을 차지하는 단계입니다."),
    bullet("⑤ **적분 & efc_force 기록** — 풀린 f로 가속도를 갱신하고 다음 상태로 적분하며, 동시에 f를 efc_force "
           "배열에 기록합니다. 우리가 사후에 GRF·연결힘을 뽑아 검증할 때 읽는 곳이 바로 여기입니다."),
    para("정리하면, 파이프라인의 앞부분(①②③)은 '접촉이 어디에 있는지 찾는' 기하 문제이고 뒷부분(④⑤)은 '그 접촉에서 "
         "얼마의 힘이 필요한지 푸는' 최적화 문제입니다. 우리처럼 geom 쌍이 하나뿐인 문제에서는 기하 문제가 거의 공짜이므로, "
         "**계산 시간의 실질적 병목은 언제나 ④번 QP 자체**입니다 — 이것이 우리 트윈이 '접촉 판정 로직'을 튜닝할 필요 없이 "
         "곧바로 solref/solimp만 튜닝해도 되는 이유이기도 합니다."),

    # ───────────────────────── 9. 증상→원인→처방 진단표 ─────────────────────────
    h2("9. 증상 → 원인 → 처방 진단표"),
    para("접촉 튜닝에서 실제로 마주치는 여덟 가지 증상과, 그 배후에 있는 파라미터, 그리고 처방을 정리합니다. "
         "우리 프로젝트에서 실제로 겪은 사례는 근거와 함께 표기했습니다."),
    table([
        ["증상", "의심 파라미터", "처방"],
        ["GRF가 톱니처럼 튐(채터링)", "solref tc가 dt에 비해 너무 작음", "tc ≥ 2·dt 로 (우리 G16에서 겪고 6ms로 해소)"],
        ["발이 바닥을 파고듦", "tc 너무 큼 / imp0(d0) 너무 낮음", "tc↓ 또는 d0↑"],
        ["착지 때 과하게 튐", "impratio 낮음 + 미끄럼", "impratio↑ (우리 100)"],
        ["경사/횡력에서 스르르 미끄러짐", "μ(마찰계수) 낮음", "friction 1번째 성분↑"],
        ["제자리 회전이 이상함", "비틀림 마찰 없음", "condim 4↑ (우리 6)"],
        ["굴러가야 하는데 미끄러짐", "구름 마찰 없음", "condim 6 + rolling 계수"],
        ["이륙이 늦음", "접촉이 놓아주지 않음 — tc 큼", "tc↓"],
        ["모서리에서 힘 방향이 이상함", "pyramidal 원뿔의 왜곡(√2)", "cone=elliptic (우리 설정)"],
    ]),
    para("표를 다시 훑어보면 tc 하나가 네 가지 증상(채터링·파고듦·이륙 지연 두 방향 모두)에 반복 등장합니다 — 7절에서 "
         "본 것처럼 tc는 목표 가속도 a*의 시간축 그 자체이기 때문에, '접촉이 얼마나 빨리 반응하는가'의 모든 증상이 "
         "결국 이 하나의 숫자로 수렴합니다. 마지막 줄의 pyramidal 왜곡은 각뿔로 원뿔을 근사하면 축과 축 사이(대각선 "
         "방향)의 반경이 실제 원보다 최대 √2배 커지는 기하학적 문제로, condim이나 impratio와는 다른 층위(원뿔의 "
         "'모양' 자체)의 오차입니다."),
    callout("결론: 접촉 튜닝 디버깅의 절반 이상은 사실 **tc 하나를 만지는 일**입니다. 나머지 절반(impratio·condim·"
            "cone)은 '방향성 있는' 문제 — 미끄럼/회전/모서리처럼 특정 상황에서만 튀어나오므로, 증상이 방향성을 "
            "띠는지부터 확인하는 것이 진단의 첫 걸음입니다.", "🩺"),

    # ───────────────────────── 10. 반발(튀어오름)이 필요할 때의 3가지 대안 ─────────────────────────
    h2("10. 반발(튀어오름)이 필요할 때의 3가지 대안"),
    para("MuJoCo의 표준 solref((tc, ζ)의 양수 표기)는 반발계수를 직접 지정하는 자리가 없습니다 — soft contact 철학상 "
         "'부드럽게 감쇠해 수렴'이 기본값이기 때문입니다. 공을 튀기거나 탄성 충돌을 재현해야 하는 문제라면 다음 세 대안이 "
         "있습니다."),
    bullet("① **solref 음수 표기** — solref의 두 값을 음수로 주면 (tc, ζ) 해석이 아니라 (−k, −b), 즉 강성·감쇠를 "
           "직접 지정하는 모드로 전환됩니다. 감쇠 b를 낮게 주면 에너지가 덜 소산되어 반발에 가까운 거동을 얻을 수 있습니다."),
    bullet("② **충돌 직후 속도 반전 (이벤트 처리)** — 접촉을 감지한 순간 스크립트/컨트롤러 레벨에서 법선 방향 속도를 "
           "−e·v로 강제 반전시키는 방법. 반발계수 e를 물리적으로 정확히 지정할 수 있지만, 접촉을 '이벤트'로 따로 "
           "감시해야 하는 부담이 있습니다."),
    bullet("③ **탄성 geom (플렉스/소프트바디)** — 아예 강체가 아니라 변형 가능한 body(flex/soft body)로 모델링해 "
           "에너지 저장·반환을 물리적으로 재현하는 방법. 가장 정확하지만 계산 비용이 가장 큽니다."),
    para("**우리 점프 로봇의 착지는 반발이 거의 없는 문제**입니다 — 발이 닿으면 에너지를 흡수하며 스탠스가 이어지는 "
         "것이 목표이지, 튀어오르는 것이 목표가 아니므로 이 절의 세 대안은 우리 파이프라인에는 무관합니다. 다만 향후 "
         "어떤 이유로든 '착지 시 탄성 반발'을 모델링해야 할 상황이 오면 이 세 갈래가 선택지가 됩니다."),

    quote("한 장 요약 | 접촉 튜닝의 90%는 solref·solimp·condim 세 손잡이 — 나머지는 진단표로."),
]

# ════════════════════════════════════════════════════════════════════
# 브리프 B — child 페이지 "②-a solref·solimp 수학 완전 분해"
# ════════════════════════════════════════════════════════════════════
child_blocks = [
    quote("목표 | solref와 solimp 두 파라미터가 '위반량 r'로부터 실제 접촉력 f로 변하는 전 과정을, "
          "한 걸음도 건너뛰지 않고 손으로 따라갑니다."),
    para("본문 ②-7절에서 본 볼록 QP는 목표 가속도 a*(solref가 결정)와 정규화 R(solimp가 결정)을 재료로 삼습니다. "
         "이 child 페이지는 그 두 재료가 각각 어떤 수식으로 채워지는지를 처음부터 끝까지 전개합니다."),

    h2("1. 위반 좌표 r — 모든 것의 출발점"),
    para("MuJoCo의 모든 구속(접촉이든 폐루프 equality든)은 '원래 0이어야 하는데 위반된 양' r 하나로 통일해서 다룹니다. "
         "r의 정의는 구속의 종류에 따라 다릅니다."),
    bullet("**접촉의 r** — 침투 깊이(penetration depth). 두 geom이 아직 안 닿았으면 r<0(음의 거리, 즉 gap), "
           "닿아서 파고들었으면 r>0."),
    bullet("**equality의 r** — 구속되어야 할 두 점 사이의 이탈 거리. 우리 connect(4-bar coupler)라면 '연결되어야 할 "
           "두 프레임 원점 사이의 벌어짐'이 r입니다."),
    para("종류는 다르지만 이후 처리(2절의 목표 동역학, 3절의 강성·감쇠 환산)는 **완전히 동일한 수식**을 씁니다 — "
         "이것이 접촉과 폐루프가 7절의 QP에서 같은 f 벡터에 함께 들어갈 수 있는 이유입니다."),

    h2("2. 목표 동역학 — r을 어떻게 없앨 것인가"),
    para("r이 0이 아니면(=위반이 있으면), MuJoCo는 r을 곧바로 0으로 만들지 않고 **'r이 이런 식으로 줄어들었으면 "
         "좋겠다'는 목표 가속도**를 세웁니다:"),
    code("r̈_target = −(2/tc)·ṙ − (1/(tc²·ζ²))·r     ← solref = (tc, ζ)"),
    para("이 식은 임계감쇠(critically damped) 스프링-댐퍼 방정식과 정확히 같은 형태입니다. **ζ=1**(임계감쇠)이면 "
         "위반량 r이 진동(오버슈트) 없이 매끄럽게 0으로 수렴하고, 그 수렴에 걸리는 시간의 스케일이 바로 **tc**입니다 — "
         "tc가 크면 천천히, 작으면 빠르게 위반이 사라집니다."),
    para("여기서 결정되는 것은 '목표'일 뿐, 실제로 얼마나 세게 밀어붙일지(=얼마나 단단한 스프링처럼 행동할지)는 "
         "아직 정해지지 않았습니다 — 그건 다음 절의 몫입니다."),

    h2("3. 목표 가속도를 강성·감쇠로 환산하기"),
    para("r̈_target이라는 '목표'는 실제로는 가상의 스프링-댐퍼가 내는 힘(단위질량 기준 가속도)으로 구현됩니다. "
         "그 스프링 상수 k와 댐퍼 계수 b를 tc·ζ·d(r)로부터 환산하는 개념식은 다음과 같습니다 (단위질량 기준 개념식 — "
         "실제 힘은 여기에 유효 관성이 곱해져 나옵니다):"),
    code("b = 2/(dmax·tc),     k = d(r)/(dmax²·tc²·ζ²)"),
    para("이 식에서 가장 눈에 띄는 것은 **tc가 분모에 제곱으로 들어간다**는 점입니다 — k ∝ 1/tc². 즉 시정수 tc를 "
         "절반으로 줄이면(접촉을 더 '빨리 반응하게' 만들면), 그 대가로 가상 강성 k는 **4배**가 됩니다. tc 하나를 "
         "만지는 것이 9절 진단표에서 그렇게 자주 등장한 이유가 바로 이 제곱 관계입니다."),
    para("또한 k의 분자에 있는 d(r)은 이 강성이 '고정된 재료 상수'가 아니라 **침투 진행 상황에 따라 값이 바뀌는 "
         "적응형 강성**이라는 뜻입니다 — 그 d(r)이 무엇인지가 다음 절의 주제입니다."),

    h2("4. 임피던스 d(r) — solimp 5개 파라미터의 실체"),
    para("d(r)은 위반량 r의 진행 정도에 따라 0(구속 없음)에 가까운 값에서 1(구속 최대)에 가까운 값 사이를 매끄럽게 "
         "잇는 곡선입니다. 이 곡선의 모양을 solimp의 5개 숫자가 결정합니다:"),
    bullet("**d0** — 접촉이 막 시작될 때(r이 아주 작을 때)의 임피던스 강도. 첫 접촉이 얼마나 '단단하게' 시작하는지."),
    bullet("**dmax** — 위반이 충분히 진행되었을 때 도달하는 최대 임피던스 강도. 최종적으로 얼마나 단단해질 수 있는지의 상한."),
    bullet("**width** — d0에서 dmax로 전이(transition)가 일어나는 구간의 길이. 전이가 '얼마나 넓은 r 범위'에 걸쳐 일어나는지."),
    bullet("**midpoint** — 그 전이 구간의 중심 위치. 전이가 침투 초반/중반/후반 중 어디에서 일어나는지."),
    bullet("**power** — 전이 곡선의 급격함(지수). 값이 클수록 midpoint 근방에서 더 가파르게 꺾이는 S자 곡선이 됩니다."),
    img(FIG / "m2_contact.png"),
    para("그림은 이 5개 파라미터가 만드는 d(r) 곡선의 모양을 보여줍니다 — 침투량 r이 커질수록(가로축) 임피던스가 "
         "d0에서 dmax로 width·midpoint·power가 정하는 모양을 따라 부드럽게 전이합니다. 이 곡선이 3절 식의 분자 "
         "d(r)에 그대로 대입되어, 침투가 얕을 때는 부드럽고(=k 작음) 깊을 때는 단단한(=k 큼) 비선형 접촉을 만듭니다 — "
         "'침투가 깊어질수록 구속이 단단해진다'는 본문 3절의 서술이 바로 이 그림입니다."),

    h2("5. 워크드 예제 — 우리 fit 값을 대입해 봅니다"),
    para("우리 모델의 실제 fit 값은 **tc=6ms, ζ=1, d0=0.371**입니다. 이 값들을 3절 식에 대입해 실제로 손을 움직여 봅니다."),
    code("tc: 6ms → 3ms로 반으로 줄이면\n"
         "k ∝ 1/tc²  이므로  k_new / k_old = (tc_old/tc_new)² = (6/3)² = 4\n"
         "→ 시정수를 절반으로 줄이는 것만으로 가상 강성은 4배가 됩니다."),
    para("이 4배라는 숫자가 실감나지 않는다면 9절 진단표의 '채터링' 행을 떠올리면 됩니다 — tc를 무심코 반으로 줄이면 "
         "접촉이 4배 뻣뻣해지고, dt 대비 상대적으로 너무 뻣뻣해진 접촉은 수치적으로 진동(채터링)하기 시작합니다. "
         "우리가 G16에서 실제로 마주친 현상이 정확히 이 메커니즘입니다."),
    para("이 개념식의 실전 활용이 G20의 핵심 연결고리입니다 — 트윈의 접촉을 위 식으로 **실제 강성 단위(N/m)**로 "
         "환산하면 유효 강성 **k_eq ≈ 1.3×10⁵ N/m**가 나옵니다. 이 수치를 NLP(궤적 최적화) 쪽 접촉 모델의 강성과 "
         "직접 맞춰준 결과, NLP와 트윈 사이의 간극이 **−14% → −4.4%**로 줄었습니다 — solref/solimp가 '트윈 내부에서만 "
         "의미 있는 손잡이'가 아니라, 다른 표현(NLP의 해석적 접촉)과도 같은 물리 단위로 대화할 수 있는 다리라는 것을 "
         "보여준 실증 사례입니다."),
    callout("정리: tc·ζ·d(r) → (k, b) → k_eq(N/m) 환산 → NLP 접촉 강성과 매칭. 이 한 줄이 solref·solimp를 "
            "'MuJoCo 안에서만 통하는 매직 넘버'에서 '물리적으로 해석 가능한 강성·감쇠'로 끌어올리는 전체 경로입니다.", "🔗"),

    h2("6. 흔한 오해 세 가지"),
    bullet("**오해 1: tc는 '접촉 지속시간'이다** — 아닙니다. tc는 위반량 r이 감쇠하는 **시정수**(response time)이지, "
           "발이 바닥에 닿아 있는 물리적 시간(스탠스 구간)과는 다른 개념입니다. 스탠스는 수백 ms 지속돼도 tc는 수 ms 단위입니다."),
    bullet("**오해 2: k는 재질(고무·강철 등) 상수다** — 아닙니다. 3절 식에서 보듯 k는 d(r)·tc·ζ로부터 나오는 "
           "**관성 스케일 상대값**(단위질량 기준 개념식)이며, 실제 물리적 힘 단위로 쓰려면 유효 관성을 곱해야 합니다 "
           "(5절의 k_eq 환산이 그 과정입니다). '단단한 재질=큰 k'라는 재질 직관을 그대로 들여오면 안 됩니다."),
    bullet("**오해 3: solimp(임피던스)를 키우면 무조건 좋아진다** — 아닙니다. d0·dmax를 무작정 올려 접촉을 "
           "'더 단단하게' 만들면 3절의 k가 커지고, 9절 진단표의 채터링 행에서 본 것처럼 dt 대비 너무 뻣뻣해져 수치적으로 "
           "진동합니다. 단단함은 항상 dt·tc와의 상대적 관계 안에서만 의미가 있습니다."),
    para("세 오해의 공통점은 solref·solimp를 '물리적 재질/시간 상수'로 직독하려는 데서 옵니다. 실제로는 둘 다 "
         "**수치 적분 솔버의 튜닝 계수**이고, 물리적 의미(k_eq 같은)를 얻으려면 반드시 5절처럼 환산을 거쳐야 합니다."),

    quote("한 장 요약 | r(위반) → r̈_target=−(2/tc)ṙ−(1/tc²ζ²)r(solref가 목표를 정함) → d(r)로 채워진 "
          "b=2/(dmax·tc), k=d(r)/(dmax²tc²ζ²)(solimp가 세기를 정함) → k_eq로 환산해 NLP와 매칭. "
          "tc는 '시정수'지 '접촉시간'이 아니고, k는 '재질값'이 아니라 '상대 강성'이며, 크게 만든다고 늘 좋아지지 않는다."),
]

# ════════════════════════════════════════════════════════════════════
# 실행
# ════════════════════════════════════════════════════════════════════
print(f"appending {len(main_blocks)} blocks to p2 ({TARGET_P2})", flush=True)
append(TARGET_P2, main_blocks)
print("main append done", flush=True)

child_id = new_page(TARGET_P2, "②-a solref·solimp 수학 완전 분해")
print("child page", child_id, flush=True)
append(child_id, child_blocks)
print("child append done", flush=True)

# 검증 (페이지네이션 포함 — 전체 블록 수)
def count_blocks(pid):
    total, n_img, cursor = 0, 0, None
    while True:
        url = f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = requests.get(url, headers=H).json()
        blocks = r.get("results", [])
        total += len(blocks)
        n_img += sum(1 for b in blocks if b.get("type") == "image")
        if r.get("has_more"):
            cursor = r.get("next_cursor")
        else:
            break
    return total, n_img


for name, pid in [("p2 (본문)", TARGET_P2), ("child (②-a)", child_id)]:
    total, n_img = count_blocks(pid)
    print(f"{name}: {total} blocks total, {n_img} images", flush=True)

print("DONE — https://www.notion.so/" + TARGET_P2.replace("-", ""))
print("DONE child — https://www.notion.so/" + child_id.replace("-", ""))
