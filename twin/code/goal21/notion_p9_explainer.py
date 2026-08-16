# -*- coding: utf-8 -*-
"""P9 — Notion 완전 해설: MuJoCo 트윈 최적화 흐름 · 접촉 · 4-bar · 파라미터 사전.
부모 페이지 + 분야별 child 7개. 이미지: file_uploads 3-step."""
# --- 저장소 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o2, sys as _s2
_d2 = _o2.path.dirname(_o2.path.abspath(__file__))
while _d2 != _o2.path.dirname(_d2) and not _o2.path.isdir(_o2.path.join(_d2, 'code', 'bench')):
    _d2 = _o2.path.dirname(_d2)
if _o2.path.join(_d2, 'code', 'bench') not in _s2.path:
    _s2.path.append(_o2.path.join(_d2, 'code', 'bench'))
from datapaths import REPO_ROOT  # noqa: E402
# ---------------------------------------------------------------
import requests, time, json
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
CONCEPT = "115ab81d255080fdaae6f28f55e3e205"
FIG = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad/p9_explain")
P6FIG = Path((REPO_ROOT + "/code/goal21"))


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
def code(t, lang="plain text"):
    return {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": lang}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


def upload(png):
    r = requests.post("https://api.notion.com/v1/file_uploads",
                      headers={**H, "Content-Type": "application/json"}, json={})
    r.raise_for_status()
    uid, url = r.json()["id"], r.json()["upload_url"]
    with open(png, "rb") as f:
        requests.post(url, headers=H, files={"file": (Path(png).name, f, "image/png")}).raise_for_status()
    return {"object": "block", "type": "image",
            "image": {"type": "file_upload", "file_upload": {"id": uid}}}


def new_page(parent, title):
    r = requests.post("https://api.notion.com/v1/pages", headers={**H, "Content-Type": "application/json"},
                      json={"parent": {"page_id": parent},
                            "properties": {"title": {"title": rt(title)}}})
    r.raise_for_status()
    time.sleep(0.4)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 90):
        r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                           headers={**H, "Content-Type": "application/json"},
                           json={"children": blocks[i:i + 90]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:400])
        time.sleep(0.4)


# ═══════════════ 부모 페이지 ═══════════════
parent = new_page(CONCEPT, "MuJoCo 트윈 최적화 완전 해설 — 흐름·접촉·4-bar·파라미터 사전 (2026-07-07)")
print("parent:", parent, flush=True)
append(parent, [
    quote("이 페이지의 목적 | \"최적화가 실제로 어떻게 돌아가는가\"를 코드 수준의 사실만으로, "
          "비유와 수식을 섞어 풀어서 설명합니다. 오늘(07-07) 질문 6개에 대한 답이 아래 child 페이지 7장에 "
          "분야별로 나뉘어 있습니다."),
    h2("질문 → 한 줄 답 → 자세한 답 위치"),
    table([
        ["질문", "한 줄 답", "child"],
        ["MuJoCo에서 로봇을 작동시키고 평가하나? gradient를 추정하나?",
         "작동이 아니라 '측정 토크 재생'. gradient는 어디에도 없음 — CMA는 순위 기반 진화", "①"],
        ["로봇이 어디까지 반영되나?",
         "링크 5개·레일·접촉·마찰·모터 관성까지 몸체로 반영. 모터 전기역학·벨트·세션 드리프트는 미반영", "②"],
        ["발끝 고정 제약은? 미끄러짐은 반영되나?",
         "고정 제약 없음 — 소프트 접촉이 매 스텝 힘을 계산. 미끄러짐은 μ=1.0 마찰 원뿔로 모델에 존재", "③"],
        ["4-bar는 식으로만 적용했나?",
         "아니오 — crank·coupler가 질량·관성을 가진 실제 몸체로 존재, connect 등식구속으로 폐루프", "④"],
        ["crank=l_i(30mm), coupler=250mm, l_o=30mm 맞나?",
         "정확히 맞음 (코드값 LC=0.03, L1=0.25, rocker 30mm) — 평행사변형이라 공칭 1:1", "④"],
        ["각 파라미터의 정의·값·물리적 의미·영향은?",
         "26개 동역학 + 7개 a_hat + 시뮬 설정 전부 표로 정리", "⑤⑥"],
        ["수학적 최적화라면 발끝 고정 같은 제약이 필요하지 않나?",
         "그건 별개 파이프라인(CasADi NLP)의 이야기 — 거기서는 실제로 그런 제약을 씀", "⑦"],
    ]),
    para("읽는 순서 권장: ① → ③ → ④ → ⑤. ②⑥⑦은 사전처럼 필요할 때."),
])

