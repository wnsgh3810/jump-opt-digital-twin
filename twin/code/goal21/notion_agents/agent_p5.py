# -*- coding: utf-8 -*-
"""⑤ Gradient의 물리학 — 본문 증축(5~9절) + child ⑤-a 토이 실험 노트."""
import requests, time
from pathlib import Path

TOKEN = "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"
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"}
H2 = {**H, "Content-Type": "application/json"}

PARENT = "396ab81d2550814995dfc2e3a712ee01"
TARGET_PREFIX = "⑤ Gradient의 물리학"
CHILD_TITLE = "⑤-a 토이 실험 노트 — 세 추정기를 직접 비교하는 법"


# ───────── 블록 헬퍼 (notion_master_part2.py에서 복사) ─────────
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
def divider(): return {"object": "block", "type": "divider", "divider": {}}


def table(rows):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(rows[0]), "has_column_header": True,
                      "children": [{"type": "table_row",
                                    "table_row": {"cells": [rt(c) for c in r]}} for r in rows]}}


# ───────── 429 재시도 래퍼 ─────────
def _retry(fn):
    while True:
        r = fn()
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", 1))
            print(f"  429 rate limited, retry after {wait}s", flush=True)
            time.sleep(wait + 0.5)
            continue
        return r


def get_json(url):
    return _retry(lambda: requests.get(url, headers=H))


def post_json(url, body):
    return _retry(lambda: requests.post(url, headers=H2, json=body))


def patch_json(url, body):
    return _retry(lambda: requests.patch(url, headers=H2, json=body))


def new_page(parent, title):
    r = post_json("https://api.notion.com/v1/pages",
                  {"parent": {"page_id": parent}, "properties": {"title": {"title": rt(title)}}})
    if r.status_code != 200:
        raise RuntimeError(r.text[:800])
    time.sleep(0.6)
    return r.json()["id"]


def append(page, blocks):
    for i in range(0, len(blocks), 80):
        r = patch_json(f"https://api.notion.com/v1/blocks/{page}/children",
                        {"children": blocks[i:i + 80]})
        if r.status_code != 200:
            raise RuntimeError(r.text[:800])
        time.sleep(0.6)


def get_all_children(block_id):
    results, cursor = [], None
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = get_json(url)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if data.get("has_more"):
            cursor = data.get("next_cursor")
            time.sleep(0.3)
        else:
            break
    return results


# ───────── 1. 대상 페이지 특정 (parent의 children GET → 제목 접두어 매칭) ─────────
print("부모 children 조회 중...", flush=True)
children = get_all_children(PARENT)
p5 = None
for c in children:
    if c.get("type") == "child_page":
        title = c["child_page"].get("title", "")
        if title.startswith(TARGET_PREFIX):
            p5 = c["id"]
            print(f"대상 확정: {title!r} -> {p5}", flush=True)
            break
if p5 is None:
    raise RuntimeError(f"'{TARGET_PREFIX}'로 시작하는 child_page를 부모 {PARENT}에서 찾지 못함")


