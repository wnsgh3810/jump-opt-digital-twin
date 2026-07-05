# -*- coding: utf-8 -*-
"""G20 graphs-only gallery page (all 24 trial 4-panels + 2 summary figures)."""
import json, base64
from pathlib import Path

SCR = Path(r"C:/Users/junho/AppData/Local/Temp/claude/C--Users-junho-Desktop-Research-4-Bar-Link-CVT-Data-26-03-24-Jump/91aad6ed-e999-400c-bacd-e1da7d4a5da4/scratchpad")
VIZ = SCR / "viz_final"; JPG = VIZ / "jpg"
OUT = SCR / "g20_graphs.html"

res = json.load(open(VIZ / "viz_index.json"))


def b64(p):
    return "data:image/jpeg;base64," + base64.b64encode(Path(p).read_bytes()).decode()


GROUPS = [
    ("jump_0324", "3월 점프 (26.03.24)", "MIT PD, dq_des=0"),
    ("jump_position_0421", "위치제어 점프 (26.04.21)", "MIT PD, dq_des=0"),
    ("jump_0424", "26.04.24", "MIT PD (q+dq)"),
    ("jump_0602", "26.06.02", "MIT PD (q+dq) · 기준 캘리브레이션"),
]

sections = ""
for pfx, name, desc in GROUPS:
    cards = []
    for r in res:
        if r["ds"] != pfx:
            continue
        img = b64(JPG / (Path(r["png"]).stem + ".jpg"))
        cards.append(
            f'''<figure class="card"><img loading="lazy" src="{img}" alt="{r['sub']}" class="zoom">
<figcaption><span class="sub">{r['sub']}</span><span class="chips">
<span class="chip">h_sim <b>{r['h_sim']:.2f}</b></span><span class="chip cam">h_cam <b>{r['h_real']:.2f}</b></span>
<span class="chip pct">{r['h_sim']/r['h_real']*100:.0f}%</span></span></figcaption></figure>''')
    cnt = len(cards)
    sections += (f'<section class="ds" id="{pfx}"><div class="ds-head"><h2>{name}</h2>'
                 f'<span class="ds-meta">{cnt} trials · {desc}</span></div>'
                 f'<div class="grid">{"".join(cards)}</div></section>')

nav = "".join(f'<a href="#{p}">{nm}</a>' for p, nm, _ in GROUPS)
hsum = b64(VIZ / "height_summary.png")
env = b64(VIZ / "nlp_envelope_check.png")

