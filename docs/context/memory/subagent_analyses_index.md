---
name: Subagent Analyses Index
description: 이전 세션에서 실행한 7개 Subagent(Task) 작업의 목적·결과·보존 위치 인덱스
type: reference
originSessionId: cb42ed46-5d3f-447a-94f6-732ce10d7dfc
---
# Sub-agent 작업 인덱스

이전 클로드 세션에서 Plan/Explore/general-purpose agent로 위임한 큰 데이터 탐색·분석 작업들. 결과는 모두 `C:\Users\junho\Desktop\session_backup\subagents\<parent_session>\` 보존됨 (jsonl + 텍스트 timeline).

## b0a02628 세션 산하 (4/17~4/24, 메인 세션)

| Agent ID (앞 8자) | 일시 | type | 작업 | 핵심 산출 |
|---|---|---|---|---|
| `a7d1fb86` | 4/17 14:21 | general | P40_D0.7 hip.xlsx 등 Excel 파일 컬럼/행/값 범위 보고 | 4.3KB — 데이터 구조 파악 (Time, Cur, Des Position 등) |
| `a3d16fda` | 4/22 17:57 | Explore | 26.04.21 / 26.04.22 폴더 전체 탐색 (Position Control 6 + Torque Control 3 = 9 실험) | **12.3KB — 디렉토리 구조 + Real Data.txt 전체 내용** |
| `adeb3b68` | 4/22 17:58 | general | 6개 Real Data.txt 전부 읽고 raw numbers 그대로 보고 | **21.4KB — 모든 실험 raw numbers 보존** (jump height, mass, peak GRF 등) |
| `a0e1b479` | 4/22 18:00 | general | 9개 실험 hip/knee/GRF.xlsx로 Impulse/Energy/RMS/지연 계산 | 4.2KB (권한 이슈로 부분 실행) |
| `af2ed0c5` | 4/22 18:00 | general | 9개 실험 Position.png / Torque.png 이미지 시각 보고 | 13.2KB — 그래프 패턴 visual 검토 |
| `a2593953` | 4/23 06:42 | Explore | sit2stand 디렉토리 탐색 + PD 게인 폴더명 분석 | 5.0KB — sit2stand 데이터 구조 |

## c82aa01d 세션 산하 (4/25 새벽 복구 세션)

| Agent ID (앞 8자) | 일시 | type | 작업 | 핵심 산출 |
|---|---|---|---|---|
| `a205b209` | 4/25 02:56 | general | 600KB session_timeline.txt 분석해서 메모리 13개 파일 자동 생성 | 8.5KB — 메모리 자동 생성 로그 |

## 사용 가이드

- **9개 실험의 raw numbers 필요**: `subagents/b0a02628.../agent-adeb3b68_timeline.txt` (21KB) 직접 검색
- **데이터 폴더 구조 까먹음**: `agent-a3d16fda_timeline.txt` (12KB)
- **메모리 파일이 어떻게 만들어졌는지 추적**: `c82aa01d/agent-a205b209_timeline.txt`

이 분석 결과들은 이미 `exp_validation_results.md`, `analysis_findings.md`, `attempts_history.md`에 요약 반영됨. raw numbers 원본은 subagent timeline에서만 볼 수 있음.
