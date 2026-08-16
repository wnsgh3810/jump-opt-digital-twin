# -*- coding: utf-8 -*-
"""Append 심화 5 (user's torque/tracking hypothesis, largely confirmed) to explainer page."""
import requests, time
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
PAGE = "395ab81d25508189b828d7c107d06f1b"
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/date_diag")


def rt(text):
    out = []
    for i, seg in enumerate(text.split("**")):
        if seg:
            out.append({"type": "text", "text": {"content": seg},
                        "annotations": {"bold": i % 2 == 1}})
    return out


def h2(t):
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt(t)}}


def h3(t):
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}


def para(t):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(t)}}


def quote(t):
    return {"object": "block", "type": "quote", "quote": {"rich_text": rt(t)}}


def bullet(t):
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": rt(t)}}


def table_block(header, rows):
    def row(cells):
        return {"object": "block", "type": "table_row",
                "table_row": {"cells": [rt(c) for c in cells]}}
    return {"object": "block", "type": "table",
            "table": {"table_width": len(header), "has_column_header": True,
                      "children": [row(header)] + [row(r) for r in rows]}}


def upload(png):
    r = requests.post("https://api.notion.com/v1/file_uploads",
                      headers={**H, "Content-Type": "application/json"}, json={})
    r.raise_for_status()
    uid, url = r.json()["id"], r.json()["upload_url"]
    with open(png, "rb") as f:
        rr = requests.post(url, headers=H, files={"file": (png.name, f, "image/png")})
        rr.raise_for_status()
    return {"object": "block", "type": "image",
            "image": {"type": "file_upload", "file_upload": {"id": uid}}}


def append(blocks):
    r = requests.patch(f"https://api.notion.com/v1/blocks/{PAGE}/children",
                       headers={**H, "Content-Type": "application/json"},
                       json={"children": blocks})
    if r.status_code != 200:
        raise RuntimeError(r.text[:400])
    time.sleep(0.4)


batches = []
batches.append([
    h2("심화 5. 사용자 가설의 검증 — \"게인↑ → 추종 좋아짐 → 토크 줄어듦 → 적합도 하락\" (07-06 추가)"),
    para("사용자 제안: 0424의 dq 적합도 하락은 세션 문제가 아니라, **게인을 올리면 지령과의 위치·속도 오차가 줄어 "
         "PD가 만들어내는 토크 자체가 작아지고**(과거 실험은 순수 PD — τ_ff 없음 — 이므로 τ는 100% 오차×게인), "
         "**작은 토크로 움직인 trial은 트윈이 재현하기 어려운 것 아니냐**는 것. 그리고 \"낮은(깊은) 자세에서 "
         "q_des와 일치하게 움직일수록 에러가 벌어지는 것 같다\"는 관찰. — 전부 수치로 검증했습니다."),
    quote("용어 | **W+ (입력 일, work)**: 스탠스 동안 모터가 다리에 실제로 넣어준 에너지 = ∫(τ×dq의 양수 부분)dt [J]. "
          "**추종 오차(tracking error)**: 실측 각도와 지령 각도의 차이 RMSE — 작을수록 로봇이 지령을 잘 따라간 것. "
          "**ID 잔차**: 트윈의 역동역학과 실제 로봇의 차이 — 대략 0.5~1 Nm급의 고정 크기 오차 (마찰·토크 변환·4절링크 손실 등)."),
    h3("검증 결과 — 세 단계 모두 사실"),
    table_block(
        ["주장", "0424", "0602", "판정"],
        [["게인↑ → 추종 오차↓", "corr −0.89 (17.3°→3.5°)", "corr −0.91 (20.1°→4.9°)", "✓ 확인"],
         ["게인↑ → 토크·일↓", "peak −0.76 · W+ −0.84 (25.8→18.7 J)", "peak −0.54 · W+ −0.54", "✓ 확인 (0424에서 강함)"],
         ["토크·일↓ → replay dq 적합도↓", "—", "—", "✓ 정상 15 trials: corr(W+, dq오차) = **−0.86 (전 가설 중 최강)**"],
         ["잘 추종할수록 replay 나빠짐", "—", "—", "✓ corr(추종오차, dq오차) = **−0.72**"]]),
])
batches.append([upload(FIG / "fig12_work_vs_dq.png"),
                para("왼쪽: 입력 일이 적을수록 dq 재현이 나빠짐 (0424 강성 trial들은 0602가 방문하지 않는 저일 영역 "
                     "18.7~23 J를 방문). 오른쪽: 추종이 좋을수록 재현이 나빠짐 — 사용자 관찰의 정량 확인.")])
