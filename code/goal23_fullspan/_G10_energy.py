# -*- coding: utf-8 -*-
"""_G10_energy — **에너지 보존 감사**: "그 큰 토크로 이것밖에 못 뛰었나?" (사용자 질문 08-07).

동기
  G5 정본 곡선은 a_hat 대비 raw 1 에서 3.1배, raw 35.5 에서 1.5배 큰 토크를 주장한다.
  그렇다면 푸시의 **관절 일(∫τ·dq)** 도 그만큼 커지는데 점프 높이는 실측으로 고정돼 있다.
  → 척도가 과대면 **효율 η = 필요에너지/관절일** 이 비현실적으로 낮아진다.
  이 감사는 **토크 센서 척도를 전혀 전제하지 않는다** (총질량 + 기구학 + 실측 h 만 씀).

★ 기구학 구속의 정확한 형태 (이 로봇에서만 성립하는 행운)
  베이스는 **수직 레일** 위 → x 고정, z 만 자유. 발은 지면 위 → z_foot=0, x_foot 자유.
  ⇒ 접지 중에는 (q1,q2) **2자유도**로 전 배치가 결정된다. **미끄러짐을 가정하지 않는다**
    (발의 수평 이동은 기하학적으로 강제되며, 그 중 얼마가 '구름'이고 얼마가 '슬립'인지만 별개 문제).

네 갈래 계산
  ① 벌크(사용자 요청): 전 질량이 base 에 있다고 보고 E = m·g·(h_실측 − z_바닥)
  ② 정밀: 2자유도 라그랑주 ΔE(바닥→이지).  ①과 독립이므로 **서로 맞으면 둘 다 검증**된다.
  ③ 역방향: 관측 운동학이 **요구하는** 토크 τ_req = M q̈ + C + ∂V/∂q → 측정 raw 두 환산과 회귀.
     ★ 자체검산: ∫τ_req·dq ≡ ΔE (에너지 정리) — 안 맞으면 라그랑주 구현 버그.
  ④ 손실 예산: 관절마찰 + 발 미끄럼마찰이 남는 일을 설명할 수 있는가 (필요 μ 역산).

주의: GRF 는 데이터 사전상 **상대 타이밍 전용**. 이지 시점은 ż_base 극대(= 접지 이탈 순간,
      이후엔 −g 로 감속)로 재정의 — GRF 창의 늦은 검출을 교정한다.
CLI: python _G10_energy.py
"""
import os, sys, io, json, re
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["P25_CLIP_RAW"] = "35.5"
from pathlib import Path
import numpy as np
import mujoco as mjm
from scipy.signal import butter, filtfilt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "bench"))
import fs_data as FD                          # noqa: E402
import fs_runner as FR                        # noqa: E402

G = 9.80665
M_REAL = 3.26                                 # 사용자 실측 총질량 [kg]
FC1, FV1, FC2, FV2 = 0.19, 0.058, 0.19, 0.017   # G2-D 실측 관절마찰 (쿨롱[Nm], 점성[Nm·s/rad])
CURVE = json.load(io.open(HERE / "_G5_curve_final.json", encoding="utf-8"))
PAT_H = re.compile(r"실제 점프 높이\s*:\s*([\d.]+)")


def tau_canon(raw):
    """G5 정본 곡선의 역함수 (단조 — 판별식<0)."""
    d1, d2, d3 = CURVE["d1"], CURVE["d2"], CURVE["d3"]
    r = np.asarray(raw, float); t = r / d1
    for _ in range(60):
        f = d1 * t + d2 * t * np.abs(t) + d3 * t ** 3 - r
        df = d1 + 2 * d2 * np.abs(t) + 3 * d3 * t ** 2
        t = t - f / np.where(np.abs(df) < 1e-9, 1e-9, df)
    return t


def lpf(x, fc, fs=500.0, order=4):
    b, a = butter(order, fc / (fs / 2), btype="low")
    return filtfilt(b, a, np.asarray(x, float))


