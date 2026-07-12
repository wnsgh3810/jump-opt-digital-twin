# -*- coding: utf-8 -*-
"""bench — 디지털 트윈 후보 평가/비교/승격 CLI (사고의 외골격).

사용 (cwd 무관):
  python code/bench/bench.py eval <candidate.json> [--judge p19|modea|p14] [--tol 0.005]
  python code/bench/bench.py compare <a.json> <b.json> [...]
  python code/bench/bench.py promote <candidate.json> --note "..." [--force]
  python code/bench/bench.py list
  python code/bench/bench.py stack

원칙:
  - 심판 재구현 금지 (p19_adapter가 검증된 진입점만 래핑)
  - promote는 게이트 내장: ① eval 재현(저장 지표와 대조) ② held-out이 현행보다
    3%p 초과 악화 시 거부 — 모델이 독트린을 기억할 필요 없게 도구가 거부한다.
  - registry.json/CURRENT_STACK.md 갱신은 이 CLI만 (원자적 쓰기).
"""
import argparse
import datetime
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import safe  # noqa: E402

safe.utf8_console()

REG = HERE / "registry.json"
STACK = HERE / "CURRENT_STACK.md"
REPO = HERE.parent.parent


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def load_registry():
    if REG.exists():
        return safe.read_json(REG)
    return {"current": None, "candidates": {}}


def cand_key(cand, path):
    name = cand.get("CANDIDATE", Path(path).stem)
    for tok in name.replace("(", " ").replace(")", " ").split():
        t = tok.lower().rstrip(",")
        if t.startswith("p1") or t.startswith("p2"):
            return t
    return Path(path).stem.replace("fourbar_", "").replace("_candidate", "")


# ── eval ──
def do_eval(path, judge="p19", tol=0.005, quiet=False):
    import p19_adapter as A
    cand = A.load_candidate(path)
    if judge == "p14":
        r = A.eval_p14(cand)
        if not quiet:
            print(f"[p14 judge] " + " ".join(f"{k}={v:.4g}" for k, v in r.items()))
        return {"judge": "p14", **r}
    if judge == "modea":
        r = A.eval_modea(cand)
        if not quiet:
            print("[modea] " + " ".join(f"{k}={v:.0f}" for k, v in r.items()))
        return {"judge": "modea", **r}
    r = A.eval_p19(cand)
    if not quiet:
        print(f"후보: {cand.get('CANDIDATE', path)}")
        for ds, (g, q2, n) in sorted(r["summary"].items()):
            if ds.startswith("jump"):
                print(f"  {ds:22s} τ-갭 {100*g:5.1f}%  q2 {q2:.3f}  (n={n})")
        print(f"  FIT {100*r['fit']:.1f}%  |  held-out(0324) {100*r['heldout']:.1f}%")
    # 재현 판정 (후보 JSON에 저장된 지표가 있으면)
    stored = cand.get("metric_full")
    verdict = None
    if stored is not None:
        drift = abs(r["fit"] - float(stored))
        verdict = "REPRODUCED" if drift <= tol else f"DRIFT(Δ{100*drift:.2f}%p)"
        if not quiet:
            print(f"  저장 지표 {100*float(stored):.1f}% 대비: {verdict}")
    return {"judge": "p19", "fit": r["fit"], "heldout": r["heldout"],
            "summary": r["summary"], "verdict": verdict}


# ── compare ──
def do_compare(paths, judge="p19"):
    rows = []
    for p in paths:
        r = do_eval(p, judge=judge, quiet=True)
        rows.append((p, r))
        print(f"... {Path(p).name} 완료", flush=True)
    if judge != "p19":
        for p, r in rows:
            print(f"{Path(p).name:36s} " + " ".join(f"{k}={v:.4g}" for k, v in r.items()
                                                    if k != "judge"))
        return
    dss = sorted({ds for _, r in rows for ds in r["summary"] if ds.startswith("jump")})
    hdr = f"{'후보':34s}" + "".join(f"{ds.split('_')[-1]:>8s}" for ds in dss) + \
          f"{'FIT':>8s}{'HO':>8s}"
    print("\n" + hdr)
    for p, r in rows:
        line = f"{Path(p).name[:33]:34s}"
        for ds in dss:
            g = r["summary"].get(ds, (float('nan'),))[0]
            line += f"{100*g:8.1f}"
        line += f"{100*r['fit']:8.1f}{100*r['heldout']:8.1f}"
        print(line)


