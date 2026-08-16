# GOAL7 — Autonomous evolution loop until 2026-06-07 KST 12:00

## ★ 미션
**현재 KST 일요일 04:06, 종료 KST 12:00 — 약 8시간 자율 진행**. Mode A와 Mode B 모두를 각각 iterative하게 개선. 매 iteration:
1. BO/실험 실행
2. 결과 분석 (RMSE, GRF peak, chattering, tau matching)
3. 새 insight 발견 → `MASTER_FINDINGS.md` 업데이트
4. (필요시) 웹/논문/오픈소스 검색
5. 다음 Stage 코드 작성 + 실행
6. Notion 페이지 생성 (GOAL6 parent 아래)
7. Git commit

---

## ★ 시작 시 필수 확인 (절대 안 하면 안 됨)

1. **읽어**: `C:\Users\junho\Desktop\jump_opt\MASTER_FINDINGS.md` — 지금까지 발견된 모든 사실 통합 문서
2. **읽어**: `C:\Users\junho\Desktop\jump_opt\GOAL6_PROMPT.md` — 이전 goal context
3. **메모리 확인**: `MEMORY.md` index에서 관련 .md 모두 (mujoco_range_bug, ak80_9_torque_calibration, goal6_findings 등)
4. **현재 best XML 확인**: `goal6/stage9/urdf/leg_g6s9_best.xml` (Mode B), `goal6/stage7/urdf/leg_g6s7_best.xml` (Mode A)
5. **데이터 확인**: `goal5/data_loaded.npz` (6 trial + ref)

---

## ★ 진행 원칙 (절대 지킴)

### Hard constraints (사용자 명시, 절대 위반 금지)
- **l1, l2, l_c, g, l_o FIXED** — BO 안 함
- **CVT/변속 없음** — 단순 multi-body
- **Pure PD only** — tau = α_kp·kp·err + α_kd·kd·err_dot (NO feedforward, no α_ff)
- **±18 Nm sat 가정 폐기** — 절대 다시 추가 금지
- **range="-3 3" 절대 추가 금지** — hidden bug
- **`<asset>`, `<visual>`, `<light>` 항상 XML에 포함** — GIF 어두움 방지
- **Mass baseline**: M=1.02, m1=1.05213, m2=0.237, m_c=0.80898, m_p=0.14977 (사용자 명시 진짜값, ±20% 안에서만 fit)
- **Sphere foot** — Capsule 안 됨 (사용자 명시)

### Mode 구분
- **Mode A (open-loop)**: ctrl = tau_real_measured. dynamics 자체 검증
- **Mode B (closed-loop)**: ctrl = α_kp·kp·err + α_kd·kd·err_dot (pure PD), motor LPF
- 두 mode 각각 별도로 발전 (Mode A는 odd stages: 11, 13, 15..., Mode B는 even: 12, 14, 16...)

### Score 가이드
- Mode A: w_q1=100, w_q2=100, w_dq=1, w_grf=5 (tau는 입력값이라 무관)
- Mode B: w_q1=100, w_q2=100, w_dq=1, w_tau=20, w_grf=5
- Per-trial weighting은 신중히 (Stage 10에서 trade-off 발생)

---

## ★ 시간 예산 (8시간 = 480분)

- iteration 1개 = 60-90분
- → 약 5-7 iterations
- Mode A 2-3 iter (Stage 11, 13, 15)
- Mode B 3-4 iter (Stage 12, 14, 16, 18)

## ★ External Findings Notion 페이지 (매 iteration 후 업데이트)

**Page ID**: `377ab81d-2550-81d5-bd89-dc3106f7ff64`
**URL**: https://app.notion.com/p/GOAL7-External-Findings-377ab81d255081d5bd89dc3106f7ff64

매 iteration 새 발견을 이 페이지에 append:
- 논문/preprint 인용 + 적용 방법
- 오픈소스 GitHub repo URL + 관련 코드 패턴
- MuJoCo docs/forum 발견
- Blog/SO 디버깅 패턴

