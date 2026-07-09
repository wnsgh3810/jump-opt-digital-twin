# -*- coding: utf-8 -*-
"""07-09 노션 보고서 — part3 추록: ⑨ 구조 감사와 P16 (springref 발견)."""
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
root = json.load(open(Path(__file__).parent / "handoff.json"))["root"]


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status(); return r
    r.raise_for_status()


def rt(t, bold=False, code=False, link=None):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold: ann["bold"] = True
    if code: ann["code"] = True
    if ann: a["annotations"] = ann
    if link: a["text"]["link"] = {"url": link}
    return a


def para(*r): return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}
def h2(t): return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(emoji, *r): return {"type": "callout", "callout": {"icon": {"emoji": emoji}, "rich_text": list(r)}}
def code(t): return {"type": "code", "code": {"rich_text": [rt(t)], "language": "plain text"}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def new_page(parent, title, emoji):
    return req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": parent}, "icon": {"emoji": emoji},
        "properties": {"title": {"title": [rt(title)]}}}).json()["id"]


def append(pid, blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{pid}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


p9 = new_page(root, "⑨ 구조 감사와 P16 — springref 발견 (추록)", "🔧")
append(p9, [
    callout("🔧", rt("보고서 작성 후 이어진 질문 — \"로봇 동역학 자체에서 개선할 부분이 없는 거 확실해?\" — 에서 출발한 추록. ",
                    bold=True),
            rt("파라미터 공간은 소진됐지만 '구조' 레벨을 감사하니 미검증 축 4개가 나왔고, 그중 하나(springref)가 "
               "오늘 두 번째로 중요한 발견이 됐다.")),
    h2("구조 감사 — 미검증 축 4개와 판정"),
    table([
        ["축", "근거", "판정"],
        ["① stiff_knee의 springref (스프링 기준각)", "역대 한 번도 자유화 안 됨 (0 LOCK). P5의 crouch 정적 −3.3Nm 편향의 유력 원인", "시험 → 승리 (아래)"],
        ["② 발 형상 (길이/이중 접점)", "과거 hip 토크 lift-off 스파이크 진단", "사용자 확인: 실물이 실린더 그대로 — 닫힘"],
        ["③ 레일 stick-slip (정지≫운동 마찰)", "P5 정적 발견. P8 frictionloss 스윕은 '정지=운동' 모델이라 판정 불가였음", "시험 → 기각 (아래)"],
        ["④ 하중 비례 관절 마찰", "베어링 쿨롱은 하중 비례가 실물리. s2s/점프 상충의 관절측 후보", "사용자 판단: 과함 — 보류"],
    ]),
    h2("P16a — springref 해방 (승리)"),
    para(rt("용어: "), rt("springref", code=True),
         rt(" = 무릎 유연성 스프링(stiff_knee)이 '어느 각도를 향해 당기는가'의 기준각. GOAL19에서 스프링 채택 시 "
            "0(완전 신전 방향)으로 잠근 채 한 번도 풀지 않았다. crouch(크랭크 각 ≈ 2.6 rad)에서 스프링 토크 = k·(2.6 − ref)가 "
            "정적 편향으로 남는 구조.")),
    table([
        ["(k, ref)", "이중심판 JA / JC", "held-out A / C", "crouch 정적편향"],
        ["P14 기준 (1.35, 0 LOCK)", "1.000 / 1.000", "1.00 / 1.00", "3.50 Nm"],
        ["drop-test (k=0)", "4.92 / 1.38 — 폭발", "—", "0"],
        ["(1.35, 2.4)", "1.016 / 0.995", "0.990 / 0.999", "0.27 Nm (−92%)"],
    ]),
    bullet(rt("drop-test 판정: ", bold=True),
           rt("스프링을 빼면 Mode A가 4.9배 폭발 — stiff_knee가 대변하는 무릎부 유연성은 확실한 실재 물리 (GOAL19 재검증)")),
    bullet(rt("핵심 통찰: ", bold=True),
           rt("문제는 스프링이 아니라 ref=0 LOCK이었다. ref를 crouch 쪽으로 옮기면 동적 성능 거의 무손실로 정적 아티팩트가 사라진다 — "
              "'유연 요소가 동작점 부근에서 이완 상태'라는 물리적으로 자연스러운 그림")),
    h2("P16 통합 재적합 (37-dim: 32 + a_hat 4 + springref)"),
    table([
        ["항목", "결과"],
        ["springref 수렴값", "2.07 rad (crouch 2.6 근방) → 정적편향 3.5 → 0.7 Nm (−80%)"],
        ["이중 목적", "P14+ref2.4 기준에서 추가 −2.8%"],
        ["게이트", "hoA 1.009 / hoC 0.992 — 양쪽 통과"],
        ["a_hat 미세 갱신", "A3(쿨롱) 0.24 → 0.17, A1·CF 0.721"],
        ["산출 파일", "code/goal22/p16_structure/fourbar_p16_candidate.json"],
    ]),
    quote(rt("폐루프 심판 누적 개선: P13h 1.00 → P14 0.91 → P16 ≈ 0.88", bold=True)),
    h2("P16c — 레일 stick-slip (기각)"),
    code("F_rail = -tanh(v/0.003) * F_s * exp(-|v|/v_str)   (정지 근방만 크고 운동 시 소멸)"),
    para(rt("F_s ∈ [3,6,12,20]N × v_str ∈ [0.01,0.04] 스윕: 0421/0424의 초반(홀드) hip τ는 개선(0.82→0.72, 0.52→0.49)되지만 "
            "0602는 어느 설정에서도 악화(0.69→0.76+), F_s가 크면 푸시 부작용. "),
         rt("균일한 F_s가 존재하지 않음 → 기각", bold=True),
         rt(" (세션별 F_s는 fudge 위험). 레일 스틱션은 실재하되(P5 정적 증거) 이 단순 모델로는 순이득 없음 — 벤치 측정 항목으로 유지.")),
    h2("벤치 없이 a_hat을 재는 대안 — 중력-벤치 (사용자가 추후 직접)"),
    bullet(rt("원리: 중력이 이미 '알려진 부하'다. 다리를 공중에 띄우고 여러 자세에서 관절 정지 유지 → 필요한 축 토크 = CAD 질량의 중력토크 (계산 가능)")),
    bullet(rt("그때의 raw 전류값 기록 → (raw, 실제토크) 쌍이 저부하 영역에서 확보")),
    bullet(rt("발끝에 무게 아는 추(물병 등)를 걸면 중부하 점 추가 — P14/P16 a_hat 곡선 검증에 충분")),
    h2("갱신된 모델 서열 (⑧장 표를 대체)"),
    table([
        ["모델", "위치", "비고"],
        ["★ P16", "p16_structure/fourbar_p16_candidate.json", "현 최강 — 폐루프 최고 + 정적 정직성 (springref 2.07)"],
        ["P14", "p14_ahat/fourbar_p14_candidate.json", "a_hat 재식별 원본"],
        ["P13h", "fourbar_p13h_candidate.json", "paper a_hat 유지 시 보수 기준"],
        ["P13e", "goal21/fourbar_honest_canonical.json", "공식 canonical — 중력-벤치 확인 후 교체 결정"],
    ]),
])

# 부모 페이지에 추록 안내
append(root, [
    callout("🔧", rt("추록 (같은 날 저녁): ", bold=True),
            rt("⑨ 구조 감사와 P16 — \"동역학에 남은 게 없나?\" 감사에서 springref(역대 미검증 1-D)가 발견되어 "
               "새 최강 후보 P16이 나왔다. 정적 편향 −80%, 폐루프 누적 P13h 1.00 → P16 ≈0.88. "
               "레일 stick-slip은 시험 후 기각. 상세는 ⑨ 차일드 페이지.")),
])
print("PART3 DONE p9=", p9)