# ════════════════ 본문 증축 (5~9절) ════════════════
blocks5 = [
    divider(),
    callout("아래는 후속 증축입니다 — 위 ①~④(세 추정기 개괄·접촉 kink·카오스·방법 지도)에 이어, "
            "이번에는 용어를 완전히 정리하고 세 추정기를 수식으로 정식화하며, randomized smoothing과 "
            "카오스를 정량적으로 다룬 뒤 방법 선택 순서도로 마무리합니다.", "🧩"),

    # ── 5. 용어 완전 사전 ──
    h2("5. 용어 완전 사전 — 이번 절부터 새로 쓰는 말들"),
    para("①~④에서 이미 정의한 용어(pathwise/해석 gradient, FD, score function/0차, BPTT, Lyapunov 지수)에 "
         "이어, §6~9에서 등장하는 용어를 표로 정리합니다. 특히 pathwise와 score function은 이름만 다를 뿐 "
         "통계학의 표준 명칭(reparameterization trick, likelihood ratio trick)을 갖고 있습니다 — 다른 "
         "문헌에서 이 이름으로 마주치면 같은 개념임을 알아채시기 바랍니다."),
    table([
        ["용어", "정의"],
        ["pathwise 미분 (= reparameterization)", "연산 사슬(시뮬레이터 전체)을 직접 사슬법칙으로 미분. "
         "파라미터의 변화가 상태를 거쳐 비용까지 흐르는 경로를 그대로 따라감."],
        ["score function (= likelihood ratio)", "동역학 자체는 미분하지 않고, '이 궤적이 뽑힐 확률'의 "
         "로그만 미분. J(x)는 사슬 밖의 상수처럼 곱해짐."],
        ["REINFORCE (Williams 1992)", "score function 추정기를 정책 탐색에 적용한 원조 알고리즘 이름. "
         "∇θE[J]=E[J·∇θ log π]의 몬테카를로 구현."],
        ["편향 (bias)", "추정기의 기댓값이 참값과 어긋나는 정도. FD는 O(h²) 편향, 스무딩은 σ가 클수록 편향이 커짐."],
        ["분산 (variance)", "같은 참값 주변에서 추정치가 시행마다 흔들리는 정도. score function이 pathwise보다 근본적으로 큼."],
        ["BPTT (backpropagation through time)", "시간 축을 펼친 계산 그래프를 역방향으로 통과하며 미분을 전파. "
         "RNN 학습과 동일한 수학이 궤적최적화에도 적용됨."],
        ["야코비안 곱 (Jacobian product)", "∂x_T/∂x_0 = Π(∂x_{t+1}/∂x_t). 매 스텝 국소 야코비안을 시간 "
         "순으로 곱한 것 — 카오스의 성장률이 여기서 나옴."],
        ["Lyapunov 지수 λ", "인접 궤적이 벌어지는 지수적 속도. 야코비안 곱(의 최대 특이값)이 시간에 따라 "
         "e^{λt}로 성장할 때의 그 λ."],
        ["변분 방정식 (δẋ = A(t)δx)", "미소 교란 δx의 시간 전파를 지배하는 선형 시변 ODE. A(t)=∂f/∂x는 "
         "매 순간의 국소 야코비안 — 야코비안 곱은 이 방정식의 이산화."],
        ["절단 (truncation)", "긴 시퀀스의 미분 사슬을 일부러 짧게 끊는 것. truncated BPTT, multiple "
         "shooting이 모두 이 원리."],
        ["randomized smoothing", "비용을 가우시안 노이즈로 평균 내어(컨볼루션) 불연속·kink를 인위적으로 "
         "매끄럽게 만드는 기법."],
        ["bundled gradient (Suh et al. 2022)", "randomized smoothing으로 얻은 매끄러운 기울기 ∇J_σ에 "
         "저자들이 붙인 이름. 0차 방법이 암묵적으로 추정하는 대상이 바로 이것."],
        ["α-order estimator", "pathwise(1차)와 score function(0차)를 α:1−α 비율로 섞는 Suh et al.의 제안. "
         "α는 튜닝 가능한 하이퍼파라미터."],
    ]),
    para("이 중 세 용어는 이 프로젝트에 이미 살아 있습니다:"),
    bullet("**pathwise** → 우리 CasADi/IPOPT NLP 궤적최적화 (모델이 매끈해 안전한 조건)"),
    bullet("**score function(0차)의 실전 사촌** → GOAL21 CMA 파라미터 식별 (baseline 없이도 몬테카를로 "
           "샘플만으로 동작)"),
    bullet("**야코비안 곱의 폭발** → full-replay 발산 현상의 수학적 이름 그 자체"),
    bullet("**randomized smoothing의 σ** ↔ ⑧에서 언급한 접촉 강성 k_eq 매칭(G20, soft contact 폭)과 "
           "개념적으로 동일한 '경계를 얼마나 무디게 볼 것인가'의 다이얼"),

    # ── 6. 세 추정기의 수식 정식 ──
    h2("6. 세 추정기의 수식 정식 — 미분은 어디서 끊기는가"),
    para("①에서 표로 개괄한 세 추정기를 이번엔 수식으로 정확히 적습니다. 세 식 모두 '같은 것'(∇θE[J])을 "
         "추정하지만, 미분이 사슬의 어느 지점까지 파고드는지가 다릅니다 — 그 위치가 바로 편향·분산·kink "
         "반응성을 가릅니다."),
    h3("① pathwise (해석/AD) — 사슬 전체를 타고 내려간다"),
    code("∇θ E[J] = E[ (∂J/∂x_T) · (∂x_T/∂θ) ]\n\n"
         "∂x_T/∂θ 는 매 스텝 야코비안의 곱을 공유한다 (BPTT가 실제로 계산하는 항):\n"
         "  ∂x_T/∂x_0 = Π_{t=0}^{T-1} (∂x_{t+1}/∂x_t)"),
    para("비용의 상태 민감도(∂J/∂x_T)와 상태의 파라미터 민감도(∂x_T/∂θ)를 곱해서 얻습니다. 후자는 매 스텝 "
         "야코비안의 곱(=변분 방정식의 이산 적분)이라 §8의 카오스 성장과 완전히 같은 항을 공유합니다. "
         "함수가 매끄러우면 분산이 가장 낮은 추정기지만, kink(접촉 전환)에서는 ∂x_{t+1}/∂x_t 자체가 두 "
         "값 중 하나로 정의가 붕괴합니다 — '틀린 답'이 아니라 '정의되지 않은 질문에 대한 임의의 답'."),
    h3("② 유한차분(FD) — 미분을 수치로 흉내낸다"),
    code("(J(θ+h) − J(θ−h)) / (2h)\n\n"
         "편향  ~ O(h²)                 (테일러 3차 잔차)\n"
         "분산  ~ O(σ²/h²)              (평가 노이즈 σ가 있을 때)\n"
         "비용  : 파라미터 n개 → 중심차분 2n회의 풀 시뮬레이션 필요"),
    para("h를 줄이면 편향은 줄지만, 시뮬레이션 자체의 평가 노이즈(접촉 solver 반복오차, 부동소수점 등)가 "
         "분모 h로 나뉘어 증폭됩니다 — '더 정확하게 재려 할수록 더 흔들린다'는 근본 딜레마입니다. 게다가 "
         "파라미터가 n개면 중심차분만으로 2n번의 전체 시뮬레이션이 필요해, iLQG류가 매 반복마다 이 비용을 "
         "지불합니다(mjd_transitionFD)."),
    para("숫자로 감을 잡으면: 접촉 solver의 반복오차가 σ~1e-4 수준이라 할 때 h=1e-3이면 상대 잡음이 "
         "σ/h~0.1, 즉 10% 수준입니다. 편향을 더 줄이겠다고 h=1e-6까지 줄이면 잡음은 100배로 뛰어 신호보다 "
         "커집니다 — h를 '더 정밀하게' 잡을수록 답이 더 나빠지는 역설입니다."),
    h3("③ score function (REINFORCE) — 동역학은 손대지 않는다"),
    code("∇θ E[J] = E_{x~p(·;θ)}[ J(x) · ∇θ log p(x; θ) ]\n\n"
         "몬테카를로 추정 (N개 샘플):\n"
         "  (1/N) Σ_{k=1}^{N} J(x_k) · ∇θ log p(x_k; θ),   x_k ~ p(·; θ)\n\n"
         "★ 이 식 어디에도 ∂x_T/∂θ, 즉 동역학의 미분이 없다."),
    para("이 식에는 야코비안 곱이 등장하지 않습니다 — **동역학 미분이 항 어디에도 없습니다.** 대신 '얼마나 "
         "그럴듯한 샘플이었는지'의 로그미분만 곱합니다. 그래서 무편향이지만, 분산이 J(x)의 크기 자체에 "
         "비례합니다 — 비용이 크면 클수록 추정이 거칠어집니다. 표준 처방은 baseline b를 빼는 것: J(x)를 "
         "(J(x)−b)로 치환해도 기댓값은 그대로면서 분산은 줄어듭니다. RL의 **advantage** "
         "A(s,a)=Q(s,a)−V(s)가 바로 이 baseline(=상태가치 V)을 뺀 결과입니다."),
    callout("REINFORCE라는 이름 — Williams(1992) 원논문 제목의 약어로, 'REward Increment = Nonnegative "
            "factor × Offset reinforcement × Characteristic Eligibility'의 머리글자입니다. score "
            "function 추정기에 붙은 가장 오래된 고유명사입니다.", "🏷️"),
    h3("score function trick의 유도 스케치"),
    code("항등식:  ∇θ p(x;θ) = p(x;θ) · ∇θ log p(x;θ)   (log 미분의 정의에서 바로 나옴)\n\n"
         "E[J·∇θ log p] = ∫ J(x) ∇θ log p(x;θ) · p(x;θ) dx\n"
         "              = ∫ J(x) ∇θ p(x;θ) dx\n"
         "              = ∇θ ∫ J(x) p(x;θ) dx     (J는 θ와 무관, 적분과 미분 교환)\n"
         "              = ∇θ E[J]"),
    para("이 세 줄이 REINFORCE의 전부입니다 — 특별한 가정 없이 로그미분 항등식과 적분·미분의 교환만으로 "
         "성립하기 때문에, J(x)가 미분 불가능하거나 심지어 불연속이어도(예: 접촉이 있었는지 없었는지의 "
         "이진값) 무편향으로 성립합니다."),
    h3("미니 비교표"),
    table([
        ["추정기", "동역학 미분", "편향", "분산", "kink에서", "카오스에서"],
        ["pathwise", "예 (야코비안 곱)", "무편향(스무딩 없을 때)", "낮음(매끄러울 때)",
         "정의 붕괴 — 임의값 반환", "e^{λT}로 폭발"],
        ["FD", "수치로 근사", "O(h²)", "O(σ²/h²)", "h가 경계에 걸리면 잡음/편향", "동일 폭발(같은 사슬을 유한차로 관통)"],
        ["score function", "아니오", "무편향", "높음 (baseline로 완화)", "영향 없음 (기대값이 이미 매끈)",
         "영향 없음 (사슬을 타지 않음)"],
    ]),

    # ── 7. randomized smoothing ──
    h2("7. randomized smoothing — 0차 방법이 몰래 풀고 있는 진짜 문제"),
    para("0차 방법(MPPI, CMA, PPO)이 '왜 kink에서도 잘 도는가'의 답이 이 절입니다. 이들은 원함수 J를 직접 "
         "최적화하는 게 아니라, 노이즈로 흐린 버전 J_σ를 최적화하고 있습니다 — 대개는 그 사실을 의식하지 "
         "않은 채로요."),
    code("정의:  J_σ(θ) = E_ε[ J(θ + ε) ],   ε ~ N(0, σ²·I)\n\n"
         "⟺ J_σ = J * N(0, σ²·I)   (가우시안 커널과의 컨볼루션과 정확히 같은 연산)"),
    para("컨볼루션은 불연속을 지웁니다 — J가 계단이든 꺾인 선이든, 폭 σ의 가우시안으로 뭉개고 나면 J_σ는 "
         "어디서나 매끄럽고(C^∞) 미분 가능합니다. 접촉 kink가 있는 J라도 J_σ는 언제나 well-defined인 "
         "이유가 이것입니다."),
    code("∇θ J_σ(θ) = E_ε[ ε · J(θ+ε) ] / σ²    (Stein's lemma 계열)\n\n"
         "→ 우변에 J의 미분이 없다 — 함수값 J(θ+ε) 샘플만으로 기울기를 추정할 수 있다\n"
         "  (MPPI/CMA/PPO 같은 0차 방법이 암묵적으로 하고 있는 일이 바로 이것)"),
    para("이 형태가 중요한 이유: 우변에 J의 미분(∂J/∂θ)이 없습니다. 시뮬레이터를 미분 가능하게 만들 필요 "
         "없이, 그냥 여러 번 '돌려보기'만 하면 됩니다 — MPPI가 수백 개 rollout의 비용으로 가중평균을 내는 "
         "것, CMA가 공분산을 업데이트하는 것 모두 이 추정을 각자의 방식으로 근사한 것입니다."),
    h3("Stein's lemma의 유도 스케치"),
    code("φ_σ(ε) = 가우시안 밀도,   J_σ(θ) = ∫ J(θ+ε) φ_σ(ε) dε\n\n"
         "∇θ J_σ(θ) = ∫ J(θ+ε) ∇θ φ_σ(ε) dε             (미분을 커널 쪽으로 이동)\n"
         "           = ∫ J(θ+ε) · (ε/σ²) φ_σ(ε) dε        (가우시안 밀도의 성질을 이용)\n"
         "           = E_ε[ (ε/σ²) · J(θ+ε) ]"),
    para("σ는 스무딩의 폭입니다. σ가 크면 J_σ는 더 매끄러워지지만 원래 J와 점점 멀어집니다(편향 커짐) — "
         "벼랑 자체가 무뎌져 최적점이 이동할 수 있습니다. σ가 작으면 J_σ는 원함수에 가깝지만 kink 근방에서 "
         "다시 거칠어집니다 — σ→0 극한에서 J_σ→J이므로, 결국 pathwise의 문제로 되돌아갑니다. 실무에서 σ는 "
         "'경계를 얼마나 무디게 볼 것인가'를 조절하는 명시적 다이얼입니다."),
    callout("MPPI의 가중합 Σ w_k·u_k (w_k ∝ exp(−J_k/λ_temp))도 결국 J_σ의 기울기를 샘플 가중치로 근사한 "
            "것과 같은 계열입니다 — '온도' λ_temp가 사실상 스무딩 폭 σ의 역할을 합니다.", "🎲"),
    para("추정 분산은 표본 수 N에 대해 ~1/N로 줄어듭니다(표준 몬테카를로 스케일링) — 병렬 rollout(GPU 위의 "
         "Isaac/MJX/Brax)이 값싸질수록 이 절이 설명하는 0차 접근의 실용성이 올라가는 이유입니다."),
    para("Suh, Simchowitz, Zhang, Tedrake, \"Do Differentiable Simulators Give Better Policy Gradients?\" "
         "(ICML 2022, arXiv:2202.00817)의 핵심 결론을 여기서 다시 짚습니다 — 강성이 높고(stiff) 불연속이 "
         "많은 시스템에서는 1차(pathwise) 추정기가 오히려 0차보다 나쁜 policy gradient를 줍니다(분산이 "
         "카오스적으로 폭발하기 때문, §8과 동일 메커니즘). 저자들은 이를 정량적으로 보이고, bundled "
         "gradient(=randomized smoothing의 기울기)와 pathwise를 α:1−α로 섞는 α-order estimator를 "
         "제안해 두 극단의 장점만 취하도록 했습니다."),

    # ── 8. 카오스 정량 ──
    h2("8. 카오스 정량 — 민감도를 숫자로 잡는다"),
    para("'카오스라서 미분을 못 믿는다'는 지금까지 정성적 서술이었습니다. 이 절은 그 직관에 수식과 처방을 "
         "붙입니다."),
    code("민감도 전파 (변분 방정식의 이산 적분):\n\n"
         "δx_T = [ Π_{t=0}^{T-1} (∂x_{t+1}/∂x_t) ] · δx_0\n\n"
         "‖δx_T‖ / ‖δx_0‖  ~  e^{λT}     (λ = 최대 Lyapunov 지수)"),
    para("이것이 §6의 pathwise 야코비안 곱과 정확히 같은 식입니다 — gradient도 이 곱을 타고 흐르므로, T가 "
         "커질수록 gradient의 크기(와 방향)도 e^{λT}로 요동칩니다. Metz et al. 2021, \"Gradients Are Not "
         "All You Need\"의 실증이 바로 이것 — BPTT로 카오스 시스템(이중진자, 유체, RNN 학습 등)을 긴 "
         "horizon으로 미분하면, gradient 분산이 ~e^{2λT}로 폭발해 **'미분이 존재는 하지만 값이 사실상 "
         "난수'**가 되는 현상을 여러 도메인에서 보였습니다."),
    code("λ의 정의:\n"
         "  λ = lim_{T→∞} (1/T) · ln( ‖δx_T‖ / ‖δx_0‖ )\n\n"
         "변분 방정식  δẋ = A(t)·δx,  A(t) = ∂f/∂x|_{x(t)}  의 해를 시간 T까지 적분해 얻은 성장률의\n"
         "극한이 λ다 — 위 야코비안 곱은 정확히 이 방정식의 이산화다."),
    para("실측 연결: 우리 프로젝트의 실물 증거는 full-replay(전체 궤적을 한 사슬로 전개)에서 초기 상태의 "
         "아주 작은 오차가 0.3초 만에 완전히 다른 궤적으로 갈라진 현상입니다 — 이는 이 시스템의 λ가 대략 "
         "수십/s 오더라는 뜻입니다(0.3s 만에 궤적이 갈라지려면 e^{λ·0.3}이 이미 O(10~100) 수준이어야 "
         "함). 우리가 창(0.1s) 단위로 평가하는 것은, e^{λ·0.1}을 아직 O(1)~O(few) 수준으로 묶어두는 "
         "선택입니다 — 그 이상 늘리면 gradient(와 비용 자체)의 신뢰도가 지수적으로 무너집니다."),
    h3("처방 표 — 카오스를 다루는 네 가지 길"),
    table([
        ["처방", "원리", "대표 사례"],
        ["절단 / 짧은 horizon", "e^{λT} 자체를 줄임 — T를 작게 유지", "iLQG의 짧은 예측 구간, receding horizon MPC"],
        ["multiple shooting (사슬 절단)", "긴 사슬을 짧은 조각으로 끊고 조각마다 미분 — 조각 경계에서 "
         "재시작하므로 오차가 안 쌓임", "우리의 0.1s 창 평가, contact-implicit trajopt의 표준 관행"],
        ["0차 (score function / 샘플링)", "애초에 야코비안 곱을 타지 않음 — §6의 score function이 카오스에도 "
         "면역인 이유", "MPPI, CMA, PPO"],
        ["폐루프화 (피드백)", "제어기가 시스템 자체의 유효 λ를 바꿈 — 좋은 피드백은 λ_closed를 음수로 "
         "만들어 오차를 오히려 수렴시킴", "PD/LQR 안정화 후 궤적 추종, ⑥의 25~100Hz MPC 재계획"],
    ]),
    callout("제어가 카오스를 죽인다 — 같은 물리 시스템도 open-loop로 재생하면 λ>0이 그대로 살아 오차가 "
            "폭발하지만, PD를 감아 폐루프로 만들면 유효 민감도가 음수(λ_closed<0)로 뒤집혀 초기 오차가 "
            "시간이 지날수록 오히려 줄어듭니다. 우리가 실기 배포에서 폐루프(PD가 오차를 흡수하는) 지표에 "
            "관대해지는 이유가 바로 이것 — 카오스는 열린 사슬에서만 사납습니다.", "🌀"),

    # ── 9. 방법 선택 순서도 ──
    h2("9. 방법 선택 순서도 — 지금 문제엔 무엇을 써야 하는가"),
    para("①~⑧에서 흩어져 있던 판단 기준을 if-then 다섯 줄로 압축합니다. 위에서부터 순서대로 확인하고, "
         "먼저 해당하는 조건에서 멈추면 됩니다."),
    bullet("**모델이 매끄럽고(연속) horizon이 짧다** → 해석적 AD 기반 NLP를 쓰십시오(우리의 CasADi/"
           "IPOPT). pathwise가 가장 낮은 분산으로 가장 빠르게 수렴합니다 — kink도 카오스도 없는 최적의 조건."),
    bullet("**접촉은 있지만 적고(스케줄이 거의 고정), 그래도 미분이 필요하다** → 유한차분 기반(iLQG, "
           "MJPC의 mjd_transitionFD)을 쓰십시오. 접촉 수가 적으면 h 딜레마(§6-②)가 감당할 만합니다."),
    bullet("**접촉이 많고 스케줄이 매 스텝 바뀐다** → 0차(MPPI/CMA) 또는 soft contact화 + AD를 쓰십시오. "
           "kink 밀도가 높을수록 pathwise의 임의성이 누적되어 못 쓰게 됩니다 — randomized smoothing(§7)이 "
           "명시적 처방입니다."),
    bullet("**horizon이 길다(수 초 이상)** → multiple shooting으로 사슬을 끊거나, 아예 폐루프로 만드십시오. "
           "e^{λT}가 지배하는 순간 어떤 추정기를 쓰든 신뢰도가 무너집니다(§8) — 추정기 선택보다 horizon "
           "처리가 우선입니다."),
    bullet("**평가(시뮬레이션 1회)가 병렬로 값싸게 돌아간다** → 0차를 우선 고려하십시오. GPU 병렬 rollout"
           "(Isaac/MJX/Brax) 환경이면 0차의 '높은 분산'은 샘플 수로 손쉽게 눌러지고, 미분 가능 시뮬레이터를 "
           "만드는 공학 비용을 아예 안 낼 수 있습니다."),
    callout("이 순서도는 이미 이 문서 전체에 숨어 있었습니다 — ①의 표(대표 사용처), ⑥의 '식별=CMA, "
            "궤적=NLP' 배치, ⑦의 'RL=0차라 kink·카오스를 원천 회피'가 전부 이 다섯 줄의 개별 사례들입니다.",
            "🗺️"),
    quote("정리 | 다섯 줄의 순서도는 결국 하나의 질문으로 요약됩니다 — '이 문제에서 kink와 카오스 중 무엇이 "
          "더 사나운가, 그리고 그것을 피할 여유(horizon을 끊을 수 있는가, 병렬 평가를 살 수 있는가)가 "
          "있는가.' 우리 파이프라인이 식별=0차, 궤적=1차(NLP)를 쓰는 것도 정확히 이 순서도를 두 번 통과한 "
          "결과입니다."),

    divider(),
    para("다음 하위 페이지 \"⑤-a 토이 실험 노트\"에서는 위 세 추정기를 실제로 손으로 재현하는 두 실험 "
         "레시피를 제공합니다 — kink 근처 산점도 비교, 그리고 이중진자로 직접 λ를 재는 법."),
]

