# -*- coding: utf-8 -*-
"""노션: P18c — 26.06.04 페이로드 s2s 검증 + CVT 효과 정량화."""
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
DST = Path((LEGACY_ROOT + "/g22_s2s_0604_results"))


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
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def callout(e, *r): return {"type": "callout", "callout": {"icon": {"emoji": e}, "rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}


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
    "parent": {"page_id": GOAL22}, "icon": {"emoji": "🏋️"},
    "properties": {"title": {"title": [rt("P18c — 26.06.04 페이로드 sit-to-stand 검증: CVT 효과 정량화")]}}}).json()["id"]

B = [
    callout("🏋️", rt("질문: ", bold=True),
            rt("26.06.04 페이로드 s2s 데이터(no-CVT는 no-load만 유효, CVT는 전부 유효)를 지금 모델(P18b)로 검증하고, "
               "CVT가 여기서 얼마나 효과가 있는지 — 페이로드는 base 질량 가산으로. "),
            rt("답: 폐루프 검증 4/4 통과 (q2 0.02~0.07 rad, GRF가 페이로드에 정확 비례 31→56→80N), "
               "반사실 트윈이 실기 성공/실패 경계(no-CVT 5kg 성공 / 7.5kg 실패)를 그대로 재현, "
               "같은 로드에서 CVT가 무릎 모터 토크 −18~23%, 페이로드 한계 ~6.1kg → ~8.4kg (+38%).", bold=True)),

    h1("1. 데이터 상태 (사용자 지시와 일치 확인)"),
    table([
        ["trial", "상태", "l_i", "비고"],
        ["cvt/no_load", "유효 (xlsx 전체)", "25.2mm 상수", "dq_des 인가 세션"],
        ["cvt/load_2.5", "유효", "25.2mm", "2.5kg base 탑재"],
        ["cvt/load_5", "유효", "25.2mm", "5kg — 무릎 실측 τ가 상승 구간에서 천장(~19.5Nm)에 플래토"],
        ["no_cvt/no_load", "유효", "30mm", "프리로드 +2.06Nm 적용 (P18b)"],
        ["no_cvt/load_5", "실기 기립 성공 — xlsx 미수출 (영상/.fig만)", "30mm", "반사실로 재현"],
        ["no_cvt/load_7.5", "실기 기립 실패 — xlsx 미수출", "30mm", "반사실로 재현"],
    ]),
    para(rt("모델링: 페이로드 = base body 질량 가산. base는 레일 병진 전용(회전 자유도 없음)이라 질량만 더하는 것이 정확 "
            "(관성/CoM 이동 무관). 게인은 각 trial에서 회귀 추정 (dq_des 항 포함, hip R² ~0.9). 세션 오프셋 0.")),

    h1("2. 검증 결과 — 폐루프 (배포 관점 지표)"),
    table([
        ["trial (CL)", "q2 RMSE [rad]", "dq2 [rad/s]", "GRF 평균 sim/real [N]", "무릎 τ 피크 sim/real [Nm]"],
        ["cvt/no_load", "0.020", "0.13", "31 / 34", "5.1 / 4.1"],
        ["cvt/load_2.5", "0.027", "0.21", "56 / 58", "9.1 / 9.5"],
        ["cvt/load_5", "0.068", "0.79", "80 / 82", "13.0 / 20.9"],
        ["no_cvt/no_load", "0.025", "0.15", "31 / 33", "4.3 / 6.1"],
    ]),
    bullet(rt("★ GRF가 페이로드에 정확히 비례 (31→56→80N ≈ (2.5kg 증분)×g): ", bold=True),
           rt("\"base 질량 가산\" 모델링이 로드셀로 직접 검증됨.")),
    bullet(rt("cvt/load_5의 실측 무릎 τ 피크 20.9 vs sim 13.0: 실기는 상승 구간에서 공급 천장에 붙어 톱니 진동 + GRF 출렁임(페이로드 흔들림/재하중) — "
              "강체 부착 sim은 이 슬로시를 재현하지 않음 (정직한 한계).")),
    bullet(rt("Mode A(1.9s 개루프 재생)는 s2s에서 발산 — 준정적 동작이라 토크 잔차에 초민감 (기존 GOAL들도 s2s는 0.2s 창 평가만 사용). "
              "그래프는 png/에 저장, 해석 지표는 CL.")),

    h1("3. 반사실 실험 — 실기가 못 한 조합을 트윈으로"),
    para(rt("같은 목표궤적·회귀 게인으로 로드만 바꿔 시뮬. 공급 천장(raw 35.5 → shaft 18.9Nm) 적용:")),
    table([
        ["구성", "기립 (base 상승)", "무릎 cmd 99% [Nm]", "천장 초과 시간", "판정"],
        ["no_cvt + 2.5kg", "29.8cm ✓", "9.8", "0%", "성공"],
        ["no_cvt + 5.0kg", "30.1cm ✓", "15.9", "0%", "성공 — 실기 성공과 일치 ✓"],
        ["no_cvt + 7.5kg", "−2.1cm ✗", "발산", "85%", "기립 실패 — 실기 실패와 일치 ✓"],
        ["cvt + 7.5kg", "31.5cm ✓", "17.5", "0%", "성공 (실기 미실험 조합)"],
        ["cvt + 10kg", "33.2cm (한계)", "26.0", "49%", "한계선"],
    ]),
    callout("✅", rt("트윈-실기 경계 일치: ", bold=True),
            rt("실기는 no-CVT 5kg까지 성공, 7.5kg 실패 — 트윈(순간 천장 18.9Nm)이 이 경계를 정확히 재현한다 "
               "(5kg: 15.9Nm 여유 / 7.5kg: 천장 초과 85% → 기립 불능). 공급 천장 모델의 독립 검증. "
               "참고: 5kg 성공은 정격(연속) 9Nm의 1.8배를 ~1초 지속한 것 — 이 시간 규모에선 열 제한이 걸리지 않음을 실기가 보여줌 (정격선은 참고용).")),

    h1("4. CVT 효과 정량 (같은 로드 맞대결)"),
    table([
        ["로드", "no-CVT 무릎 cmd 99%", "CVT 무릎 cmd 99%", "절감"],
        ["5.0kg", "15.9 Nm", "13.0 Nm", "−18%"],
        ["7.5kg", "22.7 Nm (천장 초과)", "17.5 Nm", "−23%"],
    ]),
    quote(rt("s2s 자세 범위(무릎 60~130°)에서 전달비 r ≈ 0.8 → 무릎 모터 토크 ≈ ×0.8 — 측정·시뮬 절감치(−18~23%)와 정합. "
             "페이로드 한계 (수요가 천장 18.9Nm에 닿는 로드, 트윈 보간): no-CVT ~6.1kg → CVT ~8.4kg (+2.3kg, +38%). "
             "실기 경계(no-CVT: 5kg 성공/7.5kg 실패)가 이 한계선 안팎에 정확히 놓인다.", bold=True)),

    h1("5. 그림"),
]
imgs = [
    (DST / "torque_margin.png", "무릎 모터 토크 수요 vs 공급 한계 — 실기 경계(5kg 성공/7.5kg 실패)와 트윈 한계선(no-CVT 6.1kg / CVT 8.4kg) 일치"),
    (DST / "png/cvt_load_5__CL.png", "cvt/load_5 폐루프 — q 추종 우수, 실측 무릎 τ는 천장 플래토, GRF 슬로시는 sim 미재현"),
    (DST / "png/no_cvt_no_load__CL.png", "no_cvt/no_load 폐루프 (프리로드 +2.06 적용)"),
    (DST / "counterfactual/no_cvt_CF_load7.5__CLcap.png", "반사실: no_cvt + 7.5kg + 천장 — 무릎이 천장에 걸려 기립 실패 (실기 실패와 일치)"),
    (DST / "counterfactual/cvt_CF_load7.5__CLcap.png", "반사실: cvt + 7.5kg + 천장 — 17.5Nm로 기립 성공"),
    (DST / "gif/cvt_load_5__CL.gif", "cvt/load_5 폐루프 애니메이션 (l_i=25.2mm)"),
    (DST / "gif/no_cvt_no_load__CL.gif", "no_cvt/no_load 폐루프 애니메이션 (l_i=30mm)"),
]
for p, cap in imgs:
    try:
        B.append(img(p, cap))
    except Exception as e:
        B.append(para(rt(f"[업로드 실패 {Path(p).name}: {e}]")))
B.append(para(rt("결과 폴더: "), rt("CVT/jump_opt/g22_s2s_0604_results/", code=True),
              rt(" (png 8 · counterfactual 10 · gif 4 · torque_margin · MODEL.txt) · 코드: "),
              rt("code/goal22/p18_cvt/s2s_0604*.py", code=True)))
for i in range(0, len(B), 80):
    req("PATCH", f"https://api.notion.com/v1/blocks/{root}/children",
        headers=HJ, json={"children": B[i:i + 80]})
    time.sleep(0.4)
print("0604 NOTION DONE:", "https://www.notion.so/" + root.replace("-", ""))