# ═══════════════ ① 최적화 루프의 실체 ═══════════════
p1 = new_page(parent, "① 최적화 루프의 실체 — '로봇 작동'이 아니라 '토크 재생', gradient는 없다")
print("child1:", p1, flush=True)
B = [
    quote("용어 | 후보(candidate): 파라미터 26개 숫자 한 세트. 평가(evaluation): 그 후보로 시뮬을 돌려 점수 하나를 얻는 일. "
          "세대(generation): CMA가 후보 20개를 한꺼번에 내는 묶음. open-loop replay: 측정 토크를 시간표대로만 주입하는 재생."),
    h2("1. 한 번의 '평가'에서 실제로 일어나는 일"),
    upload(FIG / "loop_flow.png"),
    para("질문하신 \"MuJoCo에서 로봇을 작동시키고 그 데이터로 평가하냐\"에 대한 정확한 답: **작동(제어)이 아니라 재생(replay)입니다.** "
         "시뮬레이션 안에는 제어기가 없습니다. 실제 로봇이 점프할 때 기록된 토크 τ(t)를 0.5ms마다 관절 모터에 "
         "그대로 주입하고, 시뮬 로봇이 그 토크로 어떻게 움직이는지를 지켜봅니다. 녹음된 피아노 연주(MIDI)를 "
         "다른 피아노에서 틀어보고 '같은 소리가 나는가'를 듣는 것과 같습니다. 같은 소리가 나면 두 피아노(실물/모델)가 같은 악기라는 뜻."),
    bullet("**입력**: 실측 τ (a_hat 변환 후, 좌표·부호 변환 — child ⑥). 데이터는 500 Hz, 시뮬 적분은 2,000 Hz라 사이는 선형보간."),
    bullet("**시작**: 매 재생 앞에 0.4초 settle 단계 — 가상 PD(kp=500, kd=10)로 초기 자세(q1=-73°, q2=146° mujoco frame)를 잡고 바닥에 정착시킴. 이 PD는 fitting 대상이 아니고 초기조건 재현용."),
    bullet("**출력**: 시뮬의 q1, q2, dq1, dq2 궤적. 실측(500 Hz 시각)에서 샘플해 RMSE 계산."),
    bullet("**점수**: score = 100×(q1 RMSE + q2 RMSE) + 50×(dq1 RMSE + dq2 RMSE). 각도가 rad, 속도가 rad/s라 가중치 100/50이 균형을 맞춤."),
    h2("2. 세 가지 '시험 길이' — 왜 하나로는 안 되나"),
    table([
        ["시험", "길이", "역할", "약점"],
        ["창 (multiple shooting)", "0.1 s (점프) / 0.25 s (s2s)", "0.1s마다 실측 상태로 리셋 → 순수 동역학 응답만 평가. fit의 주력",
         "누적 편향에 눈멂 — 이것만 쓰면 게이밍됨 (07-06 증명)"],
        ["full-stance", "push-off 전체 (~0.3 s)", "저속 편향 누적을 잡음. 하이브리드 목적의 두 번째 항", "이륙 이후는 못 봄"],
        ["full-replay", "점프 전체 (settle~착지)", "최종 심판 (갤러리 그래프). fit에는 안 씀", "카오스 증폭 — 작은 오차도 크게 보임"],
    ]),
    para("현재 fit 목적함수 = 창 점수 6그룹 + full-stance 2그룹 (각각 canonical 대비 정규화, canonical=8.0). "
         "그리고 **fit에 안 넣은 날짜(0324 full-stance)를 held-out 게이트**로 써서 '점수는 좋은데 일반화가 깨진 후보'를 걸러냅니다. "
         "P5/P6에서 이 게이트가 과적합 후보를 정확히 잡아냈습니다 (raw best가 held-out 1.8~2.7배 악화)."),
    h2("3. gradient는 어디에도 없다 — CMA-ES가 실제로 하는 일"),
    para("**gradient(기울기)를 추정하지 않습니다.** 이유부터: 접촉이 있는 시뮬레이션은 목적함수가 매끄럽지 않습니다. "
         "파라미터를 아주 조금 바꿔도 발이 닿는 타이밍이 한 스텝 달라지면 점수가 툭 튀는 불연속이 생기고, "
         "open-loop 재생은 카오스적이라 수치 미분(유한차분)이 노이즈 범벅이 됩니다. 그래서 미분 없는(derivative-free) 방법을 씁니다."),
    para("CMA-ES의 동작을 비유로: **바람에 흩뿌리는 씨앗**입니다. ① 현재 '중심'과 '퍼짐 모양(공분산)'을 가진 "
         "확률분포에서 후보 20개를 샘플 → ② 전부 병렬 평가(워커 10개) → ③ 점수 **순위**만 보고 좋은 후보들 쪽으로 "
         "중심을 이동, 좋은 후보들이 늘어선 방향으로 분포를 길쭉하게 변형 → ④ 반복. 점수의 크기가 아니라 순위만 쓰기 때문에 "
         "점수가 튀어도 강건하고, 공분산이 파라미터 간 상관(예: 질량↑ ↔ 관성↓ 보상)을 자동 학습합니다 — "
         "이게 gradient의 역할을 '분포의 방향성'으로 대신하는 부분입니다."),
    bullet("과거 자체 A/B: G9에서 CMA vs TPE(BO) vs differential evolution vs Grid vs Random 비교 — 이 규모(연속 10~30차원)에서 CMA 우세/동률."),
    bullet("선형인 파라미터(관성 등)는 탐색 대신 볼록 회귀(최소제곱)로 푸는 게 전역해 보장 — P1/P2에서 병행, canonical과 일치 확인."),
    bullet("MJX(미분가능 MuJoCo)로 gradient 하강도 가능하지만, P8 다중시작 프로브(1000점 전패)가 보여주듯 같은 분지로 내려갈 뿐."),
    h2("4. 규모 감각"),
    bullet("평가 1회 = 24 trial × 창 ~40개 + full-stance 15개 재생 ≈ 캐시 후 0.1~2초."),
    bullet("P5 재적합 = 1,520 평가, P6 = 1,900 평가, P8 프로브 = 1,420 평가. 역대 누적으로는 grid 1.69억, BO 30만 trial."),
    para("**평가 예시 그래프** (0424 120_2_120_2 full-replay — 파랑 canonical, 주황/초록 a_hat 변형, 점선 실측):"),
    upload(P6FIG / "p6_replay_jump_0424_120_2_120_2.png"),
]
append(p1, B)

