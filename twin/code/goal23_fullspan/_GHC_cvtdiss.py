# 변속기(4절 링크)의 **자세 의존 손실**을 키우면 일어서기가 더 좋아지나 — 2 차원 훑기 (읽기 전용)
#
#   왜 이 축인가 (08-14, 사용자 요청)
#     무릎 하중 비례 손실만으로는 통짜 성적이 0.783 에서 멈춘다 (합격선 0.43 의 1.8 배).
#     그런데 그 최선 자리에서 경우를 뜯어보면 **무변속은 거의 풀리고 변속만 남는다.**
#     무변속은 4절 링크의 힘/속도 교환비가 정확히 1 이라 자세 의존 손실이 **원리상 0** 이다.
#     ⇒ 남은 오차가 이 항에 있는지 직접 확인한다.
#
#   손실의 형태 (이미 구현돼 있다 — 두 재생 경로 모두)
#     손실 토크 = C · |명령 토크| · (1/|교환비| − 1) · tanh(무릎 각속도 / 1.0)
#       · |명령 토크| 에 비례      → 세게 밀수록 많이 샌다 (누르는 힘이 클수록 마찰이 큰 쿨롱 마찰)
#       · (1/교환비 − 1) 에 비례  → 교환비가 나쁜 자세일수록 급격히 커진다 (무변속은 1 → 정확히 0)
#       · tanh(속도)             → 운동을 거스르는 방향, 정지 부근에서 0
#     배수 손잡이 = FS_CVT_DISS_SCALE (1 = 지금 그대로, 0 = 손실 없음)
#
#   같이 훑는 축: 무릎 하중 비례 손실 (fc0 + fc1·|명령|)·tanh(속도/v0) 의 fc1.
#   두 축이 서로 대신할 수 있으므로 **따로 훑으면 답이 갈린다** — 그래서 2 차원이다.
import os, sys
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
from pathlib import Path
GFS = str(Path(__file__).parent)
sys.path.insert(0, GFS); os.chdir(GFS)
import numpy as np
import fs_data as FD, fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._ensure()
BASE = np.asarray(S.DEPLOY, float)


def _one(ft, d, t0, t1):
    """한 창을 통짜 개루프로 재생 → (성적, 버틴 시간). 성적은 0 이 완벽."""
    t = d["t"]; mm = (t >= t0) & (t <= t1)
    if mm.sum() < 20: return None
    i0 = int(np.argmax(mm)); tg = t[mm] - t[i0]
    L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][mm], d["raw2"][mm],
                           float(d["q1"][i0]), float(d["q2"][i0]),
                           float(d["dq1"][i0]), float(d["dq2"][i0]),
                           float(tg[-1] - 0.004), fade=True)
    if L is None: return None
    gf = lambda k: np.interp(tg, L["t"], L[k])
    sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
    v = [S._r80(tg, d[k][mm], sm, floor=fl) for k, sm, fl in zip(S.CH4, sim, S.AIR_FLOOR)]
    if not all(np.isfinite(v)): return None
    e = np.degrees(np.abs(sim[1] - d["q2"][mm]))
    k = np.where(e > 10.0)[0]
    return float(np.mean([min(x, 10.) for x in v])), (float(tg[k[0]]) if len(k) else float(tg[-1]))


def s2s_all():
    """일어서기 4 경우 → (경우별 통짜 성적, 전체 통짜 평균, 버틴 시간 평균)."""
    m0 = float(os.environ.get("FS_MASS", "3.30")); keep = os.environ.get("FS_MASS")
    out, whole, hold = {}, [], []
    try:
        for sub, pay, cvt in FD.S2S_CASES:
            d = FD.load_s2s(sub)
            if d is None: continue
            os.environ["FS_MASS"] = f"{m0+pay:.4f}"
            FR._CACHE.clear(); S._CVT_STAMPED.clear()
            ft = FC.cvt_ft(float(d["l_i"]), ft_base=FR.fs_twin()) if cvt else FR.fs_twin()
            w = _one(ft, d, float(d["t"][0]), float(d["t"][-1]))
            out[sub] = w[0] if w else 10.0
            whole.append(w[0] if w else 10.0); hold.append(w[1] if w else 0.0)
    finally:
        if keep is None: os.environ.pop("FS_MASS", None)
        else: os.environ["FS_MASS"] = keep
        FR._CACHE.clear(); S._CVT_STAMPED.clear()
    return out, float(np.mean(whole)), float(np.mean(hold))


print("변속기 자세 의존 손실 배수 × 무릎 하중 비례 손실 — 2 차원 훑기")
print("  성적 = 창 앞 80% 오차 ÷ 그 신호가 그 구간에서 움직인 폭 (0 이 완벽 · 채널당 상한 10)")
print("  일어서기는 **통짜** 재생 (창 안 나눔). 버틴s = 무릎 각도 오차 10 도까지 [s], 길수록 좋다")
print("  점프주입 = 점프 세션 측정토크 주입 재생 · 변속기점프 = 그 중 변속기 세션(26.04.29)만")
print("  ※ 자세 의존 손실은 변속기 경우에만 0 이 아니다 (무변속은 교환비 1 → 원리상 0)")
print()
hdr = (f"{'설정':26s} {'일어서기':>8s} {'변속0':>7s} {'변속2.5':>8s} {'변속5':>7s} {'무변속':>7s}"
       f" {'버틴s':>6s} | {'점프주입':>8s} {'변속기점프':>10s}")
print(hdr); print("-" * len(hdr))

ROWS = [("지금 모델 (손실배수 1)", "canon_cap", None, "1")]
for f in (0.30, 0.45):
    for ds in ("0", "1", "2", "3", "5"):
        ROWS.append((f"하중비례{f:.2f} · 손실배수{ds}", "canon_mix", f"0.18,{f:.2f},0,0.3", ds))

for tag, mode, mix, ds in ROWS:
    e = S.env_of("canon_cap", BASE)
    e["FS_TMAP"] = mode
    if mix: e["FS_TMIX"] = mix
    e["FS_CVT_DISS_SCALE"] = ds
    S._apply(e)                              # _apply 는 이 둘을 지우지 않으므로 update 로 들어간다
    if not mix: os.environ.pop("FS_TMIX", None)
    os.environ["FS_CVT_DISS_SCALE"] = ds     # 확실히 (지우는 목록 밖이지만 명시)
    s, wh, hd = s2s_all()
    S._apply(e)
    if not mix: os.environ.pop("FS_TMIX", None)
    os.environ["FS_CVT_DISS_SCALE"] = ds
    B = S.board()
    ma = S.absm(B, "ma8", S.FIT, (0, 1, 2, 3))
    mac = S.absm(B, "ma8", ("26.04.29",), (0, 1, 2, 3))
    print(f"{tag:26s} {wh:8.3f} {s.get('cvt/no_load',float('nan')):7.3f} "
          f"{s.get('cvt/load_2.5',float('nan')):8.3f} {s.get('cvt/load_5',float('nan')):7.3f} "
          f"{s.get('no_cvt/no_load',float('nan')):7.3f} {hd:6.3f} | {ma:8.4f} {mac:10.4f}", flush=True)
print("-" * len(hdr))
print("※ 나머지 16 축은 배포 스택 그대로 — 공동 재적합을 안 한 값이라 점프 대가는 과대평가다.")
os.environ.pop("FS_CVT_DISS_SCALE", None)
