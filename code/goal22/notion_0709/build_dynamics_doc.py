# -*- coding: utf-8 -*-
"""4-bar 동역학 정본 해설 — 해석식 vs MuJoCo + 파라미터 전서 + 순차 식별 논의 (GOAL22 하위)."""
import requests, time, json
import numpy as np
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
REPO = Path(r"C:/Users/junho/Documents/jump-opt-digital-twin")


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status(); return r
    r.raise_for_status()


def rt(t, bold=False, code=False, link=None):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold: ann["bold"] = True
    if code: ann["code"] = True
    if ann: a["annotations"] = ann
    if link: a["text"]["link"] = {"url": link}
    return a


def para(*r): return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}
def h2(t): return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}
def h3(t): return {"type": "heading_3", "heading_3": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(e, *r): return {"type": "callout", "callout": {"icon": {"emoji": e}, "rich_text": list(r)}}
def code(t, lang="plain text"): return {"type": "code", "code": {"rich_text": [rt(t)], "language": lang}}
def eq(expr): return {"type": "equation", "equation": {"expression": expr}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def new_page(parent, title, emoji):
    return req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": parent}, "icon": {"emoji": emoji},
        "properties": {"title": {"title": [rt(title)]}}}).json()["id"]


def append(pid, blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{pid}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


# ═══ 루트 ═══
root = new_page(GOAL22, "4-bar 동역학 정본 해설 — 해석식 vs MuJoCo + 파라미터 전서", "📐")
append(root, [
    callout("📐", rt("이 문서는 상설 참조 문서입니다. ", bold=True),
            rt("① 사용자 해석식(수정된 4-bar dynamics)의 항별 해설, ② MuJoCo 구현과의 정밀 비교(무엇이 같고 무엇이 다른가), "
               "③ 현재 최강 모델(P16)의 파라미터 37개 전서, ④ \"순차적으로 찾은 모델이 optimal인가?\"에 대한 정직한 논의를 담는다.")),
    bullet(rt("A. 해석식 해설 — 기호·구속·계수 A/B/K/IΣ의 물리적 의미")),
    bullet(rt("B. MuJoCo 구현 비교 — 같은 동역학, 다른 계산법 (검증 4.4e-16)")),
    bullet(rt("C. 해석식 위에 얹은 물리 계층 — 마찰·접촉·스프링·계측·액추에이터")),
    bullet(rt("D. 파라미터 전서 — 37개 전부, 의미/케이지/현재값/결정방식")),
    bullet(rt("E. 순차 식별과 최적성 — 함정 사례 4건과 방어 장치")),
    para(rt("원 유도 문서: "), rt("수정된 4-bar linkage dynamics",
         link="https://www.notion.so/302ab81d255080b4811ae496b9bbca56"),
         rt(" (기계 정밀도 검증 완료 — B 참조)")),
])

# ═══ A. 해석식 해설 ═══
pA = new_page(root, "A. 해석식 해설 — 기호와 계수의 물리", "✍️")
append(pA, [
    callout("✍️", rt("사용자가 유도한 최소좌표 동역학. 좌표 3개 q = [z, θ₁, θ₂]로 5링크 폐루프 시스템 전체를 기술한다 — "
                    "평행사변형 구속을 대수적으로 소거했기 때문에 가능한 축약이다.")),
    h2("좌표와 기구학적 구속"),
    table([
        ["기호", "의미"],
        ["z", "힙(베이스) 수직 위치 (+위)"],
        ["θ₁", "허벅지 절대 각도 (+반시계)"],
        ["θ₂", "무릎 상대 각도 (0°=폄, 굽힘이 음수)"],
    ]),
    para(rt("구속 (유도의 핵심): 허벅지 = θ₁ / 정강이 = θ₁+θ₂ / "),
         rt("크랭크 = θ₁+θ₂+π (정강이와 정확히 반대)", bold=True),
         rt(" / "), rt("커플러 = θ₁ (허벅지와 평행)", bold=True),
         rt(". 30-250-30-250 평행사변형이므로 크랭크각 ≡ 정강이각(+180°) — 그래서 자유도가 (z, θ₁, θ₂) 3개로 닫힌다. "
            "이 위상(크랭크가 무릎 위/뒤)은 07-07에 하드웨어로 확정된 그 구조다.")),
    h2("링크 기호"),
    table([
        ["링크", "질량/관성/CoM", "길이"],
        ["Thigh (허벅지)", "m_t, I_t, r_t", "l_t = 250mm"],
        ["Crank (크랭크, l_i)", "m_c, I_c, r_c", "l_c = 30mm"],
        ["Coupler (커플러, 푸시로드)", "m_p, I_p, r_p", "250mm"],
        ["Shin (정강이+발)", "m_s, I_s, r_s", "l_s = 250mm"],
    ]),
    para(rt("주: 유도 문서에는 m_t에 \"Knee 모터 무게 포함\" 표기가 있으나, 07-09 확인대로 무릎 모터는 base 중앙(직렬) 장착 — "
            "현행 MuJoCo 모델에서는 모터 질량이 base(총질량 3.2kg 역산분)에 들어가고 m_t는 CAD thigh 그대로다.")),
    h2("핵심 계수 5개 — 이 유도의 요체"),
    eq(r"A = m_t r_t + m_p r_p + m_s l_t"),
    bullet(rt("A (허벅지 축 질량 모멘트): ", bold=True),
           rt("θ₁ 방향으로 함께 도는 질량들의 1차 모멘트. 허벅지 자신 + 커플러(허벅지와 평행!) + 정강이가 허벅지 끝에 매달린 효과. "
              "CAD값 0.1289 — 힙 중력토크와 z-θ₁ 커플링의 원천")),
    eq(r"B = m_s r_s - (m_c r_c + m_p l_c)"),
    bullet(rt("B (무릎 축 질량 모멘트) — 부호 반전의 주인공: ", bold=True),
           rt("무릎이 돌 때 정강이 CoM은 앞으로(+), 크랭크·커플러는 반대 위상이라 뒤로(−) 움직여 서로 상쇄. "
              "CAD값 −0.0037 ≈ 0 — 직렬 뭉침 가정이면 +0.175였을 값(48배 부호 반전). "
              "물리적 의미: 무릎 중력토크 ≈ 0 = 전원 꺼도 무릎이 안 떨어지는 실물 관찰의 설명")),
    eq(r"K = m_s l_t r_s - m_p l_c r_p"),
    bullet(rt("K (코리올리/커플링 계수): ", bold=True),
           rt("θ₁-θ₂ 사이 관성 커플링과 원심력 항의 크기. 정강이의 회전 관성력과 커플러의 회전 관성력이 반대 위상이라 역시 빼기. "
              "CAD값 0.0029 ≈ 0 — 4-bar가 관절 간 커플링을 거의 지워버린다는 뜻 (설계의 미덕)")),
    eq(r"I_{\Sigma1} = (I_t{+}m_t r_t^2)+(I_c{+}m_c r_c^2)+(I_p{+}m_p r_p^2{+}m_p l_c^2)+(I_s{+}m_s r_s^2{+}m_s l_t^2)"),
    bullet(rt("IΣ₁ (허벅지 축 총 관성): ", bold=True),
           rt("θ₁이 돌 때 함께 도는 모든 것의 관성 합 (관성은 방향 무관 양수라 전부 더함). CAD값 0.0339")),
    eq(r"I_{\Sigma2} = (I_s + m_s r_s^2) + (I_c + m_c r_c^2) + m_p l_c^2"),
    bullet(rt("IΣ₂ (무릎 축 총 관성): ", bold=True),
           rt("θ₂만 돌 때 움직이는 것들 — 정강이 + (반대로 도는) 크랭크 + 커플러의 평행이동 성분. CAD값 0.0036")),
    h2("전체 방정식 M(q)q̈ + C + G = τ_ext"),
    eq(r"\begin{bmatrix} M_{tot} & A c_1 + B c_{12} & B c_{12} \\ A c_1 + B c_{12} & I_{\Sigma1} + 2K c_2 & I_{\Sigma2} + K c_2 \\ B c_{12} & I_{\Sigma2} + K c_2 & I_{\Sigma2} \end{bmatrix}\begin{bmatrix} \ddot z \\ \ddot\theta_1 \\ \ddot\theta_2 \end{bmatrix} + \begin{bmatrix} -A s_1 \dot\theta_1^2 - B s_{12}(\dot\theta_1{+}\dot\theta_2)^2 \\ -K s_2 (2\dot\theta_1\dot\theta_2 + \dot\theta_2^2) \\ K s_2 \dot\theta_1^2 \end{bmatrix} + \begin{bmatrix} M_{tot} g \\ g(A c_1 + B c_{12}) \\ g\,B c_{12} \end{bmatrix} = \tau_{ext}"),
    bullet(rt("질량행렬 M: 대각 = (총질량, 허벅지 관성 IΣ₁+2Kc₂, 무릎 관성 IΣ₂), 비대각 = 커플링. "
              "B≈0, K≈0이므로 실질적으로 거의 대각 — 힙과 무릎이 관성적으로 분리된 시스템")),
    bullet(rt("C (코리올리·원심력): 전부 B 또는 K에 비례 → 거의 0. 빠른 점프에서도 커플링 관성력이 미미한 이유")),
    bullet(rt("G (중력): 무릎 항 g·B·c₁₂ ≈ 0.04Nm급 — 무릎 중력 무시 가능")),
    bullet(rt("우변: τ₁, τ₂는 직렬 구동이라 더하지 않고 각자 들어감. 외란 d_x, d_z는 발끝 힘의 자코비안 전달항")),
])

# ═══ B. MuJoCo 비교 ═══
pB = new_page(root, "B. MuJoCo 구현 비교 — 같은 동역학, 다른 계산법", "⚙️")
append(pB, [
    callout("⚙️", rt("결론부터: 두 표현의 동역학 코어는 기계 정밀도로 동일하다 (무작위 300 상태에서 질량행렬 차이 |ΔM|max = 4.4e-16). "
                    "다른 것은 '표현 방식'과 그 위에 얹은 물리 계층(C 참조)이다.", bold=True)),
    h2("표현 방식 비교"),
    table([
        ["", "해석식 (사용자)", "MuJoCo 구현 (g21_fourbar_flip.py)"],
        ["좌표", "최소좌표 3개 (z, θ₁, θ₂) — 구속을 대수로 소거", "여유좌표 5개 (base_z, hip, crank, cpin, knee) + 구속 1개"],
        ["구속 처리", "평행사변형 항등식으로 정확(exact) 소거", "connect 등호구속 (커플러 끝 ↔ calf 로커점) — 소프트 구속, solref 0.8ms"],
        ["폐루프", "닫힘이 수식에 내장", "MuJoCo는 트리 구조만 지원 → 트리(thigh→crank→coupler, thigh→calf)로 자르고 등호구속으로 다시 붙임"],
        ["운동방정식", "손으로 유도한 M, C, G", "매 스텝 CRB/RNE 알고리즘으로 수치 계산 + 구속력(라그랑주 승수)"],
        ["적분", "(사용 시) 임의 적분기", "implicitfast, dt=0.5ms"],
    ]),
    h2("좌표 변환 사전 (세 좌표계)"),
    code("사용자/canonical:  q1 = θ1 (허벅지 절대각),  q2 = θ2 (무릎 상대각, 굽힘 음수)\n"
         "MuJoCo:            mj_q1 = -q1 - π/2   (0 = 허벅지가 아래로 늘어진 자세)\n"
         "                   mj_q2 = -q2         (crank 관절각; 평행사변형이라 crank각 ≡ calf각)\n"
         "5-dof 초기화:      qpos = [base_z, mj_q1, mj_q2, -mj_q2, mj_q2]  (cpin = -q2, knee = q2)\n"
         "검증용 투영행렬:   T = [[1,0,0],[0,1,0],[0,0,1],[0,0,-1],[0,0,1]]  (3좌표 -> 5좌표)"),
    h2("등가성 검증 (g21_userEq_check.py, 07-07)"),
    table([
        ["비교", "|ΔM|max", "|Δbias|max", "판정"],
        ["뒤집힌(현행) MuJoCo vs 해석식", "4.4e-16", "3.6e-14", "기계 정밀도 일치 — 같은 동역학"],
        ["구(잘못된)위상 MuJoCo vs 해석식", "3.5e-2", "—", "회전항 ~100% 상대오차 — 다른 동역학"],
    ]),
    para(rt("방법: T 투영으로 MuJoCo의 5×5 질량행렬·바이어스를 3×3으로 축약해 해석식과 무작위 300 상태에서 대조. "
            "즉 해석식은 MuJoCo 구현의 '정답지' 역할을 했고, 위상 오류(크랭크 방향)를 잡아낸 것도 이 대조였다.")),
    h2("소프트 구속은 오차가 아닌가?"),
    para(rt("connect의 solref=0.8ms는 '0.8ms 시정수의 극도로 딱딱한 스프링-댐퍼'로 루프를 붙인다는 뜻. "
            "점프 동역학의 시간 스케일(수십~수백 ms)보다 100배 이상 빠르므로 실질 강체이고, 위 검증이 그 등가성을 수치로 보증한다. "
            "P12/P8b에서 solref를 스윕해봤지만 0.8ms보다 무르게 하면 악화만 됐다 (강성 포화 영역).")),
])

# ═══ C. 물리 계층 ═══
pC = new_page(root, "C. 해석식 위에 얹은 물리 계층", "🧅")
append(pC, [
    callout("🧅", rt("해석식 = 이상적 강체 뼈대. 실물 재현에는 손실·접촉·계측의 살이 필요하다. "
                    "현행 모델이 뼈대 위에 얹은 계층들과 각각의 존재 이유:")),
    table([
        ["계층", "구현", "왜 필요한가 (근거)"],
        ["관절 마찰", "hip/crank에 점성(fv)+쿨롱(fc), cpin/knee 힌지에 미세 점성", "베어링·감속 손실. air 회귀에서 초과 쿨롱 실측"],
        ["무릎부 유연성", "crank 관절 스프링 stiff_knee=1.35, springref=2.07 (P16)", "GOAL19 발견(빼면 4.9배 악화) — 구동계 탄성의 등가 표현. ref는 P16에서 정적 편향 제거"],
        ["로터 반영 관성", "armature: crank에 arm_knee≈0.008 (hip은 0 — 시험 후 기각)", "모터 회전자 관성×감속비² — 실물 AK80-9 반영관성과 일치"],
        ["발-바닥 접촉", "실린더-평면, solref_tc/imp0 적합, 마찰 μ=1", "스탠스 컴플라이언스. 실린더 형상은 실물 그대로 (07-09 확인)"],
        ["세션 오프셋", "o1/o2 per 세션, ±3° 케이지", "엔코더 영점 드리프트"],
        ["계측 정렬", "sens_delay = −1.5ms (τ 로그가 q보다 앞섬)", "07-09 발견 — 단봉 최적, 전류식 τ 즉시 vs q 샘플링 지연"],
        ["액추에이터 변환 (경계)", "a_hat 4계수: raw 전류토크 → 축 토크", "모터 내부 손실 원장. P14에서 이 로봇 데이터로 재식별 (paper 대비 게인 +4.7%, 내부마찰 −51%)"],
    ]),
    para(rt("주의: a_hat은 루프 '안'이 아니라 경계 3곳에서 쓰인다 — ①데이터→식별 입력 ②최적화 제약 번역 ③배포 t_ff 역변환. "
            "폐루프 재현 실험에서만 루프 안에 들어간다 (실물 펌웨어 kp가 커맨드 단위로 작동하는 것을 재현하기 위해).")),
])

# ═══ D. 파라미터 전서 (라이브 값) ═══
C16 = json.load(open(REPO / "code/goal22/p16_structure/fourbar_p16_candidate.json"))
d16 = dict(zip(C16["names"], C16["x"]))
def v(n, f=4): return f"{d16[n]:+.{f}f}"

DESC = [
    ("M_base", "베이스 질량 스케일 — 죽은 파라미터 (총질량 3.2kg에서 역산)", "고정(역산)", "실측 총질량"),
    ("M_thigh", "허벅지 질량 스케일 (×CAD 0.9128kg)", "[0.92, 1.08]", "적합"),
    ("M_calf", "정강이+발 질량 스케일 (×CAD 0.2370kg, 발 포함)", "[0.97, 1.03]", "적합 (실측: CAD와 4~5g 차이)"),
    ("M_p", "커플러 질량 스케일 — 150g 실측 LOCK (=1.0983×CAD)", "LOCK", "실측"),
    ("M_c", "크랭크 질량 스케일 (클러치 모터 교체로 CAD보다 가벼움)", "[0.45, 1.00]", "적합"),
    ("I_thigh", "허벅지 관성 스케일", "[0.8, 1.2]", "적합"),
    ("I_calf", "정강이 관성 스케일", "[0.8, 1.2]", "적합 (상한 부근 — 흡수 경계)"),
    ("com_dz_th", "허벅지 CoM 축방향 오프셋 [m] (+는 무릎 쪽)", "±0.03", "적합 (+상한 안착 — P17로 케이지 유지 확정)"),
    ("com_dz_ca", "정강이 CoM 축방향 오프셋 [m]", "±0.03", "적합"),
    ("arm_knee", "무릎 로터 반영관성 (crank armature) [kg·m²]", "[0.0005, ~]", "적합 (AK80-9 반영관성 ≈0.005와 동차수)"),
    ("m_foot", "발끝 추가 점질량 [kg]", "≤0.010", "적합 (유령질량 방지 캡)"),
    ("stiff_knee", "무릎부 유연성 스프링 강성 [Nm/rad]", "적합", "GOAL19 발견, P16 drop-test 재확인"),
    ("solref_tc", "발-바닥 접촉 시정수 [s]", "적합", "접촉 컴플라이언스"),
    ("imp0", "접촉 임피던스 파라미터", "적합", "접촉 컴플라이언스"),
    ("fv_hip", "힙 점성 마찰 [Nm·s/rad]", "적합", "P14에서 τ채널이 상향 요구"),
    ("fv_knee", "무릎(crank) 점성 마찰", "적합", "P14에서 관절 원장으로 이동"),
    ("fc_hip", "힙 쿨롱 마찰 [Nm]", "적합", "—"),
    ("fc_knee", "무릎 쿨롱 마찰 [Nm]", "≥0", "≈0으로 수렴"),
    ("o1/o2 ×4세션", "세션별 엔코더 영점 오프셋 (0319/0324/0421/0424) [rad]", "±3°(0.0524)", "적합 (0602=기준 0)"),
    ("s_rc", "크랭크 CoM 위치 스케일 (×CAD)", "[0.8, 1.2]", "P13에서 해방"),
    ("s_ic", "크랭크 관성 스케일", "[0.7, 1.4]", "P13에서 해방"),
    ("s_rp", "커플러 CoM 위치 스케일", "[0.8, 1.2]", "적합 (하한 안착 — 흡수 경계)"),
    ("s_ip", "커플러 관성 스케일", "[0.7, 1.4]", "적합 (상한 안착 — 흡수 경계)"),
    ("d_cpin", "커플러 핀 점성 [Nm·s/rad]", "[0, 0.05]", "≈0으로 수렴"),
    ("d_kneep", "무릎 수동힌지 점성", "[0.0002, 0.05]", "적합"),
]

rows = [["파라미터", "P16 값", "물리적 의미", "케이지/결정방식"]]
for n, desc, cage, how in DESC:
    if n.startswith("o1/"):
        offs = ", ".join(f"{k.split('_')[1]}:{np.degrees(d16[k]):+.1f}°"
                         for k in ["o1_0324", "o2_0324", "o1_0421", "o2_0421", "o1_0424", "o2_0424"])
        rows.append([n, offs, desc, f"{cage} · {how}"])
    else:
        rows.append([n, v(n), desc, f"{cage} · {how}"])
A = [d16.get("A1"), d16.get("A2"), d16.get("A3"), d16.get("A4")]
rows += [
    ["A1 (a_hat)", f"{A[0]:.4f}", "전류→토크 변환 게인 (유효비 A1·CF=" + f"{A[0]*0.59:.3f})", "[1.0,1.35] · P14/P16 데이터 식별"],
    ["A2 (a_hat)", f"{A[1]:.2e}", "자기 포화 (고전류 2차 손실)", "[0,1.3e-3] · 〃"],
    ["A3 (a_hat)", f"{A[2]:.4f}", "모터 내부 쿨롱 마찰 [Nm]", "[0,0.45] · 〃"],
    ["A4 (a_hat)", f"{A[3]:.4f}", "모터 내부 부하비례 마찰", "[0,0.10] · 〃"],
    ["springref", f"{d16['springref'] if 'springref' in d16 else C16['x'][36]:+.3f}", "stiff_knee 스프링 기준각 (mj crank각; crouch≈2.6)", "[0,2.6] · P16 해방 — 정적편향 −80%"],
]

pD = new_page(root, "D. 파라미터 전서 — P16 스택 37개", "🧾")
append(pD, [
    callout("🧾", rt("현재 최강 스택 P16의 전 파라미터. ", bold=True),
            rt("값은 fourbar_p16_candidate.json에서 그대로 읽음. '적합'은 물리 케이지 안에서 CMA 동시 최적화로 정해졌다는 뜻이며, "
               "케이지 자체는 실측(질량)·CAD(관성·CoM)·상식(오프셋 3°)으로 사용자가 정한 값.")),
    table(rows),
    para(rt("'흡수 경계' 표기 3곳(com_dz_th/s_rp/s_ip)은 3개 모델 연속으로 케이지 벽에 앉는 파라미터 — "
            "P17 검증(off-axis 기각 + 케이지 초과 스윕에서 held-out 폭발)으로 '미모델 효과 흡수의 정직한 한계'로 최종 분류. "
            "케이지를 넘기면 과적합이 시작됨을 데이터가 직접 보여줬다.")),
])

# ═══ E. 순차 식별과 최적성 ═══
pE = new_page(root, "E. 순차 식별과 최적성 — \"지금 모델이 optimal인가?\"", "🌀")
append(pE, [
    callout("🌀", rt("질문 (07-09): \"모델을 순차적으로 찾았다면, 이전 단계에서 뭔가가 흡수된 채 굳어져서 "
                    "지금 모델이 optimal이 아닐 수 있는 것 아닌가?\" — 정당한 우려이고, 실제로 그 함정에 4번 빠졌다 나왔다.")),
    h2("실제로 겪은 '이전 단계 흡수' 사례 4건"),
    table([
        ["사례", "흡수된 것", "어떻게 발견/청산"],
        ["구위상 4-bar (G20~P9)", "잘못된 크랭크 방향 위에 전 파라미터가 fit됨", "사용자 하드웨어 지적 → 위상 뒤집고 전면 재적합 (P10~)"],
        ["유령질량 (M_p 1.7~2×)", "미모델 dq 평활 효과를 커플러 질량이 흡수", "150g 실측 잠금 → 흡수처 봉쇄 → 정직물리(P13e)"],
        ["springref=0 LOCK", "스프링 채택 시 기준각을 검토 없이 고정 → 정적 −3.5Nm 편향", "P5 정적 검증에서 발각 → P16 해방"],
        ["paper a_hat LOCK", "남의 모터 계수 → 마찰 원장 왜곡 (fc≈0으로 도주)", "이중 심판 충돌(P13i)로 발각 → P14 재식별"],
    ]),
    quote(rt("즉 '순차 탐색의 함정'은 이론적 걱정이 아니라 이 프로젝트의 실제 역사다. 그리고 4건 모두 소급 청산됐다.", bold=True)),
    h2("순차성의 함정을 막는 현행 장치 6개"),
    bullet(rt("① 전-파라미터 동시 재적합: ", bold=True),
           rt("축별 순차 채택이 아니라, P13e/P14/P16은 32~37개를 CMA로 '한꺼번에' 다시 푼다 — 이전 단계의 배분이 매번 재심된다")),
    bullet(rt("② 물리 케이지 + 실측 잠금: ", bold=True), rt("흡수가 갈 수 있는 공간 자체를 실측으로 제한 (질량 잠금, 3.2kg, ±3°)")),
    bullet(rt("③ held-out 게이트: ", bold=True), rt("0324를 학습에서 제외 — 흡수로 얻은 점수는 게이트에서 죽는다 (P17 케이지 초과가 즉사한 이유)")),
    bullet(rt("④ drop-test: ", bold=True), rt("채택된 축을 주기적으로 빼서 아직 밥값하는지 재확인 (P16에서 stiff_knee 재확인)")),
    bullet(rt("⑤ 재시동/다중시작: ", bold=True), rt("dq-가중 재적합이 사실상 재시동 역할로 더 좋은 분지 발견(P13f가 표준 obj에서도 P13e를 이김) — 국소최적 탈출의 실증")),
    bullet(rt("⑥ 이중 심판: ", bold=True), rt("한 심판에만 좋은 흡수는 다른 심판이 고발한다 (P13i 충돌이 a_hat을 잡아낸 메커니즘)")),
    h2("정직한 결론"),
    para(rt("global optimum 보장은 없다 — 비볼록 36차원 문제에서 그런 보장은 원리적으로 불가능하다. 정확한 진술은: ", bold=True)),
    bullet(rt("현 구조 + 현 데이터 + 물리 케이지 안에서, 다중 재시동 CMA가 도달 가능한 수준까지는 갔다 (여러 재시동이 같은 부근으로 수렴)")),
    bullet(rt("순차성의 유산 중 '발견된' 것은 전부 청산됐다. 남은 의심 지점은 경계-안착 3인방뿐이며 이는 흡수의 정직한 경계로 분류·감시 중")),
    bullet(rt("남은 비최적성의 지배 원천은 탐색 순서가 아니라 ⓐ 데이터 식별력의 한계(스탠스 널-공간, a_hat 순환성, 노이즈 바닥)와 "
              "ⓑ 구조 표현력의 한계(paper a_hat 형태의 s2s/점프 상충)다")),
    bullet(rt("따라서 다음 도약은 '더 좋은 최적화'가 아니라 '새 측정'(중력-벤치, t_ff 로깅)이고, 새 데이터가 오면 "
              "①번 장치(전체 동시 재적합)로 다시 섞기 때문에 순서 의존성은 계속 씻겨나간다")),
])

json.dump(dict(root=root, pA=pA, pB=pB, pC=pC, pD=pD, pE=pE),
          open(Path(__file__).parent / "handoff_dyn.json", "w"))
print("DYNAMICS DOC DONE root=", root)
