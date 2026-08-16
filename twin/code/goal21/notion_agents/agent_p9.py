# -*- coding: utf-8 -*-
"""GOAL21 Notion - Part 9: 폐루프 모델링의 계보 + 9-a 전달 자코비안 우회법 완전 해부."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")

PARENT = "396ab81d2550814995dfc2e3a712ee01"


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
        for attempt in range(5):
            r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                               headers={**H, "Content-Type": "application/json"},
                               json={"children": blocks[i:i + 80]})
            if r.status_code == 200:
                break
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 1.0)) + 0.5
                print("429 rate limited, waiting", wait, flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(r.text[:800])
        else:
            raise RuntimeError("Failed after retries")
        time.sleep(0.6)


# ════════════════════════════════════════════════════════════════════
# ⑨ 폐루프 모델링의 계보
# ════════════════════════════════════════════════════════════════════
p9 = new_page(PARENT, "⑨ 폐루프 모델링의 계보 — '그 논문들'이 존재하는 진짜 이유와 5가지 표현법")
print("p9", p9, flush=True)

blocks9 = [
    quote("용어 | **폐루프(closed-loop/closed-chain)**: 구동축에서 관절까지의 경로가 나무형이 아니라 고리를 이루는 "
          "기구 — 4절링크·5절링크·미분풀리 등. **equality 구속**: MuJoCo가 폐루프를 표현하는 방식 — 두 점의 위치가 "
          "항상 같아야 한다는 등식 제약을 트리 구조에 추가로 부여합니다. **MJX**: MuJoCo를 GPU에서 대규모 병렬로 "
          "돌리는 JAX 기반 구현체입니다. **축소좌표(reduced/minimal coordinates)**: 폐루프의 구속을 손으로 미리 풀어, "
          "독립적인 자유도 개수만큼의 좌표로 동역학을 표현하는 방식입니다. **전달 자코비안(transmission Jacobian)**: "
          "모터좌표와 관절좌표 사이의 순간적인 속도·힘 비율을 나타내는, 자세에 따라 변하는 행렬입니다."),

    h2("0. 출발 질문"),
    quote("MuJoCo가 폐루프를 기계 정밀도로 푼다면(①⑤ 검증), 왜 폐루프 모델링 논문이 계속 나오는가? 암시적 구현에 "
          "단점이 있는가? 요즘은 어떻게 하는가?"),

    h2("1. 한 줄 답"),
    callout("그 논문들은 '폐루프를 못 풀어서' 존재하는 것이 아닙니다. 다섯 개의 서로 다른 병목 때문에 존재합니다 — "
            "① GPU 대규모 병렬 RL의 비용, ② 로봇 기술 포맷(URDF)의 표현 불가, ③ 구속 있는 시스템의 식별(system "
            "identification), ④ 제어기(WBC/MPC)에의 구속 통합, ⑤ 시뮬 정확도 검증. 저희 폴더에 있는 11편의 논문이 "
            "정확히 이 다섯 갈래로 나뉩니다.", "💡"),
    bullet("**① GPU 병목** — MJX나 Isaac 같은 GPU 물리엔진에서 수천 개 환경을 동시에 굴려야 하는 RL 학습에서는, "
           "폐루프 구속을 매 환경·매 스텝마다 푸는 비용이 누적됩니다. BRUCE(2507.00273)와 Kamino(2603.16536)가 이 "
           "병목을 정면으로 다룹니다."),
    bullet("**② 표현 포맷 병목** — URDF는 애초에 나무(tree) 구조만 가정하는 포맷이라 폐루프 자체를 담을 수 없습니다. "
           "Extended URDF(2504.04767)가 이 인프라 문제를 다룹니다."),
    bullet("**③ 식별(sysID) 병목** — 폐루프/구속이 있는 로봇은 일반적인 unconstrained 식별 공식이 그대로 통하지 "
           "않습니다. Digit sysID(2408.08830)가 constraint Jacobian을 식별식에 명시적으로 넣는 이유입니다."),
    bullet("**④ 제어기 통합 병목** — WBC나 MPC 같은 실시간 제어기 내부에서 폐루프 구속력을 반영하려면, 시뮬레이터가 "
           "아니라 제어 공식 자체에 구속이 들어가야 합니다. Digit WBC(2311.08409), 그리고 해석적 계열의 "
           "2503.22459·2504.00642가 여기 속합니다."),
    bullet("**⑤ 검증 병목** — 폐루프를 아무리 정확히 표현해도, 접촉·충격 모델이 실제와 다르면 예측이 틀어집니다. "
           "Validating Simulators(2110.00541)가 이 층위를 다룹니다."),
    para("이 다섯 갈래는 서로 배타적이지 않고 실제로 겹칩니다 — 예를 들어 BRUCE 논문은 ①(GPU 비용)을 풀면서 동시에 "
         "'네이티브 시뮬레이션이 정확도를 지킨다'는 ⑤의 논지도 함께 주장합니다. 다만 각 논문이 '주로 어느 병목을 "
         "풀려는가'는 뚜렷이 구분됩니다."),

    h2("2. 흔한 주장 팩트체크"),
    para("커뮤니티나 AI 답변에서 자주 보이는 여섯 개의 주장을 저희 실측·검증 결과와 대조했습니다."),
    table([
        ["주장", "판정", "근거"],
        ["MuJoCo는 ERP/CFM으로 구속을 튜닝한다", "오류",
         "ERP/CFM은 ODE·Bullet 계열의 용어입니다. MuJoCo는 solref/solimp라는 별도 매개변수 체계를 씁니다(① 페이지 참조)."],
        ["구속 추가 시 연산이 기하급수적으로 증가한다", "과장",
         "단일 로봇을 CPU에서 돌릴 때 connect equality는 구속 행 3개를 추가하는 수준이며, 저희 4-bar 트윈은 2kHz "
         "실측을 그대로 유지합니다. 진짜 비용은 GPU에서 수천 개 환경을 병렬로 돌릴 때 솔버 반복이 곱해지며 커집니다."],
        ["소프트 구속이라 링크가 스펀지처럼 출렁인다", "조건부 사실",
         "설정이 나쁠 때(시간상수 tc가 클 때)만 발생합니다. 저희 실측으로는 solref 0.3ms와 0.8ms가 완전히 동일하게"
         "(포화 상태로) 거동했고, 2ms 이상에서만 물렁해지기 시작했습니다 — 제어 가능한 현상이지 필연이 아닙니다."],
        ["직렬 근사+자코비안이면 오차가 0%다", "부분 오류",
         "기구학(전달비·힘 매핑)은 정확하지만, 루프를 이루는 링크의 질량·관성 동역학이 통째로 버려집니다. 저희 "
         "로봇이 반례입니다 — crank 질량 0.656kg(로봇 전체 3.34kg의 20%)이 직렬 근사에서 '병진하는 유령 질량'으로 "
         "처리됩니다. 결과적으로 순수 CAD 4-bar 모델이 fitted serial 모델 대비 −9%의 차이를 내고, 무릎측 질량모멘트 "
         "계수가 serial 근사에서는 +0.175인데 실제는 −0.0037로 부호가 반전되고 크기가 48배 벌어집니다."],
        ["RL에서 수동 관절 상태 관리가 복잡하다", "타당",
         "초기화 시점부터 폐루프 조건을 만족해야 합니다. 2505.12231(RaiSim ankle)이 이를 위해 sub-step 정렬 phase를 "
         "별도로 두는 것이 그 증거입니다. 저희도 마찬가지로 qpos 규약 [bz, q1, q2, −q2, q2]가 필요합니다."],
        ["Isaac/PyBullet은 트리 가정이라 루프가 어렵다", "타당",
         "PhysX 계열은 폐루프 지원이 약하고, URDF 자체가 루프를 표현할 수 없습니다. 2504.04767(extended URDF)이 이 "
         "문제를 정면으로 다룹니다."],
    ]),
    bullet("첫 번째 항목 — 'ERP/CFM' 자체가 MuJoCo에 없는 개념이라는 단순한 용어 혼동입니다."),
    bullet("두 번째 항목 — '구속=비쌈'이라는 통념은 GPU 대규모 병렬이라는 맥락에서만 성립합니다. 저희처럼 CPU 단일 "
           "로봇 트윈에서는 사실상 무시할 만합니다."),
    bullet("세 번째 항목 — '소프트 구속=부정확'이라는 등식도 성립하지 않습니다. 설정값(solref)이 포화 영역에 있으면 "
           "하드 구속과 구별되지 않습니다."),
    bullet("네 번째 항목이 이 페이지 전체에서 가장 중요합니다 — 직렬 근사+자코비안이 '틀린' 것이 아니라, 정확히 "
           "무엇을 버리는지가 로봇마다 다르다는 것이 핵심이며, 이는 아래 4절과 sub-page ⑨-a에서 숫자로 풀어냅니다."),
    bullet("다섯 번째 항목 — 초기화 시점의 루프 정합 문제는 RL 진영이 실제로 별도 phase까지 두어 씨름하는 실무 "
           "장벽입니다."),
    bullet("여섯 번째 항목 — 엔진·포맷 차원의 한계(PhysX의 약한 루프 지원, URDF의 트리 가정)도 허수가 아니라, "
           "인프라 논문(2504.04767)이 정면으로 다룰 만큼 실재하는 장벽입니다."),

    h2("3. 폐루프 표현법 5가지 — 완전 분류"),
    para("폐루프를 다루는 방법은 크게 다섯 가지로 나뉩니다. 어느 것도 절대적으로 우월하지 않으며, 무엇을 보존하고 "
         "무엇을 버리는지가 서로 다릅니다."),

    h3("A. 네이티브 구속"),
    para("트리 구조에 equality 구속을 추가해, 시뮬레이터가 폐루프를 있는 그대로 풉니다."),
    bullet("**MuJoCo CPU** — 저희 트윈이 쓰는 방식입니다. connect equality로 4-bar를 직접 표현합니다."),
    bullet("**MJX(GPU MuJoCo)** — BRUCE 논문(2507.00273, Tanaka, Zhu, Wang, Hong, Humanoids 2025)이 세 가지 "
           "병렬기구(differential pulley·5-bar·4-bar)를 GPU에서 네이티브로 학습시킵니다."),
    bullet("**RaiSim pin constraint** — 2505.12231이 두 링크 위의 두 점 사이 위치 일관성을 강제하는 pin constraint로 "
           "ankle 폐루프를 구현합니다."),
    bullet("이 계열의 RL 프레임워크들이 공통적으로 수렴하는 방향이기도 합니다 — LiPS(2503.08349), TOPA(2507.10164), "
           "Kamino(2603.16536) 모두 같은 철학(폐루프를 학습 환경에서 제거하지 않는다)을 공유합니다."),
    para("장점 — 링크의 질량·관성 동역학이 완전히 보존됩니다. 접촉이 루프를 이루는 링크에 직접 닿아도 문제없이 "
         "처리됩니다."),
    para("단점 — 엔진 차원의 구속 지원이 필요하고, 초기화 시점의 정렬 문제가 생기며, GPU 대규모 병렬 시 구속 해석 "
         "비용이 곱해집니다."),

    h3("B. 축소좌표 해석"),
    para("루프를 손으로 미리 소거해, 독립 자유도 개수만큼의 최소 좌표로 동역학을 유도합니다."),
    bullet("**저희 CasADi NLP** — 사용자가 직접 유도한 4-bar 축소좌표 동역학이며, A방식(MuJoCo)과 기계 정밀도 "
           "수준(1e-16)으로 일치함이 검증되었습니다."),
    bullet("**constraint embedding(Featherstone)** — 폐루프를 트리 알고리즘에 삽입하는 고전적 축소좌표 기법입니다."),
    bullet("**Pinocchio류 constrained dynamics** — 같은 철학을 라이브러리 차원에서 구현한 계열입니다."),
    bullet("**폴더의 2503.22459(kinematic actuation models), 2504.00642(optimal control walkers), Digit 계열 "
           "2311.08409(WBC)·2408.08830(sysID)** — 모두 이 축소좌표/해석적 노선에 속합니다."),
    para("장점 — 정확하고, 미분 가능하며, 빠릅니다. 최적화 문제에 가장 잘 맞습니다."),
    para("단점 — 닫힘식을 손으로 풀 수 있는 단순한 루프(평행사변형 등)에서만 성립합니다. 임의의 복잡한 루프에는 "
         "일반화가 어렵습니다."),

    h3("C. 직렬 근사 + 전달 자코비안"),
    para("RoMeLa의 구방식입니다. 시뮬레이터 안에서는 로봇을 직렬(open-chain) 다리로 취급하고, 모터 공간과 관절 "
         "공간 사이의 매핑만 자코비안으로 처리합니다."),
    code("q_dot_act = J_T(q) * q_dot_joint\ntau_joint  = J_T(q)^T * tau_act"),
    para("원전 — Shen et al., ICRA 2022, \"Design and Control of a Miniature Bipedal Robot with Proprioceptive "
         "Actuation\" (BRUCE의 초기 설계·제어 논문)."),
    para("장점 — 어떤 물리엔진에서도 쓸 수 있고, 대규모 RL 병렬화가 쉬우며, 모터 공간 마찰 모델링이 자연스럽습니다."),
    para("단점 — 루프를 이루는 링크(crank·coupler 등)의 관성이 통째로 삭제됩니다. 무엇이 정확히 버려지는지는 "
         "sub-page ⑨-a에서 수식과 숫자로 완전히 해부합니다."),

    h3("D. 직렬 뭉침"),
    para("루프 링크의 질량을 이웃 링크에 그냥 합쳐버리고, 전달비 보정조차 하지 않는 가장 거친 근사입니다."),
    para("저희의 구(舊) serial 모델이 이 방식이었으며, 다섯 가지 방식 중 가장 부정확함을 저희가 정량적으로 "
         "실증했습니다 — G20-A 이전의 모든 fit 시도가 이 함정에 빠져 있었습니다."),

    h3("E. 학습 흡수"),
    para("전달계의 비선형성을 물리 유도 없이, 데이터로 학습한 actuator net 등으로 흡수하는 방식입니다."),
    para("Hwangbo et al. 2019(Science Robotics) 계열이 대표적이며, 이 방식은 충분한 양·질의 라벨(벤치 데이터)이 "
         "확보되어야 성립한다는 전제가 있습니다."),

    para("다섯 방식을 한 표로 정리하면 다음과 같습니다."),
    table([
        ["방식", "기구학", "링크 동역학", "미분", "병렬 RL", "대표"],
        ["A. 네이티브 구속", "정확", "보존", "엔진 지원 시 가능", "비용 큼(GPU 구속 해석)", "MuJoCo CPU/MJX, RaiSim"],
        ["B. 축소좌표 해석", "정확", "보존", "해석적으로 정확", "해당 없음(최적화용)", "저희 CasADi NLP, Digit WBC/sysID"],
        ["C. 직렬근사+자코비안", "정확", "삭제", "가능(자코비안 미분)", "쉬움", "BRUCE ICRA22(구방식)"],
        ["D. 직렬 뭉침", "근사(보정 없음)", "오염", "가능", "쉬움", "저희 구(舊) serial 모델"],
        ["E. 학습 흡수", "데이터 의존", "데이터에 암묵적으로 포함", "가능(신경망)", "쉬움", "Hwangbo 2019 actuator net"],
    ]),
    para("표의 '미분' 열은 최적화 적합성을, '병렬 RL' 열은 대규모 학습 적합성을 나타냅니다. 저희 문제(최적화)에는 "
         "B가, RoMeLa의 문제(대규모 RL, 가벼운 루프)에는 애초에 C가 자연스러운 선택이었음을 이 표가 보여줍니다."),

    h2("4. ★ 우리 로봇이 주는 교훈 — '어느 방식이 옳은가'는 로봇마다 다르다"),
    para("두 개의 축으로 로봇을 위치시킬 수 있습니다 — (루프 링크의 질량 비율) × (전달비의 비선형성)."),
    table([
        ["", "전달비 선형(상수에 가까움)", "전달비 비선형"],
        ["루프 링크 질량 큼", "A/B 방식이 사실상 필수 (저희 4-bar)", "A/B 방식 필수 + 비용 감수"],
        ["루프 링크 질량 작음", "아무 방식이나 무방", "C 방식이 최적 (BRUCE)"],
    ]),
    para("**저희 4-bar** — 평행사변형 구조이기 때문에 전달비가 상수 1:1입니다. 그 결과 C방식의 자코비안이 "
         "항등행렬이 되어, C를 쓰더라도 D(직렬 뭉침)와 똑같아져 버립니다. 즉 저희 로봇에서 4-bar를 명시적으로 "
         "모델링해서 얻는 이득의 100%는 비선형 전달비가 아니라 **질량 배치**에서 나왔습니다 — crank가 로봇 전체 "
         "질량의 20%를 차지하기 때문입니다."),
    para("**BRUCE** — 5-bar 등 루프 링크가 수십 그램 수준으로 초경량인 반면, 전달비는 강하게 비선형입니다. 그래서 "
         "이득의 대부분이 전달비 쪽에서 나오며, C방식(직렬+자코비안)이 거의 정확하면서도 효율적이었던 것입니다."),
    para("일반화하면, 새로운 다리 기구를 설계·모델링하기 전에 먼저 이 두 좌표(루프 링크 질량비, 전달비 비선형성)를 "
         "재는 것이 방법론 선택의 첫 단계가 되어야 합니다."),
    callout("같은 '4절 링크'라도 병목이 정반대일 수 있습니다 — 자기 로봇의 (질량비, 비선형성) 좌표를 먼저 재야 "
            "합니다.", "🧭"),

    h2("5. 2022 → 2026 타임라인 — 요즘은 어떻게 하나"),
    bullet("**2022** — BRUCE ICRA22(Shen et al.) — C방식(직렬 근사+전달 자코비안)의 정점입니다."),
    bullet("**2023년 이후** — MJX(GPU MuJoCo)가 성숙하면서, equality 구속을 포함한 대규모 병렬 시뮬레이션이 "
           "가능해집니다."),
    bullet("**2503.22459 / 2504.00642** — B방식(축소좌표 해석)을 최적제어 문제로 정식화하는 논문들이 등장합니다"
           "(병렬 워커 로봇 대상)."),
    bullet("**2311.08409 / 2408.08830** — Digit — 구속을 WBC와 sysID에 직접 반영합니다. 특히 2408.08830은 '구속 "
           "있는 로봇의 식별'이라는, 저희 GOAL21과 같은 문제의식을 다룹니다."),
    bullet("**2504.04767** — extended URDF — 표현 포맷 자체를 정비하는 인프라 논문입니다."),
    bullet("**2507.00273** — RoMeLa 스스로가 C방식에서 A방식으로 전환을 선언합니다 — 세 가지 병렬기구를 MJX "
           "네이티브로 학습시켜, serial 근사 정책 대비 실기 성능과 표면 일반화에서 우위를 주장합니다."),
    bullet("**2507.10164(TOPA) / 2603.16536(Kamino, 6중 중첩 루프) / 2110.00541(시뮬 검증)** — A방식의 확장과 "
           "검증이 이어집니다."),
    para("전체 흐름은 '우회(C방식)'에서 '정면(A/B방식)'으로 이동하고 있습니다 — 도구(GPU 물리엔진, 해석적 최적화 "
         "프레임워크)가 성숙했기 때문입니다. 저희 파이프라인(A방식 트윈 + B방식 NLP + 둘의 등가성 증명)은 이미 이 "
         "흐름의 종착 형태를 갖추고 있습니다."),

    h2("6. 그래서 암시적(A방식)의 정직한 단점 목록"),
    bullet("**초기화 시점 루프 정합이 필요합니다** — 저희는 qpos 규약([bz, q1, q2, −q2, q2])으로 이를 해결했습니다."),
    bullet("**수동 관절 부기(book-keeping)가 필요합니다** — 상태 5개 중 2개가 종속 변수입니다."),
    bullet("**GPU 대규모 병렬 시 솔버 비용이 커집니다** — 저희는 CPU 단일 로봇 트윈이라 이 문제와 무관합니다."),
    bullet("**solref 설정에 대한 책임이 사용자에게 있습니다** — 포화 영역(0.3~0.8ms에서 동일 거동)을 확인해 "
           "해소했습니다."),
    bullet("**URDF 기반 파이프라인과 바로 호환되지 않습니다** — MJCF를 직접 작성하는 방식으로 해소했습니다."),
    bullet("**구속력이 접촉력과 같은 솔버에서 계산되므로, 극한 충격 상황에서 상호작용할 수 있습니다** — 저희 착지 "
           "실험에서는 아직 관측되지 않았습니다."),
    para("여섯 항목 모두 저희 프로젝트에서는 이미 해소되었거나, 애초에 규모(CPU 단일 로봇)상 무관한 항목입니다 — "
         "이는 '암시적 구현이 나쁘다'는 뜻이 아니라, 단점의 대부분이 GPU 대규모 병렬이라는 특정 사용 맥락에서만 "
         "부각된다는 뜻입니다."),

    h2("7. 폴더 매핑 표"),
    para("저희 로컬 폴더에 있는 11편의 논문을 CLOSED_LOOP_PAPERS_SUMMARY.md의 분류를 따라 위 다섯 병목 및 방식에 "
         "매핑했습니다. 분류 — 1=시뮬 직접(A방식 계열, 5편), 2=해석·최적화(B방식 계열, 4편), 3=인프라·검증(2편)."),
    table([
        ["파일명(축약)", "분류", "한 줄 요지"],
        ["2507.00273 BRUCE MJX", "1",
         "3개 병렬기구(differential pulley·5-bar·4-bar)를 MJX GPU에서 네이티브로 closed-chain 학습, mechanical "
         "intelligence 보존"],
        ["2505.12231 3-DOF hopping RaiSim", "1",
         "RaiSim pin constraint로 ankle 폐루프를 직접 구현, sub-step 정렬 phase로 초기화 문제 해결"],
        ["2503.08349 LiPS humanoid RL", "1",
         "GPU RL 규모를 유지하면서 parallel-series 구조를 multi-rigid-body로 시뮬 환경에 반영"],
        ["2507.10164 TOPA biped RL", "1",
         "closed kinematic chain을 RL dynamics에 명시적으로 포함, motor-space 마찰까지 반영"],
        ["2603.16536 Kamino DR Legs", "1",
         "GPU NCP 솔버로 6중 중첩 kinematic loop까지 native 지원, 4096 병렬 환경"],
        ["2503.22459 Kinematic Actuation Models", "2",
         "closed-loop 전체 대신 analytical IK+configuration-dependent Jacobian으로 비선형 전달비 보존, DDP/PPO에 "
         "삽입 가능"],
        ["2504.00642 Optimal Control of Walkers", "2",
         "closure constraint와 analytical derivative를 OCP 제약으로 직접 삽입"],
        ["2311.08409 Digit safe WBC", "2",
         "closed kinematic chain을 QP inverse dynamics의 constraint wrench로 반영, safety-critical 제약과 통합"],
        ["2408.08830 Digit constrained sysID", "2",
         "constraint Jacobian을 포함한 식으로 폐루프 로봇의 모터관성·마찰 파라미터를 식별"],
        ["2504.04767 Extended URDF", "3",
         "URDF의 tree 가정을 확장해 closure constraint를 표현, Pinocchio 등 기존 툴체인과 호환"],
        ["2110.00541 Validating Simulators", "3",
         "Drake/MuJoCo/Bullet의 impact 정확도를 실측과 대조 검증, Cassie jump landing 사례"],
    ]),
    para("로컬 상세 요약 — Desktop\\Parallel_Actuation_ClosedChain_Targeted_Papers\\CLOSED_LOOP_PAPERS_SUMMARY.md"),

    quote("한 장 요약 | 폐루프 논문들이 계속 나오는 이유는 'MuJoCo가 폐루프를 못 풀어서'가 아니라, GPU 병렬·표현 "
          "포맷·구속 식별·제어기 통합·검증이라는 다섯 개의 다른 문제이기 때문입니다. 다섯 표현법(A 네이티브/B "
          "축소좌표/C 직렬+자코비안/D 직렬 뭉침/E 학습 흡수) 중 어느 것이 맞는지는 그 로봇의 (루프 링크 질량비, "
          "전달비 비선형성) 좌표가 정합니다. 저희 4-bar는 전달비가 선형이라 이득이 전부 질량 배치에서 나왔고, "
          "BRUCE는 전달비가 비선형이라 이득이 전달비에서 나왔습니다 — 같은 '폐루프'라는 말 아래 정반대의 병목이 "
          "숨어 있었습니다."),
]

print("blocks9 count", len(blocks9), flush=True)
append(p9, blocks9)

# ════════════════════════════════════════════════════════════════════
# ⑨-a 전달 자코비안 우회법 완전 해부
# ════════════════════════════════════════════════════════════════════
p9a = new_page(p9, "⑨-a 전달 자코비안 우회법 완전 해부 — 무엇이 정확하고 무엇이 버려지는가")
print("p9a", p9a, flush=True)

blocks9a = [
    quote("이 페이지는 상위 페이지 ⑨의 3절 'C. 직렬 근사 + 전달 자코비안'을 수식과 저희 로봇의 실제 숫자로 완전히 "
          "해부합니다 — 무엇이 정확하고 무엇이 버려지는지를 명확히 가릅니다."),

    h2("0. 이 페이지의 위치"),
    para("C방식은 시뮬레이터 안에서 로봇을 직렬(open-chain) 다리로 취급하고, 모터 공간과 관절 공간 사이의 매핑만 "
         "자코비안으로 처리하는 방식입니다. 어떤 엔진에서도 쓸 수 있고 대규모 RL에 쉽게 올라가지만, 그 대가로 무엇을 "
         "버리는지를 이 페이지가 정량적으로 보입니다."),

    h2("1. 정의와 수식"),
    para("폐루프의 닫힘 조건을 g(q_act, q_joint) = 0 이라 하면, 이를 시간에 대해 미분해 속도 수준의 관계를 얻습니다."),
    code("g(q_act, q_joint) = 0\n"
         "  => J_act(q) * q_dot_act + J_joint(q) * q_dot_joint = 0\n"
         "  => q_dot_act = J_T(q) * q_dot_joint,   J_T(q) = -J_act(q)^-1 * J_joint(q)"),
    para("가상일(virtual work) 원리를 적용하면 힘/토크는 반대 방향으로 변환됩니다."),
    code("tau_joint = J_T(q)^T * tau_act"),
    para("J_T(q)는 '자세에 따라 변하는 기어비 행렬'입니다 — 고정 기어비가 아니라, 로봇의 현재 관절각 q에 의존하는 "
         "순간적인 변환 행렬입니다."),
    bullet("J_T의 각 성분은 '모터가 1라디안 움직일 때 관절이 몇 라디안 움직이는가'라는 순간 기어비이며, 4-bar처럼 "
           "링크 길이가 유한한 기구에서는 이 값이 자세마다 달라집니다."),
    bullet("이 두 식만 있으면, 모터가 낸 속도·토크를 관절의 속도·토크로 순간마다 정확히 옮길 수 있습니다 — 이것이 "
           "C방식의 전부입니다."),

    h2("2. 무엇이 정확한가"),
    para("이 자코비안 매핑은 정적 힘 전달과 속도 전달, 즉 기구학의 전부를 정확히 포착합니다."),
    bullet("모터가 정지 상태 근처에서 내는 힘이 관절에 얼마나 전달되는지는 J_T로 완벽히 계산됩니다."),
    bullet("속도가 느리게 변하는 준정적(quasi-static) 동작이라면, 이 매핑만으로 사실상 완벽한 시뮬레이션이 "
           "가능합니다."),
    para("이는 뉴턴의 법칙에서 관성항(질량×가속도)이 무시될 만큼 가속도가 작을 때, 힘의 평형(정역학)만으로 "
         "시스템을 기술할 수 있다는 사실의 직접적인 결과입니다."),
    para("문제는 속도가 빠르게 변할 때, 즉 링크 자체의 관성이 무시할 수 없을 때 시작됩니다 — 다음 절에서 정확히 "
         "무엇이 버려지는지를 보입니다."),

    h2("3. 무엇이 버려지는가 — 핵심"),
    para("정확한 축소 동역학의 질량행렬은 로봇을 이루는 모든 링크의 기여를 합한 것입니다."),
    code("M_red(q) = sum_i  J_i(q)^T * M_i * J_i(q)   (i = 모든 링크)"),
    para("C방식은 이 합에서 다리 본체(허벅지·정강이 등 직렬 링크)의 항만 남기고, **루프를 이루는 링크(crank·"
         "coupler)의 J_i^T M_i J_i 항, 그리고 그 항이 만드는 코리올리력·중력 기여를 통째로 삭제**합니다."),
    table([
        ["항목", "직렬 본체 링크", "루프 링크(crank·coupler)"],
        ["질량·관성 항 J_i^T M_i J_i", "A/B/C 모두 보존", "A/B는 보존, C는 삭제"],
        ["코리올리·원심력 기여", "보존", "C에서 함께 삭제"],
        ["중력 기여", "보존", "C에서 함께 삭제"],
        ["정적 힘/속도 전달(기구학)", "해당 없음", "A/B/C 모두 보존 (자코비안이 처리)"],
    ]),
    bullet("코리올리·원심력 항은 J_i의 시간미분(관절 속도에 의존하는 항)에서 나오므로, 링크 관성이 삭제되면 이 "
           "항도 함께 사라집니다 — '느린 동작에서는 괜찮다'는 말이 성립하는 이유이기도 합니다."),
    para("삭제된 항이 실제로 작으려면, 루프 링크가 가볍고 느려야 합니다 — 즉 이 근사가 안전한지는 로봇마다 다른 "
         "정량적 질문입니다."),

    h2("4. 우리 로봇 대입 — 워크드 예제"),
    para("저희 4-bar의 루프 링크는 coupler(질량 0.235kg, CoM 0.133m)와 crank(질량 0.541kg, CoM 0.021m)입니다."),
    table([
        ["부품", "질량", "CoM 거리", "역할"],
        ["coupler", "0.235 kg", "0.133 m", "무릎측 질량모멘트에 -m_c r_c 항으로 기여"],
        ["crank", "0.541 kg", "0.021 m", "무릎측 질량모멘트에 -m_p l_c 항으로 기여"],
        ["정강이(직렬 본체)", "-", "-", "+0.0139 kg·m 항으로 반대 방향 기여"],
    ]),
    code("무릎측 질량모멘트 B = -(m_c * r_c) - (m_p * l_c) = -0.0155 kg*m\n"
         "정강이 기여 +0.0139 kg*m 와 거의 상쇄되어\n"
         "최종 B (실제, A/B 방식 기준) = -0.0037 kg*m"),
    para("반면 직렬 뭉침(D방식, 또는 보정 없는 C방식 오용)은 이 값을 +0.175 kg·m로 오산합니다 — 실제값 대비 48배 "
         "크고, 부호까지 반전됩니다."),
    para("이 차이는 숫자상의 오차로 끝나지 않습니다 — 부호가 반전된다는 것은, 전원을 꺼서 토크가 0이 될 때 무릎이 "
         "어느 방향으로 기우는지, 즉 실물에서 관측되는 '무릎 정지' 거동 자체가 갈라진다는 뜻입니다."),
    para("이 예제가 바로 상위 페이지 2절 표의 네 번째 행('직렬 근사+자코비안이면 오차 0%')이 '부분 오류'로 판정된 "
         "근거입니다."),
    callout("루프 링크가 가볍다는 가정이 깨지는 순간(저희 crank처럼 로봇 전체 질량의 20%에 달할 때), C방식은 "
            "근사가 아니라 부호가 뒤집힌 오답을 냅니다.", "⚠️"),

    h2("5. 판정 기준 제안"),
    para("두 가지 질문으로 어느 방식을 써야 할지 가늠할 수 있습니다 — m_loop/m_total은 몇 % 인가? 전달비는 얼마나 "
         "비선형인가?"),
    table([
        ["", "전달비 선형", "전달비 비선형"],
        ["m_loop/m_total 작음(가벼움)", "아무 방식이나 무방", "C가 최적 (BRUCE)"],
        ["m_loop/m_total 큼(무거움)", "A/B 필수 (저희 4-bar)", "A/B 필수 + 비용 감수"],
    ]),
    para("저희 로봇은 무거운 루프 링크(20%) + 선형 전달비(평행사변형)이므로 좌측 하단 — A/B가 필수인 위치에 "
         "있습니다. BRUCE는 가벼운 루프 링크 + 비선형 전달비이므로 우측 상단 — C가 최적인 위치에 있습니다."),
    bullet("판정에 필요한 것은 정확한 문턱값이 아니라 두 축의 상대적 위치입니다 — 저희처럼 20%급 무거운 루프 "
           "링크라면 이미 안전 지대에서 벗어난 것으로 봐야 합니다."),

    h2("6. 원전 안내"),
    para("C방식의 원전은 Shen et al., ICRA 2022, \"Design and Control of a Miniature Bipedal Robot with "
         "Proprioceptive Actuation\" — BRUCE의 초기 설계·제어 논문입니다."),
    para("같은 로봇 계열의 후속 연구인 Tanaka, Zhu, Wang, Hong 등, arXiv:2507.00273 (Humanoids 2025)은 A방식(MJX "
         "네이티브)으로 전환을 선언합니다."),
    bullet("두 논문의 차이는 방법론의 우열이 아니라, 5년 사이 GPU 물리엔진(MJX)이 성숙해 A방식의 비용이 감당할 "
           "만해졌다는 도구의 진화를 반영합니다."),
    para("이 전환은 RoMeLa의 로봇 자체가 바뀌어서가 아니라, 같은 문제를 다루는 도구(MJX)가 등장했기 때문에 "
         "일어났습니다 — 방법론 선택이 로봇의 물리적 특성과 당대 도구 성숙도 두 가지 모두에 의존한다는 것을 "
         "보여줍니다."),
    callout("같은 연구실이 5년 사이에 방식을 바꾼 것 자체가 이 페이지의 결론입니다 — C방식은 틀린 방법이 아니라, "
            "도구가 부족하던 시절 루프 링크가 가벼운 로봇에 맞춰 최적화된 선택이었습니다.", "🔁"),

    h2("7. 요약"),
    para("이 페이지의 결론은 상위 페이지 ⑨의 4절('우리 로봇이 주는 교훈')과 정확히 맞닿습니다 — 저희 4-bar에서 "
         "4-bar를 명시적으로 모델링해서 얻는 이득의 100%는 질량 배치(crank 20%)에서 나왔고, 전달비 비선형성에서는 "
         "나오지 않았습니다(평행사변형이라 전달비가 애초에 상수이기 때문입니다)."),

    quote("한 장 요약 | 전달 자코비안 우회법(C방식)은 준정적 기구학(힘·속도 전달)을 완벽히 보존하지만, 루프를 "
          "이루는 링크의 질량·관성·코리올리·중력 기여를 통째로 버립니다. 이 손실이 무시할 만한지는 '루프 링크가 "
          "얼마나 가볍고, 전달비가 얼마나 비선형인가'로 결정됩니다. 저희 4-bar는 crank가 로봇 질량의 20%를 차지하는 "
          "무거운 루프였기에, C방식은 무릎측 질량모멘트의 부호까지 반전(-0.0037 -> +0.175, 48배)시켰습니다."),
]

print("blocks9a count", len(blocks9a), flush=True)
append(p9a, blocks9a)

# 검증
for name, pid in [("p9", p9), ("p9a", p9a)]:
    r = requests.get(f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100", headers=H).json()
    blocks = r.get("results", [])
    print(name, len(blocks), "blocks", flush=True)

print("PART9 DONE - https://www.notion.so/" + p9.replace("-", ""))
print("PART9A DONE - https://www.notion.so/" + p9a.replace("-", ""))
