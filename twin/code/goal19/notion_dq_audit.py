# -*- coding: utf-8 -*-
"""Append dq-focused audit (심화 4) to the explainer page."""
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
    h2("심화 4. dq(관절 속도) 중심 재분석 — 어긋나는 것은 오직 'whip의 진폭'이다 (07-06 추가)"),
    quote("용어 정리 | **게인이 세다/강하다**: kp·kd 값이 크다 = 오차에 강하게 반응한다 (예: kp합 650은 120보다 '센' 게인). "
          "**세션 계단(step)**: 한 실험 세션 안에서 어느 시점 이후 모든 trial의 성적이 계단처럼 뚝 떨어지는 현상 "
          "(0424: 18:17의 3번째 trial까지 좋다가 18:40의 4번째부터 일제히 하락). "
          "**whip**: 이륙 직전 무릎이 채찍처럼 급가속하는 속도 스파이크 — 점프 높이를 결정하는 핵심 순간. "
          "**peak 비율**: sim의 whip 최고 속도 ÷ 실측 whip 최고 속도 (1.0이면 완벽). "
          "**파형 상관**: 진폭을 무시하고 모양만 비교하는 상관계수 (1.0이면 모양 동일)."),
    h3("결과: 모양·타이밍은 전 날짜 정답, 진폭만 어긋난다"),
    table_block(
        ["날짜", "dq2 RMSE [rad/s]", "whip peak 비율 (sim/real)", "peak 타이밍 오차", "파형 상관"],
        [["0602", "1.41 ± 0.56", "0.93 ± 0.12", "4 ± 7 ms", "0.988"],
         ["0424", "2.78 ± 1.20", "0.69 ± 0.17 (계단 후 0.56~0.62)", "0 ± 1 ms", "0.979"],
         ["0324", "4.07 ± 2.55", "1.51 ± 0.46 (P100은 0.95)", "−2 ± 3 ms", "0.982"],
         ["0421", "16.6 ± 4.0", "**3.54 ± 0.49**", "−10 ± 8 ms", "0.958"]]),
    para("세 가지가 한눈에 보입니다. ① **파형 상관 0.96~0.99, 타이밍 오차 ≤14ms** — 트윈은 dq의 모양과 타이밍을 "
         "전 날짜에서 맞춥니다. ② 어긋나는 것은 **whip 진폭 하나**입니다. ③ 그리고 진폭 오차의 **부호가 전송 버그와 "
         "정확히 갈립니다**: 버그 날짜(0421·0324 저게인)는 sim이 **과대 whip**(최대 4.3배!), 정상 날짜의 강성 trial은 "
         "**과소 whip**(0.56~0.89)."),
])
batches.append([upload(FIG / "fig11_dq_waves.png"),
                para("거의 같은 게인(kp≈90)의 4개 날짜 dq 파형. 0421만 sim(파랑)이 실측(주황)의 3.4배로 튀고, "
                     "나머지는 겹칩니다 — 0424 계단 전 trial과 0602는 사실상 완벽.")])
batches.append([
    h3("부호까지 설명되는 메커니즘 — '얼려진 kd'의 두 얼굴"),
    para("**버그 날짜(dq_des=0)**: 실 로봇에서 kd는 whip을 **제동**했습니다(−kd·dq). 측정 τ에는 '실제 발생한 만큼의' "
         "제동만 담겨 있으므로, replay에서 sim이 조금이라도 더 빨리 휘두르기 시작하면 그에 상응하는 추가 제동이 "
         "없습니다 → 폭주 → **과대 whip** (0421 P90: 3.43배). "
         "**정상 날짜(dq_des 전송)**: 계획된 whip 속도를 향해 kd가 오히려 **밀어주는** 힘이었고, sim이 뒤처지는 순간 "
         "실제라면 더 밀어줬을 힘이 replay에는 없습니다 → **과소 whip** (0424 계단 후: 0.56~0.62). "
         "같은 '피드백 동결' 원리가 kd의 역할에 따라 정반대 부호로 나타나는 것 — 심화 2의 M(에너지), 여기의 "
         "peak 비율이 전부 이 하나의 원리로 정렬됩니다."),
    h3("요청하신 페어 분석 완성판 (q와 dq 함께)"),
    para("**페어 유형 A — 같은 궤적·같은 게인·다른 전송** (정확히 일치하는 페어 2개 존재):"),
    table_block(
        ["페어", "q2 RMSE", "dq2 RMSE", "whip peak 비율"],
        [["0421 P60_D0.75_P60_D2 (버그)", "63.7°", "20.2", "4.34"],
         ["0424 60_0.75_60_2 (정상)", "4.2°", "0.84", "0.88"],
         ["0421 P90_D0.75_P90_D2 (버그)", "46.6°", "15.8", "3.43"],
         ["0424 90_0.75_90_2 (정상)", "0.8°", "0.63", "1.08"]]),
    para("전송 버그 하나가 q는 15배, **dq는 24~25배** 벌립니다 — dq가 버그 효과에 훨씬 민감한 지표라는 사용자 직관이 맞습니다."),
    para("**페어 유형 B — 같은 게인·다른 궤적·다른 세션** (0424 vs 0602, dq2 RMSE): "
         "60_0.75 → 0.84 vs 1.54 (0424 승) · 90_0.75 → 0.63 vs 1.18 (0424 승) · 60_1.5 → 2.11 vs 0.75 · "
         "120_2 → 3.64 vs 1.20 · 150_2.2_250_3 → 3.24 vs 1.27 · 150_500 → 3.57 vs 2.56. "
         "계단 전 0424는 같은 게인의 0602보다 **더 잘** 맞고, 계단 후는 2~3배 나쁩니다 — q에서 본 세션 계단이 dq에서도 동일."),
    para("**페어 유형 C — 같은 궤적·같은 게인·같은 전송·다른 세션**: 데이터에 존재하지 않습니다 (0421/0424는 전송이, "
         "0424/0602는 궤적이 다름). **다음 세션에서 과거 config 한 개(예: 90_0.75_90_2 + 0602 궤적)를 재실행**하면 "
         "이 빈 칸이 닫히고 세션 요인의 크기를 순수하게 잴 수 있습니다 — 체크리스트에 추가."),
    quote("종합 | dq 렌즈의 수확: ① 트윈의 dq는 모양·타이밍 완벽, 진폭만 오차 ② 진폭 오차의 부호가 dq_des 전송 여부로 "
          "갈림(버그=과대, 정상 강성=과소) = 피드백 동결 원리의 직접 증거 ③ whip peak 비율이 h 정확도의 예측자 "
          "(0424 계단 후 0.6 → h_ratio 0.82~0.87 / 0602 0.9 → 0.93~0.95) ④ 버그 감지에는 dq가 q보다 민감(24배 vs 15배)."),
])

for i, b in enumerate(batches):
    append(b)
    print(f"batch {i+1}/{len(batches)} ok ({len(b)} blocks)")
print("done")
