# -*- coding: utf-8 -*-
"""fs_track2 — 마라톤 C Phase 3: 운동 방향 조건부 요구 토크 (마찰/정역학 분해) + 트윈 조인.

원리: 저속 운동 중 실측 raw = 준정적 요구 + 마찰·sign(dq) (+ 소량 kd·ė). 같은 깊이 bin에서
  하강(desc, dq2<0) vs 상승(asc, dq2>0) 중앙값을 나누면
  마찰 f = (asc − desc)/2 · 정역학 midline = (asc + desc)/2 — 상승이 마찰만큼 더 든다.
트윈 조인: _fs_static_audit.json의 settle 유지토크 s1,s2(자세별, ahat Nm)를 같은 bin으로 →
  모델 갭 = ahat(midline) − s. (kp·e/raw는 총 요구 — 모델 오차는 갭이다: fs_track 자기교정)
정지(hold) 창 판정과 독립 — 미끼가 연속 램프여도 성립 (fs_track T3 대체).
출력: _fs_track2.json. CLI: python fs_track2.py
"""
import os, sys, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bench"))
import safe
import fs_data as FD
from fs3_recon import ROOT
from fs_track import load_full, BINS
import fs_calib as FC                     # P/A (ahat) + 감사 재사용

A = FC.A
Z0 = np.zeros(1)


def ahat0(raw):
    """정지 기준 raw→축 Nm (dq=0)."""
    return float(FC.P.J.ahat(A, np.array([raw]), Z0)[0])


def main():
    state = json.load(open(HERE / "_fs3_state.json", encoding="utf-8"))
    audit = json.load(open(HERE / "_fs_static_audit.json", encoding="utf-8"))
    OUT = {}
    sess_keys = {}
    for key in sorted(state):
        fold = ROOT / key
        sess = key.split("/")[0]
        if not (fold / "hip3.xlsx").exists() or not FD.gains_of(fold.name):
            continue
        if sess.startswith("26.04.29"):
            continue                       # CVT: knee 채널=크랭크측 — 깊이 정의 상이
        sess_keys.setdefault(sess, []).append(key)

    for sess, keys in sorted(sess_keys.items()):
        acc = {}                           # bin → dict(desc1[], asc1[], desc2[], asc2[])
        for key in keys:
            fold = ROOT / key
            try:
                d = load_full(fold)
            except Exception:
                continue
            en = max(state[key]["h"]["t_enable"] or 0, state[key]["k"]["t_enable"] or 0)
            t = d["t"]
            gs = np.convolve(d["grf"], np.ones(25) / 25, mode="same")
            g_fl = float(np.quantile(gs, 0.02)); g_full = float(np.quantile(gs, 0.90))
            gnd = gs > g_fl + 0.6 * (g_full - g_fl)
            base = (t > en + 1) & gnd & (np.abs(d["dq1"]) < 0.6)
            sp = np.abs(d["dq2"])
            desc = base & (d["dq2"] < -0.05) & (sp < 0.4)
            asc = base & (d["dq2"] > 0.05) & (sp < 0.4)
            q2d = np.degrees(d["q2"])
            for b0 in BINS:
                mb = (q2d >= b0) & (q2d < b0 + 5)
                a = acc.setdefault(f"{b0:.0f}", dict(d1=[], a1=[], d2=[], a2=[]))
                if (mb & desc).sum() >= 60:
                    a["d1"].append(float(np.median(d["raw1"][mb & desc])))
                    a["d2"].append(float(np.median(d["raw2"][mb & desc])))
                if (mb & asc).sum() >= 40:
                    a["a1"].append(float(np.median(d["raw1"][mb & asc])))
                    a["a2"].append(float(np.median(d["raw2"][mb & asc])))
        # 트윈 s 프로파일 (감사 표본 pool)
        sprof = {}
        au = audit.get(sess, {})
        rows = [r for tr in au.values() for r in tr.get("rows", []) if r.get("ok")]
        for b0 in BINS:
            rs = [r for r in rows if b0 <= np.degrees(r["q2"]) < b0 + 5]
            if len(rs) >= 3:
                sprof[f"{b0:.0f}"] = [float(np.median([r["s1"] for r in rs])),
                                      float(np.median([r["s2"] for r in rs]))]
        res = {}
        for b, a in acc.items():
            if not a["d1"]:
                continue
            D1, D2 = np.median(a["d1"]), np.median(a["d2"])
            r = dict(desc=[round(D1, 2), round(D2, 2)], n_tr=[len(a["d1"]), len(a["a1"])])
            if a["a1"]:
                A1, A2 = np.median(a["a1"]), np.median(a["a2"])
                r["asc"] = [round(A1, 2), round(A2, 2)]
                r["fric_raw"] = [round((A1 - D1) / 2, 2), round((A2 - D2) / 2, 2)]
                r["mid_Nm"] = [round(ahat0((A1 + D1) / 2), 2), round(ahat0((A2 + D2) / 2), 2)]
                if b in sprof:
                    r["twin_s"] = [round(sprof[b][0], 2), round(sprof[b][1], 2)]
                    r["gap_Nm"] = [round(r["mid_Nm"][0] - sprof[b][0], 2),
                                   round(r["mid_Nm"][1] - sprof[b][1], 2)]
            res[b] = r
        OUT[sess] = res
        # 요약 출력 (깊은 bin들)
        print(f"\n--- {sess} ---", flush=True)
        print(f"{'bin':>5} | {'desc raw':>13} | {'asc raw':>13} | {'fric raw':>11} | {'mid Nm':>12} | {'twin s':>12} | {'gap Nm':>11}", flush=True)
        for b in sorted(res, key=float):
            r = res[b]
            f_ = lambda v: "—" if v is None else ("%+.1f,%+.1f" % tuple(v))
            print(f"{b:>5} | {f_(r['desc']):>13} | {f_(r.get('asc')):>13} | {f_(r.get('fric_raw')):>11} | "
                  f"{f_(r.get('mid_Nm')):>12} | {f_(r.get('twin_s')):>12} | {f_(r.get('gap_Nm')):>11}", flush=True)

    safe.atomic_json_write(HERE / "_fs_track2.json", OUT)
    print("\ndone → _fs_track2.json", flush=True)


if __name__ == "__main__":
    main()
