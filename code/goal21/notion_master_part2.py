# -*- coding: utf-8 -*-
"""마스터 클래스 Part 2 — ⑤gradient ⑥4족MPC ⑦RL ⑧처방전."""
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")


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
def callout(t, emoji="💡"):
    return {"object": "block", "type": "callout", "callout": {"icon": {"emoji": emoji}, "rich_text": rt(t)}}
def code(t): return {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": "plain text"}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def img(p):
    r = requests.post("https://api.notion.com/v1/file_uploads",
                      headers={**H, "Content-Type": "application/json"}, json={})
    r.raise_for_status()
    uid, url = r.json()["id"], r.json()["upload_url"]
    with open(p, "rb") as f:
        requests.post(url, headers=H, files={"file": (Path(p).name, f, "image/png")}).raise_for_status()
    return {"object": "block", "type": "image", "image": {"type": "file_upload", "file_upload": {"id": uid}}}


def new_page(parent, title):
    r = requests.post("https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                      json={"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status(); time.sleep(0.4)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 80):
        r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                           headers={**H, "Content-Type": "application/json"},
                           json={"children": blocks[i:i + 80]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:500])
        time.sleep(0.4)


ids = json.load(open(Path(__file__).parent / "master_pages_part1.json"))
parent = ids["parent"]

