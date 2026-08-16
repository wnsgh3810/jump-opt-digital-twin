# -*- coding: utf-8 -*-
"""⑥ 4족 보행 MPC 해부 페이지 심화 증축 (5.~9. 절 추가) + child ⑥-a 생성."""
import requests, time, json, os, sys

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
PARENT = "396ab81d-2550-8149-95df-c2e3a712ee01"
TARGET_PREFIX = "⑥ 4족 보행 MPC 해부"
DRY_RUN = os.environ.get("DRY_RUN") == "1"


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


def _req(method, url, **kw):
    """429-aware request wrapper."""
    for attempt in range(8):
        r = requests.request(method, url, headers={**H, "Content-Type": "application/json"}, **kw)
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "1")) + 0.5
            print(f"  [429] retry in {wait}s (attempt {attempt+1})", flush=True)
            time.sleep(wait)
            continue
        return r
    raise RuntimeError(f"Gave up after retries: {url}")


def find_child_page(parent_id, title_prefix):
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{parent_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = _req("GET", url)
        r.raise_for_status()
        data = r.json()
        for b in data.get("results", []):
            if b.get("type") == "child_page":
                title = b["child_page"].get("title", "")
                if title.startswith(title_prefix):
                    return b["id"], title
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break
    return None, None


def new_page(parent_id, title):
    r = _req("POST", "https://api.notion.com/v1/pages",
              json={"parent": {"page_id": parent_id}, "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status()
    time.sleep(0.6)
    return r.json()["id"]


def append(page_id, blocks):
    for i in range(0, len(blocks), 80):
        r = _req("PATCH", f"https://api.notion.com/v1/blocks/{page_id}/children",
                  json={"children": blocks[i:i + 80]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:800])
        time.sleep(0.6)


def block_count(page_id):
    total = 0
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = _req("GET", url)
        r.raise_for_status()
        data = r.json()
        total += len(data.get("results", []))
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break
    return total


# ════════════════════════════════════════════════════════════════════
# 본문 증축 — ⑥ 페이지 끝에 붙일 5.~9. 절
# ════════════════════════════════════════════════════════════════════
blocks_p6_more = [
    callout("아래는 실무 디테일 심화 5개 절 — 용어 완전 사전부터 코드 투어, MJPC 예외 케이스까지.", "🔍"),

    # ---------------- 5. 용어 완전 사전 ----------------
    h2("5. 용어 완전 사전"),
    para("여기까지(1~4절)와 뒤에 이어지는 ⑥-a에서 정의 없이 바로 쓰는 표기를 전부 모았습니다."),
    table([
        ["용어", "뜻"],
        ["SRB / centroidal", "전신을 CoM 하나의 질량·관성으로 뭉친 축소 모델. SRB는 강체 하나, centroidal은 다리 관성까지 반영해 몸통 중심에서 재계산한 버전"],
        ["게이트(gait)", "발의 접촉 패턴 — trot(대각 쌍 동시 접지) · bound(앞뒤 쌍) · pronk(4발 동시) · pace(같은쪽 쌍) · walk(한 번에 한 발) 등"],
        ["stance / swing", "접지(힘을 낼 수 있음, f≠0 가능) / 공중(스윙, f=0 강제)"],
        ["게이트 phase 변수", "0~1을 주기적으로 순환하는 스칼라 φ — 게이트 사이클 내 현재 위치. 각 발은 φ에 오프셋을 더해 자기 접촉 타이밍을 읽음"],
        ["Raibert heuristic", "스윙 발의 착지 위치를 속도·목표속도 오차의 함수로 즉석 계산하는 규칙 (7-3절)"],
        ["WBC / WBIC", "whole-body control / whole-body impulse control — 계획된 힘·가속도를 전신 관절토크로 변환하는 고주기(수백Hz~1kHz) 제어층"],
        ["task-space", "관절각이 아니라 발끝 위치·몸통 자세 같은 '작업(task)' 좌표로 제어 목표를 기술하는 방식"],
        ["null-space projection", "우선순위가 낮은 과제를, 높은 과제를 방해하지 않는 잔여 자유도(null space)에서만 수행하도록 투영하는 기법"],
        ["state estimation", "로봇 자신의 자세·속도·위치를 센서로 추정 — 보통 칼만필터로 IMU(예측)+엔코더/접촉(보정) 융합"],
        ["ZOH 이산화", "zero-order hold — 제어입력을 한 스텝 동안 상수로 고정한다 가정하고 연속시간 동역학을 이산시간으로 바꾸는 표준 방법"],
        ["receding horizon", "매 스텝 유한한 미래 구간을 다시 최적화하고, 첫 입력만 실행한 뒤 한 스텝 전진해 반복하는 MPC의 핵심 원리"],
        ["footstep planner", "다음 몇 걸음의 착지 위치를 지형·속도명령 기반으로 미리 정하는 상위 모듈 (Raibert heuristic은 그 실시간 버전)"],
    ]),
    bullet("우리 프로젝트 대응 예시 ①: '게이트 phase 변수'는 우리가 이미 쓰는 phase 고정(스탠스→비행 스위치)과 대응됩니다 — 접촉 스케줄을 최적화 밖에서 정하는 것은 같은 트릭."),
    bullet("우리 프로젝트 대응 예시 ②: 'null-space projection'은 우리에게는 사실상 등장하지 않습니다 — 단일 다리라 우선순위 과제가 애초에 하나(궤적 추종)뿐이기 때문."),
    bullet("우리 프로젝트 대응 예시 ③: 'state estimation'도 우리는 오프라인이라 실시간 칼만필터가 필요 없고, 대신 옵티트랙·엔코더 로그를 사후에 필터링·정합하는 것으로 같은 역할을 합니다."),
    callout("이 사전이 필요한 이유: 4족 MPC 논문·코드는 이 12개 용어를 정의 없이 씁니다. 여기서 한 번 정리해두면 6절 이하는 물론, Cheetah-Software나 legged_control 코드를 직접 열어봐도 막히지 않습니다.", "📖"),

    # ---------------- 6. SRB 모델의 3가지 가정과 그 대가 ----------------
    h2("6. SRB 모델의 3가지 가정과 그 대가"),
    bullet("가정 ①: 다리 질량 무시 — 전체 질량의 약 10%를 몸통에 합산하지 않고 아예 버림. 다리는 '질량 없는 힘 전달 기구'로 취급."),
    bullet("가정 ②: roll/pitch가 작다 — 관성텐서 회전을 yaw 성분(R_z(ψ))만으로 근사, roll/pitch로 인한 관성 변화는 무시."),
    bullet("가정 ③: 발 위치를 MPC 밖에서 미리 안다 — 게이트 스케줄러(접촉 타이밍)와 Raibert heuristic(착지 위치)이 미리 정하고, MPC는 그 위치에서 '얼마나 세게 밀지'만 풂."),
    table([
        ["가정", "대가"],
        ["① 다리질량 무시", "다리 스윙의 반작용(운동량)이 몸통에 미치는 영향을 놓침 → 걸음이 빠를수록 자세 오차가 누적"],
        ["② 소각 근사", "큰 자세 변화가 필요한 기동(백플립, 급격한 자세 회복)은 이 MPC 한 프레임 안에서 못 품 → 별도 오프라인 궤적(TOWR류 비볼록 NLP)으로 풀고 그 궤적을 추종하는 방식으로 대체"],
        ["③ 발 위치 스케줄 고정", "그 시점에 최적이 아닐 수 있는 착지 위치를 그대로 받아들임 — 지형이 복잡할수록 손해 (풋스텝까지 최적화하려면 TOWR처럼 비볼록 NLP로 문제가 커짐)"],
    ]),
    bullet("예시 감각: 다리 무게가 로봇 전체 12kg 중 1.2kg(10%) 수준이면, 몸통만 다루는 SRB는 스윙 다리가 만드는 반작용 토크를 정확히 '0'으로 놓치는 셈입니다."),
    bullet("예시 감각: 백플립처럼 roll/pitch가 순간적으로 90°를 넘나드는 기동은 R_z(ψ) 근사 자체가 무너져 SRB convex MPC로는 애초에 풀리지 않고, MIT Cheetah의 백플립 데모도 오프라인 궤적 + 별도 착지 컨트롤러 조합입니다."),
    bullet("속도와 가정 ①의 관계: 걸음 속도가 빠를수록 스윙 다리의 각가속도·반작용이 커지므로, 다리질량 무시의 오차도 함께 커집니다 — 저속 walk보다 고속 bound/gallop에서 이 근사의 대가가 더 눈에 띕니다."),
    callout("왜 이래도 괜찮은가: 4족 MPC는 25~100Hz로 매 스텝 다시 계획합니다. 한 스텝의 모델 오차는 다음 스텝 재계획이 곧바로 지웁니다 — **모델 정확도와 피드백 빈도는 서로 바꿔 쓸 수 있는 통화**입니다. 우리처럼 피드백이 없는(open-loop 배포) 경우 이 교환이 성립하지 않는다는 것이 4절 표의 핵심 차이입니다.", "⚖️"),

    # ---------------- 7. 계층별 상세 ----------------
    h2("7. 계층별 상세 — 상태추정 → 게이트 → 스윙 → WBC"),
    h3("7-1. 상태추정 (state estimation)"),
    bullet("예측(predict) 단계: IMU(가속도계+자이로)를 적분해 자세·속도·위치를 한 스텝 앞으로 전파 — 드리프트가 누적되는 단계."),
    bullet("보정(correct) 단계: 접촉 중인 발은 '월드좌표에서 정지해 있다(미끄러지지 않는다)'고 가정하고, 다리 순기구학으로부터 역산한 CoM 속도로 예측을 보정 — leg odometry."),
    bullet("표준 구현은 선형/확장 칼만필터(EKF) — 예측은 IMU, 보정은 접촉 발 기구학. 접촉 판정이 틀리면(오판) 보정이 오히려 오차를 주입 → **접촉 오판이 상태추정의 최대 적**."),
    bullet("관측가능성(observability) 문제: 접촉이 전혀 없는 구간(4발 모두 공중, 점프 등)에서는 보정 소스가 사라져 IMU 드리프트가 그대로 쌓입니다 — 우리 점프 데이터의 비행구간 대응 문제와 본질이 같습니다."),
    bullet("센서 속도 감각: IMU는 보통 500Hz~1kHz로 예측을 갱신하고, 접촉 보정은 접지 이벤트가 있을 때만(게이트 주기에 종속) 들어옵니다 — 예측이 압도적으로 빠르고 보정이 드물게 오는 전형적 칼만필터 패턴."),
    bullet("참고 문헌: Bloesch et al. 2013 (IROS), \"State Estimation for Legged Robots\" — 이 접근의 표준 정식화."),
    h3("7-2. 게이트 스케줄러"),
    para("게이트 phase 변수 φ∈[0,1)는 하나의 시계처럼 계속 순환하고, 발마다 오프셋을 더해 자기 접촉 구간을 읽습니다."),
    code("φ(t) = mod(t / T_gait, 1)\nfoot_i는 (φ(t) + offset_i) mod 1 < duty  이면 stance, 아니면 swing"),
    table([
        ["게이트", "듀티비(접지 비율)", "오프셋(예: FR,FL,RR,RL)"],
        ["trot", "~0.5", "0, 0.5, 0.5, 0 (대각 쌍 동시)"],
        ["pace", "~0.5", "0, 0.5, 0, 0.5 (같은 쪽 쌍)"],
        ["bound", "~0.5", "0, 0, 0.5, 0.5 (앞/뒤 쌍)"],
        ["pronk", "~0.5(동시)", "0, 0, 0, 0 (4발 동시 접지/이륙)"],
        ["walk", "~0.75", "0, 0.5, 0.25, 0.75 (한 번에 한 발씩)"],
        ["gallop", "~0.3~0.4", "비대칭 오프셋 (고속 특화)"],
    ]),
    bullet("이 표가 3절의 B(r₁..r₄)와 만나는 지점: 스케줄러가 '지금 이 발은 stance/swing'을 정하면, stance 발의 위치가 그대로 r_i가 되어 B에 대입되고 swing 발은 힘이 0으로 마스킹됩니다 — 게이트 스케줄러의 출력이 QP의 상수 입력입니다."),
    bullet("게이트 전환(예: walk↔trot)은 듀티비·오프셋 표를 통째로 갈아 끼우는 것 — MPC 코드 자체는 손대지 않고 스케줄러 파라미터만 바뀝니다. '걸음걸이를 바꾼다'는 사용자 명령이 QP 입장에서는 그냥 B(r_i)가 다른 시퀀스로 채워지는 것에 불과합니다."),
    h3("7-3. 스윙 발"),
    code("p_land = p_hip + v · (T_stance / 2) + k_v · (v − v_cmd)"),
    para("Raibert heuristic — '반 발짝 앞에 짚기'의 수식화. 첫 항은 엉덩이 위치, 둘째 항은 다음 스탠스 구간(T_stance) 동안 몸이 이동할 거리의 절반을 미리 보정(대칭 착지), 셋째 항은 속도 오차(v−v_cmd)에 비례해 착지점을 밀어 넣어 **가속·감속을 유발**합니다 — 빠르게 가고 싶으면 발을 더 앞에, 감속하려면 더 뒤에 짚습니다."),
    bullet("실제 스윙 궤적은 이 착지점을 목표로 한 베지어(Bezier) 곡선 — 이륙점→최고점(리프트 높이)→착지점 3~5개 제어점을 보간해 부드러운 포물선형 경로를 만듭니다."),
    bullet("리프트 높이(ground clearance)는 별도 튜닝 파라미터 — 너무 낮으면 지형에 걸리고, 너무 높으면 스윙 시간이 늘어나 duty cycle을 침범합니다."),
    bullet("k_v(속도오차 게인)가 크면 더 공격적으로 감속/가속하지만 과도하면 진동(overshoot)이 생김 — Raibert 원논문(1986)에서도 이 게인은 안정성과 응답성의 트레이드오프로 다뤄집니다."),
    bullet("발끝은 task-space PD로 추종: τ = J^T(Kp(p_des−p) + Kd(v_des−v)) — 관절각이 아니라 발끝 위치·속도 오차를 직접 토크로 변환."),
    h3("7-4. WBC / WBIC"),
    bullet("우선순위 3단계(높은→낮은): ① 접촉 불변(접지 발이 미끄러지거나 지면을 뚫지 않음) > ② 몸통 자세·높이 추종 > ③ 스윙 발 궤적 추종."),
    bullet("null-space projection: 우선순위 i 과제의 자코비안 J_i에 대해 투영자 N_i = I − J_i⁺J_i를 만들고, 낮은 우선순위 과제의 목표가속도를 N_i에 통과시켜 '위 과제를 건드리지 않는 성분만' 남깁니다 — 나머지는 자동으로 버려집니다."),
    bullet("최종 단계는 다시 한 번 QP: 관절가속도·접촉력·토크를 결정변수로, 동역학 등식·마찰원뿔·토크한계를 제약으로 풀어 실제 명령 τ를 산출."),
    bullet("변수 규모 감각: 18자유도 로봇이면 이 최종 QP의 결정변수는 관절가속도(18) + 접촉력(스탠스 발 수×3) + 토크(12) 정도 — SRB MPC의 결정변수(접촉력 12개)보다 훨씬 큼. 그래서 QP를 두 층(SRB MPC + WBC QP)으로 나누어 각각을 작게 유지하는 것이 핵심 설계입니다."),
    bullet("주기 감각: SRB MPC는 수십 ms(호라이즌 재계획)마다, WBC/WBIC QP는 그보다 훨씬 촘촘한 0.5~1kHz(약 1ms 이내)로 풀립니다 — 위층이 '방향'을, 아래층이 '순간 토크'를 담당하는 시간축 분업."),
    bullet("근거 논문: Kim et al. 2019, \"Highly Dynamic Quadruped Locomotion via Whole-Body Impulse Control\" — MIT Cheetah 3의 WBIC 원전."),

    # ---------------- 8. 코드 투어 ----------------
    h2("8. 코드 투어 — Cheetah-Software 지도"),
    bullet("/common — SRB 동역학 유틸, 좌표계 변환, 상태추정기(선형 KF) 등 여러 모듈이 공유하는 기반 코드."),
    bullet("/controllers/convexMPC — QP의 실체: A_qp·B_qp 조립, 이산화, qpOASES 호출부. convexMPC.cpp 한 파일이 사실상 3~5절 수식 전부입니다."),
    bullet("/controllers/WBC_Ctrl — WBIC 구현: 우선순위 과제 정의, null-space projection, 최종 토크 QP."),
    bullet("/sim — 하드웨어 없이 개발·튜닝하기 위한 자체 시뮬레이터 (실기 대체용 — MPC 내부 '모델'이 아님에 유의, 1절 참고)."),
    bullet("/robot — CAN 통신 등 실제 모터로 명령을 내보내는 로우레벨 하드웨어 브리지."),
    bullet("/user/*_Controller — 모드별 진입점(FSM): locomotion, jumping 등. 읽는 순서 추천: convexMPC → WBC_Ctrl → 해당 user 컨트롤러 FSM."),
    bullet("대략적 규모 감각(정확한 수치가 아니라 코드를 열어봤을 때의 느낌): convexMPC 핵심 로직은 몇백 줄 남짓 — QP 조립과 solver 호출이 대부분이고, 나머지 방대한 코드베이스는 대부분 배관(상태추정·필터·하드웨어 브리지)입니다."),
    callout("실전 팁: 처음 열 때는 convexMPC.cpp의 discretization 함수(연속→이산 변환부)와 qpOASES 호출부만 먼저 찾아 읽으세요 — 그 두 지점이 이 페이지 3~5절의 수식과 1:1로 대응됩니다.", "🗺️"),

    # ---------------- 9. MJPC는 왜 예외인가 ----------------
    h2("9. MJPC는 왜 예외인가"),
    para("지금까지 본 모든 것 — SRB 축소, 게이트 고정, 계층 분업 — 은 '시뮬레이터로 직접 MPC를 풀 수 없다'는 전제 위에 서 있습니다. MJPC(DeepMind, 2022)는 이 전제를 깨는 예외입니다. 가능해진 조건은 셋: MuJoCo 자체의 속도(단일 스레드에서도 초당 수천 rollout), 유한차분 미분 API(mjd_transitionFD — 전신 비선형 모델을 그 자리에서 선형화), 그리고 여러 planner를 병렬 스레드로 동시에 돌리는 구조."),
    para("결과적으로 MPC 내부 모델이 SRB 같은 손유도 축소식이 아니라 **MuJoCo 트리 자체**가 됩니다 — 다리 질량도, 접촉도, 전신 관성도 그대로 들어갑니다. 대가는 볼록성: 더 이상 QP가 아니라 매 스텝 비선형 최적화를 실시간으로 근사해야 합니다."),
    table([
        ["planner", "미분 사용", "강점", "비고"],
        ["iLQG", "FD로 국소 선형화(1·2차 근사)", "매끄러운 문제에서 빠르고 정밀", "접촉 kink에서 FD가 흔들림 (⑤절 문제)"],
        ["Gradient descent", "1차(FD 또는 AD)", "구현 단순", "수렴 느림, 접촉에 약함"],
        ["Predictive Sampling", "0차(미분 없음, 샘플 rollout)", "접촉·불연속에 강건, 코드가 가장 단순", "Howell et al. 2022, arXiv:2212.00541 — 단순한데 실전 성능이 iLQG와 비등"],
    ]),
    bullet("실전 배치 사례: MJPC는 조작(manipulation)·사족보행 데모 다수에서 실시간으로 시연됨 — 연구실 시제품 수준을 넘어 온라인으로 도는 것이 확인된 노선입니다."),
    bullet("계산 자원 감각: convex MPC(6절)는 CPU 하나로도 수십 Hz 재계획이 충분한 반면, MJPC는 병렬 rollout(수백~수천 개)을 짧은 시간에 굴려야 해 멀티코어 CPU 또는 GPU를 전제합니다 — '모델을 통째로 쓰는 대가'는 볼록성뿐 아니라 계산 자원에서도 나타납니다."),
    callout("우리에게 시사하는 것: '트윈이 곧 MPC 모델'이라는 노선이 더 이상 실험실 시제품이 아니라 기술적으로 실행 가능한 시대입니다. 우리가 검토 중인 트윈-MPPI 카드(⑧절)의 근거가 바로 이것 — MJPC의 Predictive Sampling과 본질적으로 같은 발상(0차, 접촉에 강건, 시뮬=모델)입니다.", "🧭"),

    quote("추가분 한 장 요약 | 4족 MPC를 실무 디테일까지 뜯어보면: 상태추정(칼만)이 다리 밑을, 게이트 스케줄러(phase 변수)가 '언제'를, Raibert heuristic이 '어디'를, WBC/WBIC(null-space 우선순위)가 '몸 전체로 어떻게'를 채웁니다. SRB의 세 가정은 공짜가 아니라 재계획 피드백과 맞바꾼 대가이고, MJPC는 그 맞바꿈 자체를 없앤 유일한 예외입니다."),
]

# ════════════════════════════════════════════════════════════════════
# child 페이지 — ⑥-a Convex MPC의 QP를 손으로 세워보기
# ════════════════════════════════════════════════════════════════════
CHILD_TITLE = "⑥-a Convex MPC의 QP를 손으로 세워보기"
blocks_child = [
    quote("이 페이지의 목적 | SRB convex MPC의 QP를 상태 정의부터 최종 표준형까지 손으로 세운다 — ⑥ 본문 2절 '모델 축소'를 수식으로 완전히 풀어쓴 버전."),

    h2("1. 상태 정의 — 13차원, 그리고 중력을 상태로 숨기는 트릭"),
    para("SRB(single rigid body)의 상태는 x = [Θ, p, ω, v, g] ∈ R¹³ 로 잡습니다. Θ=(roll,pitch,yaw)=바디 자세, p=CoM 위치, ω=바디 각속도, v=CoM 선속도 — 여기까지 12차원. 마지막 g는 물리량이 아니라 **트릭**입니다: 항상 중력가속도 값을 갖고 미분값이 0(ġ=0)인 '가짜 상태'를 하나 끼워 넣으면, 뒤에서 v̇ 식에 나오는 −g 항이 상태 x의 선형결합(계수 1짜리 항)으로 흡수됩니다."),
    bullet("13개 성분 분해: Θ(3, roll·pitch·yaw) · p(3, CoM 월드좌표) · ω(3, 바디 각속도) · v(3, CoM 속도) · g(1, 상수 트릭)."),
    bullet("왜 트릭이 필요한가: ẋ=Ax+Bu+c 형태(c=상수항)는 매 스텝 c를 따로 더해야 해 QP 행렬 조립이 지저분해집니다. c를 상태에 흡수해 ẋ=Ax+Bu로 만들면 A_d, B_d 한 쌍만 있으면 끝 — 표준 선형 MPC 코드를 그대로 재사용할 수 있습니다."),

    h2("2. 연속 동역학 — 세 가지 근사가 들어가는 지점"),
    table([
        ["식", "의미", "근사 / 가정"],
        ["ṗ = v", "위치의 시간미분은 속도", "근사 없음 (순수 기구학)"],
        ["v̇ = (Σf_i)/m − g", "뉴턴 2법칙: CoM 가속도 = 발 반력 합/질량 − 중력", "질량 m은 몸통 하나로 뭉친 상수 (다리질량 무시, ⑥-6-① 가정)"],
        ["I ω̇ ≈ Σ r_i×f_i", "오일러 방정식에서 ω×Iω(자이로 항)를 생략", "저속 회전 가정 — 빠른 공중제비 등에는 부정확"],
        ["Θ̇ ≈ R_z(ψ)ω", "자세 변화율을 몸체각속도로 근사", "roll/pitch가 작다는 가정 — 원래는 Θ̇=T(Θ)ω로 세 각 모두에 의존"],
    ]),
    para("네 식 모두 ⑥ 본문 6절에서 소개한 세 가지 근사(다리질량 무시·저속회전·소각 근사)가 구체적으로 어디에 박혀 있는지 보여줍니다 — SRB 모델은 근사 하나가 아니라 근사'들'의 조합입니다."),
    bullet("네 식 중 실제로 상태 간 커플링(cross-term)을 만드는 것은 Θ̇=R_z(ψ)ω 뿐 — 나머지는 상수계수(1/m, I⁻¹)의 선형결합이라 훨씬 단순합니다."),

    h2("3. 선형화 — A는 yaw만, B는 발 위치만 본다"),
    code("ẋ = A(ψ) x + B(r₁, r₂, r₃, r₄) f"),
    para("2절의 네 식을 상태공간으로 정리하면 위 형태가 됩니다. 핵심은 **A와 B가 결정변수(x, f)에 의존하지 않는다**는 것 — A는 현재 요(yaw)각 ψ 하나만 알면 계산되고, B는 스케줄러가 이미 정해준 발 위치 rᵢ(CoM 기준)만 알면 계산됩니다. 즉 QP를 풀기 **전에** A, B가 통째로 확정됩니다. 이것이 SRB convex MPC가 '풀 수 있는' 이유의 8할입니다 — 동역학이 결정변수에 대해 완전히 선형이므로, 2차 비용함수와 결합하면 곧바로 QP입니다."),
    bullet("A의 0이 아닌 블록: Θ̇행에 R_z(ψ)(→ω), ṗ행에 I₃(→v), v̇행에 g상태 계수 1(→g). 나머지는 0."),
    bullet("B의 0이 아닌 블록: ω̇행에 I⁻¹[rᵢ]ₓ (i=1..4, 스윙발은 해당 열이 0으로 마스킹), v̇행에 (1/m)I₃가 4개 반복."),
    bullet("실무적 의미: 로봇이 회전(yaw)하거나 발 디딜 위치를 바꿀 때만 A, B를 다시 계산 — 매 QP 반복마다 다시 만들 필요가 없어 실시간성이 확보됩니다."),

    h2("4. ZOH 이산화 — 실시간 QP를 위한 마지막 준비"),
    code("x_{k+1} = A_d x_k + B_d f_k     (Δt ≈ 25~40 ms)"),
    para("연속시간 A, B를 결합한 [[A,B],[0,0]] 블록행렬의 행렬지수함수(matrix exponential, Van Loan 방법)를 한 번 계산하면 정확한 A_d, B_d가 나옵니다. Δt가 작을 때는 A_d≈I+AΔt, B_d≈BΔt로 1차 근사해도 실용적으로 충분합니다."),
    bullet("중요한 점: A, B가 3절에서 이미 '상수'로 확정되었으므로 A_d, B_d도 **호라이즌 내내 재사용 가능한 상수 행렬** — 매 스텝 다시 적분할 필요가 없습니다."),
    callout("직관: A_d, B_d는 '한 스텝 동안 상태가 어떻게 옮겨가는지'를 미리 계산해 둔 이동표(lookup table) — 매 반복 다시 풀어야 하는 미분방정식이 아닙니다.", "🧮"),

    h2("5. QP 표준형 — 목적함수와 제약"),
    code("min_{x,f}  Σ_{k=0}^{N-1} ||x_{k+1} - x_ref,k+1||²_Q + ||f_k||²_R\n\n"
         "s.t.  x_{k+1} = A_d x_k + B_d f_k        (동역학, k=0..N-1)\n"
         "      x_0 = x_measured                   (상태추정기 출력)\n"
         "      |f_x,i,k| ≤ μ f_z,i,k              (스탠스 발, 마찰 피라미드)\n"
         "      |f_y,i,k| ≤ μ f_z,i,k\n"
         "      0 ≤ f_z,i,k ≤ f_max                (수직 반력 한계, 접지 유지)\n"
         "      f_i,k = 0                          (스윙 발 i)"),
    para("비용은 상태오차·힘 크기 모두 **2차(quadratic)**, 제약은 동역학 등식(선형)과 마찰 피라미드(절댓값 부등식 = 선형 부등식 4개로 분해) 모두 **선형** — 정의상 QP입니다. 마찰 '피라미드'라는 이름 자체가 원뿔(cone, 2차 제약)을 4개 평면으로 깎아 선형으로 만들었다는 뜻 — 정확도를 조금 버리고 볼록성·선형성을 사는 또 하나의 트레이드오프입니다."),
    bullet("마찰 피라미드 |f_x|,|f_y| ≤ μf_z: 실제 마찰원뿔(√(f_x²+f_y²)≤μf_z)을 4개 반평면으로 근사 — SOCP를 LP/QP로 낮추는 표준 수법."),
    bullet("f_z 박스 제약(0 ≤ f_z ≤ f_max): 하한 0은 '지면을 당길 수 없다'(접지 유지), 상한 f_max는 모터·기구 한계."),
    bullet("스윙 발 f=0: 게이트 스케줄러가 이미 정한 접촉상태(7-2절)를 등식 제약으로 그대로 하드코딩 — 이 QP는 '어느 발이 접지인지'는 절대 스스로 풀지 않습니다."),
    bullet("실전 구현(Cheetah-Software convexMPC.cpp)은 x를 동역학 등식으로 소거해 f만 남긴 '응축(condensed)' QP로 바꿔 풀고, qpOASES 같은 dense active-set solver를 씁니다."),

    h2("6. 파라미터 감각"),
    table([
        ["파라미터", "전형적 값", "의미"],
        ["호라이즌 N", "10~16 스텝", "Δt~30ms 기준 0.3~0.5s 앞을 봄"],
        ["Q (상태가중)", "roll/pitch/높이 크게, xy위치·yaw 작게", "자세 유지가 최우선, 위치는 속도추종으로 대체"],
        ["R (힘가중)", "작게 (정규화 수준)", "힘 자체를 아끼기보다 QP 컨디셔닝용"],
        ["μ", "0.4~0.6", "지면 마찰계수 추정치"],
        ["f_max", "체중 수준/발", "모터·기구 한계"],
    ]),
    bullet("재계획 주기: 매 제어 스텝(수백Hz~1kHz)마다 새로 풀지 않고 보통 수십 ms마다 재최적화하고, 그 사이는 첫 스텝 해를 저수준 제어기가 유지 — 이 자체가 receding horizon의 실제 구현."),
    bullet("warm start: 이전 QP 해를 다음 반복의 초기값으로 재사용해 active-set solver 수렴을 가속."),

    h2("7. 볼록성의 열쇠 — 발 위치가 '상수'로 들어가는 것"),
    para("3절에서 본 것처럼 B(rᵢ)는 rᵢ에 대해 정해져 있고 f에 대해서만 선형입니다. 만약 **발 디딜 위치 rᵢ까지 결정변수**로 풀면 어떻게 될까요 — 각속도 식 Σrᵢ×fᵢ가 두 결정변수(rᵢ, fᵢ)의 곱(쌍선형, bilinear)이 되어 더 이상 볼록하지 않습니다. 이것이 정확히 TOWR(Winkler et al. 2018)류가 IPOPT 같은 비볼록 NLP 솔버를 쓰는 이유이고, 반대로 convex MPC가 그 자유도를 게이트 스케줄러+Raibert heuristic에 넘겨버리고 볼록성을 사는 이유입니다 — ⑥ 본문 2절의 '접촉 스케줄 고정' 트릭이 수식 차원에서는 이렇게 나타납니다."),
    bullet("대조: Crocoddyl·OCS2류 전신 DDP는 접촉을 스케줄이 아니라 상태궤적 안에서 암묵적으로(또는 접촉력을 통해) 다루기도 해 문제가 다시 커집니다 — SRB convex MPC는 '작게 풀 수 있는 문제'를 의도적으로 고른 결과입니다."),
    bullet("우리 프로젝트 대응: 4-bar NLP도 phase(접촉 구간)를 고정하고 접촉력을 결정변수로만 두는 동일한 트릭을 씁니다 — ⑥ 본문 2절 그대로."),

    h2("8. 한 장 요약"),
    quote("한 장 요약 | 13차원 증강 상태(중력 트릭)로 아핀을 선형으로 바꾸고, 다리질량 무시·저속회전·소각 근사로 동역학을 선형화하고(A는 yaw만, B는 발 위치만 봄), ZOH로 이산화한 뒤, 2차 비용+선형 제약(마찰 피라미드)으로 QP를 세운다. 발 위치를 상수로 취급하는 것이 볼록성의 마지막 열쇠 — 그것까지 변수로 풀면 TOWR의 비볼록 세계로 넘어간다."),
]

print(f"main-append blocks: {len(blocks_p6_more)}", flush=True)
print(f"child blocks: {len(blocks_child)}", flush=True)

if DRY_RUN:
    print("DRY_RUN=1 — skipping all network calls.", flush=True)
    sys.exit(0)

# ════════════════════════════════════════════════════════════════════
# 실행
# ════════════════════════════════════════════════════════════════════
p6_id, p6_title = find_child_page(PARENT, TARGET_PREFIX)
if not p6_id:
    raise RuntimeError(f"child_page starting with '{TARGET_PREFIX}' not found under parent {PARENT}")
print(f"found target page: {p6_title!r} id={p6_id}", flush=True)

before_count = block_count(p6_id)
print(f"before append: {before_count} blocks", flush=True)

append(p6_id, blocks_p6_more)
print("main-body append done", flush=True)

after_count = block_count(p6_id)
print(f"after append: {after_count} blocks (+{after_count - before_count})", flush=True)

child_id = new_page(p6_id, CHILD_TITLE)
print(f"child page created: {child_id}", flush=True)

append(child_id, blocks_child)
print("child append done", flush=True)

child_count = block_count(child_id)
print(f"child page block count: {child_count}", flush=True)

print("SUMMARY", flush=True)
print(f"  target page id: {p6_id}", flush=True)
print(f"  main body: {before_count} -> {after_count} blocks (added {after_count - before_count})", flush=True)
print(f"  child page: {child_id} ({CHILD_TITLE}) — {child_count} blocks", flush=True)
print("DONE — https://www.notion.so/" + p6_id.replace("-", ""))
