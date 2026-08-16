---
name: feedback-notion-image-upload
description: Notion 페이지에 이미지 첨부할 때 항상 Notion API file_uploads 사용. imgur 등 외부 호스팅 금지. 작업 방법 + 토큰 + 패턴 전부.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

**규칙**: 노션 페이지에 이미지 첨부할 때 **항상 Notion API의 `file_uploads` endpoint** 사용. imgur 등 외부 public 호스팅 금지 (이전엔 자동모드가 차단함, 데이터 유출 위험).

**Why**: 사용자가 명시적으로 "항상 너가 스스로 이미지 업로드 가능하게" 요구. World Model in Robotics 페이지(`https://www.notion.so/35eab81d255081978197ca3d24b6deaa`)가 이 방식으로 만들어짐 — 이미지 URL이 `prod-files-secure.s3.us-west-2.amazonaws.com` (Notion 자체 S3).

**Token**: `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`  
또는 (오래된 토큰): `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`  
→ 토큰 401 나면 사용자에게 새 토큰 요청.

**3-step 워크플로우**:

1. **`POST https://api.notion.com/v1/file_uploads`** (빈 JSON body `{}`) → `{id, upload_url, ...}` 반환
2. **`POST upload_url`** multipart/form-data 로 파일 전송 (field name = `"file"`)
3. **이미지 block 만들기** — image type=`file_upload`, file_upload={id: <upload_id>}, attach to page via `PATCH /v1/blocks/<page_id>/children`

**Reference 구현**: `C:\Users\junho\.codex\memories\upload_notion_graphs.py` (line 76 `upload_file` 함수가 정확한 패턴)

**핵심 코드 패턴**:
```python
TOKEN = "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"
NOTION_VERSION = "2026-03-11"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": NOTION_VERSION}

# Step 1: register upload
r = requests.post("https://api.notion.com/v1/file_uploads",
                  headers={**HEADERS, "Content-Type": "application/json"}, json={})
upload_id = r.json()["id"]; upload_url = r.json()["upload_url"]

# Step 2: send file via multipart
with open(png_path, "rb") as f:
    files = {"file": (png_path.name, f, "image/png")}
    requests.post(upload_url, headers=HEADERS, files=files)

# Step 3: attach image block to page
block = {"object":"block", "type":"image",
         "image":{"type":"file_upload", "file_upload":{"id": upload_id}}}
requests.patch(f"https://api.notion.com/v1/blocks/{page_id}/children",
               headers={**HEADERS, "Content-Type": "application/json"},
               json={"children": [block]})
```

**MCP 도구는 file 업로드 지원 안 함** — 위 raw API 호출이 유일한 방법. mcp__claude_ai_Notion__notion-create-pages는 content 마크다운만 받음.

**Tip**: 페이지 본문에 이미지 자리(텍스트로 "[image_placeholder] caption") 미리 만들고, 이후 raw API로 이미지 블록 append하는 게 안전.

**관련**: [[feedback_notion_workflow]] — 페이지 구성 워크플로우. 이미지 첨부도 그 일부.
