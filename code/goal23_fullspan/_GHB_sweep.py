# -*- coding: utf-8 -*-
"""_GHB_sweep — 질량·탄성·마찰·변환식을 **한꺼번에** 맞춘다 (마라톤H, 2026-08-11).

왜 한꺼번에인가 (사용자 지시)
  08-11 에 확인된 것: 매달림 실측이 준 관절 마찰값을 **하나씩** 넣으면 전부 나빠진다.
  특히 속도비례 항을 실측대로(≈0) 줄이면 점프 높이가 +144% 무너진다.
  ⇒ 그 항은 관절 마찰이 아니라 **다른 손실을 대신 떠맡는 층**이고, 그 손실을 물리로
    바꾸려면 변환식·마찰·질량·탄성을 **같이** 움직여야 한다. 한 축씩으로는 못 넘는다.

두 판을 따로 돌려 맞대결시킨다
  ① 지금 구조 (`canon_cap`) — 분동 저울 곡선을 쓰되 보정폭을 상한으로 막는다.
  ② 새 구조 (`canon_fric`) — 곡선 전액을 쓰되 **하중에 비례하는 마찰**을 뺀다.
     기어·벨트는 전달하는 힘이 클수록 마찰이 커진다. 이러면 토크가 작은 매달림 시험에서
     안 보이고 도약에서 커지므로, 위 모순이 설명된다.
     ※ 일정한 마찰(건마찰)은 이 식에 안 넣는다 — 물리엔진의 관절 마찰 기능이
       떨림 없이 처리하므로 그쪽(FS_KNEEM_FL/FS_HIPM_FL)에 맡기고 여기선 하중비례분만 본다.

점수 (전부 낮을수록 좋음, 현행 스택 = 1.000)
  · 측정 토크 주입 재생 : 측정된 토크를 그대로 넣고 돌린 뒤 관절각·각속도 4채널 오차.
    PD 가 없어 오차를 못 감춘다 — 물리의 1급 심판.
  · 폐루프           : 실제 게인으로 PD 제어한 뒤 관절각·각속도·토크 6채널 오차.
  · 점프 높이        : 지면 기준 몸통 최고 높이, 영상 실측 대비 오차.
  점수 = 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이, **채널별로 기준선에 나눠 정규화**
  (큰 채널이 점수를 독식하는 것을 막는다 — 08-11 에 이 함정을 한 번 밟았다).

  적합 세션 = 0424·0602·0722·0723·0724·0725·0727
  게이트 전용 = **0324(별도 보관본)·0421(위치제어)** — 목적함수에 절대 안 들어간다.
  게이트 = 위 둘의 주입재생 + 0421 폐루프. 기준선보다 2% 넘게 나빠지면 벌점.
  ★ 변속기 세션(0429)은 **이 판에서 완전히 제외**한다 — 이 모델에 변속기 기하가 없다
    (08-12 사고, board() 주석). 변속기 게이트는 `python fs_cvt.py cl` 로 따로 본다.

★ 안 건드리는 축: 발 미끄럼 관련(FS_PRESLIDE·FS_IMPRATIO). 이 점수에는 미끄러짐이 안 들어가
  있어서, 같이 풀면 점수는 좋아지고 미끄러짐만 조용히 망가진다. 별도 심판이 있는 축이다.

CLI: python _GHB_sweep.py [시간예산_시간]     ※ 실행은 .bat 더블클릭으로 (헌법 3)
"""
import os, sys, io, json, time, math, collections
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
OUT = HERE / "_GHB_sweep.json"
LOG = HERE / "_GHB_sweep_trials.jsonl"

