# -*- coding: utf-8 -*-
"""_G48_guards — **J_G 가 안 보는 두 축의 가드 검사** (마라톤G, 08-08).

왜 필요한가
  이번 마라톤의 심판 J_G 는 ①**CVT 세션(0429)을 제외**하고 ②**τ(토크) 채널을 제외**한다.
  그런데 연구의 최종 목적은 **τ-fidelity** (계획 토크 ≈ 측정 토크) 이고, CVT 는 이 로봇의
  존재 이유다. **J_G 만 보고 승격하면 이 둘이 조용히 망가져 있을 수 있다.**
  (철칙 10 · PLAYBOOK §4 의 Mode A 가드 정신 — 한 지표의 최적을 다른 지표로 검증)

무엇을 재나
  Ⓐ **CVT 가드**: 26.04.29 (l_i = 25.08mm) 10 trial 을 ModeA 로 재생 → q1·q2·dq1·dq2 RMSE.
     p24 기준선 대비 비악화여야 한다.
  Ⓑ **τ 가드 (CL)**: 폐루프 재생(rollout_cl_fs)에서 τ1·τ2 RMSE.
     ModeA 는 측정 토크를 **주입**하므로 τ 를 채점할 수 없다 — τ 는 CL 에서만 의미가 있다.

사용법
  기준선:  python _G48_guards.py p24        (인공층 전부 켠 구 구성 — 환경변수 없이)
  신구성:  <환경변수 세팅 후> python _G48_guards.py new
"""
import os, sys, io, json
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                                          # noqa: E402
import fs_runner as FR                                        # noqa: E402

TAG = sys.argv[1] if len(sys.argv) > 1 else "new"
TK = {60: 0.85, 120: 0.789, 250: 0.656, 500: 0.40}   # 무릎 α 표 (fs_runner 계보와 동일)
REF = HERE / "_G48_ref_p24.json"


def modea_rmse(ft, d, seg, pw, sp):
    """ModeA 재생 → 채널별 RMSE (q:° · dq:rad/s)."""
    tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1]); i0 = int(np.argmax(m))
    t = tt[m] - tt[i0]
    L = FR.rollout_ol_fs_b(ft, t, d["raw1"][m], d["raw2"][m],
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(t[-1] - 0.004), bias1=sp["bias1"],
                           knee_deep=sp["knee_deep"], fade=True)
    if L is None:
        return None
    out = {}
    for k, deg in (("q1", True), ("q2", True), ("dq1", False), ("dq2", False)):
        sim = np.interp(t, L["t"], L[k])
        e = sim - d[k][m]
        out[k] = float(np.sqrt(np.mean((np.degrees(e) if deg else e) ** 2)))
    return out


def cl_rmse(ft, d, seg, pw, g, sp):
    """CL(폐루프) 재생 → τ1·τ2 + q1·q2 RMSE. τ 는 여기서만 채점 가능."""
    tt = d["t"]; m = (tt >= pw[0]) & (tt <= pw[1]); i0 = int(np.argmax(m))
    t = tt[m] - tt[i0]
    need = ("qd1", "qd2", "dqd1", "dqd2")
    if any(d.get(k) is None for k in need):
        return None
    # 게인은 **α 반영 후** 넘긴다 (기존 baseline_fs 계보와 동일 규약): 무릎 kp × TK(kp), kd × 0.20
    gm = (g[0], g[1], g[2] * TK.get(g[2], 0.656), g[3] * 0.20)
    L = FR.rollout_cl_fs(ft, t, d["qd1"][m], d["qd2"][m], d["dqd1"][m], d["dqd2"][m],
                         gm, float(t[-1] - 0.05), two_stage=True,
                         bias1=sp["bias1"], knee_deep=sp["knee_deep"], fade=True,
                         init_meas=(float(d["q1"][i0]), float(d["q2"][i0]),
                                    float(d["dq1"][i0]), float(d["dq2"][i0]),
                                    float(d["raw1"][i0]), float(d["raw2"][i0])))
    if L is None:
        return None
    out = {}
    for k, deg in (("q1", True), ("q2", True)):
        sim = np.interp(t, L["t"], L[k]); e = sim - d[k][m]
        out[k] = float(np.sqrt(np.mean(np.degrees(e) ** 2)))
    # ★ τ 채점: CL 로그의 `s1`/`s2` 는 **PD 가 만들어낸 명령**(raw 단위)이다.
    #   실측 `raw1`/`raw2` 와 같은 단위·같은 의미이므로 직접 비교 가능.
    #   이게 바로 τ-fidelity 그 자체 — "이 궤적을 이 게인으로 쫓으면 로봇이 실제로 낸 만큼의
    #   토크를 트윈도 요구하는가". Nm 환산치도 함께 낸다 (해석용, 현행 토크맵 적용).
    tm = FR._tmap_init(ft["P"], ft["P"].A_PAPER)
    for k, mk, ch, vk in (("tau1", "raw1", 1, "dq1"), ("tau2", "raw2", 2, "dq2")):
        sk = "s1" if ch == 1 else "s2"
        if sk not in L:
            continue
        sim = np.interp(t, L["t"], L[sk])
        meas = np.asarray(d[mk][m], float)
        out[k + "_raw"] = float(np.sqrt(np.mean((sim - meas) ** 2)))
        if tm is not None:
            v = np.asarray(d[vk][m], float)
            vs = np.where(np.abs(v) > 1e-6, v, 1.0)
            f = lambda arr: np.array([tm(float(x), float(w), ch) for x, w in zip(arr, vs)])
            out[k] = float(np.sqrt(np.mean((f(sim) - f(meas)) ** 2)))
        else:
            out[k] = out[k + "_raw"] * 0.682          # a_hat 선형 이득 (구 기준선 해석용)
    return out


