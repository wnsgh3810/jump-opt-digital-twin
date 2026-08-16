# -*- coding: utf-8 -*-
"""P19 마라톤 노션 루트 페이지 (진행 로그는 append로 계속 추가)."""
import requests, time, json, sys, mimetypes
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
HERE = Path(__file__).parent


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


def append(pid, blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{pid}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


def create_root():
    root = req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": GOAL22}, "icon": {"emoji": "🎯"},
        "properties": {"title": {"title": [rt("P19 마라톤 — 점프 τ-fidelity (Paper 우선, ~04:00)")]}}}).json()["id"]
    B = [
        callout("🎯", rt("미션 (2026-07-10 00:1x~04:00): ", bold=True),
                rt("점프(cvt 0429 + no_cvt 0324/0421/0424/0602)에서 \"궤적(q_des,dq_des)로 PD 제어했을 때 실측 토크 ≈ sim 예측 토크\"를 "
                   "지금보다 확실히 개선. Paper 보정식 우선, 모든 방법 허용(학습 포함), s2s는 목적에서 제외.")),
        h1("0. 마라톤 고정 지표"),
        para(rt("CL τ-갭 = RMSE(τ_sim − τ_meas_paper) / RMS(τ_meas_paper)", code=True),
             rt(" — 관절별, [0, 이륙+0.1s] 창, 트라이얼 평균. 발산은 갭 2.0 캡 + 2.5 페널티. "
                "0324(ff 세션)는 held-out. 보조: Mode A 점프 창 심판, q2 RMSE 가드.")),
        h1("1. 베이스라인 (00:15) — 출발점의 정직한 민낯"),
        table([
            ["구성", "FIT τ-갭 (hip/knee)", "held-out 0324", "비고"],
            ["P16 + A_fit (현 canonical)", "89.9% (110.6/69.1)", "41.0%", "0429 CL 발산 trial 포함"],
            ["P16 + A_paper", "69.2% (95.8/42.6)", "41.6%", ""],
            ["P18b + A_fit", "90.2% (112.0/68.4)", "38.9%", ""],
            ["P18b + A_paper", "69.9% (97.5/42.3)", "39.5%", ""],
        ]),
        bullet(rt("★ 이 지표에선 A_paper가 A_fit을 압도 (69 vs 90%) — 사용자의 \"Paper 우선\" 지시가 데이터로 정당화됨. "
                  "P14/P16의 a_hat 적합은 Mode A 창 최적화였고, 폐루프 τ-갭에는 오히려 해로웠음.")),
        bullet(rt("구조 분석: τ-갭 ≈ kp·(q_real−q_sim) + kd·(dq_real−dq_sim) — 게인 가중 궤적 불일치. "
                  "hip 갭 ~100%는 hip 토크 자체가 작아(RMS 2~4Nm) 상대 지표가 민감한 것 + hip 궤적 미스매치.")),
        h1("2. 계획"),
        bullet(rt("CMA-1 (발사 00:25): A=Paper 고정, 물리 16-param (스프링/프리로드/마찰 4/접촉 2/armature/질량·관성·CoM 5/0421 게인스케일)을 "
                  "목적 지표에 직접 적합. 14-trial 부분집합, 350 evals.")),
        bullet(rt("이후: 전체 검증 → 잔차 분해 (어느 세션/구간/채널) → 축 추가 or CMA-2 → (시간 허용 시) 잔차 학습 → 최종 스택 + 보고")),
    ]
    append(root, B)
    print("P19 ROOT:", root)
    json.dump({"root": root}, open(HERE / "p19_notion.json", "w"))


if __name__ == "__main__":
    create_root()
