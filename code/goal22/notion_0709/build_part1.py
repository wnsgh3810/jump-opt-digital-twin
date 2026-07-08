# -*- coding: utf-8 -*-
"""07-09 τ-fidelity 실험 시리즈 노션 보고서 — part1: 부모 + 용어사전 + ①목적 + ②실험A + ③실험B."""
import requests, time, json, mimetypes
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
D = Path(r"C:/Users/junho/Desktop/jump_opt")
HANDOFF = Path(__file__).parent / "handoff.json"


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status()
        return r
    r.raise_for_status()


def rt(t, bold=False, code=False, color=None, link=None):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold: ann["bold"] = True
    if code: ann["code"] = True
    if color: ann["color"] = color
    if ann: a["annotations"] = ann
    if link: a["text"]["link"] = {"url": link}
    return a


def para(*r): return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}
def h1(t): return {"type": "heading_1", "heading_1": {"rich_text": [rt(t)]}}
def h2(t): return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}
def h3(t): return {"type": "heading_3", "heading_3": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(emoji, *r): return {"type": "callout", "callout": {"icon": {"emoji": emoji}, "rich_text": list(r)}}
def code(t, lang="plain text"): return {"type": "code", "code": {"rich_text": [rt(t)], "language": lang}}
def divider(): return {"type": "divider", "divider": {}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def upload(path):
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    r = req("POST", "https://api.notion.com/v1/file_uploads", headers=HJ,
            json={"mode": "single_part", "filename": p.name})
    fu = r.json()
    req("POST", fu["upload_url"], headers=H,
        files={"file": (p.name, p.read_bytes(), mt)})
    st = req("GET", f"https://api.notion.com/v1/file_uploads/{fu['id']}", headers=H).json()
    assert st.get("status") == "uploaded", f"upload fail {p.name}: {st.get('status')}"
    return fu["id"]


def img(path, caption=""):
    fid = upload(path)
    b = {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": fid}}}
    if caption:
        b["image"]["caption"] = [rt(caption)]
    return b


def new_page(parent, title, emoji):
    r = req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": parent}, "icon": {"emoji": emoji},
        "properties": {"title": {"title": [rt(title)]}}})
    return r.json()["id"]


def append(pid, blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{pid}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


# ═══════════════ 부모 페이지 ═══════════════
root = new_page(GOAL22, "2026-07-09 τ-fidelity 실험 시리즈 — 종합 보고서", "🎯")
append(root, [
    callout("🧭", rt("이 보고서는 2026-07-09 하루 동안 진행한 실험 시리즈 전체의 해설·논리·결과·원인 정리입니다. ", bold=True),
            rt("출발 질문은 하나였습니다 — \"트윈으로 최적화한 결과로 PD 제어를 하면, 측정되는 토크가 계획한 토크와 비슷하게 나오는가?\" "
               "이 질문 하나가 계측 발견 4건, 이론 발견 1건(널-공간), 모터 모델(a_hat) 재식별, 그리고 최종 모델 스택(P14)까지 이어졌습니다.")),
    h2("오늘의 결론 (한 문단)"),
    para(rt("현재 실험 방식(PD-only, 피드포워드 미송신)에서는 모델이 완벽해도 측정 토크가 계획 토크와 3~5Nm 어긋나는 것이 "
            "구조적으로 불가피하다 — 이것이 애초에 'currentTorque ≠ desiredTorque'를 만든 주범이었다. "),
         rt("토크 충실도를 높이는 길은 ① t_ff 송신(코드 몇 줄), ② 모터 변환 모델(a_hat)의 교정 순서이고, "
            "오늘 이중 심판 적합(P14)으로 a_hat이 paper 값과 어떻게 다른지(변환게인 +4.7%, 내부 마찰 −51% 등)까지 "
            "데이터에서 식별했다. 그 결과 모델(P14)은 폐루프 재현의 사실상 전 채널에서 기존(P13h)을 이긴다. "
            "최종 확정은 모터 벤치 측정 하나만 남았다.", bold=True)),
    h2("읽는 순서 (차일드 페이지)"),
    bullet(rt("⓪ 용어 사전 — 이 보고서에 나오는 모든 용어의 정의 (먼저 읽기를 권장)")),
    bullet(rt("① 목적 재정립 — \"측정 τ ≈ 계획 τ*\"가 왜 최종 목표이고, 왜 q·dq 정밀도가 그 목표와 같은 말인가")),
    bullet(rt("② 실험 A — 실데이터로 밝혀낸 실제 제어 법칙 + 폐루프 재현 (계측 발견 4건 포함)")),
    bullet(rt("③ 실험 B — PD-only의 구조적 한계 (모델이 완벽해도 토크는 어긋난다)")),
    bullet(rt("④ 널-공간 — 스탠스에서 토크 분배가 운동에 안 보이는 이유 (오늘의 이론 발견)")),
    bullet(rt("⑤ fit1~fit4 — 게인 적합 프런티어와 상태↔토크 보존법칙")),
    bullet(rt("⑥ 심판 충돌 → P14 — a_hat을 데이터에서 재식별한 과정")),
    bullet(rt("⑦ 반증 실험들 — a_hat 항등 대조, 속도 텀 기각, 아키텍처 판정")),
    bullet(rt("⑧ 최종 스택 — P14로 전체 재실행한 결과와 남은 일")),
    h2("원본 자료 위치"),
    bullet(rt("코드: "), rt("Documents/jump-opt-digital-twin/code/goal22/", code=True),
           rt(" (p14_ahat, p15_vterm, cl_p14, cl_fit2~4, p13i 등 폴더별)")),
    bullet(rt("그림·애니메이션: "), rt("Desktop/jump_opt/g22_cl_results, g22_cl_fit2~4_results, g22_cl_p14_results", code=True)),
    bullet(rt("실험 페이지(웹): "), rt("tau-fidelity 실험 v5", link="https://claude.ai/code/artifact/6e33131f-e177-4ad8-be17-ec70fea2d96e")),
    bullet(rt("커밋 체인: 461f109 → 40436b0 (약 15 커밋, 각 커밋 메시지에 결과 요약)")),
])

# ═══════════════ ⓪ 용어 사전 ═══════════════
p0 = new_page(root, "⓪ 용어 사전", "📖")
append(p0, [
    callout("💡", rt("이 페이지의 용어들은 보고서 전체에서 반복 사용됩니다. 모르는 용어가 나오면 여기로 돌아오세요.")),
    h2("목적·지표 관련"),
    table([
        ["용어", "정의"],
        ["τ-fidelity (토크 충실도)", "배포(실기 PD 제어) 시 측정되는 토크가 최적화가 계획한 토크(τ*)와 얼마나 가까운가. 이 연구의 최종 성공 지표. τ-갭 = 그 차이(RMSE)"],
        ["τ-갭", "τ_측정 − τ_계획 의 크기. PD 법칙에 의해 τ-갭 = Kp·(위치오차) + Kd·(속도오차) — 그래서 q·dq 정밀도가 곧 τ-fidelity"],
        ["Mode A", "측정된 토크를 시뮬레이션에 그대로 입력(개루프 replay)하고 운동(q/dq)이 재현되는지 보는 검증/식별 방식. 컨트롤러를 몰라도 됨"],
        ["폐루프 재현 (CL)", "실험 때의 지령(q_des, dq_des)과 게인을 시뮬레이션 PD에 넣고, sim이 스스로 토크를 만들며 실측과 비교하는 방식. 배포 상황과 동일 구조"],
        ["held-out / 게이트", "적합(fitting)에 쓰지 않고 남겨둔 데이터(우리는 0324 세션)로 과적합을 감시. 게이트 = held-out 성적이 기준(예: ≤1.05)을 넘으면 후보 탈락"],
        ["구간 (early/push/flight)", "폐루프 지표를 3구간으로 나눔: 초반(모션 시작 전 홀드) / 푸시(밀기~이륙) / 비행. 푸시가 가장 중요(가중 2배)"],
    ]),
    h2("모터·계측 관련"),
    table([
        ["용어", "정의"],
        ["raw currentTorque", "모터 드라이버가 보고하는 전류 기반 토크 (= 사실상 PD가 계산한 커맨드). 실제 축 토크가 아님!"],
        ["a_hat (변환 층)", "raw(전류 토크) → 실제 축 토크 환산 모델. 게인(A1)·자기포화(A2)·쿨롱마찰(A3)·부하비례마찰(A4)의 4계수. 원본은 UMich 논문의 paper 값 (남의 모터로 잰 것)"],
        ["커맨드 층", "PD가 요구한 토크 → 실제 흘린 전류의 관계. 전류 한계(우리 데이터에서 raw ~35 천장)가 여기 존재. paper 모델에는 이 층 개념이 없음"],
        ["언랩 (unwrap)", "토크 로그 채널이 12bit ±18Nm에서 감겨(wrap) 기록되는 것을 MATLAB 후처리로 복원한 것 (span 36, 복원한계 ±54). xlsx의 currentTorque는 언랩된 진짜 값"],
        ["실효 게인", "펌웨어가 실제로 실행한 PD 게인. 폴더명(라벨)과 다를 수 있음 — 0421 세션은 hip이 라벨의 ~0.6배로 확인됨 (회귀+게인적합 이중 확증)"],
        ["sens_delay (−1.5ms)", "τ 로그가 q 로그보다 1.5ms 앞서 기록되는 계측 스큐. 전류식 τ는 즉시, q는 샘플링+CAN 지연을 거치는 구조와 정합"],
    ]),
    h2("적합(fitting) 관련"),
    table([
        ["용어", "정의"],
        ["label / reg / fit", "폐루프 재현에서 게인을 정하는 세 기준. label = 폴더명 그대로(명목) / reg = 로그 회귀로 잰 실효 게인 / fit = 상태를 맞추도록 재적합한 게인"],
        ["널(null) 방향", "스탠스에서 (τ_hip, τ_knee) 평면 중 운동을 전혀 못 바꾸는 방향. 이 방향의 토크 재분배는 각도·속도에 안 보이고 발끝 수평력만 바꿈"],
        ["채널", "적합 점수에 들어가는 비교 항목 하나 (q1, q2, dq1, dq2, tau1, tau2). 'τ 채널' = 토크 비교 항목"],
        ["이중 심판", "Mode A 점수와 폐루프 점수를 동시에 목적으로 걸고 적합하는 것. 두 심판의 충돌이 a_hat 오류를 식별하는 신호가 됨 (P14)"],
        ["P13h / P14", "P13h = 어제까지의 최선 모델(계측보정 재적합). P14 = 오늘 이중 심판 + a_hat 해방으로 얻은 모델 (현재 폐루프 최강)"],
    ]),
])

# ═══════════════ ① 목적 재정립 ═══════════════
p1 = new_page(root, "① 목적 재정립 — 측정 τ ≈ 계획 τ*", "🥅")
append(p1, [
    callout("🎯", rt("사용자 정의 최종 목적: ", bold=True),
            rt("\"디지털 트윈을 제대로 만들고 → 그 위에서 최적화(NLP든 샘플링이든) → 그 결과로 실로봇 PD 제어 → "
               "이때 측정되는 토크가 최적화 계획 토크와 차이가 작아야 한다.\" 높이(h)나 상태 재현만이 아니라 토크-수준 일치가 성공 지표다.")),
    h2("왜 이것이 올바른 목표인가 (논리)"),
    para(rt("점프가 계획대로 '높이' 나왔다고 해도, 그것이 PD 피드백이 모델 오차를 힘으로 덮어서 만든 결과라면 트윈이 좋았던 게 아니라 "
            "피드백이 좋았던 것입니다. 반대로 측정 토크가 계획 토크와 거의 같다면 — PD가 할 일이 없었다는 뜻이고, "
            "그것이 곧 '트윈이 현실을 맞췄다'의 정의입니다.")),
    h2("수식 한 줄로 보는 연결고리"),
    code("배포 시 인가 토크:  τ_측정 = τ_ff(계획) + Kp·(q_des − q) + Kd·(dq_des − dq)\n"
         "따라서:            τ-갭 = τ_측정 − τ_계획 = Kp·(위치오차) + Kd·(속도오차)", "plain text"),
    para(rt("즉 "), rt("τ-갭은 상태 추종 오차의 게인-가중 합", bold=True),
         rt("입니다. kp 120~200 기준 위치오차 1° ≈ 2~3.5Nm, kd 2~5 기준 속도오차 1rad/s ≈ 2~5Nm. "
            "\"q·dq가 잘 맞아야 한다\"는 기존 방침은 이 목표의 수학적 표현 그 자체였던 것입니다.")),
    h2("이 목표가 오늘 하루를 어떻게 끌고 갔나"),
    bullet(rt("τ-갭을 직접 재려면 → 실험 때의 지령·게인으로 폐루프 재현이 필요 → 실제 제어 법칙부터 규명 (② 실험 A)")),
    bullet(rt("모델이 완벽하면 τ-갭이 0인가? → 아니었다. 구조적 하한 존재 (③ 실험 B)")),
    bullet(rt("상태만 맞추면 토크도 맞나? → 아니었다. 널-공간 때문 (④)")),
    bullet(rt("토크 채널을 심판에 넣자 → 두 심판이 충돌 → 충돌의 원인이 a_hat → 재식별 (⑥)")),
])

# ═══════════════ ② 실험 A ═══════════════
p2 = new_page(root, "② 실험 A — 실제 제어 법칙 규명 + 폐루프 재현", "🔬")
blocks2 = [
    callout("🔬", rt("질문: 실험 데이터의 (q_des, dq_des)를 시뮬레이션 PD에 넣고 실험과 똑같이 돌리면, "
                    "sim이 만드는 토크·운동이 실측과 얼마나 같은가? — 이를 위해 먼저 '실험 때 실제로 어떤 제어가 인가됐는지'부터 "
                    "데이터로 규명해야 했다.")),
    h2("A-1. 제어 법칙 회귀 — 실험은 어떻게 제어되고 있었나"),
    para(rt("24개 trial 전부에서 raw currentTorque를 kp·(q_des−q) + kd·(dq_des−dq) [+ c·desiredTorque] 로 "
            "최소자승 회귀했습니다. 결과:")),
    table([
        ["데이터셋", "실제 인가된 법칙 (R² 근거)", "비고"],
        ["03.24", "hip: PD(dq_des=0) / knee: τ_ff + PD", "유일하게 knee에 피드포워드 인가 (cff≈1.0)"],
        ["04.21", "PD(dq_des=0), R² 0.95~0.99", "실효 hip kp ≈ 라벨의 0.55~0.75배 (포화 0%인데도!) — 진짜 발견"],
        ["04.24 / 06.02", "PD(dq_des 인가)", "라벨 게인대로 실행됨. 무릎 포화율 40~62%"],
    ]),
    callout("⚠️", rt("핵심 발견 1: ", bold=True),
            rt("desiredTorque(최적화 τ*)는 로그에만 기록됐고 커맨드에는 안 들어갔다 (0324 knee 제외). "
               "즉 지금까지의 실험은 전부 PD-only — 'currentTorque ≠ desiredTorque'의 1차 원인이 여기 있었다.")),
    h2("A-2. 계측 체인의 완전 규명 (부수 발견 3건)"),
    bullet(rt("토크 채널은 12bit ±18Nm 랩: ", bold=True),
           rt("양자화 스텝 0.00879 = 36/4095로 확인. 사용자의 MATLAB 언랩(span 36, 복원한계 ±54)이 ±18을 넘는 "
              "진짜 토크를 복원한 것이었음 (35Nm 값들은 실제)")),
    bullet(rt("공급 천장 ~35 (raw): ", bold=True),
           rt("0424/0602에서 게인이 60이든 500이든 최대값이 ~35에서 멈춤 — 소프트웨어 클립이 아니라(사용자 확인: AK80-9 PD 경로 무클립) "
              "하드웨어 전류 한계로 추정. 속도 무관 평탄 → back-EMF 봉투 아님. R-Link 설정 확인 대기")),
    bullet(rt("0324(18.8)·0421(29)의 낮은 최대값은 한계가 아니라 수요가 안 닿은 것", bold=True),
           rt(" — 세션별 설정 차이 해석은 철회함")),
    h2("A-3. 폐루프 재현 프로토콜 (v5 최종)"),
    code("설정: 라벨 게인 + 클립 없음 + a_hat 액추에이터 변환 + sens_delay −1.5ms\n"
         "     dq_des: 0324/0421은 0, 0424/0602는 로그값 / 0324 knee는 τ_ff 추가\n"
         "판정: 상태(q1,q2,dq1,dq2), 토크(shaft 공간), h — trial별 6-패널 그림 + canonical 4-bar 애니메이션", "plain text"),
    para(rt("아래는 대표 trial의 재현 결과입니다. 그림 규격: q(합침, 파랑=sim/주황=real/초록=q_des), dq1, dq2 / "
            "tau hip, tau knee, GRF(실측 포함).")),
]
try:
    blocks2.append(img(D / "g22_cl_results/png/jump_0602__120_2_120_2__label.png",
                       "0602/120_2 — v5 폐루프 재현 (P13h+paper)"))
    blocks2.append(img(D / "g22_cl_results/png/jump_0424__150_2.2_500_4__label.png",
                       "0424/150_2.2_500_4 — 고게인 trial (무릎 라벨 500)"))
    blocks2.append(img(D / "g22_cl_results/gif/jump_0602__120_2_120_2__label.gif",
                       "canonical 4-bar 애니메이션 (crank 주황 = l_i, coupler 적색, l_o 로커 포함, h_sim/h_real 표기)"))
except Exception as e:
    blocks2.append(para(rt(f"[이미지 업로드 실패: {e}]")))
blocks2 += [
    h2("A-4. v5 결과 요약 (데이터셋 평균, P13h+paper 기준)"),
    table([
        ["데이터셋", "τ_hip RMSE", "τ_knee RMSE", "q2 [rad]", "dq2 [rad/s]", "h_sim / h_real"],
        ["0324", "1.25", "2.72", "0.215", "3.45", "0.678 / 0.770"],
        ["0421", "3.77", "1.59", "0.039", "1.02", "0.902 / 0.850"],
        ["0424", "2.49", "4.36", "0.032", "2.68", "0.886 / 0.829"],
        ["0602", "2.70", "5.49", "0.057", "3.04", "0.991 / 0.920"],
    ]),
    para(rt("τ-갭 RMS 1.3~5.5Nm — 이 수치가 '현재 트윈 + 실제 제어 방식'의 토크 충실도 현주소입니다. "
            "이 갭의 원인 분해가 ③~⑥의 내용입니다.")),
]
append(p2, blocks2)

# ═══════════════ ③ 실험 B ═══════════════
p3 = new_page(root, "③ 실험 B — PD-only의 구조적 한계", "🧱")
blocks3 = [
    callout("🧱", rt("질문: 모델이 '완벽'하면 τ-갭이 0이 되는가? — 트윈이 자기 자신의 최적화 결과(deploy s0.85 CSV)를 "
                    "PD로 추종하게 해서 확인했다. 모델 오차가 정의상 0인 상황이다.")),
    h2("결과 표 (트윈 자기일관, s0.85)"),
    table([
        ["제어 모드", "τ-갭 RMS hip/knee [Nm]", "최대 [Nm]", "q2 추종 [rad]", "h (계획 0.975)"],
        ["PD only (현재 실험실 방식)", "3.29 / 5.20", "5.8 / 8.7", "0.151", "0.899"],
        ["PD + τ_ff", "1.47 / 3.02", "2.5 / 5.3", "0.017", "0.999"],
        ["τ_ff only (개루프)", "0 / 0.3", "—", "0.222", "1.093 (상태민감)"],
    ]),
]
try:
    blocks3.append(img(D / "g22_cl_results/png/expB_selfconsistency.png",
                       "실험 B — 계획 τ* vs 폐루프 인가 τ (좌: 자기일관 P13e 플랜트, 우: 교차 P13h 플랜트)"))
except Exception as e:
    blocks3.append(para(rt(f"[이미지 업로드 실패: {e}]")))
blocks3 += [
    h2("왜 PD-only는 원리적으로 τ-fidelity가 불가능한가"),
    quote(rt("PD는 오차가 있어야 토크를 만든다:  τ_PD = kp·e  →  e = τ필요/kp", bold=True)),
    para(rt("무릎이 15Nm를 내야 하는 순간, kp=150이면 위치오차가 15/150 = 0.1rad = 5.7° '있어야만' 그 토크가 나옵니다. "
            "즉 PD-only에서 추종 지연은 버그가 아니라 토크의 생산 수단입니다. 모델이 완벽해도 τ-갭 3~5Nm은 "
            "이 구조가 만드는 하한입니다. τ_ff를 함께 보내면 PD는 잔차 수정만 담당하게 되어 갭이 절반 이하로 줄고 "
            "h도 계획에 붙습니다(0.999).")),
    h2("모델 불확실성의 기여는?"),
    para(rt("같은 CSV를 P13e 플랜트와 P13h 플랜트에서 각각 실행해 비교한 결과, 두 모델의 τ-갭 차이는 "),
         rt("≤0.06Nm", bold=True),
         rt(" — 구조 효과(3~5Nm)의 1/100 이하. 즉 현재 τ-갭은 모델 선택이 아니라 제어 구조가 지배합니다. "
            "\"모델을 더 다듬을까\"보다 \"t_ff를 보낼까\"가 100배 중요한 상황.")),
    callout("✅", rt("실행 처방: ", bold=True),
            rt("다음 실기 세션에서 MIT 커맨드의 t_ff 필드에 계획 토크를 채워 보낼 것 (내보내기 시 a_hat 역변환 필요 — ⑦ 참조). "
               "이것만으로 τ-갭의 지배 성분이 제거된다.")),
]
append(p3, blocks3)

json.dump(dict(root=root, p0=p0, p1=p1, p2=p2, p3=p3), open(HANDOFF, "w"))
print("PART1 DONE root=", root)
