# -*- coding: utf-8 -*-
"""_GH2_screen2 — 마라톤H 2차 스크리닝: 남은 축 전부 (2026-08-11).

1차(_GH1_screen)에서 23축을 훑었다. 여기서는 **나머지**를 본다.
기준선은 이제 **H1_260811** (= G26_0811 + FS_CMD_LPF=0.002, 08-11 등재).

★ 1차와 다른 점 ①: 일부 축은 **다른 축과 짝으로만** 의미가 있다.
  대체 토크맵(FS_TCAPS/TDCAPV/TFV/TENV/TFRIC/TMODEL)은 각각 FS_TMAP 을 같이 바꿔야 켜진다.
  그래서 이 스크립트는 **여러 env 를 한 묶음으로** 시험한다.

★ 1차와 다른 점 ②: 이 측정 경로(cl_pair)가 **인자로 덮어쓰는 축**은 아예 뺀다 —
  FS_FADE/FS_TAULIM/FS_VDES0/FS_LIMRAW/FS_LIM2NM/FS_MA_INIT 등은 rollout 호출부에서
  명시 인자로 넘어가므로 env 를 바꿔도 무력이다 (1차에서 "변화 0.00%" 로 확인된 부류).
  인공층 축(FS_RISE_*/FS_DEEP_*/FS_BIAS_*)도 해당 층이 꺼져 있어(NOSUPP/NODEEP/NOBIAS) 무력.

★ 사용자 승인 08-11: 총질량 **3.34 까지 허용** (실측 3.26~3.30 밖이지만 시험은 해본다).

CLI: python _GH2_screen2.py [묶음이름,...]
"""
import os, sys, io, json, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import safe                                                      # noqa: E402

SESS = os.environ.get("GH2_SESS", "26.04.21,26.04.24,26.06.02,26.07.22,26.07.24,26.07.27").split(",")
OUT = HERE / "_GH2_screen2.json"
CH = ("q1", "q2", "dq1", "dq2", "a1", "a2")

# 이름 → {env: 값}. 기준선(현행 H1)은 자동.
TRIALS = {
    # ── 힙 직렬탄성·마찰 (모델 빌드 축) ──
    "힙스프링 ks=100":      {"FS_KS_HIP": "100"},
    "힙스프링 ks=250":      {"FS_KS_HIP": "250"},
    "힙스프링 ks=450":      {"FS_KS_HIP": "450"},
    "힙2단 무르게":         {"FS_HSPR": "70,240,9"},
    "힙2단 단단히":         {"FS_HSPR": "130,430,9"},
    "힙모터 마찰 ↓":        {"FS_HIPM_FL": "0.12"},
    "힙모터 마찰 ↑":        {"FS_HIPM_FL": "0.36"},
    # ── 무릎 모터 마찰·감쇠 (공중 동정 계보) ──
    "무릎모터 감쇠 0.05":   {"FS_KNEEM_DAMP": "0.05"},
    "무릎모터 감쇠 0.20":   {"FS_KNEEM_DAMP": "0.20"},
    "무릎모터 마찰 0.10":   {"FS_KNEEM_FL": "0.10"},
    "무릎모터 마찰 0.30":   {"FS_KNEEM_FL": "0.30"},
    # ── 기어박스 효율 (모터링 사분면) ──
    "기어효율 0.92":        {"FS_ETA": "0.92"},
    "기어효율 0.85":        {"FS_ETA": "0.85"},
    # ── 전압 포락선 천장 ──
    "전압천장 25,0.5":      {"FS_VCEIL": "25,0.5"},
    "전압천장 30,0.3":      {"FS_VCEIL": "30,0.3"},
    # ── 대체 토크맵 (FS_TMAP 을 같이 바꿔야 켜진다) ──
    "맵: 캡 스케일 0.9":    {"FS_TMAP": "canon_capS", "FS_TCAPS": "0.9,3.8,2.6"},
    "맵: 캡 스케일 1.1":    {"FS_TMAP": "canon_capS", "FS_TCAPS": "1.1,3.8,2.6"},
    "맵: 속도의존 캡":      {"FS_TMAP": "canon_capv", "FS_TDCAPV": "3.8,0.05,2.6,0.03"},
    "맵: 속도의존 캡 강":   {"FS_TMAP": "canon_capv", "FS_TDCAPV": "3.8,0.12,2.6,0.08"},
    "맵: 포락선(env)":      {"FS_TMAP": "canon_env", "FS_TENV": "20,0.6"},
    "맵: 마찰형(fric)":     {"FS_TMAP": "canon_fric", "FS_TFRIC": "0.3,0.30,0.0,2.0"},
    "맵: 순수 선형 1.24":   {"FS_TMAP": "model", "FS_TMODEL": "lin:1.24"},
    "맵: 포화 2차":         {"FS_TMAP": "model", "FS_TMODEL": "sat:1.30,0.006"},
    "맵: 구간분리(pw)":     {"FS_TMAP": "model", "FS_TMODEL": "pw:1.30,11.5,0.85"},
    # ── 질량 (사용자 승인으로 실측 밖까지) ──
    "질량 3.30":            {"FS_MASS": "3.30"},
    "질량 3.34":            {"FS_MASS": "3.34"},
    "질량 3.38":            {"FS_MASS": "3.38"},
    # ── 질량분포 (형식 = 바디이름=값) ──
    "허벅지 질량 ↓":        {"FS_MBODY": "thigh=0.87"},
    "허벅지 질량 ↑":        {"FS_MBODY": "thigh=0.96"},
    "크랭크 질량 ↓":        {"FS_MBODY": "crank=0.40"},
    "크랭크 질량 ↑":        {"FS_MBODY": "crank=0.50"},
    "허벅지 관성 ↓":        {"FS_IBODY": "thigh=0.85"},
    "허벅지 관성 ↑":        {"FS_IBODY": "thigh=1.15"},
    "종아리 관성 ↓":        {"FS_IBODY": "calf=0.85"},
    "종아리 관성 ↑":        {"FS_IBODY": "calf=1.15"},
    "허벅지 무게중심 ↓":    {"FS_COMZ": "thigh=-0.008"},
    "허벅지 무게중심 ↑":    {"FS_COMZ": "thigh=0.008"},
    # ── 커맨드 지연 미세 (현행 0.002 주변) ──
    "지연 0.0015":          {"FS_CMD_LPF": "0.0015"},
    "지연 0.0025":          {"FS_CMD_LPF": "0.0025"},
}