# ── 현행 배포 스택 (CURRENT_STACK.md H2_260811 의 env 레시피 그대로) ────────────────
#    ★ 08-11 사고: 채점할 때 이 중 2개만 설정해 **배포 스택이 아닌 지점**에서 쟀다.
#      기준선은 반드시 배포 스택이어야 하므로 여기에 박아둔다.
BASE_ENV = {
    "FS_TMAP": "canon_cap", "FS_TDCAP": "3.8,2.6",
    "FS_MASS": "3.28", "FS_FOOTR": "0.020",
    "FS_NOSUPP": "1", "FS_NOSPR": "1", "FS_NOBIAS": "1", "FS_NODEEP": "1",
    "FS_PRESLIDE": "0.86,0.85,0.02,1.0",
    "FS_CMD_LPF": "0.002,0.0025",
    "FS_IMPRATIO": "20",
}
# ★ 26.04.29(변속기)는 제외 — 이 판의 모델에 변속기 기하가 없다 (08-12 사고, board() 주석 참조).
FIT = ("26.04.24", "26.06.02", "26.07.22",
       "26.07.23", "26.07.24", "26.07.25", "26.07.27")
GATE_MA = ("26.03.24", "26.04.21")     # 변속기 게이트는 `python fs_cvt.py cl` 로 따로 본다
GATE_CL = ("26.04.21",)
CH6 = ("q1", "q2", "dq1", "dq2", "a1", "a2")
CH4 = ("q1", "q2", "dq1", "dq2")

# ── 축 정의 (이름, 하한, 상한, 현행값) — 경계는 실측·설계공차에서만 온다 ─────────────
COMMON = [
    ("무릎 건마찰",      0.15, 0.60, 0.2469),   # 매달림 실측 0.46
    ("힙 건마찰",        0.10, 0.40, 0.2383),   # 매달림 실측 0.28
    ("무릎 속도비례",    0.00, 0.25, 0.150),
    ("힙 속도비례",      0.00, 0.45, 0.312),
    ("총질량",           3.26, 3.30, 3.28),     # 케이블 제거 실측 3.26~3.30
    ("허벅지 무게중심z", -0.010, 0.025, 0.0),   # [m] 기존 위치에 가산
    ("힙 스프링",        100.0, 260.0, 150.0),
    ("힙 명령 지연",     0.000, 0.006, 0.002),  # [s]
    ("무릎 명령 지연",   0.000, 0.006, 0.0025),
]
# ★★ 08-11 무게추 왕복 데이터(`26_08_07/{0,2,4}kg/probe_sweep_v1`)로 하중비례 마찰을 **직접 쟀다.**
#   마라톤G 는 상행·하행을 **평균내서 마찰을 지우고** 중력만 봤다. 지운 그 절반차가 곧 마찰이다.
#     마찰[명령단위] = 0.135 + 0.1197·|하중|  (무릎, 상관 +0.75)  → 전달 효율 88%
#     마찰[명령단위] = 0.278 + 0.0029·|하중|  (힙,  사실상 0)     → 전달 효율 ≈100%
#   무릎 기울기는 2kg 에서 +0.1169, 4kg 에서 +0.1177 — **다른 두 하중이 0.7% 안에 일치**.
#   물리적으로 타당: 무릎은 4절 링크+벨트를 거치고 힙은 모터가 거의 직접 돌린다.
#   식이 요구하는 단위는 N·m 이므로 명령→토크 환산(힙 1.241 · 무릎 1.306)을 곱한다:
#     무릎 기울기 0.1197×1.306 = **0.156** · 힙 0.0029×1.241 = **0.004**
#   ⇒ 이 값을 **하한 앵커**로 쓴다. 고정하지는 않는다 — 마라톤G G6-D 가 "빠를 때 더 깎이는
#     손실(역기전력·KT 처짐·감속기 효율 저하)은 토크 채널로 원리상 측정 불가" 라고 확정했고,
#     이 측정은 초당 0.4~0.9 라디안의 **준정적** 값이다. 도약은 그보다 훨씬 빠르다.
#     즉 준정적 손실은 **반드시 있고**(하한), 동적 손실이 그 위에 더해질 수 있다(상한 여유).
#   ★ 직전 판(하한 0.05)은 힙의 실측 0.004 를 **탐색 범위 밖으로 밀어냈다** — 사용자 실행 40분 후 발각.
EXTRA = {
    # 보정 상한: 무게추는 명령 11.5 까지 **선형**임을 확인했으나 그건 준정적 값이다.
    #   상한이 낮다 = "빠를 때 깎인다"를 대신 떠맡는 것이라 물리적으로 배제할 수 없다.
    #   ⇒ 강제로 올리지 않고 범위를 넓혀 탐색이 정하게 한다 (검증 구간 7.2/6.4 도 포함).
    "canon_cap":  [("무릎 보정상한", 2.0, 12.0, 3.8), ("힙 보정상한", 1.2, 10.0, 2.6)],
    # ★ 범위 산정 (08-11 두 번 틀린 뒤 확정)
    #   하한 = **준정적 실측** (느릴 때의 손실은 반드시 있다): 무릎 0.156 · 힙 0.004
    #   상한 = "지금 상한이 하던 일을 전부 하중비례가 떠맡는" 극단까지 여유를 둔다.
    #     (지금 구조는 명령이 커지면 보정이 상한에 걸려 기울기가 a_hat 0.682 로 수렴한다.
    #      같은 곳에 닿는 하중기울기는 환산−0.682 = 무릎 0.624 · 힙 0.559.)
    #   ★ 그런데 그 등가점을 실제로 재보니 **더 나빠졌다** (0.40 에서 34.4 → 0.624 에서 164.7).
    #     마찰은 속도 반대로 작용하므로 **내려앉는 구간에서는 토크를 더한다** — 고속 구간만 보고
    #     세운 등가 논리가 저속·역방향 구간에서 깨진 것이다. 등가점은 상한 근처일 뿐 정답이 아니다.
    #     실측 6점 중 최선은 0.40/0.35 → 시작점은 그쪽으로 둔다 (범위는 양쪽을 다 감싼다).
    #   1차 시도의 상한 0.45 는 등가점을, 그 전 판의 하한 0.05 는 힙 실측을 범위 밖으로 밀어냈다.
    "canon_fric": [("무릎 하중기울기", 0.156, 0.80, 0.40), ("힙 하중기울기", 0.004, 0.70, 0.35),
                   ("무릎 속도문턱", 0.03, 3.00, 0.30), ("힙 속도문턱", 0.03, 3.00, 0.30)],
}