# ═══════════════ ② 시뮬레이터 속의 로봇 ═══════════════
p2 = new_page(parent, "② 시뮬레이터 속의 로봇 — 무엇이 반영되고 무엇이 빠졌나")
print("child2:", p2, flush=True)
B = [
    quote("용어 | body: MuJoCo의 강체 하나. joint: 몸체 사이의 자유도. slide joint: 직선 이동 자유도(레일). "
          "hinge: 회전 자유도. armature: 관절에 더해지는 회전자 반영 관성."),
    h2("1. 몸체 트리 — 시뮬 안에 '존재'하는 것들"),
    code("world\n"
         "└ base (slide joint 'base_z' — 수직 레일, 질량 1.26 kg × M_base 스케일)\n"
         "   └ thigh (hinge 'hip' — 실측 τ_hip 주입, 질량 0.913 kg × M_thigh, 250 mm 캡슐)\n"
         "      ├ crank (hinge 'knee_motor' — 실측 τ_knee 주입 + armature + 모터마찰 + 비틀림 스프링, 30 mm)\n"
         "      │  └ coupler (수동 pin — 푸시로드 250 mm, 질량 0.137 kg × M_p)\n"
         "      └ calf (수동 hinge 'knee' — 250 mm, 발 실린더 포함)\n"
         "         └ foot geom (실린더 r=21 mm, 반길이 6.5 mm — 바닥과 접촉하는 유일한 부위)\n"
         "equality: connect(coupler 끝 == calf의 rocker 점)  ← 4-bar 폐루프"),
    para("**레일**: 실제 로봇이 수직 레일에 묶여 있듯, base에 수직 slide joint 하나만 있습니다. "
         "x(전후)·회전 자유도는 없음 — 실물의 레일 구속을 그대로 반영한 선택이고, 대신 레일 자체의 마찰은 0으로 둡니다 "
         "(P2 회귀에서 f_rail 추정치가 나왔지만 비행 데이터로는 신뢰 불가 판정, 낙하시험 대기)."),
    h2("2. 반영된 물리 (몸체/설정으로 존재)"),
    table([
        ["항목", "어떻게 반영", "근거"],
        ["질량·관성·CoM", "CAD 값 × fit 스케일 (부품 5개 각각)", "mid-push 에너지 0.99로 검증"],
        ["4-bar 전동", "실제 링크 + connect 구속 (child ④)", "serial 대비 -9% (구조만으로)"],
        ["무릎 유연성", "crank 축 비틀림 스프링 1.13 Nm/rad", "GOAL19 flex 발견 계승"],
        ["모터 회전자 관성", "knee_motor armature 0.0035 kg·m²", "AK80-9 rotor×기어비²"],
        ["관절 마찰", "hip/knee damping(점성)+frictionloss(쿨롱)", "4개 fit"],
        ["접촉", "소프트 접촉 + 마찰 원뿔 μ=1.0 (child ③)", "solref/imp0 fit"],
        ["중력/적분", "9.81, implicitfast 0.5 ms", "G9 P10 A/B로 선택"],
    ]),
    h2("3. 반영되지 않은 것 (알면서 뺀 것 + 한계)"),
    bullet("**모터 전기역학** — 전류 루프·인덕턴스·전압 한계. 대신 입력 데이터 쪽에서 a_hat 변환으로 흡수 (child ⑥). whip 영역(고속) 정확도 한계의 유력 원인."),
    bullet("**벨트/스크류 전달 손실** — 관절 쿨롱·점성으로 뭉뚱그림. 저부하에서 η 0.1~0.7로 큰데 (P1/P2 에너지 사다리) 점프 부하에선 η≈0.94~1이라 점프 fit엔 영향 작음."),
    bullet("**세션 드리프트** — 날짜별 오프셋 8개로 영점만 반영. 벨트 텐션류 세션 변화(에너지 ~20%)는 어떤 고정 파라미터로도 원리적 반영 불가 → 배포 시 세션 보정 제안."),
    bullet("**레일 마찰, 3D 효과(평면 모델), 케이블 힘, 엔코더 양자화** — 미반영."),
    para("요약: **강체 동역학과 접촉은 '몸체'로, 액추에이터는 '입력 변환'으로, 세션 변화는 '오프셋'까지만** — "
         "이 경계선이 곧 남은 오차의 지도이기도 합니다."),
]
append(p2, B)

