# -*- coding: utf-8 -*-
"""_GHA_board — 후보 하나를 **세 채점판 전부**로 재고 게이트까지 본다 (마라톤H, 2026-08-11).

왜 새로 만드나
  `_GH2/_GH3` 는 폐루프만 본다. 그런데 사용자 지적("mode A 도 고려해") 이후 확인했듯이
  **질량류 축은 폐루프와 주입재생을 반대로 끈다** — 폐루프만 보면 나쁜 후보를 채택하게 된다.
  그림 130장을 그리는 정본 경로는 너무 무거우므로, 같은 계산만 뽑아 쓴다.

무엇을 재나 (전부 낮을수록 좋음)
  · 측정 토크 주입 재생 : 실제로 측정된 토크를 그대로 넣고 돌린 뒤 관절각·각속도 4채널 RMSE.
    PD 가 없으므로 오차를 흡수하지 못한다 — 물리(질량·관성·마찰)의 1급 심판.
    토크는 **주입한 값**이라 예측이 아니므로 채널에서 뺀다.
  · 폐루프           : 실제 게인으로 PD 제어를 돌린 뒤 관절각·각속도·토크 6채널 RMSE.
  · 점프 높이        : 지면 기준 몸통 중심 최고 높이, 영상 실측 대비 오차의 절대값 평균.
  · 게이트 5종       : 0324 주입재생 · 0421 주입재생 · 0421 폐루프 · 0429(변속기) 둘 —
                      각각 기준선 대비 +2% 넘게 나빠지면 탈락.

점수는 **기준선(현행 env)을 같은 실행 안에서 먼저 재고** 채널별로 나눠 정규화한다.
과거에 적어둔 절대값과 맞출 필요가 없어지고, 큰 채널이 점수를 독식하는 문제도 막는다.

CLI: python _GHA_board.py "무릎마찰=FS_KNEEM_FL=0.46" "둘다=FS_KNEEM_FL=0.46;FS_KNEEM_DAMP=0.02"
     후보 = `이름=변수=값;변수=값` — **변수 구분은 세미콜론**이다 (값 안에 쉼표가 들어가는
     환경변수가 있다: FS_TFRIC="0.46,0.19,0,0.05"). 인자가 없으면 기본 후보표를 쓴다.
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHA_board.json"
CH6 = ("q1", "q2", "dq1", "dq2", "a1", "a2")
CH4 = ("q1", "q2", "dq1", "dq2")
GATE_MA = ("26.03.24", "26.04.21", "26.04.29")
GATE_CL = ("26.04.21", "26.04.29")

# 기본 후보 = 08-11 매달림 실측으로 잰 마찰값 (`_GH9_friction.py`)
#   실측: 힙 건마찰 0.28 N·m · 무릎 건마찰 0.46 N·m · 속도 비례 성분은 둘 다 거의 0
#   현행: 힙 0.238/감쇠 0.312 · 무릎 0.247/감쇠 0.150
DEFAULT = [
    ("무릎 건마찰 0.46 (실측)", {"FS_KNEEM_FL": "0.46"}),
    ("무릎 속도비례 0.02 (실측)", {"FS_KNEEM_DAMP": "0.02"}),
    ("무릎 둘 다 (실측)", {"FS_KNEEM_FL": "0.46", "FS_KNEEM_DAMP": "0.02"}),
    ("힙 건마찰 0.28 (실측)", {"FS_HIPM_FL": "0.28"}),
    ("힙 속도비례 0.02 (실측)", {"FS_HIPM_DAMP": "0.02"}),
    ("힙 둘 다 (실측)", {"FS_HIPM_FL": "0.28", "FS_HIPM_DAMP": "0.02"}),
    ("건마찰만 둘 다", {"FS_KNEEM_FL": "0.46", "FS_HIPM_FL": "0.28"}),
    ("네 값 전부 (실측)", {"FS_KNEEM_FL": "0.46", "FS_KNEEM_DAMP": "0.02",
                          "FS_HIPM_FL": "0.28", "FS_HIPM_DAMP": "0.02"}),
]


def board():
    """반환 {세션: dict(ma=[4], cl=[6], h=오차)} — 실패 세션은 빠진다."""
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR, fs_metric as FMET
    ft = FR.fs_twin()
    G = collections.defaultdict(lambda: dict(ma=[], cl=[], h=[]))
    for s, p, g, cvt, ho in FD.registry():
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            pw = FD.plot_window(p, d)
            if pw is None:
                continue
            t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
            if m.sum() < 30:
                continue
            i0 = int(np.argmax(m)); tg = t[m] - t[i0]
            sp = CP.sess_params(s)
            # ① 측정 토크 주입 재생
            Lf = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                    float(d["q1"][i0]), float(d["q2"][i0]),
                                    float(d["dq1"][i0]), float(d["dq2"][i0]),
                                    float(tg[-1] - 0.004), bias1=sp["bias1"],
                                    knee_deep=sp["knee_deep"], fade=True)
            if Lf is not None:
                gf = lambda k: np.interp(tg, Lf["t"], Lf[k])
                sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                G[s]["ma"].append([float(np.sqrt(np.mean((d[k][m] - v) ** 2))) *
                                   (180 / np.pi if k in ("q1", "q2") else 1)
                                   for k, v in zip(CH4, sim)])
                # ② 점프 높이 — 이지 후 0.6초까지 연장 재생해서 최고점을 직접 읽는다
                t_ext = min(t[m][-1] + 0.6, t[-1])
                m2 = (t >= t[i0]) & (t <= t_ext); tg2 = t[m2] - t[i0]
                Hf = FR.rollout_ol_fs_b(ft, tg2, d["raw1"][m2], d["raw2"][m2],
                                        float(d["q1"][i0]), float(d["q2"][i0]),
                                        float(d["dq1"][i0]), float(d["dq2"][i0]),
                                        float(tg2[-1] - 0.004), bias1=sp["bias1"],
                                        knee_deep=sp["knee_deep"], fade=True)
                hv = CP.real_h(p)
                if Hf is not None and hv is not None and np.isfinite(hv):
                    G[s]["h"].append(abs(float(np.asarray(Hf["bz"]).max()) - float(hv)))
            # ③ 폐루프
            if g:
                r = CP.cl_pair(d, seg, g, s)
                if r is not None:
                    _t, (mo, mf), old, fs, _m, _c, _ = r
                    G[s]["cl"].append([float(np.sqrt(np.mean((np.asarray(mf[k]) -
                                                             np.asarray(fs[i])) ** 2))) *
                                       (180 / np.pi if k in ("q1", "q2") else 1)
                                       for i, k in enumerate(CH6)])
        except Exception:
            continue
    out = {}
    for s, v in G.items():
        if not v["ma"] and not v["cl"]:
            continue
        out[s] = dict(ma=np.mean(v["ma"], axis=0).tolist() if v["ma"] else None,
                      cl=np.mean(v["cl"], axis=0).tolist() if v["cl"] else None,
                      h=float(np.mean(v["h"])) if v["h"] else None)
    return out


def agg(B, base, key, sess=None):
    """채널별로 기준선에 나눠 정규화한 뒤 평균 → 1.0 = 기준선과 동일."""
    v = []
    for s, d in B.items():
        if sess and s not in sess:
            continue
        if d.get(key) is None or base.get(s, {}).get(key) is None:
            continue
        a = np.asarray(d[key], float); b = np.asarray(base[s][key], float)
        if np.all(b > 0):
            v.append(np.mean(a / b))
    return float(np.mean(v)) if v else np.nan


def main():
    import fs_runner as FR
    cands = []
    for a in sys.argv[1:]:
        nm, spec = a.split("=", 1)
        # 변수 구분 = 세미콜론 (값 자체에 쉼표가 들어가므로 — FS_TFRIC 등)
        cands.append((nm, dict(x.split("=", 1) for x in spec.split(";"))))
    if not cands:
        cands = DEFAULT
    keys = sorted({k for _, c in cands for k in c})
    saved = {k: os.environ.get(k) for k in keys}

    def restore():
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        FR._S2S = None
        if hasattr(FR, "TW"):
            pass

    restore()
    print("기준선 측정 중 …", flush=True)
    BASE = board()
    if not BASE:
        raise SystemExit("기준선 실패")
    print(f"  세션 {len(BASE)} 개\n")
    print(f"{'후보':26s} {'주입재생':>9s} {'폐루프':>8s} {'점프높이':>9s} {'종합':>8s} | 게이트")
    print(f"{'(기준선)':26s} {'0.00%':>9s} {'0.00%':>8s} {'0.00%':>9s} {'0.00%':>8s} |")
    RES = {}
    for nm, cfg in cands:
        restore()
        for k, v in cfg.items():
            os.environ[k] = v
        FR._S2S = None
        try:
            B = board()
        except Exception as ex:
            print(f"{nm:26s} 실패 {type(ex).__name__}"); continue
        if not B:
            print(f"{nm:26s} 실패"); continue
        ma = agg(B, BASE, "ma"); cl = agg(B, BASE, "cl")
        hs = [B[s]["h"] / BASE[s]["h"] for s in B
              if B[s].get("h") and BASE.get(s, {}).get("h")]
        h = float(np.mean(hs)) if hs else np.nan
        tot = 0.40 * ma + 0.40 * cl + 0.20 * (h if np.isfinite(h) else 1.0)
        gm = agg(B, BASE, "ma", GATE_MA); gc = agg(B, BASE, "cl", GATE_CL)
        bad = []
        for s in GATE_MA:
            r = agg({s: B[s]}, BASE, "ma", (s,)) if s in B else np.nan
            if np.isfinite(r) and r > 1.02:
                bad.append(f"{s[3:]}주입 +{100*(r-1):.1f}%")
        for s in GATE_CL:
            r = agg({s: B[s]}, BASE, "cl", (s,)) if s in B else np.nan
            if np.isfinite(r) and r > 1.02:
                bad.append(f"{s[3:]}폐루프 +{100*(r-1):.1f}%")
        RES[nm] = dict(cfg=cfg, ma=ma, cl=cl, h=h, tot=tot, gate_ma=gm, gate_cl=gc, bad=bad)
        f = lambda x: f"{100*(x-1):+.2f}%"
        print(f"{nm:26s} {f(ma):>9s} {f(cl):>8s} {f(h):>9s} {f(tot):>8s} | "
              f"{'통과' if not bad else ' · '.join(bad)}", flush=True)
    restore()
    import safe
    safe.atomic_json_write(OUT, dict(base=BASE, res=RES))
    print(f"\n저장 → {OUT}")
    print("※ 종합 = 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이 (전부 기준선=0%, 음수가 개선)")


if __name__ == "__main__":
    main()
