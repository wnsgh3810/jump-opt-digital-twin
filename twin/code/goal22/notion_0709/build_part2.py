# -*- coding: utf-8 -*-
"""07-09 노션 보고서 — part2: ④널공간 ⑤fit1~4 ⑥P14 ⑦반증 ⑧최종스택 (자체완결)."""
# --- 옛 결과 폴더 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o3, sys as _s3
_d3 = _o3.path.dirname(_o3.path.abspath(__file__))
while _d3 != _o3.path.dirname(_d3) and not _o3.path.isdir(_o3.path.join(_d3, 'code', 'bench')):
    _d3 = _o3.path.dirname(_d3)
if _o3.path.join(_d3, 'code', 'bench') not in _s3.path:
    _s3.path.append(_o3.path.join(_d3, 'code', 'bench'))
from datapaths import LEGACY_ROOT  # noqa: E402
# ---------------------------------------------------------------
import requests, time, json, mimetypes
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
HJ = {**H, "Content-Type": "application/json"}
D = Path(LEGACY_ROOT)
HANDOFF = Path(__file__).parent / "handoff.json"
root = json.load(open(HANDOFF))["root"]


def req(method, url, **kw):
    for i in range(6):
        r = requests.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status()
        return r
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
def callout(emoji, *r): return {"type": "callout", "callout": {"icon": {"emoji": emoji}, "rich_text": list(r)}}
def code(t, lang="plain text"): return {"type": "code", "code": {"rich_text": [rt(t)], "language": lang}}


def table(rows, header=True):
    return {"type": "table", "table": {
        "table_width": len(rows[0]), "has_column_header": header, "has_row_header": False,
        "children": [{"type": "table_row", "table_row": {"cells": [[rt(str(c))] for c in row]}}
                     for row in rows]}}


def upload(path):
    p = Path(path)
    mt = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    fu = req("POST", "https://api.notion.com/v1/file_uploads", headers=HJ,
             json={"mode": "single_part", "filename": p.name}).json()
    req("POST", fu["upload_url"], headers=H, files={"file": (p.name, p.read_bytes(), mt)})
    st = req("GET", f"https://api.notion.com/v1/file_uploads/{fu['id']}", headers=H).json()
    assert st.get("status") == "uploaded", f"upload fail {p.name}"
    return fu["id"]


