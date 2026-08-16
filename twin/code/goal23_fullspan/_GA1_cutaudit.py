# -*- coding: utf-8 -*-
"""_GA1_cutaudit — **접지 절단이 이른가**를 전 trial 에서 검사 (마라톤G, 08-09).

왜
  사용자가 "영상에선 발끝이 많이 움직이는데 수치가 작다"를 반복해 지적했고,
  실제로 `0723/60_0.75_60_2` 는 절단 규칙 때문에 푸시가 통째로 잘려 있었다 (+1.2 → −48.6).
  한 건씩 고치는 대신 **전 55 trial 에 같은 질문을 던진다**:
    "f_end 다음 프레임들에서 롤러가 아직 알아볼 만한가? 그렇다면 얼마나 더 움직였나?"

방법 (측정 파이프라인과 독립)
  f_end−4 부터 f_end+8 까지, **반지름을 그 trial 값으로 고정**하고 넉넉한 창(±50px)으로
  롤러를 따라간다. 점수를 푸시 직전 중앙값으로 정규화해 신뢰도를 본다.
  ★ 반지름 고정이 핵심이다 — 자유 반지름은 블러 구간에서 작은 특징으로 도망간다
    (실측: 어긋난 중심에서 r 9.5 가 나와 "롤러가 사라졌다"고 오판할 뻔했다).

판정 — 두 조건을 **모두** 만족해야 "아직 접지"
  ① score/s0 ≥ 0.55            (롤러를 아직 알아본다)
  ② |cy − 접지높이| ≤ 10px·k    (발이 지면 높이에 있다 = 안 떴다)
  ★ ①만 쓰면 **공중에 뜬 뒤에도 롤러가 보이므로** 조기절단을 과대평가한다
    (실측: 0724 에서 8프레임 −79mm 로 나왔는데 그중 6프레임은 공중이었다).

CLI: python _GA1_cutaudit.py [세션 ...]
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("P25_CLIP_RAW", "35.5")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_vidscale as VS                                        # noqa: E402

SRC = HERE / "_G72_slipall.json"
OUT = HERE / "_GA1_cutaudit.json"
AFTER = 8          # f_end 이후 몇 프레임까지 볼 것인가
OKR = 0.55         # 점수/기준 이 값 이상이면 "아직 롤러"


def audit_one(v, sess, trial):
    import fs_data as FD
    import imageio.v3 as iio
    p = [q for s, q, g, c, h in FD.registry() if s == sess and q.name == trial][0]
    mp4 = [x for x in sorted(Path(p).glob("*.mp4")) if "online-video-cutter" not in x.name][0]
    s = v["series"]
    f = np.array(s["f"], int); cx = np.array(s["cx"]); cy = np.array(s["cy"])
    sc = np.array(s["sc"])
    ds = int(v["px_ds"]); k = float(v["px_k"])
    r = float(v["dia_px"]) / 2.0
    scale = float(v["scale"])
    f_end = int(v["f_end"])
    # 기준 점수 = 푸시 이전(마지막 15프레임 제외) 중앙값
    s0 = float(np.median(sc[: max(5, len(sc) - 15)]))
    f0 = max(0, f_end - 4); f1 = f_end + AFTER
    G = {}
    for i, fr in enumerate(iio.imiter(mp4)):
        if f0 <= i <= f1:
            a = np.asarray(fr, float)[..., :3].mean(axis=2)
            G[i] = a[::ds, ::ds] if ds > 1 else a
        if i > f1:
            break
    j = int(np.argmin(np.abs(f - f0)))
    px, py = float(cx[j]), float(cy[j])
    rows = []
    for i in sorted(G):
        s2, X, Y, _ = VS.fit_roller(G[i], px, py, win=50.0 * k, win_y=25.0 * k, step=1.0,
                                    rrange=(r, r + 0.01, 0.1), sector=VS.SECTOR,
                                    d=VS.EDGE_D * k, refine=0.25)
        rows.append(dict(f=i, cx=X, cy=Y, sc=s2, rel=s2 / max(s0, 1e-9)))
        px, py = X, Y
    # f_end 이후로 연속해서 신뢰되는 프레임
    # 접지 높이 = 푸시 이전 cy 중앙값
    y0 = float(np.median(cy[: max(5, len(cy) - 15)]))
    for q in rows:
        q["dy"] = q["cy"] - y0
    post = [q for q in rows if q["f"] > f_end]
    n_ok = 0
    for q in post:
        if q["rel"] >= OKR and abs(q["dy"]) <= 10.0 * k:
            n_ok += 1
        else:
            break
    x_end = [q for q in rows if q["f"] == f_end]
    extra = 0.0
    if n_ok and x_end:
        extra = (post[n_ok - 1]["cx"] - x_end[0]["cx"]) * scale
    return dict(sess=sess, trial=trial, f_end=f_end, s0=s0, y0=y0, n_ok=n_ok,
                extra_mm=float(extra), rows=rows)


def main():
    import fs_data as FD                                        # noqa: F401
    d = json.load(io.open(SRC, encoding="utf-8"))
    want = set(sys.argv[1:])
    res = {}
    for key, v in sorted(d.items()):
        if not (v.get("ok") and "cx" in (v.get("series") or {})):
            continue
        if want and v["sess"] not in want:
            continue
        try:
            a = audit_one(v, v["sess"], v["trial"])
        except Exception as ex:
            print(f"  ✗ {key}: {type(ex).__name__} {str(ex)[:60]}", flush=True); continue
        res[key] = a
        mark = "★조기절단" if (a["n_ok"] >= 2 and abs(a["extra_mm"]) > 5) else ""
        print(f"{key:32s} f_end {a['f_end']:4d} · 이후 신뢰 {a['n_ok']}프레임 · "
              f"추가 Δx {a['extra_mm']:+7.2f}mm  {mark}", flush=True)
    import safe
    safe.atomic_json_write(OUT, res)
    bad = [a for a in res.values() if a["n_ok"] >= 2 and abs(a["extra_mm"]) > 5]
    print(f"\n조기절단 의심: {len(bad)}/{len(res)}")
    for a in sorted(bad, key=lambda z: -abs(z["extra_mm"])):
        print(f"  {a['sess']}/{a['trial']:24s} 추가 {a['extra_mm']:+7.2f}mm "
              f"({a['n_ok']}프레임)")


if __name__ == "__main__":
    main()
