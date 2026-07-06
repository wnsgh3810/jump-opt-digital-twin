# -*- coding: utf-8 -*-
"""Append the full-replay trace audit (redo per user) to the explainer page."""
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
    h2("심화 3. 그래프에서 눈으로 보는 그 양(전체재생 트레이스)의 전수 정량화 — 재분석 (07-06)"),
    para("사용자 관찰: \"그래프에서 0324는 q·dq가 굉장히 잘 맞아 보이고, 0421은 아예 안 맞고, 0424는 편차가 크고, "
         "0602는 잘 맞는다.\" — 갤러리 그래프가 보여주는 양(전체재생 q/dq 트레이스, per-date offset 보정 적용)을 "
         "24개 trial 전수로 정량화해 이 관찰을 검증하고, 남았던 설명 공백을 다시 팠습니다."),
    h3("결과: 사용자의 눈이 정확했다"),
    table_block(
        ["날짜", "전체재생 q2 RMSE [deg]", "dq2 RMSE [rad/s]", "trial 범위", "사용자 관찰"],
        [["0602", "3.8 ± 2.0", "1.41", "1.9 ~ 7.2°", "잘 맞음 ✓"],
         ["0424", "10.1 ± 4.5", "2.78", "0.8 ~ 15.2°", "편차 큼 ✓ (최고와 최악이 19배)"],
         ["0324", "11.9 ± 6.9", "4.07", "4.0 ~ 20.8°", "잘 맞는 trial 있음 ✓ (P100_D3=4.0°, 0602급)"],
         ["0421", "50.8 ± 14.8", "16.6", "29 ~ 75°", "아예 안 맞음 ✓"]]),
    para("특히 0324의 P100_D3는 4.0°/1.03으로 **0602 평균과 동급** — '0324가 잘 맞아 보인다'는 관찰은 이 trial에서 "
         "정확합니다. 이전 서술에서 '0324 트레이스 나쁨'이라 뭉뚱그린 것은 창 점수·offset 논의와 뒤섞인 오류였음을 정정합니다."),
])
batches.append([upload(FIG / "fig10_trace_audit.png"),
                para("왼쪽: trial별 트레이스 오차(0424는 실험 순서 정렬 — 3번째까지 0602급, 4번째부터 계단). "
                     "오른쪽: 토크 거칠기 가설의 기각 증거.")])