# ═══════════════ ③ 접촉과 발끝 ═══════════════
p3 = new_page(parent, "③ 발끝과 접촉 — '고정 제약'이 아니라 소프트 접촉, 미끄러짐 포함")
print("child3:", p3, flush=True)
B = [
    quote("용어 | 소프트 접촉: 침투 깊이에 비례한 힘을 주는 스프링-댐퍼식 접촉. solref: 그 스프링의 시정수·감쇠 설정. "
          "solimp: 힘이 얼마나 단단하게 걸리는지(임피던스) 곡선. 마찰 원뿔: 접선력이 μ×수직력을 못 넘는 제약의 기하학적 표현. "
          "condim 6: 수직+접선 2방향+비틀림+구름 마찰까지 켠 설정."),
    h2("1. 질문의 핵심 — \"발끝을 지면에 고정하는 제약이 필요하지 않나?\""),
    para("**수기 수식(해석적 동역학)으로 스탠스를 풀 때는 맞는 말입니다** — 발끝 위치를 구속조건으로 놓고 "
         "라그랑주 승수(=지면반력)를 풀어야 하죠. 실제로 저희 P2 에너지 회귀와 CasADi NLP(child ⑦)가 그렇게 합니다. "
         "하지만 **MuJoCo는 그 구속을 손으로 넣지 않습니다.** 매 스텝(0.5 ms)마다:"),
    bullet("① 충돌 검사: 발 실린더(r=21 mm)와 바닥 평면이 겹쳤는지, 얼마나(침투 깊이 d) 겹쳤는지 계산"),
    bullet("② 수직력: 침투에 대한 스프링-댐퍼 응답으로 F_n 생성 — 강성은 solref_tc(시정수 6 ms), 단단함 곡선은 solimp(imp0 0.371)가 결정"),
    bullet("③ 접선력: F_t ≤ μ·F_n 원뿔 안에서 미끄럼을 막는 힘을 최적화로 풂 (elliptic cone, μ=1.0)"),
    bullet("④ 그 힘들을 관절에 전파해 가속도 적분 — 발이 뜨면(침투 0) 힘도 자연히 0 → **이륙이 자동으로 발생**"),
    upload(FIG / "contact_model.png"),
    para("비유: 발밑에 아주 뻣뻣한 **고무 매트**가 깔려 있다고 생각하면 됩니다. 서 있으면 살짝(≪1 mm~수 mm) 눌리며 "
         "반력이 생기고, 뛰어오르면 매트가 펴지며 힘이 사라집니다. '고정'과 '자유'를 스위치로 전환하는 게 아니라 "
         "하나의 연속 법칙이 스탠스→이륙→비행→착지를 전부 커버합니다. 그래서 이륙 시점을 미리 정해줄 필요가 없고, "
         "이륙 타이밍 자체가 모델 검증 지표(ste)가 됩니다."),
    h2("2. 미끄러짐 — 반영되어 있고, 한계도 명확"),
    para("**모델 안에는 있습니다**: 접선력이 μ·F_n(μ=1.0)에 도달하면 발이 미끄러집니다. condim 6이라 "
         "비틀림(0.02)·구름(0.01) 마찰까지 켜져 있습니다. 다만 **실측 μ를 식별하진 못했습니다** — 점프 데이터에서 "
         "발이 실제로 미끄러진 순간이 드물어 정보가 없고(약식별), 그래서 μ는 고무-바닥 문헌값 1.0으로 고정하고 "
         "실데이터의 미끄러짐 의심 구간은 fit 대상이 아니라 '잔차 스파이크 감지기'로만 취급합니다 (GOAL21 계획 원칙)."),
    h2("3. solref/solimp — 두 파라미터의 물리적 의미"),
    table([
        ["파라미터", "canonical 값", "물리적 의미", "바꾸면 생기는 일"],
        ["solref_tc", "6.0 ms", "접촉 스프링의 시정수. 작을수록 단단한 바닥 (k ∝ 1/tc²)",
         "작게 → GRF 스파이크·채터링, 크게 → 발이 파묻히고 이륙 늦어짐"],
        ["imp0", "0.371", "임피던스 시작값 — 침투 초기에 힘이 얼마나 빨리 차오르나 (0~1)",
         "크게 → 첫 접촉부터 강하게 반발(딱딱), 작게 → 부드러운 안착"],
    ]),
    para("이 둘은 GRF로 fit한 게 아니라 **q/dq 창 점수로 fit**했습니다 (GRF는 계측 신뢰도 문제로 fit에서 제외 — "
         "이륙 이벤트 감지에만 사용). 즉 '바닥의 촉감'이 다리 운동 재현에 미치는 영향을 통해 간접 식별된 값입니다."),
]
append(p3, B)