batches.append([
    h3("이것이 세션 미스터리를 대부분 대체합니다"),
    para("0424의 '세션 계단'과 '일(work) 하락'은 정확히 같은 분할입니다 (게인을 시간순으로 올렸으므로 시간=게인=일이 "
         "완전히 얽힘). 그런데 **일(W+)을 축으로 놓으면 0424와 0602가 상당 부분 하나의 곡선 위에 올라갑니다**: "
         "W+ ≈ 23 J에서 0424 120_2(3.64) vs 0602 150_500_5(2.56)로 잔차가 1.4배 수준으로 줄어듭니다 — "
         "원래 날짜 간 격차(2~3배)의 대부분이 '저일 영역 방문 여부'로 설명된다는 뜻입니다. "
         "즉 **미스터리한 세션 변화 없이도 사용자의 물리적 메커니즘만으로 0424 패턴의 대부분이 설명됩니다** "
         "(잔여 1.4배가 세션 요인인지 2차 요인인지는 유형 C 재실행 실험이 확정)."),
    h3("왜 토크가 작으면 재현이 어려운가 — 모델이 못 담는 것의 정체"),
    para("트윈의 역동역학에는 크기가 대략 **고정된(0.5~1 Nm급) 잔차**가 남아 있습니다 (마찰 모델 오차, a_hat 토크 변환 "
         "오차, 4절링크 관절 손실 등). 구동 토크가 18 Nm일 때 이 잔차는 3~5% 왜곡이지만, 고게인 trial처럼 총 일이 "
         "25.8→18.7 J로 줄면 같은 잔차가 whip 속도에서 차지하는 비중이 커집니다 — 그래서 whip peak가 "
         "0.88~1.08(저게인)에서 0.56~0.62(고게인)로 무너지는 것입니다. "
         "그리고 더 미묘한 층위: **추종이 완벽할수록 τ는 '지령 궤적을 강제하기 위해 모델-실물 불일치를 실시간으로 "
         "메꾼 보상 신호'가 됩니다.** 그 신호를 피드백 없이 재생하면 트윈은 보상의 대상이 달라서 지령도 실측도 아닌 "
         "제3의 궤적으로 흘러갑니다. 반대로 저게인 trial은 다리가 자연 동역학에 가깝게 움직였고, 트윈은 바로 그 "
         "자연 동역학(질량·마찰)을 잘 학습했으므로 재현이 쉽습니다. — **\"낮은 자세에서 지령과 일치하게 움직일수록 "
         "에러가 벌어진다\"는 관찰의 정체가 이것입니다** (corr −0.72)."),
    h3("정직한 한계 — 0324는 이 곡선을 따르지 않는다"),
    para("0324(버그 날짜)를 포함하면 W+ 상관이 −0.86에서 −0.61로 약해집니다: 0324 안에서는 일이 가장 적은 "
         "P100(18.1 J)이 오히려 가장 잘 맞습니다(1.03). 버그 날짜는 '얼려진 제동'의 왜곡이 지배해서 정상 날짜의 "
         "저일 메커니즘과 다른 규칙을 따릅니다 — W+ 축은 **정상 전송 날짜(=배포 조건)에 한정된 법칙**으로 기록합니다."),
    h3("함의"),
    bullet("**배포에 유리한 결론**: 배포는 τ_ff가 일을 공급하고 PD는 잔차만 보정 — 저일·순수보상 신호 문제가 "
           "구조적으로 발생하지 않는 조건. NLP 최적 궤적은 W+가 크다(τ 예산을 다 씀)."),
    bullet("**모델 개선의 표적이 좁혀짐**: 다음에 줄여야 할 것은 '0.5~1 Nm급 고정 ID 잔차' — 저속 램프 breakaway "
           "실험(마찰), 모터 벤치(a_hat)가 정확히 이걸 겨냥한다."),
    bullet("**세션 미스터리 축소**: 0424의 계단은 대부분 저일 영역 진입으로 설명 — 남은 1.4배 잔차의 확정은 "
           "다음 세션의 동일 config 재실행(유형 C)으로."),
    quote("한 줄 요약 | 사용자 가설 채택: 순수 PD 실험에서 게인을 올리면 추종은 좋아지지만 τ가 '모델 불일치 보상 신호'가 "
          "되며 일이 줄고, 그런 신호일수록 open-loop 재생이 어렵다 — 정상 날짜 15 trial에서 corr −0.86으로 "
          "이 조사의 모든 가설 중 가장 강한 설명력."),
])

for i, b in enumerate(batches):
    append(b)
    print(f"batch {i+1}/{len(batches)} ok ({len(b)} blocks)")
print("done")