def env_of(mode, x):
    """축 벡터 → 환경변수 dict (현행 스택 위에 덮어쓴다)."""
    e = dict(BASE_ENV)
    e["FS_KNEEM_FL"] = f"{x[0]:.4f}"
    e["FS_HIPM_FL"] = f"{x[1]:.4f}"
    e["FS_KNEEM_DAMP"] = f"{x[2]:.4f}"
    e["FS_HIPM_DAMP"] = f"{x[3]:.4f}"
    e["FS_MASS"] = f"{x[4]:.4f}"
    e["FS_COMZ"] = f"thigh={x[5]:.5f}"
    e["FS_KS_HIP"] = f"{x[6]:.2f}"
    e["FS_CMD_LPF"] = f"{x[7]:.5f},{x[8]:.5f}"
    e["FS_TMAP"] = mode
    if mode == "canon_cap":
        e["FS_TDCAP"] = f"{x[9]:.3f},{x[10]:.3f}"
    else:
        e.pop("FS_TDCAP", None)
        # 일정몫(건마찰)은 0 — 물리엔진 관절 마찰이 담당한다. 점성도 0 (관절 감쇠가 담당).
        e["FS_TFRIC"] = (f"0,{x[9]:.4f},0,{x[11]:.4f},"
                         f"0,{x[10]:.4f},0,{x[12]:.4f}")
    return e


# ── 작업자별 1회 준비 (엑셀 읽기 ~80초 + 기준선) ───────────────────────────────────
_C = None
_BASE = None