# ═══════════════ ④ 4-bar ═══════════════
p4 = new_page(parent, "④ 4-bar 링키지의 실체 — 식이 아니라 링크 5개, 치수 확인 (l_i=30, coupler=250, l_o=30)")
print("child4:", p4, flush=True)
B = [
    quote("용어 | crank(크랭크): 모터가 직접 돌리는 짧은 입력 레버. coupler(커플러): 크랭크와 출력 레버를 잇는 긴 막대(푸시로드). "
          "rocker(로커): 출력 쪽 레버 — 여기서는 calf에 붙은 30 mm 팔. connect: MuJoCo의 '두 점을 붙여라' 등식 구속(3D 볼조인트에 해당)."),
    h2("1. 치수 확인 — 질문하신 그대로입니다"),
    table([
        ["부재", "코드 상수", "값", "실물 대응"],
        ["crank (입력 레버)", "LC_VAL", "**0.030 m = 30 mm**", "**l_i** — CVT 조절 레버 (실험 세션 전부 30 mm 고정)"],
        ["coupler (푸시로드)", "L1_VAL", "**0.250 m = 250 mm**", "무릎으로 힘을 내려보내는 250 mm 부품"],
        ["rocker (출력 레버)", "connect 앵커 위치", "**무릎 아래 30 mm = l_o**", "calf에 붙은 출력 팔"],
        ["thigh (고정 링크)", "L1_VAL", "0.250 m", "4-bar의 '지면 링크' 역할"],
        ["calf", "L2_VAL", "0.250 m", "출력 몸체 (발까지)"],
    ]),
    upload(FIG / "fourbar_geom.png"),
    para("네 변이 30-250-30-250 — **평행사변형**입니다. 그래서 기구학적으로는 crank 각도 = calf 각도(전달비 정확히 1:1)이고, "
         "엔코더가 읽는 모터각을 그대로 무릎각으로 써온 기존 관행이 기하학적으로 정당화됩니다. "
         "(CVT의 본래 개념은 l_i를 바꿔 이 비를 바꾸는 것 — 최적화 task들에서 다뤘고, 식별에 쓴 실험 세션은 전부 30 mm.)"),
    h2("2. \"식으로만 적용했나?\" — 아니오, 몸체로 존재합니다"),
    para("전달비가 1:1이면 '식으로 치환해도 되는 것 아닌가?' 싶지만, 그게 바로 이전 모델들(serial)의 함정이었습니다. "
         "MuJoCo 안에서 crank와 coupler는 **질량·관성·회전축을 가진 실제 강체**입니다:"),
    bullet("crank: 0.656 kg (CVT l_i 조절 기구 포함!) — **hip에 고정된 축**에서 회전. serial 모델은 이 0.66 kg을 calf에 뭉쳐 넣어 '병진하는 유령 질량'을 만들었음"),
    bullet("coupler: 0.137 kg, thigh와 평행하게 병진+회전 — 고유의 원심·코리올리 항을 만듦"),
    bullet("폐루프: coupler 끝과 calf의 rocker 점을 connect 구속으로 결합 — 매 스텝 구속력(링크 내부 힘)이 계산되어 좌우 몸체에 작용"),
    bullet("solref 0.0008의 구속 컴플라이언스 + crank 축 비틀림 스프링(stiff_knee 1.13 Nm/rad) — 링키지의 유연성까지 반영"),
    h2("3. 왜 이게 결정적이었나 — 증거 3개"),
    bullet("**G20-A**: 순수 CAD 질량 그대로 4-bar만 켜도 serial 대비 -9%. fit 없이 구조만으로 이긴 것 — 유령 질량 제거 효과"),
    bullet("serial 시절 질량 fit이 항상 바운드에 몰리던 미스터리(M_calf→0.30, I_calf→1.8)가 4-bar에서 소멸 — '가벼운데 관성 큰 calf'라는 불가능 요구의 정체가 crank 뭉침이었음"),
    bullet("**P4 역검증**: serial에서 강력했던 Stribeck 마찰항이 4-bar에 얹으면 전부 악화 — serial의 그 항은 빠진 구조의 대리물이었다는 증명. 4-bar에선 knee 쿨롱이 0.99→0.057로 자연 감소"),
    para("요약: 4-bar는 수식 치환이 아니라 **관성 분포의 교정**입니다. 전달비(1:1)는 부산물이고, "
         "본질은 '0.66 kg이 어디에 붙어 어떤 축으로 도는가'를 실물과 일치시킨 것."),
]
append(p4, B)

