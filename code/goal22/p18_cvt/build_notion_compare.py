# -*- coding: utf-8 -*-
"""노션: P16 vs P18b — 변속 없는 모델과 무엇이 같고 무엇이 달라졌나 (상세 대조)."""
import requests, time, json, mimetypes
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
GOAL22 = "396ab81d2550814b9780f32285133840"
DST = Path(r"C:/Users/junho/Desktop/jump_opt/g22_cvt_0429_results")


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status(); return r
    r.raise_for_status()


def rt(t, bold=False, code=False):
    a = {"type": "text", "text": {"content": t}}
    ann = {}
    if bold: ann["bold"] = True
    if code: ann["code"] = True
    if ann: a["annotations"] = ann
    return a


def para(*r): return {"type": "paragraph", "paragraph": {"rich_text": list(r)}}
def h1(t): return {"type": "heading_1", "heading_1": {"rich_text": [rt(t)]}}
def h2(t): return {"type": "heading_2", "heading_2": {"rich_text": [rt(t)]}}
def bullet(*r): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(r)}}
def quote(*r): return {"type": "quote", "quote": {"rich_text": list(r)}}
def callout(e, *r): return {"type": "callout", "callout": {"icon": {"emoji": e}, "rich_text": list(r)}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def img(path, caption=""):
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    fu = req("POST", "https://api.notion.com/v1/file_uploads", headers=HJ,
             json={"mode": "single_part", "filename": p.name}).json()
    req("POST", fu["upload_url"], headers=H, files={"file": (p.name, p.read_bytes(), mt)})
    st = req("GET", f"https://api.notion.com/v1/file_uploads/{fu['id']}", headers=H).json()
    assert st.get("status") == "uploaded", p.name
    b = {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": fu["id"]}}}
    if caption:
        b["image"]["caption"] = [rt(caption)]
    return b


root = req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
    "parent": {"page_id": GOAL22}, "icon": {"emoji": "⚖️"},
    "properties": {"title": {"title": [rt("P16 vs P18b — 변속 없는 모델과 무엇이 같고, 무엇이 달라졌나")]}}}).json()["id"]

B = [
    callout("⚖️", rt("세 줄 요약: ", bold=True),
            rt("① 파라미터 42개 중 41개 계열이 완전히 동일 — 질량·관성·CoM·마찰·접촉·링키지·armature·세션 q오프셋·a_hat 4계수·sens_delay 전부 P16 값 그대로 (재적합 안 함). "
               "② 바뀐 것은 무릎 스프링 하나: 1.330 Nm/rad@크랭크 → \"0.404@무릎 힌지 + l_i=30mm 전용 프리로드 +2.06 Nm\"로 분해. "
               "③ 변속 없는(평행사변형) 세션 성능은 \"완전히 그대로\"는 아니고 \"평균 동률\" — 8개 그룹 평균 1.00이지만 그룹별로 −11%~+10% 재분배됐고, "
               "CL은 fit 세션 +7% 손해 / held-out(0324) 3% 개선.", bold=True)),

    h1("1. 파라미터 전수 대조"),
    table([
        ["파라미터 계열", "P16 (변속 없는 세션들로 적합)", "P18b", "동일 여부"],
        ["질량 5종 (M_base/thigh/calf/p/c)", "0.9999/1.080/0.9717/1.0985/0.5330", "왼쪽과 동일", "✅ 동일"],
        ["관성 2종 (I_thigh/I_calf)", "0.8560/1.1505", "동일", "✅"],
        ["CoM 오프셋 2종 (com_dz_th/ca)", "+0.0299/−0.0194", "동일", "✅"],
        ["관절 마찰 4종 (fv/fc × hip/knee)", "0.400/0.0112/0.0249/0.0044", "동일 (배치도 크랭크 유지)", "✅"],
        ["접촉 2종 (solref_tc/imp0)", "0.00453/0.3302", "동일", "✅"],
        ["armature (arm_knee)", "0.00753", "동일", "✅"],
        ["링키지 6종 (P13 N6, cpin/knee damping 포함)", "…/d_cpin 0.0004/d_kneep 0.0231", "동일", "✅"],
        ["세션 q 오프셋 8종 (0319/0324/0421/0424)", "±3° 이내", "동일", "✅"],
        ["a_hat 4계수 (A1~A4)", "1.2227/1.0e-3/0.1692/0.0218", "동일", "✅"],
        ["sens_delay", "−1.5 ms", "동일", "✅"],
        ["무릎 스프링 강성", "1.330 Nm/rad", "0.404 Nm/rad", "❌ 변경"],
        ["무릎 스프링 기준각 (springref)", "2.067 rad", "2.149 rad", "❌ 변경"],
        ["무릎 스프링 위치", "크랭크(모터) 관절", "무릎(종아리) 힌지", "❌ 변경 (30mm에선 수학적 동일)"],
        ["프리로드 토크 (신설)", "— (스프링에 뭉쳐 있었음)", "무릎 +2.0~2.4 Nm, l_i=30mm 세션 전용 (hip: s2s −0.22, 0421 +0.38)", "🆕"],
        ["0429 세션 파라미터 (신설)", "—", "q 오프셋 (+3.14°, −3.00°), 프리로드 0", "🆕"],
    ]),

    h1("2. 스프링이 어떻게 바뀌었나 — 한 장의 그림"),
    para(rt("아래는 두 모델이 무릎에 공급하는 여분 토크를 자세별로 수치 계산(qfrc_passive)한 것이다:")),
]
B.append(img(DST / "p16_vs_p18b_spring.png",
             "P16(파랑) vs P18b(주황): 평행사변형 작동범위(음영) 중앙에서 두 곡선은 0.7Nm 이내로 겹친다. 초록 점선 = 프리로드가 빠지는 CVT(l_i=25mm)에서 모델이 보는 것"))
