# -*- coding: utf-8 -*-
"""p23_loaders — P23 Phase 0b: 청정 로더 3+1종 (xlsx 직행, csv 오염 우회).

자산 (MARATHON_p23.md 광맥 인벤토리 / p23_survey_* 탐사 확정):
  1. load_jump_0422(sub)    — 26.04.22 FF 점프 3 trial (FF cap 15Nm + PD, GRF 있음)
  2. load_jump_0319tau(sub) — 26.03.19 tau/no_tr_tau FF 점프 (cap 9Nm, 단일 trial 0.32s 창)
  3. load_s2s_0324(sub)     — 26.03.24 지상 sit2stand 5 trial (샘플 드랍 최대 90ms → 리샘플)
  4. load_s2s_air()         — 26.03.19 공중 sit2stand (115s, 15사이클; 잘린 마지막 사이클 drop)

규약:
  - 표준 d-dict 키: t q1 q2 dq1 dq2 traw1 traw2 qd1 qd2 dqd1 dqd2 tdes1 tdes2
                    grf_real(없으면 None) h_real(없으면 NaN). t는 0 시작으로 정규화.
  - traw = raw iTM 단위 그대로 (Nm 아님!) — 축토크는 judge().J.ahat(A_PAPER, traw, dq)로만.
  - jump_opt_compare/predicted_compare.csv 절대 사용 금지 (토크 ×1.3+ 오염 — 탐사 검증).
  - 원본 데이터 읽기 전용 (아무것도 쓰지 않음). self-test 출력은 stdout만.
  - 각 로더는 (d, meta) 반환. load_s2s_air는 (cycles: list[d-dict], meta) 반환.

골든 검증 (Phase 0b 게이트):
  - validate_0422_vs_goal16(): xlsx→Paper a_hat 변환 vs goal16 Mode A npz의 baked tau_real
    (탐사에서 rms 비율 1.0000 검증된 청정본) — per-sub max|Δ|/max|τ| < 1e-3 필수.
  - load_s2s_air 사이클 분할 vs 레거시 캐시 (goal18/iter0R + goal12/xval_v2 cycle_final.npz).
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("C:/Users/junho/Desktop/Research/4-Bar_Link_CVT/Data")
REPO = Path("C:/Users/junho/Documents/jump-opt-digital-twin")
JO = Path("C:/Users/junho/Desktop/jump_opt")

COLS = ["Time", "currentAngle", "desiredAngle", "currentAngleVelocity",
        "desiredAngleVelocity", "currentTorque", "desiredTorque"]

SUBS_0422 = ["P40_D0.7", "P70_D2", "P100_D3"]
SUBS_0319TAU = ["no_tr_tau"]          # tau/ 아래 단일 trial (root xlsx 0.32s 창 하나)
SUBS_S2S_0324 = ["sit2stand_P10_D0", "sit2stand_P10_D1", "sit2stand_P20_D1",
                 "sit2stand_P30_D1", "sit2stand_P60_D1.5_P60_D2"]

GOAL16_0422 = JO / "goal16/cross_validation_modeA/jump_torque_0422/sim_data"
LEGACY_AIR = {
    "goal18_iter0R": JO / "goal18/iter0R/sit2stand_air_0319/ROOT/cycle_final.npz",
    "goal12_xval_v2": JO / "goal12/xval_v2/sit2stand_air_0319/ROOT/cycle_final.npz",
}

_P = None


def judge():
    """p19_judge lazy import (Paper a_hat 정본: judge().J.ahat(judge().A_PAPER, traw, dq))."""
    global _P
    if _P is None:
        sys.path.insert(0, str(REPO / "code/goal22/p19_jump"))
        sys.path.insert(0, str(REPO / "code/bench"))
        import p19_judge as P
        _P = P
    return _P


# ══════════════════ 공통 헬퍼 ══════════════════
def _read_joint(fp):
    df = pd.read_excel(fp)
    return {c: df[c].values.astype(float) for c in COLS}


def _read_txt(fp):
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return Path(fp).read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return Path(fp).read_bytes().decode("utf-8", errors="replace")


def _parse_h_real(fp):
    """Real Data.txt 첫 줄 '실제 점프 높이 : 0.74m' → 0.74 (레거시 load_combined_15trial 규약).
    첫 줄에 'Xm' 패턴이 없으면 (예: 0319tau는 GRF Summary로 시작) NaN."""
    try:
        first = _read_txt(fp).splitlines()[0]
        m = re.search(r"(\d+\.?\d*)\s*m", first)
        if m:
            h = float(m.group(1))
            return h / 100.0 if h > 3.0 else h    # cm 방어 (cvt_core 규약)
    except (OSError, IndexError):
        pass
    return float("nan")


def _read_grf_on(t_abs, root):
    """GRF.xlsx(Current_GRF)를 자기 Time으로 읽어 t_abs(절대초) 그리드에 보간. 없으면 None."""
    fp = Path(root) / "GRF.xlsx"
    if not fp.exists():
        return None
    try:
        g = pd.read_excel(fp)
        col = "Current_GRF" if "Current_GRF" in g.columns else \
            [c for c in g.columns if "GRF" in str(c)][0]
        tg = g["Time"].values.astype(float)
        return np.interp(t_abs, tg, g[col].values.astype(float))
    except Exception:
        return None


def _pack(hip, knee, grf_real=None, h_real=float("nan")):
    """hip/knee 채널 dict → 표준 d-dict. dqd/tdes의 NaN(미기록)은 0으로.
    grf_real은 이미 공통 그리드에 정렬된 배열(또는 None)을 받는다."""
    n = min(len(hip["Time"]), len(knee["Time"]))
    t = hip["Time"][:n] - hip["Time"][0]
    d = dict(t=t)
    for nm, src in (("1", hip), ("2", knee)):
        d["q" + nm] = src["currentAngle"][:n]
        d["qd" + nm] = src["desiredAngle"][:n]
        d["dq" + nm] = src["currentAngleVelocity"][:n]
        d["dqd" + nm] = np.nan_to_num(src["desiredAngleVelocity"][:n])
        d["traw" + nm] = src["currentTorque"][:n]
        d["tdes" + nm] = np.nan_to_num(src["desiredTorque"][:n])
    d["grf_real"] = grf_real[:n] if grf_real is not None else None
    d["h_real"] = float(h_real)
    return d


def _resample(hip, knee):
    """비균일 타임베이스(샘플 드랍) → 공통 균일 그리드 (median dt, np.interp).
    hip/knee 각자 자기 Time 기준으로 보간 (드랍 위치가 관절마다 다를 수 있음)."""
    th, tk = hip["Time"], knee["Time"]
    dt = float(np.median(np.diff(th)))
    t0 = max(th[0], tk[0])
    t1 = min(th[-1], tk[-1])
    tg = t0 + np.arange(int(np.floor((t1 - t0) / dt)) + 1) * dt

    def rs(src, ts):
        out = {"Time": tg}
        for c in COLS[1:]:
            v = src[c]
            m = np.isfinite(v)
            out[c] = np.interp(tg, ts[m], v[m]) if m.any() else np.full(len(tg), np.nan)
        return out

    meta = dict(resampled=True, dt_ms=round(dt * 1e3, 3),
                max_gap_ms=dict(hip=round(float(np.max(np.diff(th))) * 1e3, 2),
                                knee=round(float(np.max(np.diff(tk))) * 1e3, 2)),
                n_raw=dict(hip=len(th), knee=len(tk)), n_grid=len(tg))
    return rs(hip, th), rs(knee, tk), meta


def _label_gains(lab):
    """'P10_D0' → (10,0,10,0) / 'P60_D1.5_P60_D2' → (60,1.5,60,2) (폴더 라벨 규약)."""
    p = lab.split("_")
    if len(p) == 2:
        kp, kd = float(p[0][1:]), float(p[1][1:])
        return kp, kd, kp, kd
    return float(p[0][1:]), float(p[1][1:]), float(p[2][1:]), float(p[3][1:])


def _regress_gains(d, use_ff=True):
    """실효 게인 회귀 (게인 파일 부재 시): raw ≈ kp·(qd−q) − kd·dq [+ cff·tdes].
    V2 규약 (dq_des=0 커맨드 — 0319 What.txt 'V_des=0'). 포화 |raw|≥17.5 제외."""
    out = {}
    for j in ("1", "2"):
        y = d["traw" + j]
        m = np.abs(y) < 17.5
        cols = [(d["qd" + j] - d["q" + j])[m], (-d["dq" + j])[m]]
        if use_ff:
            cols.append(d["tdes" + j][m])
        A = np.column_stack(cols)
        c, *_ = np.linalg.lstsq(A, y[m], rcond=None)
        r2 = 1 - np.sum((y[m] - A @ c) ** 2) / max(np.sum((y[m] - y[m].mean()) ** 2), 1e-12)
        out[j] = dict(kp=float(c[0]), kd=float(c[1]),
                      cff=float(c[2]) if use_ff else 0.0,
                      r2=float(r2), n_sat=int((~m).sum()))
    return out


# ══════════════════ 1) 26.04.22 FF 점프 ══════════════════
def parse_pid_0422(fp):
    """PID.txt의 'Jump' 줄에서 (kp1,kd1,kp2,kd2) 파싱.
    ★ P40_D0.7 폴더: PID.txt에 'Jump P 70 D2 ( Hip ) / Jump P 40 D0.7 ( Knee)'
      → 폴더 라벨은 knee만 반영, hip은 실제 P70/D2 (탐사 확정 함정)."""
    hip = knee = None
    for ln in _read_txt(fp).splitlines():
        if "jump" not in ln.lower():
            continue
        m = re.search(r"P\s*(\d+(?:\.\d+)?)\s*D\s*(\d+(?:\.\d+)?)", ln)
        if not m:
            continue
        kp, kd = float(m.group(1)), float(m.group(2))
        low = ln.lower()
        has_hip, has_knee = "hip" in low, "knee" in low
        if has_hip and not has_knee:
            hip = (kp, kd)
        elif has_knee and not has_hip:
            knee = (kp, kd)
        else:                               # 관절 표기 없음(헤더 ' Hip Knee') = 양 관절
            hip = knee = (kp, kd)
    if hip is None or knee is None:
        raise ValueError(f"PID.txt에서 Jump 게인 파싱 실패: {fp}")
    return hip[0], hip[1], knee[0], knee[1]


def load_jump_0422(sub):
    """26.04.22/Torque Control/<sub> — FF(캡 15Nm)+PD 점프. 토크는 xlsx currentTorque 직행."""
    root = DATA / "26_04_22/Torque Control" / sub
    hip = _read_joint(root / "hip.xlsx")
    knee = _read_joint(root / "knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    grf = _read_grf_on(hip["Time"][:n], root)
    d = _pack(hip, knee, grf, _parse_h_real(root / "Real Data.txt"))
    gains = parse_pid_0422(root / "PID.txt")
    meta = dict(
        ds="jump_0422", sub=sub, gains=gains, gains_source="PID.txt (Jump 줄)",
        ffk=True, dqdes_on=False, is_cvt=False,
        l_i=0.030, l_i_assumed=True,        # Clutch.xlsx 없음 = 무변속 세션 가정
        tdes_cap=15.0, heldout_day=False,
        label_gain_mismatch=(sub == "P40_D0.7"),
        note=("hip에도 FF 신호 기록됨 (tdes1 rms~6Nm, cap 15) — 기존 러너는 knee FF만"
              " 주입(ffk). desiredAngleVelocity도 기록돼 있으나 0324 동일 명령 구조"
              " 가정으로 dqdes_on=False (회귀는 관절별로 V1/V2 판별 애매)."))
    return d, meta


def validate_0422_vs_goal16(atol_rel=1e-3):
    """골든 검증: xlsx→Paper a_hat vs goal16 npz baked tau_real (per-sub, per-joint).
    반환 {sub: {tau1_real/tau2_real: dict(max_rel_dev, sign, n)}, ...} + 'PASS' 플래그."""
    P = judge()
    out = {}
    for sub in SUBS_0422:
        z = np.load(GOAL16_0422 / f"jump_torque_0422_{sub}.npz")
        d, _ = load_jump_0422(sub)
        tz = np.asarray(z["t_real"], float)
        tz = tz - tz[0]
        n = min(len(tz), len(d["t"]))
        res = {}
        for j, key in (("1", "tau1_real"), ("2", "tau2_real")):
            clean = P.J.ahat(P.A_PAPER, d["traw" + j], d["dq" + j])
            if np.allclose(tz[:n], d["t"][:n], atol=1e-9):
                cl_i = clean[:n]
            else:                            # 타임베이스 다르면 보간 정렬
                cl_i = np.interp(tz[:n], d["t"], clean)
            tn = np.asarray(z[key], float)[:n]
            dev_p = float(np.abs(tn - cl_i).max())
            dev_m = float(np.abs(-tn - cl_i).max())
            sign = 1 if dev_p <= dev_m else -1
            mx = min(dev_p, dev_m) / max(float(np.abs(cl_i).max()), 1e-9)
            res[key] = dict(max_rel_dev=float(mx), sign=sign, n=int(n))
        res["PASS"] = all(v["max_rel_dev"] < atol_rel for k, v in res.items()
                          if isinstance(v, dict))
        out[sub] = res
    return out


# ══════════════════ 2) 26.03.19 tau/no_tr_tau FF 점프 ══════════════════
def load_jump_0319tau(sub="no_tr_tau"):
    """26.03.19/tau/no_tr_tau — FF(캡 9Nm)+PD 점프, 무변속 (Clutch 없음 → l_i=0.030 가정).
    trial 구성: 하위 trial 폴더 없음 — root xlsx 하나 (0.32s 창, 38.13~38.45s) = 단일 trial.
    게인: PID.txt 없음. 세션 What.txt = 'No 변속+V_des=0+새 모터' (게인 미기재)
    → V2+ff 회귀로 실효 게인 추정 (gains_source에 명기)."""
    root = DATA / "26_03_19/tau" / sub
    hip = _read_joint(root / "hip.xlsx")
    knee = _read_joint(root / "knee.xlsx")
    n = min(len(hip["Time"]), len(knee["Time"]))
    grf = _read_grf_on(hip["Time"][:n], root)
    d = _pack(hip, knee, grf, _parse_h_real(root / "Real Data.txt"))   # 첫 줄에 높이 없음 → NaN
    reg = _regress_gains(d, use_ff=True)
    # 러너 소비용 게인: kd<0(비물리 — FF 지배로 회귀가 음수 감쇠를 뱉음)은 0으로 클램프.
    # 정직한 회귀 원값은 meta['gain_regression']에 그대로 보존.
    gains = (reg["1"]["kp"], max(reg["1"]["kd"], 0.0),
             reg["2"]["kp"], max(reg["2"]["kd"], 0.0))
    meta = dict(
        ds="jump_0319tau", sub=sub, gains=gains,
        gains_source=("regressed V2+ff (PID.txt 없음; What.txt='No 변속+V_des=0+새 모터'"
                      " — 게인 미기재)"),
        gains_kd_clamped=(reg["1"]["kd"] < 0 or reg["2"]["kd"] < 0),
        gain_regression=reg,
        ffk=True, dqdes_on=False, is_cvt=False,
        l_i=0.030, l_i_assumed=True,        # Clutch.xlsx 없음 (tr_tau에만 있음)
        tdes_cap=9.0, heldout_day=False,
        note="h_real 없음 (Real Data.txt 첫 줄 = GRF Summary). knee cff≈0.87 (FF 실재).")
    return d, meta


# ══════════════════ 3) 26.03.24 지상 sit2stand ══════════════════
def load_s2s_0324(sub):
    """26.03.24/sit2stand/<sub> — 지상 s2s (위치제어, ~110-140s 창).
    샘플 드랍 갭 최대 ~90ms → median dt 균일 그리드로 np.interp 리샘플 (meta에 max gap).
    desiredTorque 0/NaN → tdes=0. GRF·Clutch·Real Data 없음.
    ★ held-out DAY(26.03.24)지만 sit2stand 폴더는 fit-legal (GOAL18/19에서 사용) —
      meta heldout_day=True로 태깅해 다운스트림에서 제외 판단 가능하게."""
    root = DATA / "26_03_24/sit2stand" / sub
    hip = _read_joint(root / "hip.xlsx")
    knee = _read_joint(root / "knee.xlsx")
    hip_u, knee_u, rmeta = _resample(hip, knee)
    d = _pack(hip_u, knee_u, None, float("nan"))
    d["tdes1"] = np.zeros_like(d["t"])
    d["tdes2"] = np.zeros_like(d["t"])
    gains = _label_gains(sub.replace("sit2stand_", ""))
    meta = dict(
        ds="s2s_0324", sub=sub, gains=gains, gains_source="폴더 라벨",
        ffk=False, dqdes_on=False, is_cvt=False,
        l_i=0.030, l_i_assumed=True,
        heldout_day=True, fit_legal=True,
        note="레거시 사이클 캐시 참고 가능: goal12/xval_v2/sit2stand_0324/<sub>/cycle_final.npz",
        **rmeta)
    return d, meta


# ══════════════════ 4) 26.03.19 공중 sit2stand ══════════════════
DQ_THR, PAD_SAMPLES, MIN_DUR_S, MERGE_GAP_S = 0.3, 50, 0.3, 2.0


def _detect_air_segments(t, q2):
    """레거시 detect_motion_sit2stand_air_0319 로직 그대로 (원본 타임베이스에서):
    savgol(gradient(q2,t), 11, 3) → |dq2|>0.3 → pad ±50샘플(0.1s) → 최소 0.3s."""
    from scipy.signal import savgol_filter
    dt = float(t[1] - t[0])
    dq2 = savgol_filter(np.gradient(q2, t), window_length=11, polyorder=3)
    moving = np.abs(dq2) > DQ_THR
    mask = moving.copy()
    for i in np.where(moving)[0]:
        mask[max(0, i - PAD_SAMPLES):min(len(mask), i + PAD_SAMPLES)] = True
    segs, inm, s0 = [], False, 0
    for i, m in enumerate(mask):
        if m and not inm:
            s0, inm = i, True
        elif (not m) and inm:
            if (i - s0) * dt >= MIN_DUR_S:
                segs.append((s0, i))
            inm = False
    if inm and (len(mask) - s0) * dt >= MIN_DUR_S:
        segs.append((s0, len(mask) - 1))
    return segs


def _merge_segments(t, segs, gap_s=MERGE_GAP_S):
    """모션 버스트 → 사이클: 인접 버스트 간 dwell < gap_s 병합.
    (초반 느린 사이클은 상/하강 버스트가 dwell ≤1.6s로 분리 — 레거시 cycle_final은
     이를 한 사이클로 묶음. 후반 빠른 사이클은 버스트 1개 = 사이클 1개.)"""
    out = [list(segs[0])]
    for s, e in segs[1:]:
        if t[s] - t[out[-1][1]] < gap_s:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def load_s2s_air():
    """26.03.19/position/sit2stand_air — 공중 순수 스윙 15사이클 (무접촉 심판용).
    xlsx 재유도 (레거시 npz 재사용 아님) + 균일 리샘플 + 레거시 검출 로직 사이클 분할.
    잘린 마지막 사이클(기록 끝 135s에 걸침)은 drop. 반환: (cycles: list[d-dict], meta).
    각 사이클 d-dict에는 t0_abs(원본 절대 시작초) 키 추가."""
    root = DATA / "26_03_19/position/sit2stand_air"
    hip = _read_joint(root / "hip.xlsx")
    knee = _read_joint(root / "knee.xlsx")
    # 사이클 검출은 원본(비리샘플) 타임베이스에서 — 레거시와 정확히 동일 조건
    segs_raw = _detect_air_segments(hip["Time"], knee["currentAngle"])
    cyc_raw = _merge_segments(hip["Time"], segs_raw)
    windows = [(float(hip["Time"][s]), float(hip["Time"][min(e, len(hip["Time"]) - 1)]))
               for s, e in cyc_raw]
    t_end_rec = float(hip["Time"][-1])
    truncated_last = (t_end_rec - windows[-1][1]) < 0.5
    # 균일 리샘플 후 절대시간 창으로 슬라이스
    hip_u, knee_u, rmeta = _resample(hip, knee)
    d_full = _pack(hip_u, knee_u, None, float("nan"))
    d_full["tdes1"] = np.zeros_like(d_full["t"])
    d_full["tdes2"] = np.zeros_like(d_full["t"])   # hip=0 기록, knee=NaN → 0
    t_abs = hip_u["Time"]
    keep = windows[:-1] if truncated_last else windows
    cycles = []
    for (ta, tb) in keep:
        m = (t_abs >= ta) & (t_abs <= tb)
        c = {k: (v[m] if isinstance(v, np.ndarray) and v.shape == t_abs.shape else v)
             for k, v in d_full.items()}
        c["t"] = t_abs[m] - t_abs[m][0]
        c["grf_real"] = None
        c["h_real"] = float("nan")
        c["t0_abs"] = float(ta)
        cycles.append(c)
    reg = _regress_gains(d_full, use_ff=False)
    meta = dict(
        ds="s2s_air_0319", sub="ROOT",
        gains=(reg["1"]["kp"], reg["1"]["kd"], reg["2"]["kp"], reg["2"]["kd"]),
        gains_source="regressed V2 (게인 파일 없음 — 참고용 실효 게인)",
        gain_regression=reg,
        ffk=False, dqdes_on=False, is_cvt=False, airborne=True,
        l_i=0.030, l_i_assumed=True,        # ★ 가정: Clutch 미기록 (간접 증거만 — 명기)
        heldout_day=False,
        n_segments_raw=len(segs_raw), n_cycles_detected=len(windows),
        dropped_truncated_last=bool(truncated_last),
        cycle_windows_abs=windows,
        detector="savgol(grad q2) |dq2|>0.3, pad 0.1s, min 0.3s (레거시 동일) + gap<2s 병합",
        **rmeta)
    return cycles, meta


def crosscheck_s2s_air(meta):
    """레거시 캐시 대비 사이클 수·구간 대조. 반환 {tag: dict(n_legacy, count_match,
    per_cycle=[(내 창, 레거시 창, 시작Δ, 끝Δ, durΔ)], ...)}."""
    res = {}
    mine = meta["cycle_windows_abs"]
    for tag, p in LEGACY_AIR.items():
        if not p.exists():
            res[tag] = None
            continue
        cf = np.load(p)
        cyc, tc = cf["cycles"], cf["t"]
        legacy = [(float(tc[s]), float(tc[min(e, len(tc) - 1)])) for s, e in cyc]
        per = []
        for k in range(min(len(mine), len(legacy))):
            (a0, a1), (b0, b1) = mine[k], legacy[k]
            per.append(dict(mine=(round(a0, 2), round(a1, 2)),
                            legacy=(round(b0, 2), round(b1, 2)),
                            d_start=round(a0 - b0, 2), d_end=round(a1 - b1, 2),
                            d_dur=round((a1 - a0) - (b1 - b0), 2)))
        res[tag] = dict(n_mine=len(mine), n_legacy=len(legacy),
                        count_match=(len(mine) == len(legacy)), per_cycle=per)
    return res


# ══════════════════ 통합: 러너 소비용 trial 목록 ══════════════════
def _jump_mask(d):
    """p19 점프 규약 마스크: GRF 이륙(peak 후 <2% peak) + 0.1s. GRF 없으면 전체 창."""
    t = d["t"]
    g = d.get("grf_real")
    if g is None:
        return np.ones_like(t, bool)
    pk = int(np.argmax(g))
    below = np.where(g[pk:] < 0.02 * g[pk])[0]
    toff = t[pk + below[0]] if len(below) else t[-1]
    return t <= min(t[-1], toff + 0.1)


def all_new_trials():
    """점프 신규 세션을 p19_run.all_trials 규약 행으로:
    (ds, sub, d, gains, dqdes_on, ffk, mask, is_cvt, l_i) — 기존 CL/재생 러너 직접 소비.
    (s2s 자산은 별도 심판 — 이 목록에 넣지 않음.)"""
    rows = []
    for sub in SUBS_0422:
        d, m = load_jump_0422(sub)
        rows.append(("jump_0422", sub, d, m["gains"], m["dqdes_on"], m["ffk"],
                     _jump_mask(d), False, m["l_i"]))
    for sub in SUBS_0319TAU:
        d, m = load_jump_0319tau(sub)
        rows.append(("jump_0319tau", sub, d, m["gains"], m["dqdes_on"], m["ffk"],
                     _jump_mask(d), False, m["l_i"]))
    return rows


# ══════════════════ self-test ══════════════════
def _row_summary(tag, d, gains, extra=""):
    P = judge()
    rms = lambda a: float(np.sqrt(np.mean(np.asarray(a) ** 2)))
    a1 = P.J.ahat(P.A_PAPER, d["traw1"], d["dq1"])
    a2 = P.J.ahat(P.A_PAPER, d["traw2"], d["dq2"])
    g = "-" if gains is None else "/".join(f"{v:g}" for v in gains)
    print(f"{tag:26s} N={len(d['t']):6d} dur={d['t'][-1]:7.2f}s "
          f"q1[{d['q1'].min():+.2f},{d['q1'].max():+.2f}] "
          f"q2[{d['q2'].min():+.2f},{d['q2'].max():+.2f}] "
          f"pk|dq|={np.abs(d['dq1']).max():5.2f}/{np.abs(d['dq2']).max():5.2f} "
          f"rms(raw)={rms(d['traw1']):5.2f}/{rms(d['traw2']):5.2f} "
          f"rms(ahat)={rms(a1):5.2f}/{rms(a2):5.2f} "
          f"gains={g:22s} {extra}")


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("=" * 110)
    print("p23_loaders self-test — 3+1 자산 로드 + 골든 검증 (원본 읽기 전용, 산출물 없음)")
    print("=" * 110)

    print("\n[1] jump_0422 (FF cap 15Nm + PD, xlsx 직행 — csv 오염 우회)")
    for sub in SUBS_0422:
        d, m = load_jump_0422(sub)
        ex = f"h_real={d['h_real']:.3f}m grf={'Y' if d['grf_real'] is not None else 'N'}" \
             + (" ★hip게인=PID.txt(P70_D2)" if m["label_gain_mismatch"] else "")
        _row_summary(f"jump_0422/{sub}", d, m["gains"], ex)
        cap = max(float(np.max(np.abs(d["tdes1"]))), float(np.max(np.abs(d["tdes2"]))))
        assert cap <= m["tdes_cap"] + 1e-9, f"FF cap 위반: {cap} > {m['tdes_cap']}"

    print("\n    골든 검증: xlsx→Paper a_hat vs goal16 Mode A npz tau_real (기준 <1e-3)")
    v = validate_0422_vs_goal16()
    all_pass = True
    for sub, res in v.items():
        s1, s2 = res["tau1_real"], res["tau2_real"]
        ok = res["PASS"]
        all_pass &= ok
        print(f"    {sub:10s} hip max_rel_dev={s1['max_rel_dev']:.3e} (sign {s1['sign']:+d}) "
              f"knee max_rel_dev={s2['max_rel_dev']:.3e} (sign {s2['sign']:+d}) "
              f"n={s1['n']}  -> {'PASS' if ok else 'FAIL'}")
    print(f"    ==> 골든 검증 전체: {'PASS' if all_pass else 'FAIL'}")

    print("\n[2] jump_0319tau (FF cap 9Nm, 단일 trial — 하위 폴더 없음, root 0.32s 창 하나)")
    for sub in SUBS_0319TAU:
        d, m = load_jump_0319tau(sub)
        _row_summary(f"jump_0319tau/{sub}", d, m["gains"],
                     f"h_real=NaN grf={'Y' if d['grf_real'] is not None else 'N'}")
        r = m["gain_regression"]
        print(f"    게인 근거: {m['gains_source']}")
        for j, nm in (("1", "hip"), ("2", "knee")):
            print(f"      {nm}: kp={r[j]['kp']:.1f} kd={r[j]['kd']:.2f} "
                  f"cff={r[j]['cff']:.2f} R2={r[j]['r2']:.3f} n_sat={r[j]['n_sat']}")

    print("\n[3] s2s_0324 (지상 s2s 5 trial, 리샘플 — held-out DAY지만 fit-legal, 태깅됨)")
    for sub in SUBS_S2S_0324:
        d, m = load_s2s_0324(sub)
        _row_summary(f"s2s_0324/{sub[10:]}", d, m["gains"],
                     f"maxgap={m['max_gap_ms']['hip']:.0f}/{m['max_gap_ms']['knee']:.0f}ms "
                     f"fill={m['n_grid'] - m['n_raw']['hip']:+d} (드랍 보간)")

    print("\n[4] s2s_air 0319 (공중 15사이클, xlsx 재유도 + 레거시 검출 로직)")
    cycles, m = load_s2s_air()
    print(f"    버스트 {m['n_segments_raw']}개 → 병합(gap<2s) 사이클 {m['n_cycles_detected']}개, "
          f"마지막 잘림 drop={m['dropped_truncated_last']} → 반환 {len(cycles)}개")
    print(f"    리샘플: dt={m['dt_ms']}ms, max gap hip/knee = "
          f"{m['max_gap_ms']['hip']}/{m['max_gap_ms']['knee']}ms")
    print(f"    l_i=0.030 (★가정 — Clutch 미기록), airborne={m['airborne']}")
    for k, c in enumerate(cycles):
        print(f"    cyc{k + 1:02d} t0_abs={c['t0_abs']:7.2f}s dur={c['t'][-1]:5.2f}s "
              f"q2[{c['q2'].min():+.2f},{c['q2'].max():+.2f}] "
              f"pk|dq2|={np.abs(c['dq2']).max():4.2f}")
    print("\n    레거시 캐시 교차검증 (cycle_final.npz):")
    xc = crosscheck_s2s_air(m)
    for tag, r in xc.items():
        if r is None:
            print(f"    {tag}: 캐시 없음")
            continue
        print(f"    {tag}: 사이클 수 {r['n_mine']} vs {r['n_legacy']} "
              f"-> {'MATCH' if r['count_match'] else 'MISMATCH'}")
        dd = [p["d_dur"] for p in r["per_cycle"]]
        ds_ = [p["d_start"] for p in r["per_cycle"]]
        print(f"      구간 정합: 시작Δ 평균 {np.mean(ds_):+.2f}s, durΔ 평균 {np.mean(dd):+.2f}s "
              f"(레거시 pad ±0.5s vs 본 로더 ±0.1s 차이 반영)")
        for k, p in enumerate(r["per_cycle"]):
            print(f"      cyc{k + 1:02d} mine={p['mine']} legacy={p['legacy']} "
                  f"dStart={p['d_start']:+.2f} dDur={p['d_dur']:+.2f}")

    print("\n[5] all_new_trials() — p19_run.all_trials 규약 (기존 러너 직접 소비)")
    for ds, sub, d, gains, dqon, ffk, mask, is_cvt, l_i in all_new_trials():
        print(f"    ({ds!r}, {sub!r}, d[{len(d['t'])}], "
              f"gains={tuple(round(g, 2) for g in gains)}, dqdes={dqon}, ffk={ffk}, "
              f"mask {int(mask.sum())}/{len(mask)}, cvt={is_cvt}, l_i={l_i})")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
