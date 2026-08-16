# -*- coding: utf-8 -*-
"""notion_kit — 노션 헬퍼 통합본 (goal22에 ~19회 복붙되던 패턴의 단일 출처).

사용:
    import notion_kit as N
    pid = N.create_page(N.GOAL22, "제목", icon="🎯")
    N.append(pid, [N.h1("장"), N.para(N.rt("본문")), N.table([...]), N.img(path, "캡션")])
    assert N.verify_images(pid, expected=k)   # 업로드 검증 의무 (철칙 8)
"""
import mimetypes
import time
from pathlib import Path

import requests

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


# ── rich text / 블록 빌더 ──
def rt(t, bold=False, code=False, link=None):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold:
        ann["bold"] = True
    if code:
        ann["code"] = True
    if ann:
        a["annotations"] = ann
    if link:
        a["text"]["link"] = {"url": link}
    return a


def para(*r):
    return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}


def h1(t):
    return {"type": "heading_1", "heading_1": {"rich_text": [rt(t)]}}


def h2(t):
    return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}


def h3(t):
    return {"type": "heading_3", "heading_3": {"rich_text": [rt(t)]}}


def bullet(*r):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}


def quote(*r):
    return {"type": "quote", "quote": {"rich_text": list(r)}}


def callout(emoji, *r):
    return {"type": "callout",
            "callout": {"icon": {"emoji": emoji}, "rich_text": list(r)}}


def code_block(t, language="plain text"):
    return {"type": "code", "code": {"rich_text": [rt(t)], "language": language}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header,
        "has_row_header": False,
        "children": [{"type": "table_row",
                      "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


# ── 페이지/업로드 ──
def create_page(parent_id, title, icon="📄"):
    return req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": parent_id}, "icon": {"emoji": icon},
        "properties": {"title": {"title": [rt(title)]}}}).json()["id"]


def img(path, caption=""):
    """파일 업로드 (3-step) + 상태 검증 후 image 블록 반환. 실패 시 raise."""
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    fu = req("POST", "https://api.notion.com/v1/file_uploads", headers=HJ,
             json={"mode": "single_part", "filename": p.name}).json()
    req("POST", fu["upload_url"], headers=H,
        files={"file": (p.name, p.read_bytes(), mt)})
    st = req("GET", f"https://api.notion.com/v1/file_uploads/{fu['id']}",
             headers=H).json()
    if st.get("status") != "uploaded":
        raise RuntimeError(f"notion upload 실패: {p.name} status={st.get('status')}")
    b = {"type": "image",
         "image": {"type": "file_upload", "file_upload": {"id": fu["id"]}}}
    if caption:
        b["image"]["caption"] = [rt(caption)]
    return b


def append(page_id, blocks, batch=80):
    for i in range(0, len(blocks), batch):
        req("PATCH", f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=HJ, json={"children": blocks[i:i + batch]})
        time.sleep(0.4)


def get_children(page_id):
    out, cur = [], None
    while True:
        u = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if cur:
            u += f"&start_cursor={cur}"
        j = req("GET", u, headers=H).json()
        out += j["results"]
        if not j.get("has_more"):
            break
        cur = j["next_cursor"]
    return out


def verify_images(page_id, expected=None):
    """페이지의 image 블록 수 확인 (철칙: 업로드 후 검증 의무). expected 불일치 시 False."""
    imgs = [b for b in get_children(page_id) if b["type"] == "image"]
    ok = all(b["image"].get("type") in ("file_upload", "file") for b in imgs)
    if expected is not None and len(imgs) != expected:
        return False
    return ok