# ════════════════ ⑤ Gradient의 물리학 ════════════════
p5 = new_page(parent, "⑤ Gradient의 물리학 — 세 가지 추정기와 두 마리 괴물 (접촉 kink · 카오스)")
print("c5", p5, flush=True)
append(p5, [
    quote("용어 | **pathwise/해석 gradient**: 시뮬 연산 전체를 사슬법칙으로 미분 (자동미분·미분가능 시뮬). "
          "**유한차분(FD)**: 파라미터를 ±h 흔들어 (J(θ+h)−J(θ−h))/2h. **score function/0차**: 동역학은 안 미분하고 "
          "'무엇을 샘플했는지'의 확률만 미분 (REINFORCE). **BPTT**: 시간을 거슬러 미분을 전파. "
          "**Lyapunov 지수 λ**: 초기조건 오차가 e^{λt}로 커지는 비율 — 카오스의 척도."),
    h2("1. gradient를 얻는 세 가지 길 — 편향/분산 손익"),
    table([
        ["추정기", "동역학 미분?", "편향", "분산", "접촉 kink에서", "대표 사용처"],
        ["해석/AD (pathwise)", "예 (사슬법칙)", "스무딩 없으면 무편향", "낮음(매끄러울 때)", "정의 불가/한쪽 기울기 — 스무딩 필요(=편향 도입)", "MJX/Brax/Dojo, 우리 CasADi NLP(모델이 원래 매끄러움)"],
        ["유한차분", "수치로", "O(h²)", "h로 트레이드오프", "h가 kink에 걸리면 잡음/편향", "MJPC iLQG (mjd_transitionFD)"],
        ["0차/score function", "**아니오**", "무편향(기대값 기준)", "높음 — 샘플로 눌러야", "**기대값이 스무딩 → 안전**", "RL(PPO), CMA, MPPI"],
    ]),
    para("직관: pathwise는 '지도의 등고선을 읽고' 가는 것 — 지도(모델)가 매끄러우면 최강. 0차는 '주변에 공을 여러 개 "
         "굴려보고' 가는 것 — 지도가 찢어져 있어도(불연속) 공들의 평균은 부드럽게 굴러갑니다."),
    h2("2. 괴물 1 — 접촉 kink: '기울기'가 존재하지 않는 지점"),
    img(FIG / "m4_kink.png"),
    para("왼쪽: 접촉 전환(닿느냐 마느냐) 경계에서 비용은 꺾입니다. 이때 '진짜 기울기'는 왼쪽 벼랑과 오른쪽 벼랑 두 개 — "
         "AD는 그중 하나를 임의로 돌려주고, 그 방향으로 최적화하면 경계를 못 넘습니다. 오른쪽: 유한차분은 스텝 h의 딜레마 — "
         "작으면 한쪽 벼랑만, 크면 편향. 반면 노이즈로 흐린 기대 비용 E[J(θ+ε)]는 매끄럽고(주황), 그 기울기(bundled "
         "gradient)가 0차 방법이 암묵적으로 따르는 방향입니다. 이 등가성이 Suh, Simchowitz, Zhang, Tedrake 2022 "
         "(ICML, arXiv:2202.00817)의 골자 — 결론: **미분가능 시뮬레이터가 항상 더 나은 policy gradient를 주지 않는다.** "
         "저자들은 둘을 섞는 α-차수 추정기를 제안했습니다."),
    bullet("미분가능 시뮬 진영의 대응: 접촉을 부드럽게(soft) 만들어 미분을 살림 — MJX·Brax가 이 노선. 대가 = 물리 편향 "
           "(너무 부드러우면 발이 '젤리 바닥'을 밟는 문제를 최적화하게 됨)."),
    bullet("Dojo (Howell et al. 2022)는 다른 노선: hard 접촉 문제의 해에 암시적 함수 정리를 적용해 '해 근방의 매끄러운 "
           "gradient'를 뽑음 — 정확하지만 느림."),
    bullet("관련 필독: Metz et al. 2021 \"Gradients are not all you need\" — 미분이 '있다'와 '유용하다'는 다르다는 "
           "실증 모음; Parmas et al. 2018 PIPPS — pathwise/score를 섞는 total propagation."),
    h2("3. 괴물 2 — 카오스: 긴 horizon을 통과한 미분은 숫자가 아니다"),
    img(FIG / "m5_chaos.png"),
    para("민감도 ∂x(T)/∂x(0)는 스텝별 야코비안의 곱 — 카오스 시스템에서는 e^{λT}로 폭발합니다. 위 이중진자에서 λ≈수 /s: "
         "4초면 민감도가 10⁴~10⁶배. gradient도 같은 사슬을 타므로 **BPTT로 긴 rollout을 미분하면 방향이 사실상 난수**가 "
         "됩니다 (분산 폭발). 우리 프로젝트의 실물 증거가 바로 full-replay 발산이고 — 우리가 창(0.1s) 평가를 쓰는 이유, "
         "즉 **multiple shooting은 카오스 사슬을 끊는 gradient 처방**이기도 합니다."),
    bullet("처방 목록: horizon 절단(iLQG의 짧은 horizon), multiple shooting(사슬 절단 = 우리 창), 감쇠/정규화, "
           "그리고 아예 0차로 (RL이 동역학을 미분하지 않아 이 문제를 원천 회피)."),
    h2("4. 방법 지도 — 어디에 무엇이 사는가"),
    img(FIG / "m8_map.png"),
    para("가로축 = 미분 정보 사용량, 세로축 = 온라인성. 접촉이 많고 horizon이 길수록 왼쪽(0차)이 유리해지고, 모델이 "
         "매끄럽고 정밀 제약이 필요할수록 오른쪽 아래(NLP)가 유리합니다. 우리 프로젝트는 두 극단을 하나씩 씁니다 — "
         "식별=CMA(왼쪽 아래), 궤적=NLP(오른쪽 아래). 이 배치가 우연이 아니라 두 괴물을 피하는 필연임을 이 페이지가 설명합니다."),
    quote("한 장 요약 | gradient는 세 방법으로 만들고(해석/FD/0차), 접촉 kink는 '미분의 정의'를, 카오스는 '미분의 크기'를 "
          "부순다. 스무딩(=0차의 기대값, 또는 soft contact)과 사슬 절단(=multiple shooting, 짧은 horizon)이 두 괴물의 "
          "표준 처방이며, 우리 파이프라인의 창-평가·CMA·phase-NLP는 정확히 그 처방의 조합이다."),
])