class Reduced:
    """접지 상태 (q1,q2) 2자유도 축약 — M(q), V(q), z_base, x_foot 를 트윈 기구학에서 수치 구성."""

    def __init__(self, ft):
        self.m = ft["model"]; self.iq = ft["iq"]; self.md = mjm.MjData(self.m)
        self.gf = mjm.mj_name2id(self.m, mjm.mjtObj.mjOBJ_GEOM, "foot")
        self.bf = int(self.m.geom_bodyid[self.gf])
        self.r = float(self.m.geom_size[self.gf][0])
        self.ids = [i for i in range(1, self.m.nbody) if self.m.body_mass[i] > 1e-6]
        self.mass = np.array([self.m.body_mass[i] for i in self.ids])
        self.iner = np.array([self.m.body_inertia[i][1] for i in self.ids])
        self.scale = M_REAL / float(self.mass.sum())
        self.ms = self.mass * self.scale; self.Is = self.iner * self.scale
        self._c = {}

    def _fw(self, q1, q2, zb):
        md = self.md
        md.qpos[self.iq["base_z"]] = zb
        md.qpos[self.iq["hip_m"]] = -q1 - np.pi / 2
        md.qpos[self.iq["hip"]] = 0.0
        md.qpos[self.iq["knee_motor"]] = -q2
        md.qpos[self.iq["cpin"]] = q2
        md.qpos[self.iq["knee"]] = -q2
        mjm.mj_forward(self.m, md)
        return md

    def state(self, q1, q2):
        """(z_base, x_foot, θ_foot바디, 바디별[x,z,θ]) — 발끝이 지면에 놓인 배치."""
        k = (round(q1, 9), round(q2, 9))
        if k in self._c:
            return self._c[k]
        md = self._fw(q1, q2, 0.0)
        zb = -(float(md.geom_xpos[self.gf][2]) - self.r)
        md = self._fw(q1, q2, zb)
        P = np.array([[md.xipos[i][0], md.xipos[i][2],
                       np.arctan2(md.xmat[i][2], md.xmat[i][0])] for i in self.ids])
        out = (zb, float(md.geom_xpos[self.gf][0]),
               float(np.arctan2(md.xmat[self.bf][2], md.xmat[self.bf][0])), P)
        if len(self._c) < 400000:
            self._c[k] = out
        return out

    def MV(self, q1, q2, h=2e-4):
        """M(q)[2×2], V(q)[J], z_base, ∂z_base/∂q, z_CoM, x_foot, ∂x_foot/∂q, ∂θ_foot/∂q."""
        zb, xf, thf, P0 = self.state(q1, q2)
        J = np.zeros((len(self.ids), 3, 2)); dzb = np.zeros(2); dxf = np.zeros(2); dth = np.zeros(2)
        for k, (a, b) in enumerate(((h, 0.0), (0.0, h))):
            zp, xp, tp, Pp = self.state(q1 + a, q2 + b)
            zm, xm, tm, Pm = self.state(q1 - a, q2 - b)
            J[:, :, k] = (Pp - Pm) / (2 * h)
            dzb[k] = (zp - zm) / (2 * h); dxf[k] = (xp - xm) / (2 * h); dth[k] = (tp - tm) / (2 * h)
        M = np.zeros((2, 2))
        for i in range(len(self.ids)):
            M += self.ms[i] * (np.outer(J[i, 0], J[i, 0]) + np.outer(J[i, 1], J[i, 1]))
            M += self.Is[i] * np.outer(J[i, 2], J[i, 2])
        V = G * float(self.ms @ P0[:, 1])
        zc = float(self.ms @ P0[:, 1]) / M_REAL
        dzc = np.array([float(self.ms @ J[:, 1, k]) / M_REAL for k in range(2)])
        return dict(M=M, V=V, zb=zb, dzb=dzb, zc=zc, dzc=dzc, xf=xf, dxf=dxf, dth=dth)

    def invdyn(self, q, dq, ddq, h=1e-3):
        """무손실 τ = M q̈ + C(q,q̇)q̇ + ∂V/∂q (2자유도 라그랑주, 수치 미분)."""
        s0 = self.MV(q[0], q[1])
        dM = np.zeros((2, 2, 2)); dV = np.zeros(2)
        for k in range(2):
            qp = q.copy(); qp[k] += h
            qm = q.copy(); qm[k] -= h
            sp = self.MV(qp[0], qp[1]); sm = self.MV(qm[0], qm[1])
            dM[:, :, k] = (sp["M"] - sm["M"]) / (2 * h)
            dV[k] = (sp["V"] - sm["V"]) / (2 * h)
        C = np.zeros(2)
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    C[i] += (dM[i, j, k] - 0.5 * dM[j, k, i]) * dq[j] * dq[k]
        return s0["M"] @ ddq + C + dV


