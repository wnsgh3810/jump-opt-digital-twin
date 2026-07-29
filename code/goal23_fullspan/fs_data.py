# -*- coding: utf-8 -*-
"""fs_data — GOAL23 FULLSPAN 데이터층: *2 파서 + 창 분할기 + 임베딩 검증.

*2 형식 (Explore 검증 2026-07-29): hip2/knee2/GRF2.xlsx, 전 세션 rad 통일, 500Hz(dt=0.002),
기존 hip.xlsx 창을 절대 타임축 공유로 오차 0 포함, 토크 언랩 완료.
모션 구조: hold0(초기 유지) → desc(천천히 deep squat로 하강 — 준정적, 세션 캘리브 창) → prehold(바닥 준비자세 유지)
→ push(급속 점프 국면: 최종 딥+신전) → 이륙 → flight → landing(마킹만).
채점 창 = [앉기(하강) 개시, 이륙]. 규칙: harness_output(합성)·raw_unwrap 경로 사용 금지 (파서가 차단).
CLI: verify(전 trial 임베딩+분할 표) · spot(3 trial 분할 그래프)
"""
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(r"C:/Users/junho/Desktop/Research/4-Bar Link CVT/Data")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "goal22" / "p26_sea"))
from sea_twin2 import ahat_np    # noqa: E402  (a_hat Paper 변환 — 정본 재사용)

SESS_FIT = {
    "26.07.22": ROOT / "26.07.22",
    "26.07.23": ROOT / "26.07.23",
    "26.07.24": ROOT / "26.07.24",
    "26.07.25": ROOT / "26.07.25",
    "26.07.27": ROOT / "26.07.27",
    "26.04.24": ROOT / "26.04.24",
    "26.06.02": ROOT / "26.06.02" / "position",
    "26.04.29": ROOT / "26.04.29",              # CVT l_i=25.08 — Day2 러너 정비 후 채점 편입
    "26.04.21": ROOT / "26.04.21" / "Position Control",
}
SESS_HO = {"26.03.24": ROOT / "26.03.24" / "Jump" / "Jump_No_Tr"}   # held-out — fit 절대 금지
CVT_SESS = {"26.04.29"}
BANNED = ("harness_output", "raw_unwrap", "Simulation")


def _check_path(fold: Path):
    s = str(fold)
    for b in BANNED:
        if b in s:
            raise ValueError(f"금지 경로 사용 시도: {s} ({b})")


def trials_of(base: Path):
    """세션 폴더의 *2 완비 trial 폴더 목록 (금지 경로 제외)."""
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir() or any(b in str(p) for b in BANNED):
            continue
        if (p / "hip2.xlsx").exists() and (p / "knee2.xlsx").exists() and (p / "GRF2.xlsx").exists():
            out.append(p)
    return out


def gains_of(name: str):
    """게인 파싱: 'kp1_kd1_kp2_kd2' 또는 'P100_D0.75_P100_D2' (0421 형식)."""
    toks = name.split("_")
    try:
        g = [float(x) for x in toks]
        return tuple(g) if len(g) == 4 else None
    except ValueError:
        pass
    if len(toks) == 4 and toks[0].startswith("P") and toks[1].startswith("D"):
        try:
            return (float(toks[0][1:]), float(toks[1][1:]), float(toks[2][1:]), float(toks[3][1:]))
        except ValueError:
            return None
    return None


def load2(fold: Path):
    """*2 로드 → dict (t=상대[s], 전부 rad/rad·s/Nm; t_abs=절대 타임축)."""
    _check_path(fold)
    hip = pd.read_excel(fold / "hip2.xlsx")
    knee = pd.read_excel(fold / "knee2.xlsx")
    grf = pd.read_excel(fold / "GRF2.xlsx")
    n = min(len(hip), len(knee), len(grf))
    hip, knee, grf = hip.iloc[:n], knee.iloc[:n], grf.iloc[:n]
    t_abs = hip["Time"].to_numpy(float)
    v1 = hip["currentAngleVelocity"].to_numpy(float)
    v2 = knee["currentAngleVelocity"].to_numpy(float)
    raw1 = hip["currentTorque"].to_numpy(float)
    raw2 = knee["currentTorque"].to_numpy(float)
    d = dict(
        t=t_abs - t_abs[0], t_abs=t_abs,
        q1=hip["currentAngle"].to_numpy(float), q2=knee["currentAngle"].to_numpy(float),
        qd1=hip["desiredAngle"].to_numpy(float), qd2=knee["desiredAngle"].to_numpy(float),
        dq1=v1, dq2=v2,
        dqd1=hip["desiredAngleVelocity"].to_numpy(float),
        dqd2=knee["desiredAngleVelocity"].to_numpy(float),
        raw1=raw1, raw2=raw2,
        a1=ahat_np(raw1, v1), a2=ahat_np(raw2, v2),
        grf=grf["Current_GRF"].to_numpy(float),
        name=fold.name, fold=str(fold))
    if np.nanmax(np.abs(d["q2"])) > 7:
        raise ValueError(f"{fold}: *2 각도가 rad가 아님 (규약 위반?)")
    return d


