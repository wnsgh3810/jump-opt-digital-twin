# -*- coding: utf-8 -*-
"""G20 final report — self-contained, detailed, Korean narrative."""
# --- 저장소 위치: 단일 출처 (code/bench/datapaths.py) ---
import os as _o2, sys as _s2
_d2 = _o2.path.dirname(_o2.path.abspath(__file__))
while _d2 != _o2.path.dirname(_d2) and not _o2.path.isdir(_o2.path.join(_d2, 'code', 'bench')):
    _d2 = _o2.path.dirname(_d2)
if _o2.path.join(_d2, 'code', 'bench') not in _s2.path:
    _s2.path.append(_o2.path.join(_d2, 'code', 'bench'))
from datapaths import REPO_ROOT  # noqa: E402
# ---------------------------------------------------------------
import json, base64, re
from pathlib import Path

SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
VIZ = SCR / "viz_final"; JPG = VIZ / "jpg"
REPO = Path(REPO_ROOT)
OUT = SCR / "twin_dashboard.html"   # same path => same artifact URL

res = json.load(open(VIZ / "viz_index.json"))
FM = json.load(open(REPO / "code/goal19/goal20_final_model.json", encoding="utf-8"))
P = FM["params"]; OFF = FM["offsets_deg"]

# LODO results (parse log if present)
lodo_rows = ""
lodo_log = SCR / "fourbar_lodo.log"
if lodo_log.exists():
    for m in re.finditer(r"fold\s+(\S+): held-out (\d+)\(full-fit\) vs (\d+)\(LODO-fit\)\s+ratio=([\d.]+)", lodo_log.read_text(errors="replace")):
        lodo_rows += f'<tr><td class="m">{m.group(1)}</td><td class="m num">{m.group(2)}</td><td class="m num">{m.group(3)}</td><td class="m num">{m.group(4)}</td></tr>'

def b64(p):
    return "data:image/jpeg;base64," + base64.b64encode(Path(p).read_bytes()).decode()

n = len(res)
mean_ratio = sum(r["h_sim"]/r["h_real"] for r in res)/n
hsum = b64(VIZ / "height_summary.png")
env_png = b64(VIZ / "nlp_envelope_check.png") if (VIZ / "nlp_envelope_check.png").exists() else ""

GROUPS = [
    ("jump_0324", "3월 점프 (26.03.24)", "AK 내부 MIT PD, dq_des=0 · 3 trials"),
    ("jump_position_0421", "위치제어 점프 (26.04.21)", "AK 내부 MIT PD, dq_des=0 · 6 trials"),
    ("jump_0424", "26.04.24 세트", "MIT PD (q+dq 동시) · 9 trials"),
    ("jump_0602", "26.06.02 세트", "MIT PD (q+dq 동시), 최상 캘리브레이션 · 6 trials"),
]

rows = "".join(
    f'<tr><td class="m">{r["ds"].replace("jump_","")}/{r["sub"]}</td>'
    f'<td class="m num">{r["h_sim"]:.2f}</td><td class="m num">{r["h_real"]:.2f}</td>'
    f'<td class="m num">{r["h_sim"]/r["h_real"]*100:.0f}%</td>'
    f'<td class="m num">{r["vsim"]:.2f}</td><td class="m num">{r["vfk"]:.2f}</td></tr>' for r in res)

def gallery(prefix):
    cards = []
    for r in res:
        if r["ds"] != prefix: continue
        img = b64(JPG / (Path(r["png"]).stem + ".jpg"))
        cards.append(f'''<figure class="card"><img loading="lazy" src="{img}" alt="{r['sub']}" class="zoom">
<figcaption><span class="sub">{r['sub']}</span><span class="chips">
<span class="chip">h_sim <b>{r['h_sim']:.2f}</b></span><span class="chip cam">h_cam <b>{r['h_real']:.2f}</b></span>
<span class="chip pct">{r['h_sim']/r['h_real']*100:.0f}%</span></span></figcaption></figure>''')
    return "\n".join(cards)

sections = ""
for pfx, name, desc in GROUPS:
    g = gallery(pfx)
    if not g: continue
    cnt = sum(1 for r in res if r["ds"] == pfx)
    sections += f'''<section class="ds" id="{pfx}"><div class="ds-head"><h2>{name}</h2>
<span class="ds-meta">{cnt} trials</span></div><p class="ds-desc">{desc}</p><div class="grid">{g}</div></section>'''

nav = "".join(f'<a href="#{p}">{nm}</a>' for p, nm, _ in GROUPS)
ptab = "".join(f'<tr><td class="m">{k}</td><td class="m num">{v}</td></tr>' for k, v in P.items() if not k.startswith("o"))
otab = "".join(f'<tr><td class="m">{k}</td><td class="m num">{v}°</td></tr>' for k, v in OFF.items())

