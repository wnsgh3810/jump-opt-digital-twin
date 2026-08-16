# -*- coding: utf-8 -*-
"""_GH3_eval — 후보 하나를 **슬립까지 포함해** 평가한다 (마라톤H, 2026-08-11).

왜 슬립을 넣나 (사용자 지시 08-11)
  08-11 확인: 발 예비활주를 바꿔 **시뮬 슬립을 3배로 키워도 폐루프 점수는 0.01% 움직인다.**
  즉 현행 점수는 슬립에 눈이 멀어 있고, 55 trial 영상 슬립 전수측정이 아직 트윈에 반영된
  적이 없다. 슬립을 같이 보지 않으면 어떤 축을 고르든 슬립은 계속 방치된다.

무엇을 재나 (전부 낮을수록 좋음, 상관만 높을수록 좋음)
  · 폐루프 6채널 — 관절각 2·각속도 2·토크 2 의 RMSE, 기준선 대비 **채널별 정규화** 평균
  · 슬립 오차   — 시뮬 슬립과 영상 실측 슬립의 차이 RMS [mm]
  · 슬립 상관   — 시행별로 둘이 같이 움직이는가 (+1 이면 완전 동행, 0 이면 무관)
  · 슬립 크기비 — |시뮬 중앙| / |실측 중앙| (1.0 이 정답)

시뮬 슬립 = 접촉점 물질속도(slipv)의 시간적분 [mm]. 구름이면 0 이 되는 양이라 **진짜 미끄럼**이다.
비교 대상 = 영상 실측의 **푸시~이륙 구간 슬립** (폐루프 창이 곧 도약 창이라 대응된다).
★ 하강 구간 슬립은 폐루프 창 밖이라 여기서 못 잰다 — 별도 과제.

CLI: python _GH3_eval.py "FS_CMD_LPF=0.002,0.004;FS_MASS=3.30"   (변수 구분 = 세미콜론)
     python _GH3_eval.py            # 현행 env 그대로 (기준선 확인용)
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["FS_SLIPLOG"] = "1"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")
GATE = "26.04.21"


def _meas():
    M = json.load(io.open(HERE / "_G72_slipall.json", encoding="utf-8"))
    return {(v["sess"], v["trial"]): v["seg"]["푸시~이륙"]["slip"]
            for v in M.values() if v.get("ok") and v.get("seg")}


def run(sess_filter=None):
    """반환: {세션: [채널6...]}, [(시뮬슬립, 실측슬립), ...]"""
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
    if not hasattr(FR, "_GH3_wrapped"):
        _o = FR.rollout_cl_fs
        box = {}

        def wrap(*a, **k):
            L = _o(*a, **k); box["L"] = L; return L
        FR.rollout_cl_fs = wrap
        FR._GH3_box = box
        FR._GH3_wrapped = True
    box = FR._GH3_box
    MS = _meas()
    R = {}; SL = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g:
            continue
        if sess_filter and s not in sess_filter:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            box.clear()
            r = CP.cl_pair(d, seg, g, s)
        except Exception:
            continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        e = lambda a, b, k: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if k in ("q1", "q2") else 1)
        R.setdefault(s, []).append([e(fs[i], mf[k], k) for i, k in enumerate(CH)])
        L = box.get("L")
        if L is not None and "slipv" in L and (s, p.name) in MS:
            tt = np.asarray(L["t"]); dt = float(np.median(np.diff(tt)))
            SL.append((float(np.sum(L["slipv"]) * dt) * 1000.0, MS[(s, p.name)]))
    return R, np.array(SL)


def score(R, SL):
    A = np.array([x for s in R for x in R[s]])
    out = dict(n=len(A), ch=A.mean(0).tolist(),
               gate=(np.array(R[GATE]).mean(0).tolist() if GATE in R else None))
    if len(SL) > 3:
        out["slip_rms"] = float(np.sqrt(np.mean((SL[:, 0] - SL[:, 1]) ** 2)))
        out["slip_r"] = float(np.corrcoef(SL[:, 0], SL[:, 1])[0, 1])
        out["slip_ratio"] = float(np.median(np.abs(SL[:, 0])) / max(np.median(np.abs(SL[:, 1])), 1e-9))
        out["slip_sim"] = float(np.median(SL[:, 0])); out["slip_meas"] = float(np.median(SL[:, 1]))
    return out


def main():
    cfg = {}
    if len(sys.argv) > 1 and sys.argv[1].strip():
        # ★ 구분자는 **세미콜론** — 값 자체에 쉼표가 들어간다 (FS_CMD_LPF="0.002,0.004").
        for it in sys.argv[1].split(";"):
            k, v = it.split("=", 1); cfg[k.strip()] = v.strip()
    import fs_runner as FR
    base_R, base_S = run(); b = score(base_R, base_S)
    print(f"기준선 (현재 env) — {b['n']} trial")
    print(f"  폐루프 채널: " + " ".join(f"{x:.2f}" for x in b["ch"]))
    if "slip_rms" in b:
        print(f"  슬립: 오차RMS {b['slip_rms']:.1f}mm · 상관 {b['slip_r']:+.2f} · "
              f"크기비 {b['slip_ratio']:.2f} (시뮬 중앙 {b['slip_sim']:+.1f} / 실측 {b['slip_meas']:+.1f} mm)")
    if not cfg:
        return
    for k, v in cfg.items():
        os.environ[k] = v
    FR._S2S = None
    R, S = run(); a = score(R, S)
    bb = np.array(b["ch"]); aa = np.array(a["ch"])
    print(f"\n후보 {cfg} — {a['n']} trial")
    NM = ["힙각", "무릎각", "힙속", "무릎속", "힙토크", "무릎토크"]
    print("  채널 변화: " + " ".join(f"{n} {100*(aa[i]/bb[i]-1):+.0f}%" for i, n in enumerate(NM)))
    print(f"  폐루프 종합: {100*(np.mean(aa/bb)-1):+.2f}%")
    if b["gate"] and a["gate"]:
        print(f"  게이트({GATE}): {100*(np.mean(np.array(a['gate'])/np.array(b['gate']))-1):+.2f}%")
    if "slip_rms" in a:
        print(f"  슬립: 오차RMS {b['slip_rms']:.1f} → {a['slip_rms']:.1f}mm · "
              f"상관 {b['slip_r']:+.2f} → {a['slip_r']:+.2f} · "
              f"크기비 {b['slip_ratio']:.2f} → {a['slip_ratio']:.2f}")


if __name__ == "__main__":
    main()