def _apply(e):
    import fs_runner as FR
    for k in ("FS_KNEEM_FL", "FS_HIPM_FL", "FS_KNEEM_DAMP", "FS_HIPM_DAMP", "FS_MASS",
              "FS_COMZ", "FS_KS_HIP", "FS_CMD_LPF", "FS_TMAP", "FS_TDCAP", "FS_TFRIC",
              "FS_FOOTR", "FS_NOSUPP", "FS_NOSPR", "FS_NOBIAS", "FS_NODEEP",
              "FS_PRESLIDE", "FS_IMPRATIO"):
        os.environ.pop(k, None)
    os.environ.update(e)
    FR._S2S = None
    # 모델 캐시가 무한히 자라는 것을 막는다 (축 조합마다 새 모델 = 수만 개)
    if len(FR._CACHE) > 40:
        b = FR._CACHE.get("base")
        FR._CACHE.clear()
        if b is not None:
            FR._CACHE["base"] = b


def board():
    """반환 {세션: dict(ma=[4], cl=[6], h=오차)}"""
    import fs_data as FD, fs_compare_plot as CP, fs_runner as FR
    ft = FR.fs_twin()
    G = collections.defaultdict(lambda: dict(ma=[], cl=[], h=[]))
    for s, p, g, cvt, d, seg, pw in _C:
        try:
            t = d["t"]; m = (t >= pw[0]) & (t <= pw[1])
            i0 = int(np.argmax(m)); tg = t[m] - t[i0]
            sp = CP.sess_params(s)
            L = FR.rollout_ol_fs_b(ft, tg, d["raw1"][m], d["raw2"][m],
                                   float(d["q1"][i0]), float(d["q2"][i0]),
                                   float(d["dq1"][i0]), float(d["dq2"][i0]),
                                   float(tg[-1] - 0.004), bias1=sp["bias1"],
                                   knee_deep=sp["knee_deep"], fade=True)
            if L is not None:
                gf = lambda k: np.interp(tg, L["t"], L[k])
                sim = [gf("thm1"), gf("q2"), gf("dq1"), gf("dq2")]
                v = [float(np.sqrt(np.mean((d[k][m] - w) ** 2))) *
                     (180 / np.pi if k in ("q1", "q2") else 1) for k, w in zip(CH4, sim)]
                if all(np.isfinite(v)) and max(v) < 1e4:
                    G[s]["ma"].append(v)
                t_ext = min(t[m][-1] + 0.6, t[-1])
                m2 = (t >= t[i0]) & (t <= t_ext); tg2 = t[m2] - t[i0]
                H = FR.rollout_ol_fs_b(ft, tg2, d["raw1"][m2], d["raw2"][m2],
                                       float(d["q1"][i0]), float(d["q2"][i0]),
                                       float(d["dq1"][i0]), float(d["dq2"][i0]),
                                       float(tg2[-1] - 0.004), bias1=sp["bias1"],
                                       knee_deep=sp["knee_deep"], fade=True)
                hv = CP.real_h(p)
                if H is not None and hv is not None and np.isfinite(hv):
                    hh = abs(float(np.asarray(H["bz"]).max()) - float(hv))
                    if np.isfinite(hh):
                        G[s]["h"].append(hh)
            if g:
                d["_sess"] = s; d["_fold"] = p
                r = CP.cl_pair(d, seg, g, s)
                if r is not None:
                    _t, (mo, mf), old, fs, _m, _c, _ = r
                    v = [float(np.sqrt(np.mean((np.asarray(mf[k]) - np.asarray(fs[i])) ** 2))) *
                         (180 / np.pi if k in ("q1", "q2") else 1) for i, k in enumerate(CH6)]
                    if all(np.isfinite(v)) and max(v) < 1e4:
                        G[s]["cl"].append(v)
        except Exception:
            continue
    return {s: dict(ma=np.mean(v["ma"], axis=0).tolist() if v["ma"] else None,
                    cl=np.mean(v["cl"], axis=0).tolist() if v["cl"] else None,
                    h=float(np.mean(v["h"])) if v["h"] else None)
            for s, v in G.items() if v["ma"] or v["cl"]}