# ═══════════════ ⑤ 파라미터 사전 ═══════════════
p5 = new_page(parent, "⑤ 파라미터 사전 — 26개 동역학 파라미터의 정의·값·물리적 의미·영향")
print("child5:", p5, flush=True)
B = [
    quote("읽는 법 | '값'은 canonical(fourbar_refit_best). 스케일 파라미터는 CAD 값에 곱하는 배수입니다. "
          "'영향'은 그 파라미터를 키웠을 때 시뮬 거동이 어떻게 변하는가."),
    h2("A. 질량 스케일 5개 (CAD × 배수)"),
    table([
        ["이름", "값", "적용 대상 (CAD)", "물리적 의미 / 영향"],
        ["M_base", "1.048", "베이스 1.260 kg → 1.32 kg", "레일 캐리지+배선. 크면 이륙속도↓, 착지 충격↑"],
        ["M_thigh", "1.101", "허벅지 0.913 kg → 1.005 kg", "hip 부담과 다리 스윙 관성. 크면 hip 토크 요구↑"],
        ["M_calf", "0.918", "정강이 0.237 kg → 0.218 kg", "whip(이륙 직전 무릎 스냅) 관성. 작으면 dq2 피크↑"],
        ["M_p", "1.719", "coupler 0.137 kg → 0.235 kg", "푸시로드+너트 실질량. CAD 대비 +72% = 최대 이탈 — 스크류 너트 등 미모델 부품 흡수로 해석"],
        ["M_c", "0.824", "crank 0.656 kg → 0.541 kg", "l_i 조절 기구 포함 크랭크. hip축 회전 관성에 기여"],
    ]),
    h2("B. 관성·CoM 5개"),
    table([
        ["이름", "값", "적용 대상", "물리적 의미 / 영향"],
        ["I_thigh", "0.687", "0.00923 → 0.00634 kg·m²", "허벅지 회전 관성. 작으면 hip 각가속 민첩"],
        ["I_calf", "1.156", "0.00181 → 0.00209 kg·m²", "정강이 회전 관성. whip 진폭에 직결"],
        ["com_dz_th", "+0.059 m", "CoM 0.056 → 0.115 m (아래로)", "허벅지 무게중심 위치. 중력 토크 팔 길이 변경"],
        ["com_dz_ca", "+0.036 m", "CoM 0.059 → 0.095 m", "정강이 무게중심. 스윙 다이내믹스"],
        ["m_foot", "0.087 kg", "발끝 추가 점질량", "고무발+볼트. 접촉 직전 운동량과 GRF 피크에 민감"],
    ]),
    h2("C. 구동계 2개"),
    table([
        ["이름", "값", "정의", "물리적 의미 / 영향"],
        ["arm_knee", "0.0035 kg·m²", "knee_motor 관절 armature", "회전자 관성×기어비²(9²=81배 증폭). 크면 무릎 응답이 둔해지고 whip 감쇠"],
        ["stiff_knee", "1.135 Nm/rad", "crank 축 비틀림 스프링", "링키지·벨트 유연성 뭉침. 무릎이 '살짝 출렁'하는 것 — GOAL19 under-jump의 열쇠였던 flex"],
    ]),
    h2("D. 접촉 2개 (child ③ 상세)"),
    table([
        ["이름", "값", "정의", "영향"],
        ["solref_tc", "6.0 ms", "접촉 스프링 시정수", "바닥의 단단함"],
        ["imp0", "0.371", "임피던스 시작값", "첫 접촉의 반발 성격"],
    ]),
    h2("E. 관절 마찰 4개"),
    table([
        ["이름", "값", "정의", "물리적 의미 / 영향"],
        ["fv_hip", "0.488 Nm·s/rad", "hip 점성마찰 (속도 비례)", "빠를수록 큰 저항. 크면 push-off 파워 손실 — P4에서 '이게 과도할 수 있다'는 시그널"],
        ["fc_hip", "0.169 Nm", "hip 쿨롱마찰 (방향만)", "베어링+벨트 건마찰"],
        ["fv_knee", "0.014", "knee 점성", "4-bar 도입 후 거의 0 — 구조가 손실을 대신 설명"],
        ["fc_knee", "0.057 Nm", "knee 쿨롱", "동일. serial 시절 0.99였던 것이 구조 교정 후 자연 감소"],
    ]),
    h2("F. 날짜별 엔코더 오프셋 8개"),
    para("세션마다 전원 인가 시 영점이 조금 다르다는 사실(사용자 확인)의 반영. 0602를 기준(0)으로 나머지 날짜에 "
         "(q1, q2) 오프셋 2개씩. 물리 모델이 아니라 **계측 보정(nuisance)** — 값이 ±2°를 넘는 부분은 "
         "물리 영점이 아니라 다른 미모델 효과를 흡수한 것으로 해석해야 한다는 게 07-06 결론."),
    table([
        ["날짜", "o1 (hip)", "o2 (knee)"],
        ["03.19 (s2s)", "-5.1°", "+5.8°"],
        ["03.24", "-2.5°", "+8.0°"],
        ["04.21", "-4.8°", "-3.4°"],
        ["04.24", "+3.6°", "+1.8°"],
        ["06.02 (기준)", "0°", "0°"],
    ]),
    h2("G. 고정된 시뮬 설정 (fit 아님 — 그러나 결과에 중요)"),
    table([
        ["항목", "값", "의미"],
        ["timestep / integrator", "0.5 ms / implicitfast", "G9 P10 A/B 테스트로 선택. 접촉 안정성"],
        ["마찰 계수 (바닥·발)", "μ = 1.0 / 0.02 / 0.01", "미끄럼/비틀림/구름. 고무-콘크리트 문헌값 고정"],
        ["cone / condim / impratio", "elliptic / 6 / 100", "마찰 원뿔 형태·차원, 수직-접선 강성비"],
        ["settle", "0.4 s, PD(500, 10)", "초기 자세 정착용 가상 제어 (fit 무관)"],
        ["창 가중치", "W_Q=100, W_DQ=50", "각도/속도 RMSE 균형"],
    ]),
    para("**한 줄 요약**: 26개 중 물리 파라미터는 18개(A~E), 계측 보정이 8개(F)입니다. 물리 18개는 CAD 주변 "
         "±30% 내 보정이 대부분이고(예외: M_p +72%), P5·P8 검증으로 이 조합이 현 데이터의 전역 최적임이 확인된 상태입니다."),
]
append(p5, B)