B += [
    bullet(rt("겹치는 이유 = P16이 통했던 이유: ", bold=True),
           rt("작동범위 중앙(무릎 60~130°)에서 P16의 가파른 스프링(0.8→3.5Nm)과 P18b의 \"평평한 프리로드+약한 스프링\"(2.3→3.1Nm)은 평균 0.66Nm, 최대 1.5Nm밖에 안 다르다. "
              "평행사변형 데이터만 보면 두 모델은 사실상 같은 모델이다 — 그래서 P16 적합이 이 절충값(1.33)에 수렴했던 것.")),
    bullet(rt("갈라지는 곳 = 그룹별 ±10% 재분배의 원천: ", bold=True),
           rt("완전 폄 근처(<60°)에서 P16은 훨씬 적은 토크를 준다. 이 차이가 이륙 직전 구간에 걸려 있어 fs_0602(+10%)·habs(+9%)는 약간 손해, "
              "반대로 s2s(−6%)·w_0324(−11%)는 이득 — 평균은 정확히 동률.")),
    bullet(rt("초록 점선 = 이 분해의 존재 이유: ", bold=True),
           rt("CVT(l_i=25.08mm)에서는 프리로드가 사라지고 약한 스프링만 남는다. P16을 그대로 쓰면(파란 곡선을 크랭크 좌표로 외삽) 크라우치에서 −3.5Nm 가짜 정적 토크 + 과대점프 +10.7cm가 나왔던 것.")),

    h1("3. 변속 없는 세션 성능 — 정확한 숫자"),
    para(rt("Mode A 창 심판 (그룹 절대값, 작을수록 좋음; 괄호 = P16 대비 비율):")),
    table([
        ["그룹", "P16", "P18b", "비율", "판정"],
        ["w_0421 (위치제어 점프)", "2514", "2695", "1.07", "소폭 손해"],
        ["w_0424 (점프)", "3558", "3540", "0.99", "동률"],
        ["w_0602 (점프)", "2539", "2657", "1.05", "소폭 손해"],
        ["w_0324 (점프, held-out)", "2010", "1795", "0.89", "개선"],
        ["w_s2s (sit-to-stand)", "5372", "5041", "0.94", "개선"],
        ["fs_0424 (전구간 재생+높이)", "1070", "1032", "0.96", "개선"],
        ["fs_0602", "590", "652", "1.10", "손해"],
        ["habs (점프높이 절대오차 합)", "0.269 m", "0.293 m", "1.09", "소폭 손해"],
        ["8그룹 평균", "1.00", "—", "1.00", "동률"],
    ]),
    para(rt("폐루프(CL) 심판:")),
    table([
        ["항목", "P16", "P18b (프리로드를 플랜트에 인가)", "비율"],
        ["C (fit 세션 τ-채널)", "0.894", "0.956", "1.07 (게이트 1.05 소폭 초과)"],
        ["Cg (held-out 0324)", "1.027", "0.998", "0.97 — 기준보다 개선"],
    ]),
    callout("📌", rt("답: \"성능이 그대로냐\"에 대한 정직한 대답 — ", bold=True),
            rt("평균적으로는 정확히 동률이고 held-out은 오히려 좋아졌지만, 그룹별로는 −11%~+10% 재분배가 있었다. "
               "\"P16과 같은 모델이냐\"는 질문엔: 변속 없는 데이터가 보는 범위 안에서는 사실상 같은 모델이고(위 그림), "
               "그 데이터가 보지 못하는 곳(완전 폄 근처, 그리고 l_i≠30mm 전체)에서 다른 모델이다.")),

    h1("4. 변속(0429) 세션 성능 — 이 분해가 산 이유"),
    table([
        ["0429 (l_i=25.08mm)", "P16 그대로", "P18b", "개선"],
        ["Mode A score", "243.7", "75.8", "−69%"],
        ["q2(크랭크) RMSE", "0.462 rad", "0.098 rad", "−79%"],
        ["dq2 RMSE", "13.1 rad/s", "3.24 rad/s", "−75%"],
        ["점프높이 갭", "+10.7 cm", "+4.7 cm", "−56%"],
        ["크라우치 정적 유지토크", "−3.24 Nm (실측 +0.05)", "≈0 정합", "정적 갭 해소"],
    ]),

    h1("5. 왜 P16 값이 '틀렸던' 게 아니라 '뭉쳐 있었던' 것인가"),
    quote(rt("평행사변형에서는 크랭크각≡무릎각이라 (a) 스프링의 위치(크랭크/무릎), (b) 위치 의존 성분과 상수 성분의 배합을 데이터가 원리적으로 구분할 수 없다. "
             "P16의 1.330은 그 축퇴 안에서 '스프링 역할 + 프리로드 역할'을 한 스프링이 떠맡은 최적 절충값이었다. "
             "l_i=25.08mm 데이터(0429)가 축퇴를 깨자 두 성분이 분리됐고, CL 판별 실험(센서 편향 해석 1.19 vs 플랜트 토크 해석 1.07/0.97)이 "
             "프리로드가 실재 토크임을 확정했다.")),

    h1("6. 사용 가이드"),
    bullet(rt("l_i=30mm 실험 예측: ", bold=True), rt("두 모델 실질 동급. 단 P18b 사용 시 프리로드 +2.06Nm을 반드시 포함해야 함 (빼면 스프링 제거 실험처럼 s2s가 ×5 붕괴).")),
    bullet(rt("l_i≠30mm (CVT) 예측: ", bold=True), rt("P18b만 유효 — 프리로드 0 + 무릎 스프링 0.404. P16은 크랭크 좌표 외삽으로 크게 틀림.")),
    bullet(rt("canonical 교체: ", bold=True), rt("벤치 검증(l_i=28 vs 30 동일 자세 유지토크, ±2Nm 확인) 후 권장. 중간 l_i에서의 프리로드 프로파일(계단인지 연속인지)은 미지 — 변속 중 데이터가 생기면 P18c 축.")),
    para(rt("모델 파일: "), rt("code/goal22/p18_cvt/fourbar_p18b_candidate.json", code=True),
         rt(" · 마라톤 전 과정: 노션 \"P18b 마라톤 — 변속(0429) 오차 해결\" · 코드: "),
         rt("code/goal22/p18_cvt/", code=True)),
]
for i in range(0, len(B), 80):
    req("PATCH", f"https://api.notion.com/v1/blocks/{root}/children",
        headers=HJ, json={"children": B[i:i + 80]})
    time.sleep(0.4)
print("COMPARE NOTION DONE:", "https://www.notion.so/" + root.replace("-", ""))