코드 패턴:
```python
import requests
TOKEN = "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"
EXT_FINDINGS_ID = "377ab81d-2550-81d5-bd89-dc3106f7ff64"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
           "Notion-Version": "2022-06-28"}
new_blocks = [
    {"object":"block","type":"heading_3",
     "heading_3":{"rich_text":[{"type":"text","text":{"content":f"[{ts}] Stage {N}"}, "annotations":{"bold":True}}]}},
    {"object":"block","type":"bulleted_list_item",
     "bulleted_list_item":{"rich_text":[{"type":"text","text":{"content":"출처: "}, "annotations":{"bold":True}},
                                         {"type":"text","text":{"content":url}}]}},
    # ... 핵심 인사이트, 적용 방법, 결과
]
requests.patch(f"https://api.notion.com/v1/blocks/{EXT_FINDINGS_ID}/children",
               headers=HEADERS, json={"children": new_blocks})
```

매 iteration 후 동시에:
1. MASTER_FINDINGS.md 업데이트 (local)
2. External Findings Notion 페이지 update (사용자가 phone에서 확인 가능)

## ★ 진행 protocol (autonomous loop)

### 매 iteration 단위 (약 60-90분):

#### 1. 분석 (10분)
- 이전 stage 결과 plot 검토
- 어디서 어떤 trial이 안 맞는지 정량 (RMSE, GRF range over %)
- `MASTER_FINDINGS.md`에 결과 append

#### 2. 가설 + 외부 검색 (15-30분, 필요시)
- 새 insight 필요하면:
  - WebFetch agent로 논문/블로그 검색 (예: "MuJoCo contact tuning hopping robot")
  - mujoco_menagerie GitHub 다른 robot의 XML 패턴 검색
  - AK80-9 motor model 더 정확한 적용 검색
- 발견한 사실 `MASTER_FINDINGS.md`의 "External findings" 섹션에 append

#### 3. 다음 stage 설계 (10분)
- 변경할 변수/범위/score 결정
- 이전 best XML/study를 warmstart로 사용 (Optuna seed_with_study)

#### 4. BO 실행 (30-60분)
- Background로 실행 (200-400 trials)
- 진행 monitoring (every 25 trials best print)

#### 5. 결과 plot + 페이지 (15-20분)
- 6 trial × 4 metric plot (default color, trial별 별도 image)
- Notion 페이지 (GOAL6 parent 아래)
- Code toggle 포함

#### 6. 검증 (5분)
- 페이지 children GET, image block status="uploaded" 확인
- 모든 이미지 시각 확인 (조명 OK 등)

#### 7. Git commit
- 새 stage code + plots + xml + memory 업데이트
- Auto-commit (사용자 선호)

### Wakeup 타이밍
- ScheduleWakeup으로 1200초(20분) 단위 self-check
- BO 진행 중이면 background polling
- BO 완료 시 즉시 다음 step

---

## ★ Improvement directions (시도할 것들)

### Mode B 우선 시도 (가장 큰 영향)

1. **GRF peak over-shoot 해결**
   - solref_tc range 더 wide ([0.02, 0.2])
   - solref_d over-damped 강화 ([1.5, 5.0])
   - imp_mid wide ([0.01, 0.2])

2. **Per-trial weighting 약하게**
   - 60×1.0, 90×1.0, 120×1.05, 150_250×1.1, 150_500×1.2

3. **AK80-9 a_hat 5-param motor model**
   - `ak80_9_torque_calibration.md` 참조
   - LPF tm 대신 paper a_hat 적용
   - `tau_real = a₀ + a₁·gr·kt·i - a₂·gr·|i|·i - a₃·sign(v)·smooth(v) - a₄·|i|·sign(v)·smooth(v)`

4. **Stribeck friction**
   - frictionloss + viscous + Stribeck (exp decay)
   - MuJoCo direct 지원 안 함 → 외부 force로 추가

5. **Joint armature 더 정확**
   - AK80-9 rotor inertia × gear² 정확히 계산
   - `armature ≈ 9² · 6.04e-5 = 0.0049 kg·m²` (paper 기반)

6. **Hunt-Crossley contact**
   - MuJoCo solref/solimp로 근사

### Mode A 우선 시도

