---
name: Notion Page Creation Workflow
description: 노션 보고서/문서 만들 때 사용자가 원하는 방식 — 구조 계획 → 부분별 한 페이지씩 → 다양한 그래프 → 비유+논리+수식
type: feedback
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
modified: 2026-07-28T15:09:40.157Z
---

## Paper full-fidelity publication gate (2026-08-02)

- Structural lint alone never proves that a paper translation is complete or semantically faithful.
- Before publishing, use an independent fresh-context reviewer to inspect every PDF page with no sampling. Save `full_fidelity_audit.md` using the canonical template.
- Certify the exact PDF, source index, corrected draft, audit report, `figure_manifest.json`, and every `figures_final` asset with `fidelity_audit_gate.py certify`.
- The final draft command must include `--require-fidelity`. The published phase always requires fidelity evidence.
- Any post-certification edit makes `fidelity_audit.json` stale. Repeat or explicitly revalidate the complete audit before recertifying.
- Never claim zero omissions before the full-fidelity gate passes.
# 노션 페이지 작성 방식 (사용자 명시 선호)

## 0. ★분석할 때마다 노션에 즉시 기록 (2026-07-25 사용자 지시 — 상시 규칙)

**Why:** 세션에서 분석(그래프·표·발견)이 나올 때마다 사용자가 "노션에 넣어줘"를 반복 요청해왔고,
07-25에 "분석할 때마다 노션에 넣어"로 상시화함.

**How to apply:** 분석 하나가 완결되면(그래프+수치+해석) 묻지 말고 해당 주제의 현행 노션 페이지에
섹션+이미지로 즉시 추가한다 (verify_images 필수). 새 주제면 관련 부모(현행 마라톤/실험 페이지) 아래
새 페이지. 어디 넣을지 애매할 때만 질문.
**(07-29 강화)** 마라톤/장기 작업은 **과정(실험 사이클)마다 차일드 페이지를 적극 신설** — 한 페이지에
섹션만 쌓지 말 것. 각 차일드 = 독립 학습 단위 (배경→방법→표→판정→정직한 한계→용어 노트). 길고
상세하고 이해하기 쉽게 (비유 후 수식, 표 필수).

**Why:** 한 번에 큰 페이지로 다 채우면 (1) Notion API 100 blocks 제한에 걸리고 (2) 한 페이지가 너무 길어 읽기/공부 어렵고 (3) 흐름 통제가 안 됨. 사용자가 4/26에 OOM 사고 보고서 만들면서 이 방식을 명시적으로 요구했음.

**How to apply:** 사용자가 노션에 자세한 보고서/문서를 만들어달라고 할 때마다 다음 워크플로우를 따른다.

## 1. 구조/단락/흐름 먼저 계획 (실제 만들기 전)
- 메인 페이지 1개 + 자식 페이지 N개 트리 구조로 설계
- 각 자식 페이지는 **독립 학습 단위**가 되도록
- 사용자에게 **각 페이지의 핵심 내용을 자세히 미리 보여주고 동의 받음**
- 너무 깊으면 더 분할, 비슷하면 합침

## 2. 부분별로 한 페이지씩 만들기 (한꺼번에 X)
- 메인 페이지 만들고 page_id 받음 → `report_main_id.txt`에 저장
- 자식 페이지 1, 2, 3, ... 차례로 부모를 메인 page_id로 지정해 생성
- 각 페이지 만든 후 진행 보고 + 다음 페이지 만들 의향 확인
- 페이지 100 blocks 넘으면 PATCH로 추가

## 3. 그래프 다양하고 이해하기 쉽게
- matplotlib으로 여러 종류의 그래프 만듦 (Desktop\report_graphs\에 PNG)
- 단순 막대/꺾은선뿐 아니라:
  - **인과 chain 다이어그램** (도미노식 흐름도)
  - **개념 비교 박스** (fork vs spawn처럼 개념 좌우 대조)
  - **시각적 메커니즘 도식** (RAM/pagefile 흐름 등)
  - **flow/sequence 다이어그램** (atomic write, checkpoint+resume)
  - **log scale 비교** (page fault 비용 같은 huge range)
- 각 그래프에 **annotation (화살표·라벨·강조 색)** 으로 어디를 봐야 하는지 명시
- 한 페이지에 그래프 1~3개 첨부 자리. Notion API는 file upload 까다로워서 image_placeholder callout으로 위치 지정 → 사용자가 직접 PNG 첨부

## 4. 비유 + 논리·구조·수식 함께
- 비유적 표현 OK, **단 비유 직후에 반드시 구조적·수리적 설명을 붙임**
- 사용자는 로봇공학자 → 수식·논리는 강함, OS·코드는 약함
- 어려운 OS/컴퓨터 용어 첫 등장 시 짧은 정의 + 자식 7(용어 사전)에 모음

## 5. helper 모듈 분리
- `report_notion_lib.py` — Notion API 토큰, rich_text/heading/bullet/callout/code/image_placeholder 등 helper 함수 + create_page/append_blocks
- 각 페이지별 독립 스크립트: `report_p0_main.py`, `report_p1_timeline.py`, ...
- helper 재사용으로 일관성 유지