def _ensure():
    global _C, _BASE
    if _C is not None:
        return
    import fs_data as FD
    C = []
    for s, p, g, cvt, ho in FD.registry():
        # ★★ 08-12 사고: 변속기 trial(26.04.29)을 **무변속 모델로 채점**하고 있었다.
        #   l_i 는 4절의 입력 링크 길이라 **모델 치수 자체**다 (fs_cvt: l_i 2mm 차 → 바디 2mm 차).
        #   기본 트윈에는 그 기하도, 폐쇄 초기화(cvt_init)도, 전달비 소산도 없다.
        #   증상: 무릎각 오차 26.8° (다른 세션 1.1° 의 24배) · 측정토크를 넣어도 크랭크가
        #   실측 160° 중 52° 만 돌았다. 정본 경로(`python fs_cvt.py cl`)로는 0.97° 로 정상.
        #   ⇒ 여기서는 **변속기 trial 을 제외**하고, 변속기 게이트는 정본 경로로 따로 본다.
        #   (다른 채점 스크립트 `_GH3_eval` 등은 원래부터 `if cvt: continue` 로 빼고 있었다.)
        if cvt:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d); pw = FD.plot_window(p, d)
            if pw is None:
                continue
            t = d["t"]
            if ((t >= pw[0]) & (t <= pw[1])).sum() < 30:
                continue
            C.append((s, p, g, cvt, d, seg, pw))
        except Exception:
            continue
    _C = C
    _apply(dict(BASE_ENV))
    _BASE = board()


def ratio(B, key, sess):
    v = []
    for s in sess:
        if s not in B or B[s].get(key) is None or _BASE.get(s, {}).get(key) is None:
            continue
        a = np.asarray(B[s][key], float); b = np.asarray(_BASE[s][key], float)
        if np.all(b > 0) and np.all(np.isfinite(a)):
            v.append(float(np.mean(a / b)))
    return float(np.mean(v)) if v else np.nan


def evaluate(args):
    """반환 (벌점 포함 점수, 세부). 실패·발산은 큰 값."""
    mode, x = args
    try:
        _ensure()
        _apply(env_of(mode, np.asarray(x, float)))
        B = board()
        if not B:
            return 9e2, None
        ma = ratio(B, "ma", FIT); cl = ratio(B, "cl", FIT)
        hs = [B[s]["h"] / _BASE[s]["h"] for s in FIT
              if s in B and B[s].get("h") and _BASE.get(s, {}).get("h")]
        h = float(np.mean(hs)) if hs else np.nan
        if not (np.isfinite(ma) and np.isfinite(cl)):
            return 9e2, None
        if not np.isfinite(h):
            h = 3.0
        J = 0.40 * ma + 0.40 * cl + 0.20 * h
        pen = 0.0; gl = {}
        for s in GATE_MA:
            r = ratio(B, "ma", (s,)); gl[f"{s}MA"] = r
            if np.isfinite(r):
                pen += 10.0 * max(0.0, r - 1.02)
        for s in GATE_CL:
            r = ratio(B, "cl", (s,)); gl[f"{s}CL"] = r
            if np.isfinite(r):
                pen += 10.0 * max(0.0, r - 1.02)
        return J + pen, dict(J=J, ma=ma, cl=cl, h=h, pen=pen, gate=gl)
    except Exception:
        return 9e2, None


def obj(x, mode):
    return evaluate((mode, x))[0]


def compass(mode, x0, v0, lo, hi, nproc, t0, deadline_s, rounds=40):
    """마무리 다듬기 — 축마다 +한 걸음/−한 걸음을 **동시에** 재보고 좋아지면 옮긴다.

    좋아지는 데가 없으면 걸음을 절반으로 줄인다. 전역 탐색이 대충 찾아준 자리를
    조여 들어가는 단계다 (한 바퀴 = 축 수 ×2 회 평가 = 16개 동시면 20초 남짓).
    """
    import multiprocessing as mp
    n = len(x0)
    step = (hi - lo) * 0.06
    x, v = np.array(x0, float), float(v0)
    with mp.Pool(nproc) as pool:
        for it in range(rounds):
            if time.time() - t0 > deadline_s:
                print("    (시간 예산 도달 — 다듬기 중단)", flush=True); break
            cand = []
            for i in range(n):
                for sgn in (+1, -1):
                    y = x.copy(); y[i] = min(hi[i], max(lo[i], y[i] + sgn * step[i]))
                    if abs(y[i] - x[i]) > 1e-12:
                        cand.append(y)
            if not cand:
                break
            vals = pool.map(evaluate, [(mode, c) for c in cand])
            j = int(np.argmin([q[0] for q in vals]))
            if vals[j][0] < v - 1e-6:
                x, v = cand[j], float(vals[j][0])
                print(f"    다듬기 {it+1:2d}: {v:.5f}", flush=True)
            else:
                step *= 0.5
                if np.all(step < (hi - lo) * 0.002):
                    print(f"    다듬기 수렴 ({it+1} 바퀴)", flush=True); break
    return x, v