1. **Mass/CoM/Inertia 정밀**: ±5% (현재 ±10%)
2. **Foot radius/position fit**: 현재 fixed (사용자 명시 X, fit 가능)
3. **Joint friction nonlinear**: Stribeck-like

---

## ★ Stage 인프라

### 파일 경로
- Stages: `goal6/stage11/`, `goal6/stage12/`, ...
- Master: `Desktop/jump_opt/MASTER_FINDINGS.md`
- 새 페이지 부모: `377ab81d-2550-818d-aee1-ddea3ff9d64e` (GOAL6 parent)

### BO 인프라
- Optuna BO single-process (MuJoCo pickle 안 됨)
- ScheduleWakeup으로 polling
- 결과: `stage{N}_study.pkl`, `stage{N}_rmse.json`, `leg_g6s{N}_best.xml`

### Notion 패턴
- file_uploads + GET status="uploaded" 검증
- 24 trial별 image (default color, trial별 별도)
- GIF (조명 정상 확인)
- Code toggle (BO + XML)
- 체크리스트 + Stage 비교 표

### Master findings 업데이트
```python
# 매 stage 끝에:
with open('Desktop/jump_opt/MASTER_FINDINGS.md', 'a') as f:
    f.write(f"\n### Stage {N} ({timestamp})\n")
    f.write(f"- RMSE 결과: ...\n")
    f.write(f"- 새 insight: ...\n")
    f.write(f"- 외부 발견: ...\n")
```

---

## ★ 중간 점검

### 매 3 stage마다
- Master findings 정리 (중복 제거, 우선순위 재배치)
- Notion master overview 페이지 업데이트
- Memory 업데이트

### 막힐 때 (Plateau, 같은 결과 반복)
- ultrathink로 깊이 분석
- 웹/논문 검색 강제 (적어도 1번)
- 이전 가설 다시 검토 (혹시 폐기한 게 사실 맞았나?)
- 사용자에게 알림 (필요시)

---

## ★ 종료 조건 (KST 12:00 도달)

- 모든 stage 결과 통합 보고서 (Notion + memory)
- Best Mode A + Best Mode B 최종 XML
- `MASTER_FINDINGS.md` 완성판
- 사용자가 깨어나면 한 눈에 진행 상황 + 최종 best 확인 가능하게

---

## ★ 진행 중 막히면 무조건 ultrathink

(GOAL6_PROMPT.md의 ultrathink 가이드 그대로 적용)
- BO 50 trial plateau → ultrathink + 변수/score 재설계
- 같은 trade-off 3회 반복 → 가설 자체 재검토
- 사용자 관찰과 sim 결과 모순 → 즉시 격리 테스트
- mj_solveM vs mj_forward 비교 항상 의심

---

## ★ 노션 페이지 품질 기준 (절대 양보 금지)

**원칙**: 이 페이지만 읽어도 그 stage의 내용을 완전히 마스터하고 이해할 수 있어야 함. 외부 검색 안 하고도.