# ════════════════ ⑥ 4족 MPC 해부 ════════════════
p6 = new_page(parent, "⑥ 4족 보행 MPC 해부 — GitHub의 그 코드들은 실제로 무엇을 푸는가")
print("c6", p6, flush=True)
append(p6, [
    quote("용어 | **SRB(single rigid body)**: 로봇 전체를 질량·관성 하나로 뭉친 축소 모델. **게이트 스케줄러**: 각 발의 "
          "접촉/스윙 타이밍표. **WBC(whole-body control)**: 계획된 힘·가속도를 전신 관절토크로 변환하는 고주기 제어. "
          "**receding horizon**: 매 스텝 다시 최적화하고 첫 입력만 쓰는 MPC 원리."),
    h2("1. 큰 그림 — 'MPC 안에 시뮬레이터는 없다'"),
    img(FIG / "m7_mpc.png"),
    para("MIT Cheetah 3/Mini-Cheetah 계열 (Di Carlo et al. 2018, \"Dynamic Locomotion in the MIT Cheetah 3 Through "
         "Convex Model-Predictive Control\", IROS; 코드 mit-biomimetics/Cheetah-Software)의 구조가 사실상 업계 표준입니다. "
         "질문하신 '그 GitHub 논문과 코드'의 답: **MuJoCo(또는 실 로봇)는 제어 대상(플랜트)일 뿐이고, MPC 내부 모델은 "
         "손으로 쓴 축소 해석식**입니다."),
    h2("2. 왜 그렇게 하나 — 세 가지 절묘한 근사"),
    bullet("**모델 축소 (전신 → SRB)**: 다리 질량(~10%)을 무시하고 몸통 하나로: ṗ=v, m·v̇=Σf−mg, d(Iω)/dt≈Σrᵢ×fᵢ. "
           "18자유도 비선형이 13상태 선형(yaw 선형화 후)으로 — 우리로 치면 로봇 전체를 base 하나로 뭉친 셈."),
    bullet("**접촉 스케줄 고정**: 게이트(trot 등)를 미리 정함 → 접촉의 if문이 사라져 문제가 **볼록 QP**가 됨. "
           "MPC는 '어느 발을 언제'는 안 풀고 '얼마나 세게 밀지'만 풂 — ③의 phase-고정과 같은 트릭."),
    bullet("**계층 분업**: QP가 놓친 전신 디테일은 WBC(0.5~1kHz)가, 스윙발은 Raibert 휴리스틱 + PD가 처리 "
           "(Kim et al. 2019, \"Highly Dynamic Quadruped Locomotion via Whole-Body Impulse Control\"). "
           "정밀도는 **피드백(매 스텝 재계획)**이 벌충 — 모델이 조금 틀려도 25~100Hz 재계획이 오차를 계속 지움."),
    h2("3. 계보 지도 — 대표 코드 6종"),
    table([
        ["코드/논문", "MPC 모델", "solver", "특징"],
        ["Cheetah-Software (MIT)", "SRB 선형화", "QP (qpOASES)", "convex MPC + WBIC — 백플립까지"],
        ["OCS2 / legged_control (ETH/커뮤니티)", "centroidal~전신", "SLQ/DDP", "ROS 통합, ANYmal 계열 실기"],
        ["TOWR (Winkler 2018)", "centroidal + 발위치", "IPOPT", "게이트·접촉 스케줄까지 최적화 (오프라인)"],
        ["Crocoddyl (Mastalli 2020)", "전신 (Pinocchio)", "FDDP", "전신 DDP의 표준 라이브러리"],
        ["MJPC (DeepMind 2022)", "**MuJoCo 자체**", "iLQG(FD)/Predictive Sampling", "예외 — 시뮬=모델, 실시간 (arXiv:2212.00541)"],
        ["legged_gym + rsl_rl (ETH)", "모델리스 (RL)", "PPO", "MPC 대신 정책 학습 노선 (⑦)"],
    ]),
    h2("4. 우리 프로젝트와의 1:1 대응 — 그리고 결정적 차이"),
    table([
        ["4족 MPC", "우리", "코멘트"],
        ["SRB 축소모델", "4-bar 축소좌표 해석식", "우리 쪽이 훨씬 정밀 (전신=단일다리라 가능)"],
        ["게이트 스케줄러", "phase 고정 (스탠스→비행)", "동일한 트릭"],
        ["QP 반력 → WBC 토크", "τ 직접 최적화", "단일 다리라 계층 불필요"],
        ["**25~100Hz 재계획 (피드백)**", "**오프라인 1회 + open-loop 배포**", "★ 본질적 차이 — 그들은 모델 오차를 피드백이 지우고, 우리는 트윈 정밀도가 전부"],
    ]),
    callout("이 차이가 우리 연구의 정체성입니다: 4족 MPC는 '거친 모델 + 강한 피드백', 우리는 '정밀한 모델 + 무피드백'. "
            "Mode A 고집(정확한 트윈)이 필요한 이유이자, 언젠가 온라인 재계획(MPPI/짧은 MPC)을 붙이면 트윈 요구 정밀도가 "
            "완화되는 이유이기도 합니다 — 두 노선은 상보적.", "🧭"),
    quote("한 장 요약 | 4족 MPC의 비밀은 '시뮬레이터로 MPC를 푸는 것'이 아니라 '풀 수 있게 문제를 깎는 것' — 모델 축소, "
          "스케줄 고정, 계층 분업, 그리고 피드백이 나머지를 지운다. MJPC만이 예외적으로 시뮬을 직접 모델로 쓰는 새 노선이다."),
])