def run_mode(mode, budget_s, nproc):
    from scipy.optimize import differential_evolution
    axes = COMMON + EXTRA[mode]
    lo = np.array([a[1] for a in axes]); hi = np.array([a[2] for a in axes])
    cur = np.array([a[3] for a in axes])
    print(f"\n{'='*78}\n■ {mode} — 축 {len(axes)} 개", flush=True)
    for a in axes:
        print(f"    {a[0]:16s} {a[1]:>8.4g} ~ {a[2]:<8.4g}  (현행 {a[3]:g})", flush=True)
    t0 = time.time(); hist = []

    def cb(*a, **kw):
        # scipy 버전마다 콜백 인자가 다르다 (xk,convergence 또는 intermediate_result)
        xk = a[0] if a and not hasattr(a[0], "x") else (a[0].x if a else cur)
        v, det = evaluate((mode, xk))
        hist.append((float(v), list(map(float, xk))))
        el = time.time() - t0
        print(f"    [{el/60:6.1f}분] 최고 {v:.4f}  "
              f"(주입 {det['ma']:.4f} 폐루프 {det['cl']:.4f} 높이 {det['h']:.4f} 벌점 {det['pen']:.3f})"
              if det else f"    [{el/60:6.1f}분] {v:.1f}", flush=True)
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(mode=mode, t=el, v=float(v),
                                    x=list(map(float, xk)), det=det), ensure_ascii=False) + "\n")
        return el > budget_s
    res = differential_evolution(
        obj, list(zip(lo, hi)), args=(mode,), strategy="best1bin",
        maxiter=400, popsize=12, tol=1e-5, mutation=(0.4, 1.0), recombination=0.85,
        seed=20260811, polish=False, init="sobol", updating="deferred",
        workers=nproc, callback=cb, x0=cur, disp=False)
    xb, vb = np.asarray(res.x, float), float(res.fun)
    print(f"    전역 탐색 끝 {(time.time()-t0)/60:.0f}분 · 평가 {res.nfev} 회 · {vb:.5f}", flush=True)
    xb, vb = compass(mode, xb, vb, lo, hi, nproc, t0, budget_s * 1.25)
    v, det = evaluate((mode, xb))
    res.x, res.nfev = xb, res.nfev
    print(f"  → {mode} 완료 {(time.time()-t0)/60:.0f}분 · 평가 {res.nfev} 회 · 점수 {v:.4f}", flush=True)
    return dict(mode=mode, x=list(map(float, res.x)), score=float(v), det=det,
                axes=[a[0] for a in axes], cur=list(map(float, cur)),
                nfev=int(res.nfev), minutes=(time.time() - t0) / 60)


class Tee:
    """화면과 로그 파일에 동시에 쓴다 (6시간 실행이라 로그가 남아야 한다)."""

    def __init__(self, path):
        self.f = io.open(path, "a", encoding="utf-8")
        self.o = sys.stdout

    def write(self, s):
        self.o.write(s); self.f.write(s); self.f.flush()

    def flush(self):
        self.o.flush(); self.f.flush()