html = f'''<title>2-DoF 점프 로봇 디지털 트윈 — G20 최종 보고서</title>
<style>
:root{{--paper:#f6f7f9;--surface:#fff;--ink:#17191e;--muted:#5c626d;--faint:#8b909b;--border:#e4e7ec;
--accent:#0f7d8c;--accent-deep:#0a5a66;--cam:#b5622a;--good:#2f8f5b;--warn:#9a6b1f;
--mono:ui-monospace,"Cascadia Code",Consolas,monospace;--sans:-apple-system,"Segoe UI","Malgun Gothic",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.65}}
.wrap{{max-width:1100px;margin:0 auto;padding:0 24px}}a{{color:var(--accent-deep)}}
header.top{{border-bottom:1px solid var(--border);background:linear-gradient(180deg,#fbfcfd,var(--paper))}}
.eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-deep);margin:0 0 10px}}
h1{{font-size:clamp(24px,4vw,38px);line-height:1.15;margin:0 0 12px;text-wrap:balance}}
.lede{{font-size:17px;color:var(--muted);max-width:66ch}}header.top .wrap{{padding:38px 24px 30px}}
.runmeta{{font-family:var(--mono);font-size:12px;color:var(--faint);margin-top:14px}}
.verdict{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:24px 0 6px}}
.vcard{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:15px 17px}}
.vcard .k{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin-bottom:7px;display:flex;align-items:center;gap:7px}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block}}.dot.good{{background:var(--good)}}.dot.warn{{background:var(--warn)}}.dot.off{{background:var(--faint)}}
.vcard .v{{font-size:19px;font-weight:650}}.vcard .n{{font-size:13px;color:var(--muted);margin-top:4px}}
section.block{{padding:32px 0;border-top:1px solid var(--border)}}
h2{{font-size:22px;margin:0 0 6px}}h3{{font-size:16px;margin:18px 0 6px}}
.kicker{{font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent-deep);margin:0 0 12px}}
p.body{{color:var(--muted);max-width:74ch}}p.body b{{color:var(--ink)}}
.finding{{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:15px 17px;margin:12px 0}}
.finding h3{{margin:0 0 6px;font-size:15px}}.finding p{{margin:0;color:var(--muted);font-size:14px}}
.finding.drop{{border-left-color:var(--warn)}}
figure.summary{{margin:16px 0 0;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px}}
figure.summary img{{width:100%;display:block}}
.tablewrap{{overflow-x:auto;margin-top:14px;border:1px solid var(--border);border-radius:10px;background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}
thead th{{background:#eef1f4;text-align:right;padding:8px 13px;font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border)}}
thead th:first-child{{text-align:left}}td{{padding:7px 13px;border-bottom:1px solid var(--border)}}
td.m{{font-family:var(--mono)}}td.num{{text-align:right;font-variant-numeric:tabular-nums}}
tbody tr:last-child td{{border-bottom:none}}
nav.ds-nav{{position:sticky;top:0;z-index:5;background:rgba(246,247,249,.93);backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}}
nav.ds-nav .wrap{{display:flex;gap:6px;flex-wrap:wrap;padding:10px 24px}}
nav.ds-nav a{{font-family:var(--mono);font-size:12px;text-decoration:none;color:var(--muted);padding:5px 11px;border:1px solid var(--border);border-radius:20px;background:var(--surface)}}
section.ds{{padding:30px 0;border-top:1px solid var(--border)}}
.ds-head{{display:flex;align-items:baseline;justify-content:space-between;gap:14px;flex-wrap:wrap}}
.ds-meta{{font-family:var(--mono);font-size:12px;color:var(--faint)}}.ds-desc{{color:var(--muted);margin:6px 0 16px;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:16px}}
figure.card{{margin:0;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}}
figure.card img{{width:100%;display:block;border-bottom:1px solid var(--border);cursor:zoom-in}}
figcaption{{padding:10px 13px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}}
figcaption .sub{{font-family:var(--mono);font-size:13px;font-weight:600}}
.chips{{display:flex;gap:6px}}.chip{{font-family:var(--mono);font-size:11px;color:var(--muted);background:#eef1f4;border-radius:5px;padding:3px 7px}}
.chip b{{color:var(--ink)}}.chip.cam b{{color:var(--cam)}}.chip.pct{{background:#e7f0f1;color:var(--accent-deep)}}
.timeline{{list-style:none;padding:0;margin:14px 0}}
.timeline li{{position:relative;padding:0 0 16px 26px;border-left:2px solid var(--border);margin-left:8px}}
.timeline li::before{{content:"";position:absolute;left:-6px;top:4px;width:10px;height:10px;border-radius:50%;background:var(--accent)}}
.timeline li.dropped::before{{background:var(--warn)}}
.timeline .t{{font-family:var(--mono);font-size:11px;color:var(--faint)}}
.timeline .h{{font-weight:650;margin:1px 0 3px}}.timeline p{{margin:0;color:var(--muted);font-size:14px;max-width:72ch}}
.linkgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin-top:12px}}
.link{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:11px 14px;font-size:13.5px}}
.link .t{{font-family:var(--mono);font-size:11px;color:var(--accent-deep);margin-bottom:3px}}
footer{{border-top:1px solid var(--border);padding:26px 0 46px;color:var(--faint);font-family:var(--mono);font-size:12px}}
.lb{{position:fixed;inset:0;background:rgba(15,17,20,.92);display:none;align-items:center;justify-content:center;z-index:50;padding:20px;cursor:zoom-out}}
.lb.on{{display:flex}}.lb img{{max-width:100%;max-height:100%;border-radius:6px}}
@media(max-width:520px){{.grid{{grid-template-columns:1fr}}}}
</style>

<header class="top"><div class="wrap">
<p class="eyebrow">G20 · 4절링크 명시 디지털 트윈 · 최종 보고서 (2026-07-05)</p>
<h1>측정 토크만 넣으면 실제 로봇처럼 움직이는 모델 — 그 여정의 전부</h1>
<p class="lede">2-DoF 단족 점프 로봇의 디지털 트윈을 <b>multiple shooting</b>으로 식별하고,
로봇의 실제 구조인 <b>4절링크 무릎 전달계를 명시적으로 모델링</b>해 완성한 최종 결과.
이 페이지 하나로 데이터, 방법론, 모든 가설의 채택/기각 근거, 최종 모델, 검증까지 전부 볼 수 있습니다.</p>
<p class="runmeta">단일 통합 물리 모델 · per-trial fudge 0 · 24 jumps (4개 날짜) + sit2stand · 검증: held-out 전체궤적 + 카메라 높이 + LODO</p>
<div class="verdict">
<div class="vcard"><div class="k"><span class="dot good"></span>창 예측 (fit metric)</div><div class="v">q2 1.2–1.5°</div><div class="n">0.1s open-loop 창, 4개 날짜 전부 균일. dq2 0.83–1.00 rad/s.</div></div>
<div class="vcard"><div class="k"><span class="dot good"></span>점프 높이 (held-out)</div><div class="v">88–94%</div><div class="n">0424 0.878 · 0602 0.941 · 0324 0.925. 목적함수에 h 없이 달성. 여정 시작점은 73–77%.</div></div>
<div class="vcard"><div class="k"><span class="dot good"></span>구조 발견</div><div class="v">4절링크 명시</div><div class="n">crank 0.656kg lumping 해소 — fitting 0회 pure CAD로 이전 최적 모델에 근접.</div></div>
<div class="vcard"><div class="k"><span class="dot good"></span>목적 폐루프 실증</div><div class="v">gap −14→−4.4%</div><div class="n">NLP에 식별 마찰 + k_eq 접촉 매칭 → gap 1/3로, 실현 점프 +6.5cm (§7).</div></div>
<div class="vcard"><div class="k"><span class="dot off"></span>GRF</div><div class="v">제외</div><div class="n">로드셀 비선형 + 3/4월 캘리브레이션 오류 — 표시만, fit 안 함.</div></div>
</div></div></header>

<section class="block"><div class="wrap">
<p class="kicker">1 · 문제와 목적</p>
<h2>왜 디지털 트윈인가</h2>
<p class="body">최종 목적은 트윈 자체가 아니라 <b>궤적 최적화 → sim-to-real 전이</b>입니다.
최적화가 뽑은 q*, dq*를 고게인 PD에 넣고 τ*를 피드포워드로 얹었을 때, 실제 인가 토크가
τ*와 최대한 같아야(τ_applied ≈ τ*) 합니다. 그 조건은 곧 <b>모델 정확도</b>이므로,
"측정 토크를 그대로 재생하면 실측 q/dq/h를 재현하는" Mode A 트윈을 만들어 왔습니다.
목표 매칭 변수는 사용자 확정으로 <b>q, dq, τ, h(카메라 측정 base 중심 apex)</b> — GRF는 로드셀 문제로 제외.</p>
<h3>로봇과 데이터</h3>
<p class="body">로봇: 2-DoF 단족 (hip + knee), 무릎은 <b>4절링크 CVT</b>(l_i 조절 변속, 본 데이터는 전부 l_i=30mm 평행사변형 = 1:1 고정)로 원격 구동.
모터 AK80-9 V2 ×2 (base 집중 배치). 측정 토크는 UMich 5-파라미터 a_hat(Paper) 변환 적용값.
제어 아키텍처: <b>03.19/03.24/04.21 = AK 내부 MIT PD(dq_des=0)</b>, <b>04.22만 외부 PD 루프</b>,
<b>04.24/06.02 = MIT PD(q_des+dq_des 동시)</b>.</p>
<div class="tablewrap"><table><thead><tr><th>데이터셋</th><th>trials</th><th>포함 여부</th><th>근거</th></tr></thead><tbody>
<tr><td class="m">sit2stand_gnd (03.19)</td><td class="m num">cycles</td><td>✅ fit</td><td>저속 regime 제공</td></tr>
<tr><td class="m">jump_0324 (Jump_No_Tr)</td><td class="m num">3</td><td>✅ fit</td><td>G20에서 신규 편입, 정상 품질</td></tr>
<tr><td class="m">jump_position_0421</td><td class="m num">6</td><td>✅ fit</td><td>창 단위에선 최상급 품질 (drift는 open-loop 누적일 뿐)</td></tr>
<tr><td class="m">jump_0424</td><td class="m num">9</td><td>✅ fit</td><td>MIT 모드, 다양한 gain</td></tr>
<tr><td class="m">jump_0602</td><td class="m num">6</td><td>✅ fit (기준 날짜)</td><td>최상 캘리브레이션 — offset 기준점</td></tr>
<tr><td class="m">jump_torque_0422</td><td class="m num">3</td><td>❌ 제외</td><td>유일한 외부 PD 루프 + 토크-운동 회귀 불일치 (R²=0.33)</td></tr>
<tr><td class="m">jump_0319 (NO_TR)</td><td class="m num">1</td><td>❌ 제외</td><td>fit이 점수 16%를 쏟아도 무개선(q2 0.33 고정) = 데이터 불량</td></tr>
</tbody></table></div>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">2 · 방법론 — 왜 multiple shooting인가</p>
<h2>metric을 고치니 모델이 스스로 물리로 갔다</h2>
<p class="body"><b>전체 궤적 open-loop replay(기존 Mode A 채점)는 발산 오염</b>이 있습니다:
작은 토크 잔차가 이중적분으로 지수적으로 커져 점수가 국소 모델 품질이 아닌 누적 drift를 재고,
fitter는 발산을 누르려 비물리 흡수재(flex railing, 가짜 발 질량, 과대 마찰)로 도망갑니다 —
역대 goal들의 fudge 패턴의 근원이었습니다. 반대로 <b>closed-loop(PD) 채점은 피드백이 모델 오차를 흡수</b>합니다:
kp·e = 90×0.038 ≈ 3.4 Nm = 역동역학 잔차와 동일 — q가 맞아 보여도 모델은 그대로인 착시.</p>
<p class="body">해법: <b>multiple shooting</b>. 궤적을 0.1s 창으로 잘라 각 창을 <b>측정 상태에서 시작</b>,
창 안에서는 <b>순수 τ_real replay</b>(PD 없음, gain 없음), 창의 q/dq 오차로 채점. 발산 오염 0,
피드백 흡수 0, 그리고 NLP의 dynamics 제약(단구간 예측)과 정확히 같은 물리량을 검증.
검증은 반대로 가장 엄격한 <b>전체 궤적 replay + 카메라 높이(held-out)</b>로. 이 분리 덕에
0421 위치제어 데이터가 부활했고(전체재생 24° → 창 2.7°), 창 크기 0.05/0.10/0.15 어디서도 결과가 매끄럽게 유지됩니다.</p>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">3 · 핵심 발견 — 4절링크 명시 모델</p>
<h2>0.656 kg의 유령 질량</h2>
<p class="body">역대 모든 모델은 4절링크를 serial 2-link로 뭉뚱그렸습니다: coupler(P링크, 0.137kg)는 thigh에,
<b>crank(C링크, 0.656kg — CVT l_i 조절기구 포함!)는 calf에</b> lumping. 그러나 실제 crank는 hip축에 붙어
회전만 할 뿐 무릎과 함께 날아다니지 않습니다. sim은 0.66kg의 유령 병진 질량을 무릎에 지고 뛰고 있었고,
fitter는 그걸 벗으려 "calf 질량 30% + 회전관성 180%"라는 불가능 조합으로 bound를 쫓았습니다(v4 railing의 정체).</p>
<p class="body">명시적 parallelogram 폐루프(crank→coupler→calf rocker, MuJoCo connect equality —
기본 solref는 물러서 crank가 1 rad 분리 헛돌았고 <b>solref="0.0008 1"로 조이면 해결</b>)를 구성하자:</p>
<div class="finding"><h3>fitting 0회 pure CAD로 이전 최적에 3.2% 근접</h3>
<p>4-bar 명시(pure CAD) 13666 vs CAD-serial 15024(−9.0%) vs 22-param 풀피팅 v3 13239. 구조가 옳다는 가장 강한 형태의 증거 —
파라미터가 아니라 구조가 문제였다.</p></div>
<div class="finding"><h3>joint refit 후 물리성 자발 회복</h3>
<p>M_calf 0.92 (railing 소멸), fc_knee 0.99→0.06 (마찰 흡수재 소멸), arm_knee 0.0035 + 명시 crank 관성 0.0009 ≈
0.0044 ≈ <b>AK80-9 데이터시트 반영관성 0.0049</b>. fit이 스스로 데이터시트 값을 찾아냄.</p></div>
<h3>per-date offset — 해석 정정 (07-06)</h3>
<p class="body">0602(6월) 기준 세션별 q1/q2 상수 offset은 창 점수 −16.3%의 유효한 축이지만, <b>fitted 값(3.6~8°)을
"엔코더 캘리브레이션 오차"로 읽는 것은 과잉 해석</b>입니다 — 사용자 확인: 실험 세팅상 영점 오차는 최대 1~2°.
검증: offset을 물리 한계 ±2°로 클램프하면 총 점수 +4.4%뿐이고 손상은 <b>0324에만 집중(+31.5%)</b>,
0424(+1.5%)/0421(+5.7%)은 사실상 무손상, s2s는 오히려 −2.3% 개선 — 즉 0424/0421의 큰 fitted 값은
flat direction의 허수였고(불확실성 분석의 음곡률과 일치), ±2° 물리 제약이 옳습니다.
<b>0324 무릎 방향만 진짜 일을 하는 축</b>이나, 추가 검증으로 그 정체가 좁혀짐:
① CVT l_i는 전 세션 30mm 동일(사용자 확인) — 기하 가설 기각. ② ±2° 제약 재적합(CMA 220 evals)
<b>개선 0.0%, 물리 파라미터 전부 불변</b> — 어떤 물리 축도 대체 불가. ③ 시작 crouch 판독값이
날짜간 1~3° 이내 일치(0324 무릎 −149.8° vs 0602 −147.8°) — <b>정적 각도 기준선 문제도 아님</b>.
결론: 0324의 "+8°"는 저토크(peak 11 vs 18–20 Nm)·완만한 3월 궤적 영역에서 커지는 미상의 모델/측정
잔차가 상수-무릎각 방향으로 대리 흡수된 것. 3월 측정체계의 알려진 품질 문제(자매 데이터 0319 제외 이력)와
일관. 핵심: <b>물리 트윈은 동일, held-out h·배포·NLP는 offset 미사용 = 전이 목적 무영향</b>.
offset은 ±2° 제약의 nuisance 파라미터로 확정, 0324 창 q2는 1.9°로 수용(물리 총량은 h 0.925±0.005로 건강).</p>
<div class="finding"><h3>날짜별 replay 정확도 차이 — 최종 진단 (07-06, 사용자와 공동 규명)</h3>
<p>갤러리에서 보이는 날짜별 품질 차이(0602 정확 > 0424 편차 > 0421·0324 부정확)의 인과 사슬:</p>
<p style="margin-top:6px">① <b>지령 궤적이 날짜마다 다름</b> (xlsx desiredAngle 확인): 날짜 내 전 trial은 동일 reference를
공유(폴더명=MIT 게인)하지만, 날짜 간에는 목표 신전이 −36°(0421/0424)~−49°(0324), stance가 0.25~0.32s로 상이.
② <b>dq_des 전송 버그</b> (사용자 확인): 03.24/04.21은 코드 오류로 계획 dq_des 대신 0이 전송됨 (04.24부터 정상 전송) —
kd항이 순수 제동으로 작동해 계획-실제 궤적 괴리 발생 (0324: 지령 −48°를 23° 지나쳐 −24° 거의 완전 신전까지
ballistic 관통 / 0602 soft: −45° 지령에 −57° 미달 = 중간 영역 체류).
③ <b>깊은 신전 = 오차 증폭기</b>: 신전 깊이 vs h_ratio 상관 −0.39 (0424 내부 −0.40) — straight-leg
특이점 근처에선 이륙 속도가 작은 오차에 극도로 민감. 단 0602는 같은 깊이(−31°)에서도 무상관(0.02) —
④ <b>증폭될 오차의 크기는 세션 측정 상태가 결정</b> (4월 세션 내 변화: 순서 상관 −0.63, 메커니즘 미확정).
⑤ <b>Mode A인데 왜 제어 아키텍처가 영향을 주나 — τ의 피드백 함량</b>: 측정 τ 중 상태-반응(피드백) 성분은
replay에서 시간표로 얼려져 sim 상태에 반응하지 못하므로, 피드백 함량이 클수록 open-loop replay가 취약.
무릎 속도-피드백 비율 |kd·e_dq|/|τ| 실측: <b>버그 날짜 0324 평균 93% / 0421 평균 134%</b>(214%짜리 trial은
τ가 상쇄하는 두 피드백 항의 작은 차이 = 최대 취약) <b>vs 정상 날짜 0424 39% / 0602 55%</b> — 버그 날짜가 2~3배.
"고게인 피드백 하 데이터는 open-loop 정보량이 낮다"는 시스템 식별의 고전 명제와 일치.
0421의 계통적 overshoot(1.155)도 이 프레임에서 설명됨.
<b>귀결: 그 날짜 데이터·모델이 나쁜 게 아니라 full-replay 잣대가 그 날짜들에 유난히 가혹한 것 —
창 점수가 4개 날짜 균일(1.2–1.5°)했던 이유이자, multiple shooting을 fit 잣대로 삼은 결정의 소급 정당화.
함의: 배포 전 dq_des 실전송 검증(README 반영), 새 세션+중간영역 궤적이면 0602 수준 정확도 기대.</b></p></div>
<div class="tablewrap"><table><thead><tr><th>세션 offset</th><th>값</th></tr></thead><tbody>{otab}</tbody></table></div>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">4 · 기각된 가설들 — 전부 증거와 함께</p>
<h2>시도하고, 공정하게 심판하고, 버렸다</h2>
<div class="finding drop"><h3>SEA (직렬 탄성) — 기각</h3>
<p>① in-chain rotor 토폴로지는 mass matrix ill-conditioning으로 모터 stall (RK4에서도 재현 = 적분기 무죄;
역대 SEA 실패 전부의 원인 규명). ② 표준 tendon 결합으로 재구현하니 수치는 건강하나 <b>전 강성에서 rigid보다 +43% 나쁨</b>.
③ 대조군(stiff 뺀 rigid +38.8%)보다도 나쁨 → 무릎 유연성 신호는 <b>parallel</b>(stiff_knee≈1)이며 series가 아님.</p></div>
<div class="finding drop"><h3>Stribeck 마찰 — 기각</h3>
<p>−1.7% &lt; 2% 게이트. hip은 Stribeck 효과 전무(fs≈fc). 마찰은 점성+쿨롱으로 충분.</p></div>
<div class="finding drop"><h3>잔차 액추에이터 모델 (τ-다항) — 기각</h3>
<p>LODO 3-fold 게이트에서 fold B held-out 악화(+0.8%), fold C는 계수 0이 최적 —
날짜 간 일반화 실패. <b>τ 잔차는 결국 날짜 암기(fudge)라는 실증</b> = 역대 tau_scale 금지 결정의 소급 검증.</p></div>
<div class="finding drop"><h3>bound 확장 round-2 — 기각</h3>
<p>창 점수 −0.7%에 파라미터가 비물리로 폭주(M_base 0.65). held-out에서 round-1에 패배 —
창 metric의 flat direction을 held-out+물리성으로 중재하는 원칙 확립.</p></div>
<div class="finding drop"><h3>MLP 액추에이터 잔차 (딥러닝) — 기각</h3>
<p>Hwangbo식 소형 MLP(관절당 3 hidden, 32 weights)로 δτ(τ,dq,q) 학습: train −3.1%인데
<b>held-out +0.1%</b> — 신경망도 날짜를 암기할 뿐 전이하지 않음. 상수(tau_scale)→다항(poly)→신경망(MLP)
세 단계 전부 같은 판정 = "τ 잔차 보정은 fudge"의 3중 실증.</p></div>
<div class="finding drop"><h3>질량 local polish — 기각</h3>
<p>민감도가 제안한 M_c/M_p 방향 local refit: 창 점수는 소폭 개선되나 <b>held-out 전 지표 악화</b>.
round-2·MLP와 합쳐 round-1이 fit-일반화 frontier의 최적점임을 3중 확인.</p></div>
<div class="finding drop"><h3>진짜 정지마찰(stiction) 확장 — 기각 + 유효범위 발견 ★</h3>
<p>fit에 안 쓴 <b>s2s_air</b>(공중, 15 cycles) held-out에서 새 물리 영역 노출: 실 다리는 τ≈0.04 Nm로
정지 유지(중력 요구 0.3–1.0 Nm)하는데 트윈은 낙하 — 기어박스 stiction + <b>CVT 리드스크류 비역구동성</b>.
G20-C Stribeck(tanh 주입)은 v=0 유지토크가 0이라 원리적으로 이걸 볼 수 없었음. 올바른 메커니즘
(frictionloss=fs 구속 + 이동 시 assist로 kinetic 복귀)으로 3중 프로브: air −10%까지 개선되나
<b>점프/gnd guard +36%</b> — smooth 마찰족으로는 두 영역이 화해 불가(이력성 비역구동 추정).
결론: <b>트윈 유효 범위 = 동적 영역(τ ≳ 수 Nm), 준정적 hold(τ&lt;2 Nm)는 범위 밖</b>.
점프 최적화 목적엔 영향 없음(점프는 10–50 Nm). 미래: 저속 램프 부하별 breakaway 실험으로 별도 식별.</p></div>
<p class="body">그 외 역대 기각 축: tau_scale(금지), motor_tm(Mode A에서 이중필터), backlash(발산), 관성텐서 단독 fit(rank-deficient),
per-trial fudge(교차검증 붕괴), 착지 창(데이터에 착지 없음 — 기록이 foot-off +0.02s에 종료).</p>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">5 · 최종 모델 카드</p>
<h2>G20 four-bar digital twin</h2>
<p class="body">구조: base(z) → thigh(hip) → [crank(knee_motor: 구동·armature·마찰) → coupler] + calf(knee: 수동),
coupler 끝 ↔ calf rocker point connect. 인코더 = crank. CAD 실측: L1=L2=0.25, l_i=0.03,
M1=0.913 / M2=0.237 / C=0.656 / P=0.137 kg. 파라미터는 CAD 대비 스케일:</p>
<div class="tablewrap"><table><thead><tr><th>파라미터</th><th>값</th></tr></thead><tbody>{ptab}</tbody></table></div>
<p class="body" style="margin-top:10px">파일: <code>code/goal19/goal20_final_model.json</code> ·
빌더 <code>mshoot_fourbar.py::build_xml_fourbar_jump</code> · 식별 <code>mshoot_fourbar_refit.py</code></p>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">6 · 검증</p>
<h2>세 겹의 검증: held-out 높이 · LODO · metric 견고성</h2>
<p class="body"><b>held-out 전체궤적</b>(fit에 안 쓴 잣대): 카메라 높이 대비 0424 <b>0.878</b> / 0602 <b>0.941</b> / 0324 <b>0.925</b>.
0421은 open-loop 재생이 ill-posed라 참고만(창 단위론 최상급). 0324는 이륙속도까지 일치(2.57 vs 2.51 m/s).
<b>LODO</b>(날짜 하나 빼고 fit → 그 날짜 평가):</p>
<div class="tablewrap"><table><thead><tr><th>fold</th><th>held-out (full-fit)</th><th>held-out (LODO-fit)</th><th>ratio</th></tr></thead>
<tbody>{lodo_rows if lodo_rows else '<tr><td colspan=4 class="m">LODO 진행 중 — 완료 시 갱신</td></tr>'}</tbody></table></div>
<p class="body" style="margin-top:8px"><b>창 크기 견고성</b>: W=0.05/0.10/0.15에서 창당 점수 78.9/84.1/109.5 —
지평선에 따라 매끄럽게 스케일, cliff 없음 = metric 선택에 강건.
<b>multi-seed 안정성</b>: CMA-ES seed 3종이 동일 지점 수렴 — 우연한 국소해가 아님.</p>
<h3>파라미터 불확실성 — 1% iso-score 구간</h3>
<p class="body">점수가 보정된 likelihood가 아니므로 가짜 σ 대신 정직한 양을 보고합니다:
<b>각 파라미터가 최적점에서 얼마나 움직여야 총 창 점수가 1% 나빠지는가</b>(±δ 프로브 2차 근사).
좁을수록 강하게 식별된 것.</p>
<div class="tablewrap"><table><thead><tr><th>파라미터</th><th>값</th><th>±(iso-1%)</th><th>상대</th><th>판정</th></tr></thead><tbody>
<tr><td class="m">stiff_knee</td><td class="m num">1.135</td><td class="m num">0.052</td><td class="m num">±4.6%</td><td>최강 식별</td></tr>
<tr><td class="m">M_thigh</td><td class="m num">1.101</td><td class="m num">0.061</td><td class="m num">±5.5%</td><td>강</td></tr>
<tr><td class="m">M_c (crank)</td><td class="m num">0.824</td><td class="m num">0.069</td><td class="m num">±8.4%</td><td>강</td></tr>
<tr><td class="m">imp0</td><td class="m num">0.371</td><td class="m num">0.046</td><td class="m num">±12.3%</td><td>중</td></tr>
<tr><td class="m">solref_tc</td><td class="m num">0.0060</td><td class="m num">0.0013</td><td class="m num">±21.6%</td><td>중</td></tr>
<tr><td class="m">arm_knee</td><td class="m num">0.0035</td><td class="m num">0.0013</td><td class="m num">±37.4%</td><td>중약</td></tr>
<tr><td class="m">fv_hip</td><td class="m num">0.488</td><td class="m num">0.157</td><td class="m num">±32.1%</td><td>약</td></tr>
<tr><td class="m">fv_knee</td><td class="m num">0.0141</td><td class="m num">0.0173</td><td class="m num">±122.9%</td><td>약 (0 포함)</td></tr>
<tr><td class="m">M_calf · fc_knee · o1/o2_0324</td><td class="m num">—</td><td class="m num">flat</td><td class="m num">—</td><td>음곡률 = ridge/노이즈 바닥 (round-2 기각과 일관)</td></tr>
</tbody></table></div>
<figure class="summary"><img src="{hsum}" alt="height summary"></figure>
<div class="tablewrap"><table><thead><tr><th>trial</th><th>h_sim</th><th>h_cam</th><th>ratio</th><th>v_sim</th><th>v_meas</th></tr></thead><tbody>{rows}</tbody></table></div>
</div></section>

<nav class="ds-nav"><div class="wrap">{nav}</div></nav>
{sections}

<section class="block"><div class="wrap">
<p class="kicker">7 · 목적 폐루프 실증 — 트윈 → NLP → 트윈</p>
<h2>모델이 좋아지면 점프가 실제로 높아진다</h2>
<p class="body">최종 목적(트윈으로 궤적 최적화 → 전이)을 미리 끝까지 돌려봤습니다:
CasADi NLP(해석적 4-bar EoM + G20 파라미터 + AK80-9 τ≤18 Nm)로 최대높이 점프 궤적을 뽑고,
그 <b>τ*를 4-bar 트윈에 open-loop replay</b>(실전에서 τ_applied≈τ*가 되는 상황의 프록시).
NLP 예측 h와 트윈 실현 h의 gap이 곧 전이 오차의 하한 추정치입니다.</p>
<div class="finding"><h3>식별된 마찰을 NLP에 넣자: gap 절반 + 점프 5.3cm 상승</h3>
<p>무마찰 NLP: h_pred 1.160 → 트윈 0.998 (<b>gap −14.0%</b>). G20 식별 마찰(fv_hip 0.488, fv_knee 0.0141)을
NLP dynamics에 추가: h_pred 1.122 → 트윈 <b>1.051</b> (<b>gap −6.4%</b>). 예측 일관성이 2배 좋아지고
<b>실현 높이 자체가 5.3cm 올랐습니다</b> — optimizer가 마찰을 알면 마찰을 이기는 궤적을 설계하기 때문.
"모델 정확도 ↑ → 실물 성과 ↑"라는 프로젝트 명제의 정량 증명.</p></div>
<h3>접촉 모델이 gap의 부호와 크기를 결정한다</h3>
<p class="body">NLP의 접촉 강성 k_c를 스윕(전부 마찰 포함, 트윈에 replay):</p>
<div class="tablewrap"><table><thead><tr><th>NLP 접촉 모델</th><th>h_pred</th><th>트윈 실현</th><th>gap</th></tr></thead><tbody>
<tr><td class="m">soft k=5000, α=0.85 (구모델 유산)</td><td class="m num">1.122</td><td class="m num">1.051</td><td class="m num">−6.4%</td></tr>
<tr><td class="m">soft k=5000, α=1</td><td class="m num">1.138</td><td class="m num">1.055</td><td class="m num">−7.3%</td></tr>
<tr><td class="m">soft k=15000</td><td class="m num">1.174</td><td class="m num">1.061</td><td class="m num">−9.6%</td></tr>
<tr><td class="m">soft k=40000</td><td class="m num">1.149</td><td class="m num">1.007</td><td class="m num">−12.4%</td></tr>
<tr><td class="m">soft k=100000</td><td class="m num">1.127</td><td class="m num">1.065</td><td class="m num">−5.5%</td></tr>
<tr><td class="m"><b>soft k=130000 = k_eq 실측 ★권장</b></td><td class="m num">1.112</td><td class="m num"><b>1.063</b></td><td class="m num"><b>−4.4%</b></td></tr>
<tr><td class="m">soft k=200000</td><td class="m num">1.064</td><td class="m num">1.035</td><td class="m num"><b>−2.8% (최소)</b></td></tr>
<tr><td class="m">hard (상보성)</td><td class="m num">0.940</td><td class="m num">0.971</td><td class="m num"><b>+3.3%</b> (트윈이 초과 달성)</td></tr>
<tr><td class="m">— 무마찰 기준 (soft k=5000)</td><td class="m num">1.160</td><td class="m num">0.998</td><td class="m num">−14.0%</td></tr>
</tbody></table></div>
<p class="body" style="margin-top:8px">해석: 접촉이 무르면 optimizer가 <b>접촉 스프링의 에너지를 착취</b>하는 궤적을 설계해
과대예측(−6~−12%); hard면 보수적(+3.3%, 실현 높이는 최저 0.971). <b>트윈 강성대(k≈1e5–2e5)로 맞추면</b>
실현 높이 최고(1.065m, k=1e5) 또는 gap 최소(−2.8%, k=2e5). 임피던스 매칭이 전이의 열쇠라는
MIT의 결론(arXiv 2404.15096)과 일치. ※주의: 단일 seed IPOPT라 k=40000 행처럼 국소해 비단조 존재.</p>
<div class="finding"><h3>자기일관성 확인: 트윈 접촉 강성 실측 = 스윕 최적대</h3>
<p>트윈(solref 0.006 / imp0 0.371)에 하중 스윕(0.5–8 g)을 가해 힘–침투 기울기를 직접 측정:
<b>k_eq ≈ 1.3×10⁵ N/m</b> (65.6N→0.49mm · 131N→1.15mm · 262N→2.02mm 선형 fit).
NLP 스윕이 경험적으로 찾은 최적 강성대(k=1e5–2e5)와 정확히 일치 — 두 실험이 서로를 검증.
정확히 k_c=k_eq에서 재실행한 완결판: <b>h_pred 1.112 → 트윈 1.063, gap −4.4%</b> —
실현 높이 최고 수준과 gap 개선을 동시 달성. <b>최종 체인: 무마찰 −14.0%/0.998m →
+식별 마찰 −6.4%/1.051m → +접촉 k_eq 매칭 −4.4%/1.063m (실현 높이 총 +6.5cm)</b>.
물리 충실도를 한 단계 올릴 때마다 예측 일관성과 실물 성과가 함께 올라감 = 프로젝트 명제의 3단 실증.
실무 지침: <b>NLP 접촉 k_c ≈ 1.3×10⁵ N/m + 식별 마찰 포함</b>.</p></div>
<div class="finding"><h3>실전 헤드룸: 다음 실험에서 약 +14 cm 기대</h3>
<p>같은 트윈, 같은 τ≤18 Nm에서 사과-사과 비교: 실측 최고 트라이얼(0602 90_0.75_90_2, 카메라 0.980m)의
τ replay → 트윈 0.929m vs <b>NLP 최적 τ* → 트윈 1.063m = +13.4 cm (+14.4%)</b>.
카메라 스케일 환산 시 0.98 → <b>약 1.12 m</b>. 실행 가능성(T-N) 검증: knee는 NLP가 18 Nm 한계를
전 속도대에서 타는 bang-bang 형태인데 <b>실 로봇이 이미 21.1 Nm·29.6 rad/s까지 실증</b>한 범위 내
(60점 중 2점만 +0.2 Nm 초과 = 무시 가능). hip은 13.5 Nm ≤ 18 스펙 내지만 8–14 rad/s 고속대에서
역대 trial이 안 써본 영역을 적극 사용 — <b>optimizer의 추가 높이는 주로 "미개척 hip 사용"에서 나옴</b>.
다음 실험 권장: 최적 궤적을 점진 스케일(70%→100%)로 재생하며 hip 추종을 확인.</p></div>
<div class="finding"><h3>배포 패키지 완성 — 로봇에 바로 넣을 수 있는 CSV 3종</h3>
<p>τ 예산 70/85/100%로 <b>각각 재최적화</b>(단순 스케일링은 궤적-토크 일관성 파괴)한 사다리.
<b>준최대 궤적은 거의 완벽 전이</b> — gap은 100% 한계에서만 열림:</p>
<div class="tablewrap"><table><thead><tr><th>예산</th><th>NLP 예측</th><th>트윈 실현</th><th>gap</th><th>peak τ (hip/knee)</th><th>stance</th></tr></thead><tbody>
<tr><td class="m">70% (12.6 Nm)</td><td class="m num">0.824</td><td class="m num">0.836</td><td class="m num">+1.5%</td><td class="m num">9.2 / 12.6</td><td class="m num">248 ms</td></tr>
<tr><td class="m">85% (15.3 Nm)</td><td class="m num">0.966</td><td class="m num">0.957</td><td class="m num">−0.9%</td><td class="m num">11.3 / 15.3</td><td class="m num">209 ms</td></tr>
<tr><td class="m">100% (18.0 Nm)</td><td class="m num">1.112</td><td class="m num">1.063</td><td class="m num">−4.4%</td><td class="m num">13.5 / 18.0</td><td class="m num">184 ms</td></tr>
</tbody></table></div>
<p style="margin-top:8px;color:var(--muted);font-size:14px">85% 예산만으로 이미 현 실측 최고 수준(트윈 0.957 vs 실측최고 replay 0.929).
파일: <code>nlp_demo/deploy/</code> — t·q_des·dq_des·τ_ff CSV (로봇 canonical 규약) + README(게인 kp=90/kd=0.75·2.0, 프로토콜, 안전수칙).
최적 궤적 canonical 애니메이션: <code>anim_final/nlp_optimal_jump.gif</code>.</p></div>
<div class="finding drop"><h3>배포 사전 검증 (closed-loop MIT PD+ff) — 정직한 기대치 보정</h3>
<p>실 배포와 동일 조건(kp90/kd0.75·2.0 + τ_ff, ±18Nm 클립)으로 트윈에서 closed-loop 재생:
100% 예산에서 <b>0.954m</b> (open-loop 1.063 대비 −10.9cm), 추종은 1.0–1.4°로 양호.
원인은 구조적 — PD가 트윈을 NLP 참조 운동학에 고정해 트윈 동역학의 유리한 편차를 제동하고,
knee가 18Nm 포화라 PD의 +방향 보정 여력이 0 (참조 연장 hold 무효과, kp150도 +1.4cm뿐).
α_kp=0.19(펌웨어 불확실성) 시 0.936m. <b>1차 시도 정직한 기대: 0.95–0.97m ≈ 현 실측 최고 동급 이상</b>;
상한 1.06m은 저게인 ff-위주 재생, 반복 보정(ILC), 또는 MuJoCo 트윈 위 직접 TO(contact-implicit)로 접근.
<code>deploy_cl_check.json</code>.</p></div>
{f'<figure class="summary"><img src="{env_png}" alt="envelope check"></figure>' if env_png else ''}
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">8 · 여정 타임라인</p>
<h2>under-jump 미스터리에서 4절링크까지</h2>
<ul class="timeline">
<li><span class="t">GOAL19</span><div class="h">통합 Mode A 트윈 (31 exp, 21 params)</div><p>fudge 0의 통합 모델. 그러나 점프 높이 ~77%에서 plateau.</p></li>
<li class="dropped"><span class="t">진단 1–2 (정정됨)</span><div class="h">"측정 한계" → "firmware artifact" 오판</div><p>GRF 기준 takeoff의 착시. 사용자 정정: 높이는 카메라로 잰 base 중심 apex = 진짜.</p></li>
<li><span class="t">진단 3</span><div class="h">종단 무릎속도 spike가 높이의 열쇠</div><p>측정 관절 데이터엔 0.9–1.0m 에너지가 있고(peak base 3.0–3.3 m/s), sim이 spike를 못 냈다.</p></li>
<li class="dropped"><span class="t">SEA 4회</span><div class="h">직렬탄성 시도 — 전부 실패</div><p>후에 원인 규명(ill-conditioning) + tendon 재심판으로 공식 기각. 유연성은 parallel.</p></li>
<li><span class="t">방법론 전환</span><div class="h">closed-loop 유혹을 기각하고 multiple shooting</div><p>PD는 오차를 흡수(kp·e=잔차)한다는 사용자 반론이 옳았다. 창 분할이 정답.</p></li>
<li><span class="t">G20-A</span><div class="h">4절링크 명시 모델 — 구조적 돌파</div><p>crank 0.656kg lumping 해소. pure CAD가 풀피팅 모델에 3.2% 근접.</p></li>
<li><span class="t">G20-B</span><div class="h">per-date 캘리브레이션 offset</div><p>0602 기준 세션별 3–8°. "3,4월 캘리브레이션 오류" 증언과 일치.</p></li>
<li><span class="t">G20 최종</span><div class="h">joint refit → 창 q2 1.2–1.5° · h 88–94% · 물리 파라미터</div><p>Stribeck/잔차모델은 게이트 기각. 단일 통합 물리 모델로 종결.</p></li>
<li><span class="t">07-05 새벽</span><div class="h">목적 폐루프: NLP 마찰 분해 + 접촉 스윕</div><p>마찰 추가로 gap −14→−6.4% + 트윈 점프 +5.3cm. 접촉 강성이 gap 부호 결정 (hard=+3.3% 보수).</p></li>
<li class="dropped"><span class="t">07-05 아침</span><div class="h">s2s_air held-out → stiction 영역 발견</div><p>준정적 hold는 리드스크류 비역구동성 — smooth 마찰족으로 화해 불가, 유효범위 경계로 문서화.</p></li>
</ul>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">9 · 최적화 단계를 위한 함의</p>
<h2>이 트윈으로 무엇을 해야 하나</h2>
<p class="body">① NLP dynamics는 <b>4-bar 명시 모델</b>을 사용 (CasADi 이식 시 parallelogram은 1:1이므로
serial+등가관성으로 축약 가능: knee 등가 armature ≈ arm_knee + IC + M_C·R_C², calf엔 M2+foot만).
② T-N 토크 한계(AK80-9 V2: peak 18 Nm) 제약 필수 — optimizer는 한계에서 놉니다.
③ <b>NLP에 식별 마찰 포함 + 접촉 k_c ≈ k_eq = 1.3×10⁵ N/m 매칭</b> (§7 실증: gap −14→−4.4%, 실현높이 +6.5cm).
④ 남은 높이 6–12% under-prediction은 안전측 — 필요시 readout 보정계수로만 처리(동역학 fudge 금지).
⑤ 새 실험 세션은 자체 q-offset 캘리브레이션 1회로 대응. ⑥ 준정적 동작(느린 hold)은 트윈 유효범위 밖 —
점프/s2s 같은 동적 task에만 사용. ⑦ 근본 개선의 다음 단계는 새 데이터:
공중 스윙/chirp(관성 완전 식별), 모터 벤치(자기 유닛의 a_hat), 저속 램프 breakaway(stiction), 착지까지 포함한 긴 기록.</p>
</div></section>

<section class="block"><div class="wrap">
<p class="kicker">10 · 링크 모음</p>
<h2>코드 · 자산 · 문헌</h2>
<div class="linkgrid">
<div class="link"><div class="t">REPO</div><code>Documents/jump-opt-digital-twin</code> — 모든 코드/모델/로그 (git 커밋 완비)</div>
<div class="link"><div class="t">FINAL MODEL</div><code>code/goal19/goal20_final_model.json</code></div>
<div class="link"><div class="t">FIGURES</div><code>scratchpad viz_final/</code> (원본 PNG) — 본 페이지에 전부 임베드</div>
<div class="link"><div class="t">ANIMATIONS ×24</div><code>code/goal19/phase11/anim_final/</code> — canonical 렌더러(goal18_v9 universal colored)</div>
<div class="link"><div class="t">식별 하네스</div><code>mshoot.py / mshoot_fourbar*.py / mshoot_dateoff.py</code></div>
<div class="link"><div class="t">기각 기록</div><code>mshoot_sea.py / mshoot_stribeck.py / mshoot_resid.py</code></div>
<div class="link"><div class="t">렌더링 표준</div>jump: <code>goal18_v9/_make_anim_universal_colored.py</code> · s2s: <code>goal18_CANONICAL/make_anim.py</code></div>
<div class="link"><div class="t">NLP 데모</div><code>code/goal19/nlp_demo/</code> — g20_vertjump_fric.py · contact_sweep_results.json</div>
<div class="link"><div class="t">검증 신규</div><code>mshoot_s2s_air_holdout.py / mshoot_stiction.py / mshoot_uncertainty.py / mshoot_mlp.py</code></div>
<div class="link"><div class="t">문헌 — 모델링</div><a href="https://arxiv.org/html/2507.00273v1">BRUCE 4-bar MuJoCo</a> · <a href="https://www.researchgate.net/publication/330442740">Hwangbo 2019</a> · <a href="https://arxiv.org/pdf/2303.09597">Residual physics</a> · <a href="https://arxiv.org/abs/2209.06261">Real2Sim2Real</a></div>
<div class="link"><div class="t">문헌 — 점프/전이</div><a href="https://arxiv.org/abs/2110.06764">3D 점프 TO</a> · <a href="https://arxiv.org/abs/2309.07038">단족 RL</a> · <a href="https://arxiv.org/abs/2309.01813">contact-implicit MPC</a> · <a href="https://arxiv.org/html/2509.06342v1">sim2real 체계화</a> · <a href="https://arxiv.org/abs/2504.12854">compliant 도약</a> · <a href="https://arxiv.org/html/2404.15096v1">임피던스 매칭 (§7과 동일 결론)</a></div>
<div class="link"><div class="t">문헌 — stiction</div><a href="https://www.researchgate.net/publication/260542123">Linderoth: 부하·온도 의존 정지마찰 식별</a> · <a href="https://www.sciencedirect.com/science/article/abs/pii/S0094114X10000947">리드스크류 비역구동 메커니즘</a></div>
</div>
</div></section>

<footer><div class="wrap">G20 marathon 2026-07-05 02:40–16:00 KST · 그림 클릭 = 확대 · sim 파랑 실선 / real 주황 점선 (calibrated)</div></footer>
<div class="lb" id="lb"><img id="lbimg" alt=""></div>
<script>(function(){{var lb=document.getElementById('lb'),im=document.getElementById('lbimg');
document.addEventListener('click',function(e){{if(e.target.classList&&e.target.classList.contains('zoom')){{im.src=e.target.src;lb.classList.add('on');}}
else if(e.target===lb||e.target===im){{lb.classList.remove('on');im.src='';}}}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape'){{lb.classList.remove('on');im.src='';}}}});}})();</script>
'''
OUT.write_text(html, encoding="utf-8")
print("WROTE", OUT, "%.1f MB" % (OUT.stat().st_size / 1e6))