# ════════════════ ⑦ RL 경로 ════════════════
p7 = new_page(parent, "⑦ MuJoCo에서 policy 만들기 — RL 경로의 해부와 우리 문제에의 적합성")
print("c7", p7, flush=True)
append(p7, [
    quote("용어 | **policy π(s)→a**: 상태를 행동으로 사상하는 함수(보통 신경망). **PPO/SAC**: 표준 정책 최적화 알고리즘. "
          "**domain randomization(DR)**: 학습 중 물리 파라미터를 무작위로 흔들어 강건성을 강제. "
          "**teacher-student**: 특권 정보로 배운 교사를 관측만으로 모방하는 학생으로 증류."),
    h2("1. 파이프라인 — 정책은 이렇게 만들어진다"),
    bullet("① 환경 정의: 관측(관절각·속도·IMU·명령), 행동(보통 관절 목표각 → 내부 PD가 토크로), 보상(속도 추종−에너지−자세벌점)"),
    bullet("② 병렬 시뮬: Isaac(PhysX GPU)·MJX/Brax에서 수천 환경 동시 rollout — RL의 표본 갈증을 하드웨어로 해결"),
    bullet("③ PPO 학습: 정책 기울기 ∇E[R] = E[∇log π(a|s)·A] — **동역학을 전혀 미분하지 않음** (score function). "
           "접촉 kink·카오스(⑤)를 원천 회피하는 것이 RL이 다리로봇에서 성공한 수학적 이유"),
    bullet("④ sim-to-real 갭 대응 4종 세트: DR + 액추에이터 넷(Hwangbo et al. 2019, Science Robotics) + "
           "teacher-student(Lee et al. 2020, Science Robotics — 험지 ANYmal) + 온라인 잠재 적응(RMA, Kumar et al. 2021)"),
    bullet("⑤ 배포: 관측→행동 NN 하나가 500Hz~1kHz로 돎 — MPC처럼 온라인 최적화가 없어 계산이 쌈"),
    h2("2. RL vs 궤적최적화 — 언제 무엇"),
    table([
        ["기준", "RL 정책", "궤적 최적화 (우리)"],
        ["산출물", "피드백 법칙 (어디서든 대응)", "특정 과제의 최적 궤적 1개"],
        ["정밀성/최적성", "보상 설계에 민감, 근사 최적", "제약·목적 정확 (KKT)"],
        ["모델 요구", "낮음 (DR로 뭉갬) — 대신 표본 수백만", "높음 (모델이 곧 성능) — 표본 불필요"],
        ["강건성", "◎ 학습 분포 안에서", "△ open-loop이면 취약 (그래서 트윈 정밀도)"],
        ["어울리는 문제", "다양한 지형·교란의 보행", "**단일 정밀 도약 — 우리**"],
    ]),
    callout("우리 문제(한 로봇, 한 동작, 최대 성능, open-loop τ 배포)에는 지금 노선(정밀 트윈 + NLP + 트윈 폴리시 + ILC)이 "
            "정석입니다. RL이 들어올 자리는 나중에 — 착지 안정화나 레일 제거 후 자세 회복 같은 '분포적' 과제가 생길 때이고, "
            "그때도 이 트윈이 그대로 학습 환경이 됩니다 (트윈의 재사용 가치).", "🎯"),
    h2("3. 오해 정리 — 'RL로 모델을 찾는다'는 없다"),
    para("Hutter 계열 논문에서도 **모델(트윈)은 지도학습/식별로, 정책은 RL로** 만듭니다. 액추에이터 넷은 벤치 데이터의 "
         "회귀(지도학습)이고, RL은 그 고정된 하이브리드 시뮬 안에서 행동만 배웁니다. '강화학습으로 정확한 모델 찾기'라는 "
         "구성은 표준 파이프라인에 존재하지 않습니다 — 이건 며칠 전 우리 대화의 결론 재확인."),
    quote("한 장 요약 | RL은 동역학을 미분하지 않는 0차 정책 탐색 + 대량 병렬 + sim-to-real 4종 세트로 성립한다. "
          "산출물이 '피드백 법칙'이라는 점이 궤적최적화와의 본질 차이 — 우리 단일 정밀 점프에는 궤적최적화가, "
          "미래의 분포적 과제에는 RL이 맞고, 트윈은 양쪽 모두의 기반이 된다."),
])