## 6. 페이지 시작 — Notion API 토큰
- TOKEN: `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` (메모리 attempts_history.md에 기록됨)
- 기본 부모 페이지 (CONCEPT): `115ab81d-2550-80fd-aae6-f28f55e3e205`
- 다른 부모 원하면 search_page 또는 사용자에게 확인

## 7. 페이지 구성 요소 (자유롭게 활용)
- Callout (강조 / 학습 가이드 / 위험 경고)
- Toggle (긴 정의/심화 내용 — 클릭해서 펼치기)
- Code block (코드 변경 diff)
- Equation block (KaTeX 수식)
- Table (비교표 / timeline)
- Bullet/Numbered list
- Divider로 섹션 구분
- Quote (직접 인용)

## 8. 검토 후 수정 가능하게
- 페이지 만들 때 page_id 출력해서 사용자가 바로 열어볼 수 있게
- 사용자가 "이 부분 더 자세히" / "이 부분 줄여" 라고 하면 PATCH로 수정

이 워크플로우 그대로 따르면 사용자가 만족하는 노션 보고서 나옴 (4/26 OOM 보고서로 검증).

## 9. 모델 분배 (Opus = 계획·내용 / Sonnet = API 입력)

**Why**: 노션 페이지 만들기는 두 종류의 작업이 섞임 — (1) 구조 설계·내용 작성·논리 도출 (창의·추론 heavy, Opus 강점), (2) Notion API 호출·md→blocks 파싱·이미지 업로드·페이지 ID 관리 (반복적 mechanic, Sonnet으로 충분 + 비용 절감). 사용자가 명시적으로 이 분배를 요구함 (2026-05-25).

**How to apply**:
- **Opus (메인)** 가 처리:
  - 페이지 구조·목차 계획
  - 각 section의 내용·논리·수식·비유 작성
  - 내용 markdown 파일 (`notion_<task>_content.md`) 작성/수정
  - 사용자 동의 받기
- **Sonnet (Agent 위임)** 이 처리:
  - 페이지 생성·수정·archive API 호출
  - md→Notion blocks 파싱 스크립트 작성/실행
  - 이미지/GIF 업로드 (file_uploads workflow)
  - 코드 toggle 부착
  - 100 blocks 분할 PATCH
  - block count 검증

**위임 방식**: `Agent` tool에 `subagent_type: "general-purpose"` + `model: "sonnet"`로 호출. Prompt에는 (1) 정확한 작업 파일 경로, (2) Page ID들, (3) 사용할 helper 모듈 (`notion_helper.py`), (4) 사용자 인증된 사실, (5) 내용 md 파일 수정 금지 명시.

## 10. Notion API 함정 메모 (체크리스트)
- **Code block 언어**: `batch`, `bat`, `cmd`는 invalid. 우리 helper(`report_notion_lib.py`)에 alias 추가됨 → `shell`로 매핑. 다른 invalid: `windowsbatch`, `cmdscript`. valid 목록은 Notion API docs 또는 호출 시 400 에러 응답으로 확인.
- **rich_text 길이**: 한 text 노드당 최대 2000자. 긴 코드는 helper에서 1900자로 자르고 `# ...(truncated)` 표시.
- **children 한 번에 100개**: API 제한. helper에서 자동 분할 batch.
- **유니코드 print**: Python stdout이 cp949면 ✓ 같은 문자 인쇄 시 UnicodeEncodeError. 스크립트 시작에 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` 추가.
- **page 검색**: 같은 제목 페이지 두 번 만들지 않게 `search_page("제목 키워드")` 먼저 호출.
- **이모지 코드포인트**: cp949에서 못 표현하는 emoji는 `"\U0001F6A8"` 처럼 escape로 적기.

## 11. 논문 전체 번역 페이지 예외 및 필수 게이트

- 논문 전체 번역은 사용자가 요청한 원문 구조를 보존하기 위해 기본적으로 한 페이지에 작성한다.
- 수식 번호를 `\tag{...}`로 수식 안에 넣지 않는다. 수식 다음 줄에 `(1)`, `(2a)` 같은 일반 텍스트로 둔다.
- `&nbsp;`, `&amp;nbsp;`, `&#160;`을 들여쓰기에 사용하지 않는다.
- 그림은 `![전체 한국어 캡션]([FIGURE:n])`으로 작성하고 업로드 때 소스만 교체한다.
- `Fig.`, `Figure`, `그림` 캡션을 별도 굵은/일반 문단으로 중복하지 않으며 `Figure 3` 같은 일반 alt도 금지한다.
- 게시 전 `notion-paper-translation/scripts/gate_notion_translation.py --phase draft --fix`를 통과해야 한다.
- 게시 후 완전한 fetch 본문으로 같은 게이트의 `--phase published`를 통과해야 한다.
- fetch 결과가 잘렸으면 완료로 보고하지 않는다.

- **차일드 표준 (07-30 사용자 재강조)**: 항상 확장판 — 배경(왜)→방법(비유 포함)→결과(표)→의미→용어 정리. 압축 요약판 금지.