# ═══════════════ ⑥ 입력 토크의 길 ═══════════════
p6 = new_page(parent, "⑥ 입력 토크의 길 — 로봇 로그에서 시뮬 입력까지 (a_hat 변환)")
print("child6:", p6, flush=True)
B = [
    quote("용어 | iTM: 모터 드라이버가 보고하는 전류 기반 토크 추정치(raw). Iq: q축 전류 — 토크를 만드는 전류 성분. "
          "a_hat: UMich AK80-9 논문의 5-파라미터 보정식 — 전류→실제 축 토크."),
    h2("1. 왜 변환이 필요한가"),
    para("로봇이 기록하는 'currentTorque'는 **전류에 상수를 곱한 추정치**일 뿐, 실제 축에 나오는 토크가 아닙니다. "
         "모터 내부에는 ① 전기→기계 변환 이득 오차, ② 고전류에서의 자기 포화(전류만큼 토크가 안 나옴), "
         "③ 기어박스 마찰(방향 의존), ④ 부하가 클수록 커지는 마찰이 있습니다. UMich 논문이 같은 모터(AK80-9)를 "
         "벤치에서 실측해 이 네 효과를 5개 계수로 정리한 것이 a_hat입니다."),
    h2("2. 식과 계수 (Pure Paper — sgn(v) 원형 유지)"),
    code("Iq = (CF / (GR·KT)) · iTM,   CF=0.59, GR=9, KT=0.091 Nm/A\n"
         "tau = a0 + a1·GR·KT·Iq  -  a2·GR·|Iq|·Iq  -  a3·sgn(v)  -  a4·|Iq|·sgn(v)\n"
         "A_HAT = [0, 1.156, 4.17e-4, 0.2686, 0.0490]"),
    table([
        ["계수", "값", "물리적 의미"],
        ["a0", "0", "영점 오프셋 (paper에서 0)"],
        ["a1", "1.156", "전기→기계 이득 보정 (+15.6% — 명판보다 실제 토크상수가 큼)"],
        ["a2", "4.17e-4", "포화: 전류 제곱에 비례해 토크 깎임 (고전류에서 -)"],
        ["a3", "0.269 Nm", "속도 방향 쿨롱 마찰 (기어박스)"],
        ["a4", "0.049 Nm/A", "부하(전류) 비례 마찰 — 무거울수록 마찰도 큼"],
    ]),
    h2("3. 시뮬까지의 전체 경로"),
    bullet("① 로그 iTM (500 Hz) → a_hat 변환 → '실제 축 토크' 추정 (canonical 데이터셋의 tau_real)"),
    bullet("② 좌표 변환: 시뮬 좌표계는 부호가 반대 — τ_mj = -τ_canonical (각도도 q1_mj = -q1 - π/2, q2_mj = -q2)"),
    bullet("③ 재생 시 0.5 ms마다 500 Hz 시간표를 선형보간해 d.ctrl에 주입"),
    h2("4. 어제(P6) 실험 — a_hat 계수를 풀어보면?"),
    para("사용자 지시로 a0~a4를 fit에 포함(관절별 마찰항 분리, 7개)해 봤습니다. 결과: 0424/0602는 뚜렷이 좋아지고(q2 -24/-17%) "
         "0324가 크게 나빠지는 **시소** — 전 날짜 동시 개선은 불가(플래토 4중 확인). 단, 세 프로브가 공통으로 "
         "**knee의 a3↑·a4→음수**를 요구 = 범용 a_hat이 우리 knee 유닛에서 고부하 마찰을 과감산한다는 물리 시그널. "
         "확정은 replay로 불가능하고 **모터 벤치에서 knee a3/a4 재측정**이 지목된 실험입니다."),
]
append(p6, B)

