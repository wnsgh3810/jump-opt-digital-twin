# -*- coding: utf-8 -*-
"""Append the model-free B/R/M audit section to the explainer page."""
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
    h2("심화 2. 모델을 빼고 데이터만 감사(audit)하기 — 남은 두 변칙의 해체 (07-06 추가)"),
    para("앞의 인과 사슬이 설명 못 하던 두 변칙이 남아 있었습니다: (a) **0324는 최악의 조건(버그+최심 신전+거친 지령)인데 "
         "왜 h_ratio가 0.925±0.005로 가장 일관되게 좋아 보이나?** (b) **0424는 최선의 조건(정상 전송)인데 왜 가장 나쁜가?** "
         "이를 풀기 위해 트윈(모델)을 완전히 배제하고 측정 데이터끼리의 일관성만 감사했습니다."),
    quote("용어 | h_kin (관절 탄도높이): 측정된 관절각·관절속도만으로 (링크 길이 = 실측 CAD) 이륙 순간 몸통의 높이와 "
          "수직속도를 계산하고, 포물선 공식 h = h₀ + v²/2g 로 예상한 최고점 — 카메라도 트윈도 안 쓰는 순수 측정 기반 값. "
          "B = h_kin/h_camera: 관절 데이터와 카메라 눈금의 일치도(측정 체인 감사). "
          "R = h_sim/h_camera: 기존에 쓰던 잣대. "
          "M = h_sim/h_kin = R/B: 트윈이 관절 데이터에 담긴 에너지를 얼마나 재현하는가 = 진짜 모델 충실도."),
    h3("결과 (24 trials 전수)"),
    table_block(
        ["날짜", "B = 관절/카메라", "R = sim/카메라 (기존)", "M = sim/관절 (모델 충실도)"],
        [["0324", "1.137 ± 0.008", "0.925 ± 0.005", "0.814 ± 0.010"],
         ["0421", "1.113 ± 0.028", "1.155 ± 0.038", "1.038 ± 0.056"],
         ["0424", "1.168 ± 0.015", "0.875 ± 0.053", "0.750 ± 0.051"],
         ["0602", "1.093 ± 0.057", "0.940 ± 0.014", "0.862 ± 0.045"]]),
])
batches.append([upload(FIG / "fig9_brm_audit.png"),
                para("세 잣대의 분해. 핵심: R(가운데)만 보면 날짜별 이야기가 왜곡됩니다 — R은 B와 M의 곱이라서.")])
batches.append([
    h3("변칙 (a) 해체 — 0324의 '좋음'은 상쇄 착시였다"),
    para("0324의 R=0.925는 **B(1.137) × M(0.814)의 곱**입니다. 즉 트윈은 관절 데이터 에너지의 81%만 재현하는데(0424와 "
         "비슷한 수준), 카메라 눈금이 관절 대비 낮게 앉아 있어서 나눗셈이 좋아 보였던 것뿐입니다. 진짜 모델 충실도(M) "
         "기준으로 0324는 '나쁜 조건인데 좋은' 예외가 아니라 4월 형제(0424)와 비슷한 평범한 수준 — 변칙 해소. "
         "(0324의 Real Data.txt에 있는 사용자 파이프라인의 독립 계산도 같은 방향: 운동학 예상 0.769~0.861 vs 카메라 "
         "0.74~0.80, 즉 B≈1.04~1.08 — 우리 방법과 교차 확인됨.)"),
    h3("변칙 (b) 재조명 — 0424는 M에서도 진짜 열세지만, 폭은 줄어든다"),
    para("M 기준 0424(0.750)는 0602(0.862)보다 여전히 ~0.11 낮습니다 — 4월 세션 요인은 카메라와 무관하게 실재합니다. "
         "다만 R에서 보이던 '0424 유독 나쁨'의 일부는 0424의 B가 가장 크다는(1.168) 사실, 즉 카메라-관절 불일치가 "
         "가장 큰 날짜라는 데서도 왔습니다. 그리고 0421의 미스터리한 overshoot(R=1.155)는 **M≈1.04로 해체**됩니다: "
         "트윈은 0421의 관절 데이터를 거의 완벽하게 재생하고 있고, 카메라 눈금만 관절 대비 낮았던 것입니다 "
         "(단 0421은 피드백 동결 replay라 M≈1을 모델 완벽의 증거로 읽어선 안 됨 — 두 왜곡의 부분 상쇄 가능)."),
    h3("★ 신발견 — 모든 날짜에서 B > 1: 관절은 카메라보다 9~17% 높이 '약속'한다"),
    para("이건 특정 날짜의 문제가 아니라 **보편 현상**입니다. 후보 원인 셋: ① 카메라가 apex를 낮게 읽음, "
         "② FK 탄도 계산의 과대평가(이륙 직전 실린더 발의 rolling/미끄럼이 겉보기 몸통속도를 부풀림), "
         "③ 이륙 순간의 실제 에너지 손실(구조 유연성·whip이 관절 운동 에너지를 몸통 상승으로 다 전달 못함). "
         "현재 데이터로는 셋을 못 가릅니다. 종전에 '점프 under-jump는 구조적'이라고 뭉뚱그렸던 gap이 실은 "
         "**두 개의 서로 다른 gap(M<1: 트윈 vs 관절, B>1: 관절 vs 카메라)의 합성**이었다는 것이 이번 감사의 가장 큰 수확입니다."),
    h3("통제 비교 보너스 — 같은 지령·같은 게인·다른 전송(0421 P60 vs 0424 60_0.75)"),
    para("유일하게 게인까지 완전히 일치하는 페어: 지령도 동일, 다른 것은 dq_des 전송 버그 유무(+세션)뿐. "
         "실 로봇 도달 h_kin 0.918(버그, 제동 걸림) vs 1.033(정상) — 버그가 실제 점프를 깎았음이 보이고, "
         "replay M은 1.138(버그, 동결 피드백 왜곡) vs 0.828(정상) — 같은 물리 모델이 τ의 성분에 따라 "
         "정반대 방향으로 어긋나는 것을 한 쌍으로 보여줍니다."),
    h3("실무 함의 (체크리스트 추가분)"),
    bullet("**다음 세션에서 카메라-관절 교차 검증 1회**: 점프 하나를 카메라 + 고속 촬영(또는 자로 잰 apex)으로 이중 측정해 "
           "B>1의 원인(카메라냐 역학이냐)을 확정할 것 — 배포 기대치(트윈 예측 0.95~0.97m)를 카메라 눈금으로 읽을지 "
           "실제 물리 높이로 읽을지가 여기 달려 있음."),
    bullet("날짜 비교·모델 평가에는 앞으로 R 대신 **M(=sim/관절)과 B(=관절/카메라)를 분리해서 볼 것** — R 하나로 보면 "
           "0324처럼 상쇄 착시가 생긴다."),
    bullet("0424의 M 열세(~0.11)는 세션 요인으로 잔존 — '강한 점프 몇 회마다 재확인' 프로토콜의 근거가 하나 더 늘었다."),
])

for i, b in enumerate(batches):
    append(b)
    print(f"batch {i+1}/{len(batches)} ok ({len(b)} blocks)")

r = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100", headers=H)
kinds = [b["type"] for b in r.json()["results"]]
print("TOTAL:", len(kinds), "| images:", kinds.count("image"), "| tables:", kinds.count("table"))