html = f'''<title>G20 그래프 갤러리 — 24 trials + 요약</title>
<style>
:root{{--paper:#f6f7f9;--surface:#fff;--ink:#17191e;--muted:#5c626d;--faint:#8b909b;--border:#e4e7ec;
--accent:#0f7d8c;--accent-deep:#0a5a66;--cam:#b5622a;
--mono:ui-monospace,"Cascadia Code",Consolas,monospace;--sans:-apple-system,"Segoe UI","Malgun Gothic",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6}}
.wrap{{max-width:1240px;margin:0 auto;padding:0 20px}}
header{{border-bottom:1px solid var(--border);background:linear-gradient(180deg,#fbfcfd,var(--paper))}}
header .wrap{{padding:26px 20px 18px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-deep);margin:0 0 8px}}
h1{{font-size:clamp(20px,3.2vw,30px);margin:0 0 8px;text-wrap:balance}}
.lede{{font-size:14.5px;color:var(--muted);margin:0}}
nav.ds-nav{{position:sticky;top:0;z-index:5;background:rgba(246,247,249,.93);backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}}
nav.ds-nav .wrap{{display:flex;gap:6px;flex-wrap:wrap;padding:9px 20px}}
nav.ds-nav a{{font-family:var(--mono);font-size:12px;text-decoration:none;color:var(--muted);padding:5px 11px;border:1px solid var(--border);border-radius:20px;background:var(--surface)}}
section.ds{{padding:26px 0 8px;border-top:1px solid var(--border)}}
section.ds:first-of-type{{border-top:none}}
.ds-head{{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
h2{{font-size:19px;margin:0}}.ds-meta{{font-family:var(--mono);font-size:12px;color:var(--faint)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(560px,1fr));gap:16px}}
figure.card{{margin:0;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}}
figure.card img{{width:100%;display:block;border-bottom:1px solid var(--border);cursor:zoom-in}}
figcaption{{padding:9px 13px;display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}}
figcaption .sub{{font-family:var(--mono);font-size:13px;font-weight:600}}
.chips{{display:flex;gap:6px}}.chip{{font-family:var(--mono);font-size:11px;color:var(--muted);background:#eef1f4;border-radius:5px;padding:3px 7px}}
.chip b{{color:var(--ink)}}.chip.cam b{{color:var(--cam)}}.chip.pct{{background:#e7f0f1;color:var(--accent-deep)}}
footer{{border-top:1px solid var(--border);padding:20px 0 40px;color:var(--faint);font-family:var(--mono);font-size:12px}}
.lb{{position:fixed;inset:0;background:rgba(15,17,20,.93);display:none;align-items:center;justify-content:center;z-index:50;padding:16px;cursor:zoom-out}}
.lb.on{{display:flex}}.lb img{{max-width:100%;max-height:100%;border-radius:6px}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr}}}}
</style>
<header><div class="wrap">
<p class="eyebrow">G20 · 4-bar 디지털 트윈 · 그래프 갤러리 (2026-07-05)</p>
<h1>전체 결과 그래프 — 24 trials 4-panel + 요약 2장</h1>
<p class="lede">각 그림: q₁/q₂/dq₂/base_z — <b style="color:#1f77b4">sim 파랑 실선</b> vs <b style="color:#b5622a">real 주황 점선</b> (per-date offset 보정 표기). 그림 클릭 = 확대.
전체 서사와 표는 <a href="https://claude.ai/code/artifact/7eeaec44-536d-4a56-9556-444c0f874d04">최종 보고서</a>에.</p>
</div></header>
<nav class="ds-nav"><div class="wrap"><a href="#summary">요약</a>{nav}</div></nav>

<section class="ds" id="summary"><div class="wrap">
<div class="ds-head"><h2>요약 그림</h2><span class="ds-meta">held-out 점프높이 · NLP T-N 포락선</span></div>
<div class="grid">
<figure class="card"><img src="{hsum}" class="zoom" alt="height summary">
<figcaption><span class="sub">height_summary</span><span class="chips"><span class="chip">24 trials h_sim vs h_cam (held-out)</span></span></figcaption></figure>
<figure class="card"><img src="{env}" class="zoom" alt="envelope">
<figcaption><span class="sub">nlp_envelope_check</span><span class="chips"><span class="chip">NLP 최적 vs 실증 운전점 (hip/knee)</span></span></figcaption></figure>
</div></div></section>
<div class="wrap">{sections}</div>
<footer><div class="wrap">원본 PNG: Documents/jump-opt-digital-twin/code/goal19/phase11/viz_final/ · 애니메이션 25 GIF: 같은 경로 anim_final/ · sim = round-1 4-bar canonical twin</div></footer>
<div class="lb" id="lb"><img id="lbimg" alt=""></div>
<script>(function(){{var lb=document.getElementById('lb'),im=document.getElementById('lbimg');
document.addEventListener('click',function(e){{if(e.target.classList&&e.target.classList.contains('zoom')){{im.src=e.target.src;lb.classList.add('on');}}
else if(e.target===lb||e.target===im){{lb.classList.remove('on');im.src='';}}}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape'){{lb.classList.remove('on');im.src='';}}}});}})();</script>
'''
OUT.write_text(html, encoding="utf-8")
print("WROTE", OUT, "%.1f MB" % (OUT.stat().st_size / 1e6))
