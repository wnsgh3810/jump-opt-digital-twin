# -*- coding: utf-8 -*-
"""Append the multi-dimensional reference-difficulty analysis to the explainer page."""
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
    h2("심화 분석. '더 어려운 지령'의 정체 — 끝점 하나가 아니라 다차원으로 검증 (07-06 추가)"),
    para("사용자 질문: \"어려운 지령이라는 게 마지막 각도 차이뿐이야? 가속도·지터 등 여러 면으로 보면 어느 쪽이 진짜 어려운가?\" "
         "— 지령 궤적을 5개 차원으로 분해해 전부 측정했습니다."),
    quote("용어 | 가속도(a_max): 지령 속도가 얼마나 급히 변하는가(모터가 내야 할 힘의 세기와 직결). "
          "저크(jerk): 가속도의 변화율 — 궤적의 '거칠기'. 값이 클수록 덜컹거리는 계획. "
          "계단성(step): 한 샘플(2ms)에 지령 각도가 몇 도씩 점프하는가 — 계단식으로 만들어진 궤적인지. "
          "지터(HF%): 지령에 20Hz 이상 고주파 성분이 섞여 있는 비율. "
          "일관성(|v−dq/dt|): 지령 속도 컬럼이 지령 각도의 미분과 일치하는가 — 안 맞으면 kp항과 kd항이 서로 다른 궤적을 좇아 내부 충돌."),
    h3("측정 결과 (무릎 지령, 대표 trial — 날짜 내 지령은 완전 동일함을 별도 확인)"),
    table_block(
        ["날짜", "구간 [s]", "peak 속도 [rad/s]", "peak 가속도 [rad/s²]", "저크 RMS", "최대 스텝 [deg]", "지터 HF%", "일관성 오차 [rad/s]"],
        [["0324", "0.31", "26.5", "522", "15,235 (최악)", "4.73 (최악)", "0", "0.82 (최악)"],
         ["0421", "0.27", "21.6", "388", "12,161", "2.46", "0", "0.07"],
         ["0424", "0.27", "21.6", "388", "12,161", "2.46", "0", "0.07"],
         ["0602", "0.25", "27.2 (최고)", "649 (최고)", "5,747 (최소)", "3.10", "0", "0.03 (최선)"]]),
    para("hip 지령도 같은 패턴입니다 (0602: 가속도 최고 325, 저크 최소 2,918 / 0324: 저크 최악 7,617)."),
])
batches.append([upload(FIG / "fig8_ref_kinematics.png"),
                para("세 날짜의 무릎 지령 운동학. 가운데·오른쪽 패널에서 0602(가장 잘 맞는 날짜)의 지령이 "
                     "속도·가속도 peak가 가장 높다는 것 — 즉 가장 '공격적'이라는 것 — 이 보입니다.")])
batches.append([
    h3("발견 1 — 반전: 0602 지령이 사실 가장 '공격적'이다"),
    para("peak 속도(27.2 rad/s)와 peak 가속도(649 rad/s²) 모두 **0602가 최고**입니다. 0424(21.6 / 388)보다 "
         "속도 26%, 가속도 67% 더 셉니다. 그런데도 0602가 가장 잘 맞습니다. "
         "**따라서 '공격적인 지령(빠르고 센 동작)'은 replay 정확도를 해치는 요인이 아닙니다.** "
         "트윈은 빠르고 강한 동작 자체는 잘 재현합니다 — 고토크 영역이 오히려 모델이 가장 정확한 영역이라는 "
         "기존 발견과도 일치합니다."),
    h3("발견 2 — '어려움'의 실체는 목적지(신전 깊이)였다"),
    para("0424 지령이 0602보다 어려운 점은 속도도 가속도도 아니고 딱 하나, **끝점**입니다: 무릎을 −36°까지 "
         "(0602는 −45°) 펴라고 시켜서, 다리를 특이점 근처의 취약 영역으로 데려갑니다. "
         "즉 '어려운 지령' = '공격적인 지령'이 아니라 **'트윈이 취약한 상태공간으로 보내는 지령'**입니다. "
         "이 구분이 이번 분석의 핵심 수확입니다."),
    h3("발견 3 — 0324 지령은 품질 자체가 낮았다"),
    para("0324 지령은 세 지표에서 최악입니다: 저크 15,235(0602의 2.7배), 한 샘플에 **4.7°씩 점프하는 계단식** "
         "각도 지령, 그리고 지령 속도 컬럼이 지령 각도의 미분과 **0.82 rad/s나 어긋나는 내부 비일관성** "
         "(0602는 0.03). 3월엔 궤적 생성 파이프라인 자체가 거칠었다는 뜻입니다. "
         "(다만 3월엔 dq_des가 버그로 전송도 안 됐으므로, 비일관성의 실전 영향은 kd항이 아니라 "
         "kp항이 계단 지령을 좇으며 생기는 토크 거칠기로 나타났을 것입니다.)"),
    h3("발견 4 — 보너스: 0421과 0424는 지령이 완전히 동일하다"),
    para("두 날짜의 지령은 모든 지표에서 소수점까지 일치합니다(같은 계획 파일). 그러면 0421과 0424의 차이는 "
         "**오직 dq_des 전송 버그 유무(+게인·세션)**뿐 — 같은 안무를 버그 있는 몸(0421)과 없는 몸(0424)으로 "
         "춘 자연 실험입니다. 0421만 계통적 overshoot(1.155)를 보이는 것이 버그(⑤ 피드백 함량 134%)의 "
         "효과를 통제된 조건에서 재확인해 줍니다."),
    quote("결론 | '어려운 지령'을 다차원으로 재정의: 공격성(속도·가속도)은 무해 — 0602가 가장 공격적인데 가장 정확. "
          "해로운 것은 ① 취약 영역으로 보내는 끝점(0424: −36°), ② 지령 품질(0324: 계단+비일관), "
          "③ 전송 버그(0421·0324: dq_des=0). 세 가지가 각각 다른 날짜의 '나쁨'을 만든다."),
])

for i, b in enumerate(batches):
    append(b)
    print(f"batch {i+1}/{len(batches)} ok ({len(b)} blocks)")

r = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100", headers=H)
kinds = [b["type"] for b in r.json()["results"]]
print("TOTAL:", len(kinds), "| images:", kinds.count("image"), "| tables:", kinds.count("table"))
