# -*- coding: utf-8 -*-
"""P9 추가 child 4장: 함정 사전 / 남은 오차 지도 / 개념·좌표 사전 / 배포 체크리스트."""
import requests, time
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
PARENT = "396ab81d25508135aa98fd9b55b791ac"


def rt(text):
    out = []
    for i, seg in enumerate(text.split("**")):
        if seg:
            out.append({"type": "text", "text": {"content": seg},
                        "annotations": {"bold": i % 2 == 1}})
    return out


def h2(t): return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt(t)}}
def h3(t): return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
def para(t): return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(t)}}
def quote(t): return {"object": "block", "type": "quote", "quote": {"rich_text": rt(t)}}
def bullet(t): return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(t)}}
def todo(t): return {"object": "block", "type": "to_do", "to_do": {"rich_text": rt(t), "checked": False}}
def code(t): return {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": "plain text"}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def new_page(title):
    r = requests.post("https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                      json={"parent": {"page_id": PARENT}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status(); time.sleep(0.4)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 90):
        r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                           headers={**H, "Content-Type": "application/json"},
                           json={"children": blocks[i:i + 90]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:400])
        time.sleep(0.4)


# ═══ ⑧ 함정 사전 ═══
p8 = new_page("⑧ 방법론 함정 사전 — 이 프로젝트가 '직접 밟아보고' 배운 8가지")
append(p8, [
    quote("왜 이 페이지가 중요한가 | 아래 함정들은 이론이 아니라 전부 우리 데이터에서 실제로 발생했고, "
          "각각에 '어떻게 알아챘는지'와 '지금 쓰는 처방'이 붙어 있습니다. 새 실험/새 모델을 시도할 때마다 "
          "이 목록을 체크리스트로 쓰면 같은 함정을 두 번 밟지 않습니다."),
    h2("함정 1 — 지표 게이밍 (Goodhart의 법칙)"),
    para("**\"지표가 목표가 되는 순간, 좋은 지표이기를 멈춘다.\"** 창(0.1초) 점수만 최소화시켰더니 옵티마이저가 "
         "물리가 아니라 채점 방식의 사각지대(0.1초마다 리셋 → 누적 편향에 눈멂)를 공략했습니다: "
         "창 점수 전 그룹 30%+ 개선, 실제 전체 재생은 2.4배 악화 (07-06)."),
    bullet("**알아챈 방법**: 같은 후보를 '다른 종류의 시험'(full-stance)으로 다시 채점"),
    bullet("**처방**: 목적함수에 서로 다른 시간 스케일의 심판을 섞는다 (하이브리드 = 창 + full-stance). 단일 지표 최적화 결과는 항상 의심"),
    h2("함정 2 — 과적합: 'fit이 좋아짐 ≠ 모델이 좋아짐'"),
    para("P5 재적합 raw best −7.4% → held-out 날짜에서 +83% 악화. P6 a_hat도 동일 (−8% → held-out 2.1배). "
         "**두 번 다 하이브리드 목적이었는데도** 과적합됐습니다 — 목적함수를 아무리 잘 설계해도, fit에 쓴 데이터 안에서만 채점하면 뚫립니다."),
    bullet("**처방**: fit에 절대 안 넣는 held-out(우리는 0324 full-stance)을 '게이트'로. 후보 풀을 모아 두고 "
           "'obj 최소'가 아니라 '게이트 통과 중 obj 최소'로 선택 (validation-based selection)"),
    h2("함정 3 — '정체 = local minimum'이라는 착각"),
    para("결과가 계속 비슷하면 웅덩이에 빠졌다고 의심하게 되는데, 우리는 실험으로 반증했습니다 (P8): "
         "26차원 박스 전체 균일 랜덤 1,000점 → **0/1,000이 canonical을 못 이김**, 최고점에서 CMA 재하강해도 "
         "제2의 분지 없음. 게다가 볼록 회귀(원리적으로 local minimum 없음)가 같은 답을 냈습니다."),
    bullet("**진단법**: 정체가 오면 ① 볼록/전역 방법과 교차 확인 ② 다중 시작 프로브 ③ '탈출한 해가 held-out에서도 좋은가' 확인. "
           "셋 다 아니면 정체의 정체는 **데이터의 정보 바닥** — 더 파는 게 아니라 새 데이터/새 물리/새 지표로 가야 함"),
    h2("함정 4 — per-trial 파라미터의 유혹"),
    para("trial마다 파라미터를 따로 주면 점수는 극적으로 좋아집니다 (per-trial tension: 16배). 하지만 그건 "
         "물리를 배운 게 아니라 **각 trial의 잡음을 외운 것** — 새 trial(=transfer)에 쓸 수 없습니다. "
         "날짜별 오프셋 8개도 같은 위험이 있어 '계측 보정(nuisance)'으로 명시하고 ±2° 물리 상한을 둡니다."),
    h2("함정 5 — 카오스 증폭 시험을 모델 품질로 오독"),
    para("full-replay(전체 개루프 재생)는 초기조건·노이즈가 지수적으로 증폭되는 시험입니다. 거기서 오차가 크다고 "
         "모델이 나쁘다고 단정하면 안 되고(일기예보의 2주 한계와 같은 원리), 반대로 창 시험만 믿으면 함정 1에 빠집니다. "
         "**두 시험은 보완재**이고, '환원 불가능한 바닥'(노이즈만으로 생기는 발산)을 정량화하는 트윈-온-트윈 실험이 다음 카드입니다."),
    h2("함정 6 — fudge factor의 숨은 대가"),
    para("tau_scale, motor_tm, alpha 같은 보정 계수는 fit 점수를 즉시 올려주지만, 물리적 근거가 없으면 "
         "**외삽(데이터 밖 영역)에서 무너지고 진짜 원인의 발견을 가립니다.** 결정적 증거: 명시적 4-bar 구조를 넣자 "
         "serial 시절의 큰 knee 마찰(0.99)이 0.057로 **자연 소멸** — 그 '마찰'은 빠진 구조의 변장이었습니다. "
         "현 canonical은 fudge 0개가 원칙."),
    h2("함정 7 — \"다 해봤는데 안 된다\"의 성급함"),
    para("GOAL19에서 under-jump 원인을 '측정 한계'로 결론냈다가, 나중에 무릎 유연성(flex) 하나로 total −23.5%가 "
         "나오며 뒤집혔습니다. **원인을 못 찾음 ≠ 원인이 없음.** 시도 목록을 남기고(무엇을 어떤 범위로 해봤는지), "
         "'안 해본 물리 축'을 주기적으로 재점검하는 것이 처방입니다."),
    h2("함정 8 — 데이터를 늘렸는데 점수가 나빠지는 역설"),
    para("발산이 심한 trial(0421 위치제어 등)을 fit에 넣으면 전체 점수가 그 발산에 오염돼, 데이터 추가가 오히려 "
         "모델을 망치는 것처럼 보였습니다. 원인은 데이터가 아니라 **지표** — multiple shooting으로 지표를 바꾸자 "
         "그 데이터들이 부활해 정보가 됐습니다. '이 데이터는 못 쓴다' 전에 '이 지표로는 못 쓴다'인지 먼저 확인."),
    quote("한 장 요약 | 점수는 항상 의심하고(1,2), 정체의 원인을 실험으로 가려내고(3), trial-개별 보정을 물리로 착각하지 말고(4), "
          "시험의 성격을 알고 읽고(5), 보정 계수보다 구조를(6), 결론은 시도 목록과 함께(7), 데이터 탓 전에 지표 탓(8)."),
])
print("p8 done", flush=True)

# ═══ ⑨ 남은 오차의 지도 ═══
p9 = new_page("⑨ 남은 오차의 지도 + 실험 큐 — 다음에 무엇이 무엇을 결정하나")
append(p9, [
    quote("현재 상태 | canonical 4-bar 트윈은 현 데이터의 정보 한계에 도달 (플래토 4중 확인: 0424+0602 전용 refit 0% · "
          "P5 파라미터 재가중 · P6 a_hat 공동 · P8 다중시작 전패). 남은 개선은 파라미터 튜닝이 아니라 아래 세 오차 거주지를 "
          "겨냥한 새 실험/새 물리/새 지표에서 나옵니다."),
    h2("1. 오차가 사는 곳 세 군데"),
    table([
        ["거주지", "증거", "크기", "겨냥하는 해법"],
        ["① knee 토크 under-read (고부하 마찰 과감산)",
         "3중 수렴: η 사다리(P2) + ahat probe(음의 유효마찰 선호) + P6(a3_k↑, a4_k<0)",
         "0.5~1 Nm급, whip에서 최대", "모터 벤치에서 knee a3/a4 재교정"],
        ["② 세션 드리프트 (벨트 텐션 등)",
         "에너지 비율 0424 0.77~0.97 vs 0602 0.88~1.13 (~20% 이동), 날짜 오프셋 필요성",
         "세션 간 ~20%", "배포 당일 세션 보정 (오프라인 모델로는 원리적 불가)"],
        ["③ whip 구간 (이륙 직전 ~50ms 고속 스냅)",
         "잔차 지도가 고속+고부하에 집중, τ-잔차 계열 4중 기각",
         "dq2 피크의 5~30%", "벤치의 전압한계/back-EMF 영역 측정 + ①과 동일 실험"],
    ]),
    h2("2. 죽은 축 — 더 파도 안 나오는 것들 (재시도 금지 목록)"),
    bullet("관성 텐서 미세조정, tau_scale, motor_tm(LPF), sensor delay, backlash — 전부 drop-test/LODO에서 기각"),
    bullet("26 파라미터 재가중 (P5), a_hat replay-fit (P6 — 시소만 생김), τ-잔차 poly/MLP/sign(v) (4중 기각)"),
    bullet("serial 모델용 Stribeck을 4-bar에 이식 (P4 — 구조의 대리물이었음)"),
    h2("3. 실험 큐 — 소요 시간과 '무엇이 결정되나'"),
    table([
        ["실험", "소요", "결정되는 것", "우선도"],
        ["t_ff 전송 검증 (공중에서 τ 스텝/사인)", "10분",
         "**배포 경로 안전** — desiredTorque가 하드웨어에서 한 번도 안 쓰였음. 이거 없이 배포 불가", "★★★ (배포 전 필수)"],
        ["모터 벤치: knee 단독 토크 실측 (저속~whip 영역)", "반나절",
         "a3_k/a4_k 확정 → 오차 거주지 ①③ 동시 해소. under-jump의 구조적 원인 확정", "★★★"],
        ["세션 보정 프로토콜 리허설 (준최대 점프 1회→재추정)", "10분",
         "오차 거주지 ② 관리 가능성. 배포 정확도 상한", "★★"],
        ["레일 낙하 시험 (다리 고정, 30초)", "5분", "f_rail 직접 측정 (비행 데이터로는 불가 확인됨)", "★"],
        ["카메라-관절 이중측정", "30분", "h 계측 신뢰도, B(관절/카메라) 논쟁 종결", "★"],
        ["식별용 가진(excitation) 궤적 (양 관절 다주파수)", "1시간",
         "백지 관성 식별 가능화 — 백지 System ID의 승격 조건", "★ (연구 확장 시)"],
        ["동일 조건 반복 (예: 90_0.75_90_2 ×5)", "20분", "세션 내 재현성 = 도달 가능 정확도의 바닥", "★"],
    ]),
    h2("4. 데이터 없이 지금 가능한 카드 (컴퓨터만으로)"),
    bullet("**노이즈-바닥 실험 (트윈-온-트윈)**: 트윈 궤적에 실측 노이즈를 주입해 자기 자신을 재생 → 환원 불가능한 발산의 바닥을 계측. "
           "실데이터 오차가 그 바닥에 닿아 있으면 'Mode A 완성 선언' 가능, 갭이 남으면 그 갭이 진짜 남은 모델 오차"),
    bullet("**폐루프 지표 구축**: 배포는 q_des→PD이므로 폐루프 full-horizon이 배포와 동형. 0421 데이터(게인=폴더명)로 즉시 측정 가능 — 단 fitting에는 사용 금지(사용자 원칙), 심판 전용"),
    bullet("**리드스크류 물리식**: 스크류 리드/피치경 스펙만 있으면 η 사다리·자기잠금을 2~3 파라미터 물리식으로 대체 (미분가능 → NLP 직결)"),
    bullet("**serial 마찰 재배분의 NLP 이식**: P4에서 찾은 knee Stribeck+hip 무마찰 조합은 NLP(serial 2-link)용으로 유효"),
])
print("p9 done", flush=True)

# ═══ ⑩ 개념·좌표 사전 ═══
p10 = new_page("⑩ 헷갈리기 쉬운 개념·좌표·이름 사전 — 빠른 참조용")
append(p10, [
    quote("이 페이지는 사전입니다 — 순서 없이, 헷갈릴 때 찾아보는 용도."),
    h2("모드와 시험"),
    table([
        ["용어", "정의", "주의점"],
        ["Mode A", "실측 τ를 시뮬에 재생 (트윈 검증의 기준)", "제어기 없음. '실측 τ가 정확하다'는 가정에 의존 → a_hat 품질이 상한"],
        ["Mode B", "시뮬 안에서 PD로 q_des 추종", "PD가 모델 오차를 흡수 → fitting 금지 (사용자 원칙). 배포 리허설/보고 전용"],
        ["창 (multiple shooting)", "0.1 s 조각, 실측 상태에서 시작", "누적 편향에 눈멂 (함정 1)"],
        ["full-stance", "push-off 전체 개루프", "하이브리드 목적의 두 번째 심판"],
        ["full-replay", "settle~착지 전체 개루프", "카오스 증폭 — 최종 심판이지 fit용 아님"],
        ["held-out", "fit에 안 쓴 데이터로 채점", "현재 0324 full-stance"],
    ]),
    h2("좌표계 — 실수 1순위"),
    code("canonical (데이터 저장 규약)          mujoco (시뮬 내부)\n"
         "q1_mj  = -q1_canonical - π/2          (hip)\n"
         "q2_mj  = -q2_canonical                (knee)\n"
         "dq_mj  = -dq_canonical,   τ_mj = -τ_canonical\n"
         "렌더링(v14 LOCK)도 동일 변환. 어기면 다리가 뒤집혀 보임"),
    bullet("시뮬 시작 자세 (mujoco frame): q1 = -73°, q2 = 146° (= canonical 초기 crouch), base_z 0.192 m"),
    bullet("h_sim = base_z 최대값 (절대 높이). h_real = 카메라 실측 (Real Data.txt 첫 줄) — 0602 실측 점프 0.85~0.98 m"),
    h2("데이터 이름 규칙"),
    table([
        ["표기", "뜻", "예"],
        ["폴더명 (토크 점프)", "hip kp _ hip kd _ knee kp _ knee kd (MIT 모드 게인)", "120_2.2_150_2.5"],
        ["폴더명 (0324/0421)", "P=kp, D=kd", "P60_D1.5"],
        ["currentTorque (raw)", "드라이버의 전류 기반 추정 (iTM)", "a_hat 변환 전 — 직접 쓰지 말 것"],
        ["CurrentTorquePaper / tau_real", "Pure Paper a_hat 변환 후", "canonical의 τ 입력"],
    ]),
    h2("역사적 사실 (분석 해석에 필수)"),
    bullet("**dq_des 전송 버그**: 03.19 / 03.24 / 04.21 세션은 코드 오류로 dq_des=0 전송 — kd가 순수 브레이크로 작동. "
           "04.24부터 정상. 그 날짜들의 τ는 순수 피드백 잔차 성격 → replay 난이도가 높은 근본 이유"),
    bullet("**t_ff(피드포워드 토크)는 하드웨어에서 한 번도 사용된 적 없음** — 로그의 desiredTorque는 참고용 기록일 뿐. "
           "τ 직접 배포 전 전송 검증 필수"),
    bullet("**W+ 법칙**: 게인↑ → 추종 좋음 → 일(W+) 작음 → replay 재현 나쁨 (corr −0.86). '잘 추종한 trial이 더 어렵다'는 역설의 정체"),
    bullet("**0602 = 기준 세션**: 캘리브레이션 기준(오프셋 0), 최고 재현 날짜. 세션 간 에너지 비율은 0424 대비 ~20% 높음"),
    bullet("**s2s cycle 정의**: valley 기반 분할 + 앞뒤 0.5 s 패딩 (2026-06-23 canonical lock)"),
    h2("자주 쓰는 수치 한 줄씩"),
    bullet("링크: L1=L2=250 mm, crank(l_i)=rocker(l_o)=30 mm, 발 실린더 r=21 mm"),
    bullet("모터: AK80-9 **V2** (V3 아님) — peak 18 Nm, rated 9 Nm, 기어비 9, KT 0.091"),
    bullet("총질량 ~3.58 kg (시뮬 합), 데이터 500 Hz, 시뮬 2 kHz"),
    bullet("갤러리 성적 (full-replay q2): 0602 3.9° / 0424 10.1° / 0324 11.9° / 0421 50.8°, h_ratio 0.88~0.94"),
])
print("p10 done", flush=True)

# ═══ ⑪ 배포 체크리스트 ═══
p11 = new_page("⑪ 실 로봇 배포 체크리스트 — 다음 실험실 세션용 (NLP 궤적 → 실제 점프)")
append(p11, [
    quote("목적 | G20에서 만든 배포 CSV(70/85/100% 준최대 궤적)를 실 로봇에서 실행하는 날을 위한 순서표. "
          "각 단계에 '왜'가 붙어 있습니다. 예상 소요: 사전검증 30분 + 본실험 1시간."),
    h2("0. 하드웨어 사전 검증 (다리 공중, 절대 생략 금지)"),
    todo("**t_ff 전송 확인** — MIT 모드로 τ_ff 스텝(±1, ±3 Nm)과 사인(1 Hz) 전송, 로그의 실행 토크와 대조. "
         "이 경로는 지금까지 한 번도 하드웨어에서 안 쓰였음 (로그 desiredTorque는 기록 전용이었음)"),
    todo("dq_des 전송 확인 — 04.24 수정이 현재 펌웨어에도 살아있는지 (사인 q_des 추종에서 kd 거동 확인)"),
    todo("엔코더 영점: 전원 인가 자세 표준화 (0602 프로토콜과 동일 자세에서 인가)"),
    todo("비상 정지·토크 리밋 설정 확인 (peak 18 Nm의 80% = 14.4 Nm 권장)"),
    h2("1. 세션 보정 (10분) — 오프라인 트윈이 원리적으로 못 하는 부분"),
    todo("준최대(70%) 점프 1회 실행 → q/dq/τ 로그 확보"),
    todo("그 1회로 세션 파라미터만 재추정: 엔코더 오프셋 (q1, q2), 세션 토크 스케일 1개 — 모델 구조·나머지 26개는 그대로"),
    todo("재추정 후 트윈에서 해당 trial replay가 0602 수준(q2 ~4°)으로 붙는지 확인 — 붙으면 진행, 안 붙으면 원인 기록 후 중단"),
    para("근거: 세션 드리프트 ~20%는 어떤 고정 모델도 예측 불가 (오차 거주지 ②). 항공기가 매 비행 전 "
         "무게·무게중심을 재는 것과 같은 절차입니다."),
    h2("2. 본 실험 (70 → 85 → 100% 순서)"),
    todo("각 단계: 트윈 리허설 예상치(h, 피크 τ, 이륙 시각)를 종이에 먼저 적고 → 실행 → 실측과 나란히 기록"),
    todo("**안전 PD를 약하게 걸고 kp·e 기여분을 로깅** — PD 기여 ≈ 0이면 open-loop 모델이 옳았다는 정량 증명, "
         "크면 그 크기·방향이 다음 모델 개선의 직접 타깃 (\"PD가 흡수한 것을 측정으로 뒤집기\")"),
    todo("GRF·카메라 동시 기록 (h_real 정의 일관성: Real Data.txt 규약 유지)"),
    todo("단계별 통과 기준: h가 트윈 예상 ±10% 안 → 다음 단계. 밖 → 중단하고 로그 확보"),
    h2("3. (선택) 같은 궤적 반복 — open-loop ILC"),
    todo("100% 궤적을 2~3회 반복하며 피드포워드만 보정: τ_{k+1}(t) = τ_k(t) + L·(q_real(t) − q_ref(t)), L≈0.3·kp_soft"),
    para("PD 없이 순수 τ 수정이라 Mode A 철학과 양립 — '이 궤적에서 토크 일치'로 가는 문헌상 가장 확실한 마지막 단계."),
    h2("4. 돌아와서 할 일"),
    todo("로그 → canonical 포맷 변환 → 신규 세션으로 트윈 held-out 채점 (fit 아님!)"),
    todo("PD 기여분 분석 → 오차 거주지 지도(⑨) 업데이트"),
    todo("성공/실패 무관: 세션 보정 전후 파라미터 기록 (세션 드리프트 통계 축적)"),
    h2("기대치 (G20 산출)"),
    table([
        ["항목", "값", "근거"],
        ["폐루프 1차 시도 예상 h", "0.95~0.97 m", "G20 NLP+트윈 리허설"],
        ["open-loop(τ만) 예상 오차", "폐루프보다 큼 — 세션 보정 품질에 좌우", "0602급 세션이면 q2 ~4°"],
        ["미개척 헤드룸", "+14 cm (hip 8~14 rad/s 영역)", "G20 헤드룸 분석 — 단 그 영역은 데이터 밖 = 외삽 위험도 함께"],
    ]),
])
print("p11 done", flush=True)

# parent에 안내 추가
def append_parent(blocks):
    r = requests.patch(f"https://api.notion.com/v1/blocks/{PARENT}/children",
                       headers={**H, "Content-Type": "application/json"}, json={"children": blocks})
    r.raise_for_status()

append_parent([
    h2("추가 페이지 (⑧~⑪) — '알아두면 좋은 것들'"),
    bullet("**⑧ 방법론 함정 사전** — 게이밍·과적합·local minimum 착각·per-trial 유혹 등, 직접 밟아본 8가지와 처방"),
    bullet("**⑨ 남은 오차의 지도 + 실험 큐** — 오차 거주지 3곳, 죽은 축(재시도 금지 목록), 실험별 소요·결정 사항·우선도"),
    bullet("**⑩ 개념·좌표·이름 사전** — Mode A/B, 좌표 변환, 폴더명 규칙, dq_des 버그, W+ 법칙, 자주 쓰는 수치"),
    bullet("**⑪ 실 로봇 배포 체크리스트** — t_ff 검증부터 세션 보정, 70/85/100% 순서, ILC까지 체크박스"),
])

for name, pid in [("p8", p8), ("p9", p9), ("p10", p10), ("p11", p11)]:
    r = requests.get(f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100", headers=H).json()
    print(f"{name}: {len(r.get('results', []))} blocks", flush=True)
print("DONE")