# ═══════════════ ⑦ NLP와의 대조 ═══════════════
p7 = new_page(parent, "⑦ '수학적 최적화'(CasADi NLP)와의 대조 — 발끝 고정 제약은 여기 이야기")
print("child7:", p7, flush=True)
B = [
    quote("용어 | NLP: 비선형 계획법 — 궤적 전체를 변수로 놓고 제약 하에 목적을 최소화. IPOPT: 그 해를 찾는 gradient 기반 솔버. "
          "collocation/direct transcription: 궤적을 이산 점들로 표현해 동역학을 등식 제약으로 거는 기법."),
    h2("1. 프로젝트에는 '최적화'가 두 개 있다 — 헷갈리기 쉬운 지점"),
    table([
        ["", "트윈 fitting (이 문서 ①~⑥)", "궤적 최적화 NLP (최종 목적)"],
        ["무엇을 찾나", "모델 파라미터 26개", "점프 궤적 (q(t), τ(t))"],
        ["모델", "MuJoCo (수치 시뮬)", "CasADi 해석적 동역학 (수식)"],
        ["gradient", "없음 (CMA 순위 기반)", "**있음** — 자동미분 + IPOPT"],
        ["접촉 처리", "소프트 접촉이 자동 (child ③)", "**손으로 제약**: 스탠스 phase에 발끝 위치 고정, GRF≥0, 마찰 원뿔"],
        ["이륙", "힘이 0 되면 자연 발생", "phase 전환 시점을 변수/스케줄로 명시"],
    ]),
    para("질문하신 \"수학적으로 최적화하려면 발끝 고정 제약이 필요하지 않나\"가 정확히 **오른쪽 열**의 이야기입니다. "
         "NLP에서는 동역학이 매끄러운 수식이어야 미분이 가능하므로, 접촉 같은 불연속을 phase 분할 + 제약으로 "
         "직접 설계합니다: 스탠스 구간엔 '발끝 = 지면의 한 점' 등식 제약과 'GRF ≥ 0, |F_t| ≤ μF_n' 부등식 제약, "
         "비행 구간엔 접촉힘 0. MuJoCo 쪽은 그 반대 — 제약을 안 쓰는 대신 미분을 포기(CMA)한 겁니다. "
         "**서로의 약점을 보완하는 역할 분담**입니다."),
    h2("2. 둘이 만나는 곳 — 지금 로드맵"),
    bullet("트윈(MuJoCo)에서 식별한 물리 → NLP 동역학 수식에 이식 (4-bar 관성 교정, 마찰 재배분 — serial Stribeck 항은 smooth해서 NLP 적합)"),
    bullet("NLP가 만든 최적 τ 궤적 → 트윈에서 open-loop 리허설 (G20: 마찰+접촉 매칭으로 sim-real 갭 -14→-4.4%) → 실 로봇 배포"),
    bullet("실 로봇 결과 → 다시 트윈/NLP 개선의 데이터 — 이 루프가 sim-to-real transfer의 전체 그림"),
    para("즉: **MuJoCo 트윈 = 물리를 배우는 곳, NLP = 그 물리로 궤적을 설계하는 곳, 실 로봇 = 채점하는 곳.** "
         "이 문서(①~⑥)는 첫 번째 상자의 내부를 연 것입니다."),
]
append(p7, B)

# verify
for name, pid in [("parent", parent), ("c1", p1), ("c2", p2), ("c3", p3), ("c4", p4), ("c5", p5), ("c6", p6), ("c7", p7)]:
    r = requests.get(f"https://api.notion.com/v1/blocks/{pid}/children?page_size=100", headers=H).json()
    blocks = r.get("results", [])
    imgs = [b for b in blocks if b.get("type") == "image"]
    ok = all(b["image"].get("type") in ("file", "file_upload") or "file" in b["image"] for b in imgs)
    print(f"{name}: {len(blocks)} blocks, {len(imgs)} images ({'OK' if ok else 'CHECK'})", flush=True)
print("PARENT_URL https://www.notion.so/" + parent.replace("-", ""))