def board():
    import fs_data as FD, fs_compare_plot as CP
    F = []
    for s, p, g, cvt, ho in FD.registry():
        if cvt or not g or s not in SESS:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
            d["_sess"] = s; d["_fold"] = p
            r = CP.cl_pair(d, seg, g, s)
        except Exception:
            continue
        if r is None:
            continue
        t, (mo, mf), old, fs, m, cmd, _ = r
        e = lambda a, b, k: float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2))) * \
            (180 / np.pi if k in ("q1", "q2") else 1)
        F.append([e(fs[i], mf[k], k) for i, k in enumerate(CH)])
    F = np.array(F)
    return F if len(F) and np.all(np.isfinite(F)) else None


def main():
    want = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    import fs_runner as FR
    keys = sorted({k for v in TRIALS.values() for k in v})
    saved = {k: os.environ.get(k) for k in keys}

    def restore():
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        FR._S2S = None

    restore()
    base = board()
    if base is None:
        raise SystemExit("기준선 실패")
    b = base.mean(0)
    print(f"부분집합 {SESS} · {len(base)} trial")
    print(f"기준선 (H1_260811): 채널 " + " ".join(f"{x:.2f}" for x in b) + "\n", flush=True)
    res = {}
    t0 = time.time()
    for tag, cfg in TRIALS.items():
        if want and tag not in want:
            continue
        restore()
        for k, v in cfg.items():
            os.environ[k] = v
        FR._S2S = None
        f = board()
        if f is None:
            print(f"  {tag:22s} → 발산/실패", flush=True); continue
        c = f.mean(0)
        n = 100 * (np.mean(c / b) - 1)                 # 채널 정규화 평균 (지표 정정본)
        res[tag] = dict(d=float(n), ch=[float(x) for x in c], cfg=cfg)
        mark = " ★" if n < -1.0 else ("  ." if n < 0 else "")
        print(f"  {tag:22s} → {n:+6.2f}%   (자세4 {100*(np.mean(c[:4]/b[:4])-1):+5.1f}%){mark}", flush=True)
    restore()
    safe.atomic_json_write(OUT, {"base": [float(x) for x in b], "sess": SESS, "res": res})
    print(f"\n{time.time()-t0:.0f}초 · 저장 → {OUT}")
    good = sorted([(v["d"], k) for k, v in res.items()])[:12]
    print("\n개선 상위 12 (부분집합 — 전 보드·게이트 재판정 필요)")
    for d, k in good:
        print(f"  {d:+6.2f}%  {k}   {res[k]['cfg']}")


if __name__ == "__main__":
    main()