# ════════════════ ⑧ 처방전 ════════════════
p8 = new_page(parent, "⑧ 우리 연구 처방전 — 4층 차이 · 실행 카드 · 마스터 독서목록")
print("c8", p8, flush=True)
append(p8, [
    quote("이 페이지는 ①~⑦의 지식을 우리 프로젝트(정밀 트윈 → NLP 궤적 → open-loop 실기 점프)에 다시 꽂는 종합이다."),
    h2("1. 'MuJoCo로 풀었나 해석식으로 풀었나' — 확정 정리"),
    table([
        ["", "MuJoCo (트리+connect)", "해석식 (축소좌표 유도)"],
        ["역할", "식별·검증·리허설 (트윈 전부)", "궤적 최적화 (CasADi NLP), 회귀, 교차검증"],
        ["강점", "접촉·이륙 자동, 가역 동역학", "자동미분+IPOPT, 제약 정확"],
        ["관계", "**07-07 위상 정정 후 코어 물리 1e-16 동일** — 같은 로봇의 두 표현", ""],
    ]),
    h2("2. 두 표현의 결과가 다른 4층 — 현재 상태"),
    table([
        ["층", "상태", "남은 일"],
        ["① 강체 4-bar 코어", "✅ 동일 (1e-16, 07-07 검증)", "없음 — LOCKED"],
        ["② 모델 범위 (flex·armature·마찰 구현)", "의도된 차이 — 트윈이 상위집합", "NLP에 필요한 항만 선별 이식"],
        ["③ 접촉 (soft vs phase 제약)", "구조적 차이 — G20에서 k_eq 매칭으로 갭 −14%→−4.4%", "NLP 접촉 강성을 트윈 fit값으로 유지"],
        ["④ 파라미터 세트", "❌ 어긋남 — 트윈은 P10-selected, NLP는 구값", "**최우선: fitted 질량·CoM → A,B,K,IΣ 계수 환산 이식**"],
    ]),
    h2("3. 실행 카드 (우선순위순)"),
    table([
        ["카드", "내용", "근거 페이지", "비용"],
        ["NLP 파라미터 이식", "P10-selected → 해석식 계수 재계산 → task 재실행", "⑧-2 ④층", "반나절"],
        ["트윈 직접 폴리시", "NLP 해 warm start → 트윈 위 CMA/MPPI (τ 노트 20개) — 번역 갭 0", "④", "~15분/사이클"],
        ["폐루프 지표 구축", "배포 시나리오와 동형 심판 (0421 게인 데이터)", "⑤ (카오스 회피)", "반나절"],
        ["실기 체크리스트 실행", "t_ff 검증 → 세션 보정 → 70/85/100% → ILC", "해설 ⑪", "실험실 1세션"],
        ["벤치 실험", "knee a_hat 마찰항 재교정 (whip 영역)", "오차 지도 ⑨", "반나절"],
    ]),
    h2("4. 마스터 독서목록 — 계층별"),
    h3("교과서/강의 (기초 체력)"),
    bullet("**Tedrake, \"Underactuated Robotics\"** (MIT 무료 온라인 교재) — 이 문서 전체의 배경 이론이 다 있음. "
           "특히 궤적최적화·랜딩스케이프 장. 최우선 추천"),
    bullet("Featherstone, \"Rigid Body Dynamics Algorithms\" — ABA/RNEA 등 시뮬 내부가 궁금할 때"),
    bullet("Lynch & Park, \"Modern Robotics\" — 표기·기초 통일용"),
    bullet("**MuJoCo 공식 문서 'Computation' 장** — solref/solimp·볼록 솔버의 1차 출처. 필독"),
    h3("논문 12편 (한 줄 요지와 함께)"),
    bullet("Todorov, Erez, Tassa 2012 (IROS) — MuJoCo 원전: 왜 모델기반 제어용인가"),
    bullet("Todorov 2014 (ICRA) — 볼록·가역 접촉: MuJoCo soft contact의 수학"),
    bullet("Stewart & Trinkle 1996 / Anitescu & Potra 1997 — hard(LCP) 학파의 고전"),
    bullet("Posa, Cantu, Tedrake 2014 (IJRR) — contact-implicit 궤적최적화: 스케줄까지 발견"),
    bullet("Di Carlo et al. 2018 (IROS) — 4족 convex MPC 표준"),
    bullet("Kim et al. 2019 — WBIC: MPC 아래층의 실체"),
    bullet("Williams et al. 2017 (ICRA) — MPPI 원전"),
    bullet("Howell et al. 2022, arXiv:2212.00541 — MJPC + Predictive Sampling: 단순함의 승리"),
    bullet("Suh et al. 2022 (ICML), arXiv:2202.00817 — 미분가능 시뮬 gradient의 한계와 α-혼합"),
    bullet("Metz et al. 2021 — \"Gradients are not all you need\": 카오스에서 미분의 배신"),
    bullet("Hwangbo et al. 2019 / Lee et al. 2020 / Miki et al. 2022 (Science Robotics 3부작) — 액추에이터넷·teacher-student·인지형 보행"),
    bullet("Kumar et al. 2021 (RSS) — RMA: 온라인 잠재 적응"),
    h3("코드 6곳 (읽는 순서)"),
    bullet("google-deepmind/mujoco — 특히 docs; mjd_transitionFD"),
    bullet("google-deepmind/mujoco_mpc — Predictive Sampling 구현이 놀랍도록 짧음"),
    bullet("mit-biomimetics/Cheetah-Software — convex MPC + WBIC 실전 C++"),
    bullet("qiayuanl/legged_control — OCS2 기반 ROS MPC의 현대적 정리"),
    bullet("ethz-adrl/towr — 접촉 스케줄 최적화"),
    bullet("loco-mujoco / google/brax — RL 환경·미분가능 노선 감각"),
    h3("4주 학습 로드맵 제안"),
    bullet("1주: Underactuated 궤적최적화 장 + MuJoCo Computation 문서 → 이 문서 ①②③ 재독"),
    bullet("2주: Suh 2022 + Metz 2021 정독 (⑤와 대조) → 토이 문제로 FD/0차 gradient 직접 비교 실험"),
    bullet("3주: Di Carlo 2018 + Cheetah-Software 코드 리딩 (⑥ 지도 들고) → MJPC 데모 실행"),
    bullet("4주: MPPI를 우리 트윈에 실제 구현 (④ 하이브리드 카드) — 배우기의 완성은 우리 문제에 적용"),
    quote("마지막 한 줄 | 이 분야의 모든 방법은 결국 두 괴물(접촉 kink, 카오스)을 피하는 서로 다른 우회로다. "
          "무엇을 근사하고(모델·스케줄·기대값) 무엇을 지킬지(제약·정밀도·실시간)의 선택이 방법을 결정하며, "
          "우리 파이프라인은 '정밀 모델 + 무피드백'이라는 가장 엄격한 선택지를 걷고 있다 — 그래서 트윈이 전부다."),
])

# 검증
for name, pid in [("parent", parent), ("c1", ids["p1"]), ("c2", ids["p2"]), ("c3", ids["p3"]),
                  ("c4", ids["p4"]), ("c5", p5), ("c6", p6), ("c7", p7), ("c8", p8)]:
    r = requests.get(f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100", headers=H).json()
    blocks = r.get("results", [])
    n_img = sum(1 for b in blocks if b.get("type") == "image")
    print(f"{name}: {len(blocks)} blocks, {n_img} images", flush=True)
print("PART2 DONE — https://www.notion.so/" + parent.replace("-", ""))