def main():
    ft = FR.fs_twin(); SP = FR._sess_params()
    CV, CL = {}, {}
    print("=" * 108)
    print(f"Ⓐ CVT 가드 — 26.04.29 (l_i=25.08mm) ModeA 재생   [tag={TAG}]")
    print(f"{'trial':<26}{'q1[°]':>9}{'q2[°]':>9}{'dq1':>9}{'dq2':>9}")
    for s, p, g, cvt, ho in FD.registry():
        if not cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            r = modea_rmse(ft, d, seg, pw, SP.get(s) or dict(bias1=0.0, knee_deep=None))
        except Exception as ex:
            print(f"{p.name[:25]:<26} ERR {type(ex).__name__}: {ex}")
            continue
        if r is None:
            continue
        CV[p.name] = r
        print(f"{p.name[:25]:<26}{r['q1']:9.3f}{r['q2']:9.3f}{r['dq1']:9.3f}{r['dq2']:9.3f}")
    if CV:
        agg = {k: float(np.mean([v[k] for v in CV.values()])) for k in ("q1", "q2", "dq1", "dq2")}
        print(f"{'평균':<26}{agg['q1']:9.3f}{agg['q2']:9.3f}{agg['dq1']:9.3f}{agg['dq2']:9.3f}")
    else:
        agg = {}

    print("\n" + "=" * 108)
    print(f"Ⓑ τ 가드 — 폐루프(CL) 재생. **τ 는 CL 에서만 채점 가능** (ModeA 는 τ 를 주입)")
    print(f"{'세션/trial':<32}{'q1[°]':>9}{'q2[°]':>9}{'τ1[Nm]':>10}{'τ2[Nm]':>10}")
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            r = cl_rmse(ft, d, seg, pw, g, SP.get(s) or dict(bias1=0.0, knee_deep=None))
        except Exception as ex:
            print(f"{(s+'/'+p.name)[:31]:<32} ERR {type(ex).__name__}: {str(ex)[:40]}")
            continue
        if r is None:
            continue
        CL[f"{s}/{p.name}"] = r
        print(f"{(s+'/'+p.name)[:31]:<32}{r.get('q1',np.nan):9.3f}{r.get('q2',np.nan):9.3f}"
              f"{r.get('tau1',np.nan):10.3f}{r.get('tau2',np.nan):10.3f}")
    aggc = {k: float(np.nanmean([v[k] for v in CL.values() if k in v]))
            for k in ("q1", "q2", "tau1", "tau2", "tau1_raw", "tau2_raw")} if CL else {}
    if aggc:
        print(f"{'평균':<32}{aggc['q1']:9.3f}{aggc['q2']:9.3f}{aggc['tau1']:10.3f}{aggc['tau2']:10.3f}")

    res = dict(tag=TAG, cvt=CV, cvt_agg=agg, cl=CL, cl_agg=aggc)
    if TAG == "p24" or not REF.exists():
        json.dump(res, io.open(REF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n★ 기준(p24) 저장: {REF.name}")
    else:
        ref = json.load(io.open(REF, encoding="utf-8"))
        print("\n" + "=" * 108)
        print("★★ p24 대비 (음수 = 개선)")
        print(f"{'축':<20}{'p24':>10}{'신':>10}{'변화':>10}")
        for k in ("q1", "q2", "dq1", "dq2"):
            if k in agg and k in ref.get("cvt_agg", {}):
                a, b = ref["cvt_agg"][k], agg[k]
                print(f"{'CVT '+k:<20}{a:10.3f}{b:10.3f}{100*(b/a-1):+9.1f}%")
        for k in ("q1", "q2", "tau1", "tau2", "tau1_raw", "tau2_raw"):
            if k in aggc and k in ref.get("cl_agg", {}):
                a, b = ref["cl_agg"][k], aggc[k]
                print(f"{'CL '+k:<20}{a:10.3f}{b:10.3f}{100*(b/a-1):+9.1f}%")
    json.dump(res, io.open(HERE / f"_G48_guards_{TAG}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n저장: _G48_guards_{TAG}.json")


if __name__ == "__main__":
    main()
