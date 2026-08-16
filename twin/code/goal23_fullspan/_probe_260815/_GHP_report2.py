# -*- coding: utf-8 -*-
"""_GHP_report2 — 모양 가르기 + 모델의 기존 변속기 손실항과의 대조 (재생 없음)."""
import io, json, os, sys
from pathlib import Path
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["FS_CVT_XML"] = "0"
os.environ.setdefault("FS_SWEEP_AIR", "0"); os.environ.setdefault("FS_SWEEP_S2S", "1")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "goal22" / "p18_cvt"))
os.chdir(HERE)
import numpy as np
import _GHP_posture10 as PP
import fs_runner as FR, fs_cvt as FC, _GHB_sweep as S

S._apply(S.env_of("canon_cap", np.asarray(S.DEPLOY, float)))
ft0 = FR.fs_twin(); P = ft0["P"]; A = FR.tq_shape(P.A_PAPER)
TMAP = FR._tmap_init(P, A)
C_CVT = 0.792570673664162          # fourbar_p24a_candidate.json · FS_CVT_DISS_SCALE 기본 1

D = json.load(io.open("_GHP_posture10.json", encoding="utf-8"))
R = D["rows"]; F = D["fails"]
CASES = [("cvt/no_load", 0.0), ("cvt/load_2.5", 2.5), ("cvt/load_5", 5.0), ("no_cvt/no_load", 0.0)]
EDG = np.arange(-180, -9, 10.0)
BINS = [(EDG[i], EDG[i + 1]) for i in range(len(EDG) - 1)]
TAB_C = PP.ratio_table(0.025193); TAB_N = PP.ratio_table(0.030)
QG, RG = FC.RU.rtab(0.025193)

for x in R:
    x["r"], x["drdq"] = PP.r_at(TAB_N if not x["cvt"] else TAB_C, x["crank"])
    x["s2"] = TMAP(x["raw2"], x["dq2"], 1)                       # 축 토크 [N·m]
    rm = float(np.interp(np.radians(-x["crank"]), QG, RG))       # 모델이 쓰는 교환비
    x["r_model"] = rm
    x["amp_model"] = max(1.0 / max(abs(rm), 0.2) - 1.0, 0.0)
    x["amp_true"] = max(1.0 / max(abs(x["r"]), 0.2) - 1.0, 0.0)
    # 모델이 실제로 빼고 있는 변속기 손실 (무릎축) 과 그것의 크랭크축 환산
    vk = x["r"] * x["dq2"]
    x["loss_knee"] = -C_CVT * abs(x["s2"]) * x["amp_model"] * np.tanh(vk / 1.0) if x["cvt"] else 0.0
    x["loss_crank"] = x["loss_knee"] * x["r"] if x["cvt"] else 0.0
    x["dknee"] = x["delta_axis"] / x["r"] if abs(x["r"]) > 1e-6 else np.nan


def binstat(nm, key, a, b):
    z = [x[key] for x in R if x["sub"] == nm and a <= x["crank"] < b]
    return (np.mean(z), len(z)) if z else (np.nan, 0)


print("=" * 122)
print("표 9 — 모델이 지금 빼고 있는 변속기 손실 vs 되찾은 결손 (둘 다 크랭크 축토크 [N·m])")
print("   loss_crank = −C_CVT·|τ_axis|·amp_model·tanh(v_knee)·r   (C_CVT=0.7926, 배수 1.0)")
print(f"{'구간[도]':>13s}" + "".join(f"{nm.split('/')[0][:3]+'/'+nm.split('/')[1][:4]:>16s}" for nm, _ in CASES))
for a, b in BINS:
    line = f"{f'[{a:.0f},{b:.0f})':>13s}"
    for nm, _p in CASES:
        L, n = binstat(nm, "loss_crank", a, b)
        Dx, _ = binstat(nm, "delta_axis", a, b)
        line += f"  {L:+6.2f}/{Dx:+6.2f}" if n else f"{'':>16s}"
    print(line)