print(f"본문(⑤) 추가 블록 수: {len(blocks5)}", flush=True)
append(p5, blocks5)
print("본문 append 완료", flush=True)


# ════════════════ child: ⑤-a 토이 실험 노트 ════════════════
p5a = new_page(p5, CHILD_TITLE)
print(f"child 생성: {p5a}", flush=True)

blocks5a = [
    h2("무엇을, 왜 재현하는가"),
    quote("이 노트의 목적은 §5~9에서 수식으로만 본 세 추정기의 행동을 직접 손으로 만들어 보는 것입니다 — "
          "코드 없이도 의사코드만으로 결과를 예측할 수 있어야, 그 결과가 진짜로 '이해'된 것입니다."),
    para("두 실험 모두 실제 파이썬이 아니라 의사코드입니다 — 목적은 각자의 언어/도구로 직접 구현해 보는 "
         "것이며, 아래 '기대 결과'와 맞춰보는 것이 검증입니다."),
    bullet("실험 1 준비물: 1차원 함수 J(θ) (분기 있는 조각함수), 난수생성기, 플로팅 도구"),
    bullet("실험 2 준비물: RK4 적분기(4차 Runge-Kutta), 이중진자 운동방정식(교재 어디에나 있는 표준식), "
           "로그축 플로팅"),

    # ── 실험 1 ──
    h2("실험 1 — kink에서 세 추정기 비교"),
    para("질문: 같은 비용함수 J(θ)를 두고, pathwise·FD·randomized smoothing이 접촉 경계 θ*를 어떻게 "
         "다르게 '보는가'?"),
    h3("설정"),
    para("설정은 이 문서 본문의 그림(접촉 kink, m4)과 동일합니다 — 파라미터 θ 하나(예: 접근 속도, 혹은 "
         "목표 접촉 시점)에 대해 비용 J(θ)가 어느 임계 θ*에서 꺾이는(도함수가 불연속인) 1차원 문제입니다."),
    h3("의사코드 (8줄)"),
    code("1. J_true(θ) 정의:  θ<θ* 이면 f1(θ),  θ≥θ* 이면 f2(θ)   (f1,f2는 매끈, 접합점에서 기울기가 다름)\n"
         "2. θ_grid = linspace(θ*-Δ, θ*+Δ, N)                       # 임계점 근방을 촘촘히\n"
         "3. for h in [h_큰, h_작음]:                                # 두 스텝 크기\n"
         "4.     grad_FD[h] = (J_true(θ_grid+h) - J_true(θ_grid-h)) / (2h)\n"
         "5. J_true(θ_grid) 를 산점도로 그림                          # 참 비용의 kink를 눈으로 확인\n"
         "6. grad_FD[h_큰], grad_FD[h_작음] 을 θ_grid 위에 겹쳐 그림\n"
         "7. J_sigma(θ) = mean( J_true(θ + σ·randn(M)) )              # 가우시안 스무딩, M회 샘플\n"
         "8. grad_smooth(θ) = mean( σ·randn(M) · J_true(θ+σ·randn(M)) ) / σ**2   # §7 식 그대로 몬테카를로"),
    h3("무엇을 보고 있는가 — 줄별 해설"),
    bullet("1행: 접촉 전환 자체를 가장 단순한 조각함수로 축약 — 실제 4-bar 접촉 kink(m4 그림)의 1차원 축소판."),
    bullet("3~4행: pathwise는 θ*를 정확히 통과하는 순간 f1'/f2' 둘 중 하나를 '운 나쁘게' 반환합니다 — "
           "FD는 h로 그 순간을 흐리게 만드는 것."),
    bullet("7~8행: randomized smoothing은 θ 자체를 흔들어 J를 미리 뭉갠 뒤 그 뭉갠 함수의 기울기를 재는 "
           "것 — §7의 식을 그대로 몬테카를로로 구현."),
    h3("기대 결과"),
    bullet("θ* 근처에서 FD 산점(6번)은 h가 작을수록 튀는 값이 늘어납니다 — 그리드 포인트가 θ*를 넘나들 "
           "때마다 f1'과 f2' 사이를 오가며 값이 뚝뚝 끊깁니다(발산적 산점)."),
    bullet("h가 크면 산점은 잔잔해지지만 θ* 위치 자체가 무뎌져 진짜 꺾임 지점을 놓칩니다 — 편향과 잡음의 "
           "트레이드오프(§6-②)가 그림으로 확인됩니다."),
    bullet("grad_smooth(7~8번)는 θ*를 부드럽게 통과합니다 — 값이 급변 없이 완만한 S자 형태로 넘어가며, "
           "σ가 클수록 더 완만해집니다."),

    # ── 실험 2 ──
    h2("실험 2 — 카오스 민감도 재기"),
    para("질문: 우리가 'λ가 수십/s'라고 말할 때, 그 숫자는 어디서 나오는가? 이중진자로 직접 재봅니다."),
    h3("설정"),
    para("이중진자(double pendulum)는 저비용으로 카오스를 실감할 수 있는 표준 예제입니다. RK4로 적분하고, "
         "초기조건을 아주 살짝(±1e-8) 흔든 두 궤적을 나란히 돌립니다."),
    h3("의사코드"),
    code("1. state0_A = [θ1, θ2, ω1, ω2]                              # 이중진자 초기값\n"
         "2. state0_B = state0_A + [1e-8, 0, 0, 0]                    # 각도1에만 미소 교란\n"
         "3. traj_A = RK4_integrate(double_pendulum_eom, state0_A, dt=0.001, T=4.0)\n"
         "4. traj_B = RK4_integrate(double_pendulum_eom, state0_B, dt=0.001, T=4.0)\n"
         "5. diff[t]  = norm(traj_A[t] - traj_B[t])\n"
         "6. ratio[t] = diff[t] / 1e-8\n"
         "7. semilogy(t, ratio)                                        # y축 로그 스케일\n"
         "8. λ_est = polyfit(t, log(ratio), 1)[0]                      # 직선 구간의 기울기 = λ"),
    h3("무엇을 보고 있는가"),
    bullet("2행: 교란 크기 1e-8은 임의값이 아니라 '충분히 작아서 선형 근사(변분 방정식)가 성립하는' 스케일 "
           "입니다 — 너무 크면 §8 표의 '포화'가 일찍 옵니다."),
    bullet("6~7행: ratio를 로그축으로 보는 것 자체가 '지수 성장을 직선으로 바꿔 기울기(=λ)를 육안으로 "
           "읽는' 표준 트릭입니다."),
    bullet("8행: 1차 다항 피팅(polyfit)의 기울기가 바로 λ의 수치 추정값 — §8 '실측 연결' 문단에서 언급한 "
           "그 λ입니다."),
    h3("기대 결과"),
    bullet("semilogy(t, ratio)는 거의 직선으로 나타나며, 이 직선의 기울기가 λ입니다 — 지수적 성장의 시각적 "
           "증거."),
    bullet("4초 적분에서 ratio는 보통 1e4~1e6배까지 커집니다 — 즉 1e-8 크기의 초기 오차가 4초 뒤엔 훨씬 "
           "큰 차이로 자랍니다."),
    bullet("ratio가 궤적의 물리적 스케일(예: 진자 길이)에 근접하면 곡선이 꺾여 평평해집니다(포화) — 이 "
           "지점부터는 '더 이상 같은 궤적이 아님'을 뜻하며 λ 추정 구간에서 제외해야 합니다."),
    callout("응용 — 여러분의 시스템에서 같은 실험(미소 교란 두 번 적분 → semilogy)을 돌려 그 시스템의 λ를 "
            "직접 재보십시오. 경험칙: λ·T ≲ 3 정도까지가 '같은 사슬로 미분해도 신뢰할 수 있는' horizon의 "
            "대략적 한계입니다 — 그 이상에서는 §8의 처방(절단·multiple shooting·0차·폐루프)으로 넘어가야 "
            "합니다.", "🔬"),

    # ── 종합 ──
    h2("두 실험을 합치면 — 방법 선택 순서도의 두 축"),
    para("실험 1은 §9 순서도의 'kink 밀도' 축을, 실험 2는 'horizon(=λT)' 축을 직접 잽니다. 실전에서는 이 "
         "둘을 먼저 측정한 뒤 순서도를 적용하는 것이 올바른 순서입니다 — 감으로 추정기를 고르지 않기 "
         "위해서입니다."),

    quote("추정기의 선택은 취향이 아니라 λ와 kink 밀도의 함수다."),
]

print(f"child(⑤-a) 블록 수: {len(blocks5a)}", flush=True)
append(p5a, blocks5a)
print("child append 완료", flush=True)


# ───────── 검증 ─────────
for name, pid in [("p5 (⑤ Gradient의 물리학, 본문)", p5), ("p5a (⑤-a 토이 실험 노트)", p5a)]:
    kids = get_all_children(pid)
    n_img = sum(1 for b in kids if b.get("type") == "image")
    print(f"{name}: 총 {len(kids)} blocks (이미지 {n_img}개) — https://www.notion.so/{pid.replace('-', '')}",
          flush=True)

print("DONE", flush=True)