def main():
    budget_h = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    sys.stdout = Tee(HERE / "_GHB_sweep.log")
    print(f"\n{'#'*78}\n# 시작 {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'#'*78}")
    print("""
  마라톤H 공동 재적합 — 질량·탄성·마찰·변환식을 한꺼번에 맞춘다

  왜: 매달림 실측이 준 관절 마찰값을 하나씩 넣으면 전부 나빠진다. 특히 속도에
      비례하는 항을 실측대로(거의 0) 줄이면 점프 높이가 크게 무너진다. 그 항은
      관절 마찰이 아니라 다른 곳의 손실을 대신 떠맡고 있다는 뜻이고, 그걸 진짜
      물리로 바꾸려면 여러 값을 같이 움직여야 한다. 한 축씩으로는 못 넘는다.

  무엇을: 변환식 두 구조를 각각 최적화해서 맞붙인다.
      ① 지금 것  = 분동 저울 곡선을 쓰되 보정 폭을 상한으로 막음
      ② 새 것    = 곡선을 전액 쓰되 하중에 비례하는 마찰을 뺌
                  (기어·벨트는 전달하는 힘이 클수록 마찰이 커진다 — 토크가 작은
                   매달림 시험에서 안 보이고 도약에서 커지는 이유가 된다)

  점수: 0.40×주입재생 + 0.40×폐루프 + 0.20×점프높이. 현행 스택이 1.0000 이고
        낮을수록 좋다. 별도 보관본(0324)과 위치제어(0421)는 목적함수에서 빠지고
        게이트로만 쓴다. 게이트 5종이 2% 넘게 나빠지면 벌점.

  안 건드림: 발 미끄럼 관련 두 값. 이 점수에 미끄러짐이 안 들어가 있어서 같이
             풀면 점수만 좋아지고 미끄러짐이 조용히 망가진다.

  창을 닫지 마세요. 중간에 꺼도 _GHB_sweep_trials.jsonl 까지는 남습니다.
""", flush=True)
    nproc = max(1, min(16, (os.cpu_count() or 4) - 4))
    print(f"■ 마라톤H 공동 재적합 — 시간예산 {budget_h}시간 · 작업자 {nproc} 개", flush=True)
    print("  준비 중 (엑셀 읽기 + 기준선) …", flush=True)
    _ensure()
    print(f"  trial {len(_C)} 개 · 기준선 세션 {len(_BASE)} 개", flush=True)
    b0, d0 = evaluate(("canon_cap", [a[3] for a in COMMON] + [3.8, 2.6]))
    print(f"  현행 스택 재확인: 점수 {b0:.4f} (1.0000 이어야 정상)\n", flush=True)
    R = {}
    for mode in ("canon_cap", "canon_fric"):
        R[mode] = run_mode(mode, budget_h * 3600 / 2, nproc)
        import safe
        safe.atomic_json_write(OUT, dict(base_check=b0, res=R))
    print(f"\n{'='*78}\n■ 맞대결")
    print(f"{'구조':12s} {'점수':>8s} {'주입재생':>9s} {'폐루프':>8s} {'점프높이':>9s} {'벌점':>7s}")
    print(f"{'현행 스택':12s} {1.0:8.4f} {1.0:9.4f} {1.0:8.4f} {1.0:9.4f} {0.0:7.3f}")
    for m, r in R.items():
        d = r["det"] or {}
        print(f"{m:12s} {r['score']:8.4f} {d.get('ma',float('nan')):9.4f} "
              f"{d.get('cl',float('nan')):8.4f} {d.get('h',float('nan')):9.4f} {d.get('pen',0):7.3f}")
    for m, r in R.items():
        print(f"\n── {m} 최적값")
        for nm, v, c in zip(r["axes"], r["x"], r["cur"]):
            tag = ""
            axes = COMMON + EXTRA[m]
            a = [z for z in axes if z[0] == nm][0]
            if abs(v - a[1]) < 1e-6 * max(1, abs(a[1])) or abs(v - a[2]) < 1e-6 * max(1, abs(a[2])):
                tag = "  ★경계 포화 — 물리 재검 필요"
            print(f"    {nm:16s} {v:10.5f}  (현행 {c:g}){tag}")
        print(f"    게이트: " + " · ".join(f"{k} {100*(x-1):+.1f}%"
                                          for k, x in (r["det"] or {}).get("gate", {}).items()))
    print(f"\n저장 → {OUT}")


if __name__ == "__main__":
    main()