print("   (칸 = 모델손실 / 되찾은 Δ_axis. 부호가 같아야 '손실을 키우면 메워진다'.)")
print()
print("   같은 것을 배수로: 결손을 이 손실항만으로 메우려면 배수를 얼마로 해야 하나")
print(f"{'구간[도]':>13s}" + "".join(f"{nm:>16s}" for nm, _ in CASES))
for a, b in BINS:
    line = f"{f'[{a:.0f},{b:.0f})':>13s}"
    for nm, _p in CASES:
        L, n = binstat(nm, "loss_crank", a, b)
        Dx, _ = binstat(nm, "delta_axis", a, b)
        line += f"{(1 + Dx / L if abs(L) > 1e-6 else np.nan):16.2f}" if n else f"{'':>16s}"
    print(line)
print("   (1.0 = 지금 그대로. 음수/발산 = 이 항으로는 원리상 못 메운다.)")

print()
print("=" * 122)
print("표 10 — 모양 가르기 (종속변수 = Δ_axis [크랭크 축 N·m]). 각 후보에 대해 Δ=a+b·x 적합 R²")
CAND = [("amp_true = 1/r−1", "amp_true"), ("모델형 손실 loss_crank", "loss_crank"),
        ("r (교환비)", "r"), ("dr/dθ", "drdq"), ("θ (크랭크각)", "crank"),
        ("|τ_axis| (명령크기)", "s2"), ("v (크랭크속도)", "dq2")]
print(f"{'경우':>14s} {'n':>4s}" + "".join(f"{c[0]:>22s}" for c in CAND))
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm]
    y = np.array([x["delta_axis"] for x in s])
    line = f"{nm:>14s} {len(s):4d}"
    for lab, k in CAND:
        xv = np.array([abs(x[k]) if k == "s2" else x[k] for x in s], float)
        if np.std(xv) < 1e-12:
            line += f"{'(상수)':>22s}"; continue
        Am = np.column_stack([np.ones(len(xv)), xv])
        co, *_ = np.linalg.lstsq(Am, y, rcond=None)
        r2 = 1 - np.sum((y - Am @ co) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
        line += f"{r2:22.3f}"
    print(line)
print("  ※ '모델형 손실' 은 크기·부호가 이미 정해진 물리량이라, 여기 R² 는 '그 모양이 맞나' 만 본다.")

print()
print("표 11 — (1/r−1) 에 비례하나: 원점 통과 적합 Δ_axis = k·(1/r−1) 과 잔차")
print(f"{'경우':>14s} {'n':>4s} {'k':>9s} {'R²(원점)':>10s} {'잔차 RMS':>10s} {'|Δ| RMS':>10s}")
for nm, _p in CASES[:3]:
    s = [x for x in R if x["sub"] == nm]
    y = np.array([x["delta_axis"] for x in s]); xv = np.array([1 / x["r"] - 1 for x in s])
    k = float(np.sum(xv * y) / np.sum(xv * xv))
    res = y - k * xv
    print(f"{nm:>14s} {len(s):4d} {k:9.3f} {1-np.sum(res**2)/np.sum(y**2):10.3f} "
          f"{np.sqrt(np.mean(res**2)):10.3f} {np.sqrt(np.mean(y**2)):10.3f}")

print()
print("표 12 — 무릎축 환산 결손 Δ_knee = Δ_axis / r [무릎 축 N·m] (결손이 무릎 쪽 물리면 평평해야)")
print(f"{'구간[도]':>13s}" + "".join(f"{nm:>16s}" for nm, _ in CASES))
for a, b in BINS:
    line = f"{f'[{a:.0f},{b:.0f})':>13s}"
    for nm, _p in CASES:
        v, n = binstat(nm, "dknee", a, b)
        line += f"{v:16.2f}" if n else f"{'':>16s}"
    print(line)

print()
print("표 13 — 구간별 되찾기 실패 개수 (그 구간 평균이 얼마나 잘린 값인가)")
print(f"{'구간[도]':>13s}" + "".join(f"{nm:>16s}" for nm, _ in CASES))
for a, b in BINS:
    line = f"{f'[{a:.0f},{b:.0f})':>13s}"
    for nm, _p in CASES:
        ok = sum(1 for x in R if x["sub"] == nm and a <= x["crank"] < b)
        bad = sum(1 for x in F if x["sub"] == nm and a <= x["crank"] < b)
        line += f"{f'{ok}성공/{bad}실패':>16s}" if (ok or bad) else f"{'':>16s}"
    print(line)

print()
print("표 14 — 겹치는 구간(−140~−40도) 대조 조건")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm and -140 <= x["crank"] < -40]
    if not s:
        continue
    print(f"  {nm:16s} n={len(s):3d} · 크랭크속도 {np.mean([x['dq2'] for x in s]):.2f} rad/s "
          f"(범위 {min(x['dq2'] for x in s):.2f}~{max(x['dq2'] for x in s):.2f}) · "
          f"명령 |raw2| {np.mean([abs(x['raw2']) for x in s]):.2f} N·m · "
          f"축토크 |τ| {np.mean([abs(x['s2']) for x in s]):.2f} N·m")

