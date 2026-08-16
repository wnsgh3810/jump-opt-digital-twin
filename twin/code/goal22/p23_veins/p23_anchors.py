# -*- coding: utf-8 -*-
"""p23_anchors — P23 Phase 0c: 신규 v6 성분 (CL_FF / OLDQ_FF / AIR) 앵커·바닥 산정.

절차:
  1. 재구성 바닥 (knee-only vs knee+hip FF) → 낮은 쪽으로 FF 주입 프로토콜 동결
  2. dq2 노이즈 바닥 (0422/0319tau) + AIR 노이즈 바닥
  3. 용접 베이스 settle 검증 (P19 모델)
  4. P19(x19_vec)·p22b(rows[16]) 두 벡터에 대해 CL_FF/OLDQ_FF/AIR 산출
  5. p23_anchors.json 저장 (safe.atomic_json_write) + 표 출력

앵커 = P19 값 (v6 정규화 기준: 성분̂ = 성분/P19). p22b 값은 현행 챔피언 진단용.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import p23_runners as RN
import safe

OUT = HERE / "p23_anchors.json"


def main():
    safe.utf8_console()
    t0 = time.time()
    print("=== p23_anchors — Phase 0c: 신규 v6 성분 앵커·바닥 (P19 vs p22b) ===", flush=True)
    RN.ensure_init()
    print(f"winit+fix0421 done [{time.time() - t0:.0f}s]", flush=True)

    # ── 1) FF 주입 프로토콜 결정 (재구성 바닥, 시뮬 없음) ──
    fk_sess, fk_per = RN.recon_floor(ff_hip=False)
    fh_sess, fh_per = RN.recon_floor(ff_hip=True)
    print("\n[1] 재구성 바닥 (측정 (q,dq)→명령모델 vs 측정 τ, gap_v3 동형)", flush=True)
    print(f"    {'session':14s} {'knee-only':>10s} {'knee+hip':>10s}", flush=True)
    for ds in RN.FF_SESS:
        print(f"    {ds:14s} {100*fk_sess[ds]:9.1f}% {100*fh_sess[ds]:9.1f}%", flush=True)
    print(f"    {'MEAN':14s} {100*fk_sess['MEAN']:9.1f}% {100*fh_sess['MEAN']:9.1f}%", flush=True)
    ff_hip = fh_sess["MEAN"] < fk_sess["MEAN"]
    proto = "knee+hip" if ff_hip else "knee_only"
    print(f"    ==> FF 주입 프로토콜 동결: {proto} (세션평균 바닥 낮은 쪽)", flush=True)
    floors_chosen = fh_sess if ff_hip else fk_sess

    # ── 2) 노이즈 바닥 ──
    dqfl = RN.dq2_noise_floor()
    airfl = RN.air_noise_floor()
    print("\n[2] 노이즈 바닥", flush=True)
    for ds, r in dqfl.items():
        ns = "/".join(str(p["n"]) for p in r["per_trial"])
        print(f"    dq2 noise {ds:14s} = {r['mean']:.3f} rad/s (저속 샘플 n={ns})", flush=True)
    print(f"    AIR noise floor = {airfl['floor']:.4f} "
          f"(sig_q2 {airfl['sig_q2_mean']:.5f} rad + 0.1*sig_dq2 {airfl['sig_dq2_mean']:.3f} rad/s, "
          f"{len(airfl['per_cycle'])} cycles)", flush=True)

    # ── 3) 벡터 준비 + 용접 검증 ──
    import p22_eval as E
    import p21_cma as C
    vecs = {"P19": E.x19_vec(), "p22b": RN.x22b_vec()}
    x32, sp = C.x32_of(vecs["P19"])
    model_w, _ = RN.build_flip_welded(x32, vecs["P19"][1], sp)
    wv = RN.verify_weld(model_w)
    print(f"\n[3] weld 검증: nq={wv['nq']} base_z0={wv['base_z0']:.6f} "
          f"base_z1={wv['base_z1']:.6f} foot_min_z={wv['foot_min_z']:.3f} "
          f"-> {'PASS' if wv['ok'] else 'FAIL'}", flush=True)
    if not wv["ok"]:
        print("weld 검증 실패 — 저장하지 않고 종료", flush=True)
        sys.exit(1)

    # ── 4) 성분 산출 ──
    res = {}
    for tag, v in vecs.items():
        print(f"\n[4] {tag} 평가 (tm={v[14]*1e3:.2f}ms c_qs={v[15]:.3f} "
              f"v0={v[16]:.1f} pre30={v[19]:.2f})", flush=True)
        clf, clf_rows = RN.cl_ff(v, ff_hip=ff_hip)
        for r in clf_rows:
            print(f"    CL_FF  {r['ds']}/{r['sub']}: g={100*r['g']:.1f}% q2={r['q2']:.3f}"
                  + (" CRASH" if r.get("crash") else ""), flush=True)
        olq, olq_rows = RN.oldq_ff(v)
        for r in olq_rows:
            print(f"    OLDQ_FF {r['ds']}/{r['sub']}: dq2 RMSE={r['rmse']:.3f} "
                  f"h_sim={r['h_sim']:.3f} h_real={r['h_real']:.3f}"
                  + (" CRASH" if r.get("crash") else ""), flush=True)
        air, air_rows = RN.air_score(v, pre30_on=False)          # ★ 동결 정의 (pre30=0)
        airp, airp_rows = RN.air_score(v, pre30_on=True)         # 진단 (블랭킷 pre30 반증)
        ncr = sum(r["crash"] for r in air_rows)
        print(f"    AIR = {air:.4f} (pre30=0, 동결 정의; crash {ncr}/14) | "
              f"진단 AIR(pre30 ON) = {airp:.4f} (폭주 반증용)", flush=True)
        for r in air_rows:
            print(f"      cyc{r['cyc']:02d} rq={r['rq']:.4f} rdq={r['rdq']:.3f} "
                  f"score={r['score']:.4f}" + (" CRASH" if r["crash"] else ""), flush=True)
        res[tag] = dict(vec=[float(a) for a in v],
                        CL_FF=clf, CL_FF_rows=clf_rows,
                        OLDQ_FF=olq, OLDQ_FF_rows=olq_rows,
                        AIR=air, AIR_rows=air_rows,
                        AIR_diag_pre30on=airp, AIR_diag_pre30on_rows=airp_rows)
        print(f"    [{tag}] CL_FF 0422={100*clf['jump_0422']:.1f}% "
              f"0319tau={100*clf['jump_0319tau']:.1f}% | "
              f"OLDQ_FF 0422={olq['jump_0422']:.3f} 0319tau={olq['jump_0319tau']:.3f} | "
              f"AIR={air:.4f} [{(time.time()-t0)/60:.1f}m]", flush=True)

    # ── 5) 요약 표 + 저장 ──
    print("\n=== 앵커 표 (P19 = v6 정규화 기준) ===", flush=True)
    print(f"{'component':22s} {'P19':>10s} {'p22b':>10s} {'p22b/P19':>9s} {'floor':>10s}", flush=True)
    lines = []
    for ds in RN.FF_SESS:
        a, b = res["P19"]["CL_FF"][ds], res["p22b"]["CL_FF"][ds]
        lines.append((f"CL_FF[{ds}]", a, b, floors_chosen[ds]))
    for ds in RN.FF_SESS:
        a, b = res["P19"]["OLDQ_FF"][ds], res["p22b"]["OLDQ_FF"][ds]
        lines.append((f"OLDQ_FF[{ds}]", a, b, dqfl.get(ds, {}).get("mean", float("nan"))))
    lines.append(("AIR", res["P19"]["AIR"], res["p22b"]["AIR"], airfl["floor"]))
    for name, a, b, fl in lines:
        print(f"{name:22s} {a:10.4f} {b:10.4f} {b/a:9.3f} {fl:10.4f}", flush=True)

    out = dict(
        gen=datetime.now().strftime("%Y-%m-%d %H:%M"),
        note=("P23 Phase 0c 앵커/바닥. 앵커=P19(x19_vec=p22_rebase 구성, fix0421 적용). "
              "p22b=p22_gate_check rows[16] (NSGA i=29). CL_FF: cl_run20_ff, "
              "alphas=[1,1,1,1], Cd=0, o=0, preload=v[19], 마스크=GRF 이륙+0.1s. "
              "OLDQ_FF: p22_eval.a_full (o=0, pre30=v[19]), 전체 기록 창. "
              "AIR: 용접 베이스(base z=1m, bz joint 제거), 14사이클, "
              "AIR=mean[rmse(q2)+0.1*rmse(dq2)], ★동결 정의=pre30 미가산 "
              "(블랭킷 pre30은 공중에서 크랭크 폭주=지표 포화, 실데이터 반증 — "
              "AIR_diag_pre30on에 반증 수치 보존). "
              "0319tau CL은 게인 회귀 기반(gain-uncertain) — 바닥이 이를 반영. "
              "주의: 0422 재구성 '바닥'(>100%)은 하한이 아니라 라벨게인 명령모델 "
              "불일치 진단 (실효 kd≈0, held-out 0324와 동일 이상 — floor2.log 참조)."),
        ff_protocol=dict(
            chosen=proto,
            rule="재구성 바닥 세션평균 낮은 쪽 (0422는 tdes1 rms~6.3Nm 실재 기록)",
            floor_knee_only=fk_sess, floor_knee_hip=fh_sess,
            per_trial_knee_only=fk_per, per_trial_knee_hip=fh_per),
        floors=dict(
            CL_FF_recon=floors_chosen,
            dq2_noise=dqfl,
            AIR_noise=airfl,
            caveat_0319tau=("게인=V2+ff 회귀 (PID.txt 없음), hip kd<0 → 0 클램프 — "
                            "CL_FF[0319tau]는 gain-uncertain (바닥 수치가 그 몫 포함)")),
        weld_verify=wv,
        anchors=res)
    safe.atomic_json_write(OUT, out)
    print(f"\nsaved {OUT.name} [{(time.time() - t0) / 60:.1f}m]", flush=True)


if __name__ == "__main__":
    main()