def real_h(fold):
    f = Path(fold) / "Real Data.txt"
    if not f.exists():
        return None
    m = PAT_H.search(f.read_text(encoding="utf-8", errors="ignore"))
    if not m:
        return None
    v = float(m.group(1))
    return v / 100.0 if v > 5.0 else v


def main():
    R = Reduced(FR.fs_twin())
    print("=" * 128)
    print(f"⓪ 축약 모형 — 트윈 총질량 {float(R.mass.sum()):.4f} kg → 실측 {M_REAL} 로 재규격 "
          f"(×{R.scale:.4f}) · foot 반경 {R.r*1000:.1f} mm")
    for a, b in ((-45, -90), (-25, -50), (-70, -120)):
        s = R.MV(np.radians(a), np.radians(b))
        print(f"   q=({a:+4d},{b:+5d})°  z_base {s['zb']*1000:7.1f}  z_CoM {s['zc']*1000:7.1f} mm  "
              f"∂z_b/∂q [{s['dzb'][0]:+.4f},{s['dzb'][1]:+.4f}]  "
              f"∂x_foot/∂q [{s['dxf'][0]:+.4f},{s['dxf'][1]:+.4f}] m/rad")

    ROWS = []
    for sess, p, g, cvt, ho in FD.registry():
        if cvt:
            continue
        hr = real_h(p)
        if hr is None:
            continue
        try:
            d = FD.load2(p); seg = FD.segment(d)
        except Exception:
            continue
        t = d["t"]; dt = float(np.median(np.diff(t)))
        q1 = lpf(d["q1"], 30.0); q2 = lpf(d["q2"], 30.0)
        v1 = np.gradient(q1, dt); v2 = np.gradient(q2, dt)
        # ── 이지 재정의: ż_base 극대 (접지 이탈 직후엔 −g 감속하므로 여기가 최대) ──
        lo = max(seg["i_push"], 0); hi = min(seg["i_lo"] + int(0.06 / dt), len(t) - 3)
        zdot = np.array([R.MV(q1[i], q2[i])["dzb"] @ np.array([v1[i], v2[i]])
                         for i in range(lo, hi)])
        i_to = lo + int(np.argmax(zdot))
        i0 = seg["i_bot"]
        if i_to - i0 < 30:
            i0 = max(0, i_to - int(0.35 / dt))
        ROWS.append(dict(sess=sess, p=p, name=p.name, hr=hr, dt=dt, d=d, seg=seg,
                         q1=q1, q2=q2, v1=v1, v2=v2, i0=i0, i_to=i_to,
                         zdot_to=float(zdot.max()), i_lo=seg["i_lo"]))

    print("\n" + "=" * 128)
    print("① 이지 재검출 — GRF 창(i_lo)은 늦다. ż_base 극대점을 이지로 삼는다")
    print(f"{'세션':<11}{'trial':<20}{'i_lo→i_to[ms]':>13}{'z_바닥':>8}{'z_이지':>8}"
          f"{'ż_이지':>8}{'ż_CoM':>8}{'h_예측':>8}{'h_실측':>8}{'예측/실측':>9}")
    for r in ROWS:
        s0 = R.MV(r["q1"][r["i0"]], r["q2"][r["i0"]])
        s1 = R.MV(r["q1"][r["i_to"]], r["q2"][r["i_to"]])
        dq = np.array([r["v1"][r["i_to"]], r["v2"][r["i_to"]]])
        zc_dot = float(s1["dzc"] @ dq)
        t_up = max(zc_dot, 0) / G
        j = min(r["i_to"] + int(t_up / r["dt"]), len(r["q1"]) - 1)
        sa = R.MV(r["q1"][j], r["q2"][j])
        h_pred = s1["zc"] + max(zc_dot, 0) ** 2 / (2 * G) + (sa["zb"] - sa["zc"])
        r.update(s0=s0, s1=s1, zc_dot=zc_dot, h_pred=h_pred)
        print(f"{r['sess']:<11}{r['name'][:19]:<20}{(r['i_lo']-r['i_to'])*r['dt']*1000:13.0f}"
              f"{s0['zb']*1000:8.1f}{s1['zb']*1000:8.1f}{r['zdot_to']:8.2f}{zc_dot:8.2f}"
              f"{h_pred*1000:8.1f}{r['hr']*1000:8.1f}{h_pred/r['hr']:9.3f}")
    rt = np.array([r["h_pred"] / r["hr"] for r in ROWS])
    print(f"   ★ 예측/실측 중앙 {np.median(rt):.3f}  범위 [{rt.min():.3f}, {rt.max():.3f}]  "
          f"— 1.0 이면 기구학·질량·실측 h 가 **서로 독립적으로 검증**된다")

    # ── ② 일·에너지·자체검산 ──
    print("\n" + "=" * 128)
    print("② 관절일 vs 필요에너지 · **자체검산** ∫τ_req·dq ≡ ΔE (에너지 정리)")
    print(f"{'세션':<11}{'trial':<19}{'ΔE[J]':>8}{'∫τreq·dq':>9}{'검산Δ%':>7}{'E_벌크':>8}"
          f"{'W_a_hat':>9}{'W_정본':>9}{'η_a':>7}{'η_c':>7}{'W_c/W_a':>8}")
    for r in ROWS:
        i0, i1, dt = r["i0"], r["i_to"], r["dt"]
        sl = slice(i0, i1 + 1)
        v1, v2 = r["v1"], r["v2"]
        dq0 = np.array([v1[i0], v2[i0]]); dq1 = np.array([v1[i1], v2[i1]])
        E0 = 0.5 * dq0 @ r["s0"]["M"] @ dq0 + r["s0"]["V"]
        E1 = 0.5 * dq1 @ r["s1"]["M"] @ dq1 + r["s1"]["V"]
        dE = E1 - E0
        # 필요토크 (subsample 후 보간)
        f1 = lpf(v1, 20.0); f2 = lpf(v2, 20.0)
        a1 = np.gradient(f1, dt); a2 = np.gradient(f2, dt)
        idx = np.arange(i0, i1 + 1, 3)
        T = np.array([R.invdyn(np.array([r["q1"][i], r["q2"][i]]),
                               np.array([f1[i], f2[i]]), np.array([a1[i], a2[i]])) for i in idx])
        Wreq = float(np.trapezoid(T[:, 0] * f1[idx] + T[:, 1] * f2[idx], dx=3 * dt))
        tc1, tc2 = tau_canon(r["d"]["raw1"]), tau_canon(r["d"]["raw2"])
        Wa = float(np.trapezoid(r["d"]["a1"][sl] * v1[sl] + r["d"]["a2"][sl] * v2[sl], dx=dt))
        Wc = float(np.trapezoid(tc1[sl] * v1[sl] + tc2[sl] * v2[sl], dx=dt))
        Eb = M_REAL * G * (r["hr"] - r["s0"]["zb"])
        r.update(dE=dE, Wreq=Wreq, Wa=Wa, Wc=Wc, Eb=Eb, idx=idx, T=T, tc1=tc1, tc2=tc2,
                 f1=f1, f2=f2)
        print(f"{r['sess']:<11}{r['name'][:18]:<19}{dE:8.3f}{Wreq:9.3f}"
              f"{100*(Wreq-dE)/max(abs(dE),1e-9):7.1f}{Eb:8.3f}{Wa:9.3f}{Wc:9.3f}"
              f"{dE/max(Wa,1e-9):7.3f}{dE/max(Wc,1e-9):7.3f}{Wc/max(Wa,1e-9):8.3f}")
    for lab, k in (("a_hat", "Wa"), ("정본", "Wc")):
        e = np.array([r["dE"] / max(r[k], 1e-9) for r in ROWS])
        print(f"   η({lab}) 중앙 {np.median(e):.3f}  범위 [{e.min():.3f}, {e.max():.3f}]")
    q = np.array([r["dE"] / r["Eb"] for r in ROWS])
    print(f"   ΔE / E_벌크 중앙 {np.median(q):.3f} — 두 독립 경로의 일치도")

    # ── ③ 회귀: 측정 토크 = k · 필요 토크 ──
    print("\n" + "=" * 128)
    print("③ ★★ 회귀 τ_측정 = k·τ_필요 + b  (푸시 전 구간, 채널별). k<1 은 **물리적으로 불가능**")
    print("   — 실제 토크는 필요 토크에 마찰·미끄럼 손실을 더한 값이라 k≥1 이어야 한다")
    print(f"{'세션':<11}{'trial':<19}| {'k1_a':>6}{'R²':>6}{'k1_c':>6}{'R²':>6}"
          f" | {'k2_a':>6}{'R²':>6}{'k2_c':>6}{'R²':>6}")
    AG = {"k1a": [], "k1c": [], "k2a": [], "k2c": [], "r2_1a": [], "r2_1c": [],
          "r2_2a": [], "r2_2c": []}
    for r in ROWS:
        idx = r["idx"]; out = []
        for ch in (0, 1):
            x = r["T"][:, ch]
            A = np.column_stack([x, np.ones(len(x))])
            for tag, y in (("a", r["d"]["a1"][idx] if ch == 0 else r["d"]["a2"][idx]),
                           ("c", r["tc1"][idx] if ch == 0 else r["tc2"][idx])):
                c, *_ = np.linalg.lstsq(A, y, rcond=None)
                res = y - A @ c
                r2 = 1 - np.var(res) / max(np.var(y), 1e-12)
                out += [c[0], r2]
                AG[f"k{ch+1}{tag}"].append(c[0]); AG[f"r2_{ch+1}{tag}"].append(r2)
        print(f"{r['sess']:<11}{r['name'][:18]:<19}| {out[0]:6.3f}{out[1]:6.3f}"
              f"{out[2]:6.3f}{out[3]:6.3f} | {out[4]:6.3f}{out[5]:6.3f}{out[6]:6.3f}{out[7]:6.3f}")
    print(f"\n   {'채널':<7}{'환산':<7}{'k 중앙':>9}{'k 범위':>20}{'R² 중앙':>9}")
    for ch, nm in ((1, "힙"), (2, "무릎")):
        for tag, lab in (("a", "a_hat"), ("c", "정본")):
            v = np.array(AG[f"k{ch}{tag}"]); rr = np.array(AG[f"r2_{ch}{tag}"])
            print(f"   {nm:<7}{lab:<7}{np.median(v):9.3f}"
                  f"{f'[{v.min():.2f}, {v.max():.2f}]':>20}{np.median(rr):9.3f}")

    # ── ④ 손실 예산 ──
    print("\n" + "=" * 128)
    print("④ 손실 예산 — 남는 일을 관절마찰 + 발 미끄럼이 설명할 수 있나 (필요 μ 역산)")
    print(f"   관절마찰 실측: 쿨롱 {FC1}/{FC2} Nm · 점성 {FV1}/{FV2} Nm·s/rad (G2-D)")
    print(f"{'세션':<11}{'trial':<19}{'Δx_발':>8}{'구름분':>8}{'슬립':>8}{'∫N|ds|':>9}"
          f"{'W_관절마찰':>10}{'잉여_a':>8}{'μ_a':>7}{'잉여_c':>8}{'μ_c':>7}")
    MU = {"a": [], "c": []}
    for r in ROWS:
        i0, i1, dt = r["i0"], r["i_to"], r["dt"]
        S = [R.MV(r["q1"][i], r["q2"][i]) for i in range(i0, i1 + 1, 3)]
        v = np.array([[r["f1"][i], r["f2"][i]] for i in range(i0, i1 + 1, 3)])
        xf = np.array([s["xf"] for s in S]); zc = np.array([s["zc"] for s in S])
        vx = np.array([s["dxf"] @ v[k] for k, s in enumerate(S)])
        vth = np.array([s["dth"] @ v[k] for k, s in enumerate(S)])
        acc = np.gradient(np.gradient(zc, 3 * dt), 3 * dt)
        N = np.maximum(M_REAL * (G + acc), 0.0)
        v_slip = vx - R.r * vth            # 구름 성분 제거 = 순수 미끄럼 속도
        roll = float(np.trapezoid(np.abs(R.r * vth), dx=3 * dt))
        slip = float(np.trapezoid(np.abs(v_slip), dx=3 * dt))
        INT = float(np.trapezoid(N * np.abs(v_slip), dx=3 * dt))
        sl = slice(i0, i1 + 1)
        Wjf = float(np.trapezoid(FC1 * np.abs(r["v1"][sl]) + FV1 * r["v1"][sl] ** 2
                                 + FC2 * np.abs(r["v2"][sl]) + FV2 * r["v2"][sl] ** 2, dx=dt))
        ex_a = r["Wa"] - r["dE"] - Wjf; ex_c = r["Wc"] - r["dE"] - Wjf
        mu_a = ex_a / max(INT, 1e-9); mu_c = ex_c / max(INT, 1e-9)
        MU["a"].append(mu_a); MU["c"].append(mu_c)
        print(f"{r['sess']:<11}{r['name'][:18]:<19}{1000*abs(xf[-1]-xf[0]):8.1f}"
              f"{1000*roll:8.1f}{1000*slip:8.1f}{INT:9.2f}{Wjf:10.3f}"
              f"{ex_a:8.2f}{mu_a:7.2f}{ex_c:8.2f}{mu_c:7.2f}")
    for k, lab in (("a", "a_hat"), ("c", "정본")):
        v = np.array(MU[k])
        print(f"   필요 μ({lab}) 중앙 {np.median(v):.2f}  범위 [{v.min():.2f}, {v.max():.2f}]"
              f"  — 실측 정지 μ ≈ 0.85")

    # ── ⑤ 피크 일률·전류 ──
    print("\n" + "=" * 128)
    print("⑤ 피크 기계일률·전류 — 모터가 낼 수 있는 값인가 (AK80-9: GR 9, KT 0.091)")
    print(f"{'세션':<11}{'trial':<19}{'P_a[W]':>9}{'P_c[W]':>9}{'τ2max_a':>9}{'τ2max_c':>9}"
          f"{'I_a[A]':>8}{'I_c[A]':>8}")
    for r in ROWS:
        sl = slice(r["i0"], r["i_to"] + 1)
        pa = r["d"]["a1"][sl] * r["v1"][sl] + r["d"]["a2"][sl] * r["v2"][sl]
        pc = r["tc1"][sl] * r["v1"][sl] + r["tc2"][sl] * r["v2"][sl]
        t2a = np.abs(r["d"]["a2"][sl]).max(); t2c = np.abs(r["tc2"][sl]).max()
        print(f"{r['sess']:<11}{r['name'][:18]:<19}{pa.max():9.1f}{pc.max():9.1f}"
              f"{t2a:9.2f}{t2c:9.2f}{t2a/(9*0.091):8.1f}{t2c/(9*0.091):8.1f}")

    json.dump({r["name"] + "@" + r["sess"]: dict(dE=r["dE"], Eb=r["Eb"], Wa=r["Wa"], Wc=r["Wc"],
                                                 h_pred=r["h_pred"], hr=r["hr"])
               for r in ROWS}, io.open(HERE / "_G10_energy.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: _G10_energy.json")


if __name__ == "__main__":
    main()
