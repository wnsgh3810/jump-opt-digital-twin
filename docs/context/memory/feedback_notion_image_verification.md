---
name: feedback-notion-image-verification
description: Notion 페이지에 이미지/애니메이션 업로드 후 항상 verification. GIF 특히 주의. 실패 시 재업로드
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 91aad6ed-e999-400c-bacd-e1da7d4a5da4
---

# Notion 이미지/애니메이션 업로드 후 항상 검증

**규칙**: 페이지 만들고 끝내지 말 것. 업로드 verification 필수.

**Why**: GIF 큰 파일은 upload timeout 가능. file_upload `pending` 상태로 남거나 broken image block 발생. 사용자에게 broken URL 전달하면 일 두 번 됨.

**How to apply**:
1. 페이지 생성 + 이미지 block 추가 후
2. `GET /v1/blocks/{page_id}/children` → image blocks 검증:
   - `image.type` 정상 (`file_upload` or `external`)
   - `file_upload.id` 존재
   - caption 정상
3. 특히 GIF는 file_upload status `uploaded` 확인 (`pending`이면 재시도)
4. 실패한 block: delete → 재업로드 → 재생성 → 재검증
5. 모든 검증 통과 후 user에게 URL + 정상 표시 명시

**관련 패턴**:
- 이전 GOAL2/GOAL3/GOAL4에서 GIF가 broken 상태로 페이지에 남은 사례 있음
- 30분 rate limit 발생 가능 — wait 후 재시도

**Related**: [[feedback_notion_image_upload]] [[feedback_notion_workflow]]