def _smooth(x, w):
    return np.convolve(x, np.ones(w) / w, mode="same")


def segment(d):
    """창 분할. 반환 seg dict: 인덱스 경계 (hold0/ramp/prehold/squat_on/t_lo/landing)와
    score 마스크 = [squat_on−PAD, 이륙−ε]. 이륙·착지는 GRF2 비행 스팬으로."""
    t = d["t"]; g = d["grf"]; n = len(t)
    gs = _smooth(g, 11)
    base = float(np.median(gs[: max(10, n // 20)]))
    # 비행 스팬: 후반부에서 GRF가 바닥 근처(<25% base, 최소 0.1s 지속)인 최장 구간
    low = gs < max(3.0, 0.25 * base)
    spans = []
    i = 0
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            spans.append((i, j))
            i = j
        else:
            i += 1
    spans = [(a, b) for a, b in spans if t[b - 1] - t[a] >= 0.10 and t[a] > 0.5]
    if not spans:
        raise ValueError(f"{d['name']}: 비행 스팬 미검출")
    a, b = max(spans, key=lambda ab: ab[1] - ab[0])
    i_lo, i_land = a, min(b, n - 1)
    # 이륙 새너티: 무릎 속도 피크 기준 — GRF 캘리브 불량 세션(0429 등) 방어.
    # 이륙은 |dq2| 피크 직후여야 함 (푸시 최고속 → 수 십 ms 내 이탈).
    vk = np.abs(_smooth(d["dq2"], 5))
    i_pk = int(np.argmax(vk))
    if not (0 <= t[i_lo] - t[i_pk] <= 0.12):
        i_lo = min(n - 2, i_pk + int(0.02 / max(t[1] - t[0], 1e-4)))   # 피크 +20ms 폴백
    # 미끼 각속도는 qd의 수치 미분으로 (dqd 채널은 느린 구간에서 0일 수 있음 — 스팟체크 발견)
    dt = max(float(np.median(np.diff(t))), 1e-4)
    vq = np.maximum(np.abs(np.gradient(_smooth(d["qd1"], 25), t)),
                    np.abs(np.gradient(_smooth(d["qd2"], 25), t)))
    FAST = 1.0                       # 푸시(급속 신전) 임계 [rad/s]
    SLOW = 0.02                      # 앉기(느린 하강) 임계 [rad/s]
    pre = vq[:i_lo]
    above = pre > FAST
    if not above.any():
        raise ValueError(f"{d['name']}: 푸시 개시 미검출")
    j = int(np.where(above)[0][-1])
    while j > 0 and above[j - 1]:
        j -= 1
    i_push = j                       # 급속 국면(최종 딥+신전) 개시
    # 앉기(느린 하강) 개시: 처음으로 SLOW 이상이 0.3s 지속되는 지점
    i_desc = None
    k = 0
    win = int(0.3 / dt)
    while k < i_push - win:
        if (vq[k:k + win] > SLOW).mean() > 0.8:
            i_desc = k
            break
        k += 1
    if i_desc is None:
        i_desc = max(0, i_push - int(1.0 / dt))   # 폴백: 푸시 1s 전
    # 앉기 끝(바닥 도달) → 프리홀드: i_desc 이후 vq가 SLOW 아래로 0.2s 지속되는 첫 지점
    i_bot = i_push
    k = i_desc + win
    win2 = int(0.2 / dt)
    while k < i_push - win2:
        if (vq[k:k + win2] < SLOW).mean() > 0.9:
            i_bot = k
            break
        k += 1
    score = np.zeros(n, bool)
    score[max(0, i_desc - 5): i_lo] = True        # ★채점 창 = 앉기 개시~이륙 (사용자 확정 범위)
    push = np.zeros(n, bool); push[max(0, i_push - 5): i_lo] = True
    desc = np.zeros(n, bool); desc[i_desc: i_bot] = True
    return dict(i_desc=i_desc, i_bot=i_bot, i_push=i_push, i_lo=i_lo, i_land=i_land,
                t_desc=float(t[i_desc]), t_push=float(t[i_push]), t_lo=float(t[i_lo]),
                t_land=float(t[i_land]),
                hold0=(t < t[i_desc] - 0.01) if i_desc > 5 else (t < 0),
                desc=desc,                          # 앉기(준정적 하강) — 캘리브 후보 창
                prehold=(np.arange(n) >= i_bot) & (np.arange(n) < i_push),
                push=push, score=score)


def verify_embed(fold: Path, tol=1e-9):
    """기존 hip.xlsx 창이 hip2에 그대로 임베딩돼 있는지 (절대 타임축 대조). 반환 (최대차, n대조)."""
    old = pd.read_excel(fold / "hip.xlsx") if (fold / "hip.xlsx").exists() else None
    if old is None:
        return None, 0
    d = load2(fold)
    to = old["Time"].to_numpy(float)
    qo = old["currentAngle"].to_numpy(float)
    if np.nanmax(np.abs(old.get("currentAngle", pd.Series([0])).to_numpy(float))) > 7:
        qo = np.radians(qo)          # 구세션 hip.xlsx는 deg일 수 있음 — rad 변환 후 대조
    idx = np.searchsorted(d["t_abs"], to)
    idx = np.clip(idx, 0, len(d["t_abs"]) - 1)
    m = np.abs(d["t_abs"][idx] - to) < 1e-6
    if m.sum() == 0:
        return float("nan"), 0
    return float(np.max(np.abs(d["q1"][idx[m]] - qo[m]))), int(m.sum())


def registry():
    """(세션, trial 폴더, 게인, is_cvt, is_holdout) 전수 목록."""
    out = []
    for s, base in SESS_FIT.items():
        for p in trials_of(base):
            out.append((s, p, gains_of(p.name), s in CVT_SESS, False))
    for s, base in SESS_HO.items():
        for p in trials_of(base):
            out.append((s, p, gains_of(p.name), False, True))
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    reg = registry()
    print(f"레지스트리 trial {len(reg)}개 (fit {sum(1 for r in reg if not r[4])} / HO {sum(1 for r in reg if r[4])})")
    if mode == "verify":
        bad = 0
        for s, p, g, cvt, ho in reg:
            try:
                d = load2(p)
                seg = segment(d)
                emb, ncmp = verify_embed(p)
                embs = f"{emb:.2e}({ncmp})" if emb is not None and ncmp else "구창없음"
                flag = "" if (emb is None or not ncmp or emb < 1e-6) else " ★임베딩차이"
                print(f"{s}/{p.name}: 앉기 {seg['t_desc']:.2f}→바닥 {d['t'][seg['i_bot']]:.2f}→푸시 {seg['t_push']:.2f}"
                      f"→이륙 {seg['t_lo']:.2f}s (채점 {(seg['t_lo']-seg['t_desc'])*1000:.0f}ms, 푸시 {(seg['t_lo']-seg['t_push'])*1000:.0f}ms) | 임베딩 {embs}{flag}", flush=True)
            except Exception as ex:
                bad += 1
                print(f"{s}/{p.name}: FAIL {type(ex).__name__} {ex}", flush=True)
        print(f"완료 (실패 {bad})")
    elif mode == "spot":
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
        picks = [("26.07.27", "150_2.2_250_3"), ("26.06.02", "150_2.2_250_3"), ("26.03.24", "P100_D3")]
        fig, axes = plt.subplots(len(picks), 1, figsize=(14, 3.2 * len(picks)))
        for ax, (s, name) in zip(np.atleast_1d(axes), picks):
            base = SESS_FIT.get(s) or SESS_HO.get(s)
            d = load2(base / name)
            seg = segment(d)
            ax.plot(d["t"], np.degrees(d["qd2"]), lw=1.2, label="qd2 [°]")
            ax.plot(d["t"], d["grf"] / 10, lw=1.0, label="GRF/10 [N]")
            for key, lab in [("i_desc", "앉기"), ("i_bot", "바닥"), ("i_push", "푸시"), ("i_lo", "이륙"), ("i_land", "착지")]:
                ax.axvline(d["t"][seg[key]], ls=":", lw=1.0)
                ax.text(d["t"][seg[key]], ax.get_ylim()[1] if key != "i_land" else ax.get_ylim()[0], lab, fontsize=8, rotation=90, va="top")
            ax.set_title(f"{s}/{name} — 창 분할", fontsize=10); ax.grid(alpha=.3); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(HERE / "fs_spotcheck.png", dpi=110)
        print("saved fs_spotcheck.png")


if __name__ == "__main__":
    main()