**참조 모델**: `Concept Range XML Bug` 페이지 (https://app.notion.com/p/Concept-Range-XML-Bug-377ab81d255081789cc3db76bc25b540) — 이 수준의 자세함을 매 stage 페이지에 적용.

### 필수 구성 (매 페이지)

#### 1. 한 줄 요약 (callout, yellow_background)
- TL;DR. 이 페이지에서 발견한 핵심 한 줄.
- 예: "Stage N — α_kp 0.49로 fit해서 hip τ 41% 개선. ff 빼니 GRF 정직하게 over-shoot 노출됨."

#### 2. 이 페이지를 읽으면 얻는 것 (bulleted list)
- 5-7개 항목으로 페이지 가치 명시
- 독자가 무엇을 이해하게 될지

#### 3. 📚 용어 정리 (필수, 매 페이지)
- 페이지에서 등장하는 모든 전문 용어
- 5-10개 정도. **각 용어 한 줄로 설명 + 우리 컨텍스트에서 의미**
- 예시:
  - `Pure PD` — position + velocity feedback only. 외부 feedforward 없음
  - `α_kp` — 폴더 PD를 실 mechanical PD로 변환하는 scaling factor
  - `tm (motor LPF)` — motor electrical dynamics 1차 시상수

#### 4. 사전 지식 (필요시, sub-heading)
- 처음 보는 사람이 이해 못할 개념 있으면 추가 설명 섹션
- 예: "MuJoCo의 solref/solimp가 뭔지", "BO TPESampler가 뭔지"

#### 5. 가설 / 수식 / 코드 블록
- 수식은 code block (lang="plain text")
- XML은 code block (lang="html")
- Python 코드는 lang="python"
- **수식 위/아래에 한 줄로 설명 + 우리 케이스 값 대입 예시**

#### 6. 📊 그래프 (caption이 핵심)
**모든 image block의 caption에 반드시 포함**:
- **X축, Y축이 무엇인지** (단위 포함)
- **선/막대의 색깔이 무엇 의미하는지** (실선 = real, 점선 = sim 등)
- **그래프에서 보이는 패턴** (어디서 over, 어디서 under)
- **★ 의미** (이 그래프가 우리에게 무엇을 알려주는지)
- **숫자 인용** (구체적 값으로 패턴 설명)

좋은 caption 예시:
```
"Plot 3: 200ms passive simulation
X축: 시간 (ms). Y축: joint angle (rad).
빨간 선 = range='-3 3' 있음. 시작 -1.274에서 100ms에 거의 0으로 'drift'.
파란 선 = range 제거. q1이 init 그대로 유지.
★ 의미: 무중력에서도 range 있으면 leg가 폭발적으로 움직임. 즉 limit force가 force vector를 만들고 있다."
```

나쁜 caption 예시 (안 됨):
```
"Plot 3 비교"  ← 정보 부족
"q1 evolution"  ← 의미 누락
```

#### 7. 디버깅 / 분석 chain (필요시)
- 막힌 문제 → 어떻게 분석 → 진단 → fix 시도 → 결과 → 다음
- 사용자가 비슷한 문제 만났을 때 따라할 수 있도록 step-by-step

#### 8. 비교 표 (이전 stage vs 현재)
- RMSE 표 (각 trial × 각 metric)
- "Stage X vs Stage Y" 표 (개선 % 표시)

#### 9. ✅ 체크리스트
- 검증 항목 / 기준 / 결과 / 상태 표
- ✅ ⚠ ❌ 명확히

#### 10. 💡 결론 / 교훈 / 다음 단계
- 무엇 발견 / 무엇 안 됨 / 다음 stage에서 시도할 것

#### 11. 💾 코드 토글
- BO 코드 (full)
- Best XML (full)
- 필요시 plot 코드도

#### 12. 외부 참조 (논문/오픈소스 사용한 경우)
- 참고한 paper/repo/blog URL
- 어떻게 우리 코드에 적용했나
- External Findings 페이지에도 같은 정보 cross-link

### 📋 페이지 만들 때 체크리스트

만들기 전:
- [ ] 용어 정리 5+ 항목 준비
- [ ] 그래프 caption 미리 작성 (X/Y축, 색깔, 의미, 숫자)
- [ ] 이전 stage 비교 표 데이터 준비

만든 후 검증:
- [ ] blocks 개수 = 작성한 개수 (chunk 누락 없음)
- [ ] 모든 image status="uploaded"
- [ ] GIF 조명 정상 (XML에 `<visual>` `<light>` `<asset>` 있나?)
- [ ] **용어 정리 섹션 존재 확인**
- [ ] **각 image caption에 X/Y축, 색깔, ★의미 포함 확인**
- [ ] 코드 토글 작동 (펼쳤을 때 코드 보임)
- [ ] 비교 표 / 체크리스트 존재
- [ ] 새 외부 정보 사용했으면 External Findings 페이지에도 append

---

## ★ 사용자 깨어났을 때 보여줄 것

1. `MASTER_FINDINGS.md` 최종판 (모든 발견 통합)
2. Best Mode A + Best Mode B 결과 표
3. 진행한 stage 리스트 + 각 페이지 URL
4. 새로 발견한 외부 정보 (논문, 코드, 블로그)
5. 다음 단계 추천 (사용자 결정 요청)
