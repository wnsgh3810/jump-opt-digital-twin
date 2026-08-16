# -*- coding: utf-8 -*-
"""P18b 마라톤 노션 보고서 — 변속(0429) 오차 해결: 스프링의 정체와 클러치 프리로드."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import requests, time, json, mimetypes
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
DST = Path((LEGACY_ROOT + "/g22_cvt_0429_results"))


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status(); return r
    r.raise_for_status()


def rt(t, bold=False, code=False):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold: ann["bold"] = True
    if code: ann["code"] = True
    if ann: a["annotations"] = ann
    return a


def para(*r): return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}
def h1(t): return {"type": "heading_1", "heading_1": {"rich_text": [rt(t)]}}
def h2(t): return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}
def h3(t): return {"type": "heading_3", "heading_3": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(e, *r): return {"type": "callout", "callout": {"icon": {"emoji": e}, "rich_text": list(r)}}
def divider(): return {"type": "divider", "divider": {}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def img(path, caption=""):
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    fu = req("POST", "https://api.notion.com/v1/file_uploads", headers=HJ,
             json={"mode": "single_part", "filename": p.name}).json()
    req("POST", fu["upload_url"], headers=H, files={"file": (p.name, p.read_bytes(), mt)})
    st = req("GET", f"https://api.notion.com/v1/file_uploads/{fu['id']}", headers=H).json()
    assert st.get("status") == "uploaded", p.name
    b = {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": fu["id"]}}}
    if caption:
        b["image"]["caption"] = [rt(caption)]
    return b


root = req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
    "parent": {"page_id": GOAL22}, "icon": {"emoji": "🏃"},
    "properties": {"title": {"title": [rt("P18b 마라톤 — 변속(0429) 오차 해결: 스프링의 정체와 클러치 프리로드")]}}}).json()["id"]


def append(blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{root}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


B = [
    callout("🏃", rt("요청: ", bold=True),
            rt("\"변속 데이터(26.04.29, l_i=25.08mm)의 큰 오차를 해결하라 — 자율 자가 개선 루프 마라톤.\" "),
            rt("결과: Mode A 점수 244 → 75.8 (−69%), 점프 높이 갭 +10.7cm → +4.7cm, 평행사변형 세션 성능 동률 유지(G7 평균 1.00), "
               "CL held-out 오히려 개선(0.97). 그 과정에서 2년치 모델링의 미해결 퍼즐이었던 stiff_knee 스프링의 물리적 정체가 밝혀짐: "
               "①약한 무릎 유연성(0.40 Nm/rad, 무릎 힌지) + ②l_i=30mm 전용 클러치 프리로드 토크(~+2Nm). "
               "12회 반복, 침묵 실패 1회 정정, 기각 2축(l_i 캘리브레이션, stiction), 판별 실험 2종(정적 감사, CL 판별).", bold=True)),

    h1("0. 용어 정의"),
    table([
        ["용어", "정의"],
        ["Mode A", "측정 토크(a_hat 변환)를 sim에 그대로 주입해 궤적(q/dq/GRF/h)이 실측을 재현하는지 보는 개루프 검증. 모델 자체의 시험."],
        ["CL (폐루프)", "실험과 동일한 PD 게인·목표궤적으로 sim 로봇을 제어 — 배포 상황 재현. PD가 오차를 흡수하므로 Mode A보다 관대."],
        ["마라톤 score", "100(q1+q2 stance RMSE)+10(dq1+dq2)+300|Δh|+200|Δt_off|. stance=실측 GRF 이륙까지 (비행 오염 제거). 작을수록 좋음."],
        ["G7 심판", "평행사변형(l_i=30) 5세션의 Mode A 창(0.2s) 그룹점수 8종 (w_0421/0424/0602/0324/s2s + fs_0424/0602 + habs). P16 대비 비율로 표시."],
        ["CL 심판 (C/Cg)", "폐루프 τ-채널 심판. C=fit 세션 평균, Cg=held-out(0324) 게이트."],
        ["stiff_knee", "GOAL19에서 도입된 무릎 스프링 (P16: 1.33 Nm/rad, ref 2.07 rad, 크랭크 관절). 동적 −23.5% 기여로 채택됐던 축."],
        ["크랭크/전달비 r", "무릎 모터가 돌리는 길이 l_i 링크(베이스). r=무릎각속도/크랭크각속도. l_i=30이면 r≡1(평행사변형), 25.08이면 r=0.07~0.84 가변."],
        ["프리로드", "기구가 행정 한계에 눌려 있을 때 걸리는 사전 하중. 클러치 슬라이더가 l_i=30mm(행정 끝단)에서 받는 상시 토크로 추정."],
    ]),

    h1("1. 출발점 진단 — v1 실패의 3층 구조"),
    para(rt("P16 모델 그대로 돌린 v1(Mode A)은 q2 RMSE 0.46 rad, h +10.7cm 과대점프였다. 그림을 뜯어보니 실패는 3층:")),
    bullet(rt("① 초기 킥: ", bold=True), rt("t=0에서 유지토크(−3.5Nm)→측정토크(~0Nm) 계단 전환 → GRF 210N 스파이크. 20ms 블렌딩으로 해결(러너 v2).")),
    bullet(rt("② 중반 과속: ", bold=True), rt("같은 토크에서 sim이 더 빨리 폄 (이륙 0.155s vs 실측 0.19s, 크랭크 속도 77 vs 38 rad/s).")),
    bullet(rt("③ 사점 통과 아티팩트: ", bold=True), rt("이륙 후 크랭크가 폄 특이점을 뚫고 반대 조립 브랜치로 회전(−173°→+115°) — 실기 미도달 영역. stance 전용 지표로 오염 제거.")),
    callout("🔑", rt("결정적 단서 — 정적 평형 갭: ", bold=True),
            rt("모델은 크라우치 유지에 크랭크 −3.5Nm이 필요한데 실측은 ~0Nm. 크라우치가 전달비 특이점 근처(무릎토크의 1/15만 필요)라 "
               "이론상으로도 ~0이어야 한다. 즉 모델에 크랭크 쪽 가짜 정적 토크가 있다 → 크랭크 관절에 붙은 스프링이 용의자.")),

    h1("2. 스프링 배치의 축퇴 — 평행사변형은 구분할 수 없었다"),
    para(rt("평행사변형(l_i=l_o=30mm)에서는 크랭크각≡무릎각이므로, 스프링(또는 마찰)을 크랭크에 붙이든 무릎(종아리 힌지)에 붙이든 "
            "동역학이 수학적으로 동일하다. P16까지의 모든 데이터(5세션 31실험)로는 이 축을 원리적으로 구분할 수 없었고, "
            "l_i=25.08mm인 0429가 처음으로 축퇴를 깬다: 크랭크 크라우치 변형 0.97 rad vs 무릎 변형 0.46 rad — 배치에 따라 스프링 토크가 완전히 달라진다.")),
    table([
        ["0429 Mode A (10 trials 평균)", "score", "q2 RMSE [rad]", "dq2 [rad/s]", "h갭 [cm]", "유지토크 [Nm] (실측 +0.05)"],
        ["스프링@크랭크 (P16)", "243.7", "0.462", "13.1", "+10.7", "−3.24"],
        ["스프링@무릎(종아리)", "119.4", "0.158", "5.51", "+9.8", "+0.25"],
        ["스프링 제거", "66.6", "0.072", "2.95", "+1.9", "+0.17"],
    ]),
    para(rt("주의(정직): 첫 실험(iter1)에서 무릎 관절 XML 치환이 조용히 실패해 'calf 승리'로 오판했다 — 실제로는 '스프링 제거'의 승리였다. "
            "iter5에서 정정 (fitted damping 0.02309 문자열 불일치, 정규식+컴파일 검증으로 재발 방지).")),
    para(rt("한편 평행사변형 이중심판에서 스프링 제거는 재앙(w_s2s ×5, habs ×21, CL 발산) — GOAL19의 발견(스프링 실재)도 옳았다. "
            "→ 모순: 0429는 스프링을 거부하고, 30mm 세션들은 요구한다. 물리 스프링은 세션마다 생멸할 수 없다.")),

    h1("3. 판별 실험 ① — 정적 유지토크 감사"),
    para(rt("모든 세션의 '출발 전 정지 구간'에서 측정 유지토크 vs 모델 예측(스프링 유/무)을 비교했다. 정지 상태라 동역학이 없고 순수 정역학:")),
    table([
        ["세션 (같은 크라우치 자세)", "측정 무릎 유지토크", "모델 예측 (스프링 없음)", "해석"],
        ["jump_position_0421", "+5.3 ~ +5.8 Nm", "+5.3 ~ +6.1", "스프링 없음이 정답 (잔차 0.67)"],
        ["jump_0602", "+2.4 ~ +2.6 Nm", "+5.0 ~ +5.6", "~3Nm 부족 — 스프링(또는 무언가) 필요"],
        ["s2s_gnd_0319", "+2.9 ~ +3.7 Nm", "+3.9 ~ +4.0", "중간 (잔차 +0.56)"],
        ["0429 (CVT)", "~+0.05 Nm", "~+0.3 (특이점, ×1/15)", "스프링 없음"],
    ]),
    callout("💡", rt("같은 자세에서 세션마다 측정 유지토크가 3Nm씩 다르다. 스프링이 아니라 세션 의존적인 무언가다. "
                   "hip 채널 감사에서도 s2s만 +1.77Nm 잔차 — 채널·세션별로 다른 상수 성분. "
                   "(주의: 기어박스 stiction 밴드가 정적 판별력을 흐릴 수 있어 참고 증거로 강등, 최종 판정은 동적 심판.)")),

    h1("4. 기각된 가설들"),
    bullet(rt("l_i 캘리브레이션 (23.5/26.5/28mm 스캔): ", bold=True), rt("전부 악화 — 센서값 25.08mm 확정. 기하는 사용자 NLP(jump_results.xlsx)의 TR 1.2~15.0과 1e-16 일치로 교차검증.")),
    bullet(rt("stiction (fc_knee 0.1~1.5 스캔): ", bold=True), rt("s2s는 단조 개선되나 점프 전 그룹 단조 악화 — 대체물 아님. (스프링 있는 상태에서의 과거 기각과 별개로, 없는 상태에서도 기각)")),
    bullet(rt("상수 토크 오프셋 단독 (스프링 완전 제거): ", bold=True), rt("점프 세션 회복 (0424 1.04, 0324 0.88) + hip 오프셋 추가로 s2s 26930→6152까지 회복했으나 최악 +15~20% 잔존 — 위치 의존 성분이 필요.")),

    h1("5. 최종 통합 적합 (iter11) — 9-파라미터 삼중 목적 CMA"),
    para(rt("x = [stiff, ref, 무릎 오프셋×5세션, hip 오프셋×2], 목적 J = 0.5·(평행사변형 G7 평균비) + 0.5·(0429 score비). 300 evals:")),
    quote(rt("수렴해: stiff 1.33 → 0.404 Nm/rad (무릎 힌지), ref 2.15 rad, 무릎 오프셋이 30mm 세션 공통 +2.0~2.4 Nm (hip ~0)", bold=True)),
    para(rt("오프셋이 '세션별 드리프트'가 아니라 30mm 세션 전체에 균일하다는 것이 결정적 단서 — 세션이 아니라 l_i=30mm 상태 자체에 결부된 물리다.")),

    h1("6. 판별 실험 ② — 센서 편향인가, 실재 토크인가 (iter12)"),
    para(rt("+2Nm의 두 해석: (a) 무릎 전류센서가 2Nm underread (데이터 보정) vs (b) 플랜트에 실재하는 +2Nm 보조 토크 (모델에 추가). "
            "Mode A에서는 둘이 수학적으로 동일하지만, 폐루프(CL)에서는 다르다 — (b)라면 sim 플랜트에도 +2Nm을 넣어야 실기와 같은 PD 평형이 나온다:")),
    table([
        ["해석", "CL fit (C, 게이트 1.05)", "CL held-out (Cg, 게이트 1.10)"],
        ["(a) 데이터 오프셋 (센서 편향)", "1.19 ✗", "1.12 ✗"],
        ["(b) 플랜트 +2Nm (프리로드 보조)", "1.07", "0.97 ✓ 기준보다 개선"],
        ["(b′) 플랜트 −2Nm (부호 검증)", "1.81", "1.43 — 방향 확인용"],
    ]),
    callout("🏆", rt("판정: 실재 토크다. ", bold=True),
            rt("물리 후보: 클러치(크랭크 길이 조절 기구)가 l_i=30mm = 행정 끝단에서 프리로드 상태로 눌려 있고, 그 반력이 크랭크에 ~+2Nm 보조 토크로 "
               "작용. 25.08mm(행정 중간)에서는 없음 — 0429가 오프셋을 원하지 않는 이유까지 설명된다. "
               "벤치 검증법: l_i=28mm vs 30mm에서 같은 자세 유지토크 비교 (2Nm 차이가 나타나면 확정).")),

    h1("7. 최종 스택 — 성능 총괄"),
    table([
        ["항목", "P16 (기존)", "P18b 최종", "비고"],
        ["0429 Mode A score", "243.7", "75.8 (−69%)", "q2 0.462→0.098 rad, dq2 13.1→3.24"],
        ["0429 h갭 (Mode A)", "+10.7 cm", "+4.7 cm", "10 trials 평균"],
        ["0429 CL", "q2 0.133 / h +10.0cm", "q2 0.176 / h +8.8cm", "무릎 포화(37% 천장) 무반영 한계, kp500 trial 1개 발산"],
        ["평행사변형 G7", "1.00 (기준)", "평균 1.00 (0.89~1.10)", "w_0324 0.89, w_s2s 0.94, fs_0602 1.10"],
        ["평행사변형 CL", "C 0.894 / Cg 1.027", "C×1.07 / Cg×0.97", "held-out 개선"],
        ["구조 변경", "스프링 1.33@크랭크", "스프링 0.40@무릎 + 30mm 프리로드 +2Nm", "0429 q-오프셋 (+3.1°, −3.0°)"],
    ]),
    para(rt("파일: "), rt("code/goal22/p18_cvt/fourbar_p18b_candidate.json", code=True),
         rt(" · 결과: "), rt("Desktop/jump_opt/g22_cvt_0429_results/{png_v2, gif_v2}", code=True),
         rt(" · 로그: "), rt("MARATHON_P18B.md", code=True)),

    h1("8. 남은 갭 (정직)"),
    bullet(rt("0429 Mode A h갭 +4.7cm — 약화 스프링 채택의 대가 (스프링 0이면 +1.9cm). 프리로드의 l_i 의존 프로파일(중간 행정에서 잔여?)이 다음 축.")),
    bullet(rt("0429 CL 과대점프 +8.8cm — 무릎 전류 천장(~35.5, 샘플 37%)을 sim이 반영하지 않는 것이 1차 원인 (사용자: 천장 정체 미확정, 반영 보류).")),
    bullet(rt("0421 정적 잔차 +3.4Nm 잔존 — stiction 밴드 하에서만 정합. 중력-벤치 실험(사용자 예정)으로 해소 가능.")),
    bullet(rt("CL fit 게이트 소폭 초과 (1.07 vs 1.05) — held-out은 개선이므로 수용, 차기 전역 refit(P19?)에서 흡수 권장.")),
    bullet(rt("토크 오프셋의 물리(프리로드)는 가설 단계 — 벤치 판별 실험 제안 (§6).")),

    h1("9. 그림·시뮬레이션"),
]
imgs = [
    (DST / "marathon_progression.png", "마라톤 진행: 0429 score 244→76, h갭 +10.7→+4.7cm"),
    (DST / "png/120_2_120_2__A.png", "BEFORE — v1 (P16, 스프링@크랭크): 과속·사점 통과·GRF 스파이크"),
    (DST / "png_v2/120_2_120_2__A.png", "AFTER — P18b 최종: q2 0.098 rad, 이륙 타이밍·GRF 형상 회복"),
    (DST / "png_v2/60_0.75_60_2__A.png", "최저 게인 trial Mode A (최종 스택)"),
    (DST / "png_v2/120_2_120_2__CL.png", "PD 폐루프 (최종 스택)"),
    (DST / "gif_v2/120_2_120_2__A.gif", "최종 스택 Mode A 애니메이션 — CVT 링키지 (l_i=25.1mm)"),
    (DST / "torque_gain_timeline.png", "참고: 점프 중 무릎 토크 확대비 1/r (15배→1.2배→2.5배 CVT 스윕)"),
]
for p, cap in imgs:
    try:
        B.append(img(p, cap))
    except Exception as e:
        B.append(para(rt(f"[업로드 실패 {Path(p).name}: {e}]")))
append(B)
print("P18B NOTION DONE:", "https://www.notion.so/" + root.replace("-", ""))
