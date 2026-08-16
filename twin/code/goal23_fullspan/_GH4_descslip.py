# -*- coding: utf-8 -*-
"""_GH4_descslip — **하강 구간** 슬립을 시뮬에서 재고 영상 실측과 맞댄다 (마라톤H, 08-11).

왜 별도 스크립트인가
  정본 비교 창(`fs_data.plot_window`)은 원본 xlsx 스팬 = **도약 구간**이다. 하강은 그 앞이라
  폐루프 보드가 못 본다. 그런데 영상 실측 슬립의 **큰 몫이 하강에 있다**
  (세션 중앙 −13 ~ +7mm, 도약은 −42 ~ +7mm 이지만 대부분 ±3mm).
  ⇒ 하강까지 도는 롤아웃을 따로 돌려야 한다. `i_desc` 부터 이륙까지 (fs_cvt 의 CL 과 같은 창).

★ 이건 **진단**이지 채점 그래프가 아니다 — 그래프 창 규약(plot_window)은 그림에 적용되고,
  여기서는 그림을 그리지 않는다. 채점에 쓰려면 지표를 따로 선언할 것.

★ 마찰 관련 확정 (08-11): `FS_MU` 는 FS_PRESLIDE 가 켜져 있으면 **아무 효과가 없다.**
  `_PreSlide` 가 매 스텝 `model.geom_friction[발/바닥][0]` 을 직접 덮어쓰기 때문
  (점착 중 mu_hold=2.0, 활주 중 mu_k). 슬립을 조절하는 노브는 FS_MU 가 아니라
  **FS_PRESLIDE 의 mu_s/mu_k** 다.

CLI: python _GH4_descslip.py ["FS_PRESLIDE=0.86,0.85,0.02,1.0"]
"""
import os, sys, io, json, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["FS_SLIPLOG"] = "1"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))


def meas():
    M = json.load(io.open(HERE / "_G72_slipall.json", encoding="utf-8"))
    out = {}
    for v in M.values():
        if v.get("ok") and v.get("seg"):
            g = v["seg"]
            out[(v["sess"], v["trial"])] = (g["하강전반"]["slip"] + g["하강후반"]["slip"],
                                            g["푸시~이륙"]["slip"])
    return out


def run():
    import fs_data as FD, fs_runner as FR, fs_compare_plot as CP
    MS = meas()
    G = collections.defaultdict(list)
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g or (s, p.name) not in MS:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            ft = FR.fs_twin()
            sp = FR.sess_params(s)
            i0 = max(0, seg["i_desc"] - 5)             # 하강 시작 (fs_cvt CL 과 동일 규약)
            t = d["t"][i0:] - d["t"][i0]
            t_end = seg["t_lo"] - d["t"][i0]           # 이륙까지
            L = FR.rollout_cl_fs(
                ft, t, CP.sh(d["qd1"][i0:]), CP.sh(d["qd2"][i0:]),
                CP.sh(d["dqd1"][i0:]), CP.sh(d["dqd2"][i0:]),
                tuple(g), t_end, two_stage=True, bias1=sp["bias1"],
                knee_deep=sp["knee_deep"], fade=True, taulim=None,
                vdes_ff=FD.vdes_applied(s))
        except Exception as ex:
            print(f"  ✗ {s}/{p.name}: {type(ex).__name__} {str(ex)[:50]}", flush=True); continue
        if L is None or "slipv" not in L:
            continue
        tt = np.asarray(L["t"]); sv = np.asarray(L["slipv"])
        dt = float(np.median(np.diff(tt)))
        # 하강 = 창 시작 ~ 도약 시작.  도약 시작 = seg["push"] 첫 True 의 시각
        pm = seg["push"][i0:][:len(t)]
        t_push = float(t[pm][0]) if pm.sum() else t_end
        md_ = tt < t_push
        G[s].append((float(np.sum(sv[md_]) * dt) * 1000.0,      # 시뮬 하강
                     float(np.sum(sv[~md_]) * dt) * 1000.0,     # 시뮬 도약
                     MS[(s, p.name)][0], MS[(s, p.name)][1]))   # 실측 하강, 도약
    return G


def main():
    if len(sys.argv) > 1:
        for it in sys.argv[1].split(";"):
            k, v = it.split("=", 1); os.environ[k.strip()] = v.strip()
    G = run()
    if not G:
        raise SystemExit("결과 없음")
    print("\n하강 + 도약 슬립 — 시뮬 vs 영상 실측 [mm]\n")
    print(f"{'세션':10s} {'n':>2s} | {'하강 시뮬':>9s} {'하강 실측':>9s} | {'도약 시뮬':>9s} {'도약 실측':>9s}")
    A = []
    for s in sorted(G):
        a = np.array(G[s], float); A += list(a)
        print(f"{s:10s} {len(a):2d} | {np.median(a[:,0]):+9.1f} {np.median(a[:,2]):+9.1f} "
              f"| {np.median(a[:,1]):+9.1f} {np.median(a[:,3]):+9.1f}")
    A = np.array(A)
    for i, nm in ((0, "하강"), (1, "도약")):
        j = i + 2
        r = np.corrcoef(A[:, i], A[:, j])[0, 1]
        print(f"\n{nm}: 시뮬 |중앙| {np.median(np.abs(A[:,i])):.1f}mm · 실측 |중앙| "
              f"{np.median(np.abs(A[:,j])):.1f}mm · 상관 {r:+.2f} · 차이RMS "
              f"{np.sqrt(np.mean((A[:,i]-A[:,j])**2)):.1f}mm")


if __name__ == "__main__":
    main()