print()
print("표 15 — 자세인가 '움직인 시간'인가 (두 변수는 한 시행 안에서 거의 같이 간다)")
print(f"{'경우':>14s} {'n':>4s} {'R²(θ)':>8s} {'R²(t)':>8s} {'R²(θ,t 둘다)':>12s} {'corr(θ,t)':>10s}")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm]
    y = np.array([x["delta_axis"] for x in s])
    th = np.array([x["crank"] for x in s]); tt = np.array([x["t0"] for x in s])
    def r2f(*cols):
        Am = np.column_stack([np.ones(len(y))] + list(cols))
        co, *_ = np.linalg.lstsq(Am, y, rcond=None)
        return 1 - np.sum((y - Am @ co) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
    print(f"{nm:>14s} {len(s):4d} {r2f(th):8.3f} {r2f(tt):8.3f} {r2f(th,tt):12.3f} "
          f"{np.corrcoef(th,tt)[0,1]:10.3f}")

print()
print("표 16 — ④ 축토크 단위로 다시 (겹치는 −140~−40도만) : Δ_axis = a + b·θ")
for nm, _p in CASES:
    s = [x for x in R if x["sub"] == nm and -140 <= x["crank"] < -40]
    if len(s) < 5:
        continue
    y = np.array([x["delta_axis"] for x in s]); th = np.array([x["crank"] for x in s])
    Am = np.column_stack([np.ones(len(th)), th])
    co, *_ = np.linalg.lstsq(Am, y, rcond=None)
    r2 = 1 - np.sum((y - Am @ co) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
    print(f"  {nm:16s} n={len(s):3d}  100도당 {100*co[1]:+6.2f} N·m · R²={r2:.2f} · "
          f"범위 {y.min():+6.2f}~{y.max():+6.2f} · 평균 {y.mean():+6.2f} · "
          f"짐 뺀 몸무게 정규화 {100*co[1]/(3.30+_p):+6.3f} N·m/kg")
print()
print("표 17 — 같은 구간 Δ_axis 를 하중(총질량)으로 나눠 본다 (하중 비례면 겹쳐야 한다)")
print(f"{'구간[도]':>13s}" + "".join(f"{nm:>16s}" for nm, _ in CASES))
for a, b in BINS:
    line = f"{f'[{a:.0f},{b:.0f})':>13s}"
    for nm, p in CASES:
        v, n = binstat(nm, "delta_axis", a, b)
        line += f"{v/(3.30+p):16.3f}" if n else f"{'':>16s}"
    print(line)
print("   (단위 N·m/kg. 총질량 = 로봇 3.30 + 짐)")
