# -*- coding: utf-8 -*-
"""P18 노션 보고 — l_i CVT 세션(26.04.29) 검증: 방법·결과·원인 분석."""
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
import numpy as np
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
HERE = Path(__file__).parent
DST = Path((LEGACY_ROOT + "/g22_cvt_0429_results"))
RES = json.load(open(HERE / "cvt_results.json"))


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
def h3(t): return {"type": "heading_3", "heading_3": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(e, *r): return {"type": "callout", "callout": {"icon": {"emoji": e}, "rich_text": list(r)}}
def code(t): return {"type": "code", "code": {"rich_text": [rt(t)], "language": "plain text"}}


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
    "parent": {"page_id": GOAL22}, "icon": {"emoji": "🔀"},
    "properties": {"title": {"title": [rt("l_i CVT 세션 검증 (26.04.29) — Mode A + PD 폐루프")]}}}).json()["id"]


def append(blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{root}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


def avg(mode, f):
    ks = [k for k in RES if k.endswith("/" + mode) and "err" not in RES[k]]
    return float(np.mean([RES[k][f] for k in ks]))


B = [
    callout("🔀", rt("목적: ", bold=True),
            rt("l_i(크랭크 길이)를 30mm에서 바꿔 점프한 26.04.29 세션을, MuJoCo 4-bar에서 l_i만 바꿔 재현할 수 있는가 — "
               "CVT 기능의 첫 시뮬레이션 검증이자, 현행 모델(P16)의 '전달비 밖 외삽' 시험. "
               "결과 요지: 기구학·폐루프 상태는 준수하게 전이되나, 토크·에너지 원장은 전달비가 바뀌자 계통 오차를 드러냈다 (전 trial 과대점프 +10%p — 기존 세션들의 과소점프와 부호 반전). "
               "이 세션이야말로 손실 원장을 분리 식별할 최적 데이터라는 결론.")),
    h2("1. 세션 특성 (데이터에서 확정)"),
    table([
        ["항목", "값", "근거"],
        ["l_i", "25.08 mm (점프 창 내 상수, 전 trial 동일)", "Clutch.xlsx 'Current Link Length' 실측 — 변속 프로파일은 기록 창 밖"],
        ["l_o / coupler / thigh", "30 / 250 / 250 mm (불변)", "하드웨어"],
        ["제어", "PD only, dq_des = 0", "What.txt 'V_des ≈ 0' + hip 회귀 R² 0.92~0.97 (kp≈라벨)"],
        ["무릎 포화", "raw 천장 34.8~36.1 (중앙 35.2 — 0424/0602와 동일), |raw|>30이 37%", "이 세션은 무릎 전류가 천장에 붙은 '포화 지배' 세션"],
        ["trial 수", "10 (게인 라벨 60~500)", "h_real 0.93~1.00 m"],
    ]),
    h2("2. 구현 — 비평행사변형 4-bar"),
    para(rt("l_i ≠ l_o(30mm)가 되는 순간 평행사변형이 깨진다: crank각 ≠ calf각, 전달비가 자세 의존 비선형이 된다. "
            "MuJoCo 구현은 기존과 동일한 '트리 + 등호구속'이되 두 가지만 바뀐다:")),
    bullet(rt("site-기반 connect: ", bold=True),
           rt("기존 body-anchor connect는 기준자세(전 관절 0)에서 루프가 닫혀 있어야 하는데(평행사변형만 성립) "
              "l_i=25.08mm는 기준자세에서 ~5mm 어긋남 → 커플러 끝 site와 calf 로커 site를 명시로 붙이는 표기로 전환 (물리 동일, MuJoCo 3.x)")),
    bullet(rt("폐쇄 솔버 (초기화·FK 전용): ", bold=True),
           rt("측정 crank각 → calf각·cpin각을 원-원 교차로 계산 (시뮬 중 루프 유지는 기존처럼 MuJoCo 구속이 담당). "
              "sanity: l_i=30에서 qk≡qc·r≡1 재현, 폐쇄 잔차 1.1e-16 m")),
    h3("전달비 프로파일 — CVT의 실체"),
    table([
        ["crank각 (mj)", "r = dq_calf/dq_crank", "무릎 토크 증폭 1/r"],
        ["0.35 (폄 근처)", "0.45", "2.2×"],
        ["1.0", "0.79", "1.3×"],
        ["1.5 (중간)", "0.84", "1.2×"],
        ["2.0", "0.81", "1.2×"],
        ["2.6 (crouch)", "0.60", "1.7×"],
    ]),
    para(rt("l_i 30→25mm 하나로 무릎이 전 구간 감속(토크 증폭) 기어가 됨. 부수 발견: 이 l_i에서는 무릎 완전 폄(ψ=0)이 "
            "워크스페이스 밖 — 링키지가 기하적으로 도달 불가 (CVT 설계의 실제 트레이드오프).")),
    h2("3. Mode A 결과 (개루프 τ replay, 오프셋=0)"),
    table([
        ["평균 (10 trials)", "q2(crank) RMSE", "dq2 RMSE", "h_sim / h_real"],
        ["Mode A", f"{avg('A','q2'):.3f} rad", f"{avg('A','dq2'):.1f} rad/s", f"{avg('A','h'):.3f} / {avg('A','h_real'):.3f} (+9%p 과대)"],
        ["참고: 0424/0602 (평행사변형, full-replay)", "0.15~0.20 rad", "2.6~2.9 rad/s", "0.90~0.96 (과소)"],
    ]),
    para(rt("full-replay 발산이 기존 세션 대비 3~4배 크고, "),
         rt("h가 전 trial 일관 과대(+9%p) — 기존 세션들의 과소점프와 부호가 반대", bold=True),
         rt(". 전달비가 바뀌자 모델의 에너지 원장이 반대 방향으로 틀리기 시작한 것 — 5절에서 분석.")),
    h2("4. PD 폐루프 결과 (라벨 게인, dq_des=0, 무클립+P16 a_hat)"),
    table([
        ["평균 (10 trials)", "q2 RMSE", "dq2 RMSE", "τ_hip RMSE", "τ_knee RMSE", "h_sim / h_real"],
        ["CL", f"{avg('CL','q2'):.3f} rad", f"{avg('CL','dq2'):.1f} rad/s",
         f"{avg('CL','tau1'):.2f} Nm", f"{avg('CL','tau2'):.2f} Nm",
         f"{avg('CL','h'):.3f} / {avg('CL','h_real'):.3f}"],
        ["참고: 0424/0602 (P16, cl_p14 재실행)", "0.030~0.052", "2.3~2.7", "2.3~2.5", "4.0~4.9", "0.88~0.97 (실측 근접)"],
    ]),
    para(rt("상태 추종은 준수(q2 0.13 — 기하·폐루프 구조가 잘 전이됨을 뜻함), 그러나 "),
         rt("τ_knee 7.0Nm과 고게인 trial의 h +15%p 과대가 두드러짐", bold=True), rt(".")),
    h2("5. 원인 분석 (증거 순)"),
    bullet(rt("① 무릎 포화 지배 + 무클립 sim: ", bold=True),
           rt("실측 무릎 raw의 37%가 30 이상(천장 35.2)인데 sim은 캡 없이 커맨드 그대로 냄 → 과대 토크·과대점프의 1차 후보. "
              "천장의 정체(R-Link)가 확정되면 이 세션 재현이 가장 크게 좋아질 것")),
    bullet(rt("② 손실 원장의 전달비 의존: ", bold=True),
           rt("우리 마찰은 crank축(모터측)에 뭉쳐 있음. 실물 손실 일부가 calf측(무릎 힌지·로커 핀)에 있다면, "
              "평행사변형(r=1)에선 구분 불가였지만 r≈0.6~0.8이 되는 순간 배치 오류가 노출됨 — 과대점프 부호 반전의 유력 설명")),
    bullet(rt("③ stiff_knee 스프링의 위치: ", bold=True),
           rt("crank축 스프링이라 무릎 기준 유효 강성이 r²만큼 변함 — 30mm에서 fit된 값이 25mm에선 다른 무릎 유연성을 의미")),
    bullet(rt("④ 세션 오프셋 미적합 (0 사용), 클러치 모터 질량 변화 등 세션 고유 요인")),
    h2("6. 시사점 — 이 데이터의 진짜 가치"),
    quote(rt("전달비가 다른 세션은 crank측 손실과 calf측 손실을 '구분 가능'하게 만든다 — 평행사변형 데이터만으로는 원리적으로 "
             "불가능했던 식별이다. 0429를 이중 심판 적합에 포함하는 P18b가 손실 원장 분리의 다음 열쇠.", bold=True)),
    bullet(rt("P18b 제안: 0429 10 trials를 fit set에 추가 + 마찰을 crank측/calf측으로 분리(fv/fc_calf 신설) + 이중 심판 재적합")),
    bullet(rt("결과 파일: "), rt("CVT/jump_opt/g22_cvt_0429_results/", code=True),
           rt(" (png 20 · gif 20) · 코드: "), rt("code/goal22/p18_cvt/", code=True)),
    h2("7. 그림·시뮬레이션"),
]
for p, cap in [
    (DST / "png/120_2_120_2__A.png", "Mode A (120_2) — 개루프 replay: dq2 발산과 과대점프"),
    (DST / "png/120_2_120_2__CL.png", "PD 폐루프 (120_2) — 상태 추종 준수, knee τ 갭"),
    (DST / "png/150_2.2_500_4__CL.png", "PD 폐루프 (150_2.2_500_4, 최고 게인) — 포화 지배의 전형"),
    (DST / "gif/120_2_120_2__CL.gif", "CVT 링키지 애니메이션 — l_i=25.1mm 비평행사변형 (crank·coupler 각도가 calf와 어긋나는 것이 보임)"),
    (DST / "gif/150_2.2_500_4__A.gif", "Mode A replay 애니메이션 (l_i 표기)"),
]:
    try:
        B.append(img(p, cap))
    except Exception as e:
        B.append(para(rt(f"[업로드 실패 {Path(p).name}: {e}]")))
append(B)
print("CVT NOTION DONE:", "https://www.notion.so/" + root.replace("-", ""))
