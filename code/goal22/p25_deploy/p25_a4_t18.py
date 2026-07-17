# -*- coding: utf-8 -*-
"""p25_a4_t18 — P25 A-iv 추가: 토크 제약 강화판 (축토크 18 Nm) iLQR.

사용자 추가 지시 (07-17): 공급 천장을 raw ±35.5 → **raw ±31.1771**로 강화
(a_hat 운동방향 가지에서 정확히 18.00 Nm 축토크 — 구동기 정격 근거).
p25_a4_ilqr의 전 기계(스텝 미러·mjd_transitionFD 체인·box-DDP·V_CAP)를 그대로 쓰고
클립만 교체: R19.CLIP monkeypatch (substep/rollout_ol/settle/backward/forward가 전부
호출 시점에 R19.CLIP을 읽으므로 한 곳 패치로 플랜트·박스·기록이 일관 변경).
주의: TW.twin()의 CLIP==35.5 assert가 있어 twin 초기화 **후** 패치한다 (트윈 물리 불변 —
클립은 커맨드층 파라미터).

시드: ① 35.5 최적해(p25_a4_ilqr.npz u_nodes)를 ±31.1771로 사영 ② cl_cma raw 사영
③ crouch-hold. 선발 = score(h_plan − PEN_W·env_pen), 35.5판과 동일 잣대.
산출: p25_a4_ilqr_t18.npz (동일 스키마 + h_plan 키) + p25_a4_results_t18.json.
저장 후 max|raw| ≤ 31.18 검증.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ["PYTHONIOENCODING"] = "utf-8"

import p25_a4_ilqr as IL     # 첫 import 가 p25_a_twin 경유 env 플래그 설정
import p25_a_twin as TW

import sys
import time
from pathlib import Path

import numpy as np

import p19_run as R19
import safe

HERE = Path(__file__).parent
CLIP18 = 31.1771             # a_hat 운동방향 가지 = 18.00 Nm 축토크인 raw


def main():
    safe.utf8_console()
    t00 = time.time()
    log = lambda s: print(s, flush=True)
    log("=== p25_a4_t18 — iLQR(box-DDP), 공급 천장 raw ±31.1771 (축 18 Nm) ===")
    tw = TW.twin()                       # CLIP=35.5 assert는 여기서 통과
    # 검증: 31.1771 raw ≒ 18.00 Nm (운동방향 가지, |v| 무관 — sgn만 개입)
    s_pos = TW._ahat_s(tw["P"].A_PAPER, CLIP18, 1.0)
    s_neg = TW._ahat_s(tw["P"].A_PAPER, -CLIP18, -1.0)
    log(f"ahat(±{CLIP18}, 운동방향) = {s_pos:.4f} / {s_neg:.4f} Nm (기대 ±18.00)")
    assert abs(s_pos - 18.0) < 0.01 and abs(s_neg + 18.0) < 0.01, "18 Nm 환산 불일치"
    R19.CLIP = CLIP18                    # ★ monkeypatch — 이후 전 경로 일관 적용
    cx = IL.ctx_of(tw)
    M = int(round(IL.DT_C / cx["dt"]))
    N = int(round(IL.T_HOR / IL.DT_C))
    st = TW.settle_state(tw, *tw["q0"])
    z0 = dict(qpos=st["qpos"], qvel=st["qvel"], c1f=st["c1f"], c2f=st["c2f"])
    log(f"init [{time.time() - t00:.0f}s] CLIP={R19.CLIP} M={M} N={N}")

    # ── 시드 ──
    seeds = [("crouch", IL.seed_crouch(st, N))]
    try:
        z = np.load(HERE / "p25_a4_ilqr.npz")
        u35 = np.asarray(z["u_nodes"], float)
        if u35.shape[0] < N:                       # stance 케이스 방어 (0 패드)
            u35 = np.vstack([u35, np.zeros((N - u35.shape[0], 2))])
        seeds.insert(0, ("proj35(p25_a4_ilqr.npz)", np.clip(u35[:N], -CLIP18, CLIP18)))
    except Exception as e:
        log(f"35.5 최적해 시드 불가: {e}")
    for U_w, name in IL.seed_warm(N):
        if "cl_cma" in name:
            seeds.append((f"proj({name})", np.clip(U_w, -CLIP18, CLIP18)))

    best = None
    runs = []
    for tag, U0 in seeds:
        r0 = IL.rollout(cx, z0, U0, M, store=False)
        log(f"[{tag}] seed cost={r0['cost'] if r0 else float('nan'):+.5f}")
        res = IL.ilqr(cx, z0, U0, M, tag, log)
        Lg = IL.record_final(cx, tw, st, res["U"], M)
        res["tag"] = tag
        res["h_plan"] = TW.apex_of(Lg) if Lg is not None else float("nan")
        res["stats"] = TW.stats_of(tw, Lg, t_push=IL.T_HOR) if Lg is not None else {}
        res["score"] = res["h_plan"] - TW.PEN_W * res["stats"].get("env_pen", 9e9)
        res["horizon"] = IL.T_HOR
        log(f"[{tag}] h_plan={res['h_plan']:.4f}m proxy={res['proxy']:.4f}m "
            f"score={res['score']:+.4f}")
        runs.append(res)
        if best is None or res["score"] > best["score"]:
            best = res

    # ── 산출물 ──
    Lg = IL.record_final(cx, tw, st, best["U"], M)
    mraw = float(max(np.abs(Lg["raw1"]).max(), np.abs(Lg["raw2"]).max()))
    log(f"BEST={best['tag']} h_plan={best['h_plan']:.4f}m  max|raw|={mraw:.4f} "
        f"({'OK' if mraw <= 31.18 else 'FAIL'} ≤ 31.18)")
    assert mraw <= 31.18, "클립 검증 실패"
    extra = dict(qd1=Lg["q1"], qd2=Lg["q2"], dqd1=Lg["dq1"], dqd2=Lg["dq2"],
                 u_nodes=best["U"], t_nodes=np.arange(best["U"].shape[0]) * IL.DT_C,
                 dt_ctrl=np.array(IL.DT_C), horizon=np.array(best["horizon"]),
                 h_plan=np.array(best["h_plan"]), clip_raw=np.array(CLIP18))
    TW.save_npz(HERE / "p25_a4_ilqr_t18.npz", Lg, extra=extra)
    out = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"), method="ilqr_boxddp_mjd_transitionFD",
        variant="t18", note=("공급 천장 raw ±31.1771 (=a_hat 운동방향 18.00 Nm) — "
                             "R19.CLIP monkeypatch로 플랜트·박스·기록 일관 적용. "
                             "시드=35.5 최적해 사영 외."),
        status="OK",
        clip_raw=CLIP18, ahat_at_clip=[float(s_pos), float(s_neg)],
        config_delta=dict(base="p25_a4_results.json", clip=CLIP18),
        runs=[{k: v for k, v in r.items() if k != "U"} for r in runs],
        best=dict(tag=best["tag"], h_plan=best["h_plan"], proxy=best["proxy"],
                  score=best["score"], iters=best["iters"], wall_s=best["wall_s"],
                  stats=best["stats"]),
        h_plan=best["h_plan"], max_abs_raw=mraw,
        npz="p25_a4_ilqr_t18.npz", wall_total_s=float(time.time() - t00))
    safe.atomic_json_write(HERE / "p25_a4_results_t18.json", out)
    log(f"saved p25_a4_ilqr_t18.npz + p25_a4_results_t18.json "
        f"[{(time.time() - t00) / 60:.1f}m]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