# ── stack ──
def render_stack(reg):
    cur = reg.get("current")
    lines = ["<!-- STATUS -->", "# CURRENT_STACK — 현행 디지털 트윈 스택 (수치의 단일 출처)", ""]
    if cur and cur in reg["candidates"]:
        c = reg["candidates"][cur]
        lines += [
            f"**현행: {cur}** — {c.get('note', '')}  (승격 {c.get('promoted', '?')})",
            f"- 후보 파일: `{c['path']}`  (judge: {c.get('judge', 'p19')})",
            f"- 점프 CL τ-갭 FIT **{100*c.get('metric_full', float('nan')):.1f}%** · "
            f"held-out(0324) {100*c.get('heldout', float('nan')):.1f}% · "
            f"푸시 충실도 {100*c['metric_push']:.1f}%" if c.get("metric_push") else "",
            "- 3계층: 플랜트(x) × 커맨드층(p19_cmdlayer.json: α·클립±35.5·지연) × 변환식 A=Paper",
        ]
    else:
        lines += ["**현행: 미지정** — 전 후보 bench 재평가 후 promote로 확정 예정."]
    lines += ["", "<!-- END-STATUS -->", "", "## 후보 레지스트리", "",
              "| key | 상태 | FIT | HO | judge | 파일 | note |",
              "|---|---|---|---|---|---|---|"]
    for k, c in sorted(reg["candidates"].items()):
        fit = f"{100*c['metric_full']:.1f}%" if c.get("metric_full") is not None else "—"
        ho = f"{100*c['heldout']:.1f}%" if c.get("heldout") is not None else "—"
        lines.append(f"| {k} | {c.get('status', '?')} | {fit} | {ho} | "
                     f"{c.get('judge', '?')} | `{c['path']}` | {c.get('note', '')} |")
    lines += ["", "## 변경 로그", ""]
    lines += reg.get("changelog", ["(없음)"])
    STACK.write_text("\n".join(lines), encoding="utf-8")
    print(f"CURRENT_STACK.md 갱신 ({STACK})")


# ── promote ──
def do_promote(path, note, force=False):
    import p19_adapter as A
    reg = load_registry()
    cand = A.load_candidate(path)
    key = cand_key(cand, path)
    print(f"승격 심사: {key} ({path})")
    r = do_eval(path, judge="p19")
    # 게이트 1: 재현 (저장 지표 있으면)
    if r["verdict"] and r["verdict"].startswith("DRIFT") and not force:
        print(f"거부: 저장 지표와 불일치 {r['verdict']} — 원인 규명 전 승격 불가 (--force로 무시 가능)")
        return 1
    # 게이트 2: held-out — 현행 대비 3%p 초과 악화 금지
    cur = reg.get("current")
    if cur and cur in reg["candidates"] and not force:
        cur_ho = reg["candidates"][cur].get("heldout")
        if cur_ho is not None and r["heldout"] > cur_ho + 0.03:
            print(f"거부: held-out {100*r['heldout']:.1f}% > 현행 {100*cur_ho:.1f}%+3%p — "
                  f"과적합 의심. (--force로 무시 가능하나 근거를 note에 남길 것)")
            return 1
    today = datetime.date.today().isoformat()
    reg["candidates"][key] = {
        "path": _rel(path), "judge": "p19",
        "metric_full": r["fit"], "heldout": r["heldout"],
        "metric_push": cand.get("metric_push"),
        "status": "CURRENT", "promoted": today, "note": note or "",
    }
    prev = reg.get("current")
    if prev and prev != key and prev in reg["candidates"]:
        reg["candidates"][prev]["status"] = "SUPERSEDED"
    reg["current"] = key
    reg.setdefault("changelog", []).insert(
        0, f"- {today}: **{key}** 승격 (FIT {100*r['fit']:.1f}% / HO {100*r['heldout']:.1f}%)"
           f" — {note or ''} (이전: {prev or '없음'})")
    safe.atomic_json_write(REG, reg)
    render_stack(reg)
    print(f"승격 완료: current = {key}")
    return 0


def do_list():
    reg = load_registry()
    print(f"current: {reg.get('current')}")
    for k, c in sorted(reg["candidates"].items()):
        fit = f"{100*c['metric_full']:.1f}%" if c.get("metric_full") is not None else "  — "
        ho = f"{100*c['heldout']:.1f}%" if c.get("heldout") is not None else "  — "
        print(f"  {k:8s} {c.get('status', '?'):11s} FIT {fit:>7s}  HO {ho:>7s}  "
              f"[{c.get('judge', '?')}] {c['path']}")


def main():
    ap = argparse.ArgumentParser(prog="bench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval"); e.add_argument("path")
    e.add_argument("--judge", default="p19", choices=["p19", "modea", "p14"])
    e.add_argument("--tol", type=float, default=0.005)
    c = sub.add_parser("compare"); c.add_argument("paths", nargs="+")
    c.add_argument("--judge", default="p19", choices=["p19", "modea", "p14"])
    p = sub.add_parser("promote"); p.add_argument("path")
    p.add_argument("--note", default=""); p.add_argument("--force", action="store_true")
    sub.add_parser("list")
    sub.add_parser("stack")
    a = ap.parse_args()
    if a.cmd == "eval":
        do_eval(a.path, a.judge, a.tol)
    elif a.cmd == "compare":
        do_compare(a.paths, a.judge)
    elif a.cmd == "promote":
        sys.exit(do_promote(a.path, a.note, a.force))
    elif a.cmd == "list":
        do_list()
    elif a.cmd == "stack":
        render_stack(load_registry())


if __name__ == "__main__":
    main()