def img(path, caption=""):
    fid = upload(path)
    b = {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": fid}}}
    if caption:
        b["image"]["caption"] = [rt(caption)]
    return b


def new_page(parent, title, emoji):
    return req("POST", "https://api.notion.com/v1/pages", headers=HJ, json={
        "parent": {"page_id": parent}, "icon": {"emoji": emoji},
        "properties": {"title": {"title": [rt(title)]}}}).json()["id"]


def append(pid, blocks):
    for i in range(0, len(blocks), 80):
        req("PATCH", f"https://api.notion.com/v1/blocks/{pid}/children",
            headers=HJ, json={"children": blocks[i:i + 80]})
        time.sleep(0.4)


def safe_img(path, cap):
    try:
        return [img(path, cap)]
    except Exception as e:
        return [para(rt(f"[이미지 업로드 실패 {Path(path).name}: {e}]"))]


# ═══════════════ ④ 널-공간 ═══════════════
p4 = new_page(root, "④ 널-공간 — 토크 분배가 운동에 안 보이는 이유", "🕳️")
b4 = [
    callout("🕳️", rt("사용자 관찰에서 출발: ", bold=True),
            rt("\"fit이 knee 토크를 더 쓰면 hip은 그만큼 덜 쓰네?\" — 이 관찰이 오늘의 이론 발견으로 이어졌다.")),
    h2("스쿼트 비유"),
    para(rt("사람이 스쿼트로 일어날 때 엉덩이와 무릎이 함께 밀지만, 몸이 올라가는 모습만 봐서는 두 관절이 힘을 "
            "어떻게 나눴는지 알 수 없습니다. 같은 궤적으로 일어나는 힘-분배가 무한히 많기 때문입니다.")),
    h2("왜 우리 로봇이 정확히 이 상황인가"),
    para(rt("푸시 구간에서 발은 바닥에 고정, 몸통은 레일로 수직 구속 → 좌표 3개(base_z, q1, q2)에 구속 2개 → "),
         rt("자유도 1", bold=True),
         rt(". 몸 높이 하나가 정해지면 두 관절 각도가 자동으로 정해집니다. 자유도는 1인데 토크는 2개이므로:")),
    quote(rt("운동이 결정하는 것은 a₁(q)·τ₁ + a₂(q)·τ₂ 라는 조합 하나뿐. "
             "직교 방향(널 방향)의 토크 재분배는 각도·속도를 한 치도 못 바꾸고, 발끝의 수평(x) 마찰력만 바꾼다.", bold=True)),
    para(rt("여기서 a(q) = 발-고정 자코비안에서 나오는 벡터(J·a = (0,−1))이고, 널 방향은 그에 수직인 방향입니다. "
            "우리 자세 범위에서 교환비는 Δτ_hip ≈ +2×Δτ_knee (기하 예측 +2.0~+2.4).")),
    h2("정량 검증 (24 trial)"),
    table([
        ["항목", "결과"],
        ["Δτ(fit−label)의 널 방향 에너지 비율", "중앙값 ~95%, 19/24 trial에서 90%+ — fit의 게인 자유는 사실상 이 불가시 방향의 자유였다"],
        ["측정 기울기 vs 기하 예측", "0421에서 +1.6~1.9 vs 예측 +2.2 (일치)"],
        ["잔차(label−real)의 상관", "널 방향과 다른 구조 — 즉 label 잔차는 '운동에 보이는' 진짜 모델 오차"],
    ]),
]
b4 += safe_img(D / "g22_cl_results/png/p12_tradeoff_example.png",
               "0602/90 — (fit−label) 토크 재분배 산점이 기하 예측 널 방향(주황선)에 정렬")
b4 += [
    h2("이 발견의 세 가지 함의"),
    bullet(rt("상태(q/dq)만 맞추는 적합은 스탠스 토크 분배를 원리적으로 식별 못 한다 → τ 비교는 실제 게인(label) 재현으로만 유효")),
    bullet(rt("트윈 식별 심판에 τ-잔차 채널을 추가해야 분배가 잡힌다 (⑥ P13i/P14의 설계 근거)")),
    bullet(rt("수평 GRF를 측정하면 분배를 운동학과 독립적으로 직접 검증 가능 (현재 플레이트는 수직만 — 실험실 위시리스트)")),
]
append(p4, b4)

# ═══════════════ ⑤ fit1~fit4 ═══════════════
p5 = new_page(root, "⑤ fit1~fit4 — 게인 적합 프런티어와 보존법칙", "⚖️")
b5 = [
    callout("⚖️", rt("같은 폐루프 재현에서 '게인을 무엇에 맞추는가'를 4가지로 바꿔가며, "
                    "상태 충실도와 토크 충실도가 게인 공간에서 어떻게 상충하는지 지도를 그렸다.")),
    h2("네 가지 비용함수 (COST_fit*.txt로 각 폴더에 기록)"),
    table([
        ["변형", "비용함수 요지", "τ 채널"],
        ["fit1", "100·(q1+q2 RMSE) + 10·(dq1+dq2 RMSE), 전 구간, 정규화 없음 → 사실상 dq2 지배", "없음"],
        ["fit2", "구간가중(초0.5/푸시2/비행1) × 채널 정규화(라벨=1) 평균, 6채널 동일가중", "있음"],
        ["fit3", "fit2 + 채널가중 q1=3, dq2=3 (나머지 1)", "있음"],
        ["fit4", "fit3에서 τ 채널 제거 (상태 4채널만)", "없음"],
    ]),
    h2("결과 프런티어 (push 구간 중앙값, 0602 예)"),
    table([
        ["", "q1 [rad]", "dq2 [rad/s]", "τ_hip [Nm]", "널 비율"],
        ["label (기준)", "0.014", "2.67", "2.98", "—"],
        ["fit1", "0.037", "0.83", "5.78 (폭파)", "78~99%"],
        ["fit2", "0.016", "2.09", "2.51 (최선)", "19~69%"],
        ["fit3", "0.012", "2.14", "2.96", "79~94%"],
        ["fit4", "0.009 (최고)", "1.58", "6.58 (폭파)", "92~96%"],
    ]),
    quote(rt("보존법칙: 게인 공간 안에서 상태 충실도와 토크 충실도는 상충한다. "
             "τ를 감시하지 않으면(fit1/fit4) 상태를 얼마든지 좋게 만들 수 있지만, 그것은 실제 로봇이 낸 토크와 "
             "다른 토크로 달성한 상태다 — 트윈 검증 관점에서는 허구.", bold=True)),
    h2("부산물 — 실효 게인의 이중 확증"),
    para(rt("τ 채널이 있는 fit2의 게인은 아무데나 못 가고 '실제 실행된 게인'으로 수렴해야 합니다. 실제로 0421의 "
            "fit2 hip kp(39~115)가 로그 회귀 실효 게인(45~111)과 거의 일치 — 서로 독립적인 두 방법의 수렴으로 "),
         rt("0421 세션의 hip 실효 게인 ≈ 라벨의 0.6배가 확정", bold=True),
         rt("됐습니다. 고게인 무릎(라벨 250~500)의 실효 강성도 ~0.4-0.7배로 일관 (전류 천장의 게인-등가 표현).")),
]
b5 += safe_img(D / "g22_cl_fit2_results/png/jump_position_0421__P100_D0.75_P100_D2__fit2.png",
               "fit2 예시 (0421/P100) — τ 감시 하 게인 적합: hip τ가 label 재현보다 좋아짐")
b5 += safe_img(D / "g22_cl_fit3_results/png/jump_0602__90_0.75_90_2__fit3.png",
               "fit3 예시 (0602/90) — q1·dq2 우선 + τ 감시")
b5 += safe_img(D / "g22_cl_fit4_results/png/jump_0424__150_2.2_500_4__fit4.png",
               "fit4 예시 (0424/500_4) — τ 감시 제거: 상태 최고, 토크 왜곡")
append(p5, b5)

# ═══════════════ ⑥ P14 ═══════════════
p6 = new_page(root, "⑥ 심판 충돌 → P14: a_hat을 데이터에서 재식별", "🔩")
b6 = [
    callout("🔩", rt("오늘의 가장 중요한 기술적 성과. ", bold=True),
            rt("두 심판(Mode A vs 폐루프 τ-채널)의 충돌을 역이용해 모터 변환 모델 a_hat의 4계수를 "
               "이 로봇의 데이터로 재식별했다.")),
    h2("충돌의 발견 (P13i)"),
    para(rt("폐루프 τ-채널 심판으로 32개 모델 파라미터를 재적합하자 폐루프는 −13.4% 좋아졌는데(0421 τ_hip 4.41→2.71Nm −39%) "
            "Mode A가 +32% 나빠졌습니다. 파라미터 이동의 방향이 원인을 말해줬습니다: τ 채널은 hip 마찰을 크게 요구"
            "(fv_hip 0.24→0.45, fc_hip 0.024→0.133)하는데, Mode A는 그 마찰이 에너지를 깎아 점프가 낮아지니 거부.")),
    quote(rt("같은 손실을 두 장부가 서로 다르게 요구한다 = 손실의 원장(a_hat)이 틀렸다는 신호.", bold=True)),
    h2("모터 안의 두 장부 (개념)"),
    code("전류 측정점 ──①모터 내부 손실(감속기 마찰·포화 = a_hat 담당)──> 출력축\n"
         "출력축 ──②관절/구동계 마찰(fv/fc = MuJoCo 모델 담당)──> 다리 운동", "plain text"),
    para(rt("①과 ②는 물리적으로 별개지만, 운동 데이터만으로는 배분이 안 보입니다(둘 다 속도의 함수인 토크 손실). "
            "그런데 Mode A는 에너지 총량을, 폐루프 τ 채널은 관절별 배분을 각각 구속하므로 — 둘을 동시에 목적으로 걸면 "
            "배분이 식별됩니다. 이것이 P14의 아이디어입니다.")),
    h2("P14 설계와 결과"),
    bullet(rt("자유 파라미터 36 = 기존 32(물리 케이지 유지) + a_hat 4계수 (A1 게인, A2 포화, A3 쿨롱, A4 부하마찰)")),
    bullet(rt("목적 = ½(Mode A 정규화 점수 + 폐루프 정규화 점수), 이중 held-out 게이트 (fs_0324 + CL 0324, 둘 다 ≤1.05)")),
    bullet(rt("결과: ", bold=True), rt("JA 0.985 + JC 0.911 — 두 심판 최초 동시 개선 (충돌 해소). habs(이륙 apex 오차) −36%")),
    h2("식별된 a_hat (paper → P14)"),
    table([
        ["계수", "의미", "paper", "P14", "변화"],
        ["A1", "변환 게인", "1.1561", "1.2101", "+4.7% (유효 변환비 0.682→0.714)"],
        ["A2", "자기 포화(고전류 2차)", "4.17e-4", "8.42e-4", "×2.0"],
        ["A3", "쿨롱 마찰", "0.2686", "0.2437", "−9%"],
        ["A4", "부하 비례 마찰", "0.0490", "0.0239", "−51%"],
    ]),
    table([
        ["명령 τ_rep", "paper의 축 토크", "P14의 축 토크", "차이"],
        ["10 Nm", "6.00", "6.33", "+5.5%"],
        ["18 Nm", "10.74", "11.02", "+2.6%"],
        ["25 Nm", "14.68", "14.72", "≈0"],
        ["35 Nm", "19.98", "19.33", "−3.3%"],
    ]),
    para(rt("곡선이 '회전'했습니다: 저·중부하에서 모터가 paper 추정보다 더 내고, 고전류에선 포화가 더 셉니다. "
            "그만큼 관절 점성이 손실을 받아갔습니다(fv_knee 0.018→0.048) — 예측했던 '손실의 이사' 그대로.")),
]
b6 += safe_img(D / "g22_cl_results/png/p14_ahat_curve.png",
               "paper vs P14 a_hat 곡선 — 모터 벤치에서 검증할 정량 예측")
b6 += [
    h2("정직한 한계"),
    bullet(rt("full-replay 언더점프는 미해소 (0424 0.907, 0602 0.938) — 데이터 내 식별력의 끝")),
    bullet(rt("w_s2s가 +25% 지불 — 저속(s2s)과 고속(점프)이 다른 a_hat을 요구 = paper 5계수 구조의 한계 힌트")),
    bullet(rt("최종 확정은 모터 벤치: 위 표의 곡선이 벤치에서 잴 '예측치'다 (저부하 2~3점 + 중부하 2~3점이면 판정)")),
]
append(p6, b6)

# ═══════════════ ⑦ 반증 실험들 ═══════════════
p7 = new_page(root, "⑦ 반증 실험들 — 항등 대조, 속도 텀, 아키텍처 판정", "🧪")
b7 = [
    callout("🧪", rt("사용자의 회의(懷疑)가 만든 세 가지 대조 실험 — 전부 모델·방법론의 신뢰도를 높였다.")),
    h2("7-1. a_hat 항등 대조 — \"sim은 시킨 만큼 낸다고 치면 안 되나?\""),
    para(rt("a_hat을 항등(명령=축토크)으로 바꿔 폐루프 재현을 돌린 결과:")),
    table([
        ["데이터셋", "h_sim 항등", "h_sim a_hat", "q2 RMSE 항등/a_hat"],
        ["0421", "0.865", "0.902", "0.120 / 0.039 (3.1배 악화)"],
        ["0424", "0.863", "0.886", "0.086 / 0.032 (2.7배)"],
        ["0602", "0.964", "0.991", "0.137 / 0.057 (2.4배)"],
    ]),
    bullet(rt("배운 것 1 (예측 실패 인정): ", bold=True),
           rt("h는 폭발하지 않았다 — 폐루프에서 PD는 액추에이터 게인 오차마저 흡수한다 (샤워기 원리: 수압이 세지면 손잡이를 덜 튼다)")),
    bullet(rt("배운 것 2: ", bold=True),
           rt("대신 '움직임의 모양'이 실물과 2~3배 어긋난다 — 실물은 손실 때문에 무겁게 뒤처지며 추종하는데 항등 sim은 착착 붙는다. "
              "트윈 목적에는 실격 → a_hat은 폐루프에서 에너지가 아니라 응답 모양 때문에 필요")),
    h2("7-2. 속도 텀 검증 (P15) — 학습/시험 분리 실험"),
    para(rt("\"a_hat에 속도 항(A5·v)만 추가하고 Mode A로만 학습, 폐루프는 시험지로\" — 사용자 제안 구조. 판정:")),
    bullet(rt("A5 → 0.0001 (기각): ", bold=True),
           rt("Mode A는 속도 텀을 선택하지 않음 — 관절 점성(fv)과 중복이라 필요가 없었다")),
    bullet(rt("대신 Mode A 단독으로도 P14 방향을 재발견 (A1·CF→0.736, A3 −26%) — 방향성 3중 확증")),
    bullet(rt("미학습 폐루프 전이는 미약 (dq1만 0.77→0.61/0.74→0.68 개선, 나머지 중립) → "),
           rt("τ-fidelity까지 원하면 이중 심판(P14 구조)으로 학습해야 함을 학습/시험 분리로 재확인", bold=True)),
    h2("7-3. 아키텍처 판정 — a_hat은 어디에 필요한가"),
    para(rt("사용자 주장 \"identify→optimize→deploy 본류에서 sim 모터는 이상적이어도 된다\"는 "),
         rt("옳다", bold=True), rt(". a_hat은 루프 밖 경계 3곳에만 등장한다:")),
    table([
        ["경계", "역할", "비고"],
        ["① 데이터 → 식별 입력", "raw를 축 토크로 환산해 Mode A 입력으로", "기존부터 하던 것"],
        ["② 최적화 제약 번역", "전류 천장·스펙(커맨드 공간)을 축 공간 한계로 번역", "τ*_shaft ≤ a_hat(한계, v)"],
        ["③ 배포 내보내기", "t_ff 커맨드 = a_hat⁻¹(τ*_shaft) — 그대로 보내면 32% 부족", "sim 게인→실기 환산도 1/0.68"],
    ]),
    para(rt("폐루프 안에 a_hat을 넣는 것은 '실물 세션 재현 실험'(②의 실험 A류) 전용이다 — "
            "실물 펌웨어의 kp가 커맨드 단위로 작동하기 때문.")),
]
append(p7, b7)

# ═══════════════ ⑧ 최종 스택 ═══════════════
p8 = new_page(root, "⑧ 최종 스택 — P14 전체 재실행 결과와 남은 일", "🏁")
b8 = [
    callout("🏁", rt("P14 모델+a_hat으로 폐루프 실험 전체(24 trial)를 재실행 — 기존 최선(P13h+paper) 대비 "
                    "주요 3개 데이터셋의 사실상 전 채널이 개선됐다.")),
    h2("P13h+paper → P14 (폐루프 label 재현, 데이터셋 평균)"),
    table([
        ["", "q2 [rad]", "dq1 [rad/s]", "dq2 [rad/s]", "τ_hip", "τ_knee", "h_sim (h_real)"],
        ["0421", "0.039→0.041", "0.77→0.70", "1.02→0.92", "3.77→3.56", "1.59→1.46", "0.902→0.881 (0.850)"],
        ["0424", "0.032→0.030", "0.76→0.69", "2.68→2.32", "2.49→2.27", "4.36→4.03", "0.886→0.875 (0.829)"],
        ["0602", "0.057→0.052", "0.74→0.67", "3.04→2.67", "2.70→2.48", "5.49→4.91", "0.991→0.966 (0.920)"],
        ["0324*", "0.215→0.218", "1.81→1.83", "3.45→3.58", "1.25→1.37", "2.72→2.93", "0.678→0.669 (held-out 비용)"],
    ]),
]
b8 += safe_img(D / "g22_cl_p14_results/png/jump_0602__120_2_120_2__p14.png",
               "P14 폐루프 재현 예시 (0602/120_2)")
b8 += safe_img(D / "g22_cl_p14_results/gif/jump_0602__120_2_120_2__p14.gif",
               "P14 재현 애니메이션 (canonical 4-bar 규격)")
b8 += [
    h2("P14 + fit3 (q1·dq2 우선 게인 관점)"),
    table([
        ["push 중앙값", "q1", "dq2", "τ_knee"],
        ["0324", "0.104→0.043", "3.25→2.05", "2.44→2.34"],
        ["0421", "0.060→0.073", "0.99→0.51", "1.45→1.30"],
        ["0424", "0.018→0.009", "1.90→0.99", "3.98→3.23"],
        ["0602", "0.011→0.010", "2.23→1.75", "4.60→3.79"],
    ]),
    para(rt("모델 개선(P13h→P14)과 게인 관점(fit3)의 이득이 겹쳐 쌓입니다. 고게인 무릎의 실효 강성(~0.4-0.5×라벨)은 "
            "모델을 바꿔도 같은 값으로 수렴 — 실물 펌웨어/전류천장의 속성이라는 방증.")),
]
b8 += safe_img(D / "g22_cl_p14_results/png_fit3/jump_0424__120_2.2_150_2.5__p14fit3.png",
               "P14+fit3 예시 (0424/120_2.2_150_2.5)")
b8 += [
    h2("현재 모델 서열"),
    table([
        ["모델", "위치", "용도"],
        ["P14", "code/goal22/p14_ahat/fourbar_p14_candidate.json", "폐루프/배포 기준 추천 (이중 게이트 통과, 전 채널 우위)"],
        ["P13h", "code/goal22/fourbar_p13h_candidate.json", "보수 기준 (paper a_hat 유지 시)"],
        ["P13e", "code/goal21/fourbar_honest_canonical.json", "공식 canonical (벤치 확인 전까지 유지)"],
    ]),
    h2("남은 일 (실기·실험실)"),
    bullet(rt("① 모터 벤치: ", bold=True), rt("a_hat 곡선 직접 측정 — P14 예측표와 대조 (저·중부하 4~6점이면 판정). 오늘 모든 논의가 여기로 수렴")),
    bullet(rt("② R-Link 설정 확인: ", bold=True), rt("전류 한계 값 — raw 천장 ~35의 정체 확정")),
    bullet(rt("③ t_ff 송신 배포: ", bold=True), rt("s0.85 CSV + a_hat⁻¹ 변환 — τ_meas−τ_ff 로깅이 트윈 품질의 직접 측정이 됨")),
    bullet(rt("④ 수평 GRF (여유 시): 널 방향 직접 관측 수단")),
    bullet(rt("⑤ 0421 세션의 hip 실효 게인 0.6× 원인 — 당시 설정 기억 확인")),
]
append(p8, b8)

json.dump(dict(root=root, p4=p4, p5=p5, p6=p6, p7=p7, p8=p8),
          open(Path(__file__).parent / "handoff2.json", "w"))
print("PART2 DONE")
