# -*- coding: utf-8 -*-
"""p25_a_merge — Phase A 방법별 결과 (p25_a_res_{ol,mppi,cl}.json) → p25_a_results.json.

p25_a_results.json 스키마 (Phase D 소비 규약):
  golden      : 배선 검증 (p25_a_golden.json 요약 — ahat/cl_mirror/replay PASS)
  task        : 공통 태스크 동결값 (시작자세·포락선·천장·게인·호라이즌)
  baselines   : 실측 최고 0.98 m · G20 NLP 1.063 m
  methods[m]  : h_plan · stats(피크 raw/Nm/dq, 천장 점유율, 포락선 위반, 이지 시각) ·
                evals/crash · params(매듭) · npz 경로
  npz 스키마  : t / q1 q2 dq1 dq2 / raw1 raw2 (τ* raw) / tau1_nm tau2_nm (τ* Nm) /
                bz / grf (+ qd1 qd2 dqd1 dqd2 + knots_*, 방법별) —
                ol/mppi는 t=0부터 (settle 캐시 제외), cl은 t=-0.4(settle 포함)부터.
"""
import time
from pathlib import Path
import sys

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "bench"))
import safe

FILES = dict(ol_cma="p25_a_res_ol.json", mppi="p25_a_res_mppi.json",
             cl_cma="p25_a_res_cl.json")
BASE = dict(h_real_best=0.98, h_g20_nlp=1.063,
            note="실측 최고 0.98 m (0602) · G20(P19 트윈) NLP apex 1.063 m — "
                 "p24a 트윈 재산정이 이 마라톤 베이스라인")


def main():
    safe.utf8_console()
    g = safe.read_json(HERE / "p25_a_golden.json")
    methods = {}
    for m, fn in FILES.items():
        p = HERE / fn
        if p.exists():
            methods[m] = safe.read_json(p)
        else:
            print(f"WARN: {fn} 없음 — 건너뜀", flush=True)
    out = dict(
        gen=time.strftime("%Y-%m-%d %H:%M"),
        phase="P25 Phase A",
        twin="fourbar_p24a_candidate.json (SPRING_GATED+RISE_GATED+HIP_LAW+REFIT, "
             "l_i=30 flip, 전 플랜트 층 활성)",
        golden=dict(pass_=g["golden"]["pass"],
                    replay_0602_mean=g["golden"]["replay_0602_mean"],
                    cl_mirror_maxdiff=g["golden"]["cl_mirror_maxdiff"]),
        task=dict(start_q=g["q0"], start_trial=g["seed_trial"], horizon_s=0.6,
                  push_s=0.35, clip_raw=35.5, envelope_p10=g["env"],
                  gains_cl=[150.0, 2.2, 500.0, 4.0], dt=g["dt"],
                  objective="max base-z apex (t>0 절대 bz — h_real 직접 비교 규약)",
                  slip="수직 레일 1-DOF 베이스 — 수평 DOF 없음, 미끄럼 제약 자동 충족"),
        baselines=BASE,
        methods=methods)
    safe.atomic_json_write(HERE / "p25_a_results.json", out)
    print("=== p25_a_results.json ===", flush=True)
    print(f"{'method':8s} {'h_plan':>7s} {'pk_raw1':>8s} {'pk_raw2':>8s} "
          f"{'pk_dq1':>7s} {'pk_dq2':>7s} {'ceil2':>6s} {'evals':>7s} {'crash':>6s}",
          flush=True)
    for m, r in methods.items():
        s = r["stats"]
        ev = r.get("evals", r.get("samples", 0) * r.get("replans", 0))
        cr = r.get("crashes", r.get("crash_samples", 0))
        print(f"{m:8s} {r['h_plan']:7.4f} {s['peak_raw1']:8.1f} {s['peak_raw2']:8.1f} "
              f"{s['peak_dq1']:7.2f} {s['peak_dq2']:7.2f} {s['ceil_frac_raw2']:6.2f} "
              f"{ev:7d} {cr:6d}", flush=True)
    print(f"baselines: real 0.98 m · G20 NLP 1.063 m", flush=True)


if __name__ == "__main__":
    main()