batches.append([
    h3("기각 완료 — '거칠기' 계열 지표는 전부 무관"),
    para("측정 토크의 거칠기(dτ/dt RMS)를 trial별로 재서 트레이스 오차와 상관을 보면 **−0.45 (0424 내부 −0.65)** — "
         "부호가 반대입니다. 가장 거친 토크(0602, 633±144 Nm/s)가 가장 잘 맞고, 가장 부드러운 토크(0324, 306)가 "
         "중간 수준입니다. 지령 저크·계단 크기(심화 1)에 이어 토크 거칠기까지 — **'신호가 거칠어서 안 맞는다'는 "
         "계열의 설명은 세 번 시험해서 세 번 다 기각**되었습니다. 500Hz 로깅과 트윈의 적분기는 이 정도 거칠기를 "
         "전혀 문제 삼지 않습니다."),
    h3("남는 최종 구조 — 트레이스 품질의 3요인"),
    bullet("**1위 요인 — dq_des 버그 × 높은 게인 (0421의 파국)**: 통제 페어(지령·게인 완전 동일)인 "
           "0421 P60_D0.75_P60_D2 (63.7°) vs 0424 60_0.75_60_2 (4.2°) — **15배 차이**. 같은 안무·같은 게인에서 "
           "dq_des 전송 하나가 갈랐다. 버그+고게인 조합은 τ를 피드백 덩어리(91~214%)로 만들고, 얼려진 피드백은 "
           "재생에서 형태를 파괴한다(에너지는 보존: M≈1.04)."),
    bullet("**2위 요인 — 세션 상태 (0424의 편차)**: 첫 3개 trial(17:31~18:17)은 0.8~8.3°로 0602급이거나 더 좋고 "
           "(90_0.75는 0.8°로 전체 24개 중 최고!), 18:40부터 10.8~15.2°로 계단. 같은 게인 페어로 0602와 비교해도 "
           "계단 전은 대등, 후는 2~3배 열세 — 세션 중 변화가 눈에 보이는 잣대에서도 확정."),
    bullet("**3위 요인 — 낮은 토크 권위 (0324 내부 기울기)**: P40(20.8°) → P60(11.1°) → P100(4.0°), 게인·토크가 "
           "클수록 좋아짐. 토크가 작으면 미모델 효과(마찰 밴드 등)가 상대적으로 커져 재생이 표류 — 단 n=3이라 "
           "확정보다는 경향. 0324는 버그 날짜인데도 게인이 낮아(kp 40~100) 절대 피드백 토크가 작았고, "
           "그래서 0421 같은 파국을 피했다."),
    h3("사용자 관찰 검증 — \"0424는 PD 게인이 커질수록 q·dq가 안 맞는다\""),
    para("관찰은 사실이고, 두 겹으로 분해됩니다. **① 진짜 게인 효과가 존재합니다** — 깨끗한 세션인 0602에서 "
         "corr(게인합, 트레이스 오차) = **0.86**으로 선명하게 보입니다 (soft 1.9~2.4° → stiff 3.9~7.2°). "
         "단 메커니즘은 피드백 함량이 아니라(corr 0.25, 약함) **신전 깊이**입니다(corr 0.79): 게인이 세면 "
         "깊은 목표(−45°)를 끝까지 추종해 −33°까지 파고들고, 그 영역이 증폭기라서 오차가 2~3배로 커집니다. "
         "크기는 2°→7° 수준의 완만한 효과입니다."),
    para("**② 0424에서 크게 보이는 것은 게인이 아니라 세션 계단입니다.** 0424 내부 게인 상관 0.58은 착시로, "
         "상세를 보면 kp합 120 이상 trial들(10.8~15.2°)이 전부 18:40 이후이고, 그 강성군 내부에서는 게인을 "
         "120에서 650까지 올려도 오차가 평평합니다(12.7→13.6°, 추가 추세 없음). 반면 계단 이전의 90_0.75(kp합 180)는 "
         "0.8°로 24개 trial 중 최고입니다. 즉 0424의 '게인 효과'의 대부분은 시간 효과입니다."),
    para("보너스 기각: 정상 전송 15개 trial에서 피드백 함량 vs 트레이스 오차 상관 = −0.32 (부호 반대) — "
         "피드백 함량은 날짜 수준에서 0421의 파국을 가르는 축이지, 정상 날짜 안에서 trial별 예측자는 아닙니다."),
    quote("정리 | 그래프에서 보이는 날짜별 인상의 최종 인과: 0602(깨끗한 세션·정상 전송, 게인↑=신전↑로 완만한 열화) > "
          "0424(세션 전반=0602급, 18:40 이후 계단 — 게인 아님) ≈ 0324(게인 높은 trial은 0602급, 낮은 trial은 표류) >> "
          "0421(버그×고게인 파국, 단 에너지는 정상 M≈1). 거칠기 계열(저크·계단·dτ/dt)은 3연속 기각 — 범인이 아니다."),
])

for i, b in enumerate(batches):
    append(b)
    print(f"batch {i+1}/{len(batches)} ok ({len(b)} blocks)")

r = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100", headers=H)
n_img = 0; n_tab = 0; total = 0; cur = r.json()
while True:
    total += len(cur["results"])
    n_img += sum(1 for b in cur["results"] if b["type"] == "image")
    n_tab += sum(1 for b in cur["results"] if b["type"] == "table")
    if not cur.get("has_more"):
        break
    cur = requests.get(f"https://api.notion.com/v1/blocks/{PAGE}/children?page_size=100&start_cursor={cur['next_cursor']}", headers=H).json()
print("TOTAL:", total, "| images:", n_img, "| tables:", n_tab)
