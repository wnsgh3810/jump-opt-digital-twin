# -*- coding: utf-8 -*-
"""_G12_slipgeo — 발 이동/구름/슬립의 **데이터 바닥(floor)** 계산 (사용자 요청 08-08).

핵심 착상: 이 로봇은 베이스가 **수직 레일**(x 고정) 위에 있고 발은 **지면**(z=0) 위에 있다.
  ⇒ 접지 중 발의 수평 이동량은 **모델 선택이 아니라 측정 각도 (q1,q2)가 기하학적으로 강제**한다.
    (트윈의 접촉 파라미터·마찰계수와 무관 — 강체 기하만으로 결정)
  ⇒ 이것이 **슬립 지표의 바닥**: 어떤 트윈이든 q,dq 를 맞추면 이 이동량이 나와야 한다.
    반대로 sim 이동량이 이보다 작으면 **접촉/기하 오류**이지 마찰 튜닝 문제가 아니다.

구름/슬립 분해 (영상은 롤러 마커 부재로 불가 — `_G_videoslip.json` 명시)
  발은 반경 r=21mm 롤러. 접촉점 접선속도 = ẋ_foot − r·θ̇_foot 가 **진짜 미끄럼**.
  순수 구름이면 0. 여기서는 측정 각도로부터 두 성분을 분해한다 (트윈 개입 없음).

대조 3자
  ① 기하 요구량 (본 스크립트, 데이터만)   ② sim p24 (`_E_slipdecomp_G0_p24.json`)
  ③ 영상 실측 총이동 (`_G_videoslip.json`, 26.07.23/150_2.2_250_3, push −48.04mm)
CLI: python _G12_slipgeo.py
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
from _G10_energy import Reduced, lpf                          # noqa: E402

SIM = HERE / "_E_slipdecomp_G0_p24.json"
VID = HERE / "_G_videoslip.json"


def seg_windows(seg, n):
    """fs_data.segment 경계 → (라벨, i0, i1). 영상 구간 정의와 문자 일치시킨다."""
    return [("desc", seg["i_desc"], seg["i_bot"]),
            ("prehold", seg["i_bot"], seg["i_push"]),
            ("push", seg["i_push"], seg["i_lo"]),
            ("all", seg["i_desc"], seg["i_lo"])]


def main():
    R = Reduced(FR.fs_twin())
    sim = json.load(io.open(SIM, encoding="utf-8")) if SIM.exists() else {}
    vid = json.load(io.open(VID, encoding="utf-8")) if VID.exists() else {}
    print("=" * 132)
    print(f"⓪ 발 롤러 반경 = {R.r*1000:.1f} mm (지름 {2*R.r*1000:.0f} mm) · 영상 교차검증 지름 38~42 mm — 정합")
    print("   ※ 구름/슬립 분해는 **측정 각도만** 사용. 트윈 접촉모델·마찰계수 불개입.")

    print("\n" + "=" * 132)
    print("① 기하가 요구하는 발 이동 [mm] — 측정 (q1,q2) + 강체 + 수직레일이 강제하는 값 (=바닥)")
    print(f"{'세션':<11}{'trial':<19}"
          f" | {'desc 이동':>9}{'구름':>7}{'슬립':>7}"
          f" | {'push 이동':>9}{'구름':>7}{'슬립':>7}{'슬립경로':>9}"
          f" | {'전구간 이동':>11}{'슬립':>7}")
    OUT = {}
    for s, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]; dt = float(np.median(np.diff(t)))
        q1 = lpf(d["q1"], 30.0); q2 = lpf(d["q2"], 30.0)
        v1 = np.gradient(q1, dt); v2 = np.gradient(q2, dt)
        row = {}
        for lab, a, b in seg_windows(seg, len(t)):
            if b - a < 5:
                row[lab] = dict(move=np.nan, roll=np.nan, slip=np.nan, path=np.nan)
                continue
            idx = np.arange(a, b + 1, 2)
            S = [R.MV(q1[i], q2[i]) for i in idx]
            xf = np.array([x["xf"] for x in S])
            vx = np.array([x["dxf"] @ np.array([v1[i], v2[i]]) for x, i in zip(S, idx)])
            vth = np.array([x["dth"] @ np.array([v1[i], v2[i]]) for x, i in zip(S, idx)])
            move = float(xf[-1] - xf[0]) * 1000
            roll = float(np.trapezoid(R.r * vth, dx=2 * dt)) * 1000
            slip = move - roll
            path = float(np.trapezoid(np.abs(vx - R.r * vth), dx=2 * dt)) * 1000
            row[lab] = dict(move=move, roll=roll, slip=slip, path=path)
        OUT[f"{s}/{p.name}"] = row
        print(f"{s:<11}{p.name[:18]:<19}"
              f" | {row['desc']['move']:9.1f}{row['desc']['roll']:7.1f}{row['desc']['slip']:7.1f}"
              f" | {row['push']['move']:9.1f}{row['push']['roll']:7.1f}{row['push']['slip']:7.1f}"
              f"{row['push']['path']:9.1f}"
              f" | {row['all']['move']:11.1f}{row['all']['slip']:7.1f}")

    # ── ② 영상 실측과 직접 대조 (같은 trial) ──
    print("\n" + "=" * 132)
    print("② ★ 영상 실측 대조 — 영상은 **총 이동만** 측정 가능 (롤러 마커 부재). 이동끼리 비교해야 한다")
    tv = vid.get("_meta", {}).get("trial", "")
    key = tv.replace("26.07.23", "26.07.23") if tv else None
    print(f"   영상 trial: {tv} · 스케일 {vid.get('scale',{}).get('scale_mm_per_px',0):.4f} mm/px "
          f"(불확도 {vid.get('scale',{}).get('uncertainty_pct',0):.1f}%)")
    print(f"{'구간':<10}{'영상 실측[mm]':>14}{'기하 요구[mm]':>14}{'sim p24[mm]':>13}{'기하/영상':>10}{'sim/영상':>10}")
    kk = next((k for k in OUT if k.replace("/", "").startswith("26.07.23150_2.2_250_3")), None)
    ks = next((k for k in sim if "26.07.23" in k and "150_2.2_250_3" in k), None)
    for lab in ("desc", "prehold", "push", "all"):
        vlab = {"desc": "desc", "prehold": "prehold", "push": "push", "all": "desc_to_liftoff"}[lab]
        vv = vid.get("segments", {}).get(vlab, {}).get("disp_mm", np.nan)
        gg = OUT[kk][lab]["move"] if kk else np.nan
        ss = sim.get(ks, {}).get(lab if lab != "all" else "all", {}).get("move_mm", np.nan) if ks else np.nan
        print(f"{lab:<10}{vv:14.2f}{gg:14.2f}{ss:13.2f}"
              f"{abs(gg/vv) if vv==vv and abs(vv)>1e-6 else np.nan:10.2f}"
              f"{abs(ss/vv) if vv==vv and abs(vv)>1e-6 else np.nan:10.2f}")

    # ── ③ 전 trial: 기하 요구량 vs sim ──
    print("\n" + "=" * 132)
    print("③ 전 trial 기하 요구량 vs sim p24 — sim 이 기하를 못 따라가면 접촉/기하 오류")
    print(f"{'세션':<11}{'trial':<19}{'push 기하':>10}{'push sim':>10}{'sim/기하':>10}"
          f"{'desc 기하':>10}{'desc sim':>10}{'sim/기하':>10}")
    RT = []
    for k, row in OUT.items():
        ks = next((x for x in sim if x.replace("26.07.", "26.07.").split("/")[-1] == k.split("/")[-1]
                   and x.split("/")[0].replace(".", "_") in k.replace(".", "_")), None)
        if ks is None:
            ks = next((x for x in sim if x.split("/")[-1] == k.split("/")[-1]), None)
        if ks is None:
            continue
        pg = row["push"]["move"]; ps = sim[ks]["push"]["move_mm"]
        dg = row["desc"]["move"]; ds = sim[ks]["desc"]["move_mm"]
        RT.append((pg, ps, dg, ds))
        print(f"{k.split('/')[0]:<11}{k.split('/')[1][:18]:<19}{pg:10.1f}{ps:10.1f}"
              f"{ps/pg if abs(pg)>1e-6 else np.nan:10.2f}{dg:10.1f}{ds:10.1f}"
              f"{ds/dg if abs(dg)>1e-6 else np.nan:10.2f}")
    if RT:
        a = np.array(RT)
        f = lambda x: f"{np.median(x):.2f} [{np.percentile(x,10):.2f}, {np.percentile(x,90):.2f}]"
        print(f"\n   ★ push  sim/기하  {f(a[:,1]/a[:,0])}   (1.0 이면 sim 이 기하를 정확히 따름)")
        print(f"     desc  sim/기하  {f(a[:,3]/a[:,2])}")
    json.dump(OUT, io.open(HERE / "_G12_slipgeo.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G12_slipgeo.json")


if __name__ == "__main__":
    main()
